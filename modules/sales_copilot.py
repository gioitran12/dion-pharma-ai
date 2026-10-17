import os
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from modules.claims_hub import get_active_claims, get_all_products, get_product_by_sku

# Danh sách từ khóa câu hỏi nhạy cảm y tế bắt buộc phải chuyển Dược sĩ / Bác sĩ
SENSITIVE_KEYWORDS = [
    "bầu", "mang thai", "thai kỳ", "cho con bú", "sơ sinh",
    "suy gan", "suy thận", "ung thư", "đang uống thuốc", "tiểu đường nặng",
    "bệnh nền", "dị ứng nặng", "uống cùng thuốc", "thuốc điều trị", "thuốc tim",
    "kháng sinh", "tương tác thuốc"
]

# Danh sách từ dừng cơ bản trong tiếng Việt để tránh khớp nhầm claim ngẫu nhiên
STOP_WORDS = {
    "có", "không", "cho", "của", "và", "các", "những", "được", "này",
    "sản", "phẩm", "uống", "dùng", "gì", "thế", "nào", "làm", "sao",
    "bao", "nhiêu", "hỏi", "với", "trong", "khi", "là", "bị", "hay",
    "tôi", "mình", "bạn", "khách", "hàng", "ạ", "dạ", "ơi", "giúp",
    "tốt", "cần", "nên", "phải", "nữa", "rất", "quá", "lắm", "đến",
    "đối", "về", "như", "theo", "đã", "đang", "sẽ", "nhất", "cũng"
}

def check_sensitivity(query: str) -> Tuple[bool, str]:
    """Kiểm tra xem câu hỏi có thuộc nhóm nhạy cảm y tế cần chuyển chuyên gia không"""
    query_lower = query.lower()
    for kw in SENSITIVE_KEYWORDS:
        if kw in query_lower:
            return True, f"Câu hỏi liên quan đến nhóm nhạy cảm y tế ({kw.upper()}). Cần tuân thủ quy tắc an toàn y tế nghiêm ngặt."
    return False, ""

