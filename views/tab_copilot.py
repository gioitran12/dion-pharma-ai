import streamlit as st
from modules.sales_copilot import generate_copilot_response
from modules.claims_hub import get_all_products

def render_tab_copilot():
    st.markdown("## 💬 Trợ Lý Bán Hàng & Tư Vấn (Sales Copilot)")
    st.markdown("Hỗ trợ nhân viên Sales/CSKH tra cứu sản phẩm tức thì. Câu trả lời **100% trích xuất từ Claims đã duyệt**, tự động phát hiện câu hỏi rủi ro y tế để **chuyển Dược sĩ**.")
    
    products = get_all_products()
    sku_options = {"ALL": "Tất cả sản phẩm"}
    for p in products:
        sku_options[p["sku"]] = f"[{p['sku']}] {p['name']}"
        
    selected_sku = st.selectbox("Ngữ cảnh sản phẩm:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
    
    # Gợi ý câu hỏi
    st.markdown("**💡 Gợi ý câu hỏi mẫu thử nghiệm kịch bản:**")
    q1, q2, q3 = st.columns(3)
    sample_query = None
    if q1.button("1. 🦴 Công dụng D3 là gì?", use_container_width=True):
        sample_query = "Vitamin D3 có công dụng gì đối với xương và cơ thể?"
    if q2.button("2. ⚠️ Bầu 3 tháng uống được không?", use_container_width=True):
        sample_query = "Khách hàng đang mang thai 3 tháng đầu có dùng được Vitamin D3 không?"
    if q3.button("3. 🩸 Sắt Fero-Plus có táo bón không?", use_container_width=True):
        sample_query = "Viên sắt Fero-Plus có bị táo bón và buồn nôn không?"
        
    user_query = st.text_input("💬 Nhập câu hỏi của khách hàng / nhân viên:", value=sample_query or "", placeholder="Nhập câu hỏi tại đây rồi nhấn [Gửi câu hỏi]...")
    
    if st.button("🚀 Gửi câu hỏi", type="primary") and user_query:
        with st.spinner("AI Copilot đang tra cứu từ Claims Knowledge Base..."):
            res = generate_copilot_response(user_query, sku=selected_sku)
            
            st.divider()
            if res["type"] == "ESCALATION":
                st.error(f"### {res['badge']}")
                st.warning(res["content"])
            elif res["type"] == "INSUFFICIENT_EVIDENCE":
                st.warning(f"### {res['badge']}")
                st.info(res["content"])
            else:
                st.success(f"### 📝 {res['badge']} — BẢN NHÁP ĐỀ XUẤT")
                st.info("ℹ️ **Lưu ý kiểm duyệt:** Câu trả lời dưới đây là bản nháp do AI đề xuất dựa trên các Claims đã duyệt. Nhân viên cần duyệt lại trước khi gửi khách hàng.")
                st.markdown(res["content"])
                
            if res.get("citations"):
                with st.expander("📚 Nguồn Claims đối soát từ Knowledge Hub", expanded=True):
                    for cit in res["citations"]:
                        st.markdown(f"- {cit}")
                
            st.text_area("📋 Đoạn trả lời đã kiểm duyệt (Sao chép để gửi khách hàng):", value=res["content"], height=160)
