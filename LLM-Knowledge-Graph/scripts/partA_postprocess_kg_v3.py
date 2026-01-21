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


ALLOWED_TYPES = {
    "INTERVENTION",
    "COMPARATOR",
    "LEARNER_POPULATION",
    "LEARNER_CONTEXT",
    "COGNITIVE_STATE",
    "MOTIVATION_AFFECT",
    "SETTING_CONTEXT",
    "CONTEXT",
    "MECHANISM",
    "OUTCOME",
    "CLINICAL_DOMAIN",
    "STUDY_DESIGN",
}

# Fix common normalization issues observed in v3 subset runs.
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


def _outcome_as_source_count(rels: pd.DataFrame) -> int:
    if "source_type" not in rels.columns:
        return 0
    return int((rels["source_type"] == "OUTCOME").sum())


def _write_report(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8")


def normalize_out_dir(out_dir: Path) -> NormalizationResult:
    entities_path = out_dir / "entities.parquet"
    rels_path = out_dir / "relationships.parquet"
    if not entities_path.exists() or not rels_path.exists():
        raise FileNotFoundError("Expected entities.parquet and relationships.parquet in out_dir.")

    entities = pd.read_parquet(entities_path)
    rels = pd.read_parquet(rels_path)

    # --- Entities normalization ---
    entities = entities.copy()
    entities["type_norm"] = entities["type"].map(_norm_type)

    blank_before = int((entities["type_norm"] == "").sum())

    # Fix truly blank types via conservative title rules.
    inferred = []
    for i, row in entities[entities["type_norm"] == ""].iterrows():
        title = str(row.get("title", "") or "")
        new_t = _infer_blank_type_from_title(title)
        if new_t:
            inferred.append((i, title, new_t))
            entities.at[i, "type_norm"] = new_t

    # Keep anything still invalid/blank as blank; we will report it and optionally filter.
    entities["type_norm"] = entities["type_norm"].where(entities["type_norm"].isin(ALLOWED_TYPES), "")
    blank_after = int((entities["type_norm"] == "").sum())

    # We overwrite `type` with normalized version, but keep the original in a new column for audit.
    entities["type_original"] = entities["type"]
    entities["type"] = entities["type_norm"]
    entities = entities.drop(columns=["type_norm"])

    # --- Relationships normalization ---
    etype = dict(zip(entities["title"], entities["type"]))
    rels = rels.copy()
    rels["source_type"] = rels["source"].map(etype).fillna("")
    rels["target_type"] = rels["target"].map(etype).fillna("")

    outcome_src_before = _outcome_as_source_count(rels)

    # Flip edges where OUTCOME is the source and target is not OUTCOME.
    # This is a pragmatic normalization to align with CMO directionality (Outcome as sink).
    to_flip = (rels["source_type"] == "OUTCOME") & (rels["target_type"] != "OUTCOME") & (rels["target_type"] != "")
    rels["was_flipped"] = False
    if int(to_flip.sum()) > 0:
        src = rels.loc[to_flip, "source"].copy()
        st = rels.loc[to_flip, "source_type"].copy()
        rels.loc[to_flip, "source"] = rels.loc[to_flip, "target"]
        rels.loc[to_flip, "source_type"] = rels.loc[to_flip, "target_type"]
        rels.loc[to_flip, "target"] = src
        rels.loc[to_flip, "target_type"] = st
        # mark description
        rels.loc[to_flip, "description"] = (
            "[FLIPPED_FOR_CMO] " + rels.loc[to_flip, "description"].astype(str)
        )
        rels.loc[to_flip, "was_flipped"] = True

    outcome_src_after = _outcome_as_source_count(rels)

    # --- Write normalized outputs ---
    entities_out = out_dir / "entities_cmo_normalized.parquet"
    rels_out = out_dir / "relationships_cmo_normalized.parquet"
    entities.to_parquet(entities_out, index=False)
    rels.to_parquet(rels_out, index=False)

    # --- Report ---
    unknown = entities[entities["type"].astype(str).str.strip() == ""]
    invalid_claim_type_note = (
        "Note: claim schema noise is handled in claims_fixed.parquet; this script only normalizes entities/relationships."
    )

    lines: list[str] = []
    lines.append("## Part A v3 — KG postprocess (CMO normalization)\n")
    lines.append(f"- out_dir: `{out_dir.as_posix()}`")
    lines.append(f"- wrote: `{entities_out.name}`, `{rels_out.name}`")
    lines.append("")
    lines.append("### Summary\n")
    lines.append(f"- entities: {len(pd.read_parquet(entities_path))} → {len(entities)}")
    lines.append(f"- relationships: {len(pd.read_parquet(rels_path))} → {len(rels)}")
    lines.append(f"- blank entity types: {blank_before} → {blank_after}")
    lines.append(f"- OUTCOME-as-source edges: {outcome_src_before} → {outcome_src_after}")
    lines.append("")
    lines.append("### What was normalized\n")
    lines.append("- **Type spelling/enum normalization** (e.g., `COGNITIVE STATE` → `COGNITIVE_STATE`).")
    lines.append("- **Conservative blank-type inference** for a small set of obvious titles (logged below).")
    lines.append("- **Directionality normalization**: edges with `OUTCOME → X` flipped to `X → OUTCOME` and marked with `[FLIPPED_FOR_CMO]`.")
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
    lines.append("### Notes\n")
    lines.append(f"- {invalid_claim_type_note}")

    _write_report(out_dir / "kg_postprocess_report_v3.md", "\n".join(lines).strip() + "\n")

    return NormalizationResult(
        entities_in=len(pd.read_parquet(entities_path)),
        entities_out=len(entities),
        relationships_in=len(pd.read_parquet(rels_path)),
        relationships_out=len(rels),
        blank_types_in=blank_before,
        blank_types_out=blank_after,
        outcome_as_source_in=outcome_src_before,
        outcome_as_source_out=outcome_src_after,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Part A v3: post-process KG for CMO normalization (entities/relationships).")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("LLM-Knowledge-Graph/graphrag-project/output_partA_subset5_v3"),
        help="GraphRAG output directory containing entities.parquet and relationships.parquet.",
    )
    args = ap.parse_args()

    res = normalize_out_dir(args.out_dir)
    print(
        "OK:",
        f"blank_types {res.blank_types_in}->{res.blank_types_out},",
        f"outcome_as_source {res.outcome_as_source_in}->{res.outcome_as_source_out}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

