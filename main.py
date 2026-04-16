"""MUN Argument Builder — CLI entry point."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.style import Style

import config

app = typer.Typer(
    name="mun-builder",
    help="MUN research · argument generation · fallacy checking · document export",
    add_completion=False,
)
console = Console()


@app.callback()
def _startup() -> None:
    """MUN research · argument generation · fallacy checking · document export"""
    if not config.check_groq():
        console.print(
            "  Groq API is not reachable. Check your GROQ_API_KEY in .env",
            style=Style(color="#ff7e7e"),
        )
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

@app.command()
def build(
    resolution: str = typer.Option(..., "--resolution", "-r", help="Full resolution text"),
    country: str = typer.Option(..., "--country", "-c", help="Country you represent"),
    stance: str = typer.Option(..., "--stance", "-s", help="'for' or 'against'"),
    committee: str = typer.Option("UNGA", "--committee", help="Committee name (e.g. UNSC, UNGA)"),
    output_format: str = typer.Option("markdown", "--output-format", "-f", help="markdown | json | latex"),
) -> None:
    """Generate SEEC-structured arguments for a resolution."""
    from builder import build_arguments
    build_arguments(resolution=resolution, country=country, stance=stance, committee=committee, output_format=output_format)


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

@app.command()
def check(
    verbatim: Optional[str] = typer.Option(None, "--verbatim", "-v", help="Inline text to check"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to a text file to check"),
    chain: bool = typer.Option(False, "--chain", help="Auto-check last build output"),
) -> None:
    """Run fallacy and fact checks on a speech or argument."""
    from checker.fallacy_checker import run_check
    run_check(verbatim=verbatim, file_path=file, chain=chain)


# ---------------------------------------------------------------------------
# research
# ---------------------------------------------------------------------------

@app.command()
def research(
    country: str = typer.Option(..., "--country", "-c", help="Country to profile"),
    topic: str = typer.Option(..., "--topic", "-t", help="Topic or resolution theme"),
) -> None:
    """Fetch country stance, stats, and policy positions."""
    from research.country_profile import fetch_profile
    fetch_profile(country=country, topic=topic)


# ---------------------------------------------------------------------------
# speech
# ---------------------------------------------------------------------------

@app.command()
def speech(
    block: int = typer.Option(..., "--block", "-b", help="SEEC block number (1-based)"),
    duration: int = typer.Option(60, "--duration", "-d", help="Target speech duration in seconds"),
) -> None:
    """Rewrite a SEEC block trimmed to a time-boxed word count."""
    from builder import rewrite_speech_block
    rewrite_speech_block(block=block, duration=duration)


# ---------------------------------------------------------------------------
# rebuttal
# ---------------------------------------------------------------------------

@app.command()
def rebuttal(
    verbatim: str = typer.Option(..., "--verbatim", "-v", help="Statement to rebut"),
    country: str = typer.Option("India", "--country", "-c", help="Your country"),
) -> None:
    """Generate a live structured counter-argument (no file write)."""
    from builder import generate_rebuttal_cli
    generate_rebuttal_cli(verbatim=verbatim, country=country)


# ---------------------------------------------------------------------------
# draft
# ---------------------------------------------------------------------------

@app.command()
def draft(
    input: str = typer.Option(..., "--input", "-i", help="Path to arguments.json"),
) -> None:
    """Generate a working paper from an arguments JSON file."""
    from builder import generate_working_paper
    generate_working_paper(input_path=input)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@app.command()
def export(
    format: str = typer.Option(..., "--format", "-f", help="latex | anki | pdf"),
) -> None:
    """Convert last build output to an alternate format."""
    from builder import export_output
    export_output(format=format)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
