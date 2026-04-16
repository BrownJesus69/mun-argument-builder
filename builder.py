"""MUN Argument Builder — argument generation engine."""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.style import Style

from llm import call_llm, call_llm_json
from themes.arctic_steel import COLORS as THEME

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LAST_SLUG_FILE = Path(".last_slug")
_WORDS_PER_SECOND = 2.5  # ~150 wpm


def slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:60]


def save_output(slug: str, filename: str, content: str) -> str:
    out = Path("output") / slug
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    path.write_text(content)
    return str(path)


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


# ---------------------------------------------------------------------------
# generate_argument_pack
# ---------------------------------------------------------------------------

_SEEC_PROMPT_TEMPLATE = textwrap.dedent("""\
    You are an expert MUN coach. Generate a complete argument pack for the following:

    Resolution: {resolution}
    Country: {country}
    Stance: {stance}
    Committee: {committee}

    Return a JSON object with exactly these keys:
    - "blocks": a list of exactly 3 SEEC argument objects, each with keys:
        "id" (int), "statement" (str), "explanation" (str),
        "example" (object with keys "text" (str) and "search_query" (str)),
        "conclusion" (str)
    - "operative_clauses": a list of exactly 5 strings, each starting with a standard
      UN operative verb (Urges, Calls upon, Encourages, Recommends, Affirms, etc.)

    Each block must advance a different strategic angle. Be factually grounded and diplomatically persuasive.
""")


def generate_argument_pack(
    resolution: str, country: str, stance: str, committee: str
) -> dict:
    prompt = _SEEC_PROMPT_TEMPLATE.format(
        resolution=resolution,
        country=country,
        stance=stance,
        committee=committee,
    )
    return call_llm_json(prompt)


# ---------------------------------------------------------------------------
# generate_rebuttal
# ---------------------------------------------------------------------------

_REBUTTAL_PROMPT_TEMPLATE = textwrap.dedent("""\
    You are a MUN debate coach. Given the following statement, generate a structured rebuttal
    from the perspective of {country}.

    Statement: "{verbatim}"

    Return a JSON object with exactly these keys:
    - "point_of_info": str — a concise point of information request
    - "rebuttal_angles": list of exactly 2 objects, each with:
        "angle" (str): the strategic angle being attacked
        "response" (str): the counter-argument
    - "evidence_hook": str — a compelling evidence reference or statistic to anchor the rebuttal
    - "search_query": str — a search query to find supporting evidence

    Be direct and concise — this is a live debate.
""")


def generate_rebuttal(verbatim: str, country: str) -> dict:
    prompt = _REBUTTAL_PROMPT_TEMPLATE.format(verbatim=verbatim, country=country)
    return call_llm_json(prompt)


# ---------------------------------------------------------------------------
# generate_speech
# ---------------------------------------------------------------------------

_SPEECH_PROMPT_TEMPLATE = textwrap.dedent("""\
    You are a MUN speech coach. Rewrite the following SEEC argument block as a spoken speech
    of approximately {target_words} words ({duration_seconds} seconds at 150 wpm).

    Preserve all key arguments. Output the speech text only — no labels, no headers.

    SEEC Block:
    {block_json}
""")


def generate_speech(block: dict, duration_seconds: int) -> str:
    target_words = int(duration_seconds / 60 * 150)
    prompt = _SPEECH_PROMPT_TEMPLATE.format(
        target_words=target_words,
        duration_seconds=duration_seconds,
        block_json=json.dumps(block, indent=2),
    )
    return call_llm(prompt)


# ---------------------------------------------------------------------------
# build_arguments  (CLI entry point — keeps existing Rich output)
# ---------------------------------------------------------------------------

