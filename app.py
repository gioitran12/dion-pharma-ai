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

# CSS An toàn - Đảm bảo chữ ĐEN ĐẬM RÕ RÀNG 100%, không bị ẩn hay mất chữ
st.markdown("""
<style>
    /* Chữ hiển thị đậm, rõ nét trên mọi trình duyệt */
    .stApp {
        background: #f1f5f9;
    }
    
    /* Đảm bảo toàn bộ chữ cơ bản có màu tối tương phản cao */
    p, span, label, h1, h2, h3, h4, h5, h6 {
        color: #0f172a !important;
    }
    
    /* Header Banner Xanh Dương Y Tế Cao Cấp */
    .dion-header {
        background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%);
        border-radius: 16px;
        padding: 24px 30px;
        color: #ffffff !important;
        margin-bottom: 24px;
        box-shadow: 0 10px 20px -5px rgba(2, 132, 199, 0.3);
    }
    .dion-header h1 {
        color: #ffffff !important;
        font-size: 26px !important;
        font-weight: 800 !important;
        margin: 0 !important;
    }
    .dion-header p {
        color: #e0f2fe !important;
        font-size: 15px !important;
        margin: 6px 0 14px 0 !important;
    }
    .dion-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.22);
        color: #ffffff !important;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin-right: 8px;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    /* Thẻ Card Trắng Tươi Sáng có Viền Xanh Nhẹ */
    .feature-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 20px;
        border: 1px solid #cbd5e1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 16px;
    }
    
    /* Tùy biến Tabs sáng rõ */
    button[data-baseweb="tab"] {
        font-size: 15px !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
        border-radius: 10px !important;
        color: #334155 !important;
    }
    
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
    }
    
    /* Khung Metric số liệu */
    [data-testid="stMetricValue"] {
        color: #0284c7 !important;
        font-size: 32px !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 700 !important;
    }
    
    /* Nút bấm nổi bật */
    .stButton button[kind="primary"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar gọn gàng, thanh lịch
with st.sidebar:
    st.markdown("""
    <div style="background: #ffffff; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0; text-align: center; margin-bottom: 20px;">
        <span style="font-size: 36px;">💊</span>
        <h3 style="color: #0284c7; margin: 4px 0 0 0; font-weight: 800;">DION AI</h3>
        <p style="color: #64748b; font-size: 12px; margin: 0;">Enterprise Healthcare Solutions</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📋 Thông tin hệ thống")
    st.markdown("""
    - **Đơn vị:** Digital Innovation (DION)
    - **Thị trường:** Dược phẩm & TPBS Việt Nam
    - **Khung pháp lý:**
      - *Nghị định 342/2025/NĐ-CP*
      - *Luật 91/2025/QH15*
    """)
    st.divider()
    st.success("🟢 Trạng thái hệ thống: **SẴN SÀNG**")

# Header Banner Xanh Dương Đậm Nổi Bật
st.markdown("""
<div class="dion-header">
    <h1>💊 DION HEALTHCARE AI — ENTERPRISE DEMO WORKSPACE</h1>
    <p>Hệ thống AI Nghiệp vụ Doanh nghiệp chuyên sâu cho Dược phẩm, Vitamin & Thực phẩm Chức năng</p>
    <div>
        <span class="dion-badge">🛡️ Kiểm soát Tuân thủ NĐ 342/2025</span>
        <span class="dion-badge">🎯 B2B Lead Scoring 4 Chiều</span>
        <span class="dion-badge">💬 Sales Copilot Trích Nguồn</span>
        <span class="dion-badge">✍️ Tự Động Gắn Disclaimer</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 4 Tab nghiệp vụ trực quan
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
