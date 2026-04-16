"""Country stance and statistics fetcher."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from llm import call_llm_json
from checker.checker_output import console, divider, field, header
from themes.arctic_steel import COLORS as THEME
from rich.style import Style


_PROFILE_PROMPT = textwrap.dedent("""\
    You are a diplomatic research assistant. Given a country and a topic, produce a structured
    country profile as a JSON object with exactly these keys:

    - "official_stance": str — the country's official position on the topic
    - "key_interests": list of str — 3-5 national interests driving the position
    - "historical_voting": str — summary of relevant UN voting history
    - "likely_alliances": list of str — countries or blocs likely to align with this country
    - "key_arguments": list of str — 3-5 strongest arguments the country can make
    - "vulnerabilities": list of str — 2-3 weaknesses opponents might exploit
    - "suggested_resolution_language": str — one preambulatory or operative clause suggestion
    - "evidence_placeholders": list of objects, each with "label" (str) and "search" (str)
      — 3 evidence gaps that need to be filled with real research

    Country: {country}
    Topic: {topic}

    Be factual, concise, and diplomatically accurate.
""")


def get_profile(country: str, topic: str) -> dict:
    prompt = _PROFILE_PROMPT.format(country=country, topic=topic)
    return call_llm_json(prompt)


def fetch_profile(country: str, topic: str) -> None:
    slug = f"{country.lower().replace(' ', '-')}-{topic.lower().replace(' ', '-')[:30]}"
    out = Path("output") / slug
    out.mkdir(parents=True, exist_ok=True)

    header(f"Country Profile — {country}")
    field("Topic", topic)
    divider()

    profile = get_profile(country, topic)

    # Display
    console.print(f"  Official Stance", style=Style(color=THEME["key"], bold=True))
    console.print(f"  {profile.get('official_stance', '')}", style=Style(color=THEME["value"]))

    console.print(f"\n  Key Interests", style=Style(color=THEME["key"], bold=True))
    for interest in profile.get("key_interests", []):
        console.print(f"  • {interest}", style=Style(color=THEME["value"]))

    console.print(f"\n  Key Arguments", style=Style(color=THEME["key"], bold=True))
    for arg in profile.get("key_arguments", []):
        console.print(f"  • {arg}", style=Style(color=THEME["value"]))

    console.print(f"\n  Likely Alliances", style=Style(color=THEME["key"], bold=True))
    for ally in profile.get("likely_alliances", []):
        console.print(f"  • {ally}", style=Style(color=THEME["value"]))

    console.print(f"\n  Vulnerabilities", style=Style(color=THEME["warn"], bold=True))
    for v in profile.get("vulnerabilities", []):
        console.print(f"  ⚠ {v}", style=Style(color=THEME["warn"]))

    # Save
    profile_path = out / "country_profile.json"
    profile_path.write_text(json.dumps(profile, indent=2))

    divider()
    console.print(
        f"  ✓  country_profile.json → output/{slug}/",
        style=Style(color=THEME["success"], bold=True),
    )
    console.print()
