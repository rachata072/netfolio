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


def _figure_hook(lec):
    def hook(src, alt):
        m = re.fullmatch(r"img/([a-z0-9-]+)/([a-z0-9-]+)\.webp", src)
        if not m:
            sys.exit(f"{lec['file']}: image {src!r} must be img/<module>/<name>.webp")
        folder, name = m.groups()
        f = SRC_C / "lectures" / "img" / folder / f"{name}.webp"
        if not f.is_file():
            sys.exit(f"{lec['file']}: missing image {f.relative_to(B.ROOT)}")
        pub_dir = B.PUB / "assets" / "img" / "ccnp" / folder
        _copy(f, pub_dir / f.name)
        w, h = B.webp_size(f)
        url = f"/assets/img/ccnp/{folder}/{name}.webp"
        srcset = ""
        small = f.with_name(f"{name}-800.webp")
        if small.is_file():
            _copy(small, pub_dir / small.name)
            sw, _ = B.webp_size(small)
            srcset = (f' srcset="/assets/img/ccnp/{folder}/{small.name} {sw}w, {url} {w}w"'
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


def load_lectures(course):
    for lec in course["lectures"]:
        md = (SRC_C / "lectures" / lec["file"]).read_text(encoding="utf-8")
        # the file's own title + objective block are replaced by the page header
        m = re.search(r"^-{3,}\s*$", md, re.M)
        if md.lstrip().startswith("# ") and m:
            md = md[m.end():]
        body, _ = convert(md, image_hook=_figure_hook(lec), heading_shift=1)
        body, toc, ids = _add_ids(body)
        lec["body"] = B.no_translate(body)
        lec["toc"] = toc
        lec["anchors"] = ids
        words = len(re.findall(r"\w+", B.strip_tags(body)))
        lec["read_min"] = max(1, round(words / WORDS_PER_MIN))


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

    main = f'''<main id="main">
<article class="lecture">
  <header class="post-head">
    <div class="wrap">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="/">~</a><span aria-hidden="true">/</span><a href="{BASE}">ccnp-security</a><span aria-hidden="true">/</span><span>module {esc(lec["module"])}</span></nav>
      <p class="scard-meta"><span class="sid">SCOR {esc(course["exam"]["code"])} v{esc(course["exam"]["version"])}</span><span>Module {esc(lec["module"])} &middot; Domain {esc(d0)} {esc(course["domains"][int(d0)-1]["name"])}</span></p>
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
          <p class="practice-links"><a class="btn btn-pri" href="{BASE}/flashcards#d{d0}">flashcards <span class="p">d{d0}</span></a><a class="btn btn-sec" href="{BASE}/mock-exam#d{d0}">mock exam <span class="p">d{d0}</span></a></p>
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
    return B.page(site, hashes, last_change, nav="", body=main, progress=True,
                  title=lec["seo_title"], description=lec["description"], path=lec["path"],
                  og_title=lec["title"], og_description=lec["dek"], og_type="article", jsonld=jsonld)


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
            f'<li><a class="lec" href="{lec["path"]}"><span class="mod">{esc(lec["module"])}</span>'
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
    cards = load_cards(course)
    qs = load_questions(course)
    counts = {"cards": {}, "questions": {}}
    for c in cards:
        counts["cards"][c["obj"]] = counts["cards"].get(c["obj"], 0) + 1
    for q in qs:
        counts["questions"][q["obj"]] = counts["questions"].get(q["obj"], 0) + 1

    for lec in course["lectures"]:
        B.write(f'ccnp-security/{lec["slug"]}.html', render_lecture(site, hashes, last_change, course, lec, counts))
    B.write("ccnp-security/data/questions.json", exam_json(course, qs) + "\n")

    newest = max(lec.get("updated", lec["date"]) for lec in course["lectures"])
    tokens = {
        "CCNP_STATS": block_stats(course, cards, qs),
        "CCNP_DOMAINS": block_domains(course, cards, qs),
        "CCNP_LECTURES": block_lectures(course),
        "CCNP_CARD_FILTERS": block_card_filters(course, cards),
        "CCNP_CARD_LIST": block_card_list(course, cards),
        "CCNP_CARD_COUNT": str(len(cards)),
        "CCNP_EXAM_DOMAINS": block_exam_domains(course, qs),
        "CCNP_Q_COUNT": str(len(qs)),
        "CCNP_EXAM": f'{esc(course["exam"]["name"])} {esc(course["exam"]["code"])} v{esc(course["exam"]["version"])}',
        "CCNP_UPDATED": B.fmt_date(newest),
    }
    pages = [(BASE, newest), (f"{BASE}/flashcards", newest), (f"{BASE}/mock-exam", newest)]
    pages += [(lec["path"], lec.get("updated", lec["date"])) for lec in course["lectures"]]
    print(f"  ccnp: {len(course['lectures'])} lectures, {len(cards)} cards, {len(qs)} questions")
    return tokens, pages
