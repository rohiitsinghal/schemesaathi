# SchemeSaathi — demo build

Voice/text → profile → deterministic eligibility engine → ranked schemes → documents + apply steps.

## Run
    pip install fastapi uvicorn pytest httpx
    uvicorn app.main:app --reload        # open http://localhost:8000
    pytest -q                            # 24 tests

## Layout
- app/data/schemes.json  28 schemes (26 central + 2 state), structured rules, documents, steps, official links
- app/engine.py          rule engine: pass/fail/unknown, near-miss, follow-up questions, family bundle
- app/parser.py          English / Hindi / Hinglish text → profile (offline, rule-based)
- app/scam.py            Scam Shield: link + message risk check
- app/main.py            FastAPI endpoints (/api/parse, /match, /family, /scam, /schemes)
- static/                PWA UI (voice in/out, EN/हिन्दी, Find / Family / Scam Shield)

## Design choices worth saying in the pitch
1. The LLM never decides eligibility. Rules are explicit data, so every answer is explainable and testable.
2. Unknown ≠ no. Missing facts become follow-up questions instead of wrong answers.
3. "Almost eligible" tells people what would change the result (income gap, years until age limit).
4. Headline totals count only confirmed schemes; insurance cover and loans are never added to cash.
5. Household schemes (health, housing, ration, LPG) are counted once across a family.

## Data caveat (important)
Rules and amounts are simplified from public guidelines and `verified_on` is null everywhere.
Before the demo, re-check each scheme against its official page and fill in `verified_on`.
The two state schemes are flagged `needs_state_verification`.
