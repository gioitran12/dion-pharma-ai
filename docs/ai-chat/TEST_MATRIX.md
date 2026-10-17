# DION HEALTHCARE AI — MA TRẬN KIỂM THỬ (TEST MATRIX)

> **Phân hệ:** AI Chatbot & Sales Copilot  
> **Cập nhật:** Hoàn thiện Chatbot MVP Thực Tế & Tích hợp Claims Grounding  
> **Tổng số test cases:** 79 tests (10 tests Bước 00.1 + 20 tests Bước 01A + 18 tests Bước 01B + 21 tests Bước 02A + 10 tests MVP Flow)  
> **Tỷ lệ Pass:** 100% (79/79 passed)

---

## 0. MA TRẬN TEST CASES CHATBOT MVP FLOW (`tests/test_chat_mvp_flow.py`)

| Mã Test | Tên Bài Kiểm Thử | Kịch Bản Nghiệp Vụ & Quy Tắc Kiểm Thử | Cơ Chế Test | Kết Quả |
| :---: | :--- | :--- | :---: | :---: |
| **TC-MVP-01** | `test_scenario_1_greeting` | Chào hỏi thông thường $\rightarrow$ Gọi Gateway sinh lời chào an toàn, intent=GREETING, decision=READY_TO_SEND, sources rỗng | DI (FakeProvider) | ✅ **PASS** |
| **TC-MVP-02** | `test_scenario_2_valid_product_claims` | Hỏi công dụng D3 hợp lệ $\rightarrow$ Trích xuất đúng `CLM-D3-01`/`02`, loại bỏ claim hết hạn, decision=DRAFT_FOR_APPROVAL, gắn cờ duyệt nhân viên | DI (FakeProvider) | ✅ **PASS** |
| **TC-MVP-03** | `test_scenario_3_claim_not_found_insufficient_evidence` | Hỏi công dụng không có trong hồ sơ Claims $\rightarrow$ Trả INSUFFICIENT_EVIDENCE, sources rỗng, không tự bịa công dụng | Integration | ✅ **PASS** |
| **TC-MVP-04** | `test_scenario_4_nonexistent_sku_no_fallback` | Hỏi SKU không tồn tại $\rightarrow$ Trả INSUFFICIENT_EVIDENCE, cấm fallback sang D3 | Integration | ✅ **PASS** |
| **TC-MVP-05A** | `test_scenario_5a_pregnancy_escalation` | Khách hàng mang thai $\rightarrow$ Trả HANDOFF_REQUIRED, risk=HIGH, cấm ticket giả | Safety Guard | ✅ **PASS** |
| **TC-MVP-05B** | `test_scenario_5b_drug_interaction_escalation` | Khách hỏi tương tác thuốc $\rightarrow$ Trả HANDOFF_REQUIRED, chuyển Dược sĩ | Safety Guard | ✅ **PASS** |
| **TC-MVP-05C** | `test_scenario_5c_prohibited_treatment_blocked` | Khách hỏi cam kết điều trị loãng xương $\rightarrow$ Trả BLOCKED theo Nghị định 342 | Safety Guard | ✅ **PASS** |
| **TC-MVP-06A** | `test_scenario_6a_llm_timeout` | Cổng LLM bị timeout quá hạn $\rightarrow$ Bắt lỗi và trả HTTP 504 đúng chuẩn | Mock / DI | ✅ **PASS** |
| **TC-MVP-06B** | `test_scenario_6b_llm_missing_config` | Thiếu API key thật trong môi trường $\rightarrow$ Báo lỗi LLM_NOT_CONFIGURED chính trực | Unit (Env) | ✅ **PASS** |
| **TC-MVP-07** | `test_scenario_7_legacy_endpoint_ask_intact` | Endpoint cũ `/api/copilot/ask` duy trì hoạt động 100%, bảo toàn contract | Integration | ✅ **PASS** |

---

## 1. MA TRẬN TEST CASES BƯỚC 02A (`tests/test_knowledge_hub_step02a.py`)

