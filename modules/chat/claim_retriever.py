"""
DION Healthcare AI — Intelligent Claim Retrieval & Relevance Ranking Module
Truy xuất Claims theo đánh giá mức độ liên quan ngữ nghĩa (Semantic & Concept Matching),
tuân thủ tuyệt đối ClaimEligibilityValidator, loại trừ claims hết hạn/nội bộ và chặn so khớp nông cạn.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Set

from modules.knowledge.repository import BaseKnowledgeRepository
from modules.knowledge.schemas import ClaimRecord, KnowledgeZone, ClaimStatus
from modules.knowledge.validator import ClaimEligibilityValidator


# Danh sách từ dừng (Stop words) và từ ngữ thông thường trong câu hỏi
STOP_WORDS: Set[str] = {
    "có", "không", "cho", "của", "và", "các", "những", "được", "này",
    "sản", "phẩm", "thuốc", "uống", "dùng", "gì", "thế", "nào", "làm", "sao",
    "bao", "nhiêu", "hỏi", "với", "trong", "khi", "là", "bị", "hay", "hoặc",
    "tôi", "mình", "bạn", "khách", "hàng", "ạ", "dạ", "ơi", "giúp", "em",
    "tốt", "cần", "nên", "phải", "nữa", "rất", "quá", "lắm", "đến", "ở",
    "đối", "về", "như", "theo", "đã", "đang", "sẽ", "nhất", "cũng", "thì",
    "tác", "dụng", "công", "dụng", "hiệu", "quả", "chức", "năng", "nội", "dung",
    "thông", "tin", "cho", "biết", "xin", "tư", "vấn", "hỗ", "trợ", "xem"
}


# ==============================================================================
# HỆ THỐNG MAPPING KHÁI NIỆM Y DƯỢC & TỪ ĐỒNG NGHĨA (DOMAIN CONCEPTS)
# ==============================================================================

CLAIM_CONCEPT_PROFILES: Dict[str, Dict[str, Any]] = {
    "CLM-D3-01": {
        "sku": "DION-D3-1000",
        "primary_concept": "CALCIUM_PHOSPHORUS_ABSORPTION",
        "concept_keywords": [
            "hấp thu canxi", "hấp thụ canxi", "hấp thu photpho", "hấp thụ photpho",
            "hấp thu", "hấp thụ", "ruột non", "canxi máu", "photpho", "ngấm canxi",
            "chuyển hóa canxi", "nồng độ canxi", "duy trì canxi"
        ],
        "weight": 3.0,
    },
    "CLM-D3-02": {
        "sku": "DION-D3-1000",
        "primary_concept": "BONE_TEETH_SKELETON",
        "concept_keywords": [
            "xương răng", "chắc khỏe", "hệ xương", "phát triển xương",
            "răng chắc khỏe", "xương chắc khỏe", "loãng xương", "ngừa loãng xương",
            "phòng loãng xương", "chiều cao", "phát triển chiều cao", "mật độ xương",
            "còi xương", "xương khớp", "chắc răng", "răng", "xương"
        ],
        "weight": 3.0,
    },
    "CLM-CAL-01": {
        "sku": "DION-CAL-MOM",
        "primary_concept": "BIO_CALCIUM_ALGAE_K2",
        "concept_keywords": [
            "tảo biển đỏ", "tảo đỏ", "lithothamnion", "k2", "mk7", "mk-7",
            "vitamin k2", "canxi sinh học", "canxi hữu cơ", "nguồn gốc canxi",
            "canxi tự nhiên", "tối ưu vào xương", "dẫn canxi vào xương", "hấp thu vào xương"
        ],
        "weight": 3.0,
    },
    "CLM-CAL-02": {
        "sku": "DION-CAL-MOM",
        "primary_concept": "MATERNAL_DEFICIT_CRAMPS",
        "concept_keywords": [
            "chuột rút", "vọp bẻ", "đau lưng", "thiếu hụt canxi", "thiếu canxi",
            "co cơ", "co rút", "tê chân", "mỏi lưng", "bị chuột rút", "hay bị chuột rút",
            "vọp bẻ ban đêm", "bổ sung canxi cho mẹ"
        ],
        "weight": 3.0,
    },
    "CLM-CAL-03": {
        "sku": "DION-CAL-MOM",
        "primary_concept": "CALCIUM_MAGNESIUM_TEETH",
        "concept_keywords": [
            "magie", "khoáng chất vi lượng", "biển sâu", "xương răng thai nhi",
            "trẻ nhỏ", "răng vững chắc"
        ],
        "weight": 2.5,
    },
    "CLM-FE-01": {
        "sku": "DION-FE-FOLIC",
        "primary_concept": "HEMATOPOIESIS_BLOOD_CREATION",
        "concept_keywords": [
            "tạo máu", "thiếu máu", "bổ máu", "hồng cầu", "tạo hồng cầu",
            "acid folic", "folic", "vitamin b9", "b9", "bisglycinate",
            "sắt bisglycinate", "sắt hữu cơ", "sản sinh hồng cầu", "phòng thiếu máu"
        ],
        "weight": 3.0,
    },
    "CLM-FE-02": {
        "sku": "DION-FE-FOLIC",
        "primary_concept": "GASTRIC_DIGESTIVE_TOLERANCE",
        "concept_keywords": [
            "táo bón", "buồn nôn", "nóng trong", "nóng trong người", "êm dịu dạ dày",
            "dịu nhẹ", "cồn cào", "xót ruột", "khó tiêu", "đầy bụng", "không táo bón",
            "bị táo", "uống sắt bị nóng", "xót dạ dày", "đau dạ dày", "êm bụng",
            "dễ tiêu", "dạ dày"
        ],
        "weight": 3.0,
    },
}


@dataclass
class RetrievedClaim:
    """Kết quả truy xuất một Claim kèm điểm số và căn cứ giải thích."""
    claim: ClaimRecord
    score: float
    matched_concepts: List[str]
    relevance_grade: str  # HIGH, MEDIUM, LOW


class ClaimRelevanceRetriever:
    """
    Bộ truy xuất và xếp hạng Claims thông minh theo mức độ liên quan ngữ nghĩa.
    """

    def __init__(self, repository: BaseKnowledgeRepository, min_relevance_threshold: float = 2.0):
        self.repo = repository
        self.min_threshold = min_relevance_threshold

    def _clean_text(self, text: str) -> str:
        """Làm sạch văn bản, chuyển chữ thường và chuẩn hóa khoảng trắng."""
        t = text.lower().strip()
        t = re.sub(r"[\t\r\n\.,\?!;:/\(\)\[\]\{\}\-\_]", " ", t)
        return " ".join(t.split())

    def _extract_content_tokens(self, text: str) -> List[str]:
        """Trích xuất các từ có nghĩa, loại bỏ từ dừng."""
        cleaned = self._clean_text(text)
        return [w for w in cleaned.split() if len(w) >= 2 and w not in STOP_WORDS]

    def score_claim_relevance(
        self,
        query: str,
        claim: ClaimRecord,
    ) -> Tuple[float, List[str]]:
        """
        Tính điểm liên quan của Claim với câu hỏi dựa trên:
        1. Khớp từ khóa khái niệm chuyên môn / từ đồng nghĩa (Concept Keywords)
        2. Khớp cụm từ trong claim_text gốc
        3. Khớp tên sản phẩm
        """
        clean_q = self._clean_text(query)
        q_tokens = set(self._extract_content_tokens(query))
        
        if not q_tokens:
            return 0.0, []

        claim_id = claim.claim_id.strip()
        profile = CLAIM_CONCEPT_PROFILES.get(claim_id, {})
        concept_keywords = profile.get("concept_keywords", [])
        
        score = 0.0
        matched_indicators: List[str] = []

        # 1. Khớp các khái niệm y dược & từ đồng nghĩa (Domain Concepts)
        for kw in concept_keywords:
            clean_kw = self._clean_text(kw)
            # Khớp cụm từ nguyên vẹn
            if " " in clean_kw:
                if clean_kw in clean_q:
                    score += 3.5
                    matched_indicators.append(kw)
            else:
                if re.search(r"\b" + re.escape(clean_kw) + r"\b", clean_q):
                    score += 2.0
                    matched_indicators.append(kw)

        # 2. Khớp trực tiếp văn bản Claim (đã lọc stop words)
        claim_content_tokens = set(self._extract_content_tokens(claim.claim_text))
        direct_matches = q_tokens.intersection(claim_content_tokens)
        
        # Chỉ cộng điểm token trực tiếp nếu không phải các từ chung chung
        GENERIC_MEDICAL_WORDS = {"hỗ", "trợ", "giúp", "tăng", "giảm", "bổ", "sung", "duy", "trì"}
        meaningful_direct = [w for w in direct_matches if w not in GENERIC_MEDICAL_WORDS]
        if meaningful_direct:
            score += len(meaningful_direct) * 1.5
            for w in meaningful_direct:
                if w not in matched_indicators:
                    matched_indicators.append(w)

        # 3. Phạt nếu câu hỏi hỏi chuyên biệt về tính chất khác trong cùng sản phẩm
        # Ví dụ: D3 hỏi về "xương" thì claim về "photpho/ruột non" không được vượt lên
        if claim_id == "CLM-D3-01":
            if any(w in clean_q for w in ["xương", "răng", "loãng xương", "chiều cao"]) and not any(w in clean_q for w in ["hấp thu", "photpho", "ruột non"]):
                score = max(0.0, score - 2.5)
        elif claim_id == "CLM-D3-02":
            if any(w in clean_q for w in ["photpho", "ruột non", "canxi máu"]) and not any(w in clean_q for w in ["xương", "răng", "chắc"]):
                score = max(0.0, score - 2.5)
        elif claim_id == "CLM-FE-01":
            if any(w in clean_q for w in ["táo bón", "buồn nôn", "nóng", "dạ dày", "cồn cào"]) and not any(w in clean_q for w in ["tạo máu", "thiếu máu", "bổ máu", "acid folic"]):
                score = max(0.0, score - 2.5)
        elif claim_id == "CLM-FE-02":
            if any(w in clean_q for w in ["tạo máu", "thiếu máu", "hồng cầu"]) and not any(w in clean_q for w in ["táo bón", "buồn nôn", "nóng", "dạ dày"]):
                score = max(0.0, score - 2.5)

        return round(score, 2), list(dict.fromkeys(matched_indicators))

    def retrieve_claims(
        self,
        query: str,
        target_skus: List[str],
        top_k: int = 3,
        is_overview: bool = False,
    ) -> List[RetrievedClaim]:
        """
        Truy xuất danh sách Claims đủ điều kiện pháp lý và có mức độ liên quan đạt chuẩn.
        - Chỉ tìm trong target_skus chỉ định.
        - Tự động lọc qua ClaimEligibilityValidator (loại bỏ EXPIRED, INTERNAL_EXPERT, REVOKED).
        - Nếu is_overview=True: lấy toàn bộ Claims thương mại đã được phê duyệt của sản phẩm cho câu hỏi tổng quan.
        - Nếu is_overview=False: tính điểm liên quan ngữ nghĩa và lọc theo min_threshold.
        - Trả về danh sách được xếp hạng từ cao xuống thấp.
        """
        if not target_skus:
            return []

        scored_claims: List[RetrievedClaim] = []

        # Xử lý câu hỏi tổng quan / ưu điểm nổi bật (Overview Inquiry)
        if is_overview:
            for sku in target_skus:
                eligible_claims = self.repo.get_eligible_commercial_claims(sku)
                for claim in eligible_claims:
                    profile = CLAIM_CONCEPT_PROFILES.get(claim.claim_id.strip(), {})
                    weight = profile.get("weight", 3.0)
                    scored_claims.append(
                        RetrievedClaim(
                            claim=claim,
                            score=round(weight + 0.5, 2),
                            matched_concepts=["hồ sơ công bố sản phẩm", "công dụng đã duyệt"],
                            relevance_grade="HIGH",
                        )
                    )
            scored_claims.sort(key=lambda x: x.score, reverse=True)
            return scored_claims[:max(top_k, 5)]

        clean_q = self._clean_text(query)
        content_tokens = self._extract_content_tokens(clean_q)
        if not content_tokens:
            return []

        for sku in target_skus:
            # 1. Chỉ lấy claims thương mại ĐỦ ĐIỀU KIỆN (Approved, Commercial Zone, còn hạn)
            eligible_claims = self.repo.get_eligible_commercial_claims(sku)

            for claim in eligible_claims:
                score, indicators = self.score_claim_relevance(query, claim)
                
                # Áp dụng ngưỡng liên quan tối thiểu:
                # Không xem Claim chỉ có 1 vài từ trùng chung chung là đủ bằng chứng
                if score >= self.min_threshold:
                    if score >= 5.0:
                        grade = "HIGH"
                    elif score >= 3.0:
                        grade = "MEDIUM"
                    else:
                        grade = "LOW"

                    scored_claims.append(
                        RetrievedClaim(
                            claim=claim,
                            score=score,
                            matched_concepts=indicators,
                            relevance_grade=grade,
                        )
                    )

        # 2. Xếp hạng Claims theo điểm số liên quan giảm dần
        scored_claims.sort(key=lambda x: x.score, reverse=True)

        return scored_claims[:top_k]

    def diagnose_retrieval(
        self,
        query: str,
        target_skus: List[str],
        retrieved_claims: List[RetrievedClaim],
        is_overview: bool = False,
    ) -> Dict[str, Any]:
        """Chẩn đoán kỹ thuật phân biệt nguyên nhân thiếu căn cứ hoặc từ chối."""
        if not target_skus:
            return {"code": "UNRESOLVED_PRODUCT", "message": "Không xác định được SKU sản phẩm phù hợp."}
        
        for sku in target_skus:
            prod = self.repo.get_product_by_sku(sku)
            if not prod:
                return {"code": "PRODUCT_NO_DATA", "message": f"Mã sản phẩm {sku} chưa có dữ liệu trong kho."}
            
            all_sku_claims = self.repo.get_claims_by_product(sku)
            if not all_sku_claims:
                return {"code": "PRODUCT_CLAIMS_EMPTY", "message": f"Sản phẩm {sku} chưa có bất kỳ phát biểu công dụng (Claim) nào."}
            
            eligible = self.repo.get_eligible_commercial_claims(sku)
            if not eligible:
                return {"code": "CLAIMS_UNAPPROVED_OR_EXPIRED", "message": f"Sản phẩm {sku} có claims nhưng chưa được duyệt hoặc đã hết hạn."}
        
        if not retrieved_claims:
            return {"code": "CLAIM_NOT_FOUND_FOR_INDICATION", "message": "Không có Claim nào khớp với công dụng hoặc triệu chứng được hỏi."}
        
        return {"code": "RETRIEVAL_SUCCESS", "message": f"Tìm thấy {len(retrieved_claims)} Claims hợp lệ."}
