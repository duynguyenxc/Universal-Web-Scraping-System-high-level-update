from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def _count(cur: sqlite3.Cursor, sql: str) -> int:
	return int(cur.execute(sql).fetchone()[0])


def main() -> int:
	ap = argparse.ArgumentParser(description="UWSS: quick SQLite stats (duplicates + screening counts)")
	ap.add_argument("--db", default=str(Path("data") / "uwss.sqlite"), help="Path to uwss.sqlite")
	args = ap.parse_args()

	db = Path(args.db)
	if not db.exists():
		raise SystemExit(f"DB not found: {db}")

	con = sqlite3.connect(str(db))
	try:
		cur = con.cursor()
		stats = {
			"db": str(db).replace("\\", "/"),
			"total_documents": _count(cur, "select count(*) from documents"),
			"doi_nonempty": _count(cur, "select count(*) from documents where doi is not null and trim(doi) != ''"),
			"doi_distinct": _count(cur, "select count(distinct doi) from documents where doi is not null and trim(doi) != ''"),
			"doi_duplicate_groups": _count(
				cur,
				"select count(*) from (select doi from documents where doi is not null and trim(doi) != '' group by doi having count(*) > 1)",
			),
			"title_nonempty": _count(cur, "select count(*) from documents where title is not null and trim(title) != ''"),
			"title_distinct": _count(cur, "select count(distinct title) from documents where title is not null and trim(title) != ''"),
			"title_duplicate_groups": _count(
				cur,
				"select count(*) from (select title from documents where title is not null and trim(title) != '' group by title having count(*) > 1)",
			),
			"url_hash_nonempty": _count(cur, "select count(*) from documents where url_hash_sha1 is not null and trim(url_hash_sha1) != ''"),
			"url_hash_distinct": _count(cur, "select count(distinct url_hash_sha1) from documents where url_hash_sha1 is not null and trim(url_hash_sha1) != ''"),
			"url_hash_duplicate_groups": _count(
				cur,
				"select count(*) from (select url_hash_sha1 from documents where url_hash_sha1 is not null and trim(url_hash_sha1) != '' group by url_hash_sha1 having count(*) > 1)",
			),
			"damage_v4_2_profiled": _count(cur, "select count(*) from documents where screening_profile = 'damage_v4_2'"),
			"damage_v4_2_qualified": _count(
				cur, "select count(*) from documents where screening_profile = 'damage_v4_2' and screening_qualified = 1"
			),
			"damage_v4_2_unqualified": _count(
				cur, "select count(*) from documents where screening_profile = 'damage_v4_2' and screening_qualified = 0"
			),
		}
		print(json.dumps(stats, ensure_ascii=False, indent=2))
		return 0
	finally:
		con.close()


if __name__ == "__main__":
	raise SystemExit(main())

