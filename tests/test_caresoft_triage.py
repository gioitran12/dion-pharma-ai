import pytest
from fastapi.testclient import TestClient
from server import app
from modules.caresoft_triage import (
    extract_phone_number,
    extract_customer_name,
    detect_interested_product,
    classify_inquiry_type,
    score_lead,
    generate_caresoft_summary,
    process_first_touch_chat,
    load_caresoft_leads,
    update_lead_status,
    export_caresoft_leads_csv,
    get_caresoft_metrics
)

client = TestClient(app)


def test_phone_number_extraction():
    # Standard format
    assert extract_phone_number("SĐT của mình là 0982123456 nhé") == "0982123456"
    # Format with spaces
    assert extract_phone_number("Gọi cho tôi số 0982 123 456 vào buổi chiều") == "0982123456"
    # Format with dots
    assert extract_phone_number("Số liên hệ: 0982.123.456") == "0982123456"
    # Format with +84
    assert extract_phone_number("Liên hệ +84982123456 để giao hàng") == "0982123456"
    # Vistafa phone from survey (0358186058)
    assert extract_phone_number("Đầu mối: Nguyễn Hữu Tuấn - 0358186058") == "0358186058"
    # No phone
    assert extract_phone_number("Tôi chỉ muốn hỏi giá sản phẩm thôi") is None


def test_customer_name_extraction():
    assert extract_customer_name("Chào shop, mình là Thu Trang cần tư vấn") == "Thu Trang"
    assert extract_customer_name("Ship cho chị Mai Linh nhé") == "Mai Linh"
    assert extract_customer_name("Chỉ hỏi giá thôi", "Khách Web") == "Khách Web"


def test_product_detection_vistafa():
    assert "Collagen" in detect_interested_product("Cho mình hỏi bột collagen uống có bị tăng cân không")
    assert "Calci Complex" in detect_interested_product("Hộp calci complex bầu uống có bị sỏi thận không")
    assert "Sleep Well" in detect_interested_product("Tôi bị mất ngủ 2 năm rồi uống sleep well có đỡ không")


def test_inquiry_classification():
    code, name = classify_inquiry_type("Cho mình đặt 2 hộp giao về Cầu Giấy nhé")
    assert code == "DAT_HANG"

    code, name = classify_inquiry_type("Hộp này giá bao nhiêu tiền một hộp shop?")
    assert code == "HOI_GIA"

    code, name = classify_inquiry_type("Uống cái này có bị cồn cào dạ dày hay buồn nôn không")
    assert code == "TU_VAN_CHUYEN_MON"

    code, name = classify_inquiry_type("Tôi muốn khiếu nại hộp hàng bị vỡ nắp")
    assert code == "KHIEU_NAI"


def test_lead_scoring():
    # Has phone + Wants to buy -> HOT
    score, pct = score_lead(has_phone=True, inquiry_code="DAT_HANG", text="Đặt 2 hộp số 0983112233")
    assert score == "HOT"
    assert pct >= 85

    # Has phone + Asking price -> HOT
    score, pct = score_lead(has_phone=True, inquiry_code="HOI_GIA", text="Hỏi giá số 0983112233")
    assert score == "HOT"

    # No phone + Asking price -> WARM
    score, pct = score_lead(has_phone=False, inquiry_code="HOI_GIA", text="Hỏi giá bao nhiêu tiền")
    assert score == "WARM"

    # No phone + General greeting -> COLD
    score, pct = score_lead(has_phone=False, inquiry_code="KHAC", text="Xin chào shop")
    assert score == "COLD"


def test_caresoft_summary_generation():
    summary_card = generate_caresoft_summary(
        text="Mình bị mất ngủ lâu năm uống Sleep Well có bị phụ thuộc không",
        customer_name="Lê Hoàng Nam",
        phone="0904223344",
        product="Sleep Well (Vistafa)",
        inquiry_name="Tư vấn chuyên môn y dược",
        lead_score="HOT"
    )
    assert "Lê Hoàng Nam" in summary_card["summary"]
    assert "Sleep Well" in summary_card["summary"]
    assert "mất ngủ" in summary_card["pain_point"].lower()
    assert "Dược sĩ" in summary_card["telesale_script"] or "Vistafa" in summary_card["telesale_script"]


