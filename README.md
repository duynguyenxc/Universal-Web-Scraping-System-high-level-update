# UWSS – Universal Web Scraping System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-black.svg)](https://github.com/duynguyenxc/Universal-Web-Scraping-System-high-level-update)

> **UWSS** là hệ thống thu thập dữ liệu học thuật thông minh, có thể kết nối với nhiều nguồn tài liệu khoa học khác nhau chỉ bằng cách thay đổi cấu hình.

## 🚀 Vấn đề UWSS giải quyết

Bạn đang nghiên cứu về một chủ đề khoa học và cần thu thập:
- ✅ Bài báo từ arXiv, PubMed
- ✅ Tài liệu từ Crossref, Semantic Scholar
- ✅ Dữ liệu từ OpenAlex và các nguồn khác

**UWSS giúp bạn:**
- Tự động thu thập metadata (tiêu đề, tóm tắt, tác giả, DOI)
- Tải xuống PDF của các bài báo
- Lọc dữ liệu theo từ khóa liên quan
- Xuất dữ liệu ra nhiều định dạng (JSON, CSV)
- Quản lý và phân tích chất lượng dữ liệu

## ✨ Tính năng chính

### 🔍 Thu thập thông minh
- **Kết nối nhiều nguồn**: arXiv, PubMed, Crossref, Semantic Scholar, OpenAlex
- **API chính thức**: Sử dụng API chính thức của từng nguồn, tuân thủ quy định
- **Tự động phân loại**: Lọc bài báo liên quan dựa trên từ khóa

### 📊 Quản lý dữ liệu
- **Database chuyên nghiệp**: SQLite (local) hoặc PostgreSQL (production)
- **Metadata đầy đủ**: Tiêu đề, tóm tắt, tác giả, DOI, năm xuất bản
- **PDF tự động**: Tải xuống và lưu trữ PDF

### 🛠️ Dễ sử dụng
- **Cấu hình đơn giản**: Chỉ cần chỉnh file config.yaml
- **Lệnh command line**: Giao diện dòng lệnh trực quan
- **Scripts hỗ trợ**: Công cụ phân tích và kiểm tra dữ liệu

## 🏗️ Cách UWSS hoạt động

### Quy trình 5 bước

```
1️⃣ KHÁM PHÁ 📚 → 2️⃣ ĐÁNH GIÁ 🎯 → 3️⃣ XUẤT DỮ LIỆU 📄 → 4️⃣ TẢI PDF 📎 → 5️⃣ TRÍCH XUẤT TEXT 📖
```

**Giải thích từng bước:**

1. **🔍 Khám phá**: Tìm kiếm bài báo từ các nguồn (arXiv, PubMed, v.v.)
2. **🎯 Đánh giá**: Lọc bài báo liên quan bằng từ khóa
3. **📄 Xuất dữ liệu**: Lưu metadata vào file JSON/CSV
4. **📎 Tải PDF**: Download file PDF của bài báo
5. **📖 Trích xuất**: Lấy nội dung text từ PDF

### Nguồn dữ liệu hỗ trợ

| Nguồn | Loại | Số lượng bài báo mẫu |
|-------|------|---------------------|
| **arXiv** | Preprints | 269 bài báo |
| **PubMed** | Y khoa | Đã tích hợp |
| **Crossref** | Đa ngành | 268 bài báo |
| **Semantic Scholar** | AI nghiên cứu | 283 bài báo |
| **OpenAlex** | Mở dữ liệu | Đã tích hợp |

### Dữ liệu thu thập

Mỗi bài báo bao gồm:
- 📝 **Tiêu đề** và **tóm tắt**
- 👥 **Tác giả** và **đơn vị**
- 🏷️ **Từ khóa** và **DOI**
- 📅 **Năm xuất bản**
- 🔗 **Link PDF** (nếu có)

## 🚀 Bắt đầu sử dụng

### 1. Cài đặt

```bash
# Clone repository
git clone https://github.com/duynguyenxc/Universal-Web-Scraping-System-high-level-update.git
cd Universal-Web-Scraping-System-high-level-update

# Tạo môi trường ảo
python -m venv uwss-env
uwss-env\Scripts\activate  # Windows
# source uwss-env/bin/activate  # Linux/Mac

# Cài đặt thư viện
pip install -r requirements.txt
```

