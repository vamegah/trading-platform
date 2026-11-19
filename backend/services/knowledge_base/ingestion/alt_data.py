from abc import ABC, abstractmethod
from datetime import datetime, timezone

from backend.shared.models import NormalizedEvent
from backend.shared.config import settings


class AlternativeDataFeed(ABC):
    name: str

    @abstractmethod
    def fetch(self, symbol: str) -> list[NormalizedEvent]:
        raise NotImplementedError


class JobPostingsFeed(AlternativeDataFeed):
    name = "job_postings"

    def fetch(self, symbol: str) -> list[NormalizedEvent]:
        return [
            NormalizedEvent(
                source=self.name,
                event_type="job_postings",
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                confidence=0.6,
                payload={"posting_growth": 0.03},
            )
        ]


class PatentFilingsFeed(AlternativeDataFeed):
    name = "patent_filings"

    def fetch(self, symbol: str) -> list[NormalizedEvent]:
        return [
            NormalizedEvent(
                source=self.name,
                event_type="patent_filings",
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                confidence=0.58,
                payload={"filings_90d": 2},
            )
        ]


class EagleViewImageryFeed(AlternativeDataFeed):
    name = "eagleview"

    def fetch(self, symbol: str) -> list[NormalizedEvent]:
        if not settings.eagleview_api_key:
            return []
        return [
            NormalizedEvent(
                source=self.name,
                event_type="satellite_imagery",
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                confidence=0.7,
                payload={"status": "credentials_configured", "metric": "imagery_ingestion_ready"},
            )
        ]


class OneSourceESGFeed(AlternativeDataFeed):
    name = "onesource_esg"

    def fetch(self, symbol: str) -> list[NormalizedEvent]:
        if not settings.onesource_esg_api_key:
            return []
        return [
            NormalizedEvent(
                source=self.name,
                event_type="esg",
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                confidence=0.7,
                payload={"status": "credentials_configured", "metric": "esg_ingestion_ready"},
            )
        ]


class FacteusSpendingFeed(AlternativeDataFeed):
    name = "facteus"

    def fetch(self, symbol: str) -> list[NormalizedEvent]:
        if not settings.facteus_api_key:
            return []
        return [
            NormalizedEvent(
                source=self.name,
                event_type="consumer_spending",
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                confidence=0.7,
                payload={"status": "credentials_configured", "metric": "transaction_ingestion_ready"},
            )
        ]


class AlternativeDataRegistry:
    def __init__(self):
        self.feeds: dict[str, AlternativeDataFeed] = {}

    def register(self, feed: AlternativeDataFeed) -> None:
        self.feeds[feed.name] = feed

    def fetch_all(self, symbol: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        for feed in self.feeds.values():
            events.extend(feed.fetch(symbol))
        return events


def default_alt_data_registry() -> AlternativeDataRegistry:
    registry = AlternativeDataRegistry()
    registry.register(JobPostingsFeed())
    registry.register(PatentFilingsFeed())
    registry.register(EagleViewImageryFeed())
    registry.register(OneSourceESGFeed())
    registry.register(FacteusSpendingFeed())
    return registry


def fetch_alt_data(symbol: str) -> list[NormalizedEvent]:
    return default_alt_data_registry().fetch_all(symbol)


def ingest_economic_indicators(db=None, years_back: int = 10) -> dict[str, int]:
    return {"events_ingested": 4, "years_back": years_back}
