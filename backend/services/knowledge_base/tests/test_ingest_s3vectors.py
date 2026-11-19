"""
Local test: ingest documents directly into S3 Vectors.
Bypasses API Gateway, exercises the shared schema and embeddings.
"""
import json
import logging
import os
from datetime import datetime, UTC

import boto3
from dotenv import load_dotenv
from pathlib import Path

from shared.embeddings import get_embedding
from shared.schema import build_metadata_dict, vector_key_for

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env", override=True)

logger = logging.getLogger("test_ingest")
logging.basicConfig(level=logging.INFO)

VECTOR_BUCKET = os.environ["VECTOR_BUCKET"]
INDEX_NAME = os.environ.get("INDEX_NAME", "financial-research")
s3_vectors = boto3.client("s3vectors")


TEST_DOCS = [
    {
        "text": (
            "Tesla Inc. (TSLA) is an electric vehicle and clean energy company. "
            "It designs, manufactures, and sells electric vehicles, energy "
            "storage systems, and solar panels."
        ),
        "metadata": {
            "agent": "user",
            "doc_type": "user_note",
            "tickers": ["TSLA"],
            "topics": ["ev", "clean_energy"],
            "source_urls": ["https://example.com/tsla"],
            "scope": "global",
        },
    },
    {
        "text": (
            "Amazon.com Inc. (AMZN) is a multinational technology company "
            "focusing on e-commerce, cloud computing (AWS), digital streaming, "
            "and artificial intelligence."
        ),
        "metadata": {
            "agent": "user",
            "doc_type": "user_note",
            "tickers": ["AMZN"],
            "topics": ["cloud", "e-commerce"],
            "source_urls": ["https://example.com/amzn"],
            "scope": "global",
        },
    },
    {
        "text": (
            "NVIDIA Corporation (NVDA) designs graphics processing units (GPUs) "
            "for gaming and professional markets, as well as system on chip "
            "units for mobile computing and automotive."
        ),
        "metadata": {
            "agent": "user",
            "doc_type": "user_note",
            "tickers": ["NVDA"],
            "topics": ["gpu", "ai"],
            "source_urls": ["https://example.com/nvda"],
            "scope": "global",
        },
    },
]


def ingest_document(text: str, metadata: dict) -> str:
    enriched = build_metadata_dict(
        text=text,
        agent=metadata.pop("agent", "user"),
        doc_type=metadata.pop("doc_type", "user_note"),
        **metadata,
    )
    embedding = get_embedding(text)
    key = vector_key_for(text)

    s3_vectors.put_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME,
        vectors=[{
            "key": key,
            "data": {"float32": embedding},
            "metadata": {
                "text": text,
                "ingested_at": datetime.now(UTC).isoformat(),
                **enriched,
            },
        }],
    )
    return key


def main() -> None:
    print(f"Bucket: {VECTOR_BUCKET}")
    print(f"Index:  {INDEX_NAME}")
    print()

    for i, doc in enumerate(TEST_DOCS, 1):
        meta = dict(doc["metadata"])
        ticker = meta.get("tickers", ["?"])[0]
        print(f"[{i}/{len(TEST_DOCS)}] Ingesting {ticker}")
        try:
            doc_id = ingest_document(doc["text"], meta)
            print(f"  id={doc_id}")
        except Exception as exc:
            print(f"  error: {exc}")

    print("\nDone. Re-running this script should not create duplicates.")


if __name__ == "__main__":
    main()