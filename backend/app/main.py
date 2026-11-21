"""SchemeSaathi API + static demo UI.   Run:  uvicorn app.main:app --reload"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import engine, parser, scam

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="SchemeSaathi", version="0.1.0")


class ParseIn(BaseModel):
    text: str = Field(max_length=2000)


class MatchIn(BaseModel):
    profile: dict
    include_not_eligible: bool = False


class FamilyIn(BaseModel):
    household: dict = {}
    members: list[dict] = Field(min_length=1, max_length=12)


class ScamIn(BaseModel):
    text: str = Field(max_length=4000)


@app.get("/api/health")
def health():
    return {"ok": True, "schemes": len(engine.load_schemes())}


@app.get("/api/schemes")
def schemes():
    return {"schemes": [{k: s.get(k) for k in ("id", "name", "name_hi", "category", "level", "benefit", "apply_url")}
                        for s in engine.load_schemes()]}


@app.post("/api/parse")
def parse(body: ParseIn):
    return parser.parse(body.text)


@app.post("/api/match")
def match(body: MatchIn):
    return engine.match(body.profile, body.include_not_eligible)


@app.post("/api/family")
def family(body: FamilyIn):
    return engine.match_family(body.household, body.members)


@app.post("/api/scam")
def scam_check(body: ScamIn):
    return scam.check(body.text)


@app.get("/api/fields")
def fields():
    return engine.FIELDS


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
