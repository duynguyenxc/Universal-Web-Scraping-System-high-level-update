"""Quick demo script to apply semantic scoring to existing crawler outputs.

This is only for experimentation, so we do not expose it via the main CLI.
Run, for example:

    python -m scripts.analysis.semantic_crawler_demo \
        --input data/web_crawler_scrapy_olemiss_test.jsonl \
        --output data/web_crawler_semantic_demo_from_olemiss.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.uwss.semantic import compute_semantic_score


def main() -> None:
	parser = argparse.ArgumentParser(description="Apply semantic scoring to existing web crawler JSONL output.")
	parser.add_argument(
		"--input",
		type=str,
		required=True,
		help="Input JSONL file from web-crawler-scrapy-discover.",
	)
	parser.add_argument(
		"--output",
		type=str,
		required=True,
		help="Output JSONL file with added semantic_score field.",
	)
	parser.add_argument(
		"--topic",
		type=str,
		default="corrosion and long-term durability of reinforced concrete structures",
		help="Topic description used for semantic similarity.",
	)
	parser.add_argument(
		"--semantic-model",
		type=str,
		default="sentence-transformers/all-MiniLM-L6-v2",
		help="Sentence-transformers model name.",
	)
	parser.add_argument(
		"--threshold",
		type=float,
		default=0.0,
		help="Optional minimum semantic score to keep an item (0 keeps all).",
	)
	args = parser.parse_args()

	in_path = Path(args.input)
	out_path = Path(args.output)
	if not in_path.exists():
		raise SystemExit(f"Input file not found: {in_path}")

	out_path.parent.mkdir(parents=True, exist_ok=True)

	kept = 0
	total = 0
	with in_path.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
		for line in fin:
			line = line.strip()
			if not line:
				continue
			total += 1
			item = json.loads(line)
			parts = []
			for key in ("title", "abstract", "content"):
				val = item.get(key)
				if isinstance(val, str) and val.strip():
					parts.append(val.strip())
			text = " ".join(parts)
			score = compute_semantic_score(text, args.topic, model_name=args.semantic_model)
			item["semantic_score"] = score

			if score >= args.threshold:
				kept += 1
				fout.write(json.dumps(item, ensure_ascii=False) + "\n")

	print(
		f"Semantic scoring done. Total items: {total}, written: {kept}, "
		f"threshold: {args.threshold}, output: {out_path}"
	)


if __name__ == "__main__":
	main()







