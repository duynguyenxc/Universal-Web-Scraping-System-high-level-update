from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class NormalizationResult:
    entities_in: int
    entities_out: int
    relationships_in: int
    relationships_out: int
    blank_types_in: int
    blank_types_out: int
    outcome_as_source_in: int
    outcome_as_source_out: int
    flipped_for_cmoc: int
    non_cmoc_edges: int


# Keep this superset for backwards-compatibility with v2/v3 runs; v4 uses a minimal ontology.
ALLOWED_TYPES = {
    "INTERVENTION",
    "COMPARATOR",
    "CONTEXT",
    "MECHANISM",
    "OUTCOME",
    "LEARNER_POPULATION",
    "SETTING_CONTEXT",
    "STUDY_DESIGN",
    # legacy/specifics
    "LEARNER_CONTEXT",
    "COGNITIVE_STATE",
    "MOTIVATION_AFFECT",
    "CLINICAL_DOMAIN",
    "TASK_CASE",
    "ASSESSMENT_MEASURE",
}

# Fix common normalization issues observed in subset runs.
TYPE_SYNONYMS = {
    "COGNITIVE STATE": "COGNITIVE_STATE",
}

# Conservative mapping for *blank* types when titles strongly imply a type.
# This is intentionally small and auditable (we write a report of every change).
BLANK_TITLE_RULES: list[tuple[str, str]] = [
    # learner/population
    ("JUNIOR DOCTORS", "LEARNER_POPULATION"),
    ("DOCTOR", "LEARNER_POPULATION"),
    # comparators / conditions
    ("CONTROL GROUP", "COMPARATOR"),
    ("NO INSTRUCTION", "COMPARATOR"),
    ("NON-CONTRASTIVE", "COMPARATOR"),
    # time/phase constraints
    ("TEST PHASE", "SETTING_CONTEXT"),
    ("PRACTICE PHASE", "SETTING_CONTEXT"),
    ("TRAINING PHASE", "SETTING_CONTEXT"),
    ("TRAINING TIME", "SETTING_CONTEXT"),
    ("TIME-ON-TASK", "OUTCOME"),
    # intervention-like phrasing
    ("CASE-BASED", "INTERVENTION"),
    ("INSTRUCTION", "INTERVENTION"),
    ("FEEDBACK", "INTERVENTION"),
    # mechanism-like phrasing
    ("HYPOTHESIS TESTING", "MECHANISM"),
    ("FEATURE ANALYSIS", "MECHANISM"),
    ("MISLEADING", "COGNITIVE_STATE"),
    ("BIAS", "COGNITIVE_STATE"),
]


# CMOC-family relationship directions we want to see in realist-looking graphs.
CMOC_FAMILY = {
    ("CONTEXT", "MECHANISM"),
    ("CONTEXT", "OUTCOME"),
    ("INTERVENTION", "MECHANISM"),
    ("MECHANISM", "OUTCOME"),
    ("INTERVENTION", "OUTCOME"),
    ("COMPARATOR", "OUTCOME"),
}


def _norm_type(x: object) -> str:
    t = "" if x is None else str(x)
    t = t.strip().upper()
    if t in ("", "NAN", "NONE"):
        return ""
    t = TYPE_SYNONYMS.get(t, t)
    return t


def _infer_blank_type_from_title(title: str) -> str:
    u = title.strip().upper()
    for needle, t in BLANK_TITLE_RULES:
        if needle in u:
            return t
    return ""


def _to_family(t: str) -> str:
    """
    Map detailed types into realist "family" buckets used for CMOC directionality checks.
    This makes the validator robust across v2/v3/v4.
    """
    t = (t or "").strip().upper()
    if t in {"LEARNER_CONTEXT", "SETTING_CONTEXT"}:
        return "CONTEXT"
    if t in {"COGNITIVE_STATE", "MOTIVATION_AFFECT"}:
        return "MECHANISM"
    return t


def _outcome_as_source_count(rels: pd.DataFrame) -> int:
    if "source_family" not in rels.columns:
        return 0
    return int((rels["source_family"] == "OUTCOME").sum())


