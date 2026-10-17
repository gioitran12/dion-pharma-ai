# -*- coding: utf-8 -*-
"""
DION Healthcare AI — Comprehensive Test Suite for Customer Care Flow (Section 14)
Kiểm thử trọn vẹn luồng khách hàng DEMO mới, truy vết nguồn gốc, chống trùng lặp,
kiểm soát quyền riêng tư, phân quyền xử lý và tính nhất quán của dữ liệu.
"""

import os
import json
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from server import app
from modules.customer_care.schemas import (
    CustomerRecord, CareTask, PurchaseRecord, CareInteraction, SupportRequest, CallbackRequest,
    ActionType, TaskStatus, TaskPriority, CustomerType,
    CreateCustomerRequest, CreateInteractionRequest, CreatePurchaseRequest,
    CreateSupportRequest, CreateCallbackRequest, LinkCopilotInteractionRequest
)
from modules.customer_care.service import CustomerCareService


@pytest.fixture
def isolated_service(tmp_path):
    """Tạo isolated CustomerCareService với storage tạm thời."""
    cust_file = str(tmp_path / "care_customers.json")
    task_file = str(tmp_path / "care_tasks.json")

    import modules.customer_care.service as s_mod
    orig_c = s_mod.CUSTOMERS_FILE
    orig_t = s_mod.TASKS_FILE
    s_mod.CUSTOMERS_FILE = cust_file
    s_mod.TASKS_FILE = task_file

    svc = CustomerCareService()

    yield svc

    s_mod.CUSTOMERS_FILE = orig_c
    s_mod.TASKS_FILE = orig_t


