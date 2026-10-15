import streamlit as st
from views.tab_claims import render_tab_claims
from views.tab_leads import render_tab_leads
from views.tab_copilot import render_tab_copilot
from views.tab_content import render_tab_content

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="DION Healthcare AI — Enterprise Workspace",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# BỘ STYLING CAO CẤP: CHUẨN MỰC SAAS Y TẾ (MEDICAL ENTERPRISE)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 1. NỀN CHÍNH & MÀU CHỮ CHUẨN TUYỆT ĐỐI */
    .stApp {
        background-color: #f8fafc !important;
    }
    
    /* Ép tất cả chữ, đoạn văn, danh sách, nhãn phải luôn ĐEN ĐẬM SẮC NÉT */
    .stApp p, .stApp span, .stApp label, .stApp li, .stApp div, 
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {
        color: #0f172a !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #0f172a !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }

    /* 2. SIDEBAR DOANH NGHIỆP: NỀN XANH ĐEN SANG TRỌNG (DARK NAVY) */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid #334155 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #334155 !important;
    }

    /* 3. HERO BANNER XANH DƯƠNG HIỆN ĐẠI CÓ HIỆU ỨNG GLOW */
    .hero-container {
        background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 50%, #1e40af 100%);
        border-radius: 16px;
        padding: 26px 32px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(2, 132, 199, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.15);
        position: relative;
        overflow: hidden;
    }
    .hero-container h1 {
        color: #ffffff !important;
        font-size: 26px !important;
        margin: 0 !important;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-container p {
        color: #e0f2fe !important;
        font-size: 15px !important;
        margin: 8px 0 16px 0 !important;
    }
    .badge-pill {
        display: inline-flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.2);
        color: #ffffff !important;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 4px;
        border: 1px solid rgba(255, 255, 255, 0.35);
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease;
    }
    .badge-pill:hover {
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.3);
    }

    /* 4. THANH TABS HIỆN ĐẠI CÓ HIỆU ỨNG */
    div[data-baseweb="tab-list"] {
        background: #ffffff !important;
        padding: 8px !important;
        border-radius: 14px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03) !important;
        gap: 8px !important;
    }
    button[data-baseweb="tab"] {
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 10px 20px !important;
        color: #475569 !important;
        border: none !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    button[data-baseweb="tab"]:hover {
        background-color: #f1f5f9 !important;
        color: #0284c7 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3) !important;
    }

    /* 5. METRIC CARDS ĐỒNG BỘ */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border-radius: 14px !important;
        padding: 18px 20px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08) !important;
        border-color: #0284c7 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        font-weight: 700 !important;
        color: #64748b !important;
        text-transform: uppercase !important;
    }
    div[data-testid="stMetricValue"] {
        color: #0284c7 !important;
        font-size: 32px !important;
        font-weight: 800 !important;
    }

    /* 6. NÚT BẤM (BUTTONS) */
    .stButton button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 8px 18px !important;
        transition: all 0.2s ease !important;
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(2, 132, 199, 0.3) !important;
    }
    .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0369a1 0%, #075985 100%) !important;
        box-shadow: 0 6px 14px rgba(2, 132, 199, 0.45) !important;
        transform: translateY(-1px) !important;
    }

    /* 7. BẢNG DỮ LIỆU & DROPDOWN */
    div[data-testid="stDataFrame"] {
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid #cbd5e1 !important;
    }
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# SIDEBAR: Giao diện Navy Đẳng cấp
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 12px 0 18px 0;">
        <div style="font-size: 42px; margin-bottom: 6px;">💊</div>
        <h2 style="color: #38bdf8 !important; margin: 0; font-weight: 800; font-size: 24px; letter-spacing: -0.5px;">DION AI</h2>
        <p style="color: #94a3b8 !important; font-size: 13px; margin-top: 4px;">Enterprise Healthcare Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    <div style="background: rgba(255,255,255,0.06); padding: 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 16px;">
        <div style="font-weight: 700; color: #38bdf8 !important; font-size: 13px; margin-bottom: 8px;">📌 THÔNG TIN HỆ THỐNG</div>
        <div style="font-size: 12px; color: #cbd5e1 !important; line-height: 1.6;">
            • <b>Đơn vị:</b> Digital Innovation (DION)<br/>
            • <b>Thị trường:</b> Dược & TPBS Việt Nam<br/>
            • <b>Phiên bản:</b> Enterprise PoC v2.0
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); padding: 12px; border-radius: 10px;">
        <span style="color: #34d399 !important; font-weight: 700; font-size: 13px;">🟢 TRẠNG THÁI: ONLINE</span><br/>
        <span style="color: #a7f3d0 !important; font-size: 12px;">Đã nạp quy chuẩn NĐ 342/2025</span>
    </div>
    """, unsafe_allow_html=True)

# HERO BANNER XANH DƯƠNG DOANH NGHIỆP
st.markdown("""
<div class="hero-container">
    <h1>💊 DION HEALTHCARE AI — ENTERPRISE WORKSPACE</h1>
    <p>Giải pháp Trí tuệ Nhân tạo Nghiệp vụ Doanh nghiệp chuyên sâu cho Dược phẩm, Vitamin & Thực phẩm Bổ sung</p>
    <div>
        <span class="badge-pill">🛡️ Tuân thủ NĐ 342/2025/NĐ-CP</span>
        <span class="badge-pill">🎯 B2B Lead Scoring 4 Chiều</span>
        <span class="badge-pill">💬 Sales Copilot Trích Nguồn</span>
        <span class="badge-pill">✍️ AI Content & Compliance Guard</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 4 TABS CHUYÊN NGHIỆP
tab1, tab2, tab3, tab4 = st.tabs([
    "🏛️ 1. Quản lý Claims Sản phẩm",
    "🎯 2. Tìm kiếm Lead B2B",
    "💬 3. Trợ lý Sales Copilot",
    "✍️ 4. Sản xuất Content Marketing"
])

with tab1:
    render_tab_claims()

with tab2:
    render_tab_leads()

with tab3:
    render_tab_copilot()

with tab4:
    render_tab_content()
