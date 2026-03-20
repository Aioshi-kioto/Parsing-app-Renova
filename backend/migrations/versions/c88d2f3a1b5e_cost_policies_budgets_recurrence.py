"""cost policies budgets recurrence

Revision ID: c88d2f3a1b5e
Revises: b77c9f1e2d34
Create Date: 2026-03-20 05:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "c88d2f3a1b5e"
down_revision = "b77c9f1e2d34"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("scheduled_operations", sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("scheduled_operations", sa.Column("recurrence_interval_days", sa.Integer(), nullable=True))
    op.add_column("scheduled_operations", sa.Column("next_run_at_utc", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_scheduled_operations_next_run", "scheduled_operations", ["next_run_at_utc"])

    op.create_table(
        "provider_cost_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False, index=True),
        sa.Column("pricing_mode", sa.String(), nullable=False, server_default="per_event"),
        sa.Column("unit_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unit_name", sa.String(), nullable=False, server_default="event"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "provider_budgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("period", sa.String(), nullable=False, server_default="monthly"),
        sa.Column("budget_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("warning_pct", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("hard_limit_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.execute("""
        INSERT INTO provider_cost_policies (provider, pricing_mode, unit_cost_usd, unit_name, is_active) VALUES
        ('batchdata', 'per_event', 0.07, 'match', true),
        ('lob',       'per_event', 0.806, 'letter', true),
        ('sendgrid',  'flat',      0.00,  'email',  true),
        ('decodo',    'per_gb',    8.50,  'gb',     true),
        ('sms_beta',  'per_event', 0.0079,'segment',false)
    """)

    op.execute("""
        INSERT INTO provider_budgets (provider, period, budget_usd, warning_pct, hard_limit_enabled) VALUES
        ('batchdata', 'monthly', 50.0,  80, false),
        ('lob',       'monthly', 100.0, 80, false),
        ('sendgrid',  'monthly', 0.0,   80, false),
        ('decodo',    'monthly', 30.0,  80, false),
        ('sms_beta',  'monthly', 0.0,   80, false)
    """)


def downgrade():
    op.drop_table("provider_budgets")
    op.drop_table("provider_cost_policies")
    op.drop_index("ix_scheduled_operations_next_run", table_name="scheduled_operations")
    op.drop_column("scheduled_operations", "next_run_at_utc")
    op.drop_column("scheduled_operations", "recurrence_interval_days")
    op.drop_column("scheduled_operations", "is_recurring")