def test_01_full_lifecycle_demo_customer(isolated_service):
    """
    Kịch bản chính Section 14 (Bước 1 -> 14):
    Tạo khách mới -> Tương tác hỏi SP & hẹn gọi lại -> Tạo đơn 1 giao thành công
    -> Chống trùng -> Tạo đơn 2 -> Khiếu nại Incident Lockout -> Xử lý giải quyết -> Truy vết Timeline.
    """
    svc = isolated_service
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # 1. Tạo khách DEMO mới chưa có đơn hàng
    res_c = svc.create_customer(CreateCustomerRequest(
        id="KH-DEMO-TEST01",
        name="Võ Thị Ngọc Mai",
        phone="0918889999",
        customer_type="INDIVIDUAL",
        acquisition_source="Hotline tư vấn dinh dưỡng",
        consent_status="Đã đồng ý nhận tin Zalo",
        is_opt_out_marketing=False,
        assigned_staff="Chuyên viên Thảo"
    ))
    assert res_c["status"] == "SUCCESS"
    cust_id = "KH-DEMO-TEST01"

    # 2. Ghi nhận khách hỏi sản phẩm và yêu cầu gọi lại
    res_int = svc.add_interaction(CreateInteractionRequest(
        customer_id=cust_id,
        channel="CALL",
        direction="INBOUND",
        interaction_type="INQUIRY",
        summary="Khách hàng hỏi tư vấn lộ trình bổ sung Canxi cho mẹ bầu 24 tuần, hẹn gọi lại chiều mai",
        performed_by="Chuyên viên Thảo"
    ))
    assert res_int["status"] == "SUCCESS"

    # 3. Tạo yêu cầu gọi lại
    res_cb = svc.add_callback_request(CreateCallbackRequest(
        customer_id=cust_id,
        preferred_date=today_str,
        preferred_time="14:30",
        reason="Tư vấn lộ trình vi chất Canxi Cal-Mom",
        sku="DION-CAL-MOM",
        product_name="Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
        recorded_by="Chuyên viên Thảo"
    ))
    assert res_cb["status"] == "SUCCESS"

    # 4. Kiểm tra: Có việc gọi lại, nhưng KHÔNG có nhắc tái mua vì chưa có đơn giao
    tasks = svc.list_tasks()
    cb_tasks = [t for t in tasks if t.customer_id == cust_id and t.task_type == "SCHEDULED_CALLBACK"]
    reorder_tasks = [t for t in tasks if t.customer_id == cust_id and t.task_type == "REORDER_CHECK_DAY_25"]
    assert len(cb_tasks) >= 1, "Phải có việc gọi lại"
    assert len(reorder_tasks) == 0, "Khách chưa mua hàng không được tự ý sinh việc nhắc tái mua"

    # 5. Ghi nhận đơn tham chiếu thứ nhất và trạng thái giao thành công 7 ngày trước
    d7_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    res_p1 = svc.add_purchase(CreatePurchaseRequest(
        customer_id=cust_id,
        order_id="DH-TEST01-01",
        sku="DION-CAL-MOM",
        product_name="Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
        order_date=(today - timedelta(days=9)).strftime("%Y-%m-%d"),
        delivery_date=d7_ago,
        order_status="DELIVERED",
        purchase_channel="Cửa hàng trực tiếp",
        cycle_days=30,
        quantity=1,
        recorded_by="Chuyên viên Thảo"
    ))
    assert res_p1["status"] == "SUCCESS"

    # 6. Đánh giá quy tắc: Tạo việc hỏi thăm ngày thứ 7 có nguồn gốc
    tasks_after_p1 = svc.list_tasks()
    day7_tasks = [t for t in tasks_after_p1 if t.customer_id == cust_id and t.task_type == "DELIVERY_FOLLOWUP_DAY_7"]
    assert len(day7_tasks) == 1
    t7 = day7_tasks[0]
    assert t7.source_reference_id == "DH-TEST01-01"
    assert t7.purchase_channel == "Cửa hàng trực tiếp"
    assert "Đơn hàng #DH-TEST01-01" in t7.evidence_summary

    # 7. Đánh giá lại: Không tạo việc trùng (Idempotent)
    svc.evaluate_rules()
    tasks_re_eval = svc.list_tasks()
    day7_re = [t for t in tasks_re_eval if t.customer_id == cust_id and t.task_type == "DELIVERY_FOLLOWUP_DAY_7"]
    assert len(day7_re) == 1, "Chạy lại quy tắc không được tạo việc trùng lặp"

    # 8. Ghi nhận đơn thứ hai (Khách mua thêm Vitamin D3 giao thành công 7 ngày trước)
    res_p2 = svc.add_purchase(CreatePurchaseRequest(
        customer_id=cust_id,
        order_id="DH-TEST01-02",
        sku="DION-D3-1000",
        product_name="Vitamin D3 1000IU Drops",
        delivery_date=d7_ago,
        order_status="DELIVERED",
        purchase_channel="Zalo OA DION",
        cycle_days=60,
        quantity=1,
        recorded_by="Chuyên viên Thảo"
    ))
    assert res_p2["status"] == "SUCCESS"
    tasks_after_p2 = svc.list_tasks()
    cust_day7_tasks = [t for t in tasks_after_p2 if t.customer_id == cust_id and t.task_type == "DELIVERY_FOLLOWUP_DAY_7"]
    assert len(cust_day7_tasks) == 2, "Một khách có đơn thứ hai phải sinh công việc riêng theo đơn đó"

    # 9. Ghi nhận phản ánh khiếu nại chất lượng / tác dụng phụ
    res_supp = svc.add_support_request(CreateSupportRequest(
        customer_id=cust_id,
        request_type="COMPLAINT_ADR",
        title="Bị cồn cào và khó chịu",
        description="Khách phản ánh uống vào lúc đói bị cồn cào ruột",
        sku="DION-CAL-MOM",
        product_name="Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
        recorded_by="Chuyên viên Thảo"
    ))
    assert res_supp["status"] == "SUCCESS"

    # 10. Chặn bán thêm trong lúc đang có khiếu nại (Incident Lockout)
    draft_lock = svc.auto_draft_message(cust_id)
    assert draft_lock["decision"] == "BLOCKED"
    assert draft_lock["is_locked"] is True
    assert "INCIDENT LOCKOUT" in draft_lock["message"]

    # 11. Ghi "Đã liên hệ" (CONTACTED): Nhiệm vụ khiếu nại chuyển IN_PROGRESS, CHƯA tự đóng
    complaint_tasks = [t for t in svc.list_tasks() if t.customer_id == cust_id and t.task_type == "COMPLAINT_RESOLUTION"]
    assert len(complaint_tasks) >= 1
    c_task = complaint_tasks[0]

    log_res = svc.log_action(
        task_id=c_task.task_id,
        action_type=ActionType.CONTACTED,
        performed_by="Dược sĩ Trần Mai",
        notes="Đã gọi điện hỏi thăm tình trạng cồn cào, đang hẹn theo dõi thêm"
    )
    assert log_res["status"] == "SUCCESS"
    c_task_updated = svc.get_task(c_task.task_id)
    assert c_task_updated.status == TaskStatus.IN_PROGRESS, "Đã liên hệ (CONTACTED) chưa đồng nghĩa hoàn thành (RESOLVED)"

    # 12. Hẹn lại lịch (Reschedule) và kiểm tra Persistence
    res_sched = svc.reschedule_task(
        task_id=c_task.task_id,
        new_due_date=(today + timedelta(days=2)).strftime("%Y-%m-%d"),
        reschedule_reason="Chờ theo dõi thêm phản ứng sau ăn",
        notes="Dược sĩ hướng dẫn uống sau bữa ăn sáng 30 phút"
    )
    assert res_sched["status"] == "SUCCESS"
    
    # Reload service instance from disk to check persistence
    reloaded_svc = CustomerCareService()
    persisted_task = reloaded_svc.get_task(c_task.task_id)
    assert persisted_task.due_date == (today + timedelta(days=2)).strftime("%Y-%m-%d")

    # 13. Dược sĩ chuyên môn giải quyết khiếu nại (RESOLVED)
    resolve_res = svc.log_action(
        task_id=c_task.task_id,
        action_type=ActionType.RESOLVED,
        performed_by="Dược sĩ Trần Mai",
        notes="Khách đã đổi sang uống sau bữa sáng, tình trạng cồn cào hoàn toàn hết, hài lòng tiếp tục sử dụng."
    )
    assert resolve_res["status"] == "SUCCESS"
    c_task_closed = svc.get_task(c_task.task_id)
    assert c_task_closed.status == TaskStatus.COMPLETED

    # 14. Kiểm tra Timeline truy vết: Đầy đủ chuỗi từ tương tác -> đơn hàng -> yêu cầu hỗ trợ -> nhật ký xử lý
    timeline_res = svc.get_customer_timeline(cust_id)
    assert timeline_res["status"] == "SUCCESS"
    events = timeline_res["timeline"]
    event_types = [e["event_type"] for e in events]
    assert "INTERACTION" in event_types
    assert "PURCHASE" in event_types
    assert "SUPPORT_REQUEST" in event_types
    assert "CARE_TASK" in event_types


