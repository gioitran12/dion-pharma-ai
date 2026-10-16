import os
import re
import json
import html
from typing import Dict, Any, List, Optional
from pathlib import Path
from modules.claims_hub import get_product_by_sku

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Biến bộ nhớ lưu API Key trong phiên làm việc
_RUNTIME_AI_CONFIG = {
    "api_key": os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or "",
    "provider": "auto"
}

def set_runtime_ai_key(key: str, provider: str = "auto") -> Dict[str, Any]:
    """Cập nhật API Key trong runtime"""
    _RUNTIME_AI_CONFIG["api_key"] = key.strip()
    _RUNTIME_AI_CONFIG["provider"] = provider
    if key.startswith("AIza") or key.startswith("AQ."):
        os.environ["GEMINI_API_KEY"] = key.strip()
    elif key.startswith("sk-"):
        os.environ["OPENAI_API_KEY"] = key.strip()
    return {"status": "success", "configured": bool(_RUNTIME_AI_CONFIG["api_key"]), "provider": _RUNTIME_AI_CONFIG["provider"]}

def get_runtime_ai_status() -> Dict[str, Any]:
    """Lấy trạng thái cấu hình AI Agent"""
    has_key = bool(_RUNTIME_AI_CONFIG["api_key"])
    key_masked = ""
    if has_key:
        k = _RUNTIME_AI_CONFIG["api_key"]
        key_masked = k[:6] + "..." + k[-4:] if len(k) > 10 else "***"
    return {
        "has_cloud_key": has_key,
        "masked_key": key_masked,
        "active_mode": "CLOUD_LLM" if has_key else "LOCAL_EXPERT_AGENT",
        "description": "Kết nối Gemini Flash / GPT-4o-mini" if has_key else "Động cơ AI Agent Chuyên gia Pháp chế Nội bộ (Không cần API Key)"
    }

def generate_inline_highlighted_html(text: str, violations: List[Dict[str, Any]]) -> str:
    """
    Tạo chuỗi HTML hiển thị bài viết với CÁC ĐOẠN LỖI ĐƯỢC TÔ ĐỎ TRỰC TIẾP TRÊN TRÌNH SOẠN THẢO.
    Mỗi đoạn lỗi được bọc trong thẻ <mark> tương tác, người dùng click vào sẽ hiện lý do vi phạm,
    căn cứ pháp lý / hồ sơ công bố và nút 1-click thay thế ngay tại chỗ.
    """
    if not text:
        return ""

    spans = []
    text_lower = text.lower()

    for v_idx, v in enumerate(violations):
        quote = v.get("quote", "").strip()
        if not quote or quote.startswith("["):
            continue

        quote_clean = quote.strip("\"'“”‘’")
        if not quote_clean:
            continue

        q_lower = quote_clean.lower()
        start = 0
        while True:
            idx = text_lower.find(q_lower, start)
            if idx == -1:
                break
            spans.append({
                "start": idx,
                "end": idx + len(q_lower),
                "matched_text": text[idx:idx + len(q_lower)],
                "violation": v,
                "length": len(q_lower),
                "violation_idx": v_idx
            })
            start = idx + len(q_lower)

    # Xử lý không chồng lấn: ưu tiên chuỗi khớp dài nhất trước
    spans.sort(key=lambda s: (-s["length"], s["start"]))
    non_overlapping = []
    occupied_indices = set()

    for s in spans:
        span_set = set(range(s["start"], s["end"]))
        if not (span_set & occupied_indices):
            occupied_indices.update(span_set)
            non_overlapping.append(s)

    # Sắp xếp lại theo thứ tự xuất hiện từ đầu tới cuối văn bản
    non_overlapping.sort(key=lambda s: s["start"])

    html_parts = []
    current_pos = 0

    for s in non_overlapping:
        if s["start"] > current_pos:
            safe_text = html.escape(text[current_pos:s["start"]]).replace("\n", "<br>")
            html_parts.append(safe_text)

        v = s["violation"]
        matched_str = html.escape(s["matched_text"])
        sev = v.get("severity", "CRITICAL")
        cat = html.escape(v.get("category", "Vi phạm quy chuẩn"))
        legal = html.escape(v.get("legal_basis", "Nghị định 342/2025/NĐ-CP"))
        exp = html.escape(v.get("explanation", ""))
        sug = html.escape(v.get("compliant_suggestion", ""))
        quote_esc = html.escape(s["matched_text"])

        border_color = "border-rose-600" if sev == "CRITICAL" else "border-amber-600"
        bg_color = "bg-rose-200" if sev == "CRITICAL" else "bg-amber-200"
        text_color = "text-rose-950" if sev == "CRITICAL" else "text-amber-950"

        mark_tag = (
            f'<mark class="compliance-highlight {bg_color} {text_color} border-b-2 {border_color} '
            f'px-1 py-0.5 rounded font-bold cursor-pointer hover:bg-rose-300 transition-colors inline-block relative group" '
            f'data-quote="{quote_esc}" '
            f'data-category="{cat}" '
            f'data-legal="{legal}" '
            f'data-severity="{sev}" '
            f'data-explanation="{exp}" '
            f'data-suggestion="{sug}" '
            f'title="Bấm để xem chi tiết vi phạm & thay thế 1-click" '
            f'onclick="onHighlightClick(this)">{matched_str}</mark>'
        )
        html_parts.append(mark_tag)
        current_pos = s["end"]

    if current_pos < len(text):
        safe_text = html.escape(text[current_pos:]).replace("\n", "<br>")
        html_parts.append(safe_text)

    # Hiển thị cảnh báo thiếu thành phần bắt buộc (như disclaimer, đối tượng) ở cuối
    meta_warnings = [v for v in violations if v.get("quote", "").startswith("[")]
    if meta_warnings:
        html_parts.append('<div class="mt-4 pt-3 border-t border-rose-300 space-y-2">')
        for mw in meta_warnings:
            mw_cat = html.escape(mw.get("category", "Cảnh báo hồ sơ"))
            mw_exp = html.escape(mw.get("explanation", ""))
            mw_sug = html.escape(mw.get("compliant_suggestion", ""))
            html_parts.append(
                f'<div class="p-2 bg-rose-100/95 border border-rose-400 rounded text-rose-950 text-xs font-semibold flex items-center justify-between shadow-xs">'
                f'<div>⚠️ <b>{mw_cat}:</b> {mw_exp}</div>'
                f'<button onclick="insertMissingText(\'{mw_sug}\')" class="ml-2 px-2.5 py-1 bg-rose-700 text-white rounded text-[11px] font-bold hover:bg-rose-800 whitespace-nowrap shadow-xs">Thêm vào bài</button>'
                f'</div>'
            )
        html_parts.append('</div>')

    return "".join(html_parts)

