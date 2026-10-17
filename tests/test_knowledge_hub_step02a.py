"""
DION Healthcare AI — Unit & Integration Tests for Step 02A
Bộ 21 bài kiểm thử tự động cho Product Knowledge Hub, Claim Records và Claim Eligibility Validator.
"""

import os
import json
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from server import app
from modules.knowledge.schemas import (
    ProductRecord,
    ClaimRecord,
    KnowledgeZone,
    ClaimStatus,
    ValidationCode,
    ClaimValidationResult,
)
from modules.knowledge.validator import (
    ClaimEligibilityValidator,
    validate_claim_eligibility,
)
from modules.knowledge.repository import (
    BaseKnowledgeRepository,
    JSONKnowledgeRepository,
    get_knowledge_repository,
)
from modules.claims_hub import (
    get_all_products,
    get_product_by_sku,
    get_active_claims,
    get_claims_summary,
    get_product_record,
    get_eligible_claims_records,
)
from scripts.validate_product_knowledge import validate_product_knowledge_file

client = TestClient(app)


# ------------------------------------------------------------------------------
# Test 1: Đọc danh mục sản phẩm hợp lệ từ Knowledge Hub
# ------------------------------------------------------------------------------
def test_01_list_products():
    repo = get_knowledge_repository()
    products = repo.list_products()
    assert len(products) == 3
    skus = [p.sku for p in products]
    assert "DION-D3-1000" in skus
    assert "DION-CAL-MOM" in skus
    assert "DION-FE-FOLIC" in skus
    assert all(isinstance(p, ProductRecord) for p in products)


# ------------------------------------------------------------------------------
# Test 2: Tìm sản phẩm theo SKU chính xác
# ------------------------------------------------------------------------------
def test_02_get_product_by_sku():
    repo = get_knowledge_repository()
    prod = repo.get_product_by_sku("DION-CAL-MOM")
    assert prod is not None
    assert prod.sku == "DION-CAL-MOM"
    assert "Cal-Mom" in prod.name
    assert "Thực phẩm bảo vệ sức khỏe" in (prod.regulatory_class or "")


# ------------------------------------------------------------------------------
# Test 3: SKU không tồn tại trả về None
# ------------------------------------------------------------------------------
def test_03_nonexistent_sku():
    repo = get_knowledge_repository()
    prod = repo.get_product_by_sku("NON_EXISTENT_SKU_9999")
    assert prod is None
    claims = repo.get_claims_by_product("NON_EXISTENT_SKU_9999")
    assert claims == []
    eligible = repo.get_eligible_commercial_claims("NON_EXISTENT_SKU_9999")
    assert eligible == []


# ------------------------------------------------------------------------------
# Test 4: Phát hiện SKU bị trùng trong dữ liệu
# ------------------------------------------------------------------------------
def test_04_detect_duplicate_sku(tmp_path):
    bad_data = {
        "products": [
            {"sku": "SKU-DUP", "name": "Sản phẩm A", "claims": []},
            {"sku": "SKU-DUP", "name": "Sản phẩm B (trùng SKU)", "claims": []},
        ]
    }
    file_path = tmp_path / "dup_sku.json"
    file_path.write_text(json.dumps(bad_data), encoding="utf-8")

    summary = validate_product_knowledge_file(file_path)
    assert summary.errors_count > 0
    codes = [item.code for item in summary.items]
    assert "DUPLICATE_SKU" in codes


# ------------------------------------------------------------------------------
# Test 5: Lấy Claims của đúng sản phẩm
# ------------------------------------------------------------------------------
def test_05_get_claims_by_product():
    repo = get_knowledge_repository()
    claims_d3 = repo.get_claims_by_product("DION-D3-1000")
    assert len(claims_d3) == 4
    claim_ids = [c.claim_id for c in claims_d3]
    assert "CLM-D3-01" in claim_ids
    assert "CLM-D3-02" in claim_ids
    assert "CLM-D3-03" in claim_ids
    assert "CLM-D3-04" in claim_ids


# ------------------------------------------------------------------------------
# Test 6: Không rò rỉ Claims giữa hai SKU
# ------------------------------------------------------------------------------
def test_06_no_cross_sku_leakage():
    repo = get_knowledge_repository()
    claims_cal = repo.get_claims_by_product("DION-CAL-MOM")
    assert len(claims_cal) >= 2
    claim_ids_cal = [c.claim_id for c in claims_cal]
    assert "CLM-D3-01" not in claim_ids_cal
    assert "CLM-FE-01" not in claim_ids_cal
    assert all(c.product_sku == "DION-CAL-MOM" for c in claims_cal)


