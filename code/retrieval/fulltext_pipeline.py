#!/usr/bin/env python
# =============================================================================
#  Full-text stage of the systematic review
#  "Knowing When the Model Doesn't Know: uncertainty-aware and trustworthy LLMs in education"
#
#  Stages (env STAGES, default "resolve,fetch,extract,snowball"):
#    resolve  : find each record in OpenAlex (by OpenAlex id, DOI or title) and collect
#               every open-access PDF link (OpenAlex, arXiv, Unpaywall, Semantic Scholar,
#               Europe PMC, the citation_pdf_url tag of the landing page)
#    fetch    : download the PDFs (only real PDFs are kept); PDFs you add yourself as a
#               Kaggle dataset, named <rec_id>.pdf (e.g. R00031.pdf), are used first
#    extract  : PDF -> text, reference list removed, plus a compact "evidence file" per
#               paper (method / results / limitations passages and keyword windows) that
#               is used for data extraction
#    snowball : backward (references) and forward (citing papers) citation searching for
#               the clear includes, filtered to 2020+ and LLM + education terms, minus the
#               records already screened
#
#  Env: STAGES, OPENALEX_KEY (Kaggle secret, optional), EMAIL (needed only for Unpaywall),
#       FAST=1 (first 25 records), DATA_DIR, OUT_DIR, WORKERS (default 6)
#  Output: /kaggle/working/fulltext_<date>.zip
# =============================================================================
import os, re, sys, json, time, glob, zipfile, shutil, unicodedata, threading
from datetime import datetime
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

T0 = time.time()
ON_KAGGLE = os.path.isdir("/kaggle/working")
OUT = os.environ.get("OUT_DIR", "/kaggle/working/fulltext" if ON_KAGGLE else os.path.abspath("./fulltext_out"))
DATA_DIR = os.environ.get("DATA_DIR", "/kaggle/input" if ON_KAGGLE else os.path.abspath("./data"))
STAGES = [s.strip() for s in os.environ.get("STAGES", "resolve,fetch,extract,snowball").split(",") if s.strip()]
FAST = os.environ.get("FAST", "0") not in ("0", "", "false")
KEY = os.environ.get("OPENALEX_KEY", "").strip()
EMAIL = os.environ.get("EMAIL", "").strip()
WORKERS = int(os.environ.get("WORKERS", "6"))
TODAY = datetime.now().strftime("%Y-%m-%d")
PDF_DIR, TXT_DIR, EVI_DIR = (os.path.join(OUT, d) for d in ("pdf", "text", "evidence"))
for d in (OUT, PDF_DIR, TXT_DIR, EVI_DIR):
    os.makedirs(d, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36 systematic-review-bot" + (" mailto:" + EMAIL if EMAIL else "")}
_lock = threading.Lock()


def log(*a):
    line = "[%6.1f min] %s" % ((time.time() - T0) / 60, " ".join(str(x) for x in a))
    print(line, flush=True)
    with _lock, open(os.path.join(OUT, "run.log"), "a") as f:
        f.write(line + "\n")


def find_file(name):
    hits = sorted(glob.glob(os.path.join(DATA_DIR, "**", name), recursive=True))
    if not hits and os.path.exists(name):
        hits = [name]
    return hits[0] if hits else None


def norm_text(s):
    s = unicodedata.normalize("NFKD", str(s or "")).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def norm_doi(d):
    d = str(d or "").strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d if d.startswith("10.") else ""


# ----------------------------------------------------------------------------- HTTP
def get(url, params=None, headers=None, tries=4, timeout=45, stream=False, quiet=False):
    import requests
    h = dict(UA, **(headers or {}))
    for k in range(tries):
        try:
            r = requests.get(url, params=params, headers=h, timeout=timeout, stream=stream, allow_redirects=True)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 500, 502, 503, 504) and k < tries - 1:
                time.sleep(2 if "semanticscholar" in url else 4 * (k + 1))
                continue
            if not quiet:
                log("   HTTP %d %s" % (r.status_code, url[:110]))
            return r
        except Exception as e:
            if k == tries - 1 and not quiet:
                log("   request failed (%s) %s" % (str(e)[:80], url[:100]))
            time.sleep(3 * (k + 1))
    return None


