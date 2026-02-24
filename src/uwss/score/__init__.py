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
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

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


def _clamp01(x: float) -> float:
	try:
		if x < 0.0:
			return 0.0
		if x > 1.0:
			return 1.0
		return float(x)
	except Exception:
		return 0.0


def _compile_phrase_patterns(phrases: Iterable[str]) -> List[re.Pattern]:
	"""Compile phrase regexes conservatively (word-boundary-like), case-insensitive.

	We avoid over-smart parsing: phrases come from config and may contain spaces/hyphens.
	"""
	pats: List[re.Pattern] = []
	for raw in phrases:
		s = str(raw or "").strip()
		if not s:
			continue
		# Normalize whitespace and escape regex meta, then allow flexible whitespace.
		esc = re.escape(re.sub(r"\s+", " ", s.lower()))
		esc = esc.replace(r"\ ", r"\s+")
		# Basic boundaries: non-alnum edges (works for most technical phrases).
		pat = re.compile(rf"(?<![a-z0-9]){esc}(?![a-z0-9])", re.IGNORECASE)
		pats.append(pat)
	return pats


def _count_pattern_hits(text: str, patterns: List[re.Pattern], *, max_hits: int = 50) -> int:
	if not text or not patterns:
		return 0
	n = 0
	for p in patterns:
		try:
			# Using finditer allows overlap control; cap to avoid pathological cases.
			for _ in p.finditer(text):
				n += 1
				if n >= max_hits:
					return n
		except Exception:
			continue
	return n


def _build_scoring_text(doc: Document, *, use_fulltext: bool) -> Tuple[List[Tuple[str, str]], Optional[str]]:
	"""Return (text_parts, fulltext_or_none) consistent with v1 scoring."""
	text_parts: List[Tuple[str, str]] = []
	title_text = doc.title or ""
	if title_text:
		text_parts.append(("title", title_text))
	abstract_text = doc.abstract or ""
	if abstract_text:
		text_parts.append(("abstract", abstract_text))

	fulltext = None
	if use_fulltext and doc.content_path:
		try:
			content_file = Path(doc.content_path)
			if content_file.exists():
				fulltext = content_file.read_text(encoding="utf-8", errors="ignore")
				if fulltext and len(fulltext) > 100:
					text_parts.append(("fulltext", fulltext[:5000]))
		except Exception:
			fulltext = None

	if doc.keywords:
		try:
			keywords_data = json.loads(doc.keywords) if isinstance(doc.keywords, str) else doc.keywords
			if isinstance(keywords_data, list):
				keywords_text = " ".join(str(k) for k in keywords_data)
				if keywords_text:
					text_parts.append(("keywords", keywords_text))
		except Exception:
			pass

	return text_parts, fulltext


def _base_score_and_keywords_found(
	*,
	doc: Document,
	lex: Dict[str, Set[str]],
	neg_lex: Dict[str, Set[str]],
	negative_keywords: Optional[List[str]],
	use_fulltext: bool,
) -> Tuple[float, List[str]]:
	"""Compute the existing (v1) relevance_score + keywords_found list.

	Kept separate so new profiles can reuse the base score without changing default behavior.
	"""
	kw_uni, kw_bi = lex["uni"], lex["bi"]
	n_uni, n_bi = neg_lex["uni"], neg_lex["bi"]

	text_parts, fulltext = _build_scoring_text(doc, use_fulltext=use_fulltext)
	if not text_parts:
		return 0.0, []

	all_tokens: List[str] = []
	all_bigrams: List[str] = []
	title_tokens: List[str] = []
	title_bigrams: List[str] = []
	abstract_tokens: List[str] = []
	abstract_bigrams: List[str] = []

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

	s_title = _score_text(title_tokens, title_bigrams, kw_uni, kw_bi) if title_tokens else 0.0
	s_abs = _score_text(abstract_tokens, abstract_bigrams, kw_uni, kw_bi) if abstract_tokens else 0.0
	s_fulltext = _score_text(all_tokens, all_bigrams, kw_uni, kw_bi) if all_tokens else 0.0

	if fulltext:
		score = min(1.0, 0.4 * s_title + 0.3 * s_abs + 0.3 * s_fulltext)
	else:
		score = min(1.0, 0.6 * s_title + 0.4 * s_abs)

	quality_bonus = 0.0
	if doc.abstract and len(doc.abstract) > 200:
		quality_bonus += 0.1
	if doc.authors:
		quality_bonus += 0.05
	if doc.year:
		quality_bonus += 0.05
	if doc.doi:
		quality_bonus += 0.1
	if fulltext:
		quality_bonus += 0.1
	if getattr(doc, "affiliations", None):
		quality_bonus += 0.05

	score = min(1.0, score + quality_bonus)

	if negative_keywords:
		all_text_uni = set(all_tokens)
		all_text_bi = set(all_bigrams)
		neg_hits = len(all_text_uni & n_uni) + len(all_text_bi & n_bi)
		if neg_hits > 0:
			penalty_factor = max(0.1, 1.0 - (neg_hits * 0.3))
			score = score * penalty_factor

	text_uni = set(all_tokens)
	text_bi = set(all_bigrams)
	found: List[str] = []
	for phrase in lex["phrases"]:
		ptoks = set(_tokenize(phrase))
		pbis = set(_bigrams(list(ptoks)))
		if (ptoks & text_uni) or (pbis & text_bi):
			found.append(phrase)
	return float(score), sorted(set(found))