| Mã Test | Tên Bài Kiểm Thử | Mục Tiêu & Kịch Bản Kiểm Thử | Cơ Chế Test | Kết Quả |
| :---: | :--- | :--- | :---: | :---: |
| **TC02A-01** | `test_01_list_products` | Đọc danh mục sản phẩm hợp lệ, kiểm tra đầy đủ 3 SKU mẫu (D3, Cal-Mom, Fero-Plus) | Unit (Repository) | ✅ **PASS** |
| **TC02A-02** | `test_02_get_product_by_sku` | Tìm sản phẩm chính xác theo SKU, kiểm tra đầy đủ tên và phân loại pháp lý | Unit (Repository) | ✅ **PASS** |
| **TC02A-03** | `test_03_nonexistent_sku` | SKU không tồn tại trả về `None`, không gây crash, không trả về danh sách claims rác | Unit (Repository) | ✅ **PASS** |
| **TC02A-04** | `test_04_detect_duplicate_sku` | Phát hiện lỗi nghiêm trọng khi dataset chứa SKU bị trùng lặp | Unit (Validator) | ✅ **PASS** |
| **TC02A-05** | `test_05_get_claims_by_product` | Lấy toàn bộ 4 Claims của SKU `DION-D3-1000` đúng mã định danh | Unit (Repository) | ✅ **PASS** |
| **TC02A-06** | `test_06_no_cross_sku_leakage` | Ngăn chặn 100% rò rỉ Claim giữa các sản phẩm (Claim của D3 không xuất hiện trong Cal-Mom) | Unit (Repository) | ✅ **PASS** |
| **TC02A-07** | `test_07_eligible_commercial_claims` | Lọc chính xác 2 Claims thương mại đủ điều kiện của D3 (`CLM-D3-01`, `02`) | Unit (Repository) | ✅ **PASS** |
| **TC02A-08** | `test_08_internal_expert_claims_excluded` | Claim thuộc vùng nội bộ chuyên gia (`CLM-D3-04`) bị loại khỏi tư vấn thương mại | Unit (Validator) | ✅ **PASS** |
| **TC02A-09** | `test_09_expired_claim_excluded` | Claim hết hạn (`CLM-D3-03`, hết hạn 2025) bị loại bỏ khỏi kết quả | Unit (Validator) | ✅ **PASS** |
| **TC02A-10** | `test_10_future_claim_not_yet_effective` | Claim có `effective_from` trong tương lai bị từ chối (`CLAIM_NOT_YET_EFFECTIVE`) | Unit (Validator) | ✅ **PASS** |
| **TC02A-11** | `test_11_revoked_claim_excluded` | Claim bị cơ quan y tế thu hồi (`status == REVOKED`) bị loại bỏ ngay | Unit (Validator) | ✅ **PASS** |
| **TC02A-12** | `test_12_unapproved_claim_excluded` | Claim ở trạng thái `DRAFT` / `PENDING` chưa duyệt bị loại bỏ | Unit (Validator) | ✅ **PASS** |
| **TC02A-13** | `test_13_invalid_date_format` | Định dạng ngày tháng không chuẩn ISO YYYY-MM-DD bị phát hiện (`INVALID_DATE`) | Unit (Validator) | ✅ **PASS** |
| **TC02A-14** | `test_14_missing_evidence_source` | Claim thiếu tài liệu/hồ sơ chứng minh bị phát hiện (`MISSING_SOURCE`) | Unit (Validator) | ✅ **PASS** |
| **TC02A-15** | `test_15_missing_approval_evidence` | Claim thiếu người ký duyệt Dược vụ bị gắn cờ cần rà soát (`review_required=True`) | Unit (Validator) | ✅ **PASS** |
| **TC02A-16** | `test_16_sku_mismatch` | Claim không khớp SKU yêu cầu bị từ chối với mã `SKU_MISMATCH` | Unit (Validator) | ✅ **PASS** |
| **TC02A-17** | `test_17_detect_duplicate_claim_id` | Phát hiện lỗi nghiêm trọng khi dataset chứa Claim ID bị trùng lặp | Unit (Validator) | ✅ **PASS** |
| **TC02A-18** | `test_18_no_hallucinated_fields` | Trường dữ liệu không có trong file gốc thì giữ nguyên `None`, không tự AI bịa | Unit (Repository) | ✅ **PASS** |
| **TC02A-19** | `test_19_claims_hub_backwards_compatibility` | Hàm `get_active_claims()` và `get_claims_summary()` cũ tiếp tục chạy chuẩn xác 100% | Integration | ✅ **PASS** |
| **TC02A-20** | `test_20_deterministic_as_of_date` | Hỗ trợ inject `as_of_date` phục vụ kiểm thử tất định theo thời gian | Unit (Validator) | ✅ **PASS** |
| **TC02A-21** | `test_21_endpoints_regression` | Endpoint `/api/copilot/ask` và `/api/copilot/chat` giữ nguyên hoạt động và rào chắn an toàn | Integration | ✅ **PASS** |

