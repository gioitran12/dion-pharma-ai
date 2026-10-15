# DION Healthcare AI — Enterprise Demo Workspace

Ứng dụng Web Demo tương tác (Interactive PoC) giải pháp **Enterprise AI chuyên sâu ngành Dược phẩm & Thực phẩm Bổ sung (TPBS)** được phát triển bởi **Digital Innovation (DION)**.

---

## 🌟 TÍNH NĂNG CHÍNH ĐÃ HOÀN THÀNH

1. **🏛️ Quản lý Claims Sản phẩm (Knowledge Vault):** Phân chia 3 vùng tri thức, tự động phát hiện và khóa Claims đã hết hạn, đính kèm disclaimer bắt buộc theo **Nghị định 342/2025/NĐ-CP**.
2. **🎯 Tìm kiếm Lead B2B (Partner Discovery):** Tra cứu đối tác phân phối (nhà thuốc, mẹ & bé), tính điểm 4 chiều, gom cụm chi nhánh thuộc cùng chuỗi và xuất dữ liệu CSV/Excel.
3. **💬 Trợ lý Bán hàng (Sales Copilot):** RAG Knowledge Grounding tra cứu sản phẩm có trích dẫn số Claim, tự động định tuyến ca nhạy cảm y tế (thai kỳ, bệnh nền) để chuyển Dược sĩ chuyên môn.
4. **✍️ Sản xuất Content Marketing (Compliance Engine):** Soạn thảo bài truyền thông dựa trên Claim hợp lệ, tự động đính kèm disclaimer và quét phát hiện vi phạm từ cấm theo luật quảng cáo y tế.

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY ỨNG DỤNG

### 1. Yêu cầu môi trường
* Python 3.9+ trở lên.

### 2. Cài đặt các thư viện
Mở Terminal tại thư mục dự án và chạy:
```bash
# Tạo môi trường ảo (tùy chọn)
python -m venv venv
source venv/bin/activate  # Trên macOS/Linux
# venv\Scripts\activate   # Trên Windows

# Cài đặt thư viện
pip install -r requirements.txt
```

### 3. Cấu hình API Key (Nếu cần)
Sao chép file `.env.example` thành `.env`:
```bash
cp .env.example .env
```
*(Lưu ý: Ứng dụng đã tích hợp sẵn Mock Data & Logic thông minh, có thể chạy demo đầy đủ tính năng ngay cả khi chưa nạp API Key!)*

### 4. Khởi chạy Web App Demo
Chạy lệnh sau:
```bash
streamlit run app.py
```
Trình duyệt sẽ tự động mở tại địa chỉ: `http://localhost:8501`.

---

## 👥 HƯỚNG DẪN PHỐI HỢP NHÓM 2 NGƯỜI QUA GIT

### Phân chia file:
* **Thành viên A:** Phụ trách `data/products_claims.json`, `data/b2b_leads.json`, `modules/claims_hub.py`, `modules/lead_discovery.py`, `views/tab_claims.py`, `views/tab_leads.py`.
* **Thành viên B:** Phụ trách `data/prohibited_terms.json`, `modules/sales_copilot.py`, `modules/content_generator.py`, `views/tab_copilot.py`, `views/tab_content.py`.

### Quy trình Git cơ bản:
```bash
# Tạo nhánh riêng của mình để làm việc
git checkout -b feature/ten-tinh-nang

# Sau khi sửa xong code:
git add .
git commit -m "feat: mo ta cong viec da lam"
git push origin feature/ten-tinh-nang
```
