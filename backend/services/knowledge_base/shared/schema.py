"""
Canonical document metadata schema for the knowledge base.

Every vector written to S3 Vectors carries this metadata. The schema
enforces idempotency (text_hash), tenancy (scope/user_id), and lifecycle
(expires_at), all of which the trading platform relies on.
"""
import hashlib
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


DocType = Literal[
    "research_article",
    "portfolio_note",
    "agent_analysis",
    "user_note",
    "event_context",
]

AgentName = Literal[
    "researcher_agent",
    "report_writer",
    "fundamentals_agent",
    "technical_agent",
    "news_sentiment_agent",
    "macro_agent",
    "bull_bear_agent",
    "trader_risk_agent",
    "user",
    "system",
]

ScopeType = Literal["global", "user"]


class DocumentMetadata(BaseModel):
    """Canonical metadata for a knowledge-base document."""

    # Required
    text_hash: str = Field(..., description="SHA256 of text; idempotency key")
    agent: AgentName
    doc_type: DocType

    # Content
    tickers: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

    # Lifecycle
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Tenancy
    scope: ScopeType = "global"
    user_id: Optional[str] = None  # required when scope == "user"

    def model_post_init(self, __context) -> None:
        if self.scope == "user" and not self.user_id:
            raise ValueError("user_id required when scope='user'")


def compute_text_hash(text: str) -> str:
    """Deterministic SHA256 of the text."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def vector_key_for(text: str) -> str:
    """
    Deterministic S3 Vectors key.

    Same text always produces the same key, so re-ingestion overwrites
    instead of creating duplicates.
    """
    return compute_text_hash(text).removeprefix("sha256:")[:32]


def build_metadata_dict(
    text: str,
    agent: AgentName,
    doc_type: DocType,
    **kwargs,
) -> dict:
    """Build a metadata dict ready for S3 Vectors, with defaults filled in."""
    meta = DocumentMetadata(
        text_hash=compute_text_hash(text),
        agent=agent,
        doc_type=doc_type,
        **kwargs,
    )
    return meta.model_dump(exclude_none=True, mode="json")