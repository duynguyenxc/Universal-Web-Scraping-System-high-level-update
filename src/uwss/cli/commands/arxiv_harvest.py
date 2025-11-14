from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

import yaml
from rich.console import Console

from ...store import Base
from ...store import create_sqlite_engine, create_engine_from_url
from ...arxiv.harvest_oai import harvest_oai_records

console = Console()


def _get_engine_session(db: Path, db_url: str | None):
	if db_url:
		return create_engine_from_url(db_url)
	return create_sqlite_engine(db)


def _load_config(config_path: Path) -> Dict[str, Any]:
	with config_path.open("r", encoding="utf-8") as f:
		return yaml.safe_load(f) or {}


def register(sub) -> None:
	p = sub.add_parser("arxiv-harvest-oai", help="Harvest arXiv via OAI-PMH ListRecords (official)")
	p.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p.add_argument("--from", dest="from_date", default=None, help="YYYY-MM-DD start date")
	p.add_argument("--until", dest="until_date", default=None, help="YYYY-MM-DD end date")
	p.add_argument("--set", dest="set_spec", default=None, help="Optional arXiv set/category")
	p.add_argument("--max", type=int, default=None, help="Stop after N inserted records")
	p.add_argument("--resume", action="store_true", help="Resume using saved resumptionToken")
	p.add_argument("--log-json", action="store_true")
	p.add_argument("--metrics-out", default=None, help="Optional JSON file to write harvest metrics")
	p.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

	def _cmd(args: argparse.Namespace) -> int:
		data = _load_config(Path(args.config))
		contact_email = data.get("contact_email")
		engine, SessionLocal = _get_engine_session(Path(args.db), getattr(args, "db_url", None))
		Base.metadata.create_all(engine)
		s = SessionLocal()
		try:
			res = harvest_oai_records(
				s,
				contact_email=contact_email,
				from_date=getattr(args, "from_date", None),
				until_date=getattr(args, "until_date", None),
				set_spec=getattr(args, "set_spec", None),
				max_records=getattr(args, "max", None),
				resume=bool(getattr(args, "resume", False)),
				throttle_sec=float(os.getenv("UWSS_THROTTLE_SEC", "1.0")),
			)
		finally:
			s.close()
		console.print(f"[green]arXiv OAI-PMH: inserted={res['inserted']} failed={res['failed']} pages={res['pages']} elapsed={res['elapsed_sec']}s[/green]")
		if getattr(args, "log_json", False):
			try:
				print(json.dumps({"uwss_event": "arxiv_oai_done", **res}, ensure_ascii=False))
			except Exception:
				pass
		if getattr(args, "metrics_out", None):
			try:
				Path(args.metrics_out).parent.mkdir(parents=True, exist_ok=True)
				Path(args.metrics_out).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
				console.print(f"[green]Saved metrics to {args.metrics_out}[/green]")
			except Exception:
				pass
		return 0

	p.set_defaults(func=_cmd)


