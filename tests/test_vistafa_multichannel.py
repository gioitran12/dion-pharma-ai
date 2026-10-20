import re
import pytest
from fastapi.testclient import TestClient
from server import app
from modules.vistafa_chat_copilot import get_vistafa_chat_copilot

client = TestClient(app)
copilot = get_vistafa_chat_copilot()

EMOJI_PATTERN = re.compile(
    "[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u3030\u303d\u3297\u3299]"
)

def test_playbook_data_loaded():
    channels = copilot.get_channels()
    assert len(channels) == 4
    assert set(channels.keys()) == {"facebook", "zalo", "website", "tiktok"}

    products = copilot.get_products()
    assert len(products) == 5
    assert set(products.keys()) == {
        "calcium_complex", "beauty_collagen", "ultimate_omega3", "sleep_well", "ferro_active"
    }

    shortcuts = copilot.get_shortcuts()
    assert len(shortcuts) >= 40

    competitors = copilot.get_competitor_matrix()
    assert len(competitors) >= 10

    qa_criteria = copilot.get_qa_standards()
    assert len(qa_criteria) == 10

def test_zero_emojis_in_playbook_and_responses():
    # Test internal data
    for entry in copilot._data.get("playbook_entries", []):
        for field in ["opening_message", "followup_question", "handling_notes", "transition_action"]:
            val = entry.get(field, "")
            assert len(EMOJI_PATTERN.findall(val)) == 0, f"Emoji found in playbook entry: {val}"

    for comp in copilot.get_competitor_matrix():
        for field in ["customer_question", "counter_question", "recommended_reply", "permissible_talking_points"]:
            val = comp.get(field, "")
            assert len(EMOJI_PATTERN.findall(val)) == 0, f"Emoji found in competitor matrix: {val}"

    # Test generated responses
    test_msgs = [
        "Cho mình hỏi giá canxi",
        "Có giao hàng không bạn",
        "So sánh với canxi corbiere",
        "Dầu cá uống có tác dụng gì",
        "Tôi bị mất ngủ thì dùng loại nào"
    ]
    for ch in ["facebook", "zalo", "website", "tiktok"]:
        for msg in test_msgs:
            resp = copilot.generate_response(msg, product_id="calcium_complex", channel=ch)
            assert len(EMOJI_PATTERN.findall(resp["full_text"])) == 0, f"Emoji in response: {resp['full_text']}"

def test_channel_adaptation_rules():
    msg = "Canxi này uống như thế nào và một ngày uống mấy viên?"
    
    # 1. Facebook: Split into 2 bubbles, asks for phone number
    resp_fb = copilot.generate_response(msg, product_id="calcium_complex", channel="facebook")
    assert resp_fb["channel"] == "facebook"
    assert len(resp_fb["split_messages"]) >= 2
    assert "SĐT" in resp_fb["full_text"] or "số điện thoại" in resp_fb["full_text"].lower()

    # 2. Zalo: Professional, offers label / certificates
    resp_zalo = copilot.generate_response(msg, product_id="calcium_complex", channel="zalo")
    assert resp_zalo["channel"] == "zalo"
    assert "Zalo" in resp_zalo["full_text"]

    # 3. Website: Fast response with instant contact capture
    resp_web = copilot.generate_response(msg, product_id="calcium_complex", channel="website")
    assert resp_web["channel"] == "website"
    assert "hỗ trợ ngay" in resp_web["full_text"].lower() or "sđt" in resp_web["full_text"].lower()

    # 4. TikTok: Ultra concise strictly under 140 characters, directs to inbox
    resp_tt = copilot.generate_response(msg, product_id="calcium_complex", channel="tiktok")
    assert resp_tt["channel"] == "tiktok"
    assert len(resp_tt["full_text"]) <= 140
    assert "inbox" in resp_tt["full_text"].lower()

