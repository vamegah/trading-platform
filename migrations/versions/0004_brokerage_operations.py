"""brokerage operations and client experience expansion

Revision ID: 0004_brokerage_operations
Revises: 0003_professional_workstation
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

from backend.shared import models

revision = "0004_brokerage_operations"
down_revision = "0003_professional_workstation"
branch_labels = None
depends_on = None


M13_MODEL_NAMES = (
    "FundingAccountModel",
    "CashTransferModel",
    "CashLedgerEntryModel",
    "SettlementLotModel",
    "ChartTradingLayoutModel",
    "CorporateActionModel",
    "AccountDocumentModel",
    "AdminReviewModel",
    "SurveillanceAlertModel",
    "MarketDataEntitlementModel",
    "DataUsageMeterModel",
    "RecurringInvestmentPlanModel",
    "ConditionalOrderModel",
    "PortfolioReviewPackModel",
    "MobileDeviceModel",
    "SupportCaseModel",
    "AuditRequestModel",
)


def _m13_tables():
    return [getattr(models, model_name).__table__ for model_name in M13_MODEL_NAMES]


def upgrade() -> None:
    bind = op.get_bind()
    models.Base.metadata.create_all(bind=bind, tables=_m13_tables(), checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    for table in reversed(_m13_tables()):
        if table.name in existing_tables:
            table.drop(bind=bind, checkfirst=True)