# ------------------------------------------------------------------------------
# Test 7: Chỉ nhận Claims thương mại đủ điều kiện
# ------------------------------------------------------------------------------
def test_07_eligible_commercial_claims():
    repo = get_knowledge_repository()
    # D3 có 4 claims: CLM-D3-01 (Approved), CLM-D3-02 (Approved), CLM-D3-03 (Expired), CLM-D3-04 (Internal)
    # Thời điểm 2026-10-16: chỉ có 01 và 02 đủ điều kiện
    eligible = repo.get_eligible_commercial_claims("DION-D3-1000", as_of_date="2026-10-16")
    assert len(eligible) == 2
    eligible_ids = [c.claim_id for c in eligible]
    assert "CLM-D3-01" in eligible_ids
    assert "CLM-D3-02" in eligible_ids
    assert "CLM-D3-03" not in eligible_ids
    assert "CLM-D3-04" not in eligible_ids


# ------------------------------------------------------------------------------
# Test 8: Claim thuộc vùng INTERNAL_MEDICAL / INTERNAL_EXPERT bị loại khỏi thương mại
# ------------------------------------------------------------------------------
def test_08_internal_expert_claims_excluded():
    repo = get_knowledge_repository()
    claim_internal = repo.get_claim_by_id("CLM-D3-04")
    assert claim_internal is not None
    assert claim_internal.zone in (KnowledgeZone.INTERNAL_EXPERT, KnowledgeZone.INTERNAL_MEDICAL)

    val = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=claim_internal,
        product_sku="DION-D3-1000",
        usage_context="COMMERCIAL_ADVICE",
        as_of_date="2026-10-16",
    )
    assert val.eligible is False
    assert ValidationCode.RESTRICTED_KNOWLEDGE_ZONE in val.reasons


# ------------------------------------------------------------------------------
# Test 9: Claim hết hạn bị loại
# ------------------------------------------------------------------------------
def test_09_expired_claim_excluded():
    repo = get_knowledge_repository()
    claim_expired = repo.get_claim_by_id("CLM-D3-03")
    assert claim_expired is not None
    assert claim_expired.effective_until == "2025-12-31"

    val = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=claim_expired,
        product_sku="DION-D3-1000",
        usage_context="COMMERCIAL_ADVICE",
        as_of_date="2026-10-16",
    )
    assert val.eligible is False
    assert ValidationCode.CLAIM_EXPIRED in val.reasons


# ------------------------------------------------------------------------------
# Test 10: Claim chưa đến ngày hiệu lực bị loại
# ------------------------------------------------------------------------------
def test_10_future_claim_not_yet_effective():
    future_claim = ClaimRecord(
        claim_id="CLM-FUTURE-01",
        product_sku="DION-D3-1000",
        claim_text="Công dụng áp dụng cho công thức cải tiến năm 2030.",
        status=ClaimStatus.APPROVED,
        zone=KnowledgeZone.COMMERCIAL_APPROVED,
        effective_from="2030-01-01",
        effective_until="2035-12-31",
        approved_by="DS. Nguyễn Văn An",
        source_reference="Hồ sơ công bố bổ sung năm 2030",
    )
    val = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=future_claim,
        product_sku="DION-D3-1000",
        as_of_date="2026-10-16",
    )
    assert val.eligible is False
    assert ValidationCode.CLAIM_NOT_YET_EFFECTIVE in val.reasons


# ------------------------------------------------------------------------------
# Test 11: Claim bị thu hồi (REVOKED) bị loại
# ------------------------------------------------------------------------------
def test_11_revoked_claim_excluded():
    revoked_claim = ClaimRecord(
        claim_id="CLM-REVOKED-01",
        product_sku="DION-D3-1000",
        claim_text="Công dụng bị cơ quan y tế thu hồi.",
        status=ClaimStatus.REVOKED,
        zone=KnowledgeZone.COMMERCIAL_APPROVED,
        effective_until="2028-12-31",
        approved_by="DS. Nguyễn Văn An",
        source_reference="Quyết định thu hồi số 99/QĐ-ATTP",
    )
    val = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=revoked_claim,
        product_sku="DION-D3-1000",
        as_of_date="2026-10-16",
    )
    assert val.eligible is False
    assert ValidationCode.CLAIM_REVOKED in val.reasons


