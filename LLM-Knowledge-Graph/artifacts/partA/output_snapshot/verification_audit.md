## Part A (Education) — Verification Audit (quality gates)

- output dir: `graphrag-project/output_partA`

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

- entities rows: **1383**

**Entity types (counts)**

| type               |   count |
|:-------------------|--------:|
| MECHANISM          |     264 |
| INTERVENTION       |     210 |
| SETTING_CONTEXT    |     183 |
| OUTCOME            |     161 |
| TASK_CASE          |     150 |
| ASSESSMENT_MEASURE |     144 |
| LEARNER_POPULATION |      73 |
| STUDY_DESIGN       |      69 |
| COMPARATOR         |      68 |
| CLINICAL_DOMAIN    |      39 |
| RELATIONSHIP       |      12 |
|                    |      10 |

- blacklisted-looking entity titles (heuristic): **1 / 1383**

**Top entities by frequency (spot-check for bibliographic noise)**

| title                             | type               |   frequency |   degree |
|:----------------------------------|:-------------------|------------:|---------:|
| DIAGNOSTIC ACCURACY               | OUTCOME            |          47 |      199 |
| MEDICAL STUDENTS                  | LEARNER_POPULATION |          29 |        6 |
| DIAGNOSTIC PERFORMANCE            | OUTCOME            |          26 |       87 |
| CLINICAL REASONING                | MECHANISM          |          19 |       65 |
| CONTROL GROUP                     | COMPARATOR         |          16 |        8 |
| SELF-EXPLANATION                  | INTERVENTION       |          15 |       46 |
| COGNITIVE LOAD REGULATION         | MECHANISM          |          12 |       12 |
| CLINICAL CASES                    | TASK_CASE          |          11 |        8 |
| STUDENTS                          | LEARNER_POPULATION |           9 |        3 |
| PATTERN RECOGNITION               | MECHANISM          |           8 |        8 |
| SELF-EXPLANATION (SE)             | INTERVENTION       |           7 |       12 |
| STRUCTURED REFLECTION             | INTERVENTION       |           7 |       17 |
| TRAINING CASES                    | TASK_CASE          |           7 |        7 |
| NEAR-TRANSFER CASES               | TASK_CASE          |           6 |        3 |
| FAR-TRANSFER CASES                | TASK_CASE          |           6 |        3 |
| DIAGNOSTIC ERROR                  | OUTCOME            |           6 |       18 |
| DIAGNOSTIC KNOWLEDGE              | OUTCOME            |           6 |       34 |
| ANALYTIC REASONING                | MECHANISM          |           6 |       10 |
| UNDERGRADUATE PSYCHOLOGY STUDENTS | LEARNER_POPULATION |           5 |        3 |
| UNDERGRADUATE MEDICAL STUDENTS    | LEARNER_POPULATION |           5 |        2 |
| YEAR 4 MEDICAL STUDENTS           | LEARNER_POPULATION |           5 |        3 |
| CASEBOOK APPLICATION              | INTERVENTION       |           5 |        9 |
| KNOWLEDGE RESTRUCTURING           | MECHANISM          |           5 |        7 |
| CONTRASTIVE LEARNING              | INTERVENTION       |           5 |        8 |
| ELABORATED FEEDBACK               | INTERVENTION       |           5 |        6 |

### Claim quality (traceability + CMO)

- source: **covariates.parquet**
- claims rows: **310**
- claims with `[PAGE N]` marker in source_text: **78 / 310**

**Claim types (counts)**

| type                  |   count |
|:----------------------|--------:|
| INTERVENTION_EFFECT   |     144 |
| CONTEXT_MODERATOR     |      38 |
| MECHANISM_EXPLANATION |      32 |
| OUTCOME_MEASUREMENT   |      16 |
| COMPARATOR_OUTCOME    |       1 |

**Sample claims (spot-check)**

