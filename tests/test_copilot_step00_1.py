import pytest
from fastapi.testclient import TestClient
from server import app
from modules.sales_copilot import generate_copilot_response, check_sensitivity
from modules.claims_hub import get_active_claims, get_product_by_sku

@pytest.fixture
def client():
    return TestClient(app)

# ==============================================================================
# TEST 1: Hỏi đúng sản phẩm, có Claim hợp lệ -> trả thông tin đúng SKU và nguồn tương ứng
# ==============================================================================
def test_1_valid_product_and_claim():
    res = generate_copilot_response("Vitamin D3 có công dụng gì đối với xương?", sku="DION-D3-1000")
    assert res["type"] == "NORMAL"
    assert "CLM-D3-01" in res["citations"] or "CLM-D3-02" in res["citations"]
    assert any(c["sku"] == "DION-D3-1000" for c in res["source_claims"])
    assert "DION-D3-1000" in [c["sku"] for c in res["source_claims"]]
    assert "Vitamin D3" in res["content"]
    assert len(res["citations"]) > 0

# ==============================================================================
# TEST 2: Hỏi sản phẩm không tồn tại -> KHÔNG tự lấy Claim của D3
# ==============================================================================
def test_2_nonexistent_product_no_fallback_to_d3():
    res = generate_copilot_response("Công dụng của sản phẩm này là gì?", sku="NON_EXISTENT_SKU_9999")
    assert res["type"] == "INSUFFICIENT_EVIDENCE"
    assert res["citations"] == []
    assert res["source_claims"] == []
    assert "CLM-D3-01" not in res["citations"]
    assert "DION-D3-1000" not in str(res["source_claims"])
    assert "không tìm thấy thông tin" in res["content"].lower()

# ==============================================================================
# TEST 3: Hỏi nội dung không có Claim phù hợp -> trả thiếu căn cứ
# ==============================================================================
def test_3_query_without_matching_claims():
    res = generate_copilot_response("Sản phẩm có giúp cải thiện trí nhớ không?", sku="DION-D3-1000")
    assert res["type"] == "INSUFFICIENT_EVIDENCE"
    assert res["citations"] == []
    assert res["source_claims"] == []
    assert "chưa có đủ thông tin" in res["content"].lower()

# ==============================================================================
# TEST 4: Claim hết hạn -> KHÔNG sử dụng trong tư vấn thương mại
# ==============================================================================
def test_4_expired_claims_excluded():
    # CLM-D3-03 có effective_until: 2025-12-31 và status: EXPIRED
    active_claims = get_active_claims("DION-D3-1000", zone="COMMERCIAL_APPROVED")
    active_claim_ids = [c["claim_id"] for c in active_claims]
    assert "CLM-D3-03" not in active_claim_ids
    
    # Hỏi về tăng sức đề kháng (nội dung của CLM-D3-03)
    res = generate_copilot_response("Vitamin D3 có tăng sức đề kháng và hệ miễn dịch không?", sku="DION-D3-1000")
    assert "CLM-D3-03" not in res["citations"]

# ==============================================================================
# TEST 5: Claim thuộc vùng nội bộ -> KHÔNG dùng để trả lời thương mại
# ==============================================================================
def test_5_internal_expert_claims_excluded():
    # CLM-D3-04 có zone: INTERNAL_EXPERT
    active_claims = get_active_claims("DION-D3-1000", zone="COMMERCIAL_APPROVED")
    active_claim_ids = [c["claim_id"] for c in active_claims]
    assert "CLM-D3-04" not in active_claim_ids
    
    res = generate_copilot_response("Cơ chế phân tử Calbindin-D9k của D3 là gì?", sku="DION-D3-1000")
    assert "CLM-D3-04" not in res["citations"]

