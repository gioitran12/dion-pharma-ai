"""
DION Healthcare AI — Bộ Tiếp Nhận Đầu Vào & Phân Loại Lead CareSoft
(First-Touch Chat Triage & Lead Qualification Engine for CareSoft Contact Center)

Giải quyết bài toán PoC trọng tâm số 1 của đối tác Vistafa:
1. Tiếp nhận hội thoại đa kênh (Fanpage, Zalo OA, Website Chat, Hotline).
2. Tự động bóc tách và chuẩn hóa Số Điện Thoại Việt Nam (Regex + Normalization).
3. Phân loại nhu cầu khách hàng: Hỏi giá, Cần tư vấn y dược, Đặt hàng, Khiếu nại.
4. Đánh giá xếp hạng Lead Score: HOT (Đã có SĐT + nhu cầu mua), WARM, COLD.
5. Tự động sinh thẻ "Tóm tắt 5 giây cho nhân viên CareSoft" (pain point, kịch bản chốt đơn).
6. Xuất dữ liệu tương thích 100% chuẩn định dạng import của hệ thống CareSoft (CSV/Excel).
"""

import json
import re
import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CARESOFT_LEADS_FILE = DATA_DIR / "caresoft_leads.json"

# REGEX CHUẨN HÓA SỐ ĐIỆN THOẠI VIỆT NAM (10 chữ số)
# Hỗ trợ các định dạng: 0982123456, 0982 123 456, 0982.123.456, +84982123456, 84982123456
PHONE_REGEX = re.compile(
    r'(?:(?:\+84|84|0)(?:3[2-9]|5[6|8|9]|7[0|6-9]|8[1-9]|9[0-9]))[\s\.-]?[0-9]{3}[\s\.-]?[0-9]{3,4}\b'
)


def extract_phone_number(text: str) -> Optional[str]:
    """
    Trích xuất và chuẩn hóa số điện thoại Việt Nam về định dạng 10 số (0xxxxxxxxx).
    Hỗ trợ mọi định dạng: 0982123456, 0982 123 456, 0982.123.456, +84982123456.
    """
    if not text:
        return None
    candidates = re.findall(r'(?:\+?84|0)[0-9\s\.\-]{8,16}[0-9]', text)
    for cand in candidates:
        digits = re.sub(r'\D', '', cand)
        if digits.startswith('84') and len(digits) == 11:
            digits = '0' + digits[2:]
        if len(digits) == 10 and digits.startswith('0') and digits[1] in '35789':
            return digits
    return None


def extract_customer_name(text: str, default_name: Optional[str] = None) -> str:
    """
    Bóc tách tên khách hàng từ lời thoại hoặc metadata.
    """
    if default_name and default_name.strip() and default_name.strip().lower() not in ["khách hàng", "unknown", "vô danh", "người dùng"]:
        return default_name.strip()

    match = re.search(r'(?:mình là|tôi là|em là|chị là|anh là|tên mình là|tên em là|tên là)\s+([^\s,\.!\?]+(?:\s+[^\s,\.!\?]+){0,2})', text, re.IGNORECASE)
    if match:
        raw = match.group(1).strip()
        stop_words = {'cần', 'muốn', 'hỏi', 'đang', 'ở', 'nhé', 'nha', 'ạ', 'có', 'mua', 'tư', 'vấn'}
        words = [w for w in raw.split() if w.lower() not in stop_words]
        if words:
            return ' '.join(w.capitalize() for w in words)

    match2 = re.search(r'(?:gửi cho|ship cho|đơn của)\s+(?:chị|anh|bác|cô)?\s*([^\s,\.!\?]+(?:\s+[^\s,\.!\?]+){0,2})', text, re.IGNORECASE)
    if match2:
        raw = match2.group(1).strip()
        stop_words = {'nhé', 'nha', 'ạ', 'gấp', 'sớm'}
        words = [w for w in raw.split() if w.lower() not in stop_words]
        if words:
            return ' '.join(w.capitalize() for w in words)

    return default_name if default_name else "Khách Vãng Lai"


