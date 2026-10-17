"""
DION Healthcare AI — Product Knowledge & Claims Data Validation Script (Bước 02A)
Kiểm tra cấu trúc và chất lượng dữ liệu trong `data/products_claims.json`.
Phân loại rõ ràng: ERROR, WARNING, INFO.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules.knowledge.schemas import (
    ValidationSeverity,
    DataValidationItem,
    DataValidationSummary,
    KnowledgeZone,
    ClaimStatus,
)
from modules.knowledge.validator import ClaimEligibilityValidator


def validate_product_knowledge_file(file_path: Path) -> DataValidationSummary:
    summary = DataValidationSummary()

    if not file_path.exists():
        summary.errors_count += 1
        summary.items.append(
            DataValidationItem(
                severity=ValidationSeverity.ERROR,
                code="FILE_NOT_FOUND",
                message=f"Không tìm thấy file dữ liệu tại: {file_path}",
                entity_type="DATASET",
            )
        )
        return summary

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        summary.errors_count += 1
        summary.items.append(
            DataValidationItem(
                severity=ValidationSeverity.ERROR,
                code="INVALID_JSON",
                message=f"Lỗi phân tích cú pháp JSON: {str(e)}",
                entity_type="DATASET",
            )
        )
        return summary

    if not isinstance(data, dict) or "products" not in data or not isinstance(data["products"], list):
        summary.errors_count += 1
        summary.items.append(
            DataValidationItem(
                severity=ValidationSeverity.ERROR,
                code="INVALID_SCHEMA",
                message="File JSON thiếu key cấp cao 'products' dạng danh sách.",
                entity_type="DATASET",
            )
        )
        return summary

    products_list = data["products"]
    summary.total_products = len(products_list)

    known_skus = set()
    known_claim_ids = set()
    today_date = datetime.now().date()

    for p_idx, prod in enumerate(products_list):
        if not isinstance(prod, dict):
            summary.errors_count += 1
            summary.items.append(
                DataValidationItem(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_PRODUCT_ITEM",
                    message=f"Phần tử thứ {p_idx} trong 'products' không phải là object.",
                    entity_type="PRODUCT",
                )
            )
            continue

        sku = str(prod.get("sku", "")).strip()
        name = str(prod.get("name", "")).strip()

        # 1. Kiểm tra SKU rỗng hoặc trùng
        if not sku:
            summary.errors_count += 1
            summary.items.append(
                DataValidationItem(
                    severity=ValidationSeverity.ERROR,
                    code="EMPTY_SKU",
                    message=f"Sản phẩm tại vị trí {p_idx} ('{name}') bị thiếu trường SKU.",
                    entity_type="PRODUCT",
                    field_name="sku",
                )
            )
        elif sku in known_skus:
            summary.errors_count += 1
            summary.items.append(
                DataValidationItem(
                    severity=ValidationSeverity.ERROR,
                    code="DUPLICATE_SKU",
                    message=f"Phát hiện SKU bị trùng lặp trong dữ liệu: '{sku}'.",
                    entity_type="PRODUCT",
                    entity_id=sku,
                    field_name="sku",
                )
            )
        else:
            known_skus.add(sku)

        # 2. Kiểm tra tên sản phẩm
        if not name:
            summary.warnings_count += 1
            summary.items.append(
                DataValidationItem(
                    severity=ValidationSeverity.WARNING,
                    code="EMPTY_PRODUCT_NAME",
                    message=f"Sản phẩm SKU '{sku}' thiếu tên thương mại.",
                    entity_type="PRODUCT",
                    entity_id=sku,
                    field_name="name",
                )
            )

        # 3. Kiểm tra disclaimer bắt buộc
        if not prod.get("mandatory_disclaimer"):
            summary.warnings_count += 1
            summary.items.append(
                DataValidationItem(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_DISCLAIMER",
                    message=f"Sản phẩm SKU '{sku}' thiếu 'mandatory_disclaimer' theo Nghị định 342.",
                    entity_type="PRODUCT",
                    entity_id=sku,
                    field_name="mandatory_disclaimer",
                )
            )

        # 4. Kiểm tra danh sách claims của sản phẩm
        claims = prod.get("claims", [])
        if not isinstance(claims, list):
            summary.errors_count += 1
            summary.items.append(
                DataValidationItem(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_CLAIMS_FORMAT",
                    message=f"Trường 'claims' của SKU '{sku}' không phải là danh sách.",
                    entity_type="PRODUCT",
                    entity_id=sku,
                )
            )
            continue

        for c_idx, c in enumerate(claims):
            summary.total_claims += 1
            if not isinstance(c, dict):
                summary.errors_count += 1
                summary.items.append(
                    DataValidationItem(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_CLAIM_ITEM",
                        message=f"Claim thứ {c_idx} của SKU '{sku}' không phải là object.",
                        entity_type="CLAIM",
                    )
                )
                continue

            claim_id = str(c.get("claim_id", "")).strip()
            claim_text = str(c.get("claim_text", "")).strip()

            # 4.1. Claim ID rỗng hoặc trùng
            if not claim_id:
                summary.errors_count += 1
                summary.items.append(
                    DataValidationItem(
                        severity=ValidationSeverity.ERROR,
                        code="EMPTY_CLAIM_ID",
                        message=f"Claim thứ {c_idx} của SKU '{sku}' bị thiếu 'claim_id'.",
                        entity_type="CLAIM",
                        entity_id=f"{sku}_idx_{c_idx}",
                    )
                )
            elif claim_id in known_claim_ids:
                summary.errors_count += 1
                summary.items.append(
                    DataValidationItem(
                        severity=ValidationSeverity.ERROR,
                        code="DUPLICATE_CLAIM_ID",
                        message=f"Phát hiện mã Claim ID bị trùng lặp trong dataset: '{claim_id}'.",
                        entity_type="CLAIM",
                        entity_id=claim_id,
                    )
                )
            else:
                known_claim_ids.add(claim_id)

            # 4.2. Claim text rỗng
            if not claim_text:
                summary.errors_count += 1
                summary.items.append(
                    DataValidationItem(
                        severity=ValidationSeverity.ERROR,
                        code="EMPTY_CLAIM_TEXT",
                        message=f"Claim '{claim_id}' của SKU '{sku}' có nội dung phát biểu rỗng.",
                        entity_type="CLAIM",
                        entity_id=claim_id,
                    )
                )

            # 4.3. Kiểm tra ngày hết hạn và định dạng
            eff_until = c.get("effective_until")
            is_expired = False
            if eff_until:
                parsed_until = ClaimEligibilityValidator.parse_date(eff_until)
                if parsed_until is None:
                    summary.errors_count += 1
                    summary.items.append(
                        DataValidationItem(
                            severity=ValidationSeverity.ERROR,
                            code="INVALID_DATE_FORMAT",
                            message=f"Claim '{claim_id}' có 'effective_until' sai định dạng ISO YYYY-MM-DD: '{eff_until}'.",
                            entity_type="CLAIM",
                            entity_id=claim_id,
                            field_name="effective_until",
                        )
                    )
                elif parsed_until < today_date:
                    is_expired = True
                    summary.expired_claims += 1

            # 4.4. Kiểm tra ngày bắt đầu hiệu lực
            eff_from = c.get("effective_from")
            if not eff_from:
                summary.missing_fields_claims += 1
                summary.warnings_count += 1
                summary.items.append(
                    DataValidationItem(
                        severity=ValidationSeverity.WARNING,
                        code="MISSING_EFFECTIVE_FROM",
                        message=f"Claim '{claim_id}' chưa có trường 'effective_from' (ngày bắt đầu hiệu lực).",
                        entity_type="CLAIM",
                        entity_id=claim_id,
                        field_name="effective_from",
                    )
                )
            else:
                parsed_from = ClaimEligibilityValidator.parse_date(eff_from)
                if parsed_from is None:
                    summary.errors_count += 1
                    summary.items.append(
                        DataValidationItem(
                            severity=ValidationSeverity.ERROR,
                            code="INVALID_DATE_FORMAT",
                            message=f"Claim '{claim_id}' có 'effective_from' sai định dạng: '{eff_from}'.",
                            entity_type="CLAIM",
                            entity_id=claim_id,
                            field_name="effective_from",
                        )
                    )

            # 4.5. Kiểm tra vùng tri thức (zone)
            zone = c.get("zone", "")
            if zone in ("INTERNAL_EXPERT", "INTERNAL_MEDICAL"):
                summary.internal_claims += 1
            elif zone != "COMMERCIAL_APPROVED":
                summary.warnings_count += 1
                summary.items.append(
                    DataValidationItem(
                        severity=ValidationSeverity.WARNING,
                        code="NON_STANDARD_ZONE",
                        message=f"Claim '{claim_id}' có vùng tri thức bất thường/chưa chuẩn: '{zone}'.",
                        entity_type="CLAIM",
                        entity_id=claim_id,
                        field_name="zone",
                    )
                )

            # 4.6. Kiểm tra nguồn tài liệu chứng minh
            evidence = c.get("evidence_source") or c.get("source_reference")
            if not evidence or not str(evidence).strip():
                summary.errors_count += 1
                summary.items.append(
                    DataValidationItem(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_EVIDENCE_SOURCE",
                        message=f"Claim '{claim_id}' thiếu tài liệu / nguồn chứng minh ('evidence_source').",
                        entity_type="CLAIM",
                        entity_id=claim_id,
                        field_name="evidence_source",
                    )
                )

            # 4.7. Thẩm định điều kiện thương mại kỹ thuật
            val_result = ClaimEligibilityValidator.validate_claim_eligibility(
                claim=c,
                product_sku=sku,
                usage_context="COMMERCIAL_ADVICE",
                as_of_date=today_date,
            )
            if val_result.eligible:
                summary.eligible_claims += 1

    return summary


def run_validation_cli():
    print("=" * 75)
    print("   DION HEALTHCARE AI — BÁO CÁO KIỂM TRA CHẤT LƯỢNG PRODUCT & CLAIMS")
    print("=" * 75)

    data_file = ROOT_DIR / "data" / "products_claims.json"
    print(f"[*] Đường dẫn file: {data_file}")

    summary = validate_product_knowledge_file(data_file)

    print(f"\n[*] THỐNG KÊ DỮ LIỆU:")
    print(f"    - Tổng số sản phẩm (SKU):             {summary.total_products}")
    print(f"    - Tổng số Claims:                     {summary.total_claims}")
    print(f"    - Số Claims đủ điều kiện thương mại:  {summary.eligible_claims}")
    print(f"    - Số Claims đã hết hạn hiệu lực:      {summary.expired_claims}")
    print(f"    - Số Claims thuộc vùng nội bộ:        {summary.internal_claims}")
    print(f"    - Số Claims thiếu trường thông tin:   {summary.missing_fields_claims}")

    print(f"\n[*] KẾT QUẢ ĐỐI SOÁT CHẤT LƯỢNG:")
    print(f"    - ERROR   (Lỗi nghiêm trọng): {summary.errors_count}")
    print(f"    - WARNING (Cảnh báo nghiệp vụ): {summary.warnings_count}")

    if summary.items:
        print("\n" + "-" * 75)
        print("CHI TIẾT DANH SÁCH VẤN ĐỀ PHÁT HIỆN:")
        print("-" * 75)
        for item in summary.items:
            prefix = "[ERROR]  " if item.severity == ValidationSeverity.ERROR else "[WARNING]"
            entity = f"[{item.entity_type} {item.entity_id or ''}]".ljust(25)
            print(f"{prefix} {entity} ({item.code}): {item.message}")

    print("=" * 75)
    if summary.errors_count == 0:
        print("[SUCCESS] Dữ liệu không có lỗi nghiêm trọng. An toàn cho Knowledge Hub.")
        sys.exit(0)
    else:
        print(f"[FAIL] Phát hiện {summary.errors_count} lỗi nghiêm trọng cần khắc phục trước khi dùng.")
        sys.exit(1)


if __name__ == "__main__":
    run_validation_cli()
