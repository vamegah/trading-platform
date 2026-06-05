from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_upgrades_and_downgrades_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "migration-test.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(config, "head")
    inspector = inspect(create_engine(f"sqlite:///{database_path}"))
    tables = set(inspector.get_table_names())

    assert "audit_logs" in tables
    assert "secret_records" in tables
    assert "privacy_records" in tables
    assert "paper_trades" in tables

    command.downgrade(config, "base")
    inspector = inspect(create_engine(f"sqlite:///{database_path}"))

    assert set(inspector.get_table_names()).issubset({"alembic_version"})
