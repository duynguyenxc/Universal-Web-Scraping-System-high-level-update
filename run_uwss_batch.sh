#!/usr/bin/env bash
set -euo pipefail

# UWSS daily batch runner for EC2
# - Discovers from all academic sources (Crossref, OpenAlex, Semantic Scholar, PubMed, arXiv)
# - Optionally discovers from OpenAIRE Graph if OPENAIRE_TOKEN is set
# - Scores relevance, exports a date-stamped JSONL, fetches a batch of PDFs
# - Syncs the per-day run directory to S3

# Always run from the project root (directory containing this script)
cd "$(dirname "$0")"

# 1) Make sure common locations are on PATH (cron can have a minimal PATH).
# - AWS CLI via snap is often installed in /snap/bin
export PATH="$PATH:/snap/bin"

# 2) Activate virtualenv if present.
# Support both common names:
# - .venv (recommended for Linux)
# - uwss-env (older setups)
VENV_DIR=""
if [ -d ".venv" ]; then
  VENV_DIR=".venv"
elif [ -d "uwss-env" ]; then
  VENV_DIR="uwss-env"
fi
if [ -n "${VENV_DIR}" ] && [ -f "${VENV_DIR}/bin/activate" ]; then
  echo "[UWSS] Activating virtualenv ${VENV_DIR}"
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
fi

# 3) Date-stamped run directories
RUN_DATE=$(date +%y-%m-%d)             # e.g. 25-11-29
RUN_DIR="data/runs/$RUN_DATE"
DB="data/uwss.sqlite"
EXPORT_JSON="$RUN_DIR/corrosion_papers_$RUN_DATE.jsonl"
FILES_DIR="$RUN_DIR/files"
# TODO: adjust BUCKET to your real S3 bucket name if different
BUCKET="s3://data-new-ec2/uwss-data"

mkdir -p "$RUN_DIR" "$FILES_DIR"

echo "[UWSS] ====== START BATCH $RUN_DATE ======"
echo "[UWSS] Working directory: $(pwd)"

# 3) Initialise DB once if missing
if [ ! -f "$DB" ]; then
  echo "[UWSS] Initializing DB at $DB"
  python -m src.uwss.cli db-init --db "$DB"
fi

# 4) Discover from all main academic databases
echo "[UWSS] Discovering from Crossref..."
python -m src.uwss.cli crossref-lib-discover \
  --config config/config.yaml --db "$DB" --max 200 || true

echo "[UWSS] Discovering from OpenAlex..."
python -m src.uwss.cli openalex-lib-discover \
  --config config/config.yaml --db "$DB" --max 200 || true

echo "[UWSS] Discovering from Semantic Scholar..."
python -m src.uwss.cli semantic-scholar-lib-discover \
  --config config/config.yaml --db "$DB" --max 200 || true

echo "[UWSS] Discovering from PubMed..."
python -m src.uwss.cli paperscraper-discover \
  --config config/config.yaml --db "$DB" --source pubmed --max 200 || true

echo "[UWSS] Discovering from arXiv..."
python -m src.uwss.cli paperscraper-discover \
  --config config/config.yaml --db "$DB" --source arxiv --max 200 || true

# 4b) OpenAIRE Graph – optional, only if OPENAIRE_TOKEN is configured
if [ -n "${OPENAIRE_TOKEN:-}" ]; then
  echo "[UWSS] Discovering from OpenAIRE Graph (token detected)..."
  python -m src.uwss.cli openaire-lib-discover \
    --config config/config.yaml --db "$DB" --max 200 || true
else
  echo "[UWSS] Skipping OpenAIRE (OPENAIRE_TOKEN not set)."
fi

# 5) Score relevance using corrosion/durability keywords
echo "[UWSS] Scoring documents with score-keywords..."
python -m src.uwss.cli score-keywords \
  --config config/config.yaml --db "$DB" || true

# 6) Export a high-quality subset to a date-stamped JSONL
echo "[UWSS] Exporting JSONL to $EXPORT_JSON ..."
python -m src.uwss.cli export \
  --db "$DB" \
  --out "$EXPORT_JSON" \
  --require-match \
  --min-score 0.5 \
  --require-abstract \
  --min-abstract-length 80 || true

# 7) Fetch a batch of PDFs into the per-day files directory
echo "[UWSS] Fetching PDFs to $FILES_DIR ..."
python -m src.uwss.cli fetch \
  --db "$DB" \
  --outdir "$FILES_DIR" \
  --limit 50 \
  --config config/config.yaml || true

# 8) Sync today's run directory to S3
echo "[UWSS] Syncing $RUN_DIR to $BUCKET/runs/$RUN_DATE/ ..."
aws s3 sync "$RUN_DIR" "$BUCKET/runs/$RUN_DATE/"

echo "[UWSS] ====== BATCH $RUN_DATE COMPLETED ======"