def test_clinical_red_flag_detection():
    # 1. Sỏi thận
    res_calci = copilot.detect_red_flags("Bác tôi 65 tuổi có tiền sử sỏi thận dùng canxi này được không?")
    assert res_calci["has_red_flag"] is True
    assert res_calci["pharmacist_escalation"] is True
    assert any("sỏi thận" in f for f in res_calci["flags"])

    # 2. Thuốc an thần theo đơn
    res_sleep = copilot.detect_red_flags("Tôi đang uống Seduxen và Rotunda mỗi tối, có dùng chung Sleep Well được không?")
    assert res_sleep["has_red_flag"] is True
    assert res_sleep["pharmacist_escalation"] is True
    assert any("thuốc ngủ" in f or "an thần" in f for f in res_sleep["flags"])

    # 3. Tan máu bẩm sinh Thalassemia
    res_iron = copilot.detect_red_flags("Bé nhà tôi mang gen Thalassemia thiếu máu có bổ sung sắt FerroActive được không?")
    assert res_iron["has_red_flag"] is True
    assert any("Thalassemia" in f for f in res_iron["flags"])

    # 4. Chống đông máu
    res_omega = copilot.detect_red_flags("Bố tôi đang uống thuốc chống đông máu Warfarin sau đặt stent, uống Ultimate Omega 3 được không?")
    assert res_omega["has_red_flag"] is True
    assert any("chống đông máu" in f for f in res_omega["flags"])

def test_competitor_comparison_engine():
    # 1. Calcium vs Corbiere
    resp_corbiere = copilot.generate_response(
        "Canxi Corbiere dạng ống bên kia rẻ hơn nhiều sao bên bạn đắt vậy?",
        product_id="calcium_complex",
        channel="zalo"
    )
    assert resp_corbiere["competitor_comparison"] is not None
    assert "Corbiere" in resp_corbiere["competitor_comparison"]["competitor_name"]
    assert "K2" in resp_corbiere["full_text"] or "dẫn truyền" in resp_corbiere["full_text"]

    # 2. Beauty Collagen vs Herbalife / Vital Proteins
    resp_col = copilot.generate_response(
        "Herbalife và Vital Proteins nổi tiếng thế giới, sao tôi phải mua của bạn?",
        product_id="beauty_collagen",
        channel="facebook"
    )
    assert resp_col["competitor_comparison"] is not None
    assert "Herbalife" in resp_col["competitor_comparison"]["competitor_name"]
    assert "Sensoril" in resp_col["competitor_comparison"]["permissible_talking_points"]

    # 3. Ultimate Omega 3 vs Cheap 1000mg
    resp_om3 = copilot.generate_response(
        "Loại dầu cá kia cũng ghi 1000mg mà rẻ hơn một nửa",
        product_id="ultimate_omega3",
        channel="website"
    )
    assert resp_om3["competitor_comparison"] is not None
    assert "EPA" in resp_om3["competitor_comparison"]["permissible_talking_points"]

def test_shortcuts_search():
    # Test specific shortcuts
    sc_calci = copilot.search_playbook(shortcut="/calci-gia")
    assert len(sc_calci) > 0
    assert sc_calci[0]["product_id"] == "calcium_complex"

    sc_colp = copilot.search_playbook(shortcut="/colp-gia")
    assert len(sc_colp) > 0
    assert sc_colp[0]["product_id"] == "beauty_collagen"

    sc_omega = copilot.search_playbook(shortcut="/omega3-gia")
    assert len(sc_omega) > 0
    assert sc_omega[0]["product_id"] == "ultimate_omega3"

    sc_sleep = copilot.search_playbook(shortcut="/sleep-gia")
    assert len(sc_sleep) > 0

    sc_ferro = copilot.search_playbook(shortcut="/ferro-gia")
    assert len(sc_ferro) > 0

