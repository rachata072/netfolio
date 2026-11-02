"""
CCNP Security study hub: lecture pages, flashcards and mock exam data.
Called from build.py. Python standard library only.

Inputs (src/ccnp/):
    course.json          exam blueprint (domains, weights, objectives) + lecture list
    lectures/<file>.md   lecture notes in Markdown (tools/md.py), images in lectures/img/
    flashcards.json      {"cards": [{id, obj, front, back, ref}]}
    questions.json       {"questions": [{id, obj, type, stem, options, answer, explanation, ref}]}

Outputs (public/):
    ccnp-security/<slug>.html            one page per lecture
    assets/img/ccnp/<module>/*.webp      lecture figures (copied when changed)
    ccnp-security/data/questions.json    mock exam bank (validated)
    plus {{CCNP_*}} tokens for src/pages/ccnp-*.html

Every fact that ends up in a page is HTML-escaped (OWASP A03). Card and question
text allow `code` and **bold** only; they are rendered by md.inline (escape first).
"""
import json
import re
import shutil
import sys

import build as B
from md import convert, inline

SRC_C = B.SRC / "ccnp"
BASE = "/ccnp-security"
esc = B.esc
WORDS_PER_MIN = 220


# ----------------------------------------------------------------------- course
def load_course():
    c = json.loads((SRC_C / "course.json").read_text(encoding="utf-8"))
    total = sum(d["weight"] for d in c["domains"])
    if total != 100:
        sys.exit(f"course.json: domain weights add up to {total}, not 100")
    objs = {}
    for d in c["domains"]:
        for o in d["objectives"]:
            if not o["id"].startswith(d["id"] + "."):
                sys.exit(f"course.json: objective {o['id']} filed under domain {d['id']}")
            objs[o["id"]] = (d, o)
    c["obj"] = objs
    seen = set()
    for lec in c["lectures"]:
        if lec["slug"] in seen or not re.fullmatch(r"[a-z0-9-]+", lec["slug"]):
            sys.exit(f"course.json: bad or duplicate lecture slug {lec['slug']!r}")
        seen.add(lec["slug"])
        for o in lec["objectives"] + lec.get("supports", []):
            if o not in objs:
                sys.exit(f"course.json: lecture {lec['slug']} lists unknown objective {o}")
        if not 50 <= len(lec["description"]) <= 170:
            sys.exit(f"course.json: {lec['slug']} description is {len(lec['description'])} chars (50-170)")
        lec["path"] = f"{BASE}/{lec['slug']}"
    c["lectures"].sort(key=lambda x: (x["order"], x["slug"]))
    return c


def covered_by(course):
    """objective id -> lecture (core objectives only)."""
    out = {}
    for lec in course["lectures"]:
        for o in lec["objectives"]:
            out.setdefault(o, lec)
    return out


# --------------------------------------------------------------------- lectures
def _copy(src, dst):
    if not dst.exists() or dst.read_bytes() != src.read_bytes():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        print(f"  copied {dst.relative_to(B.PUB)}")


def _figure_hook(item, src_root=None, pub_prefix="ccnp"):
    """Markdown block image -> <figure>. src_root: folder holding img/; pub_prefix: under /assets/img/."""
    src_root = src_root or (SRC_C / "lectures")

    def hook(src, alt):
        m = re.fullmatch(r"img/([a-z0-9-]+)/([a-z0-9-]+)\.webp", src)
        if not m:
            sys.exit(f"{item['file']}: image {src!r} must be img/<folder>/<name>.webp")
        folder, name = m.groups()
        f = src_root / "img" / folder / f"{name}.webp"
        if not f.is_file():
            sys.exit(f"{item['file']}: missing image {f.relative_to(B.ROOT)}")
        pub_dir = B.PUB / "assets" / "img" / pub_prefix / folder
        _copy(f, pub_dir / f.name)
        w, h = B.webp_size(f)
        url = f"/assets/img/{pub_prefix}/{folder}/{name}.webp"
        srcset = ""
        small = f.with_name(f"{name}-800.webp")
        if small.is_file():
            _copy(small, pub_dir / small.name)
            sw, _ = B.webp_size(small)
            srcset = (f' srcset="/assets/img/{pub_prefix}/{folder}/{small.name} {sw}w, {url} {w}w"'
                      f' sizes="(max-width: 64rem) calc(100vw - 2rem), 44rem"')
        a = esc(alt)
        return (f'<figure class="post-figure"><a href="{url}" aria-label="Open full-size image: {a}">'
                f'<img src="{url}"{srcset} width="{w}" height="{h}" alt="{a}" loading="lazy" decoding="async"></a>'
                f'<figcaption>{a}. Select the image to open it full size.</figcaption></figure>')
    return hook