def detect_interested_product(text: str) -> str:
    """
    Nhận diện sản phẩm khách hàng đang quan tâm dựa trên từ khóa.
    Hỗ trợ cả danh mục Vistafa và DION.
    """
    t_lower = text.lower()
    if any(k in t_lower for k in ["collagen", "đẹp da", "nếp nhăn", "trẻ hóa", "nổi mụn", "tăng cân"]):
        return "Collagen Powder (Vistafa)"
    elif any(k in t_lower for k in ["calci complex", "calci", "canxi", "cal-mom", "sỏi thận", "xương", "loãng xương"]):
        return "Calci Complex (Vistafa) / Cal-Mom"
    elif any(k in t_lower for k in ["sleep well", "sleep", "mất ngủ", "khó ngủ", "ngủ ngon", "an thần", "trằn trọc"]):
        return "Sleep Well (Vistafa)"
    elif any(k in t_lower for k in ["sắt", "fero", "thiếu máu", "folic", "nóng trong"]):
        return "Sắt Hữu Cơ Chelate Fero-Plus"
    elif any(k in t_lower for k in ["d3", "vitamin d", "nhỏ giọt"]):
        return "Vitamin D3 1000IU"
    return "Tư Vấn Tổng Hợp Vi Chất"


def classify_inquiry_type(text: str) -> Tuple[str, str]:
    """
    Phân loại nhu cầu khách hàng:
    - DAT_HANG: Khách muốn mua, hỏi đặt hàng, xin địa chỉ ship
    - HOI_GIA: Khách hỏi giá, chiết khấu, chương trình khuyến mãi
    - TU_VAN_CHUYEN_MON: Hỏi công dụng, cách dùng, đối tượng mang thai, sỏi thận, mất ngủ
    - KHIEU_NAI: Phản ánh tác dụng phụ, giao trễ, hỏng hàng
    """
    t_lower = text.lower()

    # Phân biệt câu hỏi trước khi mua ("uống có bị buồn nôn không") với khiếu nại thực tế ("uống bị buồn nôn")
    is_pre_inquiry = any(k in t_lower for k in ["có bị", "có sợ", "uống có", "dùng có", "sợ bị", "sợ uống"])

    if not is_pre_inquiry and any(k in t_lower for k in ["khiếu nại", "đổi trả", "hỏng", "vỡ", "bắt đền", "phản ánh", "giao thiếu", "uống bị đau", "uống bị cồn cào", "giao sai"]):
        return "KHIEU_NAI", "Khiếu nại & Sự cố chất lượng"
    elif any(k in t_lower for k in ["đặt", "mua", "ship", "giao về", "giao cho", "lấy 1 hộp", "lấy 2 hộp", "địa chỉ", "chốt", "gửi về"]):
        return "DAT_HANG", "Đặt hàng & Chốt đơn"
    elif any(k in t_lower for k in ["giá", "bao nhiêu", "khuyến mãi", "combo", "ưu đãi", "chi phí", "bao tiền"]):
        return "HOI_GIA", "Hỏi giá & Chương trình ưu đãi"
    elif any(k in t_lower for k in ["uống thế nào", "cách dùng", "công dụng", "có tốt không", "uống lúc nào", "bầu", "sỏi", "táo bón", "tác dụng", "buồn nôn", "cồn cào", "tăng cân", "nổi mụn"]):
        return "TU_VAN_CHUYEN_MON", "Tư vấn chuyên môn y dược"
    return "KHAC", "Tìm hiểu thông tin chung"


def score_lead(has_phone: bool, inquiry_code: str, text: str) -> Tuple[str, int]:
    """
    Tính điểm xếp hạng độ nóng của Lead (Lead Score):
    - HOT: Đã có SĐT + hỏi mua hoặc hỏi giá (Tỉ lệ chốt dự kiến 85% - 98%)
    - WARM: Có SĐT hoặc hỏi sâu chuyên môn nhưng chưa để lại SĐT (Tỉ lệ chốt 50% - 75%)
    - COLD: Chỉ chào hỏi chung chung (Tỉ lệ chốt 20% - 35%)
    """
    if has_phone:
        if inquiry_code in ["DAT_HANG", "HOI_GIA"]:
            return "HOT", 95
        elif inquiry_code == "TU_VAN_CHUYEN_MON":
            return "HOT", 88
        elif inquiry_code == "KHIEU_NAI":
            return "HOT", 90  # Khẩn cấp xử lý sự cố
        return "WARM", 75
    else:
        if inquiry_code in ["DAT_HANG", "HOI_GIA"]:
            return "WARM", 65
        elif inquiry_code == "TU_VAN_CHUYEN_MON":
            return "WARM", 55
        return "COLD", 30


