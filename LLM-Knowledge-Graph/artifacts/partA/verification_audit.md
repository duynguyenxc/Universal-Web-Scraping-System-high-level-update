## Part A (Education) — Verification Audit (quality gates)

- output dir: `LLM-Knowledge-Graph/graphrag-project/output_partA_v2`

### Artifact presence

- **documents.parquet**: YES
- **text_units.parquet**: YES
- **entities.parquet**: YES
- **relationships.parquet**: YES
- **communities.parquet**: YES
- **community_reports.parquet**: YES
- **claims.parquet**: NO
- **covariates.parquet**: YES

### Entity quality (anti-noise)

- entities rows: **2602**

**Entity types (counts)**

| type               |   count |
|:-------------------|--------:|
| ASSESSMENT_MEASURE |     998 |
| OUTCOME            |     389 |
| MECHANISM          |     311 |
| INTERVENTION       |     188 |
| SETTING_CONTEXT    |     174 |
| TASK_CASE          |     103 |
| LEARNER_CONTEXT    |      81 |
| STUDY_DESIGN       |      79 |
| COGNITIVE_STATE    |      74 |
|                    |      57 |
| LEARNER_POPULATION |      51 |
| MOTIVATION_AFFECT  |      38 |
| CONTEXT            |      25 |
| CLINICAL_DOMAIN    |      22 |
| COMPARATOR         |      12 |

- blacklisted-looking entity titles (heuristic): **13 / 2602**

**Top entities by frequency (spot-check for bibliographic noise)**

| title                        | type               |   frequency |   degree |
|:-----------------------------|:-------------------|------------:|---------:|
| DIAGNOSTIC ACCURACY          | OUTCOME            |          24 |      125 |
| COGNITIVE LOAD               | COGNITIVE_STATE    |          23 |       63 |
| LEARNING OUTCOMES            | OUTCOME            |          22 |        6 |
| LEARNING ENVIRONMENT         | SETTING_CONTEXT    |          18 |        5 |
| CLINICAL SETTING             | SETTING_CONTEXT    |          16 |       22 |
| MEDICAL STUDENTS             | LEARNER_POPULATION |          15 |       68 |
| COGNITIVE STRATEGIES         | MECHANISM          |          13 |        0 |
| CLINICAL CASES               | TASK_CASE          |          11 |       14 |
| MOTIVATION                   | MOTIVATION_AFFECT  |          10 |       23 |
| COGNITIVE LOAD MANAGEMENT    | MECHANISM          |          10 |        0 |
| CASE COMPLEXITY              | TASK_CASE          |          10 |        3 |
| DIAGNOSTIC PERFORMANCE       | OUTCOME            |           9 |       51 |
| LEARNING OUTCOMES ASSESSMENT | ASSESSMENT_MEASURE |           9 |        0 |
| CLINICAL REASONING SKILLS    | OUTCOME            |           9 |        0 |
| COGNITIVE REFLECTION         | MECHANISM          |           8 |        0 |
| COGNITIVE PROCESSES          | MECHANISM          |           8 |        6 |
| KNOWLEDGE RETENTION          | OUTCOME            |           8 |        0 |
| SELF-EXPLANATION             | INTERVENTION       |           7 |       46 |
| COGNITIVE LOAD REGULATION    | MECHANISM          |           7 |       14 |
| CLINICAL REASONING           | MECHANISM          |           7 |       22 |
| ANXIETY                      | MOTIVATION_AFFECT  |           6 |       12 |
| UNCERTAINTY TOLERANCE        | COGNITIVE_STATE    |           6 |       11 |
| CONTROL GROUP                | COMPARATOR         |           6 |       19 |
| COGNITIVE PERFORMANCE        | OUTCOME            |           6 |        0 |
| DIAGNOSTIC STRATEGIES        | MECHANISM          |           5 |        3 |

### Claim quality (traceability + CMO)

- source: **claims_fixed.parquet**
- claims rows: **1592**
- claims with `[PAGE N]` marker in source_text: **972 / 1592**

**Claim completeness (heuristic)**

- missing subject: **0 / 1592**
- missing object: **0 / 1592**
- missing evidence span (source_text/text): **534 / 1592**

**Claim types (counts)**

| type                  |   count |
|:----------------------|--------:|
| OUTCOME_MEASUREMENT   |     731 |
| SUSPECTED             |     381 |
| MECHANISM_EXPLANATION |     249 |
| INTERVENTION_EFFECT   |     175 |
| CONTEXT_MODERATOR     |      44 |
| COMPARATOR            |       8 |
| INTERVENTION          |       2 |
| TRUE                  |       2 |

**Sample claims (spot-check)**

