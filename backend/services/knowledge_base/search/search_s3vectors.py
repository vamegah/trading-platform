"""
Lambda: search the S3 Vectors financial-research index.

Contract:
    Input (body):
      {
        "query": "NVDA guidance cut",       # required
        "k": 8,                             # optional, default 8, max 50
        "filters": {                        # optional metadata filters
          "ticker": "NVDA",
          "event_type": "earnings_guidance_change",
          "magnitude": ["HIGH", "EXTREME"],
          "direction": "BEARISH",
          "since": "2025-01-14T00:00:00Z",  # ISO-8601
          "until": "2025-01-15T23:59:59Z",
          "dedupe_key": "abc123...",
          "window": "24h"
        },
        "rank_by": "hybrid",                # relevance | recency | hybrid
        "dedupe_chunks": true,              # merge chunks of same brief
        "max_chars_per_hit": 1200           # truncation guard
      }

    Output:
      {
        "status": "ok" | "error",
        "count": int,
        "results": [
          {
            "id": str,
            "distance": float,
            "similarity": float,            # normalized 0..1
            "text": str,
            "excerpt": str,                 # short highlight
            "truncated": bool,
            "metadata": {...},
            "source_url": str | null,
            "published_at": str | null,
            "dedupe_key": str | null,
            "chunk_index": int | null,
            "chunk_count": int | null
          }
        ],
        "deduped_groups": int,              # if dedupe_chunks=true
        "retryable": bool,
        "message": str
      }

Design notes:
- Prefer native metadata filtering in query_vectors when supported; falls
  back to over-fetch + local filter otherwise.
- Dedupe chunks of the same brief so the agent sees one story, not N.
- Normalize distance → similarity so downstream ranking is model-agnostic.
- Recency boost keeps stale-but-relevant items from outranking fresh ones.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

VECTOR_BUCKET = os.environ.get("VECTOR_BUCKET", "alex-vectors")
SAGEMAKER_ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT", "")
INDEX_NAME = os.environ.get("INDEX_NAME", "financial-research")

DEFAULT_K = int(os.environ.get("SEARCH_DEFAULT_K", "8"))
MAX_K = int(os.environ.get("SEARCH_MAX_K", "50"))
OVERFETCH_FACTOR = int(os.environ.get("SEARCH_OVERFETCH_FACTOR", "4"))
MAX_QUERY_CHARS = int(os.environ.get("SEARCH_MAX_QUERY_CHARS", "1000"))
MAX_CHARS_PER_HIT = int(os.environ.get("SEARCH_MAX_CHARS_PER_HIT", "1500"))
MAX_RETRIES = int(os.environ.get("SEARCH_MAX_RETRIES", "3"))
BACKOFF_BASE = float(os.environ.get("SEARCH_BACKOFF_BASE", "0.5"))

# Recency half-life for hybrid ranking (hours)
RECENCY_HALF_LIFE_HOURS = float(os.environ.get("SEARCH_RECENCY_HALF_LIFE_HOURS", "48"))


# ---------------------------------------------------------------------------
# LOGGING (structured)
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _log(level: str, event: str, **fields: Any) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        **{k: v for k, v in fields.items() if v is not None},
    }
    getattr(logger, level.lower(), logger.info)(json.dumps(record, default=str))


# ---------------------------------------------------------------------------
# AWS CLIENTS
# ---------------------------------------------------------------------------

_boto_cfg = Config(
    retries={"max_attempts": 5, "mode": "standard"},
    connect_timeout=5,
    read_timeout=30,
)

sagemaker_runtime = boto3.client("sagemaker-runtime", config=_boto_cfg)
s3_vectors = boto3.client("s3vectors", config=_boto_cfg)


# ---------------------------------------------------------------------------
# EMBEDDING
# ---------------------------------------------------------------------------

def get_embedding(text: str) -> list[float]:
    """
    Fetch an embedding, handling common HF/TEI nesting shapes:
      - [float, ...]
      - [[float, ...]]
      - [[[float, ...]]]
    """
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=json.dumps({"inputs": text}),
    )
    raw = response["Body"].read().decode("utf-8")
    result = json.loads(raw)

    if isinstance(result, list) and result:
        if isinstance(result[0], list) and result[0]:
            if isinstance(result[0][0], list):
                return result[0][0]
            return result[0]
    if not isinstance(result, list) or not all(
        isinstance(x, (int, float)) for x in result
    ):
        raise ValueError(f"Unexpected embedding response shape: {type(result)}")
    return result


# ---------------------------------------------------------------------------
# RETRY
# ---------------------------------------------------------------------------

_RETRYABLE_CODES = {
    "ThrottlingException",
    "ServiceUnavailable",
    "InternalServerError",
    "ModelNotReadyException",
    "RequestTimeout",
    "TooManyRequestsException",
}


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        return code in _RETRYABLE_CODES or status in {429, 500, 502, 503, 504}
    return isinstance(exc, (ConnectionError, TimeoutError))


def _call_with_retries(fn, *args, **kwargs):
    last: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES:
                raise
            sleep_s = BACKOFF_BASE * (2 ** (attempt - 1))
            _log("warning", "retry", attempt=attempt, sleep_s=sleep_s, error=str(exc))
            time.sleep(sleep_s)
    assert last is not None
    raise last


# ---------------------------------------------------------------------------
# INPUT PARSING
# ---------------------------------------------------------------------------

def _parse_event(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body", event)
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON body: {exc}") from exc
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")
    return body


def _normalize_filters(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce filter values into the shape our matcher expects."""
    out: dict[str, Any] = {}
    for k, v in (raw or {}).items():
        if v is None:
            continue
        if k in {"since", "until"}:
            out[k] = str(v)
        elif k in {"magnitude", "event_type", "direction", "ticker", "window"}:
            out[k] = v if isinstance(v, list) else [v]
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# LOCAL FILTER (fallback / post-filter)
# ---------------------------------------------------------------------------

