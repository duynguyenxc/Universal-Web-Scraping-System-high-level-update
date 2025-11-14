from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests


def _ensure_dir(p: Path) -> None:
	p.mkdir(parents=True, exist_ok=True)


def _build_key(url: str, params: Optional[Dict[str, Any]] = None) -> str:
	parts = [url]
	if params:
		# stable params order
		items = sorted((k, str(v)) for k, v in params.items())
		parts.extend([f"{k}={v}" for k, v in items])
	key = "|".join(parts)
	return hashlib.sha1(key.encode("utf-8")).hexdigest()


def _is_fresh(path: Path, ttl_sec: Optional[int]) -> bool:
	if ttl_sec is None:
		return False
	try:
		age = time.time() - path.stat().st_mtime
		return age < ttl_sec
	except FileNotFoundError:
		return False


def fetch_json_with_cache(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, cache_dir: Path = Path("data") / "cache", ttl_sec: Optional[int] = None, timeout: int = 30) -> Dict[str, Any]:
	"""GET JSON with a simple on-disk cache keyed by url+params. Returns parsed JSON dict."""
	_ensure_dir(cache_dir)
	key = _build_key(url, params)
	cache_file = cache_dir / f"{key}.json"
	if cache_file.exists() and _is_fresh(cache_file, ttl_sec):
		try:
			return json.loads(cache_file.read_text(encoding="utf-8"))
		except Exception:
			pass
	resp = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout)
	resp.raise_for_status()
	text = resp.text
	try:
		cache_file.write_text(text, encoding="utf-8")
	except Exception:
		pass
	return resp.json()


def fetch_text_with_cache(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, cache_dir: Path = Path("data") / "cache", ttl_sec: Optional[int] = None, timeout: int = 30) -> str:
	"""GET text with a simple on-disk cache keyed by url+params. Returns text."""
	_ensure_dir(cache_dir)
	key = _build_key(url, params)
	cache_file = cache_dir / f"{key}.txt"
	if cache_file.exists() and _is_fresh(cache_file, ttl_sec):
		try:
			return cache_file.read_text(encoding="utf-8")
		except Exception:
			pass
	resp = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout)
	resp.raise_for_status()
	text = resp.text
	try:
		cache_file.write_text(text, encoding="utf-8")
	except Exception:
		pass
	return text


