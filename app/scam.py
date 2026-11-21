"""Scam Shield: check a link or forwarded message for signs of a fake scheme portal or agent fraud."""
from __future__ import annotations

import re
from urllib.parse import urlparse

OFFICIAL_SUFFIXES = (".gov.in", ".nic.in")
OFFICIAL_EXACT = {  # official non-.gov.in sites referenced by schemes in our database
    "mudra.org.in", "maandhan.in", "standupmitra.in", "onlinesbi.sbi", "sbi.co.in", "pmuy.gov.in",
}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "rb.gy", "is.gd", "shorturl.at", "goo.gl", "wa.me", "ow.ly"}
RISKY_TLDS = (".xyz", ".top", ".click", ".link", ".site", ".online", ".live", ".vip", ".club", ".shop", ".info", ".icu", ".cfd")
GOV_WORDS = ("yojana", "kisan", "pmkisan", "pm-kisan", "pmay", "ayushman", "ujjwala", "mudra", "scheme", "sarkari",
             "subsidy", "scholarship", "mgnrega", "eshram", "gov", "sarkar", "anudan", "labharthi", "beneficiary")

URL_RE = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+|"
    r"\b[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.(?:com|in|org|net|co|xyz|top|info|online|site|click|link|ly|me|app|live|club|shop|vip|icu|cfd|sbi)\b(?:/[^\s<>\"']*)?",
    re.I,
)

MSG_FLAGS = [  # (regex, severity points, plain-language flag)
    (r"registration fee|processing fee|pay\s*(?:rs|₹)|₹\s*\d+\s*(?:fee|charge|deposit)|fees? required|shulk|शुल्क|फीस|रजिस्ट्रेशन फीस|पैसे जमा|deposit",
     30, "Asks you to pay a fee. Genuine government scheme applications are free."),
    (r"\botp\b|\bpin\b|\bcvv\b|password|ओटीपी|पासवर्ड|पिन नंबर",
     35, "Asks for an OTP, PIN or password. Never share these with anyone."),
    (r"urgent|immediately|last date today|hurry|within 24 hours|expires|तुरंत|जल्दी करें|आज ही",
     15, "Creates urgency to make you act without thinking."),
    (r"click (?:the )?link|click here|लिंक पर क्लिक|apply now at|claim (?:your|now)|download apk|\.apk",
     20, "Pushes you to click a link or install an app."),
    (r"guaranteed|100% (?:approval|sure)|pakka|गारंटी|without documents|bina document",
     20, "Promises guaranteed approval. Nobody can guarantee a government benefit."),
    (r"forward (?:this )?to|share (?:with|to) \d+|10 (?:people|groups)|आगे भेजें",
     10, "Chain-forward message, a common scam pattern."),
    (r"agent|dalal|दलाल|commission|कमीशन",
     10, "Mentions an agent or commission. Apply directly or via a CSC at the official rate."),
    (r"won|lottery|jackpot|free (?:laptop|phone|mobile)|मुफ्त मोबाइल|मुफ्त लैपटॉप",
     25, "Offers a prize or freebie that doesn't match any real scheme."),
]


def _host(url: str) -> str:
    u = url if "://" in url else "http://" + url
    return (urlparse(u).hostname or "").lower().rstrip(".")


def is_official_host(host: str) -> bool:
    return host in OFFICIAL_EXACT or any(host.endswith(s) or host == s.lstrip(".") for s in OFFICIAL_SUFFIXES)


def check_url(url: str) -> dict:
    host = _host(url)
    reasons: list[str] = []
    if not host:
        return {"url": url, "host": "", "verdict": "unknown", "reasons": ["Could not read the web address."]}
    if is_official_host(host):
        # Reject lookalikes such as "pmkisan.gov.in.verify-now.com" (those don't end with .gov.in, so they never reach here)
        if "@" in url:
            return {"url": url, "host": host, "verdict": "suspicious", "reasons": ["Address contains '@', which can hide the real destination."]}
        return {"url": url, "host": host, "verdict": "official", "reasons": ["Government domain (.gov.in / .nic.in) or a known official scheme site."]}

    if host in SHORTENERS:
        reasons.append("Shortened link hides the real destination.")
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
        reasons.append("Uses a raw IP address instead of a name.")
    if host.startswith("xn--") or ".xn--" in host:
        reasons.append("Uses look-alike characters (punycode).")
    if host.endswith(RISKY_TLDS):
        reasons.append("Uses a domain ending commonly seen on throwaway sites.")
    if "gov.in" in host or "nic.in" in host:
        reasons.append("Mentions 'gov.in' inside a non-government address, a classic fake-portal trick.")
    elif any(w in host for w in GOV_WORDS):
        reasons.append("Looks like a scheme site but is not a government domain.")
    if host.count("-") >= 3:
        reasons.append("Unusually many hyphens in the address.")

    verdict = "suspicious" if reasons else "unverified"
    if not reasons:
        reasons.append("Not a government domain. Open schemes only from the official link shown in SchemeSaathi.")
    return {"url": url, "host": host, "verdict": verdict, "reasons": reasons}


def check(text: str) -> dict:
    t = text.strip()
    urls = []
    seen = set()
    for m in URL_RE.finditer(t):
        u = m.group(0).rstrip(".,);]")
        if u.lower() not in seen:
            seen.add(u.lower())
            urls.append(check_url(u))

    score = 0
    flags = []
    low = t.lower()
    for pat, pts, msg in MSG_FLAGS:
        if re.search(pat, low):
            score += pts
            flags.append(msg)
    for u in urls:
        score += {"suspicious": 35, "unverified": 12, "unknown": 5, "official": 0}[u["verdict"]]

    # A purely official link with no message red flags is low risk
    risk = "high" if score >= 50 else "medium" if score >= 20 else "low"
    if not urls and not flags:
        risk = "low"

    advice = ["Apply only through the official link SchemeSaathi shows, or at your Gram Panchayat / CSC.",
              "Government schemes never ask for an OTP, PIN or a fee to 'release' your benefit."]
    if risk != "low":
        advice.insert(0, "Do not click, pay or share any details. Report it on cybercrime.gov.in or call 1930.")
    return {"risk": risk, "score": min(score, 100), "urls": urls, "flags": flags, "advice": advice}
