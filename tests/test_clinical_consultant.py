import pytest
from fastapi.testclient import TestClient
from server import app
from modules.clinical_consultant import consult_ai_expert, CLINICAL_KB

client = TestClient(app)

def test_kidney_stone_consultation():
    res = consult_ai_expert(
        message="Uống Canxi DION Cal-Mom có bị sỏi thận hoặc vôi hóa không?",
        sku="DION-CAL-MOM",
        mode="PHARMACIST_B2C"
    )
    assert res["status"] == "success"
    assert "Lithothamnion" in res["direct_answer"] or "tảo biển đỏ" in res["direct_answer"]
    assert "Vitamin K2 MK-7" in res["direct_answer"] or "K2" in res["direct_answer"]
    assert "sỏi thận" in res["direct_answer"].lower()
    assert "Matrix Gla Protein" in res["clinical_rationale"]
    assert "8892/2025/ĐKSP" in res["regulatory_basis"]
    assert "Dạ chị hoàn toàn yên tâm" in res["sample_script"]


def test_constipation_consultation():
    res = consult_ai_expert(
        message="Uống Sắt DION Fero-Plus có bị táo bón hoặc nóng trong không?",
        sku="DION-FE-PLUS",
        mode="PHARMACIST_B2C"
    )
    assert res["status"] == "success"
    assert "Bisglycinate" in res["direct_answer"] or "Chelate" in res["direct_answer"]
    assert "Quatrefolic" in res["direct_answer"]
    assert "táo bón" in res["direct_answer"].lower()
    assert "kênh vận chuyển Peptide" in res["clinical_rationale"] or "Glycine" in res["clinical_rationale"]
    assert "9124/2025/ĐKSP" in res["regulatory_basis"]
    assert "không hề có mùi tanh" in res["sample_script"]


def test_drug_interaction_consultation():
    res = consult_ai_expert(
        message="Canxi và Sắt có uống cùng lúc được không? Cần uống cách nhau bao lâu?",
        sku="ALL",
        mode="SALES_REP_B2B"
    )
    assert res["status"] == "success"
    assert "2 giờ" in res["direct_answer"]
    assert "kháng sinh" in res["direct_answer"].lower()
    assert "DMT1" in res["clinical_rationale"] or "cạnh tranh hấp thu" in res["clinical_rationale"]
    assert "Sáng Canxi - Trưa Sắt" in res["sample_script"]


def test_pregnancy_usage_consultation():
    res = consult_ai_expert(
        message="Phụ nữ mang thai từ tháng thứ mấy thì bắt đầu uống Canxi và Sắt DION?",
        sku="ALL",
        mode="PHARMACIST_B2C"
    )
    assert res["status"] == "success"
    assert "tuần thứ 12" in res["direct_answer"] or "tháng thứ 4" in res["sample_script"]
    assert "Tam cá nguyệt" in res["usage_and_interactions"] or "Sau sinh" in res["usage_and_interactions"]
    assert "8892/2025/ĐKSP" in res["regulatory_basis"]


def test_objection_new_brand():
    res = consult_ai_expert(
        message="Chủ nhà thuốc từ chối: Hàng mới chưa có khách hỏi mua nên quầy không dám nhập",
        sku="ALL",
        mode="OBJECTION_HANDLING"
    )
    assert res["status"] == "success"
    assert "Bước 1" in res["sample_script"]
    assert "Bước 2" in res["sample_script"]
    assert "Bước 3" in res["sample_script"]
    assert "thu hồi" in res["sample_script"] or "đổi trả" in res["sample_script"]


def test_objection_high_price():
    res = consult_ai_expert(
        message="Chủ quầy chê giá 320.000đ đắt hơn các dòng canxi đá vôi thông thường",
        sku="DION-CAL-MOM",
        mode="OBJECTION_HANDLING"
    )
    assert res["status"] == "success"
    assert "320.000" in res["clinical_rationale"]
    assert "5.000" in res["sample_script"] or "5.300" in res["sample_script"]


def test_objection_foreign_products():
    res = consult_ai_expert(
        message="Chủ quầy bảo đang bán rất chạy hàng ngoại xách tay của Úc và Pháp rồi",
        sku="DION-CAL-MOM",
        mode="SALES_REP_B2B"
    )
    assert res["status"] == "success"
    assert "Ostelin" in res["clinical_rationale"] or "xách tay" in res["clinical_rationale"]
    assert "VAT" in res["clinical_rationale"]
    assert "32-35%" in res["sample_script"]


