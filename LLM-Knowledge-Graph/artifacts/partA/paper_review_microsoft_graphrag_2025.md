## Paper review — Microsoft GraphRAG (Edge et al., 2025) (“From Local to Global”)

### 1) Full citation (as provided)
Edge D, Trinh H, Cheng N, Bradley J, Chao A, Mody A, Truitt S, Metropolitansky D, Ness RO, Larson J. **From Local to Global: A GraphRAG Approach to Query-Focused Summarization**. arXiv:2404.16130v2 (19 Feb 2025). (Preprint; under review.)

### 2) What the authors try to do (problem, goal, outcome)
- **Problem**: Conventional “vector RAG” retrieves a small set of semantically similar chunks and works for **local fact questions**, but fails on **global sensemaking** questions like “What are the main themes in the dataset?” (query-focused summarization over whole corpus).
- **Goal**: Propose **GraphRAG**, a graph-based RAG approach that scales with:
  - corpus size (million-token range),
  - and question generality (global questions).
- **Outcome**: GraphRAG improves **comprehensiveness** and **diversity** of answers over a vector-RAG baseline for global sensemaking tasks (as described in the excerpt you shared).

### 3) What they had “in mind” from the beginning
They treat global questions as a **summarization/sensemaking** problem rather than “retrieve a few relevant passages”.

GraphRAG’s key design idea:
- Build a **graph index** (entities + relationships + claims).
- Use **community detection** (Leiden) to create **communities** (topics/themes).
- Pre-generate **community summaries** (index time).
- Answer queries by map-reduce over community summaries (query time).

**Pipeline keywords (for the professor’s “process” question):**
- **Index time**: chunking → entity/relation extraction → graph aggregation → **Leiden** community detection → **community reports** (summaries).
- **Query time**: retrieve community summaries (by level) → **map** partial answers → **reduce** to global answer.

### 4) What is the input from human? (answering the professor’s question)
GraphRAG is not “fully automatic” in the scientific workflow sense; it has clear human-controlled inputs:
- **Corpus selection**: which documents/papers are included.
- **Chunking parameters**: chunk size/overlap (trade-off cost vs recall).
- **Entity schema & prompting**:
  - entity types,
  - few-shot exemplars,
  - prompt constraints (what to avoid, what to prioritize).
- **Evaluation framing** (in their paper):
  - what counts as good global answers (comprehensiveness/diversity/empowerment/directness).

In short: **humans define the extraction/synthesis schema and constraints**; GraphRAG executes extraction/summarization over the corpus.

**Human input (two-tier framing, aligned to the professor’s abstract):**
- **Research/theory input**: what constructs matter (intervention/context/mechanism/outcome), what counts as evidence, what contradictions matter.
- **System/config input**: corpus selection, chunking params, entity types, prompt exemplars, validators/thresholds, reporting format.

### 5) What did they do next? (process from start to result)
GraphRAG workflow (as described in the paper):
1. **Source documents → text chunks**
2. **Chunks → entities & relationships** (LLM extraction)
3. **(Aggregate) → knowledge graph**
4. **Knowledge graph → communities** (Leiden; hierarchical)
5. **Communities → community summaries** (report-like summaries)
6. **Query time**: community summaries → partial answers → final global answer (map-reduce)

### 6) What did they “try to get” from each document, and how did they produce results?
GraphRAG extracts:
- **Entities**: key concepts in the corpus (domain-tailored).
- **Relationships**: connections among concepts.
- **Claims (optional but important)**: verifiable factual statements attached to entities.

Then it produces results by:
- summarizing communities (global thematic structure),
- then generating global answers by aggregating partial answers.

### 7) What this implies for our education systematic review project (and the professor’s abstract)
The professor’s abstract proposes:
- a domain-adapted LLM + a Literature Knowledge Graph (LKG),
- GraphRAG as the retrieval/graph reasoning layer,
- multi-agent orchestration (LangChain/GraphChain or both),
- full traceability to protocol and evidence.

GraphRAG matches the “LKG + Graph-enhanced retrieval” part:
- GraphRAG provides:
  - structured entities/relations/claims,
  - community-level summaries (global themes),
  - a query-time mechanism for global sensemaking.

### 8) Evidence that GraphRAG can support the required “auditable” workflow (from our v3 run)
We ran GraphRAG on a **subset5 corpus** (5 full-text papers converted to `.txt` input files) as a **prototype run** to validate end-to-end artifacts and evidence traceability (not a final realist-ready KG yet).

From `artifacts/partA/verification_audit_v3.md`:
- **entities.parquet**: 216 entities
  - key construct hubs include `DIAGNOSTIC ACCURACY` (frequency 10, degree 62)
- **relationships.parquet**: 186 relationships
- **community_reports.parquet**: 15 communities with non-generic titles (0/15 generic titles)
- **claims_fixed.parquet**: 792 evidence claims
  - claims with `[PAGE N]` marker: **768/792**
  - missing evidence span: **13/792**

Interpretation for the professor:
- GraphRAG can produce **global thematic summaries** (communities) and **evidence-grounded claims** (with page markers) suitable for verification workflows.

### 9) Limitations relevant to our project plan (what to improve with feedback + agents)
From our v3 run:
- **Entity typing noise** remains (blank types and a schema inconsistency `COGNITIVE STATE` vs `COGNITIVE_STATE`).
- **Relationship directionality** needs stronger constraints (too many `OUTCOME → ...` edges), which matters for CMO-style reasoning.
- **Claims formatting** is mostly good but not perfect (a small number of invalid claim types).

This directly motivates:
- **human feedback seeds** (prompt rules) and/or
- an **agentic validation layer** (e.g., citation validator, schema validator, contradiction checker)
to enforce protocol-aligned outputs.

