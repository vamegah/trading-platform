"""
Shared embedding client for the knowledge base.

Wraps the SageMaker endpoint that produces HuggingFace embeddings.
All knowledge-base modules import from here — no duplication.
"""
import json
import logging
import os

import boto3
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

SAGEMAKER_ENDPOINT = os.environ["SAGEMAKER_ENDPOINT"]

_sagemaker = boto3.client("sagemaker-runtime")


def _normalise(result):
    """Flatten [[[vec]]] / [[vec]] / [vec] to [vec]."""
    if isinstance(result, list) and result:
        if isinstance(result[0], list) and result[0]:
            if isinstance(result[0][0], list):
                return result[0][0]
            return result[0]
    return result


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def get_embedding(text: str) -> list[float]:
    """Return the embedding vector for `text`."""
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")

    response = _sagemaker.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=json.dumps({"inputs": text}),
    )
    raw = json.loads(response["Body"].read().decode())
    vector = _normalise(raw)

    if not isinstance(vector, list) or not vector:
        raise ValueError(f"Unexpected embedding shape: {type(vector)}")
    return vector


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch helper. Falls back to per-item calls if the endpoint does not batch."""
    if not texts:
        return []
    try:
        response = _sagemaker.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType="application/json",
            Body=json.dumps({"inputs": texts}),
        )
        raw = json.loads(response["Body"].read().decode())
        if isinstance(raw, list) and len(raw) == len(texts):
            return [_normalise(item) for item in raw]
    except Exception:
        logger.warning("Batch embed failed; falling back to per-item calls")
    return [get_embedding(t) for t in texts]