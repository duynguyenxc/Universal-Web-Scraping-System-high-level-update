"""Embedding-based semantic similarity helpers for web crawling and scoring.

This module is intentionally small and self-contained so it can be reused
from multiple commands (e.g., semantic web crawler, analysis tools).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

import numpy as np


@lru_cache(maxsize=2)
def _load_model(model_name: str):
	"""Load and cache a sentence-transformer style model.

	The expected interface is compatible with `SentenceTransformer`:
	- .encode(list[str], convert_to_numpy=True, normalize_embeddings=True)
	"""
	try:
		from sentence_transformers import SentenceTransformer
	except ImportError as e:  # pragma: no cover - runtime guard
		raise RuntimeError(
			"sentence-transformers is required for semantic crawling. "
			"Install it with `pip install sentence-transformers`."
		) from e

	return SentenceTransformer(model_name)


def compute_semantic_score(
	text: Optional[str],
	topic_text: Optional[str],
	model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> float:
	"""Compute cosine similarity between a page's text and a topic description.

	Args:
		text: The page content (title + abstract + body).
		topic_text: A short paragraph or concatenation of domain keywords
			describing the topic of interest (e.g., corrosion of reinforced concrete).
		model_name: HuggingFace / sentence-transformers model name. Defaults to
			a light, widely used model that balances quality and speed.

	Returns:
		A scalar semantic similarity score in approximately [0, 1]. If inputs
		are missing or the model cannot be loaded, returns 0.0.
	"""
	if not text or not topic_text:
		return 0.0

	# Basic normalization: keep raw case for embeddings, strip whitespace only.
	text = text.strip()
	topic_text = topic_text.strip()
	if not text or not topic_text:
		return 0.0

	try:
		model = _load_model(model_name)
	except Exception:
		# Fail closed but not crash the whole pipeline – caller can still rely
		# on keyword-based relevance if semantic scoring is unavailable.
		return 0.0

	embeddings = model.encode(
		[topic_text, text],
		convert_to_numpy=True,
		normalize_embeddings=True,
	)
	topic_vec, text_vec = embeddings
	# Cosine similarity for normalized vectors is just dot product.
	score = float(np.dot(topic_vec, text_vec))
	# Clamp for numerical safety.
	if score < 0.0:
		score = 0.0
	if score > 1.0:
		score = 1.0
	return score