def test_process_first_touch_chat():
    raw_chat = "Chào shop, mình tên là Mai Lan. Mình muốn đặt 1 hộp Collagen Powder về số 25 Nguyễn Trãi, SĐT mình 0912345678."
    lead = process_first_touch_chat(raw_chat, channel="FACEBOOK")
    assert lead["lead_id"].startswith("LEAD-CS-")
    assert lead["phone"] == "0912345678"
    assert lead["has_phone"] is True
    assert lead["lead_score"] == "HOT"
    assert "Collagen" in lead["product_interest"]
    assert "Mai Lan" in lead["customer_name"]
    assert lead["status"] == "NEW"


def test_api_caresoft_triage_endpoint():
    payload = {
        "chat_text": "Cho mình hỏi Calci Complex bầu 5 tháng uống được không? Gọi tư vấn mình số 0988776655 nhé, mình là Phương Thảo.",
        "channel": "ZALO_OA",
        "customer_name": "Phương Thảo"
    }
    res = client.post("/api/caresoft/triage", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    lead = data["lead"]
    assert lead["phone"] == "0988776655"
    assert lead["lead_score"] == "HOT"
    assert "Phương Thảo" in lead["customer_name"]
    assert "Calci Complex" in lead["product_interest"]
    assert "summary" in lead
    assert "pain_point" in lead
    assert "suggested_telesale_script" in lead


def test_api_caresoft_leads_and_metrics_endpoint():
    res = client.get("/api/caresoft/leads")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert isinstance(data["leads"], list)
    assert len(data["leads"]) >= 1
    metrics = data["metrics"]
    assert "total_leads" in metrics
    assert "phone_conversion_rate" in metrics
    assert "hot_leads_count" in metrics


def test_api_caresoft_export_endpoint():
    res = client.get("/api/caresoft/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    content = res.text
    # Should start with UTF-8 BOM
    assert content.startswith("\ufeff")
    # Verify header columns
    assert "Mã Lead" in content
    assert "Số Điện Thoại" in content
    assert "Tóm Tắt Nhu Cầu" in content
    assert "Kịch Bản Gọi Telesale Gợi Ý" in content


def test_zero_emojis_in_caresoft_module():
    leads = load_caresoft_leads()
    for l in leads:
        for k, v in l.items():
            if isinstance(v, str):
                emojis = [c for c in v if ord(c) > 0x1F000 or (0x2600 <= ord(c) <= 0x27BF)]
                assert len(emojis) == 0, f"Found emoji in lead {l.get('lead_id')} field {k}: {emojis}"


def test_api_content_generate_draft_tiktok():
    res = client.post("/api/content/generate-draft", json={
        "sku": "VISTAFA-COLLAGEN",
        "channel": "TikTok Video (1-2 video/ngày)",
        "tone": "Khoa học & Chuyên môn"
    })
    assert res.status_code == 200
    data = res.json()
    assert "draft_text" in data
    text = data["draft_text"]
    assert "KỊCH BẢN VIDEO NGẮN TIKTOK" in text
    assert "HOOK" in text
    assert "CTA" in text or "LỜI KÊU GỌI HÀNH ĐỘNG" in text
    assert "KHUYẾN CÁO BẮT BUỘC" in text
    # Verify zero emojis
    emojis = [c for c in text if ord(c) > 0x1F000 or (0x2600 <= ord(c) <= 0x27BF)]
    assert len(emojis) == 0, f"Found emoji in TikTok script: {emojis}"


def test_api_content_generate_draft_facebook():
    res = client.post("/api/content/generate-draft", json={
        "sku": "VISTAFA-CALCI",
        "channel": "Facebook Post",
        "tone": "Khoa học & Chuyên môn"
    })
    assert res.status_code == 200
    data = res.json()
    assert "draft_text" in data
    text = data["draft_text"]
    assert "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO" in text
    assert "KHUYẾN CÁO BẮT BUỘC" in text

