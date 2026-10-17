from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from modules.chat.enums import (
    ChatIntent,
    ChatDecision,
    RiskLevel,
    TicketStatus,
    ChatRole
)

# ==============================================================================
# 1. REQUEST & MESSAGE SCHEMAS
# ==============================================================================

class ChatRequest(BaseModel):
    """Schema dữ liệu đầu vào cho yêu cầu chat (Single-turn & Multi-turn)"""
    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: Optional[str] = Field(
        default=None,
        description="Mã phiên hội thoại (UUID hoặc chuỗi định danh). Nếu null, bắt đầu phiên mới."
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Nội dung tin nhắn người dùng (hỗ trợ Unicode tiếng Việt đầy đủ)"
    )
    product_id: Optional[str] = Field(
        default=None,
        description="Mã SKU sản phẩm cần truy vấn ngữ cảnh (nếu có)"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Mã định danh request phục vụ chống gửi trùng lặp (Idempotency) và tracing"
    )

    @field_validator("message")
    @classmethod
    def validate_message_not_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Nội dung tin nhắn không được rỗng hoặc chỉ chứa khoảng trắng.")
        return v.strip()

    @field_validator("session_id", "product_id", "request_id", mode="before")
    @classmethod
    def normalize_empty_strings_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class ChatMessage(BaseModel):
    """Schema lưu trữ một lượt tin nhắn trong ngữ cảnh hội thoại"""
    model_config = ConfigDict(str_strip_whitespace=True)

    message_id: str = Field(..., description="Định danh duy nhất của tin nhắn (UUID do backend cấp)")
    session_id: Optional[str] = Field(default=None, description="Mã phiên hội thoại chứa tin nhắn này")
    role: ChatRole = Field(..., description="Vai trò: USER hoặc ASSISTANT")
    content: str = Field(..., min_length=1, description="Nội dung văn bản tin nhắn")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Thời điểm tạo tin nhắn (UTC)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dữ liệu siêu thông tin bổ trợ nếu cần")


# ==============================================================================
# 2. CITATION & KNOWLEDGE SCHEMAS
# ==============================================================================

class CitationInfo(BaseModel):
    """Biểu diễn nguồn trích dẫn từ Hồ sơ Claims và tài liệu khoa học đã duyệt"""
    claim_id: Optional[str] = Field(default=None, description="Mã hồ sơ Claim (ví dụ CLM-D3-01)")
    document_id: Optional[str] = Field(default=None, description="Mã số văn bản công bố hoặc số đăng ký")
    document_title: Optional[str] = Field(default=None, description="Tên hồ sơ / tài liệu nguồn trích dẫn")
    page: Optional[int] = Field(default=None, description="Số trang tài liệu gốc (nếu có)")
    source_url: Optional[str] = Field(default=None, description="Đường dẫn tra cứu công khai (nếu có)")
    source_version: Optional[str] = Field(default=None, description="Phiên bản tài liệu đã được thẩm định")


# ==============================================================================
# 3. INTENT & SAFETY SCHEMAS
# ==============================================================================

class IntentResult(BaseModel):
    """Kết quả phân loại ý định người dùng phục vụ điều phối luồng xử lý"""
    primary_intent: ChatIntent = Field(default=ChatIntent.UNKNOWN, description="Ý định chính yếu")
    secondary_intents: List[ChatIntent] = Field(default_factory=list, description="Các ý định phụ kèm theo")
    product_ids: List[str] = Field(default_factory=list, description="Danh sách SKU sản phẩm được nhắc đến")
    requires_knowledge: bool = Field(default=False, description="Cần tra cứu Knowledge Vault Claims hay không")
    recommended_route: Optional[str] = Field(default=None, description="Luồng xử lý khuyến nghị")
    reason: Optional[str] = Field(default=None, description="Giải thích lý do phân loại")


class SafetyResult(BaseModel):
    """Kết quả đánh giá an toàn y tế và tuân thủ pháp lý quảng cáo"""
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Cấp độ rủi ro y tế/pháp lý")
    risk_flags: List[str] = Field(default_factory=list, description="Danh sách các cờ rủi ro phát hiện")
    requires_handoff: bool = Field(default=False, description="Bắt buộc chuyển Dược sĩ / chuyên môn hay không")
    reason: Optional[str] = Field(default=None, description="Lý do phân cấp rủi ro hoặc yêu cầu chuyển giao")
    recommended_department: Optional[str] = Field(default=None, description="Bộ phận chuyên môn tiếp nhận")


# ==============================================================================
# 4. TICKET & ACTION SCHEMAS
# ==============================================================================

