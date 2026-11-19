from __future__ import annotations

import hashlib
from typing import Any

import httpx
from sqlalchemy.orm import Session

from backend.shared.models import ResearchSnapshotModel


def _top_symbols(result: dict[str, Any], limit: int = 5) -> list[str]:
    return list(dict.fromkeys(
        holding["symbol"].upper()
        for holding in result.get("charts", {}).get("top_holdings", [])[:limit]
        if holding.get("symbol")
    ))


def _evidence_for_symbol(brief: dict[str, Any], symbol: str) -> list[dict[str, Any]]:
    items = brief.get("items") or []
    selected = [
        item for item in items
        if symbol in {str(ticker).upper() for ticker in item.get("tickers", [])}
    ]
    if not selected and len(brief.get("universe") or []) == 1:
        selected = items
    return selected


def _snapshot_row(job_id: str, symbol: str, brief: dict[str, Any]) -> dict[str, Any] | None:
    items = _evidence_for_symbol(brief, symbol)
    if not items:
        return None
    summaries = []
    source_refs: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in items[:8]:
        headline = str(item.get("headline") or "Research item")[:300]
        summary = str(item.get("summary") or "")[:800]
        summaries.append(f"{headline}: {summary}".strip())
        for source in item.get("sources", [])[:5]:
            url = str(source.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            source_refs.append({
                "name": str(source.get("name") or "source")[:120],
                "url": url[:2000],
                "published_at": source.get("published_at"),
                "tier": source.get("tier"),
            })
    if not source_refs:
        return None
    material = f"{job_id}:{symbol}"
    snapshot_id = f"research-{hashlib.sha256(material.encode()).hexdigest()[:32]}"
    return {
        "snapshot_id": snapshot_id,
        "symbol": symbol,
        "summary": "\n".join(summaries)[:6000],
        "source_refs": source_refs,
        "items": items[:8],
        "model_version": "alex_researcher_mcp_v1",
    }


async def ingest_research_brief(
    db: Session,
    *,
    job_id: str,
    result: dict[str, Any],
    base_url: str,
    api_key: str,
) -> dict[str, Any]:
    symbols = _top_symbols(result)
    if not symbols:
        return {"status": "skipped", "reason": "no_priced_holdings", "symbols": []}
    if not base_url:
        return {"status": "unavailable", "reason": "researcher_service_not_configured", "symbols": symbols}

    try:
        async with httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key} if api_key else {},
            timeout=httpx.Timeout(630.0),
        ) as client:
            response = await client.post(
                "/research",
                json={"mode": "ticker", "tickers": symbols, "window": "7d", "ingest": False},
            )
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return {"status": "unavailable", "reason": "researcher_request_failed", "symbols": symbols}

    brief = payload.get("brief")
    if not payload.get("parse_ok") or not isinstance(brief, dict):
        return {
            "status": "unavailable",
            "reason": "research_brief_validation_failed",
            "run_id": payload.get("run_id"),
            "symbols": symbols,
        }

    snapshots = []
    for symbol in symbols:
        row_data = _snapshot_row(job_id, symbol, brief)
        if not row_data:
            continue
        row = db.query(ResearchSnapshotModel).filter_by(snapshot_id=row_data["snapshot_id"]).first()
        if row:
            row.summary = row_data["summary"]
            row.source_refs = row_data["source_refs"]
        else:
            row = ResearchSnapshotModel(
                snapshot_id=row_data["snapshot_id"],
                symbol=row_data["symbol"],
                summary=row_data["summary"],
                source_refs=row_data["source_refs"],
                model_version=row_data["model_version"],
                valuation={},
                financials={
                    "research_window": brief.get("window"),
                    "generated_at": brief.get("generated_at_utc"),
                    "items": row_data["items"],
                    "top_signal": brief.get("top_signal"),
                    "risks_and_caveats": brief.get("risks_and_caveats", []),
                },
                audit_id=f"advisor-research:{job_id}",
            )
            db.add(row)
        snapshots.append({
            "snapshot_id": row_data["snapshot_id"],
            "symbol": symbol,
            "summary": row_data["summary"],
            "source_refs": row_data["source_refs"],
            "items": row_data["items"],
        })
    db.flush()
    return {
        "status": "ingested" if snapshots else "no_cited_items",
        "run_id": payload.get("run_id"),
        "parse_ok": True,
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
    }