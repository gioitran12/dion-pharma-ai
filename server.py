from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent / ".env")
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from fastapi import FastAPI, Request, Query, Body, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from modules.claims_hub import (
    get_all_products, get_product_by_sku, get_claims_summary, get_active_claims,
    save_or_update_product, search_knowledge_hub
)
from modules.lead_discovery import (
    filter_leads, update_lead_status, get_lead_by_id, group_by_parent_chain,
    generate_b2b_outreach_pitch, generate_b2b_outreach_pitch_ai, analyze_lead_ai,
    add_new_lead, import_leads_bulk, load_hospitals_map,
    log_lead_visit, get_lead_visits
)
from modules.sales_copilot import generate_copilot_response
from modules.clinical_consultant import consult_ai_expert
from modules.caresoft_triage import (
    process_first_touch_chat,
    load_caresoft_leads,
    update_lead_status as update_caresoft_lead_status,
    export_caresoft_leads_csv,
    get_caresoft_metrics
)
from modules.content_generator import (
    generate_marketing_draft, validate_content_compliance, deep_audit_radar, auto_fix_compliance
)
from modules.ai_compliance_agent import (
    run_ai_compliance_audit, set_runtime_ai_key, get_runtime_ai_status
)
from modules.market_intelligence import (
    get_warehouse_market_intelligence, analyze_custom_competitor
)

from modules.research_intelligence import (
    ResearchIntelligenceService,
    SearchStudiesRequest,
    AIAnalyzeStudyRequest,
    LinkClaimRequest,
)

_research_service: Optional[ResearchIntelligenceService] = None

def get_research_service() -> ResearchIntelligenceService:
    global _research_service
    if _research_service is None:
        _research_service = ResearchIntelligenceService()
    return _research_service

import uuid
from modules.chat.schemas import ChatRequest, ChatResponse, IntentResult, SafetyResult, CitationInfo, ChatAction
from modules.chat.enums import ChatIntent, ChatDecision, RiskLevel
from modules.chat.llm_gateway import get_llm_gateway
from modules.knowledge.repository import get_knowledge_repository
from modules.chat.question_understanding import QuestionUnderstandingEngine
from modules.chat.claim_retriever import ClaimRelevanceRetriever
from modules.chat.session import get_session_manager
from modules.customer_care.service import get_customer_care_service
from modules.customer_care.schemas import (
    AutoDraftRequest, ActionLogRequest, RescheduleRequest, AssignTaskRequest, ActionType,
    CreateCustomerRequest, CreateInteractionRequest, CreatePurchaseRequest,
    CreateSupportRequest, CreateCallbackRequest, LinkCopilotInteractionRequest
)
from modules.chat.providers.base import (
    LLMError,
    LLMConfigurationError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMEmptyResponseError,
    LLMProviderError,
)

app = FastAPI(title="DION Healthcare AI — Enterprise Platform")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    products = get_all_products()
    resp = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "products": products}
    )
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

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

@app.get("/api/leads/{lead_id}/visits")
async def api_get_lead_visits(lead_id: str):
    visits = get_lead_visits(lead_id)
    return {"status": "success", "lead_id": lead_id, "total": len(visits), "visits": visits}

@app.post("/api/leads/{lead_id}/visits")
async def api_log_lead_visit(lead_id: str, payload: Dict[str, Any] = Body(...)):
    res = log_lead_visit(lead_id, payload)
    if not res:
        raise HTTPException(status_code=404, detail="Không tìm thấy điểm bán")
    return {"status": "success", **res}

@app.post("/api/leads/{lead_id}/pitch")
async def api_lead_pitch(lead_id: str, sku: str = Body("DION-D3-1000", embed=True)):
    pitch = await generate_b2b_outreach_pitch_ai(lead_id, recommended_sku=sku)
    return pitch

@app.post("/api/leads/{lead_id}/ai-insights")
async def api_lead_ai_insights(lead_id: str):
    insights = await analyze_lead_ai(lead_id)
    return insights

@app.post("/api/leads/add")
async def api_lead_add(lead: Dict[str, Any] = Body(...)):
    if not lead.get("name"):
        raise HTTPException(status_code=400, detail="Tên điểm bán không được để trống")
    res = add_new_lead(lead)
    return {"status": "success", "lead": res}

@app.post("/api/leads/import")
async def api_lead_import(payload: Union[List[Dict[str, Any]], Dict[str, Any]] = Body(...)):
    if isinstance(payload, list):
        leads = payload
    else:
        raw_text = payload.get("raw_text", "")
        default_province = payload.get("default_province", "Hà Nội")
        if raw_text:
            leads = []
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            for line in lines:
                if any(h in line.lower() for h in ["tên nhà thuốc", "mã lead", "tên đơn vị"]):
                    continue
                parts = [p.strip() for p in (line.split("\t") if "\t" in line else line.split(","))]
                if len(parts) >= 2:
                    lead_dict = {
                        "name": parts[0],
                        "address": parts[1] if len(parts) > 1 else "",
                        "phone": parts[2] if len(parts) > 2 else "",
                        "province": parts[3] if len(parts) > 3 and parts[3] else default_province,
                        "district": parts[4] if len(parts) > 4 else "",
                        "contact_person": parts[5] if len(parts) > 5 else "",
                        "target_hospital": parts[6] if len(parts) > 6 else ""
                    }
                    leads.append(lead_dict)
        else:
            leads = payload.get("leads", [])

    if not leads:
        raise HTTPException(status_code=400, detail="Danh sách điểm bán trống hoặc không thể phân tách dữ liệu")
    res = import_leads_bulk(leads)
    return res

# --- GIẢI PHÁP 2: AI CONTENT ENGINE ---
@app.post("/api/content/audit-radar")
async def api_content_audit(text: str = Body(..., embed=True), sku: str = Body("DION-CAL-MOM", embed=True)):
    return deep_audit_radar(text, sku=sku)

@app.post("/api/content/auto-fix")
async def api_content_autofix(text: str = Body(..., embed=True), sku: str = Body("DION-CAL-MOM", embed=True)):
    return auto_fix_compliance(text, sku=sku)

@app.post("/api/content/ai-agent-audit")
async def api_content_ai_agent_audit(
    text: str = Body(..., embed=True),
    sku: str = Body("DION-CAL-MOM", embed=True),
    api_key: Optional[str] = Body(None, embed=True),
    provider: str = Body("auto", embed=True)
):
    return run_ai_compliance_audit(text=text, sku=sku, api_key=api_key, provider=provider)

@app.post("/api/content/generate-draft")
async def api_content_generate_draft(
    sku: str = Body("DION-CAL-MOM", embed=True),
    channel: str = Body("Facebook Post", embed=True),
    tone: str = Body("Khoa học & Chuyên môn", embed=True)
):
    return generate_marketing_draft(sku=sku, channel=channel, tone=tone)


@app.post("/api/products/add-or-update")
async def api_product_add_or_update(product: Dict[str, Any] = Body(...)):
    return save_or_update_product(product)

@app.get("/api/knowledge-hub")
async def api_knowledge_hub(query: str = "", sku: Optional[str] = None):
    return search_knowledge_hub(query=query, sku=sku)

@app.get("/api/config/ai-status")
async def api_ai_status():
    return get_runtime_ai_status()

@app.post("/api/config/ai-key")
async def api_ai_set_key(
    api_key: str = Body(..., embed=True),
    provider: str = Body("auto", embed=True)
):
    return set_runtime_ai_key(key=api_key, provider=provider)

# --- GIẢI PHÁP 3: AI MARKET INTELLIGENCE (THEO DÕI THỊ TRƯỜNG & ĐỐI THỦ) ---
@app.get("/api/market-intelligence")
async def api_market_intelligence(sku: str = "ALL"):
    return get_warehouse_market_intelligence(selected_sku=sku)

@app.post("/api/market-intelligence/analyze-competitor")
async def api_analyze_competitor(
    sku: str = Body("DION-CAL-MOM", embed=True),
    competitor_name: str = Body(..., embed=True),
    competitor_info: str = Body("", embed=True)
):
    return analyze_custom_competitor(sku=sku, competitor_name=competitor_name, competitor_info=competitor_info)

# --- GIẢI PHÁP 4: AI SALES COPILOT ---
@app.post("/api/copilot/ask")
async def api_copilot_ask(query: str = Body(..., embed=True), sku: str = Body("ALL", embed=True)):
    return generate_copilot_response(query, sku=sku)

@app.post("/api/copilot/consult")
async def api_copilot_consult(
    message: str = Body(..., embed=True),
    sku: str = Body("ALL", embed=True),
    mode: str = Body("PHARMACIST_B2C", embed=True),
    channel: str = Body("all", embed=True),
    situation_hint: Optional[str] = Body(None, embed=True)
):
    """
    Tư vấn AI chuyên môn y dược và kịch bản thương mại đa chế độ:
    - PHARMACIST_B2C: Dược sĩ tư vấn tại quầy cho người mua
    - SALES_REP_B2B: Trình dược viên trao đổi chuyên môn với Bác sĩ / Dược sĩ
    - OBJECTION_HANDLING: Kịch bản 3 bước xử lý phản bác tại quầy
    - CLINICAL_SAFETY: Sàng lọc an toàn & Red Flag lâm sàng
    Hỗ trợ 5 sản phẩm Vistafa VitGarden + 3 sản phẩm DION Healthcare trên 4 kênh (Facebook, Zalo, Website, TikTok).
    """
    return consult_ai_expert(message=message, sku=sku, mode=mode, channel=channel, situation_hint=situation_hint)


_question_engine: Optional[QuestionUnderstandingEngine] = None
_claim_retriever: Optional[ClaimRelevanceRetriever] = None

def get_question_engine() -> QuestionUnderstandingEngine:
    global _question_engine
    if _question_engine is None:
        _question_engine = QuestionUnderstandingEngine(get_knowledge_repository())
    return _question_engine

def get_claim_retriever() -> ClaimRelevanceRetriever:
    global _claim_retriever
    if _claim_retriever is None:
        _claim_retriever = ClaimRelevanceRetriever(get_knowledge_repository())
    return _claim_retriever



