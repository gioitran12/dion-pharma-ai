import streamlit as st
import json
from modules.claims_hub import get_all_products, get_claims_summary, get_active_claims

def render_tab_claims():
    st.header("🏛️ Product & Claims Knowledge Vault")
    st.markdown("""
    *Nền tảng quản lý tri thức sản phẩm duy nhất (**Single Source of Truth**). Phân tách 3 vùng tri thức, 
    kiểm soát vòng đời Claims và tự động loại bỏ các công dụng hết hạn theo **Nghị định 342/2025/NĐ-CP**.*
    """)
    
    products = get_all_products()
    if not products:
        st.warning("Chưa có dữ liệu sản phẩm.")
        return
        
    # Dropdown chọn SKU
    sku_options = {p["sku"]: f"{p['sku']} - {p['name']}" for p in products}
    selected_sku = st.selectbox("Chọn Sản Phẩm để tra cứu:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
    
    summary = get_claims_summary(selected_sku)
    
    # 4 Thẻ chỉ số trực quan
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tổng số Claims", summary.get("total_claims", 0))
    col2.metric("Hợp lệ (Thương mại)", summary.get("active_commercial", 0), delta="Được phép dùng")
    col3.metric("Đã hết hạn", summary.get("expired", 0), delta="- Khóa tự động", delta_color="inverse")
    col4.metric("Chuyên môn nội bộ", summary.get("internal", 0), delta="Bảo mật")
    
    st.divider()
    
    # Chi tiết sản phẩm & Disclaimer
    prod = next((p for p in products if p["sku"] == selected_sku), None)
    if prod:
        st.subheader(f"Hồ sơ sản phẩm: {prod['name']}")
        st.markdown(f"- **Phân loại pháp lý:** `{prod['regulatory_class']}`")
        st.markdown(f"- **Ngành hàng:** {prod['category']}")
        st.markdown(f"- **Đối tượng sử dụng:** {', '.join(prod.get('target_users', []))}")
        st.info(f"⚠️ **Câu Disclaimer bắt buộc:** {prod.get('mandatory_disclaimer')}")
        
        # Bảng danh sách Claims
        st.subheader("Danh sách Claims chi tiết")
        for c in prod.get("claims", []):
            zone_color = "🟢" if c["zone"] == "COMMERCIAL_APPROVED" else "🟡"
            status_badge = "✅ HỢP LỆ" if c["status"] == "APPROVED" else "❌ ĐÃ HẾT HẠN"
            
            with st.expander(f"{zone_color} [{c['claim_id']}] {c['claim_text'][:80]}... — {status_badge}"):
                st.write(f"**Nội dung đầy đủ:** {c['claim_text']}")
                st.write(f"- **Vùng tri thức:** `{c['zone']}`")
                st.write(f"- **Trạng thái:** `{c['status']}` (Hiệu lực đến: `{c['effective_until']}`)")
                st.write(f"- **Người duyệt:** {c['approved_by']}")
                st.write(f"- **Nguồn chứng cứ:** {c['evidence_source']}")