def test_02_duplicate_customer_name_not_merged(isolated_service):
    """Hai khách hàng trùng tên không bị gộp sai."""
    svc = isolated_service
    res1 = svc.create_customer(CreateCustomerRequest(
        id="KH-DUP-01",
        name="Nguyễn Văn An",
        phone="0911000111",
        acquisition_source="Hotline"
    ))
    res2 = svc.create_customer(CreateCustomerRequest(
        id="KH-DUP-02",
        name="Nguyễn Văn An",
        phone="0988222333",
        acquisition_source="Zalo OA"
    ))
    assert res1["status"] == "SUCCESS"
    assert res2["status"] == "SUCCESS"

    c1 = svc.get_customer("KH-DUP-01")
    c2 = svc.get_customer("KH-DUP-02")
    assert c1.id != c2.id
    assert c1.phone != c2.phone
    assert len(svc.list_customers()) >= 2


def test_03_b2b_organization_order_no_consumer_created(isolated_service):
    """Đơn bán cho đại lý/nhà thuốc (ORGANIZATION) giữ nguyên nhãn tổ chức, không tự biến thành người tiêu dùng cuối."""
    svc = isolated_service
    res_b2b = svc.create_customer(CreateCustomerRequest(
        id="NT-PHARMAX-01",
        name="Nhà thuốc Pharmax Hà Đông",
        phone="02439998888",
        customer_type="ORGANIZATION",
        acquisition_source="B2B Lead Discovery"
    ))
    assert res_b2b["status"] == "SUCCESS"
    cust = svc.get_customer("NT-PHARMAX-01")
    assert cust.customer_type == "ORGANIZATION"


