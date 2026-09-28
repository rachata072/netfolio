#!/usr/bin/env python3
"""
breakfixlearn v2 static builder. Python 3.8+ standard library only.

    python tools/build.py          # build everything into public/
    python tools/build.py --og     # also (re)generate social images (needs Pillow)

Inputs (src/):
    site.json         site-wide settings, categories, series
    projects.json     project list (home table + projects page)
    posts/*.html      one file per post: a <!--meta {json} --> header + the body HTML
    pages/*.html      page templates with {{TOKENS}} filled in here

Outputs (public/): every *.html page, blog/*.html, feed.xml, sitemap.xml.
Static assets (css, js, fonts, img, _headers, robots.txt) live in public/ already.

Security notes (OWASP A03): every value that comes from JSON is HTML-escaped
before it is written. Post bodies are trusted author HTML (you wrote them).
JSON-LD is serialised with json.dumps and "</" escaped so it can never close
its <script> block.
"""
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PUB = ROOT / "public"

esc = lambda s: html.escape(str(s), quote=True)
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
MONTHS_LONG = ("January February March April May June July August "
               "September October November December").split()

VLAN = {  # project category -> vlan tag used across the site
    "network":    ("10", "NETWORK", "routing &amp; switching"),
    "automation": ("20", "AUTOMATION", "python &amp; powershell"),
    "security":   ("30", "SECURITY", "blue team"),
    "support":    ("40", "SYSADMIN", "IT support &amp; systems"),
}
STATUS = {"up": ("st-up", "up/up"), "prog": ("st-prog", "up/down"), "admin": ("st-admin", "admin down")}


# --------------------------------------------------------------------------- io
def read_meta(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"<!--meta\s*\n(.*?)\n-->\s*\n", text, re.S)
    if not m:
        sys.exit(f"missing <!--meta ... --> header in {path}")
    return json.loads(m.group(1)), text[m.end():]


def write(rel, content):
    out = PUB / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    old = out.read_text(encoding="utf-8") if out.exists() else None
    if old != content:
        out.write_text(content, encoding="utf-8", newline="\n")
        print(f"  wrote {rel}")


def asset_hash(rel):
    return hashlib.sha256((PUB / rel).read_bytes()).hexdigest()[:10]


def fmt_date(iso, long=False):
    d = dt.date.fromisoformat(iso)
    return f"{MONTHS[d.month-1]} {d.day}, {d.year}"


def rfc822(iso):
    d = dt.datetime.fromisoformat(iso + "T09:00:00-07:00")
    return d.strftime("%a, %d %b %Y %H:%M:%S %z")


def ld(obj):
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
            + "</script>")


def slugify(text, seen):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-") or "section"
    base, n = s, 2
    while s in seen:
        s = f"{base}-{n}"; n += 1
    seen.add(s)
    return s


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


# ----------------------------------------------------------------------- shared
BRAND_SVG = ('<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true" focusable="false">'
             '<rect x="1.5" y="7" width="29" height="18" rx="3.5" fill="#0D274D" stroke="#049FD9" stroke-width="1.5"/>'
             '<rect x="6" y="14" width="4" height="4" rx="0.8" fill="#6CC04A"/>'
             '<rect x="12" y="14" width="4" height="4" rx="0.8" fill="#049FD9"/>'
             '<rect x="18" y="14" width="4" height="4" rx="0.8" fill="#049FD9"/>'
             '<rect x="24" y="14" width="3" height="4" rx="0.8" fill="#22497A"/>'
             '<path d="M6 11h7" stroke="#00BCEB" stroke-width="1.2" stroke-linecap="round"/></svg>')

# (key, href, port number, label). "cheat " is hidden on narrow phones so five ports fit.
NAV = [("home", "/", "01", "home"), ("projects", "/projects", "02", "projects"), ("blog", "/blog", "03", "blog"),
       ("sheets", "/cheat-sheets", "04", '<span class="lg">cheat </span>sheets'), ("about", "/#about", "05", "about")]


def header(active):
    ports = []
    for name, href, num, label in NAV:
        cur = ' aria-current="page"' if name == active else ""
        ports.append(f'<li><a class="port" href="{href}"{cur}><span class="led" aria-hidden="true"></span>'
                     f'<span class="pn" aria-hidden="true">{num}</span>{label}</a></li>')
    return (
        '<a class="skip" href="#main">Skip to content</a>\n'
        '<header class="hdr">\n  <div class="wrap">\n'
        f'    <a class="brand" href="/" aria-label="breakfixlearn home">{BRAND_SVG}'
        '<span translate="no"><span class="b1">breakfix</span><span class="b2">learn</span><span class="b3">.com</span></span></a>\n'
        '    <nav aria-label="Main">\n      <ul class="ports">\n        '
        + "\n        ".join(ports) +
        '\n      </ul>\n    </nav>\n  </div>\n</header>\n'
    )