| subject_id                            | object_id                        | type                  | covariate_type   | status   | description                                                                                                                                                               | source_text                                                                                                                                                                                                                         | text_unit_id                                                                                                                     |
|:--------------------------------------|:---------------------------------|:----------------------|:-----------------|:---------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------|
| CASE-BASED CLINICAL REASONING SEMINAR | DIAGNOSTIC COMPETENCE            | INTERVENTION_EFFECT   | claim            | TRUE     | This seminar intervention improved aspects of diagnostic competence among students. CMO[C=NONE; I=CASE-BASED CLINICAL REASONING SEMINAR; M=NONE; O=DIAGNOSTIC COMPETENCE] | This seminar intervention improved aspects of diagnostic competence among students.                                                                                                                                                 | 391c7b5d79db439034c81f94da0d2622bec728fe85667ae24b0ed5ba165674948a771b0a8a814762ee78de03eb32037438c79e2fc43dff4a1bc70c6afb58f1cf |
| CYTOPATHOLOGY                         | ANALYTIC REASONING               | INTERVENTION_EFFECT   | claim            | TRUE     | Analytic reasoning is a traditional approach in cytopathology training.                                                                                                   | CMO[C=CYTOPATHOLOGY; I=ANALYTIC REASONING; M=NONE; O=NONE] [PAGE 1]                                                                                                                                                                 | b5279164dec1d5a9fd245d68cdca556cbf7f0f9e6fa236c9f98d53cec965ebbb423bb772b2477c1d2230117dd969589a3ca7418a631da6320f8d9530c3cfc251 |
| NOVICE PARTICIPANTS                   | DIAGNOSTIC ACCURACY              | OUTCOME_MEASUREMENT   | claim            | TRUE     | Diagnostic accuracy improved significantly between tests 1 and 2.                                                                                                         | CMO[C=NONE; I=NONE; M=NONE; O=DIAGNOSTIC ACCURACY] [PAGE 1]                                                                                                                                                                         | b5279164dec1d5a9fd245d68cdca556cbf7f0f9e6fa236c9f98d53cec965ebbb423bb772b2477c1d2230117dd969589a3ca7418a631da6320f8d9530c3cfc251 |
| NOVICE PARTICIPANTS                   | RESPONSE TIME                    | OUTCOME_MEASUREMENT   | claim            | TRUE     | Response times were generally faster under nonanalytic conditions than analytic conditions.                                                                               | CMO[C=NONE; I=NONE; M=NONE; O=RESPONSE TIME] [PAGE 1]                                                                                                                                                                               | b5279164dec1d5a9fd245d68cdca556cbf7f0f9e6fa236c9f98d53cec965ebbb423bb772b2477c1d2230117dd969589a3ca7418a631da6320f8d9530c3cfc251 |
| NOVICE PARTICIPANTS                   | DIAGNOSTIC ACCURACY              | OUTCOME_MEASUREMENT   | claim            | TRUE     | Diagnostic accuracy decreased between tests 2 and 3.                                                                                                                      | CMO[C=NONE; I=NONE; M=NONE; O=DIAGNOSTIC ACCURACY] [PAGE 1]                                                                                                                                                                         | b5279164dec1d5a9fd245d68cdca556cbf7f0f9e6fa236c9f98d53cec965ebbb423bb772b2477c1d2230117dd969589a3ca7418a631da6320f8d9530c3cfc251 |
| CYTOPATHOLOGY                         | TRAINING STRATEGY                | MECHANISM_EXPLANATION | claim            | TRUE     | Encouraging nonanalytic strategies may expedite visual interpretation skill acquisition.                                                                                  | CMO[C=CYTOPATHOLOGY; I=TRAINING STRATEGY; M=NONANALYTIC STRATEGY; O=VISUAL INTERPRETATION SKILLS] [PAGE 1]                                                                                                                          | b5279164dec1d5a9fd245d68cdca556cbf7f0f9e6fa236c9f98d53cec965ebbb423bb772b2477c1d2230117dd969589a3ca7418a631da6320f8d9530c3cfc251 |
| CYTOPATHOLOGY                         | ANALYTIC/NONANALYTIC COMBINATION | OUTCOME_MEASUREMENT   | claim            | FALSE    | Combining analytic and nonanalytic reasoning does not appear to be effective.                                                                                             | CMO[C=CYTOPATHOLOGY; I=ANALYTIC/NONANALYTIC COMBINATION; M=NONE; O=EFFECTIVENESS] [PAGE 1]                                                                                                                                          | b5279164dec1d5a9fd245d68cdca556cbf7f0f9e6fa236c9f98d53cec965ebbb423bb772b2477c1d2230117dd969589a3ca7418a631da6320f8d9530c3cfc251 |
| CYTOPATHOLOGY                         | COST-EFFECTIVENESS               | OUTCOME_MEASUREMENT   | claim            | TRUE     | Evidence-based strategies may improve cost-effectiveness of cytopathology services.                                                                                       | CMO[C=CYTOPATHOLOGY; I=NONE; M=NONE; O=COST-EFFECTIVENESS] [PAGE 1]                                                                                                                                                                 | b5279164dec1d5a9fd245d68cdca556cbf7f0f9e6fa236c9f98d53cec965ebbb423bb772b2477c1d2230117dd969589a3ca7418a631da6320f8d9530c3cfc251 |
| NOVICE PARTICIPANTS                   | VISUAL LEARNING                  | OUTCOME_MEASUREMENT   | claim            | TRUE     | Training strategies that include nonanalytic reasoning enhance diagnostic performance of novices.                                                                         | CMO[C=NONE; I=NONE; M=NONE; O=DIAGNOSTIC PERFORMANCE] [PAGE 2]                                                                                                                                                                      | b5279164dec1d5a9fd245d68cdca556cbf7f0f9e6fa236c9f98d53cec965ebbb423bb772b2477c1d2230117dd969589a3ca7418a631da6320f8d9530c3cfc251 |
| CYTOPATHOLOGY                         | VISUAL INTERPRETATION SKILLS     | OUTCOME_MEASUREMENT   | claim            | TRUE     | The study aims to expedite the acquisition of visual interpretation skills in cytopathology.                                                                              | CMO[C=CYTOPATHOLOGY; I=NONE; M=NONE; O=VISUAL INTERPRETATION SKILLS] [PAGE 2]                                                                                                                                                       | b5279164dec1d5a9fd245d68cdca556cbf7f0f9e6fa236c9f98d53cec965ebbb423bb772b2477c1d2230117dd969589a3ca7418a631da6320f8d9530c3cfc251 |
| ANALYTIC TRAINING                     | DIAGNOSTIC PERFORMANCE           | INTERVENTION_EFFECT   | claim            | TRUE     | Analytic training improved diagnostic performance by teaching morphological features of normal and abnormal cells.                                                        | Following the baseline test, 24 participants were randomly allocated to receive “analytic training,” in which they were taught the morphological features of normal and abnormal cells by an experienced cytology trainer. [PAGE 5] | 52612ce70fd1aa19875a5a8b636ddbf691b09a4ec28f33cbadbd17aeb698092657e4c00dd2d3fc1d3809def709e281e1282d48d13626d3c8cdd0fe987ed9686a |
| NONANALYTIC TRAINING                  | DIAGNOSTIC PERFORMANCE           | INTERVENTION_EFFECT   | claim            | TRUE     | Nonanalytic training improved diagnostic performance by allowing participants to develop pattern recognition skills.                                                      | This group of 25 participants was subjected to the same format of training, practice, and testing as was the “analytic training” group, and the same images were used. [PAGE 5]                                                     | 52612ce70fd1aa19875a5a8b636ddbf691b09a4ec28f33cbadbd17aeb698092657e4c00dd2d3fc1d3809def709e281e1282d48d13626d3c8cdd0fe987ed9686a |

