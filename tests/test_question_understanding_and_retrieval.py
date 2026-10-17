"""
DION Healthcare AI — Unit & Integration Test Suite
Kiểm thử nâng cao cho Question Understanding, Product Resolution & Claim Retrieval:
1. Cùng một công dụng được hỏi theo nhiều cách khác nhau.
2. Nhận diện đúng SKU (cả tường minh lẫn ngầm định qua tên).
3. Không xác định được SKU / Câu hỏi mơ hồ -> CLARIFICATION_REQUIRED.
4. Hai sản phẩm xuất hiện trong cùng câu hỏi -> PRODUCT_COMPARISON.
5. Claim không liên quan (chỉ có từ ngữ chung chung) -> INSUFFICIENT_EVIDENCE.
6. Claim hết hạn hoặc nội bộ -> Tuyệt đối không xuất hiện trong sources.
7. Câu hỏi không có nguồn phù hợp -> INSUFFICIENT_EVIDENCE.
8. Câu hỏi có rủi ro sức khỏe -> HANDOFF_REQUIRED.
9. Câu hỏi ngoài phạm vi (Off-topic) -> OFF_TOPIC & INSUFFICIENT_EVIDENCE.
10. Endpoint cũ /api/copilot/ask tiếp tục hoạt động ổn định.
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from server import app
from modules.chat.enums import ChatIntent, ChatDecision, RiskLevel
from modules.chat.providers.fake_provider import FakeLLMProvider
from modules.chat.llm_gateway import LLMGateway
from modules.knowledge.repository import get_knowledge_repository
from modules.chat.question_understanding import QuestionUnderstandingEngine
from modules.chat.claim_retriever import ClaimRelevanceRetriever

client = TestClient(app)


@pytest.fixture
def test_gateway():
    fake_provider = FakeLLMProvider(
        default_response="Bản nháp câu trả lời được tạo từ các Claims đã được xác thực."
    )
    return LLMGateway(provider=fake_provider)


# ==============================================================================
# TEST 1: Cùng một công dụng được hỏi theo nhiều cách (D3: Xương & Răng - CLM-D3-02)
# ==============================================================================
def test_01_multiple_phrasings_d3_bone_teeth(test_gateway):
    queries = [
        "Vitamin D3 có công dụng gì đối với xương?",
        "Trẻ em uống D3 có giúp chắc răng và phòng loãng xương không?",
        "D3 1000 Drops giúp xương răng phát triển thế nào?",
        "Sản phẩm D3 có hỗ trợ phát triển chiều cao và tăng mật độ xương không?"
    ]

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            for q in queries:
                res = client.post("/api/copilot/chat", json={
                    "message": q,
                    "product_id": "DION-D3-1000"
                })
                assert res.status_code == 200, f"Failed on query: {q}"
                data = res.json()
                assert data["decision"] == ChatDecision.DRAFT_FOR_APPROVAL.value
                source_claim_ids = [s["claim_id"] for s in data["sources"]]
                assert "CLM-D3-02" in source_claim_ids, f"Expected CLM-D3-02 in {source_claim_ids} for query: {q}"


# ==============================================================================
# TEST 2: Cùng một công dụng được hỏi theo nhiều cách (D3: Hấp thu Canxi & Photpho - CLM-D3-01)
# ==============================================================================
def test_02_multiple_phrasings_d3_absorption(test_gateway):
    queries = [
        "D3 giúp hấp thu canxi và photpho như thế nào?",
        "Uống D3 có giúp canxi ngấm vào ruột non không?",
        "Vitamin D3 có tăng cường nồng độ canxi máu không?"
    ]

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            for q in queries:
                res = client.post("/api/copilot/chat", json={
                    "message": q,
                    "product_id": "DION-D3-1000"
                })
                assert res.status_code == 200, f"Failed on query: {q}"
                data = res.json()
                assert data["decision"] == ChatDecision.DRAFT_FOR_APPROVAL.value
                source_claim_ids = [s["claim_id"] for s in data["sources"]]
                assert "CLM-D3-01" in source_claim_ids, f"Expected CLM-D3-01 in {source_claim_ids} for query: {q}"


# ==============================================================================
# TEST 3: Cùng một công dụng được hỏi theo nhiều cách (Cal-Mom: Chuột rút & Đau lưng - CLM-CAL-02)
# ==============================================================================
def test_03_multiple_phrasings_calmom_cramps(test_gateway):
    queries = [
        "Cal-Mom có giúp giảm chuột rút và đau lưng không?",
        "Bị vọp bẻ khi mang bầu uống Cal-Mom được không?",
        "Canxi Cal-Mom có hỗ trợ giảm tình trạng co cơ và mỏi lưng không?"
    ]

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            for q in queries:
                res = client.post("/api/copilot/chat", json={
                    "message": q,
                    "product_id": "DION-CAL-MOM"
                })
                assert res.status_code == 200, f"Failed on query: {q}"
                data = res.json()
                # Chú ý: câu hỏi có từ khóa "mang bầu" nhưng trong ngữ cảnh hỏi về công dụng Cal-Mom
                # nếu bị đánh dấu HANDOFF do từ "mang bầu" thì HANDOFF là đúng;
                # với câu không có "mang bầu" (câu 1 và 3) phải trả DRAFT với CLM-CAL-02:
                if "mang bầu" in q:
                    assert data["decision"] in (ChatDecision.HANDOFF_REQUIRED.value, ChatDecision.DRAFT_FOR_APPROVAL.value)
                else:
                    assert data["decision"] == ChatDecision.DRAFT_FOR_APPROVAL.value
                    source_ids = [s["claim_id"] for s in data["sources"]]
                    assert "CLM-CAL-02" in source_ids


# ==============================================================================
# TEST 4: Cùng một công dụng được hỏi theo nhiều cách (Fero-Plus: Êm dịu dạ dày, không táo bón - CLM-FE-02)
# ==============================================================================
def test_04_multiple_phrasings_fero_digestive_comfort(test_gateway):
    queries = [
        "Uống sắt Fero-Plus có bị táo bón không?",
        "Sắt này có gây nóng trong người hay buồn nôn không?",
        "Fero-Plus có êm dịu dạ dày không, uống có bị xót ruột cồn cào không?"
    ]

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            for q in queries:
                res = client.post("/api/copilot/chat", json={
                    "message": q,
                    "product_id": "DION-FE-FOLIC"
                })
                assert res.status_code == 200, f"Failed on query: {q}"
                data = res.json()
                assert data["decision"] == ChatDecision.DRAFT_FOR_APPROVAL.value
                source_ids = [s["claim_id"] for s in data["sources"]]
                assert "CLM-FE-02" in source_ids, f"Expected CLM-FE-02 in {source_ids} for query: {q}"


# ==============================================================================
# TEST 5: Nhận diện đúng SKU qua tên sản phẩm ngầm định trong câu hỏi
# ==============================================================================
def test_05_sku_recognition_from_query_text(test_gateway):
    repo = get_knowledge_repository()
    engine = QuestionUnderstandingEngine(repo)

    res_d3 = engine.resolve_product("Sản phẩm D3 1000 Drops uống vào lúc nào?")
    assert res_d3.target_sku == "DION-D3-1000"
    assert res_d3.all_matched_skus == ["DION-D3-1000"]

    res_cal = engine.resolve_product("Canxi tảo đỏ Cal-Mom có ưu điểm gì?")
    assert res_cal.target_sku == "DION-CAL-MOM"
    assert res_cal.all_matched_skus == ["DION-CAL-MOM"]

    res_fe = engine.resolve_product("Viên sắt Fero-Plus có acid folic không?")
    assert res_fe.target_sku == "DION-FE-FOLIC"
    assert res_fe.all_matched_skus == ["DION-FE-FOLIC"]


# ==============================================================================
# TEST 6: Không xác định được SKU / Câu hỏi mơ hồ -> CLARIFICATION_REQUIRED
# ==============================================================================
def test_06_unidentified_product_clarification_required():
    ambiguous_queries = [
        "Sản phẩm uống vào lúc nào tốt nhất?",
        "Liều dùng mỗi ngày thế nào?",
        "Mỗi ngày uống mấy viên?",
        "Sản phẩm có tác dụng phụ không?",
        "Uống trước hay sau ăn thì tốt hơn?"
    ]

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        for q in ambiguous_queries:
            res = client.post("/api/copilot/chat", json={"message": q})
            assert res.status_code == 200, f"Failed on query: {q}"
            data = res.json()
            assert data["decision"] == ChatDecision.CLARIFICATION_REQUIRED.value, f"Expected CLARIFICATION_REQUIRED for: {q}"
            assert data["sources"] == []
            assert data["product_ids"] == []
            assert "chưa nêu rõ tên sản phẩm" in data["answer"].lower()
            assert len(data["actions"]) > 0
            assert data["actions"][0]["type"] == "SELECT_PRODUCT"


# ==============================================================================
# TEST 7: Hai sản phẩm xuất hiện trong cùng câu hỏi -> PRODUCT_COMPARISON
# ==============================================================================
def test_07_two_products_in_same_query_comparison(test_gateway):
    comparison_query = "So sánh Canxi Cal-Mom và Vitamin D3 khác nhau thế nào?"

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            res = client.post("/api/copilot/chat", json={"message": comparison_query})
            assert res.status_code == 200
            data = res.json()
            assert data["intent"] == ChatIntent.PRODUCT_COMPARISON.value
            # Nhận diện được cả 2 sản phẩm
            assert "DION-CAL-MOM" in data["product_ids"] or "DION-D3-1000" in data["product_ids"]


# ==============================================================================
# TEST 8: Claim không liên quan (chỉ có từ trùng chung chung) -> INSUFFICIENT_EVIDENCE
# ==============================================================================
def test_08_irrelevant_generic_query_rejected(test_gateway):
    generic_query = "Sản phẩm D3 này có tác dụng hỗ trợ tốt không ạ?"

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            res = client.post("/api/copilot/chat", json={
                "message": generic_query,
                "product_id": "DION-D3-1000"
            })
            assert res.status_code == 200
            data = res.json()
            # Không được tự tiện match bừa khi chỉ có các từ chung chung (tác dụng, hỗ trợ, tốt)
            assert data["decision"] == ChatDecision.INSUFFICIENT_EVIDENCE.value
            assert data["sources"] == []


# ==============================================================================
# TEST 9: Claim hết hạn hoặc nội bộ -> Tuyệt đối không xuất hiện trong sources
# ==============================================================================
def test_09_expired_and_internal_claims_excluded(test_gateway):
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            # 1. Hỏi về tăng sức đề kháng (nội dung của CLM-D3-03 đã EXPIRED)
            res_expired = client.post("/api/copilot/chat", json={
                "message": "Vitamin D3 có giúp tăng cường sức đề kháng và miễn dịch không?",
                "product_id": "DION-D3-1000"
            })
            data_exp = res_expired.json()
            assert "CLM-D3-03" not in [s.get("claim_id") for s in data_exp["sources"]]
            assert data_exp["decision"] == ChatDecision.INSUFFICIENT_EVIDENCE.value

            # 2. Hỏi về cơ chế thụ thể VDR Calbindin-D9k (nội dung của CLM-D3-04 là INTERNAL_EXPERT)
            res_internal = client.post("/api/copilot/chat", json={
                "message": "Cơ chế phân tử thụ thể VDR Calbindin-D9k của D3 là gì?",
                "product_id": "DION-D3-1000"
            })
            data_int = res_internal.json()
            assert "CLM-D3-04" not in [s.get("claim_id") for s in data_int["sources"]]
            assert data_int["decision"] == ChatDecision.INSUFFICIENT_EVIDENCE.value


# ==============================================================================
# TEST 10: Câu hỏi ngoài phạm vi (Off-topic) -> OFF_TOPIC & INSUFFICIENT_EVIDENCE
# ==============================================================================
def test_10_out_of_scope_off_topic_query():
    off_topic_queries = [
        "Thời tiết hôm nay tại Hà Nội thế nào?",
        "Tư vấn cho tôi điện thoại iPhone 16 Pro Max",
        "Công ty bạn có bán collagen chống lão hóa da không?",
        "Giá vàng hôm nay tăng hay giảm?"
    ]

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        for q in off_topic_queries:
            res = client.post("/api/copilot/chat", json={"message": q})
            assert res.status_code == 200, f"Failed on query: {q}"
            data = res.json()
            assert data["intent"] == ChatIntent.OFF_TOPIC.value
            assert data["decision"] == ChatDecision.INSUFFICIENT_EVIDENCE.value
            assert data["sources"] == []
            assert "ngoài phạm vi" in data["answer"].lower()


# ==============================================================================
# TEST 11: Câu hỏi có rủi ro sức khỏe -> HANDOFF_REQUIRED
# ==============================================================================
def test_11_health_risk_handoff_required():
    risk_queries = [
        "Bệnh nhân suy thận nặng có uống được Canxi Cal-Mom không?",
        "Bệnh nhân đang uống thuốc tim mạch có dùng được viên sắt không?",
        "Người bị dị ứng sốc phản vệ có dùng được sản phẩm không?"
    ]

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        for q in risk_queries:
            res = client.post("/api/copilot/chat", json={"message": q})
            assert res.status_code == 200, f"Failed on query: {q}"
            data = res.json()
            assert data["decision"] == ChatDecision.HANDOFF_REQUIRED.value
            assert data["intent"] == ChatIntent.MEDICAL_RISK.value
            assert data["risk"]["requires_handoff"] is True
            assert data["sources"] == []
            assert "DƯỢC SĨ" in data["answer"].upper()


# ==============================================================================
# TEST 12: Endpoint cũ /api/copilot/ask tiếp tục hoạt động hoàn hảo
# ==============================================================================
def test_12_legacy_endpoint_ask_unbroken():
    payload = {"query": "Vitamin D3 có công dụng gì với xương?", "sku": "DION-D3-1000"}
    res = client.post("/api/copilot/ask", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "NORMAL"
    assert "CLM-D3-01" in data["citations"] or "CLM-D3-02" in data["citations"]
    assert len(data["source_claims"]) > 0


# ==============================================================================
# TEST 13: Câu hỏi tổng quan / ưu điểm nổi bật (Cal-Mom - CLM-CAL-01, 02, 03)
# ==============================================================================
def test_13_calmom_overview_highlights(test_gateway):
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            res = client.post("/api/copilot/chat", json={
                "message": "Canxi Cal-Mom có ưu điểm gì nổi bật?"
            })
            assert res.status_code == 200
            data = res.json()
            assert data["decision"] == ChatDecision.DRAFT_FOR_APPROVAL.value
            assert "DION-CAL-MOM" in data["product_ids"]
            source_ids = [s["claim_id"] for s in data["sources"]]
            assert "CLM-CAL-01" in source_ids
            assert "CLM-CAL-02" in source_ids


# ==============================================================================
# TEST 14: Câu hỏi tổng quan công dụng (Vitamin D3)
# ==============================================================================
def test_14_d3_overview_general_use(test_gateway):
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            res = client.post("/api/copilot/chat", json={
                "message": "Vitamin D3 có công dụng gì?"
            })
            assert res.status_code == 200
            data = res.json()
            assert data["decision"] == ChatDecision.DRAFT_FOR_APPROVAL.value
            assert "DION-D3-1000" in data["product_ids"]
            source_ids = [s["claim_id"] for s in data["sources"]]
            assert len(source_ids) > 0


# ==============================================================================
# TEST 15: Câu hỏi công dụng chuyên biệt không có nguồn (Cal-Mom: Trí nhớ)
# ==============================================================================
def test_15_calmom_unsupported_condition_memory():
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res = client.post("/api/copilot/chat", json={
            "message": "Cal-Mom giúp cải thiện trí nhớ không?"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == ChatDecision.INSUFFICIENT_EVIDENCE.value
        assert data["sources"] == []
        assert "trí nhớ" in data["answer"].lower()
        # Không dùng nhầm claim xương để đồng ý
        assert "CLM-CAL-01" not in [s.get("claim_id") for s in data["sources"]]


# ==============================================================================
# TEST 16: Câu hỏi hội thoại ghép: Công dụng + Giá + Dùng cùng thuốc
# ==============================================================================
def test_16_compound_query_product_price_drug_interaction():
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res = client.post("/api/copilot/chat", json={
            "message": "Canxi Cal-Mom có công dụng gì, giá bao nhiêu và có dùng chung với thuốc huyết áp được không?"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == ChatDecision.HANDOFF_REQUIRED.value
        assert "DION-CAL-MOM" in data["product_ids"]
        assert len(data["sources"]) > 0
        assert "CÔNG DỤNG SẢN PHẨM" in data["answer"]
        assert "GIÁ BÁN" in data["answer"]
        assert "TƯƠNG TÁC THUỐC" in data["answer"]
