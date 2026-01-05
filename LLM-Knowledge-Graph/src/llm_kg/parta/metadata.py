from __future__ import annotations

import csv
import html as html_lib
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b", re.IGNORECASE)
BMC_ID_RE = re.compile(r"\b(\d{4}-\d{4}-\d{2}-\d+)\b")
BMC_URL_RE = re.compile(r"biomedcentral\.com/(\d{4}-\d{4}/\d+/\d+)", re.IGNORECASE)


def clean_doi(doi: str) -> str:
    doi = doi.strip()
    doi = doi.rstrip(").,;:]}>'\"")
    doi = doi.lstrip("<")
    return doi


def read_text_file_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def _http_get_json(url: str, *, user_agent: str, timeout_s: float) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8", errors="replace"))


def _http_get_text(url: str, *, user_agent: str, timeout_s: float) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read()
        ctype = (resp.headers.get("Content-Type") or "").lower()
    encoding = "utf-8" if "charset=" not in ctype else ctype.split("charset=")[-1].split(";")[0].strip()
    return body.decode(encoding or "utf-8", errors="replace")


def _best_doi_from_text(text: str) -> str | None:
    matches = list(DOI_RE.finditer(text))
    if not matches:
        return None

    def score(m: re.Match[str]) -> tuple[int, int]:
        start = m.start(1)
        window_before = text[max(0, start - 80) : start].lower()
        s = 0
        if "doi:" in window_before or "doi " in window_before or "doi\t" in window_before:
            s += 3
        if "doi.org" in window_before:
            s += 2
        if start < 2000:
            s += 1
        return (s, -start)

    best = max(matches, key=score)
    return clean_doi(best.group(1))


def _normalize_title(title: str) -> str:
    t = re.sub(r"\s+", " ", title).strip().lower()
    t = re.sub(r"[^a-z0-9 ]+", "", t)
    return t


def _title_overlap_score(a: str, b: str) -> float:
    aa = set(_normalize_title(a).split())
    bb = set(_normalize_title(b).split())
    if not aa or not bb:
        return 0.0
    inter = len(aa & bb)
    union = len(aa | bb)
    return inter / union if union else 0.0


def crossref_work_by_doi(doi: str, *, user_agent: str, timeout_s: float, sleep_s: float) -> dict[str, Any] | None:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        data = _http_get_json(url, user_agent=user_agent, timeout_s=timeout_s)
        time.sleep(sleep_s)
        return data.get("message") or None
    except Exception:
        return None


def crossref_search_by_title(title: str, *, user_agent: str, timeout_s: float, sleep_s: float) -> dict[str, Any] | None:
    if not title.strip():
        return None
    q = urllib.parse.urlencode({"query.title": title, "rows": "5"})
    url = "https://api.crossref.org/works?" + q
    try:
        data = _http_get_json(url, user_agent=user_agent, timeout_s=timeout_s)
        time.sleep(sleep_s)
    except Exception:
        return None

    items = ((data.get("message") or {}).get("items") or []) if isinstance(data, dict) else []
    best: dict[str, Any] | None = None
    best_score = 0.0
    for it in items:
        t_list = it.get("title") or []
        it_title = t_list[0] if t_list else ""
        s = _title_overlap_score(title, it_title)
        if s > best_score:
            best_score = s
            best = it
    if best and best_score >= 0.65:
        best["_llmkg_title_match_score"] = best_score
        return best
    return None


def _strip_tags(s: str) -> str:
    # Crossref abstracts are often JATS: <jats:p>...</jats:p>
    s2 = re.sub(r"<[^>]+>", " ", s)
    s2 = html_lib.unescape(s2)
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


def _crossref_to_fields(msg: dict[str, Any]) -> dict[str, Any]:
    title_list = msg.get("title") or []
    title = title_list[0] if title_list else ""

    authors = []
    for a in (msg.get("author") or []):
        given = (a.get("given") or "").strip()
        family = (a.get("family") or "").strip()
        full = " ".join([p for p in [given, family] if p])
        if full:
            authors.append(full)

    year = None
    for key in ["published-print", "published-online", "issued"]:
        parts = (((msg.get(key) or {}).get("date-parts")) or [])
        if parts and parts[0]:
            year = parts[0][0]
            break

    container = msg.get("container-title") or []
    journal = container[0] if container else ""

    abstract = msg.get("abstract")
    abstract_clean = _strip_tags(abstract) if isinstance(abstract, str) and abstract.strip() else None

    return {
        "doi": (msg.get("DOI") or "").strip() or None,
        "title": title or None,
        "authors": authors,
        "year": year,
        "journal": journal or None,
        "publisher": (msg.get("publisher") or None),
        "url": (msg.get("URL") or None),
        "type": (msg.get("type") or None),
        "abstract": abstract_clean,
    }


