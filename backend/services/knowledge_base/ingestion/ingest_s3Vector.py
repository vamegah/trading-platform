"""
Lambda: ingest financial research text into S3 Vectors with SageMaker embeddings.

Contract (matches tools.py):
    Input (body):
      {
        "text": "full text to embed",
        "metadata": {
          "topic": str,
          "timestamp": ISO-8601,
          "dedupe_key": str,           # optional, enables idempotency
          "universe": [str],           # optional
          "top_signal": {...} | null,  # optional
          "item_count": int,           # optional
          "window": str,               # optional
          "format": "raw_text" | ...   # optional
        }
      }

    Output:
      {
        "status": "ok" | "duplicate" | "error",
        "document_id": str | null,
        "dedupe_key": str | null,
        "chunks_written": int,
        "retryable": bool,
        "message": str
      }

Design notes:
- Dedupe short-circuit via metadata filter BEFORE embedding (saves cost/latency).
- Deterministic vector IDs (uuid5 over dedupe_key) so re-runs overwrite.
- Chunk long briefs on structural boundaries, not char offsets.
- Retry on SageMaker cold-start and S3 Vectors throttling.
- Structured JSON logging for CloudWatch Logs Insights.
- Metadata size-guarded per S3 Vectors limits.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
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

# Limits & tuning
MAX_EMBED_CHARS = int(os.environ.get("MAX_EMBED_CHARS", "8000"))
MAX_CHUNKS_PER_DOC = int(os.environ.get("MAX_CHUNKS_PER_DOC", "64"))
MAX_METADATA_BYTES = int(os.environ.get("MAX_METADATA_BYTES", "1800"))  # < 2KB S3V cap
MAX_RETRIES = int(os.environ.get("INGEST_MAX_RETRIES", "3"))
RETRY_BACKOFF_BASE = float(os.environ.get("INGEST_RETRY_BACKOFF_BASE", "0.5"))

# Namespace for deterministic UUIDs (fixed, so hashes are stable across deploys)
UUID_NAMESPACE = uuid.UUID("6f5a4d1c-3e2b-4b8a-9f1e-2c7d8a9b0e11")


# ---------------------------------------------------------------------------
# LOGGING (structured JSON)
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
# AWS CLIENTS (module-level for Lambda warm-start reuse)
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
    Get a single embedding from the SageMaker endpoint.

    Handles three common HF/TEI output shapes:
      - [float, float, ...]              → already flat
      - [[float, float, ...]]            → batch of 1
      - [[[float, float, ...]]]          → nested batch
    """
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=json.dumps({"inputs": text}),
    )
    raw = response["Body"].read().decode("utf-8")
    result = json.loads(raw)

    # Unwrap common nested shapes
    if isinstance(result, list) and result:
        if isinstance(result[0], list) and result[0]:
            if isinstance(result[0][0], list):
                return result[0][0]
            return result[0]
    if not isinstance(result, list) or not all(isinstance(x, (int, float)) for x in result):
        raise ValueError(f"Unexpected embedding response shape: {type(result)}")
    return result


# ---------------------------------------------------------------------------
# RETRY HELPER
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
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES:
                raise
            sleep_s = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            _log(
                "warning",
                "retry",
                attempt=attempt,
                sleep_s=sleep_s,
                error=str(exc),
            )
            time.sleep(sleep_s)
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# METADATA HELPERS
# ---------------------------------------------------------------------------

def _sanitize_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """
    S3 Vectors metadata must be JSON-serializable and small.
    Drop None values, coerce unsupported types, and enforce a byte budget.
    """
    def _coerce(v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, (str, int, float, bool)):
            return v
        if isinstance(v, (list, tuple)):
            return [_coerce(x) for x in v if x is not None]
        if isinstance(v, dict):
            return {k: _coerce(x) for k, x in v.items() if x is not None}
        return str(v)

    cleaned = {k: _coerce(v) for k, v in meta.items() if v is not None}

    # Enforce byte budget by dropping least-critical keys first.
    priority = [
        "dedupe_key",
        "topic",
        "timestamp",
        "top_signal",
        "universe",
        "window",
        "item_count",
        "source",
        "category",
        "format",
    ]
    order = priority + [k for k in cleaned if k not in priority]
    trimmed: dict[str, Any] = {}
    for k in order:
        if k not in cleaned:
            continue
        candidate = {**trimmed, k: cleaned[k]}
        if len(json.dumps(candidate, default=str).encode("utf-8")) > MAX_METADATA_BYTES:
            continue
        trimmed[k] = cleaned[k]
    return trimmed