def generate_caresoft_summary(
    text: str,
    customer_name: str,
    phone: Optional[str],
    product: str,
    inquiry_name: str,
    lead_score: str
) -> Dict[str, str]:
    """
    Tạo thẻ tóm tắt 5 giây chuẩn mực cho nhân viên tổng đài CareSoft:
    - summary: Tóm tắt 2 câu về nhu cầu khách
    - pain_point: Rào cản/nỗi lo tâm lý chính
    - telesale_script: Lời thoại đề xuất khi Telesale CareSoft bốc máy gọi
    """
    t_lower = text.lower()
    
    # Xác định pain point
    if "sỏi" in t_lower or "cặn" in t_lower:
        pain_point = "Lo ngại uống canxi gây lắng cặn, sỏi thận hoặc vôi hóa bánh rau."
    elif "táo bón" in t_lower or "nóng" in t_lower or "mụn" in t_lower:
        pain_point = "Sợ uống vi chất bị nóng trong, nổi mụn hoặc táo bón nặng."
    elif "tăng cân" in t_lower:
        pain_point = "Sợ uống collagen bổ sung năng lượng làm tích nước, tăng cân không kiểm soát."
    elif "mất ngủ" in t_lower or "khó ngủ" in t_lower:
        pain_point = "Mất ngủ kéo dài, suy nhược thần kinh nhưng sợ dùng thuốc an thần tây y bị nhờn thuốc."
    elif "giá" in t_lower or "đắt" in t_lower:
        pain_point = "Băn khoăn về mức giá so với các sản phẩm thông thường trên thị trường."
    else:
        pain_point = "Cần chuyên viên y dược giải thích rõ cơ chế hấp thu và liệu trình tối ưu."

    # Tóm tắt hội thoại
    summary = (
        f"Khách hàng {customer_name} quan tâm dòng {product}. "
        f"Mục đích chính: {inquiry_name}. {pain_point}"
    )

    # Kịch bản telesale mở đầu
    phone_call_prefix = f"Dạ em chào chị {customer_name.split()[-1]}! Em là Dược sĩ bên Vistafa/DION gọi hỗ trợ chị về liệu trình {product} mà chị vừa nhắn tin qua kênh online..."
    if lead_score == "HOT":
        telesale_script = (
            f"'{phone_call_prefix} Em thấy chị đang quan tâm {pain_point.lower()} "
            f"Em xin phép giải thích nhanh trong 1 phút về cơ chế sinh học an toàn và hỗ trợ chuẩn bị đơn hàng kèm ưu đãi gửi tận nhà cho chị nhé ạ!'"
        )
    elif lead_score == "WARM":
        telesale_script = (
            f"'{phone_call_prefix} Em gửi chị thông tin chi tiết về cơ chế thành phần và bảng giá niêm yết. "
            f"Chị có thể để lại địa chỉ nhận hàng để bên em áp dụng chính sách miễn phí vận chuyển trong hôm nay ạ!'"
        )
    else:
        telesale_script = (
            f"'{phone_call_prefix} Dạ em xin phép gửi chị cẩm nang sức khỏe và hướng dẫn bổ sung vi chất đúng cách ạ.'"
        )

    return {
        "summary": summary,
        "pain_point": pain_point,
        "telesale_script": telesale_script
    }


def load_caresoft_leads() -> List[Dict[str, Any]]:
    """Tải danh sách lead từ file JSON hoặc khởi tạo dữ liệu mẫu nếu chưa có."""
    if not CARESOFT_LEADS_FILE.exists():
        seed_leads = get_seed_caresoft_leads()
        save_caresoft_leads(seed_leads)
        return seed_leads
    try:
        with open(CARESOFT_LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return get_seed_caresoft_leads()


def save_caresoft_leads(leads: List[Dict[str, Any]]) -> None:
    """Lưu danh sách lead vào file JSON."""
    CARESOFT_LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CARESOFT_LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)


