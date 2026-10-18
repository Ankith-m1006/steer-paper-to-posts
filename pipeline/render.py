"""Create: carousel slides, a static post and reel frames as PNGs in Steer's brand.

Cream paper, rust serif headlines that mix upright and italic, a clean sans for body text,
lots of white space, and the source of the claim printed small on every slide that makes one.
"""
import pathlib

from PIL import Image, ImageDraw, ImageFont

FONTS = pathlib.Path(__file__).resolve().parents[1] / "fonts"
CREAM, RUST, MAROON, INK, CLAY, BLUSH, PAPER = "#F5EBDF", "#C04E2A", "#661414", "#351D1D", "#B58777", "#E6CBBD", "#F8F2EB"


def font(name, size, weight=None):
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight:
        try:
            f.set_variation_by_axes([weight] if name.startswith("Caveat") else [14, weight] if name == "Inter.ttf" else [100, weight])
        except Exception:
            pass
    return f


def serif(size, italic=False):
    return font("InstrumentSerif-Italic.ttf" if italic else "InstrumentSerif-Regular.ttf", size)


def sans(size, weight=400):
    return font("Inter.ttf", size, weight)


def hand(size):
    return font("Caveat.ttf", size, 500)


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
        line.append((w, f))
        x += (space if len(line) > 1 else 0) + wl
    if line:
        lines.append(line)
    return lines, space


def draw_rich(draw, xy, text, emph, size, width, fill, leading=1.02):
    x0, y = xy
    lines, space = rich_lines(draw, text, emph, size, width)
    for line in lines:
        x = x0
        for w, f in line:
            draw.text((x, y), w, font=f, fill=fill)
            x += draw.textlength(w, font=f) + space
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


def draw_text(draw, xy, text, f, width, fill, leading=1.38):
    x, y = xy
    for line in wrap(draw, text, f, width):
        draw.text((x, y), line, font=f, fill=fill)
        y += int(f.size * leading)
    return y


def source_line(claims, by_id, citation):
    locs = sorted({by_id[c]["loc"] for c in claims if c in by_id})
    return f"Source: {citation}" + (f" · {', '.join(locs)}" if locs else "")


def slide(item, idx, total, citation, by_id, size=(1080, 1350)):
    W, H = size
    dark = item.get("role") == "hook"
    bg, head, body_c, small = (MAROON, CREAM, BLUSH, BLUSH) if dark else (CREAM, RUST, INK, CLAY)
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    M = 96
    d.text((M, 84), "steer", font=serif(52), fill=head)
    d.text((W - M, 98), f"{idx}/{total}", font=sans(28, 500), fill=small, anchor="ra")
    y = 300 if dark else 250
    if item.get("kicker"):
        d.text((M, y), item["kicker"].lower(), font=hand(46), fill=head if dark else RUST)
        y += 80
    y = draw_rich(d, (M, y), item["headline"], item.get("emph"), 104 if dark else 92, W - 2 * M, head)
    if item.get("body"):
        d.line([(M, y + 34), (M + 90, y + 34)], fill=BLUSH if not dark else CLAY, width=3)
        draw_text(d, (M, y + 70), item["body"], sans(38), W - 2 * M, body_c)
    if item.get("role") == "cta":
        pill_y = H - 330
        d.rounded_rectangle([M, pill_y, W - M, pill_y + 110], radius=55, fill=RUST)
        d.text((W // 2, pill_y + 55), "Talk to a Steer doctor", font=sans(40, 600), fill=PAPER, anchor="mm")
        d.text((M, H - 170), "Lose well. Live well.", font=hand(52), fill=RUST)
        d.text((W - M, H - 150), "steerclub.com", font=sans(30, 500), fill=CLAY, anchor="ra")
    elif item.get("claims"):
        draw_text(d, (M, H - 150), source_line(item["claims"], by_id, citation), sans(24), W - 2 * M, small, 1.35)
    else:
        d.text((M, H - 150), "swipe →" if dark else "steerclub.com", font=sans(28, 500), fill=small)
    return im


def static_post(item, citation, by_id, size=(1080, 1350)):
    W, H = size
    im = Image.new("RGB", size, CREAM)
    d = ImageDraw.Draw(im)
    M = 96
    d.rectangle([0, 0, W, 18], fill=RUST)
    d.text((M, 90), "steer", font=serif(56), fill=RUST)
    d.text((M, 260), "field notes from the research", font=hand(48), fill=RUST)
    y = draw_rich(d, (M, 350), item["headline"], item.get("emph"), 112, W - 2 * M, RUST, 1.0)
    d.line([(M, y + 40), (M + 120, y + 40)], fill=CLAY, width=3)
    y = draw_text(d, (M, y + 80), item["sub"], sans(42), W - 2 * M, INK)
    d.rounded_rectangle([M, H - 290, W - M, H - 170], radius=26, fill=PAPER, outline=BLUSH, width=2)
    draw_text(d, (M + 34, H - 268), source_line(item.get("claims", []), by_id, citation), sans(26), W - 2 * M - 68, CLAY, 1.35)
    d.text((M, H - 120), "Before you start, hear it from a doctor, not a reel.", font=sans(28, 500), fill=INK)
    d.text((W - M, H - 120), "steerclub.com", font=sans(28, 500), fill=CLAY, anchor="ra")
    return im


def reel_frame(item, idx, total, citation, by_id, size=(1080, 1920)):
    """The picture behind one reel scene; subtitles are burned in later from the voiceover."""
    W, H = size
    dark = item.get("role") in ("hook", "cta")
    bg, head, small = (MAROON, CREAM, BLUSH) if dark else (CREAM, RUST, CLAY)
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    M = 100
    d.text((M, 150), "steer", font=serif(64), fill=head)
    for k in range(total):        # story-style progress marks
        x0 = M + k * ((W - 2 * M) // total)
        d.rectangle([x0 + 6, 110, x0 + (W - 2 * M) // total - 6, 116], fill=head if k <= idx else (CLAY if not dark else "#8a3a3a"))
    y = 620
    if item.get("role") == "hook":
        d.text((M, y - 110), "you asked", font=hand(60), fill=BLUSH)
    draw_rich(d, (M, y), item["on_screen"], item.get("emph"), 118, W - 2 * M, head, 1.02)
    if item.get("claims"):
        draw_text(d, (M, H - 300), source_line(item["claims"], by_id, citation), sans(30), W - 2 * M, small, 1.35)
    if item.get("role") == "cta":
        d.text((M, H - 300), "Lose well. Live well. · steerclub.com", font=sans(38, 500), fill=BLUSH)
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
