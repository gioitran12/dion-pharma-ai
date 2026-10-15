import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, Query, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from modules.claims_hub import get_all_products, get_product_by_sku, get_claims_summary, get_active_claims
from modules.lead_discovery import filter_leads, update_lead_status, get_lead_by_id, group_by_parent_chain
from modules.sales_copilot import generate_copilot_response
from modules.content_generator import generate_marketing_draft, validate_content_compliance

app = FastAPI(title="DION Healthcare AI — Enterprise Platform")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# --- ROUTE CHÍNH: GIAO DIỆN WEB MODERN TAILWIND ---
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    products = get_all_products()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products
    })

# --- API ENDPOINTS CHO FRONTEND ---
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

@app.get("/api/leads")
async def api_get_leads(
    province: str = "Tất cả",
    district: str = "Tất cả",
    lead_type: str = "Tất cả",
    status: str = "Tất cả",
    keyword: str = ""
):
    leads = filter_leads(
        province=province,
        district=district,
        lead_type=lead_type,
        status=status,
        search_keyword=keyword
    )
    grouped = group_by_parent_chain(leads)
    
    chains_summary = []
    for parent, items in grouped.items():
        if parent != "Độc lập / Chưa gom nhóm" and len(items) > 1:
            chains_summary.append({
                "parent": parent,
                "count": len(items),
                "items": items
            })
            
    return {
        "total": len(leads),
        "leads": leads,
        "chains": chains_summary
    }

@app.post("/api/leads/{lead_id}/action")
async def api_lead_action(
    lead_id: str,
    action: str = Body(..., embed=True),
    assigned_to: Optional[str] = Body(None, embed=True)
):
    if action not in ["APPROVED", "REJECTED", "NEW"]:
        raise HTTPException(status_code=400, detail="Action không hợp lệ")
        
    success = update_lead_status(lead_id, new_status=action, assigned_to=assigned_to)
    if not success:
        raise HTTPException(status_code=400, detail="Không thể cập nhật trạng thái lead")
    return {"status": "success", "lead_id": lead_id, "new_status": action, "assigned_to": assigned_to}

@app.post("/api/copilot/ask")
async def api_copilot_ask(
    query: str = Body(..., embed=True),
    sku: str = Body("ALL", embed=True)
):
    result = generate_copilot_response(query, sku=sku)
    return result

@app.post("/api/content/generate")
async def api_content_generate(
    sku: str = Body(..., embed=True),
    channel: str = Body("Facebook Post", embed=True),
    tone: str = Body("Khoa học & Chuyên môn", embed=True)
):
    draft = generate_marketing_draft(sku, channel=channel, tone=tone)
    return draft

@app.post("/api/content/validate")
async def api_content_validate(
    text: str = Body(..., embed=True)
):
    is_valid, violations = validate_content_compliance(text)
    return {"is_compliant": is_valid, "violations": violations}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