def process_first_touch_chat(
    chat_text: str,
    channel: str = "FACEBOOK",
    customer_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    HÀM CỐT LÕI: Tiếp nhận đoạn chat ban đầu từ khách hàng,
    tự động phân loại, trích xuất thực thể, tính điểm Lead và lưu vào hệ thống CareSoft.
    """
    phone = extract_phone_number(chat_text)
    name = extract_customer_name(chat_text, customer_name)
    product = detect_interested_product(chat_text)
    inquiry_code, inquiry_name = classify_inquiry_type(chat_text)
    lead_score, conversion_rate = score_lead(phone is not None, inquiry_code, chat_text)
    
    summary_card = generate_caresoft_summary(
        text=chat_text,
        customer_name=name,
        phone=phone,
        product=product,
        inquiry_name=inquiry_name,
        lead_score=lead_score
    )

    lead_id = f"LEAD-CS-{datetime.now().strftime('%y%m%d%H%M%S')}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_lead = {
        "lead_id": lead_id,
        "customer_name": name,
        "phone": phone if phone else "Chưa cung cấp",
        "has_phone": phone is not None,
        "channel": channel.upper(),
        "product_interest": product,
        "inquiry_type": inquiry_name,
        "inquiry_code": inquiry_code,
        "lead_score": lead_score,
        "conversion_probability": f"{conversion_rate}%",
        "chat_snippet": chat_text.strip()[:300],
        "summary": summary_card["summary"],
        "pain_point": summary_card["pain_point"],
        "suggested_telesale_script": summary_card["telesale_script"],
        "status": "NEW",  # NEW, ASSIGNED, CONVERTED, LOST
        "assigned_agent": "Chờ phân bổ Telesale",
        "created_at": timestamp_str
    }

    # Lưu vào kho dữ liệu
    all_leads = load_caresoft_leads()
    all_leads.insert(0, new_lead)
    save_caresoft_leads(all_leads)

    return new_lead


def update_lead_status(lead_id: str, new_status: str, agent_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Cập nhật trạng thái xử lý Lead (CareSoft Ticket Status)."""
    leads = load_caresoft_leads()
    target = None
    for item in leads:
        if item.get("lead_id") == lead_id:
            item["status"] = new_status
            if agent_name:
                item["assigned_agent"] = agent_name
            target = item
            break
    if target:
        save_caresoft_leads(leads)
    return target


def export_caresoft_leads_csv() -> str:
    """
    Xuất danh sách Lead ra định dạng CSV chuẩn UTF-8 có BOM
    tương thích hoàn hảo để import 1-click vào CareSoft Contact Center & CRM.
    """
    leads = load_caresoft_leads()
    output = io.StringIO()
    # Ghi BOM để Excel hiển thị tiếng Việt không bị lỗi font
    output.write('\ufeff')
    
    writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "Mã Lead",
        "Tên Khách Hàng",
        "Số Điện Thoại",
        "Kênh Tiếp Nhận",
        "Sản Phẩm Quan Tâm",
        "Phân Loại Nhu Cầu",
        "Độ Nóng (Lead Score)",
        "Tỉ Lệ Chốt Đơn Dự Kiến",
        "Tóm Tắt Nhu Cầu (5s CareSoft)",
        "Nỗi Đau / Rào Cản Chính",
        "Kịch Bản Gọi Telesale Gợi Ý",
        "Trạng Thái Xử Lý",
        "Nhân Viên Phụ Trách",
        "Thời Gian Tiếp Nhận"
    ])

    for l in leads:
        writer.writerow([
            l.get("lead_id", ""),
            l.get("customer_name", ""),
            l.get("phone", ""),
            l.get("channel", ""),
            l.get("product_interest", ""),
            l.get("inquiry_type", ""),
            l.get("lead_score", ""),
            l.get("conversion_probability", ""),
            l.get("summary", ""),
            l.get("pain_point", ""),
            l.get("suggested_telesale_script", ""),
            l.get("status", ""),
            l.get("assigned_agent", ""),
            l.get("created_at", "")
        ])

    return output.getvalue()


