#!/usr/bin/env python3
"""
Builds the light and dark bento-style SVG cards used by the profile README.

  python scripts/build_profile.py                # live data from GitHub (set GITHUB_TOKEN)
  python scripts/build_profile.py --offline      # use scripts/data.json only

Live mode needs a token for the contribution calendar (GraphQL). Inside
GitHub Actions the built-in GITHUB_TOKEN is enough. If any request fails,
the script falls back to scripts/data.json so the README never breaks.

Edit CONFIG below to change the README text, links or which repos show.
"""
import base64, datetime as dt, functools, html, json, os, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = Path(__file__).resolve().parent / "data.json"

CONFIG = {
    "user": "Kakahaja07",
    "greeting": "Howdy!",
    # Paragraphs for the README card. Wrap a phrase in [[...]] to underline it.
    "about": [
        "I'm Prashant Sharma, an AI automation engineer, full-stack developer and open-source "
        "maintainer from India. I build open-source SDKs and APIs with Next.js and TypeScript at "
        "[[Xtream Ventures]], and I care a lot about technical SEO and developer experience.",
        "Right now I'm shipping [[FMUI]], a React component library for Next.js built on Tailwind CSS "
        "and shadcn/ui, and [[World Kit]], a TypeScript toolkit for countries, currencies and timezones. "
        "I also maintain [[DamAPI]] for lake and dam water levels, with government data SDKs for NOAA, "
        "NASA, USGS, FEMA and the Census Bureau in progress.",
        "Goals for 2026: publish 25+ npm packages, cross 1M npm downloads and ship 10+ production APIs.",
    ],
    "achievements": [{"name": "Pair Extraordinaire", "tier": "x2"}],
    "links": [
        ("building", "Xtream Ventures"),
        ("globe", "hiprashant.com"),
        ("x", "@Prsnt50"),
        ("linkedin", "in/prsntseo"),
        ("github", "Kakahaja07"),
    ],
    # Pill buttons under the cards: (file key, icon, label)
    "buttons": [
        ("site", "globe", "hiprashant.com"),
        ("fmui", "link", "fmui.dev"),
        ("worldkit", "link", "worldkit.in"),
        ("x", "x", "@Prsnt50"),
        ("linkedin", "linkedin", "LinkedIn"),
    ],
    "repo_count": 2,          # how many latest public repos to show
    "skip_repos": ["Kakahaja07"],
}

THEMES = {
    "dark": dict(id="d", card=("#212124", "#151516"), inner=("#2b2b2e", "#202022"), edge=("#4c4c54", "#27272b"),
                 line="#2e2e32", fg="#f4f4f5", body="#c9c9cd", muted="#9b9ba0", faint="#76767c",
                 mute2="#bdbdc2", link="#d9d9dc", pill_fg="#c9c9cc", pill_line="#5a5a60", beta_fg="#d2d2d5",
                 tier_bg="#ececee", tier_fg="#111111",
                 acc=("#4ade80", "#22d3ee", "#818cf8"), glow="#22d3ee", glow_op=".13",
                 g=["#2a2a2d", "#0e4429", "#006d32", "#26a641", "#39d353"]),
    "light": dict(id="l", card=("#ffffff", "#f1f4f8"), inner=("#ffffff", "#f6f8fa"), edge=("#b9c3cf", "#dbe1e8"),
                  line="#d6dde4", fg="#1f2328", body="#3d444d", muted="#59636e", faint="#6e7781",
                  mute2="#59636e", link="#1f2328", pill_fg="#3d444d", pill_line="#afb8c1", beta_fg="#3d444d",
                  tier_bg="#1f2328", tier_fg="#ffffff",
                  acc=("#16a34a", "#0891b2", "#6366f1"), glow="#0891b2", glow_op=".10",
                  g=["#e6eaee", "#9be9a8", "#40c463", "#30a14e", "#216e39"]),
}
C = dict(THEMES["dark"])   # active palette; main() swaps it per theme
_STACK = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
SANS = "'Uncut Sans'," + _STACK          # body text
HEAD = "'Geomini','Uncut Sans'," + _STACK  # headings and big numbers
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"
LANG_COLORS = {"TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5", "PHP": "#4F5D95",
               "HTML": "#e34c26", "CSS": "#563d7c", "Go": "#00ADD8", "Rust": "#dea584"}