def oa_get(path, params=None):
    params = dict(params or {})
    if EMAIL:
        params["mailto"] = EMAIL
    hdr = {"Authorization": "Bearer " + KEY} if KEY else {}
    r = get("https://api.openalex.org/" + path, params, hdr, quiet=True)
    if r is None or r.status_code != 200:
        if r is not None and r.status_code == 429:
            log("!! OpenAlex quota/rate limit (429). Add the Kaggle secret OPENALEX_KEY or wait until 00:00 UTC.")
        return None
    try:
        return r.json()
    except Exception:
        return None


def inv_abstract(inv):
    if not inv:
        return ""
    pos = [(i, w) for w, idx in inv.items() for i in idx]
    return " ".join(w for _, w in sorted(pos))


# ----------------------------------------------------------------------------- stage: resolve
SEL = ("id,doi,display_name,publication_year,type,open_access,best_oa_location,primary_location,locations,"
       "ids,referenced_works,cited_by_count,authorships")


def resolve_one(r):
    w = None
    m = re.search(r"openalex\.org/(W\d+)", str(r.url or ""))
    if m:
        w = oa_get("works/" + m.group(1), {"select": SEL})
    doi = norm_doi(r.doi)
    if w is None and doi:
        w = oa_get("works/doi:" + doi, {"select": SEL})
    if w is None and r.title:
        js = oa_get("works", {"search": str(r.title)[:250], "per_page": 3, "select": SEL})
        for c in (js or {}).get("results", []):
            if SequenceMatcher(None, norm_text(c.get("display_name")), norm_text(r.title)).ratio() >= 0.92:
                w = c
                break
    links, arxiv_id, pmcid = [], "", ""
    oa_status = ""
    wid = ""
    if w:
        wid = w["id"].rsplit("/", 1)[-1]
        oa_status = (w.get("open_access") or {}).get("oa_status", "")
        doi = doi or norm_doi(w.get("doi"))
        for loc in [w.get("best_oa_location")] + list(w.get("locations") or []):
            if not loc:
                continue
            if loc.get("pdf_url"):
                links.append(("openalex", loc["pdf_url"]))
            lp = loc.get("landing_page_url") or ""
            mm = re.search(r"arxiv\.org/abs/([\w.\-/]+?)(v\d+)?$", lp)
            if mm:
                arxiv_id = mm.group(1)
            if loc.get("is_oa") and lp:
                links.append(("landing", lp))
        pmcid = str((w.get("ids") or {}).get("pmcid") or "").rsplit("/", 1)[-1]
        oa_url = (w.get("open_access") or {}).get("oa_url")
        if oa_url:
            links.append(("landing" if not oa_url.lower().endswith(".pdf") else "openalex", oa_url))
    if "arxiv" in str(r.sources).lower() or "arxiv.org" in str(r.url):
        mm = re.search(r"arxiv\.org/(abs|pdf)/([\w.\-/]+?)(v\d+)?(\.pdf)?$", str(r.url))
        arxiv_id = arxiv_id or (mm.group(2) if mm else "")
    if not arxiv_id and doi.startswith("10.48550/arxiv."):
        arxiv_id = doi.split("arxiv.", 1)[1]
    if arxiv_id:
        links.insert(0, ("arxiv", "https://arxiv.org/pdf/" + arxiv_id))
    if pmcid:
        links.append(("europepmc", "https://europepmc.org/articles/%s?pdf=render" % pmcid))
    if doi and EMAIL:
        js = get("https://api.unpaywall.org/v2/" + doi, {"email": EMAIL}, quiet=True)
        try:
            js = js.json() if js is not None and js.status_code == 200 else {}
        except Exception:
            js = {}
        for loc in [js.get("best_oa_location")] + list(js.get("oa_locations") or []):
            if loc and loc.get("url_for_pdf"):
                links.append(("unpaywall", loc["url_for_pdf"]))
            elif loc and loc.get("url_for_landing_page"):
                links.append(("landing", loc["url_for_landing_page"]))
        oa_status = oa_status or js.get("oa_status", "")
    seen, uniq = set(), []
    for s, u in links:
        if u and u not in seen:
            seen.add(u)
            uniq.append((s, u))
    return dict(rec_id=r.rec_id, openalex_id=wid, doi=doi, oa_status=oa_status, arxiv_id=arxiv_id,
                n_links=len(uniq), links=json.dumps(uniq),
                referenced_works=json.dumps([x.rsplit("/", 1)[-1] for x in (w or {}).get("referenced_works") or []]),
                cited_by_count=(w or {}).get("cited_by_count"))


