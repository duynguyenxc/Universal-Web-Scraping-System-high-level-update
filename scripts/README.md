# Scripts Directory

This directory contains various utility scripts for the Universal Web Scraping System.

## Directory Structure

### `analysis/`
Scripts for analyzing and viewing collected data:
- `analyze_new_sources_final.py` - Analyze final new sources data
- `check_*.py` - Data quality checking scripts
- `show_*.py` - Data viewing and inspection scripts
- `view_*.py` - Data visualization scripts

### `testing/`
Scripts for testing system components:
- `test_*.py` - Component testing scripts
- `run_scale_test.py` - Large-scale testing

### `utilities/`
Utility scripts for maintenance and data processing:
- `create_viewer_files.py` - Generate viewer files
- `fix_*.py` - Data fixing scripts
- `update_*.py` - Data update scripts

## Usage

Run any script from the project root directory:

```bash
python scripts/analysis/show_source_summary.py
python scripts/testing/test_full_pipeline.py
```
