"""Build out/index.html: every paper's posts, reels and review page on one page (what the judges open)."""
import html
import json
import pathlib

OUT = pathlib.Path(__file__).parent / "out"


def main():
    cards = []
    for c_path in sorted(OUT.glob("*/content.json")):
        c = json.loads(c_path.read_text(encoding="utf-8"))
        d, f, p, t = c["draft"], c["files"], c["paper"], c["timings"]
        rel = lambda x: pathlib.Path(x).resolve().relative_to(OUT.resolve()).as_posix()
        slides = "".join(f'<img loading="lazy" src="{rel(s)}" alt="carousel slide {i}">' for i, s in enumerate(f["carousel"], 1))
        hi = f'<figure><video controls preload="none" poster="{rel(f["reel_frames"][0])}" src="{rel(f["reel_hi"])}"></video><figcaption>Reel · Hindi</figcaption></figure>' if f.get("reel_hi") else ""
        cards.append(f"""<section class="paper">
  <p class="k">{html.escape(p['citation'])} · {len(c['claims'])} verified claims · {len(c['rejected'])} thrown out by the verifier · {len(d['issues'])} flag(s) for the doctor · machine time {t['total']} s</p>
  <h2>{html.escape(d['message'])}</h2>
  <p class="why">{html.escape(d['reasoning'])}</p>
  <p><a href="{rel(c_path.parent / 'review.html')}">Open the doctor review page →</a> · <a href="{html.escape(p['url'])}">the paper</a></p>
  <h3>Carousel</h3><div class="strip">{slides}</div>
  <div class="row">
    <figure><img src="{rel(f['static'])}" alt="static post"><figcaption>Static · 4:5 (1:1 version also made)</figcaption></figure>
    <figure><video controls preload="none" poster="{rel(f['reel_frames'][0])}" src="{rel(f['reel'])}"></video><figcaption>Reel · English · {f.get('reel_seconds', '')} s</figcaption></figure>
    {hi}
  </div>
  <details><summary>Caption, hashtags and Hinglish caption</summary><pre>{html.escape(d['caption'])}\n\n{html.escape(' '.join(d.get('hashtags', [])))}\n\n{html.escape(d.get('caption_hinglish', ''))}</pre></details>
</section>""")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paper in, posts out · steer</title>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
body{{margin:0;background:#F5EBDF;color:#351D1D;font:16px/1.55 Inter,system-ui,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:36px 20px 80px}}
h1,h2,h3{{font-family:'Instrument Serif',Georgia,serif;font-weight:400;color:#C04E2A;margin:0}}
h1{{font-size:clamp(40px,6vw,64px);line-height:1}} h1 em{{font-style:italic}}
h2{{font-size:30px;line-height:1.15;margin:6px 0 8px}} h3{{font-size:22px;margin:18px 0 8px}}
.lead{{max-width:760px;font-size:18px}} .k{{color:#B58777;font-size:13px;margin:0}} .why{{color:#351D1D;max-width:860px}}
a{{color:#C04E2A}} .paper{{background:#F8F2EB;border:1px solid #E6CBBD;border-radius:24px;padding:24px;margin:26px 0}}
.strip{{display:flex;gap:10px;overflow-x:auto;padding-bottom:6px}} .strip img{{height:300px;border-radius:12px;border:1px solid #E6CBBD}}
.row{{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px}} figure{{margin:0}} figure img{{height:340px;border-radius:12px;border:1px solid #E6CBBD}}
video{{height:340px;border-radius:12px;background:#661414}} figcaption{{font-size:13px;color:#B58777;margin-top:4px}}
pre{{white-space:pre-wrap;font:14px/1.5 Inter,sans-serif;background:#F5EBDF;padding:12px;border-radius:12px}}
.steps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:22px 0}}
.steps div{{background:#F8F2EB;border:1px solid #E6CBBD;border-radius:16px;padding:12px;font-size:14px}} .steps b{{color:#C04E2A;display:block}}
</style></head><body><div class="wrap">
<p class="k">steer · Steer Club Hackathon · problem statement 2</p>
<h1>Paper in, <em>posts out.</em></h1>
<p class="lead">A research paper goes in. A carousel, a static post, English and Hindi reels and captions come out, in Steer's voice, with every line pointing to the sentence and page of the paper it came from. A Steer doctor approves on one page before anything is scheduled.</p>
<div class="steps"><div><b>1 · Ingest</b>PDF or link, split by page or paragraph</div><div><b>2 · Extract</b>claims with verbatim quotes; code drops any quote or number not in the paper</div>
<div><b>3 · Write</b>Steer's voice; every line cites claims; numbers, drug names and promises checked</div><div><b>4 · Judge</b>a doctor-style pass per line; one rewrite; leftovers flagged</div>
<div><b>5 · Create</b>brand renders, AI voiceover, motion, subtitles</div><div><b>6 · Review gate</b>doctor approves line by line; only approved posts are scheduled</div></div>
{''.join(cards)}
<p class="k">Built by Ankith M. Gemini, Europe PMC, Pillow, edge-tts, ffmpeg; Claude as coding assistant. Papers are open access (CC BY). Not medical advice.</p>
</div></body></html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print("gallery:", OUT / "index.html")


if __name__ == "__main__":
    main()