def test_api_copilot_consult_endpoint():
    response = client.post(
        "/api/copilot/consult",
        json={
            "message": "Đang uống kháng sinh hoặc thuốc huyết áp thì uống Canxi thế nào?",
            "sku": "DION-CAL-MOM",
            "mode": "PHARMACIST_B2C"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["mode"] == "PHARMACIST_B2C"
    assert "direct_answer" in data
    assert "clinical_rationale" in data
    assert "usage_and_interactions" in data
    assert "regulatory_basis" in data
    assert "sample_script" in data
    assert "citations" in data
    assert "disclaimer" in data
    assert len(data["direct_answer"]) > 20


def test_zero_emojis_in_clinical_consultation_output():
    for topic_key, topic_data in CLINICAL_KB.items():
        for field in ["direct_answer", "clinical_rationale", "usage_and_interactions", "regulatory_basis"]:
            text = topic_data[field]
            emojis = [c for c in text if ord(c) > 0x1F000]
            assert len(emojis) == 0, f"Found emoji in {topic_key} {field}: {emojis}"
        for mode, script in topic_data["sample_scripts"].items():
            emojis = [c for c in script if ord(c) > 0x1F000]
            assert len(emojis) == 0, f"Found emoji in {topic_key} script {mode}: {emojis}"


def test_vistafa_five_products_consultation():
    # 1. Calci Complex
    res_cal = client.post("/api/copilot/consult", json={"message": "Uống Canxi này có sợ sỏi thận không?", "sku": "VIST-CALCIUM"}).json()
    assert res_cal["status"] == "success"
    assert "four_steps" in res_cal
    assert "step1_direct_answer" in res_cal["four_steps"]
    assert "red_flags" in res_cal

    # 2. Beauty Collagen
    res_col = client.post("/api/copilot/consult", json={"message": "Uống Collagen có sợ tăng cân hay nổi mụn không?", "sku": "VIST-COLLAGEN"}).json()
    assert res_col["status"] == "success"
    assert "Collagen" in res_col["direct_answer"] or "Peptide" in res_col["clinical_rationale"] or "hộp" in res_col["direct_answer"]

    # 3. Ultimate Omega 3
    res_omg = client.post("/api/copilot/consult", json={"message": "Uống Omega 3 có bị ợ tanh không?", "sku": "VIST-OMEGA3"}).json()
    assert res_omg["status"] == "success"
    assert "Omega" in res_omg["product_name"]

    # 4. Sleep Well
    res_slp = client.post("/api/copilot/consult", json={"message": "Mất ngủ 2 năm uống Sleep Well có đỡ không?", "sku": "VIST-SLEEP"}).json()
    assert res_slp["status"] == "success"
    assert "Sleep Well" in res_slp["product_name"]

    # 5. FerroActive
    res_fe = client.post("/api/copilot/consult", json={"message": "Sắt FerroActive có gây táo bón không?", "sku": "VIST-FERRO"}).json()
    assert res_fe["status"] == "success"
    assert "FerroActive" in res_fe["product_name"]


def test_vistafa_multichannel_adaptation():
    channels = ["facebook", "zalo", "website", "tiktok"]
    for ch in channels:
        res = client.post("/api/copilot/consult", json={
            "message": "Collagen giá bao nhiêu?",
            "sku": "VIST-COLLAGEN",
            "channel": ch
        }).json()
        assert res["status"] == "success"
        assert res["channel"] == ch
        assert len(res["split_messages"]) > 0


def test_vistafa_clinical_red_flag_gating():
    # Sỏi thận nặng và uống diazepam
    res = client.post("/api/copilot/consult", json={
        "message": "Khách bị sỏi thận 12mm và đang uống diazepam thuốc ngủ thì dùng thế nào?",
        "sku": "VIST-CALCIUM"
    }).json()
    assert res["status"] == "success"
    assert res["red_flags"]["has_red_flag"] is True
    assert res["red_flags"]["pharmacist_escalation"] is True
    assert len(res["red_flags"]["flags"]) >= 1


def test_vistafa_competitor_comparison():
    # Corbiere vs Calci Complex
    res = client.post("/api/copilot/consult", json={
        "message": "Sao Canxi Corbiere dạng sủi rẻ hơn nhiều?",
        "sku": "VIST-CALCIUM"
    }).json()
    assert res["status"] == "success"
    assert res["competitor_comparison"] is not None
    assert "Corbiere" in res["competitor_comparison"]["competitor_name"]

