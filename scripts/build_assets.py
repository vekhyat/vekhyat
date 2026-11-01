# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools>=4.50", "brotli>=1.1"]
# ///
"""Build the profile board: a name card, an about card, and one pinned card per pinned repository.

    uv run scripts/build_assets.py            # reads dist/public-data.json
    uv run scripts/build_assets.py --data f   # another snapshot

Writes dist/header.svg, dist/card-N.svg, and the block between the pinned markers in README.md.
The name and card titles are outlined from Anybody (OFL, assets/fonts) so no web font is needed.
Every CSS animation runs once and the final state is the default, so scripts/build_static.py can strip it.
"""
import argparse
import json
import math
import sys
from datetime import date
from html import escape
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parents[1]
ASSETS, DIST = ROOT / "assets", ROOT / "dist"
FONT = ASSETS / "fonts" / "Anybody-Variable.woff2"
COPY = json.loads((ROOT / "scripts" / "pinned_copy.json").read_text(encoding="utf-8"))
MEASURE_FONTS = [Path("/usr/share/fonts/liberation/LiberationSans-Regular.ttf"),
                 Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")]  # Arial-metric twin, for wrapping

BOARD, BOARD_EDGE = "#2c4a40", "#1b312a"
CREAM, CREAM_EDGE, CREAM_INK = "#f2eee4", "#d8d0c2", "#6b665c"
NAVY, RED, CHALK = "#1a2744", "#c4452d", "#d6e8dc"
PORTFOLIO = "https://vekhyat.github.io/portfolio/"
BOARD_W, TILE_W, TILE_H = 840, 200, 250
MARK_START, MARK_END = "<!-- pinned:start -->", "<!-- pinned:end -->"
HEADER_ALT = ("Vekhyat Jain. Mobile apps, desktop tools, and ML experiments. "
              "Exploring machine learning, theoretical computer science, and programming languages.")

KEYFRAMES = ("@keyframes land{from{opacity:0;transform:translateY(-22px)}to{opacity:1;transform:none}}"
             "@keyframes press{from{opacity:0;transform:scale(2.2)}to{opacity:1;transform:none}}"
             "@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}")


# --- text -------------------------------------------------------------------

def outline(font, text, size):
    """(svg path d, advance width px) for text set in the display font at a pixel size."""
    glyph_set, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    scale = size / font["head"].unitsPerEm
    kern = {}
    if "kern" in font:
        for table in font["kern"].kernTables:
            kern.update(table.kernTable)
    d, x = [], 0.0
    names = [cmap.get(ord(c), cmap[ord("?")]) for c in text]
    for i, name in enumerate(names):
        pen = SVGPathPen(glyph_set)
        glyph_set[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, 0)))
        if (cmd := pen.getCommands()):
            d.append(cmd)
        x += hmtx[name][0] * scale
        if i + 1 < len(names):
            x += kern.get((name, names[i + 1]), 0) * scale
    return " ".join(d), x


class Measure:
    """Width of body text in the sans the viewer will most likely have (Arial or a metric twin)."""
    def __init__(self):
        self.widths = None
        for path in MEASURE_FONTS:
            if path.exists():
                f = TTFont(path)
                cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
                self.widths = {chr(c): hmtx[g][0] / upm for c, g in cmap.items()}
                break

    def width(self, s, size, bold=False):
        if not self.widths:
            return len(s) * size * (0.56 if bold else 0.5)
        return sum(self.widths.get(c, 0.55) for c in s) * size * (1.07 if bold else 1)

    def wrap(self, s, size, max_w, max_lines):
        lines, line = [], ""
        for word in s.split():
            trial = (line + " " + word).strip()
            if self.width(trial, size) <= max_w or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            while self.width(lines[-1] + "…", size) > max_w and " " in lines[-1]:
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
            lines[-1] += "…"
        return lines

    def fit(self, s, size, max_w, bold=False):
        if self.width(s, size, bold) <= max_w:
            return s
        while s and self.width(s + "…", size, bold) > max_w:
            s = s[:-1].rstrip(" ,.;:")
        return s + "…"


def text(x, y, value, size, fill, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')


# --- board parts ------------------------------------------------------------

def rotated(x, y, w, h, angle, px, py):
    cx, cy = x + w / 2, y + h / 2
    a = math.radians(angle)
    dx, dy = px - cx, py - cy
    return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)


