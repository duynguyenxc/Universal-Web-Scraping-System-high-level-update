param(
  [Parameter(Mandatory=$false)]
  [string]$Day,

  [Parameter(Mandatory=$false)]
  [int]$MaxDocs = 30,

  [Parameter(Mandatory=$false)]
  [string]$Query = "Summarize the main corrosion mechanisms and mitigation strategies discussed in this corpus.",

  [Parameter(Mandatory=$false)]
  [string]$Root = "graphrag-project",

  [Parameter(Mandatory=$false)]
  [string]$Config = "graphrag-project/settings.lowrate.yaml",

  [Parameter(Mandatory=$false)]
  [switch]$DryRun,

  [Parameter(Mandatory=$false)]
  [string]$OutDir = "graphrag-project/output_meeting_std"
)

$ErrorActionPreference = "Stop"

Write-Host "== GraphRAG smoke test ==" -ForegroundColor Cyan

# Ensure we're running from LLM-Knowledge-Graph/
if (!(Test-Path ".\graphrag-project")) {
  throw "Run this script from the LLM-Knowledge-Graph folder."
}

# Remind about env key
if (-not $env:OPENAI_API_KEY) {
  if (Test-Path ".\graphrag-project\.env") {
    Write-Host "OPENAI_API_KEY not set in environment, but .\graphrag-project\.env exists. GraphRAG may load it automatically." -ForegroundColor Yellow
  } else {
    Write-Host "OPENAI_API_KEY not set and .\graphrag-project\.env not found." -ForegroundColor Yellow
    Write-Host "Copy .\graphrag-project\env.example to .\graphrag-project\.env and fill OPENAI_API_KEY, or set `$env:OPENAI_API_KEY." -ForegroundColor Yellow
  }
}

# Verify graphrag is installed
try {
  graphrag --help | Out-Null
} catch {
  throw "GraphRAG is not installed. Run: pip install graphrag"
}

function New-TempGraphRagConfig([string]$BaseConfig, [string]$OutDirRel) {
  # GraphRAG config paths are resolved relative to the project root. We want a self-contained output folder.
  $tmp = Join-Path $env:TEMP ("graphrag-config-" + [Guid]::NewGuid().ToString() + ".yaml")
  $yaml = Get-Content $BaseConfig -Raw

  # Normalize slashes for YAML replacements
  $out = $OutDirRel -replace "\\\\", "/"

  # Replace output/log/cache base dirs and lancedb db_uri to stay under OutDir
  $yaml = $yaml -replace '(^output:\s*[\s\S]*?base_dir:\s*")[^"]+(")', "`$1$out`$2"
  $yaml = $yaml -replace '(^reporting:\s*[\s\S]*?base_dir:\s*")[^"]+(")', "`$1$out`$2"
  $yaml = $yaml -replace '(^cache:\s*[\s\S]*?base_dir:\s*")[^"]+(")', "`$1$out/cache`$2"
  $yaml = $yaml -replace '(^\s*db_uri:\s*)output\\\\lancedb', "`$1$out/lancedb"

  Set-Content -Path $tmp -Value $yaml -Encoding UTF8
  return $tmp
}

Write-Host "Preparing input texts..." -ForegroundColor Cyan
$prepArgs = @("scripts/graphrag_prepare_input.py", "--max-docs", "$MaxDocs", "--clean")
if ($Day) { $prepArgs += @("--day", "$Day") }
python @prepArgs

Write-Host "Indexing (this may take time)..." -ForegroundColor Cyan
$tmpCfg = New-TempGraphRagConfig -BaseConfig $Config -OutDirRel $OutDir
try {
  if ($DryRun) {
    graphrag index --root $Root --config $tmpCfg --dry-run
    Write-Host "Dry-run complete (no LLM calls)." -ForegroundColor Green
    exit 0
  } else {
    # Safer default: disable cache to avoid cache write issues on Windows.
    graphrag index --root $Root --config $tmpCfg --method standard --no-cache
  }
} finally {
  if (Test-Path $tmpCfg) { Remove-Item -Force $tmpCfg }
}

Write-Host "Querying (global)..." -ForegroundColor Cyan
graphrag query --root $Root --method global --query $Query --response-type "Bullet list of 5-10 items"

Write-Host "Done." -ForegroundColor Green


