import streamlit as st
from modules.claims_hub import get_all_products, get_claims_summary, get_active_claims

def render_tab_claims():
    st.markdown("## 🏛️ Trung Tâm Quản Lý Tri Thức & Claims Sản Phẩm")
    st.markdown("""
    *Nền tảng kiểm soát tri thức tập trung (**Single Source of Truth**). Phân tách **3 vùng tri thức**, 
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
    
    # 1. BỐ CỤC 3 VÙNG TRI THỨC TRỰC QUAN (3-ZONE CARDS CÓ HIỆU ỨNG ĐẸP)
    st.markdown("### 🌐 Phân Vùng Quyền Hạn Dữ Liệu (3 Vùng Tri Thức)")
    z_col1, z_col2, z_col3 = st.columns(3)
    
    with z_col1:
        st.markdown(f"""
        <div style="background: #ffffff; border: 2px solid #10b981; border-radius: 14px; padding: 18px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.12); transition: all 0.2s ease;">
            <div style="color: #047857; font-weight: 800; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">🟢 VÙNG THƯƠNG MẠI ĐÃ DUYỆT</div>
            <div style="font-size: 32px; font-weight: 800; color: #065f46; margin: 4px 0;">{summary.get('active_commercial', 0)} <span style="font-size: 16px; font-weight: 600;">Claims</span></div>
            <div style="color: #334155; font-size: 13px; line-height: 1.5; margin-top: 6px;">Được phép sử dụng cho Chatbot, Sales & Bài viết Marketing công khai.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with z_col2:
        st.markdown(f"""
        <div style="background: #ffffff; border: 2px solid #0284c7; border-radius: 14px; padding: 18px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.12); transition: all 0.2s ease;">
            <div style="color: #0369a1; font-weight: 800; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">🔵 VÙNG CHUYÊN MÔN NỘI BỘ</div>
            <div style="font-size: 32px; font-weight: 800; color: #0c4a6e; margin: 4px 0;">{summary.get('internal', 0)} <span style="font-size: 16px; font-weight: 600;">Claims</span></div>
            <div style="color: #334155; font-size: 13px; line-height: 1.5; margin-top: 6px;">Cơ chế phân tử, tài liệu nhà máy — Giới hạn nội bộ, không đưa ra ngoài.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with z_col3:
        st.markdown(f"""
        <div style="background: #ffffff; border: 2px solid #ef4444; border-radius: 14px; padding: 18px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.12); transition: all 0.2s ease;">
            <div style="color: #b91c1c; font-weight: 800; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">🔴 CLAIMS ĐÃ HẾT HẠN</div>
            <div style="font-size: 32px; font-weight: 800; color: #991b1b; margin: 4px 0;">{summary.get('expired', 0)} <span style="font-size: 16px; font-weight: 600;">Claims</span></div>
            <div style="color: #334155; font-size: 13px; line-height: 1.5; margin-top: 6px;">Tự động khóa — AI bị chặn tuyệt đối không cho phép sử dụng.</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    
    # 2. HỒ SƠ SẢN PHẨM & DISCLAIMER RÕ RÀNG
    if prod:
        st.markdown(f"### 📋 Chi tiết Hồ Sơ SKU: {prod['name']}")
        
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); margin-bottom: 16px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div>
                    <div style="color: #64748b; font-size: 13px; font-weight: 700; text-transform: uppercase;">Mã sản phẩm (SKU)</div>
                    <div style="color: #0f172a; font-size: 16px; font-weight: 800; margin-top: 2px;">{prod['sku']}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 13px; font-weight: 700; text-transform: uppercase;">Phân loại pháp lý</div>
                    <div style="color: #0284c7; font-size: 16px; font-weight: 800; margin-top: 2px;">{prod['regulatory_class']}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 13px; font-weight: 700; text-transform: uppercase;">Ngành hàng</div>
                    <div style="color: #0f172a; font-size: 15px; font-weight: 600; margin-top: 2px;">{prod['category']}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 13px; font-weight: 700; text-transform: uppercase;">Đối tượng sử dụng</div>
                    <div style="color: #0f172a; font-size: 15px; font-weight: 600; margin-top: 2px;">{', '.join(prod.get('target_users', []))}</div>
                </div>
            </div>
            
            <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid #e2e8f0;">
                <div style="background: #fffbeb; border: 1px solid #fde68a; border-left: 5px solid #f59e0b; padding: 12px 16px; border-radius: 8px;">
                    <div style="color: #92400e; font-weight: 800; font-size: 13px; margin-bottom: 4px;">⚠️ CÂU DISCLAIMER BẮT BUỘC THEO NGHỊ ĐỊNH 342/2025/NĐ-CP:</div>
                    <div style="color: #78350f; font-size: 14px; font-weight: 600;">"{prod.get('mandatory_disclaimer')}"</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. DANH SÁCH CHI TIẾT CLAIMS
        st.markdown("### 📑 Danh Mục Claims Đang Kiểm Soát")
        for c in prod.get("claims", []):
            if c["status"] == "APPROVED" and c["zone"] == "COMMERCIAL_APPROVED":
                border_color = "#10b981"
                status_badge = '<span style="background: #ecfdf5; color: #047857; border: 1px solid #10b981; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 800;">✅ HỢP LỆ — ĐƯỢC PHÉP DÙNG</span>'
            elif c["status"] == "EXPIRED":
                border_color = "#ef4444"
                status_badge = '<span style="background: #fef2f2; color: #b91c1c; border: 1px solid #ef4444; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 800;">❌ ĐÃ HẾT HẠN — KHÓA TỰ ĐỘNG</span>'
            else:
                border_color = "#0284c7"
                status_badge = '<span style="background: #f0f9ff; color: #0284c7; border: 1px solid #0284c7; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 800;">🔒 CHUYÊN MÔN NỘI BỘ</span>'
                
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #cbd5e1; border-left: 6px solid {border_color}; border-radius: 12px; padding: 18px; margin-bottom: 14px; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="color: #0f172a; font-size: 16px; font-weight: 800;">Mã Claim: <code style="background: #f1f5f9; color: #0284c7; padding: 2px 8px; border-radius: 6px;">{c['claim_id']}</code></div>
                    {status_badge}
                </div>
                <div style="color: #0f172a; font-size: 15px; font-weight: 700; line-height: 1.5; margin: 10px 0;">
                    "{c['claim_text']}"
                </div>
                <div style="color: #64748b; font-size: 13px; font-weight: 500; padding-top: 8px; border-top: 1px dashed #e2e8f0;">
                    👤 <b>Người duyệt:</b> <span style="color: #1e293b;">{c['approved_by']}</span> &nbsp;|&nbsp; 
                    📅 <b>Hiệu lực đến:</b> <span style="color: #1e293b;">{c['effective_until']}</span> &nbsp;|&nbsp; 
                    📚 <b>Nguồn chứng cứ:</b> <span style="color: #1e293b;">{c['evidence_source']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