| type                  | covariate_type   | status   | description                                                                                                                                                                                    | source_text                                                                                                                                                                                                                                                                                                                                                                             |
|:----------------------|:-----------------|:---------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| INTERVENTION_EFFECT   | claim            | TRUE     | The case-based clinical reasoning seminar intervention improved aspects of diagnostic competence by providing students with insight into cognitive features of their reasoning.                | This case-based clinical reasoning seminar intervention, designed to bring students insight into cognitive features of their reasoning, improved aspects of diagnostic competence.                                                                                                                                                                                                      |
|                       | claim            |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
| INTERVENTION_EFFECT   | claim            | TRUE     | Encouraging trainees to adopt pattern recognition strategies may help expedite the acquisition of visual interpretation skills in cytopathology training programs.                             | Nonanalytic reasoning in cytopathology image interpretation can be as accurate as traditional feature-based reasoning. Encouraging trainees to adopt pattern recognition strategies may help to expedite the acquisition of visual interpretation skills in cytopathology training programs, yet combining analytic and non-analytic reasoning do not appear to be effective. [PAGE 1]) |
|                       |                  |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
|                       |                  |          |                                                                                                                                                                                                | 2. (NONANALYTIC GROUP                                                                                                                                                                                                                                                                                                                                                                   |
|                       | claim            |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
| MECHANISM_EXPLANATION | claim            | TRUE     | Experts use nonanalytic reasoning strategies, which are efficient in using short-term memory resources, supported by research in radiology, cognitive psychology, and medical decision-making. | Experts tend to use strategies variably referred to in the literature as “backward reasoning,” “similarity-driven reasoning,” or “nonanalytic reasoning,” in which one or only a small number of tentative diagnoses are made from a rapid initial and largely nonanalytic global impression of the visual scene. [PAGE 3])                                                             |
|                       |                  |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
|                       |                  |          |                                                                                                                                                                                                | 2. (TRAINING STRATEGIES                                                                                                                                                                                                                                                                                                                                                                 |
| CONTEXT_MODERATOR     | claim            | TRUE     | The study was conducted with approval from Cardiff Metropolitan University School of Health Sciences Ethics Committee, indicating a formal research setting.                                   | The study received approval from Cardiff Metropolitan University School of Health Sciences Ethics Committee and Public Health Wales Research and Development Group.)                                                                                                                                                                                                                    |
|                       |                  |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
|                       |                  |          |                                                                                                                                                                                                | 2. (UNDERGRADUATE PSYCHOLOGY STUDENTS                                                                                                                                                                                                                                                                                                                                                   |
|                       | claim            |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
| INTERVENTION_EFFECT   | claim            | TRUE     | Participants who received analytic training were taught to identify morphological features of cells, which aimed to enhance their diagnostic skills.                                           | Participants were taught the morphological features of normal and abnormal cells by an experienced cytology trainer and shown 20 pairs of images on a computer screen. [PAGE 5])                                                                                                                                                                                                        |
|                       |                  |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
|                       |                  |          |                                                                                                                                                                                                | 2. (ANALYTIC TRAINING                                                                                                                                                                                                                                                                                                                                                                   |
| INTERVENTION_EFFECT   | claim            | TRUE     | Analytic training led to a significant reduction in miss error rates from 36.8% to 16.7% between tests 1 and 2.                                                                                | Before any training was provided (test 1), miss error rates were 36.8% and 42.3% for the analytic and nonanalytic conditions, respectively. Under both conditions, miss errors declined dramatically to 16.7% and 22.7%, respectively, following the respective training protocols (test 2).)                                                                                           |
|                       |                  |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
|                       |                  |          |                                                                                                                                                                                                | 2. (NONANALYTIC TRAINING                                                                                                                                                                                                                                                                                                                                                                |
|                       | claim            |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
| INTERVENTION_EFFECT   | claim            | TRUE     | Participants with no previous experience in cytopathology showed significant improvement in diagnostic performance after brief exposure to paired images of normal and abnormal cells.         | By recruiting participants with no previous experience in cytopathology and examining their diagnostic performance under controlled laboratory conditions, we were able to demonstrate a significant element of nonanalytic reasoning from the earliest learning stages.)                                                                                                               |
|                       |                  |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
|                       |                  |          |                                                                                                                                                                                                | 2. (NONANALYTIC REASONING                                                                                                                                                                                                                                                                                                                                                               |
| INTERVENTION_EFFECT   | claim            | TRUE     | An intensive 4-week introductory course followed by supervised screening is part of the training for cytopathology trainees, aiming to improve diagnostic accuracy.                            | attend an intensive 4-week introductory course followed by 2 years of closely supervised screening of a minimum of 5000 cytology slides. [PAGE 8])                                                                                                                                                                                                                                      |
|                       |                  |          |                                                                                                                                                                                                |                                                                                                                                                                                                                                                                                                                                                                                         |
|                       |                  |          |                                                                                                                                                                                                | 2. (PATTERN RECOGNITION TRAINING                                                                                                                                                                                                                                                                                                                                                        |

### Community structure

- communities rows: **165**

### Community report quality (principle-level heuristics)

- community_reports rows: **165**
- generic/too-short titles (heuristic): **0 / 165**

**Community report headers (sample)**

|   community |   level | title                                                                      |   rank |   size |
|------------:|--------:|:---------------------------------------------------------------------------|-------:|-------:|
|         160 |       3 | Diagnostic Performance and Self-Explanation in Medical Education           |    8.5 |     41 |
|         161 |       3 | Clinical Education Community: Topic Familiarity and Learning Opportunities |    7.5 |      2 |
|         162 |       3 | Post Hoc Analyses and Bonferroni Corrections                               |    7.5 |      2 |
|         163 |       3 | Diagnostic Accuracy and Educational Interventions                          |    7.5 |    119 |
|         164 |       3 | Non-Contrastive Learning and Diagnostic Accuracy                           |    4.5 |      2 |
|         147 |       2 | Diagnostic Knowledge Enhancement through Erroneous Examples                |    8.5 |     25 |
|         148 |       2 | Sustainability Analyses and Experimental Groups                            |    7.5 |      2 |
|         149 |       2 | Diagnostic Performance and Self-Explanation in Medical Education           |    8.5 |     45 |
|         150 |       2 | Control Group in Diagnostic Performance Study                              |    7.5 |      4 |
|         151 |       2 | Familiar and Less Familiar Problems in PBL                                 |    7.5 |      2 |
|         152 |       2 | Self-Explanation in Medical Education                                      |    8.5 |     27 |
|         153 |       2 | Cognitive Processes in Clinical Case Analysis                              |    8.5 |      6 |
|         154 |       2 | Coherent Mental Representation and Knowledge Integration                   |    7.5 |      2 |
|         155 |       2 | Diagnostic Accuracy and Learning Strategies                                |    7.5 |    121 |
|         156 |       2 | Combined Approach to Clinical Reasoning                                    |    8.5 |      2 |

### What to verify against Richmond (next)

- **Search/screening alignment**: overlap with Richmond-28 + explain mismatches.
- **CMO fidelity**: do extracted claims support C→M→O patterns?
- **Concept alignment**: map community titles ↔ Richmond mechanisms/programme theory components.
- **Cross-study synthesis**: identify dominant patterns + contradictions with citations/spans.
