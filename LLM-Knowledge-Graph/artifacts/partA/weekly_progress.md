## Báo cáo tiến độ tuần này — Part A (Education verification / Richmond-28)

### Mục tiêu tuần này (đúng theo ưu tiên của thầy)
- **Hoàn thành Education verification trước** (Richmond-28) để kiểm định pipeline GraphRAG end-to-end.
- **Tạo gói output “auditable/traceable”**: có thể lần ngược claim → evidence snippet → text_unit → paper metadata để đối chiếu với Richmond (CMO/programme theory).
- **Chứng minh quy trình iterative + human feedback seed** (ít nhất 1 vòng “review → chỉnh → xuất lại artifacts”).

---

### Việc đã hoàn thành
#### 1) Chạy GraphRAG indexing cho Richmond-28 và xuất đầy đủ artifacts
- Output GraphRAG (run hiện tại): `graphrag-project/output_partA_v2/`
- Artifacts có mặt: `documents.parquet`, `text_units.parquet`, `entities.parquet`, `relationships.parquet`, `communities.parquet`, `community_reports.parquet`, `covariates.parquet`, `stats.json`
- Share page (đưa thầy xem nhanh, theo đúng thứ tự đọc): `artifacts/partA/share/index.md`

#### 2) Khắc phục nút thắt lớn nhất: claims/covariates để verification làm được
- Vấn đề: `covariates.parquet` bị lỗi parse → **đa số thông tin claim/evidence bị nhồi vào `subject_id`**, các cột `type/status/description/source_text/object_id` gần như rỗng.
- Giải pháp (tuần này): thêm bước **repair** sau run để tách lại claims thành bảng chuẩn:
  - Script: `scripts/partA_repair_claims_parquet.py`
  - Output: `graphrag-project/output_partA_v2/claims_fixed.parquet`
  - Bản dễ đọc: `graphrag-project/output_partA_v2/human_readable/claims_fixed.md`

#### 3) Xuất gói “verification-ready” theo Richmond style
- Audit (quality gates + coverage + traceability): `artifacts/partA/verification_audit.md`
- Claims đã join paper metadata (DOI/title/year + evidence): `artifacts/partA/claims_enriched.md`
- Draft CMO configurations theo từng paper: `artifacts/partA/cmo_configurations.md`
- Snapshot tổng quan run/corpus + stats.json: `artifacts/partA/verification_summary.md`

---

### Kết quả nhanh (high-signal)
- Entities: **2602**; Communities: **57**; Community reports: **57**
- Claims sau repair: **1592**
- Claims có `[PAGE N]` marker trong evidence: **972 / 1592**
- Điểm còn yếu: **534 / 1592 claims thiếu evidence span trong `source_text`** (cần vòng iteration/prompt stricter để bắt buộc evidence snippet).

---

### Những điểm cần làm tiếp (Iteration 1 / feedback seed — tuần sau hoặc phần còn lại của tuần nếu kịp)
- **Tăng “evidence completeness” của claims**:
  - ép prompt để luôn có `Claim Source Text` 1–2 câu + giữ `[PAGE N]`
  - loại claim không có evidence (quality gate)
- **Giảm noise trong entities/relationships**:
  - giảm dominance của `ASSESSMENT_MEASURE` (đưa đo lường về vai trò “supporting”, không phải “central concepts”)
  - chuẩn hoá/merge đồng nghĩa (canonicalization)
  - thêm constraint relation theo CMO (C→M, I→M, I→O, C→O, comparator→O)
- **Tối ưu chunking** (hiện `chunks.size=2200`): cân nhắc giảm để evidence span chính xác hơn.
- **Bắt đầu mapping Richmond** (deliverable verification):
  - chọn một số “key mechanisms/CMOs” trong Richmond để map sang communities + claims (có evidence)
  - ghi rõ gap do thiếu full-text vs do ontology/prompt.

---

### “Bước nộp báo cáo tuần này” (đưa thầy xem cái gì)
Mở theo đúng thứ tự:
1) `artifacts/partA/share/index.md`
2) `artifacts/partA/verification_audit.md`
3) `artifacts/partA/claims_enriched.md`
4) `artifacts/partA/cmo_configurations.md`
5) `graphrag-project/output_partA_v2/human_readable/community_reports.md`