# ---------------------------------------------------------------------------
# DEDUPE
# ---------------------------------------------------------------------------

def _vector_id_for(dedupe_key: Optional[str], index: int) -> str:
    """
    Deterministic ID when dedupe_key present (re-runs overwrite),
    random UUID otherwise.
    """
    if dedupe_key:
        return str(uuid.uuid5(UUID_NAMESPACE, f"{dedupe_key}:{index}"))
    return str(uuid.uuid4())


def _exists(dedupe_key: str) -> Optional[str]:
    """
    Return an existing vector key for this dedupe_key, or None.
    Best-effort: falls back to None (proceed) if the API doesn't support it.
    """
    try:
        resp = s3_vectors.list_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            filter={"dedupe_key": {"equals": dedupe_key}},
            maxResults=1,
        )
        vectors = resp.get("vectors") or []
        if vectors:
            return vectors[0].get("key")
    except Exception as exc:  # noqa: BLE001
        # If the backend doesn't support filters or the call shape differs,
        # don't fail the ingest — just skip dedupe short-circuit.
        _log("warning", "dedupe_check_failed", error=str(exc))
    return None


# ---------------------------------------------------------------------------
# CHUNKING
# ---------------------------------------------------------------------------

_CHUNK_BOUNDARY = re.compile(r"\n(?=(?:#|\d+\.|-\s|\"headline\"\s*:))")


def _chunk_text(text: str, max_chars: int = MAX_EMBED_CHARS) -> list[str]:
    """
    Split on structural boundaries first (headings, numbered items, JSON
    object starts), then fall back to fixed-size windows.
    """
    if len(text) <= max_chars:
        return [text]

    pieces = _CHUNK_BOUNDARY.split(text)
    chunks: list[str] = []
    buf = ""
    for piece in pieces:
        if not piece:
            continue
        if len(piece) > max_chars:
            # Oversized single piece → hard split
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(piece), max_chars):
                chunks.append(piece[i : i + max_chars])
            continue
        if len(buf) + len(piece) + 1 > max_chars:
            chunks.append(buf)
            buf = piece
        else:
            buf = f"{buf}\n{piece}" if buf else piece
    if buf:
        chunks.append(buf)
    return chunks[:MAX_CHUNKS_PER_DOC]


# ---------------------------------------------------------------------------
# INPUT PARSING
# ---------------------------------------------------------------------------

def _parse_event(event: dict[str, Any]) -> tuple[Optional[str], dict[str, Any]]:
    body = event.get("body", event)
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON body: {exc}") from exc
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")
    text = body.get("text")
    metadata = body.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    return text, metadata


# ---------------------------------------------------------------------------
# HANDLER
# ---------------------------------------------------------------------------

