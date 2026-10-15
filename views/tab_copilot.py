import streamlit as st
from modules.sales_copilot import generate_copilot_response
from modules.claims_hub import get_all_products

def render_tab_copilot():
    st.header("💬 AI Sales & Product Copilot (Trợ lý bán hàng)")
    st.markdown("""
    *Trợ lý nội bộ hỗ trợ Sales và CSKH tra cứu sản phẩm tức thì. Câu trả lời được kiểm soát bởi **Knowledge Grounding** 
    (chỉ lấy từ Claims đã duyệt, có trích dẫn nguồn). **Tự động nhận diện câu hỏi nhạy cảm (thai kỳ, bệnh nền) để chuyển Dược sĩ**.*
    """)
    
    # Chọn ngữ cảnh sản phẩm
    products = get_all_products()
    sku_options = {"ALL": "Tất cả sản phẩm"}
    for p in products:
        sku_options[p["sku"]] = f"{p['sku']} - {p['name']}"
        
    selected_sku = st.selectbox("Ngữ cảnh sản phẩm:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
    
    # Gợi ý các câu hỏi thử nghiệm kịch bản demo
    st.markdown("**💡 Gợi ý câu hỏi để thử nghiệm:**")
    col1, col2, col3 = st.columns(3)
    sample_query = None
    if col1.button("1. Công dụng D3 là gì?"):
        sample_query = "Vitamin D3 có công dụng gì đối với xương và cơ thể?"
    if col2.button("2. Hỏi nhạy cảm thai kỳ ⚠️"):
        sample_query = "Khách hàng đang mang thai 3 tháng đầu có dùng được Vitamin D3 không?"
    if col3.button("3. Bổ máu & Sắt hữu cơ"):
        sample_query = "Viên sắt Fero-Plus có bị táo bón và buồn nôn không?"
        
    # Khung nhập câu hỏi của người dùng
    user_query = st.text_input("Nhập câu hỏi của khách hàng / nhân viên:", value=sample_query or "")
    
    if st.button("Gửi câu hỏi", type="primary") and user_query:
        with st.spinner("AI Copilot đang tra cứu từ Claims Knowledge Base..."):
            res = generate_copilot_response(user_query, sku=selected_sku)
            
            if res["type"] == "ESCALATION":
                st.error(res["badge"])
                st.warning(res["content"])
            else:
                st.success(res["badge"])
                st.markdown(res["content"])
                
                # Nút sao chép văn bản
                st.text_area("📋 Đoạn văn mẫu đã kiểm duyệt (Copy để gửi cho khách):", value=res["content"], height=160)
