"""
DION Healthcare AI — Question Understanding & Product Resolution Module
Phân tích câu hỏi, nhận diện sản phẩm/SKU, phân loại ý định (Intent) và đánh giá an toàn y tế.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple, Dict, Any

from modules.chat.enums import ChatIntent, ChatDecision, RiskLevel
from modules.knowledge.repository import BaseKnowledgeRepository
from modules.knowledge.schemas import ProductRecord


# Danh sách từ khóa nhạy cảm y tế (thai kỳ, bệnh nan y, tương tác thuốc)
SENSITIVE_MEDICAL_KEYWORDS: Dict[str, str] = {
    "mang thai": "Phụ nữ mang thai",
    "thai kỳ": "Giai đoạn thai kỳ",
    "có bầu": "Phụ nữ có bầu",
    "bầu bí": "Phụ nữ mang thai",
    "cho con bú": "Phụ nữ đang cho con bú",
    "sơ sinh": "Trẻ sơ sinh",
    "trẻ sơ sinh": "Trẻ sơ sinh",
    "suy gan": "Bệnh lý suy gan",
    "suy thận": "Bệnh lý suy thận",
    "ung thư": "Bệnh nhân ung thư",
    "xạ trị": "Bệnh nhân đang xạ trị",
    "hóa trị": "Bệnh nhân đang hóa trị",
    "đột quỵ": "Tai biến / đột quỵ",
    "tai biến": "Tai biến mạch máu não",
    "tiểu đường nặng": "Bệnh lý tiểu đường nặng",
    "bệnh nền": "Bệnh nền mạn tính",
    "dị ứng nặng": "Dị ứng thuốc / thức ăn nặng",
    "sốc phản vệ": "Tiền sử sốc phản vệ",
    "uống cùng thuốc": "Tương tác thuốc điều trị",
    "uống chung với thuốc": "Tương tác thuốc điều trị",
    "uống chung thuốc": "Tương tác thuốc điều trị",
    "dùng cùng thuốc": "Tương tác thuốc điều trị",
    "dùng chung với thuốc": "Tương tác thuốc điều trị",
    "dùng chung thuốc": "Tương tác thuốc điều trị",
    "uống kèm thuốc": "Tương tác thuốc điều trị",
    "dùng kèm thuốc": "Tương tác thuốc điều trị",
    "thuốc điều trị": "Dùng chung thuốc điều trị đặc trị",
    "thuốc tim": "Thuốc tim mạch đặc trị",
    "thuốc huyết áp": "Thuốc điều trị huyết áp",
    "thuốc tiểu đường": "Thuốc điều trị tiểu đường",
    "kháng sinh": "Dùng chung thuốc kháng sinh",
    "tương tác thuốc": "Nguy cơ tương tác thuốc",
}

# Các cụm từ vi phạm quy định quảng cáo điều trị (Nghị định 342/2025/NĐ-CP)
PROHIBITED_TREATMENT_TERMS: List[str] = [
    "chữa", "điều trị", "trị dứt điểm", "đặc trị", "khỏi hẳn", "kê đơn",
    "chỉ định", "chống chỉ định", "cam kết khỏi", "chữa bệnh", "điều trị dứt điểm",
    "trị dứt", "khỏi bệnh", "thay thế thuốc chữa bệnh"
]

# Các từ khóa chào hỏi thông thường
GREETING_STARTERS: List[str] = [
    "xin chào", "chào bạn", "chào em", "chào ad", "chào bot", "chào dion",
    "hello", "hi", "bạn là ai", "bạn giúp được gì", "dion là gì"
]

# Các từ khóa so sánh sản phẩm
COMPARISON_KEYWORDS: List[str] = [
    "so sánh", "khác nhau", "khác gì", "nên chọn", "nên uống loại nào",
    "uống cùng lúc", "uống chung", "kết hợp", "phân biệt", "loại nào tốt hơn"
]

# Các câu hỏi về sản phẩm nhưng không nêu tên cụ thể (Ambiguous / Cần làm rõ)
AMBIGUOUS_PRODUCT_PATTERNS: List[str] = [
    "sản phẩm uống vào lúc nào", "uống vào thời điểm nào", "uống trước hay sau ăn",
    "mỗi ngày dùng mấy viên", "mỗi ngày uống mấy", "liều dùng như thế nào", "liều lượng thế nào",
    "có tác dụng phụ không", "có tác dụng gì", "công dụng của sản phẩm", "sản phẩm có tốt không",
    "giá bao nhiêu", "cách dùng sản phẩm", "hướng dẫn sử dụng", "uống bao lâu thì ngưng",
    "đối tượng sử dụng là ai", "ai nên dùng sản phẩm này"
]

# Các lĩnh vực hoàn toàn ngoài phạm vi của DION (Off-topic)
OFF_TOPIC_KEYWORDS: List[str] = [
    "thời tiết", "giá vàng", "chứng khoán", "iphone", "điện thoại", "laptop",
    "mỹ phẩm", "kem chống nắng", "son môi", "nước hoa", "collagen", "nhân sâm",
    "đông trùng", "giảm cân", "tăng cân", "bất động sản", "vé máy bay", "bóng đá"
]


@dataclass
class ProductResolutionResult:
    """Kết quả phân giải sản phẩm từ câu hỏi và context."""
    target_sku: Optional[str]
    target_products: List[ProductRecord]
    all_matched_skus: List[str]
    is_explicit_sku: bool
    is_unknown_sku: bool
    is_multi_product: bool
    is_ambiguous: bool
    is_out_of_scope: bool
    clarification_message: Optional[str] = None


# Các từ khóa câu hỏi tổng quan / ưu điểm / đặc điểm nổi bật
OVERVIEW_KEYWORDS: List[str] = [
    "ưu điểm", "ưu điểm nổi bật", "nổi bật", "đặc biệt", "có gì đặc biệt",
    "đặc điểm", "đặc điểm nào", "đặc điểm gì", "đặc tính", "điểm mạnh",
    "giới thiệu", "giới thiệu sản phẩm", "thông tin về", "tổng quan",
    "công dụng gì", "tác dụng gì", "có công dụng gì", "có tác dụng gì",
    "công dụng như thế nào", "tác dụng như thế nào", "giúp ích gì",
    "thành phần gì", "thành phần có gì", "chứa những gì", "hoạt chất gì"
]

# Các từ khóa bệnh lý / triệu chứng chuyên biệt cần căn cứ chính xác (không gộp thành tổng quan)
SPECIFIC_CONDITION_KEYWORDS: Dict[str, str] = {
    "trí nhớ": "cải thiện trí nhớ",
    "não": "tuần hoàn não",
    "hạ sốt": "hạ sốt",
    "giảm sốt": "giảm sốt",
    "sốt": "hạ sốt",
    "đau đầu": "giảm đau đầu",
    "mất ngủ": "chữa mất ngủ",
    "tiêu chảy": "tiêu chảy",
    "mụn": "trị mụn",
    "nám": "mờ nám",
    "trắng da": "làm trắng da",
    "thị lực": "tăng thị lực",
    "mắt": "bổ mắt",
    "khớp": "chữa đau khớp",
    "gan": "bảo vệ gan",
    "thận": "bổ thận",
    "tiểu đường": "hạ đường huyết",
    "huyết áp": "hạ huyết áp",
    "giảm cân": "giảm cân",
    "tăng cân": "tăng cân",
}

# Từ khóa hỏi về giá bán / chính sách bán hàng
PRICING_KEYWORDS: List[str] = [
    "giá", "giá bao nhiêu", "nhiêu tiền", "bao nhiêu tiền", "ưu đãi", "khuyến mãi",
    "giảm giá", "chiết khấu", "chính sách giá", "bảng giá"
]


@dataclass
class QuestionUnderstandingResult:
    """Kết quả hiểu câu hỏi toàn diện."""
    intent: ChatIntent
    decision: Optional[ChatDecision]
    risk_level: RiskLevel
    risk_flags: List[str]
    risk_reason: Optional[str]
    handoff_required: bool
    product_resolution: ProductResolutionResult
    explanation: Optional[str] = None
    direct_answer: Optional[str] = None
    is_overview_query: bool = False
    overview_topic: Optional[str] = None
    specific_unsupported_condition: Optional[str] = None
    has_pricing_query: bool = False
    has_drug_interaction_query: bool = False
    technical_code: Optional[str] = None


class QuestionUnderstandingEngine:
    """
    Bộ máy hiểu câu hỏi, phân giải sản phẩm và đánh giá an toàn y tế cho DION AI Chatbot.
    """

    def __init__(self, repository: BaseKnowledgeRepository):
        self.repo = repository

    def _normalize_text(self, text: str) -> str:
        """Chuẩn hóa văn bản chữ thường và loại bỏ ký tự lạ."""
        t = text.lower().strip()
        # Chuyển các ký tự phân cách thành dấu cách
        t = re.sub(r"[\t\r\n\.,\?!;:/\(\)\[\]\{\}\-\_]", " ", t)
        return " ".join(t.split())

    def resolve_product(
        self,
        query: str,
        requested_sku: Optional[str] = None,
        context_sku: Optional[str] = None,
    ) -> ProductResolutionResult:
        """
        Nhận diện và phân giải sản phẩm/SKU từ câu hỏi và context.
        """
        norm_query = self._normalize_text(query)

        # 1. Nếu có requested_sku cụ thể (từ ChatRequest.product_id)
        if requested_sku and requested_sku.strip() and requested_sku.strip() != "ALL":
            clean_sku = requested_sku.strip()
            prod = self.repo.get_product_by_sku(clean_sku)
            if not prod:
                return ProductResolutionResult(
                    target_sku=clean_sku,
                    target_products=[],
                    all_matched_skus=[clean_sku],
                    is_explicit_sku=True,
                    is_unknown_sku=True,
                    is_multi_product=False,
                    is_ambiguous=False,
                    is_out_of_scope=False,
                    clarification_message=f"Hiện tại không tìm thấy thông tin cho mã sản phẩm '{clean_sku}'."
                )
            return ProductResolutionResult(
                target_sku=clean_sku,
                target_products=[prod],
                all_matched_skus=[clean_sku],
                is_explicit_sku=True,
                is_unknown_sku=False,
                is_multi_product=False,
                is_ambiguous=False,
                is_out_of_scope=False
            )

        # 2. Quét nhận diện sản phẩm theo từ khóa / alias
        matched_skus: List[str] = []

        # D3 keywords:
        d3_keywords = [
            "d3 1000", "d3 1000iu", "d3 drops", "vitamin d3", "d3 nhỏ giọt",
            "d3", "vitamin d", "dion d3"
        ]
        # Cal-Mom keywords:
        cal_keywords = [
            "cal-mom", "calmom", "canxi cal mom", "canxi calmom", "canxi cal-mom",
            "canxi tảo đỏ", "canxi sinh học", "canxi hữu cơ", "lithothamnion",
            "cal mom", "dion cal mom", "canxi bầu"
        ]
        # Fero-Plus keywords:
        fe_keywords = [
            "fero-plus", "feroplus", "fero plus", "fero", "sắt hữu cơ",
            "viên sắt", "sắt bổ máu", "sắt bầu", "acid folic", "quatrefolic",
            "dion fero", "fe folic", "sắt bisglycinate"
        ]

        has_d3 = any(re.search(r"\b" + re.escape(kw) + r"\b", norm_query) for kw in d3_keywords)
        has_cal = any(re.search(r"\b" + re.escape(kw) + r"\b", norm_query) for kw in cal_keywords)
        has_fe = any(re.search(r"\b" + re.escape(kw) + r"\b", norm_query) for kw in fe_keywords)

        # Xử lý trường hợp "canxi" đứng đơn lẻ:
        # Nếu câu hỏi có "hấp thu canxi" hoặc "hấp thụ canxi" mà đang hỏi D3 thì không xem là Cal-Mom
        if "canxi" in norm_query and not has_cal:
            if not ("hấp thu canxi" in norm_query or "hấp thụ canxi" in norm_query or has_d3):
                has_cal = True

        # Xử lý trường hợp "sắt" đứng đơn lẻ:
        if "sắt" in norm_query and not has_fe:
            has_fe = True

        if has_d3:
            matched_skus.append("DION-D3-1000")
        if has_cal:
            matched_skus.append("DION-CAL-MOM")
        if has_fe:
            matched_skus.append("DION-FE-FOLIC")

        # Kế thừa ngữ cảnh nhiều lượt (Multi-turn Context Inheritance)
        has_comp_word = any(cw in norm_query for cw in COMPARISON_KEYWORDS)
        if has_comp_word and len(matched_skus) == 1 and context_sku and context_sku != matched_skus[0]:
            if self.repo.get_product_by_sku(context_sku):
                matched_skus.insert(0, context_sku)

        if not matched_skus and context_sku:
            context_referencing_words = [
                "loại đó", "sản phẩm đó", "thuốc đó", "nó", "loại này", "sản phẩm này", "viên này",
                "loại đó thì sao", "loại đó ra sao", "thế còn loại đó",
                "ngắn hơn", "ngắn gọn hơn", "viết lại", "soạn lại", "rút gọn", "súc tích hơn",
                "chỉnh lại", "tóm tắt", "tóm lược", "dài hơn", "chi tiết hơn",
                "dùng cho ai", "đối tượng nào", "ai dùng", "uống lúc nào", "uống như thế nào",
                "liều dùng", "liều lượng", "cách dùng", "thành phần", "tác dụng gì", "công dụng gì",
                "có tốt không", "uống bao nhiêu", "dùng thế nào", "mấy tuổi", "giá bao nhiêu"
            ]
            if any(crw in norm_query for crw in context_referencing_words):
                if self.repo.get_product_by_sku(context_sku):
                    matched_skus.append(context_sku)

        # 3. Phân loại theo số lượng sản phẩm phát hiện
        if len(matched_skus) > 1:
            # Hai sản phẩm xuất hiện trong cùng câu hỏi
            prods = [self.repo.get_product_by_sku(s) for s in matched_skus if self.repo.get_product_by_sku(s)]
            return ProductResolutionResult(
                target_sku=None,
                target_products=prods,
                all_matched_skus=matched_skus,
                is_explicit_sku=False,
                is_unknown_sku=False,
                is_multi_product=True,
                is_ambiguous=False,
                is_out_of_scope=False
            )

        if len(matched_skus) == 1:
            sku = matched_skus[0]
            prod = self.repo.get_product_by_sku(sku)
            return ProductResolutionResult(
                target_sku=sku,
                target_products=[prod] if prod else [],
                all_matched_skus=matched_skus,
                is_explicit_sku=False,
                is_unknown_sku=False,
                is_multi_product=False,
                is_ambiguous=False,
                is_out_of_scope=False
            )

        # 4. Không phát hiện SKU nào:
        # Kiểm tra xem có phải câu hỏi ngoài phạm vi (Off-topic) không
        if any(re.search(r"\b" + re.escape(kw) + r"\b", norm_query) for kw in OFF_TOPIC_KEYWORDS):
            return ProductResolutionResult(
                target_sku=None,
                target_products=[],
                all_matched_skus=[],
                is_explicit_sku=False,
                is_unknown_sku=False,
                is_multi_product=False,
                is_ambiguous=False,
                is_out_of_scope=True
            )

        # Kiểm tra xem có phải câu hỏi mơ hồ về sản phẩm nhưng không rõ sản phẩm nào không
        is_ambiguous_question = any(pat in norm_query for pat in AMBIGUOUS_PRODUCT_PATTERNS) or (
            any(w in norm_query for w in ["uống", "dùng", "uống thuốc", "tác dụng", "công dụng", "liều lượng", "thành phần"])
            and not any(g in norm_query for g in GREETING_STARTERS)
        )

        if is_ambiguous_question:
            clarification_msg = (
                "Câu hỏi của bạn chưa nêu rõ tên sản phẩm cụ thể. DION hiện có 3 dòng sản phẩm chính đã được phê duyệt:\n"
                "1. 💧 **Vitamin D3 1000IU Drops** (Tăng cường hấp thu Canxi & Photpho, hỗ trợ xương răng chắc khỏe)\n"
                "2. 🌿 **Canxi Hữu Cơ Cal-Mom Plus** (Canxi sinh học từ tảo đỏ Lithothamnion & K2 MK-7, giảm nguy cơ thiếu hụt canxi thai kỳ)\n"
                "3. 🩸 **Viên Sắt Hữu Cơ & Acid Folic Fero-Plus** (Sắt Bisglycinate & Acid Folic hỗ trợ tạo máu, êm dịu dạ dày)\n\n"
                "Vui lòng cho biết bạn đang quan tâm đến sản phẩm nào để được tư vấn chính xác theo hồ sơ công bố đã duyệt."
            )
            return ProductResolutionResult(
                target_sku=None,
                target_products=[],
                all_matched_skus=[],
                is_explicit_sku=False,
                is_unknown_sku=False,
                is_multi_product=False,
                is_ambiguous=True,
                is_out_of_scope=False,
                clarification_message=clarification_msg
            )

        # Mặc định: không xác định được sản phẩm
        return ProductResolutionResult(
            target_sku=None,
            target_products=[],
            all_matched_skus=[],
            is_explicit_sku=False,
            is_unknown_sku=False,
            is_multi_product=False,
            is_ambiguous=False,
            is_out_of_scope=False
        )

    def analyze_question(
        self,
        message: str,
        requested_sku: Optional[str] = None,
        context_sku: Optional[str] = None,
    ) -> QuestionUnderstandingResult:
        """
        Phân tích câu hỏi: Intent, Safety Risk, Product Resolution.
        """
        user_msg = message.strip()
        user_msg_lower = user_msg.lower()
        norm_msg = self._normalize_text(user_msg)

        # 1. KIỂM TRA CHÀO HỎI ĐƠN GIẢN
        # (Nếu chỉ chào hỏi mà không kèm theo câu hỏi bệnh lý/sản phẩm)
        is_greeting_start = any(norm_msg.startswith(gw) for gw in GREETING_STARTERS)
        has_health_query = any(k in norm_msg for k in [
            "uống", "dùng", "bệnh", "tác dụng", "công dụng", "chữa", "trị",
            "canxi", "d3", "sắt", "fero", "bầu", "thai", "giá"
        ])

        if is_greeting_start and not has_health_query and (not requested_sku or requested_sku == "ALL"):
            prod_res = ProductResolutionResult(
                target_sku=None,
                target_products=[],
                all_matched_skus=[],
                is_explicit_sku=False,
                is_unknown_sku=False,
                is_multi_product=False,
                is_ambiguous=False,
                is_out_of_scope=False
            )
            return QuestionUnderstandingResult(
                intent=ChatIntent.GREETING,
                decision=ChatDecision.READY_TO_SEND,
                risk_level=RiskLevel.LOW,
                risk_flags=[],
                risk_reason=None,
                handoff_required=False,
                product_resolution=prod_res,
                direct_answer=(
                    "Xin chào! Tôi là trợ lý AI chuyên môn của hệ thống DION Healthcare AI. "
                    "Tôi có thể hỗ trợ bạn tra cứu công dụng, thành phần và căn cứ pháp lý của các sản phẩm "
                    "DION đã được Cục An toàn thực phẩm phê duyệt. Bạn đang quan tâm đến sản phẩm nào ạ?"
                )
            )

        # 2. KIỂM TRA TỪ CẤM QUẢNG CÁO ĐIỀU TRỊ (Nghị định 342)
        matched_prohibited = [pt for pt in PROHIBITED_TREATMENT_TERMS if pt in norm_msg]
        if matched_prohibited:
            prod_res = self.resolve_product(user_msg, requested_sku, context_sku)
            return QuestionUnderstandingResult(
                intent=ChatIntent.UNKNOWN,
                decision=ChatDecision.BLOCKED,
                risk_level=RiskLevel.MEDIUM,
                risk_flags=["UNVERIFIED_CLINICAL_QUERY", "PROHIBITED_MARKETING_TERM"],
                risk_reason=f"Phát hiện cụm từ cam kết chữa bệnh / điều trị: {', '.join(matched_prohibited)}",
                handoff_required=True,
                product_resolution=prod_res,
                direct_answer=(
                    "Hệ thống DION Healthcare AI từ chối tư vấn công dụng điều trị, chữa bệnh hoặc thông tin y khoa chưa kiểm duyệt theo quy định "
                    "của Nghị định 342/2025/NĐ-CP. Thực phẩm bảo vệ sức khỏe không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh."
                )
            )

        # 3. KIỂM SOÁT AN TOÀN Y TẾ & CHUYỂN TUYẾN DƯỢC SĨ (Thai kỳ, Bệnh nan y, Tương tác)
        matched_sensitive = []
        for kw, desc in SENSITIVE_MEDICAL_KEYWORDS.items():
            if re.search(r"\b" + re.escape(kw) + r"\b", norm_msg):
                matched_sensitive.append((kw, desc))

        has_pricing = any(pk in norm_msg for pk in PRICING_KEYWORDS)
        has_overview = any(ok in norm_msg for ok in OVERVIEW_KEYWORDS)

        if matched_sensitive:
            top_kw, top_desc = matched_sensitive[0]
            prod_res = self.resolve_product(user_msg, requested_sku, context_sku)
            
            # Kiểm tra xem có phải câu hỏi ghép (Compound Query): vừa hỏi công dụng/sản phẩm + giá + tương tác thuốc
            is_compound = bool(prod_res.target_sku and (has_overview or "công dụng" in norm_msg or "tác dụng" in norm_msg))
            
            return QuestionUnderstandingResult(
                intent=ChatIntent.MEDICAL_RISK,
                decision=ChatDecision.HANDOFF_REQUIRED,
                risk_level=RiskLevel.HIGH,
                risk_flags=["SENSITIVE_MEDICAL_ESCALATION"] + (["COMPOUND_INQUIRY"] if is_compound else []),
                risk_reason=f"Phát hiện đối tượng/tình huống nhạy cảm y tế: {top_desc} ({top_kw})",
                handoff_required=True,
                product_resolution=prod_res,
                is_overview_query=is_compound,
                has_pricing_query=has_pricing,
                has_drug_interaction_query=True,
                technical_code="COMPOUND_HEALTH_AND_PRODUCT_RISK" if is_compound else "SENSITIVE_MEDICAL_HANDOFF",
                direct_answer=(
                    f"⚠️ YÊU CẦU CHUYỂN DƯỢC SĨ TƯ VẤN CHUYÊN MÔN:\n"
                    f"Câu hỏi liên quan đến nhóm đối tượng nhạy cảm y tế ({top_kw.upper()}). "
                    "Theo tiêu chuẩn an toàn y dược, trường hợp này cần được Dược sĩ hoặc Bác sĩ có chuyên môn xem xét trực tiếp.\n"
                    "Tuyệt đối KHÔNG tự ý sử dụng hoặc điều chỉnh liều lượng khi chưa có chỉ định của chuyên gia y tế."
                )
            )

        # 4. PHÂN GIẢI SẢN PHẨM
        prod_res = self.resolve_product(user_msg, requested_sku, context_sku)

        # 4a. SKU chỉ định không tồn tại
        if prod_res.is_unknown_sku:
            return QuestionUnderstandingResult(
                intent=ChatIntent.PRODUCT_INFO,
                decision=ChatDecision.INSUFFICIENT_EVIDENCE,
                risk_level=RiskLevel.LOW,
                risk_flags=[],
                risk_reason=None,
                handoff_required=False,
                product_resolution=prod_res,
                direct_answer=(
                    f"Hiện tại không tìm thấy thông tin cho mã sản phẩm '{prod_res.target_sku}'. "
                    "Hệ thống không thể cung cấp câu trả lời khi thiếu dữ liệu sản phẩm đã xác thực."
                )
            )

        # 4b. Câu hỏi ngoài phạm vi (Off-topic)
        if prod_res.is_out_of_scope:
            return QuestionUnderstandingResult(
                intent=ChatIntent.OFF_TOPIC,
                decision=ChatDecision.INSUFFICIENT_EVIDENCE,
                risk_level=RiskLevel.LOW,
                risk_flags=[],
                risk_reason=None,
                handoff_required=False,
                product_resolution=prod_res,
                direct_answer=(
                    "DION Healthcare AI chuyên hỗ trợ tra cứu thông tin y dược và hồ sơ công bố của các sản phẩm "
                    "thuộc danh mục DION (Vitamin D3 Drops, Canxi Cal-Mom Plus, Sắt Fero-Plus). "
                    "Nội dung câu hỏi của bạn hiện nằm ngoài phạm vi danh mục sản phẩm của hệ thống."
                )
            )

        # 4c. Câu hỏi mơ hồ về sản phẩm nhưng không xác định được sản phẩm cụ thể
        if prod_res.is_ambiguous:
            return QuestionUnderstandingResult(
                intent=ChatIntent.PRODUCT_INFO,
                decision=ChatDecision.CLARIFICATION_REQUIRED,
                risk_level=RiskLevel.LOW,
                risk_flags=[],
                risk_reason=None,
                handoff_required=False,
                product_resolution=prod_res,
                direct_answer=prod_res.clarification_message
            )

        # 4d. Hai sản phẩm xuất hiện trong cùng câu hỏi (So sánh hoặc dùng chung)
        if prod_res.is_multi_product:
            has_comp_word = any(cw in norm_msg for cw in COMPARISON_KEYWORDS)
            intent = ChatIntent.PRODUCT_COMPARISON if has_comp_word else ChatIntent.PRODUCT_INFO
            return QuestionUnderstandingResult(
                intent=intent,
                decision=None, # Sẽ tiếp tục vào Claim Retrieval
                risk_level=RiskLevel.LOW,
                risk_flags=[],
                risk_reason=None,
                handoff_required=False,
                product_resolution=prod_res
            )

        # 4e. Một sản phẩm cụ thể đã được xác định
        # Kiểm tra xem câu hỏi có thuộc nhóm bệnh lý / triệu chứng chuyên biệt không có trong hồ sơ không
        detected_unsupported_condition = None
        for cond_kw, cond_desc in SPECIFIC_CONDITION_KEYWORDS.items():
            if re.search(r"\b" + re.escape(cond_kw) + r"\b", norm_msg):
                # Kiểm tra xem từ khóa này có nằm trong claims hợp lệ của sản phẩm không
                # Ví dụ Cal-Mom: xương răng, chuột rút, đau lưng, tảo đỏ
                # Fero: tạo máu, dạ dày, êm bụng
                # D3: xương răng, hấp thu canxi
                sku = prod_res.target_sku or ""
                if sku == "DION-CAL-MOM" and cond_kw in ("khớp", "xương"):
                    continue
                if sku == "DION-D3-1000" and cond_kw in ("khớp", "xương", "răng"):
                    continue
                if sku == "DION-FE-FOLIC" and cond_kw in ("dạ dày", "máu"):
                    continue
                detected_unsupported_condition = cond_desc
                break

        # Kiểm tra xem có phải câu hỏi tổng quan / ưu điểm / đặc điểm nổi bật
        is_overview = False
        overview_type = None
        if not detected_unsupported_condition:
            for okw in OVERVIEW_KEYWORDS:
                if okw in norm_msg:
                    is_overview = True
                    if any(w in okw for w in ["ưu điểm", "nổi bật", "đặc biệt", "đặc điểm", "điểm mạnh"]):
                        overview_type = "HIGHLIGHTS"
                    elif any(w in okw for w in ["giới thiệu", "thông tin", "tổng quan"]):
                        overview_type = "INTRO"
                    elif any(w in okw for w in ["thành phần", "hoạt chất"]):
                        overview_type = "INGREDIENTS"
                    else:
                        overview_type = "GENERAL_USE"
                    break

        return QuestionUnderstandingResult(
            intent=ChatIntent.PRODUCT_INFO,
            decision=None, # Tiếp tục vào Claim Retrieval
            risk_level=RiskLevel.LOW,
            risk_flags=[],
            risk_reason=None,
            handoff_required=False,
            product_resolution=prod_res,
            is_overview_query=is_overview,
            overview_topic=overview_type,
            specific_unsupported_condition=detected_unsupported_condition,
            has_pricing_query=has_pricing,
            technical_code="OVERVIEW_QUERY_DETECTED" if is_overview else ("SPECIFIC_CONDITION_QUERY" if detected_unsupported_condition else "NORMAL_CLAIM_QUERY")
        )
