# DION HEALTHCARE AI — HỢP ĐỒNG API CHAT (API CONTRACT)

> **Phiên bản:** v1.0.0  
> **Cập nhật:** Bước 01A — Chuẩn hóa Data Models & Schemas  
> **Phân hệ:** AI Chatbot & Sales Copilot  
> **Chuẩn pháp lý:** Nghị định 342/2025/NĐ-CP (Quảng cáo TPBVSK) & Luật 91/2025/QH15 (Bảo vệ Dữ liệu Cá nhân)

---

## 1. TỔNG QUAN HỢP ĐỒNG API

Hệ thống API Chatbot DION Healthcare AI cung cấp 2 giao diện song song:

1. **Endpoint Hiện Hữu (`POST /api/copilot/ask`):**
   * Phục vụ các thành phần giao diện hiện có (Web Dashboard PoC, Streamlit Tab Copilot).
   * Định dạng request/response gọn, mô hình Single-turn.
   * Duy trì **tương thích ngược 100%** (Zero Breaking Changes).

2. **Endpoint Mở Rộng Mục Tiêu (`POST /api/copilot/chat`):**
   * Phục vụ Chatbot đa lượt (Multi-turn), tích hợp RAG Claims, quản lý phiên (`session_id`), đánh giá rủi ro an toàn y khoa (`risk`), trích dẫn cấu trúc (`sources`), hành động đề xuất (`actions`), và theo dõi sự cố (`ticket_id`).
   * Sử dụng schema Pydantic V2 được xác thực nghiêm ngặt.

---

## 2. ENDPOINT HIỆN HỮU: `POST /api/copilot/ask`

### 2.1. Request Schema (`LegacyCopilotRequest`)

* **Content-Type:** `application/json`
* **Cấu trúc trường:**

| Trường | Kiểu dữ liệu | Bắt buộc | Mặc định | Mô tả |
| :--- | :---: | :---: | :---: | :--- |
| `query` | `string` | **Có** | — | Câu hỏi của nhân viên hoặc khách hàng (tối thiểu 1 ký tự). |
| `sku` | `string` | Không | `"ALL"` | Mã SKU sản phẩm cần tra cứu (`"DION-D3-1000"`, `"DION-CAL-MOM"`, `"DION-FE-FOLIC"`, hoặc `"ALL"`). |

* **Ví dụ Request:**
```json
{
  "query": "Vitamin D3 có công dụng gì đối với xương?",
  "sku": "DION-D3-1000"
}
```

### 2.2. Response Schema (`LegacyCopilotResponse`)

* **Status Code:** `200 OK`
* **Content-Type:** `application/json`
* **Cấu trúc trường:**

| Trường | Kiểu dữ liệu | Mô tả |
| :--- | :---: | :--- |
| `type` | `string` | Loại phản hồi: `"NORMAL"` (hợp lệ), `"ESCALATION"` (nhạy cảm y tế), `"INSUFFICIENT_EVIDENCE"` (thiếu căn cứ). |
| `badge` | `string` | Huy hiệu trạng thái hiển thị trên UI. |
| `content` | `string` | Nội dung văn bản câu trả lời (kèm disclaimer bắt buộc của NĐ 342 khi hợp lệ). |
| `citations` | `List[string]` | Danh sách mã Claims hợp lệ được sử dụng (ví dụ: `["CLM-D3-01"]`). Rỗng nếu thiếu căn cứ hoặc nhạy cảm. |
| `source_claims` | `List[object]` | Chi tiết Claims làm bằng chứng (`sku`, `claim_id`, `evidence`). |
| `handoff_required`| `boolean` | `true` khi gặp câu hỏi nhạy cảm (thai kỳ, bệnh nền, thuốc kê đơn) cần chuyển Dược sĩ; `false` khi bình thường. |

