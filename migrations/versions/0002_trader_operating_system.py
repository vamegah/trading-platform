"""trader operating system expansion

Revision ID: 0002_trader_operating_system
Revises: 0001_initial_production_schema
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

from backend.shared import models

revision = "0002_trader_operating_system"
down_revision = "0001_initial_production_schema"
branch_labels = None
depends_on = None


M11_MODEL_NAMES = (
    "BrokerAccountModel",
    "MarginSnapshotModel",
    "OptionContractModel",
    "CatalystEventModel",
    "WatchlistModel",
    "TradeJournalEntryV2Model",
    "DisclosureAttestationModel",
    "BrokerReconciliationRecordModel",
)


def _m11_tables():
    return [getattr(models, model_name).__table__ for model_name in M11_MODEL_NAMES]


def upgrade() -> None:
    bind = op.get_bind()
    models.Base.metadata.create_all(bind=bind, tables=_m11_tables(), checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    for table in reversed(_m11_tables()):
        if table.name in existing_tables:
            table.drop(bind=bind, checkfirst=True)
