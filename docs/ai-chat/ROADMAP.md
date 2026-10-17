# DION HEALTHCARE AI — ROADMAP NÂNG CẤP HỆ THỐNG AI CHATBOT & SALES COPILOT

> **Phiên bản:** v1.1.0  
> **Trạng thái tổng thể:** Đã hoàn thành Bước 00 & Bước 00.1  
> **Kiến trúc mục tiêu:** Modular RAG & Multi-Turn Chatbot tuân thủ Nghị định 342/2025/NĐ-CP và Luật 91/2025/QH15  
> **Luồng xử lý:** `Frontend` → `FastAPI Chat API` → `Chat Orchestrator` → `Intent / Safety / RAG` → `LLM Gateway` → `Output Validation` → `Response`

---

## BẢNG TỔNG QUAN TIẾN ĐỘ LỘ TRÌNH

| Bước | Mã Hạng Mục | Tên Bước / Mục Tiêu Trọng Tâm | Phụ Thuộc | Trạng Thái |
| :---: | :---: | :--- | :---: | :---: |
| **00** | **AUDIT-00** | Khảo sát source code hiện tại & Lập kế hoạch triển khai | Không | **DONE** |
| **00.1** | **HOTFIX-00.1** | Sửa lỗi logic nguy hiểm: Fallback Claim sai sản phẩm & Thông báo Ticket giả | Bước 00 | **DONE** |
| **01A** | **CHAT-01A** | Chuẩn hóa Pydantic Schema & API Contract (Single-turn & Multi-turn) | Bước 00.1 | **DONE** |
| **01B** | **CHAT-01B** | Tích hợp LLM Gateway (Gemini & OpenAI) & Chat API thực tế | Bước 01A | **DONE (Live: BLOCKED_FOR_LIVE_VERIFICATION)** |
| **02A** | **CHAT-02A** | Chuẩn hóa Product Knowledge Hub & Claim Validation | Bước 01A | **DONE** |
| **02B** | **CHAT-02B** | Semantic & Keyword Claims Retrieval & RAG Ranking | Bước 02A | **TODO** |
| **03** | **CHAT-03** | Xây dựng Bộ Phân loại Ý định (Intent Classification 4 Nhóm) | Bước 01A, 01B | **TODO** |
| **04** | **CHAT-04** | Bộ lọc An toàn Y khoa & Chuyển tuyến Dược sĩ (Medical Escalation) | Bước 01A, 03 | **TODO** |
| **05** | **CHAT-05** | Rule Engine Chặn Bẫy Vi phạm Quảng cáo & Cam kết Điều trị (NĐ 342) | Bước 01A, 03 | **TODO** |
| **06** | **CHAT-06** | Engine So sánh Sản phẩm Khách quan (Multi-Product Comparison) | Bước 02, 03 | **TODO** |
| **07** | **CHAT-07** | Quản lý Ngữ cảnh Hội thoại Nhiều Lượt (Session & Context Memory) | Bước 01A | **TODO** |
| **08** | **CHAT-08** | Xây dựng Core Chat Orchestrator (Hợp nhất toàn bộ luồng xử lý) | Bước 01B–07 | **TODO** |
| **09** | **CHAT-09** | Hệ thống Lưu vết Ticket Escalation Thực tế & Audit Trail Kiểm toán | Bước 04, 07 | **TODO** |
| **10** | **CHAT-10** | Endpoint FastAPI `/api/copilot/chat` & Duy trì Tương thích `/api/copilot/ask` | Bước 08, 09 | **TODO** |
| **11** | **CHAT-11** | Nâng cấp Giao diện Streamlit (`views/tab_copilot.py`) Đa lượt | Bước 10 | **TODO** |
| **12** | **CHAT-12** | Nâng cấp Giao diện Web Platform (`templates/index.html`) Đa lượt | Bước 10 | **TODO** |
| **13** | **CHAT-13** | Bộ Kiểm thử Tự động 50–100 Test Cases & Đo lường KPI Nghiệm thu | Bước 10–12 | **TODO** |
| **14** | **CHAT-14** | Tối ưu Hiệu năng, Bảo mật Dữ liệu (Luật 91/2025) & Audit Logging | Bước 10, 13 | **TODO** |
| **15** | **EXT-15** | Mở rộng Tích hợp Đa kênh (Zalo OA, Messenger Webhook & CRM Sync) | Bước 10, 14 | **TODO** |

---

## CHI TIẾT CÁC BƯỚC TRIỂN KHAI

