"""002_create_command_settings"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_create_command_settings"
down_revision: Union[str, None] = "001_create_guild_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_command_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=True),
        sa.Column("command_name", sa.String(length=128), nullable=False),
        sa.Column("command_type", sa.String(length=32), nullable=False, server_default="slash"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guild_id", "command_name", "command_type", name="uq_bot_command_settings"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("bot_command_settings", if_exists=True)
