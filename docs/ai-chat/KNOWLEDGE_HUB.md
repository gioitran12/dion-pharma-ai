# DION HEALTHCARE AI — PRODUCT KNOWLEDGE HUB & CLAIM VALIDATION
## TÀI LIỆU KIẾN TRÚC VÀ QUẢN TRỊ DỮ LIỆU SẢN PHẨM (BƯỚC 02A)

> **Phiên bản:** v1.0.0  
> **Cập nhật:** Bước 02A — Chuẩn hóa Product Knowledge Hub, Claims và Kiểm soát Dữ liệu Nguồn  
> **Phân hệ:** AI Chatbot & Sales Copilot / RAG Knowledge Vault  
> **Tuân thủ:** Nghị định 342/2025/NĐ-CP (Quản lý Quảng cáo TPBVSK) & Luật 91/2025/QH15 (Bảo vệ Dữ liệu Cá nhân)

---

## 1. TỔNG QUAN VÀ MỤC TIÊU KIẾN TRÚC

Trong hệ thống **DION Healthcare AI**, chatbot tư vấn sản phẩm và hỗ trợ bán hàng **tuyệt đối không được để LLM tự do suy đoán (hallucinate)** về công dụng, liều dùng, thành phần hoặc đối tượng sử dụng. Mọi câu trả lời liên quan đến sản phẩm đều phải dựa trên các phát biểu công dụng (Claims) đã được cơ quan quản lý y tế tiếp nhận và Ban Dược vụ phê duyệt.

**Bước 02A** thiết lập tầng cơ sở dữ liệu tri thức đáng tin cậy:
1. Chuẩn hóa Data Model cho **Product** và **Claim** bằng Pydantic V2.
2. Thiết lập bộ thẩm định **ClaimEligibilityValidator** kiểm soát 8 quy tắc nghiêm ngặt trước khi một Claim được đưa vào tập dữ liệu trả lời thương mại.
3. Tách biệt hoàn toàn Interface (`BaseKnowledgeRepository`) và Triển khai (`JSONKnowledgeRepository`), sẵn sàng tích hợp PostgreSQL/pgvector ở Bước 02B mà không phá vỡ logic Chatbot.
4. Xây dựng công cụ kiểm toán dữ liệu nguồn tự động (`scripts/validate_product_knowledge.py`).

---

## 2. CẤU TRÚC DỮ LIỆU SẢN PHẨM (`ProductRecord`)

Dữ liệu sản phẩm được chuẩn hóa tại `modules/knowledge/schemas.py`:

```python
class ProductRecord(BaseModel):
    sku: str                     # Mã SKU định danh duy nhất (ví dụ: DION-D3-1000)
    name: str                    # Tên thương mại chính thức của sản phẩm
    category: Optional[str]      # Danh mục (Vitamin & Khoáng chất, Mẹ bầu...)
    regulatory_class: Optional[str] # Phân loại pháp lý (TPBVSK, Thuốc OTC...)
    description: Optional[str]   # Tóm tắt sản phẩm (nếu có trong hồ sơ)
    target_users: List[str]      # Đối tượng sử dụng công bố
    mandatory_disclaimer: Optional[str] # Disclaimer bắt buộc theo Nghị định 342
    market: Optional[str] = "VN" # Thị trường phân phối
```

### Quy tắc bất biến (Invariants)
- `sku` là khóa chính duy nhất, không được rỗng và không được trùng lặp.
- Không tự suy diễn phân loại pháp lý nếu tài liệu chưa ghi rõ.
- Không tự ý sinh mô tả công dụng nếu nguồn dữ liệu không có.

---

## 3. CẤU TRÚC DỮ LIỆU CLAIM (`ClaimRecord`)

Claim là phát biểu khoa học về công dụng hoặc đặc tính của sản phẩm:

