import streamlit as st
import pandas as pd
from modules.lead_discovery import (
    filter_leads,
    export_leads_to_dataframe,
    group_by_parent_chain,
    update_lead_status,
    get_lead_by_id
)

def render_tab_leads():
    st.markdown("## 🎯 Tìm Kiếm & Đánh Giá Đối Tác B2B")
    st.markdown("Hệ thống tự động phát hiện, làm sạch và xếp hạng đối tác phân phối (Nhà thuốc, Shop Mẹ & Bé, Đại lý) theo **Mô hình 4 Chiều định lượng**.")
    
    # 1. BỘ LỌC TÌM KIẾM MẠCH LẠC
    search_keyword = st.text_input("🔍 Tìm kiếm theo tên, tuyến đường, số điện thoại hoặc ngành hàng:", placeholder="Nhập từ khóa (Ví dụ: Long Châu, Nguyễn Thị Thập, Canxi, Mẹ bầu...)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        province = st.selectbox("Tỉnh / Thành phố:", ["Tất cả", "TP. Hồ Chí Minh", "Hà Nội"])
    with col2:
        district_opts = ["Tất cả"]
        if province == "TP. Hồ Chí Minh":
            district_opts += ["Quận 1", "Quận 7", "Quận 10", "Quận Tân Bình"]
        elif province == "Hà Nội":
            district_opts += ["Quận Hai Bà Trưng", "Quận Cầu Giấy", "Quận Đống Đa"]
        district = st.selectbox("Quận / Huyện:", district_opts)
    with col3:
        lead_type = st.selectbox("Loại hình đối tác:", ["Tất cả", "Nhà thuốc tư nhân", "Chuỗi nhà thuốc", "Cửa hàng Mẹ & Bé", "Đại lý phân phối"])
        
    filtered_leads = filter_leads(
        province=province,
        district=district,
        lead_type=lead_type,
        status="Tất cả",
        min_fit_score=0,
        search_keyword=search_keyword
    )
    
    # 2. CHỈ SỐ THỐNG KÊ RÕ RÀNG
    approved_count = sum(1 for l in filtered_leads if l.get("status") == "APPROVED")
    high_grade_count = sum(1 for l in filtered_leads if l.get("fit_score", 0) >= 90)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng Lead tìm thấy", len(filtered_leads))
    m2.metric("Hạng A+ (≥90 điểm)", high_grade_count, delta="Ưu tiên cao")
    m3.metric("Đã Phê Duyệt", approved_count, delta="Sẵn sàng tiếp cận")
    m4.metric("Khu Vực", f"{province} / {district}")
    
    st.divider()
    
    if filtered_leads:
        df = export_leads_to_dataframe(filtered_leads)
        
        # 3. BẢNG DỮ LIỆU ĐỐI TÁC
        st.markdown("### 📋 Danh Sách Đối Tác Tiềm Năng")
        st.dataframe(
            df[["Mã Lead", "Tên đơn vị", "Loại hình", "Chuỗi mẹ", "Địa chỉ", "Điện thoại", "Điểm Phù Hợp", "Độ Tin Cậy", "Trạng Thái", "Người Phụ Trách"]],
            use_container_width=True,
            hide_index=True
        )
        
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Tải file danh sách Lead (CSV / Excel)",
            data=csv_data,
            file_name="dion_leads_export.csv",
            mime="text/csv"
        )
        
        st.divider()
        
        # 4. THẨM ĐỊNH HỒ SƠ & THAO TÁC DUYỆT
        st.markdown("### 🔍 Thẩm Định Năng Lực & Duyệt Đối Tác")
        lead_id_list = [l["lead_id"] for l in filtered_leads]
        selected_id = st.selectbox("Chọn Đối tác để xem chi tiết:", lead_id_list, format_func=lambda x: f"{x} - {next((item['name'] for item in filtered_leads if item['lead_id'] == x), '')}")
        
        lead = get_lead_by_id(selected_id)
        if lead:
            st.markdown(f"#### 🏢 {lead['name']} (`{lead['lead_id']}`)")
            st.markdown(f"- **Địa chỉ:** {lead['address']}")
            st.markdown(f"- **Liên hệ:** Điện thoại: `{lead['phone']}` | Email: `{lead['email']}`")
            st.markdown(f"- **Danh mục kinh doanh:** {', '.join(lead.get('categories', []))}")
            st.caption(f"🔗 **Nguồn công khai:** [{lead.get('source_url', '')}]({lead.get('source_url', '')})")
            
            # Điểm 4 chiều
            st.markdown("**Điểm Đánh Giá 4 Chiều Định Lượng:**")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("1. Mức Phù Hợp", f"{lead['fit_score']}/100", f"Hạng {lead['fit_grade']}")
            s2.metric("2. Độ Tin Cậy Dữ Liệu", f"{lead['trust_score']}/100", lead['trust_level'][:16]+"...")
            s3.metric("3. Khả Năng Liên Hệ", f"{lead['contact_score']}/100", "Đầy đủ kênh")
            s4.metric("4. Tín Hiệu Nhu Cầu", f"{lead['intent_score']}/100", "Nhu cầu cao")
            
            st.info(f"💡 **Tín hiệu quan sát:** {lead['intent_signals']}")
            
            # Thao tác duyệt
            st.markdown("**Thao tác Phê Duyệt:**")
            act1, act2, act3 = st.columns([1.5, 2, 1.5])
            
            sales_reps = ["Trần Thị Mai (Sales Q7)", "Nguyễn Hoàng Nam (Key Account)", "Lê Văn Hùng (Senior Sales Q1)", "Vũ Minh Tuấn (Hà Nội Lead)"]
            with act1:
                if st.button("✅ Phê Duyệt Lead", type="primary", use_container_width=True):
                    update_lead_status(selected_id, "APPROVED")
                    st.success("Đã duyệt thành công!")
                    st.rerun()
            with act2:
                rep = st.selectbox("Giao cho nhân viên Sales:", sales_reps)
                if st.button("👤 Xác Nhận Giao Việc", use_container_width=True):
                    update_lead_status(selected_id, "APPROVED", assigned_to=rep)
                    st.success(f"Đã giao việc cho {rep}!")
                    st.rerun()
            with act3:
                if st.button("❌ Loại Bỏ Lead", use_container_width=True):
                    update_lead_status(selected_id, "REJECTED")
                    st.warning("Đã loại bỏ đối tác.")
                    st.rerun()
                    
        st.divider()
        
        # 5. GOM CỤM CHUỖI
        st.markdown("### 🔗 Nhận Diện & Gom Cụm Chi Nhánh Chuỗi")
        grouped = group_by_parent_chain(filtered_leads)
        for parent, items in grouped.items():
            if parent != "Độc lập / Chưa gom nhóm" and len(items) > 1:
                with st.expander(f"📦 Chuỗi {parent} — Phát hiện {len(items)} chi nhánh cùng hệ thống", expanded=True):
                    st.info(f"💡 **Khuyến nghị AI:** Đàm phán cung ứng tập trung qua **Phòng Mua Hàng của {parent}**.")
                    for it in items:
                        st.write(f"- 📍 **{it['name']}**: {it['address']} (Trạng thái: `{it['status']}`)")
    else:
        st.warning("Không tìm thấy đối tác nào phù hợp.")
