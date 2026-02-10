from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


_META_LINE_RE = re.compile(r"^(Title|DOI|Year|Journal|URL|RecordID|Source):\s*(.*)\s*$", re.IGNORECASE)
_PAGE_RE = re.compile(r"\[PAGE\s+(\d+)\]", re.IGNORECASE)
_CMO_RE = re.compile(
    r"CMO\[C=(?P<C>.*?);\s*I=(?P<I>.*?);\s*M=(?P<M>.*?);\s*O=(?P<O>.*?)\]\s*$",
    re.IGNORECASE,
)
_DOI_RE = re.compile(r"\b10\.\d{4,9}/\S+\b", re.IGNORECASE)


def _write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _norm_name(s: str) -> str:
    s = (s or "").strip()
    # remove leading numbering/bullets like "1." or "(a)"
    s = re.sub(r"^\s*[\(\[]?\s*\d+[\)\].:-]\s*", "", s)
    s = re.sub(r"^\s*[-•]\s*", "", s)
    s = s.strip()
    # collapse whitespace and strip surrounding parentheses
    s = re.sub(r"\s+", " ", s)
    s = s.strip("()[]{}")
    return s.upper().strip()


def _parse_document_metadata(doc_text: str) -> dict[str, str]:
    """
    documents.parquet 'text' field starts with a metadata block we can parse for verification exports.
    """
    meta: dict[str, str] = {}
    for line in (doc_text or "").splitlines():
        m = _META_LINE_RE.match(line.strip())
        if not m:
            continue
        k = m.group(1).lower()
        v = (m.group(2) or "").strip()
        if v:
            meta[k] = v
    # normalize DOI if the field contains extra text
    if "doi" in meta:
        m = _DOI_RE.search(meta["doi"])
        if m:
            meta["doi"] = m.group(0)
    return meta


def _compact_evidence(s: str, *, max_chars: int = 360) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    # keep the first [PAGE N] marker if present
    page = ""
    m = _PAGE_RE.search(s)
    if m:
        page = f"[PAGE {m.group(1)}] "
    # collapse whitespace/newlines
    s = re.sub(r"\s+", " ", s).strip()
    # take up to first 2 sentences
    parts = re.split(r"(?<=[.!?])\s+", s)
    s2 = " ".join([p for p in parts[:2] if p]).strip()
    if not s2:
        s2 = s
    s2 = (page + s2).strip()
    if len(s2) > max_chars:
        s2 = s2[: max_chars - 3].rstrip() + "..."
    return s2


