from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from typing import Optional

from ..constants import DEFAULT_UA, DEFAULT_TIMEOUT_SEC, MAX_RETRIES


def build_retry(total: int = MAX_RETRIES) -> Retry:
	return Retry(
		total=total,
		backoff_factor=0.5,
		status_forcelist=[429, 500, 502, 503, 504],
		allowed_methods=frozenset(["GET", "HEAD"]),
		respect_retry_after_header=True,
	)


def session_with_retries(user_agent: Optional[str] = None, timeout_sec: int = DEFAULT_TIMEOUT_SEC) -> requests.Session:
	s = requests.Session()
	adapter = HTTPAdapter(max_retries=build_retry())
	s.mount("http://", adapter)
	s.mount("https://", adapter)
	s.headers.update({"User-Agent": user_agent or DEFAULT_UA, "Accept": "*/*"})
	# Store default timeout on the session for convenience
	s.request = _wrap_request_with_timeout(s.request, timeout_sec)
	return s


def _wrap_request_with_timeout(request_func, timeout_sec: int):
	def _wrapped(method, url, **kwargs):
		if "timeout" not in kwargs:
			kwargs["timeout"] = timeout_sec
		return request_func(method, url, **kwargs)
	return _wrapped


