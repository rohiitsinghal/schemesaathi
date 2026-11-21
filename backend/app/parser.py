"""Understand a free-text / voice transcript (English, Hindi, Hinglish) and extract a profile.

Rule-based on purpose: works offline, never invents facts, and anything not stated stays
unknown (the engine then asks a follow-up). An LLM can be plugged in later to improve recall.
"""
from __future__ import annotations

import re

STATES = {
    "andhra pradesh": ["andhra pradesh", "आंध्र प्रदेश", "andhra"], "assam": ["assam", "असम"],
    "bihar": ["bihar", "बिहार"], "chhattisgarh": ["chhattisgarh", "छत्तीसगढ़", "chattisgarh"],
    "delhi": ["delhi", "दिल्ली"], "gujarat": ["gujarat", "गुजरात"], "haryana": ["haryana", "हरियाणा"],
    "himachal pradesh": ["himachal", "हिमाचल"], "jharkhand": ["jharkhand", "झारखंड"],
    "karnataka": ["karnataka", "कर्नाटक", "bengaluru", "bangalore"],
    "kerala": ["kerala", "केरल"], "madhya pradesh": ["madhya pradesh", "मध्य प्रदेश", "m.p."],
    "maharashtra": ["maharashtra", "महाराष्ट्र", "mumbai", "pune", "मुंबई", "पुणे"],
    "odisha": ["odisha", "orissa", "ओडिशा"], "punjab": ["punjab", "पंजाब"],
    "rajasthan": ["rajasthan", "राजस्थान"], "tamil nadu": ["tamil nadu", "tamilnadu", "तमिलनाडु", "तमिल नाडु"],
    "telangana": ["telangana", "तेलंगाना"], "uttar pradesh": ["uttar pradesh", "उत्तर प्रदेश", "u.p.", "up me", "up mein"],
    "uttarakhand": ["uttarakhand", "उत्तराखंड"], "west bengal": ["west bengal", "पश्चिम बंगाल", "bengal"],
}

OCCUPATIONS = [  # order matters: first match wins
    ("farmer", ["farmer", "farming", "kisan", "kheti", "किसान", "खेती", "cultivat"]),
    ("student", ["student", "college", "vidyarthi", "छात्र", "विद्यार्थी", "padhai", "पढ़ाई", "studying"]),
    ("street_vendor", ["street vendor", "vendor", "rehri", "thela", "ठेला", "रेहड़ी", "फेरी", "hawker"]),
    ("artisan", ["carpenter", "tailor", "potter", "blacksmith", "weaver", "cobbler", "mochi", "darzi", "kumhar",
                 "lohar", "badhai", "artisan", "barber", "नाई", "बढ़ई", "दर्जी", "कुम्हार", "लोहार", "मोची"]),
    ("unorganised_worker", ["labour", "labor", "mazdoor", "majdoor", "मजदूर", "मज़दूर", "daily wage", "construction worker",
                            "domestic worker", "gig", "delivery", "driver", "rickshaw", "ड्राइवर", "रिक्शा"]),
    ("self_employed", ["business", "dukan", "shop", "दुकान", "व्यापार", "व्यवसाय", "self-employed", "self employed", "startup"]),
    ("salaried", ["salaried", "naukri", "नौकरी", "private job", "government job", "sarkari"]),
    ("unemployed", ["unemployed", "berozgar", "बेरोज़गार", "बेरोजगार", "jobless"]),
    ("homemaker", ["housewife", "homemaker", "ghar ka kaam", "गृहिणी", "गृहणी"]),
]

NEG = r"(?:\bno\b|\bnot\b|\bdon't\b|\bdont\b|\bdoesn't\b|\bwithout\b|nahi|nahin|नहीं|नही|na hai|बिना)"
LAKH = r"(?:lakh|lac|lakhs|लाख)"
THOUSAND = r"(?:k\b|thousand|hazar|hazaar|हज़ार|हजार)"
MONTHLY = r"(?:per month|a month|monthly|/month|/ month|mahine|mahina|महीने|महीना|प्रति माह|pm\b)"


NEG_BEFORE = r"(?:\bno\b|\bnot\b|\bdon't\b|\bdont\b|\bdoesn't\b|\bwithout\b|बिना)"
NEG_AFTER = r"^\W{0,3}(?:\w+\s+){0,2}?(?:nahi|nahin|नहीं|नही)"


def _negated(text: str, start: int, end: int, window: int = 14) -> bool:
    """English negation sits just before the phrase ('no bank account'); Hindi negation just after ('khata nahi hai')."""
    before = text[max(0, start - window):start]
    after = text[end:end + 18]
    return re.search(NEG_BEFORE, before) is not None or re.match(NEG_AFTER, after) is not None


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _parse_money(text: str) -> float | None:
    """Return yearly income in rupees if one is stated."""
    t = text.lower()
    pat = re.compile(
        rf"(?:₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*({LAKH}|{THOUSAND})?\s*(?:rupees|rupaye|rupay|रुपये|रुपए)?\s*({MONTHLY})?"
    )
    kw = re.search(r"(income|aay|आय|kamai|कमाई|salary|vetan|वेतन|earn\w*|कमा)", t)
    candidates = []
    for m in pat.finditer(t):
        raw, unit, monthly = m.group(1), m.group(2), m.group(3)
        val = _num(raw)
        explicit = bool(unit) or "₹" in m.group(0) or "rs" in m.group(0) or "inr" in m.group(0)
        near_kw = kw and abs(m.start() - kw.end()) <= 25
        if not (explicit or near_kw):
            continue
        # skip numbers that are clearly an age / acres
        tail = t[m.end():m.end() + 12]
        if re.match(r"\s*(?:saal|sal|years?|yrs?|वर्ष|साल|acre|एकड़|bigha|बीघा|%)", tail) and not unit:
            continue
        if unit and re.match(LAKH, unit):
            val *= 100000
        elif unit:
            val *= 1000
        if monthly or re.search(MONTHLY, t[m.end():m.end() + 20]):
            val *= 12
        candidates.append(val)
    return candidates[0] if candidates else None


