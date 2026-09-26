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

## Layout

```
netfolio-v2/
  public/            <- deploy this folder (Cloudflare Pages build output dir)
    css/ js/         hand-written, versioned by build.py (?v=hash)
    assets/fonts/    IBM Plex Sans / Mono / Condensed, woff2, OFL licensed
    assets/img/      post screenshots (only the ones posts actually use)
    assets/og/       1200x630 link-preview images, generated
    _headers         security + cache headers
  src/
    site.json        name, links, blog categories, series
    projects.json    every project card
    pages/*.html     home, projects, blog, privacy, 404 templates
    posts/*.html     one file per post: meta JSON + article body
  tools/
    build.py  qa.py  serve.py  og.py  imgprep.py
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

## Security posture (OWASP Top 10: 2021)

| Risk | How it's handled |
|---|---|
| A01 Broken Access Control | No auth, no server logic, no admin panel. |
| A02 Cryptographic Failures | HTTPS only, HSTS, no secrets anywhere in the repo. |
| A03 Injection / XSS | No `innerHTML`/`eval` (qa.py enforces). All DOM writes are `textContent`/attributes. Build output is HTML-escaped. Strict CSP with no `unsafe-inline`. |
| A04 Insecure Design | Static-first: no forms, no comments, mailto for contact. |
| A05 Misconfiguration | `_headers`: CSP, frame-ancestors none, nosniff, referrer policy, permissions policy, COOP/CORP. |
| A06 Vulnerable Components | Zero runtime dependencies. Fonts self-hosted. |
| A07 Auth Failures | None on the site; protect GitHub + Cloudflare with 2FA. |
| A08 Integrity Failures | No third-party scripts except Cloudflare's own beacon (injected by Cloudflare). |
| A09 Logging & Monitoring | Cloudflare Web Analytics + access logs (now actually able to report, see bug #1). |
| A10 SSRF | No server-side requests. |

## Before going live

- Search Console + Bing Webmaster Tools: resubmit `sitemap.xml` (URLs changed to extension-less; the old `.html` URLs still redirect, so nothing breaks).
- The privacy page date was bumped to Sep 25, 2026 because a "Fonts and scripts" section was added. Adjust it to your launch date.
- Run Lighthouse on the deployed preview URL.
