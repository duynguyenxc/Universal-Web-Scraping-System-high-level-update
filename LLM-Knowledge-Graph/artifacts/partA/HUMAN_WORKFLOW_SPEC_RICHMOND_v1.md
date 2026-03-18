## Human Workflow Specification (Gold Standard): Richmond et al. (2020) Realist Review — Human Reviewer Architecture and Algorithm

### 1.1 Objective (what the human workflow is trying to achieve)
Richmond et al. (2020) conduct a realist review to build an **explanatory programme theory** of **how educational interventions develop analytical and non‑analytical clinical reasoning** in undergraduate health professions education, explicitly addressing **why interventions work, for whom, when, and under what circumstances**.

Evidence (abstract excerpt captured in `paper_review_richmond_2020.md`):
- “Literature from a scoping search, combined with expert opinion and researcher experience was synthesised to generate an initial programme theory (IPT).”

Evidence (methods summary captured in `paper_review_richmond_2020.md`):
- Realist data are analysed to form **CMOCs** (Context–Mechanism–Outcome Configurations) which collectively form a **programme theory**.

This specification unpacks the **sequence of reasoning operations**, decision rules, and intermediate products that produced the paper’s conclusions.

---

## 2. Human “System Architecture” (who does what, with what tools, producing what artefacts)

### 2.1 Human roles (team workflow, not single-person extraction)
Richmond’s workflow is executed as a **team process** with explicit coding + consistency checking.

- **Lead reviewer (AR)**:
  - Performs background/scoping searches.
  - Runs database searches.
  - Performs initial CMOC coding.
  - Synthesises results and drafts the programme theory narrative.

- **Research team / second reviewers**:
  - Provide domain expertise (clinical teaching perspective).
  - Provide consensus building on IPT and theory refinements.
  - Check CMOC coding consistency across all included studies.

Evidence (captured in `paper_review_richmond_2020.md`):
- “Initial CMOC coding was undertaken by AR and all 28 articles were checked for consistency by another reviewer…”

### 2.2 Tooling and data management (operational supports for reasoning)
- **NVivo**:
  - Storage of full texts.
  - Coding of contexts.

- **Microsoft Excel**:
  - Elaborate “which contexts affected the mechanisms and outcomes.”
  - Cross-study causal structure refinement and consolidation.

- **Governance / reporting anchors**:
  - PROSPERO registration and RAMESES standards are referenced as process-quality anchors for realist review reporting.

### 2.3 Core artefacts (intermediate products the workflow iteratively refines)
- **Aim + research questions** (controlling specification).
- **IPT (Initial Programme Theory)** (theory seed; defines relevance).
- **Search specification** (databases, time bounds, terms; term expansion loop).
- **Screening and appraisal decisions** (inclusion tied to theory contribution + credibility).
- **CMOC set** (within- and cross-study CMOCs).
- **Cross-study pattern map** (recurrent CMOC patterns and consolidations).
- **Final programme theory** (narrative + evidence-backed CMOCs).

---

## 3. Human Algorithm (step-by-step operations, decision rules, and iterative loops)

### Stage 0 — Problem framing: define realist explanatory intent and formal questions
**Input**
- Educational importance of clinical reasoning development.
- Assumption: interventions will not work uniformly across learners/contexts.

**Operation (human reasoning)**
- Establish realist aim: explanation via C/M/O and conditional causation.
- Derive explicit research questions from that aim.

**Output**
- Stated aim + research questions guiding the whole review.

### Stage 1 — IPT construction (theory seeding; primary human import)
This stage is the core “human import” step: humans define what the system will later treat as *relevant evidence*.

**Input**
- Scoping/background literature.
- Expert opinion and researcher experience.
- Team consensus (clinical teachers).
- Complementary learning theories that shape how “context levels” are conceptualised.

**Operation (algorithmic sequence)**
1. Conduct scoping/background searches.
2. Draft candidate CMOC hypotheses.
3. Obtain research-team feedback and converge via consensus.
4. Consolidate into an IPT + a context-level lens (e.g., student/teacher/activity/organisation).

**Output**
- IPT + initial CMOC hypotheses + context-lens for subsequent screening and synthesis.

Evidence (captured in `paper_review_richmond_2020.md`):
- “Literature from a scoping search, combined with expert opinion and researcher experience was synthesised to generate an initial programme theory (IPT).”

### Stage 2 — Search strategy and execution: theory-driven retrieval with deliberate term expansion
**Input**
- IPT constructs (theory seed determines what to retrieve).

**Operation**
1. Search databases (MEDLINE, PsycINFO, ERIC, CINAHL).
2. Apply time boundary (search begins at year 2000; paper justification links to patient-safety context).
3. Expand terms when early results reveal missing constructs (e.g., pattern recognition, illness scripts, deliberate practice).

**Output**
- Candidate corpus for screening/appraisal.

### Stage 3 — Screening and appraisal: include for theory contribution; assess credibility
**Input**
- Candidate corpus (titles/abstracts → full texts).

**Operation**
1. Title/abstract screening for theory contribution.
2. Full-text appraisal for methodological credibility/trustworthiness.
3. Apply operational definition of “educational intervention” (include techniques that can be integrated into an intervention).
4. Reference-list searching for additional theory-contributing studies.

**Output**
- Included set driving theory refinement (Richmond-28) plus exclusion rationales.

Evidence (captured in `paper_review_richmond_2020.md`):
- “studies retrieved if they were deemed to contribute to theory building.”
- Included set: 28 studies (flow described in the paper; 25 + reference-list additions).

### Stage 4 — Data extraction and CMOC coding: convert each included paper into causal explanations
**Input**
- 28 included full texts + IPT/CMOC framing.

**Operation**
1. Devise CMOCs per full text.
2. Apply realist inference rule: mechanisms/outcomes may be implicit and can be theorised/inferred using learning theory + study data.
3. QA loop:
   - lead reviewer codes
   - second reviewer checks all included papers for consistency.
4. Manage codes in NVivo; elaborate cross-links in Excel.

**Output**
- CMOC set across included studies with structured C–M–O links and evidence anchors.

Evidence (captured in `paper_review_richmond_2020.md`):
- “The CMOCs were devised for all included full texts.”
- “Mechanisms… are not always explicit… can be theorised… or inferred…”

### Stage 5 — Cross-study synthesis and iterative refinement: consolidate patterns into programme theory
**Input**
- CMOC set + IPT (initial theory) + contradictions/variations.

**Operation**
1. Identify recurrent CMOC patterns across studies.
2. Consolidate similar CMOCs into mechanism/context families.
3. Re-analyse earlier studies as theory evolves (iterative loop).
4. Produce final backbone: key contexts + mechanisms determining effectiveness.

**Output**
- Refined programme theory expressed via CMOCs, emphasizing student-level contexts; teacher/organizational contexts noted as rarely discussed.

---

## 4. Public, verifiable outputs (gold-standard targets)
These are observable outputs a benchmark can target directly:
- **Included set**: final included size 28; screening flow in the paper.
- **Programme theory expressed via CMOCs**: CMOCs collectively form programme theory.
- **Key contexts (student-level) enumerated** (captured in `paper_review_richmond_2020.md`):
  - low knowledge / inability to apply knowledge
  - high domain-specific knowledge
  - positive coping / appropriate self-efficacy
  - negative coping / low self-efficacy
  - mixed knowledge levels within a group

---

## 5. What this specification clarifies (for agent replication)
- The human workflow is **not** “feed 28 papers and summarise”; it is:
  - IPT-first (human import),
  - theory-driven screening,
  - CMOC extraction with permitted mechanism inference,
  - iterative cross-study refinement into a programme theory.

