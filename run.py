"""Paper in, posts out.

    python run.py papers/A_regain.pdf "DOI:\"10.1111/dom.14725\""   # a PDF (+ optional DOI/title to cite it)
    python run.py PMC11611443                                       # a link, PMC id or DOI
    python run.py --batch papers.txt                                # one source per line: a week of content

For each paper: ingest -> extract + verify claims -> write in Steer's voice + checks + doctor-judge
-> render carousel, static (4:5 and 1:1) and reel frames -> AI-voiced reels (English, Hindi)
-> review page. Then the doctor approves in review.html, and publish.py schedules only what was approved.
"""
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent / "pipeline"))
import extract  # noqa: E402
import ingest  # noqa: E402
import reel  # noqa: E402
import render  # noqa: E402
import review  # noqa: E402
import write  # noqa: E402

OUT = pathlib.Path(__file__).parent / "out"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def run(source, query=None, hindi=True):
    t0 = time.time()
    paper = ingest.load(source, query)
    name = slug(paper.citation)
    out = OUT / name
    out.mkdir(parents=True, exist_ok=True)
    timings = {"ingest": round(time.time() - t0)}
    t = time.time()
    claims, rejected = extract.extract(paper)
    timings["extract"] = round(time.time() - t)
    t = time.time()
    draft = write.write(paper, claims)
    timings["write"] = round(time.time() - t)
    t = time.time()
    files = render.render_all(draft, claims, paper.citation, out)
    timings["render"] = round(time.time() - t)
    t = time.time()
    files["reel"], secs = reel.build(draft["reel"], files["reel_frames"], out, "en")
    files["reel_seconds"] = secs
    if hindi and len(draft.get("reel_hi", [])) == len(draft["reel"]):
        hi_scenes = [{"voice": v} for v in draft["reel_hi"]]
        files["reel_hi"], _ = reel.build(hi_scenes, files["reel_frames"], out, "hi")
    timings["reel"] = round(time.time() - t)
    timings["total"] = round(time.time() - t0)
    meta = {"source": source, "title": paper.title, "citation": paper.citation, "url": paper.url, "license": paper.license}
    (out / "content.json").write_text(json.dumps({"paper": meta, "claims": claims, "rejected": rejected, "draft": draft,
                                                   "files": files, "timings": timings}, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "caption.txt").write_text(draft["caption"] + "\n\n" + " ".join(draft.get("hashtags", [])) +
                                     "\n\n---\nHinglish:\n" + draft.get("caption_hinglish", ""), encoding="utf-8")
    (out / "review.html").write_text(review.page(name, meta, claims, rejected, draft, files, timings, out), encoding="utf-8")
    print(f"{paper.citation}: {len(claims)} claims kept, {len(rejected)} rejected, {len(draft['issues'])} flag(s); "
          f"{timings['total']} s total -> {out / 'review.html'}", flush=True)
    return name


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--batch":
        for line in pathlib.Path(args[1]).read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                src, _, q = line.partition("|")
                run(src.strip(), q.strip() or None)
    else:
        run(args[0], args[1] if len(args) > 1 else None)
