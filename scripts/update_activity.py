"""Fetch public GitHub data and build stats + a contribution snake.

No dependencies, external image service, personal access token, or invented data.
GH_TOKEN is optional and is sent ONLY to api.github.com, never the public page.
All files are built and validated before replacing the previous successful run.
"""
import argparse
from collections import Counter
from datetime import date, datetime, timezone
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

def fetch(url):
    headers = {"User-Agent": "vekhyat-profile-activity", "Accept": "application/vnd.github+json" if "api.github.com" in url else "text/html"}
    if url.startswith("https://api.github.com/") and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=40) as response:
        return response.read().decode("utf-8")

class Calendar(HTMLParser):
    def __init__(self):
        super().__init__(); self.days={}; self.tooltip=None; self.tiptext=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=="td" and "data-date" in a and "data-level" in a:
            self.days[a["id"]]={"date":a["data-date"],"level":int(a["data-level"])}
        if tag=="tool-tip" and "for" in a:
            self.tooltip=a["for"]; self.tiptext=[]
    def handle_data(self, text):
        if self.tooltip: self.tiptext.append(text)
    def handle_endtag(self, tag):
        if tag=="tool-tip" and self.tooltip:
            raw="".join(self.tiptext).strip()
            match=re.match(r"(No|[\d,]+) contributions? on ", raw)
            if self.tooltip in self.days and match:
                self.days[self.tooltip]["count"]=0 if match[1]=="No" else int(match[1].replace(",",""))
            self.tooltip=None

def get_data(user):
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})",user):
        raise ValueError("Invalid GitHub username")
    parser=Calendar(); parser.feed(fetch(f"https://github.com/users/{user}/contributions"))
    days=sorted(parser.days.values(), key=lambda d:d["date"])
    if len(days)<350 or any("count" not in d or not 0<=d["level"]<=4 for d in days):
        raise ValueError("GitHub calendar markup changed or returned incomplete data; keeping existing SVGs")
    repos=[]
    for page in range(1,20):
        batch=json.loads(fetch(f"https://api.github.com/users/{user}/repos?per_page=100&page={page}&type=owner"))
        if not isinstance(batch,list): raise ValueError("Unexpected GitHub repository response")
        repos.extend(r for r in batch if not r.get("private",True))
        if len(batch)<100: break
    else: raise ValueError("Pagination cap exceeded; refusing partial statistics")
    languages=Counter(r["language"] for r in repos if r.get("language") and not r["fork"])
    return {"user":user,"snapshot":datetime.now(timezone.utc).strftime("%Y-%m-%d"),"days":days,
            "public_repositories":len(repos),"public_stars":sum(r["stargazers_count"] for r in repos),
            "repository_primary_languages":dict(languages)}

