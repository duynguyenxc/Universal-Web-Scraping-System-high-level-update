# Part A: GraphRAG Pipeline Architecture

## Overview

Part A implements a **verification-grade GraphRAG pipeline** for the Richmond et al. (2020) education benchmark. The system follows a **clear, linear pipeline** with well-defined stages, each producing auditable artifacts.

## Pipeline Flow

```
PDFs + Links
    ↓
[Stage 1] Metadata Extraction
    ↓
studies_metadata.jsonl
    ↓
[Stage 2] GraphRAG Input Preparation
    ↓
input_partA/*.txt (GraphRAG format)
    ↓
[Stage 3] GraphRAG Indexing (LLM calls)
    ↓
entities.parquet, relationships.parquet, communities.parquet, covariates.parquet
    ↓
[Stage 4] Post-Processing & Normalization
    ↓
claims_fixed.parquet (normalized claims)
    ↓
[Stage 5] Quality Gates & Audit
    ↓
quality_gates.md, verification_audit.md
    ↓
[Stage 6] Verification Exports
    ↓
claims_enriched.md, cmo_configurations.md
```

## Script Responsibilities (Single Responsibility Principle)

### Core Pipeline Scripts

1. **`partA_extract_study_metadata.py`**
   - **Purpose**: Extract metadata (title, DOI, abstract) from PDFs and optional URL links
   - **Input**: PDF directory, optional links PDF/file
   - **Output**: `studies_metadata.jsonl` (structured metadata)
   - **Dependencies**: `llm_kg.parta.metadata` module

2. **`partA_prepare_graphrag_input.py`**
   - **Purpose**: Convert metadata + PDFs into GraphRAG input format (`.txt` files)
   - **Input**: `studies_metadata.jsonl`, PDF directory
   - **Output**: `input_partA/*.txt` (one file per study)
   - **Options**: `--limit N` (subset), `--only-pdf` (filter)
   - **Dependencies**: `llm_kg.parta.graphrag_input` module

3. **`partA_run_graphrag.ps1`**
   - **Purpose**: **Main orchestrator** - runs the entire pipeline end-to-end
   - **Stages**:
     1. Metadata extraction
     2. Input preparation
     3. GraphRAG indexing (if not `-SkipIndex`)
     4. GraphRAG query (demo)
     5. Export human-readable files
     6. Claims normalization/repair
     7. Quality gates
     8. Verification audit
     9. CMO configuration exports
     10. Create run bundle
   - **Options**: `-Limit N`, `-OnlyPdf`, `-SkipIndex`
   - **Dependencies**: All other Part A scripts

### Post-Processing Scripts

4. **`partA_repair_claims_parquet.py`**
   - **Purpose**: Normalize malformed claims from `covariates.parquet` (LLM output format issues)
   - **Input**: `covariates.parquet`
   - **Output**: `claims_fixed.parquet`, `claims_fixed.md`
   - **Why needed**: GraphRAG's `extract_covariates` can pack claims incorrectly; this stage ensures claims are properly structured for verification

5. **`partA_quality_gates.py`**
   - **Purpose**: Automated quality checks (blank types, corrupt titles, CMO-edge ratio)
   - **Input**: `entities.parquet`, `relationships.parquet`
   - **Output**: `human_readable/quality_gates.md`
   - **Metrics**: Blank types (target: 0), corrupt titles (target: 0), CMO-edge % (target: >= 15%)

6. **`partA_audit_outputs.py`**
   - **Purpose**: Comprehensive verification audit report (quality gates + spot-check tables)
   - **Input**: All parquet files in output directory
   - **Output**: `artifacts/partA/verification_audit.md`
   - **Content**: Entity/relationship/claim quality, community structure, traceability checks

### Export Scripts

7. **`partA_export_cmo_configurations.py`**
   - **Purpose**: Export enriched claims and draft CMO configurations for verification
   - **Input**: `entities.parquet`, `claims_fixed.parquet`
   - **Output**: `claims_enriched.md`, `cmo_configurations.md`
   - **Use case**: Human verification against Richmond et al. (2020)

8. **`partA_create_run_bundle.py`**
   - **Purpose**: Create a shareable bundle of verification artifacts
   - **Input**: Output directory, artifacts directory
   - **Output**: `artifacts/partA/share/index.md` (central entry point)
   - **Use case**: Share results with reviewers/colleagues

### Utility Scripts