def _matches(meta: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, wanted in filters.items():
        if key == "since":
            ts = meta.get("timestamp") or meta.get("published_at")
            if not ts or str(ts) < str(wanted):
                return False
            continue
        if key == "until":
            ts = meta.get("timestamp") or meta.get("published_at")
            if not ts or str(ts) > str(wanted):
                return False
            continue

        actual = meta.get(key)
        wanted_list = wanted if isinstance(wanted, list) else [wanted]
        if actual is None:
            return False
        if isinstance(actual, list):
            if not any(str(a) in [str(w) for w in wanted_list] for a in actual):
                return False
        else:
            if str(actual) not in [str(w) for w in wanted_list]:
                return False
    return True


def _build_backend_filter(filters: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Translate our filter dict into the S3 Vectors filter syntax when possible.
    Returns None if backend filtering isn't supported for this combo.
    """
    if not filters:
        return None

    clauses: list[dict[str, Any]] = []
    for key, val in filters.items():
        if key in {"since", "until"}:
            continue  # date range filter shape varies; post-filter locally
        if isinstance(val, list):
            clauses.append({key: {"in": val}})
        else:
            clauses.append({key: {"equals": val}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"and": clauses}


# ---------------------------------------------------------------------------
# SCORING & RANKING
# ---------------------------------------------------------------------------

def _normalize_similarity(distance: Optional[float]) -> float:
    """
    Convert an arbitrary distance to a monotone similarity in [0, 1].
    Uses 1/(1+d) which is well-behaved for cosine/L2 distances in typical
    embedding spaces (small d → ~1, large d → ~0).
    """
    if distance is None:
        return 0.0
    try:
        d = max(0.0, float(distance))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 / (1.0 + d)


def _recency_weight(ts: Optional[str], half_life_hours: float) -> float:
    """Exponential decay on age; returns 1.0 for now, 0.5 at half-life, etc."""
    if not ts:
        return 0.5
    try:
        # Accept common ISO-8601 variants
        ts_clean = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.5
    age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    if age_hours < 0:
        return 1.0
    return math.exp(-math.log(2) * age_hours / max(half_life_hours, 0.01))


def _hybrid_score(similarity: float, recency: float) -> float:
    """Weighted blend — similarity dominates, recency breaks ties."""
    return 0.75 * similarity + 0.25 * recency


# ---------------------------------------------------------------------------
# EXCERPT
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"\w+")


def _make_excerpt(text: str, query: str, max_chars: int = 240) -> str:
    """Return a short window around the first query-term hit."""
    if not text:
        return ""
    terms = {t.lower() for t in _WORD_RE.findall(query) if len(t) > 2}
    lower = text.lower()
    pos = -1
    for t in terms:
        pos = lower.find(t)
        if pos != -1:
            break
    if pos == -1:
        return text[:max_chars].strip()
    start = max(0, pos - max_chars // 2)
    end = min(len(text), start + max_chars)
    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt = excerpt + "…"
    return excerpt


# ---------------------------------------------------------------------------
# DEDUPE CHUNKS
# ---------------------------------------------------------------------------

def _dedupe_by_brief(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Merge chunks of the same brief. Keeps the highest-scoring chunk per
    dedupe_key, aggregates chunk indices, and records the group size.
    """
    groups: dict[str, dict[str, Any]] = {}
    no_key: list[dict[str, Any]] = []

    for h in hits:
        key = h.get("dedupe_key")
        if not key:
            no_key.append(h)
            continue
        existing = groups.get(key)
        if existing is None or h["_score"] > existing["_score"]:
            if existing is not None:
                # Preserve aggregated chunk indices
                h["chunk_indices"] = sorted(
                    set(existing.get("chunk_indices", []))
                    | {h.get("chunk_index")}
                )
            else:
                h["chunk_indices"] = [h.get("chunk_index")]
            groups[key] = h
        else:
            existing.setdefault("chunk_indices", []).append(h.get("chunk_index"))
            existing["chunk_indices"] = sorted(
                {i for i in existing["chunk_indices"] if i is not None}
            )

    merged = list(groups.values()) + no_key
    for h in merged:
        ci = [i for i in h.get("chunk_indices", []) if i is not None]
        h["chunk_indices"] = ci
        h["chunk_count_in_group"] = len(ci) or 1
    return merged


# ---------------------------------------------------------------------------
# HANDLER
# ---------------------------------------------------------------------------

def _response(
    status_code: int,
    status: str,
    *,
    results: Optional[list[dict[str, Any]]] = None,
    deduped_groups: int = 0,
    retryable: bool = False,
    message: str = "",
) -> dict[str, Any]:
    results = results or []
    return {
        "statusCode": status_code,
        "body": json.dumps(
            {
                "status": status,
                "count": len(results),
                "results": results,
                "deduped_groups": deduped_groups,
                "retryable": retryable,
                "message": message,
            },
            default=str,
        ),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", "local")
    started = time.monotonic()

    # ---- Parse & validate input ----
    try:
        body = _parse_event(event)
    except ValueError as exc:
        return _response(400, "error", message=str(exc))

    query = (body.get("query") or "").strip()
    if not query:
        return _response(400, "error", message="Missing required field: query")
    if len(query) > MAX_QUERY_CHARS:
        query = query[:MAX_QUERY_CHARS]

    try:
        k = int(body.get("k", DEFAULT_K))
    except (TypeError, ValueError):
        k = DEFAULT_K
    k = max(1, min(k, MAX_K))

    filters = _normalize_filters(body.get("filters") or {})
    rank_by = (body.get("rank_by") or "hybrid").lower()
    if rank_by not in {"relevance", "recency", "hybrid"}:
        rank_by = "hybrid"
    dedupe_chunks = bool(body.get("dedupe_chunks", True))
    max_chars_per_hit = int(body.get("max_chars_per_hit", MAX_CHARS_PER_HIT))

    if not SAGEMAKER_ENDPOINT:
        return _response(
            500,
            "error",
            message="SAGEMAKER_ENDPOINT not configured",
            retryable=False,
        )

    # ---- Embed the query ----
    try:
        query_embedding = _call_with_retries(get_embedding, query)
    except Exception as exc:  # noqa: BLE001
        _log("error", "embedding_failed", request_id=request_id, error=str(exc))
        return _response(
            500,
            "error",
            retryable=_is_retryable(exc),
            message=f"Embedding failed: {exc}",
        )

    # ---- Query ----
    # Over-fetch when we have local filters to apply or chunks to dedupe.
    fetch_k = k
    if filters or dedupe_chunks:
        fetch_k = min(MAX_K * OVERFETCH_FACTOR, k * OVERFETCH_FACTOR)

    kwargs: dict[str, Any] = {
        "vectorBucketName": VECTOR_BUCKET,
        "indexName": INDEX_NAME,
        "queryVector": {"float32": query_embedding},
        "topK": fetch_k,
        "returnDistance": True,
        "returnMetadata": True,
    }
    backend_filter = _build_backend_filter(filters)
    if backend_filter:
        kwargs["filter"] = backend_filter

    try:
        response = _call_with_retries(s3_vectors.query_vectors, **kwargs)
    except ClientError as exc:
        # Some backends reject the `filter` kwarg; retry without it.
        code = exc.response.get("Error", {}).get("Code", "")
        if "filter" in kwargs and code in {"ValidationException", "InvalidParameter"}:
            _log("warning", "backend_filter_unsupported_fallback", error=str(exc))
            kwargs.pop("filter", None)
            try:
                response = _call_with_retries(s3_vectors.query_vectors, **kwargs)
            except Exception as inner:  # noqa: BLE001
                _log("error", "query_failed", request_id=request_id, error=str(inner))
                return _response(
                    500,
                    "error",
                    retryable=_is_retryable(inner),
                    message=f"Query failed: {inner}",
                )
        else:
            _log("error", "query_failed", request_id=request_id, error=str(exc))
            return _response(
                500,
                "error",
                retryable=_is_retryable(exc),
                message=f"Query failed: {exc}",
            )

    raw_vectors = response.get("vectors", []) or []

    # ---- Shape + filter + score ----
    hits: list[dict[str, Any]] = []
    for v in raw_vectors:
        meta = v.get("metadata") or {}
        if filters and not _matches(meta, filters):
            continue
        distance = v.get("distance")
        similarity = _normalize_similarity(distance)
        recency = _recency_weight(
            meta.get("timestamp") or meta.get("published_at"),
            RECENCY_HALF_LIFE_HOURS,
        )
        if rank_by == "relevance":
            score = similarity
        elif rank_by == "recency":
            score = recency
        else:
            score = _hybrid_score(similarity, recency)

        text = meta.get("text", "") or ""
        truncated = len(text) > max_chars_per_hit
        text_out = text[:max_chars_per_hit] if truncated else text

        hits.append(
            {
                "id": v.get("key"),
                "distance": distance,
                "similarity": round(similarity, 6),
                "recency": round(recency, 6),
                "text": text_out,
                "excerpt": _make_excerpt(text, query),
                "truncated": truncated,
                "metadata": meta,
                "source_url": meta.get("source_url") or meta.get("url"),
                "published_at": meta.get("published_at") or meta.get("timestamp"),
                "dedupe_key": meta.get("dedupe_key"),
                "chunk_index": meta.get("chunk_index"),
                "chunk_count": meta.get("chunk_count"),
                "ticker": meta.get("ticker"),
                "topic": meta.get("topic"),
                "event_type": meta.get("event_type"),
                "direction": meta.get("direction"),
                "magnitude": meta.get("magnitude"),
                "_score": score,
            }
        )

    hits.sort(key=lambda h: h["_score"], reverse=True)

    groups_before = len(hits)
    if dedupe_chunks:
        hits = _dedupe_by_brief(hits)
        hits.sort(key=lambda h: h["_score"], reverse=True)
    deduped_groups = groups_before - len(hits) if dedupe_chunks else 0

    hits = hits[:k]

    # Strip internal scoring fields
    for h in hits:
        h.pop("_score", None)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    _log(
        "info",
        "search_done",
        request_id=request_id,
        query_len=len(query),
        fetch_k=fetch_k,
        returned=len(hits),
        deduped_groups=deduped_groups,
        elapsed_ms=elapsed_ms,
        rank_by=rank_by,
        filtered=bool(filters),
    )

    return _response(
        200,
        "ok",
        results=hits,
        deduped_groups=deduped_groups,
        message=f"Returned {len(hits)} result(s).",
    )