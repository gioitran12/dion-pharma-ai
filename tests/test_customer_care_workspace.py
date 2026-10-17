# -*- coding: utf-8 -*-
"""
Tests for Customer Care Workspace (Section 12: Tests 10-19)
Phân hệ Chăm sóc Khách hàng & Quản lý Sự cố DION
"""

import os
import json
import pytest
from datetime import datetime
from modules.customer_care.schemas import (
    CustomerRecord, CareTask, PurchaseRecord, ActionType, TaskStatus, TaskPriority
)
from modules.customer_care.service import CustomerCareService


@pytest.fixture
def isolated_care_service(tmp_path):
    """Tạo isolated CustomerCareService với thư mục lưu trữ tạm thời."""
    cust_file = str(tmp_path / "test_customers.json")
    task_file = str(tmp_path / "test_tasks.json")

    # Monkeypatch file paths in module
    import modules.customer_care.service as s_mod
    orig_c = s_mod.CUSTOMERS_FILE
    orig_t = s_mod.TASKS_FILE
    s_mod.CUSTOMERS_FILE = cust_file
    s_mod.TASKS_FILE = task_file

    svc = CustomerCareService()

    yield svc

    # Restore
    s_mod.CUSTOMERS_FILE = orig_c
    s_mod.TASKS_FILE = orig_t


def test_10_event_due_date_and_idempotent_evaluation(isolated_care_service):
    """
    Test 10: Sự kiện đến hạn tạo đúng công việc; chạy lại không tạo trùng.
    """
    svc = isolated_care_service
    tasks_1 = svc.list_tasks()
    assert len(tasks_1) > 0, "Phải có công việc được sinh ra từ seed data"

    # Chạy evaluate lại nhiều lần
    tasks_2 = svc.evaluate_rules()
    tasks_3 = svc.evaluate_rules()

    assert len(tasks_1) == len(tasks_2) == len(tasks_3), "Evaluate rules phải idempotent, không sinh trùng lặp"
    task_ids = [t.task_id for t in tasks_3]
    assert len(task_ids) == len(set(task_ids)), "Tất cả task_id phải là duy nhất"


def test_11_scheduled_callback_has_date_and_assignee(isolated_care_service):
    """
    Test 11: Khách yêu cầu gọi lại có lịch và người phụ trách rõ ràng.
    """
    svc = isolated_care_service
    tasks = svc.list_tasks()
    callback_tasks = [t for t in tasks if t.task_type == "SCHEDULED_CALLBACK"]
    assert len(callback_tasks) >= 1, "Phải có task lịch hẹn gọi lại"

    cb = callback_tasks[0]
    assert cb.due_date is not None and len(cb.due_date) == 10
    assert cb.assignee is not None and cb.assignee != ""
    assert "Dược sĩ" in cb.assignee or "Chuyên viên" in cb.assignee
    assert cb.priority == TaskPriority.HIGH


def test_12_complaint_persistence_and_reload(isolated_care_service):
    """
    Test 12: Khiếu nại được lưu thật; thay đổi trạng thái còn sau khi tải lại service.
    """
    svc = isolated_care_service
    # Tạo hoặc cập nhật khiếu nại
    task = svc.get_task("TASK-KH-7119-COMPLAINT")
    assert task is not None, "Task khiếu nại KH-7119 phải tồn tại"
    assert task.status == TaskStatus.PENDING

    # Đổi assignee và ghi log
    res = svc.assign_task(task.task_id, "Dược sĩ Lê Hoàng")
    assert res["status"] == "SUCCESS"

    # Khởi tạo instance mới cùng storage path để verify persistence
    svc_reloaded = CustomerCareService()
    reloaded_task = svc_reloaded.get_task("TASK-KH-7119-COMPLAINT")
    assert reloaded_task is not None
    assert reloaded_task.assignee == "Dược sĩ Lê Hoàng", "Thay đổi phải được lưu trữ bền vững vào JSON"


def test_13_opt_out_blocks_marketing_proposals(isolated_care_service):
    """
    Test 13: Khách opt-out không nhận đề xuất tiếp thị trái quy tắc.
    """
    svc = isolated_care_service
    # KH-7119 có is_opt_out_marketing = True
    cust = svc.get_customer("KH-7119")
    assert cust.is_opt_out_marketing is True

    # Tạo một task mời mua lại REORDER cho KH-7119 và thử soạn tin
    res = svc.auto_draft_message(customer_id="KH-7119")
    # Phải bị chặn (bởi khiếu nại hoặc opt-out)
    assert res.get("decision") in ("BLOCKED", "PRIVACY_BLOCKED")
    assert res.get("is_opt_out") is True


def test_14_complaint_lock_blocks_upsell_direct_api(isolated_care_service):
    """
    Test 14: Complaint lock chặn upsell ngay cả khi gọi API trực tiếp.
    """
    svc = isolated_care_service
    res = svc.auto_draft_message(
        customer_id="KH-7119",
        task_id="TASK-KH-7119-COMPLAINT"
    )
    assert res.get("decision") == "BLOCKED"
    assert res.get("warning") == "INCIDENT_LOCKOUT_ENFORCED"
    assert res.get("is_locked") is True
    assert "INCIDENT LOCKOUT" in res.get("message", "")