def footer(site, last_change):
    year = dt.date.today().year
    return f'''<footer class="ftr">
  <div class="wrap ftr-grid">
    <div>
      <a class="brand" href="/" aria-label="breakfixlearn home">{BRAND_SVG}<span translate="no"><span class="b1">breakfix</span><span class="b2">learn</span></span></a>
      <p>Build it, break it, fix it, learn it. Network and security lab notes by {esc(site["author"])}, written by hand in {esc(site["location"])}.</p>
    </div>
    <nav aria-label="Site">
      <h2>site</h2>
      <ul>
        <li><a href="/projects">projects</a></li>
        <li><a href="/blog">blog</a></li>
        <li><a href="/cheat-sheets">cheat sheets</a></li>
        <li><a href="/#about">about</a></li>
        <li><a href="/privacy">privacy</a></li>
        <li><a href="/feed.xml">rss feed</a></li>
      </ul>
    </nav>
    <nav aria-label="Elsewhere">
      <h2>elsewhere</h2>
      <ul>
        <li><a href="{esc(site["github"])}" rel="me noopener" target="_blank">github</a></li>
        <li><a href="{esc(site["linkedin"])}" rel="me noopener" target="_blank">linkedin</a></li>
        <li><a href="mailto:{esc(site["email"])}">email</a></li>
      </ul>
    </nav>
  </div>
  <div class="wrap"><div class="ftr-base">
    <span>&copy; {year} {esc(site["author"])} &middot; built by hand &middot; no cookies &middot; no trackers</span>
    <span><span class="ok" aria-hidden="true">&#9679;</span> last config change {esc(fmt_date(last_change))} &middot; uptime: learning since {site["since"]}</span>
  </div></div>
</footer>
'''


def head(site, *, title, description, path, og_title=None, og_description=None, og_image=None,
         og_image_alt=None, og_type="website", jsonld=(), noindex=False, preload_display=False,
         scripts=(), article=None, hashes=None):
    url = site["url"] + path
    og_image = og_image or "/assets/og/default.webp"
    tags = [
        "<!DOCTYPE html>",
        '<html lang="en-CA">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
    ]
    if noindex:
        tags.append('<meta name="robots" content="noindex">')
    else:
        tags.append(f'<link rel="canonical" href="{esc(url)}">')
    tags += [
        '<meta name="theme-color" content="#050D18">',
        '<meta name="color-scheme" content="dark">',
        '<link rel="preload" href="/assets/fonts/ibm-plex-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>',
    ]
    if preload_display:
        tags.append('<link rel="preload" href="/assets/fonts/ibm-plex-sans-condensed-latin-700-normal.woff2" as="font" type="font/woff2" crossorigin>')
    tags += [
        f'<link rel="stylesheet" href="/css/style.css?v={hashes["css/style.css"]}">',
        '<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">',
        f'<link rel="alternate" type="application/rss+xml" title="{esc(site["name"])} RSS" href="/feed.xml">',
    ]
    if not noindex:
        tags += [
            f'<meta property="og:type" content="{og_type}">',
            f'<meta property="og:site_name" content="{esc(site["name"])}">',
            '<meta property="og:locale" content="en_CA">',
            f'<meta property="og:title" content="{esc(og_title or title)}">',
            f'<meta property="og:description" content="{esc(og_description or description)}">',
            f'<meta property="og:url" content="{esc(url)}">',
            f'<meta property="og:image" content="{esc(site["url"] + og_image)}">',
            '<meta property="og:image:type" content="image/webp">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{esc(og_image_alt or og_title or title)}">',
            '<meta name="twitter:card" content="summary_large_image">',
        ]
        if article:
            tags.append(f'<meta property="article:published_time" content="{article["date"]}">')
            for t in article.get("tags", [])[:6]:
                tags.append(f'<meta property="article:tag" content="{esc(t)}">')
    for obj in jsonld:
        tags.append(ld(obj))
    tags.append(f'<script src="/js/main.js?v={hashes["js/main.js"]}" defer></script>')
    for s in scripts:
        tags.append(f'<script src="/js/{s}.js?v={hashes[f"js/{s}.js"]}" defer></script>')
    tags.append("</head>")
    return "\n".join(tags) + "\n"


def page(site, hashes, last_change, *, nav, body, progress=False, **kw):
    return (head(site, hashes=hashes, **kw)
            + "<body>\n"
            + ('<div class="progress" aria-hidden="true"></div>\n' if progress else "")
            + header(nav) + body.rstrip() + "\n" + footer(site, last_change)
            + "</body>\n</html>\n")


# ------------------------------------------------------------------------ posts
def load_posts():
    posts = []
    for f in sorted((SRC / "posts").glob("*.html")):
        meta, body = read_meta(f)
        if meta.get("draft"):
            continue
        meta["slug"] = f.stem
        meta["body"] = body
        meta.setdefault("summary", meta["description"])
        meta["path"] = f"/blog/{f.stem}"
        posts.append(meta)
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


def add_heading_ids(body):
    seen, toc = set(), []

    def repl(m):
        attrs, inner = m.group(1), m.group(2)
        if "id=" in attrs:
            hid = re.search(r'id="([^"]+)"', attrs).group(1)
            seen.add(hid)
            toc.append((hid, strip_tags(inner)))
            return m.group(0)
        hid = slugify(strip_tags(inner), seen)
        toc.append((hid, strip_tags(inner)))
        return f'<h2 id="{hid}"{attrs}>{inner}</h2>'

    body = re.sub(r"<h2([^>]*)>(.*?)</h2>", repl, body, flags=re.S)
    return body, toc


def sev_badge(site, cat, full=False):
    c = site["categories"][cat]
    label = f'%BLOG-{c["sev"]}-{c["code"]}' if full else f'{c["code"]}-{c["sev"]}'
    return f'<span class="sev c-{cat}">{label}</span>'


def no_translate(body):
    return re.sub(r"<(pre|code)(?=[\s>])(?![^>]*translate=)", r'<\1 translate="no"', body)