ICONS = {
    "repo": "M2 2.5A2.5 2.5 0 014.5 0h8.8a.7.7 0 01.7.7v12.6a.7.7 0 01-.7.7h-2.5a.7.7 0 010-1.5h1.7v-2H4.5a1 1 0 00-.6 1.8.7.7 0 01-.9 1.2A2.5 2.5 0 012 11.5zm10.5-1h-8a1 1 0 00-1 1v6.7c.3-.1.6-.2 1-.2h8zM5 12.2v3.5c0 .2.2.3.4.2l1.5-1.1a.2.2 0 01.2 0l1.5 1.1c.2.1.4 0 .4-.2v-3.5a.2.2 0 00-.2-.2H5.2a.2.2 0 00-.2.2z",
    "star": "M8 .3a.8.8 0 01.7.4l1.9 3.8 4.2.6a.8.8 0 01.4 1.3l-3 3 .7 4.1a.8.8 0 01-1.1.8L8 12.4l-3.8 2a.8.8 0 01-1.1-.8l.7-4.2-3-2.9a.8.8 0 01.4-1.3l4.2-.6L7.3.7A.8.8 0 018 .3zm0 2.4L6.6 5.6a.8.8 0 01-.6.4l-3.1.4 2.3 2.2a.8.8 0 01.2.7l-.5 3.1 2.8-1.5a.8.8 0 01.7 0l2.8 1.5-.5-3.1a.8.8 0 01.2-.7l2.3-2.2-3.2-.4a.8.8 0 01-.5-.4z",
    "fork": "M5 5.4a2.3 2.3 0 10-1.5 0v.9A2.3 2.3 0 005.8 8.5h1.5v2.1a2.3 2.3 0 101.5 0V8.5h1.5a2.3 2.3 0 002.2-2.2v-.9a2.3 2.3 0 10-1.5 0v.9a.8.8 0 01-.8.7H5.8a.8.8 0 01-.8-.7zm6.8-2.9a.8.8 0 110 1.5.8.8 0 010-1.5zM8 12a.8.8 0 110 1.5.8.8 0 010-1.5zM4.2 2.5a.8.8 0 110 1.5.8.8 0 010-1.5z",
    "link": "M9 1h6v6h-1.5V3.6L8 9.1 6.9 8 12.4 2.5H9zM2 4h5v1.5H3.5v7h7V9H12v5H2z",
    "building": "M2 14V3.5L8 1l6 2.5V14h-4v-3H6v3zm2-8h2V4H4zm0 3h2V7H4zm6-3h2V4h-2zm0 3h2V7h-2z",
    "globe": "M8 1a7 7 0 100 14A7 7 0 008 1zm4.9 6h-2.1a11 11 0 00-.9-3.9A5 5 0 0112.9 7zM8 3c.6.8 1.1 2.2 1.3 4H6.7C6.9 5.2 7.4 3.8 8 3zM3.1 9h2.1c.1 1.4.4 2.8.9 3.9A5 5 0 013.1 9zm2.1-2H3.1a5 5 0 013-3.9c-.5 1.1-.8 2.5-.9 3.9zM8 13c-.6-.8-1.1-2.2-1.3-4h2.6c-.2 1.8-.7 3.2-1.3 4zm1.9-.1c.5-1.1.8-2.5.9-3.9h2.1a5 5 0 01-3 3.9z",
    "x": "M12.2 1.5h2.2L9.6 7l5.7 7.5h-4.4L7.4 10l-4 4.5H1.2l5.1-5.9L.8 1.5h4.5l3.1 4.1zm-.8 11.7h1.2L4.7 2.7H3.4z",
    "linkedin": "M2 2h12a1 1 0 011 1v10a1 1 0 01-1 1H2a1 1 0 01-1-1V3a1 1 0 011-1zm1.5 4.5V12h2V6.5zM4.5 3.5a1.1 1.1 0 100 2.2 1.1 1.1 0 000-2.2zM7 6.5V12h2V9.2c0-.8.4-1.3 1.1-1.3s1 .5 1 1.3V12h2V8.8c0-1.6-.9-2.5-2.3-2.5-.9 0-1.5.4-1.8.9v-.7z",
    "github": "M8 .7a7.3 7.3 0 00-2.3 14.2c.4.1.5-.2.5-.4v-1.3c-2 .4-2.5-.9-2.5-.9-.3-.8-.8-1.1-.8-1.1-.7-.5 0-.5 0-.5.8.1 1.2.8 1.2.8.7 1.1 1.8.8 2.2.6.1-.5.3-.8.5-1-1.6-.2-3.3-.8-3.3-3.6 0-.8.3-1.5.8-2-.1-.2-.3-1 .1-2 0 0 .6-.2 2 .8a7 7 0 013.7 0c1.4-1 2-.8 2-.8.4 1 .2 1.8.1 2 .5.5.8 1.2.8 2 0 2.8-1.7 3.4-3.3 3.6.3.2.5.7.5 1.4v2c0 .2.1.5.5.4A7.3 7.3 0 008 .7z",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
e = lambda s: html.escape(str(s), quote=True)


# ---------------------------------------------------------------- data
def http(url, body=None, raw=False):
    headers = {"User-Agent": "profile-readme-builder", "Accept": "application/vnd.github+json"}
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if raw else json.loads(data)


def fetch_live(user):
    d = {}
    u = http(f"https://api.github.com/users/{user}")
    d["profile"] = {k: u.get(k) for k in ("public_repos", "followers", "company", "blog", "avatar_url")}
    repos = http(f"https://api.github.com/users/{user}/repos?sort=pushed&per_page=100&type=owner")
    d["repos"] = [{k: r.get(k) for k in ("name", "description", "language", "stargazers_count",
                                         "forks_count", "pushed_at", "homepage", "fork", "archived", "private")}
                  for r in repos]
    try:
        q = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
               totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""
        g = http("https://api.github.com/graphql", {"query": q, "variables": {"u": user}})
        cal = g["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
        days = [x for w in cal["weeks"] for x in w["contributionDays"]]
        d["contributions"] = {"total": cal["totalContributions"], "start": days[0]["date"],
                              "counts": [x["contributionCount"] for x in days],
                              "levels": [lv[x["contributionLevel"]] for x in days]}
    except Exception as ex:
        print("contributions: graphql failed, scraping public calendar ->", ex)
        try:
            d["contributions"] = scrape_calendar(user)
        except Exception as ex2:
            print("contributions: using cached data ->", ex2)
    return d


def scrape_calendar(user):
    """Token-free fallback: parse the public contribution calendar HTML."""
    page = http(f"https://github.com/users/{user}/contributions", raw=True).decode()
    cells = []
    for tag in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", page):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        cells.append((a["data-date"], int(a["data-level"]), a["id"]))
    if not cells:
        raise ValueError("no calendar cells found")
    tips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page))
    cells.sort()
    counts = []
    for _, _, cid in cells:
        m = re.match(r"(\d+|No) contribution", tips.get(cid, ""))
        counts.append(0 if not m or m.group(1) == "No" else int(m.group(1)))
    return {"total": sum(counts), "start": cells[0][0], "counts": counts,
            "levels": [l for _, l, _ in cells]}


