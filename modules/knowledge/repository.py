"""
DION Healthcare AI — Knowledge Repository (Bước 02A)
Cung cấp kiến trúc trừu tượng (BaseKnowledgeRepository) và triển khai JSON (JSONKnowledgeRepository).
Sẵn sàng mở rộng sang PostgreSQL / Database sau này mà không phải viết lại Chatbot.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import date
from typing import List, Optional, Dict, Any, Union

from modules.knowledge.schemas import (
    ProductRecord,
    ClaimRecord,
    KnowledgeZone,
    ClaimStatus,
)
from modules.knowledge.validator import ClaimEligibilityValidator

DEFAULT_JSON_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "products_claims.json"


class BaseKnowledgeRepository(ABC):
    """Interface cơ sở cho kho lưu trữ tri thức sản phẩm và Claims."""

    @abstractmethod
    def list_products(self) -> List[ProductRecord]:
        """Lấy danh sách tất cả sản phẩm."""
        pass

    @abstractmethod
    def get_product_by_sku(self, sku: str) -> Optional[ProductRecord]:
        """Tìm sản phẩm theo SKU chính xác."""
        pass

    @abstractmethod
    def get_claims_by_product(self, sku: str) -> List[ClaimRecord]:
        """Lấy toàn bộ Claims thuộc về một SKU (bao gồm cả nội bộ và hết hạn)."""
        pass

    @abstractmethod
    def get_claim_by_id(self, claim_id: str) -> Optional[ClaimRecord]:
        """Tìm Claim theo mã claim_id."""
        pass

    @abstractmethod
    def get_eligible_commercial_claims(
        self, sku: str, as_of_date: Optional[Union[date, str]] = None
    ) -> List[ClaimRecord]:
        """
        Lấy danh sách Claims thương mại ĐỦ ĐIỀU KIỆN (Approved, Commercial Zone, còn hạn)
        cho một SKU. Tuyệt đối không fallback sang sản phẩm khác.
        """
        pass

    @abstractmethod
    def get_all_claims(self) -> List[ClaimRecord]:
        """Lấy toàn bộ Claims trong hệ thống."""
        pass


class JSONKnowledgeRepository(BaseKnowledgeRepository):
    """
    Triển khai đọc dữ liệu từ file JSON cục bộ (`data/products_claims.json`).
    Tự động chuẩn hóa dữ liệu sang ProductRecord và ClaimRecord.
    """

    def __init__(self, file_path: Optional[Union[Path, str]] = None):
        self.file_path = Path(file_path) if file_path else DEFAULT_JSON_PATH
        self._products: Dict[str, ProductRecord] = {}
        self._claims_by_product: Dict[str, List[ClaimRecord]] = {}
        self._claims_by_id: Dict[str, ClaimRecord] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Đọc và nạp dữ liệu từ file JSON vào bộ nhớ đệm."""
        self._products.clear()
        self._claims_by_product.clear()
        self._claims_by_id.clear()

        if not self.file_path.exists():
            return

        with open(self.file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        raw_products = raw_data.get("products", [])
        for p in raw_products:
            sku = str(p.get("sku", "")).strip()
            if not sku:
                continue

            # Xây dựng ProductRecord
            product = ProductRecord(
                sku=sku,
                name=p.get("name", sku),
                category=p.get("category"),
                regulatory_class=p.get("regulatory_class"),
                description=p.get("description"),
                target_users=p.get("target_users", []),
                mandatory_disclaimer=p.get("mandatory_disclaimer"),
                market=p.get("market", "VN"),
                registration_number=p.get("registration_number"),
                ad_permit_number=p.get("ad_permit_number"),
                active_ingredients=p.get("active_ingredients", []),
                contraindications=p.get("contraindications"),
                clinical_evidence=p.get("clinical_evidence", []),
            )
            # Lưu ý: nếu SKU trùng thì ghi nhận (sẽ được kiểm tra trong DataValidation)
            self._products[sku] = product
            self._claims_by_product[sku] = []

            # Xây dựng ClaimRecord cho từng claim của sản phẩm này
            for c in p.get("claims", []):
                claim_id = str(c.get("claim_id", "")).strip()
                if not claim_id:
                    continue

                raw_zone = str(c.get("zone", "COMMERCIAL_APPROVED")).strip()
                # Ánh xạ zone an toàn
                if raw_zone == "COMMERCIAL_APPROVED":
                    zone = KnowledgeZone.COMMERCIAL_APPROVED
                elif raw_zone in ("INTERNAL_MEDICAL", "INTERNAL_EXPERT"):
                    zone = KnowledgeZone.INTERNAL_EXPERT
                elif raw_zone == "RESEARCH":
                    zone = KnowledgeZone.RESEARCH
                elif raw_zone == "EXPIRED":
                    zone = KnowledgeZone.EXPIRED
                else:
                    zone = KnowledgeZone.UNKNOWN

                raw_status = str(c.get("status", "APPROVED")).strip()
                if raw_status == "APPROVED":
                    status = ClaimStatus.APPROVED
                elif raw_status == "EXPIRED":
                    status = ClaimStatus.EXPIRED
                elif raw_status == "REVOKED":
                    status = ClaimStatus.REVOKED
                else:
                    status = ClaimStatus.APPROVED

                claim_record = ClaimRecord(
                    claim_id=claim_id,
                    product_sku=sku,
                    claim_text=c.get("claim_text", ""),
                    zone=zone,
                    status=status,
                    effective_from=c.get("effective_from"),
                    effective_until=c.get("effective_until"),
                    source_document_id=c.get("source_document_id"),
                    source_reference=c.get("evidence_source") or c.get("source_reference"),
                    evidence_source=c.get("evidence_source"),
                    approved_by=c.get("approved_by"),
                    usage_scope=c.get("usage_scope", "COMMERCIAL_ALL"),
                    market=c.get("market", "VN"),
                    required_disclaimer=c.get("required_disclaimer") or p.get("mandatory_disclaimer"),
                    prohibited_expressions=c.get("prohibited_expressions", []),
                    evidence_status=c.get("evidence_status", "VERIFIED"),
                    original_evidence_source=c.get("original_evidence_source"),
                    unverified_citations=c.get("unverified_citations", []),
                )

                self._claims_by_product[sku].append(claim_record)
                self._claims_by_id[claim_id] = claim_record

    def reload(self) -> None:
        """Tải lại dữ liệu từ đĩa."""
        self._load_data()

    def list_products(self) -> List[ProductRecord]:
        return list(self._products.values())

    def get_product_by_sku(self, sku: str) -> Optional[ProductRecord]:
        clean_sku = sku.strip()
        return self._products.get(clean_sku)

    def get_claims_by_product(self, sku: str) -> List[ClaimRecord]:
        clean_sku = sku.strip()
        return self._claims_by_product.get(clean_sku, [])

    def get_claim_by_id(self, claim_id: str) -> Optional[ClaimRecord]:
        clean_id = claim_id.strip()
        return self._claims_by_id.get(clean_id)

    def get_eligible_commercial_claims(
        self, sku: str, as_of_date: Optional[Union[date, str]] = None
    ) -> List[ClaimRecord]:
        clean_sku = sku.strip()
        claims = self.get_claims_by_product(clean_sku)
        if not claims:
            return []

        eligible_list: List[ClaimRecord] = []
        for claim in claims:
            res = ClaimEligibilityValidator.validate_claim_eligibility(
                claim=claim,
                product_sku=clean_sku,
                usage_context="COMMERCIAL_ADVICE",
                as_of_date=as_of_date,
            )
            if res.eligible:
                eligible_list.append(claim)

        return eligible_list

    def get_all_claims(self) -> List[ClaimRecord]:
        return list(self._claims_by_id.values())


# Singleton instance mặc định
_default_repository: Optional[BaseKnowledgeRepository] = None


def get_knowledge_repository(file_path: Optional[Union[Path, str]] = None) -> BaseKnowledgeRepository:
    """Factory helper cung cấp Knowledge Repository instance."""
    global _default_repository
    if file_path is not None:
        return JSONKnowledgeRepository(file_path=file_path)
    if _default_repository is None:
        _default_repository = JSONKnowledgeRepository()
    return _default_repository