### 2. Cấu hình

Chỉnh sửa file `config/config.yaml`:

```yaml
# Từ khóa tìm kiếm
domain_keywords:
  - "concrete corrosion"
  - "steel reinforcement"
  - "chloride attack"

# Từ khóa loại trừ
negative_keywords:
  - "quantum physics"
  - "machine learning"

# Email liên hệ (cho API)
contact_email: "your.email@university.edu"
```

### 3. Chạy thử nghiệm đầu tiên

```bash
# Thu thập dữ liệu từ arXiv
python -m src.uwss.cli paperscraper-discover --max 10

# Lọc dữ liệu liên quan
python -m src.uwss.cli score-keywords --config config/config.yaml

# Xuất kết quả
python -m src.uwss.cli export --require-match --out results.jsonl
```

## 📋 Ví dụ sử dụng

### Thu thập bài báo về "concrete corrosion"

```bash
# 1. Khám phá từ nhiều nguồn
python -m src.uwss.cli paperscraper-discover --max 50
python -m src.uwss.cli crossref-lib-discover --max 50
python -m src.uwss.cli semantic-scholar-lib-discover --max 50

# 2. Đánh giá độ liên quan
python -m src.uwss.cli score-keywords --config config/config.yaml

# 3. Xuất dữ liệu chất lượng cao
python -m src.uwss.cli export --require-match --min-score 0.5 --out corrosion_papers.jsonl

# 4. Tải PDF
python -m src.uwss.cli fetch-pdfs --ids-file filtered_ids.txt --limit 20
```

### Phân tích kết quả

```bash
# Xem thống kê
python scripts/analysis/show_source_summary.py

# Kiểm tra chất lượng dữ liệu
python scripts/analysis/check_paperscraper_data.py

# Trực quan hóa kết quả
python scripts/analysis/view_scale_test_results.py
```

## 📂 Cấu trúc thư mục

```
uwss/
├── config/          # Cấu hình từ khóa và thiết lập
├── data/            # Dữ liệu và file PDF đã tải
├── scripts/         # Công cụ hỗ trợ
│   ├── analysis/    # Phân tích dữ liệu
│   ├── testing/     # Test hệ thống
│   └── utilities/   # Bảo trì dữ liệu
├── src/uwss/        # Code chính của hệ thống
├── test/            # Kết quả test (không commit)
└── docs/            # Tài liệu hướng dẫn
```

## 🎯 Tại sao dùng UWSS?

**Trước khi có UWSS:**
- 🔴 Tìm bài báo thủ công trên nhiều website
- 🔴 Copy-paste metadata từ từng trang
- 🔴 Download PDF một cách rời rạc
- 🔴 Quản lý dữ liệu hỗn loạn

**Sau khi có UWSS:**
- ✅ **Tự động hóa hoàn toàn** quy trình thu thập
- ✅ **Nguồn dữ liệu đa dạng** từ 5+ nguồn uy tín
- ✅ **Chất lượng đảm bảo** với hệ thống lọc thông minh
- ✅ **Dễ mở rộng** cho các chủ đề nghiên cứu mới

## 🆘 Hỗ trợ & Đóng góp

### Báo cáo vấn đề
Nếu gặp lỗi, hãy:
1. Kiểm tra log files trong `data/runs/`
2. Chạy scripts phân tích: `python scripts/analysis/check_*.py`
3. Tạo issue trên GitHub với log chi tiết

### Thêm nguồn dữ liệu mới
Hệ thống được thiết kế để dễ dàng thêm nguồn mới:
1. Tạo adapter trong `src/uwss/sources/`
2. Thêm lệnh CLI trong `src/uwss/cli/commands/`
3. Test và validate dữ liệu

## 📞 Liên hệ

**Tác giả:** Duy Nguyen  
**Email:** [your.email@university.edu]  
**GitHub:** https://github.com/duynguyenxc

## 📄 License

Dự án này sử dụng license MIT. Xem file LICENSE để biết thêm chi tiết.

---

<div align="center">

**UWSS - Khi nghiên cứu khoa học gặp công nghệ tự động hóa**

*🚀 Thu thập thông tin học thuật chưa bao giờ dễ dàng đến thế!*

</div>
