from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_FLAG_PATTERNS = [
	# material enhancement / additives / fibers
	r"\bnano\b",
	r"\bfiber\b",
	r"\bfibres\b",
	r"silica fume",
	r"fly ash",
	r"\bgeopolymer\b",
	r"\buhpc\b",
	r"ultra-?high performance",
	r"recycled aggregate",
	# mechanical-only proxies
	r"compressive strength",
	r"flexural strength",
	r"split(ting)? tensile",
	r"\bupv\b",
	r"\brcpt\b",
	r"rapid chloride permeability",
	r"\bpermeability\b",
	# transport/simulation proxies
	r"diffusion coefficient",
	r"chloride diffusion",
	r"finite element",
	r"numerical simulation",
]


def _safe_json_loads(x: Any) -> Dict[str, Any] | None:
	if not x:
		return None
	if isinstance(x, dict):
		return x
	if isinstance(x, str):
		try:
			return json.loads(x)
		except Exception:
			return None
	return None


def main() -> int:
	ap = argparse.ArgumentParser(description="Evaluate UWSS screening output quality quickly.")
	ap.add_argument("--in", dest="in_path", required=True, help="Input JSONL export file")
	ap.add_argument("--max-examples", type=int, default=12)
	ap.add_argument("--pattern", action="append", default=None, help="Add a regex pattern (repeatable)")
	args = ap.parse_args()

	p = Path(args.in_path)
	if not p.exists():
		raise SystemExit(f"Not found: {p}")

	pats = [re.compile(s, re.IGNORECASE) for s in (DEFAULT_FLAG_PATTERNS + (args.pattern or []))]

	rows: List[Dict[str, Any]] = []
	with p.open("r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			rows.append(json.loads(line))

	neg_cats = Counter()
	pos_signals = Counter()
	flagged: List[Dict[str, Any]] = []
	missing_meta = 0

	for r in rows:
		meta = _safe_json_loads(r.get("screening_meta"))
		if meta is None:
			missing_meta += 1
		else:
			for c in meta.get("negative_categories_matched") or []:
				neg_cats[str(c)] += 1
			ph = meta.get("positive_hits") or {}
			if isinstance(ph, dict):
				for k, v in ph.items():
					try:
						if int(v) > 0:
							pos_signals[str(k)] += 1
					except Exception:
						pass

		txt = (r.get("title") or "") + "\n" + (r.get("abstract") or "")
		if any(pat.search(txt) for pat in pats):
			flagged.append(
				{
					"id": r.get("id"),
					"score": r.get("relevance_score"),
					"qualified": r.get("screening_qualified"),
					"title": (r.get("title") or "")[:180],
				}
			)

	out = {
		"file": str(p).replace("\\", "/"),
		"rows": len(rows),
		"qualified_true": sum(1 for r in rows if r.get("screening_qualified") is True),
		"qualified_false": sum(1 for r in rows if r.get("screening_qualified") is False),
		"missing_meta": missing_meta,
		"negative_categories_matched_counts": neg_cats.most_common(20),
		"positive_signal_doc_counts": pos_signals.most_common(20),
		"flagged_count": len(flagged),
		"flagged_examples": flagged[: max(0, int(args.max_examples))],
	}
	print(json.dumps(out, ensure_ascii=False, indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

