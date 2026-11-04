import re

PROSPERITY_PATTERNS = [
    r"\bseed\s+faith\b",
    r"\bsow\s+a\s+seed\b",
    r"\bfinancial\s+breakthrough\b",
    r"\bclaim\s+your\s+miracle\b",
    r"\bprosperity\b",
    r"\bwealth\s+transfer\b",
]

POLITICS_PATTERNS = [
    r"\belection\b",
    r"\bpolitic(al|s)\b",
    r"\bparty\b",
    r"\bpresident\b",
    r"\bparliament\b",
]

def contains_disallowed(text: str) -> list[str]:
    hits = []
    t = (text or "").lower()
    for p in PROSPERITY_PATTERNS:
        if re.search(p, t):
            hits.append("prosperity")
            break
    for p in POLITICS_PATTERNS:
        if re.search(p, t):
            hits.append("politics")
            break
    return hits
