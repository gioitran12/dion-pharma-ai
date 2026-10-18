# -*- coding: utf-8 -*-
"""
DION Healthcare AI — Customer Care Service
Xử lý toàn bộ logic nghiệp vụ Chăm sóc Khách hàng, Quản lý Tương tác, Đơn hàng tham chiếu,
Sự kiện phát sinh việc, Đánh giá Quy tắc Chu kỳ, Kiểm soát Quyền riêng tư (Consent / Opt-out)
và Truy vết nguồn gốc (Traceability).
"""

import os
import csv
import io
import json
import uuid
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from modules.customer_care.schemas import (
    CustomerRecord, CareTask, PurchaseRecord, CareInteraction, SupportRequest, CallbackRequest,
    ActionType, TaskPriority, TaskStatus, CustomerCareMetrics, CustomerType,
    CreateCustomerRequest, CreateInteractionRequest, CreatePurchaseRequest,
    CreateSupportRequest, CreateCallbackRequest, LinkCopilotInteractionRequest
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customer_care_customers.json")
TASKS_FILE = os.path.join(DATA_DIR, "customer_care_tasks.json")

# Danh sách nhân viên được cấp quyền thực hiện thao tác
AUTHORIZED_STAFF = [
    "Dược sĩ Trần Mai", "Dược sĩ Lê Hoàng", "Chuyên viên CSKH", "Chuyên viên Thảo", 
    "Chuyên viên Nam", "Dược vụ", "Nhân viên kiểm thử", "NV Test", "Hệ thống"
]

# Danh sách nhân sự chuyên môn có thẩm quyền đóng khiếu nại chất lượng / ADR
AUTHORIZED_CLINICAL_STAFF = [
    "Dược sĩ Trần Mai", "Dược sĩ Lê Hoàng", "Dược vụ", "Nhân viên kiểm thử", "NV Test", "Hệ thống"
]

_file_lock = threading.Lock()
_service_lock = threading.RLock()


def _get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _get_now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _atomic_json_write(filepath: str, data: Any):
    """Ghi tệp JSON nguyên tử (atomic) tránh xung đột và hỏng dữ liệu khi ghi đồng thời."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp_path = f"{filepath}.tmp_{uuid.uuid4().hex[:6]}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, filepath)


class CustomerCareService:
    """Service nghiệp vụ điều phối công việc CSKH, quy tắc chu kỳ, truy vết nguồn gốc và quyền riêng tư."""

    def __init__(self):
        self._init_seed_data_if_needed()

    def _init_seed_data_if_needed(self):
        """Khởi tạo dữ liệu seed mẫu (được gắn nhãn DEMO rõ ràng) nếu chưa có tệp lưu trữ."""
        with _service_lock:
            os.makedirs(DATA_DIR, exist_ok=True)

            if not os.path.exists(CUSTOMERS_FILE):
                today = datetime.now()
                d7_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
                d14_ago = (today - timedelta(days=14)).strftime("%Y-%m-%d")
                d25_ago = (today - timedelta(days=25)).strftime("%Y-%m-%d")
                d35_ago = (today - timedelta(days=35)).strftime("%Y-%m-%d")

                seed_customers = [
                    {
                        "id": "KH-8821",
                        "name": "Nguyễn Thị Hương",
                        "phone": "0982***821",
                        "customer_type": "INDIVIDUAL",
                        "acquisition_source": "Hotline tư vấn",
                        "consent_status": "Đã đồng ý nhận tin Zalo",
                        "is_opt_out_marketing": False,
                        "active_complaint": None,
                        "complaint_status": "Bình thường",
                        "complaint_history": [],
                        "assigned_staff": "Chuyên viên Thảo",
                        "is_demo": True,
                        "purchases": [
                            {
                                "order_id": "DH-2026-8821",
                                "sku": "DION-CAL-MOM",
                                "product_name": "Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
                                "delivery_date": d25_ago,
                                "order_date": (today - timedelta(days=27)).strftime("%Y-%m-%d"),
                                "cycle_days": 30,
                                "quantity": 1,
                                "purchase_channel": "Cửa hàng trực tiếp",
                                "source_system": "MANUAL_ENTRY",
                                "order_status": "DELIVERED",
                                "recording_method": "MANUAL",
                                "recorded_by": "Chuyên viên Thảo",
                                "verification_status": "Nhân viên ghi nhận"
                            }
                        ],
                        "interactions": []
                    },
                    {
                        "id": "KH-9042",
                        "name": "Lê Văn Tuấn",
                        "phone": "0915***042",
                        "customer_type": "INDIVIDUAL",
                        "acquisition_source": "Zalo OA DION",
                        "consent_status": "Đã đồng ý nhận SMS",
                        "is_opt_out_marketing": False,
                        "active_complaint": "Tôi uống vào thấy bị cồn cào và buồn nôn khó chịu lắm shop ơi!",
                        "complaint_status": "Đang có khiếu nại chất lượng / ADR",
                        "complaint_history": [],
                        "assigned_staff": "Chuyên viên Nam",
                        "is_demo": True,
                        "purchases": [
                            {
                                "order_id": "DH-2026-9042",
                                "sku": "DION-D3-1000",
                                "product_name": "Vitamin D3 1000IU Drops",
                                "delivery_date": d7_ago,
                                "order_date": (today - timedelta(days=9)).strftime("%Y-%m-%d"),
                                "cycle_days": 60,
                                "quantity": 1,
                                "purchase_channel": "Shopee Mall DION",
                                "source_system": "MANUAL_ENTRY",
                                "order_status": "DELIVERED",
                                "recording_method": "MANUAL",
                                "recorded_by": "Chuyên viên Nam",
                                "verification_status": "Nhân viên ghi nhận"
                            }
                        ],
                        "interactions": []
                    },
                    {
                        "id": "KH-7119",
                        "name": "Trần Thu Hà",
                        "phone": "0903***119",
                        "customer_type": "INDIVIDUAL",
                        "acquisition_source": "Website dion.vn",
                        "consent_status": "Khách hàng đã Opt-out",
                        "is_opt_out_marketing": True,
                        "active_complaint": "Khách phản ánh bị đầy hơi và xót dạ dày khi uống viên sắt",
                        "complaint_status": "Đang có khiếu nại tiêu hóa",
                        "complaint_history": [],
                        "assigned_staff": "Dược sĩ Trần Mai",
                        "is_demo": True,
                        "purchases": [
                            {
                                "order_id": "DH-2026-7119",
                                "sku": "DION-FE-FOLIC",
                                "product_name": "Viên Sắt Hữu Cơ & Quatrefolic DION Fero-Plus",
                                "delivery_date": d14_ago,
                                "order_date": (today - timedelta(days=16)).strftime("%Y-%m-%d"),
                                "cycle_days": 30,
                                "quantity": 1,
                                "purchase_channel": "TikTok Shop",
                                "source_system": "MANUAL_ENTRY",
                                "order_status": "DELIVERED",
                                "recording_method": "MANUAL",
                                "recorded_by": "Dược sĩ Trần Mai",
                                "verification_status": "Nhân viên ghi nhận"
                            }
                        ],
                        "interactions": []
                    },
                    {
                        "id": "KH-6502",
                        "name": "Phạm Hoàng Nam",
                        "phone": "0977***502",
                        "customer_type": "INDIVIDUAL",
                        "acquisition_source": "Nhà thuốc đối tác giới thiệu",
                        "consent_status": "Khách hàng đã Opt-out",
                        "is_opt_out_marketing": True,
                        "active_complaint": None,
                        "complaint_status": "Bình thường",
                        "complaint_history": [],
                        "assigned_staff": "Dược sĩ Trần Mai",
                        "is_demo": True,
                        "callback_requested": True,
                        "callback_reason": "Khách hàng đã yêu cầu gọi lại vào hôm nay để được Dược sĩ tư vấn chuyên sâu về lộ trình kết hợp vi chất.",
                        "callback_sku": "DION-CAL-MOM",
                        "callback_product_name": "Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
                        "purchases": [
                            {
                                "order_id": "DH-2026-6502",
                                "sku": "DION-CAL-MOM",
                                "product_name": "Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
                                "delivery_date": d35_ago,
                                "order_date": (today - timedelta(days=37)).strftime("%Y-%m-%d"),
                                "cycle_days": 30,
                                "quantity": 2,
                                "purchase_channel": "Nhà thuốc An Khang",
                                "source_system": "MANUAL_ENTRY",
                                "order_status": "DELIVERED",
                                "recording_method": "MANUAL",
                                "recorded_by": "Dược sĩ Trần Mai",
                                "verification_status": "Nhân viên ghi nhận"
                            }
                        ],
                        "interactions": []
                    }
                ]
                self._save_customers_raw(seed_customers)

            if not os.path.exists(TASKS_FILE):
                self._save_tasks_raw([])
                self.evaluate_rules()
            else:
                self.evaluate_rules()

    def _load_customers_raw(self) -> List[Dict[str, Any]]:
        with _file_lock:
            if not os.path.exists(CUSTOMERS_FILE):
                return []
            try:
                with open(CUSTOMERS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []

    def _save_customers_raw(self, data: List[Dict[str, Any]]):
        with _file_lock:
            _atomic_json_write(CUSTOMERS_FILE, data)

    def _load_tasks_raw(self) -> List[Dict[str, Any]]:
        with _file_lock:
            if not os.path.exists(TASKS_FILE):
                return []
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []

    def _save_tasks_raw(self, data: List[Dict[str, Any]]):
        with _file_lock:
            _atomic_json_write(TASKS_FILE, data)

    def list_customers(self) -> List[CustomerRecord]:
        with _service_lock:
            raw = self._load_customers_raw()
            return [CustomerRecord(**c) for c in raw]

    def get_customer(self, customer_id: str) -> Optional[CustomerRecord]:
        with _service_lock:
            customers = self.list_customers()
            for c in customers:
                if c.id.lower() == customer_id.lower():
                    return c
            return None

    def update_customer(self, customer: CustomerRecord):
        with _service_lock:
            raw = self._load_customers_raw()
            updated = []
            found = False
            for c in raw:
                if c["id"].lower() == customer.id.lower():
                    updated.append(customer.model_dump())
                    found = True
                else:
                    updated.append(c)
            if not found:
                updated.append(customer.model_dump())
            self._save_customers_raw(updated)

    def list_tasks(self) -> List[CareTask]:
        with _service_lock:
            raw = self._load_tasks_raw()
            today_str = _get_today_str()
            tasks = []
            for t in raw:
                task = CareTask(**t)
                is_closed = task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.BLOCKED) or task.is_blocked
                task.is_due_today = (task.due_date == today_str) and not is_closed
                task.is_overdue = (task.due_date < today_str) and not is_closed
                tasks.append(task)

            priority_order = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}
            tasks.sort(key=lambda x: (
                0 if x.status not in (TaskStatus.COMPLETED, TaskStatus.BLOCKED) and not x.is_blocked else 1,
                priority_order.get(x.priority, 1),
                x.due_date
            ))
            return tasks

    def get_task(self, task_id: str) -> Optional[CareTask]:
        with _service_lock:
            tasks = self.list_tasks()
            for t in tasks:
                if t.task_id.lower() == task_id.lower():
                    return t
            return None

    def update_task(self, task: CareTask):
        with _service_lock:
            raw = self._load_tasks_raw()
            updated = []
            found = False
            for t in raw:
                if t.get("task_id", "").lower() == task.task_id.lower():
                    updated.append(task.model_dump())
                    found = True
                else:
                    updated.append(t)
            if not found:
                updated.append(task.model_dump())
            self._save_tasks_raw(updated)

    # ==============================================================================
    # QUẢN LÝ DỮ LIỆU ĐẦU VÀO & TRUY VẾT NGUỒN GỐC (MILESTONE A)
    # ==============================================================================

    def create_customer(self, req: CreateCustomerRequest) -> Dict[str, Any]:
        """Tạo hồ sơ khách hàng mới có nguồn gốc, kiểm tra trùng lặp số điện thoại."""
        with _service_lock:
            customers = self.list_customers()
            new_id = (req.id or "").strip()
            if not new_id:
                # Sinh ID mới không trùng lặp
                existing_nums = []
                for c in customers:
                    if c.id.startswith("KH-"):
                        try:
                            existing_nums.append(int(c.id[3:]))
                        except Exception:
                            pass
                next_num = max(existing_nums) + 1 if existing_nums else 1001
                new_id = f"KH-{next_num}"

            # Kiểm tra ID đã tồn tại
            if any(c.id.lower() == new_id.lower() for c in customers):
                return {"status": "ERROR", "code": "ID_EXISTS", "message": f"Mã khách hàng '{new_id}' đã tồn tại trong hệ thống."}

            # Kiểm tra khả năng trùng SĐT (không tự ý gộp, hiển thị cảnh báo để đối chiếu)
            phone_dup = [c for c in customers if c.phone and req.phone and c.phone.replace("*", "") == req.phone.replace("*", "")]
            dup_warning = None
            if phone_dup:
                dup_warning = f"LƯU Ý ĐỐI SOÁT: Số điện thoại '{req.phone}' trùng khớp với khách {phone_dup[0].id} ({phone_dup[0].name}). Không tự động gộp hồ sơ."

            new_customer = CustomerRecord(
                id=new_id,
                name=req.name.strip(),
                phone=req.phone.strip(),
                email=req.email.strip() if req.email else "",
                customer_type=req.customer_type or "INDIVIDUAL",
                acquisition_source=req.acquisition_source or "Nhập thủ công",
                external_source_id=req.external_source_id,
                consent_status=req.consent_status or "Đã đồng ý nhận tin Zalo",
                is_opt_out_marketing=req.is_opt_out_marketing or False,
                assigned_staff=req.assigned_staff or "Chuyên viên CSKH",
                is_demo=True,
                purchases=[],
                interactions=[]
            )

            # Nếu có ghi chú ban đầu, tạo 1 interaction ghi chú
            if req.notes and req.notes.strip():
                new_customer.interactions.append(
                    CareInteraction(
                        customer_id=new_id,
                        action_type=ActionType.CONTACTED,
                        channel="DIRECT",
                        direction="INBOUND",
                        interaction_type="NOTE",
                        summary=req.notes.strip(),
                        occurred_at=_get_now_str(),
                        recorded_at=_get_now_str(),
                        performed_by=req.assigned_staff or "Chuyên viên CSKH",
                        is_staff_confirmed=True
                    )
                )

            self.update_customer(new_customer)
            self.evaluate_rules()

            return {
                "status": "SUCCESS",
                "customer": new_customer.model_dump(),
                "warning": dup_warning,
                "message": f"Đã tạo hồ sơ khách hàng {new_customer.name} ({new_customer.id})"
            }

    def add_interaction(self, req: CreateInteractionRequest) -> Dict[str, Any]:
        """Ghi nhận tương tác thực tế với khách hàng có kênh, chiều tương tác và thời điểm thực tế."""
        with _service_lock:
            cust = self.get_customer(req.customer_id)
            if not cust:
                return {"status": "ERROR", "code": "CUSTOMER_NOT_FOUND", "message": f"Không tìm thấy khách hàng {req.customer_id}"}

            now_str = _get_now_str()
            occurred_time = req.occurred_at.strip() if req.occurred_at and req.occurred_at.strip() else now_str

            interaction = CareInteraction(
                customer_id=cust.id,
                channel=req.channel or "CALL",
                action_type=ActionType.CONTACTED,
                direction=req.direction or "INBOUND",
                interaction_type=req.interaction_type or "CONSULTATION",
                summary=req.summary.strip(),
                notes=req.summary.strip(),
                occurred_at=occurred_time,
                recorded_at=now_str,
                performed_by=req.performed_by or "Chuyên viên CSKH",
                reference_note=req.reference_note,
                is_staff_confirmed=True
            )

            cust.interactions.append(interaction)
            self.update_customer(cust)
            self.evaluate_rules()

            return {
                "status": "SUCCESS",
                "interaction": interaction.model_dump(),
                "message": f"Đã ghi nhận tương tác ({req.channel}) cho khách hàng {cust.name}"
            }

    def add_purchase(self, req: CreatePurchaseRequest) -> Dict[str, Any]:
        """Ghi nhận giao dịch / đơn hàng tham chiếu có kênh bán, trạng thái giao và căn cứ chu kỳ."""
        with _service_lock:
            cust = self.get_customer(req.customer_id)
            if not cust:
                return {"status": "ERROR", "code": "CUSTOMER_NOT_FOUND", "message": f"Không tìm thấy khách hàng {req.customer_id}"}

            # Xác định tên sản phẩm nếu chưa có
            p_name = req.product_name or ""
            if not p_name:
                sku_names = {
                    "DION-CAL-MOM": "Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2",
                    "DION-D3-1000": "Vitamin D3 1000IU Drops",
                    "DION-FE-FOLIC": "Viên Sắt Hữu Cơ & Quatrefolic DION Fero-Plus"
                }
                p_name = sku_names.get(req.sku, f"Sản phẩm {req.sku}")

            order_id = req.order_id.strip() if req.order_id and req.order_id.strip() else f"DH-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
            o_date = req.order_date or req.transaction_date or _get_today_str()
            d_date = req.delivery_date or req.delivered_at

            purchase = PurchaseRecord(
                order_id=order_id,
                customer_id=cust.id,
                sku=req.sku,
                product_name=p_name,
                order_date=o_date,
                delivery_date=d_date,
                cycle_days=req.cycle_days if req.cycle_days > 0 else 30,
                quantity=req.quantity if req.quantity > 0 else 1,
                purchase_channel=req.purchase_channel or "Cửa hàng trực tiếp",
                source_order_code=req.source_order_code,
                order_status=req.order_status or "DELIVERED",
                source_system="MANUAL_ENTRY",
                recording_method="MANUAL",
                recorded_by=req.recorded_by or "Chuyên viên CSKH",
                verification_status="Nhân viên ghi nhận",
                notes=req.notes or ""
            )

            cust.purchases.append(purchase)
            self.update_customer(cust)
            self.evaluate_rules()

            return {
                "status": "SUCCESS",
                "purchase": purchase.model_dump(),
                "message": f"Đã ghi nhận đơn hàng {order_id} ({p_name}) cho khách {cust.name}"
            }

    def add_support_request(self, req: CreateSupportRequest) -> Dict[str, Any]:
        """Ghi nhận yêu cầu hỗ trợ hoặc phản ánh chất lượng / ADR từ khách hàng."""
        with _service_lock:
            cust = self.get_customer(req.customer_id)
            if not cust:
                return {"status": "ERROR", "code": "CUSTOMER_NOT_FOUND", "message": f"Không tìm thấy khách hàng {req.customer_id}"}

            now_str = _get_now_str()
            support_req = SupportRequest(
                customer_id=cust.id,
                customer_name=cust.name,
                request_type=req.request_type or "COMPLAINT_ADR",
                title=req.title.strip(),
                description=req.description.strip(),
                sku=req.sku,
                product_name=req.product_name,
                occurred_at=req.occurred_at or now_str,
                recorded_at=now_str,
                recorded_by=req.recorded_by or "Chuyên viên CSKH",
                status="PENDING",
                source="Nhân viên ghi nhận"
            )

            cust.support_requests.append(support_req)

            # Nếu là khiếu nại chất lượng hoặc ADR -> kích hoạt active_complaint trên hồ sơ
            if req.request_type in ("COMPLAINT_ADR", "COMPLAINT_QUALITY"):
                cust.active_complaint = f"{req.title}: {req.description}"
                cust.complaint_status = "Đang có khiếu nại chất lượng / ADR"

            self.update_customer(cust)
            self.evaluate_rules()

            return {
                "status": "SUCCESS",
                "request": support_req.model_dump(),
                "message": f"Đã tiếp nhận yêu cầu hỗ trợ ({req.request_type}) cho khách {cust.name}"
            }

    def add_callback_request(self, req: CreateCallbackRequest) -> Dict[str, Any]:
        """Ghi nhận yêu cầu gọi lại theo ngày giờ hẹn cụ thể của khách."""
        with _service_lock:
            cust = self.get_customer(req.customer_id)
            if not cust:
                return {"status": "ERROR", "code": "CUSTOMER_NOT_FOUND", "message": f"Không tìm thấy khách hàng {req.customer_id}"}

            now_str = _get_now_str()
            cb_req = CallbackRequest(
                customer_id=cust.id,
                customer_name=cust.name,
                preferred_date=req.preferred_date.strip().split()[0],
                preferred_time=req.preferred_time or "09:30",
                reason=req.reason.strip(),
                sku=req.sku,
                product_name=req.product_name,
                occurred_at=req.occurred_at or now_str,
                recorded_at=now_str,
                recorded_by=req.recorded_by or "Chuyên viên CSKH",
                status="PENDING",
                source="Nhân viên ghi nhận"
            )

            cust.callback_requests.append(cb_req)
            cust.callback_requested = True
            cust.callback_reason = req.reason
            cust.callback_preferred_date = cb_req.preferred_date
            cust.callback_preferred_time = cb_req.preferred_time
            if req.sku:
                cust.callback_sku = req.sku
                cust.callback_product_name = req.product_name

            self.update_customer(cust)
            self.evaluate_rules()

            return {
                "status": "SUCCESS",
                "callback": cb_req.model_dump(),
                "message": f"Đã đặt lịch hẹn gọi lại ngày {cb_req.preferred_date} cho khách {cust.name}"
            }

    def get_customer_timeline(self, customer_id: str) -> Dict[str, Any]:
        """Truy xuất toàn bộ dòng thời gian (Timeline) đa chiều của khách hàng."""
        with _service_lock:
            cust = self.get_customer(customer_id)
            if not cust:
                return {"status": "ERROR", "message": f"Không tìm thấy khách hàng {customer_id}"}

            all_tasks = [t for t in self.list_tasks() if t.customer_id.lower() == customer_id.lower()]

            timeline_events = []

            # 1. Tương tác trao đổi
            for it in cust.interactions:
                t_time = it.occurred_at or it.timestamp
                timeline_events.append({
                    "event_type": "INTERACTION",
                    "category": "INTERACTION",
                    "id": it.id,
                    "title": f"Tương tác qua {it.channel} ({it.direction})",
                    "time": t_time,
                    "recorded_at": it.recorded_at or it.timestamp,
                    "summary": it.summary or it.notes,
                    "performed_by": it.performed_by,
                    "badge": it.channel,
                    "badge_color": "blue",
                    "details": {
                        "direction": it.direction,
                        "interaction_type": it.interaction_type,
                        "reference_note": it.reference_note
                    }
                })

            # 2. Đơn hàng tham chiếu
            for p in cust.purchases:
                order_time = p.order_date or p.delivery_date or "2026-10-01"
                status_color = "emerald" if p.order_status == "DELIVERED" else ("rose" if p.order_status in ("CANCELLED", "RETURNED") else "amber")
                timeline_events.append({
                    "event_type": "PURCHASE",
                    "category": "PURCHASE",
                    "id": p.order_id,
                    "title": f"Đơn hàng #{p.order_id} ({p.order_status})",
                    "time": order_time,
                    "recorded_at": order_time,
                    "summary": f"{p.product_name} (Số lượng: {p.quantity}) qua kênh {p.purchase_channel}",
                    "performed_by": p.recorded_by,
                    "badge": p.order_status,
                    "badge_color": status_color,
                    "details": {
                        "sku": p.sku,
                        "delivery_date": p.delivery_date,
                        "cycle_days": p.cycle_days,
                        "purchase_channel": p.purchase_channel,
                        "verification_status": p.verification_status
                    }
                })

            # 3. Yêu cầu hỗ trợ / Khiếu nại
            for sr in getattr(cust, "support_requests", []):
                timeline_events.append({
                    "event_type": "SUPPORT_REQUEST",
                    "category": "SUPPORT",
                    "id": sr.request_id,
                    "title": f"Yêu cầu hỗ trợ: {sr.title}",
                    "time": sr.occurred_at,
                    "recorded_at": sr.recorded_at,
                    "summary": sr.description,
                    "performed_by": sr.recorded_by,
                    "badge": sr.request_type,
                    "badge_color": "rose" if "COMPLAINT" in sr.request_type else "purple",
                    "details": {
                        "status": sr.status,
                        "sku": sr.sku,
                        "resolution_notes": sr.resolution_notes
                    }
                })

            # 4. Yêu cầu gọi lại
            for cb in getattr(cust, "callback_requests", []):
                timeline_events.append({
                    "event_type": "CALLBACK_REQUEST",
                    "category": "CALLBACK",
                    "id": cb.callback_id,
                    "title": f"Hẹn gọi lại lúc {cb.preferred_time} ngày {cb.preferred_date}",
                    "time": cb.occurred_at,
                    "recorded_at": cb.recorded_at,
                    "summary": f"Lý do: {cb.reason}",
                    "performed_by": cb.recorded_by,
                    "badge": "LỊCH HẸN",
                    "badge_color": "purple",
                    "details": {
                        "status": cb.status,
                        "preferred_date": cb.preferred_date,
                        "preferred_time": cb.preferred_time
                    }
                })

            # 5. Các công việc và nhật ký xử lý
            for t in all_tasks:
                timeline_events.append({
                    "event_type": "CARE_TASK",
                    "category": "CARE_TASK",
                    "id": t.task_id,
                    "title": f"Công việc: {t.title}",
                    "time": t.created_at,
                    "recorded_at": t.updated_at,
                    "summary": t.reason,
                    "performed_by": t.assignee,
                    "badge": t.status.value if hasattr(t.status, "value") else str(t.status),
                    "badge_color": "emerald" if t.status == TaskStatus.COMPLETED else ("amber" if t.status == TaskStatus.BLOCKED else "blue"),
                    "details": {
                        "priority": t.priority.value if hasattr(t.priority, "value") else str(t.priority),
                        "due_date": t.due_date,
                        "logs_count": len(t.logs)
                    }
                })

            # Sắp xếp thời gian giảm dần (mới nhất lên đầu)
            timeline_events.sort(key=lambda x: str(x.get("time") or ""), reverse=True)

            return {
                "status": "SUCCESS",
                "customer": cust.model_dump(),
                "tasks": [t.model_dump() for t in all_tasks],
                "timeline": timeline_events
            }

    def link_copilot_interaction(self, req: LinkCopilotInteractionRequest) -> Dict[str, Any]:
        """Gắn hội thoại / tư vấn từ Tab 4 (Sales Copilot) vào hồ sơ khách hàng đã chọn."""
        with _service_lock:
            cust = self.get_customer(req.customer_id)
            if not cust:
                return {"status": "ERROR", "code": "CUSTOMER_NOT_FOUND", "message": f"Không tìm thấy khách hàng {req.customer_id}"}

            now_str = _get_now_str()
            summary_content = (req.chat_summary or req.consultation_notes or "Tư vấn Copilot").strip()
            is_confirmed = req.is_confirmed_interaction or bool(req.is_staff_confirmed)

            if is_confirmed:
                # Nhân viên xác nhận ĐÃ TƯ VẤN THỰC TẾ với khách hàng
                interaction = CareInteraction(
                    customer_id=cust.id,
                    channel=req.channel or "ZALO",
                    action_type=ActionType.CONTACTED,
                    direction=req.direction or "INBOUND",
                    interaction_type="CONSULTATION",
                    summary=f"[Tư vấn Copilot] {summary_content}",
                    notes=f"Tương tác tư vấn bán hàng được xác nhận từ phiên chat Copilot #{req.session_id or 'direct'}",
                    occurred_at=now_str,
                    recorded_at=now_str,
                    performed_by=req.performed_by or "Chuyên viên CSKH",
                    reference_note=f"Phiên Copilot #{req.session_id or 'direct'}",
                    is_staff_confirmed=True
                )
                cust.interactions.append(interaction)
                msg = f"Đã lưu và xác nhận tương tác tư vấn với khách hàng {cust.name}."
            else:
                # Chỉ lưu bản nháp / ghi chú nội bộ (KHÔNG đồng nghĩa đã tư vấn hoặc đã mua)
                interaction = CareInteraction(
                    customer_id=cust.id,
                    channel="INTERNAL_NOTE",
                    action_type=ActionType.DRAFT_CREATED,
                    direction="INBOUND",
                    interaction_type="NOTE",
                    summary=f"[Bản nháp nội bộ] {summary_content}",
                    notes="Nội dung tư vấn đề xuất từ Sales Copilot được nhân viên lưu tham chiếu nội bộ.",
                    occurred_at=now_str,
                    recorded_at=now_str,
                    performed_by=req.performed_by or "Chuyên viên CSKH",
                    reference_note=f"Bản nháp Copilot #{req.session_id or 'direct'}",
                    is_staff_confirmed=False
                )
                cust.interactions.append(interaction)
                msg = f"Đã lưu bản nháp tư vấn nội bộ vào hồ sơ khách hàng {cust.name}."

            self.update_customer(cust)
            self.evaluate_rules()

            return {
                "status": "SUCCESS",
                "is_confirmed": is_confirmed,
                "customer_id": cust.id,
                "customer_name": cust.name,
                "message": msg
            }

    # ==============================================================================
    # SINH CÔNG VIỆC TỪ SỰ KIỆN & ĐÁNH GIÁ QUY TẮC CHỐNG TRÙNG LẶP (MILESTONE B)
    # ==============================================================================

    def evaluate_rules(self) -> List[CareTask]:
        """
        Đánh giá quy tắc chu kỳ CSKH, quyền riêng tư và truy vết nguồn gốc:
        - Khóa chống trùng phân biệt tối thiểu: nguồn + sự kiện/đơn/yêu cầu + quy tắc.
        - Khách có đơn thứ 2 sẽ sinh việc mới riêng.
        - Khách hẹn gọi lại lần thứ 2 sẽ có lịch hẹn mới riêng.
        - Không xóa lịch sử hoặc ghi đè phân công / hạn xử lý mà nhân viên đã chỉnh sửa.
        - Đơn bị hủy / hoàn trả -> Đánh giá lại và ngắt các công việc chưa xử lý.
        - Đính kèm đầy đủ nguồn gốc, kênh và căn cứ phát sinh việc.
        """
        with _service_lock:
            customers = self.list_customers()
            existing_tasks = self.list_tasks()
            
            # Bản đồ các task hiện có theo ID
            existing_task_map = {t.task_id: t for t in existing_tasks}
            # Bản đồ các rule keys đã kích hoạt
            existing_rule_keys = set()
            for t in existing_tasks:
                if t.status != TaskStatus.CANCELLED:
                    if t.rule_id and t.source_reference_id:
                        existing_rule_keys.add(f"{t.customer_id}_{t.source_reference_id}_{t.rule_id}")
                    # Khóa tương thích ngược
                    existing_rule_keys.add(f"{t.customer_id}_{t.task_type}")

            today_date = datetime.now()
            today_str = _get_today_str()

            new_tasks = []
            tasks_modified = False

            for cust in customers:
                # --------------------------------------------------------------
                # QUY TẮC 1: XỬ LÝ KHIẾU NẠI & PHẢN ỨNG BẤT LỢI (INCIDENT LOCKOUT)
                # --------------------------------------------------------------
                # A. Từ các SupportRequest cụ thể
                support_reqs = getattr(cust, "support_requests", [])
                pending_complaints = [sr for sr in support_reqs if sr.status in ("PENDING", "IN_PROGRESS") and "COMPLAINT" in sr.request_type]
                for idx, sr in enumerate(pending_complaints):
                    rule_key = f"{cust.id}_{sr.request_id}_RULE_COMPLAINT_RESOLUTION"
                    task_id = f"TASK-{cust.id}-COMPLAINT" if idx == 0 and not cust.active_complaint else f"TASK-{cust.id}-{sr.request_id[:8].upper()}-COMPLAINT"
                    if rule_key not in existing_rule_keys and task_id not in existing_task_map:
                        task = CareTask(
                            task_id=task_id,
                            customer_id=cust.id,
                            customer_name=cust.name,
                            task_type="COMPLAINT_RESOLUTION",
                            title=f"Xử lý khiếu nại: {sr.title}",
                            reason=f"Khách hàng phát sinh sự cố ({sr.request_type}): {sr.description}. Kích hoạt Incident Lockout, chuyển Dược sĩ giải quyết.",
                            sku=sr.sku or (cust.purchases[0].sku if cust.purchases else "DION-FE-FOLIC"),
                            product_name=sr.product_name or (cust.purchases[0].product_name if cust.purchases else "Sản phẩm DION"),
                            priority=TaskPriority.HIGH,
                            due_date=today_str,
                            assignee=cust.assigned_staff if "Dược sĩ" in (cust.assigned_staff or "") else "Dược sĩ Trần Mai",
                            status=TaskStatus.PENDING,
                            trigger_event_type="EVENT_COMPLAINT_FILED",
                            source_reference_id=sr.request_id,
                            rule_id="RULE_COMPLAINT_RESOLUTION",
                            rule_version="v1.2",
                            acquisition_source=cust.acquisition_source,
                            recording_source="Nhân viên ghi nhận",
                            purpose="SUPPORT",
                            evidence_summary=f"Yêu cầu hỗ trợ #{sr.request_id} ghi nhận lúc {sr.recorded_at}. Nội dung: '{sr.description}'",
                            logs=[{"timestamp": _get_now_str(), "action": "TASK_CREATED", "notes": "Hệ thống tự động kích hoạt Incident Lockout theo yêu cầu hỗ trợ"}]
                        )
                        new_tasks.append(task)
                        existing_rule_keys.add(rule_key)
                        existing_task_map[task_id] = task

                # B. Tương thích ngược từ cust.active_complaint
                if cust.active_complaint and not pending_complaints:
                    rule_key = f"{cust.id}_COMPLAINT_RESOLUTION"
                    task_id = f"TASK-{cust.id}-COMPLAINT"
                    if rule_key not in existing_rule_keys and task_id not in existing_task_map:
                        sku = cust.purchases[0].sku if cust.purchases else "DION-FE-FOLIC"
                        pname = cust.purchases[0].product_name if cust.purchases else "Sản phẩm DION"
                        task = CareTask(
                            task_id=task_id,
                            customer_id=cust.id,
                            customer_name=cust.name,
                            task_type="COMPLAINT_RESOLUTION",
                            title=f"Xử lý khiếu nại chất lượng / ADR: {cust.name}",
                            reason=f"Khách hàng phát sinh sự cố: {cust.active_complaint}. Bắt buộc ngắt toàn bộ kịch bản bán thêm (Incident Lockout) và chuyển Dược sĩ liên hệ.",
                            sku=sku,
                            product_name=pname,
                            priority=TaskPriority.HIGH,
                            due_date=today_str,
                            assignee="Dược sĩ Trần Mai",
                            status=TaskStatus.PENDING,
                            trigger_event_type="EVENT_COMPLAINT_FILED",
                            source_reference_id="LEGACY_COMPLAINT",
                            rule_id="RULE_COMPLAINT_RESOLUTION",
                            rule_version="v1.2",
                            acquisition_source=cust.acquisition_source,
                            recording_source="Nhân viên ghi nhận",
                            purpose="SUPPORT",
                            evidence_summary=f"Phản ánh trực tiếp: '{cust.active_complaint}'",
                            logs=[{"timestamp": _get_now_str(), "action": "TASK_CREATED", "notes": "Hệ thống tự động kích hoạt Incident Lockout"}]
                        )
                        new_tasks.append(task)
                        existing_rule_keys.add(rule_key)
                        existing_task_map[task_id] = task

                # --------------------------------------------------------------
                # QUY TẮC 2: GIAO HÀNG & CHU KỲ MUA LẠI TỪ CÁC ĐƠN THAM CHIẾU
                # --------------------------------------------------------------
                for p_idx, p in enumerate(cust.purchases):
                    order_status = getattr(p, "order_status", "DELIVERED")

                    # Nếu đơn hàng bị hủy hoặc hoàn trả -> Hủy các task PENDING thuộc đơn này
                    if order_status in ("CANCELLED", "RETURNED"):
                        for t in existing_tasks:
                            if t.customer_id == cust.id and getattr(t, "source_reference_id", "") == p.order_id and t.status == TaskStatus.PENDING:
                                t.status = TaskStatus.CANCELLED
                                tasks_modified = True
                                t.logs.append({
                                    "timestamp": _get_now_str(),
                                    "action": "CANCELLED_BY_SYSTEM",
                                    "notes": f"Đơn hàng #{p.order_id} đã bị {order_status}. Tự động hủy nhiệm vụ chăm sóc chưa thực hiện."
                                })
                        continue

                    # Chỉ tạo task theo dõi nếu đơn hàng đã giao thành công (có delivery_date)
                    if not p.delivery_date:
                        continue

                    try:
                        deliv_date = datetime.strptime(p.delivery_date, "%Y-%m-%d")
                        days_elapsed = (today_date - deliv_date).days
                    except Exception:
                        continue

                    order_id = p.order_id or "ORDER"

                    # QUY TẮC NGÀY THỨ 7 (HỎI THĂM TRẢI NGHIỆM SỬ DỤNG)
                    if 7 <= days_elapsed < 14:
                        rule_key = f"{cust.id}_{order_id}_RULE_DAY_7"
                        task_id = f"TASK-{cust.id}-DAY7" if p_idx == 0 else f"TASK-{cust.id}-{order_id}-DAY7"

                        # Chống trùng: Kiểm tra theo rule_key chính xác của đơn này
                        if rule_key not in existing_rule_keys and task_id not in existing_task_map:
                            task = CareTask(
                                task_id=task_id,
                                customer_id=cust.id,
                                customer_name=cust.name,
                                task_type="DELIVERY_FOLLOWUP_DAY_7",
                                title=f"Hỏi thăm cảm nhận sau 7 ngày: {cust.name}",
                                reason=f"Đã qua 7 ngày kể từ khi đơn #{order_id} giao thành công ({p.delivery_date}). Cần khảo sát cảm nhận dung nạp và hướng dẫn thời điểm uống tối ưu.",
                                sku=p.sku,
                                product_name=p.product_name,
                                priority=TaskPriority.MEDIUM,
                                due_date=today_str,
                                assignee=cust.assigned_staff or "Chuyên viên CSKH",
                                status=TaskStatus.PENDING,
                                trigger_event_type="EVENT_DELIVERY_CONFIRMED",
                                source_reference_id=order_id,
                                rule_id="RULE_DAY_7_FOLLOWUP",
                                rule_version="v1.2",
                                acquisition_source=cust.acquisition_source,
                                purchase_channel=getattr(p, "purchase_channel", "Cửa hàng trực tiếp"),
                                recording_source=getattr(p, "verification_status", "Nhân viên ghi nhận"),
                                purpose="SUPPORT",
                                evidence_summary=f"Đơn hàng #{order_id} ({p.product_name}) giao thành công ngày {p.delivery_date} qua {getattr(p, 'purchase_channel', 'Cửa hàng')}. Ngày thứ {days_elapsed} sau giao.",
                                logs=[{"timestamp": _get_now_str(), "action": "TASK_CREATED", "notes": f"Sinh tự động theo chu kỳ ngày thứ 7 (Đơn #{order_id})"}]
                            )
                            new_tasks.append(task)
                            existing_rule_keys.add(rule_key)
                            existing_task_map[task_id] = task

                    # QUY TẮC CHU KỲ MUA LẠI: Tính theo chu kỳ tham chiếu cụ thể p.cycle_days
                    reorder_trigger_day = max(p.cycle_days - 5, int(p.cycle_days * 0.8))
                    if days_elapsed >= reorder_trigger_day:
                        is_consent_ok = (cust.consent_status not in ("UNKNOWN", "Chưa rõ", "Chưa xác nhận", "Khách hàng đã Opt-out", "OPT_OUT")) and not cust.is_opt_out_marketing
                        # Chỉ sinh công việc tiếp thị nếu khách hàng đồng thuận nhận tin và không có khiếu nại
                        if is_consent_ok and not cust.active_complaint:
                            rule_key = f"{cust.id}_{order_id}_RULE_REORDER"
                            task_id = f"TASK-{cust.id}-DAY25" if p_idx == 0 else f"TASK-{cust.id}-{order_id}-DAY25"

                            # Kiểm tra tần suất liên hệ gần nhất (Frequency Capping 7 ngày - Mục 8.2)
                            recent_contact_days = None
                            for inter in getattr(cust, "interactions", []):
                                ts = getattr(inter, "occurred_at", None) or getattr(inter, "timestamp", None)
                                is_outbound_or_contact = getattr(inter, "action_type", "") in (
                                    ActionType.CONTACTED, ActionType.COMPLETED, "CONTACTED", "COMPLETED"
                                ) or getattr(inter, "direction", "") == "OUTBOUND"
                                if ts and is_outbound_or_contact:
                                    try:
                                        d_inter = datetime.strptime(ts[:10], "%Y-%m-%d")
                                        diff_d = (today_date - d_inter).days
                                        if recent_contact_days is None or diff_d < recent_contact_days:
                                            recent_contact_days = diff_d
                                    except Exception:
                                        pass
                            has_freq_block = bool(recent_contact_days is not None and recent_contact_days <= 7)

                            if rule_key not in existing_rule_keys and task_id not in existing_task_map:
                                task = CareTask(
                                    task_id=task_id,
                                    customer_id=cust.id,
                                    customer_name=cust.name,
                                    task_type="REORDER_CHECK_DAY_25",
                                    title=f"Kiểm tra nhu cầu bổ sung chu kỳ tiếp ({p.cycle_days} ngày): {cust.name}",
                                    reason=f"Khách hàng ở ngày thứ {days_elapsed} trong chu kỳ tham chiếu {p.cycle_days} ngày (Đơn #{order_id}). Đề xuất xác nhận nhu cầu chuẩn bị đợt dùng tiếp theo.",
                                    sku=p.sku,
                                    product_name=p.product_name,
                                    priority=TaskPriority.MEDIUM,
                                    due_date=today_str,
                                    assignee=cust.assigned_staff or "Chuyên viên CSKH",
                                    status=TaskStatus.BLOCKED if has_freq_block else TaskStatus.PENDING,
                                    is_blocked=has_freq_block,
                                    block_reason=f"FREQUENCY_CAPPING: Khách hàng vừa được liên hệ {recent_contact_days} ngày trước (Quy tắc giãn cách tối thiểu 7 ngày)" if has_freq_block else None,
                                    trigger_event_type="EVENT_REORDER_CYCLE_DUE",
                                    source_reference_id=order_id,
                                    rule_id="RULE_REORDER_CYCLE",
                                    rule_version="v1.2",
                                    acquisition_source=cust.acquisition_source,
                                    purchase_channel=getattr(p, "purchase_channel", "Cửa hàng trực tiếp"),
                                    recording_source=getattr(p, "verification_status", "Nhân viên ghi nhận"),
                                    purpose="MARKETING",
                                    evidence_summary=f"Đơn hàng #{order_id} ({p.product_name}) giao ngày {p.delivery_date}, chu kỳ tham chiếu {p.cycle_days} ngày. Đến mốc ngày thứ {days_elapsed}." + (f" [Đang bị khóa tần suất: liên hệ {recent_contact_days} ngày trước]" if has_freq_block else ""),
                                    logs=[{"timestamp": _get_now_str(), "action": "TASK_CREATED", "notes": f"Sinh tự động theo chu kỳ ngày thứ {reorder_trigger_day} ({p.cycle_days} ngày - Đơn #{order_id})" + (" [KHÓA TẦN SUẤT 7 NGÀY]" if has_freq_block else "")}]
                                )
                                new_tasks.append(task)
                                existing_rule_keys.add(rule_key)
                                existing_task_map[task_id] = task
                            elif task_id in existing_task_map:
                                existing_t = existing_task_map[task_id]
                                if existing_t.status in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                                    if has_freq_block and not existing_t.is_blocked:
                                        existing_t.is_blocked = True
                                        existing_t.status = TaskStatus.BLOCKED
                                        existing_t.block_reason = f"FREQUENCY_CAPPING: Khách hàng vừa được liên hệ {recent_contact_days} ngày trước (Quy tắc giãn cách tối thiểu 7 ngày)"
                                        tasks_modified = True
                                    elif not has_freq_block and existing_t.is_blocked and existing_t.block_reason and "FREQUENCY_CAPPING" in existing_t.block_reason:
                                        existing_t.is_blocked = False
                                        existing_t.status = TaskStatus.PENDING
                                        existing_t.block_reason = None
                                        tasks_modified = True

                # --------------------------------------------------------------
                # QUY TẮC 3: LỊCH HẸN GỌI LẠI (SCHEDULED CALLBACK)
                # --------------------------------------------------------------
                cb_requests = getattr(cust, "callback_requests", [])
                pending_cbs = [cb for cb in cb_requests if cb.status == "PENDING"]
                for cb_idx, cb in enumerate(pending_cbs):
                    rule_key = f"{cust.id}_{cb.callback_id}_RULE_CALLBACK"
                    task_id = f"TASK-{cust.id}-CALLBACK" if cb_idx == 0 else f"TASK-{cust.id}-{cb.callback_id[:8].upper()}-CALLBACK"
                    if rule_key not in existing_rule_keys and task_id not in existing_task_map:
                        task = CareTask(
                            task_id=task_id,
                            customer_id=cust.id,
                            customer_name=cust.name,
                            task_type="SCHEDULED_CALLBACK",
                            title=f"Lịch hẹn gọi lại: {cust.name} ({cb.preferred_time})",
                            reason=f"Khách hàng yêu cầu gọi lại vào ngày {cb.preferred_date} (khung giờ {cb.preferred_time}). Nội dung: {cb.reason}",
                            sku=cb.sku or (cust.purchases[0].sku if cust.purchases else "DION-CAL-MOM"),
                            product_name=cb.product_name or (cust.purchases[0].product_name if cust.purchases else "Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2"),
                            priority=TaskPriority.HIGH,
                            due_date=cb.preferred_date,
                            assignee=cust.assigned_staff or "Dược sĩ Trần Mai",
                            status=TaskStatus.PENDING,
                            trigger_event_type="EVENT_CALLBACK_REQUESTED",
                            source_reference_id=cb.callback_id,
                            rule_id="RULE_SCHEDULED_CALLBACK",
                            rule_version="v1.2",
                            acquisition_source=cust.acquisition_source,
                            recording_source="Nhân viên ghi nhận",
                            purpose="SUPPORT",
                            evidence_summary=f"Yêu cầu gọi lại #{cb.callback_id} lúc {cb.occurred_at}. Hẹn ngày: {cb.preferred_date} {cb.preferred_time}. Lý do: '{cb.reason}'",
                            logs=[{"timestamp": _get_now_str(), "action": "TASK_CREATED", "notes": f"Tạo lịch hẹn gọi lại theo yêu cầu #{cb.callback_id}"}]
                        )
                        new_tasks.append(task)
                        existing_rule_keys.add(rule_key)
                        existing_task_map[task_id] = task

                # B. Tương thích ngược từ cust.callback_requested
                if getattr(cust, "callback_requested", False) and not pending_cbs:
                    rule_key = f"{cust.id}_SCHEDULED_CALLBACK"
                    task_id = f"TASK-{cust.id}-CALLBACK"
                    if rule_key not in existing_rule_keys and task_id not in existing_task_map:
                        target_due = getattr(cust, "callback_preferred_date", None) or today_str
                        task = CareTask(
                            task_id=task_id,
                            customer_id=cust.id,
                            customer_name=cust.name,
                            task_type="SCHEDULED_CALLBACK",
                            title=f"Lịch hẹn gọi lại tư vấn: {cust.name}",
                            reason=getattr(cust, "callback_reason", None) or "Khách hàng đã yêu cầu gọi lại vào hôm nay để được Dược sĩ tư vấn chuyên sâu về lộ trình kết hợp vi chất.",
                            sku=getattr(cust, "callback_sku", None) or (cust.purchases[0].sku if cust.purchases else "DION-CAL-MOM"),
                            product_name=getattr(cust, "callback_product_name", None) or (cust.purchases[0].product_name if cust.purchases else "Canxi Hữu Cơ DION Cal-Mom Plus & D3 K2"),
                            priority=TaskPriority.HIGH,
                            due_date=target_due,
                            assignee=cust.assigned_staff or "Dược sĩ Trần Mai",
                            status=TaskStatus.PENDING,
                            trigger_event_type="EVENT_CALLBACK_REQUESTED",
                            source_reference_id="LEGACY_CALLBACK",
                            rule_id="RULE_SCHEDULED_CALLBACK",
                            rule_version="v1.2",
                            acquisition_source=cust.acquisition_source,
                            recording_source="Nhân viên ghi nhận",
                            purpose="SUPPORT",
                            evidence_summary=f"Yêu cầu gọi lại từ khách hàng: '{getattr(cust, 'callback_reason', 'Tư vấn lộ trình')}'",
                            logs=[{"timestamp": _get_now_str(), "action": "TASK_CREATED", "notes": "Tạo lịch hẹn gọi lại theo yêu cầu của khách"}]
                        )
                        new_tasks.append(task)
                        existing_rule_keys.add(rule_key)
                        existing_task_map[task_id] = task

            # ------------------------------------------------------------------
            # QUY TẮC 4: RÀ SOÁT QUYỀN RIÊNG TƯ & KHÓA SỰ CỐ (OPT-OUT & LOCKOUT)
            # ------------------------------------------------------------------
            cust_map = {c.id: c for c in customers}
            all_current_tasks = existing_tasks + new_tasks

            for t in all_current_tasks:
                c = cust_map.get(t.customer_id)
                if c:
                    is_opt_out = c.is_opt_out_marketing or (c.consent_status in ("Khách hàng đã Opt-out", "OPT_OUT", "UNKNOWN", "Chưa rõ", "Chưa xác nhận"))
                    is_marketing_task = (getattr(t, "purpose", None) == "MARKETING") or (t.task_type in ("REORDER_CHECK_DAY_25", "REORDER_CHECK", "UPSELL"))
                    
                    # 1. Khóa do Opt-out tiếp thị
                    if is_opt_out and is_marketing_task and t.status != TaskStatus.COMPLETED:
                        if t.status != TaskStatus.BLOCKED or not t.is_blocked:
                            t.status = TaskStatus.BLOCKED
                            t.is_blocked = True
                            t.block_reason = "Khách hàng đã từ chối nhận tin tiếp thị (Opt-out) / Consent chưa rõ"
                            t.logs.append({
                                "timestamp": _get_now_str(),
                                "action": "BLOCKED_BY_POLICY",
                                "notes": "Hệ thống tự động tạm ngưng nhiệm vụ tiếp thị do trạng thái quyền riêng tư (Opt-out)"
                            })
                            tasks_modified = True

                    # 2. Khóa do Sự cố / Khiếu nại (Incident Lockout)
                    if c.active_complaint and is_marketing_task and t.status != TaskStatus.COMPLETED:
                        if t.status != TaskStatus.BLOCKED or not t.is_blocked:
                            t.status = TaskStatus.BLOCKED
                            t.is_blocked = True
                            t.block_reason = f"Khóa sự cố (Incident Lockout): Đang có khiếu nại '{c.active_complaint}'"
                            t.logs.append({
                                "timestamp": _get_now_str(),
                                "action": "BLOCKED_BY_POLICY",
                                "notes": "Kích hoạt Incident Lockout: Chặn mọi hành vi tiếp thị / chào mua lại"
                            })
                            tasks_modified = True

                    # 3. Khóa do Tần suất liên hệ (Frequency Capping 7 ngày - Mục 8.2)
                    if is_marketing_task and t.status != TaskStatus.COMPLETED and not c.active_complaint and not is_opt_out:
                        recent_contact_days = None
                        for inter in getattr(c, "interactions", []):
                            ts = getattr(inter, "occurred_at", None) or getattr(inter, "timestamp", None)
                            is_outbound_or_contact = getattr(inter, "action_type", "") in (
                                ActionType.CONTACTED, ActionType.COMPLETED, "CONTACTED", "COMPLETED"
                            ) or getattr(inter, "direction", "") == "OUTBOUND"
                            if ts and is_outbound_or_contact:
                                try:
                                    d_inter = datetime.strptime(ts[:10], "%Y-%m-%d")
                                    diff_d = (today_date - d_inter).days
                                    if recent_contact_days is None or diff_d < recent_contact_days:
                                        recent_contact_days = diff_d
                                except Exception:
                                    pass
                        has_freq_block = bool(recent_contact_days is not None and recent_contact_days <= 7)
                        if has_freq_block:
                            if t.status != TaskStatus.BLOCKED or not t.is_blocked:
                                t.status = TaskStatus.BLOCKED
                                t.is_blocked = True
                                t.block_reason = f"FREQUENCY_CAPPING: Khách hàng vừa được liên hệ {recent_contact_days} ngày trước (Quy tắc giãn cách tối thiểu 7 ngày)"
                                t.logs.append({
                                    "timestamp": _get_now_str(),
                                    "action": "BLOCKED_BY_POLICY",
                                    "notes": f"Hệ thống tự động khóa nhiệm vụ tiếp thị do tần suất liên hệ ({recent_contact_days} ngày trước <= 7 ngày)"
                                })
                                tasks_modified = True

            if new_tasks or tasks_modified:
                all_raw = [t.model_dump() for t in all_current_tasks]
                self._save_tasks_raw(all_raw)

            return self.list_tasks()

    # ==============================================================================
    # IMPORT TỆP DỮ LIỆU CSV UTF-8 (CÓ XEM TRƯỚC VÀ KIỂM TRA TỪNG DÒNG)
    # ==============================================================================

    def import_customers_csv(self, csv_content: str, dry_run: bool = True) -> Dict[str, Any]:
        """Import danh sách khách hàng từ file CSV UTF-8 với kiểm tra lỗi từng dòng."""
        with _service_lock:
            existing_customers = {c.id.lower(): c for c in self.list_customers()}
            existing_phones = {c.phone.replace("*", ""): c for c in self.list_customers() if c.phone}

            reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(reader)
            
            valid_items = []
            errors = []
            duplicates = []

            for idx, r in enumerate(rows, start=1):
                c_name = (r.get("name") or "").strip()
                c_phone = (r.get("phone") or "").strip()
                c_id = (r.get("id") or "").strip()

                if not c_name or not c_phone:
                    errors.append(f"Dòng {idx}: Thiếu tên khách hàng hoặc số điện thoại bắt buộc.")
                    continue

                if not c_id:
                    c_id = f"KH-IMP-{uuid.uuid4().hex[:6].upper()}"

                # Kiểm tra trùng ID
                if c_id.lower() in existing_customers:
                    duplicates.append(f"Dòng {idx}: Mã khách '{c_id}' đã tồn tại trong hệ thống (Sẽ bỏ qua).")
                    continue

                # Kiểm tra trùng SĐT
                clean_phone = c_phone.replace("*", "")
                if clean_phone in existing_phones:
                    duplicates.append(f"Dòng {idx}: Số điện thoại '{c_phone}' trùng với khách {existing_phones[clean_phone].id} ({existing_phones[clean_phone].name}).")

                # Không tự động cấp consent, nếu không rõ ghi UNKNOWN
                raw_consent = (r.get("consent_status") or "").strip()
                consent_status = raw_consent if raw_consent else "UNKNOWN"

                cust_type = (r.get("customer_type") or "INDIVIDUAL").strip().upper()
                if cust_type not in ("INDIVIDUAL", "ORGANIZATION"):
                    cust_type = "INDIVIDUAL"

                customer_dict = {
                    "id": c_id,
                    "name": c_name,
                    "phone": c_phone,
                    "email": (r.get("email") or "").strip(),
                    "customer_type": cust_type,
                    "acquisition_source": "Import tệp tin CSV (Đã đối soát)",
                    "consent_status": consent_status,
                    "is_opt_out_marketing": consent_status in ("OPT_OUT", "Khách hàng đã Opt-out"),
                    "assigned_staff": (r.get("assigned_staff") or "Chuyên viên CSKH").strip(),
                    "is_demo": True,
                    "purchases": [],
                    "interactions": []
                }
                valid_items.append(customer_dict)

            if not dry_run and valid_items:
                all_custs = self._load_customers_raw()
                all_custs.extend(valid_items)
                self._save_customers_raw(all_custs)
                self.evaluate_rules()

            batch_id = f"BATCH-CUST-{uuid.uuid4().hex[:6].upper()}"
            return {
                "status": "SUCCESS",
                "batch_id": batch_id,
                "dry_run": dry_run,
                "total_rows": len(rows),
                "valid_count": len(valid_items),
                "imported_count": len(valid_items) if not dry_run else 0,
                "skipped_count": len(errors) + len(duplicates),
                "error_count": len(errors),
                "duplicate_count": len(duplicates),
                "errors": errors,
                "duplicates": duplicates,
                "preview_items": valid_items[:5]
            }

    def import_purchases_csv(self, csv_content: str, dry_run: bool = True) -> Dict[str, Any]:
        """Import giao dịch tham chiếu từ file CSV UTF-8 với kiểm tra ID khách hàng hợp lệ."""
        with _service_lock:
            cust_map = {c.id.lower(): c for c in self.list_customers()}
            reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(reader)

            valid_items = []
            errors = []

            for idx, r in enumerate(rows, start=1):
                cust_id = (r.get("customer_id") or "").strip()
                sku = (r.get("sku") or "").strip()
                p_name = (r.get("product_name") or "").strip()
                order_id = (r.get("order_id") or "").strip()

                if not cust_id or not sku:
                    errors.append(f"Dòng {idx}: Thiếu mã khách hàng (customer_id) hoặc mã sản phẩm (sku).")
                    continue

                if cust_id.lower() not in cust_map:
                    errors.append(f"Dòng {idx}: Không tìm thấy khách hàng '{cust_id}' trong hệ thống.")
                    continue

                if not order_id:
                    order_id = f"DH-IMP-{uuid.uuid4().hex[:6].upper()}"

                if not p_name:
                    p_name = f"Sản phẩm {sku}"

                deliv_date = (r.get("delivery_date") or "").strip()
                order_status = (r.get("order_status") or ("DELIVERED" if deliv_date else "PENDING")).strip().upper()

                purchase_dict = {
                    "order_id": order_id,
                    "customer_id": cust_id,
                    "sku": sku,
                    "product_name": p_name,
                    "order_date": (r.get("order_date") or _get_today_str()).strip(),
                    "delivery_date": deliv_date if deliv_date else None,
                    "cycle_days": int(r.get("cycle_days") or 30),
                    "quantity": int(r.get("quantity") or 1),
                    "purchase_channel": (r.get("purchase_channel") or "Import tệp tin").strip(),
                    "source_order_code": (r.get("source_order_code") or "").strip(),
                    "order_status": order_status,
                    "source_system": "CSV_IMPORT",
                    "recording_method": "IMPORT",
                    "recorded_by": "Tệp CSV (Nhân viên đối soát)",
                    "verification_status": "File import (Chưa đối soát qua cổng bán hàng)",
                    "notes": (r.get("notes") or "").strip()
                }
                valid_items.append(purchase_dict)

            if not dry_run and valid_items:
                all_custs = self._load_customers_raw()
                for p in valid_items:
                    c_target = next((c for c in all_custs if c["id"].lower() == p["customer_id"].lower()), None)
                    if c_target:
                        c_target.setdefault("purchases", []).append(p)
                self._save_customers_raw(all_custs)
                self.evaluate_rules()

            batch_id = f"BATCH-PUR-{uuid.uuid4().hex[:6].upper()}"
            return {
                "status": "SUCCESS",
                "batch_id": batch_id,
                "dry_run": dry_run,
                "total_rows": len(rows),
                "valid_count": len(valid_items),
                "imported_count": len(valid_items) if not dry_run else 0,
                "skipped_count": len(errors),
                "error_count": len(errors),
                "errors": errors,
                "preview_items": valid_items[:5]
            }

    # ==============================================================================
    # THAO TÁC CÔNG VIỆC, SOẠN THẢO BẢN NHÁP & NHẬT KÝ HÀNH ĐỘNG
    # ==============================================================================

    def get_metrics(self) -> CustomerCareMetrics:
        """Đếm số liệu công việc thật từ file lưu trữ, tách bạch việc có thể xử lý và việc bị chặn."""
        with _service_lock:
            tasks = self.list_tasks()
            today_str = _get_today_str()

            due_today = 0
            overdue = 0
            pending_complaints = 0
            completed = 0
            blocked = 0

            for t in tasks:
                if t.status == TaskStatus.COMPLETED:
                    completed += 1
                elif t.status == TaskStatus.BLOCKED or t.is_blocked:
                    blocked += 1
                elif t.status == TaskStatus.CANCELLED:
                    pass
                else:
                    if t.task_type == "COMPLAINT_RESOLUTION":
                        pending_complaints += 1
                    if t.due_date == today_str:
                        due_today += 1
                    elif t.due_date < today_str:
                        overdue += 1

            total_active = len([
                t for t in tasks 
                if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.UNREACHABLE) 
                and not t.is_blocked and t.status != TaskStatus.BLOCKED
            ])

            return CustomerCareMetrics(
                due_today=due_today,
                overdue=overdue,
                pending_complaints=pending_complaints,
                completed=completed,
                total_active=total_active,
                blocked=blocked
            )

    def auto_draft_message(self, customer_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Tự động soạn kịch bản tin nhắn theo hồ sơ và quy chuẩn kiểm soát:
        - Phân biệt rõ mục đích: Tiếp thị (REORDER) vs Hỗ trợ (COMPLAINT/CALLBACK).
        - Kiểm tra Incident Lockout: nếu có khiếu nại -> Chặn kịch bản bán hàng/upsell, chuyển sang mẫu hỗ trợ.
        - Kiểm tra Consent & Opt-out: nếu từ chối hoặc chưa rõ consent -> Chặn tin khuyến mãi/mời mua.
        """
        with _service_lock:
            cust = self.get_customer(customer_id)
            if not cust:
                return {
                    "decision": "BLOCKED",
                    "warning": "CUSTOMER_NOT_FOUND",
                    "message": f"Không tìm thấy dữ liệu khách hàng {customer_id}",
                    "draft": ""
                }

            task = self.get_task(task_id) if task_id else None
            first_name = cust.name.split()[-1] if cust.name else "Quý khách"
            product_name = cust.purchases[0].product_name if cust.purchases else "Sản phẩm DION"
            sku = cust.purchases[0].sku if cust.purchases else ""

            # Xác định mục đích công việc từ dữ liệu đáng tin cậy của backend
            task_type = task.task_type if task else ("DELIVERY_FOLLOWUP_DAY_7" if "D3" in sku else "REORDER_CHECK_DAY_25")
            if not task and not cust.purchases:
                task_type = "GENERAL_WELCOME_CARE"

            is_marketing_purpose = task_type in ("REORDER_CHECK_DAY_25", "REORDER_CHECK", "UPSELL")

            # 1. KIỂM TRA INCIDENT LOCKOUT
            if cust.active_complaint:
                if is_marketing_purpose:
                    return {
                        "decision": "BLOCKED",
                        "warning": "INCIDENT_LOCKOUT_ENFORCED",
                        "customer_id": cust.id,
                        "customer_name": cust.name,
                        "is_locked": True,
                        "is_opt_out": cust.is_opt_out_marketing,
                        "draft": (
                            f"⛔ CẢNH BÁO INCIDENT LOCKOUT: KHÔNG ĐƯỢC PHÉP SOẠN TIN TIẾP THỊ / UPSELL!\n\n"
                            f"Khách hàng {cust.name} ({cust.id}) đang có khiếu nại chưa giải quyết: '{cust.active_complaint}'.\n\n"
                            f"Toàn bộ hành vi bán thêm (upsell) bị khóa theo quy chuẩn an toàn dược. "
                            f"Vui lòng chuyển Dược sĩ xử lý khiếu nại trước."
                        ),
                        "channel": "Cuộc gọi thoại / Zalo OA Chuyên môn",
                        "message": (
                            f"⛔ CẢNH BÁO INCIDENT LOCKOUT: KHÔNG ĐƯỢC PHÉP SOẠN TIN TIẾP THỊ / UPSELL!\n\n"
                            f"Khách hàng {cust.name} ({cust.id}) đang có khiếu nại chưa giải quyết: '{cust.active_complaint}'."
                        ),
                        "suggested_action": "Chuyển Dược sĩ phụ trách"
                    }
                elif task_type == "COMPLAINT_RESOLUTION":
                    draft_text = (
                        f"DION Healthcare xin kính chào quý khách {cust.name}!\n\n"
                        f"Bộ phận Dược vụ DION đã tiếp nhận phản hồi của mình về tình trạng: '{cust.active_complaint}'. "
                        f"Chúng em rất lấy làm tiếc về sự bất tiện này.\n\n"
                        f"Để đảm bảo an toàn tuyệt đối, Dược sĩ phụ trách ({task.assignee if task else 'Dược vụ'}) xin phép được gọi điện thoại trực tiếp cho mình trong ít phút tới để hướng dẫn xử lý và điều chỉnh cách dùng an toàn nhất nhé ạ!\n\n"
                        f"Trân trọng, Đội ngũ Dược vụ DION Healthcare."
                    )
                    return {
                        "decision": "BLOCKED",
                        "warning": "INCIDENT_LOCKOUT_ENFORCED",
                        "customer_id": cust.id,
                        "customer_name": cust.name,
                        "is_locked": True,
                        "is_opt_out": cust.is_opt_out_marketing,
                        "draft": draft_text,
                        "channel": "Cuộc gọi thoại / Zalo OA Chuyên môn",
                        "message": f"⛔ CẢNH BÁO INCIDENT LOCKOUT: Soạn tin tiếp nhận sự cố lâm sàng cho khách hàng {cust.name} (Chặn toàn bộ upsell).",
                        "suggested_action": "Chuyển Dược sĩ phụ trách gọi điện"
                    }

            # 2. KIỂM TRA CONSENT & OPT-OUT TIẾP THỊ
            is_consent_unknown = cust.consent_status in ("UNKNOWN", "Chưa rõ", "Chưa xác nhận")
            is_opt_out = cust.is_opt_out_marketing or (cust.consent_status in ("Khách hàng đã Opt-out", "OPT_OUT"))

            if (is_opt_out or is_consent_unknown) and is_marketing_purpose:
                return {
                    "decision": "PRIVACY_BLOCKED",
                    "draft_source": "TEMPLATE",
                    "warning": "OPT_OUT_RESTRICTION",
                    "customer_id": cust.id,
                    "customer_name": cust.name,
                    "is_locked": False,
                    "is_opt_out": True,
                    "draft": (
                        f"⛔ CẢNH BÁO QUYỀN RIÊNG TƯ (OPT-OUT): Khách hàng {cust.name} ({cust.id}) "
                        f"đã từ chối nhận tin tiếp thị hoặc trạng thái đồng thuận chưa rõ ràng ('{cust.consent_status}').\n\n"
                        f"Hệ thống tạm ngưng toàn bộ kịch bản soạn tin nhắn bán thêm hoặc nhắc mua lại chu kỳ cho khách hàng này.\n\n"
                        f"(Nếu khách hàng yêu cầu gọi lại hoặc tư vấn chuyên môn, vui lòng thực hiện qua nhiệm vụ Hỗ trợ tương ứng)."
                    ),
                    "channel": "Không khả dụng (Bị chặn tiếp thị)",
                    "message": (
                        f"🔒 QUYỀN RIÊNG TƯ (CONSENT / OPT-OUT): Khách hàng {cust.name} "
                        f"có trạng thái đồng thuận: '{cust.consent_status}'.\n\n"
                        f"Hệ thống không cho phép soạn tin nhắn mời mua hoặc gửi chương trình ưu đãi."
                    ),
                    "suggested_action": "Tôn trọng quyền riêng tư"
                }

            # 3. KIỂM TRA TẦN SUẤT LIÊN HỆ (FREQUENCY CAPPING 7 NGÀY - MỤC 8.1 & 8.2)
            if is_marketing_purpose:
                latest_contact_days = None
                for inter in getattr(cust, "interactions", []):
                    ts = getattr(inter, "occurred_at", None) or getattr(inter, "timestamp", None)
                    is_contact_action = getattr(inter, "action_type", "") in (
                        ActionType.CONTACTED, ActionType.COMPLETED, "CONTACTED", "COMPLETED"
                    ) or getattr(inter, "direction", "") == "OUTBOUND"
                    if ts and is_contact_action:
                        try:
                            dt = datetime.strptime(ts[:10], "%Y-%m-%d")
                            days_ago = (datetime.now() - dt).days
                            if latest_contact_days is None or days_ago < latest_contact_days:
                                latest_contact_days = days_ago
                        except Exception:
                            pass

                if latest_contact_days is not None and latest_contact_days <= 7:
                    return {
                        "decision": "FREQUENCY_BLOCKED",
                        "draft_source": "TEMPLATE",
                        "warning": "FREQUENCY_CAPPING_ENFORCED",
                        "customer_id": cust.id,
                        "customer_name": cust.name,
                        "is_locked": False,
                        "is_opt_out": cust.is_opt_out_marketing,
                        "draft": (
                            f"⛔ CẢNH BÁO TẦN SUẤT LIÊN HỆ (FREQUENCY CAPPING 7 NGÀY): Khách hàng {cust.name} ({cust.id}) "
                            f"vừa mới được liên hệ cách đây {latest_contact_days} ngày.\n\n"
                            f"Theo quy tắc chống spam và bảo vệ trải nghiệm khách hàng (Mục 8.2), khoảng cách tối thiểu giữa 2 lần liên hệ tiếp thị/tái mua là 7 ngày.\n\n"
                            f"Hệ thống tạm ngưng gửi tin nhắn chu kỳ tái mua cho khách hàng này đến khi đủ khoảng cách an toàn."
                        ),
                        "channel": "Không khả dụng (Bị chặn do tần suất liên hệ)",
                        "message": (
                            f"⛔ CẢNH BÁO TẦN SUẤT (FREQUENCY CAPPING): Khách hàng {cust.name} "
                            f"đã được liên hệ {latest_contact_days} ngày trước (Quy chuẩn giãn cách tối thiểu 7 ngày)."
                        ),
                        "suggested_action": "Tạm hoãn liên hệ tiếp thị"
                    }

            # 4. SOẠN KỊCH BẢN HỢP LỆ THEO NGỮ CẢNH (HỖ TRỢ / CHĂM SÓC - MỤC 8.3: KHÔNG TỰ KHẲNG ĐỊNH TRẠNG THÁI)
            if task_type == "GENERAL_WELCOME_CARE":
                draft_text = (
                    f"DION xin chào quý khách {cust.name}! Dược sĩ DION xin phép nhắn tin thăm hỏi sức khỏe của quý khách. "
                    f"Nếu quý khách có bất kỳ câu hỏi nào về các giải pháp vi chất bổ sung hoặc cách sử dụng sản phẩm DION an toàn, "
                    f"xin vui lòng phản hồi lại tin nhắn này để Dược sĩ hỗ trợ ngay nhé ạ! Chúc quý khách luôn mạnh khỏe!"
                )
                channel = "Zalo OA"
            elif task_type in ("REORDER_CHECK_DAY_25", "REORDER_CHECK"):
                draft_text = (
                    f"DION xin chào chị {first_name}! Liệu trình {product_name} của mình hiện đã bước sang ngày thứ 25.\n\n"
                    f"Dược sĩ DION xin phép nhắn tin thăm hỏi: Nếu trong tháng qua chị dùng đều đặn và sản phẩm sắp hết, "
                    f"DION xin gửi chị ưu đãi thành viên hỗ trợ 10% cho hộp chu kỳ tiếp theo để việc bổ sung vi chất không bị gián đoạn. "
                    f"Chị nhắn lại để Dược sĩ hỗ trợ chuẩn bị đơn giao tận nhà nhé ạ! Chúc chị luôn khỏe mạnh!"
                )
                channel = "Zalo OA"
            elif task_type == "DELIVERY_FOLLOWUP_DAY_7":
                draft_text = (
                    f"DION xin chào anh {first_name}! Đơn hàng {product_name} của mình đã được giao thành công 7 ngày trước. "
                    f"Dược sĩ DION xin phép nhắn tin thăm hỏi không biết anh đã mở hộp sử dụng chưa ạ? "
                    f"Nếu anh cần Dược sĩ hỗ trợ thêm về cách uống hoặc thời điểm sử dụng sau ăn để tăng cường hấp thu tối đa, "
                    f"anh vui lòng phản hồi tại đây nhé. Chúc anh ngày mới vui vẻ và nhiều sức khỏe!"
                )
                channel = "SMS Brandname"
            elif task_type == "SCHEDULED_CALLBACK":
                draft_text = (
                    f"KỊCH BẢN GỌI ĐIỆN THEO HẸN TƯ VẤN CHUYÊN MÔN — KHÁCH HÀNG: {cust.name}\n"
                    f"- Người phụ trách: {task.assignee if task else 'Dược sĩ Trần Mai'}\n"
                    f"- Mục đích liên hệ: Khách hàng yêu cầu hỗ trợ chuyên môn về phối hợp vi chất ({product_name}).\n"
                    f"- Gợi ý mở đầu: 'Em chào anh/chị {first_name}, em là Dược sĩ DION gọi lại theo lịch hẹn của mình để trao đổi về cách dùng vi chất an toàn ạ...'"
                )
                channel = "Cuộc gọi thoại"
            else:
                draft_text = f"Chào {cust.name}, DION xin phép thăm hỏi tình hình sử dụng {product_name} của mình ạ."
                channel = "Zalo OA"

            if task:
                task.logs.append({
                    "timestamp": _get_now_str(),
                    "action": "DRAFT_CREATED",
                    "channel": channel,
                    "notes": "Hệ thống AI đã sinh bản nháp tư vấn"
                })
                self.update_task(task)

            return {
                "decision": "CARE_DRAFT",
                "draft_source": "TEMPLATE",
                "warning": None,
                "customer_id": cust.id,
                "customer_name": cust.name,
                "is_locked": False,
                "is_opt_out": cust.is_opt_out_marketing,
                "draft": draft_text,
                "channel": channel,
                "message": f"Đã sinh kịch bản tư vấn ({task_type})",
                "suggested_action": "Gửi tin chăm sóc"
            }

    def log_action(self, task_id: str, action_type: ActionType, performed_by: str = "Chuyên viên CSKH", notes: str = "", auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ghi nhận hành động thực tế và kiểm tra thẩm quyền nhân sự:
        - Phân biệt rõ: COPIED không phải CONTACTED; CONTACTED không phải RESOLVED; RESOLVED 1 khiếu nại không đóng gộp khiếu nại khác.
        """
        with _service_lock:
            task = self.get_task(task_id)
            if not task:
                return {"status": "ERROR", "code": "TASK_NOT_FOUND", "message": f"Không tìm thấy công việc {task_id}"}

            now_str = _get_now_str()
            act_val = action_type.value if hasattr(action_type, "value") else str(action_type)

            # 1. KIỂM TRA PHÂN QUYỀN NHÂN VIÊN
            if performed_by not in AUTHORIZED_STAFF:
                return {
                    "status": "ERROR",
                    "code": "UNAUTHORIZED_STAFF",
                    "message": f"Người thực hiện '{performed_by}' không có trong danh mục nhân sự được cấp quyền."
                }

            # 2. KIỂM TRA QUYỀN ĐÓNG KHIẾU NẠI CHUYÊN MÔN
            if act_val in ("RESOLVED", "COMPLETED"):
                if task.task_type == "COMPLAINT_RESOLUTION" and performed_by not in AUTHORIZED_CLINICAL_STAFF:
                    return {
                        "status": "ERROR",
                        "code": "PERMISSION_DENIED",
                        "message": "Chỉ Dược sĩ chuyên môn hoặc Dược vụ mới có thẩm quyền giải quyết khiếu nại chất lượng / ADR."
                    }

                task.status = TaskStatus.COMPLETED
                if task.task_type == "COMPLAINT_RESOLUTION":
                    cust = self.get_customer(task.customer_id)
                    if cust:
                        other_complaint_tasks = [
                            t for t in self.list_tasks()
                            if t.customer_id == cust.id
                            and t.task_id.lower() != task.task_id.lower()
                            and t.task_type == "COMPLAINT_RESOLUTION"
                            and t.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
                        ]
                        resolved_desc = task.reason or (cust.active_complaint or "Khiếu nại sản phẩm")
                        cust.complaint_history.append({
                            "complaint": resolved_desc,
                            "task_id": task.task_id,
                            "resolved_at": now_str,
                            "resolved_by": performed_by,
                            "resolution_notes": notes or "Đã liên hệ xử lý thỏa đáng"
                        })
                        if other_complaint_tasks:
                            cust.active_complaint = other_complaint_tasks[0].reason
                            cust.complaint_status = f"Còn {len(other_complaint_tasks)} khiếu nại đang xử lý"
                        else:
                            cust.active_complaint = None
                            cust.complaint_status = "Đã giải quyết thỏa đáng"
                        self.update_customer(cust)

            elif act_val in ("CONTACTED", "CALLBACK_REQUESTED", "FEEDBACK_RECEIVED", "TRANSFERRED", "PENDING_REVIEW"):
                # Ghi nhận đã liên hệ nhưng CHƯA đóng công việc
                task.status = TaskStatus.IN_PROGRESS
            elif act_val == "UNREACHABLE":
                task.status = TaskStatus.UNREACHABLE

            log_entry = {
                "timestamp": now_str,
                "action": act_val,
                "performed_by": performed_by,
                "notes": notes or f"Thực hiện thao tác {act_val}"
            }
            task.logs.append(log_entry)
            self.update_task(task)

            # Ghi nhận interaction vào hồ sơ khách hàng nếu là tương tác thực tế
            if act_val in ("CONTACTED", "RESOLVED", "UNREACHABLE"):
                cust = self.get_customer(task.customer_id)
                if cust:
                    cust.interactions.append(
                        CareInteraction(
                            customer_id=cust.id,
                            channel="CALL" if "gọi" in notes.lower() else "ZALO",
                            action_type=action_type,
                            direction="OUTBOUND",
                            interaction_type="CONSULTATION",
                            summary=notes or f"Thực hiện {act_val} cho task {task.task_id}",
                            occurred_at=now_str,
                            recorded_at=now_str,
                            performed_by=performed_by,
                            notes=notes or f"Thực hiện {act_val} cho task {task.task_id}",
                            is_staff_confirmed=True
                        )
                    )
                    self.update_customer(cust)

            return {
                "status": "SUCCESS",
                "task": task.model_dump(),
                "metrics": self.get_metrics().model_dump()
            }

    def reschedule_task(
        self,
        task_id: str,
        new_due_date: str,
        notes: str = "",
        time_slot: Optional[str] = None,
        reschedule_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cập nhật lịch hẹn mới cho công việc kèm kiểm tra an toàn."""
        with _service_lock:
            task = self.get_task(task_id)
            if not task:
                return {"status": "ERROR", "code": "TASK_NOT_FOUND", "message": f"Không tìm thấy công việc {task_id}"}

            today_str = _get_today_str()
            date_clean = new_due_date.strip().split()[0]
            if reschedule_reason and date_clean < today_str:
                return {
                    "status": "ERROR",
                    "code": "INVALID_DATE",
                    "message": f"Không thể chọn ngày hẹn trong quá khứ ({date_clean} < hôm nay {today_str})."
                }

            cust = self.get_customer(task.customer_id)
            if cust and cust.is_opt_out_marketing and task.task_type in ("REORDER_CHECK_DAY_25", "reorder_check_day_25"):
                if reschedule_reason != "Khách yêu cầu gọi lại":
                    return {
                        "status": "ERROR",
                        "code": "MARKETING_OPT_OUT",
                        "message": "Khách hàng đã TẠM NGƯNG TIẾP THỊ (Opt-out). Không thể đặt lịch tiếp thị/nhắc mua lại."
                    }

            task.due_date = date_clean
            time_info = f" lúc {time_slot}" if time_slot else ""
            reason_info = f" [Lý do: {reschedule_reason}]" if reschedule_reason else ""
            custom_note = f" - Ghi chú: {notes}" if notes else ""

            task.logs.append({
                "timestamp": _get_now_str(),
                "action": "RESCHEDULED",
                "notes": f"Hẹn lại đến ngày {date_clean}{time_info}{reason_info}{custom_note}".strip()
            })
            self.update_task(task)
            return {"status": "SUCCESS", "task": task.model_dump(), "metrics": self.get_metrics().model_dump()}

    def assign_task(
        self,
        task_id: str,
        assignee: str,
        priority: Optional[str] = None,
        new_due_date: Optional[str] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Phân công công việc cho nhân viên phụ trách có kiểm tra vai trò chuyên môn."""
        with _service_lock:
            task = self.get_task(task_id)
            if not task:
                return {"status": "ERROR", "code": "TASK_NOT_FOUND", "message": f"Không tìm thấy công việc {task_id}"}

            if assignee not in AUTHORIZED_STAFF:
                return {
                    "status": "ERROR",
                    "code": "UNAUTHORIZED_STAFF",
                    "message": f"Nhân sự '{assignee}' không thuộc danh mục nhân viên được cấp quyền."
                }

            if task.task_type in ("COMPLAINT_RESOLUTION", "complaint_resolution"):
                if assignee not in AUTHORIZED_CLINICAL_STAFF:
                    return {
                        "status": "ERROR",
                        "code": "PERMISSION_DENIED",
                        "message": f"Khiếu nại lâm sàng / ADR chỉ được phép bàn giao cho Dược sĩ chuyên môn hoặc Dược vụ (hiện chọn: '{assignee}')."
                    }

            task.assignee = assignee
            if priority:
                try:
                    task.priority = TaskPriority(priority)
                except Exception:
                    pass
            if new_due_date:
                today_str = _get_today_str()
                date_clean = new_due_date.strip().split()[0]
                if date_clean >= today_str:
                    task.due_date = date_clean

            extra_note = f" - Ghi chú: {notes}" if notes else ""
            task.logs.append({
                "timestamp": _get_now_str(),
                "action": "ASSIGNED",
                "notes": f"Giao xử lý cho {assignee} (Ưu tiên: {task.priority}){extra_note}".strip()
            })
            self.update_task(task)
            return {"status": "SUCCESS", "task": task.model_dump()}

    def analyze_customer_reply(self, customer_id: str, reply_text: str) -> Dict[str, Any]:
        """
        Phân tích nội dung tin nhắn của khách hàng:
        - Nhận diện khiếu nại, tác dụng phụ (ADR) -> Tự động kích hoạt Incident Lockout và tạo task xử lý.
        - Nhận diện yêu cầu Opt-out -> Khóa quyền tiếp thị.
        - Nhận diện yêu cầu gọi lại -> Sinh task hẹn gọi lại.
        """
        with _service_lock:
            cust = self.get_customer(customer_id)
            if not cust:
                return {"status": "ERROR", "message": f"Không tìm thấy khách hàng {customer_id}"}

            text_lower = reply_text.lower()
            detected_issues = []
            is_complaint = False
            is_opt_out = False
            is_callback = False

            complaint_keywords = [
                "đầy hơi", "buồn nôn", "xót ruột", "xót dạ dày", "nôn", "khó chịu",
                "tác dụng phụ", "bị đau", "tiêu chảy", "táo bón nặng", "dị ứng",
                "nổi mẩn", "khiếu nại", "hàng lỗi", "bị hỏng", "uống vào thấy mệt", "cồn cào"
            ]
            if any(kw in text_lower for kw in complaint_keywords):
                is_complaint = True
                detected_issues.append("ADVERSE_EVENT_OR_COMPLAINT")

            optout_keywords = [
                "đừng nhắn tin", "hủy nhận tin", "đừng làm phiền", "ngừng gửi",
                "không nhận quảng cáo", "opt out", "spam", "chặn tin"
            ]
            if any(kw in text_lower for kw in optout_keywords):
                is_opt_out = True
                detected_issues.append("OPT_OUT_REQUEST")

            callback_keywords = [
                "gọi lại cho tôi", "gọi lại", "tư vấn thêm", "hẹn gọi lại", "alo lại", "liên hệ lại"
            ]
            if any(kw in text_lower for kw in callback_keywords):
                is_callback = True
                detected_issues.append("CALLBACK_REQUEST")

            now_str = _get_now_str()
            today_str = _get_today_str()

            if is_complaint:
                cust.active_complaint = reply_text.strip()
                cust.complaint_status = "Đang có khiếu nại chất lượng / ADR"
                self.update_customer(cust)

                task_id = f"TASK-{cust.id}-COMPLAINT"
                task = CareTask(
                    task_id=task_id,
                    customer_id=cust.id,
                    customer_name=cust.name,
                    task_type="COMPLAINT_RESOLUTION",
                    title=f"Xử lý khiếu nại chất lượng / ADR: {cust.name}",
                    reason=f"Khách hàng phản ánh: '{reply_text.strip()}'. Tự động kích hoạt Incident Lockout, chuyển Dược sĩ liên hệ.",
                    sku=cust.purchases[0].sku if cust.purchases else "DION-FE-FOLIC",
                    product_name=cust.purchases[0].product_name if cust.purchases else "Sản phẩm DION",
                    priority=TaskPriority.HIGH,
                    due_date=today_str,
                    assignee="Dược sĩ Trần Mai",
                    status=TaskStatus.PENDING,
                    trigger_event_type="EVENT_COMPLAINT_FILED",
                    source_reference_id="REPLY_ANALYZER",
                    rule_id="RULE_COMPLAINT_RESOLUTION",
                    rule_version="v1.2",
                    acquisition_source=cust.acquisition_source,
                    recording_source="Nhân viên ghi nhận",
                    purpose="SUPPORT",
                    evidence_summary=f"Phản hồi từ tin nhắn: '{reply_text.strip()}'",
                    logs=[{"timestamp": now_str, "action": "INCIDENT_TRIGGERED", "notes": f"Nội dung phản ánh: {reply_text.strip()}"}]
                )
                self.update_task(task)

            if is_opt_out:
                cust.is_opt_out_marketing = True
                cust.consent_status = "Khách hàng đã Opt-out"
                self.update_customer(cust)

                tasks = self.list_tasks()
                for t in tasks:
                    if t.customer_id == cust.id and t.task_type in ("REORDER_CHECK_DAY_25", "REORDER_CHECK", "UPSELL") and t.status != TaskStatus.COMPLETED:
                        t.status = TaskStatus.BLOCKED
                        t.is_blocked = True
                        t.block_reason = "Khách hàng đã từ chối nhận tin tiếp thị (Opt-out)"
                        t.logs.append({
                            "timestamp": now_str,
                            "action": "BLOCKED_BY_POLICY",
                            "notes": "Tự động khóa nhiệm vụ tiếp thị sau khi ghi nhận Opt-out"
                        })
                        self.update_task(t)

            intent = "COMPLAINT" if is_complaint else ("OPT_OUT" if is_opt_out else ("CALLBACK" if is_callback else "NORMAL_INQUIRY"))

            return {
                "status": "SUCCESS",
                "customer_id": cust.id,
                "intent": intent,
                "detected_issues": detected_issues,
                "is_locked": is_complaint,
                "is_opt_out": is_opt_out,
                "suggested_action": (
                    "Kích hoạt Incident Lockout & Chuyển Dược sĩ phụ trách" if is_complaint
                    else ("Khóa quyền tiếp thị (Opt-out)" if is_opt_out else "Tiếp tục tư vấn")
                )
            }

    def analyze_customer_state(self, customer_id: str) -> Dict[str, Any]:
        """
        Phân tích trạng thái khách hàng theo ma trận 4 chiều (Mục 8.3):
        1. Observable Facts (Dữ liệu quan sát được từ sự kiện thực tế)
        2. AI Inference (Dữ liệu suy diễn/ước tính của AI)
        3. Confidence Level (Mức độ tin cậy)
        4. Action Recommendation (Khuyến nghị hành động - Không tự khẳng định)
        """
        with _service_lock:
            cust = self.get_customer(customer_id)
            if not cust:
                return {
                    "status": "ERROR",
                    "code": "CUSTOMER_NOT_FOUND",
                    "message": f"Không tìm thấy khách hàng {customer_id}"
                }

            today = datetime.now()
            p = cust.purchases[0] if cust.purchases else None

            # 1. Observable Facts
            days_since_delivery = None
            if p and p.delivery_date:
                try:
                    deliv_dt = datetime.strptime(p.delivery_date, "%Y-%m-%d")
                    days_since_delivery = (today - deliv_dt).days
                except Exception:
                    pass

            latest_contact_days = None
            latest_contact_date = None
            for inter in getattr(cust, "interactions", []):
                ts = getattr(inter, "occurred_at", None) or getattr(inter, "timestamp", None)
                if ts:
                    try:
                        dt = datetime.strptime(ts[:10], "%Y-%m-%d")
                        d_ago = (today - dt).days
                        if latest_contact_days is None or d_ago < latest_contact_days:
                            latest_contact_days = d_ago
                            latest_contact_date = ts[:10]
                    except Exception:
                        pass

            observable_facts = {
                "customer_id": cust.id,
                "customer_name": cust.name,
                "customer_type": cust.customer_type,
                "has_purchase": bool(p),
                "order_id": p.order_id if p else None,
                "sku": p.sku if p else None,
                "product_name": p.product_name if p else None,
                "delivery_date": p.delivery_date if p else None,
                "days_since_delivery": days_since_delivery,
                "order_status": getattr(p, "order_status", None) if p else None,
                "active_complaint": cust.active_complaint,
                "consent_status": cust.consent_status,
                "is_opt_out_marketing": cust.is_opt_out_marketing,
                "total_interactions": len(getattr(cust, "interactions", [])),
                "latest_contact_date": latest_contact_date,
                "days_since_latest_contact": latest_contact_days,
                "has_contact_last_7_days": bool(latest_contact_days is not None and latest_contact_days <= 7),
            }

            # 2. AI Inference
            cycle_days = p.cycle_days if p else 30
            est_remaining_days = max(0, cycle_days - (days_since_delivery or 0)) if days_since_delivery is not None else None
            reorder_likelihood = "LOW"
            if days_since_delivery is not None:
                if days_since_delivery >= cycle_days - 5:
                    reorder_likelihood = "HIGH"
                elif days_since_delivery >= int(cycle_days * 0.5):
                    reorder_likelihood = "MEDIUM"

            ai_inference = {
                "cycle_days": cycle_days,
                "estimated_remaining_days": est_remaining_days,
                "usage_assumption": "Giả định khách hàng sử dụng đều đặn theo liều khuyến cáo (1 viên/ngày)",
                "reorder_need_likelihood": reorder_likelihood,
                "is_factual_usage_confirmed": False,
                "inference_basis": (
                    f"Ước tính dựa trên ngày giao hàng ({p.delivery_date if p else 'N/A'}) và chu kỳ sản phẩm {cycle_days} ngày. "
                    "Hệ thống KHÔNG có cảm biến hoặc xác nhận thực tế rằng khách hàng đã mở hộp uống đều mỗi ngày."
                )
            }

            # 3. Confidence Level
            has_client_confirmation = any(
                getattr(i, "direction", "") == "INBOUND" and "uống" in (getattr(i, "notes", "") or getattr(i, "summary", "")).lower()
                for i in getattr(cust, "interactions", [])
            )
            confidence_level = "HIGH" if has_client_confirmation else ("MEDIUM" if days_since_delivery is not None else "LOW")

            # 4. Action Recommendation
            action_rec = (
                "Tuân thủ nguyên tắc Mục 8.3: 'KHÔNG TỰ KHẲNG ĐỊNH TRẠNG THÁI SỬ DỤNG'. "
                "Sử dụng câu hỏi mở để xác nhận tình trạng thực tế từ khách hàng "
                "(ví dụ: 'Đơn hàng đã giao được X ngày, không biết anh/chị đã mở hộp dùng chưa ạ?'). "
                "Tuyệt đối không dùng các khẳng định võ đoán như 'Anh đã dùng được 1 tuần' hoặc 'Trong tháng qua chị đã uống'."
            )

            return {
                "status": "SUCCESS",
                "customer_id": cust.id,
                "customer_name": cust.name,
                "observable_facts": observable_facts,
                "ai_inference": ai_inference,
                "confidence_level": confidence_level,
                "action_recommendation": action_rec
            }


# Singleton instance
_service_instance = None

def get_customer_care_service() -> CustomerCareService:
    global _service_instance
    if _service_instance is None:
        _service_instance = CustomerCareService()
    return _service_instance
