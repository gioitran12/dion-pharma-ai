# DION HEALTHCARE AI — CHANGELOG PHÂN HỆ AI CHAT

Toàn bộ các thay đổi kỹ thuật, sửa đổi cấu trúc và cập nhật mã nguồn của phân hệ AI Chatbot & Sales Copilot được ghi nhận chi tiết tại tài liệu này.

## [v1.3.0] - 2026-10-16 (BƯỚC 02A: PRODUCT KNOWLEDGE HUB & CLAIM VALIDATION)

### Đã thêm mới (Added)
* **`modules/knowledge/schemas.py`:**
  - `ProductRecord`: Pydantic V2 schema cho sản phẩm (`sku`, `name`, `category`, `regulatory_class`, `mandatory_disclaimer`, `target_users`, `market`).
  - `ClaimRecord`: Pydantic V2 schema cho Claim (`claim_id`, `product_sku`, `claim_text`, `zone`, `status`, `effective_until`, `effective_from`, `evidence_source`, `approved_by`).
  - `KnowledgeZone` Enum: Phân định 4 vùng tri thức (`COMMERCIAL_APPROVED`, `INTERNAL_MEDICAL`, `RESEARCH`, `EXPIRED`).
  - `ClaimStatus` Enum: Vòng đời phê duyệt (`APPROVED`, `DRAFT`, `PENDING`, `REJECTED`, `EXPIRED`, `REVOKED`, `SUSPENDED`).
  - `ValidationCode` Enum: Hệ thống 14 mã lỗi đối soát Claim (`SKU_MISMATCH`, `CLAIM_EXPIRED`, `RESTRICTED_KNOWLEDGE_ZONE`, `MISSING_SOURCE`, `MISSING_APPROVAL_EVIDENCE`...).
  - `ClaimValidationResult`: Schema đầu ra chi tiết của bộ thẩm định.
  - `DataValidationItem` & `DataValidationSummary`: Schema báo cáo kiểm toán dataset.
* **`modules/knowledge/validator.py`:**
  - `ClaimEligibilityValidator`: Bộ thẩm định độc lập 8 bước kiểm soát tính hợp lệ của Claim trước khi đưa vào RAG/tư vấn thương mại. Hỗ trợ inject `as_of_date` phục vụ kiểm thử tất định theo thời gian.
* **`modules/knowledge/repository.py`:**
  - `BaseKnowledgeRepository`: Lớp trừu tượng định nghĩa các hàm truy xuất tri thức (`list_products`, `get_product_by_sku`, `get_claims_by_product`, `get_claim_by_id`, `get_eligible_commercial_claims`, `get_all_claims`).
  - `JSONKnowledgeRepository`: Triển khai đọc và lập chỉ mục dữ liệu từ `data/products_claims.json`, sẵn sàng chuyển đổi sang Database/PostgreSQL trong tương lai.
* **`scripts/validate_product_knowledge.py`:**
  - Script CLI kiểm toán tự động chất lượng dữ liệu nguồn, phân loại `ERROR`, `WARNING`, `INFO`.
* **`tests/test_knowledge_hub_step02a.py`:**
  - 21 bài kiểm thử tự động toàn diện bao phủ mọi khía cạnh của Bước 02A (21/21 PASS; toàn bộ repository 69/69 PASS).
* **`docs/ai-chat/KNOWLEDGE_HUB.md`:**
  - Tài liệu chi tiết về kiến trúc Knowledge Vault, cấu trúc dữ liệu, ma trận phân vùng và hướng dẫn kiểm toán.

### Đã cập nhật (Updated)
* **`modules/claims_hub.py`:**
  - Tích hợp thêm các hàm typed `get_product_record()` và `get_eligible_claims_records()`.
  - Duy trì tương thích ngược 100% cho `get_all_products()`, `get_product_by_sku()`, `get_active_claims()`, `get_claims_summary()`.
* **`docs/ai-chat/ROADMAP.md` & `TEST_MATRIX.md`:**
  - Tách Bước 02 thành 02A (DONE) và 02B (TODO), cập nhật bảng ma trận 69 test cases.

---

## [v1.2.0] - 2026-10-16 (BƯỚC 01B: TÍCH HỢP LLM GATEWAY & API CHAT THỰC TẾ)

### Đã thêm mới (Added)
* **`modules/chat/prompts/system_prompts.py` & `modules/chat/prompts/__init__.py`:**
  - `BASE_COPILOT_SYSTEM_PROMPT` và `EXPERIMENTAL_TEST_PROMPT`: Quản lý tập trung chỉ dẫn hệ thống an toàn ở Backend; client không thể tự ghi đè.
  - Hàm `get_system_prompt()`: Cung cấp system instruction chuẩn hóa cho Gateway.
