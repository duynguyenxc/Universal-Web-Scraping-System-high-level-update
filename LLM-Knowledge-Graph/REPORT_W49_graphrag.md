
## (EN) REPORT W49 — Microsoft GraphRAG local run + LLM-Knowledge-Graph integration (week wrap-up)

### 1) What we accomplished this week (short summary)
- **Installed and ran Microsoft GraphRAG locally** (end-to-end indexing).
- **Integrated our harvested data (daily JSONL exports)** into GraphRAG by converting them into a `*.txt` text corpus.
- **Completed a successful test run and produced demo outputs**, especially **Community Reports** (cluster/community summaries) — the key GraphRAG artifact.
- **Standardized output review** by exporting technical artifacts (parquet) into **human-readable Markdown** for quick inspection/presentation.
- **Pushed code to GitHub**, and created a dedicated demo branch that includes outputs for easy sharing (branch `graphrag-output-demo`).

> Note: this is a **smoke/feasibility test** to prove “runnable + outputs exist”, not a final scientific-quality evaluation.

---

### 2) What is Microsoft GraphRAG (paper/repo) and what can it do?
**Microsoft GraphRAG** (based on the paper “From Local to Global: A Graph RAG Approach to Query-Focused Summarization”, Edge et al., 2024) is a graph-based RAG workflow:

- **Local (graph construction)**: from text → extract **entities (nodes)** and **relationships (edges)**.
- **Global (hierarchical synthesis)**: apply **Leiden community detection** to group the graph into **communities/clusters (topics)**, then use an LLM to write **Community Reports** (summaries per cluster).
- **Query**: supports “big picture” global search using community reports + map/reduce, in addition to local/basic/drift search.

**Key advantages (vs. flat KG / triple extraction only):**
- Not just pathfinding (A→B), but **topic structure (clusters)** and **cluster-level summaries** for vague/high-level questions.
- Better suited for **themes / contradictions / research gaps** at a corpus level.

**Practical limitations:**
- Quality depends heavily on **ontology + prompts** (entity types/rules). Without domain-specific tuning, noise appears.
- **Rate limits (429 TPM)** and cost increase when scaling to large corpora.
- Very small corpora or “fast/NLP” mode can yield sparse graphs and/or fail in some steps.
- Default outputs are technical artifacts (`.parquet`, cache, vector store), so exporting to readable formats is necessary for review.

---

### 3) How we installed and integrated GraphRAG locally
In this repo, GraphRAG is used as an external tool (CLI); we are not rebuilding it from scratch.

- **Install GraphRAG** (Python package `graphrag`).
- **Set API key** via `.env` / `OPENAI_API_KEY` (template: `LLM-Knowledge-Graph/graphrag-project/env.example`).
- **Prepare inputs**:
  - Source data: `LLM-Knowledge-Graph/data-from-S3-bucket/<YY-MM-DD>/corrosion_papers_<YY-MM-DD>.jsonl`
  - Convert to GraphRAG corpus: `LLM-Knowledge-Graph/graphrag-project/input/*.txt`
  - Conversion script: `LLM-Knowledge-Graph/scripts/graphrag_prepare_input.py`
- **Run indexing** with GraphRAG configs:
  - `LLM-Knowledge-Graph/graphrag-project/settings.yaml` (default)
  - `LLM-Knowledge-Graph/graphrag-project/settings.lowrate.yaml` (low concurrency for stability)

---

### 4) Current architecture/pipeline/algorithm of LLM-Knowledge-Graph (are we using GraphRAG core?)
**Yes.** The “core pipeline” we are executing is **the Microsoft GraphRAG pipeline**.

Our custom work in `LLM-Knowledge-Graph` is mainly an **adapter/wrapper layer**:
- convert UWSS/JSONL → GraphRAG-readable text corpus
- run GraphRAG stably (low-rate config + scripts)
- export outputs into readable files

**GraphRAG pipeline (high level):**
1) Load `input/*.txt` → chunking (text units)
2) `extract_graph` (LLM): entities + relationships
3) `create_communities` (Leiden): community detection
4) `create_community_reports` (LLM): community summaries
5) `generate_text_embeddings` (embeddings + vector store) for query

