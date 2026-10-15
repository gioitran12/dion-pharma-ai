import streamlit as st
from modules.claims_hub import get_all_products, get_claims_summary, get_active_claims

def render_tab_claims():
    st.markdown("""
    <div style="background: #ffffff; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.05); margin-bottom: 24px;">
        <h3 style="color: #1d4ed8; font-weight: 800; margin: 0 0 8px 0; font-size: 20px; text-transform: uppercase;">
            🏛️ TRUNG TÂM QUẢN LÝ TRI THỨC & CLAIMS SẢN PHẨM
        </h3>
        <p style="color: #475569; font-size: 14px; margin: 0; line-height: 1.6;">
            Nền tảng kiểm soát tập trung (<b>Single Source of Truth</b>). Phân tách <b>3 vùng tri thức</b>, 
            kiểm soát vòng đời Claims và <b>tự động vô hiệu hóa các công dụng đã hết hạn</b> theo Nghị định 342/2025/NĐ-CP.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    products = get_all_products()
    if not products:
        st.warning("Chưa có dữ liệu sản phẩm.")
        return
        
    sku_options = {p["sku"]: f"📦 [{p['sku']}] {p['name']}" for p in products}
    selected_sku = st.selectbox("👉 Chọn Sản phẩm cần kiểm tra hồ sơ pháp lý:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
    
    summary = get_claims_summary(selected_sku)
    prod = next((p for p in products if p["sku"] == selected_sku), None)
    
    # 1. BỐ CỤC 3 VÙNG TRI THỨC TRỰC QUAN (CARDS XANH DƯƠNG / XANH LÁ / ĐỎ)
    z_col1, z_col2, z_col3 = st.columns(3)
    
    with z_col1:
        st.markdown(f"""
        <div style="background: #ffffff; border: 2px solid #10b981; border-radius: 16px; padding: 20px; box-shadow: 0 8px 16px rgba(16, 185, 129, 0.12);">
            <div style="color: #047857; font-weight: 800; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">🟢 VÙNG THƯƠNG MẠI ĐÃ DUYỆT</div>
            <div style="font-size: 36px; font-weight: 800; color: #065f46; margin: 6px 0;">{summary.get('active_commercial', 0)} <span style="font-size: 16px; font-weight: 600;">Claims</span></div>
            <div style="color: #475569; font-size: 13px; line-height: 1.5;">Được phép sử dụng cho Chatbot, Sales & Bài viết Marketing công khai.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with z_col2:
        st.markdown(f"""
        <div style="background: #ffffff; border: 2px solid #1d4ed8; border-radius: 16px; padding: 20px; box-shadow: 0 8px 16px rgba(29, 78, 216, 0.12);">
            <div style="color: #1d4ed8; font-weight: 800; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">🔵 VÙNG CHUYÊN MÔN NỘI BỘ</div>
            <div style="font-size: 36px; font-weight: 800; color: #1e40af; margin: 6px 0;">{summary.get('internal', 0)} <span style="font-size: 16px; font-weight: 600;">Claims</span></div>
            <div style="color: #475569; font-size: 13px; line-height: 1.5;">Cơ chế phân tử, tài liệu nhà máy — Giới hạn nội bộ, không đưa ra ngoài.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with z_col3:
        st.markdown(f"""
        <div style="background: #ffffff; border: 2px solid #ef4444; border-radius: 16px; padding: 20px; box-shadow: 0 8px 16px rgba(239, 68, 68, 0.12);">
            <div style="color: #b91c1c; font-weight: 800; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">🔴 CLAIMS ĐÃ HẾT HẠN</div>
            <div style="font-size: 36px; font-weight: 800; color: #991b1b; margin: 6px 0;">{summary.get('expired', 0)} <span style="font-size: 16px; font-weight: 600;">Claims</span></div>
            <div style="color: #475569; font-size: 13px; line-height: 1.5;">Tự động khóa — AI bị chặn tuyệt đối không cho phép sử dụng.</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    
    # 2. HỒ SƠ SẢN PHẨM & DISCLAIMER
    if prod:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); margin-bottom: 24px;">
            <div style="font-size: 18px; font-weight: 800; color: #1d4ed8; text-transform: uppercase; margin-bottom: 14px;">
                📋 HỒ SƠ SKU: {prod['name']}
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div>
                    <span style="color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase;">Mã sản phẩm (SKU)</span>
                    <div style="color: #0f172a; font-size: 16px; font-weight: 800;">{prod['sku']}</div>
                </div>
                <div>
                    <span style="color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase;">Phân loại pháp lý</span>
                    <div style="color: #1d4ed8; font-size: 16px; font-weight: 800;">{prod['regulatory_class']}</div>
                </div>
                <div>
                    <span style="color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase;">Ngành hàng</span>
                    <div style="color: #0f172a; font-size: 15px; font-weight: 600;">{prod['category']}</div>
                </div>
                <div>
                    <span style="color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase;">Đối tượng sử dụng</span>
                    <div style="color: #0f172a; font-size: 15px; font-weight: 600;">{', '.join(prod.get('target_users', []))}</div>
                </div>
            </div>
            
            <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid #e2e8f0;">
                <div style="background: #fffbeb; border: 1px solid #fde68a; border-left: 5px solid #f59e0b; padding: 14px 18px; border-radius: 10px;">
                    <div style="color: #92400e; font-weight: 800; font-size: 13px; margin-bottom: 4px;">⚠️ CÂU DISCLAIMER BẮT BUỘC THEO NGHỊ ĐỊNH 342/2025/NĐ-CP:</div>
                    <div style="color: #78350f; font-size: 15px; font-weight: 700;">"{prod.get('mandatory_disclaimer')}"</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. DANH SÁCH CHI TIẾT CLAIMS
        st.markdown("### 📑 DANH MỤC CLAIMS ĐANG KIỂM SOÁT")
        for c in prod.get("claims", []):
            if c["status"] == "APPROVED" and c["zone"] == "COMMERCIAL_APPROVED":
                border_color = "#10b981"
                status_badge = '<span style="background: #ecfdf5; color: #047857; border: 1px solid #10b981; padding: 5px 14px; border-radius: 9999px; font-size: 12px; font-weight: 800;">✅ HỢP LỆ — ĐƯỢC PHÉP DÙNG</span>'
            elif c["status"] == "EXPIRED":
                border_color = "#ef4444"
                status_badge = '<span style="background: #fef2f2; color: #b91c1c; border: 1px solid #ef4444; padding: 5px 14px; border-radius: 9999px; font-size: 12px; font-weight: 800;">❌ ĐÃ HẾT HẠN — KHÓA TỰ ĐỘNG</span>'
            else:
                border_color = "#1d4ed8"
                status_badge = '<span style="background: #eff6ff; color: #1d4ed8; border: 1px solid #1d4ed8; padding: 5px 14px; border-radius: 9999px; font-size: 12px; font-weight: 800;">🔒 CHUYÊN MÔN NỘI BỘ</span>'
                
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 6px solid {border_color}; border-radius: 14px; padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="color: #0f172a; font-size: 16px; font-weight: 800;">Mã Claim: <code style="background: #eff6ff; color: #1d4ed8; padding: 3px 10px; border-radius: 6px; font-size: 14px;">{c['claim_id']}</code></div>
                    {status_badge}
                </div>
                <div style="color: #0f172a; font-size: 16px; font-weight: 700; line-height: 1.6; margin: 12px 0;">
                    "{c['claim_text']}"
                </div>
                <div style="color: #64748b; font-size: 13px; font-weight: 500; padding-top: 10px; border-top: 1px dashed #e2e8f0;">
                    👤 <b>Người duyệt:</b> <span style="color: #0f172a; font-weight: 600;">{c['approved_by']}</span> &nbsp;|&nbsp; 
                    📅 <b>Hiệu lực đến:</b> <span style="color: #0f172a; font-weight: 600;">{c['effective_until']}</span> &nbsp;|&nbsp; 
                    📚 <b>Nguồn chứng cứ:</b> <span style="color: #0f172a; font-weight: 600;">{c['evidence_source']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
