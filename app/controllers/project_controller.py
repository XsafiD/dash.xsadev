"""
controllers/project_controller.py — Blueprint ``project_bp``.

Routes (semua login_required):
  - GET/POST /projects/                — daftar project root / (POST tidak dipakai)
  - GET/POST /projects/create          — tambah project root
  - GET      /projects/<id>            — detail (+ daftar sub project bila root)
  - GET/POST /projects/<id>/edit       — edit (+ pindah root/sub)
  - GET/POST /projects/<id>/sub/create — tambah sub project
  - POST     /projects/<id>/archive    — arsipkan / pulihkan
  - POST     /projects/<id>/delete     — hapus (+ sub project)
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.forms.project_forms import ProjectForm
from app.services.project_service import ProjectView, project_service
from app.services.task_service import task_service
from app.utils.decorators import login_required

project_bp = Blueprint("project", __name__, url_prefix="/projects")

_ROOT_LABEL = "— Jadikan Project Utama —"


def _form_payload(form: ProjectForm) -> dict:
    """Ambil data form tanpa token CSRF."""
    return {k: v for k, v in form.data.items() if k != "csrf_token"}


def _get_project_or_404(public_id: str) -> ProjectView:
    project = project_service.get_by_public_id(public_id)
    if project is None:
        abort(404)
    return project


def _after_write_target(project: ProjectView) -> str:
    """Kembali ke parent untuk sub project (tidak tampil di daftar root)."""
    if project.parent_id is not None and project.parent_public_id:
        return url_for("project.detail", project_id=project.parent_public_id)
    return url_for("project.index")


def _parent_choices(project: ProjectView) -> list[tuple[str, str]]:
    """Pilihan parent = root aktif; parent terarsip saat ini tetap ditampilkan."""
    choices: list[tuple[str, str]] = [("", _ROOT_LABEL)]
    seen: set[int] = set()
    for root in project_service.get_roots():
        if root.id == project.id:
            continue
        choices.append((str(root.id), root.name))
        seen.add(root.id)
    if project.parent_id is not None and project.parent_id not in seen:
        parent = project_service.get_by_id(project.parent_id)
        if parent is not None:
            choices.append((str(parent.id), f"{parent.name} (diarsipkan)"))
    return choices


@project_bp.route("/")
@login_required
def index():
    roots = project_service.get_roots(include_archived=True)
    active = [p for p in roots if not p.archived]
    archived = [p for p in roots if p.archived]
    return render_template("project/list.html", projects=active, archived_projects=archived)


@project_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    form = ProjectForm()
    if form.validate_on_submit():
        try:
            project = project_service.create(**_form_payload(form))
            flash(f"Project '{project.name}' berhasil dibuat.", "success")
            return redirect(url_for("project.index"))
        except ValueError as err:
            flash(str(err), "error")
    return render_template("project/create.html", form=form)


@project_bp.route("/<string:project_id>")
@login_required
def detail(project_id: str):
    project = _get_project_or_404(project_id)
    filters = {"project_id": project.id}
    sub_projects: list[ProjectView] = []
    archived_sub_projects: list[ProjectView] = []
    if project.parent_id is None:
        children = project_service.get_children(project.id, include_archived=True)
        sub_projects = [c for c in children if not c.archived]
        archived_sub_projects = [c for c in children if c.archived]
    return render_template(
        "project/detail.html",
        project=project,
        tasks=task_service.get_all(filters=filters),
        archived_tasks=task_service.get_archived(filters=filters),
        sub_projects=sub_projects,
        archived_sub_projects=archived_sub_projects,
    )


@project_bp.route("/<string:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit(project_id: str):
    project = _get_project_or_404(project_id)
    form = ProjectForm(obj=project)
    form.parent_id.choices = _parent_choices(project)
    if form.validate_on_submit():
        try:
            project_service.update(project.id, **_form_payload(form))
            flash(f"Project '{project.name}' berhasil diperbarui.", "success")
            return redirect(url_for("project.detail", project_id=project.public_id))
        except ValueError as err:
            flash(str(err), "error")
    return render_template("project/edit.html", form=form, project=project)


@project_bp.route("/<string:project_id>/sub/create", methods=["GET", "POST"])
@login_required
def create_sub(project_id: str):
    """Tambah sub project — parent ditentukan route, bukan input user."""
    parent = _get_project_or_404(project_id)
    if parent.parent_id is not None:
        flash("Sub project tidak bisa memiliki sub project lagi (maksimal 2 level).", "error")
        return redirect(url_for("project.detail", project_id=parent.public_id))
    if parent.archived:
        flash("Project yang diarsipkan tidak bisa ditambah sub project. Pulihkan dulu.", "error")
        return redirect(url_for("project.detail", project_id=parent.public_id))

    form = ProjectForm()
    if form.validate_on_submit():
        payload = _form_payload(form)
        payload.pop("parent_id", None)
        try:
            sub = project_service.create(**payload, parent_id=parent.id)
            flash(f"Sub project '{sub.name}' berhasil dibuat di '{parent.name}'.", "success")
            return redirect(url_for("project.detail", project_id=parent.public_id))
        except ValueError as err:
            flash(str(err), "error")
    return render_template("project/create.html", form=form, parent=parent)


@project_bp.route("/<string:project_id>/archive", methods=["POST"])
@login_required
def archive(project_id: str):
    project = _get_project_or_404(project_id)
    archived = request.form.get("archived", "true").lower() in {"1", "true", "yes"}
    target = _after_write_target(project)
    try:
        project = project_service.set_archived(project.id, archived)
    except ValueError:
        abort(404)
    verb = "diarsipkan" if archived else "dipulihkan"
    flash(f"Project '{project.name}' berhasil {verb}.", "success")
    return redirect(target)


@project_bp.route("/<string:project_id>/delete", methods=["POST"])
@login_required
def delete(project_id: str):
    project = _get_project_or_404(project_id)
    name, child_count = project.name, project.child_count
    target = _after_write_target(project)
    try:
        project_service.delete(project.id)
    except ValueError:
        abort(404)
    message = f"Project '{name}' dihapus."
    if child_count:
        message += f" {child_count} sub project ikut terhapus."
    flash(message + " Tugas di dalamnya kini tanpa project.", "success")
    return redirect(target)
