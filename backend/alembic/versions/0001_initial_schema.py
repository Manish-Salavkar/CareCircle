"""Initial schema for CareCircle Lite.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-25 12:10:00+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial CareCircle Lite tables, constraints, and indexes."""
    op.create_table(
        "care_recipients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_care_recipients")),
    )

    op.create_table(
        "family_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("care_recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("relationship", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["care_recipient_id"],
            ["care_recipients.id"],
            name=op.f("fk_family_members_care_recipient_id_care_recipients"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_family_members")),
    )
    op.create_index(
        op.f("ix_family_members_care_recipient_id"),
        "family_members",
        ["care_recipient_id"],
        unique=False,
    )

    op.create_table(
        "care_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("care_recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "task_type",
            sa.Enum(
                "medicine",
                "appointment",
                "check_in",
                name="task_type_enum",
                native_enum=False,
                length=32,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "done",
                name="task_status_enum",
                native_enum=False,
                length=16,
                create_constraint=True,
            ),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("completed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND completed_at IS NULL AND completed_by_id IS NULL) "
            "OR (status = 'done' AND completed_at IS NOT NULL)",
            name=op.f("ck_care_tasks_completion_consistency"),
        ),
        sa.ForeignKeyConstraint(
            ["care_recipient_id"],
            ["care_recipients.id"],
            name=op.f("fk_care_tasks_care_recipient_id_care_recipients"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_id"],
            ["family_members.id"],
            name=op.f("fk_care_tasks_completed_by_id_family_members"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_care_tasks")),
    )
    op.create_index(
        op.f("ix_care_tasks_care_recipient_id"),
        "care_tasks",
        ["care_recipient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_care_tasks_completed_by_id"),
        "care_tasks",
        ["completed_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_care_tasks_due_at"),
        "care_tasks",
        ["due_at"],
        unique=False,
    )
    op.create_index(
        "ix_care_tasks_recipient_status_due",
        "care_tasks",
        ["care_recipient_id", "status", "due_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_care_tasks_status"),
        "care_tasks",
        ["status"],
        unique=False,
    )

    op.create_table(
        "ai_interaction_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "context_sent",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "latency_ms >= 0",
            name=op.f("ck_ai_interaction_logs_latency_ms_non_negative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_interaction_logs")),
    )
    op.create_index(
        op.f("ix_ai_interaction_logs_created_at"),
        "ai_interaction_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop initial CareCircle Lite tables and indexes."""
    op.drop_index(op.f("ix_ai_interaction_logs_created_at"), table_name="ai_interaction_logs")
    op.drop_table("ai_interaction_logs")

    op.drop_index(op.f("ix_care_tasks_status"), table_name="care_tasks")
    op.drop_index("ix_care_tasks_recipient_status_due", table_name="care_tasks")
    op.drop_index(op.f("ix_care_tasks_due_at"), table_name="care_tasks")
    op.drop_index(op.f("ix_care_tasks_completed_by_id"), table_name="care_tasks")
    op.drop_index(op.f("ix_care_tasks_care_recipient_id"), table_name="care_tasks")
    op.drop_table("care_tasks")

    op.drop_index(op.f("ix_family_members_care_recipient_id"), table_name="family_members")
    op.drop_table("family_members")

    op.drop_table("care_recipients")