def card(x, y, w, h, angle, cls, inner):
    cx, cy = x + w / 2, y + h / 2
    return (f'<g transform="rotate({angle} {cx} {cy})"><g class="{cls}">'
            f'<rect x="{x+3}" y="{y+6}" width="{w}" height="{h}" rx="3" fill="{BOARD_EDGE}" opacity=".55"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{CREAM}" stroke="{CREAM_EDGE}"/>'
            f'{inner}</g></g>')


def pin(x, y, cls):
    return (f'<g class="{cls}" transform-origin="{x} {y}">'
            f'<ellipse cx="{x+4}" cy="{y+5}" rx="7" ry="4" fill="{BOARD_EDGE}" opacity=".5"/>'
            f'<circle cx="{x}" cy="{y}" r="7" fill="{RED}"/>'
            f'<circle cx="{x-2.3}" cy="{y-2.3}" r="2" fill="#e8a295" opacity=".9"/></g>')


def thread(x1, y1, x2, y2, cls, sag=26):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + sag
    d = f"M{x1:.1f} {y1:.1f} Q{mx:.1f} {my:.1f} {x2:.1f} {y2:.1f}"
    common = 'fill="none" stroke-width="2" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0"'
    return (f'<path class="{cls}" d="{d}" transform="translate(2 4)" stroke="{BOARD_EDGE}" opacity=".55" {common}/>'
            f'<path class="{cls}" d="{d}" stroke="{RED}" {common}/>')


def star(x, y, r=5):
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36)
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{x + rr * math.cos(a):.1f},{y + rr * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{RED}"/>'


def board_svg(path, W, H, title, desc, body, css, brackets=True):
    defs = ('<defs><filter id="scratch" x="0" y="0" width="100%" height="100%">'
            '<feTurbulence type="fractalNoise" baseFrequency="0.012 0.7" numOctaves="2" seed="7" result="streak"/>'
            '<feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="1" seed="3" result="grain"/>'
            '<feBlend in="streak" in2="grain" mode="screen" result="n"/>'
            '<feColorMatrix in="n" type="matrix" values="0 0 0 0 .84  0 0 0 0 .91  0 0 0 0 .86  0 0 0 .14 -.05"/>'
            '</filter>'
            f'<radialGradient id="vig" cx="50%" cy="45%" r="70%"><stop offset="0" stop-color="{BOARD}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{BOARD_EDGE}" stop-opacity=".75"/></radialGradient></defs>')
    board = (f'<rect width="{W}" height="{H}" rx="8" fill="{BOARD}"/>'
             f'<rect width="{W}" height="{H}" rx="8" filter="url(#scratch)"/>'
             f'<rect width="{W}" height="{H}" rx="8" fill="url(#vig)"/>')
    k = 22
    marks = (f'<path d="M28 {28+k} V28 H{28+k} M{W-28-k} 28 H{W-28} V{28+k} '
             f'M28 {H-28-k} V{H-28} H{28+k} M{W-28-k} {H-28} H{W-28} V{H-28-k}" '
             f'fill="none" stroke="{CHALK}" stroke-opacity=".45" stroke-width="1.5"/>') if brackets else ""
    style = KEYFRAMES + "".join(css) + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">\n'
           f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>\n'
           f'<style>{style}</style>\n{defs}\n{board}{marks}\n{body}\n</svg>\n')
    path.write_text(svg, encoding="utf-8")
    return len(svg)


# --- layout -----------------------------------------------------------------

def rows_for(n):
    """Tile indices per row: one row up to four pins, otherwise rows of three."""
    per = n if n <= 4 else 3
    return [list(range(i, min(i + per, n))) for i in range(0, n, per)]


