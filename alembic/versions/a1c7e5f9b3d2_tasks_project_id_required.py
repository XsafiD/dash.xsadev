"""tasks_project_id_required

Fase 5 — strict mode: setiap task WAJIB menempel ke project.

1. Backfill: task dengan `project_id IS NULL` dipindah ke project root
   "Umum" (dibuat bila belum ada). Di produksi tidak ada baris NULL,
   jadi langkah ini no-op — tetap ada sebagai jaring aman untuk DB lain.
2. `tasks.project_id` diubah menjadi NOT NULL.
3. FK `tasks.project_id` diganti `ON DELETE SET NULL` → `ON DELETE RESTRICT`
   supaya project yang masih memiliki task tidak bisa dihapus (ProjectService
   sudah memeriksa lebih dulu dan memberi pesan yang jelas).

Downgrade mengembalikan nullable + `SET NULL`, tetapi TIDAK memindahkan
task kembali ke NULL (keputusan data, bukan skema).

Revision ID: a1c7e5f9b3d2
Revises: 05adfc59cd88
Create Date: 2026-10-25 03:10:00.000000

"""
import secrets
import string
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c7e5f9b3d2"
down_revision: Union[str, None] = "05adfc59cd88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FALLBACK_NAME = "Umum"
_BASE62 = string.ascii_letters + string.digits


def _backfill_unassigned(bind) -> None:
    """Pindahkan task tanpa project ke project root "Umum" (idempotent)."""
    unassigned = bind.execute(
        sa.text("SELECT COUNT(*) FROM tasks WHERE project_id IS NULL")
    ).scalar_one()
    if not unassigned:
        return

    row = bind.execute(
        sa.text(
            "SELECT id FROM projects "
            "WHERE parent_id IS NULL AND name = :name ORDER BY id LIMIT 1"
        ),
        {"name": _FALLBACK_NAME},
    ).first()
    if row is None:
        public_id = "".join(secrets.choice(_BASE62) for _ in range(12))
        bind.execute(
            sa.text(
                "INSERT INTO projects (public_id, name, color, icon, archived, created_at) "
                "VALUES (:public_id, :name, :color, :icon, 0, CURRENT_TIMESTAMP)"
            ),
            {
                "public_id": public_id,
                "name": _FALLBACK_NAME,
                "color": "#64748B",
                "icon": "inbox",
            },
        )
        row = bind.execute(
            sa.text("SELECT id FROM projects WHERE public_id = :public_id"),
            {"public_id": public_id},
        ).first()

    bind.execute(
        sa.text("UPDATE tasks SET project_id = :project_id WHERE project_id IS NULL"),
        {"project_id": row[0]},
    )


def _project_fk_name(bind) -> str | None:
    """Nama FK pada `tasks.project_id` (MySQL menamai otomatis tasks_ibfk_1)."""
    for fk in sa.inspect(bind).get_foreign_keys("tasks"):
        if fk.get("constrained_columns") == ["project_id"]:
            return fk.get("name")
    return None


def upgrade() -> None:
    bind = op.get_bind()
    _backfill_unassigned(bind)

    fk_name = _project_fk_name(bind)
    if fk_name:
        op.drop_constraint(fk_name, "tasks", type_="foreignkey")

    op.alter_column("tasks", "project_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "fk_tasks_project_id",
        "tasks",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_tasks_project_id", "tasks", type_="foreignkey")
    op.alter_column("tasks", "project_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        "fk_tasks_project_id",
        "tasks",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
