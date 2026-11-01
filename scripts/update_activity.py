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
            "repository_primary_languages":dict(languages),"pinned":get_pinned(user),
            "latest_commit":get_latest_commit(user,repos),"streaks":streaks(days)}

def get_latest_commit(user,repos):
    """The newest commit the user authored, from the most recently pushed repositories (the profile repo excluded)."""
    candidates=sorted((r for r in repos if not r["fork"] and r["name"].lower()!=user.lower()),key=lambda r:r["pushed_at"],reverse=True)[:4]
    for r in candidates:
        for c in json.loads(fetch(f"https://api.github.com/repos/{r['full_name']}/commits?per_page=10")):
            author=(c.get("author") or {}).get("login","")
            if author.lower()==user.lower():
                message=c["commit"]["message"].split("\n")[0].strip()
                return {"repo":r["name"],"url":c["html_url"],"message":message,"date":c["commit"]["author"]["date"][:10]}
    return None

def streaks(days):
    """Current and longest runs of days with at least one contribution, from the public calendar."""
    counts=[d["count"] for d in days]
    longest=run=0
    for c in counts:
        run=run+1 if c else 0; longest=max(longest,run)
    current=0
    for c in reversed(counts[:-1] if counts[-1]==0 else counts):  # today may still be in progress
        if c: current+=1
        else: break
    busiest=max(days,key=lambda d:d["count"])
    return {"current":current,"longest":longest,"total":sum(counts),"active_days":sum(1 for c in counts if c),
            "busiest_day":busiest["date"],"busiest_count":busiest["count"]}

def get_pinned(user):
    """The profile's pinned repositories, in pinned order. Needs GH_TOKEN (GraphQL has no anonymous access)."""
    if not os.environ.get("GH_TOKEN"):
        raise ValueError("GH_TOKEN is required to read pinned repositories")
    query='{user(login:"%s"){pinnedItems(first:6,types:REPOSITORY){nodes{... on Repository{name url description stargazerCount isPrivate primaryLanguage{name}}}}}}'%user
    body=json.dumps({"query":query}).encode()
    req=Request("https://api.github.com/graphql",data=body,headers={"User-Agent":"vekhyat-profile-activity","Authorization":"Bearer "+os.environ["GH_TOKEN"],"Content-Type":"application/json"})
    with urlopen(req,timeout=40) as response:
        nodes=json.loads(response.read().decode("utf-8"))["data"]["user"]["pinnedItems"]["nodes"]
    pinned=[{"name":n["name"],"url":n["url"],"description":n["description"] or "","stars":n["stargazerCount"],
             "language":(n["primaryLanguage"] or {}).get("name")} for n in nodes if not n["isPrivate"]]
    if not pinned: raise ValueError("No public pinned repositories; keeping existing cards")
    return pinned

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

