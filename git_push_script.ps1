# Git push script for UWSS project

# Clone repository (skip long filenames)
Write-Host "Cloning repository..."
git clone --no-checkout https://github.com/duynguyenxc/Universal-Web-Scraping-System-high-level-update.git temp_repo_uwss
cd temp_repo_uwss

# Checkout without problematic files
Write-Host "Checking out files..."
git checkout HEAD -- . ':(exclude:data/phase1_large_files/*)' ':(exclude:data/paperscraper_pdfs/*)'

# Copy our updated files
Write-Host "Copying updated files..."
Copy-Item -Path "../src/*" -Destination "./src/" -Recurse -Force
Copy-Item -Path "../data/new_sources_final.jsonl" -Destination "./data/" -Force
Copy-Item -Path "../data/openalex_education_results.jsonl" -Destination "./data/" -Force
Copy-Item -Path "../config_education.yaml" -Destination "./" -Force
Copy-Item -Path "../*.md" -Destination "./" -Force
Copy-Item -Path "../*.py" -Destination "./" -Force

# Add and commit
Write-Host "Adding files to git..."
git add .

Write-Host "Creating feature branch..."
git checkout -b feature/comprehensive-testing-and-reports

Write-Host "Committing changes..."
git commit -m @"
feat: Comprehensive testing and universality assessment

- Add 3 new academic sources: Crossref, OpenAlex, Semantic Scholar
- Implement robust discovery adapters with proper error handling
- Add HTML tag cleaning and PDF URL normalization fixes
- Conduct large-scale testing (555 records across sources)
- Create detailed analysis and universality assessment reports
- Verify OpenAlex topic-specific limitations vs education research
- Generate comprehensive documentation and test results
- Achieve 85/100 universality score for database integration

Closes: OpenAlex integration, Source diversity expansion, Quality assurance
"@

# Push to GitHub
Write-Host "Pushing to GitHub..."
git push -u origin feature/comprehensive-testing-and-reports

Write-Host "✅ Successfully pushed to GitHub!"
Write-Host "Branch: feature/comprehensive-testing-and-reports"
Write-Host "Repository: https://github.com/duynguyenxc/Universal-Web-Scraping-System-high-level-update.git"