* **Ví dụ Response 1: Trường hợp bình thường (Claim hợp lệ):**
```json
{
  "type": "NORMAL",
  "badge": "✅ ĐÃ XÁC THỰC TỪ CLAIMS ĐƯỢC DUYỆT",
  "content": "Dựa trên tài liệu công bố chính thức của sản phẩm **Vitamin D3 1000IU Drops**:\n\n✅ **Công dụng được phép tư vấn:**\n- Hỗ trợ phát triển và duy trì hệ xương, răng chắc khỏe.\n\n📌 **Căn cứ pháp lý & Nguồn trích dẫn:**\n- Mã Claim: `CLM-D3-02`\n- Nguồn: Hồ sơ công bố sản phẩm số 4521/2025/ĐKSP\n\n💡 *Lưu ý: Bắt buộc đính kèm disclaimer khi gửi văn bản cho khách hàng: 'Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh'.*",
  "citations": ["CLM-D3-02"],
  "source_claims": [
    {
      "sku": "DION-D3-1000",
      "product_name": "Vitamin D3 1000IU Drops",
      "claim_id": "CLM-D3-02",
      "claim_text": "Hỗ trợ phát triển và duy trì hệ xương, răng chắc khỏe.",
      "evidence": "Hồ sơ công bố sản phẩm số 4521/2025/ĐKSP",
      "score": 4
    }
  ],
  "handoff_required": false
}
```

* **Ví dụ Response 2: Trường hợp nhạy cảm y tế (Escalation):**
```json
{
  "type": "ESCALATION",
  "badge": "⚠️ YÊU CẦU CHUYỂN DƯỢC SĨ TƯ VẤN CHUYÊN MÔN",
  "content": "Câu hỏi liên quan đến nhóm nhạy cảm y tế (MANG THAI). Cần tuân thủ quy tắc an toàn y tế nghiêm ngặt.\n\n📋 Hướng dẫn xử lý quy trình an toàn y tế:\n1. Trường hợp này cần được dược sĩ hoặc người có chuyên môn xem xét. Vui lòng chuyển yêu cầu tới bộ phận phụ trách.\n2. Tuyệt đối KHÔNG tự ý khẳng định an toàn hoặc tư vấn liều lượng cho trường hợp này.\n3. Ghi nhận đầy đủ câu hỏi và thông tin liên hệ của khách hàng để chuyển giao chuyên gia liên hệ lại.",
  "citations": [],
  "source_claims": [],
  "handoff_required": true
}
```

* **Ví dụ Response 3: Trường hợp thiếu căn cứ (Insufficient Evidence):**
```json
{
  "type": "INSUFFICIENT_EVIDENCE",
  "badge": "⚠️ CHƯA ĐỦ CĂN CỨ XÁC MINH",
  "content": "Hiện tại hệ thống chưa có đủ thông tin sản phẩm được xác minh để trả lời chính xác câu hỏi này. Vui lòng kiểm tra lại sản phẩm hoặc chuyển nhân viên phụ trách hỗ trợ.",
  "citations": [],
  "source_claims": [],
  "handoff_required": false
}
```

---

## 3. ENDPOINT MỤC TIÊU: `POST /api/copilot/chat`

Endpoint được thiết kế chuẩn Enterprise phục vụ hội thoại nhiều lượt.

### 3.1. Request Schema (`ChatRequest`)

* **Content-Type:** `application/json`
* **Cấu trúc trường:**

| Trường | Kiểu dữ liệu | Bắt buộc | Ràng buộc validation | Mô tả |
| :--- | :---: | :---: | :--- | :--- |
| `session_id` | `string \| null` | Không | UUID / chuỗi định danh; tự động chuẩn hóa chuỗi rỗng thành `null`. | Mã phiên hội thoại. Truyền `null` khi bắt đầu cuộc trò chuyện mới. |
| `message` | `string` | **Có** | Độ dài 1 – 4.000 ký tự; không cho phép rỗng hoặc chỉ có khoảng trắng; hỗ trợ tiếng Việt Unicode. | Nội dung tin nhắn người dùng. |
| `product_id` | `string \| null` | Không | Chuỗi SKU hợp lệ (`DION-D3-1000`...) hoặc `null`. | Ngữ cảnh sản phẩm trọng tâm (nếu có). |
| `request_id` | `string \| null` | Không | Chuỗi UUID chống trùng lặp request. | Mã trace client gửi lên hỗ trợ Idempotency. |

* **Ví dụ Request:**
```json
{
  "session_id": "8a32b6e1-9541-47c3-bc9a-7612f9e42100",
  "message": "Canxi Tảo Đỏ Cal-Mom có uống chung với Sắt Fero-Plus được không?",
  "product_id": "DION-CAL-MOM",
  "request_id": "req-20261016-001"
}
```

