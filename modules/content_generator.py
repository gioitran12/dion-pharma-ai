import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from modules.claims_hub import get_product_by_sku, get_active_claims

PROHIBITED_PATH = Path(__file__).resolve().parent.parent / "data" / "prohibited_terms.json"

def load_prohibited_terms() -> List[Dict[str, str]]:
    if not PROHIBITED_PATH.exists():
        return []
    with open(PROHIBITED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("prohibited_phrases", [])

def validate_content_compliance(text: str) -> Tuple[bool, List[Dict[str, str]]]:
    """
    Kiểm tra văn bản xem có vi phạm từ cấm theo Nghị định 342/2025 không.
    Trả về: (is_compliant, danh sách vi phạm nếu có)
    """
    violations = []
    terms = load_prohibited_terms()
    text_lower = text.lower()
    
    for item in terms:
        t = item["term"].lower()
        if t in text_lower:
            violations.append(item)
            
    return (len(violations) == 0), violations

def generate_marketing_draft(sku: str, channel: str = "Facebook Post", tone: str = "Chuyên nghiệp & Khoa học") -> Dict[str, Any]:
    """
    Tạo bản nháp bài viết Marketing:
    - CHỈ lấy các Claims ĐANG CÒN HIỆU LỰC.
    - Tự động đính kèm câu Disclaimer bắt buộc.
    - Kiểm tra tính tuân thủ pháp luật.
    """
    product = get_product_by_sku(sku)
    if not product:
        return {"error": "Không tìm thấy sản phẩm"}
        
    claims = get_active_claims(sku, zone="COMMERCIAL_APPROVED")
    if not claims:
        return {"error": "Sản phẩm hiện không có Claim thương mại nào còn hiệu lực"}
        
    # Tạo nội dung mẫu chuẩn hóa theo claims
    bullets = "\n".join([f"✨ {c['claim_text']}" for c in claims])
    disclaimer = product.get("mandatory_disclaimer", "")
    
    draft = f"""🌿 GIẢI PHÁP SỨC KHỎE CHỦ ĐỘNG TỪ {product['name'].upper()}

Bạn có biết? Bổ sung vi chất đúng cách là chìa khóa vàng cho sức khỏe dẻo dai mỗi ngày!

💡 LÝ DO NÊN CHỌN {product['name']}:
{bullets}

🔬 Đạt chuẩn kiểm định an toàn và được cấp phép lưu hành toàn quốc.
📦 Quy cách tiện dụng, phù hợp cho: {', '.join(product.get('target_users', []))}.

👉 Nhắn tin ngay cho chúng tôi để được tư vấn lộ trình sử dụng tối ưu!
--------------------------
⚠️ {disclaimer}
"""
    # Kiểm tra tuân thủ
    is_valid, violations = validate_content_compliance(draft)
    
    return {
        "sku": sku,
        "product_name": product["name"],
        "channel": channel,
        "tone": tone,
        "draft_text": draft,
        "used_claims": [c["claim_id"] for c in claims],
        "is_compliant": is_valid,
        "violations": violations,
        "mandatory_disclaimer": disclaimer
    }
