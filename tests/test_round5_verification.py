# -*- coding: utf-8 -*-
"""
DION Healthcare AI — Bộ kiểm thử Nghiệm thu Round 5 (Verification Test Suite)
Bao gồm:
1. Xác minh Nguồn Cal-Mom & loại trừ PMID sai lệch (EVIDENCE_MISMATCH).
2. Kiểm tra Trạng thái AI 4 cấp độ (UNCONFIGURED, CONFIGURED_UNVERIFIED, VERIFIED, DEGRADED).
3. Kiểm tra Phân quyền thực sự, AUTH_NOT_IMPLEMENTED và ranh giới Demo Sandbox.
4. Kiểm tra Bất biến Customer Care: Callback tổng quát, Giải quyết 1 khiếu nại không đóng gộp khiếu nại khác.
5. Kiểm tra Ghi đồng thời (RLock) và tính toàn vẹn khi lỗi lưu file (Atomic Write).
"""

import os
import json
import uuid
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from server import app, _ai_verification_state, _update_ai_verification_on_success, _update_ai_verification_on_error
from modules.knowledge.repository import get_knowledge_repository, JSONKnowledgeRepository
from modules.knowledge.schemas import KnowledgeZone, ClaimStatus, ValidationCode, ClaimRecord
from modules.knowledge.validator import ClaimEligibilityValidator
from modules.customer_care.schemas import (
    CustomerRecord, CareTask, PurchaseRecord, ActionType, TaskStatus, TaskPriority
)
from modules.customer_care.service import (
    CustomerCareService, AUTHORIZED_STAFF, AUTHORIZED_CLINICAL_STAFF, _service_lock
)


# ==============================================================================
# NHÓM 1: KIỂM TRA NGUỒN CAL-MOM & LOẠI TRỪ PMID SAI LỆCH
# ==============================================================================

def test_calmom_clinical_evidence_flagged_as_evidence_mismatch():
    """PMID 30121111 và 29482012 phải được đánh dấu EVIDENCE_MISMATCH trong hồ sơ Cal-Mom."""
    repo = JSONKnowledgeRepository()
    calmom = repo.get_product_by_sku("DION-CAL-MOM")
    assert calmom is not None

    ce_list = calmom.clinical_evidence
    assert len(ce_list) >= 2
    for item in ce_list:
        assert item.get("status") == "EVIDENCE_MISMATCH"
        assert item.get("is_verified") is False
        assert "Lane departure" in item.get("audit_note", "") or "Leishmania" in item.get("audit_note", "")


def test_calmom_claims_use_verified_administrative_source():
    """Claims CLM-CAL-01 và CLM-CAL-02 chỉ dùng nguồn hành chính hợp lệ (8892/2025/ĐKSP), không dùng PMID sai."""
    repo = JSONKnowledgeRepository()
    claim1 = repo.get_claim_by_id("CLM-CAL-01")
    claim2 = repo.get_claim_by_id("CLM-CAL-02")
    
    assert claim1 is not None
    assert claim2 is not None

    assert "8892/2025/ĐKSP" in claim1.get_evidence()
    assert "30121111" not in claim1.get_evidence()
    assert "PMID: 30121111" in claim1.unverified_citations
    assert claim1.original_evidence_source is not None

    assert "8892/2025/ĐKSP" in claim2.get_evidence()
    assert "29482012" not in claim2.get_evidence()
    assert "PMID: 29482012" in claim2.unverified_citations


def test_validator_detects_evidence_mismatch():
    """Claim bị gắn cờ EVIDENCE_MISMATCH sẽ bị validator từ chối hợp lệ."""
    invalid_claim = ClaimRecord(
        claim_id="CLM-TEST-MISMATCH",
        product_sku="DION-CAL-MOM",
        claim_text="Công dụng thử nghiệm kiểm tra lỗi trích dẫn",
        status=ClaimStatus.APPROVED,
        zone=KnowledgeZone.COMMERCIAL_APPROVED,
        evidence_source="PMID: 30121111",
        evidence_status="EVIDENCE_MISMATCH",
        approved_by="Dược sĩ Thẩm định",
    )
    res = ClaimEligibilityValidator.validate_claim_eligibility(invalid_claim, "DION-CAL-MOM")
    assert res.eligible is False
    assert ValidationCode.EVIDENCE_MISMATCH in res.reasons


# ==============================================================================
# NHÓM 2: TRẠNG THÁI AI 4 CẤP ĐỘ VÀ CẤU HÌNH MODEL
# ==============================================================================