def _add_ids(body):
    """ids on every h2/h3 (deep links from cards and questions); TOC from h2."""
    seen, toc = set(), []

    def repl(m):
        lvl, inner = m.group(1), m.group(2)
        # "7. Deployment model 2: ..." -> "deployment-model-2-...": anchors survive renumbering
        hid = B.slugify(re.sub(r"^\d+(\.\d+)*\.?\s+", "", B.strip_tags(inner)), seen)
        if lvl == "2":
            toc.append((hid, B.strip_tags(inner)))
        return f'<h{lvl} id="{hid}">{inner}</h{lvl}>'

    return re.sub(r"<h([23])>(.*?)</h\1>", repl, body, flags=re.S), toc, seen


def _render_md(item, folder, pub_prefix):
    md = (SRC_C / folder / item["file"]).read_text(encoding="utf-8")
    # the file's own title + intro block are replaced by the page header
    m = re.search(r"^-{3,}\s*$", md, re.M)
    if md.lstrip().startswith("# ") and m:
        md = md[m.end():]
    body, _ = convert(md, image_hook=_figure_hook(item, SRC_C / folder, pub_prefix), heading_shift=1)
    body, toc, ids = _add_ids(body)
    item["body"] = B.no_translate(body)
    item["toc"] = toc
    item["anchors"] = ids
    words = len(re.findall(r"\w+", B.strip_tags(body)))
    item["read_min"] = max(1, round(words / WORDS_PER_MIN))


def load_lectures(course):
    for lec in course["lectures"]:
        _render_md(lec, "lectures", "ccnp")


# ------------------------------------------------------------------------- labs
LAB_FILES = f"{BASE}/labs/files"
FILE_KIND = {".pkt": "PKT", ".pka": "PKA", ".zip": "ZIP", ".txt": "TXT"}


def load_labs(course):
    labs = course.get("labs", [])
    seen = set()
    for lab in labs:
        if lab["slug"] in seen or not re.fullmatch(r"[a-z0-9-]+", lab["slug"]):
            sys.exit(f"course.json: bad or duplicate lab slug {lab['slug']!r}")
        seen.add(lab["slug"])
        if not 50 <= len(lab["description"]) <= 170:
            sys.exit(f"course.json: lab {lab['slug']} description is {len(lab['description'])} chars (50-170)")
        for o in lab["objectives"]:
            if o not in course["obj"]:
                sys.exit(f"course.json: lab {lab['slug']} lists unknown objective {o}")
        lab["lec"] = next((x for x in course["lectures"] if x["slug"] == lab["lecture"]), None)
        if not lab["lec"]:
            sys.exit(f"course.json: lab {lab['slug']} points at unknown lecture {lab['lecture']!r}")
        lab["path"] = f"{BASE}/labs/{lab['slug']}"
        _render_md(lab, "labs", "ccnp/labs")
        lab["files"] = []
        for d in lab["downloads"]:
            if not re.fullmatch(r"[a-z0-9-]+\.(pkt|pka|zip|txt)", d["file"]):
                sys.exit(f"lab {lab['slug']}: download name {d['file']!r} not allowed")
            f = SRC_C / "labs" / "files" / d["file"]
            if not f.is_file():
                sys.exit(f"lab {lab['slug']}: missing download {f.relative_to(B.ROOT)}")
            raw = f.read_bytes()
            _copy(f, B.PUB / "ccnp-security" / "labs" / "files" / d["file"])
            lab["files"].append({**d, "url": f'{LAB_FILES}/{d["file"]}', "bytes": len(raw),
                                 "sha256": B.hashlib.sha256(raw).hexdigest(),
                                 "kind": FILE_KIND[f.suffix]})
    return labs