_ai_verification_state: Dict[str, Any] = {
    "status": "UNCONFIGURED",
    "verified_at": None,
    "last_error_code": None,
    "last_error_message": None,
    "last_error_at": None,
    "model_tested": None,
    "provider_tested": None,
    "config_fingerprint": None,
}


def _get_current_config_fingerprint() -> str:
    raw_key = os.getenv("GEMINI_API_KEY", "").strip()
    raw_model = os.getenv("LLM_MODEL", "gemini-3.8-flash").strip()
    raw_provider = os.getenv("LLM_PROVIDER", "gemini").strip()
    enabled = os.getenv("ENABLE_EXPERIMENTAL_CHAT", "false").lower()
    return f"{raw_key[:8]}:{raw_model}:{raw_provider}:{enabled}"


def _update_ai_verification_on_success(model: str, provider: str):
    _ai_verification_state["status"] = "VERIFIED"
    _ai_verification_state["config_fingerprint"] = _get_current_config_fingerprint()
    _ai_verification_state["verified_at"] = datetime.now().isoformat()
    _ai_verification_state["model_tested"] = model
    _ai_verification_state["provider_tested"] = provider
    _ai_verification_state["last_error_code"] = None
    _ai_verification_state["last_error_message"] = None


def _update_ai_verification_on_error(code: str, message: str):
    _ai_verification_state["status"] = "DEGRADED"
    _ai_verification_state["last_error_code"] = code
    _ai_verification_state["last_error_message"] = message
    _ai_verification_state["last_error_at"] = datetime.now().isoformat()


@app.get("/api/copilot/status")
async def api_copilot_status():
    """
    Ki?m tra tr?ng th?i c?u h?nh v? t?nh s?n s?ng c?a LLM Gateway.
    Ph?n bi?t r? 4 tr?ng th?i:
    - UNCONFIGURED: thi?u ho?c c?n placeholder
    - CONFIGURED_UNVERIFIED: c? c?u h?nh nh?ng ch?a g?i th?nh c?ng
    - VERIFIED: ?? g?i th?nh c?ng v?i c?u h?nh ?ang hi?u l?c
    - DEGRADED: l?n g?i g?n nh?t g?p l?i
    """
    is_chat_enabled = os.getenv("ENABLE_EXPERIMENTAL_CHAT", "false").lower() in ("true", "1", "yes")
    raw_key = os.getenv("GEMINI_API_KEY", "").strip()
    raw_model = os.getenv("LLM_MODEL", "gemini-3.8-flash").strip()
    raw_provider = os.getenv("LLM_PROVIDER", "gemini").strip()
    
    is_placeholder = (
        not raw_key 
        or raw_key.startswith("your-") 
        or raw_key.startswith("your_") 
        or "placeholder" in raw_key.lower()
        or "example" in raw_key.lower()
    )
    is_configured = is_chat_enabled and not is_placeholder

    current_fp = _get_current_config_fingerprint()
    if _ai_verification_state.get("config_fingerprint") != current_fp:
        _ai_verification_state["config_fingerprint"] = current_fp
        _ai_verification_state["verified_at"] = None
        _ai_verification_state["last_error_code"] = None
        _ai_verification_state["last_error_message"] = None
        if not is_configured:
            _ai_verification_state["status"] = "UNCONFIGURED"
        else:
            _ai_verification_state["status"] = "CONFIGURED_UNVERIFIED"

    if not is_configured:
        curr_status = "UNCONFIGURED"
        status_text = "Chưa kết nối AI"
    else:
        curr_status = _ai_verification_state.get("status", "CONFIGURED_UNVERIFIED")
        if curr_status == "VERIFIED":
            status_text = "AI sẵn sàng (Đã kiểm chứng)"
        elif curr_status in ("DEGRADED", "ERROR"):
            status_text = f"Lỗi AI ({_ai_verification_state.get('last_error_code') or 'DEGRADED'})"
        else:
            curr_status = "CONFIGURED_UNVERIFIED"
            status_text = "Cấu hình chưa kiểm chứng"

    admin_hint = ""
    if not is_chat_enabled:
        admin_hint = "ENABLE_EXPERIMENTAL_CHAT ?ang l? false (c?n ??t true trong .env)"
    elif is_placeholder:
        admin_hint = "GEMINI_API_KEY ?ang l? placeholder (c?n c?u h?nh key th?t t? Google AI Studio trong file .env)"
    elif curr_status == "DEGRADED":
        admin_hint = f"L?i l?n g?i g?n nh?t ({_ai_verification_state.get('last_error_code')}): {_ai_verification_state.get('last_error_message')}"

    return {
        "enabled": is_chat_enabled,
        "configured": is_configured,
        "provider": raw_provider,
        "model": raw_model,
        "status": curr_status,
        "status_text": status_text,
        "verified_at": _ai_verification_state.get("verified_at"),
        "last_error_code": _ai_verification_state.get("last_error_code"),
        "last_error_message": _ai_verification_state.get("last_error_message"),
        "admin_hint": admin_hint,
        "server_restart_hint": "C?u h?nh ???c n?p khi kh?i ??ng server. Sau khi s?a file .env, vui l?ng kh?i ??ng l?i server."
    }


@app.post("/api/copilot/verify")
async def api_copilot_verify():
    """Ki?m ch?ng c?u h?nh AI th?c t? (Smoke Verification) m? kh?ng c?n thao t?c UI chat."""
    gateway = get_llm_gateway()
    raw_model = os.getenv("LLM_MODEL", "gemini-3.8-flash").strip()
    raw_provider = os.getenv("LLM_PROVIDER", "gemini").strip()
    try:
        gateway.validate_configuration()
        res = await gateway.generate(
            prompt="Ping",
            system_instruction="Tr? v? ??ng ch?: PONG",
            temperature=0.0,
            max_output_tokens=5
        )
        _update_ai_verification_on_success(raw_model, raw_provider)
        return {
            "status": "VERIFIED",
            "model": raw_model,
            "provider": raw_provider,
            "latency_ms": res.latency_ms,
            "verified_at": _ai_verification_state["verified_at"]
        }
    except LLMError as e:
        _update_ai_verification_on_error(e.code, e.message)
        raise HTTPException(
            status_code=getattr(e, "status_code", 500) or 500,
            detail={"code": e.code, "message": e.message}
        )
    except Exception as e:
        _update_ai_verification_on_error("INTERNAL_ERROR", str(e))
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(e)})



