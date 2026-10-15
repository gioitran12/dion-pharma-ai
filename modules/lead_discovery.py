import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from modules.claims_hub import get_product_by_sku, get_active_claims

LEADS_PATH = Path(__file__).resolve().parent.parent / "data" / "b2b_leads.json"

def load_leads_data() -> List[Dict[str, Any]]:
    if not LEADS_PATH.exists():
        return []
    with open(LEADS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("leads", [])

def save_leads_data(leads: List[Dict[str, Any]]) -> bool:
    try:
        with open(LEADS_PATH, "w", encoding="utf-8") as f:
            json.dump({"leads": leads}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving leads: {e}")
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

def filter_leads(
    province: str = "Tất cả",
    district: str = "Tất cả",
    lead_type: str = "Tất cả",
    status: str = "Tất cả",
    min_fit_score: int = 0,
    search_keyword: str = "",
    only_new: bool = False
) -> List[Dict[str, Any]]:
    leads = load_leads_data()
    filtered = []
    keyword_clean = search_keyword.strip().lower()
    
    for item in leads:
        match_prov = (province == "Tất cả") or (item.get("province") == province)
        match_dist = (district == "Tất cả") or (item.get("district") == district)
        match_type = (lead_type == "Tất cả") or (item.get("type") == lead_type)
        match_status = (status == "Tất cả") or (item.get("status") == status)
        match_score = item.get("fit_score", 0) >= min_fit_score
        match_new = True if not only_new else item.get("is_new_opened", False)
        
        match_kw = True
        if keyword_clean:
            searchable_text = f"{item.get('name', '')} {item.get('address', '')} {item.get('phone', '')} {' '.join(item.get('categories', []))}".lower()
            match_kw = keyword_clean in searchable_text
            
        if match_prov and match_dist and match_type and match_status and match_score and match_kw and match_new:
            filtered.append(item)
            
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

def generate_b2b_outreach_pitch(lead_id: str, recommended_sku: str = "DION-D3-1000") -> Dict[str, Any]:
    """
    TÍNH NĂNG DOANH NGHIỆP: AI tự động phân tích hồ sơ đối tác và sinh kịch bản chào hàng 1-1.
    Tự động khớp thế mạnh của sản phẩm với đặc thù kênh bán của đối tác.
    """
    lead = get_lead_by_id(lead_id)
    if not lead:
        return {"error": "Không tìm thấy thông tin đối tác"}
        
    prod = get_product_by_sku(recommended_sku)
    if not prod:
        prod = {"name": "Danh mục Thực phẩm Bảo vệ Sức khỏe DION", "sku": recommended_sku}
        
    lead_name = lead["name"]
    lead_type = lead["type"]
    parent = lead.get("parent_chain")
    
    # Chiến lược tiếp cận theo phân khúc đối tác
    if "Mẹ & Bé" in lead_type or (parent and "Cưng" in parent):
        strategy = "Chiến lược Mẹ & Bé: Đẩy mạnh dòng Canxi sinh học & Sắt hữu cơ êm dịu dạ dày cho thai phụ"
        target_department = "Phòng Thu Mua Ngành Hàng Dinh Dưỡng Mẹ & Bé"
        angle = "Tỷ lệ hấp thu vượt trội, không gây nóng trong, bao bì chuẩn mực tạo uy tín tại quầy kệ"
    elif "Chuỗi" in lead_type or parent in ["FPT Long Châu", "Pharmacity", "An Khang (MWG)"]:
        strategy = f"Chiến lược Chuỗi Bán Lẻ: Đàm phán tập trung với Hội sở {parent} về chính sách SKU độc quyền"
        target_department = f"Ban Giám Đốc Mua Hàng & Phát Triển Sản Phẩm Mới — {parent}"
        angle = "Chiết khấu thương mại hấp dẫn, cung ứng ổn định 100% giấy phép Cục ATTP, hỗ trợ đào tạo Dược sĩ"
    else:
        strategy = "Chiến lược Nhà Thuốc Tư Nhân: Hỗ trợ quầy trưng bày, tư vấn chuyên môn và chương trình tích lũy"
        target_department = "Dược sĩ Phụ trách Chuyên môn & Chủ Nhà Thuốc"
        angle = "Hàng chính hãng dễ bán, phản hồi người dùng tích cực, chính sách đổi trả linh hoạt"
        
    email_subject = f"[DION HEALTHCARE] Đề xuất Hợp tác Phân phối Danh mục {prod['name']} tới {lead_name}"
    
    email_body = f"""Kính gửi: {target_department} — {lead_name},

Lời đầu tiên, DION Healthcare xin gửi lời chào trân trọng và lời chúc phát triển thịnh vượng tới Quý đơn vị.

Qua quá trình nghiên cứu địa bàn và danh mục sản phẩm của {lead_name} tại {lead.get('address')}, chúng tôi nhận thấy Quý đơn vị có thế mạnh vượt trội trong nhóm khách hàng chăm sóc sức khỏe chủ động và vi chất dinh dưỡng.

DION trân trọng đề xuất phương án hợp tác phân phối dòng sản phẩm:
👉 {prod['name']} (Mã SKU: {prod.get('sku')})
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
    return {
        "lead_id": lead_id,
        "lead_name": lead_name,
        "strategy": strategy,
        "target_department": target_department,
        "subject": email_subject,
        "pitch_body": email_body,
        "recommended_sku": prod["name"]
    }

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