def semantic_scholar(doi, title):
    """Open-access PDF from Semantic Scholar (1 request/s without a key)."""
    q = ("DOI:" + doi) if doi else None
    if q:
        r = get("https://api.semanticscholar.org/graph/v1/paper/" + q, {"fields": "openAccessPdf,externalIds"}, quiet=True, tries=2, timeout=20)
    else:
        r = get("https://api.semanticscholar.org/graph/v1/paper/search/match",
                {"query": title[:250], "fields": "openAccessPdf,externalIds"}, quiet=True, tries=2, timeout=20)
    time.sleep(1.1)
    try:
        js = r.json() if r is not None and r.status_code == 200 else {}
    except Exception:
        return []
    if "data" in js:
        js = (js.get("data") or [{}])[0]
    out = []
    pdf = (js.get("openAccessPdf") or {}).get("url")
    if pdf:
        out.append(("semanticscholar", pdf))
    ax = (js.get("externalIds") or {}).get("ArXiv")
    if ax:
        out.append(("arxiv", "https://arxiv.org/pdf/" + ax))
    return out


def stage_resolve(df):
    log("resolve: %d records, OpenAlex %s, Unpaywall %s" % (len(df), "key loaded" if KEY else "no key",
                                                            "on" if EMAIL else "off (set EMAIL to enable)"))
    rows = []
    with ThreadPoolExecutor(max_workers=min(WORKERS, 4)) as ex:
        futs = {ex.submit(resolve_one, r): r.rec_id for r in df.itertuples()}
        for k, f in enumerate(as_completed(futs), 1):
            try:
                rows.append(f.result())
            except Exception as e:
                rows.append(dict(rec_id=futs[f], links="[]", n_links=0, error=str(e)[:200]))
            if k % 50 == 0:
                log("   resolved %d/%d" % (k, len(df)))
    res = pd.DataFrame(rows).set_index("rec_id").reindex(df.rec_id).reset_index()
    # Semantic Scholar for records without any direct PDF link (sequential: rate limited)
    need = [i for i, r in res.iterrows() if not any(s in ("openalex", "arxiv", "unpaywall", "europepmc")
                                                    for s, _ in json.loads(r.links or "[]"))]
    log("resolve: Semantic Scholar lookup for %d records without a direct PDF link" % len(need))
    tmap = dict(zip(df.rec_id, df.title))
    if os.environ.get("SKIP_S2", "0") not in ("0", ""):
        need = []
        log("resolve: Semantic Scholar skipped (SKIP_S2=1)")
    t_s2 = time.time()
    for k, i in enumerate(need, 1):
        if k % 20 == 0:
            log("   Semantic Scholar %d/%d" % (k, len(need)))
        if time.time() - t_s2 > 15 * 60:
            log("!! Semantic Scholar lookup stopped after 15 min (%d/%d done); continuing without it" % (k, len(need)))
            break
        extra = semantic_scholar(res.at[i, "doi"] if isinstance(res.at[i, "doi"], str) else "", str(tmap[res.at[i, "rec_id"]]))
        if extra:
            L = json.loads(res.at[i, "links"] or "[]")
            L = extra + [x for x in L if x[1] not in {e[1] for e in extra}]
            res.at[i, "links"], res.at[i, "n_links"] = json.dumps(L), len(L)
    res.to_csv(os.path.join(OUT, "resolve.csv"), index=False)
    log("resolve: found in OpenAlex %d/%d; with at least one candidate link %d" %
        ((res.openalex_id.fillna("") != "").sum(), len(res), (res.n_links > 0).sum()))
    return res


