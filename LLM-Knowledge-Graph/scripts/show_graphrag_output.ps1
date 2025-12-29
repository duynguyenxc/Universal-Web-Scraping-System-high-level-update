param(
  [Parameter(Mandatory=$false)]
  [string]$OutDir = "graphrag-project/output_meeting_std",

  [Parameter(Mandatory=$false)]
  [int]$N = 10
)

$ErrorActionPreference = "Stop"

Write-Host "== Exporting GraphRAG outputs to human-readable Markdown ==" -ForegroundColor Cyan
Write-Host "OutDir: $OutDir" -ForegroundColor Cyan

python scripts/graphrag_export_readable.py --out-dir $OutDir --export-dir "$OutDir/human_readable" --n $N

Write-Host "`nOpen these files (easy to read):" -ForegroundColor Green
Write-Host "  - $OutDir/human_readable/community_reports.md" -ForegroundColor Green
Write-Host "  - $OutDir/human_readable/entities.md" -ForegroundColor Green
Write-Host "  - $OutDir/human_readable/relationships.md" -ForegroundColor Green
Write-Host "  - $OutDir/human_readable/documents.md" -ForegroundColor Green
Write-Host "  - $OutDir/human_readable/communities.md" -ForegroundColor Green
Write-Host "  - $OutDir/human_readable/stats.json" -ForegroundColor Green


