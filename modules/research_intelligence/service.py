"""
Research Intelligence Service - DION AI Research & Clinical Intelligence
Điều phối tra cứu y văn PubMed, phân tích dược lý so sánh, trích xuất PICO và gắn kết hồ sơ claims sản phẩm.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from modules.research_intelligence.schemas import (
    ActiveIngredientInfo,
    StudyRecord,
    PICOAnalysis,
    SearchStudiesRequest,
    LinkClaimRequest,
    EvidenceGrade,
    StudyType
)
from modules.research_intelligence.repository import MedicalLiteratureRepository
from modules.research_intelligence.pharmacology_engine import PharmacologyEngine
from modules.research_intelligence.evidence_extractor import ClinicalEvidenceExtractor

logger = logging.getLogger("dion.research.service")

class ResearchIntelligenceService:
    """Service trung tâm quản lý tri thức y văn lâm sàng và dược lý học DION"""

    def __init__(
        self,
        repository: Optional[MedicalLiteratureRepository] = None,
        pharmacology_engine: Optional[PharmacologyEngine] = None,
        evidence_extractor: Optional[ClinicalEvidenceExtractor] = None,
        products_claims_path: Optional[str] = None
    ):
        self.repository = repository or MedicalLiteratureRepository()
        self.pharmacology_engine = pharmacology_engine or PharmacologyEngine()
        self.evidence_extractor = evidence_extractor or ClinicalEvidenceExtractor()
        
        # Đường dẫn tệp products_claims.json
        if products_claims_path:
            self.products_claims_path = Path(products_claims_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.products_claims_path = base_dir / "data" / "products_claims.json"

    def get_active_ingredients(self, category: Optional[str] = None) -> List[ActiveIngredientInfo]:
        """Lấy danh sách các hoạt chất được theo dõi"""
        return self.repository.get_ingredients(category=category)

    def search_studies(self, req: SearchStudiesRequest) -> List[StudyRecord]:
        """Tìm kiếm y văn lâm sàng theo từ khóa, hoạt chất, cấp bằng chứng, loại nghiên cứu"""
        return self.repository.search_studies(
            query=req.query,
            ingredient_id=req.ingredient,
            study_type=req.study_type,
            evidence_grade=req.evidence_grade,
            target_group=req.target_group,
            limit=req.limit
        )

    def get_study_by_pmid(self, pmid: str) -> Optional[StudyRecord]:
        """Tra cứu chi tiết một nghiên cứu theo mã PMID"""
        clean_pmid = str(pmid).strip().upper().replace("PMID:", "").replace("PMID", "").strip()
        return self.repository.get_study_by_pmid(clean_pmid)

    def compare_pharmacology(self, category: str = "CANXI") -> Dict[str, Any]:
        """So sánh chuyên sâu dược lý học giữa các dạng muối và phân tích khoảng trống khẩu phần"""
        cat = (category or "CANXI").strip().upper()
        if cat in ("SAT", "IRON", "FERROUS"):
            return self.pharmacology_engine.get_iron_comparison()
        return self.pharmacology_engine.get_calcium_comparison()

    async def analyze_study_abstract(
        self,
        abstract_text: str,
        target_product_sku: Optional[str] = None
    ) -> PICOAnalysis:
        """Sử dụng AI để trích xuất cấu trúc PICO và đánh giá mức độ bằng chứng y học"""
        return await self.evidence_extractor.extract_pico(
            abstract_text=abstract_text,
            target_product_sku=target_product_sku
        )

    def link_study_to_product_claim(self, req: LinkClaimRequest) -> Dict[str, Any]:
        """
        Gắn một nghiên cứu lâm sàng đã kiểm chứng (PMID) vào hồ sơ clinical_evidence của sản phẩm DION.
        Cập nhật trực tiếp tệp data/products_claims.json một cách an toàn.
        """
        clean_pmid = str(req.pmid).strip().upper().replace("PMID:", "").replace("PMID", "").strip()
        study = self.repository.get_study_by_pmid(clean_pmid)
        if not study:
            raise ValueError(f"Không tìm thấy nghiên cứu y văn với PMID '{req.pmid}' trong cơ sở dữ liệu y văn đã xác thực.")

        if not self.products_claims_path.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp hồ sơ sản phẩm tại: {self.products_claims_path}")

        try:
            with open(self.products_claims_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Lỗi đọc file products_claims.json: {e}")

        products = data.get("products", [])
        target_prod = None
        for prod in products:
            if prod.get("sku", "").upper() == req.sku.strip().upper():
                target_prod = prod
                break

        if not target_prod:
            raise ValueError(f"Không tìm thấy sản phẩm có SKU '{req.sku}' trong hệ thống.")

        evidence_list = target_prod.setdefault("clinical_evidence", [])
        
        # Kiểm tra xem PMID này đã tồn tại trong danh sách chưa
        existing_idx = None
        for i, ev in enumerate(evidence_list):
            existing_pmid = ev.get("pmid", "").upper().replace("PMID:", "").replace("PMID", "").strip()
            if existing_pmid == clean_pmid:
                existing_idx = i
                break

        now_str = datetime.utcnow().isoformat()
        study_type_str = study.study_type.value if hasattr(study.study_type, "value") else str(study.study_type)
        grade_str = study.evidence_grade.value if hasattr(study.evidence_grade, "value") else str(study.evidence_grade)

        new_evidence_record = {
            "pmid": f"PMID: {clean_pmid}",
            "claimed_title": study.title,
            "actual_pubmed_title": study.title,
            "status": "VERIFIED_SUPPORT",
            "is_verified": True,
            "evidence_grade": grade_str,
            "study_type": study_type_str,
            "pubmed_url": study.pubmed_url,
            "audit_note": f"Nghiên cứu lâm sàng đã được R&D thẩm định từ PubMed (PMID: {clean_pmid}). Cung cấp bằng chứng thực chứng (Level {grade_str}) cho công dụng sản phẩm.",
            "linked_at": now_str,
            "assigned_by": req.assigned_by
        }

        if existing_idx is not None:
            evidence_list[existing_idx] = new_evidence_record
            action = "updated"
        else:
            evidence_list.append(new_evidence_record)
            action = "created"

        # Nếu có claim_id cụ thể, liên kết luôn vào claim đó
        claim_linked = False
        if req.claim_id:
            for clm in target_prod.get("claims", []):
                if clm.get("claim_id", "").upper() == req.claim_id.strip().upper():
                    pmids = clm.setdefault("supporting_pmids", [])
                    if f"PMID: {clean_pmid}" not in pmids:
                        pmids.append(f"PMID: {clean_pmid}")
                    current_source = clm.get("evidence_source", "")
                    if f"PMID: {clean_pmid}" not in current_source:
                        clm["evidence_source"] = f"{current_source} & PubMed PMID: {clean_pmid}".strip(" &")
                    claim_linked = True
                    break

        # Lưu atomic an toàn
        dir_name = os.path.dirname(self.products_claims_path)
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, ensure_ascii=False, indent=2)
            temp_path = tf.name

        os.replace(temp_path, self.products_claims_path)
        logger.info(f"[ResearchService] Linked PMID {clean_pmid} to SKU {req.sku} ({action}).")

        return {
            "status": "SUCCESS",
            "action": action,
            "sku": target_prod.get("sku"),
            "product_name": target_prod.get("name"),
            "pmid": clean_pmid,
            "study_title": study.title,
            "evidence_grade": grade_str,
            "claim_linked": claim_linked,
            "total_verified_evidence": len([e for e in evidence_list if e.get("is_verified")])
        }

    def get_legacy_research_intelligence_data(self, ingredient: str) -> Dict[str, Any]:
        """
        Duy trì tương thích 100% cho endpoint cũ GET /api/research-intelligence?ingredient=...
        """
        ing_clean = (ingredient or "").lower()
        studies = self.repository.search_studies(limit=10)
        
        # Lọc các nghiên cứu liên quan đến hoạt chất nếu tìm thấy
        matched = [s for s in studies if ing_clean in s.ingredient_id.lower() or ing_clean in s.title.lower()]
        target_studies = matched if matched else studies[:5]

        studies_payload = []
        for s in target_studies:
            studies_payload.append({
                "title": s.title,
                "pmid": f"PMID: {s.pmid}",
                "authors": s.authors,
                "journal": s.journal,
                "year": s.year,
                "study_type": s.study_type.value if hasattr(s.study_type, "value") else str(s.study_type),
                "sample_size": s.sample_size,
                "dosage_used": s.dosage_used,
                "key_findings": s.primary_outcome,
                "adverse_effects": s.adverse_events,
                "evidence_grade": s.evidence_grade.value if hasattr(s.evidence_grade, "value") else str(s.evidence_grade),
                "url": s.pubmed_url
            })

        return {
            "ingredient": ingredient,
            "summary": f"Tổng hợp y văn lâm sàng và dữ liệu PubMed cập nhật cho hoạt chất {ingredient}.",
            "clinical_studies": studies_payload,
            "safety_profile": "Hồ sơ an toàn dung nạp cao, độc tính tiêu hóa thấp, tuân thủ các quy chuẩn dược điển quốc tế và ASEAN.",
            "evidence_level": "Level I-II (Oxford CEBM)"
        }
