import streamlit as st
import io
import pandas as pd
from modules.lead_discovery import filter_leads, export_leads_to_dataframe, group_by_parent_chain

def render_tab_leads():
    st.header("🎯 B2B Lead Discovery & Partner Enrichment")
    st.markdown("""
    *Hệ thống tự động tìm kiếm, làm sạch và đánh giá đối tác phân phối B2B (Nhà thuốc, Cửa hàng Mẹ & Bé, Đại lý) 
    theo **4 chiều đánh giá** (Mức phù hợp, Độ tin cậy dữ liệu, Khả năng liên hệ, Tín hiệu nhu cầu).*
    """)
    
    # Bộ lọc tìm kiếm
    col1, col2, col3 = st.columns(3)
    with col1:
        province = st.selectbox("Tỉnh / Thành phố:", ["Tất cả", "TP. Hồ Chí Minh", "Hà Nội"])
    with col2:
        district_opts = ["Tất cả"]
        if province == "TP. Hồ Chí Minh":
            district_opts += ["Quận 7", "Quận 10"]
        elif province == "Hà Nội":
            district_opts += ["Quận Hai Bà Trưng", "Quận Cầu Giấy"]
        district = st.selectbox("Quận / Huyện:", district_opts)
    with col3:
        lead_type = st.selectbox("Loại hình đối tác:", ["Tất cả", "Nhà thuốc tư nhân", "Chuỗi nhà thuốc", "Cửa hàng Mẹ & Bé", "Đại lý phân phối"])
        
    filtered_leads = filter_leads(province, district, lead_type)
    
    # Chỉ số thống kê nhanh
    st.metric("Số lượng Lead phù hợp tìm thấy", len(filtered_leads))
    
    if filtered_leads:
        df = export_leads_to_dataframe(filtered_leads)
        
        # Hiển thị bảng dữ liệu tương tác
        st.dataframe(
            df[["Mã Lead", "Tên đơn vị", "Loại hình", "Chuỗi mẹ", "Địa chỉ", "Điện thoại", "Độ phù hợp", "Xác minh dữ liệu", "Trạng thái duyệt"]],
            use_container_width=True,
            hide_index=True
        )
        
        # Nút xuất Excel / CSV
        col_exp1, col_exp2 = st.columns([1, 4])
        with col_exp1:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Xuất dữ liệu CSV",
                data=csv_data,
                file_name="dion_b2b_leads_export.csv",
                mime="text/csv"
            )
            
        st.divider()
        
        # Tính năng nhận diện và gom nhóm chuỗi
        st.subheader("🔗 Nhận diện & Gom nhóm Chi nhánh (Deduplication)")
        grouped = group_by_parent_chain(filtered_leads)
        for parent, items in grouped.items():
            if parent != "Độc lập / Chưa gom nhóm" and len(items) > 1:
                st.info(f"Phát hiện **{len(items)} chi nhánh** thuộc chuỗi **{parent}**. Hệ thống tự động gom vào 1 đầu mối đàm phán hợp đồng tập trung:")
                for it in items:
                    st.write(f"- 📍 `{it['lead_id']}`: {it['name']} ({it['address']})")
    else:
        st.info("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
