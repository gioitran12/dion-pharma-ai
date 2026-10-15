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
    st.markdown("""
    <div style="background: #ffffff; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.05); margin-bottom: 24px;">
        <h3 style="color: #1d4ed8; font-weight: 800; margin: 0 0 8px 0; font-size: 20px; text-transform: uppercase;">
            🎯 B2B PARTNER DISCOVERY & LEAD WORKSPACE
        </h3>
        <p style="color: #475569; font-size: 14px; margin: 0; line-height: 1.6;">
            Hệ thống tự động phát hiện, làm sạch và xếp hạng đối tác phân phối B2B (Nhà thuốc, Shop Mẹ & Bé, Đại lý) 
            dựa trên <b>Mô hình Đánh giá 4 Chiều định lượng</b> (0–100 điểm) và gom cụm chi nhánh chuỗi.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 1. BỐ CỤC CHIA 2 CỘT
    filter_col, stats_col = st.columns([2.5, 1.5])
    
    with filter_col:
        search_keyword = st.text_input("🔍 Tìm kiếm nhanh theo tên, tuyến đường, SĐT hoặc từ khóa:", placeholder="VD: Long Châu, Nguyễn Thị Thập, Canxi, Mẹ bầu...")
        
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
            lead_type = st.selectbox("Loại hình đối tác:", ["Tất cả", "Nhà thuốc tư nhân", "Chuỗi nhà thuốc", "Cửa hàng Mẹ & Bé", "Đại lý phân phối"])
            
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
        <div style="background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%); border-radius: 16px; padding: 22px; color: white; box-shadow: 0 10px 20px rgba(29, 78, 216, 0.25);">
            <div style="font-weight: 800; color: #e0e7ff; font-size: 14px; text-transform: uppercase; margin-bottom: 12px; letter-spacing: 0.5px;">📊 THỐNG KÊ CHIẾN DỊCH B2B</div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
                <span style="color: #bfdbfe; font-size: 14px;">Tổng Lead tìm thấy:</span>
                <span style="font-size: 26px; font-weight: 800; color: #ffffff;">{len(filtered_leads)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
                <span style="color: #bfdbfe; font-size: 14px;">Hạng Ưu Tiên A+:</span>
                <span style="font-size: 22px; font-weight: 800; color: #34d399;">{high_grade_count}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <span style="color: #bfdbfe; font-size: 14px;">Đã Duyệt Tiếp Cận:</span>
                <span style="font-size: 22px; font-weight: 800; color: #67e8f9;">{approved_count}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    
    if filtered_leads:
        df = export_leads_to_dataframe(filtered_leads)
        
        # 2. BẢNG DỮ LIỆU
        st.markdown("### 📋 DANH SÁCH ĐỐI TÁC TIỀM NĂNG")
        st.dataframe(
            df[["Mã Lead", "Tên đơn vị", "Loại hình", "Chuỗi mẹ", "Địa chỉ", "Điện thoại", "Điểm Phù Hợp", "Độ Tin Cậy", "Trạng Thái", "Người Phụ Trách"]],
            use_container_width=True,
            hide_index=True
        )
        
        # Nút xuất file bo tròn kiểu viên thuốc
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Tải Danh Sách Đối Tác (CSV / Excel)",
            data=csv_data,
            file_name="dion_leads_export.csv",
            mime="text/csv"
        )
        
        st.divider()
        
        # 3. CHI TIẾT ĐÁNH GIÁ 4 CHIỀU & THAO TÁC DUYỆT
        st.markdown("### 🔍 HỒ SƠ NĂNG LỰC & PHÊ DUYỆT TIẾP CẬN")
        lead_id_list = [l["lead_id"] for l in filtered_leads]
        selected_id = st.selectbox("Chọn Đối tác để xem chi tiết 4 Chiều Đánh Giá:", lead_id_list, format_func=lambda x: f"{x} - {next((item['name'] for item in filtered_leads if item['lead_id'] == x), '')}")
        
        lead = get_lead_by_id(selected_id)
        if lead:
            status_color = "#10b981" if lead["status"] == "APPROVED" else ("#ef4444" if lead["status"] == "REJECTED" else "#1d4ed8")
            st.markdown(f"""
            <div style="background: #ffffff; border: 2px solid {status_color}; border-radius: 16px; padding: 24px; box-shadow: 0 6px 16px rgba(0,0,0,0.06); margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="margin: 0; color: #0f172a; font-weight: 800; font-size: 22px;">{lead['name']}</h3>
                    <span style="background: {status_color}; color: white; padding: 6px 16px; border-radius: 9999px; font-weight: 700; font-size: 13px;">{lead['status']}</span>
                </div>
                <div style="color: #334155; font-size: 15px; margin-bottom: 12px; line-height: 1.6;">
                    📍 <b>Địa chỉ:</b> {lead['address']} &nbsp;|&nbsp; 
                    📞 <b>Hotline:</b> {lead['phone']} &nbsp;|&nbsp; 
                    ✉️ <b>Email:</b> {lead['email']}
                </div>
                <div style="color: #64748b; font-size: 14px;">
                    🏷️ <b>Danh mục sản phẩm kinh doanh:</b> {', '.join(lead.get('categories', []))}<br/>
                    🔗 <b>Nguồn xác minh công khai:</b> <a href="{lead.get('source_url', '')}" target="_blank" style="color: #1d4ed8; font-weight: 600;">{lead.get('source_url', '')}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 4 Thước đo
            st.markdown("#### 📊 ĐIỂM SỐ ĐÁNH GIÁ 4 CHIỀU:")
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("1. Mức Phù Hợp", f"{lead['fit_score']}/100", f"Hạng {lead['fit_grade']}")
            sc2.metric("2. Độ Tin Cậy Dữ Liệu", f"{lead['trust_score']}/100", lead['trust_level'][:16]+"...")
            sc3.metric("3. Khả Năng Liên Hệ", f"{lead['contact_score']}/100", "Đầy đủ kênh")
            sc4.metric("4. Tín Hiệu Nhu Cầu", f"{lead['intent_score']}/100", "Nhu cầu cao")
            
            st.info(f"💡 **Tín hiệu quan sát thị trường:** {lead['intent_signals']}")
            
            # Thao tác duyệt
            st.markdown("#### 👤 THAO TÁC PHÊ DUYỆT & PHÂN BỔ SALES:")
            act_col1, act_col2, act_col3 = st.columns([1.5, 2, 1.5])
            
            sales_reps = ["Trần Thị Mai (Sales Q7)", "Nguyễn Hoàng Nam (Key Account)", "Lê Văn Hùng (Senior Sales Q1)", "Vũ Minh Tuấn (Hà Nội Lead)"]
            with act_col1:
                if st.button("✅ Phê Duyệt Lead", type="primary", use_container_width=True):
                    update_lead_status(selected_id, "APPROVED")
                    st.success("Đã duyệt thành công!")
                    st.rerun()
            with act_col2:
                rep = st.selectbox("Chọn Sales phụ trách:", sales_reps)
                if st.button("👤 Giao Việc Cho Sales", use_container_width=True):
                    update_lead_status(selected_id, "APPROVED", assigned_to=rep)
                    st.success(f"Đã giao cho {rep}!")
                    st.rerun()
            with act_col3:
                if st.button("❌ Loại Bỏ Lead", use_container_width=True):
                    update_lead_status(selected_id, "REJECTED")
                    st.warning("Đã loại bỏ đối tác.")
                    st.rerun()
                    
        st.divider()
        
        # 4. GOM CỤM CHUỖI
        st.markdown("### 🔗 NHẬN DIỆN & GOM CỤM CHI NHÁNH CHUỖI")
        grouped = group_by_parent_chain(filtered_leads)
        for parent, items in grouped.items():
            if parent != "Độc lập / Chưa gom nhóm" and len(items) > 1:
                st.markdown(f"""
                <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-left: 6px solid #1d4ed8; border-radius: 12px; padding: 18px; margin-bottom: 14px;">
                    <b style="color: #1e40af; font-size: 16px;">📦 CHUỖI {parent.upper()} — PHÁT HIỆN {len(items)} ĐIỂM BÁN CÙNG HỆ THỐNG</b><br/>
                    <span style="color: #1d4ed8; font-size: 14px;">💡 <b>Khuyến nghị AI:</b> Tiếp cận đàm phán hợp đồng cung ứng tập trung qua <b>Phòng Mua Hàng của {parent}</b>.</span>
                </div>
                """, unsafe_allow_html=True)
                for it in items:
                    st.write(f"- 📍 **{it['name']}**: {it['address']} (Trạng thái: `{it['status']}`)")
    else:
        st.warning("Không tìm thấy đối tác nào phù hợp. Vui lòng thử nới lỏng bộ lọc.")
