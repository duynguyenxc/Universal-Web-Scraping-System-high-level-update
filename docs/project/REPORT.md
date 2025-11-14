# UWSS – Current Status Report (arXiv‑first)

## 1) Objective
Adopt a professional, compliant pipeline to harvest arXiv via official channels, download PDFs lawfully, extract content locally, and prepare for S3 storage. Keep the system universal and config‑driven for future sources (TRB/ROSA P/Crossref, etc.).

## 2) What’s implemented now
- Harvest (OAI‑PMH):
  - Command: `arxiv-harvest-oai` (resume with `resumptionToken`).
  - Fixed namespace to `oai_dc` and max stopping by processed count for fast smoke.
  - Metrics: `--metrics-out` writes JSON under `data/runs/`.
- Fetch (canonical PDF):
  - Command: `arxiv-fetch-pdf` (polite UA, throttle/jitter, retry/backoff).
  - Atomic `.part→rename`, SHA256 checksums, sidecar `meta.json` (status/headers/hash/size/time).
  - Updates DB: `local_path`, `http_status`, `mime_type`, `file_size`, `checksum_sha256`, `fetched_at`.
- Extract (local):
  - Command: `extract-full-text` to `data/content/`.
- Compliance: `arxiv-policy-snapshot` stores Identify/robots and links.

## 2.1) Phased progress (what we did and why it matters)
- Phase 1 – Harvest (official OAI‑PMH)
  - Built `arxiv-harvest-oai` with resume & metrics; fixed `oai_dc` namespace and early stop by processed count → faster smoke runs and reliable ingestion.
  - Purpose: compliant discovery, idempotent re‑runs, deterministic resume.
- Phase 2 – PDF fetch (canonical)
  - Implemented polite fetching with throttle+jitter, retry/backoff, atomic write, SHA256, sidecar meta.json.
  - Purpose: robust downloads, reproducibility (hash + meta headers), provenance.
- Phase 2.5 – Hardening for stability/observability
  - Added DB columns: `pdf_status`, `pdf_fetched_at` (+ migrations/CLI `db-add-columns`).
  - Fetch improvements: HEAD size cap (`--max-mb`), `--dry-run`, `--since-days`, richer metrics; set `pdf_status` (`ok/not_found/forbidden/too_large/timeout/error`).
  - Purpose: clear querying, cost control, faster iteration, clean idempotency.

## 3) Smoke results (local SQLite)
- Harvest small: inserted 3, then 20 (pages=1, ~11–20s). Files: `data/runs/arxiv_h*.json`.
- Fetch: 1/1 then 10/10 PDFs downloaded; sidecar `arxiv_*.meta.json`. Files: `data/runs/arxiv_p*.json`.
- Extract: full text for 10. DB: `data/uwss.sqlite` updated.

## 4) How to run (repro)
```
# policy
python -m src.uwss.cli arxiv-policy-snapshot
# harvest (choose a small window)
python -m src.uwss.cli arxiv-harvest-oai --from 2024-10-01 --max 20 --resume --metrics-out data/runs/arxiv_h.json
# fetch PDFs
python -m src.uwss.cli arxiv-fetch-pdf --limit 10 --metrics-out data/runs/arxiv_p.json
# extract full text
python -m src.uwss.cli extract-full-text --db data/uwss.sqlite --content-dir data/content --limit 10
# export (domain-filtered)
python -m src.uwss.cli export --db data/uwss.sqlite --out data/export/arxiv.jsonl --require-match --oa-only
```

## 5) Architecture (summary)
- Postgres‑first (SQLite for local), config‑driven, official APIs only.
- OAI‑PMH → normalize/upsert → fetch (atomic+hash) → extract → score/export.
- Local‑first storage; S3 as a later toggle with checksums.

## 5.1) Core algorithms (concise)
- Dedupe/upsert: key on arXiv landing/ID + DOI + normalized title; upsert to avoid duplicates; resume via resumptionToken.
- Fetch strategy: HEAD (size cap) → GET with retry/backoff; per‑host throttle+jitter; atomic `.part→rename`; compute SHA256; write sidecar meta; set `pdf_status`.
- Idempotency: skip when file exists and SHA256 matches; maintain `visited_urls` with latest status.
- Scoring/export: keyword + bigram + title boost + negatives (for domain filtering at export step).

## 6) Next steps (stabilize & scale)
1. Pinned→Latest URL order for versioned PDFs (reproducibility boost) [fetch]
2. GROBID integration: PDF→TEI/XML→JSON; save `content_path`, `extractor='grobid'`, `parse_ok/parse_errors` [extract]
3. Precision controls: restrict arXiv `--set` categories + recent `--from`; export with `--require-match` and negatives [quality]
4. S3 enablement: config toggle, checksum uploads, mirror local layout; optional requester‑pays for arXiv bulk [storage]
5. Monitoring: per‑run ledger (data/runs/*), richer `visited_urls` (latency/error_kind), quick stats dashboard [ops]

## 7) Compliance notes
- arXiv data from OAI‑PMH; PDFs from canonical arXiv links.
- Only public/allowed content fetched; robots/Identify snapshots stored under `docs/policies/arxiv/`.


