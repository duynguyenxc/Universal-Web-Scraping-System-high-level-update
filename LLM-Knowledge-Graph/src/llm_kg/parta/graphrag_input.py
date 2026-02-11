from __future__ import annotations

import json
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _slugify(s: str, *, max_len: int = 120) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_.-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if len(s) > max_len:
        s = s[:max_len].rstrip("_")
    return s or "doc"


def _doi_to_filename(doi: str) -> str:
    return _slugify("doi_" + doi.replace("/", "_"))


def _record_id_to_filename(record_id: str) -> str:
    return _slugify(record_id.replace(":", "_").replace("|", "_"))


def _stable_suffix(*parts: str, n: int = 10) -> str:
    """
    Stable short hash to keep filenames short on Windows (avoid MAX_PATH issues).
    """
    raw = "|".join([p or "" for p in parts]).encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:n]


def _make_input_filename(*, doi: str | None, record_id: str, source_id: str, title: str | None) -> str:
    """
    Create a deterministic, short, filesystem-safe filename.

    Windows paths can be long in this repo; keep filenames compact and stable.
    """
    key = (doi or "").strip() or record_id.strip() or source_id.strip() or (title or "").strip() or "doc"
    slug = _slugify(key, max_len=40)
    suf = _stable_suffix(doi or "", record_id or "", source_id or "", title or "")
    return f"{slug}__{suf}.txt"


def _safe_int(x: Any) -> int | None:
    try:
        return int(x)
    except Exception:
        return None


_REF_SECTION_RE = re.compile(r"(?mi)^\s*(references|bibliography)\s*$")


def _strip_trailing_references(text: str) -> str:
    """
    Remove trailing references/bibliography when it appears near the end of the document.

    Motivation: bibliographies are dense with author/journal names and can dominate entity/community
    extraction, harming CMO/mechanism-level communities.
    """
    if not text:
        return text
    m = _REF_SECTION_RE.search(text)
    if not m:
        return text
    # Only strip if the marker is late enough (avoid false positives in e.g. "References" within body).
    if m.start() < int(len(text) * 0.60):
        return text
    return text[: m.start()].rstrip()


def _pdf_extract_text(pdf_path: Path) -> str:
    import fitz  # type: ignore

    doc = fitz.open(str(pdf_path))
    parts: list[str] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        # Add page markers to enable span-based traceability in claim source text.
        page_text = page.get_text("text") or ""
        parts.append(f"[PAGE {i + 1}]\n{page_text}".strip())
    doc.close()
    text = "\n".join(parts)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = text.strip()
    text = _strip_trailing_references(text)
    return text


@dataclass
class InputDoc:
    record_id: str
    filename: str
    text: str


def load_metadata_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def build_graphrag_docs_from_metadata(
    *,
    metadata_rows: list[dict[str, Any]],
    pdf_dir: Path,
) -> list[InputDoc]:
    docs: list[InputDoc] = []

    for r in metadata_rows:
        record_id = (r.get("record_id") or "").strip() or ""
        source = (r.get("source") or "").strip()
        source_id = (r.get("source_id") or "").strip()
        doi = (r.get("doi") or "").strip() or None
        title = (r.get("title") or "").strip() or None
        year = _safe_int(r.get("year"))
        journal = (r.get("journal") or "").strip() or None
        url = (r.get("url") or "").strip() or None
        abstract = (r.get("abstract") or "").strip() or None
        authors_raw = r.get("authors") or []
        authors = authors_raw if isinstance(authors_raw, list) else []

        header_lines = [
            f"Title: {title or ''}".strip(),
            f"DOI: {doi or ''}".strip(),
            f"Year: {year or ''}".strip(),
            f"Journal: {journal or ''}".strip(),
            f"URL: {url or ''}".strip(),
            f"Authors: {', '.join(authors)}".strip(),
            f"RecordID: {record_id}".strip(),
            f"Source: {source} {source_id}".strip(),
        ]
        header_kv = "\n".join([ln for ln in header_lines if ln and not ln.endswith(":")])
        header = "\n".join(
            [
                "### METADATA (IGNORE FOR ENTITY/CLAIM EXTRACTION)",
                header_kv,
                "### END_METADATA",
            ]
        ).strip()

        body = ""
        if source == "pdf" and source_id:
            pdf_path = pdf_dir / source_id
            if pdf_path.exists():
                body = _pdf_extract_text(pdf_path)
        elif source == "url":
            # URL-only: use abstract if we have it
            if abstract:
                body = abstract

        if not body:
            # still create a doc so coverage is explicit
            body = abstract or ""

        full_text = (
            header
            + "\n\n"
            + "### PAPER_TEXT (USE FOR ENTITY/CLAIM EXTRACTION)\n"
            + body.strip()
            + "\n### END_PAPER_TEXT\n"
        ).strip() + "\n"

        # Keep filenames short and stable across runs (Windows path-length safety).
        fname = _make_input_filename(doi=doi, record_id=record_id or "", source_id=source_id or "", title=title)

        docs.append(InputDoc(record_id=record_id or fname, filename=fname, text=full_text))

    # de-dupe filenames
    seen: dict[str, int] = {}
    out: list[InputDoc] = []
    for d in docs:
        if d.filename not in seen:
            seen[d.filename] = 0
            out.append(d)
        else:
            seen[d.filename] += 1
            stem = d.filename[:-4] if d.filename.endswith(".txt") else d.filename
            out.append(InputDoc(record_id=d.record_id, filename=f"{stem}__{seen[d.filename]}.txt", text=d.text))
    return out


def write_graphrag_input_dir(input_dir: Path, docs: list[InputDoc]) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    for d in docs:
        (input_dir / d.filename).write_text(d.text, encoding="utf-8")

