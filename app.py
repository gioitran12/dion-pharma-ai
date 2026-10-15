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
    initial_sidebar_state="collapsed"  # Mặc định ẩn sidebar để có không gian web rộng rãi như ảnh mẫu
)

# STYLING THEO PHONG CÁCH VIBRANT SAAS ROYAL BLUE (GIỐNG THUEDO.NET)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    
    /* 1. TOP NAVBAR TRẮNG TINH KHÔI GIỐNG THUEDO.NET */
    .thuedo-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #ffffff;
        padding: 12px 28px;
        border-bottom: 1px solid #e2e8f0;
        margin-top: -50px;
        margin-bottom: 24px;
        position: sticky;
        top: 0;
        z-index: 999;
    }
    .thuedo-logo {
        display: flex;
        align-items: center;
        gap: 12px;
        text-decoration: none;
    }
    .thuedo-logo-icon {
        background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%);
        color: white;
        font-size: 20px;
        font-weight: 800;
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(29, 78, 216, 0.3);
    }
    .thuedo-logo-text {
        font-size: 20px;
        font-weight: 800;
        color: #1d4ed8 !important;
        margin: 0;
        line-height: 1.1;
    }
    .thuedo-logo-sub {
        font-size: 11px;
        color: #64748b;
        margin: 0;
    }
    .thuedo-nav-links {
        display: flex;
        gap: 32px;
        font-weight: 700;
        font-size: 14px;
    }
    .thuedo-nav-links a {
        color: #1e293b;
        text-decoration: none;
        transition: color 0.2s ease;
    }
    .thuedo-nav-links a:hover, .thuedo-nav-links a.active {
        color: #1d4ed8;
    }
    .thuedo-login-btn {
        background: #1d4ed8;
        color: #ffffff !important;
        padding: 9px 26px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 14px;
        text-decoration: none;
        box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3);
        transition: all 0.2s ease;
    }
    .thuedo-login-btn:hover {
        background: #1e40af;
        transform: translateY(-1px);
    }

    /* 2. HERO BANNER XANH DƯƠNG RỰC RỠ ĐẬM CHẤT THUEDO.NET */
    .thuedo-hero {
        background: radial-gradient(circle at 80% 50%, #3b82f6 0%, #1d4ed8 60%, #1e40af 100%);
        border-radius: 20px;
        padding: 44px 48px;
        color: #ffffff;
        margin-bottom: 36px;
        box-shadow: 0 15px 30px -10px rgba(29, 78, 216, 0.45);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 30px;
    }
    .thuedo-hero-left {
        max-width: 62%;
    }
    .thuedo-hero-title {
        font-size: 32px;
        font-weight: 800;
        line-height: 1.25;
        letter-spacing: -0.5px;
        color: #ffffff !important;
        margin-bottom: 16px;
        text-transform: uppercase;
    }
    .thuedo-hero-desc {
        font-size: 15px;
        line-height: 1.65;
        color: #e0e7ff !important;
        margin-bottom: 26px;
        font-weight: 400;
    }
    .thuedo-cta-btn {
        display: inline-block;
        background: #ffffff;
        color: #1d4ed8 !important;
        font-weight: 800;
        font-size: 15px;
        padding: 12px 30px;
        border-radius: 9999px;
        text-decoration: none;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
        transition: all 0.2s ease;
    }
    .thuedo-cta-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 20px rgba(0, 0, 0, 0.2);
    }
    .thuedo-hero-right {
        max-width: 35%;
        text-align: center;
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }

    /* 3. SECTION HEADING CHUẨN XANH DƯƠNG HOA */
    .thuedo-section-header {
        text-align: center;
        margin-bottom: 28px;
    }
    .thuedo-section-title {
        font-size: 26px;
        font-weight: 800;
        color: #1d4ed8 !important;
        text-transform: uppercase;
        letter-spacing: -0.5px;
        margin-bottom: 8px;
    }
    .thuedo-section-subtitle {
        font-size: 15px;
        color: #475569;
        max-width: 700px;
        margin: 0 auto;
        line-height: 1.5;
    }

    /* 4. TABS PHẲNG HIỆN ĐẠI THEO PHONG CÁCH NAVBAR */
    div[data-baseweb="tab-list"] {
        justify-content: center !important;
        background: #ffffff !important;
        border-bottom: 2px solid #e2e8f0 !important;
        padding-bottom: 0px !important;
        gap: 24px !important;
        margin-bottom: 28px !important;
    }
    button[data-baseweb="tab"] {
        font-size: 15px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        color: #64748b !important;
        border: none !important;
        padding: 12px 18px !important;
        background: transparent !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0 !important;
        transition: all 0.2s ease !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #1d4ed8 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #1d4ed8 !important;
        border-bottom: 3px solid #1d4ed8 !important;
        background: transparent !important;
    }

    /* 5. CÁC NÚT BẤM (BUTTONS) VIÊN THUỐC BO TRÒN */
    .stButton button {
        border-radius: 9999px !important;
        font-weight: 700 !important;
        padding: 10px 24px !important;
        font-size: 14px !important;
        transition: all 0.2s ease !important;
    }
    .stButton button[kind="primary"] {
        background: #1d4ed8 !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(29, 78, 216, 0.35) !important;
    }
    .stButton button[kind="primary"]:hover {
        background: #1e40af !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(29, 78, 216, 0.45) !important;
    }
    
    /* 6. THẺ CARD TRẮNG TINH TẾ CÓ BÓNG ĐỔ MỊN */
    .white-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 1. TOP NAVBAR SANG TRỌNG GIỐNG THUEDO.NET