@app.post("/api/copilot/chat", response_model=ChatResponse)
async def api_copilot_chat(request: ChatRequest):
    """
    Endpoint thử nghiệm nội bộ cho Chatbot MVP kết nối thực tế.
    Được kiểm soát bởi biến môi trường ENABLE_EXPERIMENTAL_CHAT (mặc định false).
    Luồng xử lý hoàn chỉnh:
    1. Kiểm tra cờ ENABLE_EXPERIMENTAL_CHAT
    2. Phân tích câu hỏi, nhận diện sản phẩm/SKU, phân loại Intent & Safety Risk (QuestionUnderstandingEngine)
    3. Xử lý các luồng đặc biệt: Chào hỏi, Từ cấm, Nguy cơ y tế (Handoff), Cần làm rõ sản phẩm (Clarification), SKU không tồn tại, Ngoài phạm vi
    4. Đối soát & xếp hạng Claims theo mức độ liên quan ngữ nghĩa (ClaimRelevanceRetriever & ClaimEligibilityValidator)
    5. Nếu không có Claims đạt ngưỡng -> INSUFFICIENT_EVIDENCE
    6. Gọi LLM Gateway tạo bản nháp tư vấn trích dẫn nguồn Claims đã xác thực
    """
    is_chat_enabled = os.getenv("ENABLE_EXPERIMENTAL_CHAT", "false").lower() in ("true", "1", "yes")
    if not is_chat_enabled:
        raise HTTPException(
            status_code=403,
            detail="Experimental chat endpoint is disabled. Set ENABLE_EXPERIMENTAL_CHAT=true to enable internal testing."
        )

    user_msg = request.message.strip()

    # 1b. QUẢN LÝ PHIÊN HỘI THOẠI (MULTI-TURN SESSION)
    session_mgr = get_session_manager()
    session = session_mgr.get_or_create(request.session_id)
    active_session_id = session.session_id

    # Phân tích câu hỏi toàn diện (Kế thừa ngữ cảnh từ phiên)
    engine = get_question_engine()
    retriever = get_claim_retriever()
    analysis = engine.analyze_question(
        user_msg,
        requested_sku=request.product_id,
        context_sku=session.last_sku
    )

    # 1. XỬ LÝ CHÀO HỎI (GREETING)
    if analysis.decision == ChatDecision.READY_TO_SEND and analysis.intent == ChatIntent.GREETING:
        gateway = get_llm_gateway()
        try:
            result = await gateway.generate(
                prompt=user_msg,
                system_instruction=(
                    "Bạn là trợ lý AI nội bộ của DION Healthcare AI đang trong chế độ thử nghiệm nội bộ. "
                    "Hãy trả lời ngắn gọn, lịch sự bằng tiếng Việt, giới thiệu bạn là trợ lý AI của DION Healthcare AI "
                    "và có thể hỗ trợ tra cứu công dụng sản phẩm dựa trên hồ sơ Claims đã duyệt."
                ),
                temperature=0.7,
            )
            greeting_text = result.content
            trace_id = result.request_id or str(uuid.uuid4())
        except LLMConfigurationError as e:
            raise HTTPException(status_code=500, detail={"code": e.code, "message": e.message, "admin_hint": "Cần cấu hình GEMINI_API_KEY hợp lệ từ Google AI Studio trong file .env."})
        except LLMAuthenticationError as e:
            raise HTTPException(status_code=401, detail={"code": e.code, "message": e.message})
        except LLMRateLimitError as e:
            raise HTTPException(status_code=429, detail={"code": e.code, "message": e.message})
        except LLMTimeoutError as e:
            raise HTTPException(status_code=504, detail={"code": e.code, "message": e.message})
        except LLMError as e:
            raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})
        except Exception:
            raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": "Lỗi nội bộ khi gọi LLM Gateway."})

        return ChatResponse(
            session_id=active_session_id,
            message_id=str(uuid.uuid4()),
            trace_id=trace_id,
            intent=ChatIntent.GREETING,
            decision=ChatDecision.READY_TO_SEND,
            answer=greeting_text,
            product_ids=[],
            sources=[],
            risk=SafetyResult(risk_level=RiskLevel.LOW, requires_handoff=False),
            actions=[],
            ticket_id=None,
        )

    # 2. XỬ LÝ TỪ CẤM QUẢNG CÁO ĐIỀU TRỊ (BLOCKED)
    if analysis.decision == ChatDecision.BLOCKED:
        return ChatResponse(
            session_id=active_session_id,
            message_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            intent=ChatIntent.UNKNOWN,
            decision=ChatDecision.BLOCKED,
            answer=analysis.direct_answer or "Hệ thống DION Healthcare AI từ chối tư vấn công dụng điều trị, chữa bệnh theo quy định của Nghị định 342/2025/NĐ-CP.",
            product_ids=analysis.product_resolution.all_matched_skus,
            sources=[],
            risk=SafetyResult(
                risk_level=analysis.risk_level,
                risk_flags=analysis.risk_flags,
                requires_handoff=True,
                reason=analysis.risk_reason or "Yêu cầu tư vấn lâm sàng chưa có RAG & Safety Guard kiểm duyệt",
            ),
            actions=[],
            ticket_id=None,
        )

    # 3. XỬ LÝ Y TẾ NHẠY CẢM & CHUYỂN TUYẾN DƯỢC SĨ (HANDOFF_REQUIRED)
    if analysis.decision == ChatDecision.HANDOFF_REQUIRED:
        # Nếu là câu hỏi ghép (Compound Query): vừa hỏi công dụng/sản phẩm + giá + dùng cùng thuốc
        # Phân tách: Phần trả lời được (công dụng có căn cứ), phần thiếu dữ liệu (giá/ưu đãi), phần chuyển chuyên gia (y tế)
        target_sku = analysis.product_resolution.target_sku
        if target_sku and "COMPOUND_INQUIRY" in analysis.risk_flags:
            repo = get_knowledge_repository()
            prod = repo.get_product_by_sku(target_sku)
            prod_name = prod.name if prod else target_sku
            reg_num = prod.registration_number if prod and prod.registration_number else "8892/2025/ĐKSP"
            
            # Lấy các claims hợp lệ của sản phẩm
            comp_claims = retriever.retrieve_claims(user_msg, target_skus=[target_sku], is_overview=True)
            claims_text = "\n".join([f"- {c.claim.claim_text} [{c.claim.claim_id}] (Căn cứ: {c.claim.get_evidence()})" for c in comp_claims])
            
            disclaimer_val = prod.mandatory_disclaimer if prod else "Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh."
            
            compound_answer = (
                f"DION Healthcare AI phản hồi đa mục cho câu hỏi của bạn về {prod_name}:\n\n"
                f"1. [CÔNG DỤNG SẢN PHẨM] (CĂN CỨ HỒ SƠ CÔNG BỐ SỐ {reg_num}):\n"
                f"{claims_text}\n\n"
                f"2. [THÔNG TIN GIÁ BÁN & ƯU ĐÃI] (THIẾU DỮ LIỆU CHUYÊN MÔN):\n"
                f"- Giá bán, chương trình khuyến mãi và chính sách bán buôn/lẻ thuộc phạm vi quản lý của phòng Kinh doanh. "
                f"Vui lòng tra cứu bảng giá niêm yết hiện hành hoặc liên hệ Trưởng bộ phận bán hàng.\n\n"
                f"3. [TƯƠNG TÁC THUỐC & AN TOÀN SỬ DỤNG] (CHUYỂN DƯỢC SĨ):\n"
                f"- Việc dùng chung sản phẩm với thuốc điều trị cần được xem xét khoảng cách thời gian uống và tương tác hấp thu. "
                f"Hệ thống đã gắn cờ yêu cầu Dược sĩ chuyên môn tư vấn trực tiếp cho trường hợp này.\n\n"
                f"Khuyến cáo pháp lý: {disclaimer_val}\n\n"
                f"[Bản nháp tư vấn đa mục — Yêu cầu Dược sĩ duyệt trước khi gửi khách hàng]"
            )
            
            citations = [
                CitationInfo(
                    claim_id=c.claim.claim_id,
                    document_id=c.claim.source_document_id or c.claim.get_evidence(),
                    document_title=c.claim.get_evidence(),
                )
                for c in comp_claims
            ]
            
            session.add_turn(
                user_msg=user_msg,
                assistant_msg=compound_answer,
                intent=str(ChatIntent.MEDICAL_RISK),
                decision=str(ChatDecision.HANDOFF_REQUIRED),
                skus=[target_sku],
                citations=[c.model_dump() for c in citations]
            )
            
            return ChatResponse(
                session_id=active_session_id,
                message_id=str(uuid.uuid4()),
                trace_id=str(uuid.uuid4()),
                intent=ChatIntent.MEDICAL_RISK,
                decision=ChatDecision.HANDOFF_REQUIRED,
                answer=compound_answer,
                product_ids=[target_sku],
                sources=citations,
                risk=SafetyResult(
                    risk_level=analysis.risk_level,
                    risk_flags=analysis.risk_flags,
                    requires_handoff=True,
                    reason=analysis.risk_reason,
                    recommended_department="DƯỢC VỤ",
                ),
                actions=[ChatAction(type="TRANSFER_PHARMACIST", label="Chuyển Dược sĩ tư vấn", requires_approval=True)],
                ticket_id=None,
            )

        return ChatResponse(
            session_id=active_session_id,
            message_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            intent=ChatIntent.MEDICAL_RISK,
            decision=ChatDecision.HANDOFF_REQUIRED,
            answer=analysis.direct_answer,
            product_ids=analysis.product_resolution.all_matched_skus,
            sources=[],
            risk=SafetyResult(
                risk_level=analysis.risk_level,
                risk_flags=analysis.risk_flags,
                requires_handoff=True,
                reason=analysis.risk_reason,
                recommended_department="DƯỢC VỤ",
            ),
            actions=[ChatAction(type="TRANSFER_PHARMACIST", label="Chuyển Dược sĩ tư vấn", requires_approval=True)],
            ticket_id=None,
        )

    # 4. XỬ LÝ CẦN LÀM RÕ SẢN PHẨM (CLARIFICATION_REQUIRED)
    if analysis.decision == ChatDecision.CLARIFICATION_REQUIRED:
        return ChatResponse(
            session_id=active_session_id,
            message_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            intent=analysis.intent,
            decision=ChatDecision.CLARIFICATION_REQUIRED,
            answer=analysis.direct_answer,
            product_ids=[],
            sources=[],
            risk=SafetyResult(risk_level=RiskLevel.LOW, requires_handoff=False),
            actions=[ChatAction(type="SELECT_PRODUCT", label="Chọn sản phẩm", requires_approval=False)],
            ticket_id=None,
        )

    # 5. XỬ LÝ SKU KHÔNG TỒN TẠI (NO FALLBACK)
    if analysis.product_resolution.is_unknown_sku:
        return ChatResponse(
            session_id=active_session_id,
            message_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            intent=ChatIntent.PRODUCT_INFO,
            decision=ChatDecision.INSUFFICIENT_EVIDENCE,
            answer=analysis.direct_answer,
            product_ids=[],
            sources=[],
            risk=SafetyResult(risk_level=RiskLevel.LOW, requires_handoff=False),
            actions=[],
            ticket_id=None,
        )

    # 5b. XỬ LÝ Ý ĐỊNH ĐẶT MUA HÀNG (BUY_PRODUCT)
    if analysis.intent == ChatIntent.BUY_PRODUCT:
        return ChatResponse(
            session_id=active_session_id,
            message_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            intent=ChatIntent.BUY_PRODUCT,
            decision=analysis.decision or ChatDecision.READY_TO_SEND,
            answer=analysis.direct_answer,
            product_ids=analysis.product_resolution.all_matched_skus,
            sources=[],
            risk=SafetyResult(risk_level=RiskLevel.LOW, requires_handoff=False),
            actions=[ChatAction(type="CONTACT_SALES", label="Liên hệ Bộ phận Kinh doanh", requires_approval=False)],
            ticket_id=None,
        )

    # 6. XỬ LÝ CÂU HỎI NGOÀI PHẠM VI (OFF_TOPIC)
    if analysis.product_resolution.is_out_of_scope or analysis.intent == ChatIntent.OFF_TOPIC:
        return ChatResponse(
            session_id=active_session_id,
            message_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            intent=ChatIntent.OFF_TOPIC,
            decision=ChatDecision.INSUFFICIENT_EVIDENCE,
            answer=analysis.direct_answer,
            product_ids=[],
            sources=[],
            risk=SafetyResult(risk_level=RiskLevel.LOW, requires_handoff=False),
            actions=[],
            ticket_id=None,
        )

    # 7. TRUY XUẤT CLAIMS THEO MỨC ĐỘ LIÊN QUAN (XỬ LÝ ĐỘC LẬP TỪNG SKU CHO SO SÁNH)
    target_skus = analysis.product_resolution.all_matched_skus
    retrieved_items = []
    repo = get_knowledge_repository()

    if analysis.intent == ChatIntent.PRODUCT_COMPARISON and len(target_skus) > 1:
        # Truy xuất Claims độc lập cho từng SKU để đảm bảo đối chiếu công bằng
        for s in target_skus:
            s_items = retriever.retrieve_claims(user_msg, target_skus=[s], top_k=2)
            if not s_items:
                # Nếu không có claim khớp từ khóa cụ thể, lấy các claims được duyệt cơ bản của SKU đó
                s_items = retriever.retrieve_claims("", target_skus=[s], top_k=2, is_overview=True)
            retrieved_items.extend(s_items)
    else:
        retrieved_items = retriever.retrieve_claims(
            user_msg,
            target_skus=target_skus,
            top_k=5 if analysis.is_overview_query else 3,
            is_overview=analysis.is_overview_query
        )

    # Nếu là yêu cầu hỏi tiếp / rút gọn bản nháp (Multi-turn Follow-up: "Ngắn hơn", "Viết lại")
    if not retrieved_items and session.turns and target_skus:
        if any(rw in user_msg.lower() for rw in ["ngắn hơn", "ngắn gọn", "viết lại", "soạn lại", "rút gọn", "súc tích", "tóm tắt"]):
            retrieved_items = retriever.retrieve_claims("", target_skus=target_skus, is_overview=True)

    # Nếu không có Claims nào đạt ngưỡng liên quan
    if not retrieved_items:
        product_ids_list = target_skus if len(target_skus) == 1 else []
        prod_obj = repo.get_product_by_sku(product_ids_list[0]) if product_ids_list else None
        prod_name = prod_obj.name if prod_obj else "sản phẩm"
        
        diag = retriever.diagnose_retrieval(user_msg, target_skus, retrieved_items, is_overview=analysis.is_overview_query)
        
        # Phân biệt rõ: nếu hỏi công dụng chuyên biệt không có trong hồ sơ
        if analysis.specific_unsupported_condition:
            no_evidence_msg = (
                f"Hiện tại trong hồ sơ công bố của {prod_name} chưa có đủ căn cứ xác minh từ các phát biểu công dụng (Claim) "
                f"được phê duyệt liên quan đến '{analysis.specific_unsupported_condition}'. "
                f"Để tuân thủ quy chuẩn y dược và bảo vệ an toàn cho người dùng, hệ thống không xác nhận công dụng này."
            )
        else:
            no_evidence_msg = (
                f"Hiện tại hệ thống chưa có đủ căn cứ xác minh từ các phát biểu công dụng (Claims) đã được phê duyệt để trả lời cho câu hỏi này. "
                f"Để đảm bảo an toàn và tuân thủ quy chế thông tin y dược, AI không tự ý suy đoán công dụng chưa được công bố."
            )
            
        session.add_turn(
            user_msg=user_msg,
            assistant_msg=no_evidence_msg,
            intent=str(analysis.intent),
            decision=str(ChatDecision.INSUFFICIENT_EVIDENCE),
            skus=product_ids_list
        )
        return ChatResponse(
            session_id=active_session_id,
            message_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            intent=analysis.intent,
            decision=ChatDecision.INSUFFICIENT_EVIDENCE,
            answer=no_evidence_msg,
            product_ids=product_ids_list,
            sources=[],
            risk=SafetyResult(risk_level=RiskLevel.LOW, requires_handoff=False),
            actions=[],
            ticket_id=None,
        )

    # 8. TỔNG HỢP NGUỒN VÀ GỌI LLM GATEWAY TẠO BẢN NHÁP
    top_claims = [item.claim for item in retrieved_items]
    involved_skus = list(dict.fromkeys([c.product_sku for c in top_claims]))

    claims_text_block = "\n".join([
        f"- [{c.claim_id}] (SKU: {c.product_sku}): \"{c.claim_text}\" (Nguồn chứng minh: {c.get_evidence()})"
        for c in top_claims
    ])

    # Lấy thông tin disclaimer của sản phẩm
    first_prod = repo.get_product_by_sku(involved_skus[0]) if involved_skus else None
    disclaimer_text = first_prod.mandatory_disclaimer if first_prod else "Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh."

    if analysis.intent == ChatIntent.PRODUCT_COMPARISON and len(involved_skus) > 1:
        system_instruction = (
            "Bạn là trợ lý AI chuyên môn của hệ thống DION Healthcare AI.\n"
            "NHIỆM VỤ: So sánh khách quan giữa các sản phẩm dựa TRỰC TIẾP và DUY NHẤT vào danh sách Claims đã được phê duyệt dưới đây.\n"
            "QUY TẮC SO SÁNH BẮT BUỘC:\n"
            "1. So sánh theo tiêu chí có dữ liệu (Thành phần chính, công dụng đã duyệt, đối tượng sử dụng của từng sản phẩm).\n"
            "2. Điểm nào không có căn cứ/không có claims thì nêu rõ 'Chưa có dữ liệu công bố'.\n"
            "3. TUYỆT ĐỐI KHÔNG kết luận sản phẩm nào 'tốt hơn' hoặc 'vượt trội hơn' nếu không có bằng chứng lâm sàng đối đầu.\n"
            "4. Không suy ra hiệu quả vượt trội từ bảng thành phần.\n"
            "5. Không tự suy diễn công dụng chữa bệnh hoặc điều trị.\n"
            f"6. Bắt buộc kèm khuyến cáo pháp lý: '{disclaimer_text}'.\n\n"
            f"[CÁC CLAIMS ĐÃ ĐƯỢC DUYỆT CỦA CÁC SẢN PHẨM]\n"
            f"{claims_text_block}"
        )
    elif analysis.is_overview_query:
        prod = first_prod
        active_ing_str = ", ".join([f"{ing.get('name', '')} ({ing.get('amount_per_serving', '')})" if isinstance(ing, dict) else str(ing) for ing in prod.active_ingredients]) if prod and prod.active_ingredients else "Chiết xuất theo hồ sơ công bố"
        reg_str = prod.registration_number if prod and prod.registration_number else "8892/2025/ĐKSP"
        valid_clinical = []
        if prod and prod.clinical_evidence:
            for ce in prod.clinical_evidence:
                if isinstance(ce, dict):
                    if ce.get("status") != "EVIDENCE_MISMATCH" and ce.get("is_verified") is not False:
                        valid_clinical.append(ce.get("pmid", str(ce)))
                elif isinstance(ce, str):
                    if "30121111" not in ce and "29482012" not in ce:
                        valid_clinical.append(ce)
        clinical_str = ", ".join(valid_clinical) if valid_clinical else f"Ch?a c? RCT l?m s?ng ??c l?p (C?n c? th?m ??nh theo {reg_str})"

        system_instruction = (
            "Bạn là trợ lý AI chuyên môn của hệ thống DION Healthcare AI.\n"
            "NHIỆM VỤ: Trả lời câu hỏi tổng quan / ưu điểm nổi bật của nhân viên tư vấn dựa TRỰC TIẾP và DUY NHẤT vào hồ sơ sản phẩm và danh sách Claims đã được phê duyệt dưới đây.\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. Bắt đầu bằng câu: 'Những đặc điểm được ghi nhận trong hồ sơ sản phẩm gồm:'\n"
            "2. Trình bày các đặc điểm thành phần, công dụng đã duyệt kèm mã Claims trích dẫn, và số đăng ký công bố.\n"
            "3. TUYỆT ĐỐI KHÔNG tự ý sử dụng các từ ngữ khẳng định vượt trội như: 'tốt nhất', 'hấp thu vượt trội', 'an toàn tuyệt đối', 'tốt hơn sản phẩm khác' nếu không có bằng chứng đối đầu.\n"
            "4. Không khẳng định có tác dụng chữa bệnh hay thay thế thuốc.\n"
            f"5. Cuối câu trả lời bắt buộc kèm khuyến cáo pháp lý: '{disclaimer_text}'.\n"
            "6. Trả lời bằng tiếng Việt chuyên nghiệp, súc tích và mạch lạc.\n\n"
            f"[HỒ SƠ SẢN PHẨM]\n"
            f"- Tên sản phẩm: {prod.name if prod else involved_skus[0]}\n"
            f"- Số ĐKSP: {reg_str}\n"
            f"- Thành phần chính: {active_ing_str}\n"
            f"- Bằng chứng lâm sàng / Nguồn trích dẫn: {clinical_str}\n\n"
            f"[CÁC CLAIMS ĐÃ ĐƯỢC DUYỆT CỦA SẢN PHẨM]\n"
            f"{claims_text_block}"
        )
    else:
        system_instruction = (
            "Bạn là trợ lý AI chuyên môn của hệ thống DION Healthcare AI.\n"
            "NHIỆM VỤ: Trả lời câu hỏi của nhân viên tư vấn dựa TRỰC TIẾP và DUY NHẤT vào các phát biểu công dụng (Claims) đã được phê duyệt dưới đây.\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. TUYỆT ĐỐI KHÔNG tự ý suy đoán, thêm bớt công dụng, liều dùng, thành phần hoặc đối tượng sử dụng nằm ngoài danh sách Claims.\n"
            "2. Không khẳng định có tác dụng chữa bệnh hay thay thế thuốc.\n"
            "3. Trả lời trực diện, súc tích trong tối đa 3-4 câu, đi thẳng vào nội dung tư vấn, không viết lan man.\n"
            f"4. Cuối câu trả lời bắt buộc kèm khuyến cáo pháp lý: '{disclaimer_text}'.\n"
            "5. Trả lời bằng tiếng Việt chuyên nghiệp, gãy gọn và mạch lạc.\n\n"
            f"[CÁC CLAIMS ĐÃ ĐƯỢC DUYỆT]\n"
            f"{claims_text_block}"
        )

    if session.turns and any(rw in user_msg.lower() for rw in ["ngắn hơn", "ngắn gọn", "viết lại", "soạn lại", "rút gọn", "súc tích", "tóm tắt"]):
        last_draft = session.turns[-1].get("assistant_msg", "")
        prompt = (
            f"Bản nháp tư vấn trước đó của hệ thống:\n{last_draft}\n\n"
            f"Yêu cầu chỉnh sửa của nhân viên tư vấn: {user_msg}\n\n"
            "Hãy viết lại bản nháp trên theo đúng yêu cầu (rút gọn/súc tích), "
            "TUYỆT ĐỐI không thêm công dụng ngoài danh sách Claims và phải giữ nguyên khuyến cáo pháp lý bắt buộc."
        )
    else:
        prompt = (
            f"Câu hỏi của khách hàng / nhân viên: {user_msg}\n\n"
            "Hãy tổng hợp câu trả lời tư vấn ngắn gọn, chính xác dựa trên các Claims được cung cấp."
        )

    gateway = get_llm_gateway()
    try:
        result = await gateway.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.2,
            max_output_tokens=1024,
        )
        generated_answer = result.content
        trace_id = result.request_id or str(uuid.uuid4())
        _active_model = result.model or os.getenv("LLM_MODEL", "gemini-3.8-flash")
        _active_provider = result.provider or os.getenv("LLM_PROVIDER", "gemini")
        _update_ai_verification_on_success(model=_active_model, provider=_active_provider)
    except LLMConfigurationError as e:
        _update_ai_verification_on_error(e.code, e.message)
        raise HTTPException(status_code=500, detail={"code": e.code, "message": e.message, "admin_hint": "Cần cấu hình GEMINI_API_KEY hợp lệ từ Google AI Studio trong file .env."})
    except LLMAuthenticationError as e:
        _update_ai_verification_on_error(e.code, e.message)
        raise HTTPException(status_code=401, detail={"code": e.code, "message": e.message})
    except LLMRateLimitError as e:
        _update_ai_verification_on_error(e.code, e.message)
        raise HTTPException(status_code=429, detail={"code": e.code, "message": e.message})
    except LLMTimeoutError as e:
        _update_ai_verification_on_error(e.code, e.message)
        raise HTTPException(status_code=504, detail={"code": e.code, "message": e.message})
    except LLMError as e:
        _update_ai_verification_on_error(e.code, e.message)
        raise HTTPException(status_code=getattr(e, "status_code", 500) or 500, detail={"code": e.code, "message": e.message})
    except Exception as e:
        _update_ai_verification_on_error("INTERNAL_ERROR", str(e))
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": "L?i n?i b? khi g?i LLM Gateway."})
    draft_disclaimer = "\n\n[Bản nháp trả lời đề xuất bởi AI Copilot — Nhân viên cần duyệt lại trước khi gửi khách hàng]"
    if draft_disclaimer not in generated_answer:
        generated_answer += draft_disclaimer

    citations = [
        CitationInfo(
            claim_id=c.claim_id,
            document_id=c.source_document_id or c.get_evidence(),
            document_title=c.get_evidence(),
        )
        for c in top_claims
    ]

    # Cập nhật lịch sử lượt chat vào session
    session.add_turn(
        user_msg=user_msg,
        assistant_msg=generated_answer,
        intent=str(analysis.intent),
        decision=str(ChatDecision.DRAFT_FOR_APPROVAL),
        skus=involved_skus,
        citations=[c.model_dump() for c in citations]
    )

    return ChatResponse(
        session_id=active_session_id,
        message_id=str(uuid.uuid4()),
        trace_id=trace_id,
        intent=analysis.intent,
        decision=ChatDecision.DRAFT_FOR_APPROVAL,
        answer=generated_answer,
        product_ids=involved_skus,
        sources=citations,
        risk=SafetyResult(risk_level=RiskLevel.LOW, requires_handoff=False),
        actions=[ChatAction(type="COPY_TEXT", label="Sao chép câu trả lời", requires_approval=True)],
        ticket_id=None,
    )







