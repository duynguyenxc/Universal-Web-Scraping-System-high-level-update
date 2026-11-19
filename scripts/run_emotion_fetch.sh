#!/usr/bin/env bash
# Resolve open-access locations through Unpaywall and download what it points at.
#
# WHY THIS SCRIPT RATHER THAN THE RAW COMMAND
# Unpaywall requires a contact address in every request. That address is personal
# data and does not belong in a version-controlled config, so it is read from the
# environment here and the script refuses to run without it rather than falling
# back to a fake address — which is what the underlying library does, and which
# would make this a rude anonymous client wearing someone else's name.
#
# WHAT IT DOES
#   1. resolve_publisher_links  — turn landing pages into direct locations
#   2. enrich_open_access       — ask Unpaywall for the direct PDF location
#   3. download_open_links      — fetch what step 2 found
#
# On the corpus this was built for, a little over half of the catalogue's "open
# access" links yielded no file, the largest group being doi.org resolvers that were
# never PDF locations at all. Unpaywall publishes the direct location for exactly
# that case, which is what step 2 exists to use.
#
# IDENTITY: User-Agent rotation and proxies are NOT enabled and must not be. The
# publisher 403s answer a browser's User-Agent identically, so rotating identity
# gains nothing and means circumventing a stated bot policy.
#
# USAGE
#     export UWSS_CONTACT_EMAIL='you@example.org'
#     bash scripts/run_emotion_fetch.sh [LIMIT]
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -z "${UWSS_CONTACT_EMAIL:-}" ]]; then
  echo "UWSS_CONTACT_EMAIL is not set." >&2
  echo "Unpaywall needs a contact address in every request. Set it in this shell:" >&2
  echo "    export UWSS_CONTACT_EMAIL='you@example.org'" >&2
  echo "It is deliberately not stored in the repository." >&2
  exit 1
fi

LIMIT="${1:-1500}"
DB="data/emotion.sqlite"
OUT="data/emotion_fulltext"

# The config carries no address; inject it for this run only, into a copy that
# lives in the system temp directory and is removed on exit.
TMP_CFG="$(mktemp -t uwss_emotion_cfg).yaml"
trap 'rm -f "$TMP_CFG"' EXIT
cp config/config_emotion.yaml "$TMP_CFG"
printf '\ncontact_email: %s\n' "$UWSS_CONTACT_EMAIL" >> "$TMP_CFG"

mkdir -p "$OUT"
echo "Unpaywall + download, limit $LIMIT, into $OUT"
.venv-mac/bin/python -m src.uwss.cli fetch \
  --db "$DB" --config "$TMP_CFG" --outdir "$OUT" --limit "$LIMIT" \
  --throttle-sec 1.0 --jitter-sec 0.4
