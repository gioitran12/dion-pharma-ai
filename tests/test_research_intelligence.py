"""
Tests for DION AI Research & Clinical Intelligence (Giải pháp 6)
Kiểm thử toàn diện kho dữ liệu y văn PubMed, động cơ so sánh dược lý,
bóc tách PICO y học thực chứng và các API endpoints của hệ thống.
"""

import json
import os
import tempfile
import pytest
from starlette.testclient import TestClient

from modules.research_intelligence.schemas import (
    StudyType,
    EvidenceGrade,
    StudyRecord,
    SearchStudiesRequest,
    LinkClaimRequest,
    AIAnalyzeStudyRequest
)
from modules.research_intelligence.repository import MedicalLiteratureRepository
from modules.research_intelligence.pharmacology_engine import PharmacologyEngine
from modules.research_intelligence.evidence_extractor import ClinicalEvidenceExtractor
from modules.research_intelligence.service import ResearchIntelligenceService
from server import app


@pytest.fixture
def repo():
    return MedicalLiteratureRepository()


@pytest.fixture
def pharmacology_engine():
    return PharmacologyEngine()


@pytest.fixture
def extractor():
    return ClinicalEvidenceExtractor()


@pytest.fixture
def research_service():
    return ResearchIntelligenceService()


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. KIỂM THỬ KHO DỮ LIỆU Y VĂN (REPOSITORY)
# ==============================================================================

def test_repository_load_ingredients(repo):
    """Kho y văn tải được danh mục hoạt chất đầy đủ"""
    ingredients = repo.list_active_ingredients()
    assert len(ingredients) >= 7
    ids = [ing.id for ing in ingredients]
    assert "lithothamnion" in ids
    assert "calcium-citrate" in ids
    assert "ferrous-bisglycinate" in ids


def test_repository_category_filter(repo):
    """Lọc hoạt chất theo phân nhóm CANXI, SAT, VITAMIN"""
    calcium_list = repo.get_ingredients(category="CANXI")
    assert len(calcium_list) >= 3
    for ing in calcium_list:
        assert ing.category == "CANXI"

    iron_list = repo.get_ingredients(category="SAT")
    assert len(iron_list) >= 2
    for ing in iron_list:
        assert ing.category == "SAT"


def test_repository_studies_count_and_pmid_lookup(repo):
    """Tra cứu nghiên cứu lâm sàng theo mã PMID thực tế"""
    studies = repo.list_studies()
    assert len(studies) >= 10

    # Kiểm tra tra cứu PMID: 20213326 (Lithothamnion RCT)
    study = repo.get_study_by_pmid("20213326")
    assert study is not None
    assert "20213326" in study.pmid
    assert study.study_type in (StudyType.RCT_DOUBLE_BLIND, StudyType.RCT)
    assert study.evidence_grade == EvidenceGrade.GRADE_A
    assert "Lithothamnion" in study.title or "Canxi" in study.title


def test_repository_search_studies_filters(repo):
    """Tìm kiếm kết hợp từ khóa, loại nghiên cứu và cấp bằng chứng"""
    # Tìm kiếm theo từ khóa
    res_bmd = repo.search_studies(query="BMD")
    assert len(res_bmd) >= 1
    for s in res_bmd:
        assert "bmd" in s.title.lower() or "bmd" in s.key_findings.lower() or "bmd" in s.dion_application.lower()

    # Tìm kiếm theo phân hạng bằng chứng GRADE_A
    res_grade_a = repo.search_studies(evidence_grade="GRADE_A")
    assert len(res_grade_a) >= 5
    for s in res_grade_a:
        assert s.evidence_grade == EvidenceGrade.GRADE_A

    # Tìm kiếm theo hoạt chất
    res_iron = repo.search_studies(ingredient="Ferrous Bisglycinate")
    assert len(res_iron) >= 1
    assert "Bisglycinate" in res_iron[0].ingredient or "Sắt" in res_iron[0].ingredient


# ==============================================================================
# 2. KIỂM THỬ ĐỘNG CƠ DƯỢC LÝ & SINH KHẢ DỤNG (PHARMACOLOGY ENGINE)
# ==============================================================================

