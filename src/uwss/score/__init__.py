"""Keyword-based relevance scoring for discovered documents.

FOCUS: DATA QUALITY and RELEVANCE, not just metadata extraction.

The scorer builds a lightweight lexicon from domain keywords (unigrams and
bigrams) and computes a normalized score from title, abstract, and full-text content.

Features:
- Title-weighted scoring (title contributes more than abstract).
- Full-text scoring when available (better quality assessment).
- Quality bonus for complete data (abstract, authors, DOI, etc.).
- Records the matched keyword phrases into `keywords_found` for explainability.
- Optional negative keywords: if present, applies a penalty to reduce the final score.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Set, Optional

from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker

from ..store.models import Document


def _tokenize(text: str) -> List[str]:
	if not text:
		return []
	return re.findall(r"[a-z0-9]+", text.lower())


def _bigrams(tokens: List[str]) -> List[str]:
	return [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1)] if len(tokens) > 1 else []


def _build_keyword_lexicon(keywords: Iterable[str]) -> Dict[str, Set[str]]:
	uni: Set[str] = set()
	bi: Set[str] = set()
	phrases: List[str] = []
	for kw in keywords:
		phrases.append(kw)
		kt = _tokenize(kw)
		uni.update(kt)
		bi.update(_bigrams(kt))
	return {"uni": uni, "bi": bi, "phrases": set(phrases)}


def _score_text(tokens: List[str], bi_tokens: List[str], kw_uni: Set[str], kw_bi: Set[str]) -> float:
	if not tokens:
		return 0.0
	uni_hits = len(set(tokens) & kw_uni)
	bi_hits = len(set(bi_tokens) & kw_bi)
	# Combine hits with higher weight for bigrams; normalize by sqrt length to reduce bias
	raw = uni_hits + 2.0 * bi_hits
	norm = max(1.0, (len(tokens) ** 0.5))
	return raw / norm


def score_documents(
	db_path: Path,
	keywords: List[str],
	min_score: float = 0.0,
	db_url: str | None = None,
	negative_keywords: Optional[List[str]] = None,
	use_fulltext: bool = True
) -> int:
	"""Score documents by relevance to keywords.
	
	FOCUS: DATA QUALITY and RELEVANCE.
	- Uses full-text content when available for better quality assessment
	- Rewards complete data (abstract, authors, DOI, etc.)
	- Strong penalty for negative keywords to ensure quality
	
	Args:
		db_path: Path to SQLite database
		keywords: List of positive keywords
		min_score: Minimum score threshold (not used in scoring, only for filtering)
		db_url: Optional database URL
		negative_keywords: List of negative keywords (penalty)
		use_fulltext: If True, use full-text content for scoring when available
	"""
	# Lightweight local engine factory to avoid importing store.db at import time
	if db_url:
		engine = create_engine(db_url, future=True)
	else:
		engine = create_engine(f"sqlite:///{db_path}", future=True)
	SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
	session = SessionLocal()
	try:
		lex = _build_keyword_lexicon(keywords)
		neg_lex = _build_keyword_lexicon(negative_keywords or []) if negative_keywords else {"uni": set(), "bi": set(), "phrases": set()}
		kw_uni, kw_bi = lex["uni"], lex["bi"]
		n_uni, n_bi = neg_lex["uni"], neg_lex["bi"]
		q = session.execute(select(Document))
		updated = 0
		for (doc,) in q:
			# normalize basic fields for cleanliness
			if doc.doi:
				doc.doi = doc.doi.strip().lower()
			if doc.title:
				doc.title = doc.title.strip()
			if doc.abstract:
				doc.abstract = doc.abstract.strip()
			
			# Collect all text for scoring (prioritize quality data)
			text_parts = []
			
			# Title (high weight)
			title_text = doc.title or ""
			if title_text:
				text_parts.append(("title", title_text))
			
			# Abstract (high weight)
			abstract_text = doc.abstract or ""
			if abstract_text:
				text_parts.append(("abstract", abstract_text))
			
			# Full-text content (if available - BEST for quality scoring)
			fulltext = None
			if use_fulltext and doc.content_path:
				try:
					content_file = Path(doc.content_path)
					if content_file.exists():
						fulltext = content_file.read_text(encoding='utf-8', errors='ignore')
						if fulltext and len(fulltext) > 100:  # Only use if substantial
							text_parts.append(("fulltext", fulltext[:5000]))  # Limit to first 5000 chars for performance
				except Exception:
					pass
			
			# Keywords (if available)
			if doc.keywords:
				try:
					keywords_data = json.loads(doc.keywords) if isinstance(doc.keywords, str) else doc.keywords
					if isinstance(keywords_data, list):
						keywords_text = " ".join(str(k) for k in keywords_data)
						if keywords_text:
							text_parts.append(("keywords", keywords_text))
				except Exception:
					pass
			
			# If no text available, skip scoring (low quality data)
			if not text_parts:
				doc.relevance_score = 0.0
				doc.keywords_found = json.dumps([])
				updated += 1
				continue
			
			# Tokenize all text parts
			all_tokens = []
			all_bigrams = []
			title_tokens = []
			title_bigrams = []
			abstract_tokens = []
			abstract_bigrams = []
			
			for part_type, text in text_parts:
				tokens = _tokenize(text)
				bigrams = _bigrams(tokens)
				all_tokens.extend(tokens)
				all_bigrams.extend(bigrams)
				
				if part_type == "title":
					title_tokens = tokens
					title_bigrams = bigrams
				elif part_type == "abstract":
					abstract_tokens = tokens
					abstract_bigrams = bigrams
			
			# Calculate scores for each part
			s_title = _score_text(title_tokens, title_bigrams, kw_uni, kw_bi) if title_tokens else 0.0
			s_abs = _score_text(abstract_tokens, abstract_bigrams, kw_uni, kw_bi) if abstract_tokens else 0.0
			s_fulltext = _score_text(all_tokens, all_bigrams, kw_uni, kw_bi) if all_tokens else 0.0
			
			# Weighted scoring (prioritize quality sources)
			# Title: 40%, Abstract: 30%, Fulltext: 30% (if available)
			if fulltext:
				score = min(1.0, 0.4 * s_title + 0.3 * s_abs + 0.3 * s_fulltext)
			else:
				# Without fulltext: Title 60%, Abstract 40%
				score = min(1.0, 0.6 * s_title + 0.4 * s_abs)
			
			# Quality bonus: Reward complete, high-quality data
			quality_bonus = 0.0
			if doc.abstract and len(doc.abstract) > 200:  # Substantial abstract
				quality_bonus += 0.1
			if doc.authors:  # Has authors
				quality_bonus += 0.05
			if doc.year:  # Has year
				quality_bonus += 0.05
			if doc.doi:  # Has DOI (reliable source)
				quality_bonus += 0.1
			if fulltext:  # Has full-text content (very rich data)
				quality_bonus += 0.1
			if doc.affiliations:  # Has affiliations
				quality_bonus += 0.05
			
			score = min(1.0, score + quality_bonus)
			
			# Negative keywords penalty (stronger penalty for quality filtering)
			if negative_keywords:
				all_text_uni = set(all_tokens)
				all_text_bi = set(all_bigrams)
				neg_hits = len(all_text_uni & n_uni) + len(all_text_bi & n_bi)
				if neg_hits > 0:
					# Strong penalty: reduce score significantly
					penalty_factor = max(0.1, 1.0 - (neg_hits * 0.3))  # Each negative hit reduces by 30%
					score = score * penalty_factor
			
			doc.relevance_score = float(score)
			
			# keywords_found: include phrases whose any token appears (or bigram present)
			found = []
			text_uni = set(all_tokens)
			text_bi = set(all_bigrams)
			for phrase in lex["phrases"]:
				ptoks = set(_tokenize(phrase))
				pbis = set(_bigrams(list(ptoks)))
				if (ptoks & text_uni) or (pbis & text_bi):
					found.append(phrase)
			doc.keywords_found = json.dumps(sorted(set(found)))
			updated += 1
		session.commit()
		return updated
	finally:
		session.close()
