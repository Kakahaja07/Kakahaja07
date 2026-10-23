#!/usr/bin/env python3
"""
Builds the dark bento-style SVG cards used by the profile README.

  python scripts/build_profile.py                # live data from GitHub (set GITHUB_TOKEN)
  python scripts/build_profile.py --offline      # use scripts/data.json only

Live mode needs a token for the contribution calendar (GraphQL). Inside
GitHub Actions the built-in GITHUB_TOKEN is enough. If any request fails,
the script falls back to scripts/data.json so the README never breaks.

Edit CONFIG below to change the README text, links or which repos show.
"""
import datetime as dt, html, json, os, re, sys, urllib.request
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
    "dark": dict(card="#1a1a1b", card2="#242425", line="#2c2c2e", inner_line="#303033", fg="#ededed",
                 body="#c9c9cc", muted="#9b9b9f", faint="#6c6c70", mute2="#bdbdc0", link="#d4d4d7",
                 pill_fg="#c3c3c6", pill_line="#57575b", beta_fg="#cfcfd2", tier_bg="#e8e8e8", tier_fg="#111",
                 g=["#262628", "#0e4429", "#006d32", "#26a641", "#39d353"]),
    "light": dict(card="#f6f8fa", card2="#ffffff", line="#d0d7de", inner_line="#d8dee4", fg="#1f2328",
                  body="#3d444d", muted="#59636e", faint="#6e7781", mute2="#59636e", link="#1f2328",
                  pill_fg="#3d444d", pill_line="#afb8c1", beta_fg="#3d444d", tier_bg="#1f2328", tier_fg="#ffffff",
                  g=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]),
}
C = dict(THEMES["dark"])   # active palette; main() swaps it per theme
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
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


# ---------------------------------------------------------------- svg helpers
def svg(w, h, body, extra_defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
            f'<defs>{extra_defs}</defs>{body}</svg>\n')


def card(x, y, w, h, fill=None, stroke=None, r=16):
    return (f'<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="{r}" '
            f'fill="{fill or C["card"]}" stroke="{stroke or C["line"]}"/>')


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
    W, H = 1000, 280
    b = [card(0, 0, W, H)]
    b.append(text(26, 40, e(f'{CONFIG["user"]} / README.md'), 11, C["faint"], family=MONO, extra='letter-spacing=".3"'))
    b.append(text(26, 84, e(CONFIG["greeting"]), 25, weight=600))
    paras = "".join(
        '<p style="margin:0 0 12px">' +
        e(p).replace("[[", f'<span style="color:{C["fg"]};text-decoration:underline;text-decoration-color:{C["faint"]}">').replace("]]", "</span>") +
        "</p>" for p in CONFIG["about"])
    b.append(html_block(26, 104, W - 52, H - 120, paras,
                        f"font-family:{SANS};font-size:14px;line-height:1.6;color:{C['body']}"))
    return svg(W, H, "".join(b))


def badge(cx, cy, r=27):
    return (f'<g transform="translate({cx-27} {cy-27}) scale({r/27})">'
            '<circle cx="27" cy="27" r="26" fill="url(#bdg)"/>'
            '<circle cx="27" cy="27" r="21" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1.5"/>'
            '<circle cx="21" cy="22" r="5.5" fill="#123d24"/><path d="M11.5 38c0-5.8 4.3-9.5 9.5-9.5s9.5 3.7 9.5 9.5z" fill="#123d24"/>'
            '<circle cx="33" cy="22" r="5.5" fill="#f6fbf7"/><path d="M23.5 38c0-5.8 4.3-9.5 9.5-9.5s9.5 3.7 9.5 9.5z" fill="#f6fbf7"/></g>')