def load_data(offline):
    cached = json.loads(DATA.read_text()) if DATA.exists() else {}
    if offline:
        return cached
    try:
        live = fetch_live(CONFIG["user"])
        merged = {**cached, **live}
        DATA.write_text(json.dumps(merged, indent=1))
        return merged
    except Exception as ex:
        print("live fetch failed, using cached data ->", ex)
        return cached


# ---------------------------------------------------------------- fonts, paint, helpers
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
FACES = {"uncut": ("Uncut Sans", "uncut-sans.woff2", "300 700"), "geomini": ("Geomini", "geomini.woff2", "200 800")}
METRICS = json.loads((FONTS_DIR / "metrics.json").read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def font_css(keys):
    """Embed the fonts as data URIs: an SVG shown through <img> cannot load files from anywhere else."""
    rules = []
    for k in keys:
        fam, fn, weights = FACES[k]
        b64 = base64.b64encode((FONTS_DIR / fn).read_bytes()).decode()
        rules.append(f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{weights};"
                     f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return f"<style>{''.join(rules)}</style>"


def tw(s, size, face="uncut", weight=400):
    """Text width in px, from the recorded glyph widths (scripts/fonts/metrics.json)."""
    table = METRICS[face]
    t = table[min(table, key=lambda w: abs(int(w) - weight))]
    return sum(t.get(ch, 560) for ch in s) * size / 1000


def grad(a, b, name, x2=1, y2=1):
    return (f'<linearGradient id="{name}{C["id"]}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>')


def paint_defs():
    i, acc = C["id"], "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in zip((0, .55, 1), C["acc"]))
    return (grad(*C["card"], "card") + grad(*C["inner"], "inner") + grad(*C["edge"], "edge")
            + f'<linearGradient id="acc{i}" x1="0" y1="0" x2="1" y2="0">{acc}</linearGradient>'
            + f'<linearGradient id="accv{i}" x1="0" y1="0" x2="0" y2="1">{acc}</linearGradient>'
            + f'<radialGradient id="glow{i}" cx="1" cy="0" r="1"><stop offset="0" stop-color="{C["glow"]}" '
              f'stop-opacity="{C["glow_op"]}"/><stop offset="1" stop-color="{C["glow"]}" stop-opacity="0"/></radialGradient>')


ACC = lambda: f'url(#acc{C["id"]})'
ACCV = lambda: f'url(#accv{C["id"]})'


def svg(w, h, body, extra_defs="", fonts=("uncut", "geomini")):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
            f'<defs>{font_css(tuple(fonts))}{paint_defs()}{extra_defs}</defs>{body}</svg>\n')


def card(x, y, w, h, r=16, inner=False):
    fill = f'url(#{"inner" if inner else "card"}{C["id"]})'
    return (f'<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="{r}" '
            f'fill="{fill}" stroke="url(#edge{C["id"]})"/>')


def glow(x, y, w, h, r=16):
    return f'<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="{r}" fill="url(#glow{C["id"]})"/>'


def bar(x, y, w, h, fill, r=None):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2 if r is None else r}" fill="{fill}"/>'