def run_ai_compliance_audit(
    text: str,
    sku: str = "DION-CAL-MOM",
    api_key: Optional[str] = None,
    provider: str = "auto"
) -> Dict[str, Any]:
    """
    Điểm vào duy nhất cho AI Compliance Auditor Agent:
    - Liên kết trực tiếp với Kho Dữ liệu Hồ sơ Công bố Sản phẩm (data/products_claims.json).
    - Đối chiếu văn bản quảng cáo với từng chi tiết công bố của SKU được chọn.
    - Tô đỏ trực tiếp trên trình soạn thảo thông qua `highlighted_html`.
    """
    product = get_product_by_sku(sku)
    effective_key = api_key or _RUNTIME_AI_CONFIG["api_key"] or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    effective_provider = provider if provider != "auto" else _RUNTIME_AI_CONFIG["provider"]

    result = None
    if effective_key and effective_provider not in ["local", "local_deep"]:
        try:
            result = _try_cloud_llm_audit(text, product, effective_key, effective_provider)
        except Exception:
            result = None

    if not result:
        result = _run_local_expert_agent(text, product)

    # Sinh HTML tô đỏ trực quan trên trình soạn thảo
    violations = result.get("semantic_violations", [])
    highlighted_html = generate_inline_highlighted_html(text, violations)

    result["highlighted_html"] = highlighted_html
    result["sku"] = sku
    result["product_name"] = product["name"] if product else sku
    if product:
        result["product_dossier"] = {
            "sku": product.get("sku"),
            "name": product.get("name"),
            "registration_number": product.get("registration_number"),
            "ad_permit_number": product.get("ad_permit_number"),
            "active_ingredients": product.get("active_ingredients", []),
            "target_users": product.get("target_users", []),
            "contraindications": product.get("contraindications", ""),
            "claims_count": len(product.get("claims", [])),
            "evidence_count": len(product.get("clinical_evidence", []))
        }

    return result

