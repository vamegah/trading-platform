from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.data_pipeline.cleaning.data_quality import quality_gate_or_raise
from backend.data_pipeline.ingestion.alt_data import fetch_alt_data
from backend.data_pipeline.ingestion.market_data import fetch_market_data
from backend.data_pipeline.ingestion.news import (
    fetch_economic_calendar,
    fetch_insider_transactions,
    fetch_news,
    fetch_social_sentiment,
)
from backend.data_pipeline.lake.processed_store import write_processed_dataset
from backend.data_pipeline.lake.raw_store import write_raw_dataset


@dataclass
class IngestionJobResult:
    job_id: str
    status: str
    attempts: int
    rows_written: int = 0
    errors: list[str] = field(default_factory=list)
    dead_lettered: bool = False
    started_at: str | None = None
    finished_at: str | None = None
    metrics: dict[str, int] = field(default_factory=dict)


class IngestionScheduler:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.completed_jobs: set[str] = set()
        self.dead_letters: list[dict] = []
        self.metrics = {
            "jobs_started": 0,
            "jobs_completed": 0,
            "jobs_skipped_duplicate": 0,
            "jobs_failed": 0,
            "attempts_total": 0,
            "retry_failures": 0,
            "dead_letters_total": 0,
            "rows_written_total": 0,
        }

    def run_once(self, job_id: str, symbols: list[str]) -> IngestionJobResult:
        if job_id in self.completed_jobs:
            self.metrics["jobs_skipped_duplicate"] += 1
            return IngestionJobResult(
                job_id=job_id,
                status="skipped_duplicate",
                attempts=0,
                metrics=dict(self.metrics),
            )

        started_at = datetime.now(timezone.utc).isoformat()
        self.metrics["jobs_started"] += 1
        errors: list[str] = []
        for attempt in range(1, self.max_retries + 1):
            self.metrics["attempts_total"] += 1
            try:
                if any(symbol.upper() == "FAIL" for symbol in symbols):
                    raise RuntimeError("deterministic ingestion failure")
                rows = fetch_market_data(symbols)
                events = []
                for symbol in symbols:
                    events.extend(event.model_dump() for event in fetch_news(symbol))
                    events.extend(event.model_dump() for event in fetch_social_sentiment(symbol))
                    events.extend(event.model_dump() for event in fetch_insider_transactions(symbol))
                    events.extend(event.model_dump() for event in fetch_economic_calendar(symbol))
                    events.extend(event.model_dump() for event in fetch_alt_data(symbol))
                quality = quality_gate_or_raise(rows)
                market_write = write_raw_dataset("market_data_daily", rows, source="provider_failover")
                processed_write = write_processed_dataset(
                    "market_data_daily_normalized",
                    rows,
                    version=str(market_write["version"]),
                    source=str(market_write["manifest"]["dataset_id"]),
                )
                event_write = write_raw_dataset("events_daily", events, source="event_connectors")
                self.completed_jobs.add(job_id)
                rows_written = (
                    int(market_write["rows_written"])
                    + int(processed_write["rows_processed"])
                    + int(event_write["rows_written"])
                )
                self.metrics["jobs_completed"] += 1
                self.metrics["rows_written_total"] += rows_written
                return IngestionJobResult(
                    job_id=job_id,
                    status="completed",
                    attempts=attempt,
                    rows_written=rows_written,
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    metrics={**self.metrics, "quality_blocked": int(bool(quality["blocked"]))},
                )
            except Exception as exc:
                errors.append(str(exc))
                self.metrics["retry_failures"] += 1

        dead_letter = {
            "job_id": job_id,
            "symbols": symbols,
            "errors": errors,
            "attempts": self.max_retries,
            "dead_lettered_at": datetime.now(timezone.utc).isoformat(),
        }
        self.dead_letters.append(dead_letter)
        self.metrics["jobs_failed"] += 1
        self.metrics["dead_letters_total"] += 1
        return IngestionJobResult(
            job_id=job_id,
            status="failed",
            attempts=self.max_retries,
            errors=errors,
            dead_lettered=True,
            started_at=started_at,
            finished_at=dead_letter["dead_lettered_at"],
            metrics=dict(self.metrics),
        )


def run_daily_sync(symbols: list[str]) -> dict[str, object]:
    scheduler = IngestionScheduler()
    result = scheduler.run_once(f"daily:{datetime.now(timezone.utc).date().isoformat()}:{','.join(symbols)}", symbols)
    return result.__dict__


def run_intraday_sync(symbols: list[str], window: str = "15m") -> dict[str, object]:
    scheduler = IngestionScheduler()
    timestamp = datetime.now(timezone.utc).replace(second=0, microsecond=0).isoformat()
    result = scheduler.run_once(f"intraday:{window}:{timestamp}:{','.join(symbols)}", symbols)
    return {**result.__dict__, "window": window}


if __name__ == "__main__":
    print(run_daily_sync(["AAPL", "MSFT", "NVDA"]))
