import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from modules.claims_hub import get_product_by_sku, get_active_claims
from modules.ai_compliance_agent import generate_inline_highlighted_html

PROHIBITED_PATH = Path(__file__).resolve().parent.parent / "data" / "prohibited_terms.json"

def load_prohibited_terms() -> List[Dict[str, Any]]:
    if not PROHIBITED_PATH.exists():
        return []
    with open(PROHIBITED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("prohibited_phrases", [])

def extract_clean_body_and_disclaimer(text: str) -> Tuple[str, bool, str]:
    """
    Bóc tách nội dung chính (body) và câu cảnh báo bắt buộc (disclaimer).
    Giúp tránh trường hợp câu disclaimer chuẩn ("Thực phẩm này không phải là thuốc...")
    bị bắt nhầm từ khóa 'chữa bệnh' hoặc 'thay thế thuốc'.
    """
    lines = text.splitlines()
    body_lines = []
    disclaimer_found = False
    disclaimer_text = ""

    for line in lines:
        l_lower = line.lower()
        if "thực phẩm này không phải là thuốc" in l_lower:
            disclaimer_found = True
            disclaimer_text = line.strip()
        else:
            body_lines.append(line)

    body_text = "\n".join(body_lines)
    return body_text, disclaimer_found, disclaimer_text

def validate_content_compliance(text: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Quét kiểm tra vi phạm trên phần thân bài (đã bóc tách câu disclaimer).
    Lọc bỏ các vi phạm trùng lặp/bao hàm để báo cáo sắc bén, chuẩn xác nhất.
    """
    body_text, _, _ = extract_clean_body_and_disclaimer(text)
    body_lower = body_text.lower()
    
    terms = load_prohibited_terms()
    # Sắp xếp các từ theo độ dài giảm dần để ưu tiên cụm từ dài nhất trước
    sorted_terms = sorted(terms, key=lambda x: len(x["term"]), reverse=True)
    
    matched = []
    matched_terms_set = set()
    occupied_indices = set()
    
    for item in sorted_terms:
        term = item["term"].lower()
        start = 0
        while True:
            idx = body_lower.find(term, start)
            if idx == -1:
                break
            term_indices = set(range(idx, idx + len(term)))
            if not term_indices.issubset(occupied_indices):
                occupied_indices.update(term_indices)
                if item["term"] not in matched_terms_set:
                    matched.append(item)
                    matched_terms_set.add(item["term"])
            start = idx + 1
            
    return (len(matched) == 0), matched

def deep_audit_radar(text: str, sku: str = "DION-CAL-MOM") -> Dict[str, Any]:
    """
    Hệ thống Radar Thẩm định 4 Lớp Chuyên sâu theo Nghị định 342/2025/NĐ-CP & Luật Dược:
    Lớp 1: Từ cấm y dược & Tuyên bố chữa bệnh (Medical Treatment Claims)
    Lớp 2: Thần thánh hóa & Khoa học giả tưởng (Pseudoscience & Miracle Claims)
    Lớp 3: Hạ thấp tân dược & Cam kết quá mức (Denigrating Medicine & Absolute Exaggeration)
    Lớp 4: Cảnh báo bắt buộc (Disclaimer) & Giới hạn phạm vi công dụng TPBVSK
    """
    body_text, has_disclaimer, disclaimer_line = extract_clean_body_and_disclaimer(text)
    is_valid, all_violations = validate_content_compliance(text)
    product = get_product_by_sku(sku)
    
    # Phân loại vi phạm theo 3 nhóm cốt lõi
    med_violations = [v for v in all_violations if v.get("category") == "MEDICAL_TREATMENT"]
    miracle_violations = [v for v in all_violations if v.get("category") == "PSEUDOSCIENCE_MIRACLE"]
    exaggeration_violations = [v for v in all_violations if v.get("category") in ["DENIGRATING_MEDICINE", "EXAGGERATION_ABSOLUTE"]]
    
    # 1. Điểm Lớp 1: Từ cấm y dược (0 - 25)
    med_deduction = sum(15 if v.get("severity") == "CRITICAL" else 8 for v in med_violations)
    prohibited_score = max(0, 25 - med_deduction)
    
    # 2. Điểm Lớp 2: Thần thánh hóa & Giả khoa học (0 - 25)
    miracle_deduction = sum(15 if v.get("severity") == "CRITICAL" else 8 for v in miracle_violations)
    miracle_score = max(0, 25 - miracle_deduction)
    
    # 3. Điểm Lớp 3: Hạ thấp thuốc Tây & Cam kết quá đà (0 - 25)
    exagg_deduction = sum(15 if v.get("severity") == "CRITICAL" else 8 for v in exaggeration_violations)
    exaggeration_score = max(0, 25 - exagg_deduction)
    
    # 4. Điểm Lớp 4: Disclaimer & Phạm vi TPBVSK (0 - 25)
    disclaimer_score = 15 if has_disclaimer else 0
    has_support_wording = any(w in body_text.lower() for w in ["hỗ trợ", "bổ sung", "duy trì", "giúp"])
    boundary_score = 10 if (has_support_wording and len(med_violations) == 0) else (5 if has_support_wording else 0)
    layer4_score = disclaimer_score + boundary_score
    
    # Tính tổng điểm thô
    raw_score = prohibited_score + miracle_score + exaggeration_score + layer4_score
    
    # ĐÁNH GIÁ MỨC ĐỘ NGUY HIỂM & ÁP DỤNG TRẦN PHẠT NẶNG (STRICT SEVERITY PENALTY)
    critical_violations = [v for v in all_violations if v.get("severity") == "CRITICAL"]
    denigrating_violations = [v for v in all_violations if v.get("category") == "DENIGRATING_MEDICINE"]
    
    total_score = raw_score
    is_severe_hazard = False
    hazard_reason = ""
    
    if len(denigrating_violations) > 0:
        is_severe_hazard = True
        hazard_reason = "Hành vi xúi giục bệnh nhân bỏ thuốc tân dược hoặc hạ thấp thuốc kê đơn là vi phạm pháp luật đặc biệt nguy hiểm."
        total_score = min(total_score, 10)
    elif len(critical_violations) >= 3:
        is_severe_hazard = True
        hazard_reason = f"Phát hiện {len(critical_violations)} vi phạm nghiêm trọng (tuyên bố bách bệnh, thần thánh hóa, khoa học giả tưởng). Nguy cơ tước giấy phép quảng cáo."
        total_score = min(total_score, 15)
    elif len(all_violations) >= 5:
        total_score = min(total_score, 30)
    elif not has_disclaimer:
        total_score = min(total_score, 70)
        
    if total_score >= 85 and has_disclaimer and len(all_violations) == 0:
        status = "ĐẠT CHUẨN NGHỊ ĐỊNH 342"
        badge_type = "COMPLIANT"
    elif is_severe_hazard:
        status = "VI PHẠM ĐẶC BIỆT NGHIÊM TRỌNG (RỦI RO THU HỒI GPQC & XỬ PHẠT TỐI ĐA)"
        badge_type = "CRITICAL_HAZARD"
    else:
        status = "VI PHẠM QUY ĐỊNH QUẢNG CÁO"
        badge_type = "VIOLATION"

    # Định dạng danh sách vi phạm cho bộ tạo HTML tô đỏ
    semantic_formatted = []
    for v in all_violations:
        semantic_formatted.append({
            "quote": v["term"],
            "category": v.get("category", "Vi phạm quy định"),
            "legal_basis": "Nghị định 342/2025/NĐ-CP & Luật Dược",
            "severity": v.get("severity", "HIGH"),
            "explanation": v.get("reason", "Cụm từ không được phép sử dụng trong quảng cáo thực phẩm bảo vệ sức khỏe"),
            "compliant_suggestion": v.get("suggestion", "Thay thế bằng thuật ngữ bổ sung chức năng dinh dưỡng")
        })

    if not has_disclaimer:
        semantic_formatted.append({
            "quote": "[Cuối bài viết thiếu câu cảnh báo]",
            "category": "Thiếu Câu Cảnh Báo Bắt Buộc",
            "legal_basis": "Khoản 2 Điều 5 Nghị định 342/2025/NĐ-CP",
            "severity": "HIGH",
            "explanation": "Bắt buộc phải có câu: 'Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh'.",
            "compliant_suggestion": "Đính kèm câu Disclaimer bắt buộc vào cuối nội dung quảng cáo."
        })

    highlighted_html = generate_inline_highlighted_html(text, semantic_formatted)
        
    return {
        "total_score": total_score,
        "status": status,
        "badge_type": badge_type,
        "is_compliant": (badge_type == "COMPLIANT"),
        "is_severe_hazard": is_severe_hazard,
        "hazard_reason": hazard_reason,
        "critical_count": len(critical_violations),
        "total_violations_count": len(all_violations),
        "highlighted_html": highlighted_html,
        "sku": sku,
        "product_name": product["name"] if product else sku,
        "layers": {
            "prohibited": {
                "score": prohibited_score,
                "max": 25,
                "violations": [v["term"] for v in med_violations],
                "count": len(med_violations)
            },
            "miracle": {
                "score": miracle_score,
                "max": 25,
                "violations": [v["term"] for v in miracle_violations],
                "count": len(miracle_violations)
            },
            "exaggeration": {
                "score": exaggeration_score,
                "max": 25,
                "violations": [v["term"] for v in exaggeration_violations],
                "count": len(exaggeration_violations)
            },
            "disclaimer": {
                "score": disclaimer_score,
                "max": 15,
                "present": has_disclaimer
            },
            "boundary": {
                "score": boundary_score,
                "max": 10,
                "valid_wording": has_support_wording and len(med_violations) == 0
            }
        },
        "violations_detail": all_violations,
        "med_violations": med_violations,
        "miracle_violations": miracle_violations,
        "exaggeration_violations": exaggeration_violations
    }

def auto_fix_compliance(text: str, sku: str = "DION-CAL-MOM") -> Dict[str, Any]:
    """
    TÍNH NĂNG ĐỘT PHÁ: Tự động sửa bài viết vi phạm thành bài viết chuẩn luật NĐ 342/2025
    và tuân thủ hồ sơ công bố của sản phẩm (SKU Grounding):
    - Thay thế các từ cấm y dược bằng từ ngữ được pháp luật cho phép.
    - Chuẩn hóa: Không ghi 'Cục ATTP chứng nhận' -> ghi 'CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:'.
    - Chuẩn hóa cơ chế hấp thu: Thêm 'Hỗ trợ' đứng trước.
    - Bổ sung đối tượng phụ nữ mang thai / cho con bú đối với dòng Cal-Mom.
    - Đảm bảo câu Disclaimer bắt buộc chuẩn xác.
    """
    fixed_text = text
    changes_made = []
    product = get_product_by_sku(sku)
    
    # Danh sách chuẩn hóa ưu tiên từ cụm dài đến từ ngắn
    replacements_chain = [
        ("Được Cục An toàn thực phẩm chứng nhận", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("được cục an toàn thực phẩm chứng nhận", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("Cục An toàn thực phẩm chứng nhận", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("Được Cục ATTP chứng nhận", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("được cục attp chứng nhận", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("Cục ATTP chứng nhận", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("Được Cục ATTP phê duyệt", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("Cục ATTP phê duyệt", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("Được Bộ Y tế chứng nhận", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("Bộ Y tế chứng nhận", "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:"),
        ("là thuốc đặc trị", "là giải pháp hỗ trợ chuyên biệt"),
        ("thuốc đặc trị", "giải pháp hỗ trợ chuyên biệt"),
        ("là thuốc điều trị", "là sản phẩm hỗ trợ"),
        ("thuốc điều trị", "sản phẩm hỗ trợ"),
        ("trị dứt điểm", "hỗ trợ kiểm soát tốt"),
        ("chữa dứt điểm", "hỗ trợ kiểm soát rõ rệt"),
        ("trị dứt", "hỗ trợ kiểm soát"),
        ("chữa khỏi", "hỗ trợ phục hồi"),
        ("thuốc chữa bệnh", "sản phẩm bảo vệ sức khỏe"),
        ("là thuốc", "là giải pháp bổ sung dinh dưỡng"),
        ("Đột phá y học thế kỷ 21: dưỡng chất tự nhiên trường thọ", "Giải pháp khoa học dinh dưỡng: Dưỡng chất tự nhiên cho thể trạng khỏe mạnh"),
        ("Quét sạch bách bệnh chỉ sau đúng 7 ngày", "Hỗ trợ nâng cao sức đề kháng toàn diện khi duy trì đều đặn"),
        ("quét sạch bách bệnh", "hỗ trợ chăm sóc sức khỏe toàn diện"),
        ("bách bệnh", "sức khỏe toàn diện"),
        ("chỉ sau đúng 7 ngày", "theo liệu trình khuyến nghị từ chuyên gia"),
        ("sau đúng 7 ngày", "sau thời gian sử dụng đều đặn"),
        ("sau 7 ngày", "khi duy trì đều đặn"),
        ("viên uống Nano Diệu Dược", "viên uống Thực Phẩm Bảo Vệ Sức Khỏe DION"),
        ("Nano Diệu Dược", "TPBVSK DION"),
        ("diệu dược", "công thức dưỡng chất chuẩn hóa"),
        ("thần dược", "giải pháp bổ sung dinh dưỡng"),
        ("tiên dược", "dưỡng chất thiên nhiên"),
        ("thảo mộc ngàn năm trên đỉnh Fansipan", "chiết xuất thảo mộc tự nhiên chọn lọc"),
        ("thảo mộc ngàn năm", "chiết xuất thảo mộc chọn lọc"),
        ("giải quyết tận gốc rễ mọi căn bệnh mãn tính", "hỗ trợ cải thiện thể trạng và tăng cường sức khỏe"),
        ("giải quyết tận gốc rễ", "hỗ trợ cải thiện thể trạng từ bên trong"),
        ("tận gốc rễ", "từ sâu bên trong"),
        ("tận gốc", "bền vững"),
        ("Công nghệ bẻ khóa tế bào lượng tử giúp thẩm thấu nhanh gấp 10.000 lần thuốc Tây thông thường", "Công nghệ sinh học vi bao giúp hỗ trợ tăng cường khả năng hấp thu Canxi và khoáng chất"),
        ("bẻ khóa tế bào lượng tử", "công nghệ sinh học vi bao định hướng"),
        ("bẻ khóa tế bào", "hỗ trợ hấp thu tế bào"),
        ("lượng tử", "vi phân tử sinh học"),
        ("gấp 10.000 lần thuốc Tây thông thường", "tối ưu hóa khả năng hấp thu"),
        ("gấp 10.000 lần", "vượt trội so với thông thường"),
        ("gấp hàng ngàn lần", "tối ưu hấp thu"),
        ("không tái phát", "hỗ trợ duy trì thể trạng dẻo dai"),
        ("không tác dụng phụ", "lành tính và an toàn khi sử dụng theo hướng dẫn"),
        ("Hàng triệu bệnh nhân khắp thế giới đã vứt bỏ thuốc men nhờ siêu phẩm này", "Hàng ngàn người tiêu dùng đã an tâm bổ sung dinh dưỡng chất lượng cao mỗi ngày"),
        ("vứt bỏ thuốc men", "đồng hành cùng chế độ chăm sóc y tế"),
        ("vứt bỏ thuốc", "kết hợp cùng lối sống lành mạnh"),
        ("bỏ thuốc tây", "kết hợp chỉ định chuyên môn của bác sĩ"),
        ("siêu phẩm", "sản phẩm chất lượng cao"),
        ("trẻ hóa 10 tuổi, thọ thêm 20 năm", "hỗ trợ làm chậm quá trình lão hóa và nâng cao chất lượng cuộc sống"),
        ("trẻ hóa 10 tuổi", "hỗ trợ làm chậm quá trình lão hóa"),
        ("thọ thêm 20 năm", "nâng cao chất lượng cuộc sống khỏe mạnh"),
        ("xóa sổ vĩnh viễn mầm mống bệnh tật", "hỗ trợ tăng cường miễn dịch tự nhiên trước các tác nhân oxy hóa"),
        ("xóa sổ vĩnh viễn", "hạn chế tối đa nguy cơ ảnh hưởng sức khỏe"),
        ("xóa sổ", "hỗ trợ giảm thiểu"),
        ("mầm mống bệnh tật", "các gốc tự do oxy hóa"),
        ("trường thọ", "sức khỏe dẻo dai"),
        ("đột phá y học thế kỷ", "tiến bộ khoa học dinh dưỡng"),
        ("tối ưu hóa khả năng hấp thu", "hỗ trợ tăng cường khả năng hấp thu Canxi và khoáng chất"),
        ("tối ưu khả năng hấp thu", "hỗ trợ tăng cường khả năng hấp thu Canxi"),
        ("chữa bệnh", "hỗ trợ cải thiện sức khỏe"),
        ("điều trị", "hỗ trợ chăm sóc"),
        ("đặc trị", "hỗ trợ chuyên biệt"),
        ("khỏi hẳn", "hỗ trợ phục hồi thể trạng"),
        ("dứt điểm", "kiểm soát tốt"),
        ("tốt nhất", "chất lượng cao"),
        ("cam kết", "được kiểm chứng"),
        ("100%", "rõ rệt"),
        ("tuyệt đối", "tối ưu"),
        ("thuốc", "sản phẩm")
    ]
    
    for old_w, new_w in replacements_chain:
        if re.search(re.escape(old_w), fixed_text, flags=re.IGNORECASE):
            fixed_text = re.sub(re.escape(old_w), new_w, fixed_text, flags=re.IGNORECASE)
            changes_made.append(f"Chuẩn hóa '{old_w}' ➔ '{new_w}'")

    # Kiểm tra đối tượng phụ nữ mang thai đối với sản phẩm dòng MOM
    is_mom = product and ("mom" in product.get("sku", "").lower() or "mom" in product.get("name", "").lower())
    if is_mom and not any(k in fixed_text.lower() for k in ["mang thai", "mẹ bầu", "cho con bú"]):
        fixed_text = fixed_text.strip() + "\n\n📦 Thích hợp cho: Phụ nữ chuẩn bị mang thai, đang mang thai và cho con bú; người lớn tuổi, người có nguy cơ loãng xương."
        changes_made.append("Bổ sung đối tượng cốt lõi: Phụ nữ mang thai, cho con bú & người lớn tuổi theo hồ sơ 8892/2025/ĐKSP")
            
    # Bổ sung câu Disclaimer nếu chưa có
    disclaimer = product.get("mandatory_disclaimer") if product else "Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh."
    
    if "thực phẩm này không phải là thuốc" not in fixed_text.lower():
        fixed_text = fixed_text.strip() + f"\n\n---\n⚠️ {disclaimer}"
        changes_made.append("Tự động đính kèm câu Disclaimer bắt buộc theo NĐ 342/2025")
        
    audit_after = deep_audit_radar(fixed_text, sku=sku)
    
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

💡 CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:
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
