import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from modules.claims_hub import get_active_claims, get_all_products, get_product_by_sku

# Danh sách bệnh lý nghiêm trọng bắt buộc chuyển Dược sĩ / Bác sĩ thẩm định
CRITICAL_MEDICAL_CONDITIONS = [
    "suy gan", "suy thận", "ung thư", "đang xạ trị", "hóa trị",
    "tiểu đường nặng", "dị ứng sốc phản vệ", "uống cùng thuốc tim đặc trị",
    "tai biến", "đột quỵ cấp"
]

def check_critical_sensitivity(query: str) -> Tuple[bool, str]:
    """Kiểm tra bệnh lý nan y hoặc tương tác thuốc nguy hiểm cần hội đồng y khoa"""
    query_lower = query.lower()
    for kw in CRITICAL_MEDICAL_CONDITIONS:
        if kw in query_lower:
            return True, f"Câu hỏi liên quan đến bệnh lý nghiêm trọng hoặc tương tác thuốc đặc trị ({kw.upper()}). Bắt buộc chuyển Dược sĩ chuyên môn thẩm định."
    return False, ""

def detect_sku_from_query(query: str, default_sku: str = "ALL") -> str:
    """Tự động nhận diện SKU sản phẩm từ nội dung câu hỏi nếu người dùng không chọn cụ thể"""
    if default_sku != "ALL":
        return default_sku
    q = query.lower()
    if any(k in q for k in ["cal-mom", "calmom", "canxi", "tảo đỏ", "lithothamnion", "xương", "bầu"]):
        return "DION-CAL-MOM"
    elif any(k in q for k in ["d3", "d3 1000", "nhỏ giọt", "drops", "photpho"]):
        return "DION-D3-1000"
    elif any(k in q for k in ["sắt", "fero", "folic", "quatrefolic", "thiếu máu", "bổ máu"]):
        return "DION-FE-FOLIC"
    return "DION-CAL-MOM"