---

## 2. MA TRẬN TEST CASES BƯỚC 01B (`tests/test_llm_gateway_step01b.py`)

| Mã Test | Tên Bài Kiểm Thử | Mục Tiêu & Kịch Bản Kiểm Thử | Cơ Chế Test | Kết Quả |
| :---: | :--- | :--- | :---: | :---: |
| **TC01B-01** | `test_01_imports` | Kiểm tra import đầy đủ LLMGateway, Providers, Exception classes kế thừa đúng chuẩn | Unit | ✅ **PASS** |
| **TC01B-02** | `test_02_select_provider_from_config` | Khởi tạo Gateway tự động ánh xạ đúng Provider (`gemini` $\rightarrow$ `GeminiProvider`, `openai` $\rightarrow$ `OpenAIProvider`) | Unit (Mock Env) | ✅ **PASS** |
| **TC01B-03** | `test_03_invalid_provider_rejected` | Khởi tạo Gateway với provider lạ $\rightarrow$ Từ chối với lỗi `LLM_INVALID_PROVIDER` | Unit | ✅ **PASS** |
| **TC01B-04** | `test_04_missing_or_placeholder_key_rejected` | Thiếu API key hoặc key chứa giá trị mẫu `your_...` $\rightarrow$ Báo lỗi `LLM_NOT_CONFIGURED` | Unit | ✅ **PASS** |
| **TC01B-05** | `test_05_valid_request_routed_correctly` | Prompt và system instruction backend được chuyển chính xác tới Provider | DI (FakeProvider) | ✅ **PASS** |
| **TC01B-06** | `test_06_response_normalized_format` | Response trả về chuẩn hóa đầy đủ `content`, `provider`, `model`, `usage`, `latency_ms` | DI (FakeProvider) | ✅ **PASS** |
| **TC01B-07** | `test_07_empty_response_handled` | Provider trả về rỗng $\rightarrow$ Ném lỗi `LLM_EMPTY_RESPONSE`, retryable=False | DI (FakeProvider) | ✅ **PASS** |
| **TC01B-08** | `test_08_timeout_handled` | Quá thời gian timeout $\rightarrow$ Bắt lỗi `LLM_TIMEOUT`, thực hiện retry trong giới hạn | DI (FakeProvider) | ✅ **PASS** |
| **TC01B-09** | `test_09_rate_limit_handled` | Bị giới hạn tần suất $\rightarrow$ Bắt lỗi `LLM_RATE_LIMIT`, thực hiện retry trong giới hạn | DI (FakeProvider) | ✅ **PASS** |
| **TC01B-10** | `test_10_auth_error_not_retried` | Sai API key (`LLM_AUTH_ERROR`) $\rightarrow$ Dừng ngay lập tức sau lần gọi đầu tiên, TUYỆT ĐỐI KHÔNG RETRY | DI (FakeProvider) | ✅ **PASS** |
| **TC01B-11** | `test_11_transient_error_bounded_retry` | Lỗi mạng tạm thời $\rightarrow$ Bounded retry có exponential backoff, thành công ở lần 2 | DI (FakeProvider) | ✅ **PASS** |
| **TC01B-12** | `test_12_fake_provider_only_via_di` | `FakeLLMProvider` chỉ được kích hoạt khi inject tường minh trong test, cấm tự chạy trong production | Unit | ✅ **PASS** |
| **TC01B-13** | `test_13_no_silent_fallback_to_mock_on_error` | Khi provider lỗi $\rightarrow$ Ném lỗi trung thực, cấm tự động chuyển sang mock data | DI (FakeProvider) | ✅ **PASS** |
| **TC01B-14** | `test_14_no_api_key_leaked_in_exceptions` | Không để lộ chuỗi API key trong exception message, repr hay logs | Unit | ✅ **PASS** |
| **TC01B-15** | `test_15_legacy_endpoint_intact` | Endpoint cũ `POST /api/copilot/ask` duy trì hoạt động 100%, không phá vỡ logic | Integration | ✅ **PASS** |
| **TC01B-16** | `test_16_experimental_endpoint_disabled_by_default` | Khi `ENABLE_EXPERIMENTAL_CHAT=false` $\rightarrow$ Endpoint `/api/copilot/chat` trả về 403 Forbidden | Integration | ✅ **PASS** |
| **TC01B-17** | `test_17_experimental_endpoint_refuses_clinical_claims` | Yêu cầu tư vấn điều trị/liều dùng $\rightarrow$ Trả về `BLOCKED`, `risk.requires_handoff=True`, không bịa Claim | Integration | ✅ **PASS** |
| **TC01B-18** | `test_18_experimental_endpoint_safe_greeting` | Yêu cầu chào hỏi khi bật cấu hình $\rightarrow$ Gọi Gateway an toàn, trả về `READY_TO_SEND` | DI + Integration | ✅ **PASS** |