def icon(name, x, y, size=16, fill=None):
    s = size / 16
    return f'<path transform="translate({x} {y}) scale({s})" d="{ICONS[name]}" fill="{fill or C["muted"]}"/>'


def text(x, y, s, size=14, fill=None, weight=400, family=SANS, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or C["fg"]}" text-anchor="{anchor}" {extra}>{s}</text>')


def html_block(x, y, w, h, inner, css):
    return (f'<foreignObject x="{x}" y="{y}" width="{w}" height="{h}">'
            f'<div xmlns="http://www.w3.org/1999/xhtml" style="{css}">{inner}</div></foreignObject>')


def rel_time(iso):
    if not iso:
        return ""
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (dt.datetime.now(dt.timezone.utc) - t).days
    if days < 1:
        return "Updated today"
    if days < 2:
        return "Updated yesterday"
    if days < 30:
        return f"Updated {days} days ago"
    return f"Updated {t.day} {MONTHS[t.month-1]} {t.year}"


# ---------------------------------------------------------------- cards
def build_hero(d):
    W, H = 1000, 300
    b = [card(0, 0, W, H), glow(0, 0, W, H), bar(28, 0, 64, 3, ACC()),
         text(28, 42, e(f'{CONFIG["user"]} / README.md'), 11, C["faint"], family=MONO, extra='letter-spacing=".3"'),
         text(28, 90, e(CONFIG["greeting"]), 32, ACC(), 700, family=HEAD)]
    last = len(CONFIG["about"]) - 1
    paras = "".join(
        f'<p style="margin:0 0 {12 if i < last else 0}px">' +
        e(p).replace("[[", f'<span style="color:{C["fg"]};font-weight:500;text-decoration:underline;'
                           f'text-decoration-color:{C["faint"]};text-underline-offset:3px">').replace("]]", "</span>") +
        "</p>" for i, p in enumerate(CONFIG["about"]))
    b.append(html_block(28, 112, W - 56, H - 126, paras,
                        f"font-family:{SANS};font-size:14.5px;line-height:1.62;color:{C['body']}"))
    return svg(W, H, "".join(b))