def test_04_multiple_callbacks_create_separate_tasks(isolated_service):
    """Khách hàng hẹn lần 2 không bị chặn bởi lần 1 (mỗi lần hẹn là 1 task độc lập)."""
    svc = isolated_service
    cust_id = "KH-MULTI-CB"
    svc.create_customer(CreateCustomerRequest(
        id=cust_id,
        name="Đặng Thùy Dung",
        phone="0977665544"
    ))

    # Hẹn lần 1
    svc.add_callback_request(CreateCallbackRequest(
        customer_id=cust_id,
        preferred_date="2026-10-20",
        preferred_time="09:00",
        reason="Hỏi về thời điểm uống canxi"
    ))
    # Hẹn lần 2
    svc.add_callback_request(CreateCallbackRequest(
        customer_id=cust_id,
        preferred_date="2026-10-25",
        preferred_time="15:00",
        reason="Hỏi về kết hợp sắt và vitamin C"
    ))

    tasks = svc.list_tasks()
    cb_tasks = [t for t in tasks if t.customer_id == cust_id and t.task_type == "SCHEDULED_CALLBACK"]
    assert len(cb_tasks) == 2, "Khách hàng có 2 lần hẹn riêng biệt phải sinh 2 task riêng"
    due_dates = {t.due_date for t in cb_tasks}
    assert "2026-10-20" in due_dates
    assert "2026-10-25" in due_dates


def test_05_cancelled_order_cancels_pending_tasks(isolated_service):
    """Đơn hàng bị hủy hoặc hoàn trả đánh giá lại đúng (hủy PENDING task của đơn đó, không xóa lịch sử)."""
    svc = isolated_service
    today = datetime.now()
    d7_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")

    cust_id = "KH-CANCEL-TEST"
    svc.create_customer(CreateCustomerRequest(
        id=cust_id,
        name="Bùi Quốc Toàn",
        phone="0933221100"
    ))

    # Đơn DELIVERED -> sinh task
    svc.add_purchase(CreatePurchaseRequest(
        customer_id=cust_id,
        order_id="DH-CANCEL-01",
        sku="DION-CAL-MOM",
        delivery_date=d7_ago,
        order_status="DELIVERED"
    ))

    tasks_before = [t for t in svc.list_tasks() if t.customer_id == cust_id and getattr(t, "source_reference_id", "") == "DH-CANCEL-01"]
    assert len(tasks_before) == 1
    assert tasks_before[0].status == TaskStatus.PENDING

    # Cập nhật đơn hàng thành CANCELLED
    cust = svc.get_customer(cust_id)
    cust.purchases[0].order_status = "CANCELLED"
    svc.update_customer(cust)
    svc.evaluate_rules()

    tasks_after = [t for t in svc.list_tasks() if t.customer_id == cust_id and getattr(t, "source_reference_id", "") == "DH-CANCEL-01"]
    assert tasks_after[0].status == TaskStatus.CANCELLED, "Task PENDING phải chuyển CANCELLED khi đơn bị hủy"


