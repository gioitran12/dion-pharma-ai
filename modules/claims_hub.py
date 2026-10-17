"""
DION Healthcare AI — Claims Hub & Knowledge Hub Facade
Quản lý tri thức sản phẩm, đối soát Claims và cung cấp giao diện tương thích ngược 100% cho toàn bộ hệ thống.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from modules.knowledge.schemas import (
    ProductRecord,
    ClaimRecord,
    KnowledgeZone,
    ClaimStatus,
    ValidationCode,
    ClaimValidationResult,
)
from modules.knowledge.validator import (
    ClaimEligibilityValidator,
    validate_claim_eligibility,
)
from modules.knowledge.repository import (
    BaseKnowledgeRepository,
    JSONKnowledgeRepository,
    get_knowledge_repository,
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "products_claims.json"


# ==============================================================================
# HÀM HIỆN HỮU (DUY TRÌ TƯƠNG THÍCH NGƯỢC 100% VỚI SERVER & COPILOT)
# ==============================================================================

def load_products_data() -> Dict[str, Any]:
    """Tải dữ liệu JSON thô từ file data/products_claims.json."""
    if not DATA_PATH.exists():
        return {"products": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_products() -> List[Dict[str, Any]]:
    """Trả về danh sách sản phẩm dạng dictionary thô."""
    data = load_products_data()
    return data.get("products", [])


def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    """Tìm sản phẩm theo SKU dưới dạng dictionary thô."""
    products = get_all_products()
    clean_sku = sku.strip()
    for p in products:
        if p.get("sku", "").strip() == clean_sku:
            return p
    return None


def get_active_claims(sku: str, zone: str = "COMMERCIAL_APPROVED") -> List[Dict[str, Any]]:
    """
    Lấy danh sách Claims ĐANG CÒN HIỆU LỰC thuộc vùng tri thức chỉ định (dạng dict thô).
    Nếu Claim đã quá hạn (effective_until < now) hoặc status != APPROVED -> LOẠI BỎ.
    Tuyệt đối không đưa Claims nội bộ/chuyên môn vào vùng thương mại.
    """
    product = get_product_by_sku(sku)
    if not product:
        return []
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    active_claims = []
    
    for c in product.get("claims", []):
        c_zone = c.get("zone", "")
        is_zone_match = (c_zone == zone) if zone != "ALL" else True
        is_approved = c.get("status") == "APPROVED"
        
        # Kiểm tra ngày hiệu lực và ngày hết hạn
        effective_until = c.get("effective_until", "9999-12-31")
        effective_from = c.get("effective_from", "0000-01-01")
        is_not_expired = (effective_until >= today_str) and (today_str >= effective_from)
        
        if is_zone_match and is_approved and is_not_expired:
            active_claims.append(c)
            
    return active_claims


def get_claims_summary(sku: str) -> Dict[str, Any]:
    """Thống kê trạng thái claims của sản phẩm (hợp lệ vs hết hạn vs nội bộ) dạng dict thô."""
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
        elif c.get("zone") in ("INTERNAL_EXPERT", "INTERNAL_MEDICAL"):
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


def save_or_update_product(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Lưu hoặc cập nhật một sản phẩm nghiên cứu/công bố vào Kho Dữ liệu AI tập trung (TARGET Feature)."""
    sku = product_data.get("sku")
    if not sku:
        raise ValueError("Mã SKU sản phẩm là bắt buộc")
        
    data = load_products_data()
    products = data.get("products", [])
    
    found_idx = -1
    for i, p in enumerate(products):
        if p.get("sku") == sku:
            found_idx = i
            break
            
    if found_idx >= 0:
        products[found_idx] = product_data
        action = "UPDATED"
    else:
        products.append(product_data)
        action = "CREATED"
        
    data["products"] = products
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    return {"status": "success", "action": action, "sku": sku, "product": product_data}


def search_knowledge_hub(query: str, sku: Optional[str] = None) -> List[Dict[str, Any]]:
    """Tìm kiếm trong Kho Dữ liệu AI theo từ khóa (TARGET Feature)."""
    products = get_all_products()
    results = []
    q_lower = query.lower().strip()
    
    for p in products:
        if sku and sku != "ALL" and p.get("sku") != sku:
            continue
            
        p_name = p.get("name", "").lower()
        p_category = p.get("category", "").lower()
        ingredients = " ".join([i.get("name", "").lower() for i in p.get("active_ingredients", [])])
        targets = " ".join([t.lower() for t in p.get("target_users", [])])
        claims_text = " ".join([c.get("claim_text", "").lower() for c in p.get("claims", [])])
        evidence_text = " ".join([e.get("title", "").lower() + " " + e.get("conclusion", "").lower() for e in p.get("clinical_evidence", [])])
        
        all_text = f"{p_name} {p_category} {ingredients} {targets} {claims_text} {evidence_text}"
        
        relevance = 0
        if q_lower in p_name:
            relevance += 50
        if q_lower in ingredients:
            relevance += 30
        if any(word in all_text for word in q_lower.split() if len(word) > 2):
            relevance += 20
            
        if relevance > 0 or not q_lower:
            results.append({
                "product": p,
                "relevance": relevance,
                "matched_claims": [c for c in p.get("claims", []) if q_lower in c.get("claim_text", "").lower() or not q_lower],
                "matched_evidence": [e for e in p.get("clinical_evidence", []) if q_lower in e.get("title", "").lower() or q_lower in e.get("conclusion", "").lower() or not q_lower]
            })
            
    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results


# ==============================================================================
# HÀM MỚI NÂNG CAO (SỬ DỤNG TYPED SCHEMAS & REPOSITORY CHO CHATBOT)
# ==============================================================================

def get_product_record(sku: str) -> Optional[ProductRecord]:
    """Tìm ProductRecord chuẩn hóa."""
    repo = get_knowledge_repository()
    return repo.get_product_by_sku(sku)


def get_eligible_claims_records(
    sku: str, as_of_date: Optional[Union[datetime, str]] = None
) -> List[ClaimRecord]:
    """Lấy danh sách ClaimRecord đã qua ClaimEligibilityValidator."""
    repo = get_knowledge_repository()
    return repo.get_eligible_commercial_claims(sku, as_of_date=as_of_date)
