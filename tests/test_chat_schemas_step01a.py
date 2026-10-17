import json
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from server import app
from modules.chat.enums import (
    ChatIntent,
    ChatDecision,
    RiskLevel,
    TicketStatus,
    ChatRole
)
from modules.chat.schemas import (
    ChatRequest,
    ChatMessage,
    CitationInfo,
    IntentResult,
    SafetyResult,
    TicketData,
    ChatAction,
    ChatResponse,
    LegacyCopilotRequest,
    LegacyCopilotResponse,
    ChatErrorResponse,
    legacy_to_chat_response,
    chat_response_to_legacy
)

@pytest.fixture
def client():
    return TestClient(app)

# ==============================================================================
# TEST 1: ChatRequest hợp lệ
# ==============================================================================
def test_1_chat_request_valid():
    req = ChatRequest(
        message="Vitamin D3 có công dụng gì đối với xương?",
        product_id="DION-D3-1000",
        session_id="session-123",
        request_id="req-999"
    )
    assert req.message == "Vitamin D3 có công dụng gì đối với xương?"
    assert req.product_id == "DION-D3-1000"
    assert req.session_id == "session-123"
    assert req.request_id == "req-999"

# ==============================================================================
# TEST 2: Tin nhắn tiếng Việt Unicode đầy đủ dấu và ký tự đặc biệt
# ==============================================================================
def test_2_chat_request_vietnamese_unicode():
    msg = "Phụ nữ chuẩn bị mang thai có nên bổ sung Canxi Tảo Đỏ Cal-Mom & Sắt Fero-Plus không ạ? 💊"
    req = ChatRequest(message=msg)
    assert req.message == msg
    # Serialize to JSON and verify unicode preservation
    json_data = req.model_dump_json()
    parsed = ChatRequest.model_validate_json(json_data)
    assert parsed.message == msg

# ==============================================================================
# TEST 3: Message rỗng -> Phải raise ValidationError
# ==============================================================================
def test_3_chat_request_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="")

# ==============================================================================
# TEST 4: Message chỉ có khoảng trắng -> Phải raise ValidationError
# ==============================================================================
def test_4_chat_request_whitespace_only():
    with pytest.raises(ValidationError):
        ChatRequest(message="    \t \n   ")

# ==============================================================================
# TEST 5: Message vượt giới hạn độ dài (max_length = 4000)
# ==============================================================================
def test_5_chat_request_exceeds_max_length():
    too_long = "a" * 4001
    with pytest.raises(ValidationError):
        ChatRequest(message=too_long)

# ==============================================================================
# TEST 6: Sai kiểu dữ liệu đầu vào
# ==============================================================================
def test_6_chat_request_invalid_types():
    with pytest.raises(ValidationError):
        # Truyền message không phải chuỗi hoặc không thể chuyển đổi
        ChatRequest.model_validate({"message": None})

# ==============================================================================
# TEST 7: Session ID null khi tạo hội thoại mới
# ==============================================================================
def test_7_chat_request_session_id_null():
    req = ChatRequest(message="Khởi tạo phiên chat", session_id=None)
    assert req.session_id is None

    # Chuỗi rỗng cũng được chuẩn hóa thành None
    req_empty_str = ChatRequest(message="Khởi tạo phiên chat", session_id="   ")
    assert req_empty_str.session_id is None

# ==============================================================================
# TEST 8: Product ID có hoặc không có
# ==============================================================================
def test_8_chat_request_product_id_optional():
    req_with_sku = ChatRequest(message="Hỏi sản phẩm", product_id="DION-CAL-MOM")
    assert req_with_sku.product_id == "DION-CAL-MOM"

    req_without_sku = ChatRequest(message="Hỏi chung toàn bộ danh mục")
    assert req_without_sku.product_id is None

# ==============================================================================
# TEST 9: Enum Intent hợp lệ và không hợp lệ
# ==============================================================================
def test_9_chat_intent_enum():
    assert ChatIntent.PRODUCT_INFO == "PRODUCT_INFO"
    assert ChatIntent.MEDICAL_RISK == "MEDICAL_RISK"
    assert ChatIntent.PROHIBITED_GENERATION == "PROHIBITED_GENERATION"

    # Hợp lệ
    intent_res = IntentResult(primary_intent=ChatIntent.PRODUCT_INFO)
    assert intent_res.primary_intent == ChatIntent.PRODUCT_INFO

    # Không hợp lệ -> ValidationError
    with pytest.raises(ValidationError):
        IntentResult(primary_intent="INVALID_INTENT_XYZ")

