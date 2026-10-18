"""Review gate: one page per paper for the Steer doctor.

Every slide, scene and the static post is shown next to the claims it cites, each with the
verbatim quote and where it is in the paper. Lines the verifier or the doctor-judge flagged are
marked. The doctor ticks what is approved and downloads approvals.json; publish.py will not
schedule anything that is not in it.
"""
import html
import os
import json
import pathlib

CSS = """
body{margin:0;background:#F5EBDF;color:#351D1D;font:15px/1.5 Inter,system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 80px}
h1,h2{font-family:'Instrument Serif',Georgia,serif;font-weight:400;color:#C04E2A;margin:0}
h1{font-size:40px}h2{font-size:28px;margin:34px 0 12px}
.meta{color:#B58777;margin:6px 0 18px}.meta a{color:#B58777}
.msg{background:#F8F2EB;border:1px solid #E6CBBD;border-radius:16px;padding:16px 18px;margin:12px 0}
.item{display:grid;grid-template-columns:220px 1fr 1fr 120px;gap:16px;background:#F8F2EB;border:1px solid #E6CBBD;border-radius:16px;padding:14px;margin:10px 0}
.item.flag{border:2px solid #C04E2A}
.item img{width:220px;border-radius:10px;border:1px solid #E6CBBD}
.k{font-size:12px;color:#B58777;letter-spacing:.04em}
.q{font-family:Georgia,serif;font-style:italic;background:#F5EBDF;border-left:3px solid #C04E2A;padding:6px 10px;margin:6px 0}
.flagtxt{color:#C04E2A;font-weight:600;margin-top:6px}
label.ok{display:flex;gap:8px;align-items:center;font-weight:600}
.bar{position:sticky;bottom:0;background:#661414;color:#F5EBDF;padding:14px 20px;display:flex;justify-content:space-between;align-items:center}
.bar button{background:#F5EBDF;color:#661414;border:0;border-radius:999px;padding:10px 18px;font-weight:700;cursor:pointer}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #E6CBBD;padding:8px;text-align:left;vertical-align:top}
"""


def _cites(item, by_id, url):
    out = []
    for cid in item.get("claims", []):
        c = by_id.get(cid)
        if c:
            out.append(f"<div><span class='k'>{cid} · {html.escape(c['loc'])} · match {c['match']}</span>"
                       f"<div class='q'>“{html.escape(c['quote'])}”</div></div>")
    return "".join(out) or "<span class='k'>no claim (hook or sign-off)</span>"


def page(name, paper, claims, rejected, draft, files, timings, out_dir):
    by_id = {c["id"]: c for c in claims}
    flags = draft.get("issues", [])
    rows = []

    def flagged(where):
        return [f for f in flags if f.lower().startswith(where.lower())]

    entries = [(f"carousel slide {i}", s, files["carousel"][i - 1]) for i, s in enumerate(draft["carousel"], 1)]
    entries += [("static post", draft["static"], files["static"])]
    entries += [(f"reel scene {i}", s, files["reel_frames"][i - 1]) for i, s in enumerate(draft["reel"], 1)]
    for where, item, img in entries:
        f = flagged(where)
        text = " · ".join(html.escape(str(item.get(k, ""))) for k in ("kicker", "headline", "body", "sub", "voice", "on_screen") if item.get(k))
        rows.append(f"""<div class="item {'flag' if f else ''}">
          <img src="{os.path.relpath(img, out_dir).replace(os.sep, '/')}" alt="">
          <div><div class="k">{where}</div><div>{text}</div>{''.join(f"<div class='flagtxt'>Flag: {html.escape(x)}</div>" for x in f)}</div>
          <div>{_cites(item, by_id, paper['url'])}</div>
          <label class="ok"><input type="checkbox" data-id="{where}" {'' if f else 'checked'}> approve</label></div>""")
    cap_flags = flagged("caption")
    rej = "".join(f"<tr><td>{html.escape(r.get('finding', ''))}</td><td>{html.escape(r['why'])}</td></tr>" for r in rejected) or "<tr><td colspan=2>none</td></tr>"
    claims_rows = "".join(f"<tr><td>{c['id']}</td><td>{html.escape(c['finding'])}</td><td class='q'>{html.escape(c['quote'])}</td><td>{html.escape(c['loc'])}</td></tr>" for c in claims)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review · {html.escape(paper['citation'])}</title>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">
<h1>Doctor review · {html.escape(paper['citation'])}</h1>
<div class="meta">{html.escape(paper['title'])} · licence {html.escape(paper['license'])} · <a href="{html.escape(paper['url'])}">{html.escape(paper['url'])}</a><br>
Machine time: extract {timings.get('extract', '?')} s, write + checks {timings.get('write', '?')} s, images {timings.get('render', '?')} s, reel {timings.get('reel', '?')} s. Nothing is published until this page's approvals are saved.</div>
<div class="msg"><b>Message:</b> {html.escape(draft['message'])}<br><b>Why:</b> {html.escape(draft['reasoning'])}</div>
<div class="msg"><b>{len(flags)} flag(s)</b> from the automatic checks: {html.escape('; '.join(flags)) or 'none'}</div>
<h2>Posts, line by line, with their sources</h2>{''.join(rows)}
<h2>Caption</h2><div class="item {'flag' if cap_flags else ''}" style="grid-template-columns:1fr 1fr 120px"><div>{html.escape(draft['caption']).replace(chr(10), '<br>')}<p class="k">{html.escape(' '.join(draft.get('hashtags', [])))}</p>{''.join(f"<div class='flagtxt'>Flag: {html.escape(x)}</div>" for x in cap_flags)}</div>
<div><span class="k">Hinglish</span><br>{html.escape(draft.get('caption_hinglish', '')).replace(chr(10), '<br>')}</div><label class="ok"><input type="checkbox" data-id="caption" {'' if cap_flags else 'checked'}> approve</label></div>
<h2>Every verified claim</h2><table><tr><th>id</th><th>finding</th><th>verbatim quote</th><th>where</th></tr>{claims_rows}</table>
<h2>Thrown out by the verifier</h2><table><tr><th>proposed claim</th><th>why it was rejected</th></tr>{rej}</table>
</div><div class="bar"><span id="count"></span><button id="save">Save approvals.json</button></div>
<script>
const boxes=[...document.querySelectorAll('input[data-id]')];
const upd=()=>document.getElementById('count').textContent=boxes.filter(b=>b.checked).length+' of '+boxes.length+' approved';
boxes.forEach(b=>b.onchange=upd);upd();
document.getElementById('save').onclick=()=>{{const a={{paper:{json.dumps(name)},approved:boxes.filter(b=>b.checked).map(b=>b.dataset.id),rejected:boxes.filter(b=>!b.checked).map(b=>b.dataset.id),at:new Date().toISOString()}};
const l=document.createElement('a');l.href=URL.createObjectURL(new Blob([JSON.stringify(a,null,2)],{{type:'application/json'}}));l.download='approvals.json';l.click();}};
</script></body></html>"""
