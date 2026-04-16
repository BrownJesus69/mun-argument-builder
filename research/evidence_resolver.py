"""OpenAlex and Google Fact Check evidence resolver."""

from __future__ import annotations

from dataclasses import dataclass

import requests

import config
from themes.arctic_steel import THEME


@dataclass
class Evidence:
    title: str
    source: str
    url: str | None
    year: int | None
    verified: bool


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

_OPENALEX_BASE = "https://api.openalex.org/works"


def resolve_openalex(query: str, max_results: int = 5) -> list[Evidence]:
    try:
        resp = requests.get(
            _OPENALEX_BASE,
            params={
                "search": query,
                "per-page": max_results,
                "select": "title,doi,publication_year,primary_location",
            },
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception:  # noqa: BLE001
        return []

    evidence: list[Evidence] = []
    for r in results:
        doi = r.get("doi")
        loc = r.get("primary_location") or {}
        source = (loc.get("source") or {}).get("display_name", "OpenAlex")
        evidence.append(
            Evidence(
                title=r.get("title", "Untitled"),
                source=source,
                url=doi,
                year=r.get("publication_year"),
                verified=True,
            )
        )
    return evidence


# ---------------------------------------------------------------------------
# Google Fact Check
# ---------------------------------------------------------------------------

_FACT_CHECK_BASE = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


def resolve_fact_check(query: str, max_results: int = 5) -> list[Evidence]:
    if not config.GOOGLE_KEY:
        return []
    try:
        resp = requests.get(
            _FACT_CHECK_BASE,
            params={"query": query, "key": config.GOOGLE_KEY, "pageSize": max_results},
            timeout=8,
        )
        resp.raise_for_status()
        claims = resp.json().get("claims", [])
    except Exception:  # noqa: BLE001
        return []

    evidence: list[Evidence] = []
    for c in claims:
        review = (c.get("claimReview") or [{}])[0]
        evidence.append(
            Evidence(
                title=c.get("text", "Unknown claim"),
                source=review.get("publisher", {}).get("name", "Google Fact Check"),
                url=review.get("url"),
                year=None,
                verified=review.get("textualRating", "").lower() in ("true", "mostly true"),
            )
        )
    return evidence


# ---------------------------------------------------------------------------
# Combined resolver
# ---------------------------------------------------------------------------

def resolve(query: str, max_results: int = 5) -> list[Evidence]:
    """Resolve a search query against OpenAlex and Google Fact Check."""
    oa = resolve_openalex(query, max_results)
    fc = resolve_fact_check(query, max_results)
    return (oa + fc)[:max_results]