# ==============================================================================
# TEST 10: Enum ChatDecision hợp lệ và không hợp lệ
# ==============================================================================
def test_10_chat_decision_enum():
    assert ChatDecision.DRAFT_FOR_APPROVAL == "DRAFT_FOR_APPROVAL"
    assert ChatDecision.INSUFFICIENT_EVIDENCE == "INSUFFICIENT_EVIDENCE"
    assert ChatDecision.HANDOFF_REQUIRED == "HANDOFF_REQUIRED"

    resp = ChatResponse(
        answer="Nội dung kiểm tra",
        decision=ChatDecision.DRAFT_FOR_APPROVAL
    )
    assert resp.decision == ChatDecision.DRAFT_FOR_APPROVAL

    with pytest.raises(ValidationError):
        ChatResponse(answer="Lỗi", decision="NON_EXISTENT_DECISION")

# ==============================================================================
# TEST 11: SafetyResult với trường hợp cần chuyển chuyên gia
# ==============================================================================
def test_11_safety_result_escalation():
    safety = SafetyResult(
        risk_level=RiskLevel.HIGH,
        risk_flags=["PREGNANCY_SENSITIVE", "TRIMESTER_1"],
        requires_handoff=True,
        reason="Khách hàng mang thai 3 tháng đầu hỏi dùng Vitamin D3",
        recommended_department="DƯỢC VỤ CHUYÊN MÔN"
    )
    assert safety.requires_handoff is True
    assert safety.risk_level == RiskLevel.HIGH
    assert "PREGNANCY_SENSITIVE" in safety.risk_flags

# ==============================================================================
# TEST 12: ChatResponse bình thường
# ==============================================================================
def test_12_chat_response_normal():
    resp = ChatResponse(
        schema_version="1.0",
        session_id="session-001",
        message_id="msg-001",
        trace_id="tr-001",
        intent=ChatIntent.PRODUCT_INFO,
        decision=ChatDecision.DRAFT_FOR_APPROVAL,
        answer="Vitamin D3 hỗ trợ hấp thu Canxi.",
        product_ids=["DION-D3-1000"],
        sources=[CitationInfo(claim_id="CLM-D3-01", document_title="Hồ sơ công bố 4521/2025")],
        risk=SafetyResult(risk_level=RiskLevel.LOW),
        actions=[ChatAction(type="COPY_ANSWER", label="Sao chép nội dung", requires_approval=False)],
        ticket_id=None
    )
    assert resp.decision == ChatDecision.DRAFT_FOR_APPROVAL
    assert len(resp.sources) == 1
    assert resp.sources[0].claim_id == "CLM-D3-01"
    assert resp.ticket_id is None

# ==============================================================================
# TEST 13: ChatResponse thiếu căn cứ có sources rỗng
# ==============================================================================
def test_13_chat_response_insufficient_evidence():
    resp = ChatResponse(
        decision=ChatDecision.INSUFFICIENT_EVIDENCE,
        answer="Hiện tại hệ thống chưa có đủ thông tin sản phẩm được xác minh.",
        sources=[]
    )
    assert resp.decision == ChatDecision.INSUFFICIENT_EVIDENCE
    assert resp.sources == []

    # Invariant check: nếu gắn nguồn rỗng/giả mạo mà decision=INSUFFICIENT_EVIDENCE -> sources tự làm rỗng
    resp_with_unverified = ChatResponse(
        decision=ChatDecision.INSUFFICIENT_EVIDENCE,
        answer="Chưa đủ căn cứ",
        sources=[CitationInfo()]  # CitationInfo rỗng không có claim_id
    )
    assert resp_with_unverified.sources == []

# ==============================================================================
# TEST 14: ChatResponse cần chuyển chuyên gia nhưng chưa có Ticket
# ==============================================================================
def test_14_chat_response_handoff_without_ticket():
    resp = ChatResponse(
        decision=ChatDecision.HANDOFF_REQUIRED,
        answer="Trường hợp này cần được dược sĩ xem xét.",
        risk=SafetyResult(requires_handoff=True, risk_level=RiskLevel.HIGH),
        ticket_id=None  # Chưa lưu vào DB -> ticket_id bắt buộc là null
    )
    assert resp.decision == ChatDecision.HANDOFF_REQUIRED
    assert resp.risk.requires_handoff is True
    assert resp.ticket_id is None

