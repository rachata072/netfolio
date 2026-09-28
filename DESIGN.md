---
version: 1.0
name: breakfixlearn-noc-console
description: >
  breakfixlearn.com reads like a network you walk through at night: a dark rack-room
  canvas with a faint Packet Tracer grid, Cisco blue as the only brand accent, IBM Plex
  type, and every section introduced by an IOS command. Status colours (green, amber,
  red) are semantic, never decorative. Static HTML, one CSS file, strict CSP.
  Format follows VoltAgent/awesome-design-md so humans and AI agents build pages that match.

colors:
  bg: "#050D18"          # page canvas, "rack room at night"
  bg-2: "#081628"        # section band, toolbars, table heads
  panel: "#0B1C33"       # cards, consoles
  panel-2: "#0F2644"     # raised / hover / current nav port
  line: "#173457"        # hairlines
  line-2: "#22497A"      # stronger edges, secondary button border
  blue: "#049FD9"        # Cisco blue: primary fills, links on hover, focus
  blue-hi: "#00BCEB"     # Cisco bright blue: links, highlights
  on-blue: "#04121F"     # text on any blue fill (6.3:1). Never white on blue (3.0:1)
  text: "#E4EEF6"        # 16.6:1 on bg
  text-2: "#9DB4C8"      # secondary copy, 7.1:1 on panel-2
  text-3: "#7F97AC"      # meta, labels; >= 5:1 on every surface
  up: "#6CC04A"          # status up/up, current page LED, success
  amber: "#FBAB2C"       # up/down, caution, in progress
  red-soft: "#FF6B5E"    # errors, deny, danger text (7:1 on bg)
  red: "#E2231A"         # Cisco red: fills and strokes only, never body text (4.2:1)
  sheet-networking: "#00BCEB"
  sheet-cybersecurity: "#34D399"
  sheet-it-support: "#FB923C"
  sheet-ai: "#C4A7FF"

typography:
  display:  { fontFamily: "Plex Condensed", weight: 700, size: "clamp(1.7rem, 4vw, 2.4rem)", transform: uppercase, letterSpacing: "-0.01em" }
  hero:     { fontFamily: "Plex Condensed", weight: 700, size: "clamp(3.3rem, 8.2vw, 5.6rem)", lineHeight: 0.92, letterSpacing: "-0.02em", transform: uppercase }
  h1-article: { fontFamily: "Plex Sans", weight: 600, size: "clamp(1.8rem, 4.2vw, 2.7rem)", lineHeight: 1.15 }
  body:     { fontFamily: "Plex Sans", weight: 400, size: "1rem", lineHeight: 1.7 }
  mono:     { fontFamily: "Plex Mono", weight: "400/600", use: "commands, nav ports, labels, meta, buttons" }
  cli-prompt: { fontFamily: "Plex Mono", size: "0.8rem", parts: "edge# (up) show (blue-hi) args (text-2)" }

rounded: { sm: 3px, md: 4px, lg: 8px }
spacing: { gutter: "clamp(1rem, 4vw, 2rem)", section: "clamp(3rem, 7vw, 5rem)", max-width: "74rem", reading: "44rem" }
---

# breakfixlearn design system (NOC console)

## 1. Visual theme and atmosphere

A network operations console, not a template. The page is a dark canvas with a 32 px
Packet Tracer grid; content sits in consoles and cards like devices on a rack. Every
section opens with the IOS command that would show it (`edge# show logging`), the nav
is a row of switch ports with link LEDs, projects are interfaces (`Gi1/0/3`, VLAN =
category), blog posts are syslog messages (`%BLOG-4-NETWORK`), and cheat-sheet
downloads are `copy net-01 flash:`. Humour lives in those metaphors, never in copy.

Motion is small and meaningful: packets flow along the topology, a red packet is
dropped at the firewall, the hero globe turns slowly. All of it stops for
`prefers-reduced-motion`, off screen, in background tabs, and when the visitor presses
**pause motion** (WCAG 2.2.2).

## 2. Colour palette and roles

- One brand accent: Cisco blue (`blue`, `blue-hi`). Do not introduce a second accent.
- Status colours are semantic: green = up / current / shipped, amber = in progress /
  caution, red-soft = deny / danger / error. A status dot must mean a real state.
