## Part A — Iteration playbook (avoid overfitting, iterate fast)

Mục tiêu: cải thiện `entities.parquet` + `relationships.parquet` theo feedback (seed) của human expert, nhưng tránh “siết quá chặt” và tránh tốn 1 ngày mỗi lần chạy.

### Nguyên tắc (để không overfit)
- **Ưu tiên “soft constraints”** trong prompt (khuyến nghị/ưu tiên) thay vì hard rules loại bỏ quá nhiều.
- **Rerun subset 3–5 papers trước** để đo xu hướng (noise giảm? CMO-edge tăng?) rồi mới rerun 28.
- Seed v1 chỉ nên sửa các lỗi rõ ràng:
  - corrupted output tokens
  - category-label entities
  - measurement-skew quá nặng
  - generic placeholders

### Bước 1: Build input subset nhanh
Ví dụ: chỉ lấy 5 PDF papers đầu tiên để test prompt/config:

```bash
powershell -ExecutionPolicy Bypass -File LLM-Knowledge-Graph/scripts/partA_run_graphrag.ps1 -SkipIndex
```

Hoặc build input riêng (khuyến nghị):

```bash
python LLM-Knowledge-Graph/scripts/partA_prepare_graphrag_input.py --only-pdf --limit 5 --out-input-dir LLM-Knowledge-Graph/graphrag-project/input_partA_subset5
```

Sau đó chạy index với `-InputDir` trỏ vào subset (trong script):
- `-InputDir graphrag-project/input_partA_subset5`
- `-OutDir graphrag-project/output_partA_subset5`

### Bước 2: Run + check quality gates
Sau khi chạy xong, mở:
- `graphrag-project/<out>/human_readable/quality_gates.md`
- `artifacts/partA/verification_audit.md`

Nếu vẫn có:
- blank entity types > 0
- corrupted titles > 0
→ cần fix prompt/format trước khi làm seed “nặng”.

### Bước 3: Seed v1 (human feedback)
Xem file seed:
- `artifacts/partA/feedback_seed_v1.md`

Mục tiêu ngắn hạn:
- giảm noise rõ ràng
- tăng tỷ lệ CMO-ish edges (không cần 100%)

