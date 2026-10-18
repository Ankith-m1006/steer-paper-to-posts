"""Extract: key findings as claims, each with a verbatim quote and where it is in the paper.

The model proposes claims; code decides which survive. A claim is kept only when its quote
is really in the paper at the stated location (whitespace and hyphenation ignored) and every
number in the claim appears in that quote. Everything else is listed as rejected, so a
reviewer can see what the verifier threw out and why.
"""
import difflib
import re

from llm import ask_json

SYSTEM = """You extract findings from a medical research paper for a doctor-led metabolic health club in India.
Return JSON: {"claims": [{"id": "c1", "finding": "...", "quote": "...", "loc": "...", "kind": "result|method|limitation|context", "audience_value": 1-5}]}
Rules:
- 8 to 14 claims. Prefer results with numbers that matter to a regular person (weight, muscle, regain, risk, habits).
- "quote" must be copied EXACTLY from the text, one or two consecutive sentences, no edits, no ellipses.
- "loc" must be the bracketed location label of the chunk the quote comes from, e.g. "p. 4" or "Results, para 2".
- "finding" restates the quote plainly, keeping every number exactly as in the quote, with its unit and comparison group.
- Include the study's key limitations as kind "limitation" (e.g. exploratory analysis, small sample, who was studied).
- Never add facts that are not in the quote."""


def _norm(s):
    s = s.replace("‐", "-").replace("–", "-").replace("−", "-").replace("’", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"-\s+", "-", s)
    return re.sub(r"\s+", " ", s).strip().lower()


NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers(s):
    # Names like "STEP-1", "GLP-1" or "SURMOUNT-1" are labels, not numbers in the finding.
    s = re.sub(r"[‐‑‒–−]", "-", s)
    s = re.sub(r"\b[A-Za-z]{2,}-\d+\b", " ", s)
    return {n.replace(",", ".") for n in NUM.findall(s)}


def locate(quote, chunks, loc_hint):
    """(found_loc, score): exact match after normalising, else the best fuzzy window (>= 0.92)."""
    q = _norm(quote)
    order = sorted(chunks, key=lambda c: c["loc"] != loc_hint)   # look at the claimed location first
    for c in order:
        if q in _norm(c["text"]):
            return c["loc"], 1.0
    best = (None, 0.0)
    for c in order:
        t = _norm(c["text"])
        step = max(20, len(q) // 4)
        for i in range(0, max(1, len(t) - len(q) + 1), step):
            r = difflib.SequenceMatcher(None, q, t[i:i + len(q)]).ratio()
            if r > best[1]:
                best = (c["loc"], r)
    return best if best[1] >= 0.92 else (None, best[1])


def extract(paper):
    out = ask_json(SYSTEM, f"Paper: {paper.title} ({paper.citation})\n\n{paper.full_text()[:180000]}")
    kept, rejected = [], []
    for c in out.get("claims", []):
        loc, score = locate(c.get("quote", ""), paper.chunks, c.get("loc"))
        missing = _numbers(c.get("finding", "")) - _numbers(c.get("quote", ""))
        if not loc:
            rejected.append({**c, "why": f"quote not found in the paper (best match {score:.2f})"})
        elif missing:
            rejected.append({**c, "why": f"numbers not in the quote: {', '.join(sorted(missing))}"})
        else:
            kept.append({**c, "loc": loc, "match": round(score, 3)})
    for i, c in enumerate(kept, 1):
        c["id"] = f"c{i}"
    return kept, rejected
