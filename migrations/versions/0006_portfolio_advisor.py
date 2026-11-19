"""persisted portfolio advisor jobs

Revision ID: 0006_portfolio_advisor
Revises: 0005_one_stop_platform
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa

from backend.shared import models

revision = "0006_portfolio_advisor"
down_revision = "0005_one_stop_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    models.PortfolioAdvisorJobModel.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    models.PortfolioAdvisorJobModel.__table__.drop(bind=op.get_bind(), checkfirst=True)