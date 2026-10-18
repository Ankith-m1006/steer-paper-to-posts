"""Publish gate: schedule only what the doctor approved.

    python publish.py out/<paper>/approvals.json [out/<paper2>/approvals.json ...]

Reads each paper's content.json and the approvals saved from its review page. A post goes on the
schedule only when every part of it was approved (every carousel slide for the carousel, every
scene for the reel, the static post, and the caption). Writes:
- out/schedule.csv: a week of posts (date, time, format, files, caption) for Meta Business Suite or Buffer;
- out/canva_bulk.csv: one row per carousel slide for Canva's Bulk Create, to restyle in a Canva template.
"""
import csv
import datetime
import json
import pathlib
import sys

OUT = pathlib.Path(__file__).parent / "out"
SLOTS = ["19:30"]   # evening, after work


def main(paths):
    posts, canva = [], []
    for ap in paths:
        ap = pathlib.Path(ap)
        approved = set(json.loads(ap.read_text(encoding="utf-8"))["approved"])
        c = json.loads((ap.parent / "content.json").read_text(encoding="utf-8"))
        d, f = c["draft"], c["files"]
        caption = d["caption"] + "\n\n" + " ".join(d.get("hashtags", []))
        n_slides, n_scenes = len(d["carousel"]), len(d["reel"])
        ok_caption = "caption" in approved
        if ok_caption and all(f"carousel slide {i}" in approved for i in range(1, n_slides + 1)):
            posts.append(("carousel", c["paper"]["citation"], ";".join(f["carousel"]), caption, d.get("alt_text", "")))
        if ok_caption and "static post" in approved:
            posts.append(("static", c["paper"]["citation"], f["static"], caption, ""))
        if ok_caption and all(f"reel scene {i}" in approved for i in range(1, n_scenes + 1)):
            posts.append(("reel", c["paper"]["citation"], f["reel"], caption, ""))
        for i, s in enumerate(d["carousel"], 1):
            canva.append({"paper": c["paper"]["citation"], "slide": i, "kicker": s.get("kicker", ""), "headline": s["headline"],
                          "italic": s.get("emph", ""), "body": s.get("body", ""),
                          "source": f"Source: {c['paper']['citation']}" if s.get("claims") else "steerclub.com"})
        held = [x for x in ["caption"] + [f"carousel slide {i}" for i in range(1, n_slides + 1)] +
                ["static post"] + [f"reel scene {i}" for i in range(1, n_scenes + 1)] if x not in approved]
        print(f"{c['paper']['citation']}: held back {held or 'nothing'}")
    start = datetime.date.today() + datetime.timedelta(days=1)
    with open(OUT / "schedule.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "time", "format", "paper", "files", "caption", "alt_text"])
        for i, (fmt, paper, files, caption, alt) in enumerate(posts):
            w.writerow([(start + datetime.timedelta(days=i)).isoformat(), SLOTS[i % len(SLOTS)], fmt, paper, files, caption, alt])
    with open(OUT / "canva_bulk.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(canva[0]) if canva else ["paper"])
        w.writeheader()
        w.writerows(canva)
    print(f"{len(posts)} approved post(s) scheduled from {start} -> {OUT / 'schedule.csv'}; Canva rows: {len(canva)}")


if __name__ == "__main__":
    main(sys.argv[1:])
