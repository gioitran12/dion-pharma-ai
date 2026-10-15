import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "products_claims.json"

def load_products_data() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        return {"products": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_all_products() -> List[Dict[str, Any]]:
    data = load_products_data()
    return data.get("products", [])

def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    products = get_all_products()
    for p in products:
        if p.get("sku") == sku:
            return p
    return None

def get_active_claims(sku: str, zone: str = "COMMERCIAL_APPROVED") -> List[Dict[str, Any]]:
    """
    Lấy danh sách Claims ĐANG CÒN HIỆU LỰC thuộc vùng tri thức chỉ định.
    Nếu Claim đã quá hạn (effective_until < now) hoặc status != APPROVED -> LOẠI BỎ.
    """
    product = get_product_by_sku(sku)
    if not product:
        return []
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    active_claims = []
    
    for c in product.get("claims", []):
        is_zone_match = (c.get("zone") == zone) or (zone == "ALL")
        is_approved = c.get("status") == "APPROVED"
        is_not_expired = c.get("effective_until", "9999-12-31") >= today_str
        
        if is_zone_match and is_approved and is_not_expired:
            active_claims.append(c)
            
    return active_claims

def get_claims_summary(sku: str) -> Dict[str, Any]:
    """Thống kê trạng thái claims của sản phẩm (hợp lệ vs hết hạn vs nội bộ)"""
    product = get_product_by_sku(sku)
    if not product:
        return {}
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    total = len(product.get("claims", []))
    active_commercial = 0
    expired = 0
    internal = 0
    
    for c in product.get("claims", []):
        if c.get("effective_until", "") < today_str or c.get("status") == "EXPIRED":
            expired += 1
        elif c.get("zone") == "INTERNAL_EXPERT":
            internal += 1
        elif c.get("zone") == "COMMERCIAL_APPROVED" and c.get("status") == "APPROVED":
            active_commercial += 1
            
    return {
        "sku": sku,
        "name": product.get("name"),
        "total_claims": total,
        "active_commercial": active_commercial,
        "expired": expired,
        "internal": internal,
        "disclaimer": product.get("mandatory_disclaimer")
    }