def badge(cx, cy, r=30):
    i, k = C["id"], r / 27
    return (f'<g transform="translate({cx-27*k} {cy-27*k}) scale({k})">'
            f'<circle cx="27" cy="27" r="29" fill="none" stroke="url(#acc{i})" stroke-width="1.6" stroke-opacity=".9"/>'
            f'<circle cx="27" cy="27" r="26" fill="url(#bdg)"/>'
            '<circle cx="27" cy="27" r="21" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1.5"/>'
            '<circle cx="21" cy="22" r="5.5" fill="#123d24"/><path d="M11.5 38c0-5.8 4.3-9.5 9.5-9.5s9.5 3.7 9.5 9.5z" fill="#123d24"/>'
            '<circle cx="33" cy="22" r="5.5" fill="#f6fbf7"/><path d="M23.5 38c0-5.8 4.3-9.5 9.5-9.5s9.5 3.7 9.5 9.5z" fill="#f6fbf7"/></g>')


def calendar_stats(counts, start):
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i, current = len(counts) - 1, 0
    if counts[i] == 0:                    # today may simply not have happened yet
        i -= 1
    while i >= 0 and counts[i] > 0:
        current, i = current + 1, i - 1
    top = max(range(len(counts)), key=lambda k: counts[k])
    return dict(longest=longest, current=current, active=sum(c > 0 for c in counts),
                busiest=counts[top], busiest_date=start + dt.timedelta(days=top))


