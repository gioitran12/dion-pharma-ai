# -*- coding: utf-8 -*-
"""
Tests for Consulting Report Sections 7 & 8 Audit Fixes:
1. Sensitive Medical Escalation (Pregnancy / "bầu", Drug Interactions)
2. Product Comparison ("D3 khác Canxi+D3 chỗ nào?")
3. Out-of-Scope Requests (Purchase Intent BUY_PRODUCT & Doctor Referral OFF_TOPIC)
4. Anti-Spam Frequency Capping 7 Days (Mục 8.1 & 8.2)
5. Customer State Guardrail "Không tự khẳng định" & State Analysis Matrix (Mục 8.3)
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient

from server import app, get_question_engine
from modules.chat.enums import ChatIntent, ChatDecision, RiskLevel
from modules.chat.providers.fake_provider import FakeLLMProvider
from modules.chat.llm_gateway import LLMGateway
from modules.customer_care.schemas import (
    CustomerRecord, CareTask, PurchaseRecord, CareInteraction, ActionType,
    CreateCustomerRequest, CreateInteractionRequest, CreatePurchaseRequest
)
from modules.customer_care.service import CustomerCareService

client = TestClient(app)


@pytest.fixture
def test_gateway():
    fake_provider = FakeLLMProvider(
        default_response="Bản nháp so sánh được tạo từ các Claims đã được xác thực của D3 và Cal-Mom."
    )
    return LLMGateway(provider=fake_provider)


# ==============================================================================
# FIX 1: Sensitive Medical Escalation (Mục 7.3)
# ==============================================================================
def test_fix1_pregnancy_and_heart_medication_escalation():
    engine = get_question_engine()

    queries = [
        "Bầu 5 tháng uống được không?",
        "Bầu 3 tháng có dùng được không?",
        "Mang bầu uống có an toàn không?",
        "Đang bầu có uống được không?",
        "Bầu uống được không?",
        "Đang uống thuốc tim",
        "Tôi đang uống thuốc huyết áp",
    ]

    for q in queries:
        res = engine.analyze_question(q)
        assert res.intent == ChatIntent.MEDICAL_RISK, f"Failed intent on query: '{q}', got: {res.intent}"
        assert res.decision == ChatDecision.HANDOFF_REQUIRED, f"Failed decision on query: '{q}', got: {res.decision}"
        assert res.risk_level == RiskLevel.HIGH, f"Failed risk level on query: '{q}', got: {res.risk_level}"
        assert res.handoff_required is True, f"Failed handoff_required on query: '{q}'"
        assert "DƯỢC SĨ" in res.direct_answer.upper() or "CHUYÊN GIA" in res.direct_answer.upper()

    # Via API endpoint
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res_api = client.post("/api/copilot/chat", json={"message": "Bầu 5 tháng uống được không?"})
        assert res_api.status_code == 200
        data = res_api.json()
        assert data["intent"] == ChatIntent.MEDICAL_RISK.value
        assert data["decision"] == ChatDecision.HANDOFF_REQUIRED.value
        assert data["risk"]["requires_handoff"] is True
        assert data["risk"]["risk_level"] == RiskLevel.HIGH.value


# ==============================================================================
# FIX 2: Product Comparison (Mục 7.3)
# ==============================================================================
def test_fix2_product_comparison_d3_and_calmom(test_gateway):
    engine = get_question_engine()

    q = "D3 khác Canxi+D3 chỗ nào?"
    res = engine.analyze_question(q)
    assert res.intent == ChatIntent.PRODUCT_COMPARISON, f"Expected PRODUCT_COMPARISON, got: {res.intent}"
    assert res.product_resolution.is_multi_product is True
    assert "DION-D3-1000" in res.product_resolution.all_matched_skus
    assert "DION-CAL-MOM" in res.product_resolution.all_matched_skus

    # Compare D3 vs Canxi Cal-Mom via API
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        with patch("server.get_llm_gateway", return_value=test_gateway):
            res_api = client.post("/api/copilot/chat", json={"message": q})
            assert res_api.status_code == 200
            data = res_api.json()
            assert data["intent"] == ChatIntent.PRODUCT_COMPARISON.value
            assert "DION-D3-1000" in data["product_ids"]
            assert "DION-CAL-MOM" in data["product_ids"]


# ==============================================================================
# FIX 3: Out-of-Scope Requests (Mục 7.3)
# ==============================================================================
def test_fix3_buy_intent_and_doctor_referral():
    engine = get_question_engine()

    # 1. Purchase intent (BUY_PRODUCT)
    buy_queries = [
        "Cho tôi mua 10 hộp",
        "Tôi muốn mua 5 hộp canxi",
        "Đặt mua 10 hộp",
        "Cho tôi đặt mua sản phẩm",
    ]
    for bq in buy_queries:
        res = engine.analyze_question(bq)
        assert res.intent == ChatIntent.BUY_PRODUCT, f"Expected BUY_PRODUCT for: '{bq}', got: {res.intent}"
        assert res.decision == ChatDecision.READY_TO_SEND
        assert "Hotline" in res.direct_answer or "Kinh doanh" in res.direct_answer

    # API test for BUY_PRODUCT
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res_buy = client.post("/api/copilot/chat", json={"message": "Cho tôi mua 10 hộp"})
        assert res_buy.status_code == 200
        data_buy = res_buy.json()
        assert data_buy["intent"] == ChatIntent.BUY_PRODUCT.value
        assert "Hotline" in data_buy["answer"] or "Kinh doanh" in data_buy["answer"]
        assert any(a["type"] == "CONTACT_SALES" for a in data_buy.get("actions", []))

    # 2. Doctor referral (OFF_TOPIC)
    doc_queries = [
        "Bác sĩ nào giỏi?",
        "Bác sĩ sản khoa nào tốt?",
        "Giới thiệu bác sĩ giỏi cho tôi",
    ]
    for dq in doc_queries:
        res = engine.analyze_question(dq)
        assert res.intent == ChatIntent.OFF_TOPIC, f"Expected OFF_TOPIC for: '{dq}', got: {res.intent}"
        assert "bệnh viện chuyên khoa" in res.direct_answer or "cơ sở y tế" in res.direct_answer

    # API test for Doctor Referral
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res_doc = client.post("/api/copilot/chat", json={"message": "Bác sĩ nào giỏi?"})
        assert res_doc.status_code == 200
        data_doc = res_doc.json()
        assert data_doc["intent"] == ChatIntent.OFF_TOPIC.value
        assert "bệnh viện chuyên khoa" in data_doc["answer"] or "cơ sở y tế" in data_doc["answer"]


# ==============================================================================
# FIX 4: Anti-Spam Frequency Capping 7 Days (Mục 8.1 & 8.2)
# ==============================================================================
def test_fix4_anti_spam_frequency_capping_7_days(tmp_path):
    cust_file = str(tmp_path / "care_customers.json")
    task_file = str(tmp_path / "care_tasks.json")

    import modules.customer_care.service as s_mod
    orig_c = s_mod.CUSTOMERS_FILE
    orig_t = s_mod.TASKS_FILE
    s_mod.CUSTOMERS_FILE = cust_file
    s_mod.TASKS_FILE = task_file

    try:
        svc = CustomerCareService()
        today = datetime.now()
        d25_ago = (today - timedelta(days=25)).strftime("%Y-%m-%d")

        # Tạo khách hàng đã mua hàng 25 ngày trước
        cust_id = "KH-AUDIT-FREQ"
        svc.create_customer(CreateCustomerRequest(
            id=cust_id,
            name="Phạm Thanh Thủy",
            phone="0933111222",
            acquisition_source="Zalo OA",
            consent_status="Đã đồng ý nhận tin Zalo",
            is_opt_out_marketing=False
        ))
        svc.add_purchase(CreatePurchaseRequest(
            customer_id=cust_id,
            order_id="DH-FREQ-01",
            sku="DION-CAL-MOM",
            product_name="Canxi Hữu Cơ DION Cal-Mom Plus",
            delivery_date=d25_ago,
            cycle_days=30
        ))

        # A. Chưa có tương tác gần đây -> Soạn tin bình thường
        draft_ok = svc.auto_draft_message(cust_id)
        assert draft_ok["decision"] == "CARE_DRAFT"
        assert "ngày thứ 25" in draft_ok["draft"]

        # B. Ghi nhận 1 tương tác outbound liên hệ thành công 3 ngày trước (<= 7 ngày)
        d3_ago_str = (today - timedelta(days=3)).strftime("%Y-%m-%d 10:00:00")
        svc.add_interaction(CreateInteractionRequest(
            customer_id=cust_id,
            channel="CALL",
            direction="OUTBOUND",
            interaction_type="CONSULTATION",
            summary="Đã gọi điện tư vấn chế độ dinh dưỡng",
            occurred_at=d3_ago_str,
            performed_by="Chuyên viên CSKH"
        ))

        # C. Thử soạn tin mời mua lại (REORDER) -> Phải bị chặn FREQUENCY_BLOCKED
        draft_blocked = svc.auto_draft_message(cust_id)
        assert draft_blocked["decision"] == "FREQUENCY_BLOCKED"
        assert draft_blocked["warning"] == "FREQUENCY_CAPPING_ENFORCED"
        assert "FREQUENCY CAPPING" in draft_blocked["message"]
        assert "7 ngày" in draft_blocked["draft"]

        # D. Kiểm tra evaluate_rules: Task REORDER phải bị đánh dấu is_blocked=True
        tasks = svc.evaluate_rules()
        reorder_task = next(t for t in tasks if t.customer_id == cust_id and t.task_type == "REORDER_CHECK_DAY_25")
        assert reorder_task.is_blocked is True
        assert "FREQUENCY_CAPPING" in (reorder_task.block_reason or "")

    finally:
        s_mod.CUSTOMERS_FILE = orig_c
        s_mod.TASKS_FILE = orig_t


# ==============================================================================
# FIX 5: Customer State Guardrail "Không tự khẳng định" & State Matrix (Mục 8.3)
# ==============================================================================
def test_fix5_customer_state_guardrails_and_matrix(tmp_path):
    cust_file = str(tmp_path / "care_customers.json")
    task_file = str(tmp_path / "care_tasks.json")

    import modules.customer_care.service as s_mod
    orig_c = s_mod.CUSTOMERS_FILE
    orig_t = s_mod.TASKS_FILE
    s_mod.CUSTOMERS_FILE = cust_file
    s_mod.TASKS_FILE = task_file

    try:
        svc = CustomerCareService()
        today = datetime.now()
        d7_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        d25_ago = (today - timedelta(days=25)).strftime("%Y-%m-%d")

        # 1. Kiểm tra Day 7 template: Không khẳng định "đã uống 1 tuần"
        cust7_id = "KH-DAY7-TEST"
        svc.create_customer(CreateCustomerRequest(
            id=cust7_id,
            name="Trần Minh",
            phone="0901234567"
        ))
        svc.add_purchase(CreatePurchaseRequest(
            customer_id=cust7_id,
            order_id="DH-DAY7-01",
            sku="DION-D3-1000",
            product_name="Vitamin D3 1000IU Drops",
            delivery_date=d7_ago,
            cycle_days=60
        ))
        draft7 = svc.auto_draft_message(cust7_id)
        assert draft7["decision"] == "CARE_DRAFT"
        msg7 = draft7["draft"]
        # Vi phạm cũ: "Anh da su dung ... duoc 1 tuan"
        assert "duoc 1 tuan" not in msg7.lower() and "được 1 tuần" not in msg7.lower()
        # Mẫu chuẩn: Hỏi thăm đã mở hộp sử dụng chưa
        assert "đã mở hộp" in msg7.lower() or "mở hộp sử dụng chưa" in msg7.lower()

        # 2. Kiểm tra Day 25 template: Không áp đặt khẳng định "trong tháng qua chị uống"
        cust25_id = "KH-DAY25-TEST"
        svc.create_customer(CreateCustomerRequest(
            id=cust25_id,
            name="Đoàn Mỹ Linh",
            phone="0907654321"
        ))
        svc.add_purchase(CreatePurchaseRequest(
            customer_id=cust25_id,
            order_id="DH-DAY25-01",
            sku="DION-CAL-MOM",
            product_name="Canxi Hữu Cơ DION Cal-Mom Plus",
            delivery_date=d25_ago,
            cycle_days=30
        ))
        draft25 = svc.auto_draft_message(cust25_id)
        assert draft25["decision"] == "CARE_DRAFT"
        msg25 = draft25["draft"]
        assert "ngày thứ 25" in msg25.lower()
        assert "nếu trong tháng qua chị dùng đều đặn" in msg25.lower() or "nếu đợt này" in msg25.lower()

        # 3. Kiểm tra method analyze_customer_state ma trận 4 chiều
        state = svc.analyze_customer_state(cust25_id)
        assert state["status"] == "SUCCESS"
        assert "observable_facts" in state
        assert "ai_inference" in state
        assert "confidence_level" in state
        assert "action_recommendation" in state

        obs = state["observable_facts"]
        assert obs["days_since_delivery"] == 25
        assert obs["has_purchase"] is True
        assert obs["order_id"] == "DH-DAY25-01"

        inf = state["ai_inference"]
        assert inf["cycle_days"] == 30
        assert inf["estimated_remaining_days"] == 5
        assert inf["is_factual_usage_confirmed"] is False
        assert inf["reorder_need_likelihood"] == "HIGH"

        rec = state["action_recommendation"]
        assert "KHÔNG TỰ KHẲNG ĐỊNH" in rec

        # 4. Kiểm tra endpoint API GET /api/customer-care/customers/{id}/state
        res_api = client.get(f"/api/customer-care/customers/{cust25_id}/state")
        assert res_api.status_code == 200
        data_api = res_api.json()
        assert data_api["status"] == "SUCCESS"
        assert data_api["observable_facts"]["days_since_delivery"] == 25

    finally:
        s_mod.CUSTOMERS_FILE = orig_c
        s_mod.TASKS_FILE = orig_t
