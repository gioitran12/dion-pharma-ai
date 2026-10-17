"""
DION Healthcare AI — Knowledge Hub Schemas & Enums (Bước 02A)
Định nghĩa Data Models chuẩn hóa cho Product, Claim và Kết quả Thẩm định Claim.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ==============================================================================
# 1. ENUMS
# ==============================================================================

class KnowledgeZone(str, Enum):
    """Phân vùng tri thức sản phẩm phục vụ kiểm soát phạm vi tiếp cận thông tin"""
    COMMERCIAL_APPROVED = "COMMERCIAL_APPROVED"  # Vùng thương mại công khai đã duyệt
    INTERNAL_MEDICAL = "INTERNAL_MEDICAL"        # Tài liệu chuyên môn / Dược vụ nội bộ
    INTERNAL_EXPERT = "INTERNAL_EXPERT"          # Vùng chuyên gia nội bộ (tương thích dữ liệu mẫu)
    RESEARCH = "RESEARCH"                        # Dữ liệu nghiên cứu / tiền lâm sàng
    EXPIRED = "EXPIRED"                          # Vùng lưu trữ Claim đã hết hiệu lực
    UNKNOWN = "UNKNOWN"                          # Vùng không xác định


class ClaimStatus(str, Enum):
    """Trạng thái vòng đời phê duyệt của một Claim"""
    APPROVED = "APPROVED"    # Đã được người có thẩm quyền phê duyệt
    DRAFT = "DRAFT"          # Bản thảo mới khởi tạo
    PENDING = "PENDING"      # Đang chờ hội đồng Dược vụ thẩm định
    REJECTED = "REJECTED"    # Bị từ chối phê duyệt
    EXPIRED = "EXPIRED"      # Đã hết hạn hiệu lực
    REVOKED = "REVOKED"      # Bị thu hồi hiệu lực do rủi ro / thay đổi quy chế
    SUSPENDED = "SUSPENDED"  # Tạm đình chỉ sử dụng


class ValidationCode(str, Enum):
    """Mã lý do giải thích kết quả thẩm định Claim"""
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"                    # Không tìm thấy sản phẩm
    SKU_MISMATCH = "SKU_MISMATCH"                              # Claim không thuộc SKU được yêu cầu
    CLAIM_NOT_FOUND = "CLAIM_NOT_FOUND"                        # Không tìm thấy bản ghi Claim
    CLAIM_NOT_APPROVED = "CLAIM_NOT_APPROVED"                  # Claim chưa ở trạng thái APPROVED
    CLAIM_EXPIRED = "CLAIM_EXPIRED"                            # Claim đã quá ngày hết hạn
    CLAIM_NOT_YET_EFFECTIVE = "CLAIM_NOT_YET_EFFECTIVE"        # Claim chưa đến ngày bắt đầu hiệu lực
    CLAIM_REVOKED = "CLAIM_REVOKED"                            # Claim đã bị thu hồi
    RESTRICTED_KNOWLEDGE_ZONE = "RESTRICTED_KNOWLEDGE_ZONE"    # Thuộc vùng tri thức nội bộ / hạn chế
    MISSING_SOURCE = "MISSING_SOURCE"                          # Thiếu tài liệu hoặc hồ sơ chứng minh
    MISSING_APPROVAL_EVIDENCE = "MISSING_APPROVAL_EVIDENCE"    # Thiếu người ký duyệt / chữ ký thẩm định
    INVALID_DATE = "INVALID_DATE"                              # Định dạng ngày tháng không hợp lệ
    USAGE_SCOPE_NOT_ALLOWED = "USAGE_SCOPE_NOT_ALLOWED"        # Vượt quá phạm vi sử dụng cho phép
    DUPLICATE_CLAIM_ID = "DUPLICATE_CLAIM_ID"                  # Trùng lặp mã Claim
    DUPLICATE_SKU = "DUPLICATE_SKU"                            # Trùng lặp mã SKU
    EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"                    # Bằng chứng trích dẫn không khớp nội dung


# ==============================================================================
# 2. PRODUCT DATA MODEL
# ==============================================================================

class ProductRecord(BaseModel):
    """Mô hình dữ liệu sản phẩm chuẩn hóa trong Knowledge Hub"""
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(..., min_length=1, description="Mã SKU định danh duy nhất của sản phẩm")
    name: str = Field(..., min_length=1, description="Tên thương mại chính thức của sản phẩm")
    category: Optional[str] = Field(default=None, description="Danh mục sản phẩm")
    regulatory_class: Optional[str] = Field(default=None, description="Phân loại pháp lý (TPBVSK, Thuốc OTC...)")
    description: Optional[str] = Field(default=None, description="Mô tả tóm tắt sản phẩm")
    target_users: List[str] = Field(default_factory=list, description="Đối tượng sử dụng được công bố")
    mandatory_disclaimer: Optional[str] = Field(
        default="Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh.",
        description="Khuyến cáo bắt buộc theo Nghị định 342"
    )
    market: Optional[str] = Field(default="VN", description="Thị trường phân phối (mặc định VN)")
    registration_number: Optional[str] = Field(default=None, description="Số đăng ký công bố sản phẩm Cục ATTP")
    ad_permit_number: Optional[str] = Field(default=None, description="Số giấy phép xác nhận nội dung quảng cáo")
    active_ingredients: List[Dict[str, str]] = Field(default_factory=list, description="Thành phần hoạt chất công bố")
    contraindications: Optional[str] = Field(default=None, description="Chống chỉ định / Cảnh báo mẫn cảm")
    clinical_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Tài liệu nghiên cứu lâm sàng viện dẫn")

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("SKU không được để trống")
        return v.strip()


# ==============================================================================
# 3. CLAIM DATA MODEL
# ==============================================================================

class ClaimRecord(BaseModel):
    """Mô hình dữ liệu Claim (Công dụng / Phát biểu khoa học) chuẩn hóa"""
    model_config = ConfigDict(str_strip_whitespace=True)

    claim_id: str = Field(..., min_length=1, description="Mã định danh duy nhất của Claim (ví dụ: CLM-D3-01)")
    product_sku: str = Field(..., min_length=1, description="Mã SKU của sản phẩm sở hữu Claim này")
    claim_text: str = Field(..., min_length=1, description="Nội dung phát biểu công dụng đã được thẩm định")
    zone: KnowledgeZone = Field(default=KnowledgeZone.COMMERCIAL_APPROVED, description="Vùng tri thức")
    status: ClaimStatus = Field(default=ClaimStatus.APPROVED, description="Trạng thái phê duyệt")
    effective_from: Optional[str] = Field(default=None, description="Ngày bắt đầu hiệu lực (YYYY-MM-DD)")
    effective_until: Optional[str] = Field(default=None, description="Ngày hết hạn hiệu lực (YYYY-MM-DD)")
    source_document_id: Optional[str] = Field(default=None, description="Số văn bản / Số hồ sơ tiếp nhận ĐKSP")
    source_reference: Optional[str] = Field(default=None, description="Tên tài liệu / Hồ sơ bằng chứng khoa học")
    evidence_source: Optional[str] = Field(default=None, description="Tương thích ngược với trường evidence_source cũ")
    approved_by: Optional[str] = Field(default=None, description="Người hoặc hội đồng thẩm định phê duyệt")
    usage_scope: Optional[str] = Field(default="COMMERCIAL_ALL", description="Phạm vi sử dụng cho phép")
    market: Optional[str] = Field(default="VN", description="Thị trường áp dụng")
    required_disclaimer: Optional[str] = Field(default=None, description="Disclaimer riêng của Claim nếu có")
    prohibited_expressions: List[str] = Field(default_factory=list, description="Từ ngữ cấm đi kèm")
    evidence_status: Optional[str] = Field(default="VERIFIED", description="Trạng thái xác minh bằng chứng")
    original_evidence_source: Optional[str] = Field(default=None, description="Bằng chứng gốc trước khi đối soát")
    unverified_citations: List[str] = Field(default_factory=list, description="Các trích dẫn bị loại trừ")

    @field_validator("claim_id")
    @classmethod
    def validate_claim_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Claim ID không được để trống")
        return v.strip()

    def get_evidence(self) -> Optional[str]:
        """Lấy chuỗi tài liệu chứng minh ưu tiên source_reference hoặc evidence_source"""
        return self.source_reference or self.evidence_source or self.source_document_id


# ==============================================================================
# 4. CLAIM VALIDATION RESULT
# ==============================================================================

class ClaimValidationResult(BaseModel):
    """Kết quả kiểm tra tính hợp lệ và đủ điều kiện sử dụng của một Claim"""
    claim_id: str = Field(..., description="Mã Claim được kiểm tra")
    product_sku: str = Field(..., description="SKU được đối soát")
    eligible: bool = Field(..., description="Có đủ điều kiện sử dụng trong phạm vi yêu cầu hay không")
    review_required: bool = Field(default=False, description="Cần chuyên viên Dược vụ xem xét lại hay không")
    reasons: List[ValidationCode] = Field(default_factory=list, description="Danh sách các mã lý do từ chối/cảnh báo")
    details: Optional[str] = Field(default=None, description="Mô tả chi tiết giải thích cho người dùng/admin")
    as_of_date: str = Field(..., description="Thời điểm ngày đối soát (YYYY-MM-DD)")


# ==============================================================================
# 5. DATA VALIDATION REPORT MODELS
# ==============================================================================

class ValidationSeverity(str, Enum):
    ERROR = "ERROR"      # Lỗi nghiêm trọng khiến dữ liệu không an toàn để sử dụng
    WARNING = "WARNING"  # Cảnh báo thiếu trường tùy chọn hoặc cần hoàn thiện thêm
    INFO = "INFO"        # Thông tin thống kê hiện trạng


class DataValidationItem(BaseModel):
    severity: ValidationSeverity
    code: str
    message: str
    entity_type: str = "CLAIM"  # PRODUCT, CLAIM, DATASET
    entity_id: Optional[str] = None
    field_name: Optional[str] = None


class DataValidationSummary(BaseModel):
    total_products: int = 0
    total_claims: int = 0
    eligible_claims: int = 0
    expired_claims: int = 0
    internal_claims: int = 0
    missing_fields_claims: int = 0
    errors_count: int = 0
    warnings_count: int = 0
    items: List[DataValidationItem] = Field(default_factory=list)
