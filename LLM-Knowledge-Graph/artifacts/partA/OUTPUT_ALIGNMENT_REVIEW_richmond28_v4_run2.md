## Output alignment review — Richmond‑28 run (`output_partA_richmond28_v4_run2`)

This is a **professional, audit‑oriented review** of whether the current run’s **entities** and **relationships** look aligned with the constructs and causal structure Richmond et al. (2020) describe (CMOC → programme theory).

### 1) Run artefacts inspected
- Entities sample: `graphrag-project/output_partA_richmond28_v4_run2/human_readable_interim/entities.md`
- Relationships sample: `graphrag-project/output_partA_richmond28_v4_run2/human_readable_interim/relationships.md`
- Quality gates: `graphrag-project/output_partA_richmond28_v4_run2/human_readable/quality_gates.md`
- Scorecard: `artifacts/partA/scorecard_output_partA_richmond28_v4_run2.md`

### 2) What “aligned with Richmond” means (operational)
Aligned means the KG supports the same explanatory backbone as Richmond:
- It represents **Context / Mechanism / Outcome** (and Intervention resources) as construct-level nodes.
- It has strong **CMOC-family edges** (C→M, I→M, M→O, I→O).
- It does **not** drown the graph in bibliographic or measurement-only noise.
- It enables evidence-traceability to full texts (claims + `[PAGE N]` anchors) for verification.

### 3) High-signal positives (what already looks “sát Richmond”)

#### 3.1 Core outcomes and mechanisms appear
The entity sample contains canonical realist targets that match Richmond’s review focus:
- Outcomes: **DIAGNOSTIC ACCURACY**, **DIAGNOSTIC PERFORMANCE**, **ERROR RATE**
- Mechanism-like constructs: **PATTERN RECOGNITION**, **INSIGHT**, **COGNITIVE BIASES**, **WORKING MEMORY RESOURCES**

This is consistent with the gold target list used in evaluation (see scorecard).

#### 3.2 Relationship structure is broadly CMOC-shaped
Quality gates show:
- CMOC-family edges (normalized): **795 / 933 = 85.21%**
- OUTCOME-as-source edges (normalized): **0 / 933 = 0.00%**

Interpretation:
- The run’s relationship graph is **structurally compatible** with CMOC-style causal explanations (good).

### 4) Misalignments / problems (what is NOT yet “khớp Richmond”)

#### 4.1 Entity typing is not verification-ready (hard fail gate)
Quality gates show:
- blank entity types: **0** (target 0)

Interpretation:
- The normalized KG is now **verification-grade** w.r.t typing (no blank types).
- Remaining work shifts from “missing types” to **better realist typing fidelity** (e.g., context coverage and mechanism resource vs reaction separation).

#### 4.2 Some key constructs are mis-typed (example: reasoning treated as “INTERVENTION”)
In the entity sample, **ANALYTIC REASONING** and **NONANALYTIC REASONING** are typed as `INTERVENTION`.

Why this is misaligned:
- In Richmond, analytic/non-analytic reasoning are **reasoning processes/strategies** (mechanism/skill), not educational interventions themselves.
- Interventions are resources/techniques (e.g., seminar, training programme, feedback, simulation).

Impact:
- Mis-typing will distort downstream synthesis (programme theory) and confuse “I→M→O” pathways.

#### 4.3 Context layer is incomplete relative to Richmond’s “student is key” contexts
Scorecard keyword-proxy recall:
- contexts hit: **3/9** (CONFIDENCE, PRIOR KNOWLEDGE, SELF-EFFICACY)

Missing (relative to Richmond’s five student-level contexts captured in `paper_review_richmond_2020.md`):
- positive coping / negative coping
- mixed knowledge levels
- inability to apply knowledge

Interpretation:
- Mechanism and outcome coverage is strong; **context coverage is lagging** and needs targeted prompt+ontology improvement.

#### 4.4 Relationship descriptions sometimes contain long generic prose
In relationships sample, some edges include paragraph-length narrative text (LLM explanation) rather than a compact causal predicate.

Impact:
- Harder to normalize into CMOC claim rows.
- Increases noise and reduces auditability.

### 5) Bottom-line judgement (current run)
- **Relationships**: structurally **quite close** to CMOC-family expectations (strong positive).
- **Entities**: typing is now **verification‑grade** (no blanks) but still needs **higher-fidelity realist typing** (especially student-level contexts and mechanism resource vs reaction).
- **Richmond alignment**: **improved** — mechanisms/outcomes look strong; contexts still need targeted improvement.

### 6) Next iteration actions (concrete, non-vague)
1. **Fix entity typing**:
   - tighten `extract_graph` prompt to classify reasoning strategies as `MECHANISM` (not `INTERVENTION`).
   - expand deterministic type-mapping rules so fewer entities are dropped as unknown in the normalized KG.
2. **Improve context recall**:
   - add explicit “student-level context” extraction requirements (coping, knowledge-application ability, mixed-knowledge groups).
3. **Compact relationship predicates**:
   - constrain relationship `description` to a short causal phrase (e.g., `enables`, `inhibits`, `moderates`) plus optional evidence pointer.
4. **Claims verification gate** (when covariates completes):
   - run `partA_repair_claims_parquet.py --fill-source-from-text-units`
   - export `claims_fixed.md` + update scorecard traceability section.