def test_copilot_status_4_tier_transitions():
    """Kiểm tra GET /api/copilot/status phản ánh đúng 4 trạng thái."""
    client = TestClient(app)

    # 1. Trạng thái UNCONFIGURED (khi key là placeholder hoặc rỗng)
    with patch.dict(os.environ, {"GEMINI_API_KEY": "your-gemini-key-here", "ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res = client.get("/api/copilot/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "UNCONFIGURED"
        assert "Chưa kết nối AI" in data["status_text"]

    # 2. Trạng thái CONFIGURED_UNVERIFIED (khi có key thật nhưng chưa gọi thành công)
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyRealKeySample999888777", "ENABLE_EXPERIMENTAL_CHAT": "true"}):
        res = client.get("/api/copilot/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "CONFIGURED_UNVERIFIED"
        assert "chưa kiểm chứng" in data["status_text"]

        # 3. Trạng thái VERIFIED (sau khi smoke call thành công với cấu hình này)
        _update_ai_verification_on_success(model="gemini-3.8-flash", provider="gemini")
        res_v = client.get("/api/copilot/status")
        assert res_v.json()["status"] == "VERIFIED"
        assert "Đã kiểm chứng" in res_v.json()["status_text"]

        # 4. Trạng thái DEGRADED (khi lần gọi gần nhất gặp lỗi)
        _update_ai_verification_on_error(code="LLM_MODEL_NOT_FOUND", message="Model gemini-3.8-flash không tồn tại")
        res_d = client.get("/api/copilot/status")
        assert res_d.json()["status"] == "DEGRADED"
        assert "LLM_MODEL_NOT_FOUND" in res_d.json()["status_text"]
        assert res_d.json()["last_error_code"] == "LLM_MODEL_NOT_FOUND"

    # Dọn dẹp trạng thái sau test để không ảnh hưởng các test suite khác
    _ai_verification_state["status"] = "UNCONFIGURED"
    _ai_verification_state["config_fingerprint"] = None


# ==============================================================================
# NHÓM 3: PHÂN QUYỀN THỰC SỰ & AUTH_NOT_IMPLEMENTED
# ==============================================================================

def test_auth_unauthenticated_clinical_claim_rejected_on_non_demo_data():
    """
    Client chưa đăng nhập gửi đúng tên Dược sĩ trên hồ sơ khách thật (is_demo=False)
    phải bị từ chối với mã lỗi AUTH_NOT_IMPLEMENTED.
    """
    client = TestClient(app)
    
    with patch.object(CustomerCareService, "get_customer") as mock_get_c, \
         patch.object(CustomerCareService, "get_task") as mock_get_t:
        
        mock_get_t.return_value = CareTask(
            task_id="TASK-REAL-001",
            customer_id="KH-REAL-001",
            customer_name="Bệnh nhân thực tế",
            task_type="COMPLAINT_RESOLUTION",
            title="Sự cố phản ứng phụ",
            reason="Dị ứng",
            sku="DION-CAL-MOM",
            product_name="Cal-Mom",
            priority=TaskPriority.HIGH,
            due_date="2026-10-16",
            assignee="Dược sĩ Trần Mai",
            status=TaskStatus.PENDING,
            is_demo=False
        )
        mock_get_c.return_value = CustomerRecord(
            id="KH-REAL-001",
            name="Bệnh nhân thực tế",
            phone="0911222333",
            is_demo=False
        )

        res = client.post("/api/customer-care/log-action", json={
            "task_id": "TASK-REAL-001",
            "action_type": "RESOLVED",
            "performed_by": "Dược sĩ Trần Mai",
            "notes": "Tự khai tên Dược sĩ để giải quyết sự cố"
        })
        
        assert res.status_code == 401
        err_detail = res.json().get("detail", {})
        assert err_detail.get("code") == "AUTH_NOT_IMPLEMENTED"


def test_regular_staff_cannot_resolve_clinical_complaint():
    """Nhân viên CSKH thường không được phép đóng khiếu nại chuyên môn (PERMISSION_DENIED)."""
    svc = CustomerCareService()
    tasks = svc.list_tasks()
    complaint_task = next((t for t in tasks if t.task_type == "COMPLAINT_RESOLUTION"), None)
    if not complaint_task:
        svc.evaluate_rules()
        tasks = svc.list_tasks()
        complaint_task = next((t for t in tasks if t.task_type == "COMPLAINT_RESOLUTION"), None)

    assert complaint_task is not None

    res = svc.log_action(
        task_id=complaint_task.task_id,
        action_type=ActionType.RESOLVED,
        performed_by="Chuyên viên Nam",
        notes="Nhân viên thường thử đóng khiếu nại"
    )
    assert res["status"] == "ERROR"
    assert res["code"] == "PERMISSION_DENIED"


def test_invalid_staff_rejected_immediately():
    """Tên người thực hiện không nằm trong danh mục nhân sự bị từ chối UNAUTHORIZED_STAFF."""
    svc = CustomerCareService()
    tasks = svc.list_tasks()
    t = tasks[0]

    res = svc.log_action(
        task_id=t.task_id,
        action_type=ActionType.CONTACTED,
        performed_by="Người Lạ Không Xác Định",
        notes="Thử can thiệp hệ thống"
    )
    assert res["status"] == "ERROR"
    assert res["code"] == "UNAUTHORIZED_STAFF"


# ==============================================================================
# NHÓM 4: BẤT BIẾN CUSTOMER CARE & MULTI-COMPLAINT RESOLUTION
# ==============================================================================

def test_generic_callback_rule_without_hardcoding(tmp_path):
    """Bất kỳ khách hàng nào có callback_requested=True đều tự động sinh task SCHEDULED_CALLBACK."""
    custom_tasks_file = str(tmp_path / "cb_tasks.json")
    custom_cust_file = str(tmp_path / "cb_customers.json")

    custom_customer = CustomerRecord(
        id="KH-TEST-99",
        name="Lê Minh Anh",
        phone="0988***999",
        consent_status="Đã đồng ý nhận tin",
        is_opt_out_marketing=False,
        callback_requested=True,
        callback_reason="Khách yêu cầu gọi lại để hỏi liều uống D3",
        callback_sku="DION-D3-1000",
        callback_product_name="Vitamin D3 1000IU Drops",
        is_demo=True
    )
    with open(custom_cust_file, "w", encoding="utf-8") as f:
        json.dump([custom_customer.model_dump()], f, ensure_ascii=False)
    with open(custom_tasks_file, "w", encoding="utf-8") as f:
        json.dump([], f)

    svc = CustomerCareService()
    with patch("modules.customer_care.service.TASKS_FILE", custom_tasks_file), \
         patch("modules.customer_care.service.CUSTOMERS_FILE", custom_cust_file):
        
        created_tasks = svc.evaluate_rules()
        cb_task = next((t for t in created_tasks if t.customer_id == "KH-TEST-99" and t.task_type == "SCHEDULED_CALLBACK"), None)
        assert cb_task is not None
        assert cb_task.sku == "DION-D3-1000"
        assert "hỏi liều uống D3" in cb_task.reason


def test_resolving_one_complaint_does_not_close_other_complaints_for_same_customer():
    """Khách hàng có 2 khiếu nại, khi giải quyết khiếu nại 1 thì khiếu nại 2 vẫn còn và khách vẫn bị khóa (Incident Lockout)."""
    svc = CustomerCareService()

    cust = CustomerRecord(
        id="KH-MULTI-01",
        name="Vũ Hoàng Yến",
        phone="0933***111",
        active_complaint="Khiếu nại 1: Đau dạ dày",
        complaint_status="Đang xử lý khiếu nại",
        is_demo=True
    )
    task1 = CareTask(
        task_id="TASK-C1",
        customer_id="KH-MULTI-01",
        customer_name="Vũ Hoàng Yến",
        task_type="COMPLAINT_RESOLUTION",
        title="Xử lý khiếu nại đau dạ dày",
        reason="Khiếu nại 1: Đau dạ dày",
        sku="DION-FE-FOLIC",
        product_name="Sắt Fero-Plus",
        priority=TaskPriority.HIGH,
        due_date="2026-10-16",
        assignee="Dược sĩ Trần Mai",
        status=TaskStatus.PENDING,
        is_demo=True
    )
    task2 = CareTask(
        task_id="TASK-C2",
        customer_id="KH-MULTI-01",
        customer_name="Vũ Hoàng Yến",
        task_type="COMPLAINT_RESOLUTION",
        title="Xử lý khiếu nại vỡ viên nang",
        reason="Khiếu nại 2: Vỡ viên nang",
        sku="DION-FE-FOLIC",
        product_name="Sắt Fero-Plus",
        priority=TaskPriority.HIGH,
        due_date="2026-10-16",
        assignee="Dược sĩ Trần Mai",
        status=TaskStatus.PENDING,
        is_demo=True
    )

    all_tasks = [task1, task2]
    
    def fake_list_tasks():
        return list(all_tasks)

    def fake_get_task(tid):
        return next((t for t in all_tasks if t.task_id == tid), None)

    def fake_update_task(updated_t):
        for idx, t in enumerate(all_tasks):
            if t.task_id == updated_t.task_id:
                all_tasks[idx] = updated_t

    with patch.object(svc, "get_customer", return_value=cust), \
         patch.object(svc, "list_tasks", side_effect=fake_list_tasks), \
         patch.object(svc, "get_task", side_effect=fake_get_task), \
         patch.object(svc, "update_task", side_effect=fake_update_task), \
         patch.object(svc, "update_customer"):

        res = svc.log_action(
            task_id="TASK-C1",
            action_type=ActionType.RESOLVED,
            performed_by="Dược sĩ Trần Mai",
            notes="Đã hướng dẫn uống sau bữa ăn no"
        )
        assert res["status"] == "SUCCESS"
        assert task1.status == TaskStatus.COMPLETED

        # Khách vẫn còn khiếu nại 2 (active_complaint KHÔNG bị None)
        assert cust.active_complaint is not None
        assert "Còn 1 khiếu nại đang xử lý" in cust.complaint_status
        assert len(cust.complaint_history) == 1
        assert cust.complaint_history[0]["task_id"] == "TASK-C1"


# ==============================================================================
# NHÓM 5: KIỂM TRA GHI ĐỒNG THỜI VÀ LỖI LƯU (ATOMIC WRITE & RLOCK)
# ==============================================================================

def test_concurrent_updates_share_rlock_without_loss(tmp_path):
    """Hai cập nhật độc lập đồng thời trong cùng tiến trình đều tồn tại, không bị ghi đè mất mát dữ liệu."""
    custom_tasks_file = str(tmp_path / "concurrent_tasks.json")
    custom_cust_file = str(tmp_path / "concurrent_customers.json")

    initial_tasks = [
        {"task_id": "T-1", "customer_id": "KH-1", "customer_name": "A", "task_type": "FOLLOWUP", "title": "T1", "reason": "R", "sku": "S", "product_name": "P", "priority": "MEDIUM", "due_date": "2026-10-16", "assignee": "NV", "status": "PENDING", "created_at": "2026-10-16", "updated_at": "2026-10-16", "logs": []},
        {"task_id": "T-2", "customer_id": "KH-2", "customer_name": "B", "task_type": "FOLLOWUP", "title": "T2", "reason": "R", "sku": "S", "product_name": "P", "priority": "MEDIUM", "due_date": "2026-10-16", "assignee": "NV", "status": "PENDING", "created_at": "2026-10-16", "updated_at": "2026-10-16", "logs": []}
    ]
    with open(custom_tasks_file, "w", encoding="utf-8") as f:
        json.dump(initial_tasks, f)
    with open(custom_cust_file, "w", encoding="utf-8") as f:
        json.dump([], f)

    svc = CustomerCareService()

    with patch("modules.customer_care.service.TASKS_FILE", custom_tasks_file), \
         patch("modules.customer_care.service.CUSTOMERS_FILE", custom_cust_file):

        def worker1():
            t = svc.get_task("T-1")
            t.reason = "Updated by thread 1"
            t.status = TaskStatus.IN_PROGRESS
            svc.update_task(t)

        def worker2():
            t = svc.get_task("T-2")
            t.reason = "Updated by thread 2"
            t.status = TaskStatus.COMPLETED
            svc.update_task(t)

        th1 = threading.Thread(target=worker1)
        th2 = threading.Thread(target=worker2)
        th1.start()
        th2.start()
        th1.join()
        th2.join()

        with open(custom_tasks_file, "r", encoding="utf-8") as f:
            saved_tasks = json.load(f)

        t1_saved = next(x for x in saved_tasks if x["task_id"] == "T-1")
        t2_saved = next(x for x in saved_tasks if x["task_id"] == "T-2")

        assert t1_saved["status"] == "IN_PROGRESS"
        assert t2_saved["status"] == "COMPLETED"


def test_atomic_write_failure_preserves_disk_integrity(tmp_path):
    """Khi tiến trình ghi JSON gặp lỗi I/O, hệ thống không báo thành công và file trên đĩa không bị hỏng."""
    svc = CustomerCareService()
    test_file = str(tmp_path / "test_atomic.json")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write('[{"task_id": "T-ORIGINAL"}]')

    with patch("modules.customer_care.service.TASKS_FILE", test_file), \
         patch("modules.customer_care.service._atomic_json_write", side_effect=IOError("Mô phỏng lỗi ghi đĩa")):
        
        with pytest.raises(IOError):
            svc.update_task(CareTask(
                task_id="T-CORRUPT",
                customer_id="KH-01",
                customer_name="A",
                task_type="TEST",
                title="T",
                reason="R",
                sku="S",
                product_name="P",
                due_date="2026-10-16"
            ))

        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "T-ORIGINAL" in content
            assert "T-CORRUPT" not in content