### Community structure

- communities rows: **57**

### Community report quality (principle-level heuristics)

- community_reports rows: **57**
- generic/too-short titles (heuristic): **0 / 57**

**Community report headers (sample)**

|   community |   level | title                                                                     |   rank |   size |
|------------:|--------:|:--------------------------------------------------------------------------|-------:|-------:|
|          51 |       2 | Diagnostic Accuracy and Clinical Training Community                       |    8   |     22 |
|          52 |       2 | Test-Enhanced Learning Paradigm and Clinical Reasoning                    |    7.5 |      4 |
|          53 |       2 | SERIOUS GAME Community for Surgical Training                              |    8   |     14 |
|          54 |       2 | Serious Game for Clinical Decision-Making Training                        |    8   |     17 |
|          55 |       2 | Serious Game Performance Assessment Community                             |    7.5 |      4 |
|          56 |       2 | Learning Outcomes and Extra Time-on-Task                                  |    3   |      2 |
|          15 |       1 | Self-Explanation in Medical Education                                     |    7.5 |     12 |
|          16 |       1 | Active Learning Strategies in Medical Education                           |    8   |      4 |
|          17 |       1 | Clinical Reasoning and Self-Explanation in Medical Education              |    7.5 |     13 |
|          18 |       1 | Impact of Self-Explanation on Diagnostic Performance in Medical Education |    7.5 |      9 |
|          19 |       1 | Self-Explanation and Learning Outcomes Community                          |    7.5 |      4 |
|          20 |       1 | Diagnostic Accuracy and Clinical Training Community                       |    7.5 |     26 |
|          21 |       1 | Analytic Reasoning Group at Seoul National University College of Medicine |    7.5 |      3 |
|          22 |       1 | Analytic Tendencies and Diagnostic Accuracy in ECG Analysis               |    7.5 |      2 |
|          23 |       1 | Diagnostic Accuracy and Bias in Undergraduate Psychology Students         |    7.5 |     13 |

### What to verify against Richmond (next)

- **Search/screening alignment**: overlap with Richmond-28 + explain mismatches.
- **CMO fidelity**: do extracted claims support C→M→O patterns?
- **Concept alignment**: map community titles ↔ Richmond mechanisms/programme theory components.
- **Cross-study synthesis**: identify dominant patterns + contradictions with citations/spans.