def parse(text: str) -> dict:
    """Return {"profile": {...}, "found": [...]} for the fields we could confidently read."""
    t = " " + text.strip().lower() + " "
    p: dict = {}

    # household members described with ages (e.g. "5 saal ki beti") must not be read as the user's age
    t_noage = re.sub(r"\d+\s*(?:years?|yrs?|saal|sal|साल|वर्ष)(?:\s*(?:old|ki|ka|की|का))?\s*(?:daughter|son|beti|beta|बेटी|बेटा|girl|boy)", " ", t)

    m = re.search(r"(?:age|umr|उम्र|aayu|आयु)\D{0,10}(\d{1,3})", t_noage) or \
        re.search(r"(\d{1,3})\s*(?:years?|yrs?|yr|saal|sal|साल|वर्ष|baras|बरस)", t_noage)
    if m and 5 <= int(m.group(1)) <= 110:
        p["age"] = int(m.group(1))

    # gender: check female first ("woman" contains "man")
    if re.search(r"\b(woman|women|female|girl|lady|mahila|aurat|ladki|didi|wife|mother|mata)\b|महिला|औरत|लड़की|बहन|माँ", t):
        p["gender"] = "female"
    elif re.search(r"\b(man|male|boy|aadmi|purush|ladka|father|husband)\b|पुरुष|आदमी|लड़का", t):
        p["gender"] = "male"

    for slug, names in STATES.items():
        if any(n in t for n in names):
            p["state"] = slug
            break

    for occ, words in OCCUPATIONS:
        if any(w in t for w in words):
            p["occupation"] = occ
            break

    if re.search(r"\bsc\b|scheduled caste|dalit|अनुसूचित जाति|\bs\.c\b", t):
        p["category"] = "sc"
    elif re.search(r"\bst\b|scheduled tribe|adivasi|आदिवासी|अनुसूचित जनजाति", t):
        p["category"] = "st"
    elif re.search(r"\bobc\b|backward class|ओबीसी|पिछड़ा", t):
        p["category"] = "obc"
    elif re.search(r"\bgeneral\b|सामान्य|\bunreserved\b", t):
        p["category"] = "general"

    m = re.search(r"(\d+(?:\.\d+)?)\s*(acre|acres|एकड़|ekad|hectare|hectares|हेक्टेयर|bigha|बीघा)", t)
    if m:
        v = float(m.group(1))
        unit = m.group(2)
        v = v * 2.47 if unit.startswith(("hect", "हेक्ट")) else v * 0.6 if unit in ("bigha", "बीघा") else v
        p["land_acres"] = round(v, 2)
    elif re.search(r"landless|no land|zameen nahi|ज़मीन नहीं|जमीन नहीं|बिना ज़मीन|बिना जमीन|bhumihin|भूमिहीन", t):
        p["land_acres"] = 0

    inc = _parse_money(t_noage)
    if inc is not None:
        p["annual_income"] = inc

    # boolean-ish facts
    def flag(field: str, pattern: str, value_if_found=True):
        m = re.search(pattern, t)
        if m:
            p[field] = (not value_if_found) if _negated(t, m.start(), m.end()) else value_if_found

    if re.search(r"\bapl\b", t):
        p["bpl"] = False
    elif re.search(r"\bbpl\b|below poverty|गरीबी रेखा|antyodaya|अंत्योदय|poor family|गरीब", t):
        m = re.search(r"\bbpl\b|below poverty|गरीबी रेखा|antyodaya|अंत्योदय|poor family|गरीब", t)
        p["bpl"] = not _negated(t, m.start(), m.end(), 12)

    if re.search(r"\b(village|gaon|gram|rural)\b|गांव|गाँव|ग्रामीण", t):
        p["rural"] = True
    elif re.search(r"\b(city|shahar|urban|town)\b|शहर|शहरी", t):
        p["rural"] = False

    flag("has_bank_account", r"bank account|jan dhan|jandhan|bank khata|बैंक खाता|खाता")
    flag("income_tax_payer", r"income tax|\bitr\b|tax pay|आयकर|इनकम टैक्स", value_if_found=True)
    flag("epfo_member", r"\bepfo?\b|\bpf\b|\besic\b|provident fund")
    flag("has_lpg", r"\blpg\b|gas connection|gas cylinder|गैस कनेक्शन|गैस सिलेंडर")
    flag("owns_pucca_house", r"pucca|पक्का")
    if re.search(r"kaccha|kachcha|kutcha|कच्चा|jhopdi|झोपड़ी|no house|ghar nahi|घर नहीं|rent", t):
        p["owns_pucca_house"] = False
    flag("pregnant", r"pregnan|garbhwati|गर्भवती|expecting a baby|lactating")
    flag("disabled", r"disabl|divyang|viklang|दिव्यांग|विकलांग|handicap")

    m = re.search(r"(?:(\d+)\s*(?:year|yr|saal|sal|साल|वर्ष)\w*\s*(?:old|ki|की)?\s*)?(daughter|beti|बेटी|girl child)", t)
    if m:
        if m.group(1):
            p["girl_child_under10"] = int(m.group(1)) < 10
        elif re.search(r"(?:daughter|beti|बेटी)", t):
            p["girl_child_under10"] = None  # mentioned but age unknown -> ask

    if p.get("girl_child_under10", 0) is None:
        del p["girl_child_under10"]

    return {"profile": p, "found": sorted(p.keys())}