9. **`partA_explain_output.py`**
   - **Purpose**: Plain-language summary of GraphRAG output (helper for users)
   - **Input**: Output directory
   - **Output**: Console summary (entities, relationships, claims, quality gates)
   - **Use case**: Quick overview without reading parquet files

10. **`partA_compare_runs.py`**
    - **Purpose**: Compare two GraphRAG runs to measure improvement
    - **Input**: Two output directories (before/after)
    - **Output**: Console comparison table
    - **Use case**: Verify prompt improvements, measure quality changes

### Legacy/Other Scripts

- `graphrag_export_readable.py`: Generic GraphRAG export (used by Part A pipeline)
- `graphrag_prepare_input.py`: Generic GraphRAG input prep (not used by Part A)
- `graphrag_smoketest.ps1`: Generic smoke test (not Part A specific)
- `partA_generate_meeting_pack.py`: Legacy meeting pack generator
- `partA_export_verification_summary.py`: Legacy verification summary
- `show_graphrag_output.ps1`: Legacy output viewer

## Design Principles

### 1. Single Responsibility
Each script has **one clear purpose**. No script does multiple unrelated things.

### 2. Linear Pipeline
The pipeline is **linear and sequential**. Each stage depends only on previous stages. No circular dependencies.

### 3. Auditable Artifacts
Every stage produces **traceable artifacts** (parquet files, markdown reports). Nothing is "hidden" or implicit.

### 4. Fail-Fast
Each stage **validates inputs** and **fails early** if prerequisites are missing (e.g., `partA_run_graphrag.ps1` checks for `entities.parquet` before proceeding).

### 5. Idempotent Post-Processing
Post-processing scripts (repair, quality gates, audit) can be **run multiple times** safely. They read from parquet and write reports, without modifying source data.

### 6. No "Convenience Wrappers"
We **avoid creating wrapper scripts** that just alias commands. Users should use the main orchestrator (`partA_run_graphrag.ps1`) directly with appropriate parameters.

## File Organization

```
LLM-Knowledge-Graph/
  scripts/
    partA_*.py          # Part A pipeline scripts
    partA_*.ps1         # Part A PowerShell orchestrator
    graphrag_*.py       # Generic GraphRAG utilities (shared)
  graphrag-project/
    prompts_partA/      # Part A specific prompts
    settings.partA.yaml # Part A GraphRAG config
    input_partA/        # GraphRAG input (generated)
    output_partA/       # GraphRAG output (generated)
  artifacts/partA/      # Verification artifacts (reports, bundles)
    HOW_TO_READ_OUTPUT.md  # User guide
    ARCHITECTURE.md        # This file
    verification_audit.md   # Generated audit report
    share/                 # Shareable bundle
```

## Common Patterns

### Helper Functions (when needed)
If a helper function is used by **multiple scripts**, it should be:
1. Moved to a shared module (e.g., `src/llm_kg/common/helpers.py`)
2. Or kept as a private function (`_helper_name`) if it's truly script-specific

**Current duplicates** (to be refactored if needed):
- `_write_text()`: Used by 3 scripts → candidate for shared module
- `_safe_col()`: Used by 1 script → keep as private

### Error Handling
All scripts use:
- `argparse` for argument parsing (Python)
- `$ErrorActionPreference = "Stop"` (PowerShell)
- Explicit exit codes (`return 0` on success, `return 1` on error)
- Clear error messages pointing to logs/artifacts

### Output Format
- **Parquet files**: Machine-readable, structured data
- **Markdown files**: Human-readable reports
- **Console output**: Progress messages, summaries (not detailed data)

## Extension Points

To add new functionality:

1. **New pipeline stage**: Add to `partA_run_graphrag.ps1` as a numbered step
2. **New quality check**: Add to `partA_quality_gates.py` (or create new script if unrelated)
3. **New export format**: Create new `partA_export_*.py` script
4. **New comparison metric**: Add to `partA_compare_runs.py`

**Do NOT**:
- Create wrapper scripts that just call other scripts
- Duplicate logic across scripts (extract to shared module)
- Create "one-off" scripts without clear purpose

## Maintenance Guidelines

1. **Before adding a new script**: Ask "Can this be a stage in the main pipeline instead?"
2. **Before duplicating code**: Ask "Should this be in a shared module?"
3. **Before creating a wrapper**: Ask "Can users just use the main script with parameters?"
4. **Documentation**: Every script should have a clear docstring explaining its purpose and I/O