# --- GIẢI PHÁP 5: AI CUSTOMER CARE WORKSPACE (CHĂM SÓC KHÁCH HÀNG & QUYỀN RIÊNG TƯ) ---
@app.get("/api/customer-care")
async def api_customer_care():
    care_svc = get_customer_care_service()
    metrics = care_svc.get_metrics()
    tasks = care_svc.list_tasks()
    customers = care_svc.list_customers()

    sample_customers = []
    for c in customers:
        p = c.purchases[0] if c.purchases else None
        sku_bought = p.product_name if p else "Sản phẩm DION"
        pdate = p.delivery_date if p else "2026-10-01"
        try:
            days = (datetime.now() - datetime.strptime(pdate, "%Y-%m-%d")).days
        except Exception:
            days = 0

        status_val = "BÌNH THƯỜNG"
        if c.active_complaint:
            status_val = "KHÓA BÁN HÀNG — ĐANG KHIẾU NẠI"
        elif days >= 25:
            status_val = "CẦN NHẮC TÁI MUA"
        elif days >= 7:
            status_val = "HỎI THĂM TRẢI NGHIỆM"

        sample_customers.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "sku_bought": sku_bought,
            "purchase_date": pdate,
            "day_in_cycle": min(30, max(1, days)),
            "status": status_val,
            "consent_status": c.consent_status,
            "complaint_status": c.complaint_status,
            "is_opt_out_marketing": c.is_opt_out_marketing,
            "active_complaint": c.active_complaint,
            "suggested_message": f"Kịch bản chăm sóc theo chu kỳ ngày {days}"
        })

    staff_directory = [
        {"id": "NV-01", "name": "Dược sĩ Trần Mai", "role": "Dược sĩ Lâm sàng", "department": "Dược vụ / Lâm sàng", "is_clinical": True},
        {"id": "NV-02", "name": "Dược sĩ Lê Hoàng", "role": "Dược sĩ Chuyên môn", "department": "Dược vụ / Lâm sàng", "is_clinical": True},
        {"id": "NV-03", "name": "Dược vụ", "role": "Bộ phận Dược vụ", "department": "Dược vụ / Lâm sàng", "is_clinical": True},
        {"id": "NV-04", "name": "Chuyên viên Thảo", "role": "Chuyên viên CSKH", "department": "CSKH", "is_clinical": False},
        {"id": "NV-05", "name": "Chuyên viên Nam", "role": "Chuyên viên CSKH", "department": "CSKH", "is_clinical": False},
        {"id": "NV-06", "name": "Chuyên viên CSKH", "role": "Tư vấn viên", "department": "CSKH", "is_clinical": False},
        {"id": "NV-07", "name": "Nhân viên kiểm thử", "role": "Kiểm thử viên", "department": "QA", "is_clinical": True},
    ]

    reschedule_reasons = [
        "Khách yêu cầu gọi lại",
        "Khách chưa tiện trao đổi",
        "Cần chờ xác minh thông tin",
        "Chờ nhân viên chuyên môn",
        "Cần liên hệ lại sau",
        "Khác"
    ]

    time_slots = [
        "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00",
        "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"
    ]

    action_options = [
        {"id": "CONTACTED", "label": "Đã liên hệ với khách", "sub_fields": "contact_outcome"},
        {"id": "UNREACHABLE", "label": "Không liên hệ được", "sub_fields": "unreachable_reason"},
        {"id": "CALLBACK_REQUESTED", "label": "Khách yêu cầu gọi lại", "sub_fields": "reschedule"},
        {"id": "FEEDBACK_RECEIVED", "label": "Đã tiếp nhận phản hồi", "sub_fields": "notes_only"},
        {"id": "TRANSFERRED", "label": "Đã chuyển cho bộ phận khác", "sub_fields": "transfer"},
        {"id": "PENDING_REVIEW", "label": "Đang chờ xử lý / Xem xét", "sub_fields": "notes_only"},
        {"id": "RESOLVED", "label": "Đã giải quyết yêu cầu / Hoàn thành", "sub_fields": "resolution_outcome"}
    ]

    return {
        "metrics": metrics.model_dump(),
        "tasks": [t.model_dump() for t in tasks],
        "customers": [c.model_dump() for c in customers],
        "sample_customers": sample_customers,
        "staff_directory": staff_directory,
        "reschedule_reasons": reschedule_reasons,
        "time_slots": time_slots,
        "action_options": action_options,
        "retention_rules": [
            {"day": 7, "purpose": "Khảo sát cảm nhận sử dụng & Hướng dẫn uống đúng cách", "action": "Gửi tin nhắn ZNS chăm sóc khách hàng"},
            {"day": 25, "purpose": "Nhắc bổ sung chu kỳ tiếp theo (Sắp hết hộp 30 ngày)", "action": "Tạo lịch gọi cho chuyên viên tư vấn tái mua"},
            {"day": 60, "purpose": "Tư vấn lộ trình duy trì dài hạn theo khuyến nghị chuyên gia", "action": "Gợi ý gói combo tiết kiệm"}
        ],
        "privacy_compliance": {
            "law_reference": "Luật Bảo vệ Dữ liệu Cá nhân số 91/2025/QH15 & Nghị định 356/2025/NĐ-CP",
            "opt_out_rule": "Khi khách hàng bấm từ chối nhận tin, hệ thống tự động khóa vĩnh viễn quyền gửi tin tiếp thị trên mọi kênh.",
            "incident_lockout_rule": "Khi khách hàng phát sinh khiếu nại chất lượng hoặc phản ứng phụ, khóa ngay lập tức toàn bộ chiến dịch bán hàng."
        }
    }


