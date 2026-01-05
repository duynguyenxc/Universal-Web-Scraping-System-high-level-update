from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


GENERIC_LABELS = {
    "students",
    "student",
    "education",
    "clinical reasoning",
    "clinical",
    "intervention",
    "learning",
    "medical education",
}

BLACKLIST_PATTERNS = [
    re.compile(r"\b10\.\d{4,9}/\S+\b", re.IGNORECASE),  # DOI-like
    re.compile(r"\b(19|20)\d{2}\b"),  # years
    re.compile(r"\b(wiley|elsevier|springer|ovid|informa)\b", re.IGNORECASE),
    re.compile(r"\b(medical education|academic medicine|medical teacher)\b", re.IGNORECASE),
]


def _exists(out_dir: Path, name: str) -> bool:
    return (out_dir / name).exists()


def _count_blacklisted(strings: list[str]) -> int:
    n = 0
    for s in strings:
        if not s:
            continue
        if any(p.search(s) for p in BLACKLIST_PATTERNS):
            n += 1
    return n


def _safe_col(df: pd.DataFrame, col: str) -> list[str]:
    if col not in df.columns:
        return []
    return [str(x) for x in df[col].fillna("").tolist()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Part A: audit GraphRAG outputs for verification readiness (noise, coverage, traceability).")
    ap.add_argument("--out-dir", type=Path, default=Path("LLM-Knowledge-Graph/graphrag-project/output_partA"))
    ap.add_argument("--out-md", type=Path, default=Path("LLM-Knowledge-Graph/artifacts/partA/verification_audit.md"))
    ap.add_argument("--top-n", type=int, default=25)
    args = ap.parse_args()

    out_dir = args.out_dir
    md: list[str] = []

    md.append("## Part A (Education) — Verification Audit (quality gates)\n")
    md.append(f"- output dir: `{out_dir.as_posix()}`\n")

    # --- Presence / coverage ---
    md.append("### Artifact presence\n")
    for f in [
        "documents.parquet",
        "text_units.parquet",
        "entities.parquet",
        "relationships.parquet",
        "communities.parquet",
        "community_reports.parquet",
        # GraphRAG versions differ: claims may be written as "covariates.parquet"
        "claims.parquet",
        "covariates.parquet",
    ]:
        md.append(f"- **{f}**: {'YES' if _exists(out_dir, f) else 'NO'}")
    md.append("")

    # --- Entities ---
    if _exists(out_dir, "entities.parquet"):
        ent = pd.read_parquet(out_dir / "entities.parquet")
        md.append("### Entity quality (anti-noise)\n")
        md.append(f"- entities rows: **{len(ent)}**")
        types = ent["type"].value_counts() if "type" in ent.columns else None
        if types is not None:
            md.append("\n**Entity types (counts)**\n")
            md.append(types.to_frame("count").head(30).to_markdown())

        titles = _safe_col(ent, "title")
        blacklisted = _count_blacklisted(titles)
        md.append(f"\n- blacklisted-looking entity titles (heuristic): **{blacklisted} / {len(titles) or 1}**")

        if "frequency" in ent.columns:
            md.append("\n**Top entities by frequency (spot-check for bibliographic noise)**\n")
            cols = [c for c in ["title", "type", "frequency", "degree"] if c in ent.columns]
            md.append(ent[cols].sort_values("frequency", ascending=False).head(args.top_n).to_markdown(index=False))
        md.append("")

    # --- Claims / covariates ---
    claims_path = out_dir / "claims.parquet"
    cov_path = out_dir / "covariates.parquet"
    src_path = claims_path if claims_path.exists() else (cov_path if cov_path.exists() else None)
    if src_path is not None:
        claims = pd.read_parquet(src_path)
        md.append("### Claim quality (traceability + CMO)\n")
        md.append(f"- source: **{src_path.name}**")
        md.append(f"- claims rows: **{len(claims)}**")
        # Column names vary by version; "source_text" preferred, fallback to "text".
        src_text = _safe_col(claims, "source_text") or _safe_col(claims, "text")
        has_page = sum(1 for s in src_text if "[PAGE " in s)
        md.append(f"- claims with `[PAGE N]` marker in source_text: **{has_page} / {len(src_text) or 1}**")
        md.append("")

        type_col = "type" if "type" in claims.columns else ("covariate_type" if "covariate_type" in claims.columns else None)
        if type_col:
            md.append("**Claim types (counts)**\n")
            md.append(claims[type_col].value_counts().to_frame("count").head(30).to_markdown())
            md.append("")

        cols = [c for c in ["subject", "object", "type", "covariate_type", "status", "covariate_status", "description", "source_text", "text"] if c in claims.columns]
        if cols:
            md.append("**Sample claims (spot-check)**\n")
            md.append(claims[cols].head(12).to_markdown(index=False))
            md.append("")

    # --- Communities / reports ---
    if _exists(out_dir, "communities.parquet"):
        com = pd.read_parquet(out_dir / "communities.parquet")
        md.append("### Community structure\n")
        md.append(f"- communities rows: **{len(com)}**")
        md.append("")

    if _exists(out_dir, "community_reports.parquet"):
        rep = pd.read_parquet(out_dir / "community_reports.parquet")
        md.append("### Community report quality (principle-level heuristics)\n")
        md.append(f"- community_reports rows: **{len(rep)}**")

        if "title" in rep.columns:
            titles = [str(x).strip().lower() for x in rep["title"].fillna("").tolist()]
            generic = sum(1 for t in titles if (t in GENERIC_LABELS) or (len(t.split()) <= 2))
            md.append(f"- generic/too-short titles (heuristic): **{generic} / {len(titles) or 1}**")

        # dump a few report headers (not full content) for meeting readiness
        header_cols = [c for c in ["community", "level", "title", "rank", "size"] if c in rep.columns]
        if header_cols:
            md.append("\n**Community report headers (sample)**\n")
            md.append(rep[header_cols].head(15).to_markdown(index=False))
        md.append("")

    # --- What to do next (checklist) ---
    md.append("### What to verify against Richmond (next)\n")
    md.append("- **Search/screening alignment**: overlap with Richmond-28 + explain mismatches.")
    md.append("- **CMO fidelity**: do extracted claims support C→M→O patterns?")
    md.append("- **Concept alignment**: map community titles ↔ Richmond mechanisms/programme theory components.")
    md.append("- **Cross-study synthesis**: identify dominant patterns + contradictions with citations/spans.")
    md.append("")

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md).strip() + "\n", encoding="utf-8")
    print(f"Wrote: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

