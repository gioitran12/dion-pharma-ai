# -*- coding: utf-8 -*-
"""
DION Healthcare AI — Unit & Integration Tests for Round 3 Fixes
Kiểm thử tập trung các vấn đề thực tế:
1. Cấu hình & Trạng thái kết nối LLM (Status endpoint, phân biệt unconfigured).
2. Quyền riêng tư & Consent: Opt-out chặn tiếp thị, nhưng hỗ trợ (callback) vẫn hoạt động.
3. Phân quyền & RBAC: Từ chối nhân viên không hợp lệ, chỉ Dược sĩ được đóng khiếu nại ADR.
4. Concurrency & Lost Update Prevention: 20 luồng ghi đồng thời không làm mất dữ liệu.
5. Kiểm tra tính toàn vẹn và không sinh lỗi cú pháp / markup.
"""

import os
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient

from server import app
from modules.customer_care.service import CustomerCareService
from modules.customer_care.schemas import ActionType, TaskStatus


@pytest.fixture
def isolated_care_service(tmp_path):
    """Fixture tạo môi trường service độc lập, không đụng vào dữ liệu thật."""
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir(parents=True)
    
    # Khởi tạo instance độc lập
    import modules.customer_care.service as care_module
    orig_customers = care_module.CUSTOMERS_FILE
    orig_tasks = care_module.TASKS_FILE
    
    care_module.CUSTOMERS_FILE = str(test_data_dir / "customer_care_customers.json")
    care_module.TASKS_FILE = str(test_data_dir / "customer_care_tasks.json")
    
    svc = CustomerCareService()
    svc.evaluate_rules()
    
    yield svc
    
    care_module.CUSTOMERS_FILE = orig_customers
    care_module.TASKS_FILE = orig_tasks


def test_01_copilot_status_endpoint():
    """Kiểm tra endpoint /api/copilot/status trả về đúng trạng thái unconfigured khi dùng placeholder."""
    from unittest.mock import patch
    with patch.dict(os.environ, {"GEMINI_API_KEY": "your-gemini-key-here", "ENABLE_EXPERIMENTAL_CHAT": "false"}):
        client = TestClient(app)
        res = client.get("/api/copilot/status")
        assert res.status_code == 200
        data = res.json()
        assert "configured" in data
        assert "model" in data
        assert "status_text" in data
        # Trong môi trường test với placeholder, configured phải là False
        assert data["configured"] is False
        assert data["status"] == "UNCONFIGURED"
        assert "Chưa kết nối AI" in data["status_text"]


def test_02_opt_out_blocks_marketing_reorder_task(isolated_care_service):
    """Khách hàng Opt-out (KH-6502) có task tiếp thị bị chuyển sang BLOCKED, không nằm trong due_today."""
    svc = isolated_care_service
    
    # Giả lập tình huống: trong hệ thống đã tồn tại 1 task tiếp thị cũ của KH-6502
    from modules.customer_care.schemas import CareTask, TaskPriority
    old_task = CareTask(
        task_id="TASK-KH-6502-DAY25-OLD",
        customer_id="KH-6502",
        customer_name="Phạm Hoàng Nam",
        task_type="REORDER_CHECK_DAY_25",
        title="Kiểm tra nhu cầu bổ sung chu kỳ tiếp: Phạm Hoàng Nam",
        reason="Đến ngày thứ 25 trong chu kỳ",
        sku="DION-CAL-MOM",
        product_name="Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
        priority=TaskPriority.MEDIUM,
        due_date=svc._load_customers_raw()[0].get("purchases", [{}])[0].get("delivery_date", "2026-10-16"),
        status=TaskStatus.PENDING
    )
    svc.update_task(old_task)
    
    # Đánh giá lại quy tắc: Hệ thống phải tự động phát hiện và khóa (BLOCKED) task tiếp thị này
    tasks = svc.evaluate_rules()
    reorder_task = next((t for t in tasks if t.customer_id == "KH-6502" and t.task_type == "REORDER_CHECK_DAY_25"), None)
    assert reorder_task is not None
    assert reorder_task.status == TaskStatus.BLOCKED
    assert reorder_task.is_blocked is True
    assert "Opt-out" in reorder_task.block_reason
    assert reorder_task.is_due_today is False

    metrics = svc.get_metrics()
    assert metrics.blocked >= 1
    # due_today không bao gồm task bị blocked
    active_due = [t for t in tasks if t.is_due_today]
    assert not any(t.task_id == reorder_task.task_id for t in active_due)


def test_03_opt_out_customer_still_allows_support_callback(isolated_care_service):
    """Khách hàng Opt-out (KH-6502) vẫn được hỗ trợ cuộc gọi tư vấn (SCHEDULED_CALLBACK) bình thường."""
    svc = isolated_care_service
    tasks = svc.list_tasks()
    
    callback_task = next((t for t in tasks if t.customer_id == "KH-6502" and t.task_type == "SCHEDULED_CALLBACK"), None)
    assert callback_task is not None
    assert callback_task.status == TaskStatus.PENDING
    assert callback_task.is_blocked is False
    assert callback_task.is_due_today is True
    
    # Soạn tin cho task hỗ trợ này thành công
    draft_res = svc.auto_draft_message("KH-6502", callback_task.task_id)
    assert draft_res["decision"] == "CARE_DRAFT"
    assert "KỊCH BẢN GỌI ĐIỆN THEO HẸN" in draft_res["draft"]