def header(font, pinned):
    W, H = BOARD_W, 330
    cards, pins, threads, css = [], [], [], []

    cw, ch, cx, cy = 380, 206, 40, 40
    pad, url_h, cap_ratio, gap = 26, 24, 0.73, 0.2
    _, w1 = outline(font, "VEKHYAT", 100)
    _, w2 = outline(font, "JAIN", 100)
    size = round(min(100 * (cw - 2 * pad) / max(w1, w2), (ch - 2 * pad - url_h) / ((2 + gap) * cap_ratio)), 1)
    line1, _ = outline(font, "VEKHYAT", size)
    line2, _ = outline(font, "JAIN", size)
    cap = size * cap_ratio
    y1 = cy + pad + cap
    y2 = y1 + cap * (1 + gap)
    inner = (f'<g fill="{NAVY}"><path transform="translate({cx+pad} {y1})" d="{line1}"/>'
             f'<path transform="translate({cx+pad} {y2})" d="{line2}"/></g>')
    inner += text(cx + pad, cy + ch - pad + 6, "vekhyat.github.io/portfolio", 13, CREAM_INK)
    angle = -2.2
    cards.append(card(cx, cy, cw, ch, angle, "c0", inner))
    css.append(".c0{animation:land .55s cubic-bezier(.2,.8,.3,1) 0s both}")
    px, py = rotated(cx, cy, cw, ch, angle, cx + 22, cy + 18)
    pins.append(pin(px, py, "p0")); css.append(".p0{animation:press .3s cubic-bezier(.3,1.4,.5,1) .45s both}")
    hx, hy = rotated(cx, cy, cw, ch, angle, cx + cw - 22, cy + ch - 18)
    pins.append(pin(hx, hy, "p1")); css.append(".p1{animation:press .3s cubic-bezier(.3,1.4,.5,1) .55s both}")

    sw, sh, sx, sy = 300, 150, 500, 76
    inner = (text(sx + 26, sy + 46, "Mobile apps, desktop tools,", 15, NAVY, 700)
             + text(sx + 26, sy + 66, "ML experiments", 15, NAVY, 700)
             + text(sx + 26, sy + 90, "Exploring machine learning, theoretical", 12.5, CREAM_INK)
             + text(sx + 26, sy + 107, "computer science, and programming languages", 12.5, CREAM_INK)
             + f'<path d="M{sx+26} {sy+sh-32} H{sx+sw-26}" stroke="{CREAM_EDGE}"/>'
             + text(sx + 26, sy + sh - 13, "Python, C++, TypeScript, Go", 12, CREAM_INK))
    cards.append(card(sx, sy, sw, sh, 1.7, "c1", inner))
    css.append(".c1{animation:land .55s cubic-bezier(.2,.8,.3,1) .2s both}")
    px, py = rotated(sx, sy, sw, sh, 1.7, sx + sw - 22, sy + 18)
    pins.append(pin(px, py, "p2")); css.append(".p2{animation:press .3s cubic-bezier(.3,1.4,.5,1) .65s both}")

    first_row = rows_for(len(pinned))[0]
    for i in first_row:
        tx = W * (i + 0.5) / len(first_row)
        threads.append(thread(hx, hy, tx, H + 6, f"t{i}", sag=18))
        css.append(f".t{i}{{animation:draw .6s ease-out {1.1+i*.2:.2f}s both}}")

    names = ", ".join(r["name"] for r in pinned)
    return board_svg(DIST / "header.svg", W, H, HEADER_ALT,
                     f"A cream name card and an about card pinned to a scratched green board, with red threads leading down to the pinned repositories: {names}.",
                     "".join(cards) + "".join(threads) + "".join(pins), css)


