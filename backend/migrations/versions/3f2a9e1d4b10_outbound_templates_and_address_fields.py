"""outbound_templates_and_address_fields

Revision ID: 3f2a9e1d4b10
Revises: 08073a365dc9
Create Date: 2026-03-20 10:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f2a9e1d4b10"
down_revision: Union[str, Sequence[str], None] = "08073a365dc9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("owner_mailing_city", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("owner_mailing_state", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("owner_mailing_zip", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("state", sa.String(), nullable=True))

    op.add_column("outbound_log", sa.Column("external_id", sa.String(), nullable=True))

    op.create_table(
        "outbound_templates",
        sa.Column("case_type", sa.String(), nullable=False),
        sa.Column("email_subject", sa.String(), nullable=False),
        sa.Column("email_body", sa.String(), nullable=False),
        sa.Column("lob_template_id", sa.String(), nullable=True),
        sa.Column("lob_body_html", sa.String(), nullable=True),
        sa.Column("sms_body", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("case_type"),
    )
    op.create_index(op.f("ix_outbound_templates_case_type"), "outbound_templates", ["case_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_outbound_templates_case_type"), table_name="outbound_templates")
    op.drop_table("outbound_templates")

    op.drop_column("outbound_log", "external_id")

    op.drop_column("leads", "state")
    op.drop_column("leads", "owner_mailing_zip")
    op.drop_column("leads", "owner_mailing_state")
    op.drop_column("leads", "owner_mailing_city")