# ----------------------------------------------------------------------------- stage: fetch
def is_pdf(b):
    return b[:1024].lstrip().startswith(b"%PDF")


def download_pdf(url, dest, max_mb=60):
    r = get(url, timeout=60, stream=True, quiet=True, tries=2)
    if r is None or r.status_code != 200:
        return "http %s" % (None if r is None else r.status_code), None
    buf = b""
    for chunk in r.iter_content(65536):
        buf += chunk
        if len(buf) > max_mb * 1e6:
            return "too large", None
        if len(buf) >= 2048 and not is_pdf(buf) and b"<html" in buf[:2048].lower():
            break
    if is_pdf(buf):
        with open(dest, "wb") as f:
            f.write(buf)
        return "ok", None
    html = buf.decode("utf-8", "ignore")
    m = re.search(r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)', html, re.I) or \
        re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url', html, re.I)
    return "html", (m.group(1) if m else None)


def fetch_one(rec_id, links):
    dest = os.path.join(PDF_DIR, rec_id + ".pdf")
    manual = find_file(rec_id + ".pdf")
    if manual and os.path.abspath(manual) != os.path.abspath(dest):
        shutil.copy(manual, dest)
        return dict(rec_id=rec_id, got="manual", via="your PDF", url=manual, tried=0, note="")
    if os.path.exists(dest) and os.path.getsize(dest) > 2000:
        return dict(rec_id=rec_id, got="cached", via="", url="", tried=0, note="")
    notes, tried = [], 0
    order = {"arxiv": 0, "openalex": 1, "unpaywall": 2, "europepmc": 3, "semanticscholar": 4, "landing": 5}
    queue = sorted(links, key=lambda x: order.get(x[0], 9))
    seen = set()
    while queue and tried < 8:
        src, url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        tried += 1
        status, pdf_link = download_pdf(url, dest)
        if status == "ok":
            return dict(rec_id=rec_id, got="downloaded", via=src, url=url, tried=tried, note="")
        if pdf_link:
            pdf_link = requests_join(url, pdf_link)
            queue.insert(0, ("citation_pdf_url", pdf_link))
        notes.append("%s:%s" % (src, status))
    return dict(rec_id=rec_id, got="no", via="", url="", tried=tried, note="; ".join(notes)[:300])


def requests_join(base, link):
    from urllib.parse import urljoin
    return urljoin(base, link)


def stage_fetch(df, res):
    links = {r.rec_id: [tuple(x) for x in json.loads(r.links or "[]")] for r in res.itertuples()}
    n_manual = len(glob.glob(os.path.join(DATA_DIR, "**", "R[0-9][0-9][0-9][0-9][0-9].pdf"), recursive=True))
    log("fetch: %d records (%d PDFs supplied by you were found in the input data)" % (len(df), n_manual))
    rows = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch_one, rid, links.get(rid, [])): rid for rid in df.rec_id}
        for k, f in enumerate(as_completed(futs), 1):
            try:
                rows.append(f.result())
            except Exception as e:
                rows.append(dict(rec_id=futs[f], got="no", note="error " + str(e)[:150]))
            if k % 50 == 0:
                log("   fetched %d/%d" % (k, len(df)))
    fx = pd.DataFrame(rows).set_index("rec_id").reindex(df.rec_id).reset_index()
    fx.to_csv(os.path.join(OUT, "fetch_log.csv"), index=False)
    ok = fx.got.isin(["downloaded", "manual", "cached"])
    log("fetch: PDFs available for %d/%d records (%d downloaded, %d supplied by you)" %
        (ok.sum(), len(fx), (fx.got == "downloaded").sum(), (fx.got == "manual").sum()))
    return fx