def build_arguments(
    resolution: str,
    country: str,
    stance: str,
    committee: str,
    output_format: str,
) -> None:
    slug = slugify(resolution)
    out = _output_dir(slug)
    _save_last_slug(slug)

    console.print()
    console.print(
        f"  Building arguments for [bold]{country}[/bold] · {committee}",
        style=Style(color=THEME["header"]),
    )
    console.print(
        f"  Resolution: {resolution[:70]}{'…' if len(resolution) > 70 else ''}",
        style=Style(color=THEME["dim"]),
    )
    console.rule(style=Style(color=THEME["dim"]))

    data = generate_argument_pack(resolution, country, stance, committee)

    blocks: list[dict[str, Any]] = data.get("blocks", [])
    operative_clauses: list[str] = data.get("operative_clauses", [])

    if not blocks:
        console.print("  No blocks returned — check LLM output.", style=Style(color=THEME["warn"]))

    # Write JSON
    json_path = out / "arguments.json"
    json_path.write_text(json.dumps(data, indent=2))

    # Write Markdown
    md_lines: list[str] = [
        f"# Arguments: {country} — {resolution[:60]}\n",
        f"**Committee:** {committee} | **Stance:** {stance}\n",
    ]
    for b in blocks:
        example = b.get("example", {})
        md_lines += [
            f"\n## Block {b.get('id', '?')}\n",
            f"**Statement:** {b.get('statement', '')}\n",
            f"**Explanation:** {b.get('explanation', '')}\n",
            f"**Example:** {example.get('text') or '[search: ' + example.get('search_query', '') + ']'}\n",
            f"**Conclusion:** {b.get('conclusion', '')}\n",
        ]
    md_path = out / "arguments.md"
    md_path.write_text("\n".join(md_lines))

    # Write operative clauses
    op_lines = [f"{i+1}. {clause}" for i, clause in enumerate(operative_clauses)]
    op_path = out / "operative_clauses.md"
    op_path.write_text(f"# Operative Clauses: {country}\n\n" + "\n".join(op_lines) + "\n")

    console.print(f"  ✓  arguments.json", style=Style(color=THEME["success"], bold=True))
    console.print(f"  ✓  arguments.md", style=Style(color=THEME["success"], bold=True))
    console.print(f"  ✓  operative_clauses.md", style=Style(color=THEME["success"], bold=True))
    console.print(f"\n  Output → output/{slug}/", style=Style(color=THEME["key"]))
    console.print()


# ---------------------------------------------------------------------------
# rewrite_speech_block  (CLI entry point)
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

    data: dict = json.loads(json_path.read_text())
    blocks: list[dict] = data.get("blocks", data) if isinstance(data, dict) else data
    target = next((b for b in blocks if b.get("id") == block or b.get("block_id") == block), None)
    if not target:
        console.print(f"  Block {block} not found.", style=Style(color=THEME["error"]))
        raise typer.Exit(1)

    result = generate_speech(target, duration)
    target_words = int(duration / 60 * 150)

    console.print()
    console.print(
        f"  Speech Block {block} (~{duration}s / ~{target_words} words)",
        style=Style(color=THEME["header"], bold=True),
    )
    console.rule(style=Style(color=THEME["dim"]))
    console.print(result, style=Style(color=THEME["value"]))
    console.print()


# ---------------------------------------------------------------------------
# generate_rebuttal_cli  (CLI entry point — prints, no file write)
# ---------------------------------------------------------------------------

def generate_rebuttal_cli(verbatim: str, country: str = "India") -> None:
    data = generate_rebuttal(verbatim, country)

    console.print()
    console.print("  Rebuttal", style=Style(color=THEME["header"], bold=True))
    console.rule(style=Style(color=THEME["dim"]))
    poi = data.get("point_of_info", "")
    if poi:
        console.print(f"  Point of Info: {poi}", style=Style(color=THEME["key"]))
    for angle in data.get("rebuttal_angles", []):
        console.print(f"\n  [{angle.get('angle', '')}]", style=Style(color=THEME["warn"], bold=True))
        console.print(f"  {angle.get('response', '')}", style=Style(color=THEME["value"]))
    hook = data.get("evidence_hook", "")
    if hook:
        console.print(f"\n  Evidence: {hook}", style=Style(color=THEME["success"]))
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

    raw = json.loads(p.read_text())
    blocks: list[dict[str, Any]] = raw.get("blocks", raw) if isinstance(raw, dict) else raw
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

    md_lines = ["# Working Paper\n"]
    for b in blocks:
        md_lines += [
            f"\n### Clause {b.get('id', b.get('block_id', '?'))}\n",
            f"{b.get('conclusion', '')}\n",
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

    raw = json.loads(json_path.read_text())
    blocks: list[dict[str, Any]] = raw.get("blocks", raw) if isinstance(raw, dict) else raw
    lines = ["#separator:tab", "#html:false", "Front\tBack"]
    for b in blocks:
        front = b.get("statement", "").replace("\t", " ")
        back = f"{b.get('explanation', '')} | {b.get('conclusion', '')}".replace("\t", " ")
        lines.append(f"{front}\t{back}")

    out = _output_dir(slug)
    anki_path = out / "arguments.anki.txt"
    anki_path.write_text("\n".join(lines))
    console.print(f"  ✓  arguments.anki.txt", style=Style(color=THEME["success"], bold=True))
