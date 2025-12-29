from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser(description="Quick inspection of GraphRAG entities.parquet")
    ap.add_argument(
        "--entities",
        default=str(Path("graphrag-project") / "output" / "entities.parquet"),
        help="Path to entities.parquet (default: graphrag-project/output/entities.parquet)",
    )
    ap.add_argument("--n", type=int, default=10, help="Number of rows to show.")
    args = ap.parse_args()

    p = Path(args.entities)
    df = pd.read_parquet(p)
    print("Found entities:", len(df))
    cols = [c for c in ["title", "type", "description"] if c in df.columns]
    print(f"\nColumns: {df.columns.tolist()}")
    if cols:
        print("\nSample Entities:")
        print(df[cols].head(args.n).to_markdown(index=False))
    else:
        print(df.head(args.n).to_markdown(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
