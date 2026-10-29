

import re
from difflib import SequenceMatcher

STOP = {
    "a",
    "an",
    "the",
    "i",
    "me",
    "my",
    "you",
    "your",
    "we",
    "our",
    "is",
    "are",
    "can",
    "do",
    "does",
    "how",
    "what",
    "where",
    "when",
    "which",
    "please",
    "tell",
    "about",
    "of",
    "for",
    "to",
    "in",
    "and",
    "on",
    "it",
    "us",
    "some",
    "want",
    "need",
    "would",
    "like",
}
ALIASES = {
    "referring": "refer",
    "referred": "refer",
    "referrals": "refer",
    "referral": "refer",
    "clients": "patient",
    "client": "patient",
    "patients": "patient",
    "charges": "price",
    "cost": "price",
    "rates": "price",
    "pricing": "price",
    "fees": "price",
    "booking": "appointment",
    "book": "appointment",
    "nursing": "nurse",
    "services": "service",
    "paying": "payment",
    "payments": "payment",
}


def tokens(value):
    words = re.findall(r"[a-z0-9]+", str(value).lower())
    return {ALIASES.get(w, w) for w in words if w not in STOP}


def best_match(question, records):
    q = tokens(question)
    if not q:
        return None, 0.0
    winner, score = None, 0.0
    for item in records:
        title = item["title"] + " " + item.get("keywords", "")
        t = tokens(title)
        body = tokens(item["body"])
        title_overlap = len(q & t) / max(len(q), 1)
        title_coverage = len(q & t) / max(len(t), 1)
        body_overlap = len(q & body) / max(len(q), 1)
        ratio = SequenceMatcher(None, question.lower(), title.lower()).ratio()
        candidate = max(
            0.75 * title_overlap + 0.25 * title_coverage,
            0.55 * body_overlap,
            ratio * 0.65,
        )
        if candidate > score:
            winner, score = item, candidate
    return winner, score
