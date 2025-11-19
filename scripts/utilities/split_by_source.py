"""Split a combined JSONL file into per-source JSONL files.

Usage:
  python scripts/utilities/split_by_source.py \
    data/full_test_20251119/all_sources.jsonl \
    data/full_test_20251119 \
    --limit-per-source 100
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> int:
	parser = argparse.ArgumentParser(description="Split combined JSONL by `source` field.")
	parser.add_argument("input", help="Path to combined JSONL file (e.g., all_sources.jsonl)")
	parser.add_argument("out_dir", help="Output directory for per-source JSONL files")
	parser.add_argument(
		"--limit-per-source",
		type=int,
		default=100,
		help="Maximum records to write per source (default: 100)",
	)
	args = parser.parse_args()

	in_path = Path(args.input)
	if not in_path.exists():
		raise SystemExit(f"Input file not found: {in_path}")

	out_dir = Path(args.out_dir)
	out_dir.mkdir(parents=True, exist_ok=True)

	by_source: dict[str, list[dict]] = defaultdict(list)

	with in_path.open("r", encoding="utf-8") as f:
		for line in f:
			if not line.strip():
				continue
			try:
				obj = json.loads(line)
			except json.JSONDecodeError:
				continue
			src = (obj.get("source") or "unknown").replace("/", "_")
			by_source[src].append(obj)

	for src, items in by_source.items():
		limit = max(0, int(args.limit_per_source))
		if limit:
			slice_items = items[:limit]
		else:
			slice_items = items
		out_path = out_dir / f"full_test_{src}.jsonl"
		with out_path.open("w", encoding="utf-8") as wf:
			for obj in slice_items:
				wf.write(json.dumps(obj, ensure_ascii=False) + "\n")
		print(f"Wrote {len(slice_items)} records for source={src} to {out_path}")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())


