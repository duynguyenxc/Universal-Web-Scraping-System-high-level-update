from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
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
    "SETTING CONTEXT": "SETTING_CONTEXT",
    "SETTING-CONTEXT": "SETTING_CONTEXT",
    "LEARNER CONTEXT": "LEARNER_CONTEXT",
    "LEARNER-CONTEXT": "LEARNER_CONTEXT",
    "MOTIVATION AFFECT": "MOTIVATION_AFFECT",
    "MOTIVATION-AFFECT": "MOTIVATION_AFFECT",
    "MOTIVATION/AFFECT": "MOTIVATION_AFFECT",
}

# Conservative mapping for *blank* types when titles strongly imply a type.
# This is intentionally small and auditable (we write a report of every change).
BLANK_TITLE_RULES: list[tuple[str, str]] = [
    # learner/population
    ("JUNIOR DOCTORS", "LEARNER_POPULATION"),
    ("DOCTOR", "LEARNER_POPULATION"),
    ("MEDICAL STUDENTS", "LEARNER_POPULATION"),
    ("RESIDENTS", "LEARNER_POPULATION"),
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
    ("ANALYTIC REASONING", "MECHANISM"),
    ("NON-ANALYTIC", "MECHANISM"),
    ("PATTERN RECOGNITION", "MECHANISM"),
    ("COGNITIVE LOAD", "COGNITIVE_STATE"),
    ("ANXIETY", "MOTIVATION_AFFECT"),
    ("STRESS", "MOTIVATION_AFFECT"),
    ("SELF-EFFICACY", "LEARNER_CONTEXT"),
    ("CONFIDENCE", "LEARNER_CONTEXT"),
    ("MISLEADING", "COGNITIVE_STATE"),
    ("BIAS", "COGNITIVE_STATE"),
    # additional pragmatic fixes seen in subset runs
    ("LEARNER CONTEXT", "LEARNER_CONTEXT"),
    ("INTERFERING FEATURE", "COGNITIVE_STATE"),
    ("MIXED PRACTICE", "INTERVENTION"),
    ("STUDENT-DERIVED REASONING STRATEGIES", "MECHANISM"),
    ("KCR", "ASSESSMENT_MEASURE"),
    ("SPONTANEOUS REASONING CONDITION", "COMPARATOR"),
    ("LARGER EXPERIMENTAL GROUPS", "STUDY_DESIGN"),
    ("BIASED ECG PRESENTATION", "TASK_CASE"),
]


CORRUPT_TITLE_PATTERNS = [
    r"<\|DIFF_MARKER\|>",
    r"\(\"ENTITY\"",
    r"\(\\\"ENTITY\\\"",
]


