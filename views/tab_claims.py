import streamlit as st
from modules.claims_hub import get_all_products, get_claims_summary

def render_tab_claims():
    st.markdown("## 🏛️ Quản Lý Tri Thức & Claims Sản Phẩm")
    st.markdown("Kiểm soát tập trung nguồn dữ liệu đã phê duyệt. Phân định **3 vùng tri thức** và tự động khóa các Claims đã hết hạn theo **Nghị định 342/2025/NĐ-CP**.")
    
    products = get_all_products()
    if not products:
        st.warning("Chưa có dữ liệu sản phẩm.")
        return
        
    sku_options = {p["sku"]: f"[{p['sku']}] {p['name']}" for p in products}
    selected_sku = st.selectbox("Chọn Sản phẩm để tra cứu hồ sơ:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
    
    summary = get_claims_summary(selected_sku)
    prod = next((p for p in products if p["sku"] == selected_sku), None)
    
    # 1. THỐNG KÊ 3 VÙNG TRI THỨC BẰNG NATIVE METRICS (ĐỒNG BỘ KÍCH THƯỚC, KHÔNG BỊ LỘN XỘN)
    st.markdown("### 📊 Trạng Thái Claims & Vùng Tri Thức")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng số Claims", summary.get("total_claims", 0))
    m2.metric("🟢 Thương mại hợp lệ", summary.get("active_commercial", 0), delta="Được phép dùng")
    m3.metric("🔴 Đã hết hạn", summary.get("expired", 0), delta="- Đã khóa", delta_color="inverse")
    m4.metric("🔵 Chuyên môn nội bộ", summary.get("internal", 0), delta="Bảo mật")
    
    st.divider()
    
    # 2. HỒ SƠ CHI TIẾT SẢN PHẨM & CẢNH BÁO DISCLAIMER
    if prod:
        st.markdown(f"### 📋 Hồ Sơ Sản Phẩm: {prod['name']}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"• **Mã sản phẩm (SKU):** `{prod['sku']}`")
            st.markdown(f"• **Phân loại pháp lý:** **{prod['regulatory_class']}**")
        with c2:
            st.markdown(f"• **Ngành hàng:** {prod['category']}")
            st.markdown(f"• **Đối tượng sử dụng:** {', '.join(prod.get('target_users', []))}")
            
        st.warning(f"⚠️ **CÂU DISCLAIMER BẮT BUỘC (Nghị định 342/2025/NĐ-CP):**\n\n\"{prod.get('mandatory_disclaimer')}\"")
        
        st.divider()
        
        # 3. DANH SÁCH CHI TIẾT CÁC CLAIMS
        st.markdown("### 📑 Danh Mục Claims Chi Tiết")
        
        for c in prod.get("claims", []):
            if c["status"] == "APPROVED" and c["zone"] == "COMMERCIAL_APPROVED":
                status_label = "🟢 [HỢP LỆ - THƯƠNG MẠI]"
            elif c["status"] == "EXPIRED":
                status_label = "🔴 [ĐÃ HẾT HẠN - KHÓA]"
            else:
                status_label = "🔵 [CHUYÊN MÔN NỘI BỘ]"
                
            with st.expander(f"{status_label} Mã: {c['claim_id']} — {c['claim_text'][:80]}...", expanded=(c["status"] == "APPROVED")):
                st.markdown(f"**Nội dung công dụng:**")
                st.info(c["claim_text"])
                
                col_a, col_b, col_c = st.columns(3)
                col_a.markdown(f"**Người duyệt:** {c['approved_by']}")
                col_b.markdown(f"**Hiệu lực đến:** `{c['effective_until']}`")
                col_c.markdown(f"**Vùng dữ liệu:** `{c['zone']}`")
                
                st.caption(f"📚 **Nguồn chứng cứ:** {c['evidence_source']}")
