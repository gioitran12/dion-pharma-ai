import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

LEADS_PATH = Path(__file__).resolve().parent.parent / "data" / "b2b_leads.json"

def load_leads_data() -> List[Dict[str, Any]]:
    if not LEADS_PATH.exists():
        return []
    with open(LEADS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("leads", [])

def save_leads_data(leads: List[Dict[str, Any]]) -> bool:
    """Lưu lại danh sách Lead vào file JSON khi có cập nhật trạng thái duyệt / phân công"""
    try:
        with open(LEADS_PATH, "w", encoding="utf-8") as f:
            json.dump({"leads": leads}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving leads: {e}")
        return False

def update_lead_status(lead_id: str, new_status: str, assigned_to: Optional[str] = None) -> bool:
    """Cập nhật trạng thái duyệt (APPROVED / REJECTED / NEW) và người phụ trách"""
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
    search_keyword: str = ""
) -> List[Dict[str, Any]]:
    """Bộ lọc nâng cao: hỗ trợ lọc theo địa bàn, loại hình, trạng thái duyệt, điểm phù hợp và từ khóa tìm kiếm"""
    leads = load_leads_data()
    filtered = []
    
    keyword_clean = search_keyword.strip().lower()
    
    for item in leads:
        match_prov = (province == "Tất cả") or (item.get("province") == province)
        match_dist = (district == "Tất cả") or (item.get("district") == district)
        match_type = (lead_type == "Tất cả") or (item.get("type") == lead_type)
        match_status = (status == "Tất cả") or (item.get("status") == status)
        match_score = item.get("fit_score", 0) >= min_fit_score
        
        # Tìm kiếm theo từ khóa (Tên, địa chỉ, số điện thoại, danh mục)
        match_kw = True
        if keyword_clean:
            searchable_text = f"{item.get('name', '')} {item.get('address', '')} {item.get('phone', '')} {' '.join(item.get('categories', []))}".lower()
            match_kw = keyword_clean in searchable_text
            
        if match_prov and match_dist and match_type and match_status and match_score and match_kw:
            filtered.append(item)
            
    return filtered

def group_by_parent_chain(leads: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Phát hiện và gom nhóm các chi nhánh thuộc cùng một chuỗi bán lẻ (Deduplication)"""
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

def export_leads_to_dataframe(leads: List[Dict[str, Any]]) -> pd.DataFrame:
    """Chuyển đổi danh sách lead thành Pandas DataFrame có cấu trúc điểm số trực quan"""
    if not leads:
        return pd.DataFrame()
    
    rows = []
    for l in leads:
        rows.append({
            "Mã Lead": l.get("lead_id"),
            "Tên đơn vị": l.get("name"),
            "Loại hình": l.get("type"),
            "Chuỗi mẹ": l.get("parent_chain") or "—",
            "Tỉnh/Thành": l.get("province"),
            "Quận/Huyện": l.get("district"),
            "Địa chỉ": l.get("address"),
            "Điện thoại": l.get("phone"),
            "Điểm Phù Hợp": f"{l.get('fit_score')}/100 ({l.get('fit_grade')})",
            "Độ Tin Cậy": f"{l.get('trust_score')}/100",
            "Khả Năng Liên Hệ": f"{l.get('contact_score')}/100",
            "Tín Hiệu Nhu Cầu": f"{l.get('intent_score')}/100",
            "Trạng Thái": l.get("status"),
            "Người Phụ Trách": l.get("assigned_to", "Chưa phân công")
        })
    return pd.DataFrame(rows)