@dataclass
class EnrichedClaim:
    doc_id: str
    doi: str
    year: str
    title: str
    claim_type: str
    status: str
    subject: str
    subject_type: str
    object: str
    object_type: str
    page: str
    evidence: str
    description: str
    cmo_c: str
    cmo_i: str
    cmo_m: str
    cmo_o: str


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Part A: export verification-grade claims (with doc metadata) and draft CMO configurations."
    )
    ap.add_argument("--out-dir", type=Path, default=Path("graphrag-project/output_partA"))
    ap.add_argument("--out-md", type=Path, default=Path("artifacts/partA/cmo_configurations.md"))
    ap.add_argument("--out-claims-md", type=Path, default=Path("artifacts/partA/claims_enriched.md"))
    ap.add_argument("--max-claims-per-paper", type=int, default=8)
    args = ap.parse_args()

    out_dir = args.out_dir
    docs = pd.read_parquet(out_dir / "documents.parquet")
    tus = pd.read_parquet(out_dir / "text_units.parquet")
    # Prefer postprocessed/normalized entities if present (improves typing consistency for verification exports).
    ent_p = out_dir / "entities_cmoc_normalized.parquet"
    if not ent_p.exists():
        ent_p = out_dir / "entities.parquet"
    ent = pd.read_parquet(ent_p)
    fixed = out_dir / "claims_fixed.parquet"
    cov_path = out_dir / (
        "claims_fixed.parquet"
        if fixed.exists()
        else ("claims.parquet" if (out_dir / "claims.parquet").exists() else "covariates.parquet")
    )
    claims = pd.read_parquet(cov_path)

    # Build doc_id -> meta
    doc_meta: dict[str, dict[str, str]] = {}
    for _, row in docs.iterrows():
        doc_id = str(row.get("id", "")).strip()
        meta = _parse_document_metadata(str(row.get("text", "") or ""))
        doc_meta[doc_id] = meta

    # text_units: explode document_ids so we can map text_unit_id -> doc_id
    tu_map = tus[["id", "document_ids"]].explode("document_ids")
    tu_map = tu_map.rename(columns={"id": "text_unit_id", "document_ids": "doc_id"})

    # entity title -> entity type (normalized)
    ent["__k"] = ent["title"].fillna("").map(lambda x: _norm_name(str(x)))
    ent_map = ent.drop_duplicates("__k").set_index("__k")["type"].to_dict()

    # claims: normalize fields across GraphRAG versions
    subj_col = "subject_id" if "subject_id" in claims.columns else ("subject" if "subject" in claims.columns else None)
    obj_col = "object_id" if "object_id" in claims.columns else ("object" if "object" in claims.columns else None)
    src_col = "source_text" if "source_text" in claims.columns else ("text" if "text" in claims.columns else None)

    if subj_col is None or obj_col is None:
        raise RuntimeError(f"Cannot find subject/object columns in {cov_path.name}: {claims.columns.tolist()}")

    claims = claims.copy()
    claims["subject"] = claims[subj_col].fillna("").map(lambda x: _norm_name(str(x)))
    claims["object"] = claims[obj_col].fillna("").map(lambda x: _norm_name(str(x)))
    claims["evidence"] = claims[src_col].fillna("").map(lambda x: str(x).strip()) if src_col else ""
    claims["claim_type"] = claims["type"] if "type" in claims.columns else claims.get("covariate_type", "")
    claims["claim_status"] = claims["status"] if "status" in claims.columns else claims.get("covariate_status", "")
    claims["description"] = claims.get("description", "").fillna("").map(lambda x: str(x).strip())

    # join to doc_id via text_unit_id
    claims = claims.merge(tu_map, how="left", on="text_unit_id")

    enriched: list[EnrichedClaim] = []
    for _, r in claims.iterrows():
        doc_id = str(r.get("doc_id", "") or "").strip()
        if not doc_id:
            continue
        meta = doc_meta.get(doc_id, {})
        doi = meta.get("doi", "")
        year = meta.get("year", "")
        title = meta.get("title", "") or ""

        subj = str(r.get("subject", "") or "").strip()
        obj = str(r.get("object", "") or "").strip()
        subj_t = ent_map.get(subj, "")
        obj_t = ent_map.get(obj, "")

        ev = str(r.get("evidence", "") or "").strip()
        ev = _compact_evidence(ev)
        m_page = _PAGE_RE.search(ev)
        page = m_page.group(1) if m_page else ""

        desc = str(r.get("description", "") or "").strip()
        cmo_c = cmo_i = cmo_m = cmo_o = ""
        m = _CMO_RE.search(desc)
        if m:
            cmo_c = _norm_name(m.group("C"))
            cmo_i = _norm_name(m.group("I"))
            cmo_m = _norm_name(m.group("M"))
            cmo_o = _norm_name(m.group("O"))

        enriched.append(
            EnrichedClaim(
                doc_id=doc_id,
                doi=doi,
                year=year,
                title=title,
                claim_type=str(r.get("claim_type", "") or ""),
                status=str(r.get("claim_status", "") or ""),
                subject=subj,
                subject_type=subj_t,
                object=obj,
                object_type=obj_t,
                page=page,
                evidence=ev,
                description=desc,
                cmo_c=cmo_c,
                cmo_i=cmo_i,
                cmo_m=cmo_m,
                cmo_o=cmo_o,
            )
        )

    # ---- Write enriched claims table (meeting/verification friendly) ----
    df_out = pd.DataFrame([c.__dict__ for c in enriched])
    # Drop obviously incomplete rows (helps verification readability)
    df_out = df_out[(df_out["claim_type"].fillna("").astype(str).str.strip() != "")]
    df_out = df_out.sort_values(["doi", "doc_id", "claim_type"]).reset_index(drop=True)

    md_claims = "## Part A — Enriched claims (verification-grade view)\n\n"
    md_claims += f"- source: `{cov_path.as_posix()}`\n"
    md_claims += f"- rows: **{len(df_out)}**\n\n"
    cols = [
        "doi",
        "year",
        "title",
        "claim_type",
        "status",
        "subject",
        "subject_type",
        "object",
        "object_type",
        "page",
        "evidence",
        "description",
    ]
    cols = [c for c in cols if c in df_out.columns]
    md_claims += df_out[cols].head(120).to_markdown(index=False)
    md_claims += "\n"
    _write_text(args.out_claims_md, md_claims)

    # ---- Draft CMO configurations (per paper) ----
    md: list[str] = []
    md.append("## Part A — Draft CMO configurations (auto-generated)\n")
    md.append(
        "This file is intended for Richmond-style verification. It is a **draft** derived from GraphRAG claims + entity typing, and is expected to be refined with a human-in-the-loop pass.\n"
    )

    # Group by document id (stable), but display DOI/title for reviewers.
    for doc_id, g in df_out.groupby("doc_id"):
        g = g.copy()
        paper_title = str(g["title"].iloc[0]) if "title" in g.columns else ""
        paper_year = str(g["year"].iloc[0]) if "year" in g.columns else ""
        doi = str(g["doi"].iloc[0]) if "doi" in g.columns else ""

        md.append(f"### Paper: {paper_title} ({paper_year})")
        if doi:
            md.append(f"- DOI: `{doi}`")
        md.append(f"- DocumentID: `{doc_id}`")
        md.append("")

        # prioritize claims that already include a CMO[...] tag in description (after prompt upgrade + re-index)
        g["has_cmo_tag"] = g["description"].fillna("").map(lambda x: "CMO[" in str(x))
        g = g.sort_values(["has_cmo_tag", "claim_type"], ascending=[False, True])

        # build configs: 1 config per top claim (simple but auditable)
        for _, r in g.head(int(args.max_claims_per_paper)).iterrows():
            c = r.get("cmo_c", "") or ""
            i = r.get("cmo_i", "") or ""
            m = r.get("cmo_m", "") or ""
            o = r.get("cmo_o", "") or ""
            # fallback: infer from entity types if CMO tag is missing
            if not (c or i or m or o):
                st = str(r.get("subject_type", "") or "")
                ot = str(r.get("object_type", "") or "")
                if st in {"LEARNER_CONTEXT", "SETTING_CONTEXT", "COGNITIVE_STATE", "MOTIVATION_AFFECT"}:
                    c = str(r.get("subject", "") or "")
                if ot in {"LEARNER_CONTEXT", "SETTING_CONTEXT", "COGNITIVE_STATE", "MOTIVATION_AFFECT"}:
                    c = c or str(r.get("object", "") or "")
                if st in {"INTERVENTION", "COMPARATOR"}:
                    i = str(r.get("subject", "") or "")
                if ot in {"INTERVENTION", "COMPARATOR"}:
                    i = i or str(r.get("object", "") or "")
                if st == "MECHANISM":
                    m = str(r.get("subject", "") or "")
                if ot == "MECHANISM":
                    m = m or str(r.get("object", "") or "")
                if st == "OUTCOME":
                    o = str(r.get("subject", "") or "")
                if ot == "OUTCOME":
                    o = o or str(r.get("object", "") or "")

            md.append(
                f"- **CMO candidate**: C={c or 'NONE'} | I={i or 'NONE'} | M={m or 'NONE'} | O={o or 'NONE'}"
            )
            ev = str(r.get("evidence", "") or "").strip()
            if ev:
                md.append(f"  - evidence: {ev}")
            md.append(f"  - claim_type: {r.get('claim_type','')}; status: {r.get('status','')}")
            md.append("")

    _write_text(args.out_md, "\n".join(md).strip() + "\n")
    print(f"Wrote: {args.out_claims_md}")
    print(f"Wrote: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

