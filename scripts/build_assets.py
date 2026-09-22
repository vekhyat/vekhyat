"""Build the authored SVGs. Python standard library; no browser scripts."""
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BG, FG, MUTED, ACCENT, LINE = "#0b0f10", "#eef3ef", "#a9b8b0", "#b6f36b", "#2b3830"

def text(x, y, value, size=18, color=FG, weight=400, mono=False):
    family = "'Courier New',monospace" if mono else "Arial,Helvetica,sans-serif"
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="{family}" font-size="{size}" font-weight="{weight}">{escape(value)}</text>'

def svg(name, w, h, title, body, css=""):
    base = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(title)}. All essential text remains visible without animation.</desc>
<style>{css}
@media (prefers-reduced-motion:reduce) {{ * {{ animation:none!important; }} }}
</style>
<rect width="{w}" height="{h}" rx="8" fill="{BG}"/>
{body}
</svg>'''
    (ASSETS / name).write_text(base, encoding="utf-8")

def header(mobile=False):
    w,h = (400,264) if mobile else (840,292)
    x = 24 if mobile else 40
    name_y = 72 if mobile else 112
    body = text(x,name_y,"Vekhyat Jain",44 if mobile else 78,weight=700)
    body += text(x,h-65,"exploring",18 if mobile else 22,ACCENT,mono=True)
    # Stable label and static default survive disabled CSS; animated alternatives
    # occupy the exact same slot without a blank-first-frame reveal.
    y=h-32; size=17 if mobile else 23
    labels=["machine learning", "theoretical CS", "programming languages", "computation"]
    css="@keyframes cursor{0%,45%,100%{opacity:1}50%,90%{opacity:0}}.cursor{animation:cursor 1.4s steps(1) infinite}"
    for i,label in enumerate(labels):
        opacity=1 if i==0 else 0
        starts=[0,25,50,75]; a=starts[i]; b=a+25
        frames = ("0%,22%{opacity:1}25%,97%{opacity:0}100%{opacity:1}" if i==0 else
                  f"0%,{a-1}%{{opacity:0}}{a}%,{b-3}%{{opacity:1}}{b if b<100 else 99}%,100%{{opacity:0}}")
        css += f"@keyframes word{i}{{{frames}}}.word{i}{{animation:word{i} 20s linear infinite}}"
        body+=f'<g class="word{i}" opacity="{opacity}">'+text(x,y,label,size,FG,mono=True)+"</g>"
    body+=f'<rect class="cursor" x="{w-40}" y="{y-17}" width="10" height="20" fill="{ACCENT}"/>'
    # A moving instruction pointer along a real discrete path, not a halo/grid.
    body+=f'<path d="M{x} {h-92} H{w-x}" stroke="{LINE}"/>'
    body+=f'<path class="instruction" d="M{x} {h-92} H{w-x}" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="26 {w}"/>'
    css+=f"@keyframes instruction{{to{{stroke-dashoffset:-{w-x*2+26}}}}}.instruction{{animation:instruction 12s linear infinite}}"
    svg("header-mobile.svg" if mobile else "header.svg",w,h,"Vekhyat Jain. Exploring machine learning, theoretical CS, programming languages, and computation",body,css)

def terminal(mobile=False):
    w,h=(400,350) if mobile else (840,330)
    x=24 if mobile else 32
    sz=17 if mobile else 23
    body=text(x,36,"vekhyat@github",16 if mobile else 18,MUTED,mono=True)
    body+=f'<path d="M0 54 H{w}" stroke="{LINE}"/>'
    lines=[("$ whoami",ACCENT),("Vekhyat Jain",FG),("$ exploring",ACCENT),("machine learning",FG),("$ writing_in",ACCENT),("Python and C++",FG)]
    ys=[90,122,176,208,262,294] if mobile else [94,127,181,214,268,301]
    css="@keyframes caret{0%,45%,100%{opacity:1}50%,90%{opacity:0}}"
    for i,((s,c),y) in enumerate(zip(lines,ys)):
        line_text=text(x,y,s,sz,c,mono=True)
        body+=line_text
        if i%2==0:
            width=len(s)*sz*.602
            # Clip from left to right while typing; the static clip is fully open.
            start=(i//2)*30; stop=start+8
            css+=f"@keyframes type{i}{{0%,{start}%{{width:0px}}{stop}%,100%{{width:{width}px}}}}.type{i}{{animation:type{i} 24s steps({len(s)},end) infinite}}"
            body=body.replace(line_text,f'<defs><clipPath id="clip{i}"><rect class="type{i}" x="{x}" y="{y-sz}" width="{width}" height="{sz+5}"/></clipPath></defs><g clip-path="url(#clip{i})">{line_text}</g>')
            css+=f"@keyframes line{i}{{0%,{max(0,start-1)}%{{opacity:0}}{start+1}%,{start+27}%{{opacity:1}}{start+29}%,100%{{opacity:0}}}}"
            css+=f"@keyframes pos{i}{{0%,{start}%{{transform:translateX(0px)}}{stop}%,100%{{transform:translateX({width+8}px)}}}}.line{i}{{animation:line{i} 24s steps(1) infinite,pos{i} 24s steps({len(s)},end) infinite}}.blink{{animation:caret 1.4s steps(1) infinite}}"
            body+=f'<g class="line{i}" opacity="0"><rect class="blink" x="{x}" y="{y-sz+2}" width="9" height="{sz}" fill="{ACCENT}"/></g>'
        else:
            start=(i//2)*30+8
            css+=f"@keyframes output{i}{{0%,{start}%{{opacity:.15}}{start+2}%,100%{{opacity:1}}}}.output{i}{{animation:output{i} 24s linear infinite}}"
            # The output is never completely absent, including at loop reset.
            old=text(x,y,s,sz,c,mono=True)
            body=body.replace(old,f'<g class="output{i}">{old}</g>')
    svg("terminal-mobile.svg" if mobile else "terminal.svg",w,h,"Terminal: Vekhyat Jain. Exploring machine learning. Writing in Python and C++",body,css)

def pipeline(mobile=False):
    w,h=(400,222) if mobile else (840,174)
    labels=["source.cpp","tokens","AST","machine code"]
    positions=[(26,60),(231,60),(26,166),(221,166)] if mobile else [(26,70),(259,70),(453,70),(635,70)]
    body=""; css=""
    for i,((x,y),label) in enumerate(zip(positions,labels)):
        body+=text(x,y,label,18 if mobile else 23,FG,mono=True)
        body+=f'<circle cx="{x+6}" cy="{y+22}" r="4" fill="{ACCENT}"/>'
    # Traversal follows the labelled pipeline; mobile uses a folded reading path.
    path="M32 82 H237 V112 H32 V188 H227" if mobile else "M32 92 H641"
    body+=f'<path d="{path}" fill="none" stroke="{LINE}" stroke-width="2"/>'
    body+=f'<path class="packet" d="{path}" fill="none" stroke="{ACCENT}" stroke-width="3" stroke-dasharray="18 800"/>'
    length=640 if mobile else 630
    css="@keyframes flow{0%{stroke-dashoffset:20}100%{stroke-dashoffset:-"+str(length)+"}}.packet{animation:flow 10s linear infinite}"
    if not mobile: body+=text(26,145,"lexing                 parsing         compilation",17,MUTED,mono=True)
    svg("cs-animation-mobile.svg" if mobile else "cs-animation.svg",w,h,"Compilation stages: source.cpp, tokens, abstract syntax tree, machine code",body,css)

def stack():
    body = ""
    # Authored lettermarks are labels, not unofficial brand logos.
    for i,(label,lang) in enumerate([("Py","Python"),("C++","C++")]):
        x=24+i*190
        body+=f'<rect x="{x}" y="60" width="42" height="38" rx="4" fill="none" stroke="{LINE}"/>'
        body+=text(x+5,86,label,17,ACCENT,mono=True)
        body+=text(x,126,lang,20,FG)
    body+=f'<path d="M24 154 H376" stroke="{LINE}"/><path class="scan" d="M24 154 H376" stroke="{ACCENT}" stroke-dasharray="30 380"/>'
    css="@keyframes scan{to{stroke-dashoffset:-390}}.scan{animation:scan 18s linear infinite}"
    svg("stack.svg",400,174,"Python and C++",body,css)

def satquery():
    body=text(24,48,"SatQuery AI",30,FG,700)+text(24,79,"Ask a satellite image a question.",16,MUTED)
    body+=text(24,120,"upload, question, evidence",19,ACCENT,mono=True)
    body+=f'<path d="M24 140 H374" stroke="{LINE}"/><path class="packet" d="M24 140 H374" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="20 380"/>'
    body+=text(24,178,"Python / FastAPI / React",16,MUTED,mono=True)
    css='@keyframes packet{from{stroke-dashoffset:20}to{stroke-dashoffset:-370}}.packet{animation:packet 9s linear infinite}'
    svg("satquery.svg",400,202,"SatQuery AI. Ask a satellite image a question. Team project for an ISRO problem statement",body,css)

def project(name,title,subtitle,tech,audio=False):
    w,h=400,202
    body=text(24,48,title,30,FG,700)+text(24,79,subtitle,16,MUTED)
    body+=text(24,178,tech,16,MUTED,mono=True)
    css=""
    if audio:
        vals=[9,17,11,27,35,18,28,13,20,32,16,25,11,19,30,14,24,8]
        for i,v in enumerate(vals):
            x=26+i*20
            body+=f'<path class="bar b{i}" d="M{x} {127-v/2} V{127+v/2}" stroke="{ACCENT}" stroke-width="3" stroke-linecap="round"/>'
            css+=f'.b{i}{{animation-delay:-{i*.27:.2f}s;}}'
        css='.bar{transform-origin:center;transform-box:fill-box;animation:wave 4.8s ease-in-out infinite}@keyframes wave{0%,100%{transform:scaleY(.55)}50%{transform:scaleY(1)}}'+css
    else:
        body+=f'<rect x="24" y="105" width="350" height="40" rx="3" fill="none" stroke="{LINE}"/>'
        body+=text(36,132,"vekhyat.github.io",19,ACCENT,mono=True)
        body+=f'<path class="pointer" d="M330 113 L330 132 L336 127 L341 137 L346 134 L341 125 L349 125 Z" fill="{FG}"/>'
        css='@keyframes pointer{0%,25%,100%{transform:translateX(0)}55%,75%{transform:translateX(-42px)}}.pointer{animation:pointer 12s ease-in-out infinite}'
    svg(name,w,h,". ".join([title, subtitle.rstrip("."), tech]),body,css)

def main():
    ASSETS.mkdir(exist_ok=True)
    for mobile in (False,True): header(mobile);terminal(mobile)
    stack()
    satquery()
    project("auralis.svg","Auralis","Lossless download from a Spotify link.","Go / TypeScript / Wails",True)
    project("website.svg","Personal site","GitHub, LinkedIn, Instagram, email.","TypeScript / React / Vite")
    print("Built 8 authored SVG assets")

if __name__=="__main__": main()
