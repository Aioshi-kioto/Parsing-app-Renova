"""scheduled_operations_table

Revision ID: b77c9f1e2d34
Revises: a12b3c4d5e6f
Create Date: 2026-03-20 14:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b77c9f1e2d34"
down_revision: Union[str, Sequence[str], None] = "a12b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("run_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("channels_json", sa.JSON(), nullable=True),
        sa.Column("fixed_settings_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("cancelled_by", sa.String(), nullable=True),
        sa.Column("cancel_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_job_id", sa.Integer(), nullable=True),
        sa.Column("dispatched_table", sa.String(), nullable=True),
        sa.Column("dispatch_error", sa.String(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_scheduled_operations_status_run_at", "scheduled_operations", ["status", "run_at_utc"], unique=False)
    op.create_index("ix_scheduled_operations_type_run_at", "scheduled_operations", ["operation_type", "run_at_utc"], unique=False)
    op.create_index(op.f("ix_scheduled_operations_id"), "scheduled_operations", ["id"], unique=False)
    op.create_index(op.f("ix_scheduled_operations_operation_type"), "scheduled_operations", ["operation_type"], unique=False)
    op.create_index(op.f("ix_scheduled_operations_status"), "scheduled_operations", ["status"], unique=False)
    op.create_index(op.f("ix_scheduled_operations_run_at_utc"), "scheduled_operations", ["run_at_utc"], unique=False)
    op.create_index(op.f("ix_scheduled_operations_next_retry_at"), "scheduled_operations", ["next_retry_at"], unique=False)
    op.create_index(op.f("ix_scheduled_operations_dispatched_job_id"), "scheduled_operations", ["dispatched_job_id"], unique=False)
    op.create_index(op.f("ix_scheduled_operations_dedupe_key"), "scheduled_operations", ["dedupe_key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_operations_dedupe_key"), table_name="scheduled_operations")
    op.drop_index(op.f("ix_scheduled_operations_dispatched_job_id"), table_name="scheduled_operations")
    op.drop_index(op.f("ix_scheduled_operations_next_retry_at"), table_name="scheduled_operations")
    op.drop_index(op.f("ix_scheduled_operations_run_at_utc"), table_name="scheduled_operations")
    op.drop_index(op.f("ix_scheduled_operations_status"), table_name="scheduled_operations")
    op.drop_index(op.f("ix_scheduled_operations_operation_type"), table_name="scheduled_operations")
    op.drop_index(op.f("ix_scheduled_operations_id"), table_name="scheduled_operations")
    op.drop_index("ix_scheduled_operations_type_run_at", table_name="scheduled_operations")
    op.drop_index("ix_scheduled_operations_status_run_at", table_name="scheduled_operations")
    op.drop_table("scheduled_operations")
