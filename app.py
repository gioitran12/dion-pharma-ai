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

# Tùy chỉnh CSS cao cấp: Giao diện Xanh Dương Y Tế (Medical Blue) Sáng, Tươi, Hiện đại
st.markdown("""
<style>
    /* Nhập font liên kết */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Nền tổng thể sáng và sạch */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }
    
    /* Header Banner Xanh Dương Y Tế Cao Cấp */
    .hero-banner {
        background: linear-gradient(135deg, #0284c7 0%, #1e40af 100%);
        padding: 24px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(2, 132, 199, 0.25);
    }
    .hero-title {
        font-size: 28px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-subtitle {
        font-size: 15px;
        opacity: 0.92;
        margin-top: 6px;
        font-weight: 400;
    }
    .hero-tags {
        display: flex;
        gap: 10px;
        margin-top: 14px;
    }
    .hero-tag {
        background: rgba(255, 255, 255, 0.2);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        backdrop-filter: blur(4px);
    }

    /* Tùy chỉnh Tab bar hiện đại */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: #ffffff;
        padding: 8px 12px;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        font-weight: 600;
        font-size: 14px;
        border-radius: 10px;
        color: #475569;
        padding: 0 20px;
        border: none;
        transition: all 0.2s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: #0284c7 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);
    }
    
    /* Thẻ thẻ metric (Số liệu) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        border-left: 4px solid #0284c7;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-size: 28px !important;
        font-weight: 800 !important;
    }

    /* Khung Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Nút bấm (Buttons) */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        border: 1px solid #cbd5e1;
        transition: all 0.2s ease;
    }
    
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 10px rgba(2, 132, 199, 0.3);
    }
    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
        box-shadow: 0 6px 14px rgba(2, 132, 199, 0.4);
    }
    
    /* Khung nhập liệu Input / Select */
    .stTextInput>div>div>input, .stSelectbox>div>div {
        border-radius: 10px;
        border: 1px solid #cbd5e1;
        background-color: #ffffff;
        color: #0f172a;
    }
    
    /* Khung thông báo Info / Warning / Error */
    .stAlert {
        border-radius: 12px;
        border: none;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }
    
</style>
""", unsafe_allow_html=True)

# Sidebar thương hiệu DION với giao diện sáng thanh lịch
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 10px 0 20px 0;">
        <div style="font-size: 40px; margin-bottom: 8px;">💊</div>
        <h2 style="color: #0284c7; margin: 0; font-weight: 800; font-size: 22px;">DION AI</h2>
        <p style="color: #64748b; font-size: 13px; margin-top: 4px;">Enterprise Healthcare Intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("**📌 THÔNG TIN DỰ ÁN**")
    st.markdown("""
    - **Đơn vị tư vấn:** Digital Innovation (DION)
    - **Phiên bản:** Demo PoC v1.2 (Sáng & Tối ưu)
    - **Quy chuẩn tuân thủ:**
      - *Nghị định 342/2025/NĐ-CP (Quảng cáo Y tế)*
      - *Luật 91/2025/QH15 (Bảo vệ dữ liệu)*
    """)
    
    st.divider()
    st.info("💡 **Gợi ý Demo:** Lần lượt trải nghiệm 4 Tab để kiểm chứng giải pháp tích hợp từ **Quản lý dữ liệu** $\rightarrow$ **Tìm đối tác B2B** $\rightarrow$ **Tư vấn bán hàng** $\rightarrow$ **Truyền thông tuân thủ**.")

# Hero Banner Xanh Dương Nổi Bật Ở Đầu Trang
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">
        <span>💊 DION HEALTHCARE AI WORKSPACE</span>
    </div>
    <div class="hero-subtitle">
        Nền tảng Trí tuệ Nhân tạo Doanh nghiệp chuyên sâu cho Dược phẩm, Vitamin & Thực phẩm Bổ sung
    </div>
    <div class="hero-tags">
        <span class="hero-tag">🛡️ Tuân thủ NĐ 342/2025</span>
        <span class="hero-tag">🎯 Lead B2B Scoring</span>
        <span class="hero-tag">💬 RAG Claims Copilot</span>
        <span class="hero-tag">✍️ Compliance Engine</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Khởi tạo 4 Tab chính với icon nổi bật
tab1, tab2, tab3, tab4 = st.tabs([
    "🏛️ Quản lý Claims Sản phẩm",
    "🎯 Tìm kiếm Lead B2B",
    "💬 Trợ lý Sales Copilot",
    "✍️ Sản xuất Content Marketing"
])

with tab1:
    render_tab_claims()

with tab2:
    render_tab_leads()

with tab3:
    render_tab_copilot()

with tab4:
    render_tab_content()
