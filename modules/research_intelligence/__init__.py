"""
Research Intelligence Module - DION AI Copilot
Cung cấp tra cứu y văn lâm sàng chuẩn PubMed, phân tích dược lý so sánh và trích xuất PICO.
"""

from modules.research_intelligence.schemas import (
    StudyType,
    EvidenceGrade,
    StudyRecord,
    ActiveIngredientInfo,
    PharmacologyComparisonItem,
    PICOAnalysis,
    SearchStudiesRequest,
    AIAnalyzeStudyRequest,
    LinkClaimRequest,
)
from modules.research_intelligence.repository import MedicalLiteratureRepository
from modules.research_intelligence.pharmacology_engine import PharmacologyEngine
from modules.research_intelligence.evidence_extractor import ClinicalEvidenceExtractor
from modules.research_intelligence.service import ResearchIntelligenceService

__all__ = [
    "StudyType",
    "EvidenceGrade",
    "StudyRecord",
    "ActiveIngredientInfo",
    "PharmacologyComparisonItem",
    "PICOAnalysis",
    "SearchStudiesRequest",
    "AIAnalyzeStudyRequest",
    "LinkClaimRequest",
    "MedicalLiteratureRepository",
    "PharmacologyEngine",
    "ClinicalEvidenceExtractor",
    "ResearchIntelligenceService",
]
