"""004_create_bot_settings"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_create_bot_settings"
down_revision: Union[str, None] = "003_create_function_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_settings",
        sa.Column("setting_key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("setting_key"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("bot_settings", if_exists=True)
