# -*- coding: utf-8 -*-
"""
DION Healthcare AI — Pharmacology & Bioavailability Engine
Tính toán, phân tích hóa dược và đối chiếu sinh khả dụng giữa các dạng vi chất y khoa.
"""

from typing import List, Dict, Any, Optional
from modules.research_intelligence.schemas import PharmacologyComparisonItem


class PharmacologyEngine:
    """Động cơ tính toán và so sánh dược lực học & dược động học của các hợp chất vi chất"""

    @staticmethod
    def get_calcium_comparison() -> Dict[str, Any]:
        """
        Bảng đối chiếu toàn diện 3 dạng Canxi phổ biến nhất trên thị trường:
        1. Canxi Tảo Đỏ Lithothamnion (DION Cal-Mom Plus)
        2. Canxi Citrate Tetrahydrate (Hữu cơ tổng hợp)
        3. Canxi Carbonate (Vô cơ đá vôi tinh chế)
        """
        items = [
            PharmacologyComparisonItem(
                compound_name="Canxi Tảo Đỏ Lithothamnion calcareum (Aquamin F)",
                compound_type="Canxi hữu cơ sinh học (Polymorph Calcite + Aragonite) + 72 khoáng vi lượng",
                molecular_formula="CaCO3 sinh học liên kết ma trận tổ ong xốp",
                elemental_percent=32.0,
                solubility_gastric_ph="Hòa tan nhanh trong acid nhẹ (pH 3.0–5.0), diện tích bề mặt tiếp xúc gấp 10 lần đá vôi",
                absorption_mechanism="Vận chuyển tích cực qua kênh TRPV6 & khuếch tán thụ động cạnh tế bào. Giải phóng ion Ca2+ chậm và đều đặn",
                constipation_risk="Cực thấp (<2%)",
                dose_for_standard_need="~1.560 mg muối tảo biển (cung cấp trọn vẹn 500 mg Canxi nguyên chất)",
                clinical_evaluation="Sinh khả dụng cao nhất, duy trì nồng độ Canxi máu ổn định trong 8h, giảm 78-91% chuột rút thai kỳ, không gây lắng cặn sỏi thận.",
                is_dion_form=True
            ),
            PharmacologyComparisonItem(
                compound_name="Canxi Citrate [Ca3(C6H5O7)2 · 4H2O]",
                compound_type="Canxi hữu cơ tổng hợp (Muối Citrate ngậm 4 nước)",
                molecular_formula="Ca3(C6H5O7)2 · 4H2O",
                elemental_percent=21.1,
                solubility_gastric_ph="Hòa tan độc lập với acid dịch vị, hấp thu tốt ngay cả khi đói hoặc ở người dùng thuốc giảm tiết acid dạ dày",
                absorption_mechanism="Hấp thu tốt qua cả đường xuyên tế bào và cạnh tế bào. Không phụ thuộc pH dạ dày",
                constipation_risk="Thấp (4-6%)",
                dose_for_standard_need="~2.370 mg muối citrate (đòi hỏi kích thước viên rất lớn hoặc phải chia 2-3 viên/ngày)",
                clinical_evaluation="Ưu điểm tan tốt ở người giảm toan dịch vị, nhưng nhược điểm là hàm lượng nguyên tố thấp (~21%), viên to hoặc phải uống nhiều viên để đủ liều.",
                is_dion_form=False
            ),
            PharmacologyComparisonItem(
                compound_name="Canxi Carbonate (Đá vôi tinh chế)",
                compound_type="Canxi vô cơ (Dạng muối khoáng)",
                molecular_formula="CaCO3",
                elemental_percent=40.0,
                solubility_gastric_ph="Kém tan trong nước, bắt buộc phải có môi trường acid dịch vị mạnh (pH < 2.0) để phân ly",
                absorption_mechanism="Phụ thuộc acid dạ dày để chuyển thành CaCl2. Khi xuống ruột dễ kết tủa lại thành muối không tan",
                constipation_risk="Rất cao (30-38%)",
                dose_for_standard_need="~1.250 mg muối carbonate (cung cấp 500 mg Canxi nguyên chất)",
                clinical_evaluation="Hàm lượng nguyên tố cao (40%) nhưng sinh khả dụng trung bình, sinh khí CO2 gây đầy hơi, ợ chua và tỷ lệ táo bón thai kỳ rất cao.",
                is_dion_form=False
            )
        ]

        nutritional_context = {
            "maternal_daily_demand": "1.000 – 1.200 mg Canxi nguyên tố / ngày (khuyến cáo Viện Dinh Dưỡng Quốc Gia)",
            "average_dietary_intake": "400 – 600 mg Canxi / ngày từ bữa ăn bình thường của người Việt (cơm, canh, tôm cua cá, sữa)",
            "supplementation_gap": "500 – 600 mg Canxi nguyên tố / ngày (đây là khoảng thiếu hụt thực tế cần bù từ viên uống)",
            "scientific_takeaway": (
                "Nhận định 'hàm lượng canxi nguyên tố thấp ~21% đòi hỏi thai phụ phải uống số lượng viên lớn để đạt 1000-1200mg/ngày' "
                "chỉ đúng về mặt tỷ lệ hóa học nhưng thổi phồng nhu cầu thực tế. Thai phụ đã nhận 400-600mg từ thực phẩm, "
                "do đó chỉ cần bổ sung 500mg Canxi nguyên chất/ngày. Viên Canxi Tảo Đỏ DION Cal-Mom Plus chứa 500mg Canxi sinh học "
                "là liều lượng chuẩn mực tối ưu cho thai kỳ, vừa đủ bù đắp thiếu hụt vừa không gây quá tải thận."
            )
        }

        return {
            "category": "CANXI",
            "title": "Bảng Đối Chiếu Dược Lý & Sinh Khả Dụng Các Dạng Canxi",
            "items": [item.model_dump() for item in items],
            "nutritional_context": nutritional_context
        }

    @staticmethod
    def get_iron_comparison() -> Dict[str, Any]:
        """
        Bảng đối chiếu 3 dạng Sắt phổ biến trong sản phụ khoa:
        1. Sắt Chelate Hữu Cơ Bisglycinate (DION Fero-Plus)
        2. Sắt Vô Cơ Ferrous Sulfate (Chuẩn thường quy truyền thống)
        3. Sắt Hữu Cơ Polymaltose (IPC)
        """
        items = [
            PharmacologyComparisonItem(
                compound_name="Sắt Chelate Hữu Cơ Ferrous Bisglycinate",
                compound_type="Sắt hữu cơ chelate vòng càng (2 phân tử Glycine bao bọc Fe2+)",
                molecular_formula="Fe(C2H4NO2)2",
                elemental_percent=20.0,
                solubility_gastric_ph="Bền vững ở pH dạ dày, tan hoàn toàn tại pH ruột non mà không ion hóa tự do",
                absorption_mechanism="Hấp thu nguyên vẹn qua kênh dipeptide PEPT1, không cạnh tranh với DMT1 và không bị cản trở bởi Canxi, phytate hay polyphenol",
                constipation_risk="Cực thấp (6.8%)",
                dose_for_standard_need="25 mg Sắt nguyên tố (tương đương 1 viên DION Fero-Plus)",
                clinical_evaluation="Sinh khả dụng gấp 2-4 lần sắt vô cơ, hiệu quả tạo máu tương đương liều 50mg Ferrous Sulfate nhưng tỷ lệ tác dụng phụ thấp hơn 4 lần, không tanh, không nóng trong.",
                is_dion_form=True
            ),
            PharmacologyComparisonItem(
                compound_name="Sắt Vô Cơ Ferrous Sulfate",
                compound_type="Sắt muối khoáng vô cơ",
                molecular_formula="FeSO4 · 7H2O",
                elemental_percent=20.0,
                solubility_gastric_ph="Tan trong dịch dạ dày và phân ly ồ ạt thành ion Fe2+ tự do",
                absorption_mechanism="Hấp thu qua kênh kim loại DMT1, cạnh tranh hấp thu trực tiếp với Canxi, Kẽm và bị ức chế mạnh bởi thức ăn",
                constipation_risk="Rất cao (31.4% – 38%)",
                dose_for_standard_need="50 – 60 mg Sắt nguyên tố",
                clinical_evaluation="Gây phản ứng Fenton tạo gốc oxy hóa phá hủy niêm mạc ruột, mùi tanh nồng dễ gây nôn nghén, táo bón nặng và phân đen.",
                is_dion_form=False
            ),
            PharmacologyComparisonItem(
                compound_name="Sắt Hữu Cơ Phức Hợp Iron Polymaltose (IPC)",
                compound_type="Phức hợp Sắt (III) Hydroxyd Polymaltose",
                molecular_formula="Fe(OH)3 · Polymaltose",
                elemental_percent=33.0,
                solubility_gastric_ph="Phức hợp phân tử lớn bền vững, giải phóng chậm",
                absorption_mechanism="Hấp thu qua cơ chế khuếch tán thụ động có kiểm soát",
                constipation_risk="Trung bình (12-16%)",
                dose_for_standard_need="50 mg Sắt nguyên tố",
                clinical_evaluation="Ít kích ứng dạ dày hơn sắt sunfat, nhưng tốc độ phục hồi chỉ số Ferritin máu chậm hơn Sắt Chelate Bisglycinate.",
                is_dion_form=False
            )
        ]

        nutritional_context = {
            "maternal_daily_demand": "30 – 60 mg Sắt nguyên tố / ngày trong thai kỳ (WHO & Bộ Y Tế)",
            "absorption_efficiency_factor": "Sắt Bisglycinate hấp thu ~40-50% trong khi sắt vô cơ chỉ hấp thu ~10-15%",
            "scientific_takeaway": (
                "Do sinh khả dụng vượt trội, 25mg Sắt Bisglycinate trong DION Fero-Plus mang lại lượng sắt thực tế đi vào máu "
                "tương đương với 50-60mg Sắt Sulfate truyền thống, giúp mẹ bầu không cần phải dùng liều sắt quá cao gây quá tải "
                "đường tiêu hóa, không bị táo bón, buồn nôn hay phân đen."
            )
        }

        return {
            "category": "SAT",
            "title": "Bảng Đối Chiếu Dược Lý & Sinh Khả Dụng Các Dạng Sắt",
            "items": [item.model_dump() for item in items],
            "nutritional_context": nutritional_context
        }
