import streamlit as st
from modules.content_generator import generate_marketing_draft, validate_content_compliance
from modules.claims_hub import get_all_products

def render_tab_content():
    st.header("✍️ AI Content & Compliance Engine")
    st.markdown("""
    *Hệ thống tạo nội dung truyền thông đa kênh dựa trên **Claims đang còn hiệu lực**. 
    Tự động gắn Disclaimer bắt buộc và **quét phát hiện vi phạm từ cấm theo Nghị định 342/2025/NĐ-CP**.*
    """)
    
    products = get_all_products()
    sku_options = {p["sku"]: f"{p['sku']} - {p['name']}" for p in products}
    
    col1, col2, col3 = st.columns(3)
    with col1:
        sku = st.selectbox("Chọn Sản phẩm viết bài:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
    with col2:
        channel = st.selectbox("Kênh xuất bản:", ["Facebook Post", "Email Giới thiệu Đối tác", "Zalo OA Broadcast"])
    with col3:
        tone = st.selectbox("Văn phong:", ["Khoa học & Chuyên môn", "Truyền cảm hứng & Thân thiện", "Tập trung B2B Đối tác"])
        
    if st.button("Tạo bản nháp Marketing", type="primary"):
        res = generate_marketing_draft(sku, channel, tone)
        if "error" in res:
            st.error(res["error"])
        else:
            st.success("✅ Bản nháp đã được sinh ra thành công từ Claims hợp lệ!")
            st.info(f"Các Claim được sử dụng: `{', '.join(res['used_claims'])}`")
            
            # Khung chỉnh sửa nội dung
            edited_text = st.text_area("Nội dung bài viết (Có thể sửa trực tiếp để thử bộ lọc vi phạm):", value=res["draft_text"], height=300)
            
            # Quét kiểm tra vi phạm thời gian thực
            is_valid, violations = validate_content_compliance(edited_text)
            
            st.divider()
            st.subheader("🛡️ Kết quả thẩm định Pháp lý (Compliance Check)")
            if is_valid:
                st.success("✅ NỘI DUNG ĐẠT CHUẨN: Không phát hiện từ ngữ cấm hoặc cam kết sai quy định.")
            else:
                st.error(f"❌ CẢNH BÁO VI PHẠM PHÁP LÝ: Phát hiện {len(violations)} lỗi quy định theo NĐ 342/2025/NĐ-CP!")
                for v in violations:
                    st.warning(f"• Từ ngữ vi phạm: **'{v['term']}'**\n"
                               f"  - Lý do: {v['reason']}\n"
                               f"  - Gợi ý thay thế: *{v['suggestion']}*")