### BƯỚC 00: Khảo Sát Source Code Hiện Tại & Lập Kế Hoạch Triển Khai
* **Mục tiêu:** Kiểm tra thực tế toàn bộ mã nguồn, cấu hình môi trường, kiểm thử API hiện hữu, xác định rõ hiện trạng từng thành phần và xây dựng lộ trình thực thi.
* **Phạm vi chức năng:** Đọc mã nguồn, đo kiểm API `/api/copilot/ask`, kiểm tra database JSON, kiểm tra môi trường Python 3.11, tạo tài liệu quản lý tiến độ.
* **File/Module tác động:** Tạo mới `docs/ai-chat/ROADMAP.md`.
* **Phụ thuộc:** Không.
* **Đầu ra:** Báo cáo khảo sát chi tiết 10 mục và file `docs/ai-chat/ROADMAP.md`.
* **Test case:**
  - TC00-1: Gọi kiểm tra API hiện tại `/api/copilot/ask` với câu hỏi thường $\rightarrow$ Trả về 200 OK.
  - TC00-2: Gọi kiểm tra API hiện tại với từ khóa nhạy cảm thai kỳ $\rightarrow$ Trả về `ESCALATION`.
* **Tiêu chí nghiệm thu:** Tài liệu đầy đủ, phân loại rõ ràng 4 trạng thái, xác định đúng các rủi ro kỹ thuật, không làm thay đổi business logic hiện có.
* **Trạng thái:** **DONE**

---

### BƯỚC 00.1: Sửa Lỗi Logic Nguy Hiểm Trước Khi Tích Hợp LLM
* **Mục tiêu:** Loại bỏ hoàn toàn lỗi fallback lấy Claim của sản phẩm khác gây sai lệch thông tin y dược, loại bỏ thông báo tạo Ticket giả, bổ sung trạng thái `INSUFFICIENT_EVIDENCE` và thiết lập bộ kiểm thử 10 test case tự động bằng pytest.
* **Phạm vi chức năng:**
  - Sửa `modules/sales_copilot.py`: Chỉ tìm Claim thuộc đúng SKU yêu cầu; không fallback ngẫu nhiên sang D3; xóa thông báo tạo Ticket giả; thêm cờ `handoff_required`.
  - Cập nhật `modules/claims_hub.py`: Siết chặt kiểm tra `zone`, `status == "APPROVED"`, và ngày hết hạn `effective_until`.
  - Cập nhật frontend `views/tab_copilot.py` và `templates/index.html` xử lý hiển thị nhãn cảnh báo `INSUFFICIENT_EVIDENCE`.
  - Thiết lập bộ kiểm thử `tests/test_copilot_step00_1.py` gồm 10 unit & regression tests.
* **File/Module tác động:**
  - [`modules/sales_copilot.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/sales_copilot.py)
  - [`modules/claims_hub.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/claims_hub.py)
  - [`views/tab_copilot.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/views/tab_copilot.py)
  - [`templates/index.html`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/templates/index.html)
  - [`tests/test_copilot_step00_1.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/tests/test_copilot_step00_1.py)
* **Phụ thuộc:** Bước 00.
* **Đầu ra:** Code lõi an toàn, không rò rỉ Claim chéo SKU, 10/10 test case pass.
* **Test case:** 10 test cases trong `tests/test_copilot_step00_1.py` bao phủ: Claim hợp lệ, SKU không tồn tại, nội dung thiếu căn cứ, Claim hết hạn, Claim nội bộ, câu hỏi nhạy cảm, không thông báo ticket giả, API contract compatibility, chặn rò rỉ Claim giữa các sản phẩm, mảng citations rỗng khi thiếu nguồn.
* **Tiêu chí nghiệm thu:** Pytest 10/10 PASS; server phản hồi HTTP 200 cho cả 3 trường hợp NORMAL, ESCALATION, INSUFFICIENT_EVIDENCE.
* **Trạng thái:** **DONE**

---

### BƯỚC 01A (CHAT-01A): Chuẩn Hóa Pydantic Schema & API Contract
* **Mục tiêu:** Định nghĩa toàn bộ cấu trúc dữ liệu cho luồng chat bằng Pydantic models trong FastAPI, làm nền tảng thống nhất cho Backend, Orchestrator và Frontend.
* **Phạm vi chức năng:**
  - Định nghĩa các Schema: `ChatMessage` (role, content, timestamp), `ChatRequest` (query, session_id, sku, stream), `Citation` (claim_id, claim_text, evidence_source), `SafetyFlag` (is_sensitive, reason, risk_level), `TicketCreate` (ticket_id, customer_query, reason, created_at, status), `ChatResponse` (session_id, reply, message_type, citations, safety, handoff_required).
