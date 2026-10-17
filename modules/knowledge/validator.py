"""
DION Healthcare AI — Claim Eligibility Validator (Bước 02A)
Bộ thẩm định điều kiện sử dụng Claim theo tiêu chuẩn y dược và pháp lý (Nghị định 342 & Luật 91).
"""

from datetime import datetime, date
from typing import Union, Optional, Dict, Any, List

from modules.knowledge.schemas import (
    ClaimRecord,
    KnowledgeZone,
    ClaimStatus,
    ValidationCode,
    ClaimValidationResult,
)


class ClaimEligibilityValidator:
    """
    Bộ thẩm định độc lập kiểm tra một Claim có đủ điều kiện pháp lý và nghiệp vụ
    để sử dụng trong các tác vụ thương mại / tư vấn hay không.
    """

    @classmethod
    def parse_date(cls, date_val: Union[date, str, None]) -> Optional[date]:
        """Parse chuỗi ngày sang datetime.date an toàn."""
        if date_val is None:
            return None
        if isinstance(date_val, date):
            return date_val
        try:
            return datetime.strptime(str(date_val).strip(), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    @classmethod
    def validate_claim_eligibility(
        cls,
        claim: Union[ClaimRecord, Dict[str, Any], None],
        product_sku: str,
        usage_context: str = "COMMERCIAL_ADVICE",
        as_of_date: Optional[Union[date, str]] = None,
    ) -> ClaimValidationResult:
        """
        Thẩm định tính hợp lệ của Claim đối với SKU và ngữ cảnh sử dụng.
        
        Args:
            claim: Bản ghi ClaimRecord hoặc dictionary thô
            product_sku: SKU sản phẩm được yêu cầu đối soát
            usage_context: Ngữ cảnh ("COMMERCIAL_ADVICE", "INTERNAL_CONSULTATION"...)
            as_of_date: Ngày đối soát hiệu lực (hỗ trợ inject ngày kiểm thử tất định)
        """
        # Xác định ngày đối soát chuẩn
        if as_of_date is None:
            target_date = datetime.now().date()
        elif isinstance(as_of_date, date):
            target_date = as_of_date
        else:
            parsed_target = cls.parse_date(as_of_date)
            if parsed_target is None:
                # Nếu ngày đối soát truyền vào sai định dạng, dùng ngày hiện tại và ghi chú
                target_date = datetime.now().date()
            else:
                target_date = parsed_target

        as_of_str = target_date.strftime("%Y-%m-%d")

        # 1. Kiểm tra tồn tại Claim
        if claim is None:
            return ClaimValidationResult(
                claim_id="UNKNOWN",
                product_sku=product_sku,
                eligible=False,
                review_required=True,
                reasons=[ValidationCode.CLAIM_NOT_FOUND],
                details="Không tìm thấy bản ghi Claim.",
                as_of_date=as_of_str,
            )

        # Chuyển đổi sang ClaimRecord nếu nhận dictionary
        if isinstance(claim, dict):
            c_dict = dict(claim)
            # Ánh xạ product_sku: ưu tiên product_sku > sku > product_sku truyền vào
            if "product_sku" not in c_dict:
                c_dict["product_sku"] = c_dict.get("sku") or product_sku
            if "source_reference" not in c_dict and "evidence_source" in c_dict:
                c_dict["source_reference"] = c_dict["evidence_source"]
            try:
                claim_obj = ClaimRecord(**c_dict)
            except Exception as e:
                return ClaimValidationResult(
                    claim_id=str(c_dict.get("claim_id", "UNKNOWN")),
                    product_sku=product_sku,
                    eligible=False,
                    review_required=True,
                    reasons=[ValidationCode.MISSING_SOURCE],
                    details=f"Dữ liệu Claim không hợp lệ: {str(e)}",
                    as_of_date=as_of_str,
                )
        else:
            claim_obj = claim

        reasons: List[ValidationCode] = []
        review_required = False

        # 2. Kiểm tra SKU khớp chính xác (Chống rò rỉ chéo sản phẩm)
        clean_req_sku = product_sku.strip()
        clean_claim_sku = claim_obj.product_sku.strip()
        if clean_req_sku != clean_claim_sku:
            reasons.append(ValidationCode.SKU_MISMATCH)

        # 3. Kiểm tra Trạng thái phê duyệt (ClaimStatus)
        if claim_obj.status == ClaimStatus.REVOKED:
            reasons.append(ValidationCode.CLAIM_REVOKED)
        elif claim_obj.status == ClaimStatus.EXPIRED:
            reasons.append(ValidationCode.CLAIM_EXPIRED)
        elif claim_obj.status != ClaimStatus.APPROVED:
            reasons.append(ValidationCode.CLAIM_NOT_APPROVED)

        # 4. Kiểm tra Vùng tri thức (KnowledgeZone)
        # Trong tư vấn thương mại, chỉ chấp nhận COMMERCIAL_APPROVED
        if usage_context in ("COMMERCIAL_ADVICE", "COMMERCIAL", "CUSTOMER_FACING"):
            if claim_obj.zone != KnowledgeZone.COMMERCIAL_APPROVED:
                reasons.append(ValidationCode.RESTRICTED_KNOWLEDGE_ZONE)

        # 5. Kiểm tra Hiệu lực ngày tháng
        if claim_obj.effective_until:
            until_date = cls.parse_date(claim_obj.effective_until)
            if until_date is None:
                reasons.append(ValidationCode.INVALID_DATE)
            elif until_date < target_date:
                reasons.append(ValidationCode.CLAIM_EXPIRED)

        if claim_obj.effective_from:
            from_date = cls.parse_date(claim_obj.effective_from)
            if from_date is None:
                reasons.append(ValidationCode.INVALID_DATE)
            elif from_date > target_date:
                reasons.append(ValidationCode.CLAIM_NOT_YET_EFFECTIVE)

        # 6. Kiểm tra Nguồn tài liệu chứng minh
        evidence = claim_obj.get_evidence()
        if not evidence or not evidence.strip():
            reasons.append(ValidationCode.MISSING_SOURCE)

        # 6b. Kiem tra Trang thai bang chung nguon (EVIDENCE_MISMATCH)
        if getattr(claim_obj, "evidence_status", None) == "EVIDENCE_MISMATCH":
            reasons.append(ValidationCode.EVIDENCE_MISMATCH)

        # 7. Kiểm tra Bằng chứng phê duyệt của Dược vụ
        if not claim_obj.approved_by or not claim_obj.approved_by.strip():
            # Thiếu người ký duyệt -> cần rà soát lại
            reasons.append(ValidationCode.MISSING_APPROVAL_EVIDENCE)
            review_required = True

        eligible = len(reasons) == 0
        if not eligible:
            review_required = True

        details = None
        if not eligible:
            details = f"Claim không đủ điều kiện do: {', '.join([r.value for r in reasons])}"
        elif review_required:
            details = "Claim đủ điều kiện kỹ thuật nhưng cần thẩm định thêm chữ ký dược vụ."

        return ClaimValidationResult(
            claim_id=claim_obj.claim_id,
            product_sku=clean_req_sku,
            eligible=eligible,
            review_required=review_required,
            reasons=reasons,
            details=details,
            as_of_date=as_of_str,
        )


def validate_claim_eligibility(
    claim: Union[ClaimRecord, Dict[str, Any], None],
    product_sku: str,
    usage_context: str = "COMMERCIAL_ADVICE",
    as_of_date: Optional[Union[date, str]] = None,
) -> ClaimValidationResult:
    """Helper function tiện ích gọi ClaimEligibilityValidator."""
    return ClaimEligibilityValidator.validate_claim_eligibility(
        claim=claim,
        product_sku=product_sku,
        usage_context=usage_context,
        as_of_date=as_of_date,
    )