# ------------------------------------------------------------------------------
# Test 12: Claim chưa được duyệt (DRAFT / PENDING / REJECTED) bị loại
# ------------------------------------------------------------------------------
def test_12_unapproved_claim_excluded():
    draft_claim = ClaimRecord(
        claim_id="CLM-DRAFT-01",
        product_sku="DION-D3-1000",
        claim_text="Bản nháp đề xuất chưa duyệt.",
        status=ClaimStatus.DRAFT,
        zone=KnowledgeZone.COMMERCIAL_APPROVED,
        effective_until="2028-12-31",
        approved_by="Chưa có",
        source_reference="Đề cương thử nghiệm",
    )
    val = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=draft_claim,
        product_sku="DION-D3-1000",
        as_of_date="2026-10-16",
    )
    assert val.eligible is False
    assert ValidationCode.CLAIM_NOT_APPROVED in val.reasons


# ------------------------------------------------------------------------------
# Test 13: Claim có ngày sai định dạng bị phát hiện
# ------------------------------------------------------------------------------
def test_13_invalid_date_format():
    invalid_date_claim = ClaimRecord(
        claim_id="CLM-INVALID-DATE",
        product_sku="DION-D3-1000",
        claim_text="Claim có định dạng ngày sai.",
        status=ClaimStatus.APPROVED,
        zone=KnowledgeZone.COMMERCIAL_APPROVED,
        effective_until="31-12-2027",  # Sai format ISO
        approved_by="DS. Nguyễn Văn An",
        source_reference="Hồ sơ công bố số 4521",
    )
    val = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=invalid_date_claim,
        product_sku="DION-D3-1000",
        as_of_date="2026-10-16",
    )
    assert val.eligible is False
    assert ValidationCode.INVALID_DATE in val.reasons


# ------------------------------------------------------------------------------
# Test 14: Claim thiếu nguồn được phát hiện (MISSING_SOURCE)
# ------------------------------------------------------------------------------
def test_14_missing_evidence_source():
    no_source_claim = ClaimRecord(
        claim_id="CLM-NO-SRC",
        product_sku="DION-D3-1000",
        claim_text="Claim không có căn cứ pháp lý hoặc nguồn chứng minh.",
        status=ClaimStatus.APPROVED,
        zone=KnowledgeZone.COMMERCIAL_APPROVED,
        effective_until="2028-12-31",
        approved_by="DS. Nguyễn Văn An",
        source_reference="",
        evidence_source="",
    )
    val = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=no_source_claim,
        product_sku="DION-D3-1000",
        as_of_date="2026-10-16",
    )
    assert val.eligible is False
    assert ValidationCode.MISSING_SOURCE in val.reasons


# ------------------------------------------------------------------------------
# Test 15: Claim thiếu bằng chứng phê duyệt (MISSING_APPROVAL_EVIDENCE)
# ------------------------------------------------------------------------------
def test_15_missing_approval_evidence():
    no_approver_claim = ClaimRecord(
        claim_id="CLM-NO-APPROVER",
        product_sku="DION-D3-1000",
        claim_text="Claim đầy đủ nguồn nhưng chưa ai ký duyệt.",
        status=ClaimStatus.APPROVED,
        zone=KnowledgeZone.COMMERCIAL_APPROVED,
        effective_until="2028-12-31",
        approved_by="",  # Thiếu người duyệt
        source_reference="Hồ sơ công bố số 4521",
    )
    val = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=no_approver_claim,
        product_sku="DION-D3-1000",
        as_of_date="2026-10-16",
    )
    # Vẫn tính là không eligible hoàn toàn hoặc cần review
    assert val.review_required is True
    assert ValidationCode.MISSING_APPROVAL_EVIDENCE in val.reasons


# ------------------------------------------------------------------------------
# Test 16: Claim tham chiếu SKU không khớp (SKU_MISMATCH)
# ------------------------------------------------------------------------------
def test_16_sku_mismatch():
    d3_claim = ClaimRecord(
        claim_id="CLM-D3-01",
        product_sku="DION-D3-1000",
        claim_text="Hỗ trợ tăng cường hấp thu canxi.",
        status=ClaimStatus.APPROVED,
        zone=KnowledgeZone.COMMERCIAL_APPROVED,
        effective_until="2027-12-31",
        approved_by="DS. Nguyễn Văn An",
        source_reference="Hồ sơ số 4521",
    )
    # Thẩm định với SKU khác
    val = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=d3_claim,
        product_sku="DION-CAL-MOM",
        as_of_date="2026-10-16",
    )
    assert val.eligible is False
    assert ValidationCode.SKU_MISMATCH in val.reasons