def test_qa_tl_cskh_003_compliance():
    # Compliant response should pass
    resp = copilot.generate_response("Canxi này giá bao nhiêu?", product_id="calcium_complex", channel="facebook")
    assert resp["qa_compliance"]["score"] >= 80
    assert resp["qa_compliance"]["status"] == "PASS"

    # Evaluator penalizes prohibited terms
    eval_bad = copilot._evaluate_qa_compliance(
        "Uống canxi này cam kết 100% chữa khỏi dứt điểm loãng xương",
        {"has_red_flag": False},
        {"step_1_direct_answer": "...", "step_2_followup_question": "..."}
    )
    assert eval_bad["score"] < 80
    assert eval_bad["status"] == "NEEDS_REVIEW"
    assert any("chữa khỏi" in n or "dứt điểm" in n for n in eval_bad["notes"])

def test_api_endpoints():
    # 1. GET /api/vistafa/channels
    r = client.get("/api/vistafa/channels")
    assert r.status_code == 200
    assert "facebook" in r.json()["channels"]

    # 2. GET /api/vistafa/products
    r = client.get("/api/vistafa/products")
    assert r.status_code == 200
    assert "calcium_complex" in r.json()["products"]

    # 3. GET /api/vistafa/playbook
    r = client.get("/api/vistafa/playbook?product_id=calcium_complex&limit=5")
    assert r.status_code == 200
    assert len(r.json()["entries"]) <= 5

    # 4. GET /api/vistafa/shortcuts
    r = client.get("/api/vistafa/shortcuts?product_id=sleep_well")
    assert r.status_code == 200
    assert len(r.json()["shortcuts"]) > 0

    # 5. GET /api/vistafa/competitors
    r = client.get("/api/vistafa/competitors?product_id=beauty_collagen")
    assert r.status_code == 200
    assert len(r.json()["matrix"]) > 0

    # 6. POST /api/vistafa/chat-copilot
    r = client.post("/api/vistafa/chat-copilot", json={
        "customer_message": "Cho mình hỏi giá và cách uống viên ngủ ngon",
        "product_id": "sleep_well",
        "channel": "zalo"
    })
    assert r.status_code == 200
    res_data = r.json()["data"]
    assert res_data["product_id"] == "sleep_well"
    assert res_data["channel"] == "zalo"
    assert "Sleep Well" in res_data["full_text"]

def test_live_conversation_and_escalation_workflow():
    # 1. Get all live inbound conversations
    r = client.get("/api/vistafa/conversations")
    assert r.status_code == 200
    convs = r.json()["conversations"]
    assert len(convs) >= 5
    assert any(c["id"] == "CONV-FB-01" for c in convs)

    # 2. Get specific thread with real-time AI recommendation
    r2 = client.get("/api/vistafa/conversations/CONV-FB-01")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["conversation"]["customer_name"] == "Mai Lan"
    assert d2["ai_recommendation"] is not None
    assert d2["ai_recommendation"]["product_id"] == "beauty_collagen"

    # 3. Add message to thread
    r3 = client.post("/api/vistafa/conversations/CONV-FB-01/messages", json={
        "sender": "agent",
        "text": "Dạ thông thường sau 2-4 tuần uống đều đặn mỗi sáng da sẽ sáng và đủ ẩm hơn nhiều chị nhé."
    })
    assert r3.status_code == 200
    assert len(r3.json()["conversation"]["messages"]) >= 4

    # 4. Pharmacist handoff
    r4 = client.post("/api/vistafa/conversations/CONV-ESC-05/escalate", json={
        "reason": "Phát hiện dùng thuốc ngủ Seduxen theo đơn",
        "notes": "Bác 68 tuổi mất ngủ lâu năm",
        "pharmacist_name": "DS. Lâm Sàng Trực Ban"
    })
    assert r4.status_code == 200
    assert r4.json()["ticket"]["assigned_pharmacist"] == "DS. Lâm Sàng Trực Ban"

    # 5. Convert order
    r5 = client.post("/api/vistafa/conversations/CONV-FB-01/convert", json={
        "sku": "beauty_collagen",
        "quantity": 2,
        "delivery_address": "Số 25 Nguyễn Trãi, Hà Nội",
        "total_price": "480.000đ"
    })
    assert r5.status_code == 200
    assert r5.json()["order"]["sku"] == "beauty_collagen"

