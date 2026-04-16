"""OpenAlex and Google Fact Check evidence resolution."""

from __future__ import annotations

import requests

OPENALEX_BASE = "https://api.openalex.org/works"
GOOGLE_FACTCHECK_BASE = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


def resolve_evidence(search_query: str) -> list[dict]:
    """Query OpenAlex for academic evidence. Returns top 3 results, or [] on failure."""
    try:
        resp = requests.get(
            OPENALEX_BASE,
            params={
                "search": search_query,
                "per-page": 3,
                "select": "title,doi,id,cited_by_count,open_access,publication_year",
            },
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        out: list[dict] = []
        for r in results:
            oa = r.get("open_access") or {}
            out.append(
                {
                    "title": r.get("title", "Untitled"),
                    "doi": r.get("doi", ""),
                    "url": oa.get("oa_url") or r.get("id", ""),
                    "cited_by_count": r.get("cited_by_count", 0),
                    "open_access": oa.get("is_oa", False),
                }
            )
        return out
    except Exception:
        return []


def fact_check(claim: str, api_key: str | None) -> list[dict]:
    """Query Google Fact Check API. Returns [] if no key or on failure."""
    if not api_key:
        return []
    try:
        resp = requests.get(
            GOOGLE_FACTCHECK_BASE,
            params={"query": claim, "key": api_key, "pageSize": 3},
            timeout=8,
        )
        resp.raise_for_status()
        claims = resp.json().get("claims", [])
        out: list[dict] = []
        for c in claims:
            review = (c.get("claimReview") or [{}])[0]
            out.append(
                {
                    "text": c.get("text", ""),
                    "claimant": c.get("claimant", ""),
                    "rating": review.get("textualRating", ""),
                    "url": review.get("url", ""),
                }
            )
        return out
    except Exception:
        return []
