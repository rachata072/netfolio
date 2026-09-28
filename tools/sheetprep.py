#!/usr/bin/env python3
"""
Import one cheat sheet's exports into the site. Needs Pillow (pip install pillow).

    python tools/sheetprep.py "D:/Cheat Sheet/networking/net-01/exports"
    python tools/sheetprep.py path/to/*.pdf path/to/*.webp

Expects the project naming rule  bfl-<id>-<slug>_v<version>_<variant>.<ext>
  PDFs : _web.pdf  _print-letter.pdf  _print-a4.pdf
  WebP : _full.webp (2550x3300)  _web.webp (1200 wide)  _social.webp (1200x630)
         (.png / .jpg are accepted for these three and converted to WebP)

What it does
  1. Checks every PDF with tools/pdfcheck.py (no scripts, actions, forms, attachments,
     only https links to breakfixlearn.com, 1 page, under 2 MB). A failing file stops
     the import: nothing is copied.
  2. Checks image sizes and converts non-WebP images (the site is WebP only).
  3. Makes the 600px card thumbnail (_thumb.webp).
  4. Copies everything to public/cheat-sheets/files/ and prints the next steps.
"""
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pdfcheck import check  # noqa: E402

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: pip install pillow")

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "cheat-sheets" / "files"
NAME = re.compile(r"^bfl-(?P<id>[a-z]+-\d{2})-(?P<slug>[a-z0-9-]+)_v(?P<ver>\d+\.\d+)_"
                  r"(?P<variant>web|print-letter|print-a4|full|social)\.(?P<ext>pdf|webp|png|jpe?g)$")
PDF_VARIANTS = {"web", "print-letter", "print-a4"}
IMG_SIZE = {"full": (2550, 3300), "social": (1200, 630)}


def main(args):
    files = []
    for a in args:
        p = pathlib.Path(a)
        files += sorted(p.iterdir()) if p.is_dir() else [p]
    found, errors = {}, []
    for f in files:
        m = NAME.match(f.name.lower())
        if not m:
            continue
        key = (m["id"], m["slug"], m["ver"])
        kind = "pdf" if m["ext"] == "pdf" else "img"
        found.setdefault(key, {})[(m["variant"], kind)] = (f, m["ext"])
    if len(found) != 1:
        sys.exit(f"expected exports for exactly one sheet, found {len(found)}: {sorted(found)}"
                 "\nfile names must look like bfl-net-01-osi-model_v1.0_print-a4.pdf")
    (sid, slug, ver), parts = next(iter(found.items()))
    base = f"bfl-{sid}-{slug}_v{ver}"
    want_parts = {(v, "pdf") for v in PDF_VARIANTS} | {(v, "img") for v in ("full", "web", "social")}
    missing = sorted(f"{v}.{'pdf' if k == 'pdf' else 'webp'}" for v, k in want_parts - set(parts))
    if missing:
        errors.append(f"missing variants: {', '.join(missing)}")

    for v in PDF_VARIANTS:
        if (v, "pdf") not in parts:
            continue
        f, ext = parts[(v, "pdf")]
        for issue in check(f):
            errors.append(f"{f.name}: {issue}")

    images = {}
    for v in ("full", "web", "social"):
        if (v, "img") not in parts:
            continue
        f, ext = parts[(v, "img")]
        im = Image.open(f)
        im.load()
        want = IMG_SIZE.get(v)
        if want and im.size != want:
            errors.append(f"{f.name}: {im.size[0]}x{im.size[1]}, expected {want[0]}x{want[1]}")
        if v == "web" and im.size[0] != 1200:
            errors.append(f"{f.name}: web image must be 1200px wide, got {im.size[0]}")
        images[v] = (f, ext, im)

    if errors:
        print("Import stopped, nothing was copied:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    for v in PDF_VARIANTS:
        shutil.copyfile(parts[(v, "pdf")][0], OUT / f"{base}_{v}.pdf")
    for v, (f, ext, im) in images.items():
        dest = OUT / f"{base}_{v}.webp"
        if ext == "webp":
            shutil.copyfile(f, dest)
        else:
            im.convert("RGB").save(dest, "WEBP", quality=90, method=6)
    web = images["web"][2].convert("RGB")
    thumb = web.resize((600, round(web.size[1] * 600 / web.size[0])), Image.LANCZOS)
    thumb.save(OUT / f"{base}_thumb.webp", "WEBP", quality=82, method=6)

    print(f"Imported {sid.upper()} v{ver} into public/cheat-sheets/files/ ({base}_*)")
    print("Next:")
    print(f'  1. In src/cheatsheets.json set {sid.upper()}: "status": "live", "slug": "{slug}", "version": "{ver}",')
    print('     plus date, exam, use_when, summary, description, tags and sources (copy NET-01 as a model).')
    print(f"  2. Write the text version: src/cheat-sheets/{sid}.html")
    print("  3. python tools/build.py   then   python tools/qa.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