def generate_copilot_response(query: str, sku: str = "ALL") -> Dict[str, Any]:
    """
    Sinh câu trả lời từ RAG Knowledge Grounding:
    - Nếu câu hỏi nhạy cảm -> Yêu cầu chuyển Dược sĩ thẩm định (Không tạo Ticket giả).
    - Nếu bình thường -> Tra cứu chính xác Claims của đúng SKU được yêu cầu.
    - Tuyệt đối KHÔNG fallback sang Claim của sản phẩm khác khi không tìm thấy.
    """
    is_sensitive, reason = check_sensitivity(query)
    
    # 1. Xử lý trường hợp nhạy cảm y tế (Escalation / Handoff)
    if is_sensitive:
        return {
            "type": "ESCALATION",
            "badge": "⚠️ YÊU CẦU CHUYỂN DƯỢC SĨ TƯ VẤN CHUYÊN MÔN",
            "content": (
                f"{reason}\n\n"
                "📋 Hướng dẫn xử lý quy trình an toàn y tế:\n"
                "1. Trường hợp này cần được dược sĩ hoặc người có chuyên môn xem xét. Vui lòng chuyển yêu cầu tới bộ phận phụ trách.\n"
                "2. Tuyệt đối KHÔNG tự ý khẳng định an toàn hoặc tư vấn liều lượng cho trường hợp này.\n"
                "3. Ghi nhận đầy đủ câu hỏi và thông tin liên hệ của khách hàng để chuyển giao chuyên gia liên hệ lại."
            ),
            "citations": [],
            "source_claims": [],
            "handoff_required": True
        }
    
    # 2. Xác định phạm vi sản phẩm cần tra cứu
    if sku != "ALL":
        target_prod = get_product_by_sku(sku)
        if not target_prod:
            # SKU yêu cầu không tồn tại -> Không tự lấy Claim của sản phẩm khác!
            return {
                "type": "INSUFFICIENT_EVIDENCE",
                "badge": "⚠️ KHÔNG TÌM THẤY SẢN PHẨM",
                "content": (
                    f"Hiện tại không tìm thấy thông tin cho mã sản phẩm '{sku}'. "
                    "Hệ thống không thể cung cấp câu trả lời khi thiếu dữ liệu sản phẩm đã xác thực."
                ),
                "citations": [],
                "source_claims": [],
                "handoff_required": False
            }
        products_to_search = [target_prod]
    else:
        products_to_search = get_all_products()
    
    # 3. Lọc từ khóa có nghĩa từ câu hỏi (loại bỏ stop words)
    query_lower = query.lower()
    cleaned_query = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in query_lower)
    meaningful_tokens = [
        w for w in cleaned_query.split()
        if len(w) >= 2 and w not in STOP_WORDS
    ]
    
    if not meaningful_tokens:
        return {
            "type": "INSUFFICIENT_EVIDENCE",
            "badge": "⚠️ CHƯA ĐỦ CĂN CỨ XÁC MINH",
            "content": (
                "Hiện tại hệ thống chưa có đủ thông tin sản phẩm được xác minh để trả lời chính xác câu hỏi này. "
                "Vui lòng kiểm tra lại sản phẩm hoặc chuyển nhân viên phụ trách hỗ trợ."
            ),
            "citations": [],
            "source_claims": [],
            "handoff_required": False
        }
    
    # 4. Tìm kiếm claims hợp lệ trong Vùng thương mại (COMMERCIAL_APPROVED) và còn hiệu lực
    matched_claims = []
    for p in products_to_search:
        # get_active_claims tự động lọc: zone="COMMERCIAL_APPROVED", status="APPROVED", effective_until >= today
        active_claims = get_active_claims(p["sku"], zone="COMMERCIAL_APPROVED")
        p_name_lower = p.get("name", "").lower()
        p_name_words = set("".join(ch if ch.isalnum() or ch.isspace() else " " for ch in p_name_lower).split())
        
        for c in active_claims:
            c_text_lower = c.get("claim_text", "").lower()
            c_words = set("".join(ch if ch.isalnum() or ch.isspace() else " " for ch in c_text_lower).split())
            
            # Đếm số từ khóa có nghĩa khớp chính xác với Claim này
            matched_words = [w for w in meaningful_tokens if w in c_words]
            
            # Nếu tên sản phẩm khớp với từ khóa trong query, cộng thêm điểm
            name_matches = [w for w in meaningful_tokens if w in p_name_words]
            
            if matched_words:
                score = len(matched_words) * 2 + len(name_matches)
                matched_claims.append({
                    "sku": p["sku"],
                    "product_name": p["name"],
                    "claim_id": c["claim_id"],
                    "claim_text": c["claim_text"],
                    "evidence": c.get("evidence_source", "Hồ sơ công bố sản phẩm"),
                    "score": score
                })
    
    # 5. Xử lý trường hợp không tìm thấy Claim phù hợp
    # TUYỆT ĐỐI KHÔNG FALLBACK LẤY CLAIM CỦA SẢN PHẨM KHÁC!
    if not matched_claims:
        return {
            "type": "INSUFFICIENT_EVIDENCE",
            "badge": "⚠️ CHƯA ĐỦ CĂN CỨ XÁC MINH",
            "content": (
                "Hiện tại hệ thống chưa có đủ thông tin sản phẩm được xác minh để trả lời chính xác câu hỏi này. "
                "Vui lòng kiểm tra lại sản phẩm hoặc chuyển nhân viên phụ trách hỗ trợ."
            ),
            "citations": [],
            "source_claims": [],
            "handoff_required": False
        }
    
    # Sắp xếp theo điểm khớp cao nhất
    matched_claims.sort(key=lambda x: x["score"], reverse=True)
    primary = matched_claims[0]
    
    # Lấy các claims cùng sản phẩm của primary để trích dẫn
    same_prod_claims = [c for c in matched_claims if c["sku"] == primary["sku"]]
    
    # 6. Trả về kết quả xác thực từ Claim hợp lệ
    reply = (
        f"Dựa trên tài liệu công bố chính thức của sản phẩm **{primary['product_name']}**:\n\n"
        f"✅ **Công dụng được phép tư vấn:**\n"
        f"- {primary['claim_text']}\n\n"
        f"📌 **Căn cứ pháp lý & Nguồn trích dẫn:**\n"
        f"- Mã Claim: `{primary['claim_id']}`\n"
        f"- Nguồn: {primary['evidence']}\n\n"
        f"💡 *Lưu ý: Bắt buộc đính kèm disclaimer khi gửi văn bản cho khách hàng: 'Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh'.*"
    )
    
    return {
        "type": "NORMAL",
        "badge": "✅ ĐÃ XÁC THỰC TỪ CLAIMS ĐƯỢC DUYỆT",
        "content": reply,
        "citations": [c["claim_id"] for c in same_prod_claims],
        "source_claims": same_prod_claims,
        "handoff_required": False
    }