* **`modules/chat/providers/base.py`:**
  - `BaseLLMProvider`: Lớp trừu tượng định nghĩa hợp đồng `generate()` và `validate_configuration()`.
  - `LLMRequest` & `LLMResult`: Data models nội bộ của Gateway, tách biệt với HTTP request/response.
  - Hệ thống Exception chuẩn: `LLMError`, `LLMConfigurationError`, `LLMAuthenticationError`, `LLMRateLimitError`, `LLMTimeoutError`, `LLMEmptyResponseError`, `LLMProviderError`.
* **`modules/chat/providers/gemini_provider.py`:**
  - Adapter chính thức tích hợp `google-genai` SDK mới nhất (`genai.Client.aio.models.generate_content`).
  - Hỗ trợ trích xuất token usage (`usage_metadata`), finish_reason, latency và bắt lỗi an toàn (không lộ API key).
* **`modules/chat/providers/openai_provider.py`:**
  - Adapter chính thức tích hợp `openai` SDK (`AsyncOpenAI.chat.completions.create`).
  - Hỗ trợ bắt lỗi `AuthenticationError`, `RateLimitError`, `APITimeoutError`, `APIConnectionError`.
* **`modules/chat/providers/fake_provider.py`:**
  - Fake LLM Provider chuyên dụng phục vụ Unit Test thông qua Dependency Injection (DI). Hỗ trợ mô phỏng lỗi tạm thời để kiểm thử retry logic.
* **`modules/chat/llm_gateway.py`:**
  - `LLMGateway`: Bộ điều phối trung tâm tự động chọn Provider từ biến môi trường (`LLM_PROVIDER`, `LLM_MODEL`).
  - Bounded retries: Retry tối đa 2 lần với exponential backoff cho lỗi tạm thời/mạng; **tuyệt đối không retry** lỗi sai API key hoặc lỗi cấu hình.
  - Bắt buộc trả lỗi trung thực khi nhà cung cấp thất bại, cấm tự động fallback ngầm sang Mock trong production.
* **`scripts/smoke_llm.py`:**
  - Script CLI độc lập kiểm thử kết nối live API của Gemini hoặc OpenAI, đo latency, usage và thông báo trạng thái `BLOCKED_FOR_LIVE_VERIFICATION` rõ ràng nếu chưa có key thật.
* **`tests/test_llm_gateway_step01b.py`:**
  - 18 bài kiểm thử tự động bao phủ toàn diện các yêu cầu kỹ thuật của Bước 01B (18/18 PASS).

### Đã sửa & Cập nhật (Updated)
* **`server.py`:**
  - Đăng ký endpoint thử nghiệm nội bộ `POST /api/copilot/chat` được bảo vệ bằng cờ `ENABLE_EXPERIMENTAL_CHAT` (mặc định: `false`).
  - Chặn các câu hỏi tư vấn y khoa / Claims sản phẩm chưa qua RAG và Safety Guard (`decision: BLOCKED`, `requires_handoff: True`, không bịa Claim/Ticket).
  - Giữ nguyên 100% endpoint cũ `POST /api/copilot/ask`.
* **`modules/chat/__init__.py`:**
  - Xuất bổ sung `LLMGateway`, `get_llm_gateway`, các Providers và Exception classes.
* **`.env.example`:**
  - Cập nhật mẫu cấu hình `LLM_PROVIDER`, `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_OUTPUT_TOKENS`, `ENABLE_EXPERIMENTAL_CHAT`.
* **`docs/ai-chat/ROADMAP.md` & `API_CONTRACT.md` & `TEST_MATRIX.md`:**
  - Cập nhật tiến độ, hợp đồng kiểm soát truy cập và ma trận 48 test cases.

---

## [v1.1.0] - 2026-10-16 (BƯỚC 01A: CHUẨN HÓA DATA MODELS & API CONTRACT)


### Đã thêm mới (Added)
* **`modules/chat/enums.py`:**
  - `ChatIntent`: 16 ý định chuẩn hóa (GREETING, PRODUCT_INFO, PRODUCT_COMPARISON, USAGE_INFORMATION, MEDICAL_RISK, SAFETY_COMPLAINT, BUY_PRODUCT, B2B_INQUIRY, ORDER_STATUS, CUSTOMER_SUPPORT, MARKETING_REQUEST, PROHIBITED_GENERATION, OPT_OUT, GENERAL_CHAT, OFF_TOPIC, UNKNOWN).
  - `ChatDecision`: 7 trạng thái điều phối (DRAFT_FOR_APPROVAL, READY_TO_SEND, INSUFFICIENT_EVIDENCE, HANDOFF_REQUIRED, BLOCKED, CLARIFICATION_REQUIRED, SYSTEM_ERROR).
  - `RiskLevel`: 4 cấp độ an toàn y tế và pháp lý (LOW, MEDIUM, HIGH, CRITICAL).
  - `TicketStatus`: 5 trạng thái vòng đời Ticket (NEW, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED).
  - `ChatRole`: 2 vai trò hội thoại công khai (USER, ASSISTANT).
