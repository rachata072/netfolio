#!/usr/bin/env python3
"""Social preview images (1200x630 PNG) for LinkedIn / X / Slack link cards.

Called by `python tools/build.py --og`. Needs Pillow:  pip install pillow
Writes public/assets/og/<slug>.webp for every post plus one per page.
WebP share images work on LinkedIn, Facebook, X, Slack, WhatsApp, Discord and iMessage.
"""
import pathlib
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE / "og-fonts"
W, H = 1200, 630

BG = (5, 13, 24)
GRID = (12, 30, 52)
LINE = (34, 73, 122)
BLUE = (4, 159, 217)
BLUE_HI = (0, 188, 235)
TEXT = (228, 238, 246)
TEXT2 = (157, 180, 200)
TEXT3 = (109, 134, 156)
UP = (108, 192, 74)
CAT = {"news": (255, 107, 94), "ai": BLUE_HI, "sec": (251, 171, 44), "python": UP, "support": (183, 166, 255), "network": (63, 214, 193)}


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def wrap(draw, text, fnt, width, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while draw.textlength(lines[-1] + "...", font=fnt) > width:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] += "..."
    return lines


def base():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 32):
        d.line([(x, 0), (x, H)], fill=GRID)
    for y in range(0, H, 32):
        d.line([(0, y), (W, y)], fill=GRID)
    # topology accent on the right
    cx = 1030
    d.line([(cx, 70), (cx, 250)], fill=LINE, width=2)
    for x in (930, 1030, 1130):
        d.line([(cx, 250), (cx, 290), (x, 290), (x, 330)], fill=LINE, width=2)
        d.rounded_rectangle([x - 36, 330, x + 36, 370], 5, fill=(11, 28, 51), outline=LINE, width=2)
        d.ellipse([x + 22, 338, x + 28, 344], fill=UP)
    d.rounded_rectangle([cx - 56, 130, cx + 56, 166], 5, fill=(11, 28, 51), outline=(255, 107, 94), width=2)
    d.rounded_rectangle([cx - 64, 214, cx + 64, 250], 5, fill=(11, 28, 51), outline=BLUE, width=2)
    for y in (100, 190):
        d.ellipse([cx - 5, y - 5, cx + 5, y + 5], fill=BLUE_HI)
    # brand
    d.rounded_rectangle([64, 56, 100, 80], 4, fill=(13, 39, 77), outline=BLUE, width=2)
    d.rectangle([71, 64, 76, 70], fill=UP)
    d.rectangle([80, 64, 85, 70], fill=BLUE)
    f = font("ibm-plex-mono-latin-600-normal.woff", 26)
    d.text((114, 52), "breakfix", font=f, fill=TEXT)
    d.text((114 + d.textlength("breakfix", font=f), 52), "learn", font=f, fill=BLUE_HI)
    d.text((114 + d.textlength("breakfixlearn", font=f), 52), ".com", font=f, fill=TEXT3)
    d.rectangle([0, H - 8, W, H], fill=BLUE)
    return im, d


def post_image(site, post, path):
    im, d = base()
    color = CAT.get(post["category"], BLUE_HI)
    c = site["categories"][post["category"]]
    mono = font("ibm-plex-mono-latin-600-normal.woff", 22)
    label = f'%BLOG-{c["sev"]}-{c["code"]}'
    tw = d.textlength(label, font=mono)
    d.rounded_rectangle([64, 150, 64 + tw + 28, 188], 4, outline=color, width=2)
    d.text((78, 154), label, font=mono, fill=color)

    title = post.get("list_title", post["title"])
    size = 64
    while True:
        tf = font("ibm-plex-sans-condensed-latin-700-normal.woff", size)
        lines = wrap(d, title, tf, 800, 4)
        if len(lines) <= 3 or size <= 50:
            break
        size -= 4
    y = 222
    for ln in lines:
        d.text((64, y), ln, font=tf, fill=TEXT)
        y += int(size * 1.12)

    meta = font("ibm-plex-mono-latin-400-normal.woff", 22)
    from datetime import date
    dd = date.fromisoformat(post["date"])
    line = f'{dd.strftime("%b")} {dd.day}, {dd.year}  /  {post["read_min"]} min read  /  by {site["author"]}'
    d.text((64, H - 84), line, font=meta, fill=TEXT2)
    im.save(path, "WEBP", quality=88, method=6)


def page_image(site, path, kicker, title, sub):
    im, d = base()
    d.text((64, 160), kicker, font=font("ibm-plex-mono-latin-400-normal.woff", 24), fill=UP)
    tf = font("ibm-plex-sans-condensed-latin-700-normal.woff", 96)
    y = 210
    for ln in title.split("\n"):
        d.text((64, y), ln, font=tf, fill=TEXT)
        y += 100
    d.text((64, H - 84), sub, font=font("ibm-plex-mono-latin-400-normal.woff", 22), fill=TEXT2)
    im.save(path, "WEBP", quality=88, method=6)


def make_all(site, posts, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    for p in posts:
        post_image(site, p, outdir / f'{p["slug"]}.webp')
    sub = f'{site["author"]}  /  CCNA  /  {site["location"]}'
    page_image(site, outdir / "default.webp", "edge# show version", "BUILD. BREAK.\nFIX. LEARN.", sub)
    page_image(site, outdir / "index.webp", "edge# show version", "BUILD. BREAK.\nFIX. LEARN.", sub)
    page_image(site, outdir / "blog.webp", "edge# show logging", f"{len(posts)} LAB LOGS\n& WRITE-UPS", sub)
    page_image(site, outdir / "projects.webp", "edge# show interfaces status", "PROJECTS:\nNET + SEC LABS", sub)
    print(f"  og images: {len(posts) + 4} written to {outdir}")