class TicketData(BaseModel):
    """Schema biểu diễn thông tin Ticket chuyển tuyến Dược vụ (chỉ có ticket_id khi đã lưu thành công)"""
    ticket_id: Optional[str] = Field(default=None, description="Mã Ticket nếu đã lưu thành công vào CSDL; null nếu chưa tạo")
    ticket_type: str = Field(default="MEDICAL_ESCALATION", description="Loại ticket: MEDICAL_ESCALATION, COMPLAINT...")
    status: TicketStatus = Field(default=TicketStatus.NEW, description="Trạng thái xử lý của ticket")
    priority: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Độ ưu tiên xử lý")
    assigned_department: Optional[str] = Field(default="DƯỢC VỤ", description="Phòng ban tiếp nhận")
    created_at: Optional[datetime] = Field(default=None, description="Thời điểm lưu ticket thành công")


class ChatAction(BaseModel):
    """Hành động gợi ý cho nhân viên tư vấn hoặc giao diện người dùng"""
    type: str = Field(..., description="Mã loại hành động (ví dụ: COPY_TEXT, TRANSFER_PHARMACIST, VIEW_CLAIM)")
    label: str = Field(..., description="Nhãn hiển thị trực quan cho người dùng")
    requires_approval: bool = Field(default=True, description="Yêu cầu con người phê duyệt trước khi thực thi")


# ==============================================================================
# 5. CHAT RESPONSE SCHEMA (HỢP ĐỒNG API CHÍNH THỨC)
# ==============================================================================

class ChatResponse(BaseModel):
    """Schema chuẩn đầu ra của hệ thống AI Chatbot DION Healthcare"""
    schema_version: str = Field(default="1.0", description="Phiên bản schema hợp đồng API")
    session_id: Optional[str] = Field(default=None, description="Mã phiên hội thoại được duy trì")
    message_id: Optional[str] = Field(default=None, description="Mã tin nhắn trả lời")
    trace_id: Optional[str] = Field(default=None, description="Mã trace phục vụ kiểm toán và debug")
    intent: ChatIntent = Field(default=ChatIntent.UNKNOWN, description="Ý định chính đã nhận diện")
    decision: ChatDecision = Field(default=ChatDecision.DRAFT_FOR_APPROVAL, description="Trạng thái quyết định điều phối")
    answer: str = Field(..., description="Nội dung phản hồi trả về")
    product_ids: List[str] = Field(default_factory=list, description="Danh sách SKU liên quan trong câu trả lời")
    sources: List[CitationInfo] = Field(default_factory=list, description="Danh mục nguồn trích dẫn Claims đã xác thực")
    risk: SafetyResult = Field(default_factory=SafetyResult, description="Đánh giá rủi ro an toàn y khoa")
    actions: List[ChatAction] = Field(default_factory=list, description="Danh sách hành động gợi ý đề xuất")
    ticket_id: Optional[str] = Field(default=None, description="Mã Ticket nếu đã lưu vào hệ thống; null nếu chưa lưu")

    @model_validator(mode="after")
    def validate_invariants(self) -> "ChatResponse":
        # Bất biến 1: Nếu trạng thái là INSUFFICIENT_EVIDENCE và không có nguồn thực tế, sources phải rỗng
        if self.decision == ChatDecision.INSUFFICIENT_EVIDENCE:
            if not any(s.claim_id for s in self.sources):
                self.sources = []
        
        # Bất biến 2: Nếu chưa lưu ticket thật thì ticket_id phải là None, không tạo ticket giả
        if self.ticket_id is not None and not str(self.ticket_id).strip():
            self.ticket_id = None
            
        return self


# ==============================================================================
# 6. LEGACY SCHEMAS (DUY TRÌ TƯƠNG THÍCH 100% VỚI /api/copilot/ask)
# ==============================================================================

class LegacyCopilotRequest(BaseModel):
    """Hợp đồng request cũ của endpoint POST /api/copilot/ask"""
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(..., min_length=1, description="Câu hỏi người dùng")
    sku: str = Field(default="ALL", description="Mã sản phẩm hoặc 'ALL'")


class LegacyCopilotResponse(BaseModel):
    """Hợp đồng response cũ của endpoint POST /api/copilot/ask"""
    type: str = Field(..., description="NORMAL, ESCALATION, INSUFFICIENT_EVIDENCE...")
    badge: str = Field(..., description="Huy hiệu hiển thị trạng thái trên giao diện")
    content: str = Field(..., description="Nội dung câu trả lời")
    citations: List[str] = Field(default_factory=list, description="Danh sách mã Claim trích dẫn")
    source_claims: List[Dict[str, Any]] = Field(default_factory=list, description="Chi tiết các Claims làm bằng chứng")
    handoff_required: bool = Field(default=False, description="Cờ đánh dấu cần chuyển Dược sĩ chuyên môn")


# ==============================================================================
# 7. ERROR SCHEMAS
# ==============================================================================

class ErrorDetail(BaseModel):
    """Chi tiết lỗi chuẩn hóa"""
    code: str = Field(..., description="Mã lỗi hệ thống (ví dụ: INVALID_MESSAGE, RATE_LIMIT)")
    message: str = Field(..., description="Thông điệp mô tả lỗi thân thiện")
    field: Optional[str] = Field(default=None, description="Tên trường dữ liệu gây ra lỗi (nếu có)")