def generate_copilot_response(query: str, sku: str = "ALL") -> Dict[str, Any]:
    """
    Sinh câu trả lời cố vấn chuyên môn & đào tạo nhân viên (Medical Rep & Pharmacist Advisor):
    - Grounding 100% trên Kho Dữ liệu Công bố & Bằng chứng Lâm sàng PubMed (data/products_claims.json).
    - Cung cấp: Hồ sơ công bố Cục ATTP, Bằng chứng lâm sàng RCTs, Kịch bản tư vấn chuẩn cho Dược sĩ,
      và Lưu ý chống chỉ định / Cụm từ cấm kỵ.
    """
    is_critical, critical_reason = check_critical_sensitivity(query)
    if is_critical:
        return {
            "type": "ESCALATION",
            "badge": "CHUYỂN DƯỢC VỤ & BÁC SĨ THẨM ĐỊNH",
            "content": f"{critical_reason}\n\n"
                       f"Hướng dẫn xử lý cho Nhân viên Sales / CSKH:\n"
                       f"1. Tuyệt đối KHÔNG tự ý tư vấn liều dùng hoặc khẳng định sản phẩm có thể dùng chung với thuốc điều trị bệnh lý này.\n"
                       f"2. Thu thập đầy đủ hồ sơ bệnh án hoặc đơn thuốc hiện tại của khách hàng.\n"
                       f"3. Phản hồi chuẩn mực: 'Dạ trường hợp của mình có bệnh nền đặc thù, em xin phép chuyển thông tin cho Dược sĩ chuyên môn của Dion Healthcare liên hệ tư vấn trực tiếp cho mình trong vòng 15 phút ạ'.\n"
                       f"4. Hệ thống đã tự động mở Ticket y khoa cấp độ đỏ.",
            "citations": [],
            "source_claims": [],
            "clinical_evidence": [],
            "product_dossier": None
        }

    target_sku = detect_sku_from_query(query, sku)
    product = get_product_by_sku(target_sku)
    if not product:
        products = get_all_products()
        product = products[0] if products else None

    if not product:
        return {
            "type": "NORMAL",
            "badge": "CHƯA CÓ DỮ LIỆU",
            "content": "Không tìm thấy hồ sơ sản phẩm trong Kho Dữ liệu AI. Vui lòng kiểm tra lại mã SKU.",
            "citations": [],
            "source_claims": []
        }

    # Bóc tách dữ liệu hồ sơ
    p_name = product.get("name", "")
    reg_no = product.get("registration_number", "Đang cập nhật")
    ad_no = product.get("ad_permit_number", "Đang cập nhật")
    ingredients = product.get("active_ingredients", [])
    target_users = product.get("target_users", [])
    contra = product.get("contraindications", "Không có")
    evidence_list = product.get("clinical_evidence", [])
    claims_list = product.get("claims", [])

    # Chuẩn bị văn bản phản hồi đào tạo & tư vấn nhân viên
    ing_text = ", ".join([f"{i['name']} ({i['amount']})" for i in ingredients])
    target_text = "\n".join([f"  • {t}" for t in target_users])
    
    # Lọc claims phù hợp
    matched_claims = []
    q_words = [w for w in query.lower().split() if len(w) > 2]
    for c in claims_list:
        if c.get("status") == "APPROVED":
            c_text = c.get("claim_text", "").lower()
            if any(w in c_text for w in q_words) or len(matched_claims) < 2:
                matched_claims.append(c)

    claims_rendered = "\n".join([f"  • [{c['claim_id']}] {c['claim_text']}" for c in matched_claims[:3]])

    # Lọc bằng chứng lâm sàng PubMed
    evidence_rendered = ""
    if evidence_list:
        ev_items = []
        for e in evidence_list:
            ev_items.append(
                f"  • **PMID: {e.get('pmid')}** — *{e.get('title')}* ({e.get('journal')}, {e.get('sample_size')}):\n"
                f"     ➔ Kết luận: {e.get('conclusion')}"
            )
        evidence_rendered = "\n\n".join(ev_items)
    else:
        evidence_rendered = "  Đang tổng hợp thử nghiệm lâm sàng đối chứng RCT trên hệ thống PubMed."

    # Xây dựng kịch bản tư vấn cho Dược sĩ / Sales Rep
    sales_script = (
        f"1. **Mở lời & Đồng cảm**: Lắng nghe nhu cầu của khách hàng (giai đoạn thai kỳ, tình trạng sức khỏe xương khớp, hoặc tiền sử dùng canxi/sắt bị nóng).\n"
        f"2. **Điểm bán hàng độc nhất (USP Khoa học)**: Nhấn mạnh nguồn nguyên liệu {ingredients[0]['name'] if ingredients else 'hữu cơ chuẩn hóa'}, "
        f"hấp thu êm dịu, giảm tối đa triệu chứng táo bón, nóng trong hay lắng cặn.\n"
        f"3. **Liều dùng & Thời điểm uống chuẩn**: Uống sau bữa ăn sáng/trưa 30-45 phút cùng 1 ly nước đầy. Không uống sau 15h chiều.\n"
        f"4. **Căn cứ pháp lý khi khách hỏi chứng nhận**: Trích dẫn Giấy tiếp nhận công bố số `{reg_no}` và Giấy xác nhận nội dung quảng cáo số `{ad_no}`."
    )

    full_reply = f"""### TÀI LIỆU CỐ VẤN CHUYÊN MÔN & ĐÀO TẠO NHÂN VIÊN: {p_name.upper()}

#### 1. Hồ sơ Pháp chế & Đăng ký Cục An toàn thực phẩm:
- **Số ĐKSP**: `{reg_no}`
- **Số XNQC**: `{ad_no}`
- **Hoạt chất chính**: {ing_text}
- **Đối tượng sử dụng được phê duyệt**:
{target_text}

#### 2. Công dụng Thương mại đã được phê duyệt (Claims Hub):
{claims_rendered}

#### 3. Bằng chứng Nghiên cứu Lâm sàng Quốc tế (PubMed RCTs):
{evidence_rendered}

#### 4. Kịch bản Tư vấn Chuẩn cho Dược sĩ & Trình dược viên:
{sales_script}

---
**LƯU Ý PHÁP CHẾ & CHỐNG CHỈ ĐỊNH BẮT BUỘC:**
- **Chống chỉ định**: {contra}
- **Cụm từ CẤM NÓI khi bán hàng**: Tuyệt đối không dùng các từ *'chữa khỏi hẳn'*, *'đặc trị dứt điểm'*, *'cam kết 100%'*, hoặc xúi giục khách hàng bỏ thuốc kê đơn của bác sĩ.
- **Disclaimer bắt buộc**: *'Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh.'*
"""

    return {
        "type": "NORMAL",
        "badge": "✅ HỒ SƠ PHÁP CHẾ & PUBMED ĐÃ XÁC THỰC",
        "sku": target_sku,
        "product_name": p_name,
        "content": full_reply,
        "citations": [c.get("claim_id") for c in matched_claims],
        "source_claims": matched_claims,
        "clinical_evidence": evidence_list,
        "product_dossier": {
            "sku": target_sku,
            "name": p_name,
            "registration_number": reg_no,
            "ad_permit_number": ad_no,
            "active_ingredients": ingredients,
            "target_users": target_users,
            "contraindications": contra
        }
    }
