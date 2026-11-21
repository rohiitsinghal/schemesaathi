import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import engine, parser, scam  # noqa: E402


def ids(res, *statuses):
    return {s["id"] for s in res["schemes"] if s["status"] in statuses}


def test_data_is_well_formed():
    seen = set()
    for s in engine.load_schemes():
        assert s["id"] not in seen
        seen.add(s["id"])
        assert s["rules"] and s["documents"] and s["steps"] and s["apply_url"].startswith("https://")
        for r in s["rules"]:
            for leaf in r.get("any", [r]):
                assert leaf["f"] in engine.FIELDS, (s["id"], leaf["f"])
    assert len(seen) >= 25


def test_punjab_farmer():
    p = {"age": 42, "gender": "male", "state": "punjab", "occupation": "farmer", "land_acres": 2,
         "annual_income": 150000, "income_tax_payer": False, "rural": True, "bpl": False}
    res = engine.match(p)
    assert {"pm-kisan", "pmfby", "kcc"} <= ids(res, engine.ELIGIBLE)
    assert "pm-kmy" not in ids(res, engine.ELIGIBLE, engine.LIKELY, engine.NEAR_MISS)  # age 42 > 40
    # state schemes of other states never leak in
    assert "ladki-bahin" not in {s["id"] for s in res["schemes"]}
    assert res["totals"]["yearly_cash"] >= 6000


def test_unknown_is_not_eligible_it_is_likely():
    res = engine.match({"occupation": "farmer"})
    pmk = next(s for s in res["schemes"] if s["id"] == "pm-kisan")
    assert pmk["status"] == engine.LIKELY
    assert set(pmk["missing_fields"]) == {"land_acres", "income_tax_payer"}
    # engine asks for the field that settles the most schemes
    assert res["next_questions"][0]["unlocks"] >= 1


def test_hard_fail():
    res = engine.match({"occupation": "farmer", "land_acres": 0, "income_tax_payer": False}, include_not_eligible=True)
    pmk = next(s for s in res["schemes"] if s["id"] == "pm-kisan")
    assert pmk["status"] == engine.NOT_ELIGIBLE
    assert "You own cultivable land" in pmk["failed"]


def test_near_miss_income():
    p = {"occupation": "student", "category": "sc", "annual_income": 270000}
    res = engine.match(p)
    s = next(s for s in res["schemes"] if s["id"] == "post-matric-sc")
    assert s["status"] == engine.NEAR_MISS
    assert "20,000" in s["near_miss"]["en"]
    assert s["near_miss"]["hi"]


def test_near_miss_age_grow_into():
    p = {"age": 58, "bpl": True}
    res = engine.match(p)
    s = next(s for s in res["schemes"] if s["id"] == "nsap-oap")
    assert s["status"] == engine.NEAR_MISS and "2 year" in s["near_miss"]["en"]


def test_age_far_away_is_not_near_miss():
    res = engine.match({"age": 30, "bpl": True}, include_not_eligible=True)
    s = next(s for s in res["schemes"] if s["id"] == "nsap-oap")
    assert s["status"] == engine.NOT_ELIGIBLE


def test_or_rule_ayushman():
    assert engine.match({"age": 72})["schemes"] and "pmjay" in ids(engine.match({"age": 72}), engine.ELIGIBLE)
    assert "pmjay" in ids(engine.match({"age": 30, "bpl": True}), engine.ELIGIBLE)
    assert "pmjay" not in ids(engine.match({"age": 30, "bpl": False}), engine.ELIGIBLE, engine.LIKELY)


def test_state_scheme_only_for_that_state():
    p = {"age": 30, "gender": "female", "state": "maharashtra", "annual_income": 200000, "income_tax_payer": False}
    assert "ladki-bahin" in ids(engine.match(p), engine.ELIGIBLE)
    p["state"] = "bihar"
    assert "ladki-bahin" not in {s["id"] for s in engine.match(p)["schemes"]}


def test_totals_keep_cover_and_cash_separate():
    p = {"age": 30, "bpl": True, "has_bank_account": True}
    t = engine.match(p)["totals"]
    assert t["insurance_cover"] >= 500000  # PM-JAY + PMJJBY + PMSBY covers are not added to cash
    assert t["yearly_cash"] < 100000


def test_family_household_schemes_counted_once():
    household = {"state": "bihar", "rural": True, "bpl": True, "owns_pucca_house": False, "annual_income": 90000,
                 "income_tax_payer": False}
    members = [{"name": "Ramesh", "age": 45, "gender": "male", "occupation": "farmer", "land_acres": 1.5, "has_bank_account": True},
               {"name": "Sunita", "age": 40, "gender": "female", "has_lpg": False, "has_bank_account": True}]
    res = engine.match_family(household, members)
    all_ids = [s["id"] for m in res["members"] for s in m["schemes"]]
    assert all_ids.count("pmjay") == 1 and all_ids.count("pmay-g") == 1 and all_ids.count("mgnrega") == 1
    sunita = next(m for m in res["members"] if m["name"] == "Sunita")
    assert "ujjwala" in {s["id"] for s in sunita["schemes"]}
    ramesh = next(m for m in res["members"] if m["name"] == "Ramesh")
    assert "pm-kisan" in {s["id"] for s in ramesh["schemes"]}


# ------------------------------------------------------------------ parser
def test_parse_english():
    r = parser.parse("I am a 42 year old farmer from Punjab with 2 acres of land. Family income 1.5 lakh per year. We are BPL.")
    p = r["profile"]
    assert p["age"] == 42 and p["state"] == "punjab" and p["occupation"] == "farmer"
    assert p["land_acres"] == 2 and p["annual_income"] == 150000 and p["bpl"] is True


