from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Text, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
	pass


class Document(Base):
	__tablename__ = "documents"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	source_url: Mapped[str] = mapped_column(String(1000))
	landing_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
	pdf_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
	doi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	title: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
	authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of author names
	affiliations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of affiliations
	keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of keywords/subjects
	venue: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
	pub_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
	file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	open_access: Mapped[bool] = mapped_column(Boolean, default=False)
	abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	local_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
	content_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
	content_chars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
	keywords_found: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of matched keywords
	relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
	status: Mapped[str] = mapped_column(String(40), default="not_fetched")
	# PDF fetch specific status and timestamps
	pdf_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
	source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # crossref|arxiv|openalex|...
	topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
	# content summary and types
	mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
	text_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

	# provenance
	fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
	pdf_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
	http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
	extractor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
	license: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
	oa_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	# file integrity
	checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
	# url hash for dedupe
	url_hash_sha1: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)


class IngestionState(Base):
	__tablename__ = "ingestion_state"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	source: Mapped[str] = mapped_column(String(50))
	checkpoint_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
	checkpoint_value: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
	updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class VisitedUrl(Base):
	__tablename__ = "visited_urls"

	url: Mapped[str] = mapped_column(String(1000), primary_key=True)
	first_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
	last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
	status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


