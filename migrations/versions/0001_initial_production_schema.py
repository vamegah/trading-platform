"""initial production schema

Revision ID: 0001_initial_production_schema
Revises:
Create Date: 2026-05-15
"""

from alembic import op

from backend.shared.database import Base
from backend.shared import models  # noqa: F401

revision = "0001_initial_production_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