def test_06_unknown_consent_blocks_marketing_allows_support(isolated_service):
    """Trạng thái consent UNKNOWN chặn tiếp thị nhưng vẫn cho phép hỗ trợ chuyên môn theo yêu cầu."""
    svc = isolated_service
    cust_id = "KH-CONSENT-UNKNOWN"
    svc.create_customer(CreateCustomerRequest(
        id=cust_id,
        name="Lý Mỹ Kỳ",
        phone="0911334455",
        consent_status="UNKNOWN",
        is_opt_out_marketing=False
    ))

    # Khách có đơn hàng ở ngày 25 (mục đích tiếp thị / tái mua)
    d25_ago = (datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d")
    svc.add_purchase(CreatePurchaseRequest(
        customer_id=cust_id,
        order_id="DH-CONSENT-01",
        sku="DION-CAL-MOM",
        product_name="Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
        delivery_date=d25_ago,
        cycle_days=30
    ))

    # Yêu cầu soạn tin tiếp thị (nhắc tái mua) -> Bị chặn do Consent chưa rõ
    draft_mkt = svc.auto_draft_message(cust_id)
    assert draft_mkt["decision"] in ("BLOCKED", "PRIVACY_BLOCKED")

    # Tiếp nhận yêu cầu gọi lại hỗ trợ -> Được phép tạo việc
    svc.add_callback_request(CreateCallbackRequest(
        customer_id=cust_id,
        preferred_date="2026-10-21",
        reason="Khách chủ động nhờ Dược sĩ tư vấn"
    ))
    cb_tasks = [t for t in svc.list_tasks() if t.customer_id == cust_id and t.task_type == "SCHEDULED_CALLBACK"]
    assert len(cb_tasks) == 1
    assert cb_tasks[0].status == TaskStatus.PENDING


def test_07_tab4_copilot_linking(isolated_service):
    """Gắn phiên tư vấn Tab 4 vào hồ sơ khách hàng: Phân biệt lưu nháp nội bộ vs xác nhận tương tác."""
    svc = isolated_service
    cust_id = "KH-COPILOT-LINK"
    svc.create_customer(CreateCustomerRequest(
        id=cust_id,
        name="Trương Gia Bình",
        phone="0909090909"
    ))

    # 1. Lưu bản nháp nội bộ
    res_draft = svc.link_copilot_interaction(LinkCopilotInteractionRequest(
        customer_id=cust_id,
        session_id="SESS-1234",
        chat_summary="AI đề xuất bổ sung Canxi và D3 cho người cao tuổi",
        is_confirmed_interaction=False
    ))
    assert res_draft["status"] == "SUCCESS"
    assert res_draft["is_confirmed"] is False

    cust = svc.get_customer(cust_id)
    assert len(cust.interactions) == 1
    assert cust.interactions[0].is_staff_confirmed is False

    # 2. Nhân viên xác nhận ĐÃ TƯ VẤN cho khách
    res_confirmed = svc.link_copilot_interaction(LinkCopilotInteractionRequest(
        customer_id=cust_id,
        session_id="SESS-1234",
        chat_summary="Đã gọi điện tư vấn thành công cách uống Canxi sau ăn sáng",
        is_confirmed_interaction=True,
        channel="CALL"
    ))
    assert res_confirmed["status"] == "SUCCESS"
    assert res_confirmed["is_confirmed"] is True

    cust_updated = svc.get_customer(cust_id)
    assert len(cust_updated.interactions) == 2
    assert cust_updated.interactions[1].is_staff_confirmed is True


def test_08_csv_import_customers_and_purchases(isolated_service):
    """Import file CSV UTF-8: Kiểm tra preview, báo lỗi dòng, không tự ý gán quyền."""
    svc = isolated_service

    csv_cust_data = """id,name,phone,email,customer_type,consent_status,assigned_staff
KH-IMP-01,Hà Thị Liễu,0981112223,lieu@gmail.com,INDIVIDUAL,Đã đồng ý nhận tin Zalo,Chuyên viên Thảo
KH-IMP-02,Đoàn Văn Hậu,,hau@gmail.com,INDIVIDUAL,UNKNOWN,Chuyên viên Nam
"""
    # Preview
    prev = svc.import_customers_csv(csv_cust_data, dry_run=True)
    assert prev["total_rows"] == 2
    assert prev["valid_count"] == 1
    assert prev["error_count"] == 1  # Dòng 2 thiếu SĐT

    # Execute
    exec_res = svc.import_customers_csv(csv_cust_data, dry_run=False)
    assert exec_res["valid_count"] == 1
    assert svc.get_customer("KH-IMP-01") is not None


def test_09_api_endpoints_e2e_with_testclient(tmp_path):
    """Kiểm thử trực tiếp qua HTTP API Client các endpoint mới của Customer Care."""
    cust_file = str(tmp_path / "api_care_customers.json")
    task_file = str(tmp_path / "api_care_tasks.json")

    import modules.customer_care.service as s_mod
    orig_c = s_mod.CUSTOMERS_FILE
    orig_t = s_mod.TASKS_FILE
    s_mod.CUSTOMERS_FILE = cust_file
    s_mod.TASKS_FILE = task_file

    client = TestClient(app)

    # 1. POST /api/customer-care/customers (Tạo khách DEMO)
    res = client.post("/api/customer-care/customers", json={
        "name": "Trần Thị Bích Ngọc",
        "phone": "0987654321",
        "customer_type": "INDIVIDUAL",
        "acquisition_source": "Zalo OA",
        "consent_status": "Đã đồng ý nhận tin Zalo",
        "assigned_staff": "Dược sĩ Trần Mai",
        "is_demo": True
    })
    assert res.status_code == 200
    data_c = res.json()
    assert data_c["status"] == "SUCCESS"
    cust_id = data_c["customer"]["id"]

    # 2. POST /api/customer-care/interactions (Ghi nhận tương tác)
    res_int = client.post("/api/customer-care/interactions", json={
        "customer_id": cust_id,
        "channel": "Cuộc gọi thoại",
        "direction": "INBOUND",
        "interaction_type": "Hỏi giá / Tìm hiểu",
        "occurred_at": datetime.now().isoformat(),
        "summary": "Khách hỏi giá Cal-Mom và thời điểm uống trong ngày",
        "is_staff_confirmed": True,
        "performed_by": "Dược sĩ Trần Mai"
    })
    assert res_int.status_code == 200
    assert res_int.json()["status"] == "SUCCESS"

    # 3. POST /api/customer-care/purchases (Ghi nhận đơn tham chiếu DELIVERED)
    d7_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    res_pur = client.post("/api/customer-care/purchases", json={
        "customer_id": cust_id,
        "order_id": "DH-API-001",
        "sku": "Cal-Mom",
        "quantity": 1,
        "purchase_channel": "Nhà thuốc Long Châu",
        "order_status": "DELIVERED",
        "transaction_date": d7_ago,
        "delivered_at": d7_ago + " 10:00:00",
        "recording_source": "Biểu mẫu nhập tay",
        "recorded_by": "Nhân viên ghi nhận (PoC)",
        "auto_evaluate_rules": True
    })
    assert res_pur.status_code == 200
    assert res_pur.json()["status"] == "SUCCESS"

    # 4. GET /api/customer-care/customers/{customer_id}/timeline (Xem dòng thời gian)
    res_tl = client.get(f"/api/customer-care/customers/{cust_id}/timeline")
    assert res_tl.status_code == 200
    tl_data = res_tl.json()
    assert tl_data["status"] == "SUCCESS"
    cats = [e["category"] for e in tl_data["timeline"]]
    assert "INTERACTION" in cats
    assert "PURCHASE" in cats

    # 5. POST /api/customer-care/import/preview & execute
    csv_text = "id,name,customer_type,phone,acquisition_source,consent_status,assignee,is_demo\nCUST-CSV-01,Phạm Văn Nam,INDIVIDUAL,0912111222,Hotline,Đã đồng ý nhận tin Zalo,CSKH,true"
    res_prev = client.post("/api/customer-care/import/preview", json={
        "import_type": "customers",
        "csv_content": csv_text
    })
    assert res_prev.status_code == 200
    assert res_prev.json()["valid_count"] == 1

    res_exec = client.post("/api/customer-care/import/execute", json={
        "import_type": "customers",
        "csv_content": csv_text
    })
    assert res_exec.status_code == 200
    assert res_exec.json()["imported_count"] == 1

    # 6. POST /api/customer-care/link-copilot-interaction (Tab 4 -> Tab 5)
    res_link = client.post("/api/customer-care/link-copilot-interaction", json={
        "customer_id": cust_id,
        "consultation_notes": "Tư vấn bổ sung canxi và D3 hỗ trợ giảm chuột rút thai kỳ",
        "is_staff_confirmed": True,
        "channel": "Zalo OA"
    })
    assert res_link.status_code == 200
    assert res_link.json()["status"] == "SUCCESS"

    # Cleanup
    s_mod.CUSTOMERS_FILE = orig_c
    s_mod.TASKS_FILE = orig_t


def test_10_fake_auth_rejected_for_real_records():
    """Kiểm tra Header hoặc Cookie giả mạo không được coi là xác thực thật cho bản ghi dữ liệu thực."""
    client = TestClient(app)

    # Thử gọi với Fake Authorization header trên bản ghi không phải demo
    res = client.post(
        "/api/customer-care/customers",
        headers={"Authorization": "Bearer fake_token_abc"},
        json={
            "name": "Doanh Nghiệp Thật",
            "phone": "0912345678",
            "is_demo": False
        }
    )
    # Backend phải từ chối 401 khi chưa triển khai auth thật cho bản ghi thực
    assert res.status_code == 401
    assert "AUTH_NOT_IMPLEMENTED" in res.json().get("detail", "")

