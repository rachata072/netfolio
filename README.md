# netfolio - Networking & Cybersecurity Portfolio

A hand-built static site styled as a Cisco IOS session. No frameworks, no build
step, no trackers, no cookies. Palette: Cisco midnight navy `#0B2240` + Cisco
sky blue `#049FD9` + Cisco green `#6CC04A`.


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

### Rules to keep it secure
- Never paste third-party `<script src=...>` snippets without SRI and a CSP update - this is how portfolio sites usually get compromised (A08).
- Want comments? Use giscus (GitHub Discussions) and add its origin explicitly to the CSP rather than loosening it to `*`.
- Want a contact form? Use a hosted form endpoint (e.g., your host's forms feature) - never roll mail script.
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

