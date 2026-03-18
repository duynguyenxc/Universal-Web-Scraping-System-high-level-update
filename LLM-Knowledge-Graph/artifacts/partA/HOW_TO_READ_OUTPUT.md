# Hướng dẫn đọc Output của GraphRAG (Part A - Education Verification)

## Tổng quan: Output gồm những gì?

Sau khi chạy `partA_run_graphrag_v4.ps1`, bạn sẽ có 2 loại file:

### 1. **File gốc (Parquet)** - Dữ liệu "máy đọc"
- `entities.parquet`: Danh sách entities (khái niệm/đối tượng) được trích xuất
- `relationships.parquet`: Các mối quan hệ giữa entities
- `communities.parquet`: Các nhóm entities được gom lại (community detection)
- `community_reports.parquet`: Báo cáo tự động về mỗi community (đây là "tính năng nổi bật" của GraphRAG)
- `covariates.parquet` / `claims_fixed.parquet`: Các claims/evidence có thể trace về source text

### 2. **File human-readable (Markdown)** - Dữ liệu "người đọc" (bạn mở trong IDE)
- `human_readable/entities.md`: Bảng entities dễ đọc
- `human_readable/relationships.md`: Bảng relationships dễ đọc
- `human_readable/community_reports.md`: **ĐÂY LÀ FILE QUAN TRỌNG NHẤT** - báo cáo tự động về các "concept/principle" (GraphRAG community reports)
- `human_readable/claims_fixed.md`: Claims với evidence snippets

---

## Cách đọc từng loại output

### A. Entities (`entities.md` hoặc `entities.parquet`)

**Entities là gì?** = Các khái niệm/đối tượng được trích xuất từ papers (ví dụ: "DIAGNOSTIC ACCURACY", "CONTRASTIVE LEARNING", "NAÏVE STUDENTS").

**Cột quan trọng:**
- `title`: Tên entity (viết hoa, ngắn gọn)
- `type`: Loại entity (INTERVENTION, MECHANISM, OUTCOME, LEARNER_POPULATION, ...)
- `description`: Mô tả chi tiết (1-3 câu)
- `frequency`: Số lần entity xuất hiện trong text
- `degree`: Số relationships liên kết với entity này (entity có degree cao = "hub" trong graph)

**Ví dụ đọc:**
```
| title                    | type               | frequency | degree |
|:-------------------------|:-------------------|----------:|-------:|
| DIAGNOSTIC ACCURACY      | OUTCOME            |         9 |     61 |
| CONTRASTIVE LEARNING     | INTERVENTION       |         3 |     10 |
```

→ **Ý nghĩa**: "DIAGNOSTIC ACCURACY" xuất hiện 9 lần và có 61 mối quan hệ → đây là một outcome quan trọng, được nhiều intervention/mechanism nhắm tới.

**Cách kiểm tra chất lượng:**
- ✅ **Tốt**: Entities có `type` rõ ràng, `description` cụ thể, không phải bibliographic noise (tên tác giả, journal, DOI...)
- ❌ **Xấu**: Entities có `type` trống, hoặc tên quá generic ("STUDENTS", "EDUCATION", "INTERVENTION" - không có context)

---

### B. Relationships (`relationships.md` hoặc `relationships.parquet`)

**Relationships là gì?** = Các mối quan hệ giữa 2 entities (ví dụ: "CONTRASTIVE LEARNING → DIAGNOSTIC ACCURACY").

**Cột quan trọng:**
- `source`: Entity nguồn (thường là INTERVENTION hoặc CONTEXT)
- `target`: Entity đích (thường là MECHANISM hoặc OUTCOME)
- `description`: Mô tả quan hệ (1-2 câu)
- `weight`: Độ mạnh của quan hệ (1-10, hoặc có thể >10 nếu được aggregate từ nhiều text units)

**Ví dụ đọc:**
```
| source                  | target              | description                                    | weight |
|:------------------------|:--------------------|:-----------------------------------------------|-------:|
| CONTRASTIVE LEARNING    | DIAGNOSTIC ACCURACY | Contrastive learning improves diagnostic...    |    476 |
| COMBINED REASONING      | DIAGNOSTIC ACCURACY | Combined reasoning leads to higher accuracy... |    416 |
```

→ **Ý nghĩa**: "CONTRASTIVE LEARNING" có weight 476 → đây là một quan hệ được nhắc đến nhiều lần trong papers, có bằng chứng mạnh.

