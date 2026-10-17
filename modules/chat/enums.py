from enum import Enum

class ChatIntent(str, Enum):
    """Phân loại ý định của người dùng trong hội thoại tư vấn Dược/TPBS"""
    GREETING = "GREETING"
    PRODUCT_INFO = "PRODUCT_INFO"
    PRODUCT_COMPARISON = "PRODUCT_COMPARISON"
    USAGE_INFORMATION = "USAGE_INFORMATION"
    MEDICAL_RISK = "MEDICAL_RISK"
    SAFETY_COMPLAINT = "SAFETY_COMPLAINT"
    BUY_PRODUCT = "BUY_PRODUCT"
    B2B_INQUIRY = "B2B_INQUIRY"
    ORDER_STATUS = "ORDER_STATUS"
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"
    MARKETING_REQUEST = "MARKETING_REQUEST"
    PROHIBITED_GENERATION = "PROHIBITED_GENERATION"
    OPT_OUT = "OPT_OUT"
    GENERAL_CHAT = "GENERAL_CHAT"
    OFF_TOPIC = "OFF_TOPIC"
    UNKNOWN = "UNKNOWN"

class ChatDecision(str, Enum):
    """Quyết định điều phối luồng xử lý câu trả lời của Chatbot"""
    DRAFT_FOR_APPROVAL = "DRAFT_FOR_APPROVAL"      # Bản nháp cần nhân viên/Dược sĩ duyệt trước khi gửi
    READY_TO_SEND = "READY_TO_SEND"                # Trạng thái sẵn sàng gửi (khi đã kiểm duyệt)
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"# Chưa đủ căn cứ xác thực từ Claims đã duyệt
    HANDOFF_REQUIRED = "HANDOFF_REQUIRED"          # Bắt buộc chuyển tuyến chuyên môn cho Dược sĩ
    BLOCKED = "BLOCKED"                            # Chặn do vi phạm quy định cấm / an toàn
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED" # Cần hỏi thêm thông tin để làm rõ
    SYSTEM_ERROR = "SYSTEM_ERROR"                  # Lỗi hệ thống / dịch vụ ngoại vi

class RiskLevel(str, Enum):
    """Mức độ rủi ro an toàn y tế và pháp lý theo Nghị định 342 & Luật 91"""
    LOW = "LOW"            # An toàn, câu hỏi thông tin cơ bản
    MEDIUM = "MEDIUM"      # Cần chú ý (hỏi về liều lượng, đối tượng người lớn tuổi)
    HIGH = "HIGH"          # Rủi ro cao (thai kỳ, bệnh nền nặng, tương tác thuốc)
    CRITICAL = "CRITICAL"  # Cực kỳ nguy cấp (dị ứng cấp, phản ứng bất lợi nghiêm trọng)

class TicketStatus(str, Enum):
    """Trạng thái vòng đời của Ticket chuyển tuyến Dược vụ"""
    NEW = "NEW"                  # Mới tạo trong hệ thống
    ASSIGNED = "ASSIGNED"        # Đã phân công Dược sĩ phụ trách
    IN_PROGRESS = "IN_PROGRESS"  # Đang liên hệ / xử lý chuyên môn
    RESOLVED = "RESOLVED"        # Đã tư vấn và giải quyết xong
    CLOSED = "CLOSED"            # Đã đóng ticket

class ChatRole(str, Enum):
    """Vai trò của người tham gia hội thoại công khai"""
    USER = "USER"
    ASSISTANT = "ASSISTANT"
