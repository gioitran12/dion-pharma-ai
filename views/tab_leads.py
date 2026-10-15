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
    st.markdown("## 🎯 B2B Partner Discovery & Lead Workspace")
    st.markdown("""
    *Hệ thống tự động phát hiện, làm sạch và xếp hạng đối tác phân phối B2B (Nhà thuốc, Shop Mẹ & Bé, Đại lý) 
    dựa trên **Mô hình Đánh giá 4 Chiều định lượng** (0–100 điểm) và gom cụm chi nhánh chuỗi.*
    """)
    
    # 1. BỐ CỤC CHIA 2 CỘT: TRÁI LÀ BỘ LỌC, PHẢI LÀ THỐNG KÊ
    filter_col, stats_col = st.columns([2.5, 1.5])
    
    with filter_col:
        search_keyword = st.text_input("🔍 Tìm kiếm theo tên, tuyến đường, SĐT hoặc ngành hàng:", placeholder="VD: Long Châu, Nguyễn Thị Thập, Canxi, Mẹ bầu...")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            province = st.selectbox("Tỉnh / Thành:", ["Tất cả", "TP. Hồ Chí Minh", "Hà Nội"])
        with c2:
            district_opts = ["Tất cả"]
            if province == "TP. Hồ Chí Minh":
                district_opts += ["Quận 1", "Quận 7", "Quận 10", "Quận Tân Bình"]
            elif province == "Hà Nội":
                district_opts += ["Quận Hai Bà Trưng", "Quận Cầu Giấy", "Quận Đống Đa"]
            district = st.selectbox("Quận / Huyện:", district_opts)
        with c3:
            lead_type = st.selectbox("Loại hình:", ["Tất cả", "Nhà thuốc tư nhân", "Chuỗi nhà thuốc", "Cửa hàng Mẹ & Bé", "Đại lý phân phối"])
            
    filtered_leads = filter_leads(
        province=province,
        district=district,
        lead_type=lead_type,
        status="Tất cả",
        min_fit_score=0,
        search_keyword=search_keyword
    )
    
    with stats_col:
        approved_count = sum(1 for l in filtered_leads if l.get("status") == "APPROVED")
        high_grade_count = sum(1 for l in filtered_leads if l.get("fit_score", 0) >= 90)
        
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="font-weight: 800; color: #0284c7; font-size: 15px; margin-bottom: 8px;">📊 TỔNG QUAN TÌM KIẾM</div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                <span style="color: #475569;">Tổng Lead phù hợp:</span>
                <strong style="color: #0f172a; font-size: 18px;">{len(filtered_leads)}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                <span style="color: #047857;">Hạng Ưu Tiên A+:</span>
                <strong style="color: #047857; font-size: 18px;">{high_grade_count}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #1d4ed8;">Đã Phê Duyệt:</span>
                <strong style="color: #1d4ed8; font-size: 18px;">{approved_count}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    
    if filtered_leads:
        df = export_leads_to_dataframe(filtered_leads)
        
        # 2. BẢNG DỮ LIỆU
        st.markdown("### 📋 Danh Sách Đối Tác Tiềm Năng")
        st.dataframe(
            df[["Mã Lead", "Tên đơn vị", "Loại hình", "Chuỗi mẹ", "Địa chỉ", "Điện thoại", "Điểm Phù Hợp", "Độ Tin Cậy", "Trạng Thái", "Người Phụ Trách"]],
            use_container_width=True,
            hide_index=True
        )
        
        # Nút xuất file
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Tải file danh sách Lead (CSV / Excel)",
            data=csv_data,
            file_name="dion_leads_export.csv",
            mime="text/csv"
        )
        
        st.divider()
        
        # 3. CHI TIẾT ĐÁNH GIÁ 4 CHIỀU & THAO TÁC DUYỆT
        st.markdown("### 🔍 Hồ Sơ Năng Lực & Phê Duyệt Tiếp Cận")
        lead_id_list = [l["lead_id"] for l in filtered_leads]
        selected_id = st.selectbox("Chọn Đối tác để xem chi tiết 4 Chiều Đánh Giá:", lead_id_list, format_func=lambda x: f"{x} - {next((item['name'] for item in filtered_leads if item['lead_id'] == x), '')}")
        
        lead = get_lead_by_id(selected_id)
        if lead:
            # Card chi tiết
            status_color = "#10b981" if lead["status"] == "APPROVED" else ("#ef4444" if lead["status"] == "REJECTED" else "#0284c7")
            st.markdown(f"""
            <div style="background: #ffffff; border: 2px solid {status_color}; border-radius: 14px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h3 style="margin: 0; color: #0f172a; font-weight: 800;">{lead['name']}</h3>
                    <span style="background: {status_color}; color: white; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 13px;">{lead['status']}</span>
                </div>
                <div style="color: #334155; font-size: 14px; margin-bottom: 12px;">
                    📍 <b>Địa chỉ:</b> {lead['address']} &nbsp;|&nbsp; 
                    📞 <b>Hotline:</b> {lead['phone']} &nbsp;|&nbsp; 
                    ✉️ <b>Email:</b> {lead['email']}
                </div>
                <div style="color: #475569; font-size: 13px;">
                    🏷️ <b>Danh mục sản phẩm kinh doanh:</b> {', '.join(lead.get('categories', []))}<br/>
                    🔗 <b>Nguồn xác minh công khai:</b> <a href="{lead.get('source_url', '')}" target="_blank">{lead.get('source_url', '')}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 4 Thước đo định lượng trực quan
            st.markdown("#### 📊 Điểm số Đánh giá 4 Chiều:")
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("1. Mức Phù Hợp", f"{lead['fit_score']}/100", f"Hạng {lead['fit_grade']}")
            sc2.metric("2. Độ Tin Cậy Dữ Liệu", f"{lead['trust_score']}/100", lead['trust_level'][:16]+"...")
            sc3.metric("3. Khả Năng Liên Hệ", f"{lead['contact_score']}/100", "Đầy đủ kênh")
            sc4.metric("4. Tín Hiệu Nhu Cầu", f"{lead['intent_score']}/100", "Nhu cầu cao")
            
            st.info(f"💡 **Tín hiệu quan sát thị trường:** {lead['intent_signals']}")
            
            # Nút duyệt
            st.markdown("#### 👤 Thao tác Phê duyệt & Phân bổ Sales:")
            act_col1, act_col2, act_col3 = st.columns([1.5, 2, 1.5])
            
            sales_reps = ["Trần Thị Mai (Sales Q7)", "Nguyễn Hoàng Nam (Key Account)", "Lê Văn Hùng (Senior Sales Q1)", "Vũ Minh Tuấn (Hà Nội Lead)"]
            with act_col1:
                if st.button("✅ Phê Duyệt Lead", type="primary", use_container_width=True):
                    update_lead_status(selected_id, "APPROVED")
                    st.success("Đã duyệt thành công!")
                    st.rerun()
            with act_col2:
                rep = st.selectbox("Chọn Sales phụ trách:", sales_reps)
                if st.button("👤 Giao Việc", use_container_width=True):
                    update_lead_status(selected_id, "APPROVED", assigned_to=rep)
                    st.success(f"Đã giao cho {rep}!")
                    st.rerun()
            with act_col3:
                if st.button("❌ Loại Bỏ", use_container_width=True):
                    update_lead_status(selected_id, "REJECTED")
                    st.warning("Đã loại bỏ đối tác.")
                    st.rerun()
                    
        st.divider()
        
        # 4. GOM CỤM CHUỖI
        st.markdown("### 🔗 Nhận diện & Gom Cụm Chi Nhánh Chuỗi")
        grouped = group_by_parent_chain(filtered_leads)
        for parent, items in grouped.items():
            if parent != "Độc lập / Chưa gom nhóm" and len(items) > 1:
                st.markdown(f"""
                <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 14px; margin-bottom: 10px;">
                    <b style="color: #166534; font-size: 15px;">📦 Chuỗi {parent} — Phát hiện {len(items)} chi nhánh cùng hệ thống</b><br/>
                    <span style="color: #15803d; font-size: 13px;">💡 <b>Khuyến nghị AI:</b> Tiếp cận đàm phán hợp đồng cung ứng tập trung qua <b>Phòng Mua Hàng của {parent}</b>.</span>
                </div>
                """, unsafe_allow_html=True)
                for it in items:
                    st.write(f"- 📍 **{it['name']}**: {it['address']} (Trạng thái: `{it['status']}`)")
    else:
        st.warning("Không tìm thấy đối tác nào phù hợp. Vui lòng thử nới lỏng bộ lọc.")