# ----------------------------------------------------------------------------- stage: extract
def pdf_text(path):
    try:
        import fitz
        doc = fitz.open(path)
        pages = [p.get_text("text") for p in doc]
        return "\n".join(pages), len(pages), "pymupdf"
    except ImportError:
        pass
    except Exception as e:
        return "", 0, "error: %s" % str(e)[:80]
    try:
        from pypdf import PdfReader
        rd = PdfReader(path)
        pages = [(p.extract_text() or "") for p in rd.pages]
        return "\n".join(pages), len(pages), "pypdf"
    except Exception as e:
        return "", 0, "error: %s" % str(e)[:80]


def clean_text(t):
    t = t.replace("\r", "\n").replace("­", "")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)               # de-hyphenate line breaks
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def strip_references(t):
    ms = list(re.finditer(r"\n\s*(\d+\.?\s*)?(references|bibliography|literature cited|reference list)\s*\n", t, re.I))
    if ms and ms[-1].start() > 0.4 * len(t):
        return t[:ms[-1].start()], t[ms[-1].start():]
    return t, ""


HEAD = r"\n\s*(?:[IVX]+\.|\d+(?:\.\d+)*\.?|[A-H]\.)?\s*%s[^\n]{0,60}\n"
SECTIONS = [("METHOD", r"(?:methods?|methodology|materials and methods|approach|proposed (?:method|framework|approach|system)|"
                       r"study design|experimental setup|experiments?|research design|system design)"),
            ("DATA", r"(?:data(?:set|sets)?|participants|sample|corpus|data collection)"),
            ("RESULTS", r"(?:results?|findings|evaluation|results and discussion)"),
            ("LIMITS", r"(?:limitations?|threats to validity|discussion)"),
            ("CONCL", r"(?:conclusions?|concluding remarks|summary and conclusion)")]
CAPS = {"METHOD": 2600, "DATA": 1200, "RESULTS": 2000, "LIMITS": 1100, "CONCL": 800}
KEYWORDS = [
    # uncertainty methods (RQ2)
    r"conformal", r"calibrat\w*", r"expected calibration error|\bECE\b", r"brier", r"\bAUROC\b|\bAUC\b|AUPRC",
    r"selective (?:prediction|classification|grading)|risk.coverage|coverage", r"abstain\w*|abstention|refus\w+ to answer",
    r"defer\w*|escalat\w+|rout(?:e|ing) to (?:a )?human|human review|teacher review|flag\w* for review",
    r"threshold", r"semantic entropy|entropy", r"self.consisten\w+|multiple samples|sampl\w+ \d+ times|majority vot\w+",
    r"log.?prob\w*|token probabilit\w+|logits?", r"verbali[sz]ed confidence|self.reported confidence|confidence (?:score|rating|level)s?",
    r"ensemble|multi.?agent|inter.?model|disagreement|consensus", r"human.in.the.loop|teacher.in.the.loop|instructor.in.the.loop",
    r"hallucinat\w+", r"retriev\w+.augment\w+|\bRAG\b|ground\w+", r"verif\w+|fact.check\w*",
    # evaluation (RQ4)
    r"kappa|\bQWK\b|quadratic weighted|\bICC\b|intraclass|krippendorff|pearson|spearman|agreement",
    r"accuracy|F1|precision|recall|mean absolute error|\bMAE\b|\bRMSE\b",
    r"trust|reliance|over.?relian\w+|under.?relian\w+|workload|NASA.TLX|usability|SUS\b",
    r"learning gain|pre.?test|post.?test|learning outcome|effect size|cohen'?s d",
    r"\bN\s*=\s*\d+|\d+\s+(?:students|participants|learners|teachers|essays|responses|answers|questions|items)",
    # model (coding)
    r"GPT.?4\w*|GPT.?3\.5|ChatGPT|GPT.?5|o1\b|o3\b|Llama\s?\d?|Mistral|Mixtral|Qwen\w*|Gemini|Claude|DeepSeek\w*|Phi.?\d|Gemma|BERT|RoBERTa|DeBERTa|T5",
    r"fine.?tun\w+|LoRA|QLoRA|few.?shot|zero.?shot|chain.of.thought|prompt\w*",
    # fairness, availability (RQ5)
    r"fairness|subgroup|gender|demographic|bias(?:es)?|equit\w+|non.?native|English language learner",
    r"github\.com|code (?:is )?available|data (?:is |are )?available|open.?source|osf\.io|zenodo"]


