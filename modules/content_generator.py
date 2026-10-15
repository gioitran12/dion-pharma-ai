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
    """Kiểm tra văn bản xem có vi phạm từ cấm theo Nghị định 342/2025/NĐ-CP không."""
    violations = []
    terms = load_prohibited_terms()
    text_lower = text.lower()
    
    for item in terms:
        t = item["term"].lower()
        if t in text_lower:
            violations.append(item)
            
    return (len(violations) == 0), violations

def deep_audit_radar(text: str) -> Dict[str, Any]:
    """
    Hệ thống Radar Thẩm định 4 Lớp chuyên sâu:
    1. Kiểm soát từ cấm y dược (Prohibited Terms)
    2. Cam kết quá đà / Tuyên bố tuyệt đối (Exaggeration)
    3. Cảnh báo bắt buộc theo NĐ 342 (Mandatory Disclaimer)
    4. Bằng chứng khoa học & Giới hạn claim (Claim Boundary)
    """
    is_valid, violations = validate_content_compliance(text)
    text_lower = text.lower()
    
    # 1. Điểm Từ Cấm (0 - 25)
    prohibited_score = max(0, 25 - (len(violations) * 10))
    
    # 2. Điểm Cam Kết Quá Đà (0 - 25)
    exaggeration_terms = ["100%", "tuyệt đối", "dứt điểm", "cam kết", "nhanh nhất", "số 1", "thần dược"]
    found_exaggerations = [w for w in exaggeration_terms if w in text_lower]
    exaggeration_score = max(0, 25 - (len(found_exaggerations) * 8))
    
    # 3. Điểm Cảnh Báo Disclaimer (0 - 25)
    disclaimer_snippet = "thực phẩm này không phải là thuốc"
    has_disclaimer = disclaimer_snippet in text_lower
    disclaimer_score = 25 if has_disclaimer else 0
    
    # 4. Điểm Phạm Vi Claim (0 - 25)
    has_support_wording = any(w in text_lower for w in ["hỗ trợ", "bổ sung", "duy trì", "giúp"])
    claim_boundary_score = 25 if has_support_wording else 10
    
    total_score = prohibited_score + exaggeration_score + disclaimer_score + claim_boundary_score
    
    status = "ĐẠT CHUẨN" if (total_score >= 85 and has_disclaimer and len(violations) == 0) else "VI PHẠM QUY CHUẨN"
    
    return {
        "total_score": total_score,
        "status": status,
        "is_compliant": (status == "ĐẠT CHUẨN"),
        "layers": {
            "prohibited": {"score": prohibited_score, "max": 25, "violations": [v["term"] for v in violations]},
            "exaggeration": {"score": exaggeration_score, "max": 25, "words": found_exaggerations},
            "disclaimer": {"score": disclaimer_score, "max": 25, "present": has_disclaimer},
            "boundary": {"score": claim_boundary_score, "max": 25, "valid_wording": has_support_wording}
        },
        "violations_detail": violations
    }

def auto_fix_compliance(text: str, sku: str = "DION-D3-1000") -> Dict[str, Any]:
    """
    TÍNH NĂNG ĐỘT PHÁ: Tự động sửa bài viết vi phạm thành bài viết chuẩn luật NĐ 342/2025.
    - Thay thế các từ cấm bằng từ ngữ được pháp luật cho phép.
    - Loại bỏ các cam kết tuyệt đối quá đà.
    - Tự động bổ sung câu Disclaimer bắt buộc.
    """
    fixed_text = text
    terms = load_prohibited_terms()
    
    changes_made = []
    
    # Thay thế từ cấm
    for item in terms:
        t = item["term"]
        s = item["suggestion"]
        if t.lower() in fixed_text.lower():
            # Thay thế không phân biệt hoa thường
            import re
            fixed_text = re.sub(re.escape(t), s, fixed_text, flags=re.IGNORECASE)
            changes_made.append(f"Thay thế '{t}' bằng '{s}'")
            
    # Thay thế cam kết tuyệt đối
    replacements = {
        "100%": "hiệu quả rõ rệt",
        "cam kết": "được kiểm chứng",
        "dứt điểm": "kiểm soát tốt",
        "thần dược": "giải pháp dinh dưỡng"
    }
    for old_w, new_w in replacements.items():
        if old_w in fixed_text.lower():
            import re
            fixed_text = re.sub(re.escape(old_w), new_w, fixed_text, flags=re.IGNORECASE)
            changes_made.append(f"Chuẩn hóa '{old_w}' thành '{new_w}'")
            
    # Đảm bảo có câu Disclaimer bắt buộc
    product = get_product_by_sku(sku)
    disclaimer = product.get("mandatory_disclaimer") if product else "Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh."
    
    if "thực phẩm này không phải là thuốc" not in fixed_text.lower():
        fixed_text = fixed_text.strip() + f"\n\n---\n⚠️ {disclaimer}"
        changes_made.append("Tự động đính kèm câu Disclaimer bắt buộc theo NĐ 342/2025")
        
    audit_after = deep_audit_radar(fixed_text)
    
    return {
        "original_text": text,
        "fixed_text": fixed_text,
        "changes_made": changes_made,
        "audit": audit_after
    }

def generate_marketing_draft(sku: str, channel: str = "Facebook Post", tone: str = "Khoa học & Chuyên môn") -> Dict[str, Any]:
    """Tạo bản nháp truyền thông từ các Claims hợp lệ."""
    product = get_product_by_sku(sku)
    if not product:
        return {"error": "Không tìm thấy sản phẩm"}
        
    claims = get_active_claims(sku, zone="COMMERCIAL_APPROVED")
    if not claims:
        return {"error": "Sản phẩm hiện không có Claim thương mại nào còn hiệu lực"}
        
    bullets = "\n".join([f"• {c['claim_text']}" for c in claims])
    disclaimer = product.get("mandatory_disclaimer", "")
    
    draft = f"""🌿 GIẢI PHÁP CHĂM SÓC SỨC KHỎE CHỦ ĐỘNG TỪ {product['name'].upper()}

Bổ sung vi chất đúng cách là chìa khóa vàng giúp duy trì thể trạng dẻo dai và nâng cao chất lượng cuộc sống.

💡 CÔNG DỤNG ĐÃ ĐƯỢC CỤC AN TOÀN THỰC PHẨM CÔNG NHẬN:
{bullets}

🔬 Sản xuất tại nhà máy đạt chuẩn GMP quốc tế.
📦 Thích hợp cho: {', '.join(product.get('target_users', []))}.

👉 Liên hệ ngay để nhận tư vấn lộ trình sử dụng từ chuyên gia!
---
⚠️ {disclaimer}
"""
    audit = deep_audit_radar(draft)
    
    return {
        "sku": sku,
        "product_name": product["name"],
        "channel": channel,
        "tone": tone,
        "draft_text": draft,
        "used_claims": [c["claim_id"] for c in claims],
        "audit": audit
    }
