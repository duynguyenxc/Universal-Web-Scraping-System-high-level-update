# Cloud Deployment Guide (AWS ECS + S3 + RDS)

## Overview
This guide outlines a lightweight path to run UWSS in the cloud:
- Containerize with Docker.
- Store files in S3; use RDS/PostgreSQL (or keep SQLite for initial tests with EFS/EBS).
- Schedule periodic jobs (discovery/score/export/fetch) via ECS Scheduled Tasks or AWS Batch.
- Centralize logs/metrics in CloudWatch.

## 1) Build & Push Docker Image
```bash
# from repo root
docker build -t uwss:latest .
# optional: tag for ECR, e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/uwss:latest
```

## 2) Configuration via ENV/Secrets
- CONTACT EMAIL / USER AGENT: `UWSS_CONTACT_EMAIL`, `UWSS_USER_AGENT`
- DB URL: `UWSS_DB_URL` (Postgres e.g. `postgresql+psycopg2://user:pass@host:5432/dbname`)
- S3: `UWSS_S3_BUCKET`, `UWSS_S3_PREFIX`
- Rate limits: `UWSS_RATE_LIMIT_PER_DOMAIN`, `UWSS_RATE_LIMIT_GLOBAL`
- Provide via ECS Task Definition environment or Secrets Manager/Parameter Store.

## 3) Storage
- Files → S3 (mount local `/app/data/files` to an EFS if needed; or stream directly to S3 in future enhancement).
- DB → RDS/PostgreSQL (recommended) or start with SQLite on EFS for quick trials.

## 4) Scheduling Jobs (examples)
Run ECS tasks on a schedule (CloudWatch Events / EventBridge):
- Discovery:
  ```
  python -m src.uwss.cli discover-crossref --config config/config.yaml --db data/uwss.sqlite --max 50
  python -m src.uwss.cli score-keywords --config config/config.yaml --db data/uwss.sqlite
  ```
- Cleanup & Export:
  ```
  python -m src.uwss.cli dedupe-resolve --db data/uwss.sqlite
  python -m src.uwss.cli validate --db data/uwss.sqlite --json-out data/export/validation.json
  python -m src.uwss.cli stats --db data/uwss.sqlite --json-out data/export/stats.json
  python -m src.uwss.cli export --db data/uwss.sqlite --out data/export/candidates.jsonl --min-score 0.0 --year-min 1995 --sort relevance --skip-missing-core --include-provenance
  python -m src.uwss.cli export --db data/uwss.sqlite --out data/export/candidates_clean_005.jsonl --min-score 0.05 --year-min 1995 --sort relevance --skip-missing-core --include-provenance
  ```
- Fetch OA:
  ```
  python -m src.uwss.cli fetch --db data/uwss.sqlite --outdir data/files --limit 10 --config config/config.yaml
  ```

## 5) Logging & Metrics
- Pipe stdout/stderr to CloudWatch.
- Track counters in logs: inserted/downloaded/failed/throttled.

## 6) IAM & Security
- Minimal S3 permissions to the target prefix.
- Store secrets in Secrets Manager / SSM Parameter Store.

## 7) Cost & Scaling
- Start small (t2/t3) with short tasks; increase concurrency per domain gradually.
- Cache API calls and checkpoint runs to reduce costs.

## 8) Next Steps
- Add direct S3 uploader for downloaded files.
- Switch to RDS fully; migrate schema.
- Add health dashboards (CloudWatch metrics/alarms).

