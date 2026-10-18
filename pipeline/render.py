"""Create: carousel slides, a static post and reel frames as PNGs in Steer's brand.

Steer's palette, set like a trusted doctor's note: ruled paper with a margin line, Fraunces
headlines that mix upright and italic, Manrope body text, handwritten notes in Kalam (an
Indian Type Foundry face), a hand-drawn underline, and every source printed as a stamp.
"""
import math
import pathlib

from PIL import Image, ImageDraw, ImageFont

FONTS = pathlib.Path(__file__).resolve().parents[1] / "fonts"
CREAM, RUST, MAROON, INK, CLAY, BLUSH, PAPER = "#F5EBDF", "#C04E2A", "#661414", "#351D1D", "#B58777", "#E6CBBD", "#F8F2EB"
_cache = {}


def _font(name, size, axes=None):
    key = (name, size, tuple(sorted((axes or {}).items())))
    if key not in _cache:
        f = ImageFont.truetype(str(FONTS / name), size)
        if axes:
            try:
                names = [a["name"] if isinstance(a, dict) else a for a in f.get_variation_axes()]
                names = [n.decode() if isinstance(n, bytes) else n for n in names]
                defaults = {"Optical Size": min(144, max(9, size)), "Weight": 400, "Softness": 50, "Wonky": 0}
                values = [axes.get(n, defaults.get(n, 0)) for n in names]
                f.set_variation_by_axes(values)
            except Exception:
                pass
        _cache[key] = f
    return _cache[key]


def serif(size, italic=False, weight=400):
    return _font("Fraunces-Italic.ttf" if italic else "Fraunces.ttf", size,
                 {"Optical Size": 144, "Weight": weight, "Softness": 60, "Wonky": 1 if italic else 0})


def sans(size, weight=400):
    return _font("Manrope.ttf", size, {"Weight": weight})


def hand(size, bold=False):
    return _font("Kalam-Bold.ttf" if bold else "Kalam-Regular.ttf", size)


# ---------- paper ----------

