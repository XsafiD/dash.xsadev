"""
controllers/archive_controller.py — Blueprint ``archive_bp``.

Routes (semua login_required):
  - GET /arsip/  — daftar tugas terarsip (filter + pagination via query params)
"""
from flask import Blueprint, render_template, request

from app.services.project_service import project_service
from app.services.task_service import task_service
from app.utils.decorators import login_required

archive_bp = Blueprint("archive", __name__, url_prefix="/arsip")

PER_PAGE_OPTIONS = (10, 25, 50, 100)
DEFAULT_PER_PAGE = 25
MAX_PER_PAGE = 100


def _parse_pagination() -> tuple[int, int]:
    """Baca `page`/`per_page` query args dengan fallback aman.

    `per_page` hanya diterima bila ada di ``PER_PAGE_OPTIONS`` (cap implisit
    ``MAX_PER_PAGE``) — cegah user meminta ribuan row sekaligus.
    """
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = request.args.get("per_page", DEFAULT_PER_PAGE, type=int)
    if per_page not in PER_PAGE_OPTIONS:
        per_page = DEFAULT_PER_PAGE
    return page, min(per_page, MAX_PER_PAGE)


@archive_bp.route("/")
@login_required
def index():
    """Daftar tugas terarsip — sort `archived_at` terbaru dulu, paginated."""
    project_id = request.args.get("project_id")
    filters: dict = {}
    if project_id and project_id.isdigit():
        filters["project_id"] = int(project_id)

    page, per_page = _parse_pagination()
    return render_template(
        "archive/list.html",
        pagination=task_service.get_archived_paginated(
            filters=filters, page=page, per_page=per_page
        ),
        filters=filters,
        projects_all=project_service.get_all(),
        per_page_options=PER_PAGE_OPTIONS,
        per_page=per_page,
    )
