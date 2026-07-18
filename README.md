# MUN Argument Builder

A tool for building Model UN (MUN) arguments: it generates SEEC-structured
(Statement, Explanation, Example, Conclusion) argument blocks for a
resolution, checks speeches and arguments for logical fallacies and factual
issues, researches a country's stance on a topic, and exports the results as
Markdown, JSON, or LaTeX working papers. It's powered by the Groq API.

There are two ways to use it, and both are real, functioning entry points:

- **`main.py`** — a Typer-based command-line tool.
- **`api/server.py`** — a FastAPI web server backing `mun_webapp.html`, a
  browser-based front end.

## Project structure

```
main.py                    # CLI entry point (Typer app)
api/server.py               # FastAPI web app + REST endpoints
builder.py                  # Argument generation engine (shared by CLI + API)
config.py                   # All environment variable access
llm.py                      # Groq API client wrapper
checker/                    # Fallacy checking + legal reference data
research/                   # Country profile + evidence resolution
themes/                     # Terminal color theme (Arctic Steel)
templates/                  # SEEC schema + LaTeX (Jinja2) templates
mun_webapp.html              # Front end served by api/server.py
```

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your values:

   ```bash
   cp .env.example .env
   ```

   Required and optional environment variables (all loaded through
   `config.py`):

   | Variable | Required | Purpose |
   |----------|----------|---------|
   | `GROQ_API_KEY` | Yes | Groq API key used for all argument/rebuttal/check generation |
   | `GOOGLE_API_KEY` | No | Enables Google Fact Check integration in `research`; skipped if unset |

## Running the CLI

```bash
python main.py build --resolution "AI development should be internationally regulated" \
  --country India --stance for --committee UNSC --output-format markdown

python main.py check --verbatim "Russia invoked Article 51 for preemptive action"
python main.py research --country India --topic "AI regulation"
python main.py speech --block 1 --duration 60
python main.py rebuttal --verbatim "India's stance contradicts its own tech growth"
python main.py draft --input output/<slug>/arguments.json
python main.py export --format latex
```

Run `python main.py --help` or `python main.py <command> --help` for the full
list of options. Generated files are written to `output/{resolution_slug}/`.

## Running the web app

```bash
uvicorn api.server:app --reload --port 8000
```

Then open `http://localhost:8000` (the server serves `mun_webapp.html`
directly). Alternatively, `run.sh` starts the API server and opens the page
for you.

The web app exposes the same functionality as the CLI over a REST API
(`/api/build`, `/api/check`, `/api/rebuttal`, `/api/research`,
`/api/health`).

## Deployment

A `Procfile` is included for platforms that use one (e.g. Heroku-style
buildpacks):

```
web: uvicorn api.server:app --host 0.0.0.0 --port $PORT
```
