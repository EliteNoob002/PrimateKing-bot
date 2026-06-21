"""005_create_settings_audit_log"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_create_settings_audit_log"
down_revision: Union[str, None] = "004_create_bot_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_settings_audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=True),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("setting_key", sa.String(length=128), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("bot_settings_audit_log", if_exists=True)
