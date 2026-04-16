"""FastAPI server — MUN Argument Builder API."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from builder import generate_argument_pack, generate_rebuttal, slugify, save_output
from checker.fallacy_checker import check_verbatim
from research.country_profile import get_profile
from config import check_groq, GOOGLE_API_KEY
from research.evidence_resolver import resolve_evidence, fact_check

app = FastAPI(title="MUN Argument Builder", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class BuildRequest(BaseModel):
    resolution: str
    country: str
    stance: str
    committee: str = "UNSC"
    output_format: str = "markdown"


class CheckRequest(BaseModel):
    verbatim: str


class RebuttalRequest(BaseModel):
    verbatim: str
    country: str = "India"


class ResearchRequest(BaseModel):
    country: str
    topic: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": "llama-3.1-8b-instant", "groq": check_groq()}


@app.post("/api/build")
def build(req: BuildRequest) -> dict:
    try:
        data = generate_argument_pack(req.resolution, req.country, req.stance, req.committee)
        slug = slugify(req.resolution)
        save_output(slug, "arguments.json", json.dumps(data, indent=2))
        return {"success": True, "slug": slug, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/check")
def check(req: CheckRequest) -> dict:
    try:
        result = check_verbatim(req.verbatim)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rebuttal")
def rebuttal(req: RebuttalRequest) -> dict:
    try:
        data = generate_rebuttal(req.verbatim, req.country)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/research")
def research(req: ResearchRequest) -> dict:
    try:
        profile = get_profile(req.country, req.topic)
        evidence = resolve_evidence(f"{req.country} {req.topic} UN policy")
        fc = fact_check(f"{req.country} {req.topic}", GOOGLE_API_KEY)
        return {"success": True, "data": {"profile": profile, "evidence": evidence, "fact_checks": fc}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
