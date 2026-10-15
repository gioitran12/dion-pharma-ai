import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, Query, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from modules.claims_hub import get_all_products, get_product_by_sku, get_claims_summary, get_active_claims
from modules.lead_discovery import (
    filter_leads, update_lead_status, get_lead_by_id, group_by_parent_chain, generate_b2b_outreach_pitch, load_hospitals_map
)
from modules.sales_copilot import generate_copilot_response
from modules.content_generator import (
    generate_marketing_draft, validate_content_compliance, deep_audit_radar, auto_fix_compliance
)

app = FastAPI(title="DION Healthcare AI — Enterprise Platform")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    products = get_all_products()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products
    })

# --- API CƠ BẢN ---
@app.get("/api/products")
async def api_get_products():
    return get_all_products()

@app.get("/api/products/{sku}")
async def api_get_product_detail(sku: str):
    prod = get_product_by_sku(sku)
    if not prod:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    summary = get_claims_summary(sku)
    return {"product": prod, "summary": summary}

# --- GIẢI PHÁP 1: B2B LEAD DISCOVERY ---
@app.get("/api/leads")
async def api_get_leads(
    province: str = "Tất cả",
    district: str = "Tất cả",
    hospital: str = "Tất cả",
    max_distance: int = 0,
    lead_type: str = "Tất cả",
    status: str = "Tất cả",
    keyword: str = "",
    only_new: bool = False
):
    leads = filter_leads(
        province=province,
        district=district,
        hospital=hospital,
        max_distance=max_distance,
        lead_type=lead_type,
        status=status,
        search_keyword=keyword,
        only_new=only_new
    )
    grouped = group_by_parent_chain(leads)
    chains_summary = []
    for parent, items in grouped.items():
        if parent != "Độc lập / Chưa gom nhóm" and len(items) > 1:
            chains_summary.append({"parent": parent, "count": len(items), "items": items})
    return {
        "total": len(leads),
        "leads": leads,
        "chains": chains_summary,
        "hospitals_map": load_hospitals_map()
    }

@app.post("/api/leads/{lead_id}/action")
async def api_lead_action(lead_id: str, action: str = Body(..., embed=True), assigned_to: Optional[str] = Body(None, embed=True)):
    success = update_lead_status(lead_id, new_status=action, assigned_to=assigned_to)
    if not success:
        raise HTTPException(status_code=400, detail="Không thể cập nhật trạng thái")
    return {"status": "success", "lead_id": lead_id, "new_status": action}

@app.post("/api/leads/{lead_id}/pitch")
async def api_lead_pitch(lead_id: str, sku: str = Body("DION-D3-1000", embed=True)):
    pitch = generate_b2b_outreach_pitch(lead_id, recommended_sku=sku)
    return pitch

# --- GIẢI PHÁP 2: AI CONTENT ENGINE ---
@app.post("/api/content/audit-radar")
async def api_content_audit(text: str = Body(..., embed=True)):
    return deep_audit_radar(text)

@app.post("/api/content/auto-fix")
async def api_content_autofix(text: str = Body(..., embed=True), sku: str = Body("DION-D3-1000", embed=True)):
    return auto_fix_compliance(text, sku=sku)