def tile(font, measure, i, repo):
    W, H = TILE_W, TILE_H
    pw, ph, x, y = 186, 196, 7, 34
    pad = 13
    inner_w = pw - 2 * pad
    angle = [-1.6, 1.3, -0.9, 1.8, -1.2, 1.5][i % 6]
    copy = COPY.get(repo["name"].lower())
    if copy:
        hook, lines = copy["hook"], list(copy["lines"])
    else:
        first, _, rest = (repo.get("description") or "").strip().partition(". ")
        hook = first.rstrip(".") + "." if first else ""
        lines = measure.wrap(rest, 11.5, inner_w, 4)
    hook = measure.fit(hook, 12.5, inner_w, bold=True)
    lines = [measure.fit(l, 11.5, inner_w) for l in lines[:4]]
    if "…" in hook + "".join(lines):
        print(f"note: copy for {repo['name']} was shortened to fit; see scripts/pinned_copy.json", file=sys.stderr)
    title = (copy or {}).get("title") or repo["name"].replace("-", " ").replace("_", " ")

    tsize = 30
    d, tw = outline(font, title.upper(), tsize)
    if tw > inner_w:
        tsize = round(tsize * inner_w / tw, 1)
        d, tw = outline(font, title.upper(), tsize)
    lx = x + pad
    body = f'<path fill="{NAVY}" transform="translate({lx} {y+52})" d="{d}"/>'
    body += text(lx, y + 78, hook, 12.5, NAVY, 700)
    for j, line in enumerate(lines):
        body += text(lx, y + 100 + j * 15, line, 11.5, CREAM_INK)
    body += f'<path d="M{lx} {y+ph-36} H{x+pw-pad}" stroke="{CREAM_EDGE}"/>'
    body += text(lx, y + ph - 16, repo.get("language") or "", 11, CREAM_INK)
    if repo.get("stars"):
        body += star(x + pw - pad - 6, y + ph - 20) + text(x + pw - pad - 14, y + ph - 16, str(repo["stars"]), 11, CREAM_INK, anchor="end")

    delay = 0.5 + i * 0.18
    inner = card(x, y, pw, ph, angle, "c0", body)
    css = [f".c0{{animation:land .5s cubic-bezier(.2,.8,.3,1) {delay:.2f}s both}}"]
    qx, qy = rotated(x, y, pw, ph, angle, x + pw / 2, y + 16)
    inner += thread(W / 2, -6, qx, qy, "t0", sag=4)
    css.append(f".t0{{animation:draw .35s ease-out {1.6+i*.2:.2f}s both}}")
    inner += pin(qx, qy, "p0")
    css.append(f".p0{{animation:press .3s cubic-bezier(.3,1.4,.5,1) {delay+.4:.2f}s both}}")
    alt = f"{repo['name']}. {hook} {' '.join(lines)}".strip()
    if repo.get("language"):
        alt += f" {repo['language']}."
    size = board_svg(DIST / f"card-{i+1}.svg", W, H, alt,
                     "A pinned project card on the green board, tied by red thread to the name card above.", inner, css, brackets=False)
    return size, alt


