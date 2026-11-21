"""Skill level on the user profile

Revision ID: 20261123_skill_level
Revises: 20261122_platform
Create Date: 2026-11-21 15:20:00

Additive only: one nullable column. NULL means the user has not chosen a level yet.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261123_skill_level"
down_revision: Union[str, Sequence[str], None] = "20261122_platform"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("profiles") as batch:
        batch.add_column(sa.Column("skill_level", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("profiles") as batch:
        batch.drop_column("skill_level")
