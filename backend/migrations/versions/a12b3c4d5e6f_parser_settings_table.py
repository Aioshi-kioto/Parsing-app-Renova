"""parser_settings_table

Revision ID: a12b3c4d5e6f
Revises: 3f2a9e1d4b10
Create Date: 2026-03-20 13:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a12b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "3f2a9e1d4b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parser_settings",
        sa.Column("parser_type", sa.String(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("channels_json", sa.JSON(), nullable=True),
        sa.Column("fixed_settings_json", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("parser_type"),
    )


def downgrade() -> None:
    op.drop_table("parser_settings")