def render_lab(site, hashes, last_change, course, lab):
    toc_items = "".join(f'<li><a href="#{hid}">{esc(t)}</a></li>' for hid, t in lab["toc"])
    toc_aside = (f'<aside class="toc" aria-label="On this page"><span class="toc-title">'
                 f'<span class="h">#</span> show ip route | toc</span><ol>{toc_items}</ol></aside>')
    toc_mobile = (f'<details class="toc-mobile"><summary>show ip route | toc ({len(lab["toc"])} sections)</summary>'
                  f'<ol>{toc_items}</ol></details>\n')
    tiles, sums = [], []
    for i, f in enumerate(lab["files"]):
        tiles.append(
            f'<li><a class="dl{" dl-pri" if i == 0 else ""}" href="{f["url"]}" download>'
            f'<span class="dl-k">{f["kind"]}</span><span class="dl-t"><b>{esc(f["label"])}</b>'
            f'<span class="dl-m">{esc(f["note"])} &middot; {B.human_size(f["bytes"])}</span></span>'
            f'<svg class="dl-i" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M8 2v8m0 0L4.5 6.5M8 10l3.5-3.5M3 13h10"/></svg>'
            f'<span class="sr-only">, download</span></a></li>')
        sums.append(f'<tr><td translate="no">{esc(f["file"])}</td><td translate="no">{f["sha256"]}</td></tr>')
    objs = " ".join(obj_chip(o, course) for o in lab["objectives"])
    d0 = lab["objectives"][0].split(".")[0]
    lec = lab["lec"]
    main = f'''<main id="main">
<article class="lecture lab">
  <header class="post-head">
    <div class="wrap">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="/">~</a><span aria-hidden="true">/</span><a href="{BASE}">ccnp-security</a><span aria-hidden="true">/</span><a href="{BASE}#labs">labs</a><span aria-hidden="true">/</span><span>{esc(lab["slug"])}</span></nav>
      <p class="scard-meta"><span class="sid">Packet Tracer lab</span><span>Domain {esc(d0)} {esc(course["domains"][int(d0)-1]["name"])} &middot; topics {esc(", ".join(lab["objectives"]))}</span></p>
      <h1 class="mt-2">{esc(lab["title"])}</h1>
      <p class="post-dek">{esc(lab["dek"])}</p>
      <div class="post-meta"><time datetime="{lab["date"]}">updated {B.fmt_date(lab.get("updated", lab["date"]))}</time><span class="sep">/</span><span>{esc(lab["time"])}</span><span class="sep">/</span><span>{esc(lab["tool"])}</span><span class="sep">/</span><span>by {esc(site["author"])}</span></div>
    </div>
  </header>
  <div class="wrap post-layout">
    <div class="post-main">
      <section class="labdl" aria-labelledby="dl-h">
        <span class="cli" aria-hidden="true"><span class="h">edge#</span> <span class="v">copy</span> <span class="a">{esc(lab["slug"])} flash:</span></span>
        <h2 id="dl-h" class="sub-h">Download the lab</h2>
        <ul class="dl-list">{"".join(tiles)}</ul>
        <details class="sums">
          <summary>Verify your download (SHA-256)</summary>
          <div class="tbl"><table class="sheet-files"><thead><tr><th scope="col">File</th><th scope="col">SHA-256</th></tr></thead><tbody>{"".join(sums)}</tbody></table></div>
          <p>Compare with <code translate="no">Get-FileHash .\\file.pkt -Algorithm SHA256</code> (PowerShell) or <code translate="no">sha256sum file.pkt</code>. Different hash, different file: delete it.</p>
        </details>
        <p class="side-note">Read the <a href="{lec["path"]}">{esc(lec["title"])}</a> notes first. Topics: {objs}</p>
      </section>
{toc_mobile}<div class="prose">
{lab["body"].rstrip()}
</div>
      <footer class="post-end">
        <section class="practice" aria-labelledby="practice-h">
          <div><h2 id="practice-h" class="sub-h">Lock it in</h2>
          <p>Lab done? Drill the commands and the attack-to-defense mapping until they're automatic.</p></div>
          <p class="practice-links"><a class="btn btn-pri" href="{BASE}/flashcards#d{d0}">flashcards <span class="p">d{d0}</span></a><a class="btn btn-sec" href="{BASE}/mock-exam#d{d0}">mock exam <span class="p">d{d0}</span></a><a class="btn btn-sec" href="{lec["path"]}">notes</a></p>
        </section>
      </footer>
    </div>
    {toc_aside}
  </div>
</article>
</main>
'''
    url = site["url"] + lab["path"]
    jsonld = [{
        "@context": "https://schema.org", "@type": "LearningResource",
        "name": lab["title"], "description": lab["description"], "url": url,
        "learningResourceType": "Lab exercise", "educationalLevel": "Professional",
        "inLanguage": "en", "isAccessibleForFree": True,
        "datePublished": lab["date"], "dateModified": lab.get("updated", lab["date"]),
        "teaches": [course["obj"][o][1]["text"] for o in lab["objectives"]],
        "author": {"@type": "Person", "name": site["author"], "url": site["url"] + "/"},
        "encoding": [{"@type": "MediaObject", "name": f["label"], "contentUrl": site["url"] + f["url"],
                      "encodingFormat": "application/octet-stream", "contentSize": B.human_size(f["bytes"]),
                      "sha256": f["sha256"]} for f in lab["files"]],
    }, {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": site["url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": "CCNP Security", "item": site["url"] + BASE},
            {"@type": "ListItem", "position": 3, "name": lab["title"]},
        ],
    }]
    og = f'/assets/og/ccnp-lab-{lab["slug"]}.webp'
    return B.page(site, hashes, last_change, nav="", body=main, progress=True,
                  title=lab["seo_title"], description=lab["description"], path=lab["path"],
                  og_title=lab["title"], og_description=lab["dek"], og_type="article", jsonld=jsonld,
                  og_image=og if (B.PUB / og.lstrip("/")).exists() else None,
                  og_image_alt=f'{lab["title"]}: free Packet Tracer lab')


