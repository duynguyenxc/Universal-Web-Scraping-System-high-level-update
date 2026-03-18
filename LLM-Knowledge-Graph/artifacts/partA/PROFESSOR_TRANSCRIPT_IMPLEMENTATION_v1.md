## Professor transcript → Implementation (entities/relationships verification loop) v1

Mục tiêu của tài liệu này là “đóng gói” đúng cái mà giáo sư Wei Zheng đã hướng dẫn trong transcript thành **một quy trình chạy được trong repo**, để bạn:
- biết **mình đã làm gì** để cải thiện `entities` và `relationships`,
- biết **tiêu chuẩn nào là “chuẩn”** (để verification không mù mờ),
- và có một **iteration loop** đúng kiểu “run → check → rerun → check”, có **human input ở điểm critical**.

---

## 1) Giáo sư đã hướng dẫn gì (trích ý, đúng trọng tâm entities/relationships)

Trong transcript, giáo sư nói rõ 4 ý liên quan trực tiếp đến “entities/relationships chuẩn”:

- **(A) One-by-one prompts / chain of prompts (nghiêm túc, step-by-step)**  
  Một agent = một prompt (có thể dùng cùng một LLM), chạy theo workflow, output agent trước là input agent sau.

- **(B) Gold standard để so sánh (Richmond là “human gold”)**  
  “Whatever they do is the golden standard” → muốn biết entities/relations ổn hay chưa thì phải có target/gold để đối chiếu.

- **(C) Cách lấy target/gold cho entities/relations (cực cụ thể)**  
  Feed paper Richmond vào ChatGPT rồi hỏi:
  - “Based on outcome/conclusion + figures, what kind of knowledge graph should have?”  
  - “Give examples of possible entities and relations”  
  Sau đó **compare** với entities/relations mình extract từ 28 papers.

- **(D) Evaluation metrics để đo “close”**  
  Cần định nghĩa metrics cho từng thứ mình so sánh (selection overlap, entity coverage, relationship quality/directionality, …).

---

## 2) Mình đã “thực hiện” các ý đó trong repo như thế nào (file-level evidence)

### 2.1. (A) One-by-one prompts → đã viết prompt contract + prompt extraction

- **Prompt contract theo agent (spec)**  
  `LLM-Knowledge-Graph/artifacts/partA/ONE_BY_ONE_PROMPTS_SPEC_v1.md`

- **Prompt cho entities/relationships (GraphRAG extractor)**  
  `LLM-Knowledge-Graph/graphrag-project/prompts_partA_v4/extract_graph.txt`
  - Bắt buộc **construct-level entities** (anti-noise)
  - **Typing mandatory**: không chắc type thì *không tạo entity*
  - **Relationships chỉ CMOC-family + directionality** (OUTCOME là sink, không cho OUTCOME làm source)
  - **Evidence-local** + predicate ngắn (cue verb) để tránh “relationship văn kể chuyện”

- **Prompt cho claims (evidence + CMO tags)**  
  `LLM-Knowledge-Graph/graphrag-project/prompts_partA_v4/extract_claims.txt`
  - Bắt buộc evidence snippet (ưu tiên có `[PAGE N]`)
  - Bắt buộc `CMO[C=...; I=...; M=...; O=...]` để audit/verification
  - Anti-noise cho subject/object (không “THE STUDY”, “RESULTS”, …)

### 2.2. (B)(C) Gold standard entities/relations từ Richmond → đã tạo “gold spec” + tự động so sánh

- **Gold spec (Richmond-native entities + relationship templates)**  
  `LLM-Knowledge-Graph/artifacts/partA/RICHMOND_GOLD_ENTITIES_RELATIONS_v1.md`  
  Đây chính là “target” theo Figures 1–3 (5 contexts backbone + Mresource + Mreaction + outcomes, và CMOC edge templates).

- **Script auto-compare với gold spec**  
  `LLM-Knowledge-Graph/scripts/partA_gold_alignment.py`  
  Output report: `LLM-Knowledge-Graph/artifacts/partA/gold_alignment_<run>.md`

### 2.3. (D) Metrics / gates để biết entities/relations “chuẩn” → đã triển khai quality gates + scorecard

- **Quality gates (run health, fail-fast)**  
  `LLM-Knowledge-Graph/scripts/partA_quality_gates.py`  
  Nó đo:
  - blank type count (target = 0)
  - corrupt titles (target = 0)
  - % CMOC-family edges (raw & normalized)
  - % OUTCOME-as-source (target thấp; realist-graph coi outcome là sink)

