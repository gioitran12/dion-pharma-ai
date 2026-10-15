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
    initial_sidebar_state="collapsed"
)

# THIẾT KẾ ĐỒNG BỘ: PHÔNG CHỮ RÕ RÀNG, KÍCH THƯỚC CHUẨN, BỐ CỤC MẠCH LẠC
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* 1. RESET PHÔNG CHỮ & KÍCH THƯỚC CHUẨN MỰC TOÀN BỘ TRANG */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #f8fafc !important;
        color: #0f172a !important;
        font-size: 15px !important;
        line-height: 1.6 !important;
    }

    /* Đảm bảo toàn bộ chữ cơ bản luôn sắc nét, không bị chữ to chữ bé */
    p, span, label, li {
        font-size: 15px !important;
        color: #1e293b !important;
        line-height: 1.6 !important;
    }

    /* Tiêu đề có cấp bậc rõ ràng, không nhảy kích thước lộn xộn */
    h1 { font-size: 24px !important; font-weight: 800 !important; color: #0f172a !important; margin: 0 0 12px 0 !important; }
    h2 { font-size: 20px !important; font-weight: 800 !important; color: #1d4ed8 !important; margin: 20px 0 10px 0 !important; }
    h3 { font-size: 17px !important; font-weight: 700 !important; color: #0f172a !important; margin: 16px 0 8px 0 !important; }
    h4 { font-size: 15px !important; font-weight: 700 !important; color: #1e293b !important; }

    /* 2. HERO BANNER XANH DƯƠNG CHUẨN - GỌN GÀNG, SANG TRỌNG */
    .hero-banner {
        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
        border-radius: 14px;
        padding: 24px 28px;
        color: #ffffff !important;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(29, 78, 216, 0.2);
    }
    .hero-banner h1 {
        color: #ffffff !important;
        font-size: 24px !important;
        font-weight: 800 !important;
        margin: 0 0 6px 0 !important;
    }
    .hero-banner p {
        color: #e0e7ff !important;
        font-size: 14px !important;
        margin: 0 0 14px 0 !important;
        line-height: 1.5 !important;
    }
    .hero-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    .hero-tag {
        background: rgba(255, 255, 255, 0.2);
        color: #ffffff !important;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px !important;
        font-weight: 600 !important;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    /* 3. THANH TABS ĐỒNG ĐỀU, DỄ ĐỌC */
    div[data-baseweb="tab-list"] {
        background: #ffffff !important;
        padding: 6px !important;
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        gap: 6px !important;
        margin-bottom: 20px !important;
    }
    button[data-baseweb="tab"] {
        font-size: 14px !important;
        font-weight: 700 !important;
        padding: 10px 18px !important;
        color: #475569 !important;
        border-radius: 8px !important;
        border: none !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: #1d4ed8 !important;
        color: #ffffff !important;
    }

    /* 4. METRIC SỐ LIỆU ĐỒNG BỘ */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #64748b !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 800 !important;
        color: #1d4ed8 !important;
    }

    /* 5. NÚT BẤM (BUTTONS) ĐỒNG NHẤT */
    .stButton button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 8px 18px !important;
    }
    .stButton button[kind="primary"] {
        background: #1d4ed8 !important;
        color: #ffffff !important;
        border: none !important;
    }
    .stButton button[kind="primary"]:hover {
        background: #1e40af !important;
    }

    /* 6. Ô NHẬP LIỆU GỌN GÀNG */
    .stTextInput input, .stSelectbox select, div[data-baseweb="select"] {
        font-size: 14px !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# HERO BANNER XANH DƯƠNG RÕ RÀNG, KHÔNG RỐI MẮT
st.markdown("""
<div class="hero-banner">
    <h1>💊 DION HEALTHCARE AI — ENTERPRISE WORKSPACE</h1>
    <p>Hệ thống AI Nghiệp vụ Chuyên sâu cho Doanh nghiệp Dược phẩm & Thực phẩm Bổ sung (TPBS)</p>
    <div class="hero-tags">
        <span class="hero-tag">🛡️ Tuân thủ NĐ 342/2025/NĐ-CP</span>
        <span class="hero-tag">🎯 Đánh giá Lead B2B 4 Chiều</span>
        <span class="hero-tag">💬 Sales Copilot Trích Nguồn Claims</span>
        <span class="hero-tag">✍️ Bộ Lọc Vi Phạm Quảng Cáo</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 4 TABS NGHIỆP VỤ RÕ RÀNG
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