def test_calcium_pharmacology_comparison(pharmacology_engine):
    """Bảng so sánh 3 dạng Canxi và phân tích khoảng trống khẩu phần"""
    res = pharmacology_engine.get_calcium_comparison()
    assert res["category"] == "CANXI"
    items = res["items"]
    assert len(items) == 3

    # Kiểm tra DION Cal-Mom Plus form (Tảo Lithothamnion)
    dion_form = next(i for i in items if i["is_dion_form"])
    assert "Lithothamnion" in dion_form["compound_name"]
    assert dion_form["elemental_percent"] == 32.0

    # Kiểm tra Canxi Citrate
    citrate_form = next(i for i in items if "Citrate" in i["compound_name"])
    assert citrate_form["elemental_percent"] == 21.1

    # Kiểm tra Canxi Carbonate
    carbonate_form = next(i for i in items if "Carbonate" in i["compound_name"])
    assert carbonate_form["elemental_percent"] == 40.0

    # Kiểm tra phân tích khoảng trống dinh dưỡng
    ctx = res["nutritional_context"]
    assert "500 – 600 mg" in ctx["supplementation_gap"]
    assert "nhu cầu thực tế" in ctx["scientific_takeaway"]


def test_iron_pharmacology_comparison(pharmacology_engine):
    """Bảng so sánh 3 dạng Sắt và cơ chế dung nạp đường tiêu hóa"""
    res = pharmacology_engine.get_iron_comparison()
    assert res["category"] == "SAT"
    items = res["items"]
    assert len(items) == 3

    # Sắt Bisglycinate (DION Fero-Plus)
    bisglycinate = next(i for i in items if i["is_dion_form"])
    assert "Bisglycinate" in bisglycinate["compound_name"]
    assert "PEPT1" in bisglycinate["absorption_mechanism"]
    assert bisglycinate["constipation_risk"] == "Cực thấp (6.8%)"


# ==============================================================================
# 3. KIỂM THỬ TRÍCH XUẤT PICO (EVIDENCE EXTRACTOR)
# ==============================================================================

def test_extractor_pico_rule_fallback(extractor):
    """Trích xuất cấu trúc PICO theo chuẩn y văn bằng cơ chế phân tích lâm sàng"""
    import asyncio
    abstract = (
        "In a double-blind randomized controlled trial with n = 150 pregnant women in their second trimester, "
        "daily oral supplementation of Lithothamnion calcareum (500 mg elemental calcium) plus Vitamin D3 400 IU "
        "was compared against calcium carbonate (500 mg) for 16 weeks. "
        "Results showed significant increase in maternal bone mineral density (p < 0.01) and superior bioavailability. "
        "Gastrointestinal adverse events such as constipation were reported in only 2% vs 28% in the control group."
    )

    pico = asyncio.run(extractor.extract_pico(abstract, target_product_sku="DION-CAL-MOM"))
    assert "Phụ nữ mang thai" in pico.population
    assert "150" in pico.population
    assert "Lithothamnion" in pico.intervention
    assert "500" in pico.intervention
    assert "carbonate" in pico.comparison.lower()
    assert pico.evidence_grade in ("GRADE_A", "GRADE_B")
    assert "táo bón" in pico.adverse_reaction_profile.lower() or "tiêu hóa" in pico.adverse_reaction_profile.lower()


# ==============================================================================
# 4. KIỂM THỬ RESEARCH SERVICE & GẮN KẾT HỒ SƠ CLAIMS SẢN PHẨM
# ==============================================================================

