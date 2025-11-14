from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Iterator, Optional
import xml.etree.ElementTree as ET
import requests


def iter_oai_dc(base_url: str, from_date: Optional[str] = None, until_date: Optional[str] = None, set_spec: Optional[str] = None, resume_token: Optional[str] = None, throttle_sec: float = 1.0) -> Iterator[Dict]:
	"""Iterate OAI-PMH ListRecords (oai_dc) and yield normalized dicts.

	Yields fields: title, authors (list[str]), abstract, doi, source_url, pdf_url, year.
	"""
	headers = {
		"User-Agent": "uwss/0.1 (+oai-harvest)",
		"Accept": "application/xml, text/xml;q=0.9, */*;q=0.8",
	}
	while True:
		params = {"verb": "ListRecords"}
		if resume_token:
			params["resumptionToken"] = resume_token
		else:
			params["metadataPrefix"] = "oai_dc"
			if from_date:
				params["from"] = from_date
			if until_date:
				params["until"] = until_date
			if set_spec:
				params["set"] = set_spec
		resp = requests.get(base_url, params=params, headers=headers, timeout=30)
		resp.raise_for_status()
		root = ET.fromstring(resp.text)
		ns = {
			"oai": "http://www.openarchives.org/OAI/2.0/",
			"oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
			"dc": "http://purl.org/dc/elements/1.1/",
		}
		records = root.findall(".//oai:record", ns)
		for rec in records:
			md = rec.find("oai:metadata", ns)
			if md is None:
				continue
			dc = md.find("oai_dc:dc", ns) or md.find("dc:dc", ns)
			if dc is None:
				# fallback: any child ending with 'dc'
				for child in list(md):
					if child.tag.endswith("}dc"):
						dc = child
						break
			if dc is None:
				continue
			get_all = lambda tag: [el.text.strip() for el in dc.findall(f"dc:{tag}", ns) if (el.text or "").strip()]
			title = (get_all("title") or [None])[0]
			authors = get_all("creator")
			abstract = (get_all("description") or [None])[0]
			identifiers = get_all("identifier")
			doi: Optional[str] = None
			source_url: Optional[str] = None
			for ident in identifiers:
				low = ident.lower()
				if low.startswith("http://") or low.startswith("https://"):
					source_url = ident
				elif low.startswith("doi:"):
					doi = ident.split(":", 1)[-1].strip()
				elif "doi.org/" in low:
					doi = ident.split("doi.org/")[-1]
			year: Optional[int] = None
			dates = get_all("date")
			if dates:
				try:
					year = int(dates[0][:4])
				except Exception:
					year = None
			# pdf_url usually not present in oai_dc; leave None
			yield {
				"title": title,
				"authors": authors,
				"abstract": abstract,
				"doi": doi,
				"source_url": source_url,
				"pdf_url": None,
				"year": year,
			}
		# resumption token
		tok_el = root.find(".//oai:resumptionToken", ns)
		resume_token = tok_el.text.strip() if (tok_el is not None and (tok_el.text or "").strip()) else None
		if not resume_token:
			break
		time.sleep(throttle_sec)


