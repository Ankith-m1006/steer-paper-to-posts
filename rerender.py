"""Re-render a paper's posts and reels from its saved content.json, without calling the AI again.

    python rerender.py out/<paper>

Used when the design changes: the verified claims and the approved copy stay exactly as they were.
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent / "pipeline"))
import reel  # noqa: E402
import render  # noqa: E402
import review  # noqa: E402

out = pathlib.Path(sys.argv[1])
c = json.loads((out / "content.json").read_text(encoding="utf-8"))
d, claims, meta = c["draft"], c["claims"], c["paper"]
t = time.time()
files = render.render_all(d, claims, meta["citation"], out)
c["timings"]["render"] = round(time.time() - t)
t = time.time()
files["reel"], files["reel_seconds"] = reel.build(d["reel"], files["reel_frames"], out, "en")
if len(d.get("reel_hi", [])) == len(d["reel"]):
    files["reel_hi"], _ = reel.build([{"voice": v} for v in d["reel_hi"]], files["reel_frames"], out, "hi")
c["timings"]["reel"] = round(time.time() - t)
c["files"] = files
(out / "content.json").write_text(json.dumps(c, indent=1, ensure_ascii=False), encoding="utf-8")
(out / "review.html").write_text(review.page(out.name, meta, claims, c["rejected"], d, files, c["timings"], out), encoding="utf-8")
print(f"re-rendered {meta['citation']}", flush=True)