# --- GIẢI PHÁP 3: AI MARKET INTELLIGENCE (THEO DÕI THỊ TRƯỜNG & ĐỐI THỦ) ---
@app.get("/api/market-intelligence")
async def api_market_intelligence():
    return {
        "trends": [
            {
                "category": "Canxi cho bà bầu",
                "trend_name": "Chuyển dịch sang Canxi sinh học từ tảo Lithothamnion",
                "growth": "+42% lượng tìm kiếm",
                "insight": "Khách hàng tránh Canxi Carbonate vô cơ vì sợ táo bón và lắng cặn thận.",
                "opportunity": "Đẩy mạnh dòng Canxi Cal-Mom hữu cơ vào chuỗi Mẹ & Bé."
            },
            {
                "category": "Vitamin D3",
                "trend_name": "D3 nhỏ giọt kết hợp K2 (MK-7) chuẩn tinh khiết",
                "growth": "+35% doanh số kênh quầy thuốc",
                "insight": "Nhu cầu cao ở các gia đình trẻ khu đô thị, phụ huynh chuộng dạng nhỏ giọt chuẩn liều.",
                "opportunity": "Thiết kế gói phân phối độc quyền cho chuỗi Long Châu."
            },
            {
                "category": "Sắt & Bổ máu",
                "trend_name": "Sắt Bisglycinate hữu cơ không gây kích ứng dạ dày",
                "growth": "+28% phản hồi tích cực",
                "insight": "Thai phụ phản hồi 85% trường hợp giảm hẳn buồn nôn so với sắt Sulfate truyền thống.",
                "opportunity": "Chào hàng trực tiếp cho phòng khám sản và nhà thuốc phụ sản."
            }
        ],
        "competitors": [
            {
                "name": "Thương hiệu A (Nhập khẩu Úc)",
                "product": "Bio-Calcium D3",
                "avg_price": "450.000 đ / hộp",
                "channels": "Nhà thuốc chuỗi lớn (Long Châu, Pharmacity)",
                "strengths": "Thương hiệu lâu năm, bao bì đẹp",
                "weaknesses": "Giá cao, chiết khấu đại lý thấp (15-18%)",
                "dion_advantage": "DION chiết khấu 30-35%, hỗ trợ đào tạo Dược sĩ và POSM điểm bán."
            },
            {
                "name": "Thương hiệu B (Nội địa)",
                "product": "Calci-Nano Plus",
                "avg_price": "180.000 đ / hộp",
                "channels": "Nhà thuốc lẻ vùng ven, chợ thuốc",
                "strengths": "Giá rẻ, dễ tiếp cận số đông",
                "weaknesses": "Dạng nano vô cơ, phản hồi nóng trong người",
                "dion_advantage": "DION dùng nguồn tảo Lithothamnion tự nhiên chuẩn organic."
            }
        ]
    }

# --- GIẢI PHÁP 4: AI SALES COPILOT ---
@app.post("/api/copilot/ask")
async def api_copilot_ask(query: str = Body(..., embed=True), sku: str = Body("ALL", embed=True)):
    return generate_copilot_response(query, sku=sku)

# --- GIẢI PHÁP 5: AI CUSTOMER CARE (CHĂM SÓC KHÁCH HÀNG & QUYỀN RIÊNG TƯ) ---
@app.get("/api/customer-care")
async def api_customer_care():
    return {
        "retention_rules": [
            {"day": 7, "purpose": "Khảo sát cảm nhận sử dụng & Hướng dẫn uống đúng cách", "action": "Gửi tin nhắn ZNS chăm sóc khách hàng"},
            {"day": 25, "purpose": "Nhắc bổ sung chu kỳ tiếp theo (Sắp hết hộp 30 ngày)", "action": "Tạo lịch gọi cho chuyên viên tư vấn tái mua"},
            {"day": 60, "purpose": "Tư vấn lộ trình duy trì dài hạn theo khuyến nghị chuyên gia", "action": "Gợi ý gói combo tiết kiệm"}
        ],
        "privacy_compliance": {
            "law_reference": "Luật Bảo vệ Dữ liệu Cá nhân số 91/2025/QH15 & Nghị định 356/2025/NĐ-CP",
            "opt_out_rule": "Khi khách hàng bấm từ chối nhận tin, hệ thống tự động khóa vĩnh viễn quyền gửi tin tiếp thị trên mọi kênh.",
            "incident_lockout_rule": "Khi khách hàng phát sinh khiếu nại chất lượng hoặc phản ứng phụ, khóa ngay lập tức toàn bộ chiến dịch bán hàng."
        },
        "sample_customers": [
            {
                "id": "KH-8821",
                "name": "Nguyễn Thị Hương",
                "sku_bought": "DION Cal-Mom Plus",
                "purchase_date": "2026-09-20",
                "day_in_cycle": 25,
                "status": "CẦN NHẮC TÁI MUA",
                "consent_status": "Đã đồng ý nhận tin Zalo",
                "complaint_status": "Bình thường",
                "suggested_message": "Chào chị Hương, liệu trình Canxi Cal-Mom của mình chỉ còn 5 ngày nữa là hoàn thành hộp đầu tiên. DION gửi chị ưu đãi tích lũy cho hộp tiếp theo để đảm bảo vi chất liên tục cho bé ạ."
            },
            {
                "id": "KH-9042",
                "name": "Lê Văn Tuấn",
                "sku_bought": "DION Vitamin D3 1000IU",
                "purchase_date": "2026-10-08",
                "day_in_cycle": 7,
                "status": "HỎI THĂM TRẢI NGHIỆM",
                "consent_status": "Đã đồng ý nhận SMS",
                "complaint_status": "Bình thường",
                "suggested_message": "Chào anh Tuấn, anh đã sử dụng Vitamin D3 DION được 1 tuần. Anh uống vào buổi sáng sau ăn để cơ thể hấp thu canxi tối đa nhé ạ."
            },
            {
                "id": "KH-7119",
                "name": "Trần Thu Hà",
                "sku_bought": "DION Fero-Plus",
                "purchase_date": "2026-10-02",
                "day_in_cycle": 13,
                "status": "KHÓA BÁN HÀNG — ĐANG KHIẾU NẠI",
                "consent_status": "Khách hàng đã Opt-out",
                "complaint_status": "Đang có khiếu nại tiêu hóa",
                "suggested_message": "CẢNH BÁO: ĐÃ KHÓA TẤT CẢ TIN NHẮN BÁN HÀNG. Đang chuyển giao Dược sĩ chuyên môn gọi điện xử lý phản ứng bất lợi."
            }
        ]
    }

