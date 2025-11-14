# Phân tích lỗi khi khai thác TRB

## 🔍 Các lỗi đã gặp

### 1. **discover-trb autodetect slow/timeout** ❌

**Vấn đề:**
- Implementation ban đầu cố gắng **autodetect RSS feeds** bằng cách thử nhiều URLs khác nhau
- Logic autodetect:
  ```python
  # Thử nhiều URLs để tìm RSS feed
  urls_to_try = [
      "https://trid.trb.org/rss",
      "https://www.trb.org/rss",
      "https://trid.trb.org/feed",
      # ... nhiều URLs khác
  ]
  for url in urls_to_try:
      try:
          response = requests.get(url, timeout=5)
          if response.status_code == 200:
              # Found RSS feed!
  ```
- **Kết quả**: Chậm, timeout, không ổn định

**Nguyên nhân:**
- Không biết chính xác RSS feed URL của TRB
- Thử nhiều URLs → mất thời gian
- Timeout khi server không phản hồi

**Fix đã áp dụng:**
- ❌ Remove autodetect logic
- ✅ Require explicit `--rss-url` hoặc `--oai-url` từ user
- ✅ Thêm `socket.setdefaulttimeout(5)` để tránh hang vô hạn

---

### 2. **discover-trid OAI-PMH endpoint 404/403** ❌

**Vấn đề:**
- Cố gắng dùng OAI-PMH endpoint mặc định: `https://trid.trb.org/oai/request`
- **Kết quả**: 404 Not Found hoặc 403 Forbidden

**Nguyên nhân:**
- TRID **KHÔNG CÓ OAI-PMH endpoint công khai**
- Endpoint này không tồn tại hoặc không public

**Fix đã áp dụng:**
- ❌ Remove default OAI-PMH URL
- ✅ Allow user specify `--oai-url` hoặc `--rss-url`
- ✅ Nếu không có OAI-PMH → dùng sitemap crawling

---

### 3. **discover-fhwa (via NTL) OAI-PMH endpoint 403/503** ❌

**Vấn đề:**
- NTL có OAI-PMH endpoint: `https://rosap.ntl.bts.gov/fedora/oai`
- `Identify` request → ✅ 200 OK
- `ListRecords` request → ❌ 403 Forbidden hoặc 503 Service Unavailable

**Nguyên nhân:**
- Có thể cần **authentication/institutional access**
- Có thể có **rate limiting** hoặc **access restrictions**
- Không mở hoàn toàn như arXiv

**Fix:**
- ⚠️ Chưa có fix (cần liên hệ NTL để xác nhận access policy)

---

## 🎯 Vấn đề cốt lõi

### **Sai lầm trong approach:**

1. **Cố gắng dùng OAI-PMH cho TRB/TRID**
   - ❌ TRB/TRID **KHÔNG CÓ OAI-PMH** công khai
   - ✅ Nên dùng **sitemap crawling** thay vì OAI-PMH

2. **Autodetect logic không ổn định**
   - ❌ Thử nhiều URLs → chậm, timeout
   - ✅ Nên require explicit URLs từ user hoặc config

3. **Giả định sai về access policy**
   - ❌ Giả định TRB/TRID có OAI-PMH như arXiv
   - ✅ Thực tế: TRB/TRID miễn phí nhưng dùng sitemap, không phải OAI-PMH

---

## ✅ Giải pháp đúng

### **TRB/TRID - Nên dùng Sitemap Crawling:**

```python
# Đúng approach:
1. Parse sitemap.xml từ https://trid.trb.org/sitemap.xml
2. Extract URLs từ sitemap
3. Crawl từng URL (với rate limiting)
4. Parse HTML để extract metadata
5. Insert vào DB (cùng schema như arXiv)
```

**Ví dụ sitemap structure:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://trid.trb.org/view/123456</loc>
    <lastmod>2024-01-01</lastmod>
  </url>
  <!-- ... -->
</urlset>
```

**Crawl HTML page:**
```html
<!-- https://trid.trb.org/view/123456 -->
<h1>Title: Concrete Deterioration Study</h1>
<div class="abstract">Abstract text...</div>
<div class="authors">Author 1, Author 2</div>
```

---

## 📊 So sánh Approach

| Approach | arXiv | TRB/TRID | Kết quả |
|----------|-------|----------|---------|
| **OAI-PMH** | ✅ Có | ❌ Không có | Lỗi 404/403 |
| **RSS Feed** | ✅ Có | ⚠️ Có nhưng không rõ URL | Autodetect chậm/timeout |
| **Sitemap Crawling** | ⚠️ Không cần | ✅ **Nên dùng** | **Đúng approach** |
| **API** | ✅ Có | ❌ Không có | - |

---

## 🎯 Kết luận

### **Lý do lỗi:**

1. **Sai approach**: Cố gắng dùng OAI-PMH cho TRB/TRID (không có)
2. **Autodetect không ổn định**: Thử nhiều URLs → chậm/timeout
3. **Giả định sai**: Nghĩ TRB/TRID giống arXiv về access method

### **Giải pháp đúng:**

1. **TRB/TRID**: Dùng **sitemap crawling** (parse sitemap.xml → crawl HTML pages)
2. **Require explicit URLs**: Không autodetect, user phải cung cấp URLs
3. **Respect robots.txt**: Check robots.txt trước khi crawl

### **Pipeline vẫn giống nhau:**

- **Discover**: Sitemap crawler (thay vì OAI-PMH)
- **Score**: Keyword scoring (giống arXiv)
- **Export**: Filter & export (giống arXiv)
- **Fetch**: Download PDFs (giống arXiv)
- **Extract**: Full-text extraction (giống arXiv)

→ **Chỉ khác ở bước DISCOVER (adapter), còn lại giống hệt!**

