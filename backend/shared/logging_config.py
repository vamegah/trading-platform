import logging
from backend.shared.config import settings
from backend.shared.data_lake import record_data_lake_edge
from backend.shared.observability import configure_json_logging


def setup_logging():
    configure_json_logging(settings.log_level)


def record_monitoring_event(event_name: str) -> dict[str, str]:
    logging.getLogger("monitoring").info("monitoring_event=%s", event_name)
    return record_data_lake_edge("monitoring_logging", "write", event_name)
