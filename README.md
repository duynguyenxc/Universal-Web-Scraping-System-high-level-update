# UWSS – Universal Web Scraping System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-black.svg)](https://github.com/duynguyenxc/Universal-Web-Scraping-System-high-level-update)

> **UWSS** is an intelligent academic data collection system that can connect to multiple scientific document sources by simply changing configuration.

## 🚀 The Problem UWSS Solves

You're conducting research on a scientific topic and need to collect:
- ✅ Papers from arXiv, PubMed
- ✅ Documents from Crossref, Semantic Scholar
- ✅ Data from OpenAlex and other sources

**UWSS helps you:**
- Automatically collect metadata (title, abstract, authors, DOI)
- Download PDF files of papers
- Filter data by relevant keywords
- Export data in multiple formats (JSON, CSV)
- Manage and analyze data quality

## ✨ Key Features

### 🔍 Intelligent Collection
- **Multiple Sources**: arXiv, PubMed, Crossref, Semantic Scholar, OpenAlex
- **Web Domain Crawling**: Academic-focused web crawling from proven domains
- **Official APIs**: Uses official APIs from each source, compliant with regulations
- **Auto Classification**: Filters relevant papers based on keywords

### 📊 Data Management
- **Professional Database**: SQLite (local) or PostgreSQL (production)
- **Complete Metadata**: Title, abstract, authors, DOI, publication year
- **Automatic PDFs**: Download and store PDF files

### 🛠️ Easy to Use
- **Simple Configuration**: Just edit config.yaml file
- **Command Line Interface**: Intuitive command-line interface
- **Support Scripts**: Tools for analysis and data checking

## 🏗️ How UWSS Works

### 5-Step Process

```
1️⃣ DISCOVER 📚 → 2️⃣ SCORE 🎯 → 3️⃣ EXPORT 📄 → 4️⃣ FETCH PDF 📎 → 5️⃣ EXTRACT TEXT 📖
```

**Explanation of each step:**

1. **🔍 Discover**: Search for papers from sources (arXiv, PubMed, etc.)
2. **🎯 Score**: Filter relevant papers using keywords
3. **📄 Export**: Save metadata to JSON/CSV files
4. **📎 Fetch PDF**: Download paper PDF files
5. **📖 Extract**: Get text content from PDFs

### Supported Data Sources

| Source | Type | Sample Papers |
|--------|------|---------------|
| **arXiv** | Preprints | 269 papers |
| **PubMed** | Medical | Integrated |
| **Crossref** | Multi-disciplinary | 268 papers |
| **Semantic Scholar** | AI Research | 283 papers |
| **OpenAlex** | Open Data | Integrated |

### Collected Data

Each paper includes:
- 📝 **Title** and **abstract**
- 👥 **Authors** and **affiliations**
- 🏷️ **Keywords** and **DOI**
- 📅 **Publication year**
- 🔗 **PDF link** (if available)

## 🚀 Getting Started

### 1. Installation

```bash
# Clone repository
git clone https://github.com/duynguyenxc/Universal-Web-Scraping-System-high-level-update.git
cd Universal-Web-Scraping-System-high-level-update

# Create virtual environment
python -m venv uwss-env
uwss-env\Scripts\activate  # Windows
# source uwss-env/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit `config/config.yaml`:

```yaml
# Search keywords
domain_keywords:
  - "concrete corrosion"
  - "steel reinforcement"
  - "chloride attack"

# Exclude keywords
negative_keywords:
  - "quantum physics"
  - "machine learning"

# Contact email (for APIs)
contact_email: "your.email@university.edu"
```

### 3. First Test Run

```bash
# Collect data from arXiv
python -m src.uwss.cli paperscraper-discover --max 10

# Filter relevant data
python -m src.uwss.cli score-keywords --config config/config.yaml

# Export results
python -m src.uwss.cli export --require-match --out results.jsonl
```

## 📋 Usage Examples

### Collect papers about "concrete corrosion"

```bash
# 1. Discover from multiple sources
python -m src.uwss.cli paperscraper-discover --max 50
python -m src.uwss.cli crossref-lib-discover --max 50
python -m src.uwss.cli semantic-scholar-lib-discover --max 50

# 2. Generate web crawl targets from database analysis
python -m src.uwss.cli generate-web-targets --max-domains 20

# 3. Crawl academic domains for additional content
python -m src.uwss.cli web-domain-crawl-discover --max 100

# 4. Score relevance for all discovered content
python -m src.uwss.cli score-keywords --config config/config.yaml

# 5. Export high-quality data
python -m src.uwss.cli export --require-match --min-score 0.5 --out corrosion_papers.jsonl

# 6. Download PDFs
python -m src.uwss.cli fetch-pdfs --ids-file filtered_ids.txt --limit 20
```

### Analyze Results

```bash
# View statistics
python scripts/analysis/show_source_summary.py

# Check data quality
python scripts/analysis/check_paperscraper_data.py

# Visualize results
python scripts/analysis/view_scale_test_results.py
```

## 📂 Project Structure

```
uwss/
├── config/          # Keyword configuration and settings
├── data/            # Collected data and downloaded PDFs
├── scripts/         # Support utilities
│   ├── analysis/    # Data analysis tools
│   ├── testing/     # System testing scripts
│   └── utilities/   # Data maintenance tools
├── src/uwss/        # Main system code
├── test/            # Test results (not committed)
└── docs/            # Documentation guides
```

## 🎯 Why Use UWSS?

**Before UWSS:**
- 🔴 Manual paper search across multiple websites
- 🔴 Copy-paste metadata from each page
- 🔴 Download PDFs individually
- 🔴 Chaotic data management

**After UWSS:**
- ✅ **Fully automated** collection process
- ✅ **Diverse sources** from 5+ reputable platforms
- ✅ **Quality assurance** with intelligent filtering
- ✅ **Easy expansion** for new research topics

## 🆘 Support & Contributing

### Report Issues
If you encounter errors:
1. Check log files in `data/runs/`
2. Run analysis scripts: `python scripts/analysis/check_*.py`
3. Create GitHub issue with detailed logs

### Add New Data Sources
The system is designed for easy addition of new sources:
1. Create adapter in `src/uwss/sources/`
2. Add CLI command in `src/uwss/cli/commands/`
3. Test and validate data

## 📞 Contact

**Author:** Duy Nguyen
**Email:** 
**GitHub:** https://github.com/duynguyenxc

## 📄 License

This project uses MIT License. 

---

<div align="center">

**UWSS - When scientific research meets automation technology**

*🚀 Academic data collection has never been this easy!*

</div>
