"""tests/test_projects.py — TC: CRUD Project (service + route)."""
import pytest
from sqlalchemy import event

from app.extensions import db
from app.forms.task_forms import project_choices
from app.models import Project, Task
from app.services.project_service import project_service
from app.services.task_service import task_service


@pytest.fixture
def sample_project(app):
    return project_service.create(name="Pekerjaan", color="#3B82F6", icon="briefcase")


class TestProjectService:
    """TC-04: CRUD Project via service."""

    def test_create_berhasil(self, sample_project):
        assert sample_project.id is not None
        assert sample_project.name == "Pekerjaan"
        assert sample_project.color == "#3B82F6"

    def test_create_nama_kosong_valueerror(self, app):
        with pytest.raises(ValueError, match="wajib diisi"):
            project_service.create(name="   ", color="#3B82F6")

    def test_create_warna_invalid_valueerror(self, app):
        with pytest.raises(ValueError, match="hex"):
            project_service.create(name="X", color="merah")

    def test_update_berhasil(self, sample_project):
        updated = project_service.update(sample_project.id, name="Kantor", color="#8B5CF6", icon="building")
        assert updated.name == "Kantor"
        assert updated.color == "#8B5CF6"

    def test_update_tidak_ada_valueerror(self, app):
        with pytest.raises(ValueError, match="tidak ditemukan"):
            project_service.update(999, name="X", color="#3B82F6")

    def test_archive_dan_pulihkan(self, sample_project):
        assert project_service.set_archived(sample_project.id, True).archived is True
        assert project_service.get_all() == []  # exclude archived by default
        assert project_service.set_archived(sample_project.id, False).archived is False

    def test_delete_dengan_task_ditolak(self, sample_project):
        """Strict mode: project berisi task tidak boleh dihapus (task tak boleh yatim)."""
        project_id = sample_project.id
        task_service.create(title="Tugas A", project_id=project_id)
        with pytest.raises(ValueError, match="masih memiliki 1 tugas"):
            project_service.delete(project_id)
        db.session.expire_all()
        assert db.session.get(Project, project_id) is not None

    def test_delete_tanpa_task_menghapus_project(self, sample_project):
        project_id = sample_project.id
        project_service.delete(project_id)
        db.session.expunge_all()
        assert db.session.get(Project, project_id) is None


class TestProjectCounts:
    """TC-05: Counts aggregate untuk kartu project."""

    def test_counts_dihitung_benar(self, sample_project):
        task_service.create(title="T1", project_id=sample_project.id, status="done")
        task_service.create(title="T2", project_id=sample_project.id)
        view = project_service.get_by_id(sample_project.id)
        assert view is not None
        assert view.total_tasks == 2
        assert view.done_tasks == 1
        assert view.active_tasks == 1
        assert view.archived_tasks == 0

    def test_counts_dengan_arsip(self, sample_project):
        """Task terarsip masuk hitungan Arsip dan KELUAR dari Selesai (saling lepas)."""
        done = task_service.create(title="T1", project_id=sample_project.id, status="done")
        task_service.archive(done.id)
        task_service.create(title="T2", project_id=sample_project.id)
        view = project_service.get_by_id(sample_project.id)
        assert view is not None
        assert view.total_tasks == 2
        assert view.active_tasks == 1
        assert view.done_tasks == 0
        assert view.archived_tasks == 1

    def test_count_all_project(self, sample_project):
        other = project_service.create(name="Arsip", color="#111111")
        project_service.set_archived(other.id, True)
        total, active = project_service.count_all()
        assert total == 2
        assert active == 1