def wrap(w,h,title,body,css,bg):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title">
<title id="title">{escape(title)}</title><style>{css}@media(prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>
<rect width="{w}" height="{h}" rx="8" fill="{bg}"/>{body}</svg>'''

def txt(x,y,value,size,fg):
    return f'<text x="{x}" y="{y}" fill="{fg}" font-family="Arial,Helvetica,sans-serif" font-size="{size}">{escape(str(value))}</text>'

def activity(data,light=False):
    bg,fg,muted,accent,line=("#f6f8f5","#172219","#49594c","#427321","#d6dfd4") if light else ("#0b0f10","#eef3ef","#a9b8b0","#b6f36b","#2b3830")
    end=date.fromisoformat(data["days"][-1]["date"])
    # Exactly the latest 12 *complete* Sunday-Saturday calendar weeks.
    # Treat the newest calendar date as in progress, including on Saturday.
    last_saturday=end.toordinal()-((end.weekday()+2)%7 or 7)
    weekly=[0]*12
    for d in data["days"]:
        delta=last_saturday-date.fromisoformat(d["date"]).toordinal()
        if 0<=delta<84: weekly[11-delta//7]+=d["count"]
    total=sum(weekly)
    body=txt(24,34,"Public GitHub activity",21,fg)+txt(24,61,"Snapshot: "+data["snapshot"]+" UTC",14,muted)
    body+=txt(24,105,data["public_repositories"],29,fg)+txt(64,104,"public repos",16,muted)
    body+=txt(221,105,data["public_stars"],29,fg)+txt(263,104,"stars",16,muted)
    body+=txt(24,148,f"{total} contributions / 12 complete weeks",16,fg)
    maxval=max(1,max(weekly))
    for i,count in enumerate(weekly):
        height=round(count/maxval*59,2); x=25+i*29
        body+=f'<rect x="{x}" y="{220-height}" width="18" height="{max(1,height)}" rx="2" fill="{accent}"><title>{count} contributions in week ending {date.fromordinal(last_saturday-(11-i)*7)}</title></rect>'
    body+=f'<path d="M24 224 H374" stroke="{line}"/>'
    body+=txt(24,248,date.fromordinal(last_saturday-83).strftime("%d %b"),13,muted)+txt(321,248,date.fromordinal(last_saturday).strftime("%d %b"),13,muted)
    body+=txt(24,280,"Primary language / public non-fork repos",14,muted)
    langs=" · ".join(f"{name} {count}" for name,count in sorted(data["repository_primary_languages"].items(),key=lambda p:-p[1]))
    # Keep rows short without silently dropping a language.
    rows=[]; current=""
    for part in langs.split(" · "):
        if len(current)+len(part)>37:
            rows.append(current);current=part
        else: current=part if not current else current+" · "+part
    if current: rows.append(current)
    for i,row in enumerate(rows): body+=txt(24,305+i*23,row,16,fg)
    body+=f'<circle class="refresh" cx="370" cy="29" r="3" fill="{accent}"/>'
    css="@keyframes refresh{0%,85%,100%{opacity:1}92%{opacity:.35}}.refresh{animation:refresh 14s ease-in-out infinite}"
    return wrap(400,324+max(0,len(rows)-1)*23,"Actual public GitHub statistics, snapshot "+data["snapshot"],body,css,bg)

def snake(data,dark=False):
    bg,fg,muted,head=("#0b0f10","#eef3ef","#a9b8b0","#b6f36b") if dark else ("#f6f8f5","#172219","#49594c","#325d18")
    colors=["#19221c","#2b4525","#4b6f32","#7ea845","#b6f36b"] if dark else ["#e1e8de","#c6deb2","#9ac174","#699547","#427321"]
    days=data["days"]; first=date.fromisoformat(days[0]["date"])
    # Calendar data starts on Sunday; explicitly check before positioning.
    if first.weekday()!=6: raise ValueError("Calendar no longer starts on Sunday")
    points={}; body=txt(18,29,"The contribution snake",18,fg)
    body+=txt(18,49,days[0]["date"]+" — "+days[-1]["date"],12,muted)
    css=""; cells=""; coords=[]
    for d in days:
        offset=(date.fromisoformat(d["date"])-first).days; col,row=divmod(offset,7)
        points[(col,row)]=d
    for col in range(max(c for c,r in points)+1):
        for row in (range(7) if col%2==0 else reversed(range(7))):
            if (col,row) in points: coords.append((col,row))
    n=len(coords); unit=14
    for i,(col,row) in enumerate(coords):
        d=points[(col,row)]; x=18+col*unit;y=68+row*unit
        t=round((i/(n-1))*.91*100,3)
        cls=""
        if d["level"]:
            cls=f' class="c{i}"'
            css+=f'@keyframes eat{i}{{0%,{t}%{{opacity:1}}{min(t+.1,91.1)}%,95%{{opacity:.13}}100%{{opacity:1}}}}.c{i}{{animation:eat{i} 42s linear infinite}}'
        cells+=f'<rect{cls} x="{x}" y="{y}" width="10" height="10" rx="2" fill="{colors[d["level"]]}"><title>{d["date"]}: {d["count"]} contributions</title></rect>'
    frames="".join(f'{round(i/(n-1)*91,3)}%{{transform:translate({18+c*unit}px,{68+r*unit}px)}}' for i,(c,r) in enumerate(coords))
    last=coords[-1]
    frames+=f'95%{{transform:translate({18+last[0]*unit}px,{68+last[1]*unit}px)}}100%{{transform:translate(18px,68px)}}'
    css+='@keyframes traverse{'+frames+'}@keyframes visible{0%,91%{opacity:1}95%,99.9%{opacity:0}100%{opacity:1}}.snake{animation:traverse 42s linear infinite,visible 42s linear infinite}'
    body+=cells+f'<g class="snake" transform="translate(18,68)"><rect x="-1" y="-1" width="12" height="12" rx="4" fill="{head}"/><circle cx="3" cy="3" r="1" fill="{bg}"/><circle cx="7" cy="3" r="1" fill="{bg}"/></g>'
    # The head is followed by two slightly delayed segments on the same path.
    for delay,opacity,size in [(".22", ".55",8),(".44",".3",6)]:
        body+=f'<g class="snake" style="animation-delay:{delay}s" transform="translate(18,68)"><rect opacity="{opacity}" width="{size}" height="{size}" rx="3" fill="{head}"/></g>'
    body+=txt(18,184,"Public calendar · refreshed "+data["snapshot"],12,muted)
    return wrap(18*2+(max(c for c,r in coords)+1)*unit,202,"Animated snake traversing actual public GitHub contribution levels, "+days[0]["date"]+" to "+days[-1]["date"],body,css,bg)

def main():
    p=argparse.ArgumentParser();p.add_argument("--user",default="vekhyat");p.add_argument("--from-json",type=Path);a=p.parse_args()
    data=json.loads(a.from_json.read_text(encoding="utf-8")) if a.from_json else get_data(a.user)
    outputs={"activity.svg":activity(data),"activity-light.svg":activity(data,True),"github-contribution-grid-snake.svg":snake(data),"github-contribution-grid-snake-dark.svg":snake(data,True)}
    for name,content in outputs.items():
        ET.fromstring(content)
        if len(content.encode())>250_000: raise ValueError(f"Unexpected size: {name}")
    DIST.mkdir(exist_ok=True)
    for name,content in outputs.items():
        tmp=DIST/(name+".tmp");tmp.write_text(content,encoding="utf-8");tmp.replace(DIST/name)
    (DIST/"public-data.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(f"Generated {len(outputs)} SVGs from {len(data['days'])} public calendar days and {data['public_repositories']} public repositories; snapshot {data['snapshot']}")

if __name__=="__main__": main()