def lately(font, measure, data):
    """A strip of three notes: the latest commit, the contribution streak, and the language mix."""
    W, H = BOARD_W, 250
    parts, css, pins = [], [], []

    def note(i, x, y, w, h, angle, inner, pin_at):
        parts.append(card(x, y, w, h, angle, f"n{i}", inner))
        css.append(f".n{i}{{animation:land .5s cubic-bezier(.2,.8,.3,1) {i*.18:.2f}s both}}")
        qx, qy = rotated(x, y, w, h, angle, *pin_at)
        pins.append(pin(qx, qy, f"q{i}"))
        css.append(f".q{i}{{animation:press .3s cubic-bezier(.3,1.4,.5,1) {.4+i*.18:.2f}s both}}")

    # Latest commit.
    x, y, w, h, pad = 40, 40, 318, 170, 22
    c = data.get("latest_commit")
    inner = text(x + pad, y + 32, "Latest commit", 12, CREAM_INK)
    if c:
        d, tw = outline(font, c["repo"].upper(), 26)
        if tw > w - 2 * pad:
            d, tw = outline(font, c["repo"].upper(), round(26 * (w - 2 * pad) / tw, 1))
        inner += f'<path fill="{NAVY}" transform="translate({x+pad} {y+66})" d="{d}"/>'
        lines = measure.wrap(c["message"], 13, w - 2 * pad, 2)
        for j, line in enumerate(lines):
            inner += text(x + pad, y + 94 + j * 18, line, 13, NAVY, 700 if j == 0 else 400)
        when = date.fromisoformat(c["date"])
        inner += f'<path d="M{x+pad} {y+h-38} H{x+w-pad}" stroke="{CREAM_EDGE}"/>'
        inner += text(x + pad, y + h - 17, f"{when.day} {when.strftime('%b %Y')}", 11.5, CREAM_INK)
    else:
        inner += text(x + pad, y + 70, "Nothing public yet.", 13, NAVY, 700)
    note(0, x, y, w, h, -1.4, inner, (x + w - 20, y + 18))

    # Streak ticket: a cream ticket with a notch on each side.
    st = data["streaks"]
    x, y, w, h = 384, 40, 196, 170
    big, bw = outline(font, str(st["current"]), 74)
    inner = (f'<circle cx="{x}" cy="{y+h/2}" r="9" fill="{BOARD}"/><circle cx="{x+w}" cy="{y+h/2}" r="9" fill="{BOARD}"/>'
             f'<path d="M{x+12} {y+h/2} H{x+w-12}" stroke="{CREAM_EDGE}" stroke-dasharray="4 4"/>')
    inner += f'<path fill="{RED}" transform="translate({x+22} {y+76})" d="{big}"/>'
    inner += text(x + 22 + bw + 10, y + 76, "day streak" if st["current"] != 1 else "day streak", 13, NAVY, 700)
    inner += text(x + 22, y + 118, f"longest run {st['longest']} days", 11.5, CREAM_INK)
    inner += text(x + 22, y + 136, f"{st['total']:,} contributions this year", 11.5, CREAM_INK)
    inner += text(x + 22, y + 154, f"active on {st['active_days']} of the last 365 days", 11.5, CREAM_INK)
    note(1, x, y, w, h, 1.3, inner, (x + w - 20, y + 18))

    # Languages by repository count.
    langs = sorted(data["repository_primary_languages"].items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    x, y, w, h, pad = 606, 40, 194, 170, 18
    inner = text(x + pad, y + 32, "Languages, by repository", 12, CREAM_INK)
    top = max((n for _, n in langs), default=1)
    bar_x, bar_w = x + pad + 76, w - 2 * pad - 76
    for j, (lang, n) in enumerate(langs):
        yy = y + 58 + j * 24
        inner += text(x + pad, yy + 4, measure.fit(lang, 11.5, 70), 11.5, NAVY, 700 if j == 0 else 400)
        inner += f'<rect x="{bar_x}" y="{yy-4}" width="{bar_w}" height="8" rx="2" fill="{CREAM_EDGE}"/>'
        inner += (f'<rect class="bar b{j}" x="{bar_x}" y="{yy-4}" width="{bar_w*n/top:.1f}" height="8" rx="2" '
                  f'fill="{RED if j == 0 else NAVY}" transform-origin="{bar_x} {yy}"/>')
        css.append(f".b{j}{{animation:grow .5s ease-out {1.1+j*.08:.2f}s both}}")
    note(2, x, y, w, h, -0.9, inner, (x + w - 20, y + 18))

    css.insert(0, "@keyframes grow{from{transform:scaleX(0)}to{transform:none}}")
    desc = f"Latest commit, a {st['current']}-day contribution streak, and the top languages, pinned to the green board."
    return board_svg(DIST / "lately.svg", W, H, f"Lately. Snapshot {data['snapshot']}.", desc,
                     "".join(parts) + "".join(pins), css, brackets=False)


def readme_block(pinned, alts):
    def picture(src, width, alt):
        return (f'<picture><source media="(prefers-reduced-motion: reduce)" srcset="./dist/static/{src}">'
                f'<img src="./dist/{src}" width="{width}" alt="{escape(alt, quote=True)}"></picture>')
    out = [MARK_START, f'<a href="{PORTFOLIO}">{picture("header.svg", "100%", HEADER_ALT)}</a>']
    for row in rows_for(len(pinned)):
        width = f"{96 // len(row)}%"
        out.append('<p align="center">')
        out.extend(f'<a href="{pinned[i]["url"]}">{picture(f"card-{i+1}.svg", width, alts[i])}</a>' for i in row)
        out.append("</p>")
    out.append(MARK_END)
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=DIST / "public-data.json")
    a = p.parse_args()
    data = json.loads(a.data.read_text(encoding="utf-8"))
    pinned = data.get("pinned") or []
    if not pinned:
        raise SystemExit("No pinned repositories in the snapshot; run scripts/update_activity.py first")
    font = instantiateVariableFont(TTFont(FONT), {"wdth": 62, "wght": 820})
    measure = Measure()
    DIST.mkdir(exist_ok=True)
    for folder in (DIST, DIST / "static"):
        for old in folder.glob("card-*.svg"):
            old.unlink()
    total = header(font, pinned) + lately(font, measure, data)
    alts = []
    for i, repo in enumerate(pinned):
        size, alt = tile(font, measure, i, repo)
        total += size
        alts.append(alt)
    readme = ROOT / "README.md"
    s = readme.read_text(encoding="utf-8")
    start, end = s.index(MARK_START), s.index(MARK_END) + len(MARK_END)
    readme.write_text(s[:start] + readme_block(pinned, alts) + s[end:], encoding="utf-8")
    print(f"Built dist/header.svg, dist/lately.svg and {len(pinned)} pinned cards ({total:,} bytes); README block updated")


if __name__ == "__main__":
    main()