def block_labs(course):
    labs = course.get("labs", [])
    if not labs:
        return '<p class="hub-p">Coming next: Packet Tracer labs with downloadable baselines.</p>'
    items = []
    for lab in labs:
        chips = "".join(obj_chip(o, course) for o in lab["objectives"])
        kinds = " + ".join(f'.{f["file"].rsplit(".", 1)[1]}' for f in lab["files"])
        items.append(
            f'<li><a class="lec" href="{lab["path"]}"><span class="mod">PT</span>'
            f'<span class="lt"><b>{esc(lab["title"])}</b><span class="ld">{esc(lab["dek"])}</span>'
            f'<span class="lc">{chips}<span class="lm">{esc(lab["time"])} &middot; download {esc(kinds)}</span></span></span></a></li>')
    return '<ol class="lecs">' + "".join(items) + "</ol>"


def obj_chip(o, course, link=False):
    d, ob = course["obj"][o]
    return f'<span class="chip obj d{d["id"]}" title="{esc(ob["text"])}">{esc(o)}</span>'


def render_lecture(site, hashes, last_change, course, lec, counts):
    toc_items = "".join(f'<li><a href="#{hid}">{esc(t)}</a></li>' for hid, t in lec["toc"])
    toc_aside = (f'<aside class="toc" aria-label="On this page"><span class="toc-title">'
                 f'<span class="h">#</span> show ip route | toc</span><ol>{toc_items}</ol></aside>')
    toc_mobile = (f'<details class="toc-mobile"><summary>show ip route | toc ({len(lec["toc"])} sections)</summary>'
                  f'<ol>{toc_items}</ol></details>\n')
    objs = "".join(f'<li>{obj_chip(o, course)}<span>{esc(course["obj"][o][1]["text"])}</span></li>' for o in lec["objectives"])
    sup = " ".join(obj_chip(o, course) for o in lec.get("supports", []))
    doms = sorted({o.split(".")[0] for o in lec["objectives"]})
    d0 = doms[0]
    n_cards = sum(counts["cards"].get(o, 0) for o in lec["objectives"])
    n_qs = sum(counts["questions"].get(o, 0) for o in lec["objectives"])

    lecs = course["lectures"]
    i = lecs.index(lec)
    hop = []
    if i > 0:
        hop.append(f'<a class="prev" href="{lecs[i-1]["path"]}"><span class="k">&larr; previous lecture</span>{esc(lecs[i-1]["title"])}</a>')
    if i + 1 < len(lecs):
        hop.append(f'<a class="next" href="{lecs[i+1]["path"]}"><span class="k">next lecture &rarr;</span>{esc(lecs[i+1]["title"])}</a>')
    nexthop = f'<nav class="nexthop" aria-label="More lectures">{"".join(hop)}</nav>' if hop else ""
    lab = next((x for x in course.get("labs", []) if x["lecture"] == lec["slug"]), None)
    lab_btn = f'<a class="btn btn-pri" href="{lab["path"]}">Packet Tracer lab <span class="p">.pkt</span></a>' if lab else ""

    main = f'''<main id="main">
<article class="lecture">
  <header class="post-head">
    <div class="wrap">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="/">~</a><span aria-hidden="true">/</span><a href="{BASE}">ccnp-security</a><span aria-hidden="true">/</span><span>{esc(" + ".join(lec["objectives"]))}</span></nav>
      <p class="scard-meta"><span class="sid">SCOR {esc(course["exam"]["code"])} v{esc(course["exam"]["version"])}</span><span>Domain {esc(d0)} {esc(course["domains"][int(d0)-1]["name"])} &middot; topics {esc(", ".join(lec["objectives"]))}</span></p>
      <h1 class="mt-2">{esc(lec["title"])}</h1>
      <p class="post-dek">{esc(lec["dek"])}</p>
      <div class="post-meta"><time datetime="{lec["date"]}">updated {B.fmt_date(lec.get("updated", lec["date"]))}</time><span class="sep">/</span><span>{lec["read_min"]} min read</span><span class="sep">/</span><span>by {esc(site["author"])}</span></div>
    </div>
  </header>
  <div class="wrap post-layout">
    <div class="post-main">
      <section class="objbox" aria-labelledby="objbox-h">
        <h2 id="objbox-h" class="objbox-h">Exam topics in this module</h2>
        <ul class="objlist">{objs}</ul>
        <p class="objsup"><span>Also touches</span> {sup}</p>
      </section>
{toc_mobile}<div class="prose">
{lec["body"].rstrip()}
</div>
      <footer class="post-end">
        <section class="practice" aria-labelledby="practice-h">
          <div><h2 id="practice-h" class="sub-h">Practice this module</h2>
          <p>{n_cards} flashcards and {n_qs} mock exam questions cover {", ".join(esc(o) for o in lec["objectives"])}. Every answer links back to the section above that explains it.</p></div>
          <p class="practice-links">{lab_btn}<a class="btn btn-pri" href="{BASE}/flashcards#d{d0}">flashcards <span class="p">d{d0}</span></a><a class="btn btn-sec" href="{BASE}/mock-exam#d{d0}">mock exam <span class="p">d{d0}</span></a></p>
        </section>
        {nexthop}
      </footer>
    </div>
    {toc_aside}
  </div>
</article>
</main>
'''
    url = site["url"] + lec["path"]
    jsonld = [{
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "name": lec["title"],
        "description": lec["description"],
        "url": url,
        "learningResourceType": "Lecture notes",
        "educationalLevel": "Professional",
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "datePublished": lec["date"],
        "dateModified": lec.get("updated", lec["date"]),
        "timeRequired": f'PT{lec["read_min"]}M',
        "teaches": [course["obj"][o][1]["text"] for o in lec["objectives"]],
        "educationalAlignment": [{"@type": "AlignmentObject", "alignmentType": "assesses",
                                  "educationalFramework": f'Cisco {course["exam"]["name"]} {course["exam"]["code"]} v{course["exam"]["version"]}',
                                  "targetName": f'{o} {course["obj"][o][1]["text"]}'} for o in lec["objectives"]],
        "author": {"@type": "Person", "name": site["author"], "url": site["url"] + "/"},
    }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": site["url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": "CCNP Security", "item": site["url"] + BASE},
            {"@type": "ListItem", "position": 3, "name": lec["title"]},
        ],
    }]
    og = f'/assets/og/ccnp-{lec["slug"]}.webp'
    return B.page(site, hashes, last_change, nav="", body=main, progress=True,
                  title=lec["seo_title"], description=lec["description"], path=lec["path"],
                  og_title=lec["title"], og_description=lec["dek"], og_type="article", jsonld=jsonld,
                  og_image=og if (B.PUB / og.lstrip("/")).exists() else None,
                  og_image_alt=f'{lec["title"]}: CCNP Security SCOR 350-701 v2.0 notes')


