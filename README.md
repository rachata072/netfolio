# netfolio - Networking & Cybersecurity Portfolio

A hand-built static site styled as a Cisco IOS session. No frameworks, no build
step, no trackers, no cookies. Palette: Cisco midnight navy `#0B2240` + Cisco
sky blue `#049FD9` + Cisco green `#6CC04A`.

## Before you deploy - personalize it

Search-and-replace these placeholders in every `.html` file:

1. `Trey` - your actual name
2. `https://breakfixlearn.com` - your real domain (canonical URLs, sitemap, robots.txt)
3. `treyrct858@gmail.com`, `yourhandle` - contact email, GitHub, LinkedIn
4. Edit `js/main.js` - the `LINES` array holds the text typed in the hero terminal
5. Replace placeholder projects and blog entries with your real ones

## Deploy (pick one - all free, all HTTPS by default)

### Repo layout

```
README.md        <- dev docs, stays on GitHub, never deployed
tools/           <- authoring scripts (imgprep.py, qa.py), never deployed
public/          <- THE SITE. Only this folder is deployed.
```

### Option A: Cloudflare Pages or Netlify (recommended)
The `public/_headers` file is applied automatically, giving you the full
security header set (CSP, HSTS, X-Frame-Options, etc.).

1. Push this repo to GitHub
2. Cloudflare Pages / Netlify -> "New project" -> connect the repo
3. Build command: (leave empty) · **Build output directory: `public`**
4. Add your custom domain in the dashboard

Because only `public/` is published, README.md and tools/ are visible on
GitHub but never reachable at breakfixlearn.com.

If your existing Cloudflare Pages project currently deploys from the repo
root, change it under: your project -> Settings -> Builds & deployments ->
Build output directory -> `public`, then retry the latest deployment.

### Option B: GitHub Pages
Works, but GitHub Pages cannot set custom HTTP headers, so the CSP and other
headers in `_headers` will NOT apply. You still get HTTPS. If you use GitHub
Pages, consider adding this fallback inside each page's `<head>`:

```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'">
```

(A real header is stronger than the meta tag - `frame-ancestors` and some
directives only work as headers - which is why Option A is recommended.)

## Adding a blog post

1. Copy `blog/building-my-first-ospf-lab.html` → `blog/your-new-post.html`
2. Edit the `<title>`, meta description, canonical URL, JSON-LD dates, and body
3. Add a `.syslog-line` entry at the TOP of the list in `blog.html`
   (and optionally the latest-posts feed on `index.html`)
4. Add the URL to `sitemap.xml` with today's date
5. Add an `<item>` to the TOP of `feed.xml` (template comment is inside the
   file) and bump `<lastBuildDate>` - this is what RSS readers see

## Images in blog posts (WebP workflow)

The site has no build step, so image optimization happens once, before you
commit, with the authoring tool `tools/imgprep.py` (needs `pip install Pillow`
on YOUR machine only - the deployed site still has zero dependencies):

```bash
python3 tools/imgprep.py topology.png --slug my-post-slug   # run from the repo root
```

It writes `assets/img/my-post-slug/topology-{480,800,1200}.webp` and prints a
ready `<figure class="post-figure">` snippet with:

- `srcset` + `sizes` - phones download the 480px file, desktops the 1200px one
- `width`/`height` attributes - reserves space, so no layout shift (helps
  Core Web Vitals / Lighthouse CLS)
- `loading="lazy" decoding="async"` - images below the fold don't block render
- an `alt=` placeholder you MUST fill in (accessibility + image SEO)

Rules: always paste the generated snippet rather than hand-writing `<img>`;
never hotlink images from other domains (the CSP's `img-src 'self'` will block
them anyway, by design - OWASP A05/A08: no third-party content injection).

## Categories

Both the blog and projects pages have category filters, styled as IOS pipe
filters (`show logging | include SEC`). They are driven by `data-cat`
attributes and `js/filter.js` - no library, CSP-safe, and if JavaScript is
off the filters simply hide and everything stays visible.

