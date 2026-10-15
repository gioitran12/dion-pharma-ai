import streamlit as st
from modules.sales_copilot import generate_copilot_response
from modules.claims_hub import get_all_products

def render_tab_copilot():
    st.markdown("## 💬 AI Sales & Product Copilot (Trợ lý bán hàng)")
    st.markdown("""
    *Trợ lý nội bộ hỗ trợ nhân viên Sales và CSKH tra cứu sản phẩm tức thì. 
    **100% câu trả lời được kiểm soát bởi Claims đã duyệt**, tự động phát hiện câu hỏi rủi ro y tế để **chuyển Dược sĩ**.*
    """)
    
    products = get_all_products()
    sku_options = {"ALL": "Tất cả sản phẩm"}
    for p in products:
        sku_options[p["sku"]] = f"📦 {p['sku']} - {p['name']}"
        
    c1, c2 = st.columns([1, 2])
    with c1:
        selected_sku = st.selectbox("Ngữ cảnh sản phẩm:", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])
        
    # Gợi ý kịch bản thử nghiệm dạng nút bấm sinh động
    st.markdown("##### 💡 Gợi ý câu hỏi thử nghiệm kịch bản:")
    q_col1, q_col2, q_col3 = st.columns(3)
    sample_query = None
    if q_col1.button("1. 🦴 Công dụng D3 là gì?", use_container_width=True):
        sample_query = "Vitamin D3 có công dụng gì đối với xương và cơ thể?"
    if q_col2.button("2. ⚠️ Bầu 3 tháng uống được không?", use_container_width=True):
        sample_query = "Khách hàng đang mang thai 3 tháng đầu có dùng được Vitamin D3 không?"
    if q_col3.button("3. 🩸 Sắt Fero-Plus có táo bón không?", use_container_width=True):
        sample_query = "Viên sắt Fero-Plus có bị táo bón và buồn nôn không?"
        
    user_query = st.text_input("💬 Nhập câu hỏi của khách hàng / nhân viên:", value=sample_query or "", placeholder="Gõ câu hỏi tại đây rồi nhấn [Gửi câu hỏi]...")
    
    if st.button("🚀 Gửi câu hỏi", type="primary") and user_query:
        with st.spinner("AI Copilot đang tra cứu từ Claims Knowledge Base..."):
            res = generate_copilot_response(user_query, sku=selected_sku)
            
            st.divider()
            if res["type"] == "ESCALATION":
                st.markdown(f"""
                <div style="background: #fef2f2; border: 2px solid #ef4444; border-radius: 12px; padding: 20px; margin-top: 10px;">
                    <h4 style="color: #b91c1c; margin: 0 0 10px 0; font-weight: 800;">{res['badge']}</h4>
                    <div style="color: #7f1d1d; font-size: 15px; white-space: pre-line;">{res['content']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: #f0fdf4; border: 2px solid #10b981; border-radius: 12px; padding: 20px; margin-top: 10px;">
                    <h4 style="color: #047857; margin: 0 0 10px 0; font-weight: 800;">{res['badge']}</h4>
                    <div style="color: #064e3b; font-size: 15px; white-space: pre-line;">{res['content']}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.text_area("📋 Đoạn trả lời đã kiểm duyệt (Sao chép để gửi khách hàng):", value=res["content"], height=160)
