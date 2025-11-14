"""Database engines and lightweight migrations.

This module abstracts engine creation for SQLite/Postgres and provides a
minimal migration routine for the SQLite file-based schema used in local runs.
In Postgres, we rely on SQLAlchemy metadata and ad-hoc CREATE INDEX commands
exposed via CLI (`db-create-indexes`).
"""
from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy import text as sql_text
from sqlalchemy.orm import sessionmaker

from .models import Base


def create_sqlite_engine(db_path: Path):
	engine = create_engine(f"sqlite:///{db_path}", future=True)
	SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
	return engine, SessionLocal


def create_engine_from_url(db_url: str):
	"""Create engine/session from a full DB URL (e.g., Postgres on RDS).
	Example: postgresql+psycopg2://user:pass@host:5432/dbname
	"""
	engine = create_engine(db_url, future=True)
	SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
	return engine, SessionLocal


def init_db(db_path: Path) -> None:
	engine, _ = create_sqlite_engine(db_path)
	Base.metadata.create_all(engine)


def migrate_db(db_path: Path) -> None:
	engine, _ = create_sqlite_engine(db_path)
	with engine.connect() as conn:
		cols = conn.execute(sql_text("PRAGMA table_info(documents)")).fetchall()
		names = {c[1] for c in cols}
		# New identification fields
		if "landing_url" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN landing_url VARCHAR(1000)"))
			conn.commit()
		if "pdf_url" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN pdf_url VARCHAR(1000)"))
			conn.commit()
		if "file_size" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN file_size INTEGER"))
			conn.commit()
		if "pub_date" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN pub_date VARCHAR(20)"))
			conn.commit()
		if "source" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN source VARCHAR(50)"))
			conn.commit()
		if "oa_status" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN oa_status VARCHAR(50)"))
			conn.commit()
		if "topic" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN topic VARCHAR(100)"))
			conn.commit()
		if "checksum_sha256" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN checksum_sha256 VARCHAR(64)"))
			conn.commit()
		if "pdf_status" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN pdf_status VARCHAR(40)"))
			conn.commit()
		if "mime_type" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN mime_type VARCHAR(100)"))
			conn.commit()
		if "text_excerpt" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN text_excerpt TEXT"))
			conn.commit()
		# New scholarly fields
		if "affiliations" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN affiliations TEXT"))
			conn.commit()
		if "keywords" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN keywords TEXT"))
			conn.commit()
		if "url_hash_sha1" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN url_hash_sha1 VARCHAR(40)"))
			conn.commit()
		if "content_path" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN content_path VARCHAR(1000)"))
			conn.commit()
		if "content_chars" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN content_chars INTEGER"))
			conn.commit()
		if "pdf_fetched_at" not in names:
			conn.execute(sql_text("ALTER TABLE documents ADD COLUMN pdf_fetched_at DATETIME"))
			conn.commit()
		# Ensure visited_urls registry table exists
		conn.execute(sql_text(
			"""
			CREATE TABLE IF NOT EXISTS visited_urls (
				url VARCHAR(1000) PRIMARY KEY,
				first_seen DATETIME NULL,
				last_seen DATETIME NULL,
				status VARCHAR(50) NULL
			)
			"""
		))
		conn.commit()
		# Ensure ingestion_state table exists
		conn.execute(sql_text(
			"""
			CREATE TABLE IF NOT EXISTS ingestion_state (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				source VARCHAR(50) NOT NULL,
				checkpoint_key VARCHAR(100) NULL,
				checkpoint_value VARCHAR(1000) NULL,
				updated_at DATETIME NULL
			)
			"""
		))
		conn.commit()