# ----------------------------------------------------------------- practice data
def _ref(item, where, course):
    ref = item.get("ref")
    if not ref:
        sys.exit(f"{where} {item['id']}: missing ref (lecture-slug#anchor)")
    slug, _, anchor = ref.partition("#")
    lec = next((x for x in course["lectures"] if x["slug"] == slug), None)
    if not lec:
        sys.exit(f"{where} {item['id']}: ref to unknown lecture {slug!r}")
    if anchor and anchor not in lec["anchors"]:
        sys.exit(f"{where} {item['id']}: ref anchor #{anchor} not found in {slug} "
                 f"(have: {', '.join(sorted(lec['anchors']))[:400]}...)")
    return f'{lec["path"]}#{anchor}' if anchor else lec["path"]


def load_cards(course):
    cards = json.loads((SRC_C / "flashcards.json").read_text(encoding="utf-8"))["cards"]
    seen = set()
    for c in cards:
        if c["id"] in seen or not re.fullmatch(r"[a-z0-9.-]+", c["id"]):
            sys.exit(f"flashcards.json: bad or duplicate id {c['id']!r}")
        seen.add(c["id"])
        if c["obj"] not in course["obj"]:
            sys.exit(f"flashcards.json: {c['id']} has unknown objective {c['obj']}")
        c["url"] = _ref(c, "flashcards.json", course)
        c["dom"] = c["obj"].split(".")[0]
    return cards