**Project file layout (what each part does):**
- `LLM-Knowledge-Graph/graphrag-project/`
  - `settings.yaml`, `settings.lowrate.yaml`
  - `prompts/` (GraphRAG prompts)
- `LLM-Knowledge-Graph/scripts/`
  - `graphrag_prepare_input.py`
  - `graphrag_smoketest.ps1` (supports `-OutDir` for self-contained outputs)
  - `graphrag_export_readable.py`
  - `show_graphrag_output.ps1`
- `LLM-Knowledge-Graph/src/llm_kg/`: minimal scaffold for future pipeline/CLI.

---

### 5) Outputs: what files exist, what they mean, and how to review quality
#### 5.1. Reminder: this is a setup validation run
The current outputs are from a **demo run** (smoke test) on a small subset (e.g., 3 documents) to prove:
- GraphRAG runs locally
- graph + communities + community reports are generated

#### 5.2. Where are outputs stored?
- Demo output: `LLM-Knowledge-Graph/graphrag-project/output_meeting_std/`
- Readable exports: `LLM-Knowledge-Graph/graphrag-project/output_meeting_std/human_readable/`
- GitHub demo branch containing outputs: `graphrag-output-demo`

#### 5.3. Meaning of key output files
- `documents.parquet`: normalized document table
- `text_units.parquet`: chunked text units
- `entities.parquet`: extracted entities (nodes)
- `relationships.parquet`: extracted relations (edges)
- `communities.parquet`: Leiden communities (clusters)
- `community_reports.parquet`: **community summaries** (key artifact)
- `stats.json`: run statistics
- `indexing-engine.log`: detailed logs

#### 5.4. How to read outputs (avoid direct parquet inspection)
Use the exported Markdown files:
- `human_readable/community_reports.md` (primary)
- `human_readable/entities.md`
- `human_readable/relationships.md`
- `human_readable/documents.md`
- `human_readable/communities.md`
- `human_readable/stats.json`

#### 5.5. Quality checks (how to judge “good or not” without ground truth)
- **Check 1 — Did the pipeline complete?** (`stats.json`: `num_documents > 0` and `create_community_reports` present)
- **Check 2 — Are community summaries on-topic?** (read `community_reports.md`)
- **Check 3 — Are entities/relations reasonable?** (`entities.md`, `relationships.md`)

Current qualitative result:
- partially on-topic communities exist
- noise exists (e.g., “Crossref”) due to baseline ontology

Next improvements:
- scale up corpus size gradually
- implement domain-specific ontology + prompt tuning
- downweight/filter data-platform entities

---

### 6) Current ontology and why we used it
Current baseline ontology in config:
- `extract_graph.entity_types: [organization, person, geo, event]`

Reason for baseline first:
- this week’s goal was **runnable validation**
- domain ontology requires **human-in-the-loop** iterations (review reports → tune prompts/types → re-index)

Planned domain ontology (next week):
- e.g., `corrosion_mechanism`, `mitigation_method`, `inhibitor`, `material`, `environment`, `test_method`, `performance_metric`, `structure_component`

---

### 7) How to run (local)
From `LLM-Knowledge-Graph/`:

1) Prepare input:
- `python scripts/graphrag_prepare_input.py --day 25-12-06 --max-docs 30 --clean`

2) Index:
- `graphrag index --root graphrag-project --config graphrag-project/settings.lowrate.yaml --method standard`

3) Export readable output:
- `powershell -ExecutionPolicy Bypass -File scripts/show_graphrag_output.ps1 -OutDir \"graphrag-project/output_meeting_std\" -N 20`

---

### 8) Conclusion: is GraphRAG suitable for our project?
**This week’s feasibility conclusion:** Microsoft GraphRAG is **suitable and viable** as the base framework because:
- it runs locally and produces the key GraphRAG artifacts (communities + community reports)
- the local-to-global design aligns with our “discovery” goal

However, we should not claim 100% final success from a small demo:
- keep GraphRAG as the primary base
- next week: scale up, design domain ontology, tune prompts, re-index
- continue to evaluate whether additional tools are needed later (visualization, evaluation, full-text extraction, etc.)