def build_activity(d):
    W, H, LW = 1000, 290, 250
    defs = ('<linearGradient id="bdg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7ee0a0"/>'
            '<stop offset="1" stop-color="#2e9e5a"/></linearGradient>')
    con = d["contributions"]
    counts, levels = con["counts"], con.get("levels")
    if not levels:
        levels = [0 if c == 0 else 1 if c <= 18 else 2 if c <= 37 else 3 if c < 75 else 4 for c in counts]
    start = dt.date.fromisoformat(con["start"])
    end = start + dt.timedelta(days=len(counts) - 1)
    total = con.get("total", sum(counts))
    st = calendar_stats(counts, start)

    # ---- left card: achievements + last 12 weeks
    b = [card(0, 0, LW, H), glow(0, 0, LW, H), text(22, 38, "Achievements", 15, weight=700, family=HEAD)]
    ach = CONFIG["achievements"][:3]
    for i, a in enumerate(ach):
        cx = 22 + 30 + i * 74
        b.append(badge(cx, 96))
        if a.get("tier"):
            b.append(f'<rect x="{cx+10}" y="108" width="28" height="19" rx="9.5" fill="{C["tier_bg"]}" '
                     f'stroke="url(#card{C["id"]})" stroke-width="2"/>')
            b.append(text(cx + 24, 121.5, e(a["tier"]), 10.5, C["tier_fg"], 700, anchor="middle"))
        if len(ach) > 1:
            b.append(text(cx, 146, e(a["name"]), 10.5, C["muted"], 500, anchor="middle"))
    if len(ach) == 1:
        b.append(text(22, 150, e(ach[0]["name"]), 13.5, C["fg"], 600))
    b.append(bar(22, 170, LW - 44, 1, C["line"], 0))
    weeks = [sum(counts[i:i + 7]) for i in range(max(0, len(counts) - 84), len(counts), 7)][-12:]
    peak = max(weeks) or 1
    b.append(text(22, 194, "LAST 12 WEEKS", 10, C["faint"], 500, extra='letter-spacing="1"'))
    for i, v in enumerate(weeks):
        h = max(3, 36 * v / peak)
        b.append(bar(22 + i * 16.5, 242 - h, 11, h, ACCV(), 3))
    b.append(f'<rect x="22.5" y="{H-38}" width="36" height="18" rx="9" fill="none" stroke="{C["pill_line"]}"/>')
    b.append(text(40.5, H - 25.5, "Beta", 10.5, C["beta_fg"], 500, anchor="middle"))
    b.append(text(68, H - 25.5, "Co-authored commits", 11.5, C["faint"]))

    # ---- right card: calendar + stats
    X = LW + 16
    CW = W - X
    b += [card(X, 0, CW, H), glow(X, 0, CW, H)]
    num = f"{total:,}"
    b.append(text(X + 24, 52, num, 32, ACC(), 700, family=HEAD))
    b.append(text(X + 24 + tw(num, 32, "geomini", 700) + 10, 52, "contributions in the last year", 15, C["muted"]))
    b.append(card(W - 24 - 92, 26, 92, 32, 10, inner=True))
    b.append(text(W - 24 - 78, 47, str(end.year), 13, C["fg"], 500))
    b.append(f'<path d="M{W-24-24} 40l4 4 4-4z" fill="{C["muted"]}"/>')

    lead = (start.weekday() + 1) % 7            # Sunday-first rows
    cols = (lead + len(counts) + 6) // 7
    LBL = 32
    gx, gy = X + 24 + LBL, 100
    step = (CW - 48 - LBL + 3) / cols
    cell = step - 3
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        b.append(text(X + 24, gy + row * step + cell - 1.5, name, 10, C["faint"]))
    last_m = None
    for i, (c, l) in enumerate(zip(counts, levels)):
        col, row = divmod(i + lead, 7)
        day = start + dt.timedelta(days=i)
        b.append(f'<rect x="{gx+col*step:.2f}" y="{gy+row*step:.2f}" width="{cell:.2f}" height="{cell:.2f}" rx="3" '
                 f'fill="{C["g"][l]}"><title>{c} contributions on {day.day} {MONTHS[day.month-1]} {day.year}</title></rect>')
        if row == 0 and day.month != last_m:
            if last_m is not None or day.day <= 7:
                b.append(text(f"{gx+col*step:.2f}", gy - 10, MONTHS[day.month - 1], 10.5, C["mute2"]))
            last_m = day.month
    ly = gy + 7 * step + 24
    b.append(text(X + 24, ly, e(f"{start.day} {MONTHS[start.month-1]} {start.year} – {end.day} {MONTHS[end.month-1]} {end.year}"), 11, C["faint"]))
    lx = W - 24 - (5 * 13) - 30
    b.append(text(lx - 6, ly, "Less", 11, C["faint"], anchor="end"))
    for i in range(5):
        b.append(f'<rect x="{lx+i*13}" y="{ly-9}" width="10" height="10" rx="2.5" fill="{C["g"][i]}"/>')
    b.append(text(lx + 5 * 13 + 3, ly, "More", 11, C["faint"]))

    b.append(bar(X + 24, ly + 17, CW - 48, 1, C["line"], 0))
    bd = st["busiest_date"]
    stats = [("LONGEST STREAK", st["longest"], "days"), ("CURRENT STREAK", st["current"], "days"),
             ("ACTIVE DAYS", st["active"], f"of {len(counts)}"), ("BUSIEST DAY", st["busiest"], f"on {bd.day} {MONTHS[bd.month-1]}")]
    bw = (CW - 48) / 4
    for i, (label, value, unit) in enumerate(stats):
        sx, ty = X + 24 + i * bw, ly + 45
        b.append(bar(sx, ty - 12, 3, 38, ACCV(), 1.5))
        b.append(text(sx + 13, ty, label, 9.5, C["faint"], 500, extra='letter-spacing=".9"'))
        b.append(f'<text x="{sx+13}" y="{ty+25}" font-family="{HEAD}" font-size="21" font-weight="700" fill="{C["fg"]}">'
                 f'{value}<tspan font-family="{SANS}" font-size="12" font-weight="400" fill="{C["muted"]}" dx="5">{e(unit)}</tspan></text>')
    return svg(W, H, "".join(b), defs)


def pick_repos(d):
    rs = [r for r in d["repos"] if not r.get("fork") and not r.get("private") and not r.get("archived")
          and r["name"] not in CONFIG["skip_repos"]]
    rs.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    return rs[:CONFIG["repo_count"]]


