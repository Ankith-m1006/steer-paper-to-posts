"""Translate + create: post copy in Steer's voice, where every line points at verified claims.

Code checks the draft before anything is rendered:
- each slide, scene and the static post cites claim ids that exist (hook and sign-off may cite none);
- every number in the copy appears in the claims it cites;
- no drug or brand names, no promises of kilos or timelines, no miracle words, no ALL CAPS.
A draft that fails gets one rewrite with the list of problems; whatever still fails is marked
"blocked" for the doctor's review instead of being published.
"""
import json
import re

from llm import ask_json

VOICE = """You write Instagram content for steer, India's doctor-led metabolic health club (steerclub.com).
Audience: Indian adults who have tried diets, heard of GLP-1 medicines, and are curious but sceptical; worried about safety, muscle loss, side effects and weight coming back.
Voice: doctor-led and credible; warm and community-first (a club, not a clinic); made for India (rotis, chai, weddings, desk jobs, family dinners); long-term habits, not quick fixes. Confident, direct, reassuring. Short, punchy lines, often fragments. Sentence case, never ALL CAPS.
Lines that capture it: "Lose well. Live well." "Before you start, hear it from a doctor, not a reel." "Stop Googling. Ask a doctor." "It's biology, not willpower."
Always (in some form): doctor-led; safety first (screening and blood tests before any medicine); personal (plans built on your labs); built for India; a planned exit with habits that last.
Never: fear, shame or body-shaming; promises of kilos, timelines or miracle results; before/after bodies; naming or promoting any specific drug or brand (say "GLP-1 medicines" or "the medicine in this trial"); crowded slides.

Keep the group every number applies to (for example "of those who had prediabetes", "in men of South Asian origin") and the comparison (vs placebo). When the research shows weight returns after treatment stops, never imply that stopping is safe or that results last on their own; describe Steer's planned exit as "a long-term plan made with your doctor, including what happens when the medicine stops", and make the point that habits and follow-up matter.
Use ONLY the verified claims given. Never write a quantity in words (half, two-thirds, most, twice) unless the cited claim says it in words. When a limitation matters for India, say it kindly and usefully (for example "most people in this trial were not South Asian, so your own labs and a doctor's reading matter"), never as a statistic about race. Every number you write must appear in a claim you cite, written the same way. Name the real worry and answer it honestly, including the study's limits when they matter.

Return JSON:
{"message": "the one clear takeaway for a prospective member (one sentence)",
 "reasoning": "why this message matters to Steer's audience and why these formats (2-3 sentences)",
 "carousel": [{"role": "hook|insight|meaning|cta", "kicker": "2-4 words", "headline": "max 12 words", "emph": "a word or short phrase from the headline to set in italics", "body": "max 28 words", "claims": ["c2"]}],
 "static": {"headline": "max 10 words", "emph": "...", "sub": "max 24 words", "claims": ["..."]},
 "reel": [{"role": "hook|insight|meaning|cta", "voice": "1-2 spoken sentences, natural Indian English", "on_screen": "max 8 words", "claims": ["..."]}],
 "caption": "Instagram caption, 60-110 words, ends with 'Before you start, hear it from a doctor, not a reel.' and 'steerclub.com'",
 "caption_hinglish": "the same caption in natural Hinglish (Latin script)",
 "reel_hi": ["for each reel scene, in order, the same voice line in simple spoken Hindi (Devanagari script), numbers as digits"],
 "hashtags": ["8-12 hashtags, no drug or brand names"],
 "alt_text": "one sentence describing the carousel for screen readers"}
Carousel: 6 or 7 slides (1 hook, 3-4 insight/meaning, 1 cta). Reel: 5 or 6 scenes, each "voice" line at most 18 words, 25-40 seconds spoken in total; the hook scene asks the viewer's real worry in their words. The cta slide/scene uses claims [] and invites people to talk to a Steer doctor."""

DRUGS = re.compile(r"semaglutide|tirzepatide|liraglutide|dulaglutide|exenatide|orforglipron|retatrutide|ozempic|wegovy|"
                   r"rybelsus|mounjaro|zepbound|saxenda|victoza|trulicity", re.I)
PROMISES = re.compile(r"\b(lose|drop|shed)\s+\d+\s*(kg|kilos?|pounds|lbs)|guarantee|miracle|melt(s)? fat|in just \d+|"
                      r"before\s*/\s*after|before and after", re.I)
CAPS_OK = {"GLP-1", "GLP", "DEXA", "BMI", "LDL", "HDL", "VLDL", "HbA1c", "STEP", "IDF", "WHO", "ICMR", "HIIT", "CT", "MRI"}
NUM = re.compile(r"\d+(?:[.,]\d+)?")
# Quantities written in words must also come from the cited claim ("two-thirds" is a number too).
WORD_NUMBERS = ["half", "a third", "one-third", "two-thirds", "two thirds", "a quarter", "three-quarters", "double", "twice",
                "triple", "threefold", "fourfold", "fivefold", "tenfold", "one in three", "one in four", "one in five",
                "majority", "most of", "nearly all", "almost all"]


def _texts(item):
    return " ".join(str(item.get(k, "")) for k in ("kicker", "headline", "body", "sub", "voice", "on_screen"))


