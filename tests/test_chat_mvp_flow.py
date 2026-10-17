"""
DION Healthcare AI — Integration Test Suite: Chatbot MVP End-to-End Flow
Kiểm thử toàn diện 7 kịch bản hoạt động thực tế của Chatbot MVP:
1. Chào hỏi thông thường (GREETING)
2. Hỏi công dụng Vitamin D3 có nguồn hợp lệ (GROUNDED CLAIMS)
3. Hỏi công dụng không có trong Claims (INSUFFICIENT_EVIDENCE)
4. Hỏi SKU không tồn tại (NO_FALLBACK & INSUFFICIENT_EVIDENCE)
5. Hỏi về thai kỳ, bệnh nền, tương tác thuốc & cam kết điều trị (SAFETY ESCALATION & BLOCKED)
6. LLM API bị lỗi cấu hình hoặc timeout (ERROR HANDLING)
7. API cũ /api/copilot/ask duy trì hoạt động 100% (BACKWARD COMPATIBILITY)
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from server import app
from modules.chat.enums import ChatIntent, ChatDecision, RiskLevel
from modules.chat.schemas import ChatResponse
from modules.chat.providers.fake_provider import FakeLLMProvider
from modules.chat.llm_gateway import LLMGateway
from modules.chat.providers.base import LLMTimeoutError

client = TestClient(app)


# ------------------------------------------------------------------------------
# 1. Kịch bản 1: Câu hỏi chào hỏi thông thường
# ------------------------------------------------------------------------------
def test_scenario_1_greeting():
    fake_provider = FakeLLMProvider(default_response="Xin chào! Tôi là trợ lý AI của DION Healthcare AI.")
    gateway = LLMGateway(provider=fake_provider)

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=gateway):
            res = client.post("/api/copilot/chat", json={"message": "Xin chào bạn, bạn là ai?"})
            assert res.status_code == 200
            data = res.json()
            assert data["decision"] == ChatDecision.READY_TO_SEND.value
            assert data["intent"] == ChatIntent.GREETING.value
            assert "DION Healthcare AI" in data["answer"]
            assert data["sources"] == []
            assert data["product_ids"] == []
            assert data["risk"]["requires_handoff"] is False
            assert data["ticket_id"] is None


# ------------------------------------------------------------------------------
# 2. Kịch bản 2: Hỏi công dụng Vitamin D3 có nguồn hợp lệ
# ------------------------------------------------------------------------------
def test_scenario_2_valid_product_claims():
    fake_provider = FakeLLMProvider(
        default_response="Vitamin D3 1000IU giúp tăng cường hấp thu canxi, hỗ trợ xương và răng chắc khỏe."
    )
    gateway = LLMGateway(provider=fake_provider)

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=gateway):
            # Hỏi công dụng D3 theo SKU hoặc tên
            res = client.post("/api/copilot/chat", json={
                "message": "Vitamin D3 có công dụng gì đối với xương và cơ thể?",
                "product_id": "DION-D3-1000"
            })
            assert res.status_code == 200
            data = res.json()
            assert data["decision"] == ChatDecision.DRAFT_FOR_APPROVAL.value
            assert data["intent"] == ChatIntent.PRODUCT_INFO.value
            assert "DION-D3-1000" in data["product_ids"]
            assert len(data["sources"]) > 0

            # Kiểm tra nguồn claims đối soát
            source_claim_ids = [s["claim_id"] for s in data["sources"]]
            assert "CLM-D3-01" in source_claim_ids or "CLM-D3-02" in source_claim_ids
            # Claim hết hạn và nội bộ tuyệt đối không được xuất hiện
            assert "CLM-D3-03" not in source_claim_ids
            assert "CLM-D3-04" not in source_claim_ids

            # Kiểm tra cờ bản nháp
            assert "Bản nháp" in data["answer"] or "nhân viên" in data["answer"]
            assert data["risk"]["requires_handoff"] is False
            assert data["ticket_id"] is None


# ------------------------------------------------------------------------------
# 3. Kịch bản 3: Hỏi công dụng không có trong Claims đã duyệt
# ------------------------------------------------------------------------------
def test_scenario_3_claim_not_found_insufficient_evidence():
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        # Hỏi công dụng không hề có trong Claims (làm trắng da, mọc tóc)
        res = client.post("/api/copilot/chat", json={
            "message": "Vitamin D3 này có tác dụng làm trắng da và mọc tóc không?",
            "product_id": "DION-D3-1000"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == ChatDecision.INSUFFICIENT_EVIDENCE.value
        assert data["sources"] == []
        assert "chưa có đủ căn cứ" in data["answer"].lower() or "không tìm thấy" in data["answer"].lower()
        assert data["ticket_id"] is None


# ------------------------------------------------------------------------------
# 4. Kịch bản 4: Hỏi SKU không tồn tại
# ------------------------------------------------------------------------------
def test_scenario_4_nonexistent_sku_no_fallback():
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res = client.post("/api/copilot/chat", json={
            "message": "Sản phẩm này có tác dụng gì?",
            "product_id": "NON_EXISTENT_SKU_XYZ"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == ChatDecision.INSUFFICIENT_EVIDENCE.value
        assert data["sources"] == []
        assert "không tìm thấy thông tin" in data["answer"].lower()
        # Không rò rỉ hoặc fallback sang D3
        assert "CLM-D3-01" not in [s.get("claim_id") for s in data["sources"]]
        assert data["ticket_id"] is None


# ------------------------------------------------------------------------------
# 5. Kịch bản 5: Hỏi về thai kỳ, tương tác thuốc & cam kết điều trị
# ------------------------------------------------------------------------------
def test_scenario_5a_pregnancy_escalation():
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res = client.post("/api/copilot/chat", json={
            "message": "Khách hàng đang mang thai 3 tháng đầu có uống được D3 không?",
            "product_id": "DION-D3-1000"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == ChatDecision.HANDOFF_REQUIRED.value
        assert data["risk"]["requires_handoff"] is True
        assert data["risk"]["risk_level"] == RiskLevel.HIGH.value
        assert "DƯỢC SĨ" in data["answer"].upper()
        assert data["sources"] == []
        assert data["ticket_id"] is None  # Không tạo ticket giả


def test_scenario_5b_drug_interaction_escalation():
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res = client.post("/api/copilot/chat", json={
            "message": "Sản phẩm có tương tác thuốc với kháng sinh không?",
            "product_id": "DION-CAL-MOM"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == ChatDecision.HANDOFF_REQUIRED.value
        assert data["risk"]["requires_handoff"] is True
        assert data["sources"] == []


def test_scenario_5c_prohibited_treatment_blocked():
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res = client.post("/api/copilot/chat", json={
            "message": "Sản phẩm Canxi Cal-Mom có điều trị dứt điểm bệnh loãng xương không?"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == ChatDecision.BLOCKED.value
        assert data["risk"]["requires_handoff"] is True
        assert "từ chối" in data["answer"].lower() or "342" in data["answer"]
        assert data["sources"] == []


# ------------------------------------------------------------------------------
# 6. Kịch bản 6: LLM API bị lỗi hoặc timeout
# ------------------------------------------------------------------------------
def test_scenario_6a_llm_timeout():
    fake_provider = FakeLLMProvider(side_effect=LLMTimeoutError(message="Cổng LLM phản hồi quá hạn (timeout)"))
    gateway = LLMGateway(provider=fake_provider)

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=gateway):
            res = client.post("/api/copilot/chat", json={
                "message": "Vitamin D3 có công dụng gì với xương?",
                "product_id": "DION-D3-1000"
            })
            assert res.status_code == 504
            data = res.json()
            assert "timeout" in data["detail"]["message"].lower() or "llm_timeout" in data["detail"]["code"].lower()


def test_scenario_6b_llm_missing_config():
    # Khi LLM Gateway thiếu key thật
    with patch.dict(os.environ, {
        "ENABLE_EXPERIMENTAL_CHAT": "true",
        "GEMINI_API_KEY": "your_gemini_key_placeholder",
        "OPENAI_API_KEY": ""
    }):
        # Không mock gateway, để gateway tự khởi tạo từ env
        res = client.post("/api/copilot/chat", json={"message": "Xin chào"})
        assert res.status_code == 500
        data = res.json()
        assert data["detail"]["code"] == "LLM_NOT_CONFIGURED"


# ------------------------------------------------------------------------------
# 7. Kịch bản 7: Endpoint cũ /api/copilot/ask vẫn hoạt động bình thường
# ------------------------------------------------------------------------------
def test_scenario_7_legacy_endpoint_ask_intact():
    res = client.post("/api/copilot/ask", json={
        "query": "Vitamin D3 có công dụng gì với xương?",
        "sku": "DION-D3-1000"
    })
    assert res.status_code == 200
    data = res.json()
    assert "type" in data
    assert "content" in data
    assert "citations" in data
    assert data["type"] == "NORMAL"
    assert len(data["citations"]) > 0