def extract_uris_from_pdf(pdf_path: Path) -> list[str]:
    # Lazy import: allow running without fitz in rare modes.
    import fitz  # type: ignore

    uris: list[str] = []
    doc = fitz.open(str(pdf_path))
    for i in range(doc.page_count):
        page = doc.load_page(i)
        for link in page.get_links():
            uri = (link or {}).get("uri")
            if isinstance(uri, str) and uri.startswith(("http://", "https://")):
                uris.append(uri.strip())
    doc.close()
    # de-dupe, stable order
    seen: set[str] = set()
    out: list[str] = []
    for u in uris:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _pdf_extract_text_first_pages(pdf_path: Path, max_pages: int) -> str:
    import fitz  # type: ignore

    doc = fitz.open(str(pdf_path))
    texts: list[str] = []
    n = min(max_pages, doc.page_count)
    for i in range(n):
        page = doc.load_page(i)
        texts.append(page.get_text("text") or "")
    doc.close()
    return "\n".join(texts)


def _pdf_metadata_title(pdf_path: Path) -> str | None:
    import fitz  # type: ignore

    doc = fitz.open(str(pdf_path))
    meta = doc.metadata or {}
    doc.close()
    t = (meta.get("title") or "").strip()
    if t.strip().lower() == "untitled":
        return None
    if t and len(t) >= 8 and not t.lower().endswith(".pdf"):
        return t
    return None


def _is_bad_title_candidate(s: str) -> bool:
    s = s.strip()
    if len(s) < 10:
        return True
    low = s.lower()
    if low.startswith("reprinted from"):
        return True
    if low in {"software", "education", "original scientific report", "untitled"}:
        return True
    if low.startswith("med_") or low.startswith("med "):
        return True
    if ".." in s:
        return True
    digit_ratio = sum(ch.isdigit() for ch in s) / max(1, len(s))
    if digit_ratio > 0.25:
        return True
    return False


def _html_extract_meta(html: str) -> dict[str, str]:
    metas: dict[str, str] = {}
    for m in re.finditer(r"<meta\s+[^>]*>", html, flags=re.IGNORECASE):
        tag = m.group(0)
        name_m = re.search(r'\bname\s*=\s*"([^"]+)"', tag, flags=re.IGNORECASE)
        prop_m = re.search(r'\bproperty\s*=\s*"([^"]+)"', tag, flags=re.IGNORECASE)
        content_m = re.search(r'\bcontent\s*=\s*"([^"]*)"', tag, flags=re.IGNORECASE)
        if not content_m:
            continue
        key = (name_m.group(1) if name_m else (prop_m.group(1) if prop_m else "")).strip().lower()
        val = (content_m.group(1) or "").strip()
        if not key or not val:
            continue
        metas.setdefault(key, val)
    return metas


@dataclass
class StudyRecord:
    record_id: str
    source: str  # "pdf" | "url"
    source_id: str  # filename or url

    doi: str | None = None
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    journal: str | None = None
    publisher: str | None = None
    url: str | None = None
    type: str | None = None
    abstract: str | None = None

    doi_source: str | None = None
    title_source: str | None = None
    abstract_source: str | None = None  # "crossref" | "html_meta"
    confidence: float | None = None
    notes: str | None = None


def _make_record_id(doi: str | None, title: str | None, year: int | None) -> str:
    if doi:
        return f"doi:{doi.lower()}"
    t = _normalize_title(title or "")
    if year:
        return f"title:{t}|year:{year}"
    return f"title:{t}"


