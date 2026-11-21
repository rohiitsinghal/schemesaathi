"""SchemeSaathi eligibility engine.

Deterministic and explainable: every decision is made by explicit rules from
schemes.json, never by an LLM. Each rule returns pass / fail / unknown, so a
missing answer never silently becomes "eligible" or "not eligible".
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data" / "schemes.json"

# How each profile field is asked / described. Used for missing-info prompts and Hindi text.
FIELDS: dict[str, dict[str, str]] = {
    "age": {"en": "your age", "hi": "आपकी उम्र", "q_en": "How old are you?", "q_hi": "आपकी उम्र कितनी है?"},
    "gender": {"en": "your gender", "hi": "आपका लिंग", "q_en": "Are you male, female or other?", "q_hi": "आप पुरुष हैं या महिला?"},
    "state": {"en": "your state", "hi": "आपका राज्य", "q_en": "Which state do you live in?", "q_hi": "आप किस राज्य में रहते हैं?"},
    "annual_income": {"en": "your family income", "hi": "आपके परिवार की आय", "q_en": "What is your family's yearly income?", "q_hi": "आपके परिवार की सालाना आय कितनी है?"},
    "occupation": {"en": "your occupation", "hi": "आपका पेशा", "q_en": "What work do you do?", "q_hi": "आप क्या काम करते हैं?"},
    "category": {"en": "your category", "hi": "आपकी श्रेणी", "q_en": "General, OBC, SC or ST?", "q_hi": "सामान्य, ओबीसी, एससी या एसटी?"},
    "land_acres": {"en": "your land holding", "hi": "आपकी ज़मीन", "q_en": "How many acres of land do you own?", "q_hi": "आपके पास कितने एकड़ ज़मीन है?"},
    "bpl": {"en": "BPL status", "hi": "बीपीएल स्थिति", "q_en": "Do you have a BPL / ration card for poor families?", "q_hi": "क्या आपके पास बीपीएल / गरीबी रेखा का राशन कार्ड है?"},
    "rural": {"en": "rural / urban area", "hi": "ग्रामीण / शहरी क्षेत्र", "q_en": "Do you live in a village or a city?", "q_hi": "आप गांव में रहते हैं या शहर में?"},
    "owns_pucca_house": {"en": "house ownership", "hi": "पक्का घर", "q_en": "Does your family own a pucca (concrete) house?", "q_hi": "क्या आपके परिवार के पास पक्का घर है?"},
    "has_bank_account": {"en": "bank account", "hi": "बैंक खाता", "q_en": "Do you have a bank account?", "q_hi": "क्या आपका बैंक खाता है?"},
    "income_tax_payer": {"en": "income tax status", "hi": "आयकर स्थिति", "q_en": "Does anyone in the family pay income tax?", "q_hi": "क्या परिवार में कोई आयकर देता है?"},
    "girl_child_under10": {"en": "daughter under 10", "hi": "10 वर्ष से कम की बेटी", "q_en": "Do you have a daughter under 10?", "q_hi": "क्या आपकी 10 साल से कम उम्र की बेटी है?"},
    "disabled": {"en": "disability", "hi": "विकलांगता", "q_en": "Do you have a disability of 80% or more?", "q_hi": "क्या आपको 80% या अधिक विकलांगता है?"},
    "pregnant": {"en": "pregnancy", "hi": "गर्भावस्था", "q_en": "Are you pregnant or nursing a first child?", "q_hi": "क्या आप गर्भवती हैं या पहले बच्चे को दूध पिला रही हैं?"},
    "epfo_member": {"en": "EPFO / ESIC membership", "hi": "ईपीएफओ / ईएसआईसी सदस्यता", "q_en": "Are you a member of EPFO / ESIC?", "q_hi": "क्या आप ईपीएफओ / ईएसआईसी के सदस्य हैं?"},
    "has_lpg": {"en": "LPG connection", "hi": "एलपीजी कनेक्शन", "q_en": "Does your home already have an LPG connection?", "q_hi": "क्या आपके घर में एलपीजी कनेक्शन है?"},
    "top20_percentile": {"en": "Class 12 percentile", "hi": "12वीं का परसेंटाइल", "q_en": "Did you score in the top 20 percentile in Class 12?", "q_hi": "क्या आप 12वीं में शीर्ष 20 परसेंटाइल में थे?"},
}

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"

# Status of a scheme for a user
ELIGIBLE, LIKELY, NEAR_MISS, NOT_ELIGIBLE = "eligible", "likely", "near_miss", "not_eligible"
POSSIBLE = "possible"  # a core fact (work, gender, state...) is unknown, so we don't show it yet; it still drives follow-up questions

# Facts that merely confirm a scheme we already know applies. Anything else is a "gate" (who you are / where you live):
# until a gate is known we don't claim the scheme is relevant.
DETAIL_FIELDS = {"land_acres", "income_tax_payer", "epfo_member", "has_bank_account", "has_lpg",
                 "owns_pucca_house", "top20_percentile", "annual_income", "bpl"}

_cache: list[dict] | None = None


def load_schemes() -> list[dict]:
    global _cache
    if _cache is None:
        _cache = json.loads(DATA.read_text(encoding="utf-8"))["schemes"]
    return _cache


def _norm(v: Any) -> Any:
    return v.strip().lower() if isinstance(v, str) else v


def eval_rule(rule: dict, profile: dict) -> dict:
    """Evaluate one rule (or an OR-group) and return a result dict."""
    if "any" in rule:
        subs = [eval_rule(r, profile) for r in rule["any"]]
        if any(s["result"] == PASS for s in subs):
            result = PASS
        elif any(s["result"] == UNKNOWN for s in subs):
            result = UNKNOWN
        else:
            result = FAIL
        fields = [f for s in subs if s["result"] == UNKNOWN for f in s["fields"]]  # only what is actually missing
        return {"label": rule["label"], "result": result, "fields": fields, "subs": subs, "gap": None}

    f, op, v = rule["f"], rule["op"], rule.get("v")
    actual = _norm(profile.get(f))
    base = {"label": rule["label"], "fields": [f], "field": f, "actual": actual, "gap": None}
    if actual is None:
        return {**base, "result": UNKNOWN}

    ok: bool
    gap = None
    if op == "eq":
        ok = actual == _norm(v)
    elif op == "in":
        ok = actual in [_norm(x) for x in v]
    elif op == "is_true":
        ok = bool(actual) is True
    elif op == "is_false":
        ok = bool(actual) is False
    elif op == "gt":
        ok = actual > v
        if not ok:
            gap = {"kind": "min", "field": f, "need": v, "have": actual}
    elif op == "gte":
        ok = actual >= v
        if not ok:
            gap = {"kind": "min", "field": f, "need": v, "have": actual}
    elif op == "lte":
        ok = actual <= v
        if not ok:
            gap = {"kind": "max", "field": f, "need": v, "have": actual}
    elif op == "between":
        lo, hi = v
        ok = lo <= actual <= hi
        if not ok:
            gap = ({"kind": "min", "field": f, "need": lo, "have": actual} if actual < lo
                   else {"kind": "max", "field": f, "need": hi, "have": actual})
    else:  # pragma: no cover
        raise ValueError(f"unknown op {op}")
    return {**base, "result": PASS if ok else FAIL, "gap": gap}


def _near_miss_text(gap: dict, lang: str) -> str | None:
    """Turn a numeric gap into advice. Only fixable gaps (age to grow into, income/land to reduce) count."""
    f = gap["field"]
    if f == "age" and gap["kind"] == "min":
        yrs = gap["need"] - gap["have"]
        if yrs <= 5:
            return (f"You become eligible in {yrs} year{'s' if yrs != 1 else ''} (at age {gap['need']})."
                    if lang == "en" else f"आप {yrs} साल बाद ({gap['need']} वर्ष की उम्र में) पात्र हो जाएंगे।")
    if f == "annual_income" and gap["kind"] == "max":
        over = gap["have"] - gap["need"]
        if over <= max(0.3 * gap["need"], 50000):
            return (f"Your income is ₹{over:,.0f} above the limit of ₹{gap['need']:,.0f}. If a recent income certificate shows a lower figure, you may qualify."
                    if lang == "en" else f"आपकी आय सीमा (₹{gap['need']:,.0f}) से ₹{over:,.0f} अधिक है। नया आय प्रमाणपत्र कम आय दिखाए तो आप पात्र हो सकते हैं।")
    if f == "land_acres" and gap["kind"] == "max":
        return ("Your landholding is slightly above the limit; check how land is recorded in your family's name."
                if lang == "en" else "आपकी ज़मीन सीमा से थोड़ी अधिक है; परिवार के नाम पर दर्ज ज़मीन जांचें।")
    return None


def evaluate_scheme(scheme: dict, profile: dict) -> dict:
    results = [eval_rule(r, profile) for r in scheme["rules"]]
    fails = [r for r in results if r["result"] == FAIL]
    unknowns = [r for r in results if r["result"] == UNKNOWN]
    passes = [r for r in results if r["result"] == PASS]

    unknown_gate = [f for r in unknowns for f in r["fields"] if f not in DETAIL_FIELDS]
    status = NOT_ELIGIBLE
    near = None
    if not fails:
        status = ELIGIBLE if not unknowns else (POSSIBLE if unknown_gate else LIKELY)
    elif len(fails) == 1 and not unknown_gate:
        # Near miss: exactly one failing rule and it is a fixable numeric gap
        gap = fails[0].get("gap")
        if gap:
            en = _near_miss_text(gap, "en")
            if en:
                status = NEAR_MISS
                near = {"rule": fails[0]["label"], "en": en, "hi": _near_miss_text(gap, "hi")}

    # Mini state check: a state scheme for another state is simply not shown
    missing = sorted({f for r in unknowns for f in r["fields"]})
    return {
        "id": scheme["id"],
        "status": status,
        "passed": [r["label"] for r in passes],
        "failed": [r["label"] for r in fails],
        "unknown": [r["label"] for r in unknowns],
        "missing_fields": missing,
        "near_miss": near,
    }


def _scheme_view(scheme: dict, ev: dict) -> dict:
    keys = ("id", "name", "name_hi", "category", "level", "benefit", "benefit_hi", "value_type",
            "frequency", "amount", "value_note", "documents", "steps", "apply_url", "deadline",
            "verified_on", "scope", "needs_state_verification")
    out = {k: scheme.get(k) for k in keys}
    out.update(ev)
    return out


def _state_applicable(scheme: dict, profile: dict) -> bool:
    """State schemes are only shown to people in that state (or when state is unknown)."""
    st = scheme.get("state")
    if not st:
        return True
    ps = _norm(profile.get("state"))
    return ps is None or ps == st


STATUS_ORDER = {ELIGIBLE: 0, LIKELY: 1, NEAR_MISS: 2, POSSIBLE: 3, NOT_ELIGIBLE: 4}
VISIBLE = (ELIGIBLE, LIKELY, NEAR_MISS)


def _rank_value(s: dict) -> float:
    """Rank by yearly-equivalent benefit; cover/credit/pension get a modest weight so they still surface."""
    amt = s.get("amount") or 0
    ft = s.get("frequency")
    if s["value_type"] == "cash":
        return amt * (1 if ft in ("yearly", "one_time") else 12)
    if s["value_type"] in ("cover", "credit", "pension", "in_kind", "savings"):
        return min(amt, 100000) * 0.02 + 1000  # protection ranks below real cash, above nothing
    return 0


def match(profile: dict, include_not_eligible: bool = False) -> dict:
    """Evaluate a single person's profile against all schemes."""
    everything = []
    for sc in load_schemes():
        if not _state_applicable(sc, profile):
            continue
        everything.append(_scheme_view(sc, evaluate_scheme(sc, profile)))
    items = [s for s in everything if s["status"] in VISIBLE or (include_not_eligible and s["status"] != POSSIBLE)]
    items.sort(key=lambda s: (STATUS_ORDER[s["status"]], -_rank_value(s)))
    return {"profile": profile, "schemes": items, "totals": totals(items), "next_questions": next_questions(everything)}


