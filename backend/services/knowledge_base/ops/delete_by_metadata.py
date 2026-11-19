"""
Selective deletion from S3 Vectors by metadata filters.

Usage:
    python delete_by_metadata.py agent=researcher_agent
    python delete_by_metadata.py scope=user user_id=abc-123
"""
import logging
import os
import sys

import boto3
from shared.embeddings import get_embedding

logger = logging.getLogger("delete_by_metadata")
logging.basicConfig(level=logging.INFO)

VECTOR_BUCKET = os.environ["VECTOR_BUCKET"]
INDEX_NAME = os.environ.get("INDEX_NAME", "financial-research")

s3_vectors = boto3.client("s3vectors")


def _matches(meta: dict, filters: dict) -> bool:
    return all(meta.get(k) == v for k, v in filters.items())


def delete_by_filters(filters: dict, batch_size: int = 30) -> int:
    probe = get_embedding("document")
    deleted = 0

    while True:
        resp = s3_vectors.query_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            queryVector={"float32": probe},
            topK=batch_size,
            returnMetadata=True,
        )
        vectors = resp.get("vectors", [])
        if not vectors:
            break

        to_delete = [
            v["key"] for v in vectors
            if _matches(v.get("metadata", {}) or {}, filters)
        ]
        if to_delete:
            s3_vectors.delete_vectors(
                vectorBucketName=VECTOR_BUCKET,
                indexName=INDEX_NAME,
                keys=to_delete,
            )
            deleted += len(to_delete)

        if len(vectors) < batch_size:
            break

    return deleted


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: delete_by_metadata.py key=value [key=value ...]")
        sys.exit(1)

    filters = dict(arg.split("=", 1) for arg in sys.argv[1:])
    logger.info("Deleting vectors matching %s", filters)

    n = delete_by_filters(filters)
    print(f"Deleted {n} vectors matching {filters}")


if __name__ == "__main__":
    main()