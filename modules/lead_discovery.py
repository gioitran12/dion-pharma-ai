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

def filter_leads(province: str = "Tất cả", district: str = "Tất cả", lead_type: str = "Tất cả") -> List[Dict[str, Any]]:
    leads = load_leads_data()
    filtered = []
    
    for item in leads:
        match_prov = (province == "Tất cả") or (item.get("province") == province)
        match_dist = (district == "Tất cả") or (item.get("district") == district)
        match_type = (lead_type == "Tất cả") or (item.get("type") == lead_type)
        
        if match_prov and match_dist and match_type:
            filtered.append(item)
            
    return filtered

def group_by_parent_chain(leads: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Phát hiện và gom nhóm các chi nhánh thuộc cùng một chuỗi bán lẻ"""
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

def export_leads_to_dataframe(leads: List[Dict[str, Any]]) -> pd.DataFrame:
    """Chuyển đổi danh sách lead thành Pandas DataFrame để hiển thị và xuất file Excel/CSV"""
    if not leads:
        return pd.DataFrame()
    
    rows = []
    for l in leads:
        rows.append({
            "Mã Lead": l.get("lead_id"),
            "Tên đơn vị": l.get("name"),
            "Loại hình": l.get("type"),
            "Chuỗi mẹ": l.get("parent_chain") or "Độc lập",
            "Tỉnh/Thành": l.get("province"),
            "Quận/Huyện": l.get("district"),
            "Địa chỉ": l.get("address"),
            "Điện thoại": l.get("phone"),
            "Email": l.get("email"),
            "Độ phù hợp": l.get("fit_score"),
            "Xác minh dữ liệu": l.get("trust_score"),
            "Trạng thái liên hệ": l.get("contact_readiness"),
            "Tín hiệu nhu cầu": l.get("intent_signal"),
            "Trạng thái duyệt": l.get("status")
        })
    return pd.DataFrame(rows)