### 3.2. Response Schema (`ChatResponse`)

* **Status Code:** `200 OK`
* **Content-Type:** `application/json`
* **Cấu trúc trường:**

| Trường | Kiểu dữ liệu | Mô tả |
| :--- | :---: | :--- |
| `schema_version` | `string` | Phiên bản hợp đồng API (mặc định `"1.0"`). |
| `session_id` | `string \| null` | Mã phiên hội thoại tiếp tục duy trì. |
| `message_id` | `string \| null` | Định danh duy nhất của tin nhắn phản hồi. |
| `trace_id` | `string \| null` | Mã vết phục vụ truy soát lỗi và kiểm toán tuân thủ. |
| `intent` | `ChatIntent` (Enum) | Ý định chính (`PRODUCT_INFO`, `MEDICAL_RISK`, `PRODUCT_COMPARISON`...). |
| `decision` | `ChatDecision` (Enum) | Quyết định (`DRAFT_FOR_APPROVAL`, `HANDOFF_REQUIRED`, `INSUFFICIENT_EVIDENCE`, `BLOCKED`...). |
| `answer` | `string` | Nội dung văn bản câu trả lời đã được thẩm định. |
| `product_ids` | `List[string]` | Danh mục SKU liên quan đến câu trả lời. |
| `sources` | `List[CitationInfo]` | Danh sách trích dẫn Claim (`claim_id`, `document_title`, `page`, `source_url`). |
| `risk` | `SafetyResult` | Cấp độ rủi ro (`risk_level`), cờ an toàn (`risk_flags`), yêu cầu chuyển giao (`requires_handoff`). |
| `actions` | `List[ChatAction]` | Gợi ý hành động (`type`, `label`, `requires_approval`). |
| `ticket_id` | `string \| null` | Mã ticket nếu đã lưu thành công; **bắt buộc là null** khi chưa lưu vào CSDL. |

* **Ví dụ Response (ChatResponse):**
```json
{
  "schema_version": "1.0",
  "session_id": "8a32b6e1-9541-47c3-bc9a-7612f9e42100",
  "message_id": "msg-20261016-092",
  "trace_id": "trace-dion-82194",
  "intent": "USAGE_INFORMATION",
  "decision": "DRAFT_FOR_APPROVAL",
  "answer": "Canxi và Sắt nên uống cách nhau ít nhất 2 giờ để tránh ức chế cạnh tranh hấp thu vi chất tại ruột non.\n\nSản phẩm này là thực phẩm bảo vệ sức khỏe, không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
  "product_ids": ["DION-CAL-MOM", "DION-FE-FOLIC"],
  "sources": [
    {
      "claim_id": "CLM-CAL-01",
      "document_id": "8892/2025/ĐKSP",
      "document_title": "Hồ sơ công bố Canxi Cal-Mom",
      "page": 1,
      "source_url": null,
      "source_version": "Verified"
    }
  ],
  "risk": {
    "risk_level": "LOW",
    "risk_flags": [],
    "requires_handoff": false,
    "reason": null,
    "recommended_department": null
  },
  "actions": [
    {
      "type": "COPY_ANSWER",
      "label": "Sao chép câu trả lời gửi khách hàng",
      "requires_approval": false
    }
  ],
  "ticket_id": null
}
```

---

## 4. SCHEMA XỬ LÝ LỖI (`ChatErrorResponse`)

Khi client gửi request không hợp lệ (HTTP 400 / 422) hoặc hệ thống gặp sự cố (HTTP 500):

* **Status Codes:**
  * `400 Bad Request`: Message rỗng, chỉ gồm khoảng trắng, hoặc sai định dạng.
  * `422 Unprocessable Entity`: Kiểu dữ liệu không tương thích.
  * `500 Internal Server Error`: Lỗi máy chủ không mong muốn.

* **Cấu trúc trường:**
```json
{
  "schema_version": "1.0",
  "error": "Dữ liệu yêu cầu không hợp lệ",
  "details": [
    {
      "code": "EMPTY_MESSAGE",
      "message": "Nội dung tin nhắn không được rỗng hoặc chỉ chứa khoảng trắng.",
      "field": "message"
    }
  ],
  "trace_id": "err-trace-9921"
}
```

---