```python
class ClaimRecord(BaseModel):
    claim_id: str                # Mã định danh Claim (ví dụ: CLM-D3-01)
    product_sku: str             # SKU của sản phẩm sở hữu
    claim_text: str              # Nội dung phát biểu đã được thẩm định
    zone: KnowledgeZone          # Phân vùng tri thức tiếp cận
    status: ClaimStatus          # Trạng thái phê duyệt
    effective_from: Optional[str] # Ngày bắt đầu hiệu lực (YYYY-MM-DD)
    effective_until: Optional[str]# Ngày hết hạn hiệu lực (YYYY-MM-DD)
    source_document_id: Optional[str] # Số công bố tiếp nhận ĐKSP
    source_reference: Optional[str]   # Tên tài liệu chứng minh khoa học
    evidence_source: Optional[str]    # Trường tương thích ngược
    approved_by: Optional[str]   # Chuyên viên Dược vụ ký duyệt
    usage_scope: Optional[str]   # Phạm vi sử dụng (COMMERCIAL_ALL...)
    market: Optional[str]        # Thị trường áp dụng
    required_disclaimer: Optional[str]
    prohibited_expressions: List[str] # Từ ngữ cấm đi kèm
```

---

## 4. QUẢN LÝ PHÂN VÙNG TRI THỨC (KNOWLEDGE ZONES)

Hệ thống phân định ranh giới tiếp cận thông tin thành 4 phân vùng tri thức:

| Phân Vùng (`KnowledgeZone`) | Mục Đích Sử Dụng | Mức Độ Tiếp Cận | Áp Dụng Trong Chatbot |
| :--- | :--- | :---: | :---: |
| **`COMMERCIAL_APPROVED`** | Thông tin công dụng thương mại đã được Cục ATTP/Dược vụ phê duyệt | Công khai | **Được phép sử dụng** để tư vấn và quảng cáo thương mại |
| **`INTERNAL_MEDICAL`** | Tài liệu phân tích chuyên sâu, dược động học, khuyến cáo nội bộ | Nội bộ Dược vụ | **Cấm** trả lời tự động cho khách hàng; chỉ phục vụ đào tạo nội bộ |
| **`RESEARCH`** | Nghiên cứu tiền lâm sàng, cơ chế phân tử chưa có phê duyệt thương mại | Nghiên cứu R&D | **Cấm** đưa vào hội thoại tư vấn bán hàng |
| **`EXPIRED`** | Các Claim đã hết hạn hiệu lực định kỳ hoặc bị thay thế | Lưu trữ kiểm toán | **Cấm** sử dụng trong mọi hoạt động tư vấn mới |

> **Lưu ý tương thích:** Trong dữ liệu JSON cũ có vùng `INTERNAL_EXPERT`, hệ thống tự động ánh xạ tương thích vào vùng nội bộ `INTERNAL_MEDICAL` để bảo toàn khả năng vận hành của code cũ.

---

## 5. BỘ THẨM ĐỊNH CLAIM ELIGIBILITY VALIDATOR

Bộ thẩm định độc lập `ClaimEligibilityValidator` tại `modules/knowledge/validator.py` kiểm tra từng Claim qua chuỗi 8 bước logic:

1. **Kiểm tra tồn tại:** Claim không được rỗng hoặc None.
2. **Khớp SKU chính xác:** `claim.product_sku == requested_sku`. Ngăn chặn 100% rò rỉ Claim chéo sản phẩm.
3. **Trạng thái phê duyệt:** Bắt buộc `status == ClaimStatus.APPROVED`. Từ chối ngay nếu `REVOKED`, `EXPIRED`, `DRAFT`, `PENDING`, `REJECTED`.
4. **Kiểm tra phân vùng:** Trong tư vấn thương mại (`COMMERCIAL_ADVICE`), chỉ chấp nhận `zone == KnowledgeZone.COMMERCIAL_APPROVED`.
5. **Kiểm tra ngày hết hạn:** `effective_until >= as_of_date`.
6. **Kiểm tra ngày bắt đầu:** `effective_from <= as_of_date` (nếu có).
7. **Kiểm tra hồ sơ chứng minh:** Bắt buộc có `source_reference` hoặc `evidence_source` không rỗng.
8. **Kiểm tra chữ ký duyệt:** Bắt buộc có thông tin `approved_by` (nếu thiếu, đánh dấu `review_required = True`).

### Danh sách mã kết quả (`ValidationCode`)
- `PRODUCT_NOT_FOUND`: SKU không tồn tại trong hệ thống.
- `SKU_MISMATCH`: Claim không thuộc về SKU đang hỏi.
- `CLAIM_NOT_FOUND`: Không tìm thấy bản ghi Claim.
- `CLAIM_NOT_APPROVED`: Chưa được phê duyệt.
- `CLAIM_EXPIRED`: Đã quá ngày hết hạn hiệu lực.
- `CLAIM_NOT_YET_EFFECTIVE`: Chưa đến ngày bắt đầu có hiệu lực.
- `CLAIM_REVOKED`: Đã bị cơ quan quản lý thu hồi.
- `RESTRICTED_KNOWLEDGE_ZONE`: Thuộc vùng nội bộ/nghiên cứu.
- `MISSING_SOURCE`: Thiếu căn cứ tài liệu chứng minh.
- `MISSING_APPROVAL_EVIDENCE`: Thiếu chữ ký/người ký duyệt Dược vụ.
- `INVALID_DATE`: Định dạng ngày không chuẩn ISO YYYY-MM-DD.