* **`modules/chat/schemas.py`:**
  - `ChatRequest`: Schema đầu vào đa lượt hỗ trợ tiếng Việt Unicode, giới hạn 4.000 ký tự, chặn rỗng/khoảng trắng, tự động chuẩn hóa `session_id`.
  - `ChatMessage`: Schema lưu vết từng lượt tin nhắn trong hội thoại.
  - `CitationInfo`: Schema biểu diễn nguồn trích dẫn Claim, tài liệu công bố, số trang, link nguồn.
  - `IntentResult`: Schema kết quả phân loại ý định phục vụ routing.
  - `SafetyResult`: Schema đánh giá rủi ro y tế và cờ rủi ro.
  - `TicketData`: Schema biểu diễn thông tin Ticket chuyển tuyến Dược vụ.
  - `ChatAction`: Schema mô tả hành động gợi ý đề xuất cho nhân viên.
  - `ChatResponse`: Schema đầu ra chính thức của AI Chatbot với validation bất biến (invariants).
  - `LegacyCopilotRequest` & `LegacyCopilotResponse`: Schema tương thích ngược 100% cho client hiện tại.
  - `ErrorDetail` & `ChatErrorResponse`: Schema chuẩn mực cho các phản hồi lỗi HTTP 400/422/500.
  - Adapter functions: `legacy_to_chat_response()` và `chat_response_to_legacy()` chuyển đổi hai chiều độc lập.
* **`modules/chat/__init__.py`:** Xuất gói package chuẩn hóa cho phân hệ chat.
* **`tests/test_chat_schemas_step01a.py`:** 20 bài unit & integration tests kiểm thử validation, unicode, serialization, enum, invariants, adapter và API endpoint.
* **`docs/ai-chat/API_CONTRACT.md`:** Tài liệu đặc tả hợp đồng API cho cả endpoint hiện tại (`POST /api/copilot/ask`) và endpoint mới (`POST /api/copilot/chat`).
* **`docs/ai-chat/TEST_MATRIX.md`:** Bảng ma trận 30 test cases đang hoạt động.

### Đã kiểm tra & Duy trì (Maintained)
* Endpoint hiện hữu `POST /api/copilot/ask` tiếp tục hoạt động ổn định, không thay đổi tên trường, bảo toàn giao diện Streamlit và Web Tailwind UI.
* Toàn bộ 10 bài test của Bước 00.1 tiếp tục PASS 100%.

---

## [v1.0.1] - 2026-10-16 (BƯỚC 00.1: SỬA LỖI LOGIC NGUY HIỂM)

### Đã sửa (Fixed)
* **`modules/sales_copilot.py`:**
  - Loại bỏ hoàn toàn lỗi fallback lấy Claim của sản phẩm đầu tiên (D3) khi không tìm thấy Claim phù hợp.
  - Xóa bỏ thông báo giả lập *"Hệ thống đã tự động tạo Ticket chuyển tiếp cho Dược vụ"*, thay bằng thông báo yêu cầu chuyển chuyên gia và gắn cờ `handoff_required: True`.
  - Thêm trạng thái `INSUFFICIENT_EVIDENCE` khi không tìm thấy Claim hợp lệ hoặc khi SKU không tồn tại.
  - Ngăn chặn rò rỉ Claim giữa các sản phẩm khác nhau khi hỏi theo SKU cụ thể.
* **`modules/claims_hub.py`:**
  - Thắt chặt hàm `get_active_claims()` để loại bỏ Claim hết hạn (`CLM-D3-03`) và Claim nội bộ (`CLM-D3-04`) khỏi vùng thương mại.
* **`views/tab_copilot.py` & `templates/index.html`:**
  - Bổ sung xử lý hiển thị nhãn cảnh báo vàng khi nhận `INSUFFICIENT_EVIDENCE`.
* **`tests/test_copilot_step00_1.py`:**
  - Bổ sung bộ 10 unit & regression tests đầu tiên cho repository.

---

## [v1.0.0] - 2026-10-16 (BƯỚC 00: KHẢO SÁT & ROADMAP)

### Đã thêm mới (Added)
* **`docs/ai-chat/ROADMAP.md`:** Xây dựng lộ trình tổng thể 16 bước từ Bước 00 đến Bước 15, bao phủ CHAT-01 đến CHAT-14 và mở rộng đa kênh EXT-15.
* Khảo sát chi tiết cấu trúc source code, API hiện hữu và thiết kế kiến trúc mục tiêu.
