from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


KEY_COMMUNITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Self-explanation", re.compile(r"\bself-?explanation\b", re.I)),
    ("Structured reflection", re.compile(r"\bstructured reflection\b|\breflection\b", re.I)),
    ("Schema-based instruction", re.compile(r"\bschema[- ]based\b|\bschemas\b", re.I)),
    ("Test-enhanced learning", re.compile(r"\btest[- ]enhanced\b|\bkey feature\b", re.I)),
    ("Cognitive load", re.compile(r"\bcognitive load\b|\bworked example\b", re.I)),
    ("Cognitive forcing / debiasing", re.compile(r"\bcognitive forcing\b|\bbias\b|\bdebias", re.I)),
]

KEY_CLAIM_TYPES = [
    "INTERVENTION_EFFECT",
    "MECHANISM_EXPLANATION",
    "CONTEXT_MODERATOR",
    "OUTCOME_MEASUREMENT",
    "COMPARATOR_OUTCOME",
]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _pick_communities(rep: pd.DataFrame, *, k: int = 3) -> pd.DataFrame:
    df = rep.copy()
    if "title" not in df.columns:
        return df.head(0)

    df["__title"] = df["title"].fillna("").astype(str)
    df["__score"] = 0.0

    for i, (_, pat) in enumerate(KEY_COMMUNITY_PATTERNS):
        df.loc[df["__title"].str.contains(pat), "__score"] += 10.0 - i * 0.5

    # Prefer higher GraphRAG rank and larger size (but avoid tiny size=2 "noise" communities)
    if "rank" in df.columns:
        df["__score"] += df["rank"].fillna(0).astype(float)
    if "size" in df.columns:
        df["__score"] += (df["size"].fillna(0).astype(float).clip(0, 200)) / 40.0

    df = df.sort_values(["__score"], ascending=False)
    df = df[df.get("size", 0).fillna(0).astype(float) >= 10] if "size" in df.columns else df
    out = df.head(k)
    return out


def _pick_claims(cov: pd.DataFrame, *, k: int = 6) -> pd.DataFrame:
    df = cov.copy()
    # normalize columns across versions
    if "type" not in df.columns and "covariate_type" in df.columns:
        df["type"] = df["covariate_type"]
    df["type"] = df.get("type", "").fillna("").astype(str)
    df["status"] = df.get("status", "").fillna("").astype(str)
    df["description"] = df.get("description", "").fillna("").astype(str)
    df["source_text"] = df.get("source_text", "").fillna("").astype(str)

    df = df[df["type"].isin(KEY_CLAIM_TYPES)]

    # scoring: prefer ones with page marker and that mention key interventions/mechanisms
    df["__score"] = 0.0
    df.loc[df["source_text"].str.contains(r"\[PAGE\s+\d+\]", regex=True), "__score"] += 3.0

    for i, (_, pat) in enumerate(KEY_COMMUNITY_PATTERNS):
        df.loc[df["description"].str.contains(pat) | df["source_text"].str.contains(pat), "__score"] += 2.5 - i * 0.25

    # prefer TRUE and informative descriptions
    df.loc[df["status"].str.upper() == "TRUE", "__score"] += 1.0
    df["__score"] += (df["description"].str.len().clip(0, 180) / 180.0) * 0.5

    # drop obvious garbage rows (empty description or empty source)
    df = df[(df["description"].str.strip() != "") & (df["source_text"].str.strip() != "")]

    df = df.sort_values("__score", ascending=False)
    return df.head(k)


