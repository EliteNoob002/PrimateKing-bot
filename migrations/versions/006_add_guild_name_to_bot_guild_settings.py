"""006_add_guild_name_to_bot_guild_settings"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_add_guild_name"
down_revision: Union[str, None] = "005_create_settings_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bot_guild_settings",
        sa.Column("guild_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bot_guild_settings", "guild_name")
