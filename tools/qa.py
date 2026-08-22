#!/usr/bin/env python3
"""QA checks for breakfixlearn.com — run before every commit.
Checks: tag balance, broken internal links (ignores commented-out markup),
inline styles (CSP violation), innerHTML usage in JS."""
import re, pathlib, sys

root = pathlib.Path(__file__).resolve().parent.parent / "public"
ok = True

def strip_comments(html):
    return re.sub(r'<!--.*?-->', '', html, flags=re.S)

for f in root.rglob('*.html'):
    html = strip_comments(f.read_text())
    for tag in ('div','a','button','section','article','figure','table'):
        o = len(re.findall(rf'<{tag}\b', html)); c = html.count(f'</{tag}>')
        if o != c: print(f"IMBALANCE {f.relative_to(root)}: <{tag}> {o}/{c}"); ok = False
    for href in re.findall(r'(?:href|src)="([^"]+)"', html):
        if href.startswith(('http','mailto:','#')): continue
        t = (root/href.lstrip('/')) if href.startswith('/') else (f.parent/href)
        t = pathlib.Path(str(t).split('#')[0])
        if not t.exists(): print(f"BROKEN in {f.relative_to(root)}: {href}"); ok = False
    if re.search(r'style="', html):
        print(f"INLINE STYLE (CSP violation) in {f.relative_to(root)}"); ok = False

for f in root.rglob('js/*.js'):
    for i, line in enumerate(f.read_text().splitlines(), 1):
        if 'innerHTML' in line and 'never' not in line and 'No innerHTML' not in line:
            print(f"innerHTML in {f.relative_to(root)}:{i}"); ok = False

print("QA PASS" if ok else "QA FAIL")
sys.exit(0 if ok else 1)