def _is_corrupt_title(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    return any(bool(re.search(p, s)) for p in CORRUPT_TITLE_PATTERNS)


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
    t = t.strip()
    # Some extractions accidentally wrap enum values in quotes/backticks.
    t = re.sub(r"^[`\"']+|[`\"']+$", "", t).strip()
    t = t.upper()
    if t in ("", "NAN", "NONE"):
        return ""
    t = TYPE_SYNONYMS.get(t, t)
    return t


def _infer_blank_type_from_title(title: str) -> str:
    u = title.strip().upper()
    # Exact placeholders first (avoid mapping "CONTEXT SPECIFICITY" → CONTEXT).
    if u in {"CONTEXT", "MECHANISM", "OUTCOME"}:
        return u
    for needle, t in BLANK_TITLE_RULES:
        if needle == u or (len(needle) >= 8 and needle in u):
            return t
    return ""


def _infer_type_from_title_heuristic(title: str) -> str:
    """
    Heuristic type inference for common realist-review constructs.
    Used only when upstream type is blank/invalid.
    """
    u = (title or "").strip().upper()
    if not u:
        return ""

    # Outcomes (measured endpoints)
    if any(k in u for k in ["DIAGNOSTIC ACCURACY", "DIAGNOSTIC PERFORMANCE", "ERROR RATE", "RETENTION", "SATISFACTION", "RESPONSE TIME"]):
        return "OUTCOME"
    if u in {"CORRECT DIAGNOSIS", "DIFFERENTIAL DIAGNOSIS"}:
        return "OUTCOME"

    # Learner-level contexts (student attributes)
    if any(k in u for k in ["PRIOR KNOWLEDGE", "PRE-EXISTING KNOWLEDGE", "SELF-EFFICACY", "SELF CONFIDENCE", "SELF-CONFIDENCE", "CONFIDENCE", "COPING"]):
        return "LEARNER_CONTEXT"
    if any(k in u for k in ["LOW KNOWLEDGE", "HIGH KNOWLEDGE", "LOW CLINICAL DOMAIN", "HIGH CLINICAL DOMAIN", "MIXED KNOWLEDGE", "INABILITY TO APPLY KNOWLEDGE"]):
        return "LEARNER_CONTEXT"

    # Mechanism reactions (cognitive/affective)
    if any(k in u for k in ["COGNITIVE LOAD", "WORKING MEMORY"]):
        return "COGNITIVE_STATE"
    if any(k in u for k in ["ANXIETY", "STRESS", "FEAR", "FRUSTRATION", "CONFUSION", "PANIC", "RESENTMENT", "PRESSURE", "DISTRESS"]):
        return "MOTIVATION_AFFECT"

    # Mechanism processes / strategies
    if any(k in u for k in ["ILLNESS SCRIPT", "SCRIPT FORMATION", "PATTERN RECOGNITION", "REFLECTION", "SELF-EXPLANATION", "UNDERSTANDING", "INSIGHT", "HYPOTHESIS TESTING", "FEATURE ANALYSIS"]):
        return "MECHANISM"
    if "REASONING" in u and not any(k in u for k in ["SEMINAR", "WORKSHOP", "TRAINING", "PROGRAM", "COURSE", "SESSION"]):
        return "MECHANISM"

    # Intervention resources (instructional methods)
    if any(
        k in u
        for k in [
            "SIMULATION",
            "SIMULATED PATIENT",
            "VIRTUAL PATIENT",
            "WORKED EXAMPLE",
            "FEEDBACK",
            "PROMPT",
            "INSTRUCTION",
            "SCAFFOLD",
            "CASE-BASED",
            "TEST-ENHANCED",
            "RETRIEVAL PRACTICE",
        ]
    ):
        return "INTERVENTION"

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
    entities["title"] = entities.get("title", "").fillna("").astype(str)

    dropped_entities: list[str] = []
    corrupt_mask = entities["title"].map(_is_corrupt_title)
    if bool(corrupt_mask.any()):
        dropped_entities = entities.loc[corrupt_mask, "title"].tolist()
        entities = entities.loc[~corrupt_mask].copy()

    entities["type_norm"] = entities.get("type", "").map(_norm_type)

    # Fix a common realist-ontology drift: "reasoning" strategies are mechanisms, not interventions.
    # Keep true teaching activities (seminar/training/workshop/etc.) as interventions.
    ttitle = entities["title"].fillna("").astype(str)
    is_reasoning = ttitle.str.contains(r"\bREASONING\b", case=False, regex=True)
    is_teaching_activity = ttitle.str.contains(r"\b(?:SEMINAR|WORKSHOP|TRAINING|PROGRAM|COURSE|SESSION)\b", case=False, regex=True)
    drift_mask = (entities["type_norm"] == "INTERVENTION") & is_reasoning & (~is_teaching_activity)
    if bool(drift_mask.any()):
        entities.loc[drift_mask, "type_norm"] = "MECHANISM"

    blank_before = int((entities["type_norm"] == "").sum())

    # Capture invalid non-blank types so we can expand TYPE_SYNONYMS / ontology iteratively.
    invalid_nonblank_mask = (entities["type_norm"] != "") & (~entities["type_norm"].isin(ALLOWED_TYPES))
    invalid_types_seen = sorted(set(entities.loc[invalid_nonblank_mask, "type_norm"].astype(str).tolist()))

    inferred: list[tuple[int, str, str]] = []
    for i, row in entities[entities["type_norm"] == ""].iterrows():
        title = str(row.get("title", "") or "")
        new_t = _infer_blank_type_from_title(title) or _infer_type_from_title_heuristic(title)
        if new_t:
            inferred.append((int(i), title, new_t))
            entities.at[i, "type_norm"] = new_t

    # Keep anything still invalid as blank; we will report it.
    entities["type_norm"] = entities["type_norm"].where(entities["type_norm"].isin(ALLOWED_TYPES), "")
    blank_after = int((entities["type_norm"] == "").sum())

    dropped_unknown_titles: list[str] = []
    unknown_mask = (entities["type_norm"] == "")
    if bool(unknown_mask.any()):
        dropped_unknown_titles = entities.loc[unknown_mask, "title"].astype(str).tolist()
        entities = entities.loc[~unknown_mask].copy()

    # After dropping unknowns, the normalized KG has no blank types by construction.
    blank_after_normalized = int((entities["type_norm"] == "").sum())

    # Overwrite `type` with normalized version, but keep original for audit.
    entities["type_original"] = entities.get("type", "")
    entities["type"] = entities["type_norm"]
    entities = entities.drop(columns=["type_norm"])

    # --- Relationships normalization ---
    etype = dict(zip(entities["title"], entities["type"]))
    rels = rels_in_df.copy()
    if dropped_entities:
        drop_set = set(dropped_entities)
        rels = rels[~rels["source"].isin(drop_set) & ~rels["target"].isin(drop_set)].copy()

    # Drop relationships referencing unknown-typed entities removed from normalized KG.
    if dropped_unknown_titles:
        drop_set2 = set(dropped_unknown_titles)
        rels = rels[~rels["source"].isin(drop_set2) & ~rels["target"].isin(drop_set2)].copy()
    rels["source_type"] = rels.get("source", "").map(etype).fillna("")
    rels["target_type"] = rels.get("target", "").map(etype).fillna("")
    rels["source_family"] = rels["source_type"].map(_to_family).fillna("")
    rels["target_family"] = rels["target_type"].map(_to_family).fillna("")

    # Drop ASSESSMENT_MEASURE edges from the CMOC-normalized graph to reduce
    # measurement/logistics edges that inflate OUTCOME-as-source artifacts.
    dropped_rels_measure = 0
    if "ASSESSMENT_MEASURE" in ALLOWED_TYPES:
        m_mask = (rels["source_type"] == "ASSESSMENT_MEASURE") | (rels["target_type"] == "ASSESSMENT_MEASURE")
        dropped_rels_measure = int(m_mask.sum())
        if dropped_rels_measure:
            rels = rels.loc[~m_mask].copy()

    outcome_src_before = _outcome_as_source_count(rels)

    rels["was_flipped"] = False
    rels["is_non_cmoc"] = False

    # Flip when the direction is not CMOC-family but the reverse is.
    pair = list(zip(rels["source_family"], rels["target_family"]))
    pair_rev = list(zip(rels["target_family"], rels["source_family"]))
    pair_ok = pd.Series(pair, index=rels.index).isin(CMOC_FAMILY)
    pair_rev_ok = pd.Series(pair_rev, index=rels.index).isin(CMOC_FAMILY)
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
    non_cmoc = ~pd.Series(pair2, index=rels.index).isin(CMOC_FAMILY) & (rels["source_family"] != "") & (rels["target_family"] != "")
    non_cmoc_count = int(non_cmoc.sum())
    if non_cmoc_count:
        rels.loc[non_cmoc, "description"] = "[NON_CMOC] " + rels.loc[non_cmoc, "description"].astype(str)
        rels.loc[non_cmoc, "is_non_cmoc"] = True

    # Realist simplification: in CMOC graphs, outcomes should be sinks.
    # Drop remaining OUTCOME-as-source edges from the normalized output (they are typically measurement/logistics links).
    dropped_outcome_source = int((rels["source_family"] == "OUTCOME").sum())
    if dropped_outcome_source:
        rels = rels.loc[rels["source_family"] != "OUTCOME"].copy()

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
    if dropped_rels_measure:
        lines.append(f"- dropped relationships with ASSESSMENT_MEASURE: {dropped_rels_measure}")
    if dropped_outcome_source:
        lines.append(f"- dropped remaining OUTCOME-as-source edges: {dropped_outcome_source}")
    lines.append(f"- blank entity types (raw→post-inference): {blank_before} → {blank_after}")
    lines.append(f"- blank entity types (normalized KG): {blank_after_normalized}")
    if invalid_types_seen:
        lines.append(f"- invalid non-blank types observed (blanked unless mapped): {', '.join(invalid_types_seen[:15])}" + (" ..." if len(invalid_types_seen) > 15 else ""))
    if dropped_unknown_titles:
        lines.append(f"- dropped unknown-typed entities from normalized KG: {len(dropped_unknown_titles)}")
    lines.append(f"- OUTCOME-as-source edges (family): {outcome_src_before} → {outcome_src_after}")
    lines.append(f"- flipped for CMOC-family: {flipped_count}")
    lines.append(f"- remaining non-CMOC edges (flagged): {non_cmoc_count}")
    lines.append("")
    if dropped_entities:
        lines.append("### Dropped corrupt entities (heuristic)\n")
        lines.append(f"- dropped entities: **{len(dropped_entities)}**")
        for t in dropped_entities[:30]:
            lines.append(f"- `{t}`")
        if len(dropped_entities) > 30:
            lines.append(f"- ... and {len(dropped_entities) - 30} more")
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
    if dropped_unknown_titles:
        lines.append("### Dropped unknown-typed entities (still present in raw extraction; fix via prompt/typing iteration)\n")
        for t in dropped_unknown_titles[:60]:
            lines.append(f"- `{t}`")
        if len(dropped_unknown_titles) > 60:
            lines.append(f"- ... and {len(dropped_unknown_titles) - 60} more")
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

