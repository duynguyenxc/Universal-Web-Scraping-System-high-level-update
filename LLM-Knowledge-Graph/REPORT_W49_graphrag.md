## Weekly deliverable (GraphRAG runnable + initial validation)

### Goal (per advisor)
- Download and use **Microsoft GraphRAG** (`microsoft/graphrag`) and make it **runnable locally**.
- Run a **small end-to-end test** on our harvested literature to confirm feasibility.
- Prepare for next step: **iterative refinement** (prompt tuning + cluster/community tuning).

### What we have in this repo now
- **GraphRAG project**: `LLM-Knowledge-Graph/graphrag-project/`
  - `settings.yaml`: base config
  - `settings.lowrate.yaml`: full config with **lower concurrency** for avoiding 429 TPM rate limits
  - `input/`: text corpus used by GraphRAG
  - `prompts/`: GraphRAG prompts (editable for refinement)
- **Data source** (S3-synced): `LLM-Knowledge-Graph/data-from-S3-bucket/<YY-MM-DD>/corrosion_papers_<YY-MM-DD>.jsonl`
- **Scripts**
  - `scripts/graphrag_prepare_input.py`: JSONL → `graphrag-project/input/*.txt`
  - `scripts/graphrag_smoketest.ps1`: prepare → index → query (and `-DryRun`)

### Commands (reproducible)
From `LLM-Knowledge-Graph/`:

1) Build a small input set (e.g., 30 docs from one day)

```bash
python scripts/graphrag_prepare_input.py --day 25-12-06 --max-docs 30 --clean
```

2) Index (GraphRAG)

```bash
graphrag index --root graphrag-project --config graphrag-project/settings.lowrate.yaml
```

3) Query (Global Search = “big picture / synthesis”)

```bash
graphrag query --root graphrag-project --method global --query "What are the main corrosion mitigation intervention clusters and their reported outcomes?"
```

4) Prompt tuning (next step for iterative refinement)

```bash
graphrag prompt-tune --root graphrag-project --config graphrag-project/settings.lowrate.yaml --domain "reinforced concrete corrosion"
```

### What happened in the first run (observations)
- **Rate limit issue**: initial indexing run hit OpenAI TPM 429 (tokens-per-minute) due to high concurrency.
- **Mitigation**: use `settings.lowrate.yaml` (lower `concurrent_requests`) and/or reduce corpus size for initial smoke tests.

### What we can report this week
- GraphRAG is **integrated and runnable locally** on our harvested data exports (JSONL → text corpus).
- The pipeline supports:
  - building the base graph from documents
  - community detection / community reports (hierarchical structure)
  - global query mode for synthesis-style questions
- Next, we will do **human-in-the-loop refinement**:
  - prompt tuning (`graphrag prompt-tune`)
  - adjust entity types + rules (domain ontology)
  - tune clustering/community level and report prompts

### Next week (refinement plan)
- Replace generic entity types `[organization, person, geo, event]` with domain types, e.g.:
  - `material`, `environment`, `corrosion_mechanism`, `mitigation_method`, `inhibitor`, `test_method`, `performance_metric`
- Run `prompt-tune` on a small subset (15–30 docs), manually edit prompts, then rerun indexing.
- Compare community reports before/after tuning (qualitative + simple metrics: #entities, #communities, coverage).

