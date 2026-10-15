import streamlit as st
from views.tab_claims import render_tab_claims
from views.tab_leads import render_tab_leads
from views.tab_copilot import render_tab_copilot
from views.tab_content import render_tab_content

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="DION Healthcare AI — Enterprise Demo Workspace",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar thương hiệu DION
with st.sidebar:
    st.title("💊 DION AI ENTERPRISE")
    st.caption("Giải pháp AI Chuyên sâu ngành Dược & TPBS")
    st.divider()
    
    st.markdown("**Thông tin dự án:**")
    st.write("• **Đơn vị:** Digital Innovation (DION)")
    st.write("• **Phiên bản:** Demo PoC v1.0")
    st.write("• **Quy chuẩn:** NĐ 342/2025/NĐ-CP & Luật 91/2025/QH15")
    
    st.divider()
    st.info("💡 **Gợi ý Demo:** Chuyển qua lại giữa các Tab để xem trọn vẹn luồng từ Quản lý dữ liệu -> Tìm đối tác -> Tư vấn bán hàng -> Sản xuất nội dung.")

# Khởi tạo 4 Tab chính của Dashboard
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
