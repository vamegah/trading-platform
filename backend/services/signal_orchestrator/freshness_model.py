from datetime import datetime, timezone
from math import exp, log

from backend.shared.config import settings


def signal_freshness_score(
    generated_at: datetime,
    now: datetime | None = None,
    half_life_minutes: float | None = None,
) -> float:
    reference = now or datetime.now(timezone.utc)
    generated = generated_at
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    half_life = max(half_life_minutes or settings.signal_half_life_minutes, 1.0)
    age_minutes = max((reference - generated).total_seconds() / 60, 0.0)
    return round(exp(-log(2) * age_minutes / half_life), 4)


def should_auto_cancel_signal(generated_at: datetime, now: datetime | None = None) -> bool:
    return signal_freshness_score(generated_at, now) < settings.signal_auto_cancel_threshold