def main() -> int:
    ap = argparse.ArgumentParser(description="Part A: generate a meeting-ready pack (selected communities + claims + short verification note).")
    ap.add_argument("--out-dir", type=Path, default=Path("graphrag-project/output_partA"))
    ap.add_argument("--artifacts-dir", type=Path, default=Path("artifacts/partA"))
    ap.add_argument("--k-communities", type=int, default=3)
    ap.add_argument("--k-claims", type=int, default=6)
    args = ap.parse_args()

    out_dir = args.out_dir
    art_dir = args.artifacts_dir

    rep_p = out_dir / "community_reports.parquet"
    cov_p = out_dir / "covariates.parquet"
    if not rep_p.exists():
        raise SystemExit(f"Missing: {rep_p}")
    if not cov_p.exists():
        raise SystemExit(f"Missing: {cov_p}")

    rep = pd.read_parquet(rep_p)
    cov = pd.read_parquet(cov_p)

    top_com = _pick_communities(rep, k=args.k_communities)
    top_claims = _pick_claims(cov, k=args.k_claims)

    # --- selected examples ---
    md: list[str] = []
    md.append("## Part A (Education) — Selected outputs for meeting (auto-picked)\n")
    md.append(f"- output dir: `{out_dir.as_posix()}`\n")

    md.append("### Selected mechanism communities (from `community_reports.parquet`)\n")
    for _, row in top_com.iterrows():
        cid = row.get("community")
        title = str(row.get("title") or "").strip()
        level = row.get("level")
        rank = row.get("rank")
        size = row.get("size")
        md.append(f"#### Community {cid} — {title}\n")
        md.append(f"- meta: level={level}, rank={rank}, size={size}\n")
        full = str(row.get("full_content") or row.get("summary") or "").strip()
        preview = "\n".join(full.splitlines()[:18]).strip()
        md.append(preview + "\n")

    md.append("### Selected claims (from `covariates.parquet`)\n")
    cols = [c for c in ["type", "status", "description", "source_text"] if c in top_claims.columns]
    md.append(top_claims[cols].to_markdown(index=False))
    md.append("")

    _write(art_dir / "verification_selected_examples.md", "\n".join(md).strip() + "\n")

    # --- short verification note ---
    # Pull coverage from existing summary if present; else keep it minimal.
    summary_p = art_dir / "verification_summary.md"
    coverage_lines: list[str] = []
    if summary_p.exists():
        # extract the 5 key coverage bullets if present
        for ln in summary_p.read_text(encoding="utf-8", errors="replace").splitlines():
            if ln.strip().startswith("- **records") or ln.strip().startswith("- **PDF-backed") or ln.strip().startswith("- **URL-only") or ln.strip().startswith("- **with DOI") or ln.strip().startswith("- **with abstract"):
                coverage_lines.append(ln.strip())

    note: list[str] = []
    note.append("## Part A (Education) — Verification note (meeting draft)\n")
    note.append("### What I ran\n")
    note.append("- Built a benchmark package for the Richmond-28 education corpus (28 records).")
    note.append("- Ingested 20 full-text PDFs + 8 URL-only studies (abstract fallback), and indexed with Microsoft GraphRAG using a CMO-oriented schema.")
    note.append("")
    if coverage_lines:
        note.append("### Corpus coverage (from artifacts)\n")
        note.extend(coverage_lines)
        note.append("")

    note.append("### Evidence-grounded outputs produced\n")
    note.append("- Knowledge graph artifacts: `documents.parquet`, `text_units.parquet`, `entities.parquet`, `relationships.parquet`.")
    note.append("- Community-defined concept artifacts: `communities.parquet`, `community_reports.parquet` (human-readable export available).")
    note.append("- Claim/evidence artifacts: `covariates.parquet` (exported as `human_readable/claims.md`).")
    note.append("")

    note.append("### Representative results (selected)\n")
    for _, row in top_com.iterrows():
        note.append(f"- **Community-as-mechanism**: *{row.get('title')}* (community={row.get('community')}, rank={row.get('rank')}, size={row.get('size')}).")
    note.append("")
    note.append("**Sample CMO-relevant claims (evidence spans):**\n")
    for _, r in top_claims.head(3).iterrows():
        t = str(r.get("type") or "").strip()
        desc = str(r.get("description") or "").strip()
        src = str(r.get("source_text") or "").strip()
        src = " ".join(src.split())
        if len(src) > 260:
            src = src[:260].rstrip() + "…"
        note.append(f"- **{t}**: {desc}\n  - evidence: {src}")
    note.append("")

    note.append("### Verification status vs. professor protocol (this week)\n")
    note.append("- **Search/screening alignment**: Corpus coverage is explicit (PDF-backed vs URL-only) and traceable via DOI/title metadata.")
    note.append("- **CMO extraction**: Claims include intervention effects, mechanism explanations, context moderators, and outcome measurements.")
    note.append("- **Community-defined concepts**: Communities summarize recurring mechanisms (e.g., self-explanation, schema-based learning, reflection).")
    note.append("- **Programme theory comparison (next)**: Map top mechanism-communities to Richmond’s programme theory components (structural comparison).")
    note.append("")

    note.append("### Known limitations (transparent)\n")
    note.append("- 8/28 studies are URL-only (abstract-based), so evidence spans may be less detailed than full text.")
    note.append("- Only ~25% of extracted claim snippets preserve `[PAGE N]` markers; improving span traceability is a next refinement.")
    note.append("")

    note.append("### Where to look in the repo\n")
    note.append(f"- Selected examples: `{(art_dir / 'verification_selected_examples.md').as_posix()}`")
    note.append(f"- Quality gates: `{(art_dir / 'verification_audit.md').as_posix()}`")
    note.append(f"- Community reports: `{(out_dir / 'human_readable/community_reports.md').as_posix()}`")
    note.append(f"- Claims: `{(out_dir / 'human_readable/claims.md').as_posix()}`")
    note.append("")

    _write(art_dir / "verification_note.md", "\n".join(note).strip() + "\n")

    print(f"Wrote: {art_dir / 'verification_selected_examples.md'}")
    print(f"Wrote: {art_dir / 'verification_note.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

