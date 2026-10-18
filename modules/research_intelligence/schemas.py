# -*- coding: utf-8 -*-
"""
DION Healthcare AI — Research Intelligence Schemas & Enums
Định nghĩa Data Models cho Y văn Khoa học, Bằng chứng Lâm sàng PubMed, PICO Framework và Đối chiếu Dược lý học.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StudyType(str, Enum):
    """Phân loại thiết kế nghiên cứu lâm sàng theo chuẩn y khoa quốc tế"""
    RCT = "RCT"                                   # Thử nghiệm ngẫu nhiên có đối chứng
    RCT_DOUBLE_BLIND = "RCT_DOUBLE_BLIND"         # Thử nghiệm ngẫu nhiên mù đôi có đối chứng
    META_ANALYSIS = "META_ANALYSIS"               # Phân tích gộp
    SYSTEMATIC_REVIEW = "SYSTEMATIC_REVIEW"       # Tổng quan hệ thống
    CROSSOVER_TRIAL = "CROSSOVER_TRIAL"           # Thử nghiệm đối chứng chéo
    COHORT_STUDY = "COHORT_STUDY"                 # Nghiên cứu thuần tập
    IN_VITRO = "IN_VITRO"                         # Nghiên cứu tiền lâm sàng / in vitro


class EvidenceGrade(str, Enum):
    """Xếp hạng mức độ tin cậy bằng chứng y khoa theo Oxford CEBM"""
    GRADE_A = "GRADE_A"  # Hạng A: Bằng chứng lâm sàng mạnh (RCTs lớn, Meta-analysis chất lượng cao)
    GRADE_B = "GRADE_B"  # Hạng B: Bằng chứng trung bình (Thử nghiệm đối chứng không ngẫu nhiên, Cohort)
    GRADE_C = "GRADE_C"  # Hạng C: Bằng chứng sơ bộ / In vitro / Báo cáo ca lâm sàng


class StudyRecord(BaseModel):
    """Bản ghi dữ liệu của một nghiên cứu y văn lâm sàng"""
    pmid: str = Field(..., description="Định danh chuẩn PubMed (ví dụ: PMID: 20213326)")
    title_en: str = Field(..., description="Tiêu đề nghiên cứu tiếng Anh gốc trên PubMed")
    title_vi: str = Field(..., description="Tiêu đề nghiên cứu dịch chuẩn ngữ nghĩa tiếng Việt")
    authors: str = Field(..., description="Danh sách tác giả chính")
    journal: str = Field(..., description="Tên tạp chí y khoa công bố")
    publication_year: int = Field(..., description="Năm công bố bài báo")
    ingredient: str = Field(..., description="Hoạt chất hoặc hợp chất vi chất được nghiên cứu")
    study_type: StudyType = Field(default=StudyType.RCT_DOUBLE_BLIND, description="Thiết kế nghiên cứu")
    sample_size: str = Field(..., description="Cỡ mẫu và đối tượng thử nghiệm (N)")
    target_group: str = Field(..., description="Nhóm đối tượng (Mẹ bầu, Phụ nữ mãn kinh, Người lớn tuổi, v.v.)")
    dosage: str = Field(..., description="Liều can thiệp cụ thể và thời gian sử dụng")
    intervention: str = Field(..., description="Phương pháp / phác đồ can thiệp nhóm thử nghiệm")
    control: str = Field(..., description="Nhóm đối chứng (Placebo hoặc hoạt chất so sánh)")
    key_findings: str = Field(..., description="Kết quả chính ghi nhận được")
    adverse_events: str = Field(default="Không ghi nhận tác dụng phụ nghiêm trọng", description="Tác dụng phụ / tính an toàn")
    evidence_grade: EvidenceGrade = Field(default=EvidenceGrade.GRADE_A, description="Hạng bằng chứng y khoa")
    evidence_grade_label: str = Field(default="Hạng A (Bằng chứng lâm sàng mạnh)", description="Nhãn hiển thị trực quan")
    dion_application: str = Field(..., description="Ứng dụng thực tế bảo chứng cho sản phẩm DION")
    pubmed_url: str = Field(..., description="Đường link tra cứu trực tiếp trên PubMed NCBI")
    abstract: Optional[str] = Field(default="", description="Tóm tắt nghiên cứu khoa học (Abstract)")
    tags: List[str] = Field(default_factory=list, description="Thẻ phân loại chuyên môn")

    @property
    def title(self) -> str:
        return self.title_vi or self.title_en

    @property
    def year(self) -> int:
        return self.publication_year

    @property
    def dosage_used(self) -> str:
        return self.dosage

    @property
    def primary_outcome(self) -> str:
        return self.key_findings

    @property
    def ingredient_id(self) -> str:
        return self.ingredient


class ActiveIngredientInfo(BaseModel):
    """Thông tin hóa dược & dược lực học của một hoạt chất vi chất"""
    id: str = Field(..., description="Định danh hoạt chất (ví dụ: lithothamnion, calcium-citrate)")
    name: str = Field(..., description="Tên thương mại / tên thông dụng")
    scientific_name: str = Field(..., description="Tên danh pháp khoa học")
    chemical_formula: Optional[str] = Field(default="", description="Công thức hóa học")
    category: str = Field(..., description="Nhóm phân loại: CANXI, VITAMIN, SAT, KHOANG_CHAT")
    elemental_content_percent: float = Field(..., description="Tỷ lệ nguyên tố nguyên chất tính theo % khối lượng")
    elemental_content_desc: str = Field(..., description="Mô tả cụ thể về tỷ lệ nguyên tố")
    bioavailability_rating: str = Field(default="HIGH", description="Mức độ sinh khả dụng: VERY_HIGH, HIGH, MEDIUM, LOW")
    solubility_profile: str = Field(..., description="Đặc tính hòa tan theo môi trường pH dạ dày / ruột")
    gi_tolerance: str = Field(..., description="Mức độ êm dịu dạ dày & nguy cơ tác dụng phụ tiêu hóa")
    pharmacology_summary: str = Field(..., description="Tóm tắt dược lý và cơ chế hấp thu")
    clinical_notes: str = Field(..., description="Lưu ý lâm sàng khi chỉ định / sử dụng thực tế")


class PharmacologyComparisonItem(BaseModel):
    """Một dòng đối chiếu dược lý so sánh các dạng muối/hợp chất"""
    compound_name: str
    compound_type: str
    molecular_formula: str
    elemental_percent: float
    solubility_gastric_ph: str
    absorption_mechanism: str
    constipation_risk: str
    dose_for_standard_need: str
    clinical_evaluation: str
    is_dion_form: bool = False


class PICOAnalysis(BaseModel):
    """Cấu trúc trích xuất PICO từ tài liệu khoa học lâm sàng"""
    population: str = Field(..., description="P (Population / Patient): Đối tượng và cỡ mẫu nghiên cứu")
    intervention: str = Field(..., description="I (Intervention): Hoạt chất can thiệp, liều lượng, dạng dùng")
    comparison: str = Field(..., description="C (Comparison): Nhóm đối chứng hoặc chất so sánh")
    outcome: str = Field(..., description="O (Outcome): Kết quả lâm sàng chính đo lường được")
    evidence_grade: str = Field(..., description="Phân hạng bằng chứng khuyến nghị")
    clinical_takeaways: str = Field(..., description="Kết luận thực tiễn cho R&D và Dược vụ")
    adverse_reaction_profile: str = Field(..., description="Hồ sơ an toàn và tác dụng không mong muốn")
    dion_alignment_note: str = Field(..., description="Mức độ phù hợp với hồ sơ công bố của DION")


# ==============================================================================
# DTOs CHO REQUEST & RESPONSE CỦA CÁC API NGHIÊN CỨU
# ==============================================================================

class SearchStudiesRequest(BaseModel):
    """Tham số tìm kiếm y văn lâm sàng"""
    query: Optional[str] = None
    ingredient: Optional[str] = None
    study_type: Optional[str] = None
    evidence_grade: Optional[str] = None
    target_group: Optional[str] = None
    limit: int = 50


class AIAnalyzeStudyRequest(BaseModel):
    """Yêu cầu AI trích xuất PICO và phân tích bài báo"""
    abstract_text: str = Field(..., description="Đoạn trích tóm tắt bài báo y khoa (Abstract) cần phân tích")
    target_product_sku: Optional[str] = Field(default=None, description="SKU sản phẩm DION cần đối chiếu")


class LinkClaimRequest(BaseModel):
    """Yêu cầu gắn kết quả nghiên cứu vào hồ sơ Claims sản phẩm"""
    sku: str = Field(..., description="Mã SKU sản phẩm (ví dụ: DION-CAL-MOM)")
    pmid: str = Field(..., description="Mã PMID của nghiên cứu cần gắn")
    claim_id: Optional[str] = Field(default=None, description="Mã Claim cụ thể nếu gắn vào Claim có sẵn")
    assigned_by: str = Field(default="Dược sĩ Phụ trách R&D", description="Nhân sự thực hiện gắn kết")