def evidence(rec, body):
    parts = ["TITLE: %s" % rec.title, "YEAR/VENUE: %s | %s | %s" % (rec.year, rec.venue, rec.type),
             "ABSTRACT: %s" % str(rec.abstract or "")[:1800]]
    taken = []
    for name, pat in SECTIONS:
        m = re.search(HEAD % pat, body, re.I)
        if m and m.end() > 0.05 * len(body):
            seg = body[m.end(): m.end() + CAPS[name]]
            taken.append((m.end(), m.end() + CAPS[name]))
            parts.append("[%s] %s" % (name, re.sub(r"\s+", " ", seg)))
    # keyword windows, merged, skipping text already taken
    spans = []
    for pat in KEYWORDS:
        for m in re.finditer(pat, body, re.I):
            spans.append((max(0, m.start() - 220), min(len(body), m.end() + 220)))
            if len(spans) > 4000:
                break
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    def overlap(s, e):
        return any(s < b and e > a for a, b in taken)
    # rank windows by number of distinct keyword families they contain
    scored = []
    for s, e in merged:
        if overlap(s, e):
            continue
        seg = body[s:e]
        score = sum(1 for p in KEYWORDS if re.search(p, seg, re.I))
        scored.append((score, s, seg))
    scored.sort(key=lambda x: (-x[0], x[1]))
    budget, kw = 5200, []
    for score, s, seg in scored:
        if budget <= 0:
            break
        seg = re.sub(r"\s+", " ", seg)[:budget]
        kw.append((s, seg))
        budget -= len(seg)
    for s, seg in sorted(kw):
        parts.append("[KW] ..." + seg + "...")
    return "\n".join(parts)


def stage_extract(df, fx):
    rows = []
    have = set(fx.rec_id[fx.got.isin(["downloaded", "manual", "cached"])]) if fx is not None else \
        {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(PDF_DIR, "*.pdf"))}
    recs = {r.rec_id: r for r in df.itertuples()}
    ev_all = []
    for rid in df.rec_id:
        rec = recs[rid]
        path = os.path.join(PDF_DIR, rid + ".pdf")
        if rid in have and os.path.exists(path):
            raw, npages, eng = pdf_text(path)
            txt = clean_text(raw)
            body, refs = strip_references(txt)
            ok = len(body) > 3000
            with open(os.path.join(TXT_DIR, rid + ".txt"), "w") as f:
                f.write(body)
            ev = evidence(rec, body) if ok else evidence(rec, "")
            # a PDF whose first page does not contain words of the title may be the wrong paper
            tw = [w for w in norm_text(rec.title).split() if len(w) > 4][:8]
            first = norm_text(body[:4000])
            match = sum(w in first for w in tw) / max(1, len(tw))
            rows.append(dict(rec_id=rid, fulltext=ok, pages=npages, chars=len(body), engine=eng,
                             title_match=round(match, 2), ref_chars=len(refs)))
        else:
            ev = evidence(rec, "")
            rows.append(dict(rec_id=rid, fulltext=False, pages=0, chars=0, engine="", title_match=None, ref_chars=0))
        status = "FULL TEXT" if rows[-1]["fulltext"] else "ABSTRACT ONLY"
        ev = "### %s | %s | screen=%s\n%s" % (rid, status, rec.screen, ev)
        with open(os.path.join(EVI_DIR, rid + ".txt"), "w") as f:
            f.write(ev)
        ev_all.append(ev)
    ex = pd.DataFrame(rows)
    ex.to_csv(os.path.join(OUT, "extract_log.csv"), index=False)
    with open(os.path.join(OUT, "evidence_all.txt"), "w") as f:
        f.write("\n\n".join(ev_all))
    bad = ex[(ex.fulltext) & (ex.title_match.fillna(1) < 0.5)]
    log("extract: full text for %d/%d; %d PDFs may be the wrong paper (title words missing on page 1, see extract_log.csv)"
        % (ex.fulltext.sum(), len(ex), len(bad)))
    return ex