@app.post("/api/customer-care/evaluate")
@app.post("/api/customer-care/evaluate-rules")
async def api_customer_care_evaluate():
    care_svc = get_customer_care_service()
    tasks = care_svc.evaluate_rules()
    return {
        "status": "SUCCESS",
        "new_tasks_count": len(tasks),
        "updated_tasks_count": len(tasks),
        "tasks": [t.model_dump() for t in tasks],
        "metrics": care_svc.get_metrics().model_dump()
    }


@app.post("/api/customer-care/draft")
async def api_customer_care_draft(req: AutoDraftRequest):
    care_svc = get_customer_care_service()
    return care_svc.auto_draft_message(req.customer_id, req.task_id)


def check_request_authentication(req: Request) -> Dict[str, Any]:
    """
    Kiểm tra cơ chế xác thực danh tính.
    Dự án hiện tại CHƯA triển khai SSO / JWT token / Session Cookie (AUTH_NOT_IMPLEMENTED).
    Chỉ cho phép chạy chế độ Local Demo Sandbox với dữ liệu mẫu (is_demo=True).
    Không coi header Authorization hoặc cookie giả mạo là đã xác thực.
    """
    return {
        "authenticated": False,
        "auth_code": "AUTH_NOT_IMPLEMENTED",
        "user_id": "demo_sandbox_user",
        "message": "Hệ thống chưa triển khai cơ chế xác thực phiên người dùng (SSO/JWT - AUTH_NOT_IMPLEMENTED). Mọi thao tác chạy trong môi trường Demo Sandbox nội bộ.",
        "is_demo_mode": True,
        "auth_status": "LOCAL_DEMO_SANDBOX"
    }