---

## 6. KIẾN TRÚC REPOSITORY VÀ KHẢ NĂNG MỞ RỘNG DATABASE

Để chuẩn bị cho việc chuyển đổi từ file JSON mẫu sang **PostgreSQL / pgvector** trong tương lai mà không phải viết lại Chatbot, hệ thống tách rời interface:

```text
               +-----------------------------+
               |   BaseKnowledgeRepository   | (Interface trừu tượng)
               +-----------------------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
+---------------------------+   +---------------------------+
| JSONKnowledgeRepository   |   | PostgreSQLRepository      |
| (Đang dùng ở Bước 02A)    |   | (Kế hoạch mở rộng tương lai)|
+---------------------------+   +---------------------------+
```

### Các hàm cốt lõi của Repository:
- `list_products() -> List[ProductRecord]`
- `get_product_by_sku(sku: str) -> Optional[ProductRecord]`
- `get_claims_by_product(sku: str) -> List[ClaimRecord]`
- `get_claim_by_id(claim_id: str) -> Optional[ClaimRecord]`
- `get_eligible_commercial_claims(sku: str, as_of_date=None) -> List[ClaimRecord]`
- `get_all_claims() -> List[ClaimRecord]`

---

## 7. CÔNG CỤ ĐỐI SOÁT DỮ LIỆU (`validate_product_knowledge.py`)

Chạy script kiểm toán chất lượng dữ liệu nguồn bất cứ lúc nào:

```bash
python scripts/validate_product_knowledge.py
```

### Báo cáo đối soát thực tế trên `data/products_claims.json`:
- **Tổng số SKU:** 3 (`DION-D3-1000`, `DION-CAL-MOM`, `DION-FE-FOLIC`)
- **Tổng số Claims:** 8
- **Số Claims đủ điều kiện thương mại:** 6
  - `CLM-D3-01`: Hấp thu Canxi và Photpho
  - `CLM-D3-02`: Phát triển và duy trì hệ xương, răng
  - `CLM-CAL-01`: Canxi sinh học từ tảo đỏ & Vitamin K2
  - `CLM-CAL-02`: Giảm nguy cơ thiếu canxi thai kỳ
  - `CLM-FE-01`: Bổ sung Sắt hữu cơ & Acid Folic
  - `CLM-FE-02`: Sắt hữu cơ êm dịu dạ dày
- **Số Claims hết hạn:** 1 (`CLM-D3-03` hết hạn ngày 2025-12-31)
- **Số Claims vùng nội bộ:** 1 (`CLM-D3-04` thuộc vùng chuyên gia `INTERNAL_EXPERT`)
- **Số cảnh báo thiếu trường (WARNING):** 8 (Toàn bộ 8 Claims hiện chưa có trường `effective_from` trong file JSON mẫu)
- **Lỗi nghiêm trọng (ERROR):** 0

---

## 8. GIỚI HẠN DỮ LIỆU MẪU & KHUYẾN NGHỊ CHO BƯỚC 02B

1. **Dữ liệu mẫu PoC:** Bộ dữ liệu `data/products_claims.json` hiện là dữ liệu mẫu phục vụ phát triển kỹ thuật. Cần được rà soát và xác nhận bởi Ban Dược vụ DION trước khi triển khai môi trường Production thực tế.
2. **Bổ sung Schema tương lai:** Trong các bước mở rộng sau, khuyến nghị bổ sung trường `effective_from` và `source_document_id` chính thức vào nguồn dữ liệu.
3. **Sẵn sàng cho Bước 02B:** Các phương thức `get_eligible_commercial_claims()` của `KnowledgeRepository` đã sẵn sàng cung cấp tập văn bản nguồn sạch, đã kiểm duyệt để làm đầu vào cho thuật toán BM25 Keyword Search và Vector Embedding ở Bước 02B.
