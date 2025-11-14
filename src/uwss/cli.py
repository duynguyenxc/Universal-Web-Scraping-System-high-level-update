"""UWSS CLI: orchestrates discovery, scoring, fetching, extraction, and export.

Usage examples:
- Discover via Semantic Scholar, then score, fetch, extract, export.
- Swap databases by providing --db-url (Postgres) or default to SQLite path.

Design principles:
- Single source of truth: database first (Postgres recommended for production).
- Idempotent commands: safe to rerun; dedupe and checkpointing avoid rework.
- Observability: JSON logs on demand; simple, copy-pastable commands.
"""
import argparse
import sys
from pathlib import Path
from typing import Any, Dict
import os
import time
import json

import yaml
from rich.console import Console
from rich.table import Table


console = Console()


def load_config(config_path: Path) -> Dict[str, Any]:
	if not config_path.exists():
		raise FileNotFoundError(f"Config not found: {config_path}")
	with config_path.open("r", encoding="utf-8") as f:
		data = yaml.safe_load(f) or {}
	return data
# Safe clip helper for varchar columns
def _clip(text: Any, max_len: int) -> Any:
	try:
		s = str(text)
		return s[:max_len]
	except Exception:
		return text


def validate_config(data: Dict[str, Any]) -> None:
	required_keys = [
		"domain_keywords",
		"domain_sources",
		"max_depth",
		"file_types",
	]
	missing = [k for k in required_keys if k not in data]
	if missing:
		raise ValueError(f"Missing required config keys: {', '.join(missing)}")
	if not isinstance(data["domain_keywords"], list) or not data["domain_keywords"]:
		raise ValueError("domain_keywords must be a non-empty list")
	if not isinstance(data["domain_sources"], list) or not data["domain_sources"]:
		raise ValueError("domain_sources must be a non-empty list")
	if not isinstance(data["file_types"], list) or not data["file_types"]:
		raise ValueError("file_types must be a non-empty list")


# Structured logging helper
def _log_json(enabled: bool, event: str, **kwargs: Any) -> None:
	if not enabled:
		return
	try:
		payload = {"uwss_event": event}
		payload.update(kwargs)
		print(json.dumps(payload, ensure_ascii=False))
	except Exception:
		pass


# Helper: choose DB engine from --db-url or fallback to SQLite path

def _get_engine_session(args, sqlite_path: Path):
	from .store import create_sqlite_engine, create_engine_from_url
	if getattr(args, "db_url", None):
		return create_engine_from_url(args.db_url)
	return create_sqlite_engine(sqlite_path)