* **File/Module tác động:** Tạo mới `modules/chat/schemas.py`.
* **Phụ thuộc:** Bước 00.1.
* **Đầu ra:** Module `schemas.py` hoàn chỉnh với type annotations và validation chặt chẽ.
* **Test case:**
  - TC01A-1: Khởi tạo `ChatRequest` hợp lệ và không hợp lệ $\rightarrow$ Kiểm tra Pydantic ValidationError.
  - TC01A-2: Serialize và Deserialize `ChatResponse` $\rightarrow$ Đảm bảo đúng định dạng JSON contract.
* **Tiêu chí nghiệm thu:** Các schema bao phủ đủ mọi tình huống nghiệp vụ (NORMAL, ESCALATION, INSUFFICIENT_EVIDENCE, PROHIBITED_BLOCKED, COMPARISON). Đạt 20/20 test cases PASS.
* **Trạng thái:** **DONE**

---

### BƯỚC 01B (CHAT-01B): Tích Hợp LLM Gateway & Chat API Thực Tế
* **Mục tiêu:** Xây dựng cổng giao tiếp LLM Gateway đa nhà cung cấp, hỗ trợ cả OpenAI và Google Gemini, tích hợp xử lý timeout, bounded retries và endpoint thử nghiệm nội bộ có cổng kiểm soát `ENABLE_EXPERIMENTAL_CHAT`.
* **Phạm vi chức năng:**
  - Xây dựng `modules/chat/providers/base.py`: Interface `BaseLLMProvider`, `LLMRequest`, `LLMResult`, và hệ thống Exception chuẩn (`LLMConfigurationError`, `LLMAuthenticationError`, `LLMRateLimitError`, `LLMTimeoutError`, `LLMEmptyResponseError`, `LLMProviderError`).
  - Xây dựng `modules/chat/providers/gemini_provider.py`: Adapter chuẩn cho Google GenAI SDK (`google-genai`).
  - Xây dựng `modules/chat/providers/openai_provider.py`: Adapter chuẩn cho OpenAI SDK (`openai.AsyncOpenAI`).
  - Xây dựng `modules/chat/providers/fake_provider.py`: Mock/Fake Provider phục vụ riêng Unit Test qua Dependency Injection (DI).
  - Xây dựng `modules/chat/llm_gateway.py`: Điều phối khởi tạo provider theo biến môi trường, quản lý timeout, giới hạn retry cho lỗi tạm thời, chuẩn hóa tokens và latency. Tuyệt đối không fallback ngầm sang Mock trong production.
  - Xây dựng `modules/chat/prompts/system_prompts.py`: Quản lý tập trung chỉ dẫn hệ thống an toàn ở Backend.
  - Cập nhật `server.py`: Đăng ký endpoint thử nghiệm nội bộ `POST /api/copilot/chat` được bảo vệ bởi cờ `ENABLE_EXPERIMENTAL_CHAT` (mặc định tắt), từ chối tư vấn y khoa tự do khi chưa có RAG & Safety Guard. Giữ nguyên 100% endpoint cũ `POST /api/copilot/ask`.
  - Xây dựng `scripts/smoke_llm.py`: Smoke test kiểm tra live API key độc lập, báo lỗi trung thực và không làm lộ API keys.
* **File/Module tác động:**
  - [`modules/chat/prompts/system_prompts.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/chat/prompts/system_prompts.py)
  - [`modules/chat/prompts/__init__.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/chat/prompts/__init__.py)
  - [`modules/chat/providers/base.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/chat/providers/base.py)
  - [`modules/chat/providers/gemini_provider.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/chat/providers/gemini_provider.py)
  - [`modules/chat/providers/openai_provider.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/chat/providers/openai_provider.py)
  - [`modules/chat/providers/fake_provider.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/chat/providers/fake_provider.py)
  - [`modules/chat/providers/__init__.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/chat/providers/__init__.py)
  - [`modules/chat/llm_gateway.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/chat/llm_gateway.py)
  - [`modules/chat/__init__.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/chat/__init__.py)
  - [`server.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/server.py)
  - [`scripts/smoke_llm.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/scripts/smoke_llm.py)
  - [`tests/test_llm_gateway_step01b.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/tests/test_llm_gateway_step01b.py)
  - [`.env.example`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/.env.example)