def test_15_contextual_auto_draft_without_manual_prompting(isolated_care_service):
    """
    Test 15: Soạn tin từ hồ sơ chỉ cần chọn khách và bấm nút.
    """
    svc = isolated_care_service
    # KH-8821 là khách bình thường đang ở Ngày 25
    draft_res = svc.auto_draft_message(customer_id="KH-8821", task_id="TASK-KH-8821-DAY25")
    assert draft_res.get("decision") == "CARE_DRAFT"
    draft_text = draft_res.get("draft", "")
    assert len(draft_text) > 20
    assert "ngày thứ 25" in draft_text.lower()
    assert "chị Hương" in draft_text or "Hương" in draft_text
    assert draft_res.get("channel") in ("Zalo OA", "SMS Brandname")


def test_16_copy_action_does_not_increment_completed(isolated_care_service):
    """
    Test 16: Sao chép (COPIED) không làm tăng số "đã liên hệ" hoặc hoàn thành.
    """
    svc = isolated_care_service
    m_before = svc.get_metrics()

    log_res = svc.log_action(
        task_id="TASK-KH-8821-DAY25",
        action_type=ActionType.COPIED,
        performed_by="NV Test",
        notes="Nhân viên bấm copy tin nhắn"
    )
    assert log_res["status"] == "SUCCESS"

    m_after = svc.get_metrics()
    assert m_after.completed == m_before.completed, "Thao tác COPIED không được tính là hoàn thành nhiệm vụ"

    # Khi ghi nhận RESOLVED thì completed mới tăng
    svc.log_action(
        task_id="TASK-KH-8821-DAY25",
        action_type=ActionType.RESOLVED,
        performed_by="NV Test",
        notes="Đã gọi và chốt đơn"
    )
    m_resolved = svc.get_metrics()
    assert m_resolved.completed == m_before.completed + 1, "RESOLVED phải tăng chỉ số completed"


def test_17_switching_customer_context_isolation(isolated_care_service):
    """
    Test 17: Chuyển khách không lẫn dữ liệu hoặc phản hồi đang chờ.
    """
    svc = isolated_care_service
    # Lấy thông tin khách A (khiếu nại)
    draft_a = svc.auto_draft_message("KH-7119", "TASK-KH-7119-COMPLAINT")
    assert draft_a.get("decision") == "BLOCKED"

    # Lấy thông tin khách B (bình thường)
    draft_b = svc.auto_draft_message("KH-8821", "TASK-KH-8821-DAY25")
    assert draft_b.get("decision") == "CARE_DRAFT"

    # Dữ liệu khách B hoàn toàn không bị ảnh hưởng bởi cảnh báo của khách A
    assert draft_b.get("is_locked") is False
    assert "chị Hương" in draft_b.get("draft", "")
    assert "Hà" not in draft_b.get("draft", "")


def test_18_metrics_match_stored_json_no_hardcoded_constants(isolated_care_service):
    """
    Test 18: Báo cáo khớp dữ liệu đã lưu, không dùng số cố định.
    """
    svc = isolated_care_service
    metrics = svc.get_metrics()
    tasks = svc.list_tasks()

    actual_pending_complaints = len([t for t in tasks if t.task_type == "COMPLAINT_RESOLUTION" and t.status != TaskStatus.COMPLETED])
    actual_completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
    actual_active = len([t for t in tasks if t.status != TaskStatus.COMPLETED])

    assert metrics.pending_complaints == actual_pending_complaints
    assert metrics.completed == actual_completed
    assert metrics.total_active == actual_active


def test_19_missing_purchase_history_handled_without_hallucinated_certainty(isolated_care_service):
    """
    Test 19: Thiếu lịch sử mua hàng không bị biến thành dự đoán chắc chắn.
    """
    svc = isolated_care_service
    # Tạo một khách hàng mới không có lịch sử mua hàng
    new_cust = CustomerRecord(
        id="KH-NEW-9999",
        name="Đỗ Minh Quân",
        phone="0911***999",
        consent_status="UNKNOWN",
        is_opt_out_marketing=False,
        active_complaint=None,
        purchases=[]
    )
    svc.update_customer(new_cust)

    # Đánh giá rules
    tasks = svc.evaluate_rules()
    # Khách không có purchases không được tự ý sinh ngày 25 hay ngày 7
    new_cust_tasks = [t for t in tasks if t.customer_id == "KH-NEW-9999"]
    assert len(new_cust_tasks) == 0, "Không được tự ý phán đoán chu kỳ khi thiếu lịch sử mua hàng"

    # Thử gọi auto draft
    res = svc.auto_draft_message(customer_id="KH-NEW-9999")
    assert res.get("decision") == "CARE_DRAFT"
    # Kịch bản phải dùng định danh tham chiếu chung, không bịa ngày cụ thể
    assert "ngày thứ 25" not in res.get("draft", "").lower()