def build_activity(d):
    W, H, LW = 1000, 250, 250
    defs = ('<linearGradient id="bdg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7ee0a0"/>'
            '<stop offset="1" stop-color="#2e9e5a"/></linearGradient>')
    b = [card(0, 0, LW, H), text(22, 38, "Achievements", 14, weight=600)]
    for i, a in enumerate(CONFIG["achievements"][:6]):
        cx = 22 + 27 + i * 64
        b.append(badge(cx, 86))
        if a.get("tier"):
            b.append(f'<rect x="{cx+8}" y="100" width="26" height="18" rx="9" fill="{C["tier_bg"]}" stroke="{C["card"]}" stroke-width="2"/>')
            b.append(text(cx + 21, 113, e(a["tier"]), 10, C["tier_fg"], 700, anchor="middle"))
    if len(CONFIG["achievements"]) == 1:
        b.append(text(22, 146, e(CONFIG["achievements"][0]["name"]), 12.5, C["muted"]))
    else:
        for i, a in enumerate(CONFIG["achievements"][:3]):
            b.append(text(22 + 27 + i * 64, 140, e(a["name"]), 10.5, C["muted"], anchor="middle"))
    b.append(f'<rect x="22.5" y="{H-44}" width="36" height="17" rx="8.5" fill="none" stroke="{C["pill_line"]}"/>')
    b.append(text(40.5, H - 31.5, "Beta", 10.5, C["beta_fg"], anchor="middle"))
    b.append(text(68, H - 31.5, "Co-authored commits", 11.5, C["faint"]))

    X = LW + 16
    CW = W - X
    b.append(card(X, 0, CW, H))
    con = d["contributions"]
    counts, levels = con["counts"], con.get("levels")
    if not levels:
        levels = [0 if c == 0 else 1 if c <= 18 else 2 if c <= 37 else 3 if c < 75 else 4 for c in counts]
    total = con.get("total", sum(counts))
    b.append(f'<text x="{X+24}" y="42" font-family="{SANS}" font-size="19" fill="{C["fg"]}">'
             f'<tspan font-weight="600">{total:,}</tspan> contributions in the last year</text>')
    end = dt.date.fromisoformat(con["start"]) + dt.timedelta(days=len(counts) - 1)
    b.append(card(W - 24 - 92, 20, 92, 32, C["card2"], C["line"], 10))
    b.append(text(W - 24 - 78, 41, str(end.year), 13))
    b.append(f'<path d="M{W-24-24} 34l4 4 4-4z" fill="{C["muted"]}"/>')

    start = dt.date.fromisoformat(con["start"])
    lead = (start.weekday() + 1) % 7            # Sunday-first rows
    cols = (lead + len(counts) + 6) // 7
    gx, gy, step, cell = X + 24, 96, (CW - 48 + 3) / cols, None
    cell = step - 3
    last_m = None
    for i, (c, l) in enumerate(zip(counts, levels)):
        k = i + lead
        col, row = divmod(k, 7)
        day = start + dt.timedelta(days=i)
        b.append(f'<rect x="{gx+col*step:.2f}" y="{gy+row*step:.2f}" width="{cell:.2f}" height="{cell:.2f}" rx="2.5" '
                 f'fill="{C["g"][l]}"><title>{c} contributions on {day.day} {MONTHS[day.month-1]} {day.year}</title></rect>')
        if row == 0 and day.month != last_m:
            if last_m is not None or day.day <= 7:
                b.append(text(f"{gx+col*step:.2f}", gy - 9, MONTHS[day.month - 1], 10.5, C["mute2"]))
            last_m = day.month
    ly = gy + 7 * step + 22
    b.append(text(gx, ly, e(f"{start.day} {MONTHS[start.month-1]} {start.year} – {end.day} {MONTHS[end.month-1]} {end.year}"), 11, C["faint"]))
    lx = W - 24 - (5 * 13) - 32
    b.append(text(lx - 6, ly, "Less", 11, C["faint"], anchor="end"))
    for i in range(5):
        b.append(f'<rect x="{lx+i*13}" y="{ly-9}" width="10" height="10" rx="2" fill="{C["g"][i]}"/>')
    b.append(text(lx + 5 * 13 + 3, ly, "More", 11, C["faint"]))
    return svg(W, H, "".join(b), defs)


def pick_repos(d):
    rs = [r for r in d["repos"] if not r.get("fork") and not r.get("private") and not r.get("archived")
          and r["name"] not in CONFIG["skip_repos"]]
    rs.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    return rs[:CONFIG["repo_count"]]


