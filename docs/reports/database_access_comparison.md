# So sánh Access Policy: TRB/TRID/FHWA/ERDC vs Subscription Databases

## 📊 Bảng so sánh

| Database | Access Type | Subscription Required? | API Keys Required? | Bulk Harvest Allowed? | Similar to arXiv? |
|----------|-------------|------------------------|-------------------|----------------------|-------------------|
| **arXiv** | Open | ❌ No | ❌ No | ✅ Yes (OAI-PMH) | ✅ Yes |
| **TRID** | Public/Free | ❌ No | ❌ No | ✅ Yes (sitemap crawl) | ✅ Yes (similar) |
| **TRB** | Public/Free | ❌ No | ❌ No | ✅ Yes (sitemap crawl) | ✅ Yes (similar) |
| **NTL (FHWA)** | Partially Open | ⚠️ Maybe | ⚠️ Maybe | ⚠️ Limited (OAI-PMH issues) | ⚠️ Partially |
| **ERDC** | Unknown | ❓ Unknown | ❓ Unknown | ❓ Unknown | ❌ No |
| **Web of Science** | Subscription | ✅ Yes | ✅ Yes | ❌ No (ToS prohibits) | ❌ No |
| **Scopus** | Subscription | ✅ Yes | ✅ Yes | ❌ No (ToS prohibits) | ❌ No |
| **ScienceDirect** | Subscription | ✅ Yes | ✅ Yes | ❌ No (ToS prohibits) | ❌ No |
| **ProQuest** | Subscription | ✅ Yes | ✅ Yes | ❌ No (ToS prohibits) | ❌ No |
| **EBSCO** | Subscription | ✅ Yes | ✅ Yes | ❌ No (ToS prohibits) | ❌ No |

## 🔍 Phân tích chi tiết

### TRB/TRID - KHÁC với Subscription Databases

**TRID:**
- ✅ **Free and public**: FAQ states "anyone may search TRID and download/print/email records"
- ✅ **No subscription needed**: Completely open access
- ✅ **Sitemap crawling allowed**: Has public XML sitemap, robots.txt allows crawling
- ✅ **No API keys required**: Can crawl directly (with proper rate limiting)
- ⚠️ **No OAI-PMH**: Unlike arXiv, doesn't have OAI-PMH, but sitemap crawling is legitimate

**Kết luận**: TRID giống arXiv ở chỗ:
- Miễn phí, công khai
- Cho phép harvest metadata (qua sitemap thay vì OAI-PMH)
- Không cần subscription/API keys
- Chỉ cần tuân thủ robots.txt và rate limit

### FHWA (NTL) - KHÁC một phần

**NTL (National Transportation Library):**
- ⚠️ **OAI-PMH endpoint exists**: `https://rosap.ntl.bts.gov/fedora/oai`
- ❌ **Access issues**: ListRecords returns 403/503 errors
- ❓ **May require authentication**: Might need institutional access or special permissions
- ⚠️ **Not fully open**: Not as open as arXiv/TRID

**Kết luận**: NTL có vẻ không hoàn toàn mở như arXiv/TRID, có thể cần institutional access.

### ERDC - KHÔNG RÕ

**ERDC:**
- ❓ **Domain issues**: `erdc.usace.army.mil` doesn't resolve
- ❓ **Access unknown**: No clear public access information
- ❓ **May be internal/military**: Could be restricted access

**Kết luận**: Không rõ, cần liên hệ trực tiếp để xác nhận.

### Subscription Databases - HOÀN TOÀN KHÁC

**Web of Science, Scopus, ScienceDirect, ProQuest, EBSCO:**
- ❌ **Require subscription**: Must have institutional subscription
- ❌ **Require API keys**: Need official API access from providers
- ❌ **Strict ToS**: Terms of Service prohibit bulk scraping/harvesting
- ❌ **Not open**: Cannot be treated like open repositories

**Kết luận**: Hoàn toàn khác với TRID/arXiv - cần subscription, API keys, và tuân thủ ToS nghiêm ngặt.

## ✅ Trả lời câu hỏi của bạn

**"Có phải là TRB hay là FHWA/ERDC đều gặp tình trạng tương tự giống như các database mà thầy đưa cho tôi đúng không?"**

**Trả lời: KHÔNG**

- **TRB/TRID**: KHÔNG - Giống arXiv, miễn phí, công khai, cho phép harvest (qua sitemap)
- **FHWA (NTL)**: CÓ PHẦN - Có vấn đề access (403/503), có thể cần authentication
- **ERDC**: KHÔNG RÕ - Cần xác nhận thêm
- **Subscription databases (Web of Science, Scopus, etc.)**: HOÀN TOÀN KHÁC - Cần subscription + API keys + tuân thủ ToS nghiêm ngặt

## 🎯 Khuyến nghị

1. **TRB/TRID**: Có thể tích hợp ngay (sitemap crawling, tuân thủ robots.txt)
2. **FHWA (NTL)**: Cần liên hệ để xác nhận access policy, có thể cần institutional access
3. **ERDC**: Cần liên hệ trực tiếp để xác nhận
4. **Subscription databases**: Chỉ tích hợp khi có institutional subscription + API keys hợp pháp

