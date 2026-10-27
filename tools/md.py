"""
Minimal Markdown -> HTML for CCNP lecture notes. Python standard library only.

Supports what the lecture files use: headings, paragraphs, **bold**, *italic*,
`code`, [links](url), ![images](src) on their own line, pipe tables, block quotes,
- / 1. lists (one level), ``` fenced code, --- rules, and <details><summary>
blocks for self-check answers.

Security (OWASP A03): every character of text is HTML-escaped BEFORE any
markup is added. The only raw HTML that survives is the exact tag set
<details>, </details>, <summary>, </summary> on lines of their own; anything
else that looks like HTML is printed as text. Link targets are allow-listed:
https://, http://, mailto:, site-relative (/...), in-page (#...) and relative
paths. javascript:, data: and friends become plain text.
"""
import html
import re

esc = lambda s: html.escape(s, quote=True)

SAFE_URL = re.compile(r"^(https?://|mailto:|/|#|[A-Za-z0-9._-]+(/|$|\.|#))")


def _safe_url(u):
    u = u.strip()
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", u) and not u.startswith(("http://", "https://", "mailto:")):
        return None
    return u if SAFE_URL.match(u) else None


def inline(text, link_hook=None):
    """Escape, then apply inline markup. link_hook(url) may rewrite internal URLs."""
    codes = []

    def keep_code(m):
        codes.append(f'<code translate="no">{esc(m.group(1))}</code>')
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", keep_code, text)
    s = esc(s)

    def link(m):
        label, url = m.group(1), html.unescape(m.group(2))
        if link_hook:
            url = link_hook(url)
        u = _safe_url(url)
        if not u:
            return m.group(0)
        if u.startswith(("http://", "https://")):
            return f'<a href="{esc(u)}" rel="noopener" target="_blank">{label}</a>'
        return f'<a href="{esc(u)}">{label}</a>'

    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)
    return s


def _cells(row):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def convert(md, image_hook=None, link_hook=None, heading_shift=0):
    """
    Returns (html, headings). headings is a list of (level, text) in order.
    image_hook(src, alt) -> html for a block image (required if images are used).
    heading_shift: added to every heading level (1 -> h2 when shift=1).
    """
    lines = md.replace("\r\n", "\n").split("\n")
    out, heads = [], []
    i, n = 0, len(lines)
    last_hr = False

    def il(t):
        return inline(t, link_hook)

    while i < n:
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        # raw allow-listed tags
        m = re.fullmatch(r"<details>\s*<summary>(.*)</summary>", s)
        if m:
            out.append(f"<details class=\"qa\"><summary>{il(m.group(1))}</summary>")
            i += 1; last_hr = False
            continue
        if s == "</details>":
            out.append("</details>")
            i += 1
            continue

        # fenced code
        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            cls = f' class="language-{esc(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{esc(chr(10).join(buf))}</code></pre>")
            last_hr = False
            continue

        # horizontal rule (collapse repeats)
        if re.fullmatch(r"-{3,}|\*{3,}", s):
            if not last_hr:
                out.append("<hr>")
            last_hr = True
            i += 1
            continue
        last_hr = False

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lvl = min(6, len(m.group(1)) + heading_shift)
            text = m.group(2).strip()
            heads.append((lvl, text))
            out.append(f"<h{lvl}>{il(text)}</h{lvl}>")
            i += 1
            continue

        # image on its own line
        m = re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+)\)", s)
        if m:
            if not image_hook:
                raise ValueError("image found but no image_hook given")
            out.append(image_hook(m.group(2), m.group(1)))
            i += 1
            continue

        # table
        if s.startswith("|") and i + 1 < n and re.fullmatch(r"\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?", lines[i + 1].strip()):
            head = _cells(s)
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            th = "".join(f'<th scope="col">{il(c)}</th>' for c in head)
            body = "".join("<tr>" + "".join(f"<td>{il(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="int-table-scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>')
            continue

        # block quote (consecutive > lines; blank > lines split paragraphs)
        if s.startswith(">"):
            paras, cur = [], []
            while i < n and lines[i].strip().startswith(">"):
                t = lines[i].strip()[1:].strip()
                if t:
                    cur.append(t)
                elif cur:
                    paras.append(cur); cur = []
                i += 1
            if cur:
                paras.append(cur)
            inner = "".join("<p>" + "<br>".join(il(t) for t in p) + "</p>" for p in paras)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # lists
        if re.match(r"^[-*]\s+", s) or re.match(r"^\d+\.\s+", s):
            ordered = bool(re.match(r"^\d+\.\s+", s))
            pat = r"^\d+\.\s+" if ordered else r"^[-*]\s+"
            items = []
            while i < n:
                t = lines[i]
                ts = t.strip()
                if re.match(pat, ts) and not t.startswith((" ", "\t")):
                    items.append([re.sub(pat, "", ts)])
                elif ts and t.startswith((" ", "\t")) and items:
                    items[-1].append(re.sub(r"^[-*]\s+|^\d+\.\s+", "", ts))
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            lis = "".join("<li>" + "<br>".join(il(x) for x in it) + "</li>" for it in items)
            out.append(f"<{tag}>{lis}</{tag}>")
            continue

        # paragraph: until blank line or another block start
        buf = [s]
        i += 1
        while i < n:
            t = lines[i].strip()
            if (not t or t.startswith(("#", ">", "|", "```", "<details", "</details")) or re.fullmatch(r"-{3,}", t)
                    or re.match(r"^[-*]\s+", t) or re.match(r"^\d+\.\s+", t) or re.fullmatch(r"!\[.*\]\(.*\)", t)):
                break
            buf.append(t)
            i += 1
        out.append("<p>" + il(" ".join(buf)) + "</p>")

    # drop a rule directly before a heading or at the very start/end (headings carry their own border)
    cleaned = []
    for k, block in enumerate(out):
        if block == "<hr>":
            nxt = out[k + 1] if k + 1 < len(out) else ""
            if not cleaned or not nxt or re.match(r"<h[1-3]>", nxt):
                continue
        cleaned.append(block)
    return "\n".join(cleaned), heads