## 5. QUY TẮC TƯƠNG THÍCH VÀ BẢO TOÀN HỆ THỐNG

1. **Zero Breaking Changes:** Không đổi tên hoặc xóa các trường trong phản hồi của `/api/copilot/ask` (`type`, `badge`, `content`, `citations`, `source_claims`, `handoff_required`).
2. **Adapter hai chiều độc lập:** Sử dụng `legacy_to_chat_response()` và `chat_response_to_legacy()` để chuyển đổi cấu trúc linh hoạt khi nâng cấp backend.
3. **Chống Fake Data:** Không tự tiện tạo `ticket_id` nếu chưa có bản ghi thật trong database; không tự tiện gán `sources` nếu quyết định là `INSUFFICIENT_EVIDENCE`.

---

## 6. ĐẶC TẢ BƯỚC 01B: LLM GATEWAY VÀ ENDPOINT THỬ NGHIỆM NỘI BỘ

### 6.1. Cơ chế kiểm soát truy cập (Gating Mechanism)
* Endpoint `POST /api/copilot/chat` được bảo vệ bằng biến môi trường `ENABLE_EXPERIMENTAL_CHAT` (mặc định: `false`).
* Khi `ENABLE_EXPERIMENTAL_CHAT=false`: API trả về `403 Forbidden` với thông điệp:
  ```json
  {
    "detail": "Experimental chat endpoint is disabled. Set ENABLE_EXPERIMENTAL_CHAT=true to enable internal testing."
  }
  ```
* Chỉ khi quản trị viên chủ động bật `ENABLE_EXPERIMENTAL_CHAT=true`, endpoint mới mở quyền phục vụ kiểm thử kết nối nội bộ.

### 6.2. Phạm vi thử nghiệm an toàn (Safe Scope Boundary)
* Chatbot ở Bước 01B **chưa tích hợp Semantic RAG Claims** (sẽ làm ở Bước 02) và **chưa có Safety Guard y khoa hoàn chỉnh** (Bước 04).
* Vì vậy, endpoint từ chối trả lời tự do cho các câu hỏi lâm sàng/công dụng/liều dùng/chỉ định:
  * Trả về `decision: BLOCKED`
  * `sources: []` (không bịa đặt nguồn dẫn)
  * `ticket_id: null` (không bịa đặt ticket chuyển tiếp)
  * `risk`: `SafetyResult(risk_level=MEDIUM, requires_handoff=True)`
* Đối với câu hỏi chào hỏi hoặc giới thiệu hệ thống, Gateway sẽ gọi mô hình LLM đã cấu hình (Gemini / OpenAI) với System Instructions do Backend quản lý độc quyền.

### 6.3. Mã lỗi chuẩn hóa của LLM Gateway

| Mã Lỗi | HTTP Code | Retryable | Nguyên Nhân | Hành Động Khuyến Nghị |
| :--- | :---: | :---: | :--- | :--- |
| `LLM_NOT_CONFIGURED` | 500 | Không | Thiếu API key hoặc key chứa giá trị placeholder mẫu | Cấu hình API key thực tế vào file `.env` |
| `LLM_INVALID_PROVIDER` | 500 | Không | Biến `LLM_PROVIDER` không thuộc `gemini`, `openai`, `fake` | Đặt lại `LLM_PROVIDER=gemini` hoặc `openai` |
| `LLM_AUTH_ERROR` | 401 | **Không** | API key sai, hết hạn hoặc không có quyền truy cập | Kiểm tra lại tài khoản và cấp lại key mới |
| `LLM_RATE_LIMIT` | 429 | Có | Vượt quá hạn mức request/token của nhà cung cấp | Giảm tần suất gọi hoặc tăng quota tài khoản |
| `LLM_TIMEOUT` | 504 | Có | Quá thời gian `LLM_TIMEOUT_SECONDS` mà không có phản hồi | Kiểm tra kết nối mạng hoặc tăng timeout |
| `LLM_EMPTY_RESPONSE` | 502 | Không | Nhà cung cấp trả về rỗng hoặc ứng viên bị lọc | Rà soát lại prompt và bộ lọc an toàn nhà mạng |
| `LLM_PROVIDER_ERROR` | 502 | Phụ thuộc | Lỗi mạng, 5xx server error từ phía nhà cung cấp | Bounded retry tự động tối đa 2 lần |