def cmd_config_validate(args: argparse.Namespace) -> int:
	config_path = Path(args.config)
	try:
		data = load_config(config_path)
		validate_config(data)
		# Pretty print a brief summary
		table = Table(title="UWSS Config Summary")
		table.add_column("Field")
		table.add_column("Value")
		table.add_row("config_path", str(config_path))
		table.add_row("#domain_keywords", str(len(data.get("domain_keywords", []))))
		table.add_row("#domain_sources", str(len(data.get("domain_sources", []))))
		table.add_row("max_depth", str(data.get("max_depth", "")))
		table.add_row("file_types", ", ".join(map(str, data.get("file_types", []))))
		if "year_filter" in data:
			table.add_row("year_filter", str(data["year_filter"]))
		console.print(table)
		console.print("[green]Config validation passed.[/green]")
		return 0
	except Exception as e:
		console.print(f"[red]Config validation failed:[/red] {e}")
		return 1


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(prog="uwss", description="Universal Web-Scraping System (UWSS)")
	sub = parser.add_subparsers(dest="command")

	# config-validate
	p_validate = sub.add_parser("config-validate", help="Validate and summarize a config.yaml")
	p_validate.add_argument("--config", default=str(Path("config") / "config.yaml"), help="Path to config.yaml")
	p_validate.set_defaults(func=cmd_config_validate)

	# db-init
	p_db = sub.add_parser("db-init", help="Initialize SQLite database schema")
	p_db.add_argument("--db", default=str(Path("data") / "uwss.sqlite"), help="Path to SQLite DB file")

	def _cmd_db(args: argparse.Namespace) -> int:
		from src.uwss.store import init_db
		db_path = Path(args.db)
		db_path.parent.mkdir(parents=True, exist_ok=True)
		init_db(db_path)
		console.print(f"[green]Initialized DB:[/green] {db_path}")
		return 0

	p_db.set_defaults(func=_cmd_db)

	# db-migrate
	p_mig = sub.add_parser("db-migrate", help="Run lightweight DB migrations")
	# Global DB URL option via env (fallback when provided)
	parser.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"), help="SQLAlchemy DB URL (postgresql+psycopg2://...)")
	p_mig.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))

	def _cmd_migrate(args: argparse.Namespace) -> int:
		from .store import migrate_db
		migrate_db(Path(args.db))
		console.print(f"[green]DB migration completed:[/green] {args.db}")
		return 0

	p_mig.set_defaults(func=_cmd_migrate)

	# db-add-columns (add new columns on Postgres/SQLite for pdf_status/pdf_fetched_at)
	p_cols = sub.add_parser("db-add-columns", help="Add new columns (pdf_status, pdf_fetched_at) if missing")
	p_cols.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))

	def _cmd_cols(args: argparse.Namespace) -> int:
		from sqlalchemy import text as sql_text
		engine, _ = _get_engine_session(args, Path(args.db))
		with engine.connect() as conn:
			try:
				conn.execute(sql_text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS pdf_status VARCHAR(40)"))
			except Exception:
				# SQLite older versions don't support IF NOT EXISTS in ADD COLUMN; ignore
				try:
					conn.execute(sql_text("ALTER TABLE documents ADD COLUMN pdf_status VARCHAR(40)"))
				except Exception:
					pass
			try:
				conn.execute(sql_text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS pdf_fetched_at TIMESTAMP"))
			except Exception:
				try:
					conn.execute(sql_text("ALTER TABLE documents ADD COLUMN pdf_fetched_at DATETIME"))
				except Exception:
					pass
			conn.commit()
		console.print("[green]Ensured pdf_status/pdf_fetched_at columns exist.[/green]")
		return 0

	p_cols.set_defaults(func=_cmd_cols)

	# db-create-indexes (works for SQLite and Postgres)
	p_idx = sub.add_parser("db-create-indexes", help="Create helpful indexes (doi, lower(title), url_hash_sha1)")
	p_idx.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))

	def _cmd_idx(args: argparse.Namespace) -> int:
		from sqlalchemy import text as sql_text
		engine, _ = _get_engine_session(args, Path(args.db))
		with engine.connect() as conn:
			# DOI index
			conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_documents_doi ON documents(doi)"))
			# lower(title) functional index (Postgres); SQLite will ignore function index but we attempt compat
			try:
				conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_documents_title_lower ON documents((lower(title)))"))
			except Exception:
				# fallback plain title index for engines that don't support functional index
				try:
					conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title)"))
				except Exception:
					pass
			# url_hash_sha1
			conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_documents_urlhash ON documents(url_hash_sha1)"))
			# pdf_status and year (useful for filters/exports)
			try:
				conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_documents_pdf_status ON documents(pdf_status)"))
			except Exception:
				pass
			try:
				conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year)"))
			except Exception:
				pass
			conn.commit()
		console.print("[green]Indexes created (or already exist).[/green]")
		return 0

	p_idx.set_defaults(func=_cmd_idx)

	# openalex-discover (moved to commands.openalex_discover)
	try:
		import sys
		# Add src to path if not already there
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.openalex_discover import register as register_openalex_discover
		register_openalex_discover(sub)
	except Exception as e:
		# Fallback: keep CLI loading even if optional module fails
		console.print(f"[yellow]Warning: openalex_discover command not available: {e}[/yellow]")

	# crossref-discover (moved to commands.crossref_discover)
	try:
		import sys
		# Add src to path if not already there
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.crossref_discover import register as register_crossref_discover
		register_crossref_discover(sub)
	except Exception as e:
		# Fallback: keep CLI loading even if optional module fails
		console.print(f"[yellow]Warning: crossref_discover command not available: {e}[/yellow]")

	# core-discover (moved to commands.core_discover)
	try:
		import sys
		# Add src to path if not already there
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.core_discover import register as register_core_discover
		register_core_discover(sub)
	except Exception as e:
		# Fallback: keep CLI loading even if optional module fails
		console.print(f"[yellow]Warning: core_discover command not available: {e}[/yellow]")

	# doaj-discover (moved to commands.doaj_discover)
	try:
		import sys
		# Add src to path if not already there
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.doaj_discover import register as register_doaj_discover
		register_doaj_discover(sub)
	except Exception as e:
		# Fallback: keep CLI loading even if optional module fails
		console.print(f"[yellow]Warning: doaj_discover command not available: {e}[/yellow]")

	# paperscraper-discover (moved to commands.paperscraper_discover)
	try:
		import sys
		# Add src to path if not already there
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.paperscraper_discover import register as register_paperscraper_discover
		register_paperscraper_discover(sub)
	except Exception as e:
		# Fallback: keep CLI loading even if optional module fails
		console.print(f"[yellow]Warning: paperscraper_discover command not available: {e}[/yellow]")

	# crossref-lib-discover (using habanero library)
	try:
		import sys
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.crossref_lib_discover import register as register_crossref_lib_discover
		register_crossref_lib_discover(sub)
	except Exception as e:
		console.print(f"[yellow]Warning: crossref_lib_discover command not available: {e}[/yellow]")

	# openalex-lib-discover (using pyalex library)
	try:
		import sys
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.openalex_lib_discover import register as register_openalex_lib_discover
		register_openalex_lib_discover(sub)
	except Exception as e:
		console.print(f"[yellow]Warning: openalex_lib_discover command not available: {e}[/yellow]")

	# semantic-scholar-lib-discover (using semanticscholar library)
	try:
		import sys
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.semantic_scholar_lib_discover import register as register_semantic_scholar_lib_discover
		register_semantic_scholar_lib_discover(sub)
	except Exception as e:
		console.print(f"[yellow]Warning: semantic_scholar_lib_discover command not available: {e}[/yellow]")

	# discover-crossref
	p_crossref = sub.add_parser("discover-crossref", help="Fetch candidate metadata from Crossref")
	p_crossref.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_crossref.add_argument("--keywords-file", default=None)
	p_crossref.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_crossref.add_argument("--max", type=int, default=100)
	p_crossref.add_argument("--cache-ttl-sec", type=int, default=None)
	p_crossref.add_argument("--resume", action="store_true", help="Resume from saved offset")
	p_crossref.add_argument("--log-json", action="store_true")

	def _cmd_crossref(args: argparse.Namespace) -> int:
		from .discovery import iter_crossref_results
		from .store import Document, Base
		import json

		data = load_config(Path(args.config))
		validate_config(data)
		keywords = data["domain_keywords"]
		if args.keywords_file:
			keywords = [k.strip() for k in Path(args.keywords_file).read_text(encoding="utf-8").splitlines() if k.strip()]
		year_filter = data.get("year_filter")
		contact_email = data.get("contact_email")
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		session = SessionLocal()
		from .store import IngestionState
		start_offset = 0
		if args.resume:
			st = session.query(IngestionState).filter(IngestionState.source == "crossref", IngestionState.checkpoint_key == "offset").first()
			if st and st.checkpoint_value:
				try:
					start_offset = int(st.checkpoint_value)
				except Exception:
					start_offset = 0
		start_ts = time.time()
		inserted = 0
		try:
			for item in iter_crossref_results(keywords, year_filter, max_records=args.max, contact_email=contact_email, cache_ttl_sec=args.cache_ttl_sec, start_offset=start_offset):
				doi = (item.get("DOI") or "")
				title_list = item.get("title") or []
				title = title_list[0] if title_list else None
				abstract = (item.get("abstract") or "")
				link = ""
				for l in item.get("link", []) or []:
					if l.get("URL"):
						link = l["URL"]
						break
				pdf_url = None
				for l in item.get("link", []) or []:
					if (l.get("content-type") == "application/pdf") and l.get("URL"):
						pdf_url = l["URL"]
						break
				authors = []
				for a in item.get("author", []) or []:
					name = " ".join([x for x in [a.get("given"), a.get("family")] if x])
					if name:
						authors.append(name)
				year = None
				issued = (item.get("issued") or {}).get("date-parts")
				if issued and issued[0] and len(issued[0]) > 0:
					year = int(issued[0][0])
				# Deduplicate by DOI or title
				exists = None
				if doi:
					exists = session.query(Document).filter(Document.doi == doi).first()
				if not exists and title:
					exists = session.query(Document).filter(Document.title == title).first()
				if exists:
					continue
				else:
					doc = Document(
						source_url=link or item.get("URL", ""),
						landing_url=link or item.get("URL", ""),
						pdf_url=pdf_url or None,
						doi=doi,
						title=_clip(title, 1000),
						authors=json.dumps(authors),
						venue=_clip((item.get("container-title") or [None])[0], 255) if (item.get("container-title") or [None])[0] else None,
						year=year,
						open_access=bool(pdf_url),
						abstract=abstract,
						status="metadata_only",
						source="crossref",
						topic=_clip(", ".join(keywords[:3]), 100) if keywords else None,
					)
					session.add(doc)
				inserted += 1
			session.commit()
			# save new offset state
			if args.resume:
				new_off = start_offset + inserted
				st = session.query(IngestionState).filter(IngestionState.source == "crossref", IngestionState.checkpoint_key == "offset").first() or IngestionState(source="crossref", checkpoint_key="offset")
				from datetime import datetime
				st.checkpoint_value = str(new_off)
				st.updated_at = datetime.utcnow()
				session.merge(st)
				session.commit()
			console.print(f"[green]Inserted {inserted} Crossref records into {args.db}[/green]")
			_log_json(args.log_json, "discover_crossref_done", inserted=inserted, elapsed_sec=round(time.time()-start_ts,3))
			return 0
		except Exception as e:
			session.rollback()
			console.print(f"[red]Discovery failed:[/red] {e}")
			return 1
		finally:
			session.close()

	p_crossref.set_defaults(func=_cmd_crossref)

	# discover-arxiv
	p_arxiv = sub.add_parser("discover-arxiv", help="Fetch candidate metadata from arXiv")
	p_arxiv.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_arxiv.add_argument("--keywords-file", default=None)
	p_arxiv.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_arxiv.add_argument("--max", type=int, default=50)
	p_arxiv.add_argument("--resume", action="store_true")
	p_arxiv.add_argument("--log-json", action="store_true")

	def _cmd_arxiv(args: argparse.Namespace) -> int:
		from .discovery import iter_arxiv_results
		from .store import Document, Base
		import json
		data = load_config(Path(args.config))
		validate_config(data)
		keywords = data["domain_keywords"]
		if args.keywords_file:
			keywords = [k.strip() for k in Path(args.keywords_file).read_text(encoding="utf-8").splitlines() if k.strip()]
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		session = SessionLocal()
		from .store import IngestionState
		start = 0
		if args.resume:
			st = session.query(IngestionState).filter(IngestionState.source == "arxiv", IngestionState.checkpoint_key == "start").first()
			if st and st.checkpoint_value:
				try:
					start = int(st.checkpoint_value)
				except Exception:
					start = 0
		start_ts = time.time()
		inserted = 0
		try:
			for item in iter_arxiv_results(keywords, max_records=args.max, start=start):
				title = item.get("title")
				pdf_link = item.get("pdf_link")
				year = None
				pub = item.get("published")
				if pub and len(pub) >= 4:
					year = int(pub[:4])
				authors = item.get("authors") or []
				# Deduplicate by title
				exists = None
				if title:
					exists = session.query(Document).filter(Document.title == title).first()
				if exists:
					continue
				doc = Document(
					source_url=item.get("id", ""),
					landing_url=item.get("id", ""),
					pdf_url=pdf_link or None,
					doi=None,
					title=_clip(title, 1000),
					authors=json.dumps(authors),
					venue="arXiv",
					year=year,
					open_access=True if pdf_link else False,
					abstract=item.get("summary") or "",
					status="metadata_only",
					source="arxiv",
					topic=_clip(", ".join(keywords[:3]), 100) if keywords else None,
				)
				session.add(doc)
				inserted += 1
			session.commit()
			if args.resume:
				new_start = start + inserted
				st = session.query(IngestionState).filter(IngestionState.source == "arxiv", IngestionState.checkpoint_key == "start").first() or IngestionState(source="arxiv", checkpoint_key="start")
				from datetime import datetime
				st.checkpoint_value = str(new_start)
				st.updated_at = datetime.utcnow()
				session.merge(st)
				session.commit()
			console.print(f"[green]Inserted {inserted} arXiv records into {args.db}[/green]")
			_log_json(args.log_json, "discover_arxiv_done", inserted=inserted, elapsed_sec=round(time.time()-start_ts,3))
			return 0
		except Exception as e:
			session.rollback()
			console.print(f"[red]Discovery failed:[/red] {e}")
			return 1
		finally:
			session.close()

	p_arxiv.set_defaults(func=_cmd_arxiv)

	# arxiv-harvest-oai (moved to commands.arxiv_harvest)
	try:
		import sys
		# Add src to path if not already there
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.arxiv_harvest import register as register_arxiv_harvest
		register_arxiv_harvest(sub)
	except Exception as e:
		# Fallback: keep CLI loading even if optional module fails
		console.print(f"[yellow]Warning: arxiv_harvest command not available: {e}[/yellow]")

	# trid-discover-sitemap (moved to commands.trid_discover)
	try:
		import sys
		# Add src to path if not already there
		_src_path = str(Path(__file__).parent.parent.parent)
		if _src_path not in sys.path:
			sys.path.insert(0, _src_path)
		from src.uwss.cli.commands.trid_discover import register as register_trid_discover
		register_trid_discover(sub)
	except Exception as e:
		# Fallback: keep CLI loading even if optional module fails
		console.print(f"[yellow]Warning: trid_discover command not available: {e}[/yellow]")

	# arxiv-policy-snapshot
	p_pol = sub.add_parser("arxiv-policy-snapshot", help="Capture arXiv Identify/robots and save under docs/policies/arxiv")
	p_pol.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_pol.add_argument("--out-dir", default=str(Path("docs") / "policies" / "arxiv"))

	def _cmd_arxiv_policy(args: argparse.Namespace) -> int:
		from .arxiv.policy_snapshot import snapshot_arxiv_policy
		data = load_config(Path(args.config))
		contact_email = data.get("contact_email")
		res = snapshot_arxiv_policy(Path(args.out_dir), contact_email=contact_email)
		console.print(f"[green]Saved arXiv policy artifacts to {args.out_dir}[/green]")
		_log_json(True, "arxiv_policy_snapshot", **res)
		return 0

	p_pol.set_defaults(func=_cmd_arxiv_policy)

	# arxiv-fetch-pdf (moved to commands.arxiv_fetch)
	try:
		from .cli.commands.arxiv_fetch import register as register_arxiv_fetch
		register_arxiv_fetch(sub)
	except Exception:
		pass

	# discover-eupmc
	p_eupmc = sub.add_parser("discover-eupmc", help="Fetch candidate metadata from Europe PMC")
	p_eupmc.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_eupmc.add_argument("--keywords-file", default=None)
	p_eupmc.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_eupmc.add_argument("--max", type=int, default=100)
	p_eupmc.add_argument("--cache-ttl-sec", type=int, default=None)
	p_eupmc.add_argument("--resume", action="store_true")
	p_eupmc.add_argument("--log-json", action="store_true")

	def _cmd_eupmc(args: argparse.Namespace) -> int:
		from .discovery import iter_eupmc_results
		from .store import Document, Base
		import json
		data = load_config(Path(args.config))
		validate_config(data)
		keywords = data["domain_keywords"]
		if args.keywords_file:
			keywords = [k.strip() for k in Path(args.keywords_file).read_text(encoding="utf-8").splitlines() if k.strip()]
		year_filter = data.get("year_filter")
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		session = SessionLocal()
		from .store import IngestionState
		start_cursor = "*"
		if args.resume:
			st = session.query(IngestionState).filter(IngestionState.source == "europe_pmc", IngestionState.checkpoint_key == "cursor").first()
			if st and st.checkpoint_value:
				start_cursor = st.checkpoint_value
		start_ts = time.time()
		inserted = 0
		try:
			for item in iter_eupmc_results(keywords, year_filter, max_records=args.max, cache_ttl_sec=args.cache_ttl_sec, start_cursor=start_cursor):
				title = item.get("title")
				doi = item.get("doi") or item.get("DOI") or ""
				landing_url = None
				pdf_url = None
				ft = item.get("fullTextUrlList") or {}
				urls = ft.get("fullTextUrl") or []
				if urls:
					landing_url = urls[0].get("url")
					for u in urls:
						if str(u.get("documentStyle")).lower() == "pdf" and u.get("url"):
							pdf_url = u["url"]
							break
				year = None
				try:
					year = int(item.get("pubYear")) if item.get("pubYear") else None
				except Exception:
					year = None
				authors = []
				alist = (item.get("authorList") or {}).get("author") or []
				for a in alist:
					name = " ".join([a.get("firstName") or "", a.get("lastName") or ""]).strip()
					if name:
						authors.append(name)
				# dedupe by DOI or title
				exists = None
				if doi:
					exists = session.query(Document).filter(Document.doi == doi).first()
				if not exists and title:
					exists = session.query(Document).filter(Document.title == title).first()
				if exists:
					continue
				doc = Document(
					source_url=landing_url or item.get("source") or "",
					landing_url=landing_url or None,
					pdf_url=pdf_url or None,
					doi=doi,
					title=_clip(title, 1000),
					authors=json.dumps(authors),
					venue=_clip(item.get("journalTitle") or item.get("bookOrReportDetails"), 255) if (item.get("journalTitle") or item.get("bookOrReportDetails")) else None,
					year=year,
					open_access=True if pdf_url else False,
					abstract=item.get("abstractText") or "",
					status="metadata_only",
					source="europe_pmc",
					topic=_clip(", ".join(keywords[:3]), 100) if keywords else None,
				)
				session.add(doc)
				inserted += 1
			session.commit()
			# save new cursor (naive: not available here; leave as provided)
			if args.resume and inserted > 0:
				st = session.query(IngestionState).filter(IngestionState.source == "europe_pmc", IngestionState.checkpoint_key == "cursor").first() or IngestionState(source="europe_pmc", checkpoint_key="cursor")
				from datetime import datetime
				st.checkpoint_value = start_cursor
				st.updated_at = datetime.utcnow()
				session.merge(st)
				session.commit()
			console.print(f"[green]Inserted {inserted} Europe PMC records into {args.db}[/green]")
			_log_json(args.log_json, "discover_eupmc_done", inserted=inserted, elapsed_sec=round(time.time()-start_ts,3))
			return 0
		finally:
			session.close()

	p_eupmc.set_defaults(func=_cmd_eupmc)

	# discover-pmc
	p_pmc = sub.add_parser("discover-pmc", help="Fetch candidate metadata from PubMed Central (E-utilities)")
	p_pmc.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_pmc.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_pmc.add_argument("--max", type=int, default=50)
	p_pmc.add_argument("--cache-ttl-sec", type=int, default=None)
	p_pmc.add_argument("--resume", action="store_true")
	p_pmc.add_argument("--log-json", action="store_true")

	def _cmd_pmc(args: argparse.Namespace) -> int:
		from .discovery import iter_pmc_results
		from .store import Document, Base, IngestionState
		import json
		data = load_config(Path(args.config))
		validate_config(data)
		keywords = data["domain_keywords"]
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		session = SessionLocal()
		retstart = 0
		if args.resume:
			st = session.query(IngestionState).filter(IngestionState.source == "pmc", IngestionState.checkpoint_key == "retstart").first()
			if st and st.checkpoint_value:
				try:
					retstart = int(st.checkpoint_value)
				except Exception:
					retstart = 0
		start_ts = time.time()
		inserted = 0
		try:
			for item in iter_pmc_results(keywords, max_records=args.max, cache_ttl_sec=args.cache_ttl_sec, start_retstart=retstart):
				title = item.get("title") or (item.get("sorttitle") or {}).get("#text")
				journal = (item.get("fulljournalname") or item.get("source"))
				year = None
				try:
					year = int((item.get("pubdate") or "")[:4]) if item.get("pubdate") else None
				except Exception:
					year = None
				pmcid = item.get("pmcid")
				if not pmcid:
					for aid in (item.get("articleids") or []):
						if str(aid.get("idtype")).lower() == "pmcid" and aid.get("value"):
							pmcid = aid.get("value")
							break
				landing = item.get("elocationid") or item.get("link") or None
				if (not landing) and pmcid:
					landing = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
				pdf_url = None
				authors = []
				aus = item.get("authors")
				if isinstance(us := item.get("authors"), list):
					for au in us:
						name = " ".join([au.get("firstname") or "", au.get("lastname") or ""]).strip()
						if name:
							authors.append(name)
				elif isinstance(us, dict):
					for au in (us.get("author") or []):
						name = " ".join([au.get("firstname") or "", au.get("lastname") or ""]).strip()
						if name:
							authors.append(name)
				# dedupe by title
				exists = None
				if title:
					exists = session.query(Document).filter(Document.title == title).first()
				if exists:
					continue
				doc = Document(
					source_url=landing or "",
					landing_url=landing or None,
					pdf_url=pdf_url,
					doi=None,
					title=_clip(title, 1000),
					authors=json.dumps(authors),
					venue=_clip(journal, 255) if journal else None,
					year=year,
					open_access=True if pdf_url else False,
					abstract=None,
					status="metadata_only",
					source="pmc",
					topic=_clip(", ".join(keywords[:3]), 100) if keywords else None,
				)
				session.add(doc)
				inserted += 1
			session.commit()
			# save state
			if args.resume and inserted > 0:
				st = session.query(IngestionState).filter(IngestionState.source == "pmc", IngestionState.checkpoint_key == "retstart").first() or IngestionState(source="pmc", checkpoint_key="retstart")
				from datetime import datetime
				st.checkpoint_value = str(retstart + inserted)
				st.updated_at = datetime.utcnow()
				session.merge(st)
				session.commit()
			console.print(f"[green]Inserted {inserted} PMC records into {args.db}[/green]")
			_log_json(args.log_json, "discover_pmc_done", inserted=inserted, elapsed_sec=round(time.time()-start_ts,3))
			return 0
		finally:
			session.close()

	p_pmc.set_defaults(func=_cmd_pmc)

	# discover-doaj
	p_doaj = sub.add_parser("discover-doaj", help="Fetch candidate metadata from DOAJ API")
	p_doaj.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_doaj.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_doaj.add_argument("--max", type=int, default=50)
	p_doaj.add_argument("--cache-ttl-sec", type=int, default=None)
	p_doaj.add_argument("--resume", action="store_true")
	p_doaj.add_argument("--log-json", action="store_true")

	def _cmd_doaj(args: argparse.Namespace) -> int:
		from .discovery import iter_doaj_results
		from .store import Document, Base, IngestionState
		import json
		data = load_config(Path(args.config))
		validate_config(data)
		keywords = data["domain_keywords"]
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		session = SessionLocal()
		page = 1
		if args.resume:
			st = session.query(IngestionState).filter(IngestionState.source == "doaj", IngestionState.checkpoint_key == "page").first()
			if st and st.checkpoint_value:
				try:
					page = int(st.checkpoint_value)
				except Exception:
					page = 1
		start_ts = time.time()
		inserted = 0
		try:
			for item in iter_doaj_results(keywords, max_records=args.max, cache_ttl_sec=args.cache_ttl_sec, start_page=page):
				title = ((item.get("bibjson") or {}).get("title"))
				journal = ((item.get("bibjson") or {}).get("journal") or {}).get("title")
				year = None
				try:
					year = int(((item.get("bibjson") or {}).get("year") or 0)) or None
				except Exception:
					year = None
				landing = None
				links = ((item.get("bibjson") or {}).get("link") or [])
				pdf_url = None
				for lk in links:
					if str(lk.get("type")).lower() == "fulltext" and lk.get("url"):
						landing = lk.get("url")
					if str(lk.get("content_type") or "").lower() == "application/pdf" and lk.get("url"):
						pdf_url = lk.get("url")
				authors = [a.get("name") for a in ((item.get("bibjson") or {}).get("author") or []) if a.get("name")]
				# dedupe by title
				exists = None
				if title:
					exists = session.query(Document).filter(Document.title == title).first()
				if exists:
					continue
				doc = Document(
					source_url=landing or "",
					landing_url=landing or None,
					pdf_url=pdf_url or None,
					doi=None,
					title=_clip(title, 1000),
					authors=json.dumps(authors),
					venue=_clip(journal, 255) if journal else None,
					year=year,
					open_access=True if pdf_url else False,
					abstract=None,
					status="metadata_only",
					source="doaj",
					topic=_clip(", ".join(keywords[:3]), 100) if keywords else None,
				)
				session.add(doc)
				inserted += 1
			session.commit()
			if args.resume and inserted > 0:
				st = session.query(IngestionState).filter(IngestionState.source == "doaj", IngestionState.checkpoint_key == "page").first() or IngestionState(source="doaj", checkpoint_key="page")
				from datetime import datetime
				st.checkpoint_value = str(page + 1)
				st.updated_at = datetime.utcnow()
				session.merge(st)
				session.commit()
			console.print(f"[green]Inserted {inserted} DOAJ records into {args.db}[/green]")
			_log_json(args.log_json, "discover_doaj_done", inserted=inserted, elapsed_sec=round(time.time()-start_ts,3))
			return 0
		finally:
			session.close()

	p_doaj.set_defaults(func=_cmd_doaj)

	# discover-semanticscholar
	p_s2 = sub.add_parser("discover-semanticscholar", help="Fetch candidate metadata from Semantic Scholar")
	p_s2.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_s2.add_argument("--keywords-file", default=None)
	p_s2.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_s2.add_argument("--max", type=int, default=100)
	p_s2.add_argument("--api-key", default=None, help="Semantic Scholar API key (optional)")
	p_s2.add_argument("--cache-ttl-sec", type=int, default=None)
	p_s2.add_argument("--resume", action="store_true")
	p_s2.add_argument("--log-json", action="store_true")

	def _cmd_s2(args: argparse.Namespace) -> int:
		from .discovery import iter_semanticscholar_results
		from .store import Document, Base
		import json
		data = load_config(Path(args.config))
		validate_config(data)
		keywords = data["domain_keywords"]
		if args.keywords_file:
			keywords = [k.strip() for k in Path(args.keywords_file).read_text(encoding="utf-8").splitlines() if k.strip()]
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		session = SessionLocal()
		from .store import IngestionState
		start_offset = 0
		if args.resume:
			st = session.query(IngestionState).filter(IngestionState.source == "semantic_scholar", IngestionState.checkpoint_key == "offset").first()
			if st and st.checkpoint_value:
				try:
					start_offset = int(st.checkpoint_value)
				except Exception:
					start_offset = 0
		start_ts = time.time()
		inserted = 0
		try:
			for item in iter_semanticscholar_results(keywords, max_records=args.max, api_key=args.api_key, cache_ttl_sec=args.cache_ttl_sec, start_offset=start_offset):
				title = item.get("title")
				year = item.get("year")
				venue = item.get("venue") or (item.get("journal") or {}).get("name")
				abstract = item.get("abstract") or ""
				url = item.get("url")
				pdf_url = ((item.get("openAccessPdf") or {}) or {}).get("url")
				# externalIds can contain DOI
				ext_ids = item.get("externalIds") or {}
				doi = ext_ids.get("DOI") or ""
				authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
				# dedupe by DOI or title
				exists = None
				if doi:
					exists = session.query(Document).filter(Document.doi == doi).first()
				if not exists and title:
					exists = session.query(Document).filter(Document.title == title).first()
				if exists:
					continue
				doc = Document(
					source_url=url or "",
					landing_url=url or None,
					pdf_url=pdf_url or None,
					doi=doi,
					title=_clip(title, 1000),
					authors=json.dumps(authors),
					venue=_clip(venue, 255) if venue else None,
					year=int(year) if isinstance(year, int) else (int(year) if str(year).isdigit() else None),
					open_access=True if pdf_url else False,
					abstract=abstract,
					status="metadata_only",
					source="semantic_scholar",
					topic=_clip(", ".join(keywords[:3]), 100) if keywords else None,
				)
				session.add(doc)
				inserted += 1
			session.commit()
			if args.resume:
				new_off = start_offset + inserted
				st = session.query(IngestionState).filter(IngestionState.source == "semantic_scholar", IngestionState.checkpoint_key == "offset").first() or IngestionState(source="semantic_scholar", checkpoint_key="offset")
				from datetime import datetime
				st.checkpoint_value = str(new_off)
				st.updated_at = datetime.utcnow()
				session.merge(st)
				session.commit()
			console.print(f"[green]Inserted {inserted} Semantic Scholar records into {args.db}[/green]")
			_log_json(args.log_json, "discover_s2_done", inserted=inserted, elapsed_sec=round(time.time()-start_ts,3))
			return 0
		finally:
			session.close()

	p_s2.set_defaults(func=_cmd_s2)

	# oai-harvest (generic)
	p_oai = sub.add_parser("oai-harvest", help="Harvest via generic OAI-PMH (oai_dc)")
	p_oai.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_oai.add_argument("--oai-url", required=True, help="Base OAI-PMH endpoint (e.g., https://.../oai/request)")
	p_oai.add_argument("--from", dest="from_date", default=None)
	p_oai.add_argument("--until", dest="until_date", default=None)
	p_oai.add_argument("--set", dest="set_spec", default=None)
	p_oai.add_argument("--max", type=int, default=None)
	p_oai.add_argument("--resume-key", default=None, help="Checkpoint key to store resumptionToken under ingestion_state")
	p_oai.add_argument("--throttle-sec", type=float, default=1.0)

	def _cmd_oai(args: argparse.Namespace) -> int:
		from sqlalchemy import select
		from .store import Document, IngestionState, Base
		from .discovery.oai import iter_oai_dc
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		s = SessionLocal()
		inserted = 0
		try:
			resume_token = None
			if args.resume_key:
				st = s.query(IngestionState).filter(IngestionState.source == args.oai_url, IngestionState.checkpoint_key == args.resume_key).first()
				if st and st.checkpoint_value:
					resume_token = st.checkpoint_value
			for item in iter_oai_dc(args.oai_url, getattr(args, "from_date", None), getattr(args, "until_date", None), getattr(args, "set_spec", None), resume_token=resume_token, throttle_sec=float(getattr(args, "throttle_sec", 1.0))):
				title = item.get("title")
				doi = item.get("doi")
				src = item.get("source_url") or ""
				# dedupe by DOI then title then source_url
				existing = None
				if doi:
					existing = s.query(Document).filter(Document.doi == doi).first()
				if existing is None and title:
					existing = s.query(Document).filter(Document.title == title).first()
				if existing is None and src:
					existing = s.query(Document).filter(Document.source_url == src).first()
				if existing:
					continue
				d = Document(
					source_url=src,
					landing_url=src,
					pdf_url=item.get("pdf_url"),
					doi=(_clip(doi, 255) if doi else None),
					title=_clip(title, 1000),
					authors=None if not item.get("authors") else __import__("json").dumps(item.get("authors")),
					venue=None,
					year=item.get("year"),
					open_access=True if item.get("pdf_url") else False,
					abstract=_clip(item.get("abstract"), 20000),
					status="metadata_only",
					source="oai",
				)
				s.add(d)
				inserted += 1
				if args.max and inserted >= args.max:
					break
			s.commit()
			# Save resume token placeholder if provided by caller via resume_key (not available from iter here)
			# Caller can re-provide resume token on next run using --resume-key with stored value
			console.print(f"[green]OAI-PMH inserted {inserted} records from {args.oai_url}[/green]")
			return 0
		finally:
			s.close()

	p_oai.set_defaults(func=_cmd_oai)

	# discover-rss (generic)
	p_rss = sub.add_parser("discover-rss", help="Discover documents from an RSS/Atom feed")
	p_rss.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_rss.add_argument("--rss-url", required=True)
	p_rss.add_argument("--source-label", default="rss")
	p_rss.add_argument("--max", type=int, default=100)

	def _cmd_rss(args: argparse.Namespace) -> int:
		from .discovery.rss import iter_rss
		from .store import Document, Base
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		s = SessionLocal()
		inserted = 0
		try:
			for item in iter_rss(args.rss_url, max_records=args.max):
				# Dedupe by DOI (none for RSS), then title, then source_url
				existing = None
				title = item.get("title")
				src = item.get("source_url") or ""
				if title:
					existing = s.query(Document).filter(Document.title == title).first()
				if existing is None and src:
					existing = s.query(Document).filter(Document.source_url == src).first()
				if existing:
					continue
				# flags
				pdf_url = item.get("pdf_url")
				open_access = True if pdf_url else False
				oa_status = ("fulltext_pdf" if pdf_url else "abstract_only")
				# normalize authors/affiliations/keywords to JSON strings
				import json as _json
				authors_json = _json.dumps(item.get("authors") or [])
				affils_json = _json.dumps(item.get("affiliations") or [])
				keywords_json = _json.dumps(item.get("keywords") or [])
				d = Document(
					source_url=src,
					landing_url=src,
					pdf_url=pdf_url,
					doi=None,
					title=_clip(title, 1000),
					authors=authors_json,
					affiliations=affils_json,
					keywords=keywords_json,
					venue=None,
					year=item.get("year"),
					open_access=open_access,
					oa_status=oa_status,
					abstract=_clip(item.get("abstract"), 20000),
					status="metadata_only",
					source=str(args.source_label or "rss"),
				)
				s.add(d)
				inserted += 1
			s.commit()
			console.print(f"[green]RSS inserted {inserted} records from {args.rss_url}[/green]")
			return 0
		finally:
			s.close()

	p_rss.set_defaults(func=_cmd_rss)

	# export-preset (strict/relaxed)
	p_preset = sub.add_parser("export-preset", help="Export with strict/relaxed presets and write IDs")
	p_preset.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_preset.add_argument("--out", required=True, help="Output file path (.jsonl or .csv)")
	p_preset.add_argument("--preset", choices=["strict", "relaxed"], required=True)
	p_preset.add_argument("--ids-out", default=None)
	p_preset.add_argument("--year-min", type=int, default=None, help="Override default year for preset")
	p_preset.add_argument("--min-score", type=float, default=None, help="Override default min-score for preset")
	p_preset.add_argument("--negative-keywords-file", default=None)
	p_preset.add_argument("--require-match", action="store_true", help="Require matched keywords (default true for presets)")
	p_preset.add_argument("--log-json", action="store_true")
	def _cmd_preset(args: argparse.Namespace) -> int:
		# derive defaults by preset
		defaults = {"strict": {"min_score": 0.25, "year_min": 1995}, "relaxed": {"min_score": 0.20, "year_min": 2015}}
		p = defaults[args.preset]
		ns_min = args.min_score if args.min_score is not None else p["min_score"]
		ns_year = args.year_min if args.year_min is not None else p["year_min"]
		# Reuse export selection logic
		from sqlalchemy import select
		from .store import Document
		import json, csv
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		session = SessionLocal()
		try:
			q = session.execute(select(Document))
			rows = []
			nk_set = None
			if args.negative_keywords_file:
				try:
					nk_set = set([ln.strip().lower() for ln in Path(args.negative_keywords_file).read_text(encoding="utf-8").splitlines() if ln.strip()])
				except Exception:
					nk_set = None
			for (d,) in q:
				if d.relevance_score is not None and d.relevance_score < ns_min:
					continue
				if ns_year and d.year and d.year < ns_year:
					continue
				if (args.require_match or True):
					kf = (d.keywords_found or "").strip()
					if not kf or kf == "[]":
						continue
				row = {
					"id": d.id,
					"source_url": d.source_url,
					"landing_url": getattr(d, "landing_url", None),
					"pdf_url": getattr(d, "pdf_url", None),
					"doi": d.doi,
					"title": d.title,
					"authors": d.authors,
					"venue": d.venue,
					"year": d.year,
					"date": getattr(d, "pub_date", None),
					"relevance_score": d.relevance_score,
					"status": d.status,
					"local_path": d.local_path,
					"pdf_path": d.local_path,
					"content_path": getattr(d, "content_path", None),
					"content_chars": getattr(d, "content_chars", None),
					"open_access": d.open_access,
					"license": d.license,
					"file_size": d.file_size,
					"source": d.source,
					"oa_status": d.oa_status,
					"topic": d.topic,
				}
				if nk_set:
					txt = ((d.title or "") + "\n" + (d.abstract or "") + "\n" + (getattr(d, "text_excerpt", None) or "")).lower()
					if any(neg in txt for neg in nk_set):
						continue
				rows.append(row)
			# Write out
			out_path = Path(args.out)
			out_path.parent.mkdir(parents=True, exist_ok=True)
			if out_path.suffix.lower() == ".jsonl":
				with open(out_path, "w", encoding="utf-8") as f:
					for r in rows:
						f.write(json.dumps(r, ensure_ascii=False) + "\n")
			elif out_path.suffix.lower() == ".csv":
				if rows:
					with open(out_path, "w", encoding="utf-8", newline="") as f:
						writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
						writer.writeheader()
						writer.writerows(rows)
			else:
				raise ValueError("Unsupported extension. Use .jsonl or .csv")
			if getattr(args, "ids_out", None):
				try:
					id_path = Path(args.ids_out)
					id_path.parent.mkdir(parents=True, exist_ok=True)
					id_path.write_text("\n".join(str(r.get("id")) for r in rows), encoding="utf-8")
					console.print(f"[green]Saved IDs to {args.ids_out}[/green]")
				except Exception:
					pass
			console.print(f"[green]Preset export ({args.preset}) wrote {len(rows)} records to {args.out}[/green]")
			_log_json(args.log_json, "export_preset_done", preset=args.preset, out=str(args.out), count=len(rows))
			return 0
		finally:
			session.close()
	p_preset.set_defaults(func=_cmd_preset)

	# sample-preset (pdf-only sampling aligned to preset thresholds)
	p_sp = sub.add_parser("sample-preset", help="Sample PDF-only records aligned to preset thresholds")
	p_sp.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_sp.add_argument("--out", required=True)
	p_sp.add_argument("--preset", choices=["strict", "relaxed"], required=True)
	p_sp.add_argument("--n", type=int, default=20)
	def _cmd_sp(args: argparse.Namespace) -> int:
		defaults = {"strict": {"min_score": 0.25}, "relaxed": {"min_score": 0.20}}
		ms = defaults[args.preset]["min_score"]
		# Delegate to existing sample-records implementation by selecting and writing file here (reuse selection quickly)
		from sqlalchemy import select
		from .store import Document
		import json, random
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		s = SessionLocal()
		try:
			q = s.execute(select(Document))
			candidates = []
			for (d,) in q:
				if not getattr(d, "local_path", None):
					continue
				if (d.relevance_score or 0.0) < ms:
					continue
				kf = (d.keywords_found or "").strip()
				if not kf or kf == "[]":
					continue
				candidates.append(d)
			random.shuffle(candidates)
			sample = candidates[: max(0, int(args.n))]
			out_path = Path(args.out)
			out_path.parent.mkdir(parents=True, exist_ok=True)
			with open(out_path, "w", encoding="utf-8") as f:
				for d in sample:
					row = {"id": d.id, "title": d.title, "year": d.year, "relevance_score": d.relevance_score, "local_path": d.local_path}
					f.write(json.dumps(row, ensure_ascii=False) + "\n")
			console.print(f"[green]Wrote {len(sample)} samples to {args.out}[/green]")
			return 0
		finally:
			s.close()
	p_sp.set_defaults(func=_cmd_sp)

	# grobid-batch-small (convenience)
	p_gbs = sub.add_parser("grobid-batch-small", help="Parse a small batch of PDFs via GROBID (default limit=50)")
	p_gbs.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_gbs.add_argument("--content-dir", default=str(Path("data") / "content"))
	p_gbs.add_argument("--limit", type=int, default=50)
	p_gbs.add_argument("--grobid-url", default=os.getenv("UWSS_GROBID_URL", "http://localhost:8070"))
	def _cmd_gbs(args: argparse.Namespace) -> int:
		from .parse.grobid_client import parse_with_grobid
		from .store import Base
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		s = SessionLocal()
		try:
			res = parse_with_grobid(s, Path(args.content_dir), limit=args.limit, grobid_url=args.grobid_url)
		finally:
			s.close()
		console.print(f"[green]GROBID batch: ok={res['parsed_ok']} fail={res['parsed_fail']} attempted={res['attempted']}[/green]")
		return 0
	p_gbs.set_defaults(func=_cmd_gbs)
	# score-keywords
	p_score = sub.add_parser("score-keywords", help="Compute keyword relevance scores for documents in DB")
	p_score.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_score.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_score.add_argument("--min", type=float, default=0.0)
	p_score.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))
	p_score.add_argument("--negative-keywords-file", default=None)
	p_score.add_argument("--use-fulltext", action="store_true", default=True, help="Use full-text content for scoring when available (default: True)")

	def _cmd_score(args: argparse.Namespace) -> int:
		from src.uwss.score import score_documents
		data = load_config(Path(args.config))
		validate_config(data)
		keywords = data["domain_keywords"]
		neg = None
		if args.negative_keywords_file:
			try:
				neg = [ln.strip() for ln in Path(args.negative_keywords_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
			except Exception:
				neg = None
		# Fall back to config negative_keywords when file not provided
		if neg is None:
			cfg_neg = data.get("negative_keywords")
			if isinstance(cfg_neg, list) and cfg_neg:
				neg = [str(x).strip() for x in cfg_neg if str(x).strip()]
		updated = score_documents(Path(args.db), keywords, args.min, db_url=getattr(args, "db_url", None), negative_keywords=neg, use_fulltext=args.use_fulltext)
		console.print(f"[green]Scored {updated} documents[/green]")
		return 0

	p_score.set_defaults(func=_cmd_score)

	# extract-text-excerpt (stub)
	p_xt = sub.add_parser("extract-text-excerpt", help="Populate text_excerpt from abstract/title (stub)")
	p_xt.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_xt.add_argument("--limit", type=int, default=30)
	p_xt.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

	def _cmd_xt(args: argparse.Namespace) -> int:
		from .extract import extract_text_excerpt
		n = extract_text_excerpt(Path(args.db), limit=args.limit, db_url=getattr(args, "db_url", None))
		console.print(f"[green]Populated text_excerpt for {n} records[/green]")
		return 0

	p_xt.set_defaults(func=_cmd_xt)

	# extract-full-text
	p_xf = sub.add_parser("extract-full-text", help="Extract full text from local files or metadata into data/content")
	p_xf.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_xf.add_argument("--content-dir", default=str(Path("data") / "content"))
	p_xf.add_argument("--limit", type=int, default=50)
	p_xf.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

	def _cmd_xf(args: argparse.Namespace) -> int:
		from .extract import extract_full_text
		n = extract_full_text(Path(args.db), Path(args.content_dir), limit=args.limit, db_url=getattr(args, "db_url", None))
		console.print(f"[green]Extracted full text for {n} records[/green]")
		return 0

	p_xf.set_defaults(func=_cmd_xf)

	# arxiv-parse-grobid (Phase 3)
	p_gb = sub.add_parser("arxiv-parse-grobid", help="Parse local arXiv PDFs via GROBID and store TEI/text")
	p_gb.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_gb.add_argument("--content-dir", default=str(Path("data") / "content"))
	p_gb.add_argument("--limit", type=int, default=20)
	p_gb.add_argument("--grobid-url", default=os.getenv("UWSS_GROBID_URL", "http://localhost:8070"))
	p_gb.add_argument("--log-json", action="store_true")
	p_gb.add_argument("--metrics-out", default=None)
	def _cmd_gb(args: argparse.Namespace) -> int:
		from .parse.grobid_client import parse_with_grobid
		from .store import Base
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		Base.metadata.create_all(engine)
		s = SessionLocal()
		try:
			res = parse_with_grobid(s, Path(args.content_dir), limit=args.limit, grobid_url=args.grobid_url)
		finally:
			s.close()
		console.print(f"[green]GROBID parse: ok={res['parsed_ok']} fail={res['parsed_fail']} attempted={res['attempted']}[/green]")
		_log_json(args.log_json, "grobid_parse_done", **res)
		if getattr(args, "metrics_out", None):
			try:
				Path(args.metrics_out).parent.mkdir(parents=True, exist_ok=True)
				Path(args.metrics_out).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
				console.print(f"[green]Saved metrics to {args.metrics_out}[/green]")
			except Exception:
				pass
		return 0

	p_gb.set_defaults(func=_cmd_gb)

	# scrape-full-content (from landing/source URL)
	p_sfc = sub.add_parser("scrape-full-content", help="Fetch landing/source URL and extract full content to data/content")
	p_sfc.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_sfc.add_argument("--content-dir", default=str(Path("data") / "content"))
	p_sfc.add_argument("--limit", type=int, default=50)
	p_sfc.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_sfc.add_argument("--overwrite", action="store_true")
	p_sfc.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

	def _cmd_sfc(args: argparse.Namespace) -> int:
		from .extract import scrape_full_content
		data = load_config(Path(args.config))
		contact_email = data.get("contact_email")
		n = scrape_full_content(Path(args.db), Path(args.content_dir), limit=args.limit, contact_email=contact_email, overwrite=args.overwrite, db_url=getattr(args, "db_url", None))
		console.print(f"[green]Scraped full content for {n} URLs[/green]")
		return 0

	p_sfc.set_defaults(func=_cmd_sfc)

	# s3-upload (optional: upload downloaded files to S3)
	p_s3 = sub.add_parser("s3-upload", help="Upload files (PDF + optional sidecars/metadata/content) to S3")
	p_s3.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_s3.add_argument("--files-dir", default=str(Path("data") / "files"))
	p_s3.add_argument("--bucket", required=True)
	p_s3.add_argument("--prefix", default="uwss/")
	p_s3.add_argument("--region", default=None)
	p_s3.add_argument("--include-sidecars", action="store_true", help="Also upload PDF sidecar .meta.json if present")
	p_s3.add_argument("--include-docjson", action="store_true", help="Upload per-document doc.json (identification)")
	p_s3.add_argument("--include-content", action="store_true", help="Upload extracted content if available")
	p_s3.add_argument("--layout", choices=["flat", "by-id"], default="flat", help="Key layout: flat or by-id/<id>/...")

	def _cmd_s3(args: argparse.Namespace) -> int:
		from .upload import upload_files_to_s3
		count = upload_files_to_s3(
			Path(args.db),
			Path(args.files_dir),
			args.bucket,
			args.prefix,
			args.region,
			include_sidecars=bool(getattr(args, "include_sidecars", False)),
			include_docjson=bool(getattr(args, "include_docjson", False)),
			include_content=bool(getattr(args, "include_content", False)),
			layout=str(getattr(args, "layout", "flat")),
		)
		console.print(f"[green]Uploaded {count} files to s3://{args.bucket}/{args.prefix}[/green]")
		return 0

	p_s3.set_defaults(func=_cmd_s3)

	# export-manifest (one JSONL entry per Document with identification + file provenance)
	p_manifest = sub.add_parser("export-manifest", help="Export manifest.jsonl with identification and file provenance")
	p_manifest.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_manifest.add_argument("--out", required=True, help="Path to write manifest (.jsonl)")

	def _cmd_manifest(args: argparse.Namespace) -> int:
		from sqlalchemy import select
		from .store import Document
		import json
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		session = SessionLocal()
		count = 0
		try:
			q = session.execute(select(Document))
			Path(args.out).parent.mkdir(parents=True, exist_ok=True)
			with open(args.out, "w", encoding="utf-8") as wf:
				for (d,) in q:
					# normalize authors
					authors_val = None
					try:
						import json as _json
						if isinstance(d.authors, str):
							a = _json.loads(d.authors)
							if isinstance(a, list):
								authors_val = a
					except Exception:
						authors_val = None
					if authors_val is None and isinstance(d.authors, str):
						parts = [p.strip() for p in (d.authors.split(";") if ";" in d.authors else d.authors.split(",")) if p.strip()]
						authors_val = parts or None
					# arxiv id guess
					arxiv_id = None
					try:
						from .fetch.arxiv_pdf import _guess_arxiv_id
						arxiv_id = _guess_arxiv_id(getattr(d, "landing_url", None), getattr(d, "pdf_url", None))
					except Exception:
						arxiv_id = None
					row = {
						"document_id": int(d.id),
						"source": d.source,
						"arxiv_id": arxiv_id,
						"doi": d.doi,
						"title": d.title,
						"authors": authors_val,
						"abstract": d.abstract,
						"year": int(d.year) if d.year is not None else None,
						"topic": d.topic,
						"local_path": d.local_path,
						"checksum_sha256": getattr(d, "checksum_sha256", None),
						"file_size": getattr(d, "file_size", None),
						"http_status": getattr(d, "http_status", None),
						"pdf_status": getattr(d, "pdf_status", None),
						"pdf_fetched_at": str(getattr(d, "pdf_fetched_at", "")) if getattr(d, "pdf_fetched_at", None) else None,
						# s3 key may be filled by upload step later; default None
						"s3_key": None,
					}
					wf.write(json.dumps(row, ensure_ascii=False) + "\n")
					count += 1
			console.print(f"[green]Wrote manifest for {count} records to {args.out}[/green]")
			return 0
		finally:
			session.close()

	p_manifest.set_defaults(func=_cmd_manifest)

	# delete-doc by id
	p_del = sub.add_parser("delete-doc", help="Delete a document by id")
	p_del.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_del.add_argument("--id", type=int, required=True)

	def _cmd_del(args: argparse.Namespace) -> int:
		from sqlalchemy import select
		from .store import Document
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		s = SessionLocal()
		try:
			d = s.get(Document, args.id)
			if not d:
				console.print(f"[yellow]No document with id {args.id}[/yellow]")
				return 0
			s.delete(d)
			s.commit()
			console.print(f"[green]Deleted document {args.id}[/green]")
			return 0
		finally:
			s.close()

	p_del.set_defaults(func=_cmd_del)

	# export-jsonl / export-csv
	p_export = sub.add_parser("export", help="Export documents to JSONL or CSV")
	p_export.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_export.add_argument("--out", required=True, help="Output file path (.jsonl or .csv)")
	p_export.add_argument("--ids-out", default=None, help="Optional path to write exported IDs (one per line)")
	p_export.add_argument("--min-score", type=float, default=0.0)
	p_export.add_argument("--year-min", type=int, default=None)
	p_export.add_argument("--oa-only", action="store_true")
	p_export.add_argument("--sort", choices=["relevance", "year"], default="relevance")
	# skip missing-core records (no title and no doi)
	p_export.add_argument("--skip-missing-core", action="store_true")
	# include-new-fields
	p_export.add_argument("--include-provenance", action="store_true")
	# embed content text (use with caution for large outputs)
	p_export.add_argument("--embed-content", action="store_true")
	# require at least one matched keyword/phrase (from score-keywords)
	p_export.add_argument("--require-match", action="store_true", help="Require matched keywords (ensures relevance)")
	p_export.add_argument("--min-abstract-length", type=int, default=50, help="Minimum abstract length for quality (default: 50)")
	p_export.add_argument("--require-abstract", action="store_true", help="Require abstract for quality data")
	# logging
	p_export.add_argument("--log-json", action="store_true")
	# include-full-text excerpt
	p_export.add_argument("--include-full-text", action="store_true")
	# negative keywords filter file (one per line)
	p_export.add_argument("--negative-keywords-file", default=None)

	def _cmd_export(args: argparse.Namespace) -> int:
		from sqlalchemy import select
		from src.uwss.store.models import Document
		from src.uwss.store.db import create_sqlite_engine, create_engine_from_url
		import json, csv
		if args.db_url:
			engine, SessionLocal = create_engine_from_url(args.db_url)
		else:
			engine, SessionLocal = create_sqlite_engine(Path(args.db))
		session = SessionLocal()
		try:
			q = session.execute(select(Document))
			rows = []
			for (d,) in q:
				if d.relevance_score is not None and d.relevance_score < args.min_score:
					continue
				if args.year_min and d.year and d.year < args.year_min:
					continue
				if args.skip_missing_core and (not d.title and not d.doi):
					continue
				if args.require_match:
					kf = (d.keywords_found or "").strip()
					if not kf or kf == "[]":
						continue
				# Quality filter: require abstract if specified
				if args.require_abstract:
					if not d.abstract or len(d.abstract) < args.min_abstract_length:
						continue
				# negative keyword filter (simple substring check in title/abstract/excerpt)
				nk_set = None
				if args.negative_keywords_file:
					try:
						nk_set = set([ln.strip().lower() for ln in Path(args.negative_keywords_file).read_text(encoding="utf-8").splitlines() if ln.strip()])
					except Exception:
						nk_set = None
				row = {
					"id": d.id,
					"source_url": d.source_url,
					"landing_url": getattr(d, "landing_url", None),
					"pdf_url": getattr(d, "pdf_url", None),
					"doi": d.doi,
					"title": d.title,
					"abstract": getattr(d, "abstract", None),
					"authors": d.authors,
					"venue": d.venue,
					"year": d.year,
					"date": getattr(d, "pub_date", None),
					"relevance_score": d.relevance_score,
					"status": d.status,
					"local_path": d.local_path,
					"pdf_path": d.local_path,
					"content_path": getattr(d, "content_path", None),
					"content_chars": getattr(d, "content_chars", None),
					"open_access": d.open_access,
					"license": d.license,
					"file_size": d.file_size,
					"source": d.source,
					"oa_status": d.oa_status,
					"topic": d.topic,
				}
				if nk_set:
					txt = ((d.title or "") + "\n" + (d.abstract or "") + "\n" + (getattr(d, "text_excerpt", None) or "")).lower()
					if any(neg in txt for neg in nk_set):
						continue
				if args.include_full_text:
					row["text_excerpt"] = getattr(d, "text_excerpt", None)
				if args.embed_content:
					try:
						cp = getattr(d, "content_path", None)
						row["full_content"] = Path(cp).read_text(encoding="utf-8") if cp else None
					except Exception:
						row["full_content"] = None
				if args.include_provenance:
					row["checksum_sha256"] = getattr(d, "checksum_sha256", None)
					row["mime_type"] = getattr(d, "mime_type", None)
					row["url_hash_sha1"] = getattr(d, "url_hash_sha1", None)
					row["http_status"] = getattr(d, "http_status", None)
					row["fetched_at"] = str(getattr(d, "fetched_at", "")) if getattr(d, "fetched_at", None) else None
				rows.append(row)
			# OA filter
			if args.oa_only:
				rows = [r for r in rows if r.get("open_access")]
			# Sorting
			if args.sort == "relevance":
				rows.sort(key=lambda x: (x.get("relevance_score") or 0.0), reverse=True)
			elif args.sort == "year":
				rows.sort(key=lambda x: (x.get("year") or 0))
			
			# Handle S3 URLs
			if args.out.startswith("s3://"):
				import boto3
				from urllib.parse import urlparse
				parsed = urlparse(args.out)
				bucket = parsed.netloc
				key = parsed.path.lstrip("/")
				
				s3 = boto3.client("s3")
				if key.endswith(".jsonl"):
					content = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
					s3.put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"))
				elif key.endswith(".csv"):
					if rows:
						import io
						output = io.StringIO()
						writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
						writer.writeheader()
						writer.writerows(rows)
						s3.put_object(Bucket=bucket, Key=key, Body=output.getvalue().encode("utf-8"))
				else:
					raise ValueError("Unsupported extension. Use .jsonl or .csv")
			else:
				# Local file handling
				out_path = Path(args.out)
				out_path.parent.mkdir(parents=True, exist_ok=True)
				if out_path.suffix.lower() == ".jsonl":
					with open(out_path, "w", encoding="utf-8") as f:
						for r in rows:
							f.write(json.dumps(r, ensure_ascii=False) + "\n")
				elif out_path.suffix.lower() == ".csv":
					if rows:
						with open(out_path, "w", encoding="utf-8", newline="") as f:
							writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
							writer.writeheader()
							writer.writerows(rows)
				else:
					raise ValueError("Unsupported extension. Use .jsonl or .csv")
			# Optional IDs file
			if getattr(args, "ids_out", None):
				try:
					id_path = Path(args.ids_out)
					id_path.parent.mkdir(parents=True, exist_ok=True)
					id_path.write_text("\n".join(str(r.get("id")) for r in rows), encoding="utf-8")
					console.print(f"[green]Saved IDs to {args.ids_out}[/green]")
				except Exception:
					pass
			console.print(f"[green]Exported {len(rows)} records to {args.out}[/green]")
			_log_json(args.log_json, "export_done", out=str(args.out), count=len(rows))
			return 0
		finally:
			session.close()

	p_export.set_defaults(func=_cmd_export)

	# import-jsonl: import an exported JSONL into DB with dedupe (DOI/title/url hash)
	p_imp = sub.add_parser("import-jsonl", help="Import JSONL into DB with dedupe (DOI/title/url hash)")
	p_imp.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_imp.add_argument("--in", dest="in_file", required=True, help="Input JSONL file path")
	p_imp.add_argument("--source-override", default=None, help="Override source column for imported rows")
	p_imp.add_argument("--limit", type=int, default=None)
	p_imp.add_argument("--dry-run", action="store_true")
	p_imp.add_argument("--log-json", action="store_true")

	def _cmd_import_jsonl(args: argparse.Namespace) -> int:
		import hashlib
		from sqlalchemy import select
		from .store import Document

		in_path = Path(args.in_file)
		if not in_path.exists():
			console.print(f"[red]Input not found: {in_path}[/red]")
			return 1

		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		inserted = 0
		updated = 0
		skipped = 0

		def _sha1_url(u: str | None) -> str | None:
			if not u:
				return None
			try:
				return hashlib.sha1(u.encode("utf-8")).hexdigest()
			except Exception:
				return None

		limit = args.limit or 10**12
		with SessionLocal() as session:
			with in_path.open("r", encoding="utf-8") as f:
				for idx, line in enumerate(f, start=1):
					if idx > limit:
						break
					line = line.strip()
					if not line:
						continue
					try:
						obj = json.loads(line)
					except Exception:
						skipped += 1
						continue
					doi = (obj.get("doi") or None)
					title = (obj.get("title") or None)
					# basic clip for varchar
					def _clip_local(text: str | None, max_len: int) -> str | None:
						if text is None:
							return None
						return str(text)[:max_len]
					title = _clip_local(title, 1000)
					venue = _clip_local((obj.get("venue") or None), 255)
					topic = _clip_local((obj.get("topic") or None), 100)
					source_url = obj.get("source_url") or obj.get("url") or None
					landing_url = obj.get("landing_url") or None
					pdf_url = obj.get("pdf_url") or None
					local_path = obj.get("pdf_path") or obj.get("local_path") or None
					content_path = obj.get("content_path") or None
					content_chars = obj.get("content_chars") or None
					authors = obj.get("authors") or None
					abstract = obj.get("abstract") or None
					year = obj.get("year") or None
					pub_date = obj.get("date") or obj.get("pub_date") or None
					source = args.source_override or (obj.get("source") or None)
					license_ = obj.get("license") or None
					oa_status = obj.get("oa_status") or None
					relevance_score = obj.get("relevance_score") or None
					keywords_found = obj.get("keywords_found") or None
					url_hash = obj.get("url_hash_sha1") or _sha1_url(pdf_url or landing_url or source_url)

					existing = None
					if doi:
						existing = session.execute(select(Document).where(Document.doi == doi)).scalar_one_or_none()
					if existing is None and title:
						existing = session.execute(select(Document).where(Document.title == title)).scalar_one_or_none()
					if existing is None and url_hash:
						existing = session.execute(select(Document).where(Document.url_hash_sha1 == url_hash)).scalar_one_or_none()

					if existing is None:
						if args.dry_run:
							inserted += 1
							continue
						doc = Document(
							source_url=source_url or (landing_url or pdf_url or ""),
							landing_url=landing_url,
							pdf_url=pdf_url,
							doi=doi,
							title=title,
							authors=authors,
							venue=venue,
							year=year,
							pub_date=pub_date,
							abstract=abstract,
							local_path=local_path,
							content_path=content_path,
							content_chars=content_chars,
							keywords_found=keywords_found,
							relevance_score=relevance_score,
							source=source,
							license=license_,
							oa_status=oa_status,
							url_hash_sha1=url_hash,
						)
						session.add(doc)
						inserted += 1
					else:
						# update only when empty
						def _set_if_empty(attr: str, val):
							if val is not None and getattr(existing, attr) in (None, "", 0):
								setattr(existing, attr, val)
						_set_if_empty("landing_url", landing_url)
						_set_if_empty("pdf_url", pdf_url)
						_set_if_empty("doi", doi)
						_set_if_empty("title", title)
						_set_if_empty("authors", authors)
						_set_if_empty("venue", venue)
						_set_if_empty("year", year)
						_set_if_empty("pub_date", pub_date)
						_set_if_empty("abstract", abstract)
						_set_if_empty("local_path", local_path)
						_set_if_empty("content_path", content_path)
						_set_if_empty("content_chars", content_chars)
						_set_if_empty("keywords_found", keywords_found)
						try:
							if relevance_score is not None:
								existing.relevance_score = max(filter(lambda x: x is not None, [existing.relevance_score, relevance_score]))
						except Exception:
							pass
						_set_if_empty("source", source)
						_set_if_empty("license", license_)
						_set_if_empty("oa_status", oa_status)
						if (getattr(existing, "url_hash_sha1", None) in (None, "")) and url_hash:
							existing.url_hash_sha1 = url_hash
						updated += 1
					if not args.dry_run and (inserted + updated) % 200 == 0:
						session.commit()
				# final commit
				if not args.dry_run:
					session.commit()

		_log_json(args.log_json, "import_jsonl_done", inserted=inserted, updated=updated, skipped=skipped, file=str(in_path))
		return 0

	p_imp.set_defaults(func=_cmd_import_jsonl)

	# sample-records: randomly sample documents for manual QA
	p_samp = sub.add_parser("sample-records", help="Write a random sample of records to a file for manual review")
	p_samp.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_samp.add_argument("--out", required=True, help="Output path (.jsonl or .txt)")
	p_samp.add_argument("--n", type=int, default=20, help="Number of records to sample")
	p_samp.add_argument("--pdf-only", action="store_true", help="Only include records with downloaded PDFs (pdf_status ok and local_path exists)")
	p_samp.add_argument("--require-match", action="store_true", help="Require matched keywords (non-empty keywords_found)")
	p_samp.add_argument("--min-score", type=float, default=0.0, help="Minimum relevance_score")

	def _cmd_sample(args: argparse.Namespace) -> int:
		import random, json
		from sqlalchemy import select
		from .store import Document
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		s = SessionLocal()
		try:
			q = s.execute(select(Document))
			candidates = []
			for (d,) in q:
				if args.pdf_only:
					if not getattr(d, "local_path", None):
						continue
					if getattr(d, "pdf_status", None) not in ("ok", "fetched", None):
						continue
				if args.require_match:
					kf = (d.keywords_found or "").strip()
					if not kf or kf == "[]":
						continue
				if (d.relevance_score or 0.0) < float(getattr(args, "min_score", 0.0)):
					continue
				candidates.append(d)
			random.shuffle(candidates)
			sample = candidates[: max(0, int(args.n))]
			out_path = Path(args.out)
			out_path.parent.mkdir(parents=True, exist_ok=True)
			if out_path.suffix.lower() == ".jsonl":
				with open(out_path, "w", encoding="utf-8") as f:
					for d in sample:
						row = {
							"id": d.id,
							"title": d.title,
							"year": d.year,
							"relevance_score": d.relevance_score,
							"keywords_found": d.keywords_found,
							"pdf_status": getattr(d, "pdf_status", None),
							"local_path": getattr(d, "local_path", None),
						}
						f.write(json.dumps(row, ensure_ascii=False) + "\n")
			else:
				with open(out_path, "w", encoding="utf-8") as f:
					for d in sample:
						f.write(f"{d.id}\t{d.year or ''}\t{(d.relevance_score or 0):.3f}\t{(d.title or '').strip()}\n")
			console.print(f"[green]Wrote sample of {len(sample)} records to {args.out}[/green]")
			return 0
		finally:
			s.close()

	p_samp.set_defaults(func=_cmd_sample)

	# download-open (basic)
	p_dl = sub.add_parser("download-open", help="Download open-access links for a small batch")
	p_dl.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_dl.add_argument("--outdir", default=str(Path("data") / "files"))
	p_dl.add_argument("--limit", type=int, default=5)
	p_dl.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_dl.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

	def _cmd_dl(args: argparse.Namespace) -> int:
		from src.uwss.crawl import download_open_links, enrich_open_access_with_unpaywall
		data = load_config(Path(args.config))
		contact_email = data.get("contact_email")
		# Try to enrich OA first to improve hit rate
		enriched = enrich_open_access_with_unpaywall(Path(args.db), contact_email=contact_email, limit=50, db_url=getattr(args, "db_url", None))
		console.print(f"[blue]Enriched OA via Unpaywall: {enriched}[/blue]")
		n = download_open_links(Path(args.db), Path(args.outdir), limit=args.limit, contact_email=contact_email, db_url=getattr(args, "db_url", None))
		console.print(f"[green]Downloaded {n} files[/green]")
		return 0

	p_dl.set_defaults(func=_cmd_dl)

	# fetch: enrich OA + download
	p_fetch = sub.add_parser("fetch", help="Enrich OA (Unpaywall) then download files")
	p_fetch.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_fetch.add_argument("--outdir", default=str(Path("data") / "files"))
	p_fetch.add_argument("--limit", type=int, default=10)
	p_fetch.add_argument("--config", default=str(Path("config") / "config.yaml"))
	p_fetch.add_argument("--throttle-sec", type=float, default=None, help="Global per-host throttle seconds (override env UWSS_THROTTLE_SEC)")
	p_fetch.add_argument("--jitter-sec", type=float, default=None, help="Extra random jitter seconds (override env UWSS_JITTER_SEC)")
	p_fetch.add_argument("--log-json", action="store_true")
	p_fetch.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

	def _cmd_fetch(args: argparse.Namespace) -> int:
		from src.uwss.crawl import download_open_links, enrich_open_access_with_unpaywall
		start = time.time()
		data = load_config(Path(args.config))
		contact_email = data.get("contact_email")
		# allow overrides for throttle/jitter via flags
		if args.throttle_sec is not None:
			os.environ["UWSS_THROTTLE_SEC"] = str(args.throttle_sec)
		if args.jitter_sec is not None:
			os.environ["UWSS_JITTER_SEC"] = str(args.jitter_sec)
		# resolve publisher links first to improve pdf_url hit rate
		try:
			from src.uwss.crawl import resolve_publisher_links
			resolved = resolve_publisher_links(Path(args.db), limit=200, contact_email=contact_email, db_url=getattr(args, "db_url", None))
			_log_json(args.log_json, "resolve_publisher_done", resolved=resolved)
		except Exception:
			pass
		enriched = enrich_open_access_with_unpaywall(Path(args.db), contact_email=contact_email, limit=200, db_url=getattr(args, "db_url", None))
		console.print(f"[blue]Enriched OA via Unpaywall: {enriched}[/blue]")
		n = download_open_links(Path(args.db), Path(args.outdir), limit=args.limit, contact_email=contact_email, db_url=getattr(args, "db_url", None))
		console.print(f"[green]Downloaded {n} files[/green]")
		elapsed = round(time.time() - start, 3)
		_log_json(args.log_json, "fetch_done", elapsed_sec=elapsed, enriched=enriched, downloaded=n)
		return 0

	p_fetch.set_defaults(func=_cmd_fetch)

	# crawl-seeds (Scrapy wrapper)
	p_crawl = sub.add_parser("crawl-seeds", help="Crawl seed URLs using Scrapy and store candidates")
	p_crawl.add_argument("--seeds", required=True, help="Comma-separated seed URLs")
	p_crawl.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_crawl.add_argument("--max-pages", type=int, default=10)
	p_crawl.add_argument("--keywords-file", default=None)
	p_crawl.add_argument("--config", default=str(Path("config") / "config.yaml"), help="Path to config.yaml (for whitelist/blacklist)")

	def _cmd_crawl(args: argparse.Namespace) -> int:
		# Run seed_spider via Scrapy's CrawlerProcess programmatically
		try:
			from scrapy.crawler import CrawlerProcess
			from .crawl.scrapy_project.spiders.seed_spider import SeedSpider
			from .crawl.scrapy_project import settings as uwss_settings
			process = CrawlerProcess(settings={
				"ROBOTSTXT_OBEY": True,
				"DOWNLOAD_DELAY": 1.0,
				"CONCURRENT_REQUESTS_PER_DOMAIN": 2,
				"DEFAULT_REQUEST_HEADERS": {
					"User-Agent": "uwss/0.1 (respect robots)"
				},
			})
			# keywords
			keywords_csv = None
			if args.keywords_file:
				keywords_csv = ",".join([k.strip() for k in Path(args.keywords_file).read_text(encoding="utf-8").splitlines() if k.strip()])
			# whitelist/blacklist from config (optional)
			wl_csv = None
			bl_csv = None
			try:
				data = load_config(Path(args.config))
				wl = data.get("scrapy_whitelist_domains") or []
				bl = data.get("scrapy_path_blacklist") or []
				if wl:
					wl_csv = ",".join([str(d).strip() for d in wl if str(d).strip()])
				if bl:
					bl_csv = ",".join([str(p).strip() for p in bl if str(p).strip()])
			except Exception:
				pass
			process.crawl(SeedSpider, start_urls=args.seeds, db_path=args.db, max_pages=args.max_pages, keywords=keywords_csv, allowed_domains_extra=wl_csv, path_blocklist=bl_csv)
			process.start()
			console.print("[green]Seed crawl completed[/green]")
			return 0
		except Exception as e:
			console.print(f"[red]Seed crawl failed:[/red] {e}")
			return 1

	p_crawl.set_defaults(func=_cmd_crawl)
	
	# crawl-research (Research groups and faculty pages)
	p_research = sub.add_parser("crawl-research", help="Crawl research groups and faculty pages")
	p_research.add_argument("--seeds", required=False, help="Comma-separated seed URLs (or use --auto-seeds)")
	p_research.add_argument("--auto-seeds", action="store_true", help="Auto-discover seeds from database")
	p_research.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_research.add_argument("--max-pages", type=int, default=50)
	p_research.add_argument("--max-depth", type=int, default=3)
	p_research.add_argument("--keywords-file", default=None)
	p_research.add_argument("--config", default=str(Path("config") / "config.yaml"))
	
	def _cmd_research_crawl(args: argparse.Namespace) -> int:
		from scrapy.crawler import CrawlerProcess
		from src.uwss.crawl.scrapy_project.spiders.research_spider import ResearchSpider
		from .discovery.seed_finder import find_seeds_from_database
		
		try:
			# Get seeds
			seeds = []
			if args.auto_seeds:
				data = load_config(Path(args.config))
				keywords = data.get("domain_keywords", [])
				seeds = find_seeds_from_database(args.db, keywords=keywords, limit=20)
				console.print(f"[cyan]Auto-discovered {len(seeds)} seed URLs from database[/cyan]")
			elif args.seeds:
				seeds = args.seeds.split(",")
			else:
				console.print("[red]Error: Must provide --seeds or --auto-seeds[/red]")
				return 1
			
			if not seeds:
				console.print("[red]Error: No seed URLs found[/red]")
				return 1
			
			# Keywords
			keywords_csv = None
			if args.keywords_file:
				keywords_csv = ",".join([k.strip() for k in Path(args.keywords_file).read_text(encoding="utf-8").splitlines() if k.strip()])
			else:
				# Use keywords from config
				data = load_config(Path(args.config))
				keywords = data.get("domain_keywords", [])
				if keywords:
					keywords_csv = ",".join(keywords)
			
			# Run spider
			process = CrawlerProcess(settings={
				"ROBOTSTXT_OBEY": True,
				"DOWNLOAD_DELAY": 2.0,
				"CONCURRENT_REQUESTS_PER_DOMAIN": 1,
			})
			process.crawl(
				ResearchSpider,
				start_urls=",".join(seeds),
				db_path=args.db,
				max_pages=args.max_pages,
				max_depth=args.max_depth,
				keywords=keywords_csv
			)
			process.start()
			console.print("[green]Research crawl completed[/green]")
			return 0
		except Exception as e:
			console.print(f"[red]Research crawl failed:[/red] {e}")
			import traceback
			traceback.print_exc()
			return 1
	
	p_research.set_defaults(func=_cmd_research_crawl)
	
	# crawl-pdfs (PDF discovery spider)
	p_pdf = sub.add_parser("crawl-pdfs", help="Discover and extract PDFs from web pages")
	p_pdf.add_argument("--seeds", required=False, help="Comma-separated seed URLs (or use --auto-seeds)")
	p_pdf.add_argument("--auto-seeds", action="store_true", help="Auto-discover seeds from database")
	p_pdf.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_pdf.add_argument("--max-pages", type=int, default=100)
	p_pdf.add_argument("--max-depth", type=int, default=2)
	p_pdf.add_argument("--keywords-file", default=None)
	p_pdf.add_argument("--config", default=str(Path("config") / "config.yaml"))
	
	def _cmd_pdf_crawl(args: argparse.Namespace) -> int:
		from scrapy.crawler import CrawlerProcess
		from src.uwss.crawl.scrapy_project.spiders.pdf_spider import PDFSpider
		from src.uwss.discovery.seed_finder import find_seeds_from_database, find_seeds_from_papers
		
		try:
			# Get seeds
			seeds = []
			if args.auto_seeds:
				data = load_config(Path(args.config))
				keywords = data.get("domain_keywords", [])
				# Try multiple seed discovery methods
				seeds1 = find_seeds_from_database(args.db, keywords=keywords, limit=20)
				seeds2 = find_seeds_from_papers(args.db, limit=20)
				seeds = list(set(seeds1 + seeds2))  # Deduplicate
				console.print(f"[cyan]Auto-discovered {len(seeds)} seed URLs from database[/cyan]")
			elif args.seeds:
				seeds = args.seeds.split(",")
			else:
				console.print("[red]Error: Must provide --seeds or --auto-seeds[/red]")
				return 1
			
			if not seeds:
				console.print("[red]Error: No seed URLs found[/red]")
				return 1
			
			# Keywords
			keywords_csv = None
			if args.keywords_file:
				keywords_csv = ",".join([k.strip() for k in Path(args.keywords_file).read_text(encoding="utf-8").splitlines() if k.strip()])
			else:
				data = load_config(Path(args.config))
				keywords = data.get("domain_keywords", [])
				if keywords:
					keywords_csv = ",".join(keywords)
			
			# Run spider
			process = CrawlerProcess(settings={
				"ROBOTSTXT_OBEY": True,
				"DOWNLOAD_DELAY": 1.5,
				"CONCURRENT_REQUESTS_PER_DOMAIN": 1,
			})
			process.crawl(
				PDFSpider,
				start_urls=",".join(seeds),
				db_path=args.db,
				max_pages=args.max_pages,
				max_depth=args.max_depth,
				keywords=keywords_csv
			)
			process.start()
			console.print("[green]PDF discovery crawl completed[/green]")
			return 0
		except Exception as e:
			console.print(f"[red]PDF crawl failed:[/red] {e}")
			import traceback
			traceback.print_exc()
			return 1
	
	p_pdf.set_defaults(func=_cmd_pdf_crawl)
	
	# discover-seeds (Seed discovery utility)
	p_seeds = sub.add_parser("discover-seeds", help="Discover seed URLs from database")
	p_seeds.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_seeds.add_argument("--limit", type=int, default=50)
	p_seeds.add_argument("--out", default=None, help="Output file for seeds (one per line)")
	p_seeds.add_argument("--config", default=str(Path("config") / "config.yaml"))
	
	def _cmd_discover_seeds(args: argparse.Namespace) -> int:
		from src.uwss.discovery.seed_finder import find_seeds_from_database, find_seeds_from_papers
		
		try:
			data = load_config(Path(args.config))
			keywords = data.get("domain_keywords", [])
			
			# Discover seeds
			seeds1 = find_seeds_from_database(args.db, keywords=keywords, limit=args.limit)
			seeds2 = find_seeds_from_papers(args.db, limit=args.limit)
			seeds = list(set(seeds1 + seeds2))  # Deduplicate
			
			console.print(f"[green]Discovered {len(seeds)} seed URLs[/green]")
			
			# Print seeds
			for seed in seeds[:20]:  # Show first 20
				console.print(f"  {seed}")
			if len(seeds) > 20:
				console.print(f"  ... and {len(seeds) - 20} more")
			
			# Save to file if requested
			if args.out:
				with open(args.out, 'w', encoding='utf-8') as f:
					for seed in seeds:
						f.write(f"{seed}\n")
				console.print(f"[green]Saved seeds to {args.out}[/green]")
			
			return 0
		except Exception as e:
			console.print(f"[red]Seed discovery failed:[/red] {e}")
			return 1
	
	p_seeds.set_defaults(func=_cmd_discover_seeds)

	# stats
	p_stats = sub.add_parser("stats", help="Show dataset statistics (counts, OA ratio, by source/year)")
	p_stats.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_stats.add_argument("--json-out", default=None)
	p_stats.add_argument("--log-json", action="store_true")

	def _cmd_stats(args: argparse.Namespace) -> int:
		from sqlalchemy import select, func
		from src.uwss.store.models import Document
		import json
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		s = SessionLocal()
		start = time.time()
		try:
			stats = {}
			# totals
			total = s.execute(select(func.count(Document.id))).scalar() or 0
			stats["total"] = total
			# oa
			oa = s.execute(select(func.count(Document.id)).where(Document.open_access == True)).scalar() or 0
			stats["open_access"] = oa
			# by source
			rows = s.execute(select(Document.source, func.count(Document.id)).group_by(Document.source)).all()
			stats["by_source"] = {str(k): v for k, v in rows}
			# by year
			years = s.execute(select(Document.year, func.count(Document.id)).where(Document.year != None).group_by(Document.year)).all()
			stats["by_year"] = {int(k): v for k, v in years if k is not None}
			console.print(stats)
			if args.json_out:
				Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
				Path(args.json_out).write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
				console.print(f"[green]Saved stats to {args.json_out}[/green]")
			elapsed = round(time.time() - start, 3)
			_log_json(args.log_json, "stats_done", elapsed_sec=elapsed, **stats)
			return 0
		finally:
			s.close()

	p_stats.set_defaults(func=_cmd_stats)

	# recent-downloads
	p_recent = sub.add_parser("recent-downloads", help="List recently fetched PDFs (most recent first)")
	p_recent.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_recent.add_argument("--hours", type=int, default=24, help="Look back window in hours")
	p_recent.add_argument("--limit", type=int, default=20)
	p_recent.add_argument("--source", default=None, help="Optional source filter, e.g., arxiv")
	p_recent.add_argument("--json-out", default=None)

	def _cmd_recent(args: argparse.Namespace) -> int:
		from sqlalchemy import select
		from datetime import datetime, timedelta
		from .store import Document
		import json
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		s = SessionLocal()
		try:
			cutoff = datetime.utcnow() - timedelta(hours=max(0, int(args.hours)))
			q = select(Document.id, Document.title, Document.year, Document.topic, Document.local_path, Document.pdf_fetched_at, Document.source, Document.checksum_sha256).where(Document.pdf_fetched_at != None).where(Document.pdf_fetched_at >= cutoff)
			if getattr(args, "source", None):
				q = q.where(Document.source == args.source)
			q = q.order_by(Document.pdf_fetched_at.desc()).limit(int(args.limit))
			rows = s.execute(q).all()
			items = []
			for (_id, title, year, topic, path, fetched_at, source, sha) in rows:
				items.append({
					"id": int(_id),
					"title": title,
					"year": int(year) if year is not None else None,
					"topic": topic,
					"local_path": path,
					"fetched_at": fetched_at.isoformat() + "Z" if fetched_at else None,
					"source": source,
					"sha256": sha,
				})
			console.print(items)
			if getattr(args, "json_out", None):
				Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
				Path(args.json_out).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
				console.print(f"[green]Saved recent list to {args.json_out}[/green]")
			return 0
		finally:
			s.close()

	p_recent.set_defaults(func=_cmd_recent)

	# runs-summary (quick ledger over data/runs/*.json)
	p_rsum = sub.add_parser("runs-summary", help="Summarize recent run metrics under data/runs")
	p_rsum.add_argument("--dir", dest="runs_dir", default=str(Path("data") / "runs"))
	p_rsum.add_argument("--limit", type=int, default=50)
	p_rsum.add_argument("--out", default=None)

	def _cmd_rsum(args: argparse.Namespace) -> int:
		import json, glob, os, time
		items = []
		pattern = str(Path(args.runs_dir) / "*.json")
		paths = sorted(glob.glob(pattern), key=lambda p: os.path.getmtime(p), reverse=True)
		for p in paths[: int(args.limit)]:
			try:
				data = json.loads(Path(p).read_text(encoding="utf-8"))
				entry = {
					"file": p,
					"mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(p))),
				}
				# classify
				if all(k in data for k in ("inserted", "pages")):
					entry.update({"kind": "harvest", "inserted": data.get("inserted"), "pages": data.get("pages"), "failed": data.get("failed"), "elapsed_sec": data.get("elapsed_sec")})
				elif all(k in data for k in ("attempted", "downloaded")):
					entry.update({"kind": "fetch", "attempted": data.get("attempted"), "downloaded": data.get("downloaded"), "failed": data.get("failed"), "bytes": data.get("bytes_downloaded")})
				elif all(k in data for k in ("attempted", "parsed_ok")):
					entry.update({"kind": "grobid", "attempted": data.get("attempted"), "ok": data.get("parsed_ok"), "fail": data.get("parsed_fail")})
				else:
					entry.update({"kind": "other"})
				items.append(entry)
			except Exception:
				continue
		console.print(items)
		if getattr(args, "out", None):
			try:
				Path(args.out).parent.mkdir(parents=True, exist_ok=True)
				Path(args.out).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
				console.print(f"[green]Saved runs summary to {args.out}[/green]")
			except Exception:
				pass
		return 0

	p_rsum.set_defaults(func=_cmd_rsum)

	# validate
	p_val = sub.add_parser("validate", help="Validate data quality: duplicates, missing fields, invalid years, broken files")
	p_val.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_val.add_argument("--json-out", default=None)

	def _cmd_validate(args: argparse.Namespace) -> int:
		from sqlalchemy import select, func
		from .store import Document
		import json, os
		engine, SessionLocal = _get_engine_session(args, Path(args.db))
		s = SessionLocal()
		issues = {"dup_doi": [], "dup_title": [], "missing_core": [], "invalid_year": [], "missing_files": []}
		try:
			# dup doi
			dup_doi = s.execute(select(Document.doi, func.count(Document.id)).where(Document.doi != None).group_by(Document.doi).having(func.count(Document.id) > 1)).all()
			issues["dup_doi"] = [{"doi": str(k), "count": int(c)} for (k, c) in dup_doi]
			# dup title (case-insensitive)
			dup_title = s.execute(select(func.lower(Document.title), func.count(Document.id)).where(Document.title != None).group_by(func.lower(Document.title)).having(func.count(Document.id) > 1)).all()
			issues["dup_title"] = [{"title": str(k), "count": int(c)} for (k, c) in dup_title]
			# missing core fields
			rows = s.execute(select(Document.id, Document.title, Document.doi)).all()
			for _id, title, doi in rows:
				if not (title or doi):
					issues["missing_core"].append(int(_id))
			# invalid year
			rows = s.execute(select(Document.id, Document.year)).all()
			for _id, year in rows:
				if year is not None and (year < 1900 or year > 2100):
					issues["invalid_year"].append(int(_id))
			# missing files
			rows = s.execute(select(Document.id, Document.local_path)).all()
			for _id, p in rows:
				if p and not os.path.exists(p):
					issues["missing_files"].append(int(_id))
			console.print(issues)
			if args.json_out:
				Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
				Path(args.json_out).write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding="utf-8")
				console.print(f"[green]Saved validation to {args.json_out}[/green]")
			return 0
		finally:
			s.close()

	p_val.set_defaults(func=_cmd_validate)

	# dedupe-resolve
	p_dedupe = sub.add_parser("dedupe-resolve", help="Resolve duplicates (DOI/title) and keep best record")
	p_dedupe.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))

	def _cmd_dedupe(args: argparse.Namespace) -> int:
		from .clean import resolve_duplicates
		res = resolve_duplicates(Path(args.db))
		console.print(res)
		return 0

	p_dedupe.set_defaults(func=_cmd_dedupe)

	# dedupe-resolve-fuzzy
	p_dfz = sub.add_parser("dedupe-resolve-fuzzy", help="Resolve duplicates by fuzzy title matching")
	p_dfz.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p_dfz.add_argument("--threshold", type=float, default=0.9)

	def _cmd_dfz(args: argparse.Namespace) -> int:
		from .clean import resolve_duplicates_fuzzy
		merged = resolve_duplicates_fuzzy(Path(args.db), threshold=args.threshold)
		console.print(f"[green]Fuzzy merged {merged} duplicates[/green]")
		return 0

	p_dfz.set_defaults(func=_cmd_dfz)

	# normalize-metadata
	p_norm = sub.add_parser("normalize-metadata", help="Normalize authors/venue/title/doi formatting")
	p_norm.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))

	def _cmd_norm(args: argparse.Namespace) -> int:
		from .clean import normalize_metadata
		n = normalize_metadata(Path(args.db))
		console.print(f"[green]Normalized {n} records[/green]")
		return 0

	p_norm.set_defaults(func=_cmd_norm)

	# backfill-source
	p_bfs = sub.add_parser("backfill-source", help="Backfill missing Document.source from URL/venue")
	p_bfs.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))

	def _cmd_bfs(args: argparse.Namespace) -> int:
		from .clean import backfill_source
		n = backfill_source(Path(args.db))
		console.print(f"[green]Backfilled source for {n} records[/green]")
		return 0

	p_bfs.set_defaults(func=_cmd_bfs)

	return parser


def main(argv: Any = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)
	if not hasattr(args, "func"):
		parser.print_help()
		return 0
	return int(args.func(args))


if __name__ == "__main__":
	sys.exit(main())


