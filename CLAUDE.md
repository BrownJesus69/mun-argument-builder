# CLAUDE.md — MUN Argument Builder

> Drop this file in your project root. Run `/init` at the start of every Claude Code session.

---

## Project Identity

| Field | Value |
|-------|-------|
| Name | MUN Argument Builder |
| Type | Local Python CLI |
| Purpose | MUN research · argument generation · fallacy checking · document export |
| Stack | Python · Typer · Rich · Anthropic SDK · python-dotenv · Jinja2 · SQLite |
| Theme | Arctic Steel |
| Font | JetBrains Mono or Cascadia Code |

---

## Absolute Rules

1. **Never hardcode API keys.** All keys load through `config.py` only.
2. **Never call `os.getenv()` outside `config.py`.**
3. **All file output goes to `output/{resolution_slug}/`** — never to project root.
4. **`output/` and `.env` are gitignored.** Never commit either.
5. All CLI subcommands use **Typer**. All terminal output uses **Rich** with Arctic Steel hex colors.
6. Every function must have a full type signature.
7. Graceful degradation: if any API is unavailable, fall back to placeholder mode — never crash.
8. Run `detect-secrets scan > .secrets.baseline` before first commit.

---

## Project Structure

```
mun-builder/
├── main.py                        # CLI entry point — Typer app
├── builder.py                     # Argument generation engine
├── config.py                      # ALL env var access — single source of truth
├── requirements.txt               # All dependencies pinned
├── CLAUDE.md                      # This file
├── themes/
│   └── arctic_steel.py            # Confirmed color palette
├── templates/
│   ├── seec_template.json         # SEEC argument block schema
│   └── position_paper.tex.j2      # Jinja2 LaTeX template
├── checker/
│   ├── fallacy_checker.py         # Core fallacy + fact analysis engine
│   ├── legal_reference_db.json    # UN resolutions, charter articles, treaties
│   ├── fallacy_patterns.json      # Logical fallacy pattern definitions
│   └── checker_output.py          # Rich-formatted error report renderer
├── research/
│   ├── country_profile.py         # Country stance + stats fetcher
│   └── evidence_resolver.py       # OpenAlex + Google Fact Check integration
├── output/                        # Gitignored — all generated files land here
└── .env                           # Gitignored — API keys only
```

---

## Environment Variables

```bash
# .env — never commit this file
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
# UNdata and OpenAlex require no keys
```

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

