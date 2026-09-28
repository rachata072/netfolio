#!/usr/bin/env python3
"""
Static safety check for PDFs we publish (OWASP A08:2025 Software or Data Integrity
Failures, A05:2025 Injection). Standard library only, used by qa.py and sheetprep.py.

A cheat sheet is a flat, printed page. It never needs scripts, forms, attachments or
actions, so any of those in a file means the export went wrong or the file was
tampered with. The check looks at the raw bytes and inside every Flate-compressed
stream (object streams can hide dictionaries).

    python tools/pdfcheck.py file.pdf [...]
"""
import re
import sys
import zlib

# PDF names that can run code, open other files/apps, submit data or carry payloads
BANNED = rb"/(JavaScript|JS|Launch|EmbeddedFiles?|RichMedia|XFA|AcroForm|SubmitForm|ImportData|GoToR|GoToE|OpenAction|AA|Encrypt|Sound|Movie)(?![A-Za-z0-9+#])"
ALLOWED_LINK_HOSTS = ("breakfixlearn.com", "www.breakfixlearn.com")
MAX_BYTES = 2 * 1024 * 1024  # plan: web PDF under 2 MB


def _streams(data):
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end == -1:
            break
        chunk = data[start:end].rstrip(b"\r\n")
        try:
            yield zlib.decompress(chunk)
        except zlib.error:
            continue


def check(path, max_pages=1):
    """Return a list of human-readable problems (empty list = safe)."""
    problems = []
    try:
        data = open(path, "rb").read()
    except OSError as e:
        return [f"cannot read: {e}"]
    if not data.startswith(b"%PDF-"):
        return ["not a PDF (missing %PDF- header)"]
    if len(data) > MAX_BYTES:
        problems.append(f"{len(data) // 1024} KB is over the {MAX_BYTES // 1024} KB budget")
    blobs = [data] + list(_streams(data))
    found = set()
    for b in blobs:
        found.update(n.decode() for n in re.findall(BANNED, b))
    for name in sorted(found):
        problems.append(f"contains /{name} (scripts, actions, forms, attachments and encryption are not allowed)")
    uris = set()
    for b in blobs:
        uris.update(u.decode("latin-1") for u in re.findall(rb"/URI\s*\(([^)]*)\)", b))
    for u in sorted(uris):
        m = re.match(r"https://([^/:?#]+)", u)
        if not m or m.group(1).lower() not in ALLOWED_LINK_HOSTS:
            problems.append(f"link to {u!r} (only https links to {', '.join(ALLOWED_LINK_HOSTS)} are allowed)")
    pages = len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", b"".join(blobs)))
    if max_pages and pages > max_pages:
        problems.append(f"{pages} pages (a cheat sheet is {max_pages} page)")
    return problems


if __name__ == "__main__":
    bad = 0
    for f in sys.argv[1:]:
        issues = check(f)
        bad += bool(issues)
        print(("FAIL " if issues else "ok   ") + f)
        for i in issues:
            print("     - " + i)
    sys.exit(1 if bad else 0)