def build_record_from_pdf(
    pdf_path: Path,
    *,
    max_pages: int,
    user_agent: str,
    timeout_s: float,
    crossref_sleep_s: float,
) -> StudyRecord:
    text = ""
    try:
        text = _pdf_extract_text_first_pages(pdf_path, max_pages=max_pages)
    except Exception as e:
        rec = StudyRecord(record_id=f"pdf:{pdf_path.name}", source="pdf", source_id=pdf_path.name, authors=[])
        rec.notes = f"pdf_read_error: {e}"
        rec.confidence = 0.0
        return rec

    doi = _best_doi_from_text(text)
    doi_source = None
    if doi:
        doi_source = "pdf_regex"
    else:
        m = BMC_ID_RE.search(pdf_path.stem)
        if m:
            doi = f"10.1186/{m.group(1)}"
            doi_source = "filename_bmc"
        else:
            m2 = BMC_URL_RE.search(text)
            if m2:
                doi = f"10.1186/{m2.group(1).replace('/', '-')}"
                doi_source = "pdf_bmc_url"

    title = _pdf_metadata_title(pdf_path)
    title_source = "pdf_meta" if title else None
    if not title:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for cand in lines[:60]:
            if 10 <= len(cand) <= 240 and not _is_bad_title_candidate(cand):
                title = cand
                title_source = "pdf_first_pages"
                break

    cr_msg = None
    if doi:
        cr_msg = crossref_work_by_doi(doi, user_agent=user_agent, timeout_s=timeout_s, sleep_s=crossref_sleep_s)
    if not cr_msg and title:
        cr_msg = crossref_search_by_title(title, user_agent=user_agent, timeout_s=timeout_s, sleep_s=crossref_sleep_s)
        if cr_msg and not doi:
            doi = cr_msg.get("DOI") or doi
            doi_source = doi_source or "crossref_title_match"

    rec = StudyRecord(record_id=_make_record_id(doi, title, None), source="pdf", source_id=pdf_path.name, authors=[])
    rec.doi = doi
    rec.doi_source = doi_source
    rec.title = title
    rec.title_source = title_source

    if cr_msg:
        fields = _crossref_to_fields(cr_msg)
        if fields.get("doi"):
            rec.doi = fields["doi"]
            rec.doi_source = rec.doi_source or "crossref"
        if fields.get("title"):
            if not rec.title or _is_bad_title_candidate(rec.title):
                rec.title = fields["title"]
                rec.title_source = "crossref"
            else:
                overlap = _title_overlap_score(rec.title, fields["title"])
                if overlap < 0.35:
                    rec.notes = (rec.notes + " | " if rec.notes else "") + f"pdf_title_replaced_with_crossref:{overlap:.2f}"
                    rec.title = fields["title"]
                    rec.title_source = "crossref"
        rec.authors = (fields.get("authors") or []) or rec.authors
        rec.year = fields.get("year") or rec.year
        rec.journal = fields.get("journal") or rec.journal
        rec.publisher = fields.get("publisher") or rec.publisher
        rec.url = fields.get("url") or rec.url
        rec.type = fields.get("type") or rec.type
        if fields.get("abstract"):
            rec.abstract = fields["abstract"]
            rec.abstract_source = "crossref"

    rec.record_id = _make_record_id(rec.doi, rec.title, rec.year)

    score = 0.2
    if rec.doi:
        score += 0.5
    if rec.title:
        score += 0.2
    if rec.year:
        score += 0.1
    rec.confidence = min(1.0, score)
    return rec


