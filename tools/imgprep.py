#!/usr/bin/env python3
"""
imgprep.py — pre-publish image pipeline for breakfixlearn.com

Converts JPG/PNG (and other Pillow-readable formats) to WebP at three
responsive widths, writes them into assets/img/<slug>/, and prints a
paste-ready <figure> snippet with srcset/sizes, width/height (prevents
layout shift), lazy loading, and an alt-text placeholder.

This is an AUTHORING tool, run on machine before you commit.
The deployed site stays pure static with zero dependencies.

Requires: pip install Pillow

Usage:
    python3 tools/imgprep.py my-topology.png --slug ospf-lab
    python3 tools/imgprep.py photos/*.jpg --slug soc-homelab --quality 80

Output files:
    assets/img/<slug>/<name>-480.webp
    assets/img/<slug>/<name>-800.webp
    assets/img/<slug>/<name>-1200.webp   (skipped if source is smaller)
"""

import argparse
import pathlib
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

WIDTHS = (480, 800, 1200)          # mobile / tablet / desktop
SITE_ROOT = pathlib.Path(__file__).resolve().parent.parent


def process(src: pathlib.Path, slug: str, quality: int) -> str:
    out_dir = SITE_ROOT / "assets" / "img" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(src) as im:
        im = im.convert("RGB") if im.mode in ("P", "CMYK") else im
        orig_w, orig_h = im.size
        stem = src.stem.lower().replace(" ", "-")

        made = []
        for w in WIDTHS:
            if w > orig_w and made:      # don't upscale; keep at least one size
                break
            target_w = min(w, orig_w)
            target_h = round(orig_h * target_w / orig_w)
            resized = im.resize((target_w, target_h), Image.LANCZOS)
            out = out_dir / f"{stem}-{w}.webp"
            resized.save(out, "WEBP", quality=quality, method=6)
            kb = out.stat().st_size // 1024
            made.append((w, target_w, target_h, out, kb))
            print(f"  wrote {out.relative_to(SITE_ROOT)}  ({target_w}x{target_h}, {kb} KB)")

    # Largest generated size = the <img> src fallback and intrinsic dimensions
    big_w, real_w, real_h, big_out, _ = made[-1]
    srcset = ", ".join(
        f"/assets/img/{slug}/{stem}-{w}.webp {tw}w" for (w, tw, _th, _o, _kb) in made
    )

    return f'''<figure class="post-figure">
  <img src="/assets/img/{slug}/{stem}-{big_w}.webp"
       srcset="{srcset}"
       sizes="(max-width: 46rem) 100vw, 46rem"
       width="{real_w}" height="{real_h}"
       loading="lazy" decoding="async"
       alt="DESCRIBE THE IMAGE — required for accessibility and SEO">
  <figcaption>Optional caption — delete this line if not needed.</figcaption>
</figure>'''


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert images to responsive WebP for the blog.")
    ap.add_argument("images", nargs="+", type=pathlib.Path, help="source image file(s)")
    ap.add_argument("--slug", required=True, help="post slug, becomes assets/img/<slug>/")
    ap.add_argument("--quality", type=int, default=82, help="WebP quality 1-100 (default 82)")
    args = ap.parse_args()

    snippets = []
    for src in args.images:
        if not src.exists():
            sys.exit(f"not found: {src}")
        print(f"processing {src} ...")
        snippets.append(process(src, args.slug, args.quality))

    print("\n----- paste into your post -----\n")
    print("\n\n".join(snippets))


if __name__ == "__main__":
    main()
