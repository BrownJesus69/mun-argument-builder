"""Core fallacy and fact analysis engine."""

from __future__ import annotations

import json
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from llm import call_llm_json
from checker.checker_output import (
    console,
    divider,
    error,
    field,
    header,
    placeholder,
    severity_summary,
    success,
)
from themes.arctic_steel import THEME


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CheckerError:
    claim: str
    error_type: str
    severity: Literal["HIGH", "MEDIUM", "LOW", "INFO"]
    explanation: str
    correction: str
    evidence: list[str]


# ---------------------------------------------------------------------------
# DB loaders
# ---------------------------------------------------------------------------

def load_legal_db() -> dict:
    p = Path(__file__).parent / "legal_reference_db.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _load_fallacy_patterns() -> list[dict]:
    p = Path(__file__).parent / "fallacy_patterns.json"
    if p.exists():
        return json.loads(p.read_text())
    return []


# ---------------------------------------------------------------------------
# LLM deep scan
# ---------------------------------------------------------------------------

_CHECKER_PROMPT = textwrap.dedent("""\
    You are a strict MUN argument auditor. Analyse the provided text for:
    1. Logical fallacies (ad hominem, straw man, false dilemma, slippery slope, etc.)
    2. Legal misapplications (incorrect citation of UN Charter articles, resolutions, treaties)
    3. Factual inaccuracies or unverifiable statistics

    Return a JSON object with exactly these keys:
    - "errors": list of error objects, each with:
        "claim" (str): the exact phrase or sentence containing the error
        "error_type" (str): short label e.g. "Legal Misapplication", "Ad Hominem"
        "severity" (str): one of HIGH | MEDIUM | LOW | INFO
        "explanation" (str): why this is an error
        "correction" (str): how to fix or rephrase it
        "search_query" (str): a search query to find verification evidence
    - "summary": object with integer counts for "high", "medium", "low", "info"

    If no errors are found, return {"errors": [], "summary": {"high": 0, "medium": 0, "low": 0, "info": 0}}.

    Text to analyse:

    {text}
""")


def _llm_scan(text: str) -> dict:
    prompt = _CHECKER_PROMPT.format(text=text)
    try:
        return call_llm_json(prompt)
    except Exception:
        return {"errors": [], "summary": {"high": 0, "medium": 0, "low": 0, "info": 0}}


# ---------------------------------------------------------------------------
# Heuristic pre-scan
# ---------------------------------------------------------------------------

def _heuristic_scan(text: str) -> list[CheckerError]:
    patterns = _load_fallacy_patterns()
    found: list[CheckerError] = []
    text_lower = text.lower()

    for pattern in patterns:
        for phrase in pattern.get("trigger_phrases", []):
            if phrase.lower() in text_lower:
                found.append(
                    CheckerError(
                        claim=phrase,
                        error_type=pattern["name"],
                        severity=pattern["severity"],
                        explanation=pattern["description"],
                        correction="Review phrasing to avoid this fallacy pattern.",
                        evidence=[f"search: {pattern['name']} fallacy MUN examples"],
                    )
                )
                break

    return found


# ---------------------------------------------------------------------------
# Legal DB cross-reference
# ---------------------------------------------------------------------------

_LEGAL_KEYWORDS = {
    "UN Charter Art 51": "UN_CHARTER_ART_51",
    "Article 51": "UN_CHARTER_ART_51",
    "Art. 51": "UN_CHARTER_ART_51",
    "UN Charter Art 42": "UN_CHARTER_ART_42",
    "Article 42": "UN_CHARTER_ART_42",
    "Resolution 1373": "UNSC_RES_1373",
    "Res 1373": "UNSC_RES_1373",
    "Resolution 2231": "UNSC_RES_2231",
    "Res 2231": "UNSC_RES_2231",
    "Paris Agreement": "PARIS_AGREEMENT",
    "UDHR Article 19": "UDHR_ART_19",
    "Article 19": "UDHR_ART_19",
    "ICCPR Article 6": "ICCPR_ART_6",
    "Article 6": "ICCPR_ART_6",
    "UNCLOS Article 121": "UNCLOS_ART_121",
    "Article 121": "UNCLOS_ART_121",
}