# ==============================================================================
# TEST 6: Hỏi về thai kỳ và thuốc điều trị -> trả yêu cầu chuyển chuyên gia
# ==============================================================================
def test_6_sensitive_escalation():
    queries = [
        "Khách hàng mang thai 3 tháng có uống D3 được không?",
        "Bệnh nhân đang uống thuốc tim mạch có dùng kèm sắt được không?",
        "Phụ nữ cho con bú có dùng được không?",
        "Bệnh nhân suy thận nặng dùng canxi thế nào?"
    ]
    for q in queries:
        res = generate_copilot_response(q, sku="ALL")
        assert res["type"] == "ESCALATION", f"Failed on query: {q}"
        assert res["handoff_required"] is True
        assert res["citations"] == []
        assert "dược sĩ" in res["content"].lower() or "chuyên môn" in res["content"].lower()

# ==============================================================================
# TEST 7: Không có Ticket Service -> KHÔNG thông báo đã tạo Ticket thành công
# ==============================================================================
def test_7_no_fake_ticket_notification():
    res = generate_copilot_response("Phụ nữ mang thai uống sắt được không?", sku="ALL")
    assert res["type"] == "ESCALATION"
    content_lower = res["content"].lower()
    assert "hệ thống đã tự động tạo ticket" not in content_lower
    assert "đã tạo ticket" not in content_lower
    assert "ticket_id" not in res

# ==============================================================================
# TEST 8: Endpoint /api/copilot/ask vẫn hoạt động và tương thích frontend
# ==============================================================================
def test_8_api_endpoint_compatibility(client):
    payload = {"query": "Vitamin D3 có công dụng gì với xương?", "sku": "DION-D3-1000"}
    response = client.post("/api/copilot/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Kiểm tra đầy đủ các trường mà frontend yêu cầu
    expected_keys = {"type", "badge", "content", "citations", "source_claims"}
    assert expected_keys.issubset(data.keys())
    assert isinstance(data["citations"], list)
    assert isinstance(data["source_claims"], list)
    assert len(data["content"]) > 0

# ==============================================================================
# TEST 9: Câu hỏi về sản phẩm A KHÔNG nhận thông tin hoặc nguồn của sản phẩm B
# ==============================================================================
def test_9_no_cross_product_claim_leakage():
    # Hỏi về sắt nhưng lại truyền sku của D3 -> không được trả về Claim của sắt
    res = generate_copilot_response("Viên sắt Fero-Plus có gây táo bón không?", sku="DION-D3-1000")
    # Vì SKU D3 không có claim nào về sắt, phải trả về INSUFFICIENT_EVIDENCE
    assert res["type"] == "INSUFFICIENT_EVIDENCE"
    assert "CLM-FE-01" not in res["citations"]
    assert "CLM-FE-02" not in res["citations"]
    assert res["citations"] == []

    # Hỏi về D3 nhưng truyền sku của Cal-Mom -> không được trả về Claim của D3
    res2 = generate_copilot_response("Vitamin D3 1000IU dạng nhỏ giọt có tác dụng gì?", sku="DION-CAL-MOM")
    assert "CLM-D3-01" not in res2.get("citations", [])
    assert "CLM-D3-02" not in res2.get("citations", [])

# ==============================================================================
# TEST 10: Khi không có nguồn hợp lệ, mảng citations phải rỗng
# ==============================================================================
def test_10_empty_citations_when_no_valid_source():
    # Câu hỏi không khớp
    res_no_match = generate_copilot_response("Sản phẩm có dùng để làm đẹp da không?", sku="DION-D3-1000")
    assert res_no_match["citations"] == []
    assert res_no_match["source_claims"] == []

    # Câu hỏi nhạy cảm
    res_sensitive = generate_copilot_response("Mang thai tháng thứ 2 uống được không?", sku="DION-D3-1000")
    assert res_sensitive["citations"] == []
    assert res_sensitive["source_claims"] == []

    # SKU không tồn tại
    res_no_sku = generate_copilot_response("Công dụng là gì?", sku="INVALID_SKU")
    assert res_no_sku["citations"] == []
    assert res_no_sku["source_claims"] == []
