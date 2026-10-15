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
    st.header("🎯 B2B Partner Discovery & Lead Workspace")
    st.markdown("""
    *Hệ thống tự động phát hiện, làm sạch và xếp hạng đối tác B2B (Nhà thuốc, Shop Mẹ & Bé, Đại lý) 
    dựa trên **Mô hình Đánh giá 4 Chiều định lượng** (0–100 điểm) và gom nhóm chi nhánh chuỗi.*
    """)
    
    # 1. THANH TÌM KIẾM NHANH
    search_keyword = st.text_input("🔍 Tìm nhanh theo tên, tuyến đường, số điện thoại hoặc từ khóa sản phẩm:", placeholder="VD: Long Châu, Nguyễn Thị Thập, Canxi, Mẹ bầu...")
    
    # 2. BỘ LỌC ĐA TIÊU CHÍ
    with st.expander("⚙️ Bộ lọc Nâng cao (Địa bàn, Loại hình, Điểm số, Trạng thái)", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
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
        with col4:
            status_filter = st.selectbox("Trạng thái phê duyệt:", ["Tất cả", "NEW", "APPROVED", "REJECTED"])
            
        min_fit = st.slider("Lọc theo Điểm Phù Hợp tối thiểu (Fit Score):", min_value=0, max_value=100, value=70, step=5)
        
    filtered_leads = filter_leads(
        province=province,
        district=district,
        lead_type=lead_type,
        status=status_filter,
        min_fit_score=min_fit,
        search_keyword=search_keyword
    )
    
    # 3. CHỈ SỐ DASHBOARD NHANH
    approved_count = sum(1 for l in filtered_leads if l.get("status") == "APPROVED")
    high_grade_count = sum(1 for l in filtered_leads if l.get("fit_score", 0) >= 90)
    
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Tổng Lead Tìm Thấy", len(filtered_leads))
    mcol2.metric("Đạt Hạng A+ (≥90đ)", high_grade_count, delta="Ưu tiên số 1")
    mcol3.metric("Đã Duyệt (Approved)", approved_count, delta="Sẵn sàng tiếp cận")
    mcol4.metric("Khu Vực Khảo Sát", f"{province} / {district}")
    
    st.divider()
    
    if filtered_leads:
        df = export_leads_to_dataframe(filtered_leads)
        
        # 4. BẢNG DỮ LIỆU
        st.subheader("📋 Danh sách Hồ sơ Đối tác B2B")
        st.dataframe(
            df[["Mã Lead", "Tên đơn vị", "Loại hình", "Chuỗi mẹ", "Địa chỉ", "Điện thoại", "Điểm Phù Hợp", "Độ Tin Cậy", "Trạng Thái", "Người Phụ Trách"]],
            use_container_width=True,
            hide_index=True
        )
        
        # Nút xuất CSV / Excel
        c_dl1, c_dl2 = st.columns([1, 4])
        with c_dl1:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Xuất danh sách (CSV / Excel)",
                data=csv_data,
                file_name=f"dion_leads_{province}_{district}.csv",
                mime="text/csv"
            )
            
        st.divider()
        
        # 5. CHI TIẾT ĐÁNH GIÁ 4 CHIỀU & QUY TRÌNH DUYỆT LEAD (ACTION WORKFLOW)
        st.subheader("🔍 Thẩm định Chi tiết & Phê duyệt Lead")
        lead_id_list = [l["lead_id"] for l in filtered_leads]
        selected_id = st.selectbox("Chọn Lead để xem hồ sơ năng lực và duyệt:", lead_id_list, format_func=lambda x: f"{x} - {next((item['name'] for item in filtered_leads if item['lead_id'] == x), '')}")
        
        selected_lead = get_lead_by_id(selected_id)
        if selected_lead:
            st.markdown(f"#### 🏢 {selected_lead['name']} (`{selected_lead['lead_id']}`)")
            st.write(f"📍 **Địa chỉ:** {selected_lead['address']} | 📞 **SĐT:** {selected_lead['phone']} | ✉️ **Email:** {selected_lead['email']}")
            st.write(f"🏷️ **Danh mục hàng:** {', '.join(selected_lead.get('categories', []))}")
            st.caption(f"🔗 **Nguồn thu thập công khai:** [{selected_lead.get('source_url', '')}]({selected_lead.get('source_url', '')})")
            
            # Hiển thị 4 thanh điểm số
            s1, s2, s3, s4 = st.columns(4)
            s1.write(f"**1. Mức phù hợp (Fit):** `{selected_lead['fit_score']}/100`")
            s1.progress(selected_lead['fit_score'] / 100)
            
            s2.write(f"**2. Tin cậy dữ liệu (Trust):** `{selected_lead['trust_score']}/100`")
            s2.progress(selected_lead['trust_score'] / 100)
            
            s3.write(f"**3. Khả năng liên hệ:** `{selected_lead['contact_score']}/100`")
            s3.progress(selected_lead['contact_score'] / 100)
            
            s4.write(f"**4. Tín hiệu nhu cầu:** `{selected_lead['intent_score']}/100`")
            s4.progress(selected_lead['intent_score'] / 100)
            
            st.info(f"💡 **Tín hiệu quan sát thực tế:** {selected_lead['intent_signals']}")
            
            # Khung duyệt và phân công Sales
            st.markdown("##### 👤 Thao tác Nghiệp vụ:")
            b_col1, b_col2, b_col3 = st.columns([1.5, 2, 2])
            
            sales_reps = ["Trần Thị Mai (Sales Q7)", "Nguyễn Hoàng Nam (Key Account)", "Lê Văn Hùng (Senior Sales Q1)", "Vũ Minh Tuấn (Hà Nội Lead)"]
            
            with b_col1:
                if st.button("✅ Phê duyệt Lead (Approve)", type="primary"):
                    update_lead_status(selected_id, "APPROVED")
                    st.success(f"Đã duyệt đối tác `{selected_id}` thành công!")
                    st.rerun()
            with b_col2:
                rep = st.selectbox("Chọn Sales phụ trách:", sales_reps, key="assign_rep_select")
                if st.button("👤 Giao việc (Assign)"):
                    update_lead_status(selected_id, "APPROVED", assigned_to=rep)
                    st.success(f"Đã giao `{selected_id}` cho {rep}!")
                    st.rerun()
            with b_col3:
                if st.button("❌ Loại bỏ Lead (Reject)"):
                    update_lead_status(selected_id, "REJECTED")
                    st.warning(f"Đã chuyển `{selected_id}` sang trạng thái Loại bỏ.")
                    st.rerun()
                    
        st.divider()
        
        # 6. PHÁT HIỆN & GOM CỤM CHUỖI (DEDUPLICATION)
        st.subheader("🔗 Phát hiện & Gom Cụm Chi Nhánh (Chain Deduplication)")
        grouped = group_by_parent_chain(filtered_leads)
        for parent, items in grouped.items():
            if parent != "Độc lập / Chưa gom nhóm" and len(items) > 1:
                with st.expander(f"📦 Chuỗi '{parent}' — Phát hiện {len(items)} điểm bán cùng hệ thống", expanded=True):
                    st.markdown(f"**Khuyến nghị AI:** Đàm phán tập trung qua **Phòng Mua Hàng của {parent}**, không tiếp cận đơn lẻ từng chi nhánh.")
                    for it in items:
                        st.write(f"- 📍 **{it['name']}** (`{it['lead_id']}`): {it['address']} — Trạng thái: `{it['status']}`")
    else:
        st.warning("Không có đối tác nào thỏa mãn bộ lọc hiện tại. Vui lòng thử nới lỏng tiêu chí tìm kiếm.")