def repo_card(r, x, y, w, h):
    b = [card(x, y, w, h, 12, inner=True), bar(x + 16, y, 40, 3, ACC()), icon("repo", x + 16, y + 20, 15, ACC())]
    b.append(text(x + 40, y + 33, e(r["name"]), 15, weight=700, family=HEAD))
    px = x + 40 + tw(r["name"], 15, "geomini", 700) + 10
    pw = tw("Public", 10.5, "uncut", 500) + 18
    b.append(f'<rect x="{px:.1f}" y="{y+21.5}" width="{pw:.1f}" height="17" rx="8.5" fill="none" stroke="{C["pill_line"]}"/>')
    b.append(text(f"{px+pw/2:.1f}", y + 34, "Public", 10.5, C["pill_fg"], 500, anchor="middle"))
    b.append(html_block(x + 16, y + 48, w - 32, 44, e(r.get("description") or "No description yet."),
                        f"font-family:{SANS};font-size:12.5px;line-height:1.5;color:{C['muted']};"
                        "display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden"))
    home = (r.get("homepage") or "").strip()
    url = home.replace("https://", "").replace("http://", "").rstrip("/") if home else f'github.com/{CONFIG["user"]}/{r["name"]}'
    col = C["g"][4] if home else C["faint"]
    b.append(icon("link", x + 16, y + 102, 11, col))
    b.append(text(x + 33, y + 112, e(url), 11.5, col, family=MONO))
    my = y + h - 20
    mx = x + 16
    lang = r.get("language")
    if lang:
        b.append(f'<circle cx="{mx+5}" cy="{my-4}" r="5" fill="{LANG_COLORS.get(lang, "#8b8b8b")}"/>')
        b.append(text(mx + 15, my, e(lang), 12, C["mute2"]))
        mx += 15 + tw(lang, 12) + 16
    for ic, n in (("star", r.get("stargazers_count", 0)), ("fork", r.get("forks_count", 0))):
        b.append(icon(ic, mx, my - 11, 13, C["mute2"]))
        b.append(text(mx + 18, my, n, 12, C["mute2"]))
        mx += 18 + tw(str(n), 12) + 16
    b.append(text(x + w - 16, my, e(rel_time(r.get("pushed_at"))), 11.5, C["faint"], anchor="end"))
    return "".join(b)


def build_repos(d):
    W, H, RW = 1000, 262, 250
    LW = W - RW - 16
    b = [card(0, 0, LW, H), glow(0, 0, LW, H), text(24, 42, "Latest repositories", 19, weight=700, family=HEAD)]
    reps = pick_repos(d)
    iw = (LW - 48 - 14) / 2
    for i, r in enumerate(reps):
        b.append(repo_card(r, 24 + i * (iw + 14), 64, iw, 174))

    X = LW + 16
    b += [card(X, 0, RW, H), glow(X, 0, RW, H), text(X + 22, 38, "Find me", 15, weight=700, family=HEAD)]
    for i, (ic, label) in enumerate(CONFIG["links"]):
        yy = 62 + i * 30
        b.append(icon(ic, X + 22, yy, 15, ACC()))
        b.append(text(X + 46, yy + 12, e(label), 13, C["link"], 500))
    p = d.get("profile", {})
    b.append(bar(X + 22, H - 46, RW - 44, 1, C["line"], 0))
    b.append(f'<text x="{X+22}" y="{H-22}" font-family="{SANS}" font-size="12" fill="{C["muted"]}">'
             f'<tspan fill="{C["fg"]}" font-weight="700">{p.get("public_repos", 0)}</tspan> repos   '
             f'<tspan fill="{C["fg"]}" font-weight="700" dx="10">{p.get("followers", 0)}</tspan> followers</text>')
    return svg(W, H, "".join(b))


def build_buttons(theme):
    out = {}
    for key, ic, label in CONFIG["buttons"]:
        w = round(48 + tw(label, 12.5, "uncut", 500))
        b = [card(0, 0, w, 34, 17), icon(ic, 16, 9.5, 15, ACC()), text(38, 22, e(label), 12.5, C["link"], 500)]
        out[f"btn-{key}-{theme}.svg"] = svg(w, 34, "".join(b), fonts=("uncut",))
    return out


def main():
    offline = "--offline" in sys.argv
    d = load_data(offline)
    ASSETS.mkdir(exist_ok=True)
    files = {}
    for theme, palette in THEMES.items():
        C.clear(); C.update(palette)
        files.update({f"hero-{theme}.svg": build_hero(d), f"activity-{theme}.svg": build_activity(d),
                      f"repos-{theme}.svg": build_repos(d)})
        files.update(build_buttons(theme))
    for name, content in files.items():
        (ASSETS / name).write_text(content, encoding="utf-8")
    print("wrote", len(files), "files")


if __name__ == "__main__":
    main()