- Text on blue fills uses `on-blue` (#04121F). White on #049FD9 fails AA.
- `red` (#E2231A) is for strokes and fills; red text uses `red-soft`.
- Cheat-sheet categories keep the sheet themes, lightened for the dark canvas:
  networking cyan, cybersecurity emerald, IT support orange, AI violet. They appear
  only as small keys (ID badges, rack top borders, filter dots), never as big fills.
- Printed sheets are the exception: light paper (#FAFAF7) so they save ink. On the site
  they are shown as paper on the desk, with a shadow.

## 3. Typography rules

- IBM Plex everywhere, self-hosted WOFF2, `font-display: swap`, preload 400 and the
  condensed 700 only. No Google Fonts link (CSP `font-src 'self'`).
- Plex Condensed 700 uppercase for page and section titles; Plex Sans for reading;
  Plex Mono for anything a device would print (commands, ports, dates, sizes, labels).
- Headings use `text-wrap: balance`; paragraphs `text-wrap: pretty`.
- Numbers in columns use `font-variant-numeric: tabular-nums`.
- Real typography: `…` not `...`, no em dashes anywhere (qa.py fails the build).
- Code, commands and the wordmark carry `translate="no"`.

## 4. Component stylings

- **Button primary** `.btn.btn-pri`: blue fill, `on-blue` mono 600 text, 4 px radius,
  `# ` prompt prefix at 60 % opacity; hover goes to `blue-hi`; active moves 1 px down.
- **Button secondary** `.btn.btn-sec`: transparent panel, `line-2` border, text colour;
  hover border blue, text `blue-hi`.
- **Nav port** `.port`: mono 0.8 rem, LED dot (grey, amber on hover, green + glow when
  current), port number hidden under 64 rem, five ports fit down to 320 px.
- **Console** `.console`: panel at 92 %, `line-2` border, 8 px radius, a mono title bar
  (`lab-core / topology.pkt`) and optional status or controls on the right.
- **Filter button** `.fbtn`: mono chip with count; pressed = blue fill + `on-blue`.
- **Search** `.search`: `| include` prompt; focus = `blue-hi` border + 3 px ring.
- **Sheet card** `.scard`: paper thumbnail left (light, slight tilt on hover), ID badge,
  title, summary, exam + version line, text links. Never three identical cards in a row
  for their own sake; a young library pairs one card with the "on the bench" rack.
- **Rack** `.rack`: roadmap panel per category, 2 px category top border, rows of
  `ID | title | wave | status`.
- **Download tile** `.dl`: format key block (PDF / WebP), name, `note · size`, download
  arrow. The first tile (US Letter) is primary blue. Checksums live in a `<details>`.
- **Notes** `.note-caution` (amber) and `.note-auth` (red-soft): 3 px left border, bold
  label word first. Flags inline: `.flag-caution`.

## 5. Layout principles

- Container `74rem`, reading column `44rem`, gutters `clamp(1rem, 4vw, 2rem)`.
- Sections alternate plain canvas and `.sec-band` so neighbours never share a surface.
- Section header = CLI prompt, uppercase title, one-line lede, optional `.more` link on
  the right (`show logging | full →`). Keep ledes under 20 words on the home page.
- Grids use CSS Grid with explicit column counts per breakpoint; no leftover single
  cells (four racks = 2 × 2, four trust points = 4 or 2 × 2).

## 6. Depth and elevation

Flat panels separated by hairlines. Only three things float: the hero console
(`0 30px 80px -30px`), paper sheets (`0 40px 80px -40px`), and focus rings. Shadows are
tinted to the navy canvas, never grey.

## 7. Do's and don'ts

Do
- Introduce sections with a real IOS/CLI command that fits the content.
- Keep every animation stoppable (reduced motion, off screen, pause motion).
- Use documentation-only IPs (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24,
  2001:db8::/32) and example.com in every example.
- Give every raster image WebP format, width, height and alt text.

Don't
- Add inline `style=""`, inline scripts or event-handler attributes (CSP blocks them).
- Use white text on Cisco blue, or `red` for body text.
- Add purple/blue AI gradients, glassmorphism, stock photos or emoji icons.
- Use Lucide-style generic icons for decoration; icons are hand-drawn network glyphs.
- Write em dashes, "Elevate", "Seamless", "Unleash" or exclamation marks in copy.
- Put fake numbers on the page: counts come from the build (posts, projects, sheets).

## 8. Responsive behaviour

- Breakpoints: 64 rem (hide port numbers), 60 rem (sheet page stacks), 52 rem
  ("cheat" drops from the nav), 48 rem (touch sizes, blog legend collapses),
  40 rem (nav moves under the brand), 25 rem (small phones).
- Touch targets ≥ 44 px on coarse pointers; `touch-action: manipulation`.
- `100dvh` with `100vh` fallback. No horizontal scroll from 320 px to 1920 px
  (checked with playwright-cli, see README).
- Wide tables scroll inside `.tbl`, never the page.

## 9. Agent prompt guide

> Build it as a breakfixlearn NOC-console page: dark `#050D18` canvas with a faint grid,
> Cisco blue `#049FD9` as the only accent (text on it `#04121F`), IBM Plex Condensed
> uppercase titles, Plex Sans body, Plex Mono for anything a router would print. Open
> each section with a CLI prompt (`edge# show …`). Status colours only for real state.
> Static HTML generated by `tools/build.py`, no inline styles or scripts, WebP images
> with width/height/alt, no em dashes, documentation-only IPs. Run `python tools/qa.py`
> until it prints QA PASS, then check 375/768/1280 px with playwright-cli.