def get_caresoft_metrics() -> Dict[str, Any]:
    """Tính toán các chỉ số KPI chuyển đổi của bộ tiếp nhận CareSoft."""
    leads = load_caresoft_leads()
    total = len(leads)
    if total == 0:
        return {
            "total_leads": 0,
            "leads_with_phone": 0,
            "phone_conversion_rate": "0%",
            "hot_leads_count": 0,
            "hot_leads_rate": "0%",
            "converted_count": 0,
            "converted_rate": "0%"
        }
    
    has_phone = sum(1 for l in leads if l.get("has_phone") or (l.get("phone") and l.get("phone") != "Chưa cung cấp"))
    hot_leads = sum(1 for l in leads if l.get("lead_score") == "HOT")
    converted = sum(1 for l in leads if l.get("status") == "CONVERTED")

    return {
        "total_leads": total,
        "leads_with_phone": has_phone,
        "phone_conversion_rate": f"{round((has_phone / total) * 100, 1)}%",
        "hot_leads_count": hot_leads,
        "hot_leads_rate": f"{round((hot_leads / total) * 100, 1)}%",
        "converted_count": converted,
        "converted_rate": f"{round((converted / total) * 100, 1)}%"
    }


def get_seed_caresoft_leads() -> List[Dict[str, Any]]:
    """Dữ liệu mẫu thực chiến cho buổi trình diễn PoC với đối tác Vistafa."""
    return [
        {
            "lead_id": "LEAD-CS-26101901",
            "customer_name": "Nguyễn Thị Thu Trang",
            "phone": "0983112233",
            "has_phone": True,
            "channel": "ZALO_OA",
            "product_interest": "Calci Complex (Vistafa) / Cal-Mom",
            "inquiry_type": "Đặt hàng & Chốt đơn",
            "inquiry_code": "DAT_HANG",
            "lead_score": "HOT",
            "conversion_probability": "95%",
            "chat_snippet": "Chào shop, mình đang bầu tháng thứ 4, muốn mua Calci Complex. Uống cái này có sợ bị đọng sỏi thận hay vôi hóa không shop? Nếu êm bụng cho mình đặt trước 2 hộp về số 15 Lê Văn Lương, SĐT mình 0983112233 nhé.",
            "summary": "Khách hàng Nguyễn Thị Thu Trang quan tâm dòng Calci Complex (Vistafa) / Cal-Mom. Mục đích chính: Đặt hàng & Chốt đơn. Lo ngại uống canxi gây lắng cặn, sỏi thận hoặc vôi hóa bánh rau.",
            "pain_point": "Lo ngại uống canxi gây lắng cặn, sỏi thận hoặc vôi hóa bánh rau.",
            "suggested_telesale_script": "'Dạ em chào chị Trang! Em là Dược sĩ bên Vistafa gọi hỗ trợ chị về liệu trình Calci Complex mà chị vừa nhắn qua Zalo. Sản phẩm dùng canxi tảo biển đỏ kết hợp Vitamin K2 MK-7 định hướng canxi thẳng vào xương cho bé, hoàn toàn không gây lắng cặn sỏi thận. Em xin phép xác nhận gửi 2 hộp về số 15 Lê Văn Lương cho chị nhé ạ!'",
            "status": "CONVERTED",
            "assigned_agent": "DS. Hoàng Lan (CareSoft)",
            "created_at": "2026-10-19 14:15:20"
        },
        {
            "lead_id": "LEAD-CS-26101902",
            "customer_name": "Trần Mai Linh",
            "phone": "0915667788",
            "has_phone": True,
            "channel": "FACEBOOK",
            "product_interest": "Collagen Powder (Vistafa)",
            "inquiry_type": "Tư vấn chuyên môn y dược",
            "inquiry_code": "TU_VAN_CHUYEN_MON",
            "lead_score": "HOT",
            "conversion_probability": "90%",
            "chat_snippet": "Cho mình hỏi bột Collagen Powder của Vistafa một hộp dùng được bao lâu? Mình rất sợ uống collagen bị nổi mụn với tăng cân. Có gì gọi tư vấn giúp mình qua số 0915667788 vào buổi chiều nhé.",
            "summary": "Khách hàng Trần Mai Linh quan tâm dòng Collagen Powder (Vistafa). Mục đích chính: Tư vấn chuyên môn y dược. Sợ uống collagen bổ sung năng lượng làm tích nước, tăng cân không kiểm soát.",
            "pain_point": "Sợ uống collagen bổ sung năng lượng làm tích nước, tăng cân không kiểm soát.",
            "suggested_telesale_script": "'Dạ em chào chị Linh! Em là chuyên viên Vistafa gọi từ tổng đài CareSoft tư vấn dòng Collagen Powder theo hẹn ạ. Dòng collagen bên em là dạng thủy phân peptide từ cá biển sâu với phân tử siêu nhỏ, không chứa chất béo và không gây tăng cân hay nổi mụn như collagen thường. Chị uống 1 gói mỗi tối trước khi ngủ là da căng mịn rất rõ rệt ạ!'",
            "status": "ASSIGNED",
            "assigned_agent": "Nguyễn Hữu Tuấn (Telesale)",
            "created_at": "2026-10-19 14:35:10"
        },
        {
            "lead_id": "LEAD-CS-26101903",
            "customer_name": "Lê Hoàng Nam",
            "phone": "0904223344",
            "has_phone": True,
            "channel": "WEBSITE_CHAT",
            "product_interest": "Sleep Well (Vistafa)",
            "inquiry_type": "Đặt hàng & Chốt đơn",
            "inquiry_code": "DAT_HANG",
            "lead_score": "HOT",
            "conversion_probability": "92%",
            "chat_snippet": "Bác bị mất ngủ 2 năm nay rồi, đêm chỉ chợp mắt được 2 tiếng. Uống Sleep Well có ngủ sâu được không và có bị phụ thuộc thuốc không cháu? Bác ở Cầu Giấy, gọi bác số 0904 223 344 nhé.",
            "summary": "Khách hàng Lê Hoàng Nam quan tâm dòng Sleep Well (Vistafa). Mục đích chính: Đặt hàng & Chốt đơn. Mất ngủ kéo dài, suy nhược thần kinh nhưng sợ dùng thuốc an thần tây y bị nhờn thuốc.",
            "pain_point": "Mất ngủ kéo dài, suy nhược thần kinh nhưng sợ dùng thuốc an thần tây y bị nhờn thuốc.",
            "suggested_telesale_script": "'Dạ cháu chào bác Nam ạ! Cháu gọi từ tổng đài y dược Vistafa hỗ trợ bác về Sleep Well. Dòng này chiết xuất 100% thảo mộc tự nhiên Lạc tiên, Tâm sen và Melatonin tự nhiên, giúp phục hồi nhịp sinh học tự nhiên chứ không phải thuốc ngủ hóa dược nên sáng dậy đầu óc rất nhẹ nhõm, không bị nhờn thuốc đâu bác ạ!'",
            "status": "NEW",
            "assigned_agent": "Chờ phân bổ Telesale",
            "created_at": "2026-10-19 15:02:45"
        },
        {
            "lead_id": "LEAD-CS-26101904",
            "customer_name": "Vũ Bích Ngọc",
            "phone": "Chưa cung cấp",
            "has_phone": False,
            "channel": "FACEBOOK",
            "product_interest": "Calci Complex (Vistafa) / Cal-Mom",
            "inquiry_type": "Hỏi giá & Chương trình ưu đãi",
            "inquiry_code": "HOI_GIA",
            "lead_score": "WARM",
            "conversion_probability": "65%",
            "chat_snippet": "Shop ơi hộp Calci Complex giá bao nhiêu tiền một hộp thế? Có chương trình khuyến mãi mua combo 2 hộp không shop?",
            "summary": "Khách hàng Vũ Bích Ngọc quan tâm dòng Calci Complex (Vistafa) / Cal-Mom. Mục đích chính: Hỏi giá & Chương trình ưu đãi. Băn khoăn về mức giá so với các sản phẩm thông thường trên thị trường.",
            "pain_point": "Băn khoăn về mức giá so với các sản phẩm thông thường trên thị trường.",
            "suggested_telesale_script": "'Dạ chào bạn! Hộp Calci Complex 60 viên giá niêm yết 320.000đ dùng được 2 tháng, tính ra mỗi ngày chỉ 5.000đ. Đang có ưu đãi combo 2 hộp giảm 10% kèm quà tặng bình giữ nhiệt. Bạn để lại SĐT và địa chỉ để shop giữ ưu đãi nhé!'",
            "status": "NEW",
            "assigned_agent": "Chờ phân bổ Telesale",
            "created_at": "2026-10-19 15:20:18"
        },
        {
            "lead_id": "LEAD-CS-26101905",
            "customer_name": "Phạm Quốc Huy",
            "phone": "0977889900",
            "has_phone": True,
            "channel": "ZALO_OA",
            "product_interest": "Sleep Well (Vistafa)",
            "inquiry_type": "Đặt hàng & Chốt đơn",
            "inquiry_code": "DAT_HANG",
            "lead_score": "HOT",
            "conversion_probability": "95%",
            "chat_snippet": "Bên mình có ship vào Đà Nẵng không ạ? Mình muốn lấy thử 1 hộp Sleep Well uống thử nghiệm xem có đỡ căng thẳng không. Giao về Hải Châu, SĐT 0977889900.",
            "summary": "Khách hàng Phạm Quốc Huy quan tâm dòng Sleep Well (Vistafa). Mục đích chính: Đặt hàng & Chốt đơn. Mất ngủ kéo dài, suy nhược thần kinh nhưng sợ dùng thuốc an thần tây y bị nhờn thuốc.",
            "pain_point": "Mất ngủ kéo dài, suy nhược thần kinh nhưng sợ dùng thuốc an thần tây y bị nhờn thuốc.",
            "suggested_telesale_script": "'Dạ chào anh Huy! Vistafa có giao hàng miễn phí tận nơi tại Đà Nẵng trong 2 ngày ạ. Đơn 1 hộp Sleep Well của anh đã được tiếp nhận trên hệ thống CareSoft, bên em sẽ gửi mã vận đơn qua Zalo cho anh ngay ạ!'",
            "status": "CONVERTED",
            "assigned_agent": "DS. Hoàng Lan (CareSoft)",
            "created_at": "2026-10-19 15:45:00"
        },
        {
            "lead_id": "LEAD-CS-26101906",
            "customer_name": "Đỗ Thu Hà",
            "phone": "0966554433",
            "has_phone": True,
            "channel": "HOTLINE",
            "product_interest": "Sắt Hữu Cơ Chelate Fero-Plus",
            "inquiry_type": "Khiếu nại & Sự cố chất lượng",
            "inquiry_code": "KHIEU_NAI",
            "lead_score": "HOT",
            "conversion_probability": "90%",
            "chat_snippet": "Hôm trước tôi mua hộp sắt Fero-Plus uống lúc đói bị cồn cào ruột nhẹ, nhân viên kiểm tra lại giúp tôi xem uống vào giờ nào cho êm. Số tôi 0966554433.",
            "summary": "Khách hàng Đỗ Thu Hà quan tâm dòng Sắt Hữu Cơ Chelate Fero-Plus. Mục đích chính: Khiếu nại & Sự cố chất lượng. Sợ uống vi chất bị nóng trong, nổi mụn hoặc táo bón nặng.",
            "pain_point": "Sợ uống vi chất bị nóng trong, nổi mụn hoặc táo bón nặng.",
            "suggested_telesale_script": "'Dạ em chào chị Hà! Em là Dược sĩ chuyên môn bên tổng đài chăm sóc gọi lại cho chị ngay đây ạ. Sắt Fero-Plus dù là sắt chelate hữu cơ rất êm nhưng chị không nên uống lúc bụng đang đói cồn cào ạ. Chị chuyển sang uống sau bữa trưa 1 tiếng với 1 cốc nước đầy hoặc nước cam giúp em là sẽ hết hẳn cảm giác cồn cào chị nhé!'",
            "status": "ASSIGNED",
            "assigned_agent": "DS. Trần Văn Hưng",
            "created_at": "2026-10-19 16:05:12"
        }
    ]