@app.post("/api/customer-care/log-action")
async def api_customer_care_log_action(req: ActionLogRequest, request: Request):
    auth_info = check_request_authentication(request)
    care_svc = get_customer_care_service()
    
    task = care_svc.get_task(req.task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": f"Không tìm thấy công việc {req.task_id}"})

    cust = care_svc.get_customer(task.customer_id)
    if cust and not getattr(cust, "is_demo", True) and not auth_info["authenticated"]:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_NOT_IMPLEMENTED",
                "message": "Thao tác trên hồ sơ khách hàng thật bị từ chối do hệ thống chưa triển khai xác thực danh tính (AUTH_NOT_IMPLEMENTED)."
            }
        )

    res = care_svc.log_action(
        task_id=req.task_id,
        action_type=req.action_type,
        performed_by=req.performed_by,
        notes=req.notes,
        auth_context=auth_info
    )
    if res.get("status") == "ERROR":
        code = res.get("code")
        if code in ("UNAUTHORIZED_STAFF", "PERMISSION_DENIED"):
            raise HTTPException(status_code=403, detail=res)
        elif code == "AUTH_NOT_IMPLEMENTED":
            raise HTTPException(status_code=401, detail=res)
        elif code == "TASK_NOT_FOUND":
            raise HTTPException(status_code=404, detail=res)
        else:
            raise HTTPException(status_code=400, detail=res)
    return res


@app.post("/api/customer-care/reschedule")
async def api_customer_care_reschedule(req: RescheduleRequest):
    care_svc = get_customer_care_service()
    res = care_svc.reschedule_task(
        task_id=req.task_id,
        new_due_date=req.new_due_date,
        notes=req.notes or "",
        time_slot=getattr(req, "time_slot", None),
        reschedule_reason=getattr(req, "reschedule_reason", None)
    )
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res)
    return res


@app.post("/api/customer-care/assign")
async def api_customer_care_assign(req: AssignTaskRequest):
    care_svc = get_customer_care_service()
    res = care_svc.assign_task(
        task_id=req.task_id,
        assignee=req.assignee,
        priority=getattr(req, "priority", None),
        new_due_date=getattr(req, "new_due_date", None),
        notes=getattr(req, "notes", "") or ""
    )
    if res.get("status") == "ERROR":
        status_code = 403 if res.get("code") in ("PERMISSION_DENIED", "UNAUTHORIZED_STAFF") else 400
        raise HTTPException(status_code=status_code, detail=res)
    return res


class CustomerCareAnalyzeReplyRequest(BaseModel):
    customer_id: str
    reply_text: str


@app.post("/api/customer-care/analyze-reply")
async def api_customer_care_analyze_reply(req: CustomerCareAnalyzeReplyRequest):
    care_svc = get_customer_care_service()
    return care_svc.analyze_customer_reply(req.customer_id, req.reply_text)


@app.post("/api/customer-care/customers")
async def api_customer_care_create_customer(req: CreateCustomerRequest):
    if not getattr(req, "is_demo", True):
        raise HTTPException(
            status_code=401,
            detail="AUTH_NOT_IMPLEMENTED: Hệ thống đang ở chế độ Demo Sandbox PoC. Thao tác trên hồ sơ dữ liệu thực yêu cầu xác thực SSO/IAM doanh nghiệp thật."
        )
    care_svc = get_customer_care_service()
    res = care_svc.create_customer(req)
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res)
    return res


@app.get("/api/customer-care/customers/{customer_id}/timeline")
async def api_customer_care_customer_timeline(customer_id: str):
    care_svc = get_customer_care_service()
    res = care_svc.get_customer_timeline(customer_id)
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=404, detail=res)
    return res


@app.get("/api/customer-care/customers/{customer_id}/state")
async def api_customer_care_customer_state(customer_id: str):
    care_svc = get_customer_care_service()
    res = care_svc.analyze_customer_state(customer_id)
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=404, detail=res)
    return res


@app.post("/api/customer-care/interactions")
async def api_customer_care_add_interaction(req: CreateInteractionRequest):
    care_svc = get_customer_care_service()
    res = care_svc.add_interaction(req)
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res)
    return res


@app.post("/api/customer-care/purchases")
async def api_customer_care_add_purchase(req: CreatePurchaseRequest):
    care_svc = get_customer_care_service()
    res = care_svc.add_purchase(req)
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res)
    return res


@app.post("/api/customer-care/support-requests")
async def api_customer_care_add_support_request(req: CreateSupportRequest):
    care_svc = get_customer_care_service()
    res = care_svc.add_support_request(req)
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res)
    return res


@app.post("/api/customer-care/callback-requests")
async def api_customer_care_add_callback_request(req: CreateCallbackRequest):
    care_svc = get_customer_care_service()
    res = care_svc.add_callback_request(req)
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res)
    return res


class CsvImportPayload(BaseModel):
    import_type: str  # CUSTOMERS, PURCHASES
    csv_content: str
    dry_run: bool = True


@app.post("/api/customer-care/import/preview")
async def api_customer_care_import_preview(payload: CsvImportPayload):
    care_svc = get_customer_care_service()
    if payload.import_type.upper() == "CUSTOMERS":
        return care_svc.import_customers_csv(payload.csv_content, dry_run=True)
    elif payload.import_type.upper() == "PURCHASES":
        return care_svc.import_purchases_csv(payload.csv_content, dry_run=True)
    else:
        raise HTTPException(status_code=400, detail={"code": "INVALID_IMPORT_TYPE", "message": "Loại import không hợp lệ (hỗ trợ CUSTOMERS hoặc PURCHASES)"})


@app.post("/api/customer-care/import/execute")
async def api_customer_care_import_execute(payload: CsvImportPayload):
    care_svc = get_customer_care_service()
    if payload.import_type.upper() == "CUSTOMERS":
        return care_svc.import_customers_csv(payload.csv_content, dry_run=False)
    elif payload.import_type.upper() == "PURCHASES":
        return care_svc.import_purchases_csv(payload.csv_content, dry_run=False)
    else:
        raise HTTPException(status_code=400, detail={"code": "INVALID_IMPORT_TYPE", "message": "Loại import không hợp lệ"})


@app.post("/api/customer-care/link-copilot-interaction")
async def api_customer_care_link_copilot_interaction(req: LinkCopilotInteractionRequest):
    care_svc = get_customer_care_service()
    res = care_svc.link_copilot_interaction(req)
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res)
    return res

# --- GIẢI PHÁP 6: AI RESEARCH INTELLIGENCE (NGHIÊN CỨU & BẰNG CHỨNG PUBMED) ---
@app.get("/api/research/ingredients")
async def api_research_ingredients(category: Optional[str] = None):
    """Danh mục hoạt chất được theo dõi bằng chứng y văn lâm sàng"""
    svc = get_research_service()
    ingredients = svc.get_active_ingredients(category=category)
    return {"ingredients": [ing.model_dump() for ing in ingredients], "total": len(ingredients)}


@app.get("/api/research/studies")
async def api_research_studies(
    query: Optional[str] = None,
    ingredient: Optional[str] = None,
    study_type: Optional[str] = None,
    evidence_grade: Optional[str] = None,
    target_group: Optional[str] = None,
    limit: int = 50,
):
    """Tìm kiếm nghiên cứu y văn lâm sàng chuẩn PubMed theo nhiều tiêu chí"""
    svc = get_research_service()
    req = SearchStudiesRequest(
        query=query,
        ingredient=ingredient,
        study_type=study_type,
        evidence_grade=evidence_grade,
        target_group=target_group,
        limit=limit,
    )
    studies = svc.search_studies(req)
    return {"studies": [s.model_dump() for s in studies], "total": len(studies)}


@app.get("/api/research/studies/{pmid}")
async def api_research_study_detail(pmid: str):
    """Xem chi tiết một nghiên cứu y văn lâm sàng theo mã PMID"""
    svc = get_research_service()
    study = svc.get_study_by_pmid(pmid)
    if not study:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy nghiên cứu y văn với PMID '{pmid}'")
    return study.model_dump()


@app.get("/api/research/pharmacology/compare")
async def api_research_pharmacology_compare(category: str = "CANXI"):
    """Bảng so sánh chuyên sâu dược lý học giữa các dạng muối và phân tích khoảng trống khẩu phần"""
    svc = get_research_service()
    return svc.compare_pharmacology(category=category)


@app.post("/api/research/ai-analyze")
async def api_research_ai_analyze(request: AIAnalyzeStudyRequest):
    """AI trích xuất PICO và đánh giá cấp độ y văn từ Abstract y khoa"""
    svc = get_research_service()
    try:
        analysis = await svc.analyze_study_abstract(
            abstract_text=request.abstract_text,
            target_product_sku=request.target_product_sku,
        )
        return {"status": "SUCCESS", "analysis": analysis.model_dump()}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích AI: {str(e)}")


@app.post("/api/research/link-to-product-claim")
async def api_research_link_claim(request: LinkClaimRequest):
    """Gắn kết nghiên cứu đã thẩm định vào hồ sơ bằng chứng lâm sàng sản phẩm DION"""
    svc = get_research_service()
    try:
        res = svc.link_study_to_product_claim(request)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi liên kết bằng chứng: {str(e)}")


@app.get("/api/research-intelligence")
async def api_research_intelligence(ingredient: str = "Lithothamnion"):
    """
    Endpoint tương thích ngược cho Tab Nghiên cứu PubMed cũ.
    Trả về cấu trúc dữ liệu khoa học kết nối trực tiếp với MedicalLiteratureRepository.
    """
    svc = get_research_service()
    studies = svc.search_studies(SearchStudiesRequest(ingredient=ingredient, limit=10))
    if not studies:
        studies = svc.search_studies(SearchStudiesRequest(query=ingredient, limit=10))
    if not studies:
        studies = svc.search_studies(SearchStudiesRequest(limit=5))

    evidence_table = []
    for s in studies:
        grade_label = s.evidence_grade.value if hasattr(s.evidence_grade, "value") else str(s.evidence_grade)
        study_type_label = s.study_type.value if hasattr(s.study_type, "value") else str(s.study_type)
        evidence_table.append({
            "pmid": f"PMID: {s.pmid}",
            "study_type": study_type_label,
            "sample_size": s.sample_size,
            "dosage": s.dosage_used,
            "key_findings": s.primary_outcome,
            "adverse_events": s.adverse_events,
            "evidence_grade": f"Hạng {grade_label[-1]} (Oxford CEBM)",
            "title": s.title,
            "url": s.pubmed_url,
        })

    summary = (
        "Chiết xuất tảo đỏ vôi hóa Lithothamnion calcareum chứa 32% Canxi nguyên tố, 2.2% Magie và hơn 70 khoáng chất vi lượng, có cấu trúc xốp tổ ong giúp tăng độ hòa tan và sinh khả dụng so với canxi đá vôi."
        if "litho" in ingredient.lower()
        else f"Tổng hợp y văn lâm sàng và dữ liệu PubMed cập nhật cho hoạt chất {ingredient}."
    )

    return {
        "ingredient": ingredient,
        "scientific_summary": summary,
        "evidence_table": evidence_table,
        "total_studies": len(evidence_table),
    }


