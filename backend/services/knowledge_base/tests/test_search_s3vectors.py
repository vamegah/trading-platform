"""
Local test: search S3 Vectors.
Exercises filters, min_score, and the normalised score output.
"""
import json
import logging
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

from shared.embeddings import get_embedding

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env", override=True)

logger = logging.getLogger("test_search")
logging.basicConfig(level=logging.INFO)

VECTOR_BUCKET = os.environ["VECTOR_BUCKET"]
INDEX_NAME = os.environ.get("INDEX_NAME", "financial-research")
s3_vectors = boto3.client("s3vectors")


def search(query: str, k: int = 5, min_score: float = 0.0, filters: dict | None = None):
    embedding = get_embedding(query)
    resp = s3_vectors.query_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME,
        queryVector={"float32": embedding},
        topK=k,
        returnDistance=True,
        returnMetadata=True,
    )

    results = []
    for v in resp.get("vectors", []):
        meta = v.get("metadata", {}) or {}
        score = 1.0 - float(v.get("distance", 0.0))
        if score < min_score:
            continue
        if filters and not all(meta.get(kk) == vv for kk, vv in filters.items()):
            continue
        results.append({
            "id": v["key"],
            "score": round(score, 4),
            "text": meta.get("text", ""),
            "metadata": {k2: v2 for k2, v2 in meta.items() if k2 != "text"},
        })
    return results


def main() -> None:
    print("Exploratory search:")

    for query in [
        "electric vehicles and sustainable transportation",
        "cloud computing and AWS services",
        "artificial intelligence and GPU computing",
    ]:
        print(f"\nQuery: {query}")
        for r in search(query, k=3, min_score=0.3):
            tickers = r["metadata"].get("tickers", [])
            print(f"  score={r['score']} tickers={tickers}")
            print(f"  {r['text'][:120]}…")

    print("\nFiltered search (agent=user):")
    for r in search("company overview", k=5, filters={"agent": "user"}):
        print(f"  {r['id']} score={r['score']}")

    print("\nIdempotency check — same query should return same keys:")
    first = [r["id"] for r in search("technology", k=3)]
    second = [r["id"] for r in search("technology", k=3)]
    assert first == second, "Non-deterministic results"
    print("  ok")


if __name__ == "__main__":
    main()