from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _sanitize_filename(s: str, max_len: int = 80) -> str:
    s = (s or "").strip()
    if not s:
        return "untitled"
    s = re.sub(r"[^\w\s\-\(\)\[\]\.]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len].strip() or "untitled"


def _pick_day_dir(data_root: Path, day: str | None) -> Path:
    if day:
        p = data_root / day
        if not p.exists() or not p.is_dir():
            raise SystemExit(f"Day folder not found: {p}")
        return p

    # Pick latest folder by name (works for YY-MM-DD naming)
    candidates = sorted([p for p in data_root.iterdir() if p.is_dir()], key=lambda p: p.name)
    if not candidates:
        raise SystemExit(f"No day folders found under: {data_root}")
    return candidates[-1]


def _pick_jsonl(day_dir: Path, jsonl: str | None) -> Path:
    if jsonl:
        p = Path(jsonl)
        if not p.is_absolute():
            p = day_dir / p
        if not p.exists():
            raise SystemExit(f"JSONL not found: {p}")
        return p

    jsonls = sorted(day_dir.glob("*.jsonl"))
    if not jsonls:
        raise SystemExit(f"No *.jsonl found in: {day_dir}")
    # Prefer corrosion_papers_*.jsonl if present
    preferred = [p for p in jsonls if p.name.startswith("corrosion_papers_")]
    return preferred[0] if preferred else jsonls[0]


def _get_first(d: dict[str, Any], keys: list[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _to_text_record(obj: dict[str, Any]) -> tuple[str, str] | None:
    title = str(_get_first(obj, ["title", "paper_title", "name"]) or "").strip()
    abstract = str(_get_first(obj, ["abstract", "summary", "description"]) or "").strip()
    if not title and not abstract:
        return None

    doi = _get_first(obj, ["doi", "DOI"])
    url = _get_first(obj, ["url", "landing_page_url", "pdf_url"])
    published = _get_first(obj, ["published", "year", "publication_date", "date"])
    source = _get_first(obj, ["source", "provider", "origin"])
    authors = _get_first(obj, ["authors", "author"])
    keywords = _get_first(obj, ["keywords", "keyword"])

    # Build a compact text doc (GraphRAG will chunk it)
    parts: list[str] = []
    if title:
        parts.append(f"Title: {title}")
    if doi:
        parts.append(f"DOI: {doi}")
    if url:
        parts.append(f"URL: {url}")
    if published:
        parts.append(f"Published: {published}")
    if source:
        parts.append(f"Source: {source}")
    if authors:
        parts.append(f"Authors: {authors}")
    if keywords:
        parts.append(f"Keywords: {keywords}")

    if abstract:
        parts.append("")
        parts.append("Abstract:")
        parts.append(abstract)

    fname = _sanitize_filename(title) if title else "no_title"
    return fname, "\n".join(parts).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare Microsoft GraphRAG input (*.txt) from UWSS JSONL exports.")
    ap.add_argument(
        "--data-root",
        default=str(Path(__file__).resolve().parents[1] / "data-from-S3-bucket"),
        help="Folder containing day subfolders like 25-12-06/ (default: LLM-Knowledge-Graph/data-from-S3-bucket).",
    )
    ap.add_argument("--day", default=None, help="Day folder name (e.g., 25-12-06). If omitted, uses latest.")
    ap.add_argument(
        "--jsonl",
        default=None,
        help="JSONL filename within the day folder (or absolute path). If omitted, auto-picks *.jsonl.",
    )
    ap.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "graphrag-project" / "input"),
        help="Output directory for GraphRAG input text files.",
    )
    ap.add_argument("--max-docs", type=int, default=50, help="Maximum number of docs to export.")
    ap.add_argument("--min-abstract-len", type=int, default=50, help="Skip docs with short/empty abstracts.")
    ap.add_argument("--clean", action="store_true", help="Delete existing *.txt in output-dir first.")
    args = ap.parse_args()

    data_root = Path(args.data_root).resolve()
    day_dir = _pick_day_dir(data_root, args.day)
    jsonl_path = _pick_jsonl(day_dir, args.jsonl)

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.clean:
        for p in out_dir.glob("*.txt"):
            p.unlink(missing_ok=True)

    written = 0
    seen: set[str] = set()

    with jsonl_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if written >= args.max_docs:
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            rec = _to_text_record(obj)
            if not rec:
                continue
            fname_base, text = rec

            # Enforce abstract length if present
            abstract = str(_get_first(obj, ["abstract", "summary", "description"]) or "").strip()
            if len(abstract) < args.min_abstract_len:
                continue

            # Dedupe by DOI/URL/title
            doi = str(_get_first(obj, ["doi", "DOI"]) or "").strip().lower()
            url = str(_get_first(obj, ["url", "landing_page_url", "pdf_url"]) or "").strip().lower()
            title = str(_get_first(obj, ["title", "paper_title", "name"]) or "").strip().lower()
            key = doi or url or title
            if key and key in seen:
                continue
            if key:
                seen.add(key)

            filename = f"{fname_base}_{i}.txt"
            (out_dir / filename).write_text(text, encoding="utf-8")
            written += 1

    print(f"Day: {day_dir.name}")
    print(f"Source JSONL: {jsonl_path}")
    print(f"Output dir: {out_dir}")
    print(f"Wrote {written} text files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



