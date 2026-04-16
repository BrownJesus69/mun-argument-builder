"""Rich-formatted error report renderer for the MUN fallacy/fact checker."""

from __future__ import annotations

from rich.console import Console
from rich.style import Style
from rich.text import Text

from themes.arctic_steel import THEME

console = Console()


def divider(label: str = "") -> None:
    if label:
        console.rule(f"[bold]{label}[/bold]", style=Style(color=THEME["dim"]))
    else:
        console.print("  " + "─" * 47, style=Style(color=THEME["dim"]))


def header(title: str) -> None:
    console.print()
    console.print(f"  {title}", style=Style(color=THEME["header"], bold=True))
    divider()


def field(key: str, value: str, faint: bool = False) -> None:
    t = Text()
    t.append(f"  {key:<14}", style=Style(color=THEME["key"], bold=True))
    t.append(value, style=Style(color=THEME["dim"] if faint else THEME["value"], italic=faint))
    console.print(t)


def placeholder(label: str, query: str) -> None:
    t = Text()
    t.append("  [ PLACEHOLDER ]  ", style=Style(color=THEME["dim"], bold=True))
    t.append(f'{label} — Search: "{query}"', style=Style(color=THEME["dim"], italic=True))
    console.print(t)


def error(severity: str, claim: str, message: str) -> None:
    color = (
        THEME["error"] if severity == "HIGH"
        else THEME["warn"] if severity == "MEDIUM"
        else THEME["info"]
    )
    icon = "✗" if severity == "HIGH" else "⚠" if severity == "MEDIUM" else "·"
    console.print(
        f"\n  {icon} {severity:<8}",
        style=Style(color=color, bold=True),
        end="",
    )
    console.print(f" {claim}", style=Style(color=THEME["value"]))
    console.print(
        f"  {'':12}{message}",
        style=Style(color=THEME["dim"], italic=True),
    )


def success(message: str) -> None:
    console.print(f"  ✓  {message}", style=Style(color=THEME["success"], bold=True))


def severity_summary(high: int, medium: int, low: int) -> None:
    divider()
    console.print("  SEVERITY SUMMARY", style=Style(color=THEME["header"], bold=True))
    console.print(f"  {'HIGH':<10} {high}", style=Style(color=THEME["error"], bold=True))
    console.print(f"  {'MEDIUM':<10} {medium}", style=Style(color=THEME["warn"], bold=True))
    console.print(f"  {'LOW':<10} {low}", style=Style(color=THEME["info"], bold=True))
    console.print()