**Blog categories** (set `data-cat` on the `.syslog-line` and use the matching
facility label + color class):

| `data-cat` | Facility label | Class | Meaning |
|---|---|---|---|
| `sec` | `%BLOG-5-SEC:` | `fac cat-sec` | security news breakdowns |
| `lab` | `%BLOG-6-LAB:` | `fac cat-lab` | network lab walkthroughs |
| `python` | `%BLOG-6-PYTHON:` | `fac cat-python` | Python automation notes |

**Project categories** (set `data-cat` on the `.card`):
`routing` (routing & switching labs) · `automation` (Python tools) ·
`security` (blue-team / SOC work).

To add a new category: add a `.filter-btn` with `data-filter="yourcat"` to the
page's `.filter-bar`, tag entries with `data-cat="yourcat"`, and (for blog)
add a `fac cat-yourcat` color rule in `css/style.css`.

## Security posture (OWASP Top 10 mapping)

This is a fully static site - the strongest security decision here is
architectural: there is no server-side code to attack.

| OWASP 2021 | How it's addressed |
|---|---|
| A01 Broken Access Control | No auth, no server logic, no admin panel. Nothing to escalate. |
| A02 Cryptographic Failures | HTTPS enforced by host + HSTS header. No secrets stored anywhere. |
| A03 Injection / XSS | No user input is rendered. `js/main.js` only writes hard-coded constants via `textContent`/`createTextNode` - never `innerHTML`. Strict CSP (`script-src 'self'`) as defense-in-depth. |
| A04 Insecure Design | Static-first design: blog is flat HTML, no comment system, no contact form (mailto instead). Smallest possible attack surface. |
| A05 Security Misconfiguration | `_headers` sets CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, HSTS, COOP/CORP. No directory listing on static hosts. |
| A06 Vulnerable Components | Zero dependencies. No CDN scripts, no jQuery, no framework, no npm. Nothing to patch. |
| A07 Auth Failures | No authentication exists. Protect the DEPLOY pipeline instead: enable 2FA on GitHub + your hosting account. |
| A08 Integrity Failures | No third-party scripts, so no SRI needed. If you ever add one, use `integrity=` + `crossorigin` attributes. |
| A09 Logging & Monitoring | Use your host's access logs / analytics (Cloudflare gives this free, privacy-friendly, no JS needed). |
| A10 SSRF | No server-side requests exist. |

### Rules to keep it secure as you grow it
- Never paste third-party `<script src=...>` snippets without SRI and a CSP update - this is how portfolio sites usually get compromised (A08).
- Want comments? Use giscus (GitHub Discussions) and add its origin explicitly to the CSP rather than loosening it to `*`.
- Want a contact form? Use a hosted form endpoint (e.g., your host's forms feature) - never roll your own mail script.
- Keep 2FA on GitHub and the hosting dashboard; the deploy chain IS your attack surface now.

## SEO checklist (already done, verify after deploy)

- [x] Unique `<title>` + meta description per page
- [x] Canonical URLs (update the domain!)
- [x] Semantic HTML: one `<h1>` per page, `<article>`, `<nav>`, landmarks
- [x] JSON-LD: `Person` on home, `BlogPosting` on posts
- [x] Open Graph tags for link previews
- [x] `sitemap.xml` + `robots.txt`
- [ ] After deploy: submit sitemap in Google Search Console + Bing Webmaster Tools
- [ ] After deploy: run Lighthouse (aim 95+ on all four categories)
- [ ] Post consistently - for ranking, real content beats every tag on this list

## Accessibility & QA (already done)

- Keyboard focus visible on all links/controls
- `prefers-reduced-motion` respected (terminal renders instantly, cursor stops blinking)
- `<noscript>` fallback: hero content readable with JS disabled
- Color contrast checked against the navy background
- Responsive to ~360px; project table scrolls horizontally on small screens
- Custom 404 page (`404.html` - picked up automatically by Netlify/CF Pages/GH Pages)