---

## 2. MA TRẬN TEST CASES BƯỚC 01A (`tests/test_chat_schemas_step01a.py`)

| Mã Test | Tên Bài Kiểm Thử | Mục Tiêu & Kịch Bản Kiểm Thử | Kết Quả Thực Tế |
| :---: | :--- | :--- | :---: |
| **TC01A-01** | `test_1_chat_request_valid` | Khởi tạo `ChatRequest` hợp lệ đầy đủ message, product_id, session_id, request_id. | ✅ **PASS** |
| **TC01A-02** | `test_2_chat_request_vietnamese_unicode` | Kiểm tra khả năng hỗ trợ tiếng Việt Unicode có dấu, ký tự emoji (💊) qua vòng lặp Serialize/Deserialize. | ✅ **PASS** |
| **TC01A-03** | `test_3_chat_request_empty_message` | Tin nhắn rỗng (`""`) $\rightarrow$ Bắt buộc ném `ValidationError`. | ✅ **PASS** |
| **TC01A-04** | `test_4_chat_request_whitespace_only` | Tin nhắn chỉ chứa khoảng trắng (`"   \t\n "`) $\rightarrow$ Ném `ValidationError`. | ✅ **PASS** |
| **TC01A-05** | `test_5_chat_request_exceeds_max_length` | Tin nhắn dài 4.001 ký tự (vượt ngưỡng 4.000) $\rightarrow$ Ném `ValidationError`. | ✅ **PASS** |
| **TC01A-06** | `test_6_chat_request_invalid_types` | Sai kiểu dữ liệu (`message=None`) $\rightarrow$ Ném `ValidationError`. | ✅ **PASS** |
| **TC01A-07** | `test_7_chat_request_session_id_null` | `session_id=None` hoặc chuỗi rỗng $\rightarrow$ Tự động chuẩn hóa về `None` khi tạo hội thoại mới. | ✅ **PASS** |
| **TC01A-08** | `test_8_chat_request_product_id_optional` | `product_id` có thể nhận SKU hoặc nhận `None` mà không gây lỗi. | ✅ **PASS** |
| **TC01A-09** | `test_9_chat_intent_enum` | Xác thực các giá trị hợp lệ của `ChatIntent` Enum và từ chối giá trị ngoài danh mục. | ✅ **PASS** |
| **TC01A-10** | `test_10_chat_decision_enum` | Xác thực các giá trị hợp lệ của `ChatDecision` Enum và từ chối giá trị ngoài danh mục. | ✅ **PASS** |
| **TC01A-11** | `test_11_safety_result_escalation` | Khởi tạo `SafetyResult` với cờ `requires_handoff=True`, `risk_level=HIGH` cho ca nhạy cảm. | ✅ **PASS** |
| **TC01A-12** | `test_12_chat_response_normal` | Khởi tạo `ChatResponse` hợp lệ bình thường với đầy đủ sources trích dẫn và decision. | ✅ **PASS** |
| **TC01A-13** | `test_13_chat_response_insufficient_evidence` | Khi `decision=INSUFFICIENT_EVIDENCE` $\rightarrow$ Đảm bảo invariant `sources` luôn rỗng. | ✅ **PASS** |
| **TC01A-14** | `test_14_chat_response_handoff_without_ticket` | Trường hợp `HANDOFF_REQUIRED` nhưng chưa lưu DB $\rightarrow$ `ticket_id` bắt buộc là `null`. | ✅ **PASS** |
| **TC01A-15** | `test_15_json_serialization_roundtrip` | Kiểm tra tính bảo toàn dữ liệu khi xuất JSON (`model_dump_json`) và đọc lại (`model_validate_json`). | ✅ **PASS** |
| **TC01A-16** | `test_16_citation_info_partial_data` | Khởi tạo `CitationInfo` với dữ liệu không đầy đủ (các trường nullable). | ✅ **PASS** |
| **TC01A-17** | `test_17_legacy_copilot_request` | Kiểm tra schema `LegacyCopilotRequest` tương thích 100% với payload cũ (`query`, `sku`). | ✅ **PASS** |
| **TC01A-18** | `test_18_legacy_copilot_response_and_adapter` | Kiểm tra adapter `legacy_to_chat_response()` và `chat_response_to_legacy()` chuyển đổi hai chiều an toàn. | ✅ **PASS** |
| **TC01A-19** | `test_19_existing_api_endpoint_ask_still_works` | Gọi trực tiếp `POST /api/copilot/ask` qua TestClient $\rightarrow$ Trả về HTTP 200 đầy đủ trường. | ✅ **PASS** |
| **TC01A-20** | `test_20_regression_step00_1_sensitive_and_no_fallback` | Kiểm thử hồi quy logic Bước 00.1: Ca nhạy cảm trả về ESCALATION, SKU sai không fallback D3. | ✅ **PASS** |

