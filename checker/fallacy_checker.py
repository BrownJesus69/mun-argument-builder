"""Core fallacy and fact analysis engine."""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests

import config
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
# Claude-powered analysis
# ---------------------------------------------------------------------------

_CHECKER_SYSTEM = textwrap.dedent("""\
    You are a strict MUN argument auditor. Analyse the provided text for:
    1. Logical fallacies (ad hominem, straw man, false dilemma, slippery slope, etc.)
    2. Legal misapplications (incorrect citation of UN Charter articles, resolutions, treaties)
    3. Factual inaccuracies or unverifiable statistics

    Respond ONLY with a JSON array of error objects. Each object must have exactly these keys:
    - claim (str): the exact phrase or sentence that contains the error
    - error_type (str): short label e.g. "Legal Misapplication", "Ad Hominem"
    - severity (str): one of HIGH | MEDIUM | LOW | INFO
    - explanation (str): why this is an error
    - correction (str): how to fix or rephrase it
    - evidence (list[str]): search queries or DOI strings to verify

    If no errors are found, return an empty array [].
    Do NOT wrap the JSON in markdown fencing.
""")


def _call_llm(text: str) -> list[dict]:
    prompt = f"{_CHECKER_SYSTEM}\n\nText to analyse:\n\n{text}"
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    try:
        resp = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["response"].strip()
        return json.loads(raw)
    except requests.ConnectionError:
        console.print(
            "  Ollama not reachable. Run: ollama serve",
            style=__import__("rich.style", fromlist=["Style"]).Style(color=THEME["error"]),
        )
        return []
    except json.JSONDecodeError:
        return []
    except Exception as exc:  # noqa: BLE001
        console.print(
            f"  [PLACEHOLDER] LLM unavailable: {exc}",
            style=__import__("rich.style", fromlist=["Style"]).Style(color=THEME["dim"], italic=True),
        )
        return []


def _load_fallacy_patterns() -> list[dict]:
    p = Path(__file__).parent / "fallacy_patterns.json"
    if p.exists():
        return json.loads(p.read_text())
    return []


def _load_legal_db() -> dict:
    p = Path(__file__).parent / "legal_reference_db.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


# ---------------------------------------------------------------------------
# Heuristic pre-scan (no API needed)
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
                break  # one hit per pattern is enough

    return found


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _render_report(errors: list[CheckerError], text_excerpt: str) -> None:
    header("Fallacy & Fact Check Report")
    field("Input", text_excerpt[:60] + ("…" if len(text_excerpt) > 60 else ""))
    divider()

    if not errors:
        success("No issues found.")
        severity_summary(0, 0, 0)
        return

    high = medium = low = 0
    for e in errors:
        if e.severity == "HIGH":
            high += 1
        elif e.severity == "MEDIUM":
            medium += 1
        elif e.severity == "LOW":
            low += 1

        error(e.severity, e.claim, e.explanation)
        console.print(
            f"  {'':12}→ {e.correction}",
            style=__import__("rich.style", fromlist=["Style"]).Style(color=THEME["key"], italic=True),
        )
        for ev in e.evidence:
            placeholder("Evidence", ev)

    severity_summary(high, medium, low)


# ---------------------------------------------------------------------------
# Output files
# ---------------------------------------------------------------------------

def _write_report(errors: list[CheckerError], slug: str) -> None:
    out = Path("output") / slug
    out.mkdir(parents=True, exist_ok=True)

    # JSON
    data = [
        {
            "claim": e.claim,
            "error_type": e.error_type,
            "severity": e.severity,
            "explanation": e.explanation,
            "correction": e.correction,
            "evidence": e.evidence,
        }
        for e in errors
    ]
    (out / "fallacy_report.json").write_text(json.dumps(data, indent=2))

    # Markdown
    lines = ["# Fallacy & Fact Check Report\n"]
    if not errors:
        lines.append("No issues found.\n")
    else:
        for e in errors:
            lines += [
                f"\n## [{e.severity}] {e.error_type}",
                f"**Claim:** {e.claim}",
                f"**Explanation:** {e.explanation}",
                f"**Correction:** {e.correction}",
                f"**Evidence:** {', '.join(e.evidence)}\n",
            ]
    (out / "fallacy_report.md").write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_check(
    verbatim: str | None,
    file_path: str | None,
    chain: bool,
) -> None:
    # Resolve input text
    if chain:
        last = Path(".last_slug")
        if not last.exists():
            console.print("  No previous build. Run `build` first.", style=__import__("rich.style", fromlist=["Style"]).Style(color=THEME["error"]))
            return
        slug = last.read_text().strip()
        src = Path("output") / slug / "arguments.md"
        if not src.exists():
            console.print(f"  {src} not found.", style=__import__("rich.style", fromlist=["Style"]).Style(color=THEME["error"]))
            return
        text = src.read_text()
        output_slug = slug
    elif file_path:
        p = Path(file_path)
        if not p.exists():
            console.print(f"  File not found: {file_path}", style=__import__("rich.style", fromlist=["Style"]).Style(color=THEME["error"]))
            return
        text = p.read_text()
        output_slug = p.stem
    elif verbatim:
        text = verbatim
        output_slug = "verbatim-check"
    else:
        console.print("  Provide --verbatim, --file, or --chain.", style=__import__("rich.style", fromlist=["Style"]).Style(color=THEME["warn"]))
        return

    # Heuristic scan (fast, no API)
    heuristic_errors = _heuristic_scan(text)

    # LLM-powered deep scan
    raw_errors = _call_llm(text)
    claude_errors: list[CheckerError] = []
    for item in raw_errors:
        try:
            claude_errors.append(
                CheckerError(
                    claim=item["claim"],
                    error_type=item["error_type"],
                    severity=item["severity"],
                    explanation=item["explanation"],
                    correction=item["correction"],
                    evidence=item.get("evidence", []),
                )
            )
        except (KeyError, TypeError):
            continue

    # Merge — deduplicate by claim text
    seen: set[str] = set()
    all_errors: list[CheckerError] = []
    for e in claude_errors + heuristic_errors:
        if e.claim not in seen:
            seen.add(e.claim)
            all_errors.append(e)

    _render_report(all_errors, text)
    _write_report(all_errors, output_slug)
