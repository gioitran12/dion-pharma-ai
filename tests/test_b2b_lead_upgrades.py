import pytest
from fastapi.testclient import TestClient
from server import app
from modules.lead_discovery import load_leads_data, add_new_lead, import_leads_bulk

import shutil
from pathlib import Path

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def backup_and_restore_leads():
    leads_file = Path("data/b2b_leads.json")
    backup_file = Path("data/b2b_leads.json.testbak")
    if leads_file.exists():
        shutil.copyfile(leads_file, backup_file)
    yield
    if backup_file.exists():
        shutil.move(backup_file, leads_file)

def test_load_leads_data():
    leads = load_leads_data()
    assert isinstance(leads, list)
    assert len(leads) > 0
    # verify schema has required fields
    sample = leads[0]
    assert "lead_id" in sample
    assert "name" in sample
    assert "fit_score" in sample

def test_add_lead_api():
    payload = {
        "name": "Nhà thuốc Test Đống Đa - GPP",
        "type": "Nhà thuốc tư nhân",
        "province": "Hà Nội",
        "district": "Đống Đa",
        "address": "99 Tây Sơn, Đống Đa, Hà Nội",
        "phone": "0988776655",
        "email": "test@dongda.vn",
        "contact_person": "DS. Hoàng Lan",
        "tax_code": "0109998881",
        "gpp_license": "9999/GPP-HN",
        "target_hospital": "BV Phụ sản TW",
        "is_new_opened": True,
        "notes": "Mới mở, có 3 tầng kệ trống"
    }
    response = client.post("/api/leads/add", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    lead = data["lead"]
    assert lead["name"] == "Nhà thuốc Test Đống Đa - GPP"
    assert lead["is_new_opened"] is True
    assert lead["fit_score"] >= 80
    assert "BV Phụ sản TW" in lead["target_hospital"]

def test_import_leads_api():
    import time
    t = str(time.time_ns())[-6:]
    p1 = f"091{t}"
    p2 = f"092{t}"
    raw_text = f"""Tên nhà thuốc\tĐịa chỉ\tĐiện thoại\tTỉnh\tQuận\tNgười liên hệ\tBệnh viện lân cận
Nhà Thuốc Bulk Test {t} A\t123 Phố Huế\t{p1}\tHà Nội\tHai Bà Trưng\tDS. Nam\tBV Bạch Mai
Nhà Thuốc Bulk Test {t} B\t456 CMT8\t{p2}\tTP. Hồ Chí Minh\tQuận 3\tDS. Hằng\tBV Từ Dũ
Nhà Thuốc Bulk Test {t} A\t123 Phố Huế\t{p1}\tHà Nội\tHai Bà Trưng\tDS. Nam\tBV Bạch Mai"""
    
    response = client.post("/api/leads/import", json={
        "raw_text": raw_text,
        "default_province": "Hà Nội"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["imported_count"] == 2
    assert data["skipped_duplicates"] == 1

def test_pitch_3_channels_api():
    # Use existing lead LD-HN-001
    response = client.post("/api/leads/LD-HN-001/pitch", json={"sku": "DION-CAL-MOM"})
    assert response.status_code == 200
    data = response.json()
    assert "pitch_body" in data
    assert "zalo_message" in data
    assert "call_script" in data
    assert "strategy" in data
    assert len(data["pitch_body"]) > 50
    assert len(data["zalo_message"]) > 30
    assert len(data["call_script"]) > 30

def test_ai_insights_swot_api():
    # Use existing lead LD-HN-001
    response = client.post("/api/leads/LD-HN-001/ai-insights", json={})
    assert response.status_code == 200
    data = response.json()
    assert "swot" in data
    swot = data["swot"]
    assert "strengths" in swot and len(swot["strengths"]) > 0
    assert "weaknesses" in swot and len(swot["weaknesses"]) > 0
    assert "opportunities" in swot and len(swot["opportunities"]) > 0
    assert "threats" in swot and len(swot["threats"]) > 0
    assert "entry_angle" in data
    assert "icp_rating" in data
