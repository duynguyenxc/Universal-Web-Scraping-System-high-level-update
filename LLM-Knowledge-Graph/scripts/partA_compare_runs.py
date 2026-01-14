"""
Compare two GraphRAG runs to measure improvement.
Usage: python scripts/partA_compare_runs.py --before <output_dir1> --after <output_dir2>
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _get_quality_metrics(out_dir: Path) -> dict:
    """Extract quality metrics from a run."""
    metrics = {}
    
    # Entities
    ent_p = out_dir / "entities.parquet"
    if ent_p.exists():
        ent = pd.read_parquet(ent_p)
        ent["type"] = ent.get("type", "").fillna("").astype(str)
        metrics["entities_total"] = len(ent)
        metrics["entities_blank_type"] = int((ent["type"].str.strip() == "").sum())
        metrics["entities_corrupt_title"] = 0  # Would need to check, but skip for now
    
    # Relationships
    rel_p = out_dir / "relationships.parquet"
    if rel_p.exists():
        rel = pd.read_parquet(rel_p)
        metrics["relationships_total"] = len(rel)
        
        # CMO-ish edges
        if ent_p.exists():
            emap = ent.set_index("title")["type"].to_dict()
            rel["source_type"] = rel["source"].map(emap).fillna("")
            rel["target_type"] = rel["target"].map(emap).fillna("")
            want = {
                ("INTERVENTION", "MECHANISM"),
                ("INTERVENTION", "OUTCOME"),
                ("COMPARATOR", "OUTCOME"),
                ("LEARNER_CONTEXT", "MECHANISM"),
                ("LEARNER_CONTEXT", "OUTCOME"),
                ("COGNITIVE_STATE", "MECHANISM"),
                ("COGNITIVE_STATE", "OUTCOME"),
                ("MOTIVATION_AFFECT", "MECHANISM"),
                ("MOTIVATION_AFFECT", "OUTCOME"),
                ("SETTING_CONTEXT", "MECHANISM"),
                ("SETTING_CONTEXT", "OUTCOME"),
                ("TASK_CASE", "MECHANISM"),
                ("TASK_CASE", "OUTCOME"),
            }
            pairs = list(zip(rel["source_type"], rel["target_type"]))
            cmo_edges = sum(1 for p in pairs if p in want)
            metrics["relationships_cmo_edges"] = cmo_edges
            metrics["relationships_cmo_pct"] = (cmo_edges / len(rel) * 100.0) if len(rel) else 0.0
    
    # Claims
    claims_p = out_dir / "claims_fixed.parquet"
    if not claims_p.exists():
        claims_p = out_dir / "covariates.parquet"
    if claims_p.exists():
        claims = pd.read_parquet(claims_p)
        metrics["claims_total"] = len(claims)
        if "source_text" in claims.columns:
            has_page = claims["source_text"].astype(str).str.contains(r"\[PAGE \d+\]", regex=True).sum()
            metrics["claims_with_page"] = int(has_page)
            metrics["claims_page_pct"] = (has_page / len(claims) * 100.0) if len(claims) else 0.0
        if "type" in claims.columns:
            type_counts = claims["type"].value_counts()
            metrics["claims_outcome_measurement"] = int(type_counts.get("OUTCOME_MEASUREMENT", 0))
            metrics["claims_mechanism_explanation"] = int(type_counts.get("MECHANISM_EXPLANATION", 0))
            metrics["claims_context_moderator"] = int(type_counts.get("CONTEXT_MODERATOR", 0))
            metrics["claims_intervention_effect"] = int(type_counts.get("INTERVENTION_EFFECT", 0))
    
    # Communities
    comm_p = out_dir / "communities.parquet"
    if comm_p.exists():
        comm = pd.read_parquet(comm_p)
        metrics["communities_total"] = len(comm)
        metrics["communities_avg_size"] = float(comm["size"].mean()) if len(comm) else 0.0
    
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser(description="Part A: compare two GraphRAG runs to measure improvement.")
    ap.add_argument("--before", type=Path, required=True, help="Before run output directory")
    ap.add_argument("--after", type=Path, required=True, help="After run output directory")
    args = ap.parse_args()

    before = args.before
    after = args.after
    
    if not before.exists():
        print(f"ERROR: Before directory not found: {before}")
        return 1
    if not after.exists():
        print(f"ERROR: After directory not found: {after}")
        return 1

    m_before = _get_quality_metrics(before)
    m_after = _get_quality_metrics(after)

    print("=" * 80)
    print("COMPARISON: BEFORE vs AFTER")
    print("=" * 80)
    print(f"\nBefore: {before}")
    print(f"After:  {after}\n")

    # Entities
    print("[ENTITIES]")
    if "entities_total" in m_before and "entities_total" in m_after:
        print(f"  Total:        {m_before.get('entities_total', 0):4d} → {m_after.get('entities_total', 0):4d}")
    if "entities_blank_type" in m_before and "entities_blank_type" in m_after:
        b_blank = m_before.get("entities_blank_type", 0)
        a_blank = m_after.get("entities_blank_type", 0)
        diff = a_blank - b_blank
        status = "✅ IMPROVED" if diff < 0 else "❌ WORSE" if diff > 0 else "➡️  SAME"
        print(f"  Blank types:  {b_blank:4d} → {a_blank:4d} ({diff:+d}) {status}")
    print()

    # Relationships
    print("[RELATIONSHIPS]")
    if "relationships_total" in m_before and "relationships_total" in m_after:
        print(f"  Total:        {m_before.get('relationships_total', 0):4d} → {m_after.get('relationships_total', 0):4d}")
    if "relationships_cmo_pct" in m_before and "relationships_cmo_pct" in m_after:
        b_pct = m_before.get("relationships_cmo_pct", 0.0)
        a_pct = m_after.get("relationships_cmo_pct", 0.0)
        diff = a_pct - b_pct
        status = "✅ IMPROVED" if diff > 0 else "❌ WORSE" if diff < 0 else "➡️  SAME"
        print(f"  CMO-edge %:   {b_pct:5.2f}% → {a_pct:5.2f}% ({diff:+.2f}%) {status}")
    print()

    # Claims
    print("[CLAIMS]")
    if "claims_total" in m_before and "claims_total" in m_after:
        print(f"  Total:        {m_before.get('claims_total', 0):4d} → {m_after.get('claims_total', 0):4d}")
    if "claims_page_pct" in m_before and "claims_page_pct" in m_after:
        b_pct = m_before.get("claims_page_pct", 0.0)
        a_pct = m_after.get("claims_page_pct", 0.0)
        diff = a_pct - b_pct
        status = "✅ IMPROVED" if diff > 0 else "❌ WORSE" if diff < 0 else "➡️  SAME"
        print(f"  [PAGE] %:     {b_pct:5.2f}% → {a_pct:5.2f}% ({diff:+.2f}%) {status}")
    
    # Claim type distribution
    if "claims_outcome_measurement" in m_before:
        print(f"\n  Claim type distribution:")
        for ctype in ["outcome_measurement", "mechanism_explanation", "context_moderator", "intervention_effect"]:
            b_val = m_before.get(f"claims_{ctype}", 0)
            a_val = m_after.get(f"claims_{ctype}", 0)
            if b_val > 0 or a_val > 0:
                diff = a_val - b_val
                print(f"    {ctype.replace('_', ' ').title():25s}: {b_val:4d} → {a_val:4d} ({diff:+d})")
    print()

    # Communities
    print("[COMMUNITIES]")
    if "communities_total" in m_before and "communities_total" in m_after:
        print(f"  Total:        {m_before.get('communities_total', 0):4d} → {m_after.get('communities_total', 0):4d}")
    if "communities_avg_size" in m_before and "communities_avg_size" in m_after:
        b_size = m_before.get("communities_avg_size", 0.0)
        a_size = m_after.get("communities_avg_size", 0.0)
        print(f"  Avg size:     {b_size:5.2f} → {a_size:5.2f}")
    print()

    # Summary
    print("[SUMMARY]")
    improvements = []
    if "entities_blank_type" in m_before and m_after.get("entities_blank_type", 0) < m_before.get("entities_blank_type", 0):
        improvements.append("Blank types reduced")
    if "relationships_cmo_pct" in m_before and m_after.get("relationships_cmo_pct", 0.0) > m_before.get("relationships_cmo_pct", 0.0):
        improvements.append("CMO-edge % increased")
    if "claims_mechanism_explanation" in m_after and m_after.get("claims_mechanism_explanation", 0) > m_before.get("claims_mechanism_explanation", 0):
        improvements.append("Mechanism explanation claims increased")
    if "claims_context_moderator" in m_after and m_after.get("claims_context_moderator", 0) > m_before.get("claims_context_moderator", 0):
        improvements.append("Context moderator claims increased")
    
    if improvements:
        print("  ✅ Improvements detected:")
        for imp in improvements:
            print(f"     • {imp}")
    else:
        print("  ⚠️  No clear improvements detected (check metrics above)")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