def totals(items: list[dict]) -> dict:
    """Money you can count on. Headline numbers come from confirmed ('eligible') schemes only; 'likely' ones are
    reported separately as potential. Cash, pension, insurance cover and credit are never mixed."""
    t = {"yearly_cash": 0, "one_time_cash": 0, "insurance_cover": 0,
         "potential_yearly_cash": 0, "potential_one_time_cash": 0, "potential_insurance_cover": 0,
         "count_eligible": 0, "count_likely": 0, "count_near": 0}
    for s in items:
        st = s["status"]
        if st in VISIBLE:
            t[{ELIGIBLE: "count_eligible", LIKELY: "count_likely", NEAR_MISS: "count_near"}[st]] += 1
        if st not in (ELIGIBLE, LIKELY):
            continue
        pre = "" if st == ELIGIBLE else "potential_"
        amt = s.get("amount") or 0
        if s["value_type"] == "cash":
            t[pre + ("one_time_cash" if s["frequency"] == "one_time" else "yearly_cash")] += amt
        elif s["value_type"] == "pension" and s["frequency"] == "yearly" and amt:
            t[pre + "yearly_cash"] += amt
        elif s["value_type"] == "cover" and amt:
            t[pre + "insurance_cover"] += amt
    return t


def next_questions(items: list[dict], limit: int = 3) -> list[dict]:
    """Which unanswered question would settle the most 'likely' schemes? Drives the follow-up chat."""
    counts: dict[str, int] = {}
    for s in items:
        if s["status"] in (LIKELY, POSSIBLE):
            for f in s["missing_fields"]:
                # for hidden schemes only the missing core facts matter; their detail fields come later
                if s["status"] == LIKELY or f not in DETAIL_FIELDS:
                    counts[f] = counts.get(f, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])[:limit]
    return [{"field": f, "unlocks": n, **{k: FIELDS[f][k] for k in ("q_en", "q_hi")}} for f, n in ranked if f in FIELDS]


# ---------------------------------------------------------------- family mode
def match_family(household: dict, members: list[dict]) -> dict:
    """Run the engine for every member. Household-level facts are shared; a household scheme is
    credited once, to the member with the strongest match (first member on ties)."""
    per_member = []
    for m in members:
        profile = {**household, **{k: v for k, v in m.items() if v is not None}}
        per_member.append({"name": m.get("name") or "Member", "profile": profile, "schemes": match(profile)["schemes"]})
    owner: dict[str, tuple[int, int]] = {}  # scheme id -> (member index, status rank)
    for i, pm in enumerate(per_member):
        for s in pm["schemes"]:
            if s["scope"] == "household":
                rank = STATUS_ORDER[s["status"]]
                if s["id"] not in owner or rank < owner[s["id"]][1]:
                    owner[s["id"]] = (i, rank)
    all_items: list[dict] = []
    for i, pm in enumerate(per_member):
        pm["schemes"] = [s for s in pm["schemes"] if s["scope"] != "household" or owner[s["id"]][0] == i]
        all_items.extend(pm["schemes"])
    return {"members": per_member, "totals": totals(all_items)}
