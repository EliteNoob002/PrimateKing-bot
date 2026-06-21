"""001_create_guild_settings"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_create_guild_settings"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_guild_settings",
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("prefix", sa.String(length=10), nullable=False, server_default="$"),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="ru"),
        sa.Column("status_rotation_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status_rotation_interval", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("log_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("guild_id"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("bot_guild_settings", if_exists=True)
