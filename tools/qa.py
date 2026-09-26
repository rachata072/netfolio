#!/usr/bin/env python3
"""QA gate for breakfixlearn v2. Run after `python tools/build.py`, before every commit.

Checks
  structure : tag balance, exactly one <h1>, <title> + description present, lang attr
  links     : every internal href/src/srcset resolves (extension-less URLs map to .html),
              every in-page #anchor exists, no internal link opens a new tab
  security  : no inline style="", no inline <script> (JSON-LD data blocks allowed),
              no inline event handlers (onclick=...), target=_blank always has rel=noopener,
              no innerHTML / outerHTML / insertAdjacentHTML / document.write / eval in JS,
              no http:// resources (mixed content)
  content   : no em dashes (house style), images have alt + width + height,
              every raster image (posts, OG/share images, files in public/) is WebP
  seo       : canonical is extension-less and absolute, description 50-170 chars
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent / "public"
problems = []


def bad(f, msg):
    problems.append(f"{f.relative_to(ROOT)}: {msg}")


def strip_comments(s):
    return re.sub(r"<!--.*?-->", "", s, flags=re.S)


def resolve(page, url):
    url = url.split("#")[0].split("?")[0]
    if not url:
        return page
    p = (ROOT / url.lstrip("/")) if url.startswith("/") else (page.parent / url)
    if p.is_file():
        return p
    if p.with_name(p.name + ".html").is_file():
        return p.with_name(p.name + ".html")
    if (p / "index.html").is_file():
        return p / "index.html"
    if url == "/":
        return ROOT / "index.html"
    return None


ids_cache = {}


def ids_of(f):
    if f not in ids_cache:
        t = f.read_text(encoding="utf-8")
        # ids, plus JS filter deep links like /blog#sec (data-filter values)
        ids_cache[f] = set(re.findall(r'\sid="([^"]+)"', t)) | set(re.findall(r'data-filter="([^"]+)"', t))
    return ids_cache[f]


for f in sorted(ROOT.rglob("*.html")):
    html = strip_comments(f.read_text(encoding="utf-8"))

    for tag in ("div", "a", "section", "article", "figure", "table", "ul", "ol", "li", "nav", "main", "header", "footer", "p", "svg", "details"):
        o = len(re.findall(rf"<{tag}\b", html))
        c = html.count(f"</{tag}>")
        if o != c:
            bad(f, f"tag imbalance <{tag}> {o} open / {c} close")

    if len(re.findall(r"<h1\b", html)) != 1:
        bad(f, "must have exactly one <h1>")
    if not re.search(r'<html lang="[a-z-A-Z]+"', html):
        bad(f, "missing <html lang>")
    if "<title>" not in html:
        bad(f, "missing <title>")
    m = re.search(r'<meta name="description" content="([^"]*)"', html)
    if not m:
        bad(f, "missing meta description")
    elif f.name != "404.html" and not 50 <= len(m.group(1)) <= 170:
        bad(f, f"meta description length {len(m.group(1))} (aim 50-170)")
    can = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    if f.name != "404.html":
        if not can:
            bad(f, "missing canonical")
        elif can.group(1).endswith(".html") or not can.group(1).startswith("https://"):
            bad(f, f"canonical should be absolute https and extension-less: {can.group(1)}")

    # --- security ---
    if re.search(r'\sstyle="', html):
        bad(f, "inline style attribute (blocked by CSP)")
    for s in re.findall(r"<script\b([^>]*)>", html):
        if "src=" not in s and 'type="application/ld+json"' not in s:
            bad(f, "inline <script> (blocked by CSP)")
    if re.search(r"\son[a-z]+\s*=", html):
        bad(f, "inline event handler attribute (blocked by CSP)")
    for a in re.findall(r"<a\b[^>]*>", html):
        href = (re.search(r'href="([^"]*)"', a) or [None, ""])[1]
        blank = 'target="_blank"' in a
        if blank and "noopener" not in a:
            bad(f, f"target=_blank without rel=noopener: {href}")
        if blank and not href.startswith(("http://", "https://")):
            bad(f, f"internal link opens a new tab: {href}")
    if re.search(r'(?:src|href)="http://', html):
        bad(f, "http:// resource (mixed content)")

    # --- links ---
    urls = re.findall(r'(?:href|src)="([^"]+)"', html)
    for srcset in re.findall(r'srcset="([^"]+)"', html):
        urls += [part.strip().split()[0] for part in srcset.split(",") if part.strip()]
    for url in urls:
        if url.startswith(("http://", "https://", "mailto:")):
            continue
        if url.startswith("#"):
            if url != "#main" and url[1:] not in ids_of(f):
                bad(f, f"missing anchor {url}")
            continue
        target = resolve(f, url)
        if not target:
            bad(f, f"broken link {url}")
        elif ".html" in url.split("#")[0] and "/404.html" not in url:
            bad(f, f"link uses .html (Cloudflare 308-redirects it): {url}")
        elif "#" in url:
            anchor = url.split("#", 1)[1]
            if target.suffix == ".html" and anchor not in ids_of(target):
                bad(f, f"missing anchor {url}")

    # --- content ---
    if "—" in html:
        bad(f, "em dash found (house style: use a comma or colon)")
    # house rule: every raster image the site uses is WebP (SVG is fine: it's vector)
    img_urls = re.findall(r'<img\b[^>]*\ssrc="([^"]+)"', html)
    for srcset in re.findall(r'srcset="([^"]+)"', html):
        img_urls += [part.strip().split()[0] for part in srcset.split(",") if part.strip()]
    img_urls += re.findall(r'<meta property="(?:og:image|twitter:image)" content="([^"]+)"', html)
    img_urls += re.findall(r'"image":\s*"([^"]+)"', html)
    for u in img_urls:
        ext = u.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in ("webp", "svg"):
            bad(f, f"image is not WebP: {u}")
    for img in re.findall(r"<img\b[^>]*>", html, re.S):
        for attr in ("alt=", "width=", "height="):
            if attr not in img:
                bad(f, f"<img> missing {attr[:-1]}: {img[:80]}")

RASTER = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".avif", ".heic"}
for f in sorted(ROOT.rglob("*")):
    if f.is_file() and f.suffix.lower() in RASTER:
        bad(f, "non-WebP image in public/ (convert with tools/imgprep.py)")

danger = re.compile(r"\b(innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\s*\(|new Function)")
for f in sorted(ROOT.rglob("*.js")):
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), f.read_text(encoding="utf-8"), flags=re.S)
    for i, line in enumerate(src.splitlines(), 1):
        code = line.split("//")[0]
        if danger.search(code):
            bad(f, f"line {i}: dangerous DOM/eval sink")

for p in problems:
    print("FAIL", p)
print(f"\nQA {'PASS' if not problems else 'FAIL'} ({len(problems)} problems, {len(list(ROOT.rglob('*.html')))} pages checked)")
sys.exit(1 if problems else 0)
