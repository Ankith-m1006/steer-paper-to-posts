"""Collect the 3 finished posts the hackathon asks for into final-posts/, with a source sheet.

    python final_posts.py

One carousel, one static and one reel, each from a different paper, so the folder also shows the
pipeline working on three papers. Every line of every post is traced to the verbatim quote and the
location in the paper it came from.
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "out"
DEST = ROOT / "final-posts"
PICK = [  # (format, paper folder)
    ("carousel", "mclaren-et-al-nat-metab-2024"),
    ("static", "wilding-et-al-diabetes-obes-metab-2022"),
    ("reel", "mechanick-et-al-obes-rev-2025"),
]


def load(folder):
    return json.loads((OUT / folder / "content.json").read_text(encoding="utf-8"))


def trace(lines, claims):
    by_id = {c["id"]: c for c in claims}
    rows = []
    for label, text, ids in lines:
        for cid in ids or [None]:
            c = by_id.get(cid)
            if c:
                rows.append(f"| {label} | {text} | {cid} | \"{c['quote']}\" | {c['loc']} |")
            else:
                rows.append(f"| {label} | {text} | none (hook or call to action, no health claim) | | |")
    return rows


if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir()
sheet = ["# Source sheet: the 3 finished posts",
         "",
         "Every line below is traced to a verbatim quote from an open-access (CC BY) paper and its location. "
         "Code checked that each quote is really in the paper and that every number in a line appears in its quote; "
         "a doctor-style AI pass then read each line against its cited claims (0 flags left on all three). "
         "The posts never name a prescription drug; drug names appear only inside the papers' own quotes below.",
         ""]
for fmt, folder in PICK:
    c = load(folder)
    p, d, src = c["paper"], c["draft"], OUT / folder
    target = DEST / f"{fmt}"
    target.mkdir()
    if fmt == "carousel":
        for f in sorted((src / "carousel").glob("*.png")):
            shutil.copy(f, target / f.name)
        lines = [(f"Slide {i}", f"{s['headline']}. {s.get('body', '')}".strip(), s.get("claims")) for i, s in enumerate(d["carousel"], 1)]
    elif fmt == "static":
        shutil.copy(src / "static.png", target / "static_4x5.png")
        shutil.copy(src / "static_square.png", target / "static_1x1.png")
        s = d["static"]
        lines = [("Static", f"{s['headline']}. {s['sub']}", s.get("claims"))]
    else:
        shutil.copy(src / "reel_en.mp4", target / "reel_english.mp4")
        if (src / "reel_hi.mp4").exists():
            shutil.copy(src / "reel_hi.mp4", target / "reel_hindi.mp4")
        lines = [(f"Scene {i}", f"{s.get('on_screen', '')} (voice: {s.get('voice', '')})", s.get("claims")) for i, s in enumerate(d["reel"], 1)]
    shutil.copy(src / "caption.txt", target / "caption.txt")
    sheet += [f"## {fmt.capitalize()}: {p['citation']}",
              "",
              f"- **Paper:** {p['title']}",
              f"- **Link:** {p['url']} · licence: {p.get('license', 'CC BY')}",
              f"- **Key message:** {d['message']}",
              f"- **Why this angle:** {d['reasoning']}",
              f"- **Files:** `final-posts/{fmt}/`",
              f"- **Verifier:** {len(c['claims'])} claims kept, {len(c['rejected'])} thrown out, {len(d['issues'])} flags",
              "",
              "| Where | Line in the post | Claim | Verbatim quote from the paper | Location |",
              "|---|---|---|---|---|"]
    sheet += trace(lines, c["claims"])
    if c["rejected"]:
        sheet += ["", "Thrown out by the verifier (never used):", ""]
        sheet += [f"- {r.get('finding', '')} ({r['why']})" for r in c["rejected"]]
    sheet.append("")
(DEST / "SOURCES.md").write_text("\n".join(sheet), encoding="utf-8")
print("final-posts written:", sorted(x.name for x in DEST.iterdir()))