def load_questions(course):
    qs = json.loads((SRC_C / "questions.json").read_text(encoding="utf-8"))["questions"]
    seen = set()
    for q in qs:
        qid = q["id"]
        if qid in seen or not re.fullmatch(r"[a-z0-9.-]+", qid):
            sys.exit(f"questions.json: bad or duplicate id {qid!r}")
        seen.add(qid)
        if q["obj"] not in course["obj"]:
            sys.exit(f"questions.json: {qid} has unknown objective {q['obj']}")
        if q["type"] not in ("single", "multi"):
            sys.exit(f"questions.json: {qid} type must be single or multi")
        n = len(q["options"])
        if not 3 <= n <= 6 or len(set(q["options"])) != n:
            sys.exit(f"questions.json: {qid} needs 3-6 distinct options")
        ans = q["answer"]
        if not ans or any(not isinstance(a, int) or not 0 <= a < n for a in ans) or len(set(ans)) != len(ans):
            sys.exit(f"questions.json: {qid} has an invalid answer list")
        if q["type"] == "single" and len(ans) != 1:
            sys.exit(f"questions.json: {qid} is single but has {len(ans)} answers")
        if q["type"] == "multi" and len(ans) < 2:
            sys.exit(f"questions.json: {qid} is multi but has {len(ans)} answer")
        if len(q["explanation"]) < 40:
            sys.exit(f"questions.json: {qid} explanation too short to teach anything")
        q["url"] = _ref(q, "questions.json", course)
    return qs