st.markdown("""
<div class="thuedo-navbar">
    <div class="thuedo-logo">
        <div class="thuedo-logo-icon">💊</div>
        <div>
            <div class="thuedo-logo-text">DION AI</div>
            <div class="thuedo-logo-sub">https://dion.healthcare.ai</div>
        </div>
    </div>
    <div class="thuedo-nav-links">
        <a href="#" class="active">TRANG CHỦ</a>
        <a href="#">TÍNH NĂNG</a>
        <a href="#">KIẾN TRÚC AI</a>
        <a href="#">PHÁP LÝ NĐ 342</a>
        <a href="#">LIÊN HỆ</a>
    </div>
    <a href="#demo-workspace" class="thuedo-login-btn">Khám phá Demo</a>
</div>
""", unsafe_allow_html=True)

# 2. HERO BANNER XANH DƯƠNG RỰC RỠ VỚI 3D PODIUM
st.markdown("""
<div class="thuedo-hero">
    <div class="thuedo-hero-left">
        <div class="thuedo-hero-title">
            HỆ THỐNG ENTERPRISE AI DƯỢC PHẨM & TPBS SỐ 1 VIỆT NAM
        </div>
        <div class="thuedo-hero-desc">
            DION Healthcare AI là nền tảng trí tuệ nhân tạo chuyên biệt cho ngành dược phẩm, thực phẩm bổ sung và chăm sóc sức khỏe. 
            Được xây dựng phù hợp tối đa với nghiệp vụ thực tế, tập trung giải quyết các bài toán trọng yếu: tìm kiếm đối tác B2B (nhà thuốc, chuỗi mẹ & bé), 
            quản lý vòng đời Claims pháp lý, trợ lý tư vấn sản phẩm RAG và tự động hóa truyền thông tuân thủ Nghị định 342/2025/NĐ-CP.
        </div>
        <a href="#demo-section" class="thuedo-cta-btn">TRẢI NGHIỆM TÍNH NĂNG NGAY</a>
    </div>
    <div class="thuedo-hero-right">
        <div style="font-size: 48px; margin-bottom: 10px;">🛡️ 🔬 💊</div>
        <div style="font-weight: 800; font-size: 17px; color: #ffffff; margin-bottom: 6px;">CHUẨN HÓA DƯỢC VỤ</div>
        <div style="font-size: 13px; color: #dbeafe; line-height: 1.5;">
            • 100% Căn cứ pháp lý & Nguồn trích dẫn<br/>
            • 4 Chiều Đánh giá Lead Nhà thuốc B2B<br/>
            • Tự động chặn từ cấm & Gắn disclaimer
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 3. SECTION HEADING THEO PHONG CÁCH THUEDO.NET
st.markdown("""
<div id="demo-section" class="thuedo-section-header">
    <div class="thuedo-section-title">GIẢI PHÁP AI CHUYÊN SÂU, ĐƠN GIẢN VÀ HIỆU QUẢ</div>
    <div class="thuedo-section-subtitle">
        Được thiết kế 100% cho ngành dược phẩm & thực phẩm bảo vệ sức khỏe, giúp vận hành đúng quy trình và nâng cao doanh số phân phối.
    </div>
</div>
""", unsafe_allow_html=True)

# 4. TABS NGHIỆP VỤ HIỆN ĐẠI
tab1, tab2, tab3, tab4 = st.tabs([
    "🏛️ QUẢN LÝ CLAIMS SẢN PHẨM",
    "🎯 TÌM KIẾM LEAD B2B",
    "💬 TRỢ LÝ SALES COPILOT",
    "✍️ SẢN XUẤT CONTENT MARKETING"
])

with tab1:
    render_tab_claims()

with tab2:
    render_tab_leads()

with tab3:
    render_tab_copilot()

with tab4:
    render_tab_content()
