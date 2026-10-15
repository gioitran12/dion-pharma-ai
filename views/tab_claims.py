import streamlit as st
from modules.claims_hub import get_all_products, get_claims_summary, get_active_claims

def render_tab_claims():
    st.markdown("## 🏛️ Trung Tâm Quản Lý Tri Thức & Claims Sản Phẩm")
    st.markdown("""
    *Nền tảng kiểm soát tập trung (**Single Source of Truth**). Phân tách **3 vùng tri thức**, 
    kiểm soát vòng đời Claims và **tự động vô hiệu hóa các công dụng đã hết hạn** theo Nghị định 342/2025/NĐ-CP.*
    """)
    
    products = get_all_products()
    if not products:
        st.warning("Chưa có dữ liệu sản phẩm.")
        return
        
    # Dropdown chọn SKU trực quan
    sku_options = {p["sku"]: f"📦 [{p['sku']}] {p['name']}" for p in products}
    selected_sku = st.selectbox("👉 Chọn Sản phẩm cần kiểm tra hồ sơ pháp lý:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
    
    summary = get_claims_summary(selected_sku)
    prod = next((p for p in products if p["sku"] == selected_sku), None)
    
    # 1. BỐ CỤC 3 VÙNG TRI THỨC TRỰC QUAN (3-ZONE KNOWLEDGE CARDS)
    st.markdown("### 🌐 Phân Vùng Quyền Hạn Dữ Liệu (3 Tri thức)")
    z_col1, z_col2, z_col3 = st.columns(3)
    
    with z_col1:
        st.markdown(f"""
        <div style="background: #ecfdf5; border: 2px solid #10b981; border-radius: 12px; padding: 16px;">
            <div style="color: #047857; font-weight: 800; font-size: 16px; margin-bottom: 4px;">🟢 VÙNG THƯƠNG MẠI ĐÃ DUYỆT</div>
            <div style="font-size: 28px; font-weight: 800; color: #065f46;">{summary.get('active_commercial', 0)} Claims</div>
            <div style="color: #047857; font-size: 13px; margin-top: 6px;">Được phép sử dụng cho Chatbot, Sales & Bài viết Marketing công khai.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with z_col2:
        st.markdown(f"""
        <div style="background: #eff6ff; border: 2px solid #3b82f6; border-radius: 12px; padding: 16px;">
            <div style="color: #1d4ed8; font-weight: 800; font-size: 16px; margin-bottom: 4px;">🔵 VÙNG CHUYÊN MÔN NỘI BỘ</div>
            <div style="font-size: 28px; font-weight: 800; color: #1e40af;">{summary.get('internal', 0)} Claims</div>
            <div style="color: #1d4ed8; font-size: 13px; margin-top: 6px;">Cơ chế phân tử, tài liệu nhà máy — Giới hạn nội bộ, không đưa ra ngoài.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with z_col3:
        st.markdown(f"""
        <div style="background: #fef2f2; border: 2px solid #ef4444; border-radius: 12px; padding: 16px;">
            <div style="color: #b91c1c; font-weight: 800; font-size: 16px; margin-bottom: 4px;">🔴 CLAIMS ĐÃ HẾT HẠN</div>
            <div style="font-size: 28px; font-weight: 800; color: #991b1b;">{summary.get('expired', 0)} Claims</div>
            <div style="color: #b91c1c; font-size: 13px; margin-top: 6px;">Tự động khóa — AI bị chặn tuyệt đối không cho phép sử dụng.</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    
    # 2. HỒ SƠ SẢN PHẨM & CẢNH BÁO PHÁP LÝ BẮT BUỘC
    if prod:
        st.markdown(f"### 📋 Chi tiết Hồ Sơ SKU: {prod['name']}")
        
        info_col1, info_col2 = st.columns([1, 1])
        with info_col1:
            st.markdown(f"""
            - **Mã sản phẩm (SKU):** `{prod['sku']}`
            - **Phân loại pháp lý:** **{prod['regulatory_class']}**
            - **Danh mục:** {prod['category']}
            """)
        with info_col2:
            st.markdown(f"""
            - **Nhóm đối tượng sử dụng:** {', '.join(prod.get('target_users', []))}
            - **Trạng thái lưu hành:** ✅ Đạt chuẩn công bố Cục ATTP
            """)
            
        st.markdown(f"""
        <div style="background: #fffbeb; border-left: 5px solid #f59e0b; padding: 14px; border-radius: 8px; margin: 12px 0;">
            <strong style="color: #92400e;">⚠️ CÂU DISCLAIMER BẮT BUỘC PHẢI ĐÍNH KÈM (Theo NĐ 342/2025):</strong><br/>
            <span style="color: #78350f; font-size: 14px;">"{prod.get('mandatory_disclaimer')}"</span>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. DANH SÁCH CHI TIẾT CLAIMS
        st.markdown("### 📑 Danh Mục Claims Đang Kiểm Soát")
        for c in prod.get("claims", []):
            if c["status"] == "APPROVED" and c["zone"] == "COMMERCIAL_APPROVED":
                border_color = "#10b981"
                status_html = '<span style="background: #10b981; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">HỢP LỆ — ĐƯỢC PHÉP DÙNG</span>'
            elif c["status"] == "EXPIRED":
                border_color = "#ef4444"
                status_html = '<span style="background: #ef4444; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">ĐÃ HẾT HẠN — KHÓA TỰ ĐỘNG</span>'
            else:
                border_color = "#3b82f6"
                status_html = '<span style="background: #3b82f6; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">CHUYÊN MÔN NỘI BỘ</span>'
                
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 6px solid {border_color}; border-radius: 10px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="color: #0f172a; font-size: 16px;">Mã Claim: <code>{c['claim_id']}</code></strong>
                    {status_html}
                </div>
                <div style="color: #1e293b; font-size: 15px; font-weight: 600; margin-bottom: 8px;">
                    "{c['claim_text']}"
                </div>
                <div style="color: #64748b; font-size: 13px;">
                    👤 <b>Người duyệt:</b> {c['approved_by']} &nbsp;|&nbsp; 
                    📅 <b>Hiệu lực đến:</b> {c['effective_until']} &nbsp;|&nbsp; 
                    📚 <b>Nguồn chứng cứ:</b> {c['evidence_source']}
                </div>
            </div>
            """, unsafe_allow_html=True)
