from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    pd.set_option("display.max_colwidth", 120)

    ap = argparse.ArgumentParser(description="Quick inspection of GraphRAG communities.parquet")
    ap.add_argument(
        "--communities",
        default=str(Path("graphrag-project") / "output" / "communities.parquet"),
        help="Path to communities.parquet (default: graphrag-project/output/communities.parquet)",
    )
    ap.add_argument("--n", type=int, default=10, help="Number of rows to show.")
    args = ap.parse_args()

    p = Path(args.communities)
    df = pd.read_parquet(p)
    print(f"Found {len(df)} communities.")
    print("\nColumns:", df.columns.tolist())
    print("\nSample Communities:")
    print(df.head(args.n).to_markdown(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
