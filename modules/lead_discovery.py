import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from modules.claims_hub import get_product_by_sku, get_active_claims

logger = logging.getLogger("dion.lead_discovery")
LEADS_PATH = Path(__file__).resolve().parent.parent / "data" / "b2b_leads.json"

def load_leads_data() -> List[Dict[str, Any]]:
    if not LEADS_PATH.exists():
        return []
    with open(LEADS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("leads", [])

def save_leads_data(leads: List[Dict[str, Any]]) -> bool:
    try:
        hospitals_map = {}
        if LEADS_PATH.exists():
            try:
                with open(LEADS_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    hospitals_map = existing.get("hospitals_map", {})
            except Exception:
                pass
        with open(LEADS_PATH, "w", encoding="utf-8") as f:
            json.dump({"leads": leads, "hospitals_map": hospitals_map}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving leads: {e}")
        return False

def update_lead_status(lead_id: str, new_status: str, assigned_to: Optional[str] = None) -> bool:
    leads = load_leads_data()
    updated = False
    for l in leads:
        if l.get("lead_id") == lead_id:
            l["status"] = new_status
            if assigned_to:
                l["assigned_to"] = assigned_to
            updated = True
            break
            
    if updated:
        return save_leads_data(leads)
    return False

def load_hospitals_map() -> Dict[str, Dict[str, List[str]]]:
    if not LEADS_PATH.exists():
        return {}
    with open(LEADS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("hospitals_map", {})

def filter_leads(
    province: str = "Tất cả",
    district: str = "Tất cả",
    hospital: str = "Tất cả",
    max_distance: int = 0,
    lead_type: str = "Tất cả",
    status: str = "Tất cả",
    min_fit_score: int = 0,
    search_keyword: str = "",
    only_new: bool = False
) -> List[Dict[str, Any]]:
    leads = load_leads_data()
    filtered = []
    keyword_clean = search_keyword.strip().lower()
    
    for orig_item in leads:
        item = dict(orig_item) # tạo bản sao để tính cự ly động
        match_prov = (province == "Tất cả") or (item.get("province") == province)
        match_dist = (district == "Tất cả") or (item.get("district") == district)
        
        match_hosp = True
        if hospital != "Tất cả":
            hosp_clean = hospital.lower()
            lead_hosp = (item.get("target_hospital") or "").lower()
            lead_fac = (item.get("nearby_facility") or "").lower()
            
            # Khớp từ khóa cốt lõi (Bạch Mai, Lão Khoa, Từ Dũ, Dinh Dưỡng, Phụ Sản...)
            keywords = [w for w in hosp_clean.replace("(", " ").replace(")", " ").split() if len(w) > 3 and w not in ["bệnh", "viện", "trung", "ương", "quốc", "khoa", "thành", "phố"]]
            has_kw = any(k in lead_hosp or k in lead_fac for k in keywords) if keywords else False
            
            if (hosp_clean in lead_hosp) or (lead_hosp in hosp_clean) or has_kw:
                match_hosp = True
                item["target_hospital"] = hospital
            elif match_dist and match_prov:
                # Nếu cùng quận thì nằm trong cự ly mở rộng của bệnh viện này
                match_hosp = True
                base_dist = item.get("distance_meters", 800) + 350
                item["target_hospital"] = hospital
                item["distance_meters"] = base_dist
                mins = max(2, round(base_dist / 80))
                item["distance_text"] = f"{base_dist}m · {mins} phút đi bộ" if base_dist <= 800 else f"{round(base_dist/1000, 1)}km · {max(2, round(base_dist/350))} phút xe máy"
            else:
                match_hosp = False
                
        match_radius = True if max_distance <= 0 else (item.get("distance_meters", 9999) <= max_distance)
        match_type = (lead_type == "Tất cả") or (item.get("type") == lead_type)
        match_status = (status == "Tất cả") or (item.get("status") == status)
        match_score = item.get("fit_score", 0) >= min_fit_score
        match_new = True if not only_new else item.get("is_new_opened", False)
        
        match_kw = True
        if keyword_clean:
            searchable_text = f"{item.get('name', '')} {item.get('address', '')} {item.get('phone', '')} {item.get('target_hospital', '')} {' '.join(item.get('categories', []))}".lower()
            match_kw = keyword_clean in searchable_text
            
        if match_prov and match_dist and match_hosp and match_radius and match_type and match_status and match_score and match_kw and match_new:
            filtered.append(item)
            
    # Sắp xếp lộ trình theo khoảng cách gần nhất
    if hospital != "Tất cả" or max_distance > 0:
        filtered.sort(key=lambda x: x.get("distance_meters", 9999))
        
    return filtered

def group_by_parent_chain(leads: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    groups: Dict[str, List[Dict[str, Any]]] = {"Độc lập / Chưa gom nhóm": []}
    for l in leads:
        parent = l.get("parent_chain")
        if parent:
            if parent not in groups:
                groups[parent] = []
            groups[parent].append(l)
        else:
            groups["Độc lập / Chưa gom nhóm"].append(l)
    return groups

def get_lead_by_id(lead_id: str) -> Optional[Dict[str, Any]]:
    leads = load_leads_data()
    for l in leads:
        if l.get("lead_id") == lead_id:
            return l
    return None

def compute_lead_ai_recommendation(lead_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tính toán mặt hàng nên chào (Hero SKU), lý do phù hợp và điểm số
    dựa trên khoa phòng bệnh viện lân cận, loại hình và tệp khách hàng.
    """
    target_hosp = (lead_dict.get("target_hospital") or lead_dict.get("nearby_facility") or "").lower()
    lead_type = lead_dict.get("type", "Nhà thuốc tư nhân")
    
    if any(k in target_hosp for k in ["phụ sản", "từ dũ", "hùng vương", "mekong", "mỹ đức", "bưu điện"]):
        sku = "DION-CAL-MOM"
        sku_name = "Canxi Tảo Đỏ DION Cal-Mom Plus & D3 K2 (Hero SKU)"
        reason = f"Cự ly gần {lead_dict.get('target_hospital') or 'cơ sở y tế Sản khoa'}, tệp mẹ bầu & sau sinh cao (>50% đơn vi chất). Khách hàng tìm kiếm Canxi sinh học không nóng, không sỏi thận và Sắt hữu cơ êm bụng."
        score = 96
        grade = "A+"
    elif any(k in target_hosp for k in ["nhi", "nhi đồng", "dinh dưỡng", "trẻ em"]):
        sku = "DION-D3-1000"
        sku_name = "Vitamin D3 1000IU Nhỏ Giọt Hấp Thu Cao (Hero SKU)"
        reason = f"Vị trí chiến lược gần {lead_dict.get('target_hospital') or 'viện Nhi khoa'}, lượng mẹ bỉm sữa tìm vi chất tinh khiết cho trẻ sơ sinh và trẻ nhỏ rất cao. Dạng nhỏ giọt tiện lợi là mặt hàng quay vòng nhanh."
        score = 95
        grade = "A+"
    elif any(k in target_hosp for k in ["huyết học"]):
        sku = "DION-FE-PLUS"
        sku_name = "Sắt Sinh Học Hữu Cơ DION Fero-Plus & Axit Folic (Hero SKU)"
        reason = f"Gần {lead_dict.get('target_hospital')}, tệp bệnh nhân cần bổ máu, tăng hồng cầu; Sắt sinh học Fero-Plus không gây tanh, không táo bón là giải pháp thay thế vượt trội."
        score = 95
        grade = "A+"
    elif any(k in target_hosp for k in ["bạch mai", "chợ rẫy", "lão khoa", "108", "115", "thống nhất", "quân y 103", "việt đức", "xanh pôn", "việt tiệp", "đa khoa tw"]):
        sku = "DION-CAL-MOM"
        sku_name = "Canxi Tảo Đỏ DION Cal-Mom Plus & D3 K2 (Hero SKU)"
        reason = f"Gần tuyến viện đa khoa & lão khoa {lead_dict.get('target_hospital')}, lượng lớn người cao tuổi điều trị thoái hóa xương khớp, loãng xương và phục hồi thể trạng."
        score = 94
        grade = "A+"
    elif lead_type == "Chuỗi nhà thuốc" or lead_dict.get("parent_chain"):
        sku = "COMPANY_PORTFOLIO"
        sku_name = "Gói Danh Mục Toàn Diện & Ký Gửi Tủ Kệ Doanh Nghiệp"
        reason = f"Chuỗi nhà thuốc quy mô lớn ({lead_dict.get('parent_chain') or 'Hệ thống chuỗi'}), tiêu chuẩn quầy kệ cao; phù hợp đàm phán phân phối trọn bộ Canxi - Sắt - D3 với chính sách chiết khấu bậc thang."
        score = 92
        grade = "A"
    else:
        sku = "DION-CAL-MOM"
        sku_name = "Canxi Tảo Đỏ DION Cal-Mom Plus & D3 K2 (Hero SKU)"
        reason = "Sản phẩm mũi nhọn đạt chuẩn GPP dễ bán nhất tại các quầy thuốc bán lẻ, đáp ứng đối tượng rộng từ thanh thiếu niên đến phụ nữ và người lớn tuổi."
        score = 88
        grade = "A"

    return {
        "recommended_sku": sku,
        "recommended_sku_name": sku_name,
        "ai_match_reason": reason,
        "fit_score": score,
        "fit_grade": grade
    }


def add_new_lead(lead_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Thêm một điểm bán mới vào cơ sở dữ liệu thực địa."""
    leads = load_leads_data()
    prov = lead_dict.get("province", "Hà Nội")
    prov_code = "HN" if "Hà Nội" in prov else ("HCM" if "Hồ Chí Minh" in prov else "TINH")
    max_id = 1
    for l in leads:
        lid = l.get("lead_id", "")
        if lid.startswith(f"LD-{prov_code}-"):
            try:
                num = int(lid.split("-")[-1])
                if num >= max_id:
                    max_id = num + 1
            except ValueError:
                pass
    
    new_id = lead_dict.get("lead_id") or f"LD-{prov_code}-{max_id:03d}"
    lead_dict["lead_id"] = new_id
    lead_dict["status"] = lead_dict.get("status", "NEW")
    
    # Tự động tính toán mặt hàng nên chào và điểm phù hợp nếu chưa có
    rec = compute_lead_ai_recommendation(lead_dict)
    if "recommended_sku" not in lead_dict:
        lead_dict["recommended_sku"] = rec["recommended_sku"]
        lead_dict["recommended_sku_name"] = rec["recommended_sku_name"]
        lead_dict["ai_match_reason"] = rec["ai_match_reason"]
        
    lead_dict["fit_score"] = int(lead_dict.get("fit_score", rec["fit_score"]))
    lead_dict["fit_grade"] = rec["fit_grade"] if "fit_grade" not in lead_dict else lead_dict["fit_grade"]
    lead_dict["trust_score"] = int(lead_dict.get("trust_score", 90))
    lead_dict["contact_score"] = int(lead_dict.get("contact_score", 85))
    lead_dict["intent_score"] = int(lead_dict.get("intent_score", 82))
    lead_dict["is_new_opened"] = bool(lead_dict.get("is_new_opened", False))
    
    if "distance_meters" not in lead_dict:
        lead_dict["distance_meters"] = 650
        lead_dict["distance_text"] = "650m · 8 phút đi bộ"
    if "nearby_facility" not in lead_dict and lead_dict.get("target_hospital"):
        lead_dict["nearby_facility"] = f"Gần {lead_dict['target_hospital']} ({lead_dict.get('distance_text', '800m')})"

    leads.insert(0, lead_dict)
    save_leads_data(leads)
    return lead_dict


def import_leads_bulk(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Nhập danh bạ nhà thuốc hàng loạt từ file Excel / CSV."""
    leads = load_leads_data()
    existing_phones = {str(l.get("phone", "")).strip().replace(" ", "") for l in leads if l.get("phone")}
    existing_names = {(str(l.get("name", "")).strip().lower(), str(l.get("province", "")).strip().lower()) for l in leads}
    
    added = []
    skipped = 0
    
    for item in items:
        name = str(item.get("name", "")).strip()
        if not name:
            skipped += 1
            continue
        phone = str(item.get("phone", "")).strip().replace(" ", "")
        prov = str(item.get("province", "Hà Nội")).strip()
        name_key = (name.lower(), prov.lower())
        
        if phone and phone in existing_phones:
            skipped += 1
            continue
        if name_key in existing_names:
            skipped += 1
            continue
            
        saved = add_new_lead(item)
        added.append(saved)
        if phone:
            existing_phones.add(phone)
        existing_names.add(name_key)
        
    return {
        "success": True,
        "status": "success",
        "imported_count": len(added),
        "skipped_duplicates": skipped,
        "added_count": len(added),
        "skipped_count": skipped,
        "total_leads": len(load_leads_data()),
        "total_leads_now": len(load_leads_data())
    }


def generate_b2b_outreach_pitch(lead_id: str, recommended_sku: str = "DION-D3-1000") -> Dict[str, Any]:
    """
    TÍNH NĂNG DOANH NGHIỆP: Tự động phân tích hồ sơ đối tác và sinh kịch bản chào hàng 1-1 (Fallback Rule-based).
    Hỗ trợ cả 3 kênh: Email trang trọng, Tin nhắn Zalo ngắn gọn và Kịch bản gọi điện / gặp quầy.
    """
    lead = get_lead_by_id(lead_id)
    if not lead:
        return {"error": "Không tìm thấy thông tin đối tác"}
        
    if recommended_sku == "COMPANY_PORTFOLIO":
        prod = {"name": "Hồ sơ Năng lực Doanh nghiệp & Toàn bộ Danh mục TPBVSK DION Healthcare", "sku": "DION-PORTFOLIO-2026"}
    else:
        prod = get_product_by_sku(recommended_sku)
        if not prod:
            prod = {"name": "Danh mục Thực phẩm Bảo vệ Sức khỏe DION", "sku": recommended_sku}
        
    lead_name = lead["name"]
    lead_type = lead.get("type", "Nhà thuốc tư nhân")
    parent = lead.get("parent_chain")
    target_hosp = lead.get("target_hospital") or lead.get("nearby_facility") or "cơ sở y tế trọng điểm"
    
    # Chiến lược tiếp cận theo phân khúc đối tác
    if "Mẹ & Bé" in lead_type or (parent and "Cưng" in parent):
        strategy = "Chiến lược Mẹ & Bé: Đẩy mạnh dòng Canxi sinh học & Sắt hữu cơ êm dịu dạ dày cho thai phụ"
        target_department = "Phòng Thu Mua Ngành Hàng Dinh Dưỡng Mẹ & Bé"
        angle = "Tỷ lệ hấp thu vượt trội, không gây nóng trong hay táo bón, bao bì đạt chuẩn Cục ATTP tạo uy tín tại quầy kệ"
    elif "Chuỗi" in lead_type or parent in ["FPT Long Châu", "Pharmacity", "An Khang (MWG)"]:
        strategy = f"Chiến lược Chuỗi Bán Lẻ: Đàm phán tập trung với Hội sở {parent} về chính sách SKU độc quyền"
        target_department = f"Ban Giám Đốc Mua Hàng & Phát Triển Sản Phẩm Mới — {parent}"
        angle = "Chiết khấu thương mại hấp dẫn, cung ứng ổn định 100% giấy phép Cục ATTP, hỗ trợ đào tạo Dược sĩ"
    else:
        strategy = "Chiến lược Nhà Thuốc Tư Nhân: Hỗ trợ quầy trưng bày, tư vấn chuyên môn và chương trình tích lũy"
        target_department = "Dược sĩ Phụ trách Chuyên môn & Chủ Nhà Thuốc"
        angle = "Dược chất sinh học dễ bán, phản hồi người dùng tích cực, chính sách đổi trả và kệ trưng bày linh hoạt"
        
    email_subject = f"[DION HEALTHCARE] Đề xuất Hợp tác Phân phối Danh mục {prod['name']} tới {lead_name}"
    
    email_body = f"""Kính gửi: {target_department} — {lead_name},

Lời đầu tiên, DION Healthcare xin gửi lời chào trân trọng và lời chúc phát triển thịnh vượng tới Quý đơn vị.

Qua quá trình nghiên cứu địa bàn và danh mục sản phẩm của {lead_name} tại {lead.get('address')} ({target_hosp}), chúng tôi nhận thấy Quý đơn vị có thế mạnh vượt trội trong nhóm khách hàng chăm sóc sức khỏe chủ động và vi chất dinh dưỡng.

DION trân trọng đề xuất phương án hợp tác phân phối dòng sản phẩm:
• Sản phẩm: {prod['name']} (Mã SKU: {prod.get('sku')})
• Đặc điểm nổi bật: {angle}.
• Hồ sơ pháp lý: Đã được Cục An Toàn Thực Phẩm cấp Giấy tiếp nhận đăng ký bản công bố sản phẩm, đạt chuẩn GMP.

QUYỀN LỢI DÀNH RIÊNG CHO {lead_name.upper()}:
1. Chính sách chiết khấu trực tiếp và hỗ trợ kích hoạt điểm bán (POSM, tủ kệ trưng bày).
2. Tài liệu đào tạo tư vấn chuẩn y khoa cho đội ngũ Dược sĩ đứng quầy.
3. Cam kết đồng hành cùng các chiến dịch truyền thông thương hiệu khu vực {lead.get('district')}.

Chúng tôi rất mong có cơ hội được gửi bảng báo giá chi tiết và mẫu sản phẩm trải nghiệm tới Quý đơn vị trong tuần này.

Trân trọng cảm ơn,
Đội ngũ Phát triển Đối tác B2B — DION Healthcare AI
Hotline B2B: 0903 112 456 | Email: b2b@dion.healthcare.ai
"""

    zalo_msg = (
        f"Dạ em chào Dược sĩ/Chủ quầy {lead_name}! Em là Trình dược viên phụ trách khu vực {lead.get('district')} từ DION Healthcare AI.\n\n"
        f"Bên em đang triển khai chương trình Hợp tác phân phối dòng {prod['name']} (Chuẩn GMP Cục ATTP) cho các nhà thuốc trọng điểm gần {target_hosp}.\n\n"
        f"🎁 Quyền lợi dành riêng cho quầy mình:\n"
        f"- Chiết khấu trực tiếp hấp dẫn ngay từ đơn hàng đầu tiên.\n"
        f"- Tặng kệ trưng bày POSM cao cấp + Hỗ trợ gửi mẫu trải nghiệm miễn phí.\n"
        f"- Cam kết thu hồi/đổi trả 100% nếu không ra hàng.\n\n"
        f"Em xin phép gửi Dược sĩ bảng báo giá chi tiết và catalogue qua Zalo này nhé ạ!"
    )

    call_script = (
        f"📞 KỊCH BẢN GỌI ĐIỆN / GẶP TRỰC TIẾP TẠI QUẦY:\n"
        f"1. LỜI CHÀO & MỞ ĐẦU:\n"
        f"   'Em chào Dược sĩ ạ! Em là [Tên], đại diện kinh doanh từ DION Healthcare phụ trách khu vực {lead.get('district')}. "
        f"   Em thấy quầy mình có lượng khách mẹ bầu và chăm sóc sức khỏe rất tốt ở gần {target_hosp} nên em muốn trao đổi nhanh 1 phút về dòng {prod['name']}.'\n\n"
        f"2. ĐIỂM NHẤN SẢN PHẨM (USP 10 GIÂY):\n"
        f"   'Dòng này bên em ứng dụng công nghệ vi chất sinh học chuẩn châu Âu, {angle}, hồ sơ công bố Cục ATTP đầy đủ nên khách hỏi mua theo đơn là quầy tư vấn rất tự tin.'\n\n"
        f"3. XỬ LÝ TỪ CHỐI THƯỜNG GẶP:\n"
        f"   • Nếu bảo 'Quầy có bán dòng khác quen rồi':\n"
        f"     -> 'Dạ em hiểu quầy mình đã có sẵn sản phẩm. Dòng DION bên em hướng tới phân khúc khách khó tính cần giải pháp êm bụng không nóng trong, bên em có tặng kèm mẫu trải nghiệm và bảo hành đổi trả 100% để quầy an tâm kiểm chứng nhu cầu khách ạ.'\n"
        f"   • Nếu bảo 'Hàng mới sợ chưa ai mua':\n"
        f"     -> 'Dạ bên em đang chạy truyền thông khu vực {lead.get('district')} và hỗ trợ kệ POSM quầy thuốc ngay tuần này để kéo khách lại quầy ạ.'\n\n"
        f"4. CHỐT BƯỚC TIẾP THEO:\n"
        f"   'Em xin phép gửi tặng Dược sĩ 1 hộp mẫu trải nghiệm kèm bảng chiết khấu đại lý để Dược sĩ xem thử nhé ạ!'"
    )

    return {
        "lead_id": lead_id,
        "lead_name": lead_name,
        "strategy": strategy,
        "target_department": target_department,
        "subject": email_subject,
        "pitch_body": email_body,
        "zalo_message": zalo_msg,
        "call_script": call_script,
        "recommended_sku": prod["name"],
        "is_ai_generated": False
    }


async def generate_b2b_outreach_pitch_ai(lead_id: str, recommended_sku: str = "DION-D3-1000") -> Dict[str, Any]:
    """Sinh kịch bản chào hàng 1-1 tối ưu bằng Gemini 3.8 Flash, tự động fallback an toàn."""
    base_result = generate_b2b_outreach_pitch(lead_id, recommended_sku=recommended_sku)
    if "error" in base_result:
        return base_result

    lead = get_lead_by_id(lead_id)
    if not lead:
        return base_result

    try:
        from dotenv import load_dotenv
        load_dotenv()
        from modules.chat.llm_gateway import get_llm_gateway
        gw = get_llm_gateway()
        gw.validate_configuration()
    except Exception as e:
        logger.info(f"AI Gateway offline or not configured: {e}. Using rule-based pitch.")
        return base_result

    prod = get_product_by_sku(recommended_sku) if recommended_sku != "COMPANY_PORTFOLIO" else {"name": "Hồ sơ Năng lực Toàn bộ Danh mục DION", "sku": "PORTFOLIO"}
    prod_name = prod.get("name", recommended_sku) if prod else recommended_sku
    
    prompt = f"""Bạn là Giám đốc Phát triển Đối tác B2B của DION Healthcare AI.
Hãy phân tích hồ sơ nhà thuốc mục tiêu sau và biên soạn bộ kịch bản tiếp cận 1-1 chuyên nghiệp:

[THÔNG TIN ĐỐI TÁC MỤC TIÊU]
- Tên điểm bán: {lead.get('name')}
- Loại hình: {lead.get('type')} (Chuỗi: {lead.get('parent_chain') or 'Độc lập'})
- Địa chỉ: {lead.get('address')}
- Vị trí y tế lân cận: {lead.get('nearby_facility') or lead.get('target_hospital')}
- Tín hiệu nhu cầu thực tế: {lead.get('intent_signals')}

[SẢN PHẨM MŨI NHỌN CHÀO HÀNG]
- Tên sản phẩm: {prod_name}
- Chuẩn mực: Đạt chuẩn GMP, Số tiếp nhận Cục An Toàn Thực Phẩm - Bộ Y Tế.

YÊU CẦU ĐẦU RA (Trả về định dạng JSON thuần túy, không kèm markdown khác):
{{
  "strategy": "Chiến lược tiếp cận ngắn gọn (1-2 câu)",
  "target_department": "Chức danh người nhận thư/trao đổi",
  "subject": "Tiêu đề email chào hàng B2B hấp dẫn",
  "pitch_body": "Nội dung thư Email B2B trang trọng, đầy đủ quyền lợi chiết khấu, POSM và đề xuất gửi mẫu thử",
  "zalo_message": "Tin nhắn Zalo ngắn gọn (dưới 150 từ), trực diện, thân thiện gửi Dược sĩ / Chủ quầy",
  "call_script": "Kịch bản Trình dược viên gọi điện / gặp trực tiếp: Lời chào -> USP 10 giây -> Xử lý từ chối nếu đang bán hãng khác -> Chốt gửi mẫu trải nghiệm"
}}"""

    try:
        res = await gw.generate(
            prompt=prompt,
            system_instruction="Bạn là chuyên gia B2B Dược phẩm. Chỉ trả về JSON hợp lệ duy nhất.",
            temperature=0.3,
            max_output_tokens=1024,
        )
        text = res.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        ai_data = json.loads(text)
        return {
            "lead_id": lead_id,
            "lead_name": lead.get("name"),
            "strategy": ai_data.get("strategy") or base_result["strategy"],
            "target_department": ai_data.get("target_department") or base_result["target_department"],
            "subject": ai_data.get("subject") or base_result["subject"],
            "pitch_body": ai_data.get("pitch_body") or base_result["pitch_body"],
            "zalo_message": ai_data.get("zalo_message") or base_result["zalo_message"],
            "call_script": ai_data.get("call_script") or base_result["call_script"],
            "recommended_sku": prod_name,
            "is_ai_generated": True
        }
    except Exception as e:
        logger.warning(f"Error in generate_b2b_outreach_pitch_ai: {e}. Fallback to rule-based.")
        return base_result


async def analyze_lead_ai(lead_id: str) -> Dict[str, Any]:
    """AI phân tích SWOT và chân dung khách hàng cho Trình dược viên đi thị trường."""
    lead = get_lead_by_id(lead_id)
    if not lead:
        return {"error": "Không tìm thấy thông tin điểm bán"}

    lead_name = lead.get("name")
    lead_type = lead.get("type")
    address = lead.get("address")
    facility = lead.get("nearby_facility") or lead.get("target_hospital") or "Khu dân cư"
    fit_score = lead.get("fit_score", 85)
    
    # Rule-based fallback SWOT & ICP structure
    swot = {
        "strengths": [
            f"Vị trí chiến lược: {facility}",
            f"Độ tin cậy dữ liệu: Đạt chuẩn GPP ({lead.get('gpp_info', {}).get('status', 'Đã thẩm định')})",
            f"Tín hiệu thị trường: {lead.get('intent_signals', 'Điểm bán có nhu cầu nhập hàng')}"
        ],
        "weaknesses": [
            "Có thể đã có một số sản phẩm nhập ngoại hoặc thương hiệu lâu năm tại quầy kệ",
            "Cần chính sách hỗ trợ tủ kệ POSM và chương trình chiết khấu rõ ràng ở đơn hàng đầu"
        ],
        "opportunities": [
            f"Khai thác tệp bệnh nhân sản/nhi & đa khoa từ {facility}",
            "Nhu cầu gia tăng về Canxi sinh học không nóng & Sắt hữu cơ không táo bón",
            "Mở rộng biên độ lợi nhuận & chương trình hỗ trợ trưng bày POSM từ DION"
        ],
        "threats": [
            "Đã có một số nhãn hàng truyền thống chiếm giữ mặt bằng tủ kệ trước",
            "Chủ quầy thận trọng với nhãn hàng mới nếu chưa có đầy đủ hồ sơ kiểm nghiệm lâm sàng"
        ]
    }

    base_insights = {
        "lead_id": lead_id,
        "lead_name": lead_name,
        "icp_summary": f"Điểm bán {lead_type} tiềm năng cao tại {lead.get('district')}, tệp khách hàng hướng tới chăm sóc sức khỏe gia đình và mẹ bầu nhờ cự ly gần {facility}.",
        "icp_rating": f"Hạng A (Điểm phù hợp {fit_score}/100)",
        "strengths": swot["strengths"],
        "challenges": swot["weaknesses"],
        "swot": swot,
        "entry_angle": "Trình dược viên nên chào hàng vào khung giờ 9h-10h sáng hoặc 14h-15h chiều khi vắng khách, mang theo mẫu trải nghiệm thực tế và tập trung vào ưu điểm êm bụng không táo bón.",
        "action_plan": [
            "Bước 1: Ghé quầy vào khung giờ 9h-10h sáng hoặc 14h-15h chiều để gặp trực tiếp Dược sĩ phụ trách.",
            "Bước 2: Mang theo bộ hồ sơ công bố ĐKSP chuẩn Bộ Y Tế & mẫu thử Canxi Cal-Mom.",
            "Bước 3: Nhấn mạnh giải pháp vi chất không gây táo bón, đối chiếu hồ sơ lâm sàng cho đối tượng quanh bệnh viện.",
            "Bước 4: Đề xuất chính sách chiết khấu đơn đầu và tài trợ vật phẩm trưng bày POSM."
        ],
        "recommended_sku": "DION Cal-Mom Plus & D3 Drops (Phù hợp tệp mẹ bầu và trẻ nhỏ quanh bệnh viện)",
        "estimated_monthly_volume": "15 – 35 hộp/tháng cho các dòng vi chất chủ lực",
        "actionable_tips": "Trình dược viên nên chào hàng vào khung giờ 9h-10h sáng hoặc 14h-15h chiều khi vắng khách, mang theo mẫu trải nghiệm thực tế và tập trung vào ưu điểm êm bụng không táo bón.",
        "generated_by": "DION B2B Expert System (Rule-based Fallback)",
        "is_ai_generated": False
    }

    try:
        from dotenv import load_dotenv
        load_dotenv()
        from modules.chat.llm_gateway import get_llm_gateway
        gw = get_llm_gateway()
        gw.validate_configuration()
    except Exception:
        return base_insights

    prompt = f"""Bạn là Chuyên gia Tư vấn Chiến lược B2B Dược phẩm (Pharma B2B Strategist).
Hãy phân tích hồ sơ điểm bán thực tế sau đây để hỗ trợ Giám đốc kinh doanh và Trình dược viên:

[HỒ SƠ ĐIỂM BÁN]
- Tên: {lead_name}
- Loại hình: {lead_type} (Chuỗi: {lead.get('parent_chain') or 'Độc lập'})
- Địa chỉ: {address}
- Vị trí y tế lân cận: {facility}
- Điểm phù hợp: {fit_score}/100 | Điểm nhu cầu: {lead.get('intent_score', 80)}/100
- Tín hiệu thực tế: {lead.get('intent_signals')}

YÊU CẦU ĐẦU RA (JSON thuần túy, không bọc text ngoài):
{{
  "icp_summary": "Tóm tắt chân dung đối tác & tệp khách hàng mục tiêu của điểm bán này (1-2 câu)",
  "icp_rating": "Đánh giá xếp hạng ICP (VD: Hạng A+ - Ưu tiên hàng đầu)",
  "strengths": ["Thế mạnh vị trí/khách hàng 1", "Thế mạnh 2", "Thế mạnh 3"],
  "challenges": ["Thách thức cạnh tranh 1", "Thách thức 2"],
  "swot": {{
    "strengths": ["Điểm mạnh 1", "Điểm mạnh 2"],
    "weaknesses": ["Điểm yếu 1", "Điểm yếu 2"],
    "opportunities": ["Cơ hội hợp tác 1", "Cơ hội 2"],
    "threats": ["Rào cản từ chối 1", "Rào cản 2"]
  }},
  "entry_angle": "Góc tiếp cận khuyên dùng cho Trình dược viên",
  "action_plan": ["Bước 1: ...", "Bước 2: ...", "Bước 3: ...", "Bước 4: ..."],
  "recommended_sku": "SKU nên chào đầu tiên kèm lý do ngắn gọn",
  "estimated_monthly_volume": "Dự báo dung lượng nhập hàng ước tính / tháng",
  "actionable_tips": "Lời khuyên thực chiến đắt giá cho Trình dược viên khi tới gặp nhà thuốc này"
}}"""

    try:
        res = await gw.generate(
            prompt=prompt,
            system_instruction="Bạn là chuyên gia thẩm định B2B Dược phẩm. Chỉ trả về JSON hợp lệ.",
            temperature=0.3,
            max_output_tokens=1024,
        )
        text = res.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(text)
        return {
            "lead_id": lead_id,
            "lead_name": lead_name,
            "icp_summary": data.get("icp_summary") or base_insights["icp_summary"],
            "icp_rating": data.get("icp_rating") or base_insights["icp_rating"],
            "strengths": data.get("strengths") or base_insights["strengths"],
            "challenges": data.get("challenges") or base_insights["challenges"],
            "swot": data.get("swot") or base_insights["swot"],
            "entry_angle": data.get("entry_angle") or data.get("actionable_tips") or base_insights["entry_angle"],
            "action_plan": data.get("action_plan") or base_insights["action_plan"],
            "recommended_sku": data.get("recommended_sku") or base_insights["recommended_sku"],
            "estimated_monthly_volume": data.get("estimated_monthly_volume") or base_insights["estimated_monthly_volume"],
            "actionable_tips": data.get("actionable_tips") or base_insights["actionable_tips"],
            "generated_by": "Gemini 3.8 Flash (B2B Partner Intelligence)",
            "is_ai_generated": True
        }
    except Exception as e:
        logger.warning(f"Error in analyze_lead_ai: {e}. Fallback to rule-based.")
        return base_insights


def export_leads_to_dataframe(leads: List[Dict[str, Any]]) -> pd.DataFrame:
    if not leads:
        return pd.DataFrame()
    rows = []
    for l in leads:
        rows.append({
            "Mã Lead": l.get("lead_id"),
            "Tên đơn vị": l.get("name"),
            "Loại hình": l.get("type"),
            "Chuỗi mẹ": l.get("parent_chain") or "—",
            "Địa chỉ": l.get("address"),
            "Điện thoại": l.get("phone"),
            "Điểm Phù Hợp": f"{l.get('fit_score')}/100",
            "Hạng": l.get("fit_grade"),
            "Trạng Thái": l.get("status"),
            "Người Phụ Trách": l.get("assigned_to", "Chưa phân công")
        })
    return pd.DataFrame(rows)