- **Scorecard (tổng hợp 1 trang để iteration)**  
  `LLM-Knowledge-Graph/scripts/partA_scorecard_md.py`  
  Output: `LLM-Knowledge-Graph/artifacts/partA/scorecard_<run>.md`

---

## 3) Cải thiện entities/relationships bằng cái gì (cơ chế kỹ thuật chính)

### 3.1 Entities: chuẩn hóa type + loại noise + xử lý sai lệch ontology

Script chính: `LLM-Knowledge-Graph/scripts/partA_postprocess_kg.py`

Những can thiệp trực tiếp vào “entities quality”:
- **Normalize type enums + synonyms** (vd `COGNITIVE STATE` → `COGNITIVE_STATE`)
- **Detect/drop corrupt titles** do LLM/GraphRAG artifacts (vd `<|DIFF_MARKER|>`, `(\"ENTITY\"...`)
- **Heuristic type inference cho blank/invalid types** (nhưng có kiểm soát, có report)
- **Fix drift**: “reasoning strategy” bị gán thành `INTERVENTION` → remap thành `MECHANISM` (trừ khi là activity như training/workshop)
- **Drop unknown-typed entities khỏi normalized KG** để normalized output đạt “verification-grade” (blank type = 0)

### 3.2 Relationships: ép CMOC-family + sửa direction + loại OUTCOME-as-source

Vẫn trong `partA_postprocess_kg.py`:
- **Map type → family** để check CMOC robust (vd `LEARNER_CONTEXT` coi là `CONTEXT` family; `COGNITIVE_STATE` coi là `MECHANISM` family)
- **Flip edges** nếu chiều hiện tại không CMOC nhưng đảo chiều thì CMOC (đánh dấu `[FLIPPED_FOR_CMOC]`)
- **Flag non-CMOC** (`[NON_CMOC]`) để audit, tránh “xóa bừa”
- **Drop OUTCOME-as-source edges** trong normalized output (realist simplification: outcomes là sinks)
- **Drop edges dính `ASSESSMENT_MEASURE`** để giảm measurement/logistics noise

---

## 4) Chạy “Professor loop” trên 1 run (commands)

Ví dụ run Richmond hiện tại:

1) Postprocess KG → tạo normalized parquet + report

```powershell
python LLM-Knowledge-Graph/scripts/partA_postprocess_kg.py --out-dir LLM-Knowledge-Graph/graphrag-project/output_partA_richmond28_v4_run2 --label richmond28_v4_run2
```

2) Quality gates (đo chuẩn entities/relationships)

```powershell
python LLM-Knowledge-Graph/scripts/partA_quality_gates.py --out-dir LLM-Knowledge-Graph/graphrag-project/output_partA_richmond28_v4_run2
```

3) Gold alignment (so sánh với target Richmond)

```powershell
python LLM-Knowledge-Graph/scripts/partA_gold_alignment.py --out-dir LLM-Knowledge-Graph/graphrag-project/output_partA_richmond28_v4_run2
```

4) Scorecard (tổng hợp)

```powershell
python LLM-Knowledge-Graph/scripts/partA_scorecard_md.py --out-dir LLM-Knowledge-Graph/graphrag-project/output_partA_richmond28_v4_run2
```

5) (Theo đúng lời giáo sư) Tạo “prompt pack” để feed vào ChatGPT và yêu cầu nó judge entities/relations so với Richmond outcome/figures.
Script: `LLM-Knowledge-Graph/scripts/partA_professor_prompt_pack.py` (được thêm kèm theo tài liệu này).

---

## 5) Khi nào bạn có thể nói “entities/relationships đã chuẩn để verification”

Một run được coi là “verification-ready” (tối thiểu) khi:
- **Quality gates pass**:
  - blank type = 0
  - corrupt titles = 0
  - CMOC-family edges (normalized) cao (không cần 100%, nhưng phải “chiếm đa số”)
  - OUTCOME-as-source ≈ 0
- **Gold alignment coverage** đạt mức tốt ở các backbone items:
  - 5 contexts backbone phải “hit” (hoặc tương đương paraphrase)
  - resources/reactions không cần 100% ngay nhưng phải có coverage rõ ràng, để iterate được
- **Claims** có evidence traceability (>= 90% có `[PAGE N]`) để bạn audit được đúng/sai

