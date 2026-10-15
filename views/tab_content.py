import streamlit as st
from modules.content_generator import generate_marketing_draft, validate_content_compliance
from modules.claims_hub import get_all_products

def render_tab_content():
    st.markdown("## ✍️ Sản Xuất Nội Dung & Kiểm Soát Pháp Lý")
    st.markdown("Tự động tạo nội dung truyền thông đa kênh dựa trên **Claims đang còn hiệu lực**. Đính kèm Disclaimer bắt buộc và **quét phát hiện vi phạm từ cấm theo Nghị định 342/2025/NĐ-CP**.")
    
    products = get_all_products()
    sku_options = {p["sku"]: f"[{p['sku']}] {p['name']}" for p in products}
    
    col_left, col_right = st.columns([1, 1.3])
    
    with col_left:
        st.markdown("### ⚙️ Thiết Lập Bài Viết")
        sku = st.selectbox("Chọn Sản phẩm viết bài:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
        channel = st.selectbox("Kênh xuất bản:", ["Facebook Post", "Email Giới thiệu Đối tác", "Zalo OA Broadcast"])
        tone = st.selectbox("Văn phong:", ["Khoa học & Chuyên môn", "Truyền cảm hứng & Thân thiện", "Tập trung B2B Đối tác"])
        
        generate_btn = st.button("✨ Tạo Bản Nháp Bài Viết", type="primary", use_container_width=True)
        
        st.info("""
        **🛡️ Nguyên tắc Tuân thủ:**
        - Chỉ dùng Claims hợp lệ (APPROVED).
        - Luôn đính kèm câu Disclaimer bắt buộc.
        - Tự động phát hiện và cảnh báo từ ngữ vi phạm luật.
        """)
        
    with col_right:
        st.markdown("### 📱 Bản Soạn Thảo & Thẩm Định")
        
        if generate_btn or "current_draft" not in st.session_state:
            res = generate_marketing_draft(sku, channel, tone)
            st.session_state["current_draft"] = res.get("draft_text", "")
            st.session_state["used_claims"] = res.get("used_claims", [])
            
        draft_text = st.session_state.get("current_draft", "")
        used_claims = st.session_state.get("used_claims", [])
        
        if used_claims:
            st.caption(f"✅ Đang sử dụng các Claim hợp lệ: `{', '.join(used_claims)}`")
            
        edited_text = st.text_area("Chỉnh sửa nội dung (Thử gõ từ cấm như 'chữa bệnh', 'khỏi hẳn' để kiểm tra bộ lọc):", value=draft_text, height=260)
        
        # Thẩm định vi phạm
        is_valid, violations = validate_content_compliance(edited_text)
        
        if is_valid:
            st.success("✅ **NỘI DUNG ĐẠT CHUẨN:** Không phát hiện từ ngữ vi phạm quy định quảng cáo (Nghị định 342/2025/NĐ-CP).")
        else:
            st.error(f"❌ **CẢNH BÁO VI PHẠM PHÁP LÝ ({len(violations)} lỗi phát hiện):**")
            for v in violations:
                st.warning(f"• Từ vi phạm: **'{v['term']}'**\n  - Lý do: {v['reason']}\n  - Gợi ý thay thế: *{v['suggestion']}*")
