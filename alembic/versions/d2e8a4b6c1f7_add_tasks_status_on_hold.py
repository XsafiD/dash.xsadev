"""add_tasks_status_on_hold

Status task baru: ON_HOLD ("Tertunda") — tugas yang sengaja ditahan /
belum bisa dikerjakan saat ini, terpisah dari todo maupun selesai.

ADDITIVE-ONLY: member enum di-APPEND di posisi terakhir definisi ENUM
MySQL sehingga nilai lama ('TODO','IN_PROGRESS','DONE') tetap valid
tanpa menyentuh data. Downgrade menyempitkan definisi ENUM, maka baris
ON_HOLD dipulihkan ke IN_PROGRESS terlebih dahulu (strict mode MySQL
menolak alter bila ada nilai di luar definisi ENUM).

Revision ID: d2e8a4b6c1f7
Revises: a1c7e5f9b3d2
Create Date: 2026-10-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2e8a4b6c1f7"
down_revision: Union[str, None] = "a1c7e5f9b3d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# SQLEnum menyimpan NAME member enum ke kolom MySQL ('TODO'), bukan value ('todo').
_OLD_STATUS = sa.Enum("TODO", "IN_PROGRESS", "DONE", name="task_status")
_NEW_STATUS = sa.Enum("TODO", "IN_PROGRESS", "DONE", "ON_HOLD", name="task_status")


def upgrade() -> None:
    # existing_nullable=False → Alembic merender NOT NULL. Wajib eksplisit:
    # MODIFY ENUM tanpa NOT NULL me-reset kolom jadi nullable (gotcha MySQL).
    op.alter_column(
        "tasks", "status", existing_type=_OLD_STATUS, type_=_NEW_STATUS, existing_nullable=False
    )


def downgrade() -> None:
    op.execute("UPDATE tasks SET status = 'IN_PROGRESS' WHERE status = 'ON_HOLD'")
    op.alter_column(
        "tasks", "status", existing_type=_NEW_STATUS, type_=_OLD_STATUS, existing_nullable=False
    )