# ==============================================================================
# TEST 15: Serialization / Deserialization JSON
# ==============================================================================
def test_15_json_serialization_roundtrip():
    original = ChatResponse(
        schema_version="1.0",
        session_id="sess-xyz",
        intent=ChatIntent.USAGE_INFORMATION,
        decision=ChatDecision.DRAFT_FOR_APPROVAL,
        answer="Uống vào buổi sáng sau bữa ăn.",
        product_ids=["DION-D3-1000"],
        sources=[CitationInfo(claim_id="CLM-D3-01", page=2)],
        risk=SafetyResult(risk_level=RiskLevel.LOW, requires_handoff=False)
    )
    json_str = original.model_dump_json()
    data_dict = json.loads(json_str)

    assert data_dict["schema_version"] == "1.0"
    assert data_dict["intent"] == "USAGE_INFORMATION"
    assert data_dict["decision"] == "DRAFT_FOR_APPROVAL"
    assert data_dict["sources"][0]["page"] == 2

    reconstructed = ChatResponse.model_validate_json(json_str)
    assert reconstructed.session_id == original.session_id
    assert reconstructed.answer == original.answer
    assert reconstructed.sources[0].claim_id == "CLM-D3-01"

# ==============================================================================
# TEST 16: CitationInfo có dữ liệu không đầy đủ (Nullable fields)
# ==============================================================================
def test_16_citation_info_partial_data():
    # Chỉ có claim_id, các trường khác null
    cit = CitationInfo(claim_id="CLM-CAL-01")
    assert cit.claim_id == "CLM-CAL-01"
    assert cit.document_title is None
    assert cit.page is None
    assert cit.source_url is None

    # Khởi tạo rỗng
    cit_empty = CitationInfo()
    assert cit_empty.claim_id is None

# ==============================================================================
# TEST 17: LegacyCopilotRequest tương thích
# ==============================================================================
def test_17_legacy_copilot_request():
    req = LegacyCopilotRequest(query="Vitamin D3 dùng thế nào?", sku="DION-D3-1000")
    assert req.query == "Vitamin D3 dùng thế nào?"
    assert req.sku == "DION-D3-1000"

    req_default_sku = LegacyCopilotRequest(query="Hỏi chung")
    assert req_default_sku.sku == "ALL"

# ==============================================================================
# TEST 18: LegacyCopilotResponse tương thích và Adapter chuyển đổi
# ==============================================================================
def test_18_legacy_copilot_response_and_adapter():
    legacy = LegacyCopilotResponse(
        type="NORMAL",
        badge="✅ ĐÃ XÁC THỰC",
        content="Nội dung tư vấn D3",
        citations=["CLM-D3-01"],
        source_claims=[{"sku": "DION-D3-1000", "claim_id": "CLM-D3-01", "evidence": "Hồ sơ số 4521"}],
        handoff_required=False
    )
    assert legacy.type == "NORMAL"
    assert legacy.citations == ["CLM-D3-01"]
    assert legacy.handoff_required is False

    # Chuyển từ Legacy sang ChatResponse mới
    new_resp = legacy_to_chat_response(legacy, session_id="sess-legacy-1")
    assert new_resp.session_id == "sess-legacy-1"
    assert new_resp.decision == ChatDecision.DRAFT_FOR_APPROVAL
    assert new_resp.sources[0].claim_id == "CLM-D3-01"
    assert new_resp.product_ids == ["DION-D3-1000"]

    # Chuyển ngược từ ChatResponse mới sang Legacy
    back_to_legacy = chat_response_to_legacy(new_resp)
    assert back_to_legacy.type == "NORMAL"
    assert "CLM-D3-01" in back_to_legacy.citations
    assert back_to_legacy.handoff_required is False

# ==============================================================================
# TEST 19: Endpoint /api/copilot/ask vẫn hoạt động bình thường
# ==============================================================================
def test_19_existing_api_endpoint_ask_still_works(client):
    payload = {"query": "Vitamin D3 có công dụng gì với xương?", "sku": "DION-D3-1000"}
    res = client.post("/api/copilot/ask", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "type" in data
    assert "badge" in data
    assert "content" in data
    assert "citations" in data
    assert "source_claims" in data
    assert "handoff_required" in data
    assert data["type"] == "NORMAL"
    assert len(data["citations"]) > 0

# ==============================================================================
# TEST 20: Các test Bước 00.1 vẫn PASS nguyên vẹn (Regression Test)
# ==============================================================================
def test_20_regression_step00_1_sensitive_and_no_fallback():
    from modules.sales_copilot import generate_copilot_response
    
    # Ca nhạy cảm
    res_sens = generate_copilot_response("Mang thai 3 tháng uống D3 được không?")
    assert res_sens["type"] == "ESCALATION"
    assert res_sens["handoff_required"] is True
    assert "tạo ticket" not in res_sens["content"].lower()

    # SKU không tồn tại -> Không lấy D3
    res_nosku = generate_copilot_response("Công dụng?", sku="SKU_INVALID_RANDOM")
    assert res_nosku["type"] == "INSUFFICIENT_EVIDENCE"
    assert res_nosku["citations"] == []
