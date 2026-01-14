"""
Helper script to explain GraphRAG output in plain language.
Usage: python scripts/partA_explain_output.py --out-dir <output_dir>
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser(description="Part A: explain GraphRAG output in plain language.")
    ap.add_argument("--out-dir", type=Path, default=Path("LLM-Knowledge-Graph/graphrag-project/output_partA_subset5"))
    args = ap.parse_args()

    out = args.out_dir
    if not out.exists():
        print(f"ERROR: Output directory not found: {out}")
        return 1

    import sys
    import io
    # Fix Windows console encoding
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("=" * 80)
    print("GRAPH RAG OUTPUT EXPLAINER")
    print("=" * 80)
    print(f"\nOutput directory: {out}\n")

    # 1. Entities summary
    ent_p = out / "entities.parquet"
    if ent_p.exists():
        ent = pd.read_parquet(ent_p)
        ent["type"] = ent.get("type", "").fillna("").astype(str)
        blank = (ent["type"].str.strip() == "").sum()
        print("[ENTITIES] Khai niem/Doi tuong duoc trich xuat")
        print(f"   - Tổng số: {len(ent)} entities")
        print(f"   - Entities bị thiếu type: {blank} (cần fix nếu > 0)")
        print(f"\n   Top 5 entities quan trọng nhất (theo số mối quan hệ):")
        top = ent.nlargest(5, "degree")[["title", "type", "degree", "frequency"]]
        for _, row in top.iterrows():
            print(f"      • {row['title']} ({row['type']}) - {int(row['degree'])} mối quan hệ, xuất hiện {int(row['frequency'])} lần")
        print()

    # 2. Relationships summary
    rel_p = out / "relationships.parquet"
    if rel_p.exists():
        rel = pd.read_parquet(rel_p)
        print("[RELATIONSHIPS] Moi quan he giua entities")
        print(f"   - Tổng số: {len(rel)} relationships")
        if "weight" in rel.columns:
            w = rel["weight"]
            print(f"   - Weight trung bình: {w.mean():.1f} (min={w.min():.0f}, max={w.max():.0f})")
        print(f"\n   Top 5 relationships mạnh nhất (theo weight):")
        top = rel.nlargest(5, "weight")[["source", "target", "weight"]]
        for _, row in top.iterrows():
            print(f"      • {row['source']} → {row['target']} (weight={int(row['weight'])})")
        print()

    # 3. Communities summary
    comm_p = out / "communities.parquet"
    if comm_p.exists():
        comm = pd.read_parquet(comm_p)
        print("[COMMUNITIES] Nhom entities duoc gom lai")
        print(f"   - Tổng số: {len(comm)} communities")
        print(f"   - Kích thước trung bình: {comm['size'].mean():.1f} entities/community")
        print(f"\n   Danh sách communities:")
        for _, row in comm.iterrows():
            title = row.get("title", f"Community {int(row['community'])}")
            print(f"      • Community {int(row['community'])}: {title} (size={int(row['size'])})")
        print()

    # 4. Claims summary
    claims_p = out / "claims_fixed.parquet"
    if not claims_p.exists():
        claims_p = out / "covariates.parquet"
    if claims_p.exists():
        claims = pd.read_parquet(claims_p)
        print("[CLAIMS] Menh de evidence-grounded")
        print(f"   - Tổng số: {len(claims)} claims")
        if "source_text" in claims.columns:
            has_page = claims["source_text"].astype(str).str.contains(r"\[PAGE \d+\]", regex=True).sum()
            print(f"   - Claims có [PAGE N] marker: {has_page}/{len(claims)} ({has_page/len(claims)*100:.1f}%)")
        if "type" in claims.columns:
            print(f"\n   Phân bố claim types:")
            type_counts = claims["type"].value_counts()
            for ctype, count in type_counts.head(5).items():
                print(f"      • {ctype}: {count}")
        print()

    # 5. Quality gates summary
    qg_p = out / "human_readable" / "quality_gates.md"
    if qg_p.exists():
        print("[QUALITY GATES] Chat luong output")
        content = qg_p.read_text(encoding="utf-8")
        # Extract key metrics
        if "blank type count:" in content:
            import re
            blank_match = re.search(r"blank type count: \*\*(\d+)\*\*", content)
            if blank_match:
                blank_count = int(blank_match.group(1))
                status = "[FAIL]" if blank_count > 0 else "[PASS]"
                print(f"   - Blank types: {blank_count} {status}")
        if "CMO-ish edges:" in content:
            cmo_match = re.search(r"CMO-ish edges: \*\*(\d+) / (\d+) = ([\d.]+)%\*\*", content)
            if cmo_match:
                cmo_pct = float(cmo_match.group(3))
                status = "[PASS]" if cmo_pct >= 15.0 else "[LOW]"
                print(f"   - CMO-edge %: {cmo_pct:.2f}% {status}")
        print()

    # 6. Recommendations
    print("[KHUYEN NGHI]")
    print("   1. Đọc file QUAN TRỌNG NHẤT: human_readable/community_reports.md")
    print("      → Đây là báo cáo tự động về các concept/principle chính")
    print("   2. Nếu quality gates fail → fix prompt và rerun")
    print("   3. So sánh community reports với Richmond et al. (2020) để verify")
    print("   4. Xem chi tiết: artifacts/partA/HOW_TO_READ_OUTPUT.md")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
