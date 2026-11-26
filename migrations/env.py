from logging.config import fileConfig

from alembic import context

from backend.shared.config import settings
from backend.shared.database import Base, resolve_database_url
from backend.shared import models  # noqa: F401

config = context.config
configured_url = config.get_main_option("sqlalchemy.url")
if not configured_url or configured_url == "driver://user:pass@localhost/dbname":
    configured_url = settings.database_url
# configparser treats "%" as interpolation, so escape it (passwords may be URL-encoded).
config.set_main_option("sqlalchemy.url", resolve_database_url(configured_url).replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    connectable = create_engine(config.get_main_option("sqlalchemy.url"))
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