def ridge(data):
    """The year as a mountain ridge: each day's contributions set the height, the trekker walks it, the route is red thread."""
    import math
    bg,chalk,muted,red,rock,snow,haze="#2c4a40","#f2eee4","#b9cbc0","#c4452d","#1b312a","#f2eee4","#3d5c50"
    days=data["days"]; n=len(days)
    W,H=840,300; left,right,top,base=40,800,74,236
    counts=[d["count"] for d in days]
    # Smooth over three days so the ridge reads as terrain, then compress with a log so one huge day does not flatten the rest.
    kernel=[1,2,3,4,3,2,1]; k=len(kernel)//2
    smooth=[sum(counts[min(max(i+j-k,0),n-1)]*w for j,w in enumerate(kernel))/sum(kernel) for i in range(n)]
    peak=max(smooth) or 1
    xs=[left+(right-left)*i/(n-1) for i in range(n)]
    ys=[base-(base-top)*math.log1p(v)/math.log1p(peak) for v in smooth]
    pts=" ".join(f"{x:.1f},{y:.1f}" for x,y in zip(xs,ys))
    ridge_line=f"M{xs[0]:.1f} {ys[0]:.1f} "+" ".join(f"L{x:.1f} {y:.1f}" for x,y in zip(xs[1:],ys[1:]))
    # A hazier range behind, offset and lower, for depth.
    back=" ".join(f"{(left+(right-left)*i/(n-1)):.1f},{(base-(base-top)*0.55*math.log1p(smooth[(i*7+40)%n])/math.log1p(peak)-10):.1f}" for i in range(n))
    body=f'<polygon points="{left},{base} {back} {right},{base}" fill="{haze}" opacity=".7"/>'
    body+=f'<polygon points="{left},{base} {pts} {right},{base}" fill="{rock}"/>'
    # Snow where the ridge is high: the top third of the range.
    snowline=base-(base-top)*0.55
    snow_pts=[]
    for x,y in zip(xs,ys):
        snow_pts.append(f"{x:.1f},{min(y,snowline):.1f}" if y<snowline else f"{x:.1f},{snowline:.1f}")
    body+=f'<clipPath id="ridgeclip"><polygon points="{left},{base} {pts} {right},{base}"/></clipPath>'
    body+=f'<polygon clip-path="url(#ridgeclip)" points="{left},{snowline} {pts} {right},{snowline}" fill="{snow}" opacity=".92"/>'
    body+=f'<path d="{ridge_line}" fill="none" stroke="{chalk}" stroke-width="1" opacity=".5"/>'
    body+=f'<path d="M{left} {base} H{right}" stroke="{muted}" stroke-opacity=".5"/>'
    # Month ticks.
    seen=set()
    for i,d in enumerate(days):
        m=d["date"][:7]
        if m not in seen and d["date"].endswith("-01"):
            seen.add(m); x=xs[i]
            body+=f'<path d="M{x:.1f} {base} v6" stroke="{muted}" stroke-opacity=".7"/>'
            body+=txt(x-10,base+22,date.fromisoformat(d["date"]).strftime("%b"),11,muted)
    # The route: red thread drawn along the ridge as the trekker walks it (SMIL, so it works inside an img).
    dur=40
    body+=(f'<path id="route" d="{ridge_line}" fill="none" stroke="{red}" stroke-width="1.6" stroke-linecap="round" '
           f'pathLength="1" stroke-dasharray="1" stroke-dashoffset="0">'
           f'<animate attributeName="stroke-dashoffset" from="1" to="0" dur="{dur}s" repeatCount="indefinite"/></path>')
    # The trekker: a small chalk figure with a pole. It rests at today's end of the ridge; the motion path is
    # expressed relative to that spot so the same figure walks the route when animation is available.
    ex,ey=xs[-1],ys[-1]
    fig=(f'<g transform="translate(0 -11)"><circle cx="0" cy="-7" r="2.6" fill="{chalk}"/>'
         f'<path d="M0 -4 V3 M0 3 L-3 9 M0 3 L3 9 M0 -1 L-4 2 M0 -1 L4 1" stroke="{chalk}" stroke-width="1.6" stroke-linecap="round" fill="none"/>'
         f'<path d="M4.5 0 L6 10" stroke="{red}" stroke-width="1.4" stroke-linecap="round"/></g>')
    walk=f"M{xs[0]-ex:.1f} {ys[0]-ey:.1f} "+" ".join(f"L{x-ex:.1f} {y-ey:.1f}" for x,y in zip(xs[1:],ys[1:]))
    body+=f'<g transform="translate({ex:.1f} {ey:.1f})">{fig}<animateMotion dur="{dur}s" repeatCount="indefinite" path="{walk}"/></g>'
    peak_i=max(range(n),key=lambda i:counts[i]); px,py=xs[peak_i],ys[peak_i]
    body+=f'<path d="M{px:.1f} {py:.1f} v-14" stroke="{red}" stroke-width="1.2"/><path d="M{px:.1f} {py-14:.1f} h9 l-3 3 l3 3 h-9z" fill="{red}"/>'
    body+=txt(18,30,"A year on the ridge",18,chalk)
    body+=txt(18,50,f"{days[0]['date']} to {days[-1]['date']}. Height is contributions per day; snow is a busy stretch; the flag is the busiest day ({counts[peak_i]} on {days[peak_i]['date']}).",12,muted)
    body+=txt(18,H-14,"Public contribution calendar, refreshed "+data["snapshot"],12,muted)
    return wrap(W,H,"A year of GitHub contributions drawn as a mountain ridge, with a trekker walking the route from "+days[0]["date"]+" to "+days[-1]["date"],body,"",bg)

def main():
    p=argparse.ArgumentParser();p.add_argument("--user",default="vekhyat");p.add_argument("--from-json",type=Path);a=p.parse_args()
    data=json.loads(a.from_json.read_text(encoding="utf-8")) if a.from_json else get_data(a.user)
    outputs={"activity.svg":activity(data),"activity-light.svg":activity(data,True),"ridge.svg":ridge(data)}
    for name,content in outputs.items():
        ET.fromstring(content)
        if len(content.encode())>250_000: raise ValueError(f"Unexpected size: {name}")
    DIST.mkdir(exist_ok=True)
    for name,content in outputs.items():
        tmp=DIST/(name+".tmp");tmp.write_text(content,encoding="utf-8");tmp.replace(DIST/name)
    (DIST/"public-data.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(f"Generated {len(outputs)} SVGs from {len(data['days'])} public calendar days and {data['public_repositories']} public repositories; snapshot {data['snapshot']}")

if __name__=="__main__": main()
