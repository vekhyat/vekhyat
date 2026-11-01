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


def header():
    W, H = 840, 320
    font = instantiateVariableFont(TTFont(FONT), {"wdth": 62, "wght": 820})

    # Name card: two lines of condensed navy capitals, sized to fill the card's width or height, whichever binds.
    cw, ch, cx, cy = 404, 236, 60, 44
    pad, url_h, cap_ratio, gap = 28, 26, 0.73, 0.22
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
    name = (f'<g fill="{NAVY}"><path transform="translate({cx+pad} {y1})" d="{line1}"/>'
            f'<path transform="translate({cx+pad} {y2})" d="{line2}"/></g>')
    name += text(cx + cw - pad, cy + ch - pad + 6, "vekhyat.github.io/portfolio", 13, CREAM_INK, anchor="end")
    name_card = card(cx, cy, cw, ch, -2.4, "card name", name)

    # Second card: what I do, in plain type.
    sw, sh, sx, sy = 272, 142, 516, 126
    lines = [("Data Science & AI undergraduate", 15, NAVY, 700),
             ("Thapar Institute of Engineering", 14, CREAM_INK, 400),
             ("& Technology, Patiala", 14, CREAM_INK, 400)]
    inner, ly = "", sy + 44
    for value, fs, fill, weight in lines:
        inner += text(sx + 26, ly, value, fs, fill, weight)
        ly += 22 if weight == 700 else 19
    inner += f'<path d="M{sx+26} {sy+sh-34} H{sx+sw-26}" stroke="{CREAM_EDGE}"/>'
    inner += text(sx + 26, sy + sh - 15, "mobile apps, desktop tools, ML experiments", 12, CREAM_INK)
    about_card = card(sx, sy, sw, sh, 1.6, "card about", inner)

    # One red pin through the top-left corner of the name card.
    px, py = cx + 22, cy + 18
    pin = (f'<g class="pin" transform-origin="{px} {py}">'
           f'<ellipse cx="{px+4}" cy="{py+5}" rx="7" ry="4" fill="{BOARD_EDGE}" opacity=".5"/>'
           f'<circle cx="{px}" cy="{py}" r="7.5" fill="{RED}"/>'
           f'<circle cx="{px-2.5}" cy="{py-2.5}" r="2.2" fill="#e8a295" opacity=".9"/></g>')

    # Scratched board: stretched noise as faint chalk streaks, then a soft vignette.
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
    # Corner brackets, as on the portfolio board.
    k = 22
    brackets = (f'<path d="M28 {28+k} V28 H{28+k} M{W-28-k} 28 H{W-28} V{28+k} '
                f'M28 {H-28-k} V{H-28} H{28+k} M{W-28-k} {H-28} H{W-28} V{H-28-k}" '
                f'fill="none" stroke="{CHALK}" stroke-opacity=".45" stroke-width="1.5"/>')

    css = ("@keyframes land{from{opacity:0;transform:translateY(-22px)}to{opacity:1;transform:none}}"
           "@keyframes press{from{opacity:0;transform:scale(2.2)}to{opacity:1;transform:none}}"
           ".name{animation:land .55s cubic-bezier(.2,.8,.3,1) both}"
           ".about{animation:land .55s cubic-bezier(.2,.8,.3,1) .22s both}"
           ".pin{animation:press .3s cubic-bezier(.3,1.4,.5,1) .5s both}"
           "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    title = "Vekhyat Jain. Data Science & AI undergraduate at Thapar Institute of Engineering & Technology, Patiala. Builds mobile apps, desktop tools, and ML experiments."
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">\n'
           f'<title id="t">{escape(title)}</title><desc id="d">A cream name card and a smaller card pinned to a scratched green board.</desc>\n'
           f'<style>{css}</style>\n{defs}\n{board}{brackets}\n{name_card}\n{about_card}\n{pin}\n</svg>\n')
    (ASSETS / "header.svg").write_text(svg, encoding="utf-8")
    return len(svg)


if __name__ == "__main__":
    print(f"Built assets/header.svg ({header():,} bytes)")
