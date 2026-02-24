from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
	ap = argparse.ArgumentParser(description="Split a UWSS export JSONL into included/review by screening_qualified.")
	ap.add_argument("--in", dest="in_path", required=True, help="Input JSONL file")
	ap.add_argument("--included-out", required=True, help="Output JSONL for screening_qualified=true")
	ap.add_argument("--review-out", required=True, help="Output JSONL for screening_qualified!=true")
	args = ap.parse_args()

	in_p = Path(args.in_path)
	if not in_p.exists():
		raise SystemExit(f"Not found: {in_p}")

	inc_p = Path(args.included_out)
	rev_p = Path(args.review_out)
	inc_p.parent.mkdir(parents=True, exist_ok=True)
	rev_p.parent.mkdir(parents=True, exist_ok=True)

	inc_n = 0
	rev_n = 0
	with in_p.open("r", encoding="utf-8") as fin, inc_p.open("w", encoding="utf-8") as f_inc, rev_p.open(
		"w", encoding="utf-8"
	) as f_rev:
		for line in fin:
			line = line.strip()
			if not line:
				continue
			obj = json.loads(line)
			if obj.get("screening_qualified") is True:
				f_inc.write(json.dumps(obj, ensure_ascii=False) + "\n")
				inc_n += 1
			else:
				f_rev.write(json.dumps(obj, ensure_ascii=False) + "\n")
				rev_n += 1

	print(json.dumps({"input": str(in_p), "included": inc_n, "review": rev_n}, ensure_ascii=False))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

