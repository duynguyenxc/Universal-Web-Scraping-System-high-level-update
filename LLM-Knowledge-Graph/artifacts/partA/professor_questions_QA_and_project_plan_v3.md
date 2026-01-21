## Professor Q&A + What we did this week (grounded in v3 run)

This document answers the professor’s questions and connects them to the current **GraphRAG Part A v3** implementation and outputs.

**Framing (to match the professor’s “interactive process” expectation):**
- This week’s output is a **prototype run (subset5)** to validate end-to-end GraphRAG artifacts and **evidence traceability**.
- The KG is **not final / not yet realist-ready**; we identified three issues to fix before scaling to all 28 studies: **entity typing noise**, **relationship directionality**, and **minor claim schema/format noise**.
- Next iteration will use **prompt tightening + validator agents** (schema + directionality + evidence requirements) to enforce a realist C–M–O graph pattern.

### Q1) “What is the input from human?”

#### A) In Richmond et al. (2020) (realist review)
Human input is central:
- Humans create an **Initial Programme Theory (IPT)** using:
  - scoping search,
  - expert opinion,
  - researcher experience,
  - and team consensus.
- Humans interpret data into **CMOCs** (Context–Mechanism–Outcome Configurations), including inferring mechanisms when not explicit.

#### B) In Microsoft GraphRAG (Edge et al., 2025)
Human input defines “what the system extracts and how it is judged”:
- The **corpus** (which documents/papers).
- **Chunking parameters** (size/overlap) that control extraction recall vs cost.
- **Entity schema + prompts** (types, constraints, domain exemplars).
- **Evaluation framing** (what counts as good answers: comprehensiveness/diversity/empowerment, etc.).

#### C) In our project (Part A v3)
Human input (your work) is:
- Choosing a corpus slice (subset5 vs full 28).
- Providing **feedback seed rules** (what to avoid/keep for entities + relationship patterns for CMO).
- Defining the **review protocol constraints** (what must be traceable/auditable).

**Important clarification for the professor (“input from human” is not just prompts):**
- **Human input (research/theory layer)**:
  - IPT / ontology (CMO/CMOC rubric), inclusion scope, adjudication rules for contradictions.
- **Human input (system/config layer)**:
  - chunking, entity type enums, prompt constraints, validator thresholds (e.g., “no blank types”, “Outcome as sink”), and reporting templates.

Evidence from our v3 run:
- Output dir: `LLM-Knowledge-Graph/graphrag-project/output_partA_subset5_v3`
- Audit: `LLM-Knowledge-Graph/artifacts/partA/verification_audit_v3.md`
  - `claims_fixed.parquet` has **768/792** claims with `[PAGE N]` markers.

---

### Q2) “Try to understand their process from the beginning: what they have in mind; what they do next”

#### A) Richmond process (manual, theory-driven)
1. Build IPT (human theory).
2. Search & screen papers (theory-driven relevance).
3. CMOC coding (C–M–O extraction).
4. Iterative synthesis to refine programme theory (recurrent CMOC patterns).

#### B) GraphRAG process (computational, but schema-driven)
1. Corpus → text chunks
2. Chunks → entities + relationships (+ claims)
3. Graph → communities
4. Communities → community reports (global themes)
5. Query time: map-reduce summarization to answer global questions

#### C) Our Part A v3 process (what we actually executed)
1. PDFs + metadata → GraphRAG input `.txt` corpus (subset5)
2. GraphRAG indexing → `entities.parquet`, `relationships.parquet`, `communities.parquet`, `community_reports.parquet`, `covariates.parquet`
3. Normalize claims → `claims_fixed.parquet`
4. Quality gates + audit → `verification_audit_v3.md`

**Interactive iteration loop**
1. **Define/lock ontology** (CMO-first entity types + allowed relations + directionality).
2. **Run a small subset** (subset5) to get fast feedback.
3. **Audit** (blank types, outcome-as-source edges, claim evidence spans, noise patterns).
4. **Feedback seed update** (prompt constraints + validator rules).
5. **Re-run** subset until quality gates pass, then scale to **full 28**.

Evidence that we can do iterative improvement:
- A post-process/validator step on v3 parquet reduced **blank entity types 15 → 3** and **OUTCOME-as-source edges 86 → 7** (see `LLM-Knowledge-Graph/graphrag-project/output_partA_subset5_v3/kg_postprocess_report_v3.md`).

---

### Q3) “When you review the paper, what did they try to get from the paper and how did they come out with results?”

#### A) Richmond: what they extract
- C, M, O (and how interventions provide resources that trigger responses).
- Outputs are CMOC statements and a programme theory across 28 papers.

**Checklist (paper-by-paper extraction target)**:
- Context? Mechanism resource? Mechanism response? Outcome? Evidence span/page?

#### B) GraphRAG: what it extracts
- **Entities** (concepts), **relationships** (connections), **claims** (verifiable statements).
- Results come from community-level summarization + query-time aggregation.

#### C) Evidence that our run extracts the right kind of “things”
From `verification_audit_v3.md`:
- `entities.parquet`: **216** entities
  - includes construct-level nodes (e.g., `DIAGNOSTIC ACCURACY`, `ANALYTIC REASONING`, `NON-ANALYTIC REASONING`, `COGNITIVE LOAD`)
- `relationships.parquet`: **186** edges
- `community_reports.parquet`: **15** reports with specific (non-generic) titles
- `claims_fixed.parquet`: **792** claims with evidence snippets; **768/792** contain `[PAGE N]`

---

### Q4) “Knowledge Graph is only one part; we need some agent(s). How do we define roles?”