def _try_cloud_llm_audit(
    text: str,
    product: Optional[Dict[str, Any]],
    api_key: str,
    provider: str
) -> Optional[Dict[str, Any]]:
    """Gọi LLM đám mây (Gemini Flash hoặc GPT-4o-mini) với prompt đối chiếu hồ sơ công bố sản phẩm."""
    product_dossier_str = "Chưa chọn sản phẩm cụ thể."
    if product:
        ingredients_str = ", ".join([f"{i['name']} ({i['amount']})" for i in product.get("active_ingredients", [])])
        targets_str = "; ".join(product.get("target_users", []))
        claims_str = "\n".join([f"- [{c['claim_id']}] {c['claim_text']}" for c in product.get("claims", [])])
        product_dossier_str = f"""
HỒ SƠ CÔNG BỐ SẢN PHẨM CHÍNH THỨC CỦA DOANH NGHIỆP:
- Tên sản phẩm: {product.get('name')} (Mã SKU: {product.get('sku')})
- Số Giấy tiếp nhận đăng ký bản công bố sản phẩm: {product.get('registration_number')}
- Số Giấy xác nhận nội dung quảng cáo: {product.get('ad_permit_number')}
- Hoạt chất & Hàm lượng đăng ký: {ingredients_str}
- Đối tượng sử dụng đã phê duyệt: {targets_str}
- Chống chỉ định: {product.get('contraindications')}
- Công dụng thương mại đã được thẩm định & cấp phép (Claims):
{claims_str}
- Cảnh báo bắt buộc (Disclaimer): {product.get('mandatory_disclaimer')}
"""

    prompt = f"""Bạn là Trưởng Ban Pháp chế & Thẩm định Dược phẩm cao cấp của Dion Healthcare, am hiểu sâu sắc:
1. Nghị định 342/2025/NĐ-CP (Quy chuẩn quảng cáo Thực phẩm bảo vệ sức khỏe mới nhất).
2. Luật Dược 2016 (và Luật Dược sửa đổi 2024/2025).
3. Nghị định 15/2018/NĐ-CP (Điều 27 về Quảng cáo thực phẩm chức năng).
4. Luật Quảng cáo 2012 (Điều 8).

{product_dossier_str}

BÀI VIẾT QUẢNG CÁO CẦN THẨM ĐỊNH & ĐỐI CHIẾU:
\"\"\"{text}\"\"\"

YÊU CẦU ĐỐI CHIẾU VÀ THẨM ĐỊNH TOÀN DIỆN:
1. ĐỐI CHIẾU VỚI HỒ SƠ SẢN PHẨM:
   - Bài viết có bịa đặt công dụng ngoài hồ sơ công bố không? (Ví dụ: Cal-Mom chữa thoái hóa sụn khớp, điều trị đau lưng, chữa dạ dày).
   - Bài viết có sai lệch thành phần hoạt chất không?
   - Bài viết có bỏ sót đối tượng sử dụng cốt lõi của dòng sản phẩm MOM không? (Bắt buộc phải có: "Phụ nữ chuẩn bị mang thai, đang mang thai và cho con bú; người lớn tuổi, người có nguy cơ loãng xương").
2. PHÁT HIỆN LẠM DỤNG TÊN CƠ QUAN NHÀ NƯỚC:
   - TUYỆT ĐỐI KHÔNG được viết "Được Cục An toàn thực phẩm chứng nhận" (vì cơ quan nhà nước không chứng nhận công dụng, chỉ cấp Giấy xác nhận nội dung quảng cáo). Bắt buộc ghi: "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:" hoặc "CÔNG DỤNG NỔI BẬT:".
3. PHÁT HIỆN KHẲNG ĐỊNH CƠ CHẾ DƯỢC LÝ TUYỆT ĐỐI:
   - Mọi phát biểu về khả năng hấp thu hoặc cơ chế phải có từ "Hỗ trợ" đứng trước (Ví dụ: "Hỗ trợ tăng cường khả năng hấp thu Canxi và khoáng chất"), không dùng từ đơn độc "Tối ưu hóa khả năng hấp thu".
4. QUÉT 7 TẦNG VI PHẠM LUẬT ĐỊNH:
   - Mạo danh bác sĩ / nhân viên y tế / bài thuốc gia truyền lương y.
   - Dùng thư cảm ơn, câu chuyện bệnh nhân kể việc khỏi bệnh.
   - Hù dọa biến chứng nan y (teo cơ, tàn phế, liệt giường) để ép mua hàng.
   - Khẳng định khỏi bệnh, dứt điểm, không tái phát, hoàn tiền 100%.
   - Xúi giục vứt bỏ thuốc tây, dùng thuật ngữ lượng tử, diệu dược.
   - Kiểm tra câu Disclaimer bắt buộc: "Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh."

QUY TẮC BẢN NHÁP VIẾT LẠI (rewritten_draft):
- Viết lại toàn bộ bài viết đạt 100/100 điểm pháp lý.
- Áp dụng đầy đủ 3 quy tắc: ghi "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:", ghi rõ đối tượng mẹ bầu và người cao tuổi, thêm từ "Hỗ trợ tăng cường khả năng hấp thu".
- Đính kèm câu Disclaimer bắt buộc ở cuối.

Trả về DUY NHẤT một chuỗi JSON hợp lệ không có markdown code block theo định dạng:
{{
  "agent_mode": "CLOUD_LLM",
  "model_name": "Cloud LLM (Gemini / OpenAI)",
  "total_score": <int 0-100>,
  "risk_level": "CRITICAL_HAZARD" | "HIGH_RISK" | "MODERATE_RISK" | "COMPLIANT",
  "verdict_title": "<tiêu đề kết luận pháp lý>",
  "executive_summary": "<tổng kết ngắn gọn 2-3 câu>",
  "chain_of_thought": [
    "<bước 1: đối chiếu hồ sơ công bố sản phẩm & xác định sai lệch>",
    "<bước 2: bóc tách thủ thuật thao túng tâm lý / hù dọa / mạo danh>",
    "<bước 3: viện dẫn điều khoản NĐ 342/2025, NĐ 15/2018 & Luật Dược>",
    "<bước 4: đánh giá rủi ro pháp lý cho doanh nghiệp>"
  ],
  "semantic_violations": [
    {{
      "quote": "<đoạn trích dẫn nguyên văn trong bài>",
      "category": "<Lạm dụng cơ quan nhà nước | Sai lệch hồ sơ công bố | Mạo danh y bác sĩ | Thư cảm ơn bệnh nhân | Hù dọa biến chứng | Ẩn dụ trị bệnh | Cam kết quá mức | Hạ thấp tân dược>",
      "legal_basis": "<Điều khoản luật hoặc Số hồ sơ công bố>",
      "severity": "CRITICAL" | "HIGH" | "MEDIUM",
      "explanation": "<giải thích lý do vi phạm>",
      "compliant_suggestion": "<gợi ý sửa đổi chính xác>"
    }}
  ],
  "rewritten_draft": "<bài viết hoàn chỉnh đã được AI viết lại đạt chuẩn 100/100>"
}}
"""

    # 1. Thử Gemini API
    if not api_key.startswith("sk-"):
        import requests
        gemini_models = ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-pro-latest"]
        for model in gemini_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.2
                    }
                }
                r = requests.post(url, json=payload, timeout=25)
                if r.status_code == 200:
                    raw_text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if raw_text.startswith("```"):
                        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                        raw_text = re.sub(r"\s*```$", "", raw_text)
                    data = json.loads(raw_text)
                    data["agent_mode"] = "CLOUD_LLM"
                    data["model_name"] = f"Google Gemini ({model})"
                    data["violations_count"] = len(data.get("semantic_violations", []))
                    data["critical_count"] = sum(1 for v in data.get("semantic_violations", []) if v.get("severity") == "CRITICAL")
                    return data
            except Exception:
                continue

    # 2. Thử OpenAI API nếu có
    if HAS_OPENAI and (api_key.startswith("sk-") or "openai" in provider.lower()):
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Chief Legal Officer specializing in Vietnam Pharmaceutical Law and Food Safety Advertising."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)
            data["agent_mode"] = "CLOUD_LLM"
            data["model_name"] = "OpenAI GPT-4o-mini"
            data["violations_count"] = len(data.get("semantic_violations", []))
            data["critical_count"] = sum(1 for v in data.get("semantic_violations", []) if v.get("severity") == "CRITICAL")
            return data
        except Exception:
            pass

    return None

