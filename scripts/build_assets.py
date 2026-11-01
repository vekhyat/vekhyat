# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools>=4.50", "brotli>=1.1"]
# ///
"""Build the profile header: a cream name card pinned to the green board from vekhyat.github.io/portfolio.

Run with:  uv run scripts/build_assets.py
The name is outlined from Anybody (OFL, assets/fonts) so the SVG needs no web font.
The CSS animation runs once; the final state is the default, so scripts/build_static.py can strip it.
"""
from pathlib import Path
from html import escape

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FONT = ASSETS / "fonts" / "Anybody-Variable.woff2"

BOARD, BOARD_EDGE = "#2c4a40", "#1b312a"
CREAM, CREAM_EDGE, CREAM_INK = "#f2eee4", "#d8d0c2", "#6b665c"
NAVY, RED, CHALK = "#1a2744", "#c4452d", "#d6e8dc"


def outline(font, text, size):
    """Return (svg path d, advance width in px) for text at the given px size."""
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    scale = size / font["head"].unitsPerEm
    kern = {}
    if "kern" in font:
        for table in font["kern"].kernTables:
            kern.update(table.kernTable)
    d, x = [], 0.0
    names = [cmap[ord(c)] for c in text]
    for i, name in enumerate(names):
        pen = SVGPathPen(glyph_set)
        # Flip y (font units go up, SVG goes down) and place the pen at the current x.
        glyph_set[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, 0)))
        if (cmd := pen.getCommands()):
            d.append(cmd)
        x += hmtx[name][0] * scale
        if i + 1 < len(names):
            x += kern.get((name, names[i + 1]), 0) * scale
    return " ".join(d), x


def text(x, y, value, size, fill, weight=400, anchor="start", family="Arial,Helvetica,sans-serif"):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')


def card(x, y, w, h, angle, cls, inner):
    """A cream card with a soft board shadow, rotated about its centre. The animated group sits inside the rotation."""
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


def rotated(x, y, w, h, angle, px, py):
    """Where a point on an unrotated card ends up after the card's rotation about its centre."""
    import math
    cx, cy = x + w / 2, y + h / 2
    a = math.radians(angle)
    dx, dy = px - cx, py - cy
    return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)


PROJECTS = [
    ("Ingradient", "What's in your food?",
     ["Scan a label or barcode.", "OCR on the phone, sourced", "verdicts, encrypted history."],
     "React Native, Expo, FastAPI"),
    ("SatQuery AI", "Ask a satellite a question.",
     ["Change detection, optical", "against SAR, and a trace", "of how each answer formed."],
     "Python, FastAPI, React, Rasterio"),
    ("Auralis", "Lossless audio from a link.",
     ["Search music and download", "FLAC from a streaming link,", "in a Go desktop app."],
     "Go, Wails, TypeScript"),
    ("Git Guide", "Git, explained visually.",
     ["Commands, branches,", "remotes, and undo. Quick", "or detailed, fully offline."],
     "HTML, CSS, JavaScript"),
]