We map the manual systematic/realist review workflow into specialized agents (as in your professor’s abstract):

- **Protocol/Orchestrator agent**
  - Maintains protocol (e.g., PRISMA/RAMESES-like checklist), logs every decision.
- **Screening agent**
  - Title/abstract/full-text include-exclude with reasons.
- **CMO/Claim extraction agent**
  - Extracts CMO-style claims with evidence spans; enforces claim schema.
- **Entity/Relation schema validator agent**
  - Rejects blank types; enforces allowed type set; normalizes type spelling.
  - Enforces preferred directions (C/I → M/O; M → O), flags “reverse” edges.
- **Contradiction agent**
  - Surfaces disagreements (same intervention, different outcomes by context).
- **Citation/evidence validator agent**
  - Verifies every synthesized claim is traceable to a snippet/page.
- **Synthesis agent**
  - Builds programme-theory summaries (CMOC patterns) from graph/claims.

GraphRAG (the KG layer) provides the shared “memory”:
entities/relationships/claims/communities become the structured substrate that agents can query and validate.

**Agent roles (explicit mapping to LangChain-style design):**
- In LangChain terms, each “agent” is a **role + tools + constraints + memory**:
  - **Tools**: GraphRAG query, document retrieval, schema validator, evidence checker.
  - **Memory**: LKG artifacts (entities/relations/claims/communities) + protocol logs.
  - **Constraints**: allowed entity types/relations, evidence-required outputs.

So, the “agentic framework” is not magic: it is a controlled workflow where each agent has:
- an **input schema** (what it consumes),
- an **output schema** (what it must produce),
- a **quality gate** (what it must not violate),
- and an **audit log**.

---

### Q5) “Entities are big concepts… what entities/relationships should we build?”

Richmond implies a CMO-centric KG:

#### Entity families (construct-level)
- **Context**: prior knowledge, self-efficacy/confidence, coping strategies, cognitive load, setting constraints
- **Intervention**: simulation, worked examples, explicit instruction, feedback, test-enhanced learning
- **Mechanism**: self-explanation, illness scripts, reflection, pattern recognition, cognitive load regulation
- **Outcome**: diagnostic accuracy, performance, errors, retention, confidence

#### Relationship families (CMO edges)
- `CONTEXT → MECHANISM` (context enables/disables mechanisms)
- `CONTEXT → OUTCOME` (context moderates outcomes)
- `INTERVENTION → MECHANISM` (resources trigger processes)
- `MECHANISM → OUTCOME` (process causes outcomes)
- `INTERVENTION → OUTCOME` (direct effects when mechanism is implicit)

#### Evidence from v3 (subset5) that we are already close
From `verification_audit_v3.md`, top entities include:
- `DIAGNOSTIC ACCURACY` (OUTCOME; frequency 10; degree 62)
- `CONTRASTIVE LEARNING` (INTERVENTION)
- `ANALYTIC REASONING` / `NON-ANALYTIC REASONING` (MECHANISM)

And claims already express I→O and C→… patterns with evidence spans and page markers.

**Clear picture (what the professor wants to hear explicitly):**
- Our KG must represent **construct-level CMOC logic**, not named entities like school/student names.
- Minimal realist graph “shape”:
  - **Entities**: {Context, Intervention/Comparator, Mechanism, Outcome} (+ optional Population/Setting/StudyDesign)
  - **Edges** (direction matters): \(C/I \rightarrow M \rightarrow O\) and \(C \rightarrow O\) (moderation)
  - **Claims**: evidence rows that tie edges to text snippets with page markers.

**Concrete example**
- `SCHEMA-BASED INSTRUCTION (INTERVENTION)` → *(triggers)* → `SELF-EXPLANATION (MECHANISM)` → *(leads_to)* → `DIAGNOSTIC ACCURACY (OUTCOME)`
- `LOW PRIOR KNOWLEDGE (CONTEXT)` → *(increases)* → `COGNITIVE LOAD (MECHANISM / cognitive state)` → *(reduces)* → `DIAGNOSTIC ACCURACY (OUTCOME)`
- Each arrow must be backed by **claims with evidence** (snippet + `[PAGE N]`).

---

### Q6) “What next should I do?"

#### Immediate (this week deliverable)
1. Submit the two paper reviews:
   - `paper_review_richmond_2020.md`
   - `paper_review_microsoft_graphrag_2025.md`
2. Submit this Q&A plan document with **v3 evidence**

#### Next iteration (technical fixes based on v3 evidence)
From `verification_audit_v3.md` and direct parquet inspection:
- Fix **blank/invalid entity types** (15 blank; 4 `COGNITIVE STATE` typo) via prompt tightening + optional post-normalization.
- Reduce “reverse” edges (many `OUTCOME → ...`), enforcing CMO directionality.
- Fix remaining claim formatting noise:
  - invalid claim type strings (10 rows total).

Then rerun:
- **subset5_v3** (fast validation),
- then **full 28** for the final evidence base.
---

### Q7) “Does the paper give you any clue what KG we should build? Do you have a clear picture?”
Yes — the clue is in the *authors’ outputs*:
- **Richmond output = CMOCs + programme theory** → implies a KG that can encode CMOC patterns with traceable evidence.
- **GraphRAG output = entities/relations/claims + communities + global summaries** → implies a KG that supports global sensemaking but must be constrained to realist constructs for this project.

So the “clear picture” after reading both papers is:
- Richmond tells us **what semantics** the graph must capture (CMOC causal/moderation logic).
- GraphRAG tells us **how to compute it at scale** (extract → graph → communities → summarize), but we must enforce **schema + directionality** to keep it realist.

---