@app.delete("/api/copilot/session/{session_id}")
async def api_copilot_clear_session(session_id: str):
    """Xóa lịch sử phiên chat để bắt đầu hội thoại mới"""
    mgr = get_session_manager()
    success = mgr.clear_session(session_id)
    return {"status": "success", "session_id": session_id, "cleared": success}


# ============================================================================
# --- CARESOFT FIRST-TOUCH TRIAGE & LEAD QUALIFICATION (VISTAFA POC) ---
# ============================================================================

@app.post("/api/caresoft/triage")
async def api_caresoft_triage(
    chat_text: str = Body(..., embed=True),
    channel: str = Body("FACEBOOK", embed=True),
    customer_name: Optional[str] = Body(None, embed=True)
):
    """
    Tiếp nhận hội thoại ban đầu từ Facebook/Zalo/Web,
    tự động bóc tách SĐT, phân loại nhu cầu, tính Lead Score và sinh tóm tắt 5s CareSoft.
    """
    lead = process_first_touch_chat(
        chat_text=chat_text,
        channel=channel,
        customer_name=customer_name
    )
    return {"status": "success", "lead": lead}


@app.get("/api/caresoft/leads")
async def api_get_caresoft_leads(
    score: Optional[str] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None
):
    """Lấy danh sách Lead CareSoft kèm các chỉ số KPI chuyển đổi."""
    leads = load_caresoft_leads()
    if score and score != "ALL":
        leads = [l for l in leads if l.get("lead_score") == score]
    if channel and channel != "ALL":
        leads = [l for l in leads if l.get("channel") == channel]
    if status and status != "ALL":
        leads = [l for l in leads if l.get("status") == status]
    metrics = get_caresoft_metrics()
    return {"status": "success", "leads": leads, "metrics": metrics}


@app.post("/api/caresoft/leads/{lead_id}/status")
async def api_update_caresoft_lead_status_endpoint(
    lead_id: str,
    status: str = Body(..., embed=True),
    agent_name: Optional[str] = Body(None, embed=True)
):
    """Cập nhật trạng thái xử lý Lead (NEW, ASSIGNED, CONVERTED, LOST)."""
    updated = update_caresoft_lead_status(lead_id, status, agent_name)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy Lead")
    return {"status": "success", "lead": updated}


@app.get("/api/caresoft/export")
async def api_export_caresoft_leads():
    """Xuất file CSV chuẩn UTF-8 có BOM tương thích 1-click import vào CareSoft Contact Center."""
    csv_content = export_caresoft_leads_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=caresoft_leads_export.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )


class CustomerCareChatRequest(BaseModel):
    customer_id: Optional[str] = None
    message: str
    session_id: Optional[str] = None


@app.post("/api/customer-care/chat")
async def api_customer_care_chat(request: CustomerCareChatRequest):
    """
    AI Customer Care Copilot:
    - Nhận diện khách hàng và đối chiếu hồ sơ
    - Kiểm soát nghiêm ngặt Incident Lockout (khóa bán thêm khi có khiếu nại)
    - Tuân thủ Luật Bảo vệ Dữ liệu Cá nhân 91/2025/QH15 (Opt-out)
    - Soạn thảo tin nhắn chăm sóc chu kỳ ngày 7, 25, 60
    """
    care_data = await api_customer_care()
    customers = care_data.get("sample_customers", [])

    cust = None
    if request.customer_id:
        for c in customers:
            if c["id"].lower() == request.customer_id.lower():
                cust = c
                break

    m_lower = request.message.lower().strip()
    if not cust:
        if any(k in m_lower for k in ["hà", "7119", "khiếu nại", "opt-out", "opt out", "tiêu hóa"]):
            cust = customers[2] if len(customers) > 2 else customers[0]
        elif any(k in m_lower for k in ["tuấn", "9042", "ngày 7", "ngày thứ 7", "d3"]):
            cust = customers[1] if len(customers) > 1 else customers[0]
        else:
            cust = customers[0] if customers else {}

    is_locked = "KHÓA" in cust.get("status", "") or cust.get("complaint_status", "") != "Bình thường"
    is_opt_out = "opt-out" in cust.get("consent_status", "").lower()

    # 1. RÀNG BUỘC INCIDENT LOCKOUT: Chặn đứng mọi hành vi Upsell / Bán thêm khi đang có khiếu nại
    upsell_keywords = ["upsell", "bán thêm", "tái mua", "mua thêm", "khuyến mãi", "combo", "chào hàng", "tiếp thị", "mời mua"]
    if is_locked and any(w in m_lower for w in upsell_keywords):
        return {
            "customer_id": cust.get("id"),
            "customer_name": cust.get("name"),
            "status": cust.get("status"),
            "is_locked": True,
            "is_opt_out": is_opt_out,
            "decision": "BLOCKED",
            "warning": "INCIDENT_LOCKOUT_VIOLATION",
            "answer": (
                f"[CẢNH BÁO INCIDENT LOCKOUT: KHÔNG ĐƯỢC PHÉP UPSELL / BÁN THÊM]\n\n"
                f"Khách hàng {cust.get('name')} ({cust.get('id')}) hiện đang trong trạng thái: {cust.get('status')} "
                f"(Ghi nhận sự cố: {cust.get('complaint_status')}).\n\n"
                f"Theo Quy chuẩn An toàn Dược DION và Nghị định 356/2025/NĐ-CP:\n"
                f"1. Tuyệt đối KHÔNG gợi ý mua thêm, bán chéo (upsell/cross-sell) hoặc gửi bất kỳ thông điệp thương mại nào.\n"
                f"2. Toàn bộ kịch bản tự động đã bị ngắt.\n"
                f"3. Bắt buộc: Chuyển giao hồ sơ cho Dược sĩ chuyên môn liên hệ trực tiếp thăm hỏi, ghi nhận triệu chứng phản ứng bất lợi (ADR) và xử lý dứt điểm khiếu nại trước khi mở lại quyền tư vấn."
            ),
            "suggested_action": "Chuyển Dược vụ xử lý sự cố"
        }

    # 1b. Giải thích lý do Incident Lockout
    if any(w in m_lower for w in ["tại sao khóa", "vì sao khóa", "lý do khóa", "giải thích khóa"]):
        return {
            "customer_id": cust.get("id"),
            "customer_name": cust.get("name"),
            "status": cust.get("status"),
            "is_locked": is_locked,
            "is_opt_out": is_opt_out,
            "decision": "EXPLANATION",
            "warning": "INCIDENT_LOCKOUT_POLICY",
            "answer": (
                f"GIẢI THÍCH LÝ DO KHÓA BÁN HÀNG (INCIDENT LOCKOUT):\n"
                f"Hệ thống kích hoạt cơ chế khóa bảo vệ tự động đối với khách hàng {cust.get('name')} ({cust.get('id')}) vì:\n"
                f"- Khiếu nại chất lượng/tác dụng phụ: {cust.get('complaint_status')} khi sử dụng {cust.get('sku_bought')} (ngày thứ {cust.get('day_in_cycle')}).\n"
                f"- Tránh phản cảm & rủi ro pháp lý: Tiếp tục tiếp thị bán hàng khi khách đang có trải nghiệm bất lợi vi phạm nghiêm trọng tiêu chuẩn chăm sóc y dược.\n"
                f"- Tình trạng chấp thuận: Khách hàng đồng thời ở trạng thái {cust.get('consent_status')}."
            ),
            "suggested_action": "Ghi nhận biên bản khiếu nại"
        }

    # 2. RÀNG BUỘC QUYỀN RIÊNG TƯ & OPT-OUT (Luật 91/2025/QH15)
    if any(w in m_lower for w in ["opt-out", "opt out", "từ chối nhận tin", "phản ứng thế nào", "gửi tin được không"]):
        return {
            "customer_id": cust.get("id"),
            "customer_name": cust.get("name"),
            "status": cust.get("status"),
            "is_locked": is_locked,
            "is_opt_out": True,
            "decision": "PRIVACY_ENFORCED",
            "warning": "OPT_OUT_COMPLIANCE",
            "answer": (
                "TUÂN THỦ LUẬT BẢO VỆ DỮ LIỆU CÁ NHÂN (Luật 91/2025/QH15 & Nghị định 356/2025/NĐ-CP):\n\n"
                "Khi khách hàng kích hoạt trạng thái TỪ CHỐI NHẬN TIN (OPT-OUT):\n"
                "1. Hệ thống tự động khóa vĩnh viễn quyền gửi tin tiếp thị tự động trên mọi kênh Zalo OA / SMS Brandname.\n"
                "2. Nghiêm cấm nhân viên sử dụng thông tin liên lạc của khách cho mục đích quảng cáo hoặc bán hàng.\n"
                "3. Hệ thống chỉ cho phép tiếp nhận thông tin một chiều khi khách hàng chủ động liên hệ yêu cầu trợ giúp sự cố y tế hoặc khiếu nại sản phẩm."
            ),
            "suggested_action": "Khóa kênh tiếp thị tự động"
        }

    # 3. KỊCH BẢN CHĂM SÓC NGÀY THỨ 25 (Nhắc bổ sung chu kỳ tiếp theo)
    if any(w in m_lower for w in ["soạn tin", "ngày 25", "ngày thứ 25", "tái mua", "nhắc tái mua", "tin nhắn chăm sóc"]):
        return {
            "customer_id": cust.get("id"),
            "customer_name": cust.get("name"),
            "status": cust.get("status"),
            "is_locked": is_locked,
            "is_opt_out": is_opt_out,
            "decision": "CARE_DRAFT",
            "warning": None,
            "answer": (
                f"KỊCH BẢN CHĂM SÓC KHÁCH HÀNG — NGÀY THỨ 25 (NHẮC BỔ SUNG CHU KỲ TIẾP THEO)\n"
                f"Khách hàng: {cust.get('name')} ({cust.get('id')}) | Sản phẩm: {cust.get('sku_bought')}\n\n"
                f"[Nội dung tin nhắn đề xuất gửi qua Zalo OA]:\n"
                f"\"DION xin chào chị {cust.get('name', '').split()[-1]}! Liệu trình Canxi Cal-Mom Plus của chị hiện đã bước sang ngày thứ 25 và sắp hoàn thành hộp đầu tiên.\n\n"
                f"Dược sĩ DION xin phép nhắn tin thăm hỏi: Trong tháng qua chị uống sau bữa sáng có thấy êm bụng và dễ chịu không ạ?\n\n"
                f"Để đảm bảo lượng Canxi sinh học từ tảo đỏ Lithothamnion và D3 K2 được cung cấp liên tục không bị ngắt quãng cho mẹ và bé, DION xin gửi chị mã đặc quyền tích lũy thành viên [CALMOM-REORDER] hỗ trợ 10% cho hộp chu kỳ tiếp theo. Chị nhắn lại để Dược sĩ hỗ trợ chuẩn bị đơn giao tận nơi nhé ạ! Chúc chị luôn khỏe mạnh!\""
            ),
            "suggested_action": "Sao chép kịch bản Zalo OA"
        }

    # 4. KỊCH BẢN CHĂM SÓC NGÀY THỨ 7 (Khảo sát cảm nhận sử dụng)
    if any(w in m_lower for w in ["ngày 7", "ngày thứ 7", "hỏi thăm", "cảm nhận"]):
        return {
            "customer_id": cust.get("id"),
            "customer_name": cust.get("name"),
            "status": cust.get("status"),
            "is_locked": is_locked,
            "is_opt_out": is_opt_out,
            "decision": "CARE_DRAFT",
            "warning": None,
            "answer": (
                f"KỊCH BẢN CHĂM SÓC KHÁCH HÀNG — NGÀY THỨ 7 (KHẢO SÁT CẢM NHẬN SỬ DỤNG)\n"
                f"Khách hàng: {cust.get('name')} ({cust.get('id')}) | Sản phẩm: {cust.get('sku_bought')}\n\n"
                f"[Nội dung tin nhắn đề xuất gửi qua SMS Brandname]:\n"
                f"\"DION xin chao anh {cust.get('name', '').split()[-1]}! Anh da su dung Vitamin D3 DION Drops duoc 1 tuan. Anh nho uong deu vao buoi sang sau an de tang cuong hap thu canxi toi da nhe a. Neu can them tu van huong dan, anh vui long phan hoi tai day. Chuc anh ngay moi tran day nang luong!\""
            ),
            "suggested_action": "Sao chép tin nhắn SMS"
        }

    # 5. TÓM TẮT THÔNG TIN KHÁCH HÀNG
    return {
        "customer_id": cust.get("id"),
        "customer_name": cust.get("name"),
        "status": cust.get("status"),
        "is_locked": is_locked,
        "is_opt_out": is_opt_out,
        "decision": "INFO",
        "warning": "INCIDENT_LOCKOUT_ACTIVE" if is_locked else None,
        "answer": (
            f"HỒ SƠ KHÁCH HÀNG DION: {cust.get('name')} (Mã: {cust.get('id')})\n"
            f"- Sản phẩm: {cust.get('sku_bought')} | Ngày mua: {cust.get('purchase_date')} (Ngày chu kỳ: {cust.get('day_in_cycle')}/30)\n"
            f"- Trạng thái chăm sóc: {cust.get('status')}\n"
            f"- Chấp thuận dữ liệu: {cust.get('consent_status')} (Luật 91/2025/QH15)\n"
            f"- Tình trạng khiếu nại: {cust.get('complaint_status')}\n\n"
            f"Gợi ý hành động: {cust.get('suggested_message')}"
        ),
        "suggested_action": "Tư vấn khách hàng"
    }


