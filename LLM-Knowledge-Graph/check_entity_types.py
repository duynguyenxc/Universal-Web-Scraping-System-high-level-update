from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser(description="Show distribution of entity types from GraphRAG entities.parquet")
    ap.add_argument(
        "--entities",
        default=str(Path("graphrag-project") / "output" / "entities.parquet"),
        help="Path to entities.parquet (default: graphrag-project/output/entities.parquet)",
    )
    ap.add_argument("--n", type=int, default=20, help="Number of rows to show.")
    args = ap.parse_args()

    df = pd.read_parquet(Path(args.entities))
    if "type" in df.columns:
        print("Top entity types:")
        print(df["type"].value_counts().head(30).to_string())
    else:
        print("No 'type' column found. Columns:", df.columns.tolist())
    cols = [c for c in ["title", "type"] if c in df.columns]
    if cols:
        print("\nSample rows:")
        print(df[cols].head(args.n).to_markdown(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