# ----------------------------------------------------------------------------- stage: snowball
A = ["large language model", "large language models", "llm", "llms", "generative ai", "generative artificial intelligence",
     "gpt", "gpt 3", "gpt 4", "gpt 4o", "chatgpt", "pretrained language model", "pre trained language model",
     "language model", "language models", "bert", "transformer"]
C = ["education", "educational", "student", "students", "learner", "learners", "teacher", "teachers", "tutor",
     "tutoring", "automated scoring", "grading", "feedback", "assessment", "classroom", "mooc", "learning analytics",
     "essay", "exam", "course", "school", "university"]
NOT = ["knowledge distillation", "teacher student"]
B_WEAK = ["uncertainty", "uncertain", "confidence", "calibration", "calibrated", "reliability", "reliable", "trust",
          "trustworthy", "hallucination", "hallucinations", "validity", "agreement", "human in the loop", "verification",
          "abstain", "abstention", "deferral", "overreliance", "over reliance", "reliance", "accuracy", "error", "errors",
          "human raters", "kappa", "consistency"]


def has_any(text, terms):
    t = " " + norm_text(text) + " "
    return any(" " + x + " " in t for x in terms)


def oa_batch(ids, extra_filter=None):
    out = []
    sel = "id,doi,display_name,publication_year,type,primary_location,abstract_inverted_index,language,cited_by_count"
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        js = oa_get("works", {"filter": "openalex_id:" + "|".join(chunk), "per_page": 50, "select": sel})
        out += (js or {}).get("results", [])
        time.sleep(0.12)
    return out


def oa_citing(wid, cap=400):
    sel = "id,doi,display_name,publication_year,type,primary_location,abstract_inverted_index,language,cited_by_count"
    out, page = [], 1
    while len(out) < cap:
        js = oa_get("works", {"filter": "cites:%s,publication_year:2020-%d" % (wid, datetime.now().year),
                              "per_page": 100, "page": page, "select": sel})
        res = (js or {}).get("results", [])
        out += res
        if len(res) < 100:
            break
        page += 1
        time.sleep(0.12)
    return out