def header():
    W, H = 840, 580
    font = instantiateVariableFont(TTFont(FONT), {"wdth": 62, "wght": 820})
    cards, pins, threads, css = [], [], [], []

    # Name card, top left. Its bottom pin is the hub every thread runs from.
    cw, ch, cx, cy = 380, 206, 40, 36
    pad, url_h, cap_ratio, gap = 26, 24, 0.73, 0.2
    probe = 100
    _, w1 = outline(font, "VEKHYAT", probe)
    _, w2 = outline(font, "JAIN", probe)
    by_width = probe * (cw - 2 * pad) / max(w1, w2)
    by_height = (ch - 2 * pad - url_h) / ((2 + gap) * cap_ratio)
    size = round(min(by_width, by_height), 1)
    line1, _ = outline(font, "VEKHYAT", size)
    line2, _ = outline(font, "JAIN", size)
    cap = size * cap_ratio
    y1 = cy + pad + cap
    y2 = y1 + cap * (1 + gap)
    inner = (f'<g fill="{NAVY}"><path transform="translate({cx+pad} {y1})" d="{line1}"/>'
             f'<path transform="translate({cx+pad} {y2})" d="{line2}"/></g>')
    inner += text(cx + pad, cy + ch - pad + 6, "vekhyat.github.io/portfolio", 13, CREAM_INK)
    name_angle = -2.2
    cards.append(card(cx, cy, cw, ch, name_angle, "card c0", inner))
    css.append(".c0{animation:land .55s cubic-bezier(.2,.8,.3,1) 0s both}")
    px, py = rotated(cx, cy, cw, ch, name_angle, cx + 22, cy + 18)
    pins.append(pin(px, py, "pin p0")); css.append(".p0{animation:press .3s cubic-bezier(.3,1.4,.5,1) .45s both}")
    hx, hy = rotated(cx, cy, cw, ch, name_angle, cx + cw - 22, cy + ch - 18)
    pins.append(pin(hx, hy, "pin p1")); css.append(".p1{animation:press .3s cubic-bezier(.3,1.4,.5,1) .55s both}")

    # About card, top right.
    sw, sh, sx, sy = 300, 150, 500, 70
    inner = (text(sx + 26, sy + 46, "Data Science & AI undergraduate", 15, NAVY, 700)
             + text(sx + 26, sy + 68, "Thapar Institute of Engineering", 14, CREAM_INK)
             + text(sx + 26, sy + 87, "& Technology, Patiala", 14, CREAM_INK)
             + f'<path d="M{sx+26} {sy+sh-38} H{sx+sw-26}" stroke="{CREAM_EDGE}"/>'
             + text(sx + 26, sy + sh - 17, "mobile apps, desktop tools, ML experiments", 12, CREAM_INK))
    cards.append(card(sx, sy, sw, sh, 1.7, "card c1", inner))
    css.append(".c1{animation:land .55s cubic-bezier(.2,.8,.3,1) .2s both}")
    px, py = rotated(sx, sy, sw, sh, 1.7, sx + sw - 22, sy + 18)
    pins.append(pin(px, py, "pin p2")); css.append(".p2{animation:press .3s cubic-bezier(.3,1.4,.5,1) .65s both}")

    # Four project cards along the bottom, each tied to the hub with red thread.
    pw, ph, py0 = 184, 176, 352
    angles = [-1.6, 1.3, -0.9, 1.8]
    for i, (title, hook, lines, tech) in enumerate(PROJECTS):
        x = 40 + i * (pw + 20)
        tsize = 30
        d, tw = outline(font, title.upper(), tsize)
        if tw > pw - 32:
            tsize = round(tsize * (pw - 32) / tw, 1)
            d, tw = outline(font, title.upper(), tsize)
        inner = f'<path fill="{NAVY}" transform="translate({x+16} {py0+48})" d="{d}"/>'
        inner += text(x + 16, py0 + 74, hook, 13, NAVY, 700)
        for j, line in enumerate(lines):
            inner += text(x + 16, py0 + 96 + j * 15, line, 11.5, CREAM_INK)
        inner += f'<path d="M{x+16} {py0+ph-36} H{x+pw-16}" stroke="{CREAM_EDGE}"/>'
        inner += text(x + 16, py0 + ph - 16, tech, 11, CREAM_INK)
        delay = 0.5 + i * 0.18
        cards.append(card(x, py0, pw, ph, angles[i], f"card c{i+2}", inner))
        css.append(f".c{i+2}{{animation:land .5s cubic-bezier(.2,.8,.3,1) {delay:.2f}s both}}")
        qx, qy = rotated(x, py0, pw, ph, angles[i], x + pw / 2, py0 + 16)
        pins.append(pin(qx, qy, f"pin p{i+3}"))
        css.append(f".p{i+3}{{animation:press .3s cubic-bezier(.3,1.4,.5,1) {delay+.4:.2f}s both}}")
        # Thread: a slack curve from the hub pin to this card's pin. Default state is fully drawn.
        mx, my = (hx + qx) / 2, (hy + qy) / 2 + 26
        threads.append(f'<path class="thread t{i}" d="M{hx:.1f} {hy:.1f} Q{mx:.1f} {my:.1f} {qx:.1f} {qy:.1f}" '
                       f'fill="none" stroke="{RED}" stroke-width="2" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0"/>')
        css.append(f".t{i}{{animation:draw .6s ease-out {1.3+i*.22:.2f}s both}}")

    defs = ('<defs>'
            '<filter id="scratch" x="0" y="0" width="100%" height="100%">'
            '<feTurbulence type="fractalNoise" baseFrequency="0.012 0.7" numOctaves="2" seed="7" result="streak"/>'
            '<feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="1" seed="3" result="grain"/>'
            '<feBlend in="streak" in2="grain" mode="screen" result="n"/>'
            '<feColorMatrix in="n" type="matrix" values="0 0 0 0 .84  0 0 0 0 .91  0 0 0 0 .86  0 0 0 .14 -.05"/>'
            '</filter>'
            f'<radialGradient id="vig" cx="50%" cy="45%" r="70%"><stop offset="0" stop-color="{BOARD}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{BOARD_EDGE}" stop-opacity=".75"/></radialGradient>'
            '</defs>')
    board = (f'<rect width="{W}" height="{H}" rx="8" fill="{BOARD}"/>'
             f'<rect width="{W}" height="{H}" rx="8" filter="url(#scratch)"/>'
             f'<rect width="{W}" height="{H}" rx="8" fill="url(#vig)"/>')
    k = 22
    brackets = (f'<path d="M28 {28+k} V28 H{28+k} M{W-28-k} 28 H{W-28} V{28+k} '
                f'M28 {H-28-k} V{H-28} H{28+k} M{W-28-k} {H-28} H{W-28} V{H-28-k}" '
                f'fill="none" stroke="{CHALK}" stroke-opacity=".45" stroke-width="1.5"/>')

    css = ["@keyframes land{from{opacity:0;transform:translateY(-22px)}to{opacity:1;transform:none}}",
           "@keyframes press{from{opacity:0;transform:scale(2.2)}to{opacity:1;transform:none}}",
           "@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}",
           *css,
           "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"]
    # Thread shadow sits under the thread; both are drawn by the same dash animation via the shared class.
    thread_layer = ("".join(t.replace('class="thread', 'class="thread shadow').replace(f'stroke="{RED}"', f'transform="translate(2 4)" stroke="{BOARD_EDGE}" opacity=".55"')
                            for t in threads) + "".join(threads))
    title = ("Vekhyat Jain. Data Science & AI undergraduate at Thapar Institute of Engineering & Technology, Patiala. "
             "Pinned projects: Ingradient, SatQuery AI, Auralis, and Git Guide.")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">\n'
           f'<title id="t">{escape(title)}</title><desc id="d">Cream cards pinned to a scratched green board, joined by red thread.</desc>\n'
           f'<style>{"".join(css)}</style>\n{defs}\n{board}{brackets}\n'
           f'{"".join(cards)}\n{thread_layer}\n{"".join(pins)}\n</svg>\n')
    (ASSETS / "header.svg").write_text(svg, encoding="utf-8")
    return len(svg)


if __name__ == "__main__":
    print(f"Built assets/header.svg ({header():,} bytes)")