def build_record_from_url(
    url: str,
    *,
    user_agent: str,
    timeout_s: float,
    crossref_sleep_s: float,
) -> StudyRecord:
    rec = StudyRecord(record_id=f"url:{url}", source="url", source_id=url, authors=[])
    try:
        html = _http_get_text(url, user_agent=user_agent, timeout_s=timeout_s)
    except Exception as e:
        rec.notes = f"url_fetch_error: {e}"
        rec.confidence = 0.0
        return rec

    meta = _html_extract_meta(html)
    doi = meta.get("citation_doi") or meta.get("dc.identifier") or None
    if doi:
        rec.doi = clean_doi(doi)
        rec.doi_source = "html_meta"
    else:
        doi2 = _best_doi_from_text(html)
        if doi2:
            rec.doi = doi2
            rec.doi_source = "html_regex"

    title = meta.get("citation_title") or meta.get("dc.title") or meta.get("og:title") or None
    if title:
        rec.title = title.strip()
        rec.title_source = "html_meta"

    abstract = meta.get("citation_abstract") or meta.get("dc.description") or meta.get("description") or meta.get("og:description")
    if abstract:
        rec.abstract = re.sub(r"\s+", " ", html_lib.unescape(abstract)).strip()
        rec.abstract_source = "html_meta"

    cr_msg = None
    if rec.doi:
        cr_msg = crossref_work_by_doi(rec.doi, user_agent=user_agent, timeout_s=timeout_s, sleep_s=crossref_sleep_s)
    if not cr_msg and rec.title:
        cr_msg = crossref_search_by_title(rec.title, user_agent=user_agent, timeout_s=timeout_s, sleep_s=crossref_sleep_s)
        if cr_msg and not rec.doi:
            rec.doi = cr_msg.get("DOI") or rec.doi
            rec.doi_source = rec.doi_source or "crossref_title_match"

    if cr_msg:
        fields = _crossref_to_fields(cr_msg)
        rec.doi = rec.doi or fields.get("doi")
        if fields.get("title"):
            rec.title = fields["title"]
            rec.title_source = rec.title_source or "crossref"
        rec.authors = (fields.get("authors") or []) or rec.authors
        rec.year = fields.get("year") or rec.year
        rec.journal = fields.get("journal") or rec.journal
        rec.publisher = fields.get("publisher") or rec.publisher
        rec.url = fields.get("url") or rec.url
        rec.type = fields.get("type") or rec.type
        if fields.get("abstract") and not rec.abstract:
            rec.abstract = fields["abstract"]
            rec.abstract_source = "crossref"

    rec.record_id = _make_record_id(rec.doi, rec.title, rec.year)
    score = 0.2
    if rec.doi:
        score += 0.5
    if rec.title:
        score += 0.2
    if rec.year:
        score += 0.1
    rec.confidence = min(1.0, score)
    return rec


def _dedupe_records(records: Iterable[StudyRecord]) -> list[StudyRecord]:
    by_id: dict[str, StudyRecord] = {}
    for r in records:
        if r.record_id not in by_id:
            by_id[r.record_id] = r
        else:
            # merge preference: keep richer record
            cur = by_id[r.record_id]
            if (cur.abstract is None) and (r.abstract is not None):
                cur.abstract = r.abstract
                cur.abstract_source = r.abstract_source
            if (cur.url is None) and (r.url is not None):
                cur.url = r.url
            if (cur.authors is None or not cur.authors) and (r.authors is not None and r.authors):
                cur.authors = r.authors
            if (cur.year is None) and (r.year is not None):
                cur.year = r.year
            if (cur.journal is None) and (r.journal is not None):
                cur.journal = r.journal
    return list(by_id.values())


def write_csv(path: Path, records: list[StudyRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "record_id",
        "source",
        "source_id",
        "doi",
        "title",
        "authors",
        "year",
        "journal",
        "publisher",
        "url",
        "type",
        "abstract",
        "doi_source",
        "title_source",
        "abstract_source",
        "confidence",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            row = asdict(r)
            row["authors"] = "; ".join(r.authors or [])
            w.writerow({k: row.get(k) for k in fieldnames})


def write_jsonl(path: Path, records: list[StudyRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def run_metadata_extraction(
    *,
    pdf_dir: Path,
    links_file: Path | None,
    links_pdf: Path | None,
    max_pages: int,
    out_dir: Path,
    timeout_s: float,
    crossref_sleep_s: float,
    user_agent: str,
) -> list[StudyRecord]:
    records: list[StudyRecord] = []

    if pdf_dir.exists():
        for pdf in sorted(pdf_dir.glob("*.pdf")):
            records.append(
                build_record_from_pdf(
                    pdf,
                    max_pages=max_pages,
                    user_agent=user_agent,
                    timeout_s=timeout_s,
                    crossref_sleep_s=crossref_sleep_s,
                )
            )

    urls: list[str] = []
    if links_file is not None:
        urls.extend(read_text_file_lines(links_file))
    if links_pdf is not None and links_pdf.exists():
        urls.extend(extract_uris_from_pdf(links_pdf))

    # de-dupe URLs
    seen_url: set[str] = set()
    urls2: list[str] = []
    for u in urls:
        if u not in seen_url:
            seen_url.add(u)
            urls2.append(u)

    for url in urls2:
        records.append(
            build_record_from_url(
                url,
                user_agent=user_agent,
                timeout_s=timeout_s,
                crossref_sleep_s=crossref_sleep_s,
            )
        )

    records = sorted(_dedupe_records(records), key=lambda r: (r.year or 0, r.title or "", r.doi or "", r.source_id))

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "studies_metadata.csv", records)
    write_jsonl(out_dir / "studies_metadata.jsonl", records)
    return records