def _write_text(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8")


def normalize_out_dir(*, out_dir: Path, label: str = "") -> NormalizationResult:
    entities_path = out_dir / "entities.parquet"
    rels_path = out_dir / "relationships.parquet"
    if not entities_path.exists() or not rels_path.exists():
        raise FileNotFoundError("Expected entities.parquet and relationships.parquet in out_dir.")

    entities_in_df = pd.read_parquet(entities_path)
    rels_in_df = pd.read_parquet(rels_path)

    # --- Entities normalization ---
    entities = entities_in_df.copy()
    entities["type_norm"] = entities.get("type", "").map(_norm_type)

    blank_before = int((entities["type_norm"] == "").sum())

    inferred: list[tuple[int, str, str]] = []
    for i, row in entities[entities["type_norm"] == ""].iterrows():
        title = str(row.get("title", "") or "")
        new_t = _infer_blank_type_from_title(title)
        if new_t:
            inferred.append((int(i), title, new_t))
            entities.at[i, "type_norm"] = new_t

    # Keep anything still invalid/blank as blank; we will report it.
    entities["type_norm"] = entities["type_norm"].where(entities["type_norm"].isin(ALLOWED_TYPES), "")
    blank_after = int((entities["type_norm"] == "").sum())

    # Overwrite `type` with normalized version, but keep original for audit.
    entities["type_original"] = entities.get("type", "")
    entities["type"] = entities["type_norm"]
    entities = entities.drop(columns=["type_norm"])

    # --- Relationships normalization ---
    etype = dict(zip(entities["title"], entities["type"]))
    rels = rels_in_df.copy()
    rels["source_type"] = rels.get("source", "").map(etype).fillna("")
    rels["target_type"] = rels.get("target", "").map(etype).fillna("")
    rels["source_family"] = rels["source_type"].map(_to_family).fillna("")
    rels["target_family"] = rels["target_type"].map(_to_family).fillna("")

    outcome_src_before = _outcome_as_source_count(rels)

    rels["was_flipped"] = False
    rels["is_non_cmoc"] = False

    # Flip when the direction is not CMOC-family but the reverse is.
    pair = list(zip(rels["source_family"], rels["target_family"]))
    pair_rev = list(zip(rels["target_family"], rels["source_family"]))
    pair_ok = pd.Series(pair).isin(CMOC_FAMILY)
    pair_rev_ok = pd.Series(pair_rev).isin(CMOC_FAMILY)
    can_flip = (~pair_ok) & pair_rev_ok & (rels["source_family"] != "") & (rels["target_family"] != "")

    flipped_count = int(can_flip.sum())
    if flipped_count:
        src = rels.loc[can_flip, "source"].copy()
        st = rels.loc[can_flip, "source_type"].copy()
        sf = rels.loc[can_flip, "source_family"].copy()

        rels.loc[can_flip, "source"] = rels.loc[can_flip, "target"]
        rels.loc[can_flip, "source_type"] = rels.loc[can_flip, "target_type"]
        rels.loc[can_flip, "source_family"] = rels.loc[can_flip, "target_family"]

        rels.loc[can_flip, "target"] = src
        rels.loc[can_flip, "target_type"] = st
        rels.loc[can_flip, "target_family"] = sf

        rels.loc[can_flip, "description"] = "[FLIPPED_FOR_CMOC] " + rels.loc[can_flip, "description"].astype(str)
        rels.loc[can_flip, "was_flipped"] = True

    # Mark remaining non-CMOC edges (do not delete; keep auditable).
    pair2 = list(zip(rels["source_family"], rels["target_family"]))
    non_cmoc = ~pd.Series(pair2).isin(CMOC_FAMILY) & (rels["source_family"] != "") & (rels["target_family"] != "")
    non_cmoc_count = int(non_cmoc.sum())
    if non_cmoc_count:
        rels.loc[non_cmoc, "description"] = "[NON_CMOC] " + rels.loc[non_cmoc, "description"].astype(str)
        rels.loc[non_cmoc, "is_non_cmoc"] = True

    outcome_src_after = _outcome_as_source_count(rels)

    # --- Write normalized outputs ---
    entities_out = out_dir / "entities_cmoc_normalized.parquet"
    rels_out = out_dir / "relationships_cmoc_normalized.parquet"
    entities.to_parquet(entities_out, index=False)
    rels.to_parquet(rels_out, index=False)

    # --- Report ---
    unknown = entities[entities["type"].astype(str).str.strip() == ""]

    header = "## Part A — KG postprocess (CMOC normalization)\n"
    if label:
        header = f"## Part A {label} — KG postprocess (CMOC normalization)\n"

    lines: list[str] = []
    lines.append(header)
    lines.append(f"- out_dir: `{out_dir.as_posix()}`")
    lines.append(f"- wrote: `{entities_out.name}`, `{rels_out.name}`")
    lines.append("")
    lines.append("### Summary\n")
    lines.append(f"- entities: {len(entities_in_df)} → {len(entities)}")
    lines.append(f"- relationships: {len(rels_in_df)} → {len(rels)}")
    lines.append(f"- blank entity types: {blank_before} → {blank_after}")
    lines.append(f"- OUTCOME-as-source edges (family): {outcome_src_before} → {outcome_src_after}")
    lines.append(f"- flipped for CMOC-family: {flipped_count}")
    lines.append(f"- remaining non-CMOC edges (flagged): {non_cmoc_count}")
    lines.append("")
    lines.append("### What was normalized\n")
    lines.append("- **Type spelling/enum normalization** (e.g., `COGNITIVE STATE` → `COGNITIVE_STATE`).")
    lines.append("- **Conservative blank-type inference** for a small set of obvious titles (logged below).")
    lines.append("- **CMOC directionality normalization**: if `A→B` is non-CMOC but `B→A` is CMOC-family, the edge is flipped and marked `[FLIPPED_FOR_CMOC]`.")
    lines.append("- **Non-CMOC preservation**: edges that still violate CMOC-family are kept (auditable) and marked `[NON_CMOC]`.")
    lines.append("")
    if inferred:
        lines.append("### Inferred types for previously blank entities (conservative rules)\n")
        for _, title, new_t in inferred[:50]:
            lines.append(f"- `{title}` → `{new_t}`")
        if len(inferred) > 50:
            lines.append(f"- ... and {len(inferred) - 50} more")
        lines.append("")
    lines.append("### Remaining blank/unknown entity types (requires prompt/ontology iteration)\n")
    if len(unknown) == 0:
        lines.append("- (none)\n")
    else:
        for t in unknown["title"].astype(str).head(30).tolist():
            lines.append(f"- `{t}`")
        if len(unknown) > 30:
            lines.append(f"- ... and {len(unknown) - 30} more")
        lines.append("")

    report_name = "kg_postprocess_report.md" if not label else f"kg_postprocess_report_{label}.md"
    _write_text(out_dir / report_name, "\n".join(lines).strip() + "\n")

    return NormalizationResult(
        entities_in=len(entities_in_df),
        entities_out=len(entities),
        relationships_in=len(rels_in_df),
        relationships_out=len(rels),
        blank_types_in=blank_before,
        blank_types_out=blank_after,
        outcome_as_source_in=outcome_src_before,
        outcome_as_source_out=outcome_src_after,
        flipped_for_cmoc=flipped_count,
        non_cmoc_edges=non_cmoc_count,
    )


def cli(*, default_label: str = "") -> int:
    ap = argparse.ArgumentParser(description="Part A: post-process KG for CMOC normalization (entities/relationships).")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("LLM-Knowledge-Graph/graphrag-project/output_partA_subset5_v3"),
        help="GraphRAG output directory containing entities.parquet and relationships.parquet.",
    )
    ap.add_argument("--label", type=str, default=default_label, help="Label used in report filename.")
    args = ap.parse_args()

    res = normalize_out_dir(out_dir=args.out_dir, label=args.label)
    print(
        "OK:",
        f"blank_types {res.blank_types_in}->{res.blank_types_out},",
        f"outcome_as_source {res.outcome_as_source_in}->{res.outcome_as_source_out},",
        f"flipped {res.flipped_for_cmoc}, non_cmoc {res.non_cmoc_edges}",
    )
    return 0


def main() -> int:
    return cli()


if __name__ == "__main__":
    raise SystemExit(main())