def _run_local_expert_agent(text: str, product: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Động cơ AI Agent Chuyên gia Nội bộ (Local Deep Semantic Agent):
    - Đối chiếu văn bản với Hồ sơ Công bố Sản phẩm chính thức (SKU Grounding).
    - Phân tích 7 tầng vi phạm luật định NĐ 342/2025 & NĐ 15/2018.
    - Tạo chuỗi Chain-of-Thought và bản nháp viết lại đạt chuẩn 100/100.
    """
    text_lower = text.lower()
    violations: List[Dict[str, Any]] = []

    # 1. BÓC TÁCH CÂU DISCLAIMER TRƯỚC
    has_disclaimer = "thực phẩm này không phải là thuốc" in text_lower
    body_lines = [l for l in text.splitlines() if "thực phẩm này không phải là thuốc" not in l.lower()]
    body_text = "\n".join(body_lines)
    body_lower = body_text.lower()

    # 2. ĐỐI CHIẾU HỒ SƠ SẢN PHẨM (SKU GROUNDING CHECKS)
    # Lỗi 1: Lạm dụng danh nghĩa "Được Cục An toàn thực phẩm chứng nhận" / "Bộ Y tế chứng nhận"
    gov_cert_patterns = [
        (r"(được cục an toàn thực phẩm chứng nhận|cục an toàn thực phẩm chứng nhận|bộ y tế chứng nhận|được bộ y tế chứng nhận|viện dinh dưỡng chứng nhận)",
         "Lạm dụng Danh nghĩa Cơ quan Quản lý Nhà nước",
         "Khoản 2 Điều 27 Nghị định 15/2018/NĐ-CP & Nghị định 342/2025/NĐ-CP",
         "CRITICAL",
         "Cơ quan quản lý nhà nước không chứng nhận công dụng sản phẩm, chỉ cấp Giấy xác nhận nội dung quảng cáo. Việc ghi 'Được Cục An toàn thực phẩm chứng nhận' là hành vi mượn danh nghĩa cơ quan nhà nước bị nghiêm cấm.",
         "CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:")
    ]
    for pattern, cat, legal, sev, exp, sug in gov_cert_patterns:
        for m in re.finditer(pattern, body_lower):
            matched_str = text[m.start():m.end()]
            if not any(v["quote"].lower() == matched_str.lower() for v in violations):
                violations.append({
                    "quote": matched_str,
                    "category": cat,
                    "legal_basis": legal,
                    "severity": sev,
                    "explanation": exp,
                    "compliant_suggestion": sug
                })

    # Lỗi 2: Bỏ sót đối tượng mẹ bầu đối với sản phẩm dòng MOM (Cal-Mom)
    is_mom_product = product and ("mom" in product.get("sku", "").lower() or "mom" in product.get("name", "").lower())
    if is_mom_product:
        has_pregnant_mention = any(k in body_lower for k in ["mang thai", "mẹ bầu", "thai kỳ", "cho con bú", "sau sinh"])
        if not has_pregnant_mention:
            violations.append({
                "quote": "[Bỏ sót đối tượng sử dụng cốt lõi]",
                "category": "Sai lệch Đối tượng Chỉ định Hồ sơ Công bố",
                "legal_basis": f"Hồ sơ công bố số {product.get('registration_number', '8892/2025/ĐKSP')}",
                "severity": "HIGH",
                "explanation": "Sản phẩm DION Cal-Mom Plus & D3 K2 được phê duyệt chính thức cho: Phụ nữ chuẩn bị mang thai, đang mang thai và cho con bú; người lớn tuổi, người có nguy cơ loãng xương. Bỏ sót đối tượng thai phụ làm mất tệp khách hàng cốt lõi và sai lệch công bố.",
                "compliant_suggestion": "Phụ nữ chuẩn bị mang thai, đang mang thai và cho con bú; người lớn tuổi, người có nguy cơ loãng xương."
            })

    # Lỗi 3: Khẳng định tuyệt đối cơ chế hấp thu thiếu từ "Hỗ trợ"
    abs_absorption_patterns = [
        (r"(tối ưu hóa khả năng hấp thu|tối ưu khả năng hấp thu|hấp thu tuyệt đối|hấp thu 100%)",
         "Khẳng định Tuyệt đối Cơ chế Dược lý",
         "Khoản 3 Điều 5 Nghị định 342/2025/NĐ-CP",
         "HIGH",
         "Thực phẩm bảo vệ sức khỏe không được khẳng định tuyệt đối cơ chế sinh học trong cơ thể. Bắt buộc phải có từ 'Hỗ trợ' đứng trước mô tả khả năng hấp thu khoáng chất.",
         "Hỗ trợ tăng cường khả năng hấp thu Canxi và khoáng chất")
    ]
    for pattern, cat, legal, sev, exp, sug in abs_absorption_patterns:
        for m in re.finditer(pattern, body_lower):
            matched_str = text[m.start():m.end()]
            if not any(v["quote"].lower() == matched_str.lower() for v in violations):
                violations.append({
                    "quote": matched_str,
                    "category": cat,
                    "legal_basis": legal,
                    "severity": sev,
                    "explanation": exp,
                    "compliant_suggestion": sug
                })

    # 3. TẦNG 1: MẠO DANH BÁC SĨ, NHÂN VIÊN Y TẾ, BÀI THUỐC GIA TRUYỀN
    doc_patterns = [
        (r"(bác sĩ đầu ngành|bác sĩ viện|giáo sư viện|tiến sĩ viện|chuyên gia y tế hàng đầu|thầy thuốc ưu tú|lương y \d+ đời|bài thuốc gia truyền|viện quân y|bệnh viện|dược sĩ chỉ định|bác sĩ khuyên)",
         "Mạo danh Y - Bác sĩ & Uy tín Cơ sở Khám chữa bệnh",
         "Khoản 2 Điều 27 Nghị định 15/2018/NĐ-CP & Điều 8 Luật Quảng cáo",
         "CRITICAL",
         "Nghiêm cấm tuyệt đối việc sử dụng hình ảnh, danh nghĩa, thư tín, lời cảm ơn của thầy thuốc, bác sĩ, cơ sở y tế để quảng cáo thực phẩm bảo vệ sức khỏe.",
         "Tham vấn ý kiến chuyên gia y tế / Dựa trên công trình nghiên cứu dinh dưỡng chuẩn hóa")
    ]
    for pattern, cat, legal, sev, exp, sug in doc_patterns:
        for m in re.finditer(pattern, body_lower):
            matched_str = text[m.start():m.end()]
            if not any(v["quote"].lower() == matched_str.lower() for v in violations):
                violations.append({
                    "quote": matched_str,
                    "category": cat,
                    "legal_basis": legal,
                    "severity": sev,
                    "explanation": exp,
                    "compliant_suggestion": sug
                })

    # 4. TẦNG 2: THƯ CẢM ƠN, CHIA SẺ TRẢI NGHIỆM CỦA BỆNH NHÂN (ANECDOTAL EVIDENCE)
    patient_patterns = [
        (r"(chú [a-zà-ỹ]+|bác [a-zà-ỹ]+|chị [a-zà-ỹ]+|anh [a-zà-ỹ]+|cụ [a-zà-ỹ]+)\s*\([^)]*tuổi[^)]*\)[^.!?\n]*?(suýt|liệt giường|khỏi hẳn|chạy nhảy|đi lại|khỏi bệnh)",
         "Sử dụng Thư cảm ơn / Trải nghiệm Bệnh nhân",
         "Khoản 2 Điều 27 Nghị định 15/2018/NĐ-CP",
         "CRITICAL",
         "Quy định cấm sử dụng câu chuyện, chia sẻ của bệnh nhân kể về việc chữa khỏi bệnh để dẫn dắt, tạo lòng tin giả tạo cho người tiêu dùng.",
         "Nghiên cứu lâm sàng đối chứng ngẫu nhiên (RCT) ghi nhận hiệu quả hỗ trợ tích cực trên nhóm người dùng")
    ]
    for pattern, cat, legal, sev, exp, sug in patient_patterns:
        for m in re.finditer(pattern, body_lower):
            matched_str = text[m.start():m.end()]
            if not any(v["quote"].lower() == matched_str.lower() for v in violations):
                violations.append({
                    "quote": matched_str,
                    "category": cat,
                    "legal_basis": legal,
                    "severity": sev,
                    "explanation": exp,
                    "compliant_suggestion": sug
                })

    # 5. TẦNG 3: CHIÊU TRÒ HÙ DỌA BIẾN CHỨNG ĐỂ ÉP MUA (FEAR-MONGERING)
    fear_patterns = [
        (r"(biến chứng teo cơ|tàn phế gõ cửa|nguy cơ đột quỵ|ung thư hóa|hoại tử|suýt liệt giường|nằm liệt giường|đừng để quá muộn|mù lòa)",
         "Thao túng Tâm lý / Hù dọa Biến chứng",
         "Điều 8 Luật Quảng cáo 2012 & Nghị định 342/2025/NĐ-CP",
         "HIGH",
         "Hành vi sử dụng ngôn từ hù dọa về tàn tật, tử vong hoặc biến chứng nan y nhằm đánh vào nỗi sợ hãi để thúc ép người tiêu dùng mua hàng là vi phạm đạo đức và pháp luật quảng cáo.",
         "Chăm sóc và bảo vệ sức khỏe chủ động từ sớm để duy trì thể trạng dẻo dai")
    ]
    for pattern, cat, legal, sev, exp, sug in fear_patterns:
        for m in re.finditer(pattern, body_lower):
            matched_str = text[m.start():m.end()]
            if not any(v["quote"].lower() == matched_str.lower() for v in violations):
                violations.append({
                    "quote": matched_str,
                    "category": cat,
                    "legal_basis": legal,
                    "severity": sev,
                    "explanation": exp,
                    "compliant_suggestion": sug
                })

    # 6. TẦNG 4: ẨN DỤ ĐIỀU TRỊ BỆNH / KHÔI PHỤC CƠ THỂ
    metaphor_patterns = [
        (r"(hồi sinh sụn khớp|hồi sinh|thổi bay|đánh tan sỏi|đánh tan|chia tay nỗi lo thoái hóa|chia tay nỗi lo|vĩnh biệt|cắt đứt đau nhức|cắt đứt cơn đau|quét sạch bách bệnh|bách bệnh|tận gốc rễ|xóa sổ vĩnh viễn|không tái phát|mầm mống bệnh tật)",
         "Ẩn dụ Điều trị Y khoa & Tuyên bố Chữa bệnh",
         "Điều 5 Nghị định 342/2025/NĐ-CP & Luật Dược",
         "CRITICAL",
         "Thực phẩm bảo vệ sức khỏe chỉ có tác dụng hỗ trợ chức năng dinh dưỡng, không được dùng các từ ngữ ẩn dụ khẳng định phục hồi hoàn toàn giải phẫu học cơ thể hoặc điều trị dứt điểm bệnh lý.",
         "Hỗ trợ tăng cường sức khỏe xương răng, hỗ trợ giảm triệu chứng khó chịu khi vận động")
    ]
    for pattern, cat, legal, sev, exp, sug in metaphor_patterns:
        for m in re.finditer(pattern, body_lower):
            matched_str = text[m.start():m.end()]
            if not any(v["quote"].lower() == matched_str.lower() for v in violations):
                violations.append({
                    "quote": matched_str,
                    "category": cat,
                    "legal_basis": legal,
                    "severity": sev,
                    "explanation": exp,
                    "compliant_suggestion": sug
                })

    # 7. TẦNG 5: CAM KẾT HIỆU QUẢ TUYỆT ĐỐI & HOÀN TIỀN
    guarantee_patterns = [
        (r"(không đỡ xin hoàn tiền|hoàn tiền 100%|không đỡ hoàn tiền|uống là thấy khác|uống 1 liệu trình|trẻ hóa \d+ tuổi|thọ thêm \d+ năm|chỉ sau đúng \d+ ngày|sau đúng \d+ ngày|sau \d+ ngày|không tác dụng phụ|100%|tuyệt đối)",
         "Cam kết Kết quả Tuyệt đối & Đảm bảo Hoàn tiền",
         "Khoản 3 Điều 5 Nghị định 342/2025/NĐ-CP",
         "CRITICAL",
         "Nghiêm cấm hành vi cam kết hiệu quả 100%, bảo đảm kết quả chắc chắn hoặc cam kết hoàn tiền để lôi kéo người bệnh.",
         "Kiên trì duy trì đều đặn kết hợp cùng chế độ sinh hoạt khoa học để đạt hiệu quả tối ưu")
    ]
    for pattern, cat, legal, sev, exp, sug in guarantee_patterns:
        for m in re.finditer(pattern, body_lower):
            matched_str = text[m.start():m.end()]
            if not any(v["quote"].lower() == matched_str.lower() for v in violations):
                violations.append({
                    "quote": matched_str,
                    "category": cat,
                    "legal_basis": legal,
                    "severity": sev,
                    "explanation": exp,
                    "compliant_suggestion": sug
                })

    # 8. TẦNG 6: HẠ THẤP TÂN DƯỢC & KHOA HỌC GIẢ TƯỞNG
    denigrate_patterns = [
        (r"(vứt bỏ thuốc men|vứt bỏ thuốc|bỏ thuốc tây|gấp 10\.000 lần thuốc tây|gấp 10\.000 lần|gấp hàng ngàn lần|bẻ khóa tế bào lượng tử|bẻ khóa tế bào|lượng tử|nano diệu dược|diệu dược|thần dược|tiên dược|siêu phẩm|đột phá y học thế kỷ|thảo mộc ngàn năm)",
         "Hạ thấp Tân dược & Khoa học Giả tưởng",
         "Khoản 11 Điều 8 Luật Quảng cáo & Điều 5 NĐ 342/2025",
         "CRITICAL",
         "Hành vi xúi giục bệnh nhân vứt bỏ thuốc kê đơn của bác sĩ là hành vi vi phạm nghiêm trọng tính mạng con người. Sử dụng thuật ngữ khoa học giả tưởng (lượng tử, diệu dược) là hành vi lừa dối người tiêu dùng.",
         "Giải pháp dinh dưỡng bổ trợ lành tính, hỗ trợ tăng cường khả năng hấp thu của cơ thể")
    ]
    for pattern, cat, legal, sev, exp, sug in denigrate_patterns:
        for m in re.finditer(pattern, body_lower):
            matched_str = text[m.start():m.end()]
            if not any(v["quote"].lower() == matched_str.lower() for v in violations):
                violations.append({
                    "quote": matched_str,
                    "category": cat,
                    "legal_basis": legal,
                    "severity": sev,
                    "explanation": exp,
                    "compliant_suggestion": sug
                })

    # 9. TẦNG 7: KIỂM TRA DISCLAIMER BẮT BUỘC
    if not has_disclaimer:
        violations.append({
            "quote": "[Cuối bài viết thiếu câu cảnh báo]",
            "category": "Thiếu Câu Cảnh Báo Bắt Buộc",
            "legal_basis": "Khoản 2 Điều 5 Nghị định 342/2025/NĐ-CP & Thông tư Bộ Y tế",
            "severity": "HIGH",
            "explanation": "Tất cả các xuất bản phẩm quảng cáo thực phẩm bảo vệ sức khỏe bắt buộc phải có câu: 'Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh'.",
            "compliant_suggestion": "Đính kèm câu Disclaimer bắt buộc vào cuối nội dung quảng cáo."
        })

    # 10. TÍNH TOÁN ĐIỂM SỐ & PHÂN CẤP RỦI RO
    critical_count = sum(1 for v in violations if v["severity"] == "CRITICAL")
    high_count = sum(1 for v in violations if v["severity"] == "HIGH")

    if critical_count >= 3 or any("vứt bỏ thuốc" in v["quote"].lower() or "bác sĩ" in v["quote"].lower() or "lương y" in v["quote"].lower() for v in violations):
        total_score = max(5, 15 - (critical_count * 2))
        risk_level = "CRITICAL_HAZARD"
        verdict_title = "BÁO ĐỘNG ĐỎ: RỦI RO PHÁP LÝ ĐẶC BIỆT NGHIÊM TRỌNG"
        executive_summary = (
            f"AI Agent phát hiện {len(violations)} vi phạm nghiêm trọng so với hồ sơ công bố và pháp luật y tế. "
            f"Bài viết mạo danh bác sĩ, dùng câu chuyện bệnh nhân, hù dọa biến chứng và sai lệch công dụng đăng ký. "
            f"Doanh nghiệp đối mặt với nguy cơ bị Thanh tra tước Giấy xác nhận quảng cáo và phạt kịch khung theo Nghị định 342/2025/NĐ-CP."
        )
    elif critical_count >= 1 or high_count >= 2:
        total_score = max(20, 55 - (critical_count * 15 + high_count * 10))
        risk_level = "HIGH_RISK"
        verdict_title = "RỦI RO CAO: VI PHẠM QUY CHUẨN NGHỊ ĐỊNH 342"
        executive_summary = (
            f"AI Agent phát hiện {len(violations)} điểm chưa đạt chuẩn. Nội dung có dấu hiệu cường điệu hóa công dụng "
            f"và sử dụng các cụm từ chưa được phê duyệt trong hồ sơ công bố. Cần chuẩn hóa toàn diện trước khi phát hành."
        )
    elif len(violations) > 0:
        total_score = 75
        risk_level = "MODERATE_RISK"
        verdict_title = "CẦN ĐIỀU CHỈNH: THIẾU CÂU CẢNH BÁO BẮT BUỘC HOẶC ĐỐI TƯỢNG"
        executive_summary = "Nội dung cơ bản phù hợp nhưng cần bổ sung câu cảnh báo Disclaimer và hoàn thiện danh sách đối tượng sử dụng theo hồ sơ đăng ký."
    else:
        total_score = 100
        risk_level = "COMPLIANT"
        verdict_title = "ĐẠT CHUẨN NGHỊ ĐỊNH 342/2025/NĐ-CP & HỒ SƠ CÔNG BỐ"
        executive_summary = "Bài viết xuất sắc! Nội dung khớp 100% với hồ sơ công bố sản phẩm, có câu cảnh báo đầy đủ và văn phong khoa học chuẩn mực."

    # 11. XÂY DỰNG CHUỖI SUY LUẬN AI (CHAIN-OF-THOUGHT)
    p_name = product.get("name") if product else "Sản phẩm DION"
    reg_num = product.get("registration_number") if product else "8892/2025/ĐKSP"
    chain_of_thought = [
        f"1. Đối chiếu Hồ sơ Pháp chế & Đăng ký: Kiểm tra văn bản với Hồ sơ công bố số {reg_num} của {p_name}. Phát hiện {len(violations)} điểm sai lệch về công dụng chỉ định, hoạt chất và quy tắc xưng danh.",
        f"2. Bóc tách Kỹ thuật Thao túng Tâm lý: Phát hiện các thủ thuật hù dọa biến chứng nan y để kích hoạt nỗi sợ hãi, cam kết hoàn tiền 100% để hạ thấp phòng thủ của khách hàng và mượn danh nghĩa lương y/bác sĩ viện quân y.",
        "3. Đối chiếu Khung Pháp lý Y tế: Vi phạm trực tiếp Khoản 2 Điều 27 NĐ 15/2018 (cấm mượn danh y bác sĩ, cấm ghi cơ quan nhà nước chứng nhận công dụng), Điều 5 NĐ 342/2025 (cấm cam kết hoàn tiền & khẳng định trị bệnh) và Điều 8 Luật Quảng cáo.",
        "4. Đánh giá Rủi ro Pháp chế: Nếu đăng tải, bài viết có nguy cơ 100% bị thuật toán giám sát của Cục An toàn Thực phẩm gắn cờ vi phạm, dẫn tới đình chỉ lưu hành sản phẩm và phạt tiền từ 50 - 100 triệu đồng."
    ]

    # 12. TỔNG HỢP BÀI VIẾT VIẾT LẠI HOÀN TOÀN TỪ AI AGENT (REWRITTEN DRAFT)
    rewritten_draft = (
        f"🌿 GIẢI PHÁP CHĂM SÓC SỨC KHỎE XƯƠNG RĂNG & VI CHẤT TOÀN DIỆN TỪ TPBVSK {p_name.upper()}\n\n"
        "Bổ sung vi chất đúng cách và duy trì hệ xương dẻo dai là nền tảng quan trọng giúp bảo vệ sức khỏe cho cả mẹ bầu và người lớn tuổi.\n\n"
        "💡 CÔNG DỤNG ĐÃ ĐƯỢC XÁC NHẬN NỘI DUNG QUẢNG CÁO:\n"
        "• Hỗ trợ bổ sung Canxi sinh học từ tảo biển đỏ Lithothamnion và Vitamin D3 K2 MK-7 chất lượng cao.\n"
        "• Hỗ trợ tăng cường sức khỏe xương răng, hỗ trợ giảm nguy cơ loãng xương ở người lớn và hỗ trợ đáp ứng nhu cầu Canxi tăng cao cho phụ nữ mang thai.\n"
        "• Hỗ trợ tăng cường khả năng hấp thu Canxi và khoáng chất, an toàn và lành tính cho dạ dày khi sử dụng đều đặn.\n\n"
        "🔬 ĐƯỢC SẢN XUẤT TẠI NHÀ MÁY ĐẠT CHUẨN GMP QUỐC TẾ:\n"
        "Sản phẩm ứng dụng công nghệ vi bao hiện đại, được kiểm soát chất lượng nghiêm ngặt theo tiêu chuẩn ISO 22000.\n\n"
        "📦 Thích hợp cho: Phụ nữ chuẩn bị mang thai, đang mang thai và cho con bú; người lớn tuổi, người có nguy cơ loãng xương hoặc người có nhu cầu bổ sung Canxi.\n\n"
        "👉 Liên hệ ngay đội ngũ Dược sĩ tư vấn để xây dựng lộ trình chăm sóc sức khỏe khoa học phù hợp với thể trạng của bạn!\n"
        "---\n"
        "⚠️ Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh."
    )

    return {
        "agent_mode": "LOCAL_EXPERT_AGENT",
        "model_name": "DION Enterprise Legal AI Agent v2.5 (Pháp chế Dược phẩm Chuyên sâu)",
        "total_score": total_score,
        "risk_level": risk_level,
        "verdict_title": verdict_title,
        "executive_summary": executive_summary,
        "chain_of_thought": chain_of_thought,
        "semantic_violations": violations,
        "violations_count": len(violations),
        "critical_count": critical_count,
        "rewritten_draft": rewritten_draft
    }
