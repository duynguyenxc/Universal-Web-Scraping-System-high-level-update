Param(
  [Parameter(Mandatory=$false)][string]$OutDir = "graphrag-project/output_partA_v4",
  [Parameter(Mandatory=$false)][string]$InputDir = "graphrag-project/input_partA_v4",
  [Parameter(Mandatory=$false)][string]$PdfDir = "data-28-studies",
  [Parameter(Mandatory=$false)][string]$LinksPdf = "documents/in4-about-28-studies-paper.pdf",
  [Parameter(Mandatory=$false)][string]$Settings = "graphrag-project/settings.partA.v4.yaml",
  [Parameter(Mandatory=$false)][string]$UserAgent = "llm-kg/0.1 (mailto:YOUR_EMAIL_HERE)",
  [Parameter(Mandatory=$false)][string]$Query = "What educational interventions improve clinical reasoning, for whom, in what contexts, and why? Summarize contexts, mechanisms, and outcomes with evidence snippets.",
  [Parameter(Mandatory=$false)][ValidateSet("global","local","basic","drift")][string]$QueryMethod = "global",
  [Parameter(Mandatory=$false)][switch]$SkipIndex,
  [Parameter(Mandatory=$false)][int]$Limit = 0,
  [Parameter(Mandatory=$false)][switch]$OnlyPdf
)

$ErrorActionPreference = "Stop"

Write-Host "== Part A v4: metadata -> input -> GraphRAG index/query ==" -ForegroundColor Cyan

# Make this script location-independent: resolve the LLM-Knowledge-Graph project root
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptRoot "..")).Path
Set-Location $ProjectRoot

# Ensure folders exist (Resolve-Path requires existence)
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path $InputDir | Out-Null

# Resolve to absolute paths and export for config env-var substitution
$OutAbs = (Resolve-Path $OutDir).Path
$InAbs = (Resolve-Path $InputDir).Path
$RootAbs = (Resolve-Path "graphrag-project").Path
$SettingsAbs = (Resolve-Path $Settings).Path

$env:PARTA_OUTPUT_DIR = $OutAbs
$env:PARTA_INPUT_DIR = $InAbs
$env:PARTA_CACHE_DIR = (Join-Path $env:TEMP "graphrag_cache_partA_v4")
$env:PARTA_LOG_DIR = (Join-Path $OutAbs "logs")
$env:PARTA_LANCEDB_DIR = (Join-Path $OutAbs "lancedb")

# Create expected cache/log folders up-front (GraphRAG sometimes assumes they exist on Windows)
New-Item -ItemType Directory -Force -Path $env:PARTA_CACHE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:PARTA_CACHE_DIR "extract_graph") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:PARTA_CACHE_DIR "extract_covariates") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:PARTA_CACHE_DIR "community_reports") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:PARTA_CACHE_DIR "embed_text") | Out-Null
New-Item -ItemType Directory -Force -Path $env:PARTA_LOG_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:PARTA_LANCEDB_DIR | Out-Null

# 1) Build metadata (PDF + embedded PubMed links)
python "scripts/partA_extract_study_metadata.py" `
  --pdf-dir "$PdfDir" `
  --links-pdf "$LinksPdf" `
  --out-dir "artifacts/partA" `
  --max-pages 3 `
  --user-agent "$UserAgent"
if ($LASTEXITCODE -ne 0) { throw "Metadata extraction failed (exit=$LASTEXITCODE)." }

# 2) Build GraphRAG input .txt
$PrepareArgs = @(
  "scripts/partA_prepare_graphrag_input.py",
  "--metadata-jsonl", "artifacts/partA/studies_metadata.jsonl",
  "--pdf-dir", "$PdfDir",
  "--out-input-dir", "$InputDir"
)
if ($OnlyPdf) { $PrepareArgs += "--only-pdf" }
if ($Limit -gt 0) { $PrepareArgs += @("--limit", "$Limit") }
python @PrepareArgs
if ($LASTEXITCODE -ne 0) { throw "GraphRAG input preparation failed (exit=$LASTEXITCODE)." }

if (-not $SkipIndex) {
  # 3) GraphRAG index (authoritative knowledge layer)
  graphrag index --root "$RootAbs" --config "$SettingsAbs" --method standard --output "$OutAbs"
  if ($LASTEXITCODE -ne 0) { throw "GraphRAG index failed (exit=$LASTEXITCODE). Check $OutAbs\\indexing-engine.log" }
  if (-not (Test-Path (Join-Path $OutAbs "entities.parquet"))) {
    throw "GraphRAG index did not produce entities.parquet. Check $OutAbs\\indexing-engine.log"
  }
}

# 4) GraphRAG query (demo question)
if (Test-Path (Join-Path $OutAbs "entities.parquet")) {
  graphrag query --root "$RootAbs" --config "$SettingsAbs" --data "$OutAbs" --method "$QueryMethod" --query "$Query" --response-type "Bullet list of 8-12 items"
}

# 5) Export human-readable files for meeting (avoid reading parquet)
python "scripts/graphrag_export_readable.py" --out-dir "$OutAbs" --export-dir "$OutAbs/human_readable" --n 15

# 6) Claims normalization (robustness layer)
if (Test-Path (Join-Path $OutAbs "covariates.parquet")) {
  python "scripts/partA_repair_claims_parquet.py" --out-dir "$OutAbs" --in-parquet "covariates.parquet" --out-parquet "claims_fixed.parquet" --out-md "human_readable/claims_fixed.md"
}

# 7) KG quality gates (detect regressions early)
python "scripts/partA_quality_gates.py" --out-dir "$OutAbs"

# 7.5) KG postprocess validator (CMOC normalization; produces normalized parquet + report)
if (Test-Path (Join-Path $OutAbs "entities.parquet")) {
  python "scripts/partA_postprocess_kg.py" --out-dir "$OutAbs" --label "v4"
}

# 8) Verification audit report (v4; avoid overwriting stable artifact)
python "scripts/partA_audit_outputs.py" --out-dir "$OutAbs" --out-md "artifacts/partA/verification_audit_v4.md"

# 9) Verification-grade exports (v4; avoid overwriting stable artifact)
if (Test-Path (Join-Path $OutAbs "entities.parquet")) {
  python "scripts/partA_export_cmo_configurations.py" --out-dir "$OutAbs" --out-claims-md "artifacts/partA/claims_enriched_v4.md" --out-md "artifacts/partA/cmo_configurations_v4.md"
}

# 10) v4 share page (stable link-page)
python "scripts/partA_create_run_bundle_v3.py" --out-dir "$OutAbs" --artifacts-dir "artifacts/partA" --mode "share" --share-subdir "share_v4" --artifact-suffix "v4"

Write-Host "Done. Output dir: $OutDir" -ForegroundColor Green