**Pattern quan trọng (CMO - Context-Mechanism-Outcome):**
- ✅ **Tốt**: `INTERVENTION → MECHANISM → OUTCOME` (chiều đúng, causal)
- ✅ **Tốt**: `CONTEXT → MECHANISM` (context kích hoạt mechanism)
- ⚠️ **Cần kiểm tra**: `OUTCOME → MECHANISM` (chiều ngược, chỉ đúng nếu paper nói rõ outcome gây ra mechanism)

**Cách kiểm tra chất lượng:**
- Xem `quality_gates.md`: % CMO-ish edges (mục tiêu >= 15-20%)
- Kiểm tra xem có quá nhiều edge chiều ngược không (OUTCOME → MECHANISM)

---

### C. Communities (`communities.parquet` + `community_reports.md`)

**Communities là gì?** = Các nhóm entities được gom lại bằng thuật toán community detection (Leiden). Mỗi community đại diện cho một "concept/principle" ở mức cao hơn.

**File `communities.parquet`** (metadata):
- `community`: ID của community (0, 1, 2, ...)
- `size`: Số entities trong community
- `title`: Tên community (tự động generate)

**File `community_reports.md`** (QUAN TRỌNG NHẤT - đây là "tính năng nổi bật"):
- Mỗi community có một báo cáo tự động gồm:
  - **Title**: Tên concept/principle (ví dụ: "Diagnostic Learning Strategies Community")
  - **Summary**: Tóm tắt ngắn về community này
  - **Findings**: Các phát hiện chính (dạng bullet points, có citations)
  - **Full content**: Báo cáo chi tiết với evidence paths

**Ví dụ đọc `community_reports.md`:**
```markdown
## Community 0 — Diagnostic Learning Strategies Community

- meta:
  - community: 0
  - size: 45
  - rank: 8.0

# Diagnostic Learning Strategies Community

The community focuses on various educational strategies aimed at enhancing 
diagnostic accuracy in medical education...

## Contrastive Learning significantly enhances Diagnostic Accuracy

Contrastive Learning is a pedagogical strategy that has been shown to improve 
diagnostic accuracy by encouraging learners to compare different diagnostic 
categories. Research indicates that participants who engage in contrastive 
learning demonstrate significantly better diagnostic performance...
[Data: Relationships (3, 6, 16, 17, 59)]
```

→ **Ý nghĩa**: Community 0 gom 45 entities liên quan đến "strategies để học diagnostic skills". Báo cáo tự động tóm tắt: "Contrastive Learning → Diagnostic Accuracy" là một finding chính, với evidence từ relationships #3, #6, #16, #17, #59.

**Cách sử dụng:**
- Đọc `community_reports.md` để hiểu "big picture" - các concept/principle chính
- So sánh với Richmond et al. (2020) để xem có overlap không
- Dùng `[Data: Relationships (...)]` để trace về `relationships.parquet` nếu cần verify

---

### D. Claims (`claims_fixed.md` hoặc `claims_fixed.parquet`)

**Claims là gì?** = Các mệnh đề evidence-grounded, có thể trace về source text trong paper gốc.

**Cột quan trọng:**
- `subject_id`: Entity chủ thể (ví dụ: "CONTRASTIVE LEARNING")
- `object_id`: Entity đối tượng (ví dụ: "DIAGNOSTIC ACCURACY")
- `type`: Loại claim (INTERVENTION_EFFECT, MECHANISM_EXPLANATION, CONTEXT_MODERATOR, OUTCOME_MEASUREMENT)
- `status`: TRUE / FALSE / SUSPECTED
- `description`: Mô tả claim (có thể có CMO field ở cuối)
- `source_text`: **QUAN TRỌNG** - đoạn text gốc trong paper (có `[PAGE N]` marker)

**Ví dụ đọc:**
```
| subject_id              | object_id           | type                  | source_text                                    |
|:------------------------|:--------------------|:----------------------|:-----------------------------------------------|
| CONTRASTIVE LEARNING    | DIAGNOSTIC ACCURACY | INTERVENTION_EFFECT   | "Greater diagnostic accuracy was achieved..." [PAGE 1] |
```

→ **Ý nghĩa**: Claim này nói "CONTRASTIVE LEARNING → DIAGNOSTIC ACCURACY" là TRUE, với evidence từ page 1 của paper.