def test_dynamic_customer_simulation_and_triage():
    # Simulate customer sending a high-risk clinical inquiry
    r = client.post("/api/vistafa/conversations/CONV-FB-01/messages", json={
        "sender": "customer",
        "text": "Bác năm nay 72 tuổi đang uống thuốc huyết áp Amlodipine và bị sỏi thận 12mm thì uống canxi này được không?"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True

    conv = data["conversation"]
    # 1. Verify dynamic extraction
    assert conv["clinical_profile"]["age"] == 72
    assert "sỏi thận" in conv["clinical_profile"]["notes"].lower()
    assert "amlodipine" in conv["clinical_profile"]["notes"].lower()
    assert conv["product_id"] == "calcium_complex"
    assert conv["status"] == "REQUIRES_PHARMACIST"
    assert conv["lead_priority"] == "URGENT"

    # 2. Verify AI Copilot recommendation
    ai_rec = data["ai_recommendation"]
    assert ai_rec is not None
    assert ai_rec["red_flags"]["has_red_flag"] is True
    assert ai_rec["red_flags"]["pharmacist_escalation"] is True
    assert any("sỏi thận" in f or "12mm" in f for f in ai_rec["red_flags"]["flags"])
    assert "sỏi" in ai_rec["four_steps"]["step_1_direct_answer"].lower()
    assert "Dược sĩ" in ai_rec["four_steps"]["step_4_action_cta"]

    # 3. Zero emojis in new response
    assert len(EMOJI_PATTERN.findall(ai_rec["full_text"])) == 0

def test_pancake_api_integration():
    from modules.pancake_client import get_pancake_client
    client_pc = get_pancake_client()
    assert client_pc.api_key == "57d1deca6acd500213ef572b272d2852"
    assert client_pc.shop_id == 1943149040

    r = client.get("/api/pancake/status")
    assert r.status_code == 200
    data = r.json()
    assert "connected" in data
    assert "api_key_valid" in data


def test_pancake_instagram_conversation_and_adaptation():
    # 1. Verify CONV-PC-IG-06 exists in live conversations
    r = client.get("/api/vistafa/conversations")
    assert r.status_code == 200
    convs = r.json()["conversations"]
    pc_conv = next((c for c in convs if c["id"] == "CONV-PC-IG-06"), None)
    assert pc_conv is not None
    assert pc_conv["channel"] == "instagram"
    assert pc_conv["customer_name"] == "fptu_muayclub"
    assert pc_conv["pancake_metadata"]["shop_id"] == 1943149040

    # 2. Verify AI Copilot adaptation for Instagram channel
    resp = copilot.generate_response(
        "Bên mình có canxi nào phục hồi cơ khớp sau tập võ không?",
        product_id="calcium_complex",
        channel="instagram"
    )
    assert resp["channel"] == "instagram"
    assert len(EMOJI_PATTERN.findall(resp["full_text"])) == 0
    assert "Direct" in resp["four_steps"]["step_4_action_cta"] or "SĐT" in resp["four_steps"]["step_4_action_cta"]


def test_pancake_pages_and_webhook_endpoints():
    # 1. GET /api/pancake/pages
    r = client.get("/api/pancake/pages")
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert "pages" in data or "error" in data

    # 2. POST /api/webhook/pancake
    r_wh = client.post("/api/webhook/pancake", json={
        "event": "message_created",
        "page_id": "igo_17841436773289596",
        "timestamp": 1729400000
    })
    assert r_wh.status_code == 200
    assert r_wh.json()["status"] == "ok"