def test_parse_hinglish_and_hindi():
    p = parser.parse("main ek mahila hoon, 35 saal, Maharashtra mein rehti hoon, meri income 15000 per month hai")["profile"]
    assert p["gender"] == "female" and p["age"] == 35 and p["state"] == "maharashtra" and p["annual_income"] == 180000
    h = parser.parse("मैं पंजाब का किसान हूँ, उम्र 50 साल, 3 एकड़ ज़मीन है")["profile"]
    assert h["state"] == "punjab" and h["occupation"] == "farmer" and h["age"] == 50 and h["land_acres"] == 3


def test_parse_daughter_age_not_taken_as_user_age():
    p = parser.parse("I am a 30 year old woman with a 5 year old daughter")["profile"]
    assert p["age"] == 30 and p["girl_child_under10"] is True


def test_parse_negation():
    p = parser.parse("I do not have a bank account and no land")["profile"]
    assert p["has_bank_account"] is False and p["land_acres"] == 0


def test_parse_unknown_stays_unknown():
    assert parser.parse("hello")["profile"] == {}


# -------------------------------------------------------------- scam shield
def test_official_and_fake_domains():
    assert scam.check_url("https://pmkisan.gov.in")["verdict"] == "official"
    assert scam.check_url("https://pmkisan.gov.in.verify-now.com/login")["verdict"] == "suspicious"
    assert scam.check_url("http://pm-kisan-yojana-apply.xyz")["verdict"] == "suspicious"
    assert scam.check_url("https://bit.ly/abc")["verdict"] == "suspicious"


def test_scam_message_high_risk():
    r = scam.check("Congratulations! Pay ₹500 registration fee and share OTP urgently to claim your PM Kisan money http://pmkisan-claim.top")
    assert r["risk"] == "high" and len(r["flags"]) >= 3


def test_clean_official_message_low_risk():
    assert scam.check("Apply at https://pmjay.gov.in")["risk"] == "low"


# ---------------------------------------------- regressions found while demoing
def test_negation_does_not_leak_across_clauses():
    p = parser.parse("I have a bank account and I do not pay income tax")["profile"]
    assert p["has_bank_account"] is True and p["income_tax_payer"] is False
    assert parser.parse("mere paas bank account nahi hai")["profile"]["has_bank_account"] is False


def test_unknown_core_fact_hides_scheme_but_asks_question():
    res = engine.match({"age": 35, "gender": "female", "state": "maharashtra"})
    shown = {s["id"] for s in res["schemes"]}
    assert "pm-kisan" not in shown and "svanidhi" not in shown  # occupation unknown -> not claimed as relevant
    assert res["next_questions"][0]["field"] == "occupation"


def test_headline_total_counts_only_confirmed_schemes():
    res = engine.match({"occupation": "farmer", "age": 30})  # PM-KISAN only "likely" (land, tax unknown)
    assert res["totals"]["yearly_cash"] == 0 and res["totals"]["potential_yearly_cash"] >= 6000
    res = engine.match({"occupation": "farmer", "land_acres": 2, "income_tax_payer": False})
    assert res["totals"]["yearly_cash"] >= 6000


def test_near_miss_needs_known_core_facts():
    # income is over the PM-SYM cap, but occupation is unknown -> don't claim "almost eligible"
    res = engine.match({"age": 35, "annual_income": 200000})
    assert "pmsym" not in {s["id"] for s in res["schemes"]}


def test_cash_schemes_rank_above_insurance():
    res = engine.match({"occupation": "farmer", "land_acres": 2, "income_tax_payer": False, "age": 30, "has_bank_account": True})
    order = [s["id"] for s in res["schemes"]]
    assert order.index("pm-kisan") < order.index("pmjjby")


def test_new_state_schemes_match_only_their_state():
    mp = engine.match({"age": 35, "gender": "female", "state": "madhya pradesh", "annual_income": 180000, "income_tax_payer": False})
    assert "ladli-behna" in ids(mp, engine.ELIGIBLE)
    assert "lado-lakshmi" not in {s["id"] for s in mp["schemes"]}  # Haryana scheme must not leak into MP
    hr = engine.match({"age": 35, "gender": "female", "state": "haryana", "annual_income": 150000, "income_tax_payer": False},
                      include_not_eligible=True)
    ll = next(s for s in hr["schemes"] if s["id"] == "lado-lakshmi")
    assert ll["status"] in (engine.NEAR_MISS, engine.NOT_ELIGIBLE)  # income above the ₹1 lakh limit


def test_vay_vandana_and_jsy():
    senior = engine.match({"age": 72, "gender": "male", "state": "punjab", "annual_income": 400000})
    assert "ayushman-vay-vandana" in ids(senior, engine.ELIGIBLE)
    mum = engine.match({"age": 26, "gender": "female", "pregnant": True, "bpl": True})
    assert "jsy" in ids(mum, engine.ELIGIBLE)
    mum_general = engine.match({"age": 26, "gender": "female", "pregnant": True, "bpl": False, "category": "general"})
    assert "jsy" not in ids(mum_general, engine.ELIGIBLE, engine.LIKELY)


def test_every_state_scheme_is_flagged_for_verification():
    for s in engine.load_schemes():
        if s["level"] == "state":
            assert s["state"] and s["needs_state_verification"] is True, s["id"]