def stage_snowball(df, res):
    inc = df[df.screen == "I"].merge(res[["rec_id", "openalex_id", "referenced_works"]], on="rec_id", how="left")
    inc = inc[inc.openalex_id.fillna("") != ""]
    log("snowball: %d clear includes with an OpenAlex id" % len(inc))
    seeds = {}
    back = {}
    for r in inc.itertuples():
        for w in json.loads(r.referenced_works or "[]"):
            back.setdefault(w, set()).add(r.rec_id)
    log("snowball: %d distinct references (backward)" % len(back))
    cand = {}
    for w in oa_batch(sorted(back)):
        cand[w["id"].rsplit("/", 1)[-1]] = (w, "backward", back.get(w["id"].rsplit("/", 1)[-1], set()))
    fwd = 0
    for k, r in enumerate(inc.itertuples(), 1):
        for w in oa_citing(r.openalex_id):
            wid = w["id"].rsplit("/", 1)[-1]
            fwd += 1
            if wid in cand:
                old = cand[wid]
                cand[wid] = (old[0], old[1] if "forward" in old[1] else old[1] + "+forward", old[2] | {r.rec_id})
            else:
                cand[wid] = (w, "forward", {r.rec_id})
        if k % 40 == 0:
            log("   forward search %d/%d seeds" % (k, len(inc)))
    log("snowball: %d citing records (forward); %d distinct candidates" % (fwd, len(cand)))
    known = pd.read_csv(find_file("known_records.csv"))
    kdoi = set(known.doi_n.dropna().astype(str))
    ktit = set(known.title_n.dropna().astype(str))
    kurl = set(known.url.dropna().astype(str).str.rsplit("/", n=1).str[-1])
    rows = []
    for wid, (w, how, by) in cand.items():
        title = w.get("display_name") or ""
        ab = inv_abstract(w.get("abstract_inverted_index"))
        yr = w.get("publication_year") or 0
        doi = norm_doi(w.get("doi"))
        txt = title + " " + ab
        if yr < 2020 or wid in kurl or (doi and doi in kdoi) or norm_text(title) in ktit:
            continue
        if not (has_any(txt, A) and has_any(txt, C)) or has_any(txt, NOT):
            continue
        if (w.get("language") or "en") not in ("en", ""):
            continue
        src = ((w.get("primary_location") or {}).get("source") or {})
        rows.append(dict(cand_id="S" + wid[1:], openalex_id=wid, how=how, seeds="; ".join(sorted(by)), n_seeds=len(by),
                         title=title, abstract=ab, year=yr, venue=src.get("display_name") or "",
                         type=w.get("type") or "", doi=doi, url="https://openalex.org/" + wid,
                         cited_by=w.get("cited_by_count"),
                         b_hits=sum(1 for x in B_WEAK if " " + x + " " in " " + norm_text(txt) + " ")))
    sb = pd.DataFrame(rows)
    if len(sb):
        sb = sb.sort_values(["b_hits", "n_seeds", "cited_by"], ascending=False)
    sb.to_csv(os.path.join(OUT, "snowball_candidates.csv"), index=False)
    log("snowball: %d new candidates after removing known records and applying the 2020+, LLM and education filters"
        % len(sb))
    return sb


# ----------------------------------------------------------------------------- main
def package(df):
    summ = {}
    for name in ("resolve.csv", "fetch_log.csv", "extract_log.csv", "snowball_candidates.csv"):
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            summ[name] = int(len(pd.read_csv(p)))
    zpath = "/kaggle/working/%s_%s.zip" % (os.path.basename(OUT.rstrip("/")), TODAY) if ON_KAGGLE else os.path.join(OUT, "..", "fulltext_%s.zip" % TODAY)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(OUT):
            for fn in files:
                if fn.endswith(".pdf"):
                    continue                     # PDFs stay on Kaggle (copyright, size); text is enough
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, OUT))
        z.write(__file__, "code_snapshot.py")
    log("package: %s (%.1f MB) %s" % (zpath, os.path.getsize(zpath) / 1e6, summ))


def main():
    path = find_file(os.environ.get("LIST", "fulltext_list.csv"))
    if not path:
        sys.exit(os.environ.get("LIST", "fulltext_list.csv") + " not found under %s: add the dataset with the data folder" % DATA_DIR)
    df = pd.read_csv(path)
    if FAST:
        df = df.head(25)
    log("records: %d (%s)  stages: %s" % (len(df), df.screen.value_counts().to_dict(), STAGES))
    res = fx = None
    rp = os.path.join(OUT, "resolve.csv")
    if "resolve" in STAGES:
        res = stage_resolve(df)
    elif os.path.exists(rp):
        res = pd.read_csv(rp)
    if "fetch" in STAGES:
        if res is None:
            sys.exit("run the resolve stage first")
        fx = stage_fetch(df, res)
    elif os.path.exists(os.path.join(OUT, "fetch_log.csv")):
        fx = pd.read_csv(os.path.join(OUT, "fetch_log.csv"))
    if "extract" in STAGES:
        stage_extract(df, fx)
    if "snowball" in STAGES and res is not None:
        try:
            stage_snowball(df, res)
        except Exception as e:
            log("!! snowball failed (%s); the other outputs are kept" % e)
    package(df)
    log("done in %.1f min" % ((time.time() - T0) / 60))


if __name__ == "__main__":
    main()