def _numbers(s):
    s = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", s)
    # "one year" and "1 year" are the same number (also across Hindi and English lines).
    for w, n in (("one", 1), ("two", 2), ("three", 3), ("four", 4), ("five", 5), ("six", 6), ("seven", 7),
                 ("eight", 8), ("nine", 9), ("ten", 10)):
        s = re.sub(r"\b" + w + r"\b(?!-)", str(n), s, flags=re.I)   # unicode hyphens, as in "GLP‑1"
    s = re.sub(r"GLP-1|HbA1c|steerclub\.com|\b1\s*/\s*\d+\b", " ", s)
    out = set()
    for n in NUM.findall(s):
        n = n.replace(",", ".")
        out.add(n[:-2] if n.endswith(".0") else n)
    low = s.lower()
    out |= {w for w in WORD_NUMBERS if re.search(r"\b" + re.escape(w) + r"\b", low)}
    return out


def problems(draft, claims):
    by_id = {c["id"]: c for c in claims}
    found = []
    items = [("carousel slide", i + 1, s) for i, s in enumerate(draft.get("carousel", []))] + \
            [("reel scene", i + 1, s) for i, s in enumerate(draft.get("reel", []))] + [("static post", 1, draft.get("static", {}))] +             [("hindi reel scene", i + 1, {"voice": v, "claims": (draft.get("reel") or [{}] * (i + 1))[min(i, len(draft.get("reel", [])) - 1)].get("claims", []),
                                          "role": (draft.get("reel") or [{}] * (i + 1))[min(i, len(draft.get("reel", [])) - 1)].get("role")})
             for i, v in enumerate(draft.get("reel_hi", []))]
    for kind, n, item in items:
        text = _texts(item)
        cited = item.get("claims") or []
        unknown = [c for c in cited if c not in by_id]
        if unknown:
            found.append(f"{kind} {n}: cites unknown claims {unknown}")
        if not cited and item.get("role") not in ("hook", "cta"):
            found.append(f"{kind} {n}: makes a point but cites no claim")
        source = " ".join(by_id[c]["finding"] + " " + by_id[c]["quote"] for c in cited if c in by_id)
        extra = _numbers(text) - _numbers(source)
        if extra:
            found.append(f"{kind} {n}: numbers not in its cited claims: {', '.join(sorted(extra))}")
    whole = json.dumps({k: v for k, v in draft.items() if k not in ("reasoning",)}, ensure_ascii=False)
    for rx, what in ((DRUGS, "names a drug or brand"), (PROMISES, "makes a promise or miracle claim")):
        for m in set(x.group(0) for x in rx.finditer(whole)):
            found.append(f"{what}: '{m}'")
    shouting = {w for w in re.findall(r"\b[A-Z]{4,}\b", whole) if w not in CAPS_OK}
    if shouting:
        found.append(f"ALL CAPS words: {', '.join(sorted(shouting))}")
    return found


JUDGE = """You are a careful doctor reviewing social posts before publication. For each line, check it against ONLY the claims it cites.
Statements about Steer's own care model (doctor-led, screening and blood tests first, plans built on labs, building habits, long-term follow-up, a plan made with a doctor) are allowed as long as they promise no outcome.
Flag a line when: it states anything the cited claims do not support (wrong claim cited, overstated, a cause where the claim shows an association, a group the study did not include); it could mislead a patient; it promotes a drug or promises results; or it shames or frightens.
Return JSON: {"flags": [{"where": "carousel slide 2 | reel scene 3 | static post | caption", "problem": "...", "fix": "..."}]}. Return {"flags": []} when everything is supported."""


def judge(draft, claims):
    by_id = {c["id"]: c for c in claims}
    lines = []
    for kind, items in (("carousel slide", draft.get("carousel", [])), ("reel scene", draft.get("reel", []))):
        for i, it in enumerate(items, 1):
            lines.append({"where": f"{kind} {i}", "text": _texts(it), "cites": {c: by_id[c]["finding"] for c in it.get("claims", []) if c in by_id}})
    st = draft.get("static", {})
    lines.append({"where": "static post", "text": _texts(st), "cites": {c: by_id[c]["finding"] for c in st.get("claims", []) if c in by_id}})
    all_claims = {c["id"]: c["finding"] for c in claims}
    lines.append({"where": "caption", "text": draft.get("caption", ""), "cites": all_claims})
    out = ask_json(JUDGE, json.dumps(lines, ensure_ascii=False, indent=1), temperature=0)
    return [f"{f['where']}: {f['problem']} (fix: {f.get('fix', '')})" for f in out.get("flags", [])]


def write(paper, claims):
    usable = [c for c in claims if c["kind"] != "method" or c["audience_value"] >= 4]
    brief = json.dumps([{k: c[k] for k in ("id", "finding", "kind", "loc")} for c in usable], ensure_ascii=False, indent=1)
    prompt = f"Paper: {paper.title} ({paper.citation}).\nVerified claims:\n{brief}"
    draft = ask_json(VOICE, prompt, temperature=0.6)
    issues = problems(draft, claims) + judge(draft, claims)
    if issues:
        draft = ask_json(VOICE, prompt + "\n\nYour previous draft had these problems; fix every one and return the full JSON again:\n- "
                         + "\n- ".join(issues) + "\n\nPrevious draft:\n" + json.dumps(draft, ensure_ascii=False), temperature=0.3)
        issues = problems(draft, claims)
        flags = judge(draft, claims)
        draft["judge_flags"] = flags
        issues += flags
    draft["issues"] = issues
    return draft