# ------------------------------------------------------------------------------
# Test 17: Claim ID trùng được phát hiện
# ------------------------------------------------------------------------------
def test_17_detect_duplicate_claim_id(tmp_path):
    dup_claim_data = {
        "products": [
            {
                "sku": "SKU-01",
                "name": "Sản phẩm 1",
                "claims": [
                    {"claim_id": "CLM-DUP", "claim_text": "Tác dụng 1", "evidence_source": "Nguồn 1"},
                    {"claim_id": "CLM-DUP", "claim_text": "Tác dụng 2", "evidence_source": "Nguồn 2"},
                ],
            }
        ]
    }
    file_path = tmp_path / "dup_claim.json"
    file_path.write_text(json.dumps(dup_claim_data), encoding="utf-8")

    summary = validate_product_knowledge_file(file_path)
    assert summary.errors_count > 0
    codes = [item.code for item in summary.items]
    assert "DUPLICATE_CLAIM_ID" in codes


# ------------------------------------------------------------------------------
# Test 18: Trường dữ liệu không có thì không bị AI tự sinh
# ------------------------------------------------------------------------------
def test_18_no_hallucinated_fields():
    repo = get_knowledge_repository()
    claim = repo.get_claim_by_id("CLM-D3-01")
    assert claim is not None
    # Trong JSON mẫu không có effective_from -> phải là None, không tự chế
    assert claim.effective_from is None
    # Trong JSON mẫu không có source_document_id riêng -> phải là None
    assert claim.source_document_id is None


# ------------------------------------------------------------------------------
# Test 19: get_active_claims() trong claims_hub.py vẫn tương thích 100%
# ------------------------------------------------------------------------------
def test_19_claims_hub_backwards_compatibility():
    active = get_active_claims("DION-D3-1000", zone="COMMERCIAL_APPROVED")
    assert len(active) == 2
    c_ids = [c["claim_id"] for c in active]
    assert "CLM-D3-01" in c_ids
    assert "CLM-D3-02" in c_ids
    assert "CLM-D3-03" not in c_ids
    assert "CLM-D3-04" not in c_ids

    summary = get_claims_summary("DION-D3-1000")
    assert summary["total_claims"] == 4
    assert summary["active_commercial"] == 2
    assert summary["expired"] == 1
    assert summary["internal"] == 1


# ------------------------------------------------------------------------------
# Test 20: Hỗ trợ inject as_of_date cho kiểm thử tất định
# ------------------------------------------------------------------------------
def test_20_deterministic_as_of_date():
    repo = get_knowledge_repository()
    # Vào năm 2024, CLM-D3-03 (hết hạn 2025-12-31) vẫn còn hiệu lực
    # Nhưng status="EXPIRED" trong JSON -> vẫn bị loại do ClaimStatus != APPROVED
    val_2024 = ClaimEligibilityValidator.validate_claim_eligibility(
        claim=repo.get_claim_by_id("CLM-D3-03"),
        product_sku="DION-D3-1000",
        as_of_date="2024-01-01",
    )
    # Bị loại vì status='EXPIRED', nhưng lý do không phải là CLAIM_EXPIRED theo ngày
    assert val_2024.eligible is False
    assert ValidationCode.CLAIM_EXPIRED in val_2024.reasons

    # Vào năm 2029, tất cả các Claim D3 hiện tại đều đã hết hạn
    eligible_2029 = repo.get_eligible_commercial_claims("DION-D3-1000", as_of_date="2029-01-01")
    assert len(eligible_2029) == 0


# ------------------------------------------------------------------------------
# Test 21: Endpoint cũ /api/copilot/ask và mới /api/copilot/chat vẫn nguyên vẹn
# ------------------------------------------------------------------------------
def test_21_endpoints_regression():
    # Endpoint cũ
    res_ask = client.post("/api/copilot/ask", json={"query": "Vitamin D3 có tác dụng gì?", "sku": "DION-D3-1000"})
    assert res_ask.status_code == 200
    assert "content" in res_ask.json()

    # Endpoint mới bị khóa mặc định
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "false"}):
        res_chat = client.post("/api/copilot/chat", json={"message": "Xin chào"})
        assert res_chat.status_code == 403
