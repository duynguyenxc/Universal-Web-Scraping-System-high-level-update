from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

import yaml
from rich.console import Console

from ...store import Base
from ...store import create_sqlite_engine, create_engine_from_url
from ...fetch.arxiv_pdf import fetch_arxiv_pdfs

console = Console()


def _get_engine_session(db: Path, db_url: str | None):
	if db_url:
		return create_engine_from_url(db_url)
	return create_sqlite_engine(db)


def _load_config(config_path: Path) -> Dict[str, Any]:
	with config_path.open("r", encoding="utf-8") as f:
		return yaml.safe_load(f) or {}


def register(sub) -> None:
	p = sub.add_parser("arxiv-fetch-pdf", help="Download canonical arXiv PDFs with throttle/backoff")
	p.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p.add_argument("--outdir", default=str(Path("data") / "files"))
	p.add_argument("--limit", type=int, default=50)
	p.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p.add_argument("--throttle-sec", type=float, default=None)
	p.add_argument("--jitter-sec", type=float, default=None)
	p.add_argument("--max-mb", type=float, default=60.0, help="Max PDF size in MB (HEAD check)")
	p.add_argument("--dry-run", action="store_true", help="HEAD only, do not download")
	p.add_argument("--since-days", type=int, default=None, help="Only consider docs older than N days or missing local_path")
	p.add_argument("--ids-file", default=None, help="Optional file with Document IDs (one per line) to restrict fetching")
	p.add_argument("--log-json", action="store_true")
	p.add_argument("--metrics-out", default=None)
	p.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

	def _cmd(args: argparse.Namespace) -> int:
		data = _load_config(Path(args.config))
		contact_email = data.get("contact_email")
		engine, SessionLocal = _get_engine_session(Path(args.db), getattr(args, "db_url", None))
		Base.metadata.create_all(engine)
		s = SessionLocal()
		try:
			throttle = args.throttle_sec if args.throttle_sec is not None else float(os.getenv("UWSS_THROTTLE_SEC", "1.0"))
			jitter = args.jitter_sec if args.jitter_sec is not None else float(os.getenv("UWSS_JITTER_SEC", "0.5"))
			ids = None
			if getattr(args, "ids_file", None):
				try:
					ids = set(int(x.strip()) for x in Path(args.ids_file).read_text(encoding="utf-8").splitlines() if x.strip())
				except Exception:
					ids = None
			res = fetch_arxiv_pdfs(
				s,
				Path(args.outdir),
				limit=args.limit,
				contact_email=contact_email,
				throttle_sec=throttle,
				jitter_sec=jitter,
				max_mb=float(getattr(args, "max_mb", 60.0)),
				dry_run=bool(getattr(args, "dry_run", False)),
				since_days=getattr(args, "since_days", None),
				ids=ids,
			)
		finally:
			s.close()
		console.print(f"[green]arXiv PDF: downloaded={res['downloaded']} failed={res['failed']} attempted={res['attempted']}[/green]")
		if getattr(args, "log_json", False):
			try:
				print(json.dumps({"uwss_event": "arxiv_pdf_done", **res}, ensure_ascii=False))
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


