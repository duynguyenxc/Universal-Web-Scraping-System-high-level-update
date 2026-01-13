## Part A — Feedback seed v1 (entities/relationships)

Mục tiêu: giảm noise + tăng khả năng “CMO-style reasoning” theo Richmond, nhưng **không siết quá chặt** để tránh overfitting vào 28 papers.

### 1) Entities — drop / avoid (noise patterns)
- **Category-label entities** (không phải khái niệm): `MECHANISM`, `INTERVENTION`, `ASSESSMENT MEASURE`, `SETTING`, `TASK CASE`
- **Generic placeholders**: `THE RESULTS`, `RESULTS`, `THE STUDY`, `STUDY`, `LEARNING`, `INTERVENTION` (khi đứng một mình)
- **Bibliographic/platform noise**: publishers/journals (Wiley/Elsevier/“Medical Education”…), DOI fragments, years
- **Corrupted titles**: bất kỳ entity title chứa `<|DIFF_MARKER|>` hoặc `("ENTITY"` hoặc chỉ là `("ENTITY")`

### 2) Entities — prefer / keep (Richmond backbone)
Richmond nhấn mạnh “student contexts” và mechanisms, nên ưu tiên các nhóm entity sau:
- **Learner contexts**: prior knowledge / low knowledge / high domain knowledge; self-confidence; self-efficacy; coping strategies; anxiety; uncertainty tolerance
- **Cognitive states**: cognitive load; time pressure; fatigue (nếu có)
- **Mechanisms**: pattern recognition; illness script activation/formation; reflection; self-explanation (nếu như cognitive process); bias mitigation; knowledge organization; cognitive flexibility
- **Outcomes**: diagnostic accuracy; diagnostic performance; error rate; confidence rating; response time; knowledge retention
- **Interventions**: schema-based instruction; worked examples; simulation; case-based learning; test-enhanced learning; explicit reasoning instruction; feedback interventions

### 3) Common retag suggestions (soft, not strict)
- **ANALYTIC REASONING / NONANALYTIC REASONING**: default → **MECHANISM** (trừ khi paper mô tả như một “training intervention”)
- **FACE VALIDITY / CONTENT VALIDITY / CONSTRUCT VALIDITY**: không phải MECHANISM; thường là **ASSESSMENT_MEASURE** hoặc bỏ nếu không phục vụ CMO
- **INFORMATION (background/new/misleading)**: tránh làm entity độc lập; chỉ giữ nếu thật sự là context moderator (“misleading information” trong task)

### 4) Relationship constraints (CMO-oriented, soft)
Ưu tiên các patterns:
- **CONTEXT → MECHANISM**
- **CONTEXT → OUTCOME**
- **INTERVENTION → MECHANISM**
- **INTERVENTION → OUTCOME**
- **COMPARATOR → OUTCOME**

Hạn chế (không cấm tuyệt đối):
- **OUTCOME ↔ ASSESSMENT_MEASURE**: chỉ giữ 1–2 relations “đủ dùng để audit” (immediate test / delayed test / OSCE…) thay vì nở thành graph đo lường.
- **STUDY_DESIGN ↔ (mọi thứ)**: chỉ giữ khi thật sự giải thích outcome khác biệt (ví dụ RCT vs qualitative làm thay đổi interpretation).

### 5) Minimal examples (để prompt học “đúng kiểu”, không overfit)
- **Good (context moderator)**: `LOW KNOWLEDGE → COGNITIVE LOAD` (low knowledge làm tăng load) → ảnh hưởng `DIAGNOSTIC ACCURACY`
- **Good (intervention effect)**: `SCHEMA-BASED INSTRUCTION → DIAGNOSTIC SUCCESS` (outcome) và/hoặc qua `DIAGNOSTIC REASONING STRATEGIES` (mechanism)
- **Good (confidence/self-efficacy)**: `LOW SELF-EFFICACY → STRESS/ANXIETY` (mechanism-ish) → `POOR PERFORMANCE`
- **Bad (generic)**: `THE RESULTS → OUTCOME`, `STUDY → LEARNING`