class ChatErrorResponse(BaseModel):
    """Phản hồi lỗi chuẩn mực của API Chat"""
    schema_version: str = Field(default="1.0", description="Phiên bản schema")
    error: str = Field(..., description="Tóm tắt thông báo lỗi")
    details: List[ErrorDetail] = Field(default_factory=list, description="Chi tiết danh sách các lỗi phát hiện")
    trace_id: Optional[str] = Field(default=None, description="Mã trace phục vụ tra cứu logs sự cố")


# ==============================================================================
# 8. ADAPTER UTILITIES (CHUYỂN ĐỔI AN TOÀN GIỮA LEGACY VÀ SCHEMA MỚI)
# ==============================================================================

def legacy_to_chat_response(
    legacy: LegacyCopilotResponse,
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None
) -> ChatResponse:
    """Chuyển đổi dữ liệu từ LegacyCopilotResponse sang ChatResponse chuẩn mới"""
    decision_map = {
        "NORMAL": ChatDecision.DRAFT_FOR_APPROVAL,
        "ESCALATION": ChatDecision.HANDOFF_REQUIRED,
        "INSUFFICIENT_EVIDENCE": ChatDecision.INSUFFICIENT_EVIDENCE,
        "BLOCKED": ChatDecision.BLOCKED,
    }
    decision = decision_map.get(legacy.type, ChatDecision.DRAFT_FOR_APPROVAL)
    
    citations = [
        CitationInfo(
            claim_id=c.get("claim_id"),
            document_title=c.get("evidence"),
            source_version="Verified"
        )
        for c in legacy.source_claims
    ] if legacy.source_claims else [CitationInfo(claim_id=cid) for cid in legacy.citations]
    
    product_ids = list({c.get("sku") for c in legacy.source_claims if c.get("sku")})

    risk = SafetyResult(
        risk_level=RiskLevel.HIGH if legacy.handoff_required else RiskLevel.LOW,
        requires_handoff=legacy.handoff_required,
        reason="Yêu cầu chuyển Dược sĩ thẩm định" if legacy.handoff_required else None,
        recommended_department="DƯỢC VỤ" if legacy.handoff_required else None
    )

    actions = []
    if legacy.handoff_required:
        actions.append(ChatAction(type="TRANSFER_PHARMACIST", label="Chuyển Dược sĩ phụ trách", requires_approval=True))
    else:
        actions.append(ChatAction(type="COPY_ANSWER", label="Sao chép nội dung đã duyệt", requires_approval=False))

    return ChatResponse(
        schema_version="1.0",
        session_id=session_id,
        trace_id=trace_id,
        intent=ChatIntent.MEDICAL_RISK if legacy.handoff_required else ChatIntent.PRODUCT_INFO,
        decision=decision,
        answer=legacy.content,
        product_ids=product_ids,
        sources=citations,
        risk=risk,
        actions=actions,
        ticket_id=None
    )


def chat_response_to_legacy(chat_resp: ChatResponse) -> LegacyCopilotResponse:
    """Chuyển đổi dữ liệu từ ChatResponse mới sang LegacyCopilotResponse để phục vụ client cũ"""
    type_map = {
        ChatDecision.DRAFT_FOR_APPROVAL: "NORMAL",
        ChatDecision.READY_TO_SEND: "NORMAL",
        ChatDecision.INSUFFICIENT_EVIDENCE: "INSUFFICIENT_EVIDENCE",
        ChatDecision.HANDOFF_REQUIRED: "ESCALATION",
        ChatDecision.BLOCKED: "ESCALATION",
        ChatDecision.CLARIFICATION_REQUIRED: "INSUFFICIENT_EVIDENCE",
        ChatDecision.SYSTEM_ERROR: "INSUFFICIENT_EVIDENCE",
    }
    legacy_type = type_map.get(chat_resp.decision, "NORMAL")
    
    badge_map = {
        "NORMAL": "✅ ĐÃ XÁC THỰC TỪ CLAIMS ĐƯỢC DUYỆT",
        "ESCALATION": "⚠️ YÊU CẦU CHUYỂN DƯỢC SĨ TƯ VẤN CHUYÊN MÔN",
        "INSUFFICIENT_EVIDENCE": "⚠️ CHƯA ĐỦ CĂN CỨ XÁC MINH"
    }
    badge = badge_map.get(legacy_type, "✅ THÔNG TIN SẢN PHẨM")
    
    citations = [s.claim_id for s in chat_resp.sources if s.claim_id]
    source_claims = [
        {
            "claim_id": s.claim_id,
            "evidence": s.document_title or "Hồ sơ công bố sản phẩm",
            "sku": chat_resp.product_ids[0] if chat_resp.product_ids else None
        }
        for s in chat_resp.sources if s.claim_id
    ]

    return LegacyCopilotResponse(
        type=legacy_type,
        badge=badge,
        content=chat_resp.answer,
        citations=citations,
        source_claims=source_claims,
        handoff_required=chat_resp.risk.requires_handoff
    )