def _enrich_with_legal_db(errors: list[CheckerError], legal_db: dict) -> list[CheckerError]:
    for err in errors:
        for keyword, db_key in _LEGAL_KEYWORDS.items():
            if keyword.lower() in err.claim.lower() and db_key in legal_db:
                entry = legal_db[db_key]
                misuse = entry.get("common_misuse", "")
                if misuse:
                    err.explanation += f" [Legal DB: {misuse}]"
                break
    return errors


# ---------------------------------------------------------------------------
# Public entry point — check_verbatim (API)
# ---------------------------------------------------------------------------

def check_verbatim(text: str) -> dict:
    legal_db = load_legal_db()

    # LLM deep scan
    llm_result = _llm_scan(text)
    llm_errors_raw: list[dict] = llm_result.get("errors", [])

    llm_errors: list[CheckerError] = []
    for item in llm_errors_raw:
        try:
            llm_errors.append(
                CheckerError(
                    claim=item["claim"],
                    error_type=item["error_type"],
                    severity=item["severity"],
                    explanation=item["explanation"],
                    correction=item["correction"],
                    evidence=[item.get("search_query", "")] if item.get("search_query") else [],
                )
            )
        except (KeyError, TypeError):
            continue

    # Heuristic scan
    heuristic_errors = _heuristic_scan(text)

    # Merge — deduplicate by claim
    seen: set[str] = set()
    all_errors: list[CheckerError] = []
    for e in llm_errors + heuristic_errors:
        if e.claim not in seen:
            seen.add(e.claim)
            all_errors.append(e)

    # Enrich with legal DB
    all_errors = _enrich_with_legal_db(all_errors, legal_db)

    # Build summary
    counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for e in all_errors:
        counts[e.severity.lower()] = counts.get(e.severity.lower(), 0) + 1

    return {
        "errors": [asdict(e) for e in all_errors],
        "summary": counts,
    }


# ---------------------------------------------------------------------------
# CLI entry point — run_check
# ---------------------------------------------------------------------------

def run_check(
    verbatim: str | None,
    file_path: str | None,
    chain: bool,
) -> None:
    from rich.style import Style

    if chain:
        last = Path(".last_slug")
        if not last.exists():
            console.print("  No previous build. Run `build` first.", style=Style(color=THEME["error"]))
            return
        slug = last.read_text().strip()
        src = Path("output") / slug / "arguments.md"
        if not src.exists():
            console.print(f"  {src} not found.", style=Style(color=THEME["error"]))
            return
        text = src.read_text()
        output_slug = slug
    elif file_path:
        p = Path(file_path)
        if not p.exists():
            console.print(f"  File not found: {file_path}", style=Style(color=THEME["error"]))
            return
        text = p.read_text()
        output_slug = p.stem
    elif verbatim:
        text = verbatim
        output_slug = "verbatim-check"
    else:
        console.print("  Provide --verbatim, --file, or --chain.", style=Style(color=THEME["warn"]))
        return

    result = check_verbatim(text)
    errors_raw: list[dict] = result["errors"]
    summary = result["summary"]

    # Render
    header("Fallacy & Fact Check Report")
    field("Input", text[:60] + ("…" if len(text) > 60 else ""))
    divider()

    if not errors_raw:
        success("No issues found.")
        severity_summary(0, 0, 0)
    else:
        for e in errors_raw:
            error(e["severity"], e["claim"], e["explanation"])
            console.print(
                f"  {'':12}→ {e['correction']}",
                style=Style(color=THEME["key"], italic=True),
            )
            for ev in e.get("evidence", []):
                if ev:
                    placeholder("Evidence", ev)
        severity_summary(summary["high"], summary["medium"], summary["low"])

    # Write files
    out = Path("output") / output_slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "fallacy_report.json").write_text(json.dumps(result, indent=2))

    lines = ["# Fallacy & Fact Check Report\n"]
    if not errors_raw:
        lines.append("No issues found.\n")
    else:
        for e in errors_raw:
            lines += [
                f"\n## [{e['severity']}] {e['error_type']}",
                f"**Claim:** {e['claim']}",
                f"**Explanation:** {e['explanation']}",
                f"**Correction:** {e['correction']}",
                f"**Evidence:** {', '.join(e.get('evidence', []))}\n",
            ]
    (out / "fallacy_report.md").write_text("\n".join(lines))
