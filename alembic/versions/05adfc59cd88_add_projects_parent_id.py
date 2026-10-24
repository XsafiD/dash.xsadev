"""add_projects_parent_id

Hierarki 2 level project → sub project lewat self-reference.

ADDITIVE-ONLY: kolom nullable, tanpa backfill dan tanpa menyentuh tabel
`tasks`. Semua baris `projects` yang sudah ada otomatis menjadi root
(`parent_id = NULL`), sehingga aplikasi versi lama tetap berjalan normal
setelah migrasi ini.

Revision ID: 05adfc59cd88
Revises: 6287c4b72132
Create Date: 2026-10-25 01:41:06.954648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '05adfc59cd88'
down_revision: Union[str, None] = '6287c4b72132'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_index('idx_projects_parent_id', 'projects', ['parent_id'], unique=False)
    op.create_foreign_key(
        'fk_projects_parent_id',
        'projects',
        'projects',
        ['parent_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('fk_projects_parent_id', 'projects', type_='foreignkey')
    op.drop_index('idx_projects_parent_id', table_name='projects')
    op.drop_column('projects', 'parent_id', existing_type=sa.Integer())
