"""MUN Argument Builder — argument generation engine."""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any

import requests
from rich.console import Console
from rich.style import Style
from rich.text import Text

import config
from themes.arctic_steel import THEME

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LAST_SLUG_FILE = Path(".last_slug")
_WORDS_PER_SECOND = 2.5  # ~150 wpm


def _slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:60]


def _output_dir(slug: str) -> Path:
    path = Path("output") / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_last_slug(slug: str) -> None:
    _LAST_SLUG_FILE.write_text(slug)


def _load_last_slug() -> str | None:
    if _LAST_SLUG_FILE.exists():
        return _LAST_SLUG_FILE.read_text().strip()
    return None


def _call_llm(system: str, user: str, json_format: bool = False) -> str:
    prompt = f"{system}\n\n{user}"
    payload: dict = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if json_format:
        payload["format"] = "json"
    try:
        resp = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except requests.ConnectionError:
        console.print(
            "  Ollama not reachable. Run: ollama serve",
            style=Style(color=THEME["error"]),
        )
        return ""
    except Exception as exc:  # noqa: BLE001
        console.print(
            f"  [PLACEHOLDER] LLM unavailable: {exc}",
            style=Style(color=THEME["dim"], italic=True),
        )
        return ""


# ---------------------------------------------------------------------------
# SEEC block schema
# ---------------------------------------------------------------------------

_SEEC_SYSTEM = textwrap.dedent("""\
    You are an expert MUN coach. Produce structured arguments in the SEEC format:
    Statement → Explanation → Example → Conclusion.

    Always respond with a JSON array of exactly 3 objects, each with these exact keys:
    block_id (int), statement (str), explanation (str),
    example (object with keys: text, placeholder (bool), search_query (str)),
    conclusion (str), confidence (null).

    Ensure every argument is factually grounded, legally accurate, and diplomatically persuasive.
    Do NOT add markdown fencing around the JSON — output raw JSON only.
""")


def _build_seec_prompt(resolution: str, country: str, stance: str, committee: str) -> str:
    return (
        f"Resolution: {resolution}\n"
        f"Country: {country}\n"
        f"Stance: {stance}\n"
        f"Committee: {committee}\n\n"
        "Generate 3 distinct SEEC argument blocks. Each must advance a different strategic angle."
    )


