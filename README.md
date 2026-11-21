# SchemeSaathi — demo build

Voice/text → profile → deterministic eligibility engine → ranked schemes → documents + apply steps.

## Run
    # 1. build the UI (React + Tailwind CSS v4, Vite)
    cd frontend && npm install && npm run build      # → frontend/dist

    # 2. start the API, which also serves frontend/dist at /
    cd ../backend
    pip install -r requirements-dev.txt
    uvicorn app.main:app --reload                    # open http://localhost:8000
    pytest -q                                        # 27 tests

Deployment (Docker + GitHub Actions CI/CD to an instance): see [deploy/README.md](deploy/README.md).

While working on the UI, run `npm run dev` in `frontend/` alongside uvicorn:
hot-reload on http://localhost:5173, with /api proxied to :8000.

## Layout
    backend/
      app/data/schemes.json  54 schemes (37 central + 17 state across 13 states / UTs), structured rules, documents, steps, official links
      app/engine.py          rule engine: pass/fail/unknown, near-miss, follow-up questions, family bundle
      app/parser.py          English / Hindi / Hinglish text → profile (offline, rule-based)
      app/scam.py            Scam Shield: link + message risk check
      app/main.py            FastAPI endpoints (/api/parse, /match, /family, /scam, /schemes) + serves the UI
      tests/                 engine / parser / scam tests
      requirements.txt
    frontend/
      src/                   React PWA UI (voice in/out, EN/हिन्दी, Find / Family / Scam Shield)
        i18n.js              all English / Hindi strings
        components/          FindTab, FamilyTab, ScamTab, SchemeCard, Banner, Followup, ui (buttons, inputs)
      public/                manifest, icon, service worker (copied into the build)
      dist/                  build output (git-ignored)

## Design choices worth saying in the pitch
1. The LLM never decides eligibility. Rules are explicit data, so every answer is explainable and testable.
2. Unknown ≠ no. Missing facts become follow-up questions instead of wrong answers.
3. "Almost eligible" tells people what would change the result (income gap, years until age limit).
4. Headline totals count only confirmed schemes; insurance cover and loans are never added to cash.
5. Household schemes (health, housing, ration, LPG) are counted once across a family.

## Data caveat (important)
Rules and amounts are simplified from public guidelines and `verified_on` is null everywhere.
Before the demo, re-check each scheme against its official page and fill in `verified_on`.
All state schemes are flagged `needs_state_verification`. Several 2026 state schemes were changing while this was written (Delhi Lakshmi, West Bengal's Annapurna, Karnataka's Gruha Jyothi / Shakti reviews, Haryana's Lado Lakshmi rule changes), so re-check those first.