def _response(
    status_code: int,
    status: str,
    *,
    document_id: Optional[str] = None,
    dedupe_key: Optional[str] = None,
    chunks_written: int = 0,
    retryable: bool = False,
    message: str = "",
) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "body": json.dumps(
            {
                "status": status,
                "document_id": document_id,
                "dedupe_key": dedupe_key,
                "chunks_written": chunks_written,
                "retryable": retryable,
                "message": message,
            }
        ),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", "local")
    started = time.monotonic()

    try:
        text, metadata = _parse_event(event)
    except ValueError as exc:
        _log("warning", "bad_request", request_id=request_id, error=str(exc))
        return _response(400, "error", message=str(exc), retryable=False)

    if not text or not text.strip():
        return _response(400, "error", message="Missing required field: text")

    if not SAGEMAKER_ENDPOINT:
        return _response(
            500,
            "error",
            message="SAGEMAKER_ENDPOINT not configured",
            retryable=False,
        )

    dedupe_key = metadata.get("dedupe_key")

    # ---- Dedupe short-circuit (cheap; avoids an embedding call) ----
    if dedupe_key:
        existing = _exists(dedupe_key)
        if existing:
            _log(
                "info",
                "duplicate_skipped",
                request_id=request_id,
                dedupe_key=dedupe_key,
                existing_key=existing,
            )
            return _response(
                200,
                "duplicate",
                document_id=existing,
                dedupe_key=dedupe_key,
                chunks_written=0,
                message="Duplicate ingest; skipped.",
            )

    chunks = _chunk_text(text)
    if not chunks:
        return _response(400, "error", message="Text produced no chunks")

    _log(
        "info",
        "ingest_start",
        request_id=request_id,
        dedupe_key=dedupe_key,
        text_len=len(text),
        chunks=len(chunks),
        topic=metadata.get("topic"),
    )

    # Normalize base metadata
    base_meta = dict(metadata)
    base_meta.setdefault(
        "timestamp",
        datetime.now(timezone.utc).isoformat(),
    )
    base_meta["chunk_count"] = len(chunks)

    vectors_payload: list[dict[str, Any]] = []
    primary_id: Optional[str] = None

    for idx, chunk in enumerate(chunks):
        try:
            embedding = _call_with_retries(get_embedding, chunk)
        except Exception as exc:  # noqa: BLE001
            _log(
                "error",
                "embedding_failed",
                request_id=request_id,
                chunk_index=idx,
                error=str(exc),
            )
            return _response(
                500,
                "error",
                dedupe_key=dedupe_key,
                retryable=_is_retryable(exc),
                message=f"Embedding failed on chunk {idx}: {exc}",
            )

        vector_id = _vector_id_for(dedupe_key, idx)
        if primary_id is None:
            primary_id = vector_id

        chunk_meta = {
            **base_meta,
            "chunk_index": idx,
            "text": chunk,  # keep original text alongside vector for retrieval
        }
        chunk_meta = _sanitize_metadata(chunk_meta)

        vectors_payload.append(
            {
                "key": vector_id,
                "data": {"float32": embedding},
                "metadata": chunk_meta,
            }
        )

    # ---- Write in one batched call (falls back to serial if backend limits) ----
    try:
        _call_with_retries(
            s3_vectors.put_vectors,
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            vectors=vectors_payload,
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        # Some backends cap batch size; fall back to serial writes.
        if code in {"ValidationException", "BatchSizeLimitExceeded"}:
            _log(
                "warning",
                "batch_write_rejected_serial_fallback",
                request_id=request_id,
                error=str(exc),
            )
            for v in vectors_payload:
                try:
                    _call_with_retries(
                        s3_vectors.put_vectors,
                        vectorBucketName=VECTOR_BUCKET,
                        indexName=INDEX_NAME,
                        vectors=[v],
                    )
                except Exception as inner:  # noqa: BLE001
                    _log(
                        "error",
                        "serial_write_failed",
                        request_id=request_id,
                        key=v["key"],
                        error=str(inner),
                    )
                    return _response(
                        500,
                        "error",
                        dedupe_key=dedupe_key,
                        retryable=_is_retryable(inner),
                        message=f"Vector write failed: {inner}",
                    )
        else:
            _log("error", "write_failed", request_id=request_id, error=str(exc))
            return _response(
                500,
                "error",
                dedupe_key=dedupe_key,
                retryable=_is_retryable(exc),
                message=f"Vector write failed: {exc}",
            )

    elapsed_ms = int((time.monotonic() - started) * 1000)
    _log(
        "info",
        "ingest_done",
        request_id=request_id,
        dedupe_key=dedupe_key,
        chunks_written=len(vectors_payload),
        elapsed_ms=elapsed_ms,
    )

    return _response(
        200,
        "ok",
        document_id=primary_id,
        dedupe_key=dedupe_key,
        chunks_written=len(vectors_payload),
        message=f"Indexed {len(vectors_payload)} chunk(s).",
    )