def notepad(d, W, H, top, bottom, margin_x=78, gap=62, line=BLUSH, rule=RUST):
    """Ruled lines and a margin line, like a page from a doctor's pad."""
    y = top
    while y < bottom:
        d.line([(0, y), (W, y)], fill=line, width=2)
        y += gap
    d.line([(margin_x, 0), (margin_x, H)], fill=rule, width=2)
    for k in range(3):                       # punch holes at the left
        cy = top + (bottom - top) * (k + 1) // 4
        d.ellipse([margin_x // 2 - 9, cy - 9, margin_x // 2 + 9, cy + 9], fill=CREAM, outline=BLUSH, width=2)


def squiggle(d, x0, x1, y, color=RUST, width=4):
    pts = [(x, y + 6 * math.sin((x - x0) / 26)) for x in range(int(x0), int(x1), 4)]
    d.line(pts, fill=color, width=width, joint="curve")


def stamp(d, xy, text, f, color, max_w):
    """A source line inside a dashed pill, slightly crooked like a rubber stamp."""
    x, y = xy
    lines = wrap(d, text, f, max_w - 48)
    h = len(lines) * int(f.size * 1.35) + 26
    w = min(max_w, max(d.textlength(l, font=f) for l in lines) + 48)
    for k in range(0, int(2 * (w + h)), 16):           # dashed outline
        _dash_point(d, x, y, w, h, k, color)
    yy = y + 13
    for l in lines:
        d.text((x + 24, yy), l, font=f, fill=color)
        yy += int(f.size * 1.35)
    return y + h


def _dash_point(d, x, y, w, h, k, color):
    per = 2 * (w + h)
    k %= per
    if k < w:
        a, b = (x + k, y), (x + min(k + 9, w), y)
    elif k < w + h:
        a, b = (x + w, y + k - w), (x + w, y + min(k - w + 9, h))
    elif k < 2 * w + h:
        a, b = (x + w - (k - w - h), y + h), (x + max(w - (k - w - h) - 9, 0), y + h)
    else:
        a, b = (x, y + h - (k - 2 * w - h)), (x, y + max(h - (k - 2 * w - h) - 9, 0))
    d.line([a, b], fill=color, width=3)


# ---------- text ----------

def rich_lines(draw, text, emph, size, width):
    """Wrap a headline word by word; words inside the `emph` phrase are set in italic."""
    words = text.split()
    emph_words = set()
    if emph and emph.lower() in text.lower():
        start = text.lower().index(emph.lower())
        pos = 0
        for i, w in enumerate(words):
            j = text.index(w, pos)
            if start <= j < start + len(emph):
                emph_words.add(i)
            pos = j + len(w)
    lines, line, x = [], [], 0
    space = draw.textlength(" ", font=serif(size))
    for i, w in enumerate(words):
        f = serif(size, i in emph_words)
        wl = draw.textlength(w, font=f)
        if line and x + space + wl > width:
            lines.append(line)
            line, x = [], 0
        line.append((w, f, i in emph_words))
        x += (space if len(line) > 1 else 0) + wl
    if line:
        lines.append(line)
    return lines, space


def draw_rich(draw, xy, text, emph, size, width, fill, leading=1.04, underline=True):
    """Headline with italics; the italic phrase gets a hand-drawn underline."""
    x0, y = xy
    lines, space = rich_lines(draw, text, emph, size, width)
    for line in lines:
        x = x0
        for w, f, is_emph in line:
            draw.text((x, y), w, font=f, fill=fill)
            wl = draw.textlength(w, font=f)
            if is_emph and underline:
                squiggle(draw, x, x + wl + space * 0.2, y + size * 1.02, color=RUST if fill != CREAM else BLUSH, width=2)
            x += wl + space
        y += int(size * leading)
    return y


def wrap(draw, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_text(draw, xy, text, f, width, fill, leading=1.4):
    x, y = xy
    for line in wrap(draw, text, f, width):
        draw.text((x, y), line, font=f, fill=fill)
        y += int(f.size * leading)
    return y


def source_line(claims, by_id, citation):
    locs = sorted({by_id[c]["loc"] for c in claims if c in by_id})
    return f"Source: {citation}" + (f" · {', '.join(locs)}" if locs else "")


# ---------- formats ----------

def slide(item, idx, total, citation, by_id, size=(1080, 1350)):
    W, H = size
    dark = item.get("role") == "hook"
    bg, head, body_c, small = (MAROON, CREAM, BLUSH, BLUSH) if dark else (CREAM, RUST, INK, CLAY)
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    M = 130 if not dark else 100
    if not dark:
        notepad(d, W, H, 200, H - 40)
    d.text((M, 78), "steer", font=serif(56, weight=600), fill=head)
    d.text((W - 90, 96), f"{idx}/{total}", font=sans(28, 600), fill=small, anchor="ra")
    y = 300 if dark else 236
    if item.get("kicker"):
        d.text((M, y), item["kicker"].lower(), font=hand(46), fill=BLUSH if dark else RUST)
        y += 84
    y = draw_rich(d, (M, y), item["headline"], item.get("emph"), 96 if dark else 86, W - M - 90, head)
    if item.get("body"):
        draw_text(d, (M, y + 44), item["body"], sans(37, 500 if dark else 400), W - M - 90, body_c, 1.42)
    if item.get("role") == "cta":
        pill_y = H - 340
        d.rounded_rectangle([M, pill_y, W - 90, pill_y + 110], radius=55, fill=RUST)
        d.text(((M + W - 90) // 2, pill_y + 55), "Talk to a Steer doctor", font=sans(40, 700), fill=PAPER, anchor="mm")
        d.text((M, H - 180), "Lose well. Live well.", font=hand(54, bold=True), fill=RUST)
        d.text((W - 90, H - 160), "steerclub.com", font=sans(30, 600), fill=CLAY, anchor="ra")
    elif item.get("claims"):
        stamp(d, (M, H - 200), source_line(item["claims"], by_id, citation), sans(24, 600), RUST if not dark else BLUSH, W - M - 90)
    else:
        d.text((M, H - 150), "swipe →" if dark else "steerclub.com", font=hand(40) if dark else sans(28, 600), fill=small)
    return im


def static_post(item, citation, by_id, size=(1080, 1350)):
    W, H = size
    im = Image.new("RGB", size, CREAM)
    d = ImageDraw.Draw(im)
    notepad(d, W, H, 230, H - 40)
    M = 130
    d.rectangle([0, 0, W, 16], fill=RUST)
    d.text((M, 80), "steer", font=serif(60, weight=600), fill=RUST)
    d.text((W - 90, 96), "doctor's note", font=hand(40), fill=CLAY, anchor="ra")
    d.text((M, 246), "field notes from the research", font=hand(48), fill=RUST)
    y = draw_rich(d, (M, 330), item["headline"], item.get("emph"), 104, W - M - 90, RUST, 1.02)
    y = draw_text(d, (M, y + 50), item["sub"], sans(41), W - M - 90, INK, 1.42)
    stamp(d, (M, H - 300), source_line(item.get("claims", []), by_id, citation), sans(25, 600), RUST, W - M - 90)
    d.text((M, H - 140), "Before you start, hear it from a doctor, not a reel.", font=sans(28, 700), fill=INK)
    d.text((W - 90, H - 100), "steerclub.com", font=sans(28, 600), fill=CLAY, anchor="ra")
    return im


def reel_frame(item, idx, total, citation, by_id, size=(1080, 1920)):
    """The picture behind one reel scene; subtitles are burned in later from the voiceover."""
    W, H = size
    dark = item.get("role") in ("hook", "cta")
    bg, head, small = (MAROON, CREAM, BLUSH) if dark else (CREAM, RUST, CLAY)
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    M = 100 if dark else 140
    if not dark:
        notepad(d, W, H, 300, H - 60, margin_x=92, gap=70)
    d.text((M, 160), "steer", font=serif(68, weight=600), fill=head)
    for k in range(total):        # story-style progress marks
        x0 = 100 + k * ((W - 200) // total)
        d.rectangle([x0 + 6, 110, x0 + (W - 200) // total - 6, 116], fill=head if k <= idx else (CLAY if not dark else "#8a3a3a"))
    y = 600
    if item.get("role") == "hook":
        d.text((M, y - 120), "you asked", font=hand(64), fill=BLUSH)
    draw_rich(d, (M, y), item["on_screen"], item.get("emph"), 112, W - M - 100, head, 1.04)
    if item.get("claims"):
        stamp(d, (M, H - 330), source_line(item["claims"], by_id, citation), sans(30, 600), RUST, W - M - 100)
    if item.get("role") == "cta":
        d.text((M, H - 320), "Lose well. Live well. · steerclub.com", font=hand(52, bold=True), fill=BLUSH)
    return im


def render_all(draft, claims, citation, out_dir):
    out = pathlib.Path(out_dir)
    (out / "carousel").mkdir(parents=True, exist_ok=True)
    (out / "reel_frames").mkdir(parents=True, exist_ok=True)
    by_id = {c["id"]: c for c in claims}
    files = {"carousel": [], "static": None, "reel_frames": []}
    for i, s in enumerate(draft["carousel"], 1):
        p = out / "carousel" / f"slide_{i:02d}.png"
        slide(s, i, len(draft["carousel"]), citation, by_id).save(p, optimize=True)
        files["carousel"].append(str(p))
    p = out / "static.png"
    static_post(draft["static"], citation, by_id).save(p, optimize=True)
    files["static"] = str(p)
    # A 1:1 version of the static post (bonus: auto-resize).
    sq = Image.new("RGB", (1080, 1080), CREAM)
    sq.paste(Image.open(p).resize((864, 1080)), (108, 0))
    sq.save(out / "static_square.png", optimize=True)
    for i, s in enumerate(draft["reel"]):
        p = out / "reel_frames" / f"scene_{i + 1:02d}.png"
        reel_frame(s, i, len(draft["reel"]), citation, by_id).save(p, optimize=True)
        files["reel_frames"].append(str(p))
    return files
