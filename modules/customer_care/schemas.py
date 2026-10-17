# -*- coding: utf-8 -*-
"""
DION Healthcare AI — Customer Care Schemas & Enums
Định nghĩa Data Models cho Khách hàng, Tương tác, Đơn hàng tham chiếu, Yêu cầu hỗ trợ, Sự kiện và Nhiệm vụ Chăm sóc.
Đảm bảo tính tương thích ngược 100% với các phiên bản trước.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    DRAFT_CREATED = "DRAFT_CREATED"
    COPIED = "COPIED"
    CONTACTED = "CONTACTED"
    UNREACHABLE = "UNREACHABLE"
    BLOCKED = "BLOCKED"
    REPLY_RECEIVED = "REPLY_RECEIVED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    RESCHEDULED = "RESCHEDULED"
    ASSIGNED = "ASSIGNED"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"
    FEEDBACK_RECEIVED = "FEEDBACK_RECEIVED"
    TRANSFERRED = "TRANSFERRED"
    PENDING_REVIEW = "PENDING_REVIEW"
    COMPLETED = "COMPLETED"


class TaskPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    UNREACHABLE = "UNREACHABLE"
    BLOCKED = "BLOCKED"


class ConsentStatus(str, Enum):
    AGREED = "AGREED"
    OPT_OUT = "OPT_OUT"
    UNKNOWN = "UNKNOWN"


class CustomerType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"      # Cá nhân / Người tiêu dùng
    ORGANIZATION = "ORGANIZATION"  # Tổ chức / Quầy thuốc / Đại lý B2B


class PurchaseRecord(BaseModel):
    order_id: str
    sku: str
    product_name: str
    delivery_date: Optional[str] = None  # YYYY-MM-DD (Chỉ có khi giao hàng thành công)
    order_date: Optional[str] = None     # YYYY-MM-DD (Ngày giao dịch ban đầu)
    cycle_days: int = 30
    quantity: int = 1
    customer_id: Optional[str] = None
    source_system: str = "MANUAL_ENTRY"  # MANUAL_ENTRY, CSV_IMPORT, UNCONNECTED_MOCK
    purchase_channel: str = "Cửa hàng trực tiếp"  # Kênh mua: Cửa hàng, Shopee, TikTok Shop, Zalo OA, Nhà thuốc đối tác
    source_order_code: Optional[str] = None       # Mã đơn nguồn từ kênh bán nếu có
    order_status: str = "DELIVERED"               # PENDING, DELIVERED, CANCELLED, RETURNED
    recording_method: str = "MANUAL"              # MANUAL (Nhân viên nhập), IMPORT (File CSV), SYNC (Chưa kết nối)
    recorded_by: str = "Chuyên viên CSKH"
    verification_status: str = "Nhân viên ghi nhận"  # "Nhân viên ghi nhận" (không ghi "Đã xác minh từ hệ thống bán hàng" khi nhập tay)
    notes: Optional[str] = ""


class CareInteraction(BaseModel):
    id: str = Field(default_factory=lambda: f"INT-{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    channel: str = "ZALO"  # Kênh tương tác: ZALO, CALL, MESSENGER, SMS, DIRECT, EMAIL
    action_type: ActionType = ActionType.CONTACTED
    performed_by: str = "Chuyên viên CSKH"
    notes: str = ""
    customer_id: Optional[str] = None
    occurred_at: Optional[str] = None   # Thời điểm khách trao đổi thực tế
    recorded_at: Optional[str] = None   # Thời điểm nhân viên ghi vào hệ thống
    direction: str = "INBOUND"          # INBOUND (Khách liên hệ đến), OUTBOUND (Nhân viên gọi ra)
    interaction_type: str = "CONSULTATION"  # INQUIRY, CONSULTATION, CALLBACK_REQUEST, COMPLAINT, NOTE, FEEDBACK
    summary: Optional[str] = ""
    reference_note: Optional[str] = None   # Tham chiếu phiên chat Copilot Tab 4 nếu gắn
    is_staff_confirmed: bool = True       # Dữ kiện nhân viên xác nhận vs đề xuất AI


class SupportRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"REQ-{uuid.uuid4().hex[:8]}")
    customer_id: str
    customer_name: Optional[str] = ""
    request_type: str = "COMPLAINT_ADR"  # COMPLAINT_ADR, COMPLAINT_QUALITY, COMPLAINT_SHIPPING, GENERAL_SUPPORT
    title: str
    description: str
    sku: Optional[str] = None
    product_name: Optional[str] = None
    occurred_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    recorded_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    recorded_by: str = "Chuyên viên CSKH"
    status: str = "PENDING"  # PENDING, IN_PROGRESS, RESOLVED, CANCELLED
    resolution_notes: Optional[str] = ""
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    source: str = "Nhân viên ghi nhận"


class CallbackRequest(BaseModel):
    callback_id: str = Field(default_factory=lambda: f"CB-{uuid.uuid4().hex[:8]}")
    customer_id: str
    customer_name: Optional[str] = ""
    preferred_date: str  # YYYY-MM-DD
    preferred_time: Optional[str] = "09:30"
    reason: str
    sku: Optional[str] = None
    product_name: Optional[str] = None
    occurred_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    recorded_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    recorded_by: str = "Chuyên viên CSKH"
    status: str = "PENDING"  # PENDING, COMPLETED, CANCELLED
    source: str = "Nhân viên ghi nhận"


class CustomerRecord(BaseModel):
    id: str
    name: str
    phone: str
    customer_type: str = "INDIVIDUAL"  # INDIVIDUAL (Cá nhân), ORGANIZATION (Tổ chức / Nhà thuốc)
    email: Optional[str] = ""
    acquisition_source: str = "Nhập thủ công"  # Hotline, Zalo OA, Facebook Page, Website Chat, Giới thiệu tại quầy, B2B Lead, Nhập thủ công
    external_source_id: Optional[str] = None   # Mã bản ghi ở hệ thống nguồn nếu có
    consent_status: str = "Đã đồng ý nhận tin Zalo"
    is_opt_out_marketing: bool = False
    active_complaint: Optional[str] = None
    complaint_status: str = "Bình thường"
    complaint_history: List[Dict[str, Any]] = Field(default_factory=list)
    assigned_staff: str = "Dược sĩ Trần Mai"
    purchases: List[PurchaseRecord] = Field(default_factory=list)
    interactions: List[CareInteraction] = Field(default_factory=list)
    support_requests: List[SupportRequest] = Field(default_factory=list)
    callback_requests: List[CallbackRequest] = Field(default_factory=list)
    is_demo: bool = True
    callback_requested: bool = False
    callback_reason: Optional[str] = None
    callback_preferred_date: Optional[str] = None
    callback_preferred_time: Optional[str] = None
    callback_sku: Optional[str] = None
    callback_product_name: Optional[str] = None


class CareTask(BaseModel):
    task_id: str
    customer_id: str
    customer_name: str
    task_type: str  # DELIVERY_FOLLOWUP_DAY_7, REORDER_CHECK_DAY_25, REORDER_CHECK, COMPLAINT_RESOLUTION, SCHEDULED_CALLBACK
    title: str
    reason: str
    sku: str
    product_name: str
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: str  # YYYY-MM-DD
    assignee: str = "Chuyên viên CSKH"
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    is_overdue: bool = False
    is_due_today: bool = False
    is_blocked: bool = False
    block_reason: Optional[str] = None
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    is_demo: bool = True

    # Trường truy vết nguồn gốc & căn cứ phát sinh việc (Traceability)
    trigger_event_type: Optional[str] = None   # EVENT_DELIVERY_CONFIRMED, EVENT_REORDER_CYCLE_DUE, EVENT_CALLBACK_REQUESTED, EVENT_COMPLAINT_FILED
    source_reference_id: Optional[str] = None  # order_id, callback_id, request_id, int_id
    rule_id: Optional[str] = None              # RULE_DAY_7_FOLLOWUP, RULE_REORDER_CYCLE, RULE_COMPLAINT_RESOLUTION, RULE_SCHEDULED_CALLBACK
    rule_version: str = "v1.2"
    acquisition_source: Optional[str] = "Nhập thủ công"
    interaction_channel: Optional[str] = "Zalo OA"
    purchase_channel: Optional[str] = "Cửa hàng trực tiếp"
    recording_source: Optional[str] = "Nhân viên ghi nhận"
    evidence_summary: Optional[str] = ""
    purpose: str = "SUPPORT"  # SUPPORT (Hỗ trợ / Sự cố / Hẹn lại), MARKETING (Tiếp thị / Tái mua)


class CustomerCareMetrics(BaseModel):
    due_today: int = 0
    overdue: int = 0
    pending_complaints: int = 0
    completed: int = 0
    total_active: int = 0
    blocked: int = 0


# ==============================================================================
# REQUEST & RESPONSE DTOs CHO API & GIAO DIỆN NHẬP LIỆU
# ==============================================================================

class AutoDraftRequest(BaseModel):
    task_id: Optional[str] = None
    customer_id: str
    action_type: str = "AUTO"  # AUTO, FOLLOWUP_DAY_7, REORDER_DAY_25, COMPLAINT_REPLY


class ActionLogRequest(BaseModel):
    task_id: str
    action_type: ActionType
    performed_by: str = "Chuyên viên CSKH"
    notes: str = ""
    channel: Optional[str] = None
    outcome: Optional[str] = None
    callback_date: Optional[str] = None
    callback_time: Optional[str] = None
    transferred_to: Optional[str] = None


class RescheduleRequest(BaseModel):
    task_id: str
    new_due_date: str
    notes: str = ""
    time_slot: Optional[str] = None
    reschedule_reason: Optional[str] = None


class AssignTaskRequest(BaseModel):
    task_id: str
    assignee: str
    priority: Optional[str] = None
    new_due_date: Optional[str] = None
    notes: Optional[str] = ""


class ReplyAnalysisRequest(BaseModel):
    customer_id: str
    reply_text: str


class CreateCustomerRequest(BaseModel):
    id: Optional[str] = None
    name: str
    phone: str
    email: Optional[str] = ""
    customer_type: str = "INDIVIDUAL"  # INDIVIDUAL, ORGANIZATION
    acquisition_source: str = "Nhập thủ công"  # Hotline, Zalo OA, Facebook Page, Website Chat, Giới thiệu tại quầy, B2B Lead, Nhập thủ công
    external_source_id: Optional[str] = None
    consent_status: str = "Đã đồng ý nhận tin Zalo"
    is_opt_out_marketing: bool = False
    assigned_staff: Optional[str] = "Chuyên viên CSKH"
    notes: Optional[str] = ""
    is_demo: bool = True


class CreateInteractionRequest(BaseModel):
    customer_id: str
    channel: str = "CALL"  # CALL, ZALO, MESSENGER, SMS, DIRECT, EMAIL
    direction: str = "INBOUND"  # INBOUND, OUTBOUND
    interaction_type: str = "CONSULTATION"  # INQUIRY, CONSULTATION, CALLBACK_REQUEST, COMPLAINT, NOTE, FEEDBACK
    occurred_at: Optional[str] = None
    summary: str
    performed_by: str = "Chuyên viên CSKH"
    reference_note: Optional[str] = None
    is_staff_confirmed: bool = True


class CreatePurchaseRequest(BaseModel):
    customer_id: str
    sku: str
    product_name: Optional[str] = None
    order_id: Optional[str] = None
    source_order_code: Optional[str] = None
    purchase_channel: str = "Cửa hàng trực tiếp"
    order_date: Optional[str] = None
    transaction_date: Optional[str] = None
    delivery_date: Optional[str] = None
    delivered_at: Optional[str] = None
    order_status: str = "DELIVERED"  # PENDING, DELIVERED, CANCELLED, RETURNED
    cycle_days: int = 30
    quantity: int = 1
    recorded_by: str = "Chuyên viên CSKH"
    recording_source: Optional[str] = None
    auto_evaluate_rules: bool = True
    notes: Optional[str] = ""


class CreateSupportRequest(BaseModel):
    customer_id: str
    request_type: str = "COMPLAINT_ADR"  # COMPLAINT_ADR, COMPLAINT_QUALITY, COMPLAINT_SHIPPING, GENERAL_SUPPORT
    title: str
    description: str
    sku: Optional[str] = None
    product_name: Optional[str] = None
    occurred_at: Optional[str] = None
    recorded_by: str = "Chuyên viên CSKH"


class CreateCallbackRequest(BaseModel):
    customer_id: str
    preferred_date: str  # YYYY-MM-DD
    preferred_time: Optional[str] = "09:30"
    reason: str
    sku: Optional[str] = None
    product_name: Optional[str] = None
    occurred_at: Optional[str] = None
    recorded_by: str = "Chuyên viên CSKH"


class LinkCopilotInteractionRequest(BaseModel):
    customer_id: str
    session_id: Optional[str] = None
    chat_summary: Optional[str] = None
    consultation_notes: Optional[str] = None
    customer_name: Optional[str] = None
    referenced_sku: Optional[str] = None
    is_confirmed_interaction: bool = False  # False = Lưu nháp nội bộ, True = Xác nhận tương tác với khách
    is_staff_confirmed: Optional[bool] = None
    direction: str = "INBOUND"
    channel: str = "ZALO"
    performed_by: str = "Chuyên viên CSKH"