def repo_card(r, x, y, w, h):
    b = [card(x, y, w, h, C["card2"], C["inner_line"], 12), icon("repo", x + 16, y + 18, 15)]
    name = e(r["name"])
    b.append(text(x + 40, y + 31, name, 15, weight=600))
    px = x + 40 + len(r["name"]) * 8.6 + 10
    b.append(f'<rect x="{px:.1f}" y="{y+19.5}" width="46" height="17" rx="8.5" fill="none" stroke="{C["pill_line"]}"/>')
    b.append(text(f"{px+23:.1f}", y + 32, "Public", 10.5, C["pill_fg"], anchor="middle"))
    b.append(html_block(x + 16, y + 46, w - 32, 44, e(r.get("description") or "No description yet."),
                        f"font-family:{SANS};font-size:12.5px;line-height:1.5;color:{C['muted']};"
                        "display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden"))
    home = (r.get("homepage") or "").strip()
    url = home.replace("https://", "").replace("http://", "").rstrip("/") if home else f'github.com/{CONFIG["user"]}/{r["name"]}'
    col = C["g"][4] if home else C["faint"]
    b.append(icon("link", x + 16, y + 100, 11, col))
    b.append(text(x + 33, y + 110, e(url), 11.5, col, family=MONO))
    my = y + h - 20
    lang = r.get("language")
    mx = x + 16
    if lang:
        b.append(f'<circle cx="{mx+5}" cy="{my-4}" r="5" fill="{LANG_COLORS.get(lang, "#8b8b8b")}"/>')
        b.append(text(mx + 15, my, e(lang), 12, C["mute2"]))
        mx += 15 + len(lang) * 7 + 16
    b.append(icon("star", mx, my - 11, 13, C["mute2"]))
    b.append(text(mx + 18, my, r.get("stargazers_count", 0), 12, C["mute2"]))
    mx += 18 + len(str(r.get("stargazers_count", 0))) * 7 + 16
    b.append(icon("fork", mx, my - 11, 13, C["mute2"]))
    b.append(text(mx + 18, my, r.get("forks_count", 0), 12, C["mute2"]))
    b.append(text(x + w - 16, my, e(rel_time(r.get("pushed_at"))), 11.5, C["faint"], anchor="end"))
    return "".join(b)


def build_repos(d):
    W, H, RW = 1000, 262, 250
    LW = W - RW - 16
    b = [card(0, 0, LW, H), text(24, 42, "Latest repositories", 19, weight=500),
         f'<path d="M210 33l4 4 4-4z" fill="{C["muted"]}"/>']
    reps = pick_repos(d)
    iw = (LW - 48 - 14) / 2
    for i, r in enumerate(reps):
        b.append(repo_card(r, 24 + i * (iw + 14), 64, iw, 174))

    X = LW + 16
    b.append(card(X, 0, RW, H))
    b.append(text(X + 22, 38, "Find me", 14, weight=600))
    for i, (ic, label) in enumerate(CONFIG["links"]):
        yy = 62 + i * 30
        b.append(icon(ic, X + 22, yy, 15))
        b.append(text(X + 46, yy + 12, e(label), 13, C["link"]))
    p = d.get("profile", {})
    b.append(f'<line x1="{X+22}" y1="{H-46}" x2="{W-22}" y2="{H-46}" stroke="{C["line"]}"/>')
    b.append(f'<text x="{X+22}" y="{H-22}" font-family="{SANS}" font-size="12" fill="{C["muted"]}">'
             f'<tspan fill="{C["fg"]}" font-weight="600">{p.get("public_repos", 0)}</tspan> repos   '
             f'<tspan fill="{C["fg"]}" font-weight="600" dx="10">{p.get("followers", 0)}</tspan> followers</text>')
    return svg(W, H, "".join(b))


def build_buttons(theme):
    out = {}
    for key, ic, label in CONFIG["buttons"]:
        w = int(46 + len(label) * 7.4)
        b = [card(0, 0, w, 34, C["card"], C["line"], 17), icon(ic, 16, 9.5, 15, C["muted"]),
             text(38, 22, e(label), 12.5, C["link"])]
        out[f"btn-{key}-{theme}.svg"] = svg(w, 34, "".join(b))
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