# --- GIẢI PHÁP 6: AI RESEARCH INTELLIGENCE (NGHIÊN CỨU & BẰNG CHỨNG PUBMED) ---
@app.get("/api/research-intelligence")
async def api_research_intelligence(ingredient: str = "Lithothamnion"):
    return {
        "ingredient": ingredient,
        "scientific_summary": "Chiết xuất tảo đỏ vôi hóa Lithothamnion calcareum chứa 32% Canxi nguyên tố, 2.2% Magie và hơn 70 khoáng chất vi lượng, có cấu trúc xốp tổ ong giúp tăng độ hòa tan và sinh khả dụng so với canxi đá vôi.",
        "evidence_table": [
            {
                "pmid": "PMID: 20213326",
                "study_type": "Thử nghiệm lâm sàng ngẫu nhiên có đối chứng (RCT)",
                "sample_size": "N = 120 phụ nữ tiền mãn kinh",
                "dosage": "1.000 mg Canxi sinh học / ngày trong 12 tháng",
                "key_findings": "Tăng mật độ khoáng xương (BMD) tại đốt sống thắt lưng thêm +2.1% so với nhóm chứng (p < 0.05).",
                "adverse_events": "Không ghi nhận trường hợp táo bón hoặc rối loạn tiêu hóa nghiêm trọng.",
                "evidence_grade": "Hạng A (Bằng chứng lâm sàng mạnh)"
            },
            {
                "pmid": "PMID: 29487192",
                "study_type": "Nghiên cứu đối chứng sinh khả dụng chéo (Crossover Trial)",
                "sample_size": "N = 45 người trưởng thành khỏe mạnh",
                "dosage": "Liều đơn 500 mg Canxi tảo đỏ vs 500 mg Canxi Carbonate",
                "key_findings": "Khả năng ức chế hormone tuyến cận giáp (PTH) kéo dài hơn 8 giờ, cho thấy thời gian duy trì nồng độ canxi máu ổn định hơn.",
                "adverse_events": "Tỷ lệ dung nạp đường ruột đạt 96.8%.",
                "evidence_grade": "Hạng A (Sinh khả dụng được kiểm chứng)"
            },
            {
                "pmid": "PMID: 31092144",
                "study_type": "Đánh giá tổng quan hệ thống & Phân tích gộp (Systematic Review & Meta-analysis)",
                "sample_size": "Tổng hợp 18 nghiên cứu, N = 2.450 đối tượng",
                "dosage": "Bổ sung kết hợp Canxi + Vitamin D3 + Vitamin K2 (MK-7)",
                "key_findings": "Sự kết hợp ba thành phần giúp định hướng canxi vào mô xương, giảm 38% nguy cơ vôi hóa mạch máu.",
                "adverse_events": "An toàn khi sử dụng theo liều khuyến cáo hàng ngày.",
                "evidence_grade": "Hạng A (Đồng thuận y khoa quốc tế)"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