---

## 3. MA TRẬN TEST CASES BƯỚC 00.1 (`tests/test_copilot_step00_1.py`)

| Mã Test | Tên Bài Kiểm Thử | Trọng Tâm Nghiệp Vụ | Kết Quả Thực Tế |
| :---: | :--- | :--- | :---: |
| **TC00.1-01** | `test_1_valid_product_and_claim` | Hỏi đúng SKU D3 $\rightarrow$ Trích dẫn đúng `CLM-D3-01`/`02`. | ✅ **PASS** |
| **TC00.1-02** | `test_2_nonexistent_product_no_fallback_to_d3` | Hỏi SKU không tồn tại $\rightarrow$ Không tự lấy Claim của D3. | ✅ **PASS** |
| **TC00.1-03** | `test_3_query_without_matching_claims` | Hỏi nội dung không có Claim $\rightarrow$ Trả về thiếu căn cứ, citations rỗng. | ✅ **PASS** |
| **TC00.1-04** | `test_4_expired_claims_excluded` | Claim hết hạn (`CLM-D3-03`) $\rightarrow$ Bị loại khỏi tư vấn thương mại. | ✅ **PASS** |
| **TC00.1-05** | `test_5_internal_expert_claims_excluded` | Claim nội bộ (`CLM-D3-04`) $\rightarrow$ Bị loại khỏi tư vấn thương mại. | ✅ **PASS** |
| **TC00.1-06** | `test_6_sensitive_escalation` | Thai kỳ, bệnh nền $\rightarrow$ Bắt buộc chuyển Dược sĩ (`handoff_required=True`). | ✅ **PASS** |
| **TC00.1-07** | `test_7_no_fake_ticket_notification` | Không thông báo "đã tạo ticket" khi chưa có hệ thống lưu thật. | ✅ **PASS** |
| **TC00.1-08** | `test_8_api_endpoint_compatibility` | Kiểm tra tương thích contract của `/api/copilot/ask`. | ✅ **PASS** |
| **TC00.1-09** | `test_9_no_cross_product_claim_leakage` | Hỏi Sắt trong D3 $\rightarrow$ Không rò rỉ Claim của Sắt. | ✅ **PASS** |
| **TC00.1-10** | `test_10_empty_citations_when_no_valid_source` | Khi không có nguồn hợp lệ $\rightarrow$ Mảng citations luôn rỗng. | ✅ **PASS** |

