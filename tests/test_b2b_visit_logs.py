import pytest
from fastapi.testclient import TestClient
from server import app
from modules.lead_discovery import load_leads_data, log_lead_visit, get_lead_visits, filter_leads
import shutil
from pathlib import Path

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def backup_and_restore_leads():
    leads_file = Path("data/b2b_leads.json")
    backup_file = Path("data/b2b_leads.json.visitbak")
    if leads_file.exists():
        shutil.copyfile(leads_file, backup_file)
    yield
    if backup_file.exists():
        shutil.move(backup_file, leads_file)

def test_get_lead_visits_api():
    # LD-HN-001 was seeded with a visit log
    res = client.get("/api/leads/LD-HN-001/visits")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["lead_id"] == "LD-HN-001"
    assert isinstance(data["visits"], list)
    assert data["total"] >= 1
    v = data["visits"][0]
    assert "visit_id" in v
    assert "DS. Nguyễn Thị Lan" in v["contact_person"]
    assert "Ostelin" in v["competitor_products"]

def test_log_lead_visit_api():
    payload = {
        "visited_at": "2026-10-19 15:30",
        "visitor_name": "Vũ Hải Đăng (Sales Lead Hà Nội)",
        "contact_person": "DS. Trần Văn Hưng",
        "contact_role": "Chủ nhà thuốc",
        "competitor_products": "Cal-D Ostelin (Úc), Feroglobin B12",
        "competitor_price": "210.000đ/hộp",
        "meeting_result": "SAMPLE_DELIVERED",
        "meeting_result_text": "Đã gửi mẫu trải nghiệm & Catalogue",
        "new_status": "SAMPLE_EVALUATING",
        "notes": "Chủ quầy đánh giá cao công thức hữu cơ Lithothamnion không gây sỏi thận. Hẹn tuần sau ghé lại chốt đơn đầu.",
        "next_follow_up_date": "2026-10-26"
    }
    res = client.post("/api/leads/LD-HN-002/visits", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["lead_status"] == "SAMPLE_EVALUATING"
    assert "Cal-D Ostelin" in data["competitor_presence"]
    assert data["visit"]["contact_person"] == "DS. Trần Văn Hưng"

    # Verify visit is retrieved via GET
    get_res = client.get("/api/leads/LD-HN-002/visits")
    assert get_res.status_code == 200
    visits = get_res.json()["visits"]
    assert len(visits) >= 1
    assert visits[0]["contact_role"] == "Chủ nhà thuốc"

def test_log_visit_order_agreed():
    payload = {
        "visitor_name": "Nguyễn Hoàng Nam (TDV)",
        "contact_person": "DS. Lê Mai",
        "contact_role": "Dược sĩ đứng quầy",
        "meeting_result": "ORDER_AGREED",
        "notes": "Quầy chốt nhập đơn thử nghiệm 20 hộp Cal-Mom và 10 hộp D3.",
        "new_status": "APPROVED"
    }
    res = client.post("/api/leads/LD-HN-003/visits", json=payload)
    assert res.status_code == 200
    assert res.json()["lead_status"] == "APPROVED"

def test_log_visit_not_found():
    res = client.post("/api/leads/NON-EXISTENT-LEAD-999/visits", json={"notes": "test"})
    assert res.status_code == 404

def test_filter_leads_by_sample_evaluating():
    # Filter with status SAMPLE_EVALUATING
    leads = filter_leads(status="SAMPLE_EVALUATING")
    assert isinstance(leads, list)
    assert len(leads) >= 1
    for l in leads:
        assert l["status"] == "SAMPLE_EVALUATING"
