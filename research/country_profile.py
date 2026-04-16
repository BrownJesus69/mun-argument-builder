"""Country stance and statistics fetcher."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import anthropic
import requests
from rich.style import Style

import config
from checker.checker_output import console, divider, field, header, placeholder
from themes.arctic_steel import THEME


# ---------------------------------------------------------------------------
# OpenAlex helpers (no key required)
# ---------------------------------------------------------------------------

_OPENALEX_BASE = "https://api.openalex.org/works"


def _openalex_search(query: str, max_results: int = 3) -> list[dict]:
    try:
        resp = requests.get(
            _OPENALEX_BASE,
            params={"search": query, "per-page": max_results, "select": "title,doi,publication_year"},
            timeout=8,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# UNdata REST (no key required)
# ---------------------------------------------------------------------------

_UNDATA_BASE = "https://data.un.org/ws/rest/data"


def _undata_search(country: str, topic: str) -> str:
    """Return a placeholder; UNdata REST is complex to query ad-hoc."""
    return f"[PLACEHOLDER] UNdata query: {country} {topic}"


# ---------------------------------------------------------------------------
# Claude-powered country brief
# ---------------------------------------------------------------------------

_PROFILE_SYSTEM = textwrap.dedent("""\
    You are a diplomatic research assistant. Given a country and a topic, produce a structured country profile with:
    1. Official position / stance on the topic (cite UN voting record if known)
    2. Key national interests driving the position
    3. Relevant treaties, resolutions, or agreements the country has signed
    4. 2-3 statistics or data points that support the country's narrative
    5. Likely alliances and opposition in committee
    6. Suggested talking points (3 bullet points)

    Format as clean markdown with section headers. Be factual and concise.
""")


def _claude_profile(country: str, topic: str) -> str:
    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_KEY)
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system=_PROFILE_SYSTEM,
            messages=[{"role": "user", "content": f"Country: {country}\nTopic: {topic}"}],
        )
        return message.content[0].text
    except Exception as exc:  # noqa: BLE001
        console.print(
            f"  [PLACEHOLDER] Claude unavailable: {exc}",
            style=Style(color=THEME["dim"], italic=True),
        )
        return (
            f"## {country} — {topic}\n\n"
            "_[PLACEHOLDER] Claude API unavailable. Fill in manually._\n\n"
            "### Position\n_Unknown_\n\n"
            "### Key Interests\n_Unknown_\n\n"
            "### Suggested Talking Points\n- Point 1\n- Point 2\n- Point 3\n"
        )


# ---------------------------------------------------------------------------
# Google Fact Check (optional)
# ---------------------------------------------------------------------------

_FACT_CHECK_BASE = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


def _google_fact_check(query: str) -> list[dict]:
    if not config.GOOGLE_KEY:
        return []
    try:
        resp = requests.get(
            _FACT_CHECK_BASE,
            params={"query": query, "key": config.GOOGLE_KEY, "pageSize": 3},
            timeout=8,
        )
        resp.raise_for_status()
        return resp.json().get("claims", [])
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fetch_profile(country: str, topic: str) -> None:
    slug = f"{country.lower().replace(' ', '-')}-{topic.lower().replace(' ', '-')[:30]}"
    out = Path("output") / slug
    out.mkdir(parents=True, exist_ok=True)

    header(f"Country Profile — {country}")
    field("Topic", topic)
    divider()

    # Claude brief
    profile_md = _claude_profile(country, topic)

    # OpenAlex academic evidence
    oa_results = _openalex_search(f"{country} {topic} policy")

    # Assemble output
    lines = [profile_md, "\n---\n", "## Academic Evidence (OpenAlex)\n"]
    if oa_results:
        for r in oa_results:
            title = r.get("title", "Untitled")
            doi = r.get("doi", "")
            year = r.get("publication_year", "n.d.")
            lines.append(f"- ({year}) {title}" + (f" — {doi}" if doi else ""))
    else:
        lines.append("_[PLACEHOLDER] OpenAlex unavailable or no results._")

    content = "\n".join(lines)
    profile_path = out / "country_profile.md"
    profile_path.write_text(content)

    console.print(profile_md, style=Style(color=THEME["value"]))
    divider()
    console.print(f"  ✓  country_profile.md → output/{slug}/", style=Style(color=THEME["success"], bold=True))
    console.print()