def test_04_draft_for_blocked_marketing_strictly_rejected(isolated_care_service):
    """Thao tác soạn tin cho task tiếp thị của khách Opt-out bị chặn PRIVACY_BLOCKED."""
    svc = isolated_care_service
    
    from modules.customer_care.schemas import CareTask, TaskPriority
    old_task = CareTask(
        task_id="TASK-KH-6502-DAY25-TEST",
        customer_id="KH-6502",
        customer_name="Phạm Hoàng Nam",
        task_type="REORDER_CHECK_DAY_25",
        title="Kiểm tra nhu cầu bổ sung chu kỳ tiếp: Phạm Hoàng Nam",
        reason="Đến ngày thứ 25 trong chu kỳ",
        sku="DION-CAL-MOM",
        product_name="Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
        priority=TaskPriority.MEDIUM,
        due_date="2026-10-16",
        status=TaskStatus.BLOCKED,
        is_blocked=True
    )
    svc.update_task(old_task)
    
    draft_res = svc.auto_draft_message("KH-6502", old_task.task_id)
    assert draft_res["decision"] == "PRIVACY_BLOCKED"
    assert draft_res["is_opt_out"] is True
    assert "⛔ CẢNH BÁO QUYỀN RIÊNG TƯ" in draft_res["draft"]


def test_05_rbac_rejects_unauthorized_staff_names(isolated_care_service):
    """Gửi tên nhân viên giả mạo / không có trong danh sách qua log_action bị từ chối lỗi 403."""
    svc = isolated_care_service
    tasks = svc.list_tasks()
    target_task = tasks[0]
    
    res = svc.log_action(
        task_id=target_task.task_id,
        action_type=ActionType.CONTACTED,
        performed_by="Hacker_Unknown_User",
        notes="Thao tác trái phép"
    )
    assert res["status"] == "ERROR"
    assert res["code"] == "UNAUTHORIZED_STAFF"


def test_06_rbac_only_clinical_staff_can_resolve_complaint(isolated_care_service):
    """Nhân viên CSKH thông thường không được phép đóng khiếu nại chất lượng / ADR (yêu cầu Dược sĩ)."""
    svc = isolated_care_service
    tasks = svc.list_tasks()
    complaint_task = next(t for t in tasks if t.task_type == "COMPLAINT_RESOLUTION")
    
    # Thử đóng bằng Chuyên viên CSKH -> Bị từ chối PERMISSION_DENIED
    res_cskh = svc.log_action(
        task_id=complaint_task.task_id,
        action_type=ActionType.RESOLVED,
        performed_by="Chuyên viên CSKH",
        notes="Tôi tự đóng khiếu nại này"
    )
    assert res_cskh["status"] == "ERROR"
    assert res_cskh["code"] == "PERMISSION_DENIED"
    
    # Đóng bằng Dược sĩ Trần Mai -> Thành công
    res_ds = svc.log_action(
        task_id=complaint_task.task_id,
        action_type=ActionType.RESOLVED,
        performed_by="Dược sĩ Trần Mai",
        notes="Dược sĩ đã gọi điện hướng dẫn uống sau bữa ăn no"
    )
    assert res_ds["status"] == "SUCCESS"
    assert res_ds["task"]["status"] == TaskStatus.COMPLETED


def test_07_concurrent_updates_lost_update_prevention(isolated_care_service):
    """Kiểm thử 20 thao tác ghi đồng thời (multi-threaded): Concurrency Lock đảm bảo 0 lost updates."""
    svc = isolated_care_service
    tasks = svc.list_tasks()
    assert len(tasks) > 0
    
    target_task_id = tasks[0].task_id
    num_updates = 20
    
    def worker(i):
        svc.reschedule_task(
            task_id=target_task_id,
            new_due_date=f"2026-10-{10 + (i % 15):02d}",
            notes=f"Concurrent update #{i}"
        )
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(worker, range(num_updates)))
        
    final_task = svc.get_task(target_task_id)
    # Kiểm tra tất cả 20 log thao tác đều được bảo toàn trong danh sách logs của task
    reschedule_logs = [l for l in final_task.logs if "Concurrent update #" in l.get("notes", "")]
    assert len(reschedule_logs) == num_updates, f"Expected {num_updates} logs, got {len(reschedule_logs)}"


def test_08_api_server_routes_clean_and_authenticated():
    """Kiểm tra API /api/customer-care/log-action trả về mã HTTP 403 khi unauthorized staff gửi lên."""
    client = TestClient(app)
    res = client.post("/api/customer-care/log-action", json={
        "task_id": "TASK-KH-7119-COMPLAINT",
        "action_type": "CONTACTED",
        "performed_by": "FakeStaffName",
        "notes": "Test injection"
    })
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UNAUTHORIZED_STAFF"
