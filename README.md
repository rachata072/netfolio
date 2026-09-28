# breakfixlearn v2

A redesign of breakfixlearn.com, built beside the original so it can be tested
before anything is replaced. The original site in `../netfolio/` is untouched.

Still 100% static: plain HTML, one CSS file, two small vanilla JS files, and
self-hosted fonts. No framework, no CDN, no npm, no cookies. The only new thing is
a small Python build script (standard library only) that writes the static pages
for you, so you stop hand-editing the blog index, home page, RSS and sitemap.

## Test it locally

```bash
cd netfolio-v2
python tools/serve.py          # open http://localhost:8080
```

`serve.py` behaves like Cloudflare Pages: extension-less URLs (`/blog`), `.html`
redirects, the 404 page, and every header in `public/_headers` including the
strict CSP. Open DevTools > Console: if anything violates the CSP, you will see it
here before it ever reaches production. (Opening the HTML files directly with
file:// will look broken because links are root-absolute; use the server.)

## Publish a new post

1. Copy `src/post-template.html` to `src/posts/<slug>.html` and fill in the meta block.
2. `python tools/build.py --og` (the `--og` part needs `pip install pillow`)
3. `python tools/qa.py`
4. `python tools/serve.py` and check it, then commit and push.

The home page, blog index, month groups, filter counts, RSS feed, sitemap,
table of contents, series box, and previous/next links all update from that one file.
Projects live in `src/projects.json`.

## Publish a cheat sheet

1. Export the sheet (PDF web, PDF print-letter, PDF print-a4, WebP full / web / social) using the naming rule
   `bfl-<id>-<slug>_v<version>_<variant>.<ext>`.
2. `python tools/sheetprep.py "D:/Cheat Sheet/networking/net-02/exports"`
   checks the PDFs (no scripts, actions, forms, attachments; 1 page; < 2 MB), checks image sizes,
   converts PNG/JPG to WebP, makes the card thumbnail and copies everything to `public/cheat-sheets/files/`.
3. In `src/cheatsheets.json` set the sheet to `"status": "live"` and fill slug, version, date, exam,
   use_when, summary, description (120-160 chars), tags and sources (copy NET-01).
4. Write the text version in `src/cheat-sheets/<id>.html` (accessible alternative to the image, and what Google reads).
5. `python tools/build.py`, `python tools/qa.py`, preview with `python tools/serve.py`.

Pages: `/cheat-sheets` (library + roadmap of all 40) and `/cheat-sheets/<id>` (the QR code on each sheet
points here). The roadmap statuses are `planned`, `audit` (shows "in review") and `live`.

## Check the layout with playwright-cli

```bash
npm install -g @playwright/cli@latest
python tools/serve.py &                        # in another terminal on Windows
playwright-cli open http://localhost:8080/cheat-sheets
playwright-cli resize 375 812                  # then 768 1024, 1280 800
playwright-cli screenshot --full-page --filename=sheets-375.png
playwright-cli eval "() => document.documentElement.scrollWidth - innerWidth"   # must be 0
playwright-cli console error                   # must be empty
```

Design rules for new pages are in `DESIGN.md` (awesome-design-md format).

## Images: WebP only

Every raster image on the site is WebP: post screenshots and the link-preview (OG)
images alike. SVG is allowed for vector art such as the favicon.

- Convert screenshots before using them: `python tools/imgprep.py shot.png --slug <post-slug>`
  writes 480/800/1200 px WebP files to `public/assets/img/<slug>/` and prints the `<figure>` to paste.
- `python tools/build.py --og` writes the share images as WebP (supported by LinkedIn, Facebook,
  X, Slack, WhatsApp, Discord and iMessage).
- `python tools/qa.py` fails if any PNG/JPG/GIF/AVIF file sits in `public/`, or if a page, srcset,
  og:image or JSON-LD image points at anything other than `.webp` / `.svg`.

## Layout

```
netfolio-v2/
  public/            <- deploy this folder (Cloudflare Pages build output dir)
    css/ js/         hand-written, versioned by build.py (?v=hash)
    assets/fonts/    IBM Plex Sans / Mono / Condensed, woff2, OFL licensed
    assets/img/      post screenshots (only the ones posts actually use)
    assets/og/       1200x630 link-preview images (WebP), generated
    cheat-sheets/files/  sheet PDFs + WebP, copied in by tools/sheetprep.py
    _headers         security + cache headers
  src/
    site.json        name, links, blog categories, series
    projects.json    every project card
    pages/*.html     home, projects, blog, privacy, 404 templates
    posts/*.html     one file per post: meta JSON + article body
    cheatsheets.json the 40-sheet catalog (status, wave, files, sources)
    cheat-sheets/    text version of each live sheet
  tools/
    build.py  qa.py  serve.py  og.py  imgprep.py  sheetprep.py  pdfcheck.py
```

## Deploying

The site runs as a **Cloudflare Worker with static assets** (Workers & Pages >
breakfixlearn). `wrangler.jsonc` in the repo root tells the build to upload
`public/` as the site; there is no Worker script and no build step, because the
built files are committed. Cloudflare's default deploy command (`npx wrangler deploy`)
picks the config up automatically.

- `_headers` in `public/` is applied by Workers exactly like it was on Pages (and is never served).
- `/page.html` redirects to `/page`, and unknown URLs get `404.html` with a 404 status.
- Pushing `main` deploys production. Pushing any other branch uploads a preview version.
- Rollback: dashboard > Deployments > pick an older version > Deploy (or `git revert` + push).

Keep 2FA on GitHub and Cloudflare: the deploy chain is the real attack surface of a static site.

## Design

"NOC console": the site reads like a network you are walking through, not a template.

- Packet Tracer style grid canvas, Cisco palette (midnight #0D274D, Cisco blue
  #049FD9, bright #00BCEB, status green, amber, Cisco red).
- Home hero: a slowly rotating 3D "internet" globe behind the headline (`js/globe.js`,
  ~4.5 KB gzipped, plain Canvas 2D, no WebGL or libraries). Routers linked in a mesh,
  packets arcing between them, red packets dropped at a dashed security perimeter ring
  with lock nodes. It pauses off screen and in background tabs, runs at 30 fps on phones,
  leans toward the mouse on desktop, and shows one still frame for reduced-motion users.
- Nav is a row of switch ports with link LEDs (green = the page you're on).
- Home hero: an animated lab topology (internet > firewall > core switch > labs).
  Packets flow, a red packet gets dropped at the firewall ACL. Pure SVG + SMIL, no JS,
  and it switches off for people with reduced-motion enabled.
- Projects are switch interfaces (`Gi1/0/x`, VLAN = category, up/up status).
- The SOC series is a traceroute, one hop per post.
- Blog is `show logging`: month groups, syslog severity badges, live search and filters.
- Posts get a sticky table of contents, reading progress, copy buttons on code,
  a repo box, and "next hop" navigation.

## Bugs found in v1 and fixed here

| # | Issue in the old site | Impact | Fix in v2 |
|---|---|---|---|
| 1 | CSP `connect-src 'self'` while Cloudflare Web Analytics is allowed in `script-src` | The beacon script loads but its report to `cloudflareinsights.com` is blocked, so analytics under-count or record nothing | `connect-src 'self' https://cloudflareinsights.com` |
| 2 | Every internal link, canonical, sitemap and RSS URL ends in `.html` | Cloudflare Pages 308-redirects `*.html` to the extension-less URL: every click costs an extra round trip, and canonicals point at redirects (SEO) | All URLs are extension-less; `qa.py` fails the build on `.html` links |
| 3 | 49 image files deployed that no page references (3.1 MB), including 34 raw JPG screenshots from M365 projects | Wasted deploy size, and raw screenshots publicly reachable by URL | Only referenced images copied into v2. Originals left untouched in v1; review them before re-adding |
| 4 | `blog/building-my-first-ospf-lab.html` is the placeholder template ("you@lab") and is live | Thin/placeholder page indexable by Google | Not migrated. The template now lives in `src/post-template.html` and drafts never build |
| 5 | 40 internal links in posts had `target="_blank"` | Your own pages opened in new tabs | Removed for internal links; `qa.py` blocks it |
| 6 | Hero terminal used `aria-live` while typing character by character | Screen readers announce every keystroke | Typing animation removed; hero is static text + decorative SVG |
| 7 | `tools/imgprep.py` wrote to `assets/img/` at the repo root | After the move to `public/`, new images landed outside the deployed folder | Writes to `public/assets/img/` |
| 8 | Em dashes left in two posts (house style says none) | Reads as AI-written | Replaced; `qa.py` now checks |
| 9 | Meta descriptions of 11 posts were 196-259 characters | Google truncates around 155-160 | Rewritten to 142-159 chars. The longer text is kept as the on-page intro and link-preview text |
| 10 | No `og:image`, no Twitter card | LinkedIn / Slack previews were bare text | Per-post 1200x630 preview images + `summary_large_image` |
| 11 | CSS/JS/fonts served with `max-age=0, must-revalidate` (Pages default) | Revalidation request on every page view | Hash-versioned URLs + `immutable` one-year cache |
| 12 | Projects page listed 5 projects while posts linked 11 public repos | Most of your real work was invisible to recruiters | 13 project cards, each with its repo and write-up |
| 13 | No skip link, nav unusable on narrow phones | Accessibility / mobile | Skip link, focus styles, phone layout for nav, tables and topology |

Other hardening: `default-src 'none'` instead of `'self'`, `base-uri 'none'`,
`form-action 'none'`, extra `Permissions-Policy` entries, `X-Permitted-Cross-Domain-Policies`.
The blog filter only accepts URL hash values that exactly match a hard-coded filter
(allow-list), and nothing from the URL or the search box is ever written into the page.

## Security posture (OWASP Top 10:2025)

| Risk | How it's handled |
|---|---|
| A01 Broken Access Control | No auth, no server logic, no admin panel. Nothing private is deployed: only `public/` goes to Cloudflare. |
| A02 Security Misconfiguration | `_headers`: strict CSP (`default-src 'none'`), frame-ancestors none, nosniff, referrer policy, permissions policy, COOP/CORP, HSTS. Downloads get their own narrower CSP (see below). |
| A03 Software Supply Chain Failures | Zero runtime dependencies, no CDN, no npm packages shipped. Build tools are Python standard library (Pillow only for images). Fonts self-hosted. |
| A04 Cryptographic Failures | HTTPS only, HSTS, no secrets anywhere in the repo. Every cheat-sheet download lists its SHA-256 hash. |
| A05 Injection | No `innerHTML`/`eval` (qa.py enforces). DOM writes are `textContent`/attributes. Build output is HTML-escaped; JSON-LD can't close its script tag. Filter deep links are allow-listed. PDFs are scanned for JavaScript, actions and forms. |
| A06 Insecure Design | Static-first: no forms, no comments, mailto for contact. Cheat sheets are flat one-page files; the site never accepts uploads. |
| A07 Authentication Failures | None on the site; protect GitHub and Cloudflare with 2FA (the deploy chain is the real attack surface). |
| A08 Software or Data Integrity Failures | `tools/pdfcheck.py` (run by qa.py and sheetprep.py) rejects PDFs with `/JavaScript`, `/Launch`, `/OpenAction`, forms, attachments, encryption or links outside breakfixlearn.com. SHA-256 per file on each sheet page and in JSON-LD. |
| A09 Security Logging and Alerting Failures | Cloudflare Web Analytics + Workers logs; CSP allows the beacon to report. |
| A10 Mishandling of Exceptional Conditions | Build fails loudly on missing files, bad IDs or unknown categories; qa.py fails on broken links; JS wraps storage access so a blocked localStorage never breaks a page; unknown URLs get the 404 page with a real 404 status. |

### Cheat-sheet downloads

- Files live in `public/cheat-sheets/files/` and are served with
  `! Content-Security-Policy` + a PDF-only policy (`default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data: blob:; object-src 'self'; frame-ancestors 'none'`).
  Chrome's PDF viewer injects styles, so the site-wide `style-src 'self'` would show a blank page.
  Scripts stay blocked.
- Download links are same-origin with the `download` attribute; external links use `rel="noopener"`.
- Examples on every sheet use documentation-only addresses (RFC 5737, RFC 3849) and example.com.

## Before going live

- Search Console + Bing Webmaster Tools: resubmit `sitemap.xml` (URLs changed to extension-less; the old `.html` URLs still redirect, so nothing breaks).
- The privacy page date was bumped to Sep 25, 2026 because a "Fonts and scripts" section was added. Adjust it to your launch date.
- Run Lighthouse on the deployed preview URL.