def exam_json(course, qs):
    data = {
        "exam": {k: course["exam"][k] for k in ("code", "name", "version", "duration_min")},
        "domains": [{"id": d["id"], "name": d["name"], "weight": d["weight"]} for d in course["domains"]],
        "questions": [{"id": q["id"], "obj": q["obj"], "type": q["type"], "stem": q["stem"],
                       "options": q["options"], "answer": q["answer"], "explanation": q["explanation"],
                       "ref": q["url"], "ref_label": q.get("ref_label", "Review this in the notes")} for q in qs],
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


# ------------------------------------------------------------------- page blocks
def block_stats(course, cards, qs):
    cov = covered_by(course)
    n_obj = len(course["obj"])
    rows = [
        ("lectures", len(course["lectures"]), "published"),
        ("objectives", f'{len(cov)}/{n_obj}', "have notes"),
        ("flashcards", len(cards), "in the deck"),
        ("questions", len(qs), "in the exam bank"),
    ]
    return "".join(f'<div class="stat"><dt>{esc(k)}</dt><dd><b>{v}</b> {esc(note)}</dd></div>' for k, v, note in rows)


def block_domains(course, cards, qs):
    cov = covered_by(course)
    out = []
    for d in course["domains"]:
        objs = d["objectives"]
        have = [o for o in objs if o["id"] in cov]
        nq = sum(1 for q in qs if q["obj"].split(".")[0] == d["id"])
        nc = sum(1 for c in cards if c["dom"] == d["id"])
        rows = []
        for o in objs:
            lec = cov.get(o["id"])
            if lec:
                state = f'<a class="st st-up" href="{lec["path"]}">notes</a>'
            else:
                state = '<span class="st st-plan">planned</span>'
            rows.append(f'<li><span class="rid">{esc(o["id"])}</span><span class="rt">{esc(o["text"])}</span>{state}</li>')
        pct = round(100 * len(have) / len(objs))
        out.append(
            f'<section class="dom d{d["id"]}" aria-labelledby="dom-{d["id"]}-h">'
            f'<h3 id="dom-{d["id"]}-h"><span class="dw">{d["weight"]}%</span><span class="dn">{d["id"]}.0 {esc(d["name"])}</span>'
            f'<span class="ct">{len(have)}/{len(objs)} topics &middot; {nc} cards &middot; {nq} questions</span></h3>'
            f'<div class="meter" role="img" aria-label="{pct} percent of domain {d["id"]} topics have notes"><span class="w{pct // 5 * 5}"></span></div>'
            f'<details><summary>{len(objs)} exam topics</summary><ol class="rack-list">{"".join(rows)}</ol></details>'
            f'</section>')
    return "\n      ".join(out)


def block_lectures(course):
    items = []
    for lec in course["lectures"]:
        chips = "".join(obj_chip(o, course) for o in lec["objectives"])
        items.append(
            f'<li><a class="lec" href="{lec["path"]}"><span class="mod">D{esc(lec["objectives"][0].split(".")[0])}</span>'
            f'<span class="lt"><b>{esc(lec["title"])}</b><span class="ld">{esc(lec["dek"])}</span>'
            f'<span class="lc">{chips}<span class="lm">{lec["read_min"]} min &middot; {B.fmt_date(lec.get("updated", lec["date"]))}</span></span></span></a></li>')
    return '<ol class="lecs">' + "".join(items) + "</ol>"


def block_card_filters(course, cards):
    btns = [f'<button type="button" class="fbtn" data-filter="all" aria-pressed="true">all <span class="ct">{len(cards)}</span></button>']
    for d in course["domains"]:
        n = sum(1 for c in cards if c["dom"] == d["id"])
        dis = " disabled" if not n else ""
        btns.append(f'<button type="button" class="fbtn" data-filter="d{d["id"]}" aria-pressed="false"{dis}>'
                    f'd{d["id"]} <span class="ct">{n}</span></button>')
    return "\n          ".join(btns)


def block_card_list(course, cards):
    items = []
    for c in cards:
        items.append(
            f'<li class="fc-item" data-id="{esc(c["id"])}" data-dom="d{c["dom"]}" data-obj="{esc(c["obj"])}">'
            f'<details><summary><span class="chip obj d{c["dom"]}">{esc(c["obj"])}</span> '
            f'<span class="fc-front">{inline(c["front"])}</span></summary>'
            f'<div class="fc-back"><p>{inline(c["back"])}</p>'
            f'<a class="fc-ref" href="{esc(c["url"])}">review in the notes &rarr;</a></div></details></li>')
    return '<ol class="fc-list">' + "".join(items) + "</ol>"


def block_sample_questions(course, qs):
    """Crawlable sample questions (answers behind <details>) so search engines see real content."""
    items = []
    for q in [x for x in qs if x.get("sample")]:
        opts = "".join(f"<li>{inline(o)}</li>" for o in q["options"])
        letters = ", ".join(chr(65 + a) for a in sorted(q["answer"]))
        hint = "Choose one." if q["type"] == "single" else f"Choose {len(q['answer'])}."
        items.append(
            f'<li class="sq"><p class="sq-stem">{inline(q["stem"])} <span class="mut">{hint}</span></p>'
            f'<ol class="sq-opts">{opts}</ol>'
            f'<details class="qa"><summary>Show answer</summary><p><strong>Answer: {letters}.</strong> {inline(q["explanation"])} '
            f'<a href="{esc(q["url"])}">Review topic {esc(q["obj"])} in the notes &rarr;</a></p></details></li>')
    return '<ol class="sqs">' + "".join(items) + "</ol>"


def block_exam_domains(course, qs):
    rows = []
    for d in course["domains"]:
        n = sum(1 for q in qs if q["obj"].split(".")[0] == d["id"])
        dis = "" if n else " disabled"
        chk = " checked" if n else ""
        rows.append(f'<label class="opt"><input type="checkbox" name="dom" value="{d["id"]}" id="d{d["id"]}"{chk}{dis}>'
                    f'<span><b>{d["id"]}.0 {esc(d["name"])}</b> <span class="mut">{d["weight"]}% of the exam &middot; {n} question{"s" if n != 1 else ""} in the bank</span></span></label>')
    return "\n          ".join(rows)


# ------------------------------------------------------------------------- main
def build(site, hashes, last_change):
    course = load_course()
    load_lectures(course)
    labs = load_labs(course)
    cards = load_cards(course)
    qs = load_questions(course)
    counts = {"cards": {}, "questions": {}}
    for c in cards:
        counts["cards"][c["obj"]] = counts["cards"].get(c["obj"], 0) + 1
    for q in qs:
        counts["questions"][q["obj"]] = counts["questions"].get(q["obj"], 0) + 1

    for lec in course["lectures"]:
        B.write(f'ccnp-security/{lec["slug"]}.html', render_lecture(site, hashes, last_change, course, lec, counts))
    for lab in labs:
        B.write(f'ccnp-security/labs/{lab["slug"]}.html', render_lab(site, hashes, last_change, course, lab))
    B.write("ccnp-security/data/questions.json", exam_json(course, qs) + "\n")

    newest = max(lec.get("updated", lec["date"]) for lec in course["lectures"])
    tokens = {
        "CCNP_STATS": block_stats(course, cards, qs),
        "CCNP_DOMAINS": block_domains(course, cards, qs),
        "CCNP_LECTURES": block_lectures(course),
        "CCNP_LABS": block_labs(course),
        "CCNP_CARD_FILTERS": block_card_filters(course, cards),
        "CCNP_CARD_LIST": block_card_list(course, cards),
        "CCNP_CARD_COUNT": str(len(cards)),
        "CCNP_EXAM_DOMAINS": block_exam_domains(course, qs),
        "CCNP_Q_COUNT": str(len(qs)),
        "CCNP_SAMPLE_QS": block_sample_questions(course, qs),
        "CCNP_SAMPLE_COUNT": str(sum(1 for q in qs if q.get("sample"))),
        "CCNP_EXAM": f'{esc(course["exam"]["name"])} {esc(course["exam"]["code"])} v{esc(course["exam"]["version"])}',
        "CCNP_UPDATED": B.fmt_date(newest),
    }
    pages = [(BASE, newest), (f"{BASE}/flashcards", newest), (f"{BASE}/mock-exam", newest),
             (f"{BASE}/scor-350-701-v2-changes", "2026-10-27")]
    pages += [(lec["path"], lec.get("updated", lec["date"])) for lec in course["lectures"]]
    pages += [(lab["path"], lab.get("updated", lab["date"])) for lab in labs]
    print(f"  ccnp: {len(course['lectures'])} lectures, {len(labs)} labs, {len(cards)} cards, {len(qs)} questions")
    return tokens, pages
