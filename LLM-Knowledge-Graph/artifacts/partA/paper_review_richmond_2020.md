## Paper review — Richmond et al. (2020) (Realist review; “The student is key”)

### 1) Full citation (as provided)
Richmond A, Cooper N, Gay S, Atiomo W, Patel R. **The student is key: A realist review of educational interventions to develop analytical and non-analytical clinical reasoning ability**. *Medical Education*. 2020;54:709–719. DOI: `10.1111/medu.14137`.

### 2) What the authors try to do (problem, goal, outcome)
- **Problem**: Educational interventions for clinical reasoning show mixed effectiveness; “what works” does not transfer uniformly across learners and contexts.
- **Goal**: Use a **realist review** approach to explain not only whether interventions work, but **why they work, for whom, and under what circumstances** (the realist “why/for whom/when” lens).
- **Output/Outcome of the paper**: A **programme theory** built from **CMOCs** (Context–Mechanism–Outcome Configurations) across **28 papers**.

### 3) What they had “in mind” from the beginning (initial theory / assumptions)
The realist review starts from an **Initial Programme Theory (IPT)**, then iteratively refines it.

Evidence (from the abstract excerpt you shared):
- “Literature from a scoping search, combined with expert opinion and researcher experience was synthesised to generate an initial programme theory (IPT).”

Interpretation:
- Their starting point is not “blank-slate”. They begin with:
  - an initial theory about how reasoning develops (analytic + non-analytic),
  - and an assumption that **context and mechanism** shape outcomes.

**Concrete IPT statement (for the professor’s “what was in their mind?” question):**
- **IPT (compact)**: Educational interventions improve clinical reasoning **only when** the learner’s **context** (e.g., prior knowledge, self-efficacy/confidence, coping) supports the intervention’s **mechanisms** (cognitive/emotional responses such as understanding vs anxiety/cognitive load), which then produces measurable **outcomes** (e.g., diagnostic accuracy/performance).

### 4) What is the input from human? (answering the professor’s question)
In Richmond et al. (2020), **human input is essential and front-loaded**:
- **IPT construction** from:
  - scoping search,
  - **expert opinion**,
  - **researcher experience**,
  - team consensus (the paper describes the team as clinical teachers with expertise).
- **Human interpretation/inference of mechanisms**:
  - The methods explicitly note mechanisms may be hard to “see” and can be inferred using learning theories.

This directly answers “what is the input from human?”:
- Humans provide the **initial theory**, define what counts as **context/mechanism/outcome**, and perform/validate **CMOC coding and synthesis**.

### 5) What did they do next? (process from start to result)
Evidence (from the excerpt you shared):
- They performed structured database searching (MEDLINE, PsycINFO, ERIC, CINAHL).
- They selected articles relevant to **the developing theory** (not only relevance to a narrow PICO question).
- They devised **CMOCs for included full texts**, compared across studies, and iteratively refined theory.

High-level workflow (realist review):
1. Build IPT (human-driven).
2. Search and screen papers (theory-driven inclusion).
3. Extract data into **CMOCs** (C–M–O).
4. Compare CMOCs, find recurrent patterns, and refine programme theory.
5. Summarize final contexts/mechanisms/outcomes.

### 6) What did they “try to get” from each paper, and how did they come out with results?
They are not extracting only effect sizes; they are extracting **explanatory structure**:
- **Contexts** (learner-level, teacher-level, organizational-level).
- **Mechanisms** as “resources and responses”.
- **Outcomes** (diagnostic accuracy, knowledge structures, etc.).

Their results are “how/why” statements supported by multiple studies, expressed as:
- “When C, then intervention resource triggers response M, leading to outcome O.”

**Operational checklist (what they try to extract from each paper):**
- **Context (C)**: learner-level moderators (knowledge level, self-efficacy/confidence, coping), teacher/organizational contexts when stated.
- **Intervention (I)**: instructional method/resource introduced (simulation, worked examples, feedback, explicit instruction, etc.).
- **Mechanism-Resource (Mresource)**: what the intervention provides (structure, examples, feedback, practice environment).
- **Mechanism-Response (Mresponse)**: learner cognitive/affective response (understanding/insight vs stress/panic/cognitive load).
- **Outcome (O)**: measured/reported endpoint (diagnostic accuracy, retention, satisfaction, etc.).
- **Evidence anchor**: where the text supports CMOC (page/paragraph/snippet) for auditability.

### 7) Key findings (what matters for our KG/agent project)
Evidence (from excerpt you shared):
- They identify **five key student-level contexts**, including:
  - low knowledge / inability to apply knowledge,
  - high domain-specific knowledge,
  - positive coping / appropriate self-efficacy,
  - negative coping / low self-efficacy,
  - mixed knowledge levels within group.
- Mechanisms and outcomes vary by these contexts.

### 8) What entities and relationships does this paper imply for a Knowledge Graph?
This paper effectively defines a **CMO ontology** for our Literature Knowledge Graph (LKG).

#### Entities (construct-level; what the professor emphasized)
- **Context entities (C)**:
  - prior knowledge (low/high), domain familiarity, self-efficacy, self-confidence, coping strategy, anxiety/stress susceptibility, etc.
- **Intervention entities (I)**:
  - simulation / real cases, worked examples, explicit reasoning instruction, feedback, test-enhanced learning, etc.
- **Mechanism entities (M)**:
  - cognitive load, self-explanation, illness scripts, pattern recognition, reflection, etc.
- **Outcome entities (O)**:
  - diagnostic accuracy, diagnostic performance, error rate, retention, confidence rating, etc.

#### Relationship patterns (CMO-style; the “edges” we need)
- `CONTEXT → (enables/blocks) MECHANISM`
- `CONTEXT → (moderates) OUTCOME`
- `INTERVENTION → (triggers) MECHANISM`
- `MECHANISM → (leads_to) OUTCOME`
- `INTERVENTION → (improves/harms) OUTCOME` (when mechanism is implicit)

This matches the professor’s examples: “This pedagogy leads to good learning outcome” and “entities are categories/phenomena, not names”.

### 9) How this paper maps to the professor’s abstract (agentic systematic review)
Richmond et al. (2020) provides a **manual reference workflow** we want to automate:
- Human builds IPT and CMOCs → we aim to let **agents + LKG (GraphRAG)** do parts of that work with audit trails.

### 10) Limitations / what we still need (for the project plan)
For an agentic pipeline, we must:
- operationalize CMOC extraction into a **schema**,
- enforce evidence traceability (claim → snippet/page),
- handle contradictions explicitly (not smooth over).