def get_key(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise EnvironmentError(f"Missing required env var: {name}")
    return val

ANTHROPIC_KEY = get_key("ANTHROPIC_API_KEY")
GOOGLE_KEY    = get_key("GOOGLE_API_KEY")
```

---

## CLI Subcommands

### `build` — Argument Generator

```bash
python main.py build \
  --resolution "AI development should be internationally regulated" \
  --country India \
  --stance for \
  --committee UNSC \
  --output-format markdown        # markdown | json | latex
```

Outputs:
- `output/{slug}/arguments.md`
- `output/{slug}/arguments.json`
- `output/{slug}/operative_clauses.md`

---

### `check` — Fallacy & Fact Checker

```bash
python main.py check --verbatim "Russia invoked Article 51 for preemptive action"
python main.py check --file speech_draft.txt
python main.py check --chain     # auto-checks last build output
```

Outputs:
- `output/{slug}/fallacy_report.md`
- `output/{slug}/fallacy_report.json`

---

### `research` — Country Profile

```bash
python main.py research --country India --topic "AI regulation"
```

Outputs:
- `output/{slug}/country_profile.md`

---

### `speech` — Time-boxed Speech Writer

```bash
python main.py speech --block 1 --duration 60
```

Output: Rewritten SEEC block trimmed to target word count, printed to terminal.

---

### `rebuttal` — Live Counter-argument

```bash
python main.py rebuttal --verbatim "India's stance contradicts its own tech growth"
```

Output: Instant structured counter printed to terminal. No file write.

---

### `draft` — Working Paper Generator

```bash
python main.py draft --input output/ai-regulation/arguments.json
```

Outputs:
- `output/{slug}/working_paper.md`
- `output/{slug}/working_paper.pdf` (via LaTeX)

---

### `export` — Format Converter

```bash
python main.py export --format latex    # latex | anki | pdf
```

---

## Argument Structure — SEEC Schema

Every argument block must conform to this exact structure:

```json
{
  "block_id": 1,
  "statement":   "A shared framework prevents compliance fragmentation.",
  "explanation": "Unilateral national frameworks create incompatible standards across jurisdictions.",
  "example": {
    "text": "IAEA safeguards model demonstrates dual-use governance works at scale.",
    "placeholder": true,
    "search_query": "IAEA safeguards model AI governance precedent"
  },
  "conclusion":  "India supports a UN framework modeled on IAEA's safeguards approach.",
  "confidence":  null
}
```

---

## CheckerError Dataclass

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class CheckerError:
    claim:       str
    error_type:  str                                          # e.g. "Legal Misapplication"
    severity:    Literal["HIGH", "MEDIUM", "LOW", "INFO"]
    explanation: str
    correction:  str
    evidence:    list[str]                                    # search queries or DOIs
```

Severity logic:

| Level | Trigger |
|-------|---------|
| HIGH | Directly contradicts cited law or inverts factual data |
| MEDIUM | Partially correct but missing key qualifier or context |
| LOW | Weak phrasing, hasty generalisation, unverified stat |
| INFO | Stylistic — not an error, but improvable |

---

## API Integrations

| API | Key Required | Env Var | Fallback |
|-----|-------------|---------|----------|
| Anthropic | Yes | `ANTHROPIC_API_KEY` | Raise `EnvironmentError` |
| Google Fact Check | Yes | `GOOGLE_API_KEY` | Skip, output placeholder |
| OpenAlex | No | — | Skip, output placeholder |
| UNdata REST | No | — | Skip, output placeholder |
| UNDP Data | No | — | Skip, output placeholder |

---

## Arctic Steel Theme — `themes/arctic_steel.py`

```python
THEME = {
    "header":  "#7eb8f7",   # sky blue    — section titles, country name
    "key":     "#9dd9c5",   # ice teal    — field labels
    "value":   "#d4dde8",   # steel white — body text
    "warn":    "#f4c542",   # amber       — MEDIUM severity
    "error":   "#ff7e7e",   # salmon red  — HIGH severity
    "dim":     "#3a4a5e",   # slate       — dividers, placeholders
    "success": "#9dd9c5",   # ice teal    — verified facts
    "info":    "#7eb8f7",   # sky blue    — INFO suggestions
}

DESIGNED_FOR_BG = "#0d1117"   # GitHub Dark / Default Dark+
```

Best VS Code themes: **Tokyo Night · Default Dark+ · One Dark Pro**

---

## checker_output.py — Full Implementation

```python
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
    color = THEME["error"] if severity == "HIGH" else             THEME["warn"]  if severity == "MEDIUM" else THEME["info"]
    icon  = "✕" if severity == "HIGH" else "⚠" if severity == "MEDIUM" else "·"
    console.print(f"\n  {icon} {severity:<8}", style=Style(color=color, bold=True), end="")
    console.print(f" {claim}", style=Style(color=THEME["value"]))
    console.print(f"  {'':12}{message}", style=Style(color=THEME["dim"], italic=True))

def success(message: str) -> None:
    console.print(f"  ✓  {message}", style=Style(color=THEME["success"], bold=True))

def severity_summary(high: int, medium: int, low: int) -> None:
    divider()
    console.print("  SEVERITY SUMMARY", style=Style(color=THEME["header"], bold=True))
    console.print(f"  {'HIGH':<10} {high}",    style=Style(color=THEME["error"], bold=True))
    console.print(f"  {'MEDIUM':<10} {medium}", style=Style(color=THEME["warn"],  bold=True))
    console.print(f"  {'LOW':<10} {low}",       style=Style(color=THEME["info"],  bold=True))
    console.print()
```

---

## Legal Reference DB — `checker/legal_reference_db.json`

Pre-seed with these entries minimum:

```json
{
  "UN_CHARTER_ART_51": {
    "summary": "Inherent right of individual or collective self-defence if an armed attack occurs.",
    "common_misuse": "Invoked to justify preemptive strikes. Article 51 does NOT authorise anticipatory self-defence."
  },
  "UN_CHARTER_ART_42": {
    "summary": "Security Council may take military action to maintain or restore international peace.",
    "common_misuse": "Confused with Article 51. Art 42 is collective SC enforcement action, not individual self-defence."
  },
  "UNSC_RES_1373": {
    "year": 2001,
    "topic": "Counter-terrorism obligations post-9/11.",
    "common_misuse": "Cited as general security justification in non-terrorism contexts."
  },
  "UNSC_RES_2231": {
    "year": 2015,
    "topic": "Endorses JCPOA — Iran nuclear deal.",
    "common_misuse": "Cited as blanket nuclear non-proliferation mandate. Scope is Iran-specific."
  },
  "PARIS_AGREEMENT": {
    "year": 2015,
    "signatories": 196,
    "common_misuse": "NDC targets cited as legally binding. They are nationally determined and not internationally enforceable."
  },
  "UDHR_ART_19": {
    "summary": "Right to freedom of opinion and expression.",
    "common_misuse": "Cited to block platform content moderation. Art 19 binds states, not private entities."
  },
  "ICCPR_ART_6": {
    "summary": "Inherent right to life. No one arbitrarily deprived of life.",
    "common_misuse": "Cited to oppose capital punishment universally — ICCPR restricts but does not abolish it."
  },
  "UNCLOS_ART_121": {
    "summary": "Islands generate full maritime entitlements; rocks sustaining no habitation generate only territorial sea.",
    "common_misuse": "All land features cited as islands with full EEZ rights regardless of habitability."
  }
}
```

---

## requirements.txt

```
anthropic>=0.25.0
typer[all]>=0.12.0
rich>=13.7.0
python-dotenv>=1.0.0
jinja2>=3.1.0
requests>=2.31.0
detect-secrets>=1.4.0
```

---

## .gitignore

```
.env
.env.*
__pycache__/
*.pyc
*.pyo
.secrets.baseline
output/
*.egg-info/
dist/
.DS_Store
```

---

## Build Order

| Session | Focus | Deliverable |
|---------|-------|-------------|
| 0 | Manual bootstrap | `git init`, `.gitignore`, `.env`, `code .` |
| 1 | Full scaffold | All files/folders, boilerplate, `requirements.txt` |
| 2 | `builder.py` | Working `build` subcommand with SEEC JSON + Markdown output |
| 3 | `checker/` | Working `check` subcommand with fallacy + fact report |
| 4 | Wire + test | `--chain` flag, end-to-end run on sample resolution |
| 5 | `speech` + `rebuttal` | Live in-session tools, no file write |
| 6 | `research/` | Country profile + OpenAlex + Google Fact Check |
| 7 | `draft` + `export` | Working paper generator + LaTeX/Anki export |

---

## Validation Test — Run After Session 2

```bash
python main.py build \
  --resolution "This house believes AI development should be internationally regulated" \
  --country India \
  --stance for \
  --committee UNSC \
  --output-format markdown
```

Expected output files:
- `output/this-house-believes-ai-development/arguments.md`
- `output/this-house-believes-ai-development/arguments.json`
- `output/this-house-believes-ai-development/operative_clauses.md`

If all three files exist and `arguments.json` contains 3 SEEC blocks with no null fields except `confidence`, Session 2 is complete.