def render_post(site, hashes, last_change, post, posts):
    body, toc = add_heading_ids(post["body"])
    body = no_translate(body)
    cat = post["category"]
    c = site["categories"][cat]

    # series box
    series_html = ""
    if post.get("series"):
        ser = site["series"][post["series"]]
        parts = sorted([p for p in posts if p.get("series") == post["series"]], key=lambda p: p["series_part"])
        items = []
        for p in parts:
            if p["slug"] == post["slug"]:
                items.append(f'<li><span class="here" aria-current="page">{esc(p["title"])}</span></li>')
            else:
                items.append(f'<li><a href="{p["path"]}">{esc(p["title"])}</a></li>')
        series_html = (f'<nav class="series" aria-label="{esc(ser["name"])} series">'
                       f'<div class="series-head"><span>traceroute <b>{esc(ser["name"])}</b></span>'
                       f'<span>hop {post["series_part"]} of {len(parts)}</span></div>'
                       f'<ol>{"".join(items)}</ol></nav>\n')

    toc_items = "".join(f'<li><a href="#{hid}">{esc(t)}</a></li>' for hid, t in toc)
    toc_aside = (f'<aside class="toc" aria-label="On this page"><span class="toc-title">'
                 f'<span class="h">#</span> show ip route | toc</span><ol>{toc_items}</ol></aside>') if toc else ""
    toc_mobile = (f'<details class="toc-mobile"><summary>show ip route | toc ({len(toc)} sections)</summary>'
                  f'<ol>{toc_items}</ol></details>\n') if len(toc) > 2 else ""

    # prev / next (chronological)
    i = posts.index(post)
    newer = posts[i - 1] if i > 0 else None
    older = posts[i + 1] if i + 1 < len(posts) else None
    hop = []
    if older:
        hop.append(f'<a class="prev" href="{older["path"]}"><span class="k">&larr; previous hop</span>{esc(older.get("list_title", older["title"]))}</a>')
    if newer:
        hop.append(f'<a class="next" href="{newer["path"]}"><span class="k">next hop &rarr;</span>{esc(newer.get("list_title", newer["title"]))}</a>')

    repo_html = ""
    meta_repo = ""
    if post.get("repo"):
        r = f'{site["github"]}/{post["repo"]}'
        meta_repo = f'<span class="sep">/</span><a href="{esc(r)}" rel="noopener" target="_blank">source on github &#8599;</a>'
        repo_html = (f'<div class="repo-box"><div><span class="k">source for this post</span>'
                     f'<span class="v">github.com/rachata072/{esc(post["repo"])}</span></div>'
                     f'<a class="btn btn-sec" href="{esc(r)}" rel="noopener" target="_blank">view repo <span aria-hidden="true">&#8599;</span></a></div>')

    tags = "".join(f'<span class="chip">{esc(t)}</span>' for t in post.get("tags", []))

    main = f'''<main id="main">
<article>
  <header class="post-head">
    <div class="wrap">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="/">~</a><span aria-hidden="true">/</span><a href="/blog">blog</a><span aria-hidden="true">/</span><a href="/blog#{cat}">{esc(c["code"].lower())}</a></nav>
      {sev_badge(site, cat, full=True)}
      <h1 class="mt-2">{esc(post["title"])}</h1>
      <p class="post-dek">{esc(post["og_description"])}</p>
      <div class="post-meta"><time datetime="{post["date"]}">{fmt_date(post["date"])}</time><span class="sep">/</span><span>{post["read_min"]} min read</span><span class="sep">/</span><span>by {esc(site["author"])}</span>{meta_repo}</div>
      <div class="post-tags">{tags}</div>
    </div>
  </header>
  <div class="wrap post-layout">
    <div class="post-main">
{series_html}{toc_mobile}<div class="prose">
{body.rstrip()}
</div>
      <footer class="post-end">
        {repo_html}
        <nav class="nexthop" aria-label="More posts">{"".join(hop)}</nav>
      </footer>
    </div>
    {toc_aside}
  </div>
</article>
</main>
'''
    url = site["url"] + post["path"]
    jsonld = [{
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post["title"][:110],
        "description": post["description"],
        "datePublished": post["date"],
        "dateModified": post.get("updated", post["date"]),
        "author": {"@type": "Person", "name": site["author"], "url": site["url"] + "/"},
        "publisher": {"@type": "Person", "name": site["author"]},
        "mainEntityOfPage": url,
        "image": site["url"] + f'/assets/og/{post["slug"]}.webp',
        "keywords": ", ".join(post.get("tags", [])),
        "articleSection": c["name"],
        "timeRequired": f'PT{post["read_min"]}M',
    }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": site["url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": site["url"] + "/blog"},
            {"@type": "ListItem", "position": 3, "name": post["title"]},
        ],
    }]
    if post.get("faq"):
        jsonld.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in post["faq"]],
        })
    og_img = f'/assets/og/{post["slug"]}.webp'
    if not (PUB / og_img.lstrip("/")).exists():
        og_img = None
    return page(site, hashes, last_change, nav="blog", body=main, progress=True,
                title=f'{post.get("seo_title", post["title"])} | Trey',
                description=post["description"], path=post["path"],
                og_title=post["title"], og_description=post["og_description"],
                og_image=og_img, og_type="article", jsonld=jsonld, article=post)


# ------------------------------------------------------------------ page blocks
def block_series(site, posts, key="soc-homelab"):
    parts = sorted([p for p in posts if p.get("series") == key], key=lambda p: p["series_part"])
    ser = site["series"][key]
    rows = []
    for p in parts:
        rows.append(f'<li><a class="hop" href="{p["path"]}"><span class="num">{p["series_part"]:>2}</span>'
                    f'<span class="t">{esc(p["title"])}<span class="d">{fmt_date(p["date"])}</span></span>'
                    f'<span class="ms">{p["read_min"]} min</span></a></li>')
    return (f'<div class="trace-wrap"><div class="trace-head" aria-hidden="true"><span class="h">edge#</span> <span class="v">traceroute</span> '
            f'{esc(ser["name"].lower())}<br>Tracing the route to {esc(ser["name"])}, {len(parts)} hops max</div>'
            f'<ol class="trace" aria-label="{esc(ser["name"])} series, {len(parts)} parts">{"".join(rows)}</ol></div>')


