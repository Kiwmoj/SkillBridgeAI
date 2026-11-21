"""Platform features: application tracking, project milestones, portfolio metadata, O*NET reference, lessons

Revision ID: 20261122_platform
Revises: 20261121_repair
Create Date: 2026-11-21 14:30:00

Additive only: new nullable/defaulted columns and new tables. No existing data is modified.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261122_platform"
down_revision: Union[str, Sequence[str], None] = "20261121_repair"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("opportunities") as batch:
        batch.add_column(sa.Column("category", sa.String(length=32), nullable=False, server_default="other"))
        batch.add_column(sa.Column("deadline", sa.Date(), nullable=True))
        batch.add_column(sa.Column("notes", sa.Text(), nullable=True))

    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("milestones", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("notes", sa.Text(), nullable=True))

    with op.batch_alter_table("portfolios") as batch:
        batch.add_column(sa.Column("title", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("tags", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("featured", sa.Boolean(), nullable=False, server_default="0"))
        batch.create_foreign_key("fk_portfolios_project_id_projects", "projects", ["project_id"], ["id"])

    op.create_table(
        "onet_elements",
        sa.Column("element_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("element_id"),
    )
    op.create_index(op.f("ix_onet_elements_name"), "onet_elements", ["name"], unique=False)
    op.create_table(
        "onet_job_zones",
        sa.Column("zone", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("experience", sa.Text(), nullable=True),
        sa.Column("education", sa.Text(), nullable=True),
        sa.Column("training", sa.Text(), nullable=True),
        sa.Column("examples", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("zone"),
    )
    op.create_table(
        "onet_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("element_id", sa.String(length=32), nullable=False),
        sa.Column("scale_id", sa.String(length=8), nullable=False),
        sa.Column("category", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("element_id", "scale_id", "category"),
    )
    op.create_index(op.f("ix_onet_categories_element_id"), "onet_categories", ["element_id"], unique=False)
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("element_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "element_id"),
    )
    op.create_index(op.f("ix_lesson_progress_user_id"), "lesson_progress", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_lesson_progress_user_id"), table_name="lesson_progress")
    op.drop_table("lesson_progress")
    op.drop_index(op.f("ix_onet_categories_element_id"), table_name="onet_categories")
    op.drop_table("onet_categories")
    op.drop_table("onet_job_zones")
    op.drop_index(op.f("ix_onet_elements_name"), table_name="onet_elements")
    op.drop_table("onet_elements")
    with op.batch_alter_table("portfolios") as batch:
        batch.drop_constraint("fk_portfolios_project_id_projects", type_="foreignkey")
        for column in ("featured", "project_id", "tags", "description", "title"):
            batch.drop_column(column)
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("notes")
        batch.drop_column("milestones")
    with op.batch_alter_table("opportunities") as batch:
        batch.drop_column("notes")
        batch.drop_column("deadline")
        batch.drop_column("category")