* **Phụ thuộc:** Bước 01A.
* **Đầu ra:** Cổng LLMGateway hoàn chỉnh, hỗ trợ đa provider, xử lý lỗi an toàn và bộ test 18 test cases.
* **Test case:** 18 bài kiểm thử trong `tests/test_llm_gateway_step01b.py` bao phủ: Import, routing cấu hình, từ chối provider sai, từ chối thiếu/placeholder key, chuẩn hóa response, xử lý timeout, rate limit, không retry lỗi xác thực, bounded retry lỗi tạm thời, DI fake provider, cấm silent fallback sang mock, bảo vệ secret, kiểm tra endpoint cũ `/api/copilot/ask`, kiểm tra gating endpoint mới `/api/copilot/chat`, chặn truy vấn y khoa chưa qua RAG & Safety.
* **Tiêu chí nghiệm thu:**
  - Unit tests: 18/18 PASS (Toàn bộ test suite: 48/48 PASS).
  - Live smoke test: Sẵn sàng, báo trạng thái `BLOCKED_FOR_LIVE_VERIFICATION` rõ ràng và chính trực khi chưa điền API key thật vào `.env`.
* **Trạng thái:** **DONE (Live test: BLOCKED_FOR_LIVE_VERIFICATION)**

---

### BƯỚC 02A (CHAT-02A): Chuẩn Hóa Product Knowledge Hub & Claim Validation
* **Mục tiêu:** Xây dựng nguồn dữ liệu sản phẩm thống nhất, chuẩn hóa Data Models (ProductRecord, ClaimRecord), bộ thẩm định ClaimEligibilityValidator và Repository trừu tượng, ngăn chặn 100% rò rỉ Claim chéo sản phẩm hoặc sử dụng Claim hết hạn/chưa duyệt.
* **Phạm vi chức năng:**
  - Xây dựng `modules/knowledge/schemas.py`: Định nghĩa `ProductRecord`, `ClaimRecord`, `KnowledgeZone`, `ClaimStatus`, `ValidationCode`, `ClaimValidationResult`.
  - Xây dựng `modules/knowledge/validator.py`: `ClaimEligibilityValidator` kiểm tra 8 quy tắc độc lập (SKU match, status APPROVED, zone COMMERCIAL_APPROVED, ngày hiệu lực `effective_until`/`effective_from`, nguồn chứng minh, bằng chứng phê duyệt).
  - Xây dựng `modules/knowledge/repository.py`: `BaseKnowledgeRepository` và `JSONKnowledgeRepository`, sẵn sàng tích hợp DB/PostgreSQL trong tương lai.
  - Cập nhật `modules/claims_hub.py`: Duy trì tương thích ngược 100% với server và copilot, tích hợp thêm typed methods.
  - Xây dựng `scripts/validate_product_knowledge.py`: Công cụ kiểm toán chất lượng dữ liệu nguồn, phân loại ERROR, WARNING, INFO.
  - Thiết lập bộ kiểm thử `tests/test_knowledge_hub_step02a.py`: 21 unit & integration tests tự động.
* **File/Module tác động:**
  - [`modules/knowledge/schemas.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/knowledge/schemas.py)
  - [`modules/knowledge/validator.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/knowledge/validator.py)
  - [`modules/knowledge/repository.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/knowledge/repository.py)
  - [`modules/knowledge/__init__.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/knowledge/__init__.py)
  - [`modules/claims_hub.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/modules/claims_hub.py)
  - [`scripts/validate_product_knowledge.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/scripts/validate_product_knowledge.py)
  - [`tests/test_knowledge_hub_step02a.py`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/tests/test_knowledge_hub_step02a.py)
  - [`docs/ai-chat/KNOWLEDGE_HUB.md`](file:///d:/Project_AI/dion-pharma-ai-main/dion-pharma-ai-main/docs/ai-chat/KNOWLEDGE_HUB.md)
* **Phụ thuộc:** Bước 01A.
* **Đầu ra:** Knowledge Hub hoàn chỉnh, ClaimEligibilityValidator, Repository trừu tượng, 21/21 test cases PASS (Tổng cộng toàn bộ hệ thống: 69/69 tests PASS).
* **Trạng thái:** **DONE**

---

### BƯỚC 02B (CHAT-02B): Semantic & Keyword Claims Retrieval & RAG Ranking
* **Mục tiêu:** Xây dựng cơ chế tra cứu tri thức sản phẩm chuẩn mực (Knowledge Grounding), phân tích ngữ nghĩa câu hỏi người dùng và trích xuất top-K Claims phù hợp nhất từ Knowledge Hub.
* **Phạm vi chức năng:**
  - BM25/Keyword scoring + Semantic Similarity (sử dụng lightweight embedding hoặc LLM reranking).
  - Tích hợp trích xuất liều dùng, đối tượng, disclaimer bắt buộc.
* **Phụ thuộc:** Bước 02A.
* **Trạng thái:** **TODO**