def block_ifs_table(projects, limit=7):
    rows = []
    for i, p in enumerate(projects[:limit], 1):
        vid, vname, _ = VLAN[p["cat"]]
        cls, label = STATUS[p["status"]]
        name = f'<a href="/projects#{p["id"]}">{esc(p["name"])}</a>'
        short = p["blurb"].split(". ")[0].rstrip(".") + "."
        rows.append(
            f'<tr><td class="port-id">Gi1/0/{i}</td><td class="nm">{name}</td>'
            f'<td class="st-cell"><span class="st {cls}">{label}</span></td>'
            f'<td class="vlan">{vid} {vname}</td><td class="ds">{esc(short)}</td></tr>')
    return ('<table class="ifs"><caption class="sr-only">Projects as switch interfaces</caption>'
            '<thead><tr><th scope="col">Port</th><th scope="col">Name</th><th scope="col">Status</th>'
            '<th scope="col">Vlan</th><th scope="col">Description</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def block_latest(site, posts, n=4):
    cards = []
    for p in posts[:n]:
        cards.append(
            f'<a class="logcard c-{p["category"]}" href="{p["path"]}">'
            f'<span class="top">{sev_badge(site, p["category"])}<time datetime="{p["date"]}">{fmt_date(p["date"])}</time>'
            f'<span class="rt">&middot; {p["read_min"]} min</span></span>'
            f'<h3>{esc(p.get("list_title", p["title"]))}</h3><p>{esc(p["summary"])}</p></a>')
    return '<div class="logs">' + "".join(cards) + "</div>"


def block_filters(pairs, total):
    btns = [f'<button type="button" class="fbtn" data-filter="all" aria-pressed="true">all <span class="ct">{total}</span></button>']
    for key, label, count, color in pairs:
        dot = f'<span class="dot {color}" aria-hidden="true"></span>' if color else ""
        btns.append(f'<button type="button" class="fbtn" data-filter="{key}" aria-pressed="false">{dot}{label} <span class="ct">{count}</span></button>')
    return "\n        ".join(btns)


def block_legend(site, cat_counts):
    rows = []
    for key, c in sorted(site["categories"].items(), key=lambda kv: kv[1]["sev"]):
        n = cat_counts.get(key, 0)
        count = f"{n} post{'s' if n != 1 else ''}" if n else "coming soon"
        rows.append(
            f'<div class="fac-row c-{key}{" is-empty" if not n else ""}">'
            f'<dt><span class="sev c-{key}">{c["code"]}-{c["sev"]}</span>'
            f'<span class="lvl">{c["sev"]} {esc(c["level"])}</span></dt>'
            f'<dd><b>{esc(c["name"])}</b> {esc(c["desc"])} <span class="ct">{count}</span></dd></div>')
    return ('<details class="facilities" open><summary><span class="h">edge#</span> show logging facilities</summary>'
            '<dl>' + "".join(rows) + "</dl></details>")


def block_blog_list(site, posts):
    out, current = [], None
    for p in posts:
        d = dt.date.fromisoformat(p["date"])
        key = f"m-{d.year}-{d.month:02d}"
        if key != current:
            if current:
                out.append("</ol>")
            out.append(f'<h2 class="month" data-month="{key}">{MONTHS_LONG[d.month-1]} {d.year}</h2>')
            out.append(f'<ol class="loglist" id="{key}">')
            current = key
        c = site["categories"][p["category"]]
        search = " ".join([p.get("list_title", p["title"]), p["summary"], " ".join(p.get("tags", [])), c["code"], c["name"]]).lower()
        out.append(
            f'<li data-cat="{p["category"]}" data-search="{esc(search)}"><a class="logrow" href="{p["path"]}">'
            f'<time class="date" datetime="{p["date"]}">{MONTHS[d.month-1]}<b>{d.day:02d}</b></time>'
            f'<div><div class="meta">{sev_badge(site, p["category"])}<span class="fac">%BLOG-{c["sev"]}-{c["code"]} &middot; {p["read_min"]} min read</span></div>'
            f'<h3>{esc(p.get("list_title", p["title"]))}</h3><p>{esc(p["summary"])}</p></div></a></li>')
    if current:
        out.append("</ol>")
    return "\n    ".join(out)


def block_project_cards(site, projects, posts_by_slug):
    cards = []
    for i, p in enumerate(projects, 1):
        vid, vname, vdesc = VLAN[p["cat"]]
        cls, label = STATUS[p["status"]]
        chips = "".join(f'<span class="chip">{esc(t)}</span>' for t in p.get("tags", []))
        links = []
        if p.get("post"):
            if p["post"] not in posts_by_slug:
                sys.exit(f'project {p["id"]}: unknown post {p["post"]}')
            links.append(f'<a href="/blog/{p["post"]}">{esc(p.get("post_label", "read the write-up"))} &rarr;</a>')
        if p.get("repo"):
            links.append(f'<a href="{esc(site["github"])}/{esc(p["repo"])}" rel="noopener" target="_blank">repo &#8599;</a>')
        if not links:
            links.append('<span class="na">write-up coming</span>')
        search = " ".join([p["name"], p["blurb"], " ".join(p.get("tags", []))]).lower()
        cards.append(
            f'<article class="pcard" id="{esc(p["id"])}" data-cat="{p["cat"]}" data-search="{esc(search)}">'
            f'<div class="pcard-bar"><span>Gi1/0/{i} &middot; vlan {vid} {vname}</span><span class="st {cls}">{label}</span></div>'
            f'<div class="pcard-body"><h2>{esc(p["name"])}</h2><p>{esc(p["blurb"])}</p><div class="chips">{chips}</div></div>'
            f'<div class="pcard-links">{"".join(links)}</div></article>')
    return "\n      ".join(cards)


# ------------------------------------------------------------------ cheat sheets
SHEET_FILES = "/cheat-sheets/files"
SHEET_STATUS = {"live": ("st-up", "published"), "audit": ("st-prog", "in review"), "planned": ("st-plan", "planned")}
DOWNLOADS = [  # variant, format label, name, note
    ("print-letter", "PDF", "US Letter", "print"),
    ("print-a4", "PDF", "A4", "print"),
    ("web", "PDF", "Screen", "links work"),
    ("full", "WebP", "Hi-res image", "2550 &times; 3300"),
]


def webp_size(path):
    """Width/height of a WebP file from its header (VP8, VP8L or VP8X), stdlib only."""
    b = path.read_bytes()[:40]
    if b[:4] != b"RIFF" or b[8:12] != b"WEBP":
        sys.exit(f"{path} is not a WebP file")
    kind = b[12:16]
    if kind == b"VP8X":
        return 1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little")
    if kind == b"VP8L":
        bits = int.from_bytes(b[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if kind == b"VP8 ":
        return int.from_bytes(b[26:28], "little") & 0x3FFF, int.from_bytes(b[28:30], "little") & 0x3FFF
    sys.exit(f"{path}: unknown WebP chunk {kind!r}")


def human_size(n):
    return f"{n / 1024 / 1024:.1f} MB" if n >= 1024 * 1024 else f"{round(n / 1024)} KB"


def load_sheets():
    data = json.loads((SRC / "cheatsheets.json").read_text(encoding="utf-8"))
    cats = data["categories"]
    seen = set()
    for sh in data["sheets"]:
        sid = sh["id"]
        if sid in seen or not re.fullmatch(r"[A-Z]+-\d{2}", sid):
            sys.exit(f"cheatsheets.json: bad or duplicate id {sid!r}")
        seen.add(sid)
        if sh["cat"] not in cats:
            sys.exit(f"cheatsheets.json: {sid} has unknown category {sh['cat']!r}")
        if sh["status"] not in SHEET_STATUS:
            sys.exit(f"cheatsheets.json: {sid} has unknown status {sh['status']!r}")
        sh["key"] = sid.lower()
        sh["path"] = f"/cheat-sheets/{sh['key']}"
        if sh["status"] != "live":
            continue
        base = f"bfl-{sh['key']}-{sh['slug']}_v{sh['version']}"
        sh["files"] = {}
        for variant, ext in [("web", "pdf"), ("print-letter", "pdf"), ("print-a4", "pdf"),
                             ("full", "webp"), ("web", "webp"), ("social", "webp"), ("thumb", "webp")]:
            name = f"{base}_{variant}.{ext}"
            f = PUB / "cheat-sheets" / "files" / name
            if not f.is_file():
                sys.exit(f"{sid}: missing {f.relative_to(ROOT)} (run tools/sheetprep.py on the exports)")
            raw = f.read_bytes()
            info = {"name": name, "url": f"{SHEET_FILES}/{name}", "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest()}
            if ext == "webp":
                info["w"], info["h"] = webp_size(f)
            sh["files"][f"{variant}.{ext}"] = info
        body_f = SRC / "cheat-sheets" / f"{sh['key']}.html"
        if not body_f.is_file():
            sys.exit(f"{sid}: missing text version {body_f.relative_to(ROOT)}")
        sh["body"] = re.sub(r"<!--.*?-->", "", body_f.read_text(encoding="utf-8"), flags=re.S).strip()
    return data


def sheet_badge(sh):
    return f'<span class="sid k-{sh["cat"]}">{esc(sh["id"])}</span>'


def sheet_search(data, sh):
    c = data["categories"][sh["cat"]]
    return esc(" ".join([sh["id"], sh["title"], c["name"], sh.get("summary", ""), " ".join(sh.get("tags", []))]).lower())


def block_sheet_cards(data, sheets, heading="h3"):
    cards = []
    for sh in sheets:
        c = data["categories"][sh["cat"]]
        th = sh["files"]["thumb.webp"]
        cards.append(
            f'<article class="scard" data-cat="{sh["cat"]}" data-search="{sheet_search(data, sh)}">'
            f'<a class="scard-img" href="{sh["path"]}" tabindex="-1" aria-hidden="true">'
            f'<img src="{th["url"]}" width="{th["w"]}" height="{th["h"]}" alt="" loading="lazy" decoding="async"></a>'
            f'<div class="scard-body"><p class="scard-meta">{sheet_badge(sh)}<span>{esc(c["name"])}</span></p>'
            f'<{heading}><a href="{sh["path"]}">{esc(sh["title"])}</a></{heading}>'
            f'<p>{esc(sh["summary"])}</p>'
            f'<p class="scard-foot"><span>{esc(sh["exam"])}</span><span>v{esc(sh["version"])} &middot; {fmt_date(sh["date"])}</span></p>'
            f'<p class="scard-links"><a href="{sh["path"]}">open sheet &rarr;</a>'
            f'<a href="{sh["files"]["print-letter.pdf"]["url"]}" download>PDF Letter</a>'
            f'<a href="{sh["files"]["print-a4.pdf"]["url"]}" download>PDF A4</a></p>'
            f'</div></article>')
    return "\n      ".join(cards)


def block_sheet_roadmap(data):
    racks = []
    for key, c in data["categories"].items():
        items = [sh for sh in data["sheets"] if sh["cat"] == key]
        live = sum(1 for sh in items if sh["status"] == "live")
        rows = []
        for sh in sorted(items, key=lambda x: x["id"]):
            cls, label = SHEET_STATUS[sh["status"]]
            title = (f'<a href="{sh["path"]}">{esc(sh["title"])}</a>' if sh["status"] == "live" else esc(sh["title"]))
            rows.append(f'<li data-cat="{key}" data-search="{sheet_search(data, sh)}">'
                        f'<span class="rid">{esc(sh["id"])}</span><span class="rt">{title}</span>'
                        f'<span class="rw" title="Release wave {sh["wave"]}">w{sh["wave"]}</span>'
                        f'<span class="st {cls}">{label}</span></li>')
        racks.append(
            f'<section class="rack k-{key}" data-month="rm-{key}" aria-labelledby="rm-{key}-h">'
            f'<h3 id="rm-{key}-h"><span class="sid k-{key}">{esc(c["code"])}</span>{esc(c["name"])}'
            f'<span class="ct">{len(items)} sheets &middot; {live} live</span></h3>'
            f'<ol class="rack-list" id="rm-{key}">{"".join(rows)}</ol></section>')
    return "\n      ".join(racks)


def block_sheet_teaser(data, live):
    """Home page: newest live sheet next to what ships next (keeps the row full while the library is young)."""
    order = list(data["categories"])
    upcoming = sorted([sh for sh in data["sheets"] if sh["status"] != "live"],
                      key=lambda x: (x["wave"], order.index(x["cat"]), x["id"]))[:6]
    rows = "".join(f'<li class="k-{sh["cat"]}"><span class="rid">{esc(sh["id"])}</span><span class="rt">{esc(sh["title"])}</span>'
                   f'<span class="rw">w{sh["wave"]}</span></li>' for sh in upcoming)
    nxt = (f'<div class="rack k-networking next-up"><h3><span class="sid">next</span>On the bench'
           f'<span class="ct">{len([s for s in data["sheets"] if s["status"] != "live"])} to go</span></h3>'
           f'<ol class="rack-list">{rows}</ol></div>')
    return block_sheet_cards(data, live[-1:]) + "\n        " + nxt


def block_sheet_filters(data):
    counts = {}
    for sh in data["sheets"]:
        counts[sh["cat"]] = counts.get(sh["cat"], 0) + 1
    return block_filters([(k, esc(c.get("short", c["name"]).lower()), counts.get(k, 0), f"k-{k}")
                          for k, c in data["categories"].items()], len(data["sheets"]))


def render_sheet(site, hashes, last_change, data, sh, posts_by_slug):
    c = data["categories"][sh["cat"]]
    lic = data["license"]
    fl = sh["files"]
    web, full, social = fl["web.webp"], fl["full.webp"], fl["social.webp"]
    body = re.sub(r"<(/?)h2\b", r"<\1h3", sh["body"])  # page h2 is "Text version"
    body = no_translate(body)

    tiles = []
    for i, (variant, fmt, name, note) in enumerate(DOWNLOADS):
        f = fl[f"{variant}.{'webp' if fmt == 'WebP' else 'pdf'}"]
        tiles.append(
            f'<li><a class="dl{" dl-pri" if i == 0 else ""}" href="{f["url"]}" download>'
            f'<span class="dl-k">{fmt}</span><span class="dl-t"><b>{name}</b>'
            f'<span class="dl-m">{note} &middot; {human_size(f["bytes"])}</span></span>'
            f'<svg class="dl-i" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M8 2v8m0 0L4.5 6.5M8 10l3.5-3.5M3 13h10"/></svg>'
            f'<span class="sr-only">, download</span></a></li>')
    sums = "".join(f'<tr><td translate="no">{esc(f["name"])}</td><td translate="no">{f["sha256"]}</td></tr>'
                   for k, f in fl.items() if not k.startswith(("thumb", "social", "web.webp")))
    sources = "".join(f'<li><a href="{esc(u)}" rel="noopener" target="_blank">{esc(t)}</a></li>' for t, u in sh.get("sources", []))
    related = ""
    for slug in sh.get("related", []):
        p = posts_by_slug.get(slug)
        if not p:
            sys.exit(f'{sh["id"]}: related post {slug!r} not found')
        related += f'<li><a href="{p["path"]}">{esc(p.get("list_title", p["title"]))}</a></li>'
    related_html = f'<h3>Go deeper on the blog</h3><ul>{related}</ul>' if related else ""

    # previous / next live sheet
    live = [x for x in data["sheets"] if x["status"] == "live"]
    i = live.index(sh)
    hop = []
    if i > 0:
        hop.append(f'<a class="prev" href="{live[i-1]["path"]}"><span class="k">&larr; previous sheet</span>{esc(live[i-1]["id"])} {esc(live[i-1]["title"])}</a>')
    if i + 1 < len(live):
        hop.append(f'<a class="next" href="{live[i+1]["path"]}"><span class="k">next sheet &rarr;</span>{esc(live[i+1]["id"])} {esc(live[i+1]["title"])}</a>')
    nexthop = f'<nav class="nexthop" aria-label="More cheat sheets">{"".join(hop)}</nav>' if hop else ""

    main = f'''<main id="main">
<article class="sheet">
  <header class="post-head sheet-head">
    <div class="wrap">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="/">~</a><span aria-hidden="true">/</span><a href="/cheat-sheets">cheat-sheets</a><span aria-hidden="true">/</span><a href="/cheat-sheets#{sh["cat"]}">{esc(c["code"].lower())}</a></nav>
      <p class="scard-meta">{sheet_badge(sh)}<span>{esc(c["name"])}</span></p>
      <h1>{esc(sh["title"])}</h1>
      <p class="post-dek"><b>Use this when:</b> {esc(sh["use_when"][0].lower() + sh["use_when"][1:])}</p>
      <div class="post-meta"><span>{esc(sh["exam"])}</span><span class="sep">/</span><span>v{esc(sh["version"])}</span><span class="sep">/</span><time datetime="{sh["date"]}">{fmt_date(sh["date"])}</time><span class="sep">/</span><span>1 page</span><span class="sep">/</span><a href="{esc(lic["url"])}" rel="license noopener" target="_blank">{esc(lic["name"])}</a></div>
    </div>
  </header>
  <div class="wrap sheet-grid">
    <figure class="sheet-paper">
      <a href="{full["url"]}" aria-label="Open the full-size {esc(sh["id"])} image ({full["w"]} by {full["h"]} pixels)">
        <img src="{web["url"]}" srcset="{web["url"]} {web["w"]}w, {full["url"]} {full["w"]}w" sizes="(max-width: 60rem) calc(100vw - 2rem), 46rem"
             width="{web["w"]}" height="{web["h"]}" fetchpriority="high" decoding="async"
             alt="{esc(sh["id"])} {esc(sh["title"])} cheat sheet. Every table on it is repeated as text below.">
      </a>
      <figcaption>Tap the sheet for the full-size image. The <a href="#text-version">text version</a> below is screen-reader friendly.</figcaption>
    </figure>
    <aside class="sheet-side" aria-labelledby="dl-h">
      <span class="cli" aria-hidden="true"><span class="h">edge#</span> <span class="v">copy</span> <span class="a">{esc(sh["key"])} flash:</span></span>
      <h2 id="dl-h" class="side-h">Download</h2>
      <ul class="dl-list">{"".join(tiles)}</ul>
      <p class="dl-open"><a href="{fl["web.pdf"]["url"]}">Open the PDF in your browser</a> instead of downloading it.</p>
      <details class="sums">
        <summary>Verify your download (SHA-256)</summary>
        <div class="tbl"><table class="sheet-files"><thead><tr><th scope="col">File</th><th scope="col">SHA-256</th></tr></thead><tbody>{sums}</tbody></table></div>
        <p>Compare the hash with the one printed by
          <code translate="no">Get-FileHash .\\file.pdf -Algorithm SHA256</code> (PowerShell) or
          <code translate="no">sha256sum file.pdf</code> (Linux, macOS: <code translate="no">shasum -a 256</code>). Different hash, different file: delete it.</p>
      </details>
      <p class="side-note">Free for personal and classroom use under {esc(lic["name"])}. Keep the credit line; don't sell it. Spotted a mistake? <a href="mailto:{esc(site["email"])}?subject={esc(sh["id"])}%20v{esc(sh["version"])}%20correction">Email a correction</a>.</p>
    </aside>
  </div>
  <section class="wrap sheet-text" aria-labelledby="text-version">
    <div class="prose">
      <h2 id="text-version">Text version</h2>
      <p>Everything on the sheet, as plain HTML: handy for screen readers, copy-paste and search.</p>
{body}
      <h3>Sources</h3>
      <ul>{sources}</ul>
      {related_html}
    </div>
    {nexthop}
  </section>
</article>
</main>
'''
    url = site["url"] + sh["path"]
    media = []
    for variant, fmt, name, note in DOWNLOADS:
        f = fl[f"{variant}.{'webp' if fmt == 'WebP' else 'pdf'}"]
        media.append({"@type": "MediaObject", "name": f'{sh["id"]} {sh["title"]} ({name})',
                      "contentUrl": site["url"] + f["url"],
                      "encodingFormat": "image/webp" if fmt == "WebP" else "application/pdf",
                      "contentSize": human_size(f["bytes"]), "sha256": f["sha256"]})
    jsonld = [{
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "name": f'{sh["id"]} {sh["title"]} cheat sheet',
        "description": sh["description"],
        "url": url,
        "learningResourceType": "Cheat sheet",
        "educationalLevel": "Beginner",
        "teaches": sh["title"],
        "keywords": ", ".join(sh.get("tags", [])),
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "license": lic["url"],
        "version": sh["version"],
        "datePublished": sh["date"],
        "dateModified": sh.get("updated", sh["date"]),
        "image": site["url"] + social["url"],
        "author": {"@type": "Person", "name": site["author"], "url": site["url"] + "/"},
        "encoding": media,
    }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": site["url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": "Cheat sheets", "item": site["url"] + "/cheat-sheets"},
            {"@type": "ListItem", "position": 3, "name": f'{sh["id"]} {sh["title"]}'},
        ],
    }]
    return page(site, hashes, last_change, nav="sheets", body=main,
                title=f'{sh["id"]} {sh["title"]} Cheat Sheet (PDF) | breakfixlearn',
                description=sh["description"], path=sh["path"],
                og_title=f'{sh["title"]} cheat sheet ({sh["id"]})', og_description=sh["summary"],
                og_image=social["url"], og_image_alt=f'{sh["id"]} {sh["title"]} cheat sheet preview',
                jsonld=jsonld)


# ------------------------------------------------------------------ feed / map
def feed(site, posts):
    items = []
    for p in posts:
        link = site["url"] + p["path"]
        items.append(f'''  <item>
    <title>{esc(p.get("list_title", p["title"]))}</title>
    <link>{link}</link>
    <guid isPermaLink="false">{link}.html</guid>
    <pubDate>{rfc822(p["date"])}</pubDate>
    <category>{site["categories"][p["category"]]["code"]}</category>
    <description>{esc(p["summary"])}</description>
  </item>''')
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>breakfixlearn - network lab notes &amp; security write-ups</title>
  <link>{site["url"]}/</link>
  <description>CCNA lab walkthroughs, security write-ups, and Python network automation notes by {esc(site["author"])}.</description>
  <language>en-ca</language>
  <lastBuildDate>{rfc822(posts[0]["date"])}</lastBuildDate>
  <atom:link href="{site["url"]}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
</channel>
</rss>
'''


def sitemap(site, posts, pages):
    urls = [(site["url"] + path, lastmod) for path, lastmod in pages]
    urls += [(site["url"] + p["path"], p.get("updated", p["date"])) for p in posts]
    body = "\n".join(f"  <url><loc>{esc(u)}</loc><lastmod>{m}</lastmod></url>" for u, m in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n")


# ------------------------------------------------------------------------- main
def main():
    site = json.loads((SRC / "site.json").read_text(encoding="utf-8"))
    projects = json.loads((SRC / "projects.json").read_text(encoding="utf-8"))
    posts = load_posts()
    by_slug = {p["slug"]: p for p in posts}
    hashes = {k: asset_hash(k) for k in ["css/style.css"] + [f"js/{f.name}" for f in sorted((PUB / "js").glob("*.js"))]}
    last_change = max(p.get("updated", p["date"]) for p in posts)

    if "--og" in sys.argv:
        from og import make_all  # noqa: optional, needs Pillow
        make_all(site, posts, PUB / "assets" / "og")

    print(f"building {len(posts)} posts, {len(projects)} projects")
    for p in posts:
        write(f'blog/{p["slug"]}.html', render_post(site, hashes, last_change, p, posts))

    # counts per category
    cat_counts = {}
    for p in posts:
        cat_counts[p["category"]] = cat_counts.get(p["category"], 0) + 1
    blog_filters = block_filters(
        [(k, v["code"].lower(), cat_counts[k], f"c-{k}") for k, v in site["categories"].items() if k in cat_counts],
        len(posts))
    proj_counts = {}
    for p in projects:
        proj_counts[p["cat"]] = proj_counts.get(p["cat"], 0) + 1
    proj_filters = block_filters(
        [(k, f"{VLAN[k][0]} {VLAN[k][1].lower()}", proj_counts[k], "") for k in VLAN if k in proj_counts],
        len(projects))
    shipped = sum(1 for p in projects if p["status"] == "up")

    sheets = load_sheets()
    live_sheets = [sh for sh in sheets["sheets"] if sh["status"] == "live"]
    for sh in live_sheets:
        write(f'cheat-sheets/{sh["key"]}.html', render_sheet(site, hashes, last_change, sheets, sh, by_slug))
    n_sheets = len(sheets["sheets"])

    tokens = {
        "POST_COUNT": str(len(posts)),
        "LAST_CHANGE": fmt_date(last_change),
        "SERIES_TRACE": block_series(site, posts),
        "IFS_TABLE": block_ifs_table(projects),
        "LATEST": block_latest(site, posts),
        "BLOG_FILTERS": blog_filters,
        "BLOG_LEGEND": block_legend(site, cat_counts),
        "BLOG_LIST": block_blog_list(site, posts),
        "PROJECT_FILTERS": proj_filters,
        "PROJECT_CARDS": block_project_cards(site, projects, by_slug),
        "PROJECT_SUMMARY": f"{len(projects)} interfaces, {shipped} up/up.",
        "SHEET_FILTERS": block_sheet_filters(sheets),
        "SHEET_CARDS": block_sheet_cards(sheets, live_sheets),
        "SHEET_ROADMAP": block_sheet_roadmap(sheets),
        "SHEET_COUNT": str(n_sheets),
        "SHEET_LIVE": str(len(live_sheets)),
        "SHEETS_TEASER": block_sheet_teaser(sheets, live_sheets),
    }

    for f in sorted((SRC / "pages").glob("*.html")):
        meta, body = read_meta(f)
        for k, v in tokens.items():
            body = body.replace("{{" + k + "}}", v)
        left = re.findall(r"\{\{[A-Z_]+\}\}", body)
        if left:
            sys.exit(f"unfilled tokens in {f.name}: {left}")
        jsonld = []
        if meta["path"] == "/":
            jsonld = [{
                "@context": "https://schema.org", "@type": "Person",
                "name": site["author"], "url": site["url"] + "/", "jobTitle": site["job_title"],
                "email": "mailto:" + site["email"],
                "address": {"@type": "PostalAddress", "addressLocality": "Vancouver", "addressRegion": "BC", "addressCountry": "CA"},
                "sameAs": [site["github"], site["linkedin"]],
                "knowsAbout": site["knows_about"],
            }, {
                "@context": "https://schema.org", "@type": "WebSite",
                "name": site["name"], "url": site["url"] + "/",
            }]
        og = f'/assets/og/{f.stem}.webp'
        write(meta["out"], page(
            site, hashes, last_change, nav=meta.get("nav", ""), body=body,
            title=meta["title"], description=meta["description"], path=meta["path"],
            og_title=meta.get("og_title"), og_description=meta.get("og_description"),
            og_image=og if (PUB / og.lstrip("/")).exists() else None,
            jsonld=jsonld, noindex=meta.get("noindex", False),
            preload_display=meta.get("preload_display", False),
            scripts=meta.get("scripts", [])))

    write("feed.xml", feed(site, posts))
    sheets_mod = max([sh.get("updated", sh["date"]) for sh in live_sheets] or [last_change])
    write("sitemap.xml", sitemap(site, posts, [("/", last_change), ("/projects", last_change),
                                                ("/blog", last_change), ("/cheat-sheets", sheets_mod),
                                                ("/privacy", "2026-09-28")]
                                 + [(sh["path"], sh.get("updated", sh["date"])) for sh in live_sheets]))
    print("done")


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    main()