def _get_profile_config(profile: str, profile_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
	if not profile_config:
		return {}
	profiles = profile_config.get("screening_profiles")
	if not isinstance(profiles, dict):
		return {}
	cfg = profiles.get(profile)
	return cfg if isinstance(cfg, dict) else {}


def _damage_v4_2_defaults() -> Dict[str, Any]:
	"""Conservative defaults for Damage-Oriented screening (V4.2).

	These are intended as a starter set; teams should override via config.
	"""
	return {
		"positive_phrases": {
			"field_data": [
				"bridge management system",
				"national bridge inventory",
				"bridge inspection",
				"inspection database",
				"inspection record",
				"condition rating",
				"dot inspection",
				"bms data",
				"nbi data",
			],
			"time_evolving_damage": [
				"time series",
				"time-dependent",
				"damage evolution",
				"deterioration trajectory",
				"condition rating progression",
				"aging curve",
				"deterioration curve",
				"multi-year",
				"service-life prediction",
				"damage index",
				"durability performance index",
				"dpi",
			],
			"data_driven_modeling": [
				"data-driven",
				"statistical model",
				"bayesian",
				"regression model",
				"survival analysis",
				"markov",
				"hazard model",
				"reliability-based",
				"calibration",
			],
		},
		"negative_phrases": {
			"material_enhancement_only": [
				"fiber reinforced",
				"steel fiber",
				"basalt fiber",
				"hybrid fiber",
				"fly ash",
				"silica fume",
				"nano silica",
				"nano",
				"geopolymer",
				"mix design",
				"additive",
				"uhpc",
				"ultra-high performance",
				"high performance concrete",
				"recycled aggregate",
				"rac",
				"rca",
				"co2 curing",
				"carbonation curing",
			],
			"mechanical_properties_only": [
				"compressive strength",
				"flexural strength",
				"split tensile",
				"mechanical properties",
				"upv",
				"ultrasonic pulse velocity",
				"rcpt",
				"rapid chloride permeability",
				"permeability",
				"porosity",
				"sorptivity",
			],
			"short_term_lab_only": [
				"accelerated test",
				"short-term",
				"28 days",
				"7 days",
				"early age",
				"curing time",
			],
			"simulation_only": [
				"finite element",
				"numerical simulation",
				"computational model",
				"simulation study",
				"finite element analysis",
				"fea",
			],
			# Mild penalty: transport-property papers often are not trajectory/inspection-focused.
			"transport_properties_only": [
				"chloride diffusion",
				"diffusion coefficient",
				"chloride migration",
				"migration coefficient",
				"fick",
				"c-s-h",
				"calcium silicate hydrate",
				"capillary pores",
				"gel pores",
				"pore structure",
			],
		},
		"bonuses": {
			"field_data": 0.25,
			"time_evolving_damage": 0.25,
			"data_driven_modeling": 0.10,
		},
		"penalties": {
			# multiplicative factor applied once per matched negative category (smaller = harsher)
			"category_factor": 0.20,
			# optional per-category override (lets us be strict without killing recall)
			"per_category_factor": {
				"material_enhancement_only": 0.20,
				"mechanical_properties_only": 0.20,
				"short_term_lab_only": 0.30,
				"simulation_only": 0.20,
				"transport_properties_only": 0.70,
			},
		},
		"qualification": {
			# Only apply "qualification gate" when score is already high.
			"high_score_threshold": 0.75,
			"must_have_any": ["field_data", "time_evolving_damage"],
			"cap_if_unqualified": 0.49,
		},
	}


def _damage_v4_2_adjust(
	*,
	doc: Document,
	base_score: float,
	use_fulltext: bool,
	profile_cfg: Dict[str, Any],
) -> Tuple[float, bool, Dict[str, Any]]:
	"""Apply V4.2 penalty/bonus + high-score qualification gate."""
	cfg = _damage_v4_2_defaults()
	# Merge profile_cfg shallowly (user config wins at top-level keys)
	for k, v in (profile_cfg or {}).items():
		cfg[k] = v

	pos = cfg.get("positive_phrases") if isinstance(cfg.get("positive_phrases"), dict) else {}
	neg = cfg.get("negative_phrases") if isinstance(cfg.get("negative_phrases"), dict) else {}
	bonuses = cfg.get("bonuses") if isinstance(cfg.get("bonuses"), dict) else {}
	penalties = cfg.get("penalties") if isinstance(cfg.get("penalties"), dict) else {}
	qualification = cfg.get("qualification") if isinstance(cfg.get("qualification"), dict) else {}

	text_parts, _full = _build_scoring_text(doc, use_fulltext=use_fulltext)
	joined = "\n".join(t for _, t in text_parts).lower()

	pos_hits: Dict[str, int] = {}
	neg_hits: Dict[str, int] = {}

	for cat, phrases in pos.items():
		if isinstance(phrases, list):
			pats = _compile_phrase_patterns(phrases)
			pos_hits[str(cat)] = _count_pattern_hits(joined, pats)
	for cat, phrases in neg.items():
		if isinstance(phrases, list):
			pats = _compile_phrase_patterns(phrases)
			neg_hits[str(cat)] = _count_pattern_hits(joined, pats)

	bonus = 0.0
	for cat, n in pos_hits.items():
		if n > 0:
			try:
				bonus += float(bonuses.get(cat, 0.0))
			except Exception:
				pass

	category_factor = penalties.get("category_factor", 0.20)
	try:
		category_factor_f = float(category_factor)
	except Exception:
		category_factor_f = 0.20

	per_cat = penalties.get("per_category_factor", {})
	if not isinstance(per_cat, dict):
		per_cat = {}

	penalty_factor = 1.0
	neg_categories_matched = [cat for cat, n in neg_hits.items() if n > 0]
	for _cat in neg_categories_matched:
		f = per_cat.get(_cat, category_factor_f)
		try:
			penalty_factor *= float(f)
		except Exception:
			penalty_factor *= category_factor_f

	raw = _clamp01(base_score + bonus)
	final = _clamp01(raw * penalty_factor)

	high_thr = float(qualification.get("high_score_threshold", 0.75))
	cap_unq = float(qualification.get("cap_if_unqualified", 0.49))
	must_any = qualification.get("must_have_any", ["field_data", "time_evolving_damage"])
	if not isinstance(must_any, list):
		must_any = ["field_data", "time_evolving_damage"]
	must_any = [str(x) for x in must_any if str(x).strip()]

	has_required_signal = any((pos_hits.get(cat, 0) or 0) > 0 for cat in must_any)
	# V4.2 meaning: "qualified" means the paper contains at least one required signal.
	qualified = bool(has_required_signal)
	if final >= high_thr and not has_required_signal:
		final = min(final, cap_unq)

	meta = {
		"profile": "damage_v4_2",
		"base_score": float(base_score),
		"bonus": float(bonus),
		"penalty_factor": float(penalty_factor),
		"raw_score": float(raw),
		"final_score": float(final),
		"qualified": bool(qualified),
		"positive_hits": pos_hits,
		"negative_hits": neg_hits,
		"negative_categories_matched": neg_categories_matched,
		"qualification_gate": {
			"high_score_threshold": high_thr,
			"must_have_any": must_any,
			"cap_if_unqualified": cap_unq,
			"has_required_signal": bool(has_required_signal),
		},
	}
	return float(final), bool(qualified), meta


def score_documents(
	db_path: Path,
	keywords: List[str],
	min_score: float = 0.0,
	db_url: str | None = None,
	negative_keywords: Optional[List[str]] = None,
	use_fulltext: bool = True,
	profile: str = "default",
	profile_config: Optional[Dict[str, Any]] = None,
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
		profile: Scoring profile name. "default" preserves v1 behavior.
		profile_config: Optional config dict that may contain screening profile settings.
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
		profile = (profile or "default").strip()
		profile_cfg = _get_profile_config(profile, profile_config)
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

			base_score, found = _base_score_and_keywords_found(
				doc=doc,
				lex=lex,
				neg_lex=neg_lex,
				negative_keywords=negative_keywords,
				use_fulltext=use_fulltext,
			)

			if profile == "damage_v4_2":
				final_score, qualified, meta = _damage_v4_2_adjust(
					doc=doc,
					base_score=base_score,
					use_fulltext=use_fulltext,
					profile_cfg=profile_cfg,
				)
				doc.relevance_score = float(final_score)
				# Optional, new columns (safe if not present in DB/model yet via getattr)
				try:
					setattr(doc, "screening_profile", "damage_v4_2")
					setattr(doc, "screening_qualified", bool(qualified))
					setattr(doc, "screening_meta", json.dumps(meta, ensure_ascii=False))
				except Exception:
					pass
			else:
				doc.relevance_score = float(base_score)

			doc.keywords_found = json.dumps(found, ensure_ascii=False)
			updated += 1
		session.commit()
		return updated
	finally:
		session.close()