# ==========================================
# VISTAFA MULTI-CHANNEL CHAT & COMPETITOR COPILOT
# ==========================================

from modules.vistafa_chat_copilot import get_vistafa_chat_copilot

class VistafaChatCopilotRequest(BaseModel):
    customer_message: str
    product_id: str = "calcium_complex"
    channel: str = "facebook"
    customer_profile: Optional[Dict[str, Any]] = None
    situation_hint: Optional[str] = None


@app.get("/api/vistafa/channels")
async def api_vistafa_channels():
    copilot = get_vistafa_chat_copilot()
    return {
        "success": True,
        "channels": copilot.get_channels()
    }


@app.get("/api/vistafa/products")
async def api_vistafa_products():
    copilot = get_vistafa_chat_copilot()
    return {
        "success": True,
        "products": copilot.get_products()
    }


@app.get("/api/vistafa/playbook")
async def api_vistafa_playbook(
    q: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    situation: Optional[str] = Query(None),
    shortcut: Optional[str] = Query(None),
    limit: int = Query(50)
):
    copilot = get_vistafa_chat_copilot()
    entries = copilot.search_playbook(
        query=q,
        product_id=product_id,
        channel=channel,
        situation=situation,
        shortcut=shortcut,
        limit=limit
    )
    return {
        "success": True,
        "total": len(entries),
        "entries": entries
    }


@app.get("/api/vistafa/shortcuts")
async def api_vistafa_shortcuts(product_id: Optional[str] = Query(None)):
    copilot = get_vistafa_chat_copilot()
    shortcuts = copilot.get_shortcuts(product_id=product_id)
    return {
        "success": True,
        "total": len(shortcuts),
        "shortcuts": shortcuts
    }


@app.get("/api/vistafa/competitors")
async def api_vistafa_competitors(product_id: Optional[str] = Query(None)):
    copilot = get_vistafa_chat_copilot()
    matrix = copilot.get_competitor_matrix(product_id=product_id)
    return {
        "success": True,
        "total": len(matrix),
        "matrix": matrix
    }


@app.post("/api/vistafa/chat-copilot")
async def api_vistafa_chat_copilot(req: VistafaChatCopilotRequest):
    copilot = get_vistafa_chat_copilot()
    response = copilot.generate_response(
        customer_message=req.customer_message,
        product_id=req.product_id,
        channel=req.channel,
        customer_profile=req.customer_profile,
        situation_hint=req.situation_hint
    )
    return {
        "success": True,
        "data": response
    }


# ==========================================
# UNIFIED LIVE CONVERSATION & PHARMACIST HANDOFF
# ==========================================

class VistafaConversationMessageRequest(BaseModel):
    sender: str = "agent"  # "agent" or "customer"
    text: str

class VistafaEscalateRequest(BaseModel):
    reason: str = "Phát hiện yếu tố nguy cơ y tế / Red Flag"
    notes: Optional[str] = ""
    pharmacist_name: str = "DS. Lâm Sàng Trực Ban"

class VistafaConvertOrderRequest(BaseModel):
    sku: str
    quantity: int = 1
    delivery_address: str = ""
    total_price: str = ""


@app.get("/api/vistafa/conversations")
async def api_vistafa_get_conversations():
    copilot = get_vistafa_chat_copilot()
    cm = copilot.get_conversation_manager()
    return {
        "success": True,
        "conversations": cm.get_all()
    }


@app.get("/api/vistafa/conversations/{conv_id}")
async def api_vistafa_get_conversation(conv_id: str):
    copilot = get_vistafa_chat_copilot()
    cm = copilot.get_conversation_manager()
    conv = cm.get_by_id(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại")

    latest_customer_msg = ""
    for m in reversed(conv.get("messages", [])):
        if m.get("sender") == "customer":
            latest_customer_msg = m.get("text", "")
            break

    ai_recommendation = None
    if latest_customer_msg:
        ai_recommendation = copilot.generate_response(
            customer_message=latest_customer_msg,
            product_id=conv.get("product_id", "calcium_complex"),
            channel=conv.get("channel", "facebook"),
            customer_profile=conv.get("clinical_profile", {})
        )

    return {
        "success": True,
        "conversation": conv,
        "ai_recommendation": ai_recommendation
    }


@app.post("/api/vistafa/conversations/{conv_id}/messages")
async def api_vistafa_add_conversation_message(conv_id: str, req: VistafaConversationMessageRequest):
    copilot = get_vistafa_chat_copilot()
    cm = copilot.get_conversation_manager()
    msg = cm.add_message(conv_id, req.sender, req.text, copilot=copilot)
    if not msg:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại")

    conv = cm.get_by_id(conv_id)
    latest_customer_msg = ""
    for m in reversed(conv.get("messages", [])):
        if m.get("sender") == "customer":
            latest_customer_msg = m.get("text", "")
            break

    ai_recommendation = None
    if latest_customer_msg:
        ai_recommendation = copilot.generate_response(
            customer_message=latest_customer_msg,
            product_id=conv.get("product_id", "calcium_complex"),
            channel=conv.get("channel", "facebook"),
            customer_profile=conv.get("clinical_profile", {})
        )

    return {
        "success": True,
        "message": msg,
        "conversation": conv,
        "ai_recommendation": ai_recommendation
    }


@app.post("/api/vistafa/conversations/{conv_id}/escalate")
async def api_vistafa_escalate_conversation(conv_id: str, req: VistafaEscalateRequest):
    copilot = get_vistafa_chat_copilot()
    cm = copilot.get_conversation_manager()
    ticket = cm.escalate_pharmacist(conv_id, req.reason, req.notes, req.pharmacist_name)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại để chuyển Dược sĩ")
    return {
        "success": True,
        "ticket": ticket,
        "message": "Đã chuyển giao hồ sơ sang Dược sĩ lâm sàng phụ trách thành công"
    }


@app.post("/api/vistafa/conversations/{conv_id}/convert")
async def api_vistafa_convert_order(conv_id: str, req: VistafaConvertOrderRequest):
    copilot = get_vistafa_chat_copilot()
    cm = copilot.get_conversation_manager()
    order = cm.convert_order(conv_id, req.sku, req.quantity, req.delivery_address, req.total_price)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại để chốt đơn")
    return {
        "success": True,
        "order": order,
        "message": "Đã chốt đơn hàng và đồng bộ thành công vào CRM DION"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