def _parse_seec_json(raw: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Try to extract JSON array from mixed output
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return []


def _placeholder_seec(resolution: str, country: str, stance: str) -> list[dict[str, Any]]:
    return [
        {
            "block_id": i,
            "statement": f"[PLACEHOLDER] Argument {i} for {country} ({stance})",
            "explanation": "Claude API unavailable — fill in manually.",
            "example": {
                "text": "",
                "placeholder": True,
                "search_query": f"{country} {resolution[:40]}",
            },
            "conclusion": "[PLACEHOLDER] Conclusion.",
            "confidence": None,
        }
        for i in range(1, 4)
    ]


# ---------------------------------------------------------------------------
# Operative clauses
# ---------------------------------------------------------------------------

_OPERATIVE_SYSTEM = textwrap.dedent("""\
    You are an expert MUN coach. Given a country's SEEC arguments, produce 5 operative clauses
    for a working paper. Use standard MUN operative verbs (Urges, Calls upon, Encourages, etc.).
    Return a markdown numbered list only — no preamble text.
""")


# ---------------------------------------------------------------------------
# build_arguments
# ---------------------------------------------------------------------------

def build_arguments(
    resolution: str,
    country: str,
    stance: str,
    committee: str,
    output_format: str,
) -> None:
    slug = _slugify(resolution)
    out = _output_dir(slug)
    _save_last_slug(slug)

    console.print()
    console.print(f"  Building arguments for [bold]{country}[/bold] · {committee}", style=Style(color=THEME["header"]))
    console.print(f"  Resolution: {resolution[:70]}{'…' if len(resolution) > 70 else ''}", style=Style(color=THEME["dim"]))
    console.rule(style=Style(color=THEME["dim"]))

    # Generate SEEC blocks
    raw = _call_llm(
        system=_SEEC_SYSTEM,
        user=_build_seec_prompt(resolution, country, stance, committee),
        json_format=True,
    )

    blocks: list[dict[str, Any]] = _parse_seec_json(raw) if raw else []
    if not blocks:
        console.print("  Using placeholder SEEC blocks.", style=Style(color=THEME["warn"]))
        blocks = _placeholder_seec(resolution, country, stance)

    # Generate operative clauses
    operative_raw = _call_llm(
        system=_OPERATIVE_SYSTEM,
        user=f"Country: {country}\nStance: {stance}\nArguments:\n{json.dumps(blocks, indent=2)}",
    )
    if not operative_raw:
        operative_raw = "\n".join(
            f"{i}. [PLACEHOLDER] Operative clause {i}." for i in range(1, 6)
        )

    # Write JSON
    json_path = out / "arguments.json"
    json_path.write_text(json.dumps(blocks, indent=2))

    # Write Markdown
    md_lines: list[str] = [
        f"# Arguments: {country} — {resolution[:60]}\n",
        f"**Committee:** {committee} | **Stance:** {stance}\n",
    ]
    for b in blocks:
        md_lines += [
            f"\n## Block {b['block_id']}\n",
            f"**Statement:** {b['statement']}\n",
            f"**Explanation:** {b['explanation']}\n",
            f"**Example:** {b['example']['text'] or '[placeholder — ' + b['example']['search_query'] + ']'}\n",
            f"**Conclusion:** {b['conclusion']}\n",
        ]
    md_path = out / "arguments.md"
    md_path.write_text("\n".join(md_lines))

    # Write operative clauses
    op_path = out / "operative_clauses.md"
    op_path.write_text(f"# Operative Clauses: {country}\n\n{operative_raw}\n")

    console.print(f"  ✓  arguments.json", style=Style(color=THEME["success"], bold=True))
    console.print(f"  ✓  arguments.md", style=Style(color=THEME["success"], bold=True))
    console.print(f"  ✓  operative_clauses.md", style=Style(color=THEME["success"], bold=True))
    console.print(f"\n  Output → output/{slug}/", style=Style(color=THEME["key"]))
    console.print()


# ---------------------------------------------------------------------------
# rewrite_speech_block
# ---------------------------------------------------------------------------

def rewrite_speech_block(block: int, duration: int) -> None:
    slug = _load_last_slug()
    if not slug:
        console.print("  No previous build found. Run `build` first.", style=Style(color=THEME["error"]))
        raise typer.Exit(1)

    json_path = Path("output") / slug / "arguments.json"
    if not json_path.exists():
        console.print(f"  arguments.json not found at {json_path}", style=Style(color=THEME["error"]))
        raise typer.Exit(1)

    blocks: list[dict[str, Any]] = json.loads(json_path.read_text())
    target = next((b for b in blocks if b["block_id"] == block), None)
    if not target:
        console.print(f"  Block {block} not found.", style=Style(color=THEME["error"]))
        raise typer.Exit(1)

    target_words = int(duration * _WORDS_PER_SECOND)

    system = (
        "You are a MUN speech coach. Rewrite the given SEEC block as a spoken speech "
        f"of approximately {target_words} words ({duration} seconds). "
        "Preserve all key arguments. Output the speech text only."
    )
    result = _call_llm(system=system, user=json.dumps(target, indent=2))

    console.print()
    console.print(f"  Speech Block {block} (~{duration}s / ~{target_words} words)", style=Style(color=THEME["header"], bold=True))
    console.rule(style=Style(color=THEME["dim"]))
    console.print(result or "[PLACEHOLDER — Claude unavailable]", style=Style(color=THEME["value"]))
    console.print()


# ---------------------------------------------------------------------------
# generate_rebuttal
# ---------------------------------------------------------------------------

def generate_rebuttal(verbatim: str) -> None:
    system = textwrap.dedent("""\
        You are a MUN debate coach. Given a statement from a delegate, produce a structured rebuttal:
        1. Identify the core claim.
        2. Point out the logical or factual flaw.
        3. Offer a counter-argument with a supporting example.
        4. Conclude with a redirect to your position.
        Be direct and concise — this is a live debate. Plain text, no markdown headers.
    """)
    result = _call_llm(system=system, user=f'Statement to rebut: "{verbatim}"')

    console.print()
    console.print("  Rebuttal", style=Style(color=THEME["header"], bold=True))
    console.rule(style=Style(color=THEME["dim"]))
    console.print(result or "[PLACEHOLDER — Claude unavailable]", style=Style(color=THEME["value"]))
    console.print()


# ---------------------------------------------------------------------------
# generate_working_paper
# ---------------------------------------------------------------------------

def generate_working_paper(input_path: str) -> None:
    from jinja2 import Environment, FileSystemLoader

    p = Path(input_path)
    if not p.exists():
        console.print(f"  File not found: {input_path}", style=Style(color=THEME["error"]))
        raise typer.Exit(1)

    blocks: list[dict[str, Any]] = json.loads(p.read_text())
    slug = p.parent.name
    out = _output_dir(slug)

    env = Environment(loader=FileSystemLoader("templates"), autoescape=False)
    try:
        tmpl = env.get_template("position_paper.tex.j2")
        latex = tmpl.render(blocks=blocks, slug=slug)
        tex_path = out / "working_paper.tex"
        tex_path.write_text(latex)
        console.print(f"  ✓  working_paper.tex", style=Style(color=THEME["success"], bold=True))
    except Exception as exc:  # noqa: BLE001
        console.print(f"  LaTeX render skipped: {exc}", style=Style(color=THEME["warn"]))

    # Markdown fallback always written
    md_lines = ["# Working Paper\n"]
    for b in blocks:
        md_lines += [
            f"\n### Clause {b['block_id']}\n",
            f"{b['conclusion']}\n",
        ]
    md_path = out / "working_paper.md"
    md_path.write_text("\n".join(md_lines))
    console.print(f"  ✓  working_paper.md", style=Style(color=THEME["success"], bold=True))


# ---------------------------------------------------------------------------
# export_output
# ---------------------------------------------------------------------------

def export_output(format: str) -> None:
    slug = _load_last_slug()
    if not slug:
        console.print("  No previous build found. Run `build` first.", style=Style(color=THEME["error"]))
        raise typer.Exit(1)

    if format == "anki":
        _export_anki(slug)
    elif format in ("latex", "pdf"):
        json_path = Path("output") / slug / "arguments.json"
        generate_working_paper(str(json_path))
    else:
        console.print(f"  Unknown format: {format}", style=Style(color=THEME["error"]))
        raise typer.Exit(1)


def _export_anki(slug: str) -> None:
    json_path = Path("output") / slug / "arguments.json"
    if not json_path.exists():
        console.print(f"  arguments.json not found.", style=Style(color=THEME["error"]))
        raise typer.Exit(1)

    blocks: list[dict[str, Any]] = json.loads(json_path.read_text())
    lines = ["#separator:tab", "#html:false", "Front\tBack"]
    for b in blocks:
        front = b["statement"].replace("\t", " ")
        back = f"{b['explanation']} | {b['conclusion']}".replace("\t", " ")
        lines.append(f"{front}\t{back}")

    out = _output_dir(slug)
    anki_path = out / "arguments.anki.txt"
    anki_path.write_text("\n".join(lines))
    console.print(f"  ✓  arguments.anki.txt", style=Style(color=THEME["success"], bold=True))


# ---------------------------------------------------------------------------
# Needed for speech subcommand exit
# ---------------------------------------------------------------------------
import typer  # noqa: E402 (re-import for Exit usage inside functions above)
