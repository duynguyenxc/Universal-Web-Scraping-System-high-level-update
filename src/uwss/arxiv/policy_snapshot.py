from __future__ import annotations

from pathlib import Path
from datetime import datetime
import requests


def snapshot_arxiv_policy(out_dir: Path, contact_email: str | None = None) -> dict:
    """Save arXiv policy artifacts for compliance (Identify, robots, links).

    Writes into out_dir:
      - identify.xml (OAI-PMH Identify response)
      - robots.txt (site robots)
      - links.md (URLs and timestamp)
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": f"uwss/0.1 (+policy; {contact_email or 'contact@unknown'})",
        "Accept": "application/xml, text/plain, */*;q=0.8",
    }

    # OAI-PMH Identify
    identify_url = "https://export.arxiv.org/oai2?verb=Identify"
    r1 = requests.get(identify_url, headers=headers, timeout=30)
    r1.raise_for_status()
    (out_dir / "identify.xml").write_text(r1.text, encoding="utf-8")

    # robots.txt
    robots_url = "https://arxiv.org/robots.txt"
    r2 = requests.get(robots_url, headers=headers, timeout=30)
    r2.raise_for_status()
    (out_dir / "robots.txt").write_text(r2.text, encoding="utf-8")

    # Links record
    links_md = (
        "# arXiv policy snapshot\n\n"
        f"- captured_at: {datetime.utcnow().isoformat()}Z\n"
        f"- oai_identify: {identify_url}\n"
        f"- robots: {robots_url}\n"
        "- bulk_data_docs: https://info.arxiv.org/help/bulk_data.html\n"
        "- terms_of_use: https://info.arxiv.org/help/rights/index.html\n"
    )
    (out_dir / "links.md").write_text(links_md, encoding="utf-8")

    return {
        "identify_saved": True,
        "robots_saved": True,
        "out_dir": str(out_dir),
    }