class TestProjectRoutes:
    """TC-06: Project routes (PRG + proteksi)."""

    def test_list_tampil(self, client, login_user, sample_project):
        response = client.get("/projects/")
        assert response.status_code == 200
        assert b"Pekerjaan" in response.data

    def test_detail_404_bila_tidak_ada(self, client, login_user):
        assert client.get("/projects/NonexistentId123").status_code == 404

    def test_detail_tampilkan_tugas_dan_arsip(self, client, login_user, sample_project):
        """Section Tugas berisi task aktif; section Arsip berisi task terarsip."""
        done = task_service.create(title="Tugas Lama", project_id=sample_project.id, status="done")
        task_service.archive(done.id)
        task_service.create(title="Tugas Aktif", project_id=sample_project.id)
        response = client.get(f"/projects/{sample_project.public_id}")
        assert response.status_code == 200
        assert b"Tugas Aktif" in response.data
        assert b"Tugas Lama" in response.data
        assert b"Arsip" in response.data

    def test_create_via_post_persist_dan_redirect(self, client, login_user):
        response = client.post(
            "/projects/create",
            data={"name": "Rumah", "color": "#10B981", "icon": "house"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert db.session.query(Project).filter_by(name="Rumah").first() is not None

    def test_create_invalid_flash_error_dan_tanpa_persist(self, client, login_user):
        response = client.post(
            "/projects/create",
            data={"name": "X", "color": "bukan-hex", "icon": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"hex" in response.data
        assert db.session.query(Project).filter_by(name="X").first() is None


def _create_child(parent: Project, name: str) -> Project:
    """Bikin sub project langsung via model — service.create belum terima parent (Fase 3)."""
    child = Project(name=name, color="#111111", parent=parent)
    db.session.add(child)
    db.session.commit()
    return child


class TestProjectHierarchyRead:
    """TC-07: read layer hierarki project — Fase 2."""

    def test_get_roots_hanya_root_dan_child_count(self, app, sample_project):
        child = _create_child(sample_project, "Sub A")

        roots = project_service.get_roots()
        assert [r.id for r in roots] == [sample_project.id]
        assert roots[0].child_count == 1
        assert roots[0].parent_id is None

        child_view = project_service.get_by_id(child.id)
        assert child_view.parent_public_id == sample_project.public_id
        assert child_view.parent_name == "Pekerjaan"
        assert child_view.child_count == 0

    def test_counts_root_menjumlahkan_sub_project(self, app, sample_project):
        child = _create_child(sample_project, "Sub A")
        task_service.create(title="Root aktif", project_id=sample_project.id)
        task_service.create(title="Sub done", project_id=child.id, status="done")

        root = project_service.get_by_id(sample_project.id)
        assert root.total_tasks == 2
        assert root.active_tasks == 1
        assert root.done_tasks == 1

        child_view = project_service.get_by_id(child.id)
        assert child_view.total_tasks == 1
        assert child_view.active_tasks == 0

    def test_counts_root_tetap_menghitung_sub_terarsip(self, app, sample_project):
        child = _create_child(sample_project, "Sub A")
        project_service.set_archived(child.id, True)
        task_service.create(title="T", project_id=child.id)

        root = project_service.get_by_id(sample_project.id)
        assert root.child_count == 1
        assert root.total_tasks == 1  # subtree tetap dihitung walau sub diarsipkan
        assert project_service.get_children(sample_project.id) == []
        assert [v.id for v in project_service.get_children(sample_project.id, include_archived=True)] == [child.id]

    def test_get_hierarchical_root_lalu_sub_dan_skip_parent_arsip(self, app, sample_project):
        beta = _create_child(sample_project, "Beta")
        alpha = _create_child(sample_project, "Alpha")
        archived_root = project_service.create(name="Lain", color="#222222")
        archived_child = _create_child(archived_root, "Anak Lain")
        project_service.set_archived(archived_root.id, True)

        ordered = project_service.get_hierarchical()
        assert [v.name for v in ordered] == ["Pekerjaan", "Alpha", "Beta"]
        assert {v.id for v in ordered} == {sample_project.id, alpha.id, beta.id}
        assert archived_child.id not in {v.id for v in ordered}

    def test_project_choices_label_hierarkis(self, app, sample_project):
        child = _create_child(sample_project, "Sub A")

        choices = dict(project_choices())
        assert choices[str(sample_project.id)] == "Pekerjaan"
        assert choices[str(child.id)] == "Pekerjaan / Sub A"


class TestProjectReadPerformance:
    """TC-08: listing project tidak menarik task/reminder (anti N+1)."""

    def test_get_all_satu_query(self, app, sample_project):
        _create_child(sample_project, "Sub A")
        statements: list[str] = []

        def _capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        engine = db.engine
        event.listen(engine, "before_cursor_execute", _capture)
        try:
            project_service.get_all()
        finally:
            event.remove(engine, "before_cursor_execute", _capture)

        assert len(statements) == 1