**Cách kiểm tra chất lượng:**
- ✅ **Tốt**: Claims có `source_text` với `[PAGE N]` marker, `description` rõ ràng
- ❌ **Xấu**: Claims thiếu `source_text`, hoặc `subject_id`/`object_id` là generic ("THE RESULTS", "THE STUDY")

**Cách sử dụng:**
- Dùng claims để verify CMO configurations
- Trace về paper gốc bằng `source_text` + `[PAGE N]`
- So sánh với Richmond's CMO statements

---

## Workflow đọc output (recommended, v4)

### Bước 1: Đọc `quality_gates.md` (nhanh, 30 giây)
- Xem blank types, corrupt titles, CMO-edge %
- Nếu fail gates → cần fix prompt và rerun

### Bước 2: Đọc `human_readable/community_reports.md` (5-10 phút)
- Đây là file quan trọng nhất
- Đọc từng community report để hiểu "big picture"
- Ghi chú các findings chính và so sánh với Richmond

### Bước 3: Spot-check `entities.md` và `relationships.md` (5 phút)
- Xem top entities (frequency/degree cao)
- Xem top relationships (weight cao)
- Kiểm tra xem có noise không (bibliographic, generic entities)

### Bước 4: Deep-dive `claims_fixed.md` (nếu cần verify)
- Tìm claims liên quan đến một CMO cụ thể
- Trace về source text để verify
- So sánh với Richmond's statements

---

## Ví dụ cụ thể: Đọc output của subset5

### 1. Quality gates
```
- blank type count: 8 (threshold <= 0)  ← FAIL
- CMO-ish edges: 38 / 182 = 20.88% (threshold >= 15.0%)  ← PASS
```
→ **Kết luận**: Cần fix blank types, nhưng CMO structure đã tốt hơn baseline.

### 2. Community reports
Đọc `community_reports.md`, thấy:
- Community 0: "Diagnostic Learning Strategies Community" (size=45, rank=8.0)
  - Finding: "Contrastive Learning significantly enhances Diagnostic Accuracy"
  - Finding: "Combined Reasoning Approach improves diagnostic performance"
→ **Kết luận**: GraphRAG đã phát hiện được các concept chính mà Richmond cũng nhắc đến.

### 3. Entities spot-check
Đọc `entities.md`, thấy:
- Top entity: "DIAGNOSTIC ACCURACY" (frequency=9, degree=61)
- Có entities như "CONTRASTIVE LEARNING", "COMBINED REASONING STRATEGY"
→ **Kết luận**: Entities có vẻ relevant, không thấy bibliographic noise.

### 4. Relationships spot-check
Đọc `relationships.md`, thấy:
- Top edge: "CONTRASTIVE LEARNING → DIAGNOSTIC ACCURACY" (weight=476)
- Có nhiều edge kiểu INTERVENTION → OUTCOME
→ **Kết luận**: Relationships có chiều đúng (causal), nhưng cần kiểm tra xem có quá nhiều OUTCOME → MECHANISM không.

---

## FAQ

**Q: Tại sao `community_reports.parquet` nhìn "không nổi bật"?**
A: Vì parquet là bảng dữ liệu, phần "hay" nằm trong cột `full_content`/`summary` (text dài). UI thường truncate. Đọc `community_reports.md` thay vì parquet.

**Q: Làm sao biết output "tốt" hay "xấu"?**
A: Xem `quality_gates.md`:
- Blank types = 0 → tốt
- CMO-edge % >= 15-20% → tốt
- Corrupt titles = 0 → tốt
- Claims có `[PAGE N]` marker >= 90% → tốt

**Q: Làm sao so sánh với Richmond?**
A: 
1. Đọc Richmond's programme theory (5 contexts + mechanisms + outcomes)
2. Đọc `community_reports.md` để xem có overlap không
3. Dùng `claims_fixed.md` để verify từng CMO statement cụ thể

**Q: File nào quan trọng nhất?**
A: **`community_reports.md`** - đây là "tính năng nổi bật" của GraphRAG, tự động tóm tắt các concept/principle từ graph.

---

## Next steps sau khi đọc output

1. **Nếu quality gates fail**: Fix prompt → rerun subset → check lại
2. **Nếu quality gates pass**: Rerun full 28 papers → so sánh với Richmond
3. **Nếu cần verify cụ thể**: Dùng `claims_fixed.md` để trace về source text
