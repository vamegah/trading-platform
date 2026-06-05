"""one stop trading platform expansion

Revision ID: 0005_one_stop_platform
Revises: 0004_brokerage_operations
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

from backend.shared import models

revision = "0005_one_stop_platform"
down_revision = "0004_brokerage_operations"
branch_labels = None
depends_on = None


M14_MODEL_NAMES = (
    "TerminalQuoteModel",
    "LevelIIBookModel",
    "TimeAndSalesPrintModel",
    "OptionFlowEventModel",
    "ResearchSnapshotModel",
    "BrokerConnectionModel",
    "ACATSTransferModel",
    "AccountTypeRuleModel",
    "PortfolioAnalyticsSnapshotModel",
    "AlertRuleModel",
    "AutomationPolicyModel",
    "StrategyMarketplaceListingModel",
    "DocumentAISummaryModel",
    "CoachingPlanModel",
    "CollaborationSpaceModel",
    "FeeYieldRecordModel",
    "TrustSecurityEventModel",
    "NotificationPolicyModel",
    "NotificationDeliveryLogModel",
)


def _m14_tables():
    return [getattr(models, model_name).__table__ for model_name in M14_MODEL_NAMES]


def upgrade() -> None:
    bind = op.get_bind()
    models.Base.metadata.create_all(bind=bind, tables=_m14_tables(), checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    for table in reversed(_m14_tables()):
        if table.name in existing_tables:
            table.drop(bind=bind, checkfirst=True)
