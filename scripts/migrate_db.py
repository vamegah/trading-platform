import sys
from pathlib import Path

from alembic.config import Config
from alembic import command

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.shared.config import settings  # noqa: E402


def preflight() -> None:
    settings.validate_runtime()
    if settings.is_production and settings.create_tables_on_startup:
        raise RuntimeError("Refusing to run production migrations with CREATE_TABLES_ON_STARTUP enabled")


def upgrade() -> None:
    preflight()
    config = Config("alembic.ini")
    command.upgrade(config, "head")


if __name__ == "__main__":
    upgrade()
