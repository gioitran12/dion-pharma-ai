import streamlit as st
from modules.content_generator import generate_marketing_draft, validate_content_compliance
from modules.claims_hub import get_all_products

def render_tab_content():
    st.markdown("## ✍️ AI Content & Compliance Engine")
    st.markdown("""
    *Hệ thống sản xuất nội dung truyền thông đa kênh dựa trên **Claims đang còn hiệu lực**. 
    Tự động gắn Disclaimer bắt buộc và **quét phát hiện vi phạm từ cấm theo Nghị định 342/2025/NĐ-CP**.*
    """)
    
    products = get_all_products()
    sku_options = {p["sku"]: f"📦 {p['sku']} - {p['name']}" for p in products}
    
    # BỐ CỤC CHIA 2 CỘT: TRÁI LÀ CẤU HÌNH, PHẢI LÀ PREVIEW
    left_col, right_col = st.columns([1, 1.3])
    
    with left_col:
        st.markdown("### ⚙️ Thiết lập Nội dung")
        sku = st.selectbox("Chọn Sản phẩm viết bài:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
        channel = st.selectbox("Kênh xuất bản:", ["Facebook Post", "Email Giới thiệu Đối tác", "Zalo OA Broadcast"])
        tone = st.selectbox("Văn phong:", ["Khoa học & Chuyên môn", "Truyền cảm hứng & Thân thiện", "Tập trung B2B Đối tác"])
        
        generate_btn = st.button("✨ Tạo Bản Nháp Marketing", type="primary", use_container_width=True)
        
        st.markdown("""
        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 14px; margin-top: 16px;">
            <b style="color: #1d4ed8;">🛡️ Nguyên tắc AI Content:</b>
            <ul style="color: #1e40af; font-size: 13px; margin: 6px 0 0 -10px;">
                <li>Chỉ dùng Claims còn hạn (Status: APPROVED).</li>
                <li>Tự động gắn Disclaimer y tế ở chân bài.</li>
                <li>Bộ lọc tự động phát hiện và chặn từ ngữ vi phạm.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with right_col:
        st.markdown("### 📱 Bản Xem Trước & Thẩm Định Pháp Lý")
        
        if generate_btn or "current_draft" not in st.session_state:
            res = generate_marketing_draft(sku, channel, tone)
            st.session_state["current_draft"] = res.get("draft_text", "")
            st.session_state["used_claims"] = res.get("used_claims", [])
            
        draft_text = st.session_state.get("current_draft", "")
        used_claims = st.session_state.get("used_claims", [])
        
        if used_claims:
            st.caption(f"✅ Đang sử dụng các Claim hợp lệ: `{', '.join(used_claims)}`")
            
        # Khung chỉnh sửa nội dung
        edited_text = st.text_area("Chỉnh sửa nội dung (Thử gõ từ cấm như 'chữa bệnh', 'khỏi hẳn' để xem bộ lọc cảnh báo):", value=draft_text, height=260)
        
        # Thẩm định vi phạm thời gian thực
        is_valid, violations = validate_content_compliance(edited_text)
        
        if is_valid:
            st.markdown("""
            <div style="background: #ecfdf5; border: 2px solid #10b981; border-radius: 10px; padding: 14px;">
                <b style="color: #047857; font-size: 15px;">✅ NỘI DUNG ĐẠT CHUẨN PHÁP LÝ</b><br/>
                <span style="color: #065f46; font-size: 13px;">Không phát hiện từ cấm hoặc cam kết sai quy định theo NĐ 342/2025/NĐ-CP.</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: #fef2f2; border: 2px solid #ef4444; border-radius: 10px; padding: 14px;">
                <b style="color: #b91c1c; font-size: 15px;">❌ CẢNH BÁO VI PHẠM PHÁP LÝ ({len(violations)} lỗi)</b><br/>
                <span style="color: #991b1b; font-size: 13px;">Nội dung vi phạm quy định quảng cáo thực phẩm bảo vệ sức khỏe:</span>
            </div>
            """, unsafe_allow_html=True)
            for v in violations:
                st.warning(f"• Từ vi phạm: **'{v['term']}'**\n  - Lý do: {v['reason']}\n  - Gợi ý thay thế: *{v['suggestion']}*")
