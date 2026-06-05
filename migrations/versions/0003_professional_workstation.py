"""professional trading workstation expansion

Revision ID: 0003_professional_workstation
Revises: 0002_trader_operating_system
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

from backend.shared import models

revision = "0003_professional_workstation"
down_revision = "0002_trader_operating_system"
branch_labels = None
depends_on = None


M12_MODEL_NAMES = (
    "BasketTradeModel",
    "PreTradeCheckModel",
    "TaxLotDecisionModel",
    "BorrowLocateModel",
    "PortfolioConstructionModel",
    "MarketDepthSnapshotModel",
    "StagedOrderModel",
    "DataQualityScoreModel",
    "StrategyDefinitionModel",
    "RiskConstitutionRuleModel",
    "CommunicationArchiveRecordModel",
    "EmergencyActionModel",
)


def _m12_tables():
    return [getattr(models, model_name).__table__ for model_name in M12_MODEL_NAMES]


def upgrade() -> None:
    bind = op.get_bind()
    models.Base.metadata.create_all(bind=bind, tables=_m12_tables(), checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    for table in reversed(_m12_tables()):
        if table.name in existing_tables:
            table.drop(bind=bind, checkfirst=True)