def test_service_link_study_to_product_claim_isolated():
    """Gắn nghiên cứu lâm sàng vào hồ sơ claims độc lập trên tệp tạm"""
    dummy_data = {
        "products": [
            {
                "sku": "DION-TEST-01",
                "name": "Sản phẩm thử nghiệm R&D",
                "clinical_evidence": [],
                "claims": [
                    {
                        "claim_id": "CLM-TEST-01",
                        "claim_text": "Bổ sung canxi sinh học hỗ trợ xương",
                        "evidence_source": "Hồ sơ công bố nội bộ"
                    }
                ]
            }
        ]
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
        json.dump(dummy_data, tf, ensure_ascii=False)
        temp_file = tf.name

    try:
        svc = ResearchIntelligenceService(products_claims_path=temp_file)
        req = LinkClaimRequest(
            sku="DION-TEST-01",
            pmid="20213326",
            claim_id="CLM-TEST-01",
            assigned_by="DS. Kiểm định"
        )
        res = svc.link_study_to_product_claim(req)
        assert res["status"] == "SUCCESS"
        assert res["action"] == "created"
        assert res["claim_linked"] is True

        # Đọc lại và xác thực nội dung tệp tạm
        with open(temp_file, "r", encoding="utf-8") as f:
            updated = json.load(f)

        prod = updated["products"][0]
        assert len(prod["clinical_evidence"]) == 1
        ev = prod["clinical_evidence"][0]
        assert ev["is_verified"] is True
        assert ev["status"] == "VERIFIED_SUPPORT"
        assert "20213326" in ev["pmid"]
        assert "https://pubmed.ncbi.nlm.nih.gov/20213326/" == ev["pubmed_url"]

        # Kiểm tra claim liên kết giữ nguyên nguồn hành chính
        claim = prod["claims"][0]
        assert "Hồ sơ công bố nội bộ" in claim["evidence_source"]
        assert "20213326" in claim["evidence_source"]
        assert "PMID: 20213326" in claim["supporting_pmids"]
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_service_legacy_backward_compatibility(research_service):
    """Duy trì tương thích 100% cho cấu trúc endpoint cũ"""
    legacy_data = research_service.get_legacy_research_intelligence_data("Lithothamnion")
    assert legacy_data["ingredient"] == "Lithothamnion"
    assert "clinical_studies" in legacy_data
    assert len(legacy_data["clinical_studies"]) >= 1
    assert "safety_profile" in legacy_data
    assert "evidence_level" in legacy_data


# ==============================================================================
# 5. KIỂM THỬ CÁC FASTAPI ENDPOINTS
# ==============================================================================

def test_api_research_ingredients(client):
    """GET /api/research/ingredients"""
    resp = client.get("/api/research/ingredients")
    assert resp.status_code == 200
    data = resp.json()
    assert "ingredients" in data
    assert data["total"] >= 7


def test_api_research_studies_search(client):
    """GET /api/research/studies?query=calcium"""
    resp = client.get("/api/research/studies?query=calcium")
    assert resp.status_code == 200
    data = resp.json()
    assert "studies" in data
    assert len(data["studies"]) >= 1


def test_api_research_study_detail(client):
    """GET /api/research/studies/{pmid}"""
    resp = client.get("/api/research/studies/20213326")
    assert resp.status_code == 200
    data = resp.json()
    assert "20213326" in data["pmid"]
    assert "Lithothamnion" in data["title_vi"] or "Lithothamnion" in data["title_en"]

    # Tra cứu PMID không tồn tại -> 404
    resp_404 = client.get("/api/research/studies/99999999")
    assert resp_404.status_code == 404


def test_api_research_pharmacology_compare(client):
    """GET /api/research/pharmacology/compare?category=CANXI"""
    resp = client.get("/api/research/pharmacology/compare?category=CANXI")
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "CANXI"
    assert len(data["items"]) == 3
    assert "nutritional_context" in data


def test_api_research_ai_analyze(client):
    """POST /api/research/ai-analyze"""
    payload = {
        "abstract_text": "Randomized cross-over trial with n = 45 healthy volunteers comparing Lithothamnion vs calcium carbonate. PTH was suppressed for 8 hours with p < 0.01.",
        "target_product_sku": "DION-CAL-MOM"
    }
    resp = client.post("/api/research/ai-analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "analysis" in data
    assert "population" in data["analysis"]
    assert "intervention" in data["analysis"]


def test_api_legacy_research_intelligence_endpoint(client):
    """GET /api/research-intelligence?ingredient=Lithothamnion (Tương thích ngược)"""
    resp = client.get("/api/research-intelligence?ingredient=Lithothamnion")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingredient"] == "Lithothamnion"
    assert "scientific_summary" in data
    assert "evidence_table" in data
    assert len(data["evidence_table"]) >= 1
    item = data["evidence_table"][0]
    assert "pmid" in item
    assert "study_type" in item
    assert "evidence_grade" in item
