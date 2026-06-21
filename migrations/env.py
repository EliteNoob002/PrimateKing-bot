from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import models  # noqa: F401
from utils.bootstrap_settings import load_bootstrap_settings
from utils.database import Base

# Отдельно от web-панели: одна MySQL, разные цепочки миграций
BOT_VERSION_TABLE = "alembic_version_bot"

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _configure_context(**kwargs):
    return context.configure(
        target_metadata=target_metadata,
        version_table=BOT_VERSION_TABLE,
        **kwargs,
    )


def run_migrations_offline() -> None:
    url = load_bootstrap_settings().database_url
    _configure_context(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # DATABASE_URL из .env напрямую — ConfigParser Alembic ломается на % в пароле
    connectable = create_engine(
        load_bootstrap_settings().database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _configure_context(connection=connection)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
