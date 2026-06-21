"""003_create_function_settings"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_create_function_settings"
down_revision: Union[str, None] = "002_create_command_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_function_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=True),
        sa.Column("function_name", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guild_id", "function_name", name="uq_bot_function_settings"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("bot_function_settings", if_exists=True)
