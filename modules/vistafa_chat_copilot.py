"""
Vistafa Multi-Channel Chat Copilot & Clinical Competitor Engine
Handles Facebook, Zalo, Website, TikTok messaging workflows for VitGarden products.
Strictly adheres to:
1. Four-step conversation rhythm: Tra loi -> Hoi 1 cau -> Sang loc an toan -> Chuyen buoc
2. Zero emoji policy across all generated responses and logs
3. QA Standard TL.CSKH.003
4. Clinical competitor comparison boundaries without disparagement
"""

import json
import os
import re
from typing import Dict, List, Optional, Any

PLAYBOOK_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vistafa_multichannel_chat_playbook.json")

class VistafaChatCopilot:
    _instance = None
    _data = None

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or PLAYBOOK_FILE
        self._load_data()

    def _load_data(self):
        if not os.path.exists(self.data_path):
            self._data = {
                "channel_guidelines": {},
                "rhythm_standard": {},
                "products": {},
                "playbook_entries": [],
                "competitor_matrix": [],
                "qa_standards": []
            }
            return

        with open(self.data_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    def reload(self):
        self._load_data()

    def get_channels(self) -> Dict[str, Any]:
        return self._data.get("channel_guidelines", {})

    def get_products(self) -> Dict[str, Any]:
        return self._data.get("products", {})

    def get_qa_standards(self) -> List[Dict[str, Any]]:
        return self._data.get("qa_standards", [])

    def get_shortcuts(self, product_id: Optional[str] = None) -> List[Dict[str, str]]:
        shortcuts = []
        seen = set()
        for item in self._data.get("playbook_entries", []):
            sc = item.get("shortcut", "").strip()
            if sc and sc not in seen:
                if not product_id or item.get("product_id") == product_id:
                    seen.add(sc)
                    shortcuts.append({
                        "shortcut": sc,
                        "product_id": item.get("product_id"),
                        "product_name": item.get("product_name"),
                        "situation": item.get("situation"),
                        "channel": item.get("channel")
                    })
        return sorted(shortcuts, key=lambda x: x["shortcut"])

    def get_competitor_matrix(self, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        matrix = self._data.get("competitor_matrix", [])
        if product_id:
            return [c for c in matrix if c.get("product_id") == product_id]
        return matrix

    def search_playbook(
        self,
        query: Optional[str] = None,
        product_id: Optional[str] = None,
        channel: Optional[str] = None,
        situation: Optional[str] = None,
        shortcut: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        results = []
        entries = self._data.get("playbook_entries", [])

        q_lower = query.lower().strip() if query else None
        sc_lower = shortcut.lower().strip() if shortcut else None

        for item in entries:
            # Shortcut filter
            if sc_lower:
                if item.get("shortcut", "").lower() != sc_lower:
                    continue

            # Product filter
            if product_id and product_id != "all":
                if item.get("product_id") != product_id:
                    continue

            # Channel filter
            if channel and channel != "all":
                item_ch = item.get("channel", "all")
                if item_ch != "all" and item_ch != channel:
                    continue

            # Situation filter
            if situation and situation != "all":
                if situation.lower() not in item.get("situation", "").lower():
                    continue

            # Keyword query filter
            if q_lower:
                combined_text = (
                    item.get("situation", "") + " " +
                    item.get("opening_message", "") + " " +
                    item.get("followup_question", "") + " " +
                    item.get("handling_notes", "") + " " +
                    item.get("shortcut", "")
                ).lower()
                if q_lower not in combined_text:
                    continue

            results.append(item)
            if len(results) >= limit:
                break

        return results

    def detect_red_flags(self, text: str, customer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Scans inquiry and customer health background for high-risk clinical triggers.
        Returns red flag evaluation with pharmacist escalation requirements.
        """
        flags = []
        text_lower = text.lower()
        profile_lower = json.dumps(customer_profile or {}, ensure_ascii=False).lower()
        combined = text_lower + " " + profile_lower

        # 1. Kidney stones / Hypercalcemia (Risk for Calcium)
        if any(w in combined for w in ["sỏi thận", "soi than", "tăng canxi máu", "tang canxi mau", "vôi hóa thận", "sỏi niệu"]):
            if any(w in combined for w in ["12mm", "10mm", "15mm", "kích thước lớn", "sỏi to", "sỏi đài thận", "sỏi san hô"]):
                flags.append("Phát hiện tiền sử sỏi thận kích thước lớn (12mm) / nguy cơ tắc nghẽn: Chống chỉ định tuyệt đối tự ý bổ sung canxi. Bắt buộc chuyển Dược sĩ lâm sàng tham vấn bác sĩ điều trị.")
            else:
                flags.append("Phát hiện tiền sử sỏi thận / tăng canxi máu: Chống chỉ định tự ý bổ sung canxi liều cao. Bắt buộc chuyển Dược sĩ lâm sàng.")

        # 1b. Calcium Channel Blockers / Antihypertensive drugs (Amlodipine, Nifedipine)
        if any(w in combined for w in ["amlodipine", "nifedipine", "thuốc huyết áp", "thuoc huyet ap", "chẹn kênh canxi", "chen kenh canxi", "huyết áp cao"]):
            flags.append("Khách đang dùng thuốc huyết áp (Amlodipine / chẹn kênh canxi): Cần uống cách thời điểm dùng thuốc ít nhất 1-2 giờ và kiểm soát chức năng thận.")

        # 2. Prescription Sedatives / Antidepressants (Risk for Sleep Well)
        if any(w in combined for w in ["thuốc ngủ", "thuoc ngu", "an thần", "an than", "lexomil", "diazepam", "seduxen", "rotunda", "stilnox", "trầm cảm", "chong tram cam"]):
            flags.append("Khách đang sử dụng thuốc ngủ / an thần kê đơn: Nguy cơ tương tác ức chế thần kinh trung ương. Bắt buộc chuyển Dược sĩ; tuyệt đối không tự ý phối hợp.")

        # 3. Thalassemia / Iron Overload (Risk for Iron)
        if any(w in combined for w in ["thalassemia", "tan máu", "tan mau", "thừa sắt", "thua sat", "ferritin cao"]):
            flags.append("Phát hiện nguy cơ bệnh lý tan máu bẩm sinh (Thalassemia) hoặc thừa sắt: Chống chỉ định bổ sung sắt. Bắt buộc tham vấn bác sĩ điều trị.")

        # 4. Anticoagulants / Blood thinners (Risk for High-Dose Omega-3)
        if any(w in combined for w in ["kháng đông", "khang dong", "chống đông", "warfarin", "aspirin", "clopidogrel", "xarelto", "sắp phẫu thuật", "sap phau thuat"]):
            flags.append("Khách đang dùng thuốc chống đông máu hoặc sắp phẫu thuật: Thận trọng khi bổ sung Omega-3 liều cao (>2000mg) do nguy cơ kéo dài thời gian đông máu.")

        # 5. Dual Iron Risk (FerroActive + Ferro Max / Prenatal)
        if ("ferroactive" in combined and "ferro max" in combined) or ("sắt" in combined and "uống cả 2" in combined):
            flags.append("Cảnh báo dùng song song 2 loại chế phẩm sắt hữu cơ cùng lúc: Nguy cơ ngộ độc sắt đường tiêu hóa. Chỉ chọn duy nhất 1 chế phẩm phù hợp.")

        # 6. Pregnancy / Lactation general screening
        if any(w in combined for w in ["mang thai", "mang bau", "có bầu", "cho con bú", "sau sinh"]):
            if any(w in combined for w in ["sleep well", "ngủ ngon", "melatonin"]):
                flags.append("Phụ nữ mang thai / cho con bú: Chưa có đầy đủ nghiên cứu an toàn về Melatonin cho thai nhi. Khuyến cáo không sử dụng Sleep Well.")

        has_flags = len(flags) > 0
        pharmacist_required = any("Bắt buộc chuyển Dược sĩ" in f or "Chống chỉ định" in f for f in flags)

        return {
            "has_red_flag": has_flags,
            "flags": flags,
            "pharmacist_escalation": pharmacist_required,
            "action_guidance": (
                "CHUYEN DUOC SI LAM SANG: Khong tu y chot don. Giai thich ly do an toan va chuyen cuoc goi/chat sang Duoc si."
                if pharmacist_required else
                ("CANH BAO AN TOAN: Can kiem tra ky lieu dung va huong dan uong dung cach." if has_flags else "AN TOAN: Khong phat hien yeu to nguy co cao.")
            )
        }

    def extract_clinical_profile(self, text: str, current_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Tu dong phan tich va trich xuat do tuoi, benh nen, thuoc dieu tri va san pham quan tam tu tin nhan khach hang.
        """
        import re
        profile = dict(current_profile or {})
        text_lower = text.lower()

        # 1. Trich xuat do tuoi
        age_match = re.search(r'(?:nam nay|năm nay|bac|bác|em|chau|cháu|chi|chị|anh|toi|tôi|cu|cụ)?\s*(\d{1,2})\s*(?:tuoi|tuổi|t\b)', text_lower)
        if not age_match:
            age_match = re.search(r'\b(\d{1,2})\s*(?:tuoi|tuổi)\b', text_lower)
        if age_match:
            try:
                extracted_age = int(age_match.group(1))
                if 1 <= extracted_age <= 120:
                    profile["age"] = extracted_age
            except Exception:
                pass

        # 2. Trich xuat benh nen & thuoc dieu tri
        conditions = []
        if "sỏi" in text_lower or "soi" in text_lower:
            size_match = re.search(r'(?:sỏi|soi)\s*(?:thận|than)?\s*(\d+\s*mm)?', text_lower)
            if size_match and size_match.group(1):
                conditions.append(f"Sỏi thận {size_match.group(1).strip()}")
            else:
                conditions.append("Sỏi thận")

        if "amlodipine" in text_lower:
            conditions.append("Thuốc huyết áp Amlodipine")
        elif "huyết áp" in text_lower or "huyet ap" in text_lower:
            conditions.append("Thuốc điều trị huyết áp")

        if "seduxen" in text_lower or "rotunda" in text_lower or "thuốc ngủ" in text_lower or "thuoc ngu" in text_lower:
            conditions.append("Thuốc ngủ / an thần kê đơn")

        if "tiểu đường" in text_lower or "tieu duong" in text_lower:
            conditions.append("Tiểu đường")

        if "triglycerid" in text_lower or "mỡ máu" in text_lower or "mo mau" in text_lower:
            conditions.append("Mỡ máu cao")

        if "kháng đông" in text_lower or "khang dong" in text_lower or "chống đông" in text_lower or "warfarin" in text_lower or "aspirin" in text_lower:
            conditions.append("Thuốc chống đông máu")

        if conditions:
            profile["notes"] = ", ".join(conditions)
            profile["conditions"] = conditions

        # 3. Nhan dien san pham quan tam
        detected_product = None
        if any(w in text_lower for w in ["canxi", "calcium", "cal-mom", "calmom"]):
            detected_product = "calcium_complex"
        elif any(w in text_lower for w in ["collagen", "nám", "nam", "sạm da", "da sạm", "da sam"]):
            detected_product = "beauty_collagen"
        elif any(w in text_lower for w in ["dầu cá", "dau ca", "omega", "omega3", "mỡ máu"]):
            detected_product = "ultimate_omega3"
        elif any(w in text_lower for w in ["mất ngủ", "mat ngu", "ngủ ngon", "ngu ngon", "sleep", "khó ngủ", "kho ngu", "seduxen"]):
            detected_product = "sleep_well"
        elif any(w in text_lower for w in ["sắt", "sat", "ferro", "thiếu máu", "thieu mau", "thalassemia"]):
            detected_product = "ferro_active"

        # 4. Tom tat Intent
        intent_parts = []
        if detected_product:
            p_name = self.get_products().get(detected_product, {}).get("name", "")
            intent_parts.append(f"Hỏi tư vấn {p_name}")
        if conditions:
            intent_parts.append(f"có {', '.join(conditions)}")
        if profile.get("age"):
            intent_parts.append(f"({profile['age']} tuổi)")

        intent_summary = " ".join(intent_parts) if intent_parts else text[:80]

        return {
            "profile": profile,
            "detected_product": detected_product,
            "intent": intent_summary
        }

    def generate_response(
        self,
        customer_message: str,
        product_id: str,
        channel: str = "facebook",
        customer_profile: Optional[Dict[str, Any]] = None,
        situation_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a compliant 4-step response customized for the target channel.
        Rhythm: Tra loi -> Hoi 1 cau -> Sang loc an toan -> Chuyen buoc
        """
        # Validate channel
        valid_channels = ["facebook", "zalo", "website", "tiktok", "instagram"]
        channel = channel.lower() if channel.lower() in valid_channels else "facebook"

        # Validate product
        products = self.get_products()
        if product_id not in products:
            product_id = "calcium_complex"
        product_info = products[product_id]

        # 1. Run safety gate
        red_flags_info = self.detect_red_flags(customer_message, customer_profile)

        # 2. Detect competitor mention
        comp_matches = self._detect_competitor_match(customer_message, product_id)

        # 3. Detect situation & pick best playbook entry
        matched_entry = self._find_matching_entry(customer_message, product_id, channel, situation_hint, comp_matches)

        # 4. Build 4-step structured content
        four_steps = self._construct_four_steps(
            matched_entry,
            product_info,
            channel,
            red_flags_info,
            comp_matches,
            customer_message
        )

        # 5. Format channel-tailored final message
        full_text, split_msgs = self._format_channel_message(four_steps, channel)

        # 6. Evaluate QA TL.CSKH.003 compliance
        qa_eval = self._evaluate_qa_compliance(full_text, red_flags_info, four_steps)

        # 7. Collect suggested shortcuts
        suggested_sc = self._get_suggested_shortcuts(product_id)

        return {
            "channel": channel,
            "channel_name": self._data.get("channel_guidelines", {}).get(channel, {}).get("name", channel.upper()),
            "product_id": product_id,
            "product_name": product_info.get("name", ""),
            "detected_situation": matched_entry.get("situation", "Tư vấn tổng quát") if matched_entry else "Tư vấn thông tin",
            "shortcut": matched_entry.get("shortcut", "") if matched_entry else "",
            "full_text": full_text,
            "split_messages": split_msgs,
            "four_steps": four_steps,
            "red_flags": red_flags_info,
            "competitor_comparison": comp_matches,
            "suggested_shortcuts": suggested_sc,
            "qa_compliance": qa_eval,
            "source": matched_entry.get("source", "Hồ sơ công bố sản phẩm VitGarden") if matched_entry else "Hồ sơ công bố sản phẩm VitGarden"
        }

    def _detect_competitor_match(self, message: str, product_id: str) -> Optional[Dict[str, Any]]:
        msg_lower = message.lower()
        matrix = self.get_competitor_matrix(product_id)

        for comp in matrix:
            comp_name_lower = comp.get("competitor_name", "").lower()
            q_lower = comp.get("customer_question", "").lower()
            
            # Check key triggers
            triggers = []
            if "corbiere" in comp_name_lower: triggers.extend(["corbiere", "canxi sủi", "sủi"])
            if "carbonate" in comp_name_lower: triggers.extend(["carbonate", "cacbonat", "hàm lượng cao hơn"])
            if "herbalife" in comp_name_lower: triggers.extend(["herbalife", "unicity", "vital proteins", "thương hiệu"])
            if "high_dose" in comp.get("id", ""): triggers.extend(["10000mg", "5000mg", "10.000mg", "hàm lượng cao"])
            if "cheap" in comp.get("id", ""): triggers.extend(["rẻ hơn", "giá rẻ", "hộp to"])
            if "1000mg" in comp.get("id", ""): triggers.extend(["1000mg", "cũng 1000mg"])
            if "natures_bounty" in comp.get("id", ""): triggers.extend(["nature's bounty", "natures bounty", "kẹo ngủ"])
            if "failed_melatonin" in comp.get("id", ""): triggers.extend(["không đỡ", "không hiệu quả", "từng uống melatonin"])
            if "inorganic" in comp.get("id", ""): triggers.extend(["sắt viên", "sắt sulfate", "hiệu thuốc rẻ"])
            if "ferro_max" in comp.get("id", ""): triggers.extend(["ferro max", "folic", "b12"])

            if any(t in msg_lower for t in triggers):
                return comp

        # Generic competitor keywords
        if any(w in msg_lower for w in ["bên kia", "loại khác", "hãng khác", "sản phẩm khác", "so với"]):
            if matrix:
                return matrix[0]
        return None

    def _find_matching_entry(
        self,
        message: str,
        product_id: str,
        channel: str,
        situation_hint: Optional[str],
        comp_matches: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        entries = self.search_playbook(product_id=product_id, channel=channel)
        if not entries:
            entries = self.search_playbook(product_id=product_id)

        msg_lower = message.lower()

        # If situation hint provided, match situation directly
        if situation_hint:
            for e in entries:
                if situation_hint.lower() in e.get("situation", "").lower():
                    return e

        # If competitor matched, look for competitor entry
        if comp_matches:
            for e in entries:
                if "so sánh" in e.get("situation", "").lower() or "đối thủ" in e.get("situation", "").lower() or "/sosanh" in e.get("shortcut", ""):
                    return e

        # Match by keywords
        keyword_situation_map = [
            (["giá bao nhiêu", "nhiêu tiền", "bao nhiêu một hộp", "báo giá", "chi phí"], "Hỏi giá"),
            (["công dụng", "tác dụng gì", "dùng để làm gì", "có tốt không", "uống có tác dụng gì"], "Hỏi công dụng"),
            (["uống thế nào", "cách dùng", "ngày mấy viên", "uống lúc nào", "uống trước hay sau ăn"], "Hỏi cách dùng"),
            (["ai dùng được", "đối tượng", "bao nhiêu tuổi", "mẹ bầu", "trẻ em"], "Hỏi ai dùng được"),
            (["đắt thế", "giá cao", "bớt không", "giảm giá", "sao đắt vậy", "cân nhắc"], "Chê giá cao"),
            (["đặt hàng", "mua 1 hộp", "lấy 2 hộp", "ship về", "giao cho anh", "chốt đơn"], "Chốt đơn"),
            (["thành phần", "chứa gì", "có những chất gì", "hàm lượng"], "Hỏi thành phần"),
            (["tác dụng phụ", "có an toàn không", "có bị nóng không", "có táo bón không", "sợ đau dạ dày"], "Sợ tác dụng phụ"),
            (["hỏi vợ", "hỏi chồng", "hỏi mẹ", "hỏi ý kiến"], "Muốn hỏi người thân"),
            (["đang dùng loại khác", "đang uống", "ở nhà đang có"], "Đang dùng sản phẩm khác")
        ]

        for keywords, sit_name in keyword_situation_map:
            if any(k in msg_lower for k in keywords):
                for e in entries:
                    if sit_name.lower() in e.get("situation", "").lower():
                        return e

        # Return first entry as fallback
        return entries[0] if entries else None

    def _construct_four_steps(
        self,
        entry: Optional[Dict[str, Any]],
        product_info: Dict[str, Any],
        channel: str,
        red_flags_info: Dict[str, Any],
        comp_matches: Optional[Dict[str, Any]],
        message: str
    ) -> Dict[str, str]:
        # Step 1: Trả lời trực diện
        if red_flags_info.get("pharmacist_escalation"):
            if "sỏi" in message.lower() or "soi" in message.lower():
                size_txt = " (12mm)" if "12mm" in message.lower() else ""
                step1 = (
                    f"Dạ Vistafa xin kính chào bác ạ! Về băn khoăn bổ sung canxi khi bác có sỏi thận{size_txt} và đang uống thuốc huyết áp Amlodipine: "
                    "Vistafa xin phép KHÔNG hướng dẫn tự ý mua dùng canxi ngay lúc này vì sỏi thận kích thước lớn là trường hợp chống chỉ định tự ý bổ sung canxi khi chưa có chỉ định của bác sĩ chuyên khoa Thận - Tiết niệu ạ."
                )
            elif any(w in message.lower() for w in ["thuốc ngủ", "seduxen", "rotunda", "an thần"]):
                step1 = (
                    "Dạ Vistafa xin ghi nhận thông tin của bác ạ! Khi bác đang sử dụng thuốc an thần/thuốc ngủ kê đơn (như Seduxen, Rotunda), "
                    "Vistafa tuyệt đối không hướng dẫn tự ý phối hợp thêm viên uống thảo dược để tránh nguy cơ ức chế quá mức thần kinh trung ương ạ."
                )
            elif comp_matches:
                step1 = comp_matches.get("recommended_reply", entry.get("opening_message", "") if entry else "")
            elif entry:
                step1 = entry.get("opening_message", f"Dạ {product_info.get('name')} là thực phẩm bảo vệ sức khỏe chính hãng bên em ạ.")
            else:
                step1 = (
                    f"Dạ Vistafa xin ghi nhận thông tin của anh/chị về sản phẩm {product_info.get('name')}. "
                    "Tuy nhiên, qua trao đổi em nhận thấy tình trạng sức khỏe / đơn thuốc của mình có yếu tố y khoa đặc biệt cần được đánh giá chuyên môn kỹ lưỡng trước khi sử dụng ạ."
                )
        elif comp_matches:
            step1 = comp_matches.get("recommended_reply", entry.get("opening_message", "") if entry else "")
        elif entry:
            step1 = entry.get("opening_message", f"Dạ {product_info.get('name')} là thực phẩm bảo vệ sức khỏe chính hãng bên em ạ.")
        else:
            step1 = f"Dạ {product_info.get('name')} hiện đang được phân phối chính hãng bởi Vistafa ạ."

        # Step 2: Hỏi 1 câu khai thác
        if red_flags_info.get("pharmacist_escalation"):
            if "sỏi" in message.lower() or "soi" in message.lower():
                step2 = "Bác cho cháu hỏi thêm bác đã siêu âm kiểm tra kích thước sỏi thận gần đây nhất là khi nào, và bác sĩ điều trị huyết áp có lưu ý xét nghiệm canxi niệu hoặc canxi máu không ạ?"
            elif any(w in message.lower() for w in ["thuốc ngủ", "seduxen", "rotunda", "an thần"]):
                step2 = "Bác cho cháu hỏi thêm đơn thuốc Seduxen bác đang uống được bác sĩ kê từ bao giờ và hiện tại liều dùng mỗi tối như thế nào ạ?"
            elif comp_matches:
                step2 = comp_matches.get("counter_question", "Anh/chị ưu tiên tiêu chí nào nhất khi so sánh ạ?")
            elif entry and entry.get("followup_question"):
                step2 = entry.get("followup_question", "Anh/chị đang quan tâm sử dụng cho mình hay cho người thân ạ?")
            else:
                step2 = "Anh/chị đang có nhu cầu sử dụng cho độ tuổi nào và có vấn đề sức khỏe cụ thể nào không ạ?"
        elif comp_matches:
            step2 = comp_matches.get("counter_question", "Anh/chị ưu tiên tiêu chí nào nhất khi so sánh ạ?")
        elif entry and entry.get("followup_question"):
            step2 = entry.get("followup_question", "Anh/chị đang quan tâm sử dụng cho mình hay cho người thân ạ?")
        else:
            step2 = "Anh/chị đang có nhu cầu sử dụng cho độ tuổi nào và có vấn đề sức khỏe cụ thể nào không ạ?"

        # Step 3: Sàng lọc an toàn / Red flag
        if red_flags_info.get("has_red_flag"):
            flags_summary = " | ".join(red_flags_info["flags"])
            step3 = f"[CANH BAO Y KHOA]: {flags_summary}"
        elif entry and entry.get("red_flag"):
            step3 = f"Lưu ý an toàn: {entry.get('red_flag')}"
        else:
            step3 = "Lưu ý an toàn: Kiểm tra tiền sử dị ứng, phụ nữ có thai/cho con bú và thuốc điều trị đang dùng trước khi hướng dẫn liều."

        # Step 4: Chuyển bước chốt hành động
        if red_flags_info.get("pharmacist_escalation"):
            if "bác" in message.lower() or "bac" in message.lower():
                step4 = "Cháu xin phép ghi nhận thông tin và chuyển ngay hồ sơ của bác sang Dược sĩ lâm sàng phụ trách để gọi điện tư vấn phác đồ an toàn nhất cho bác ạ."
            elif channel == "zalo":
                step4 = "Em xin phép chuyển ngay thông tin đến Dược sĩ phụ trách chuyên môn qua Zalo để xem đơn và tư vấn an toàn nhất cho mình nhé ạ."
            elif channel == "website":
                step4 = "Anh/chị vui lòng để lại Số điện thoại hoặc kết nối Zalo để Dược sĩ lâm sàng liên hệ tư vấn chuyên sâu ngay ạ."
            elif channel == "tiktok":
                step4 = "Anh/chị nhắn tin vào Inbox để Dược sĩ chuyên môn hỗ trợ trực tiếp an toàn cho mình nhé ạ!"
            elif channel == "instagram":
                step4 = "Bạn cho mình xin SĐT hoặc nhắn qua Zalo/Direct để Dược sĩ lâm sàng liên hệ tư vấn chuyên sâu an toàn nhất nhé ạ."
            else: # facebook
                step4 = "Anh/chị cho em xin Số điện thoại để em chuyển Dược sĩ lâm sàng bên em liên hệ tư vấn riêng an toàn nhất cho mình nhé ạ."
        elif comp_matches:
            if channel == "zalo":
                step4 = "Nếu tiện, anh/chị chụp ảnh bảng thành phần sản phẩm đang so gửi qua Zalo để em đối chiếu chi tiết từng chỉ số giúp mình ạ."
            elif channel == "tiktok":
                step4 = "Anh/chị nhắn tin vào Inbox em gửi bảng so sánh chi tiết đối chiếu thành phần nhé ạ!"
            elif channel == "instagram":
                step4 = "Bạn nhắn qua Direct Message (DM) hoặc để lại SĐT em gửi bảng phân tích thành phần đối chiếu chi tiết nhé ạ."
            else:
                step4 = comp_matches.get("next_step", "Anh/chị gửi em ảnh nhãn để em đối chiếu cùng đơn vị liều giúp mình nhé ạ.")
        elif entry and entry.get("transition_action"):
            step4 = entry.get("transition_action")
        else:
            if channel == "zalo":
                step4 = "Em gửi phiếu tiếp nhận công bố và ảnh nhãn qua Zalo để anh/chị xem chi tiết nhé ạ."
            elif channel == "website":
                step4 = "Anh/chị để lại SĐT hoặc kết nối Zalo để em gửi tài liệu hướng dẫn và ưu đãi tốt nhất ạ."
            elif channel == "tiktok":
                step4 = "Nhấn vào Inbox để em tư vấn kỹ hơn nhé ạ!"
            elif channel == "instagram":
                step4 = "Bạn nhắn tin qua Direct Message (DM) hoặc để lại SĐT để em tư vấn liệu trình phù hợp nhất nhé ạ."
            else:
                step4 = "Anh/chị cho em xin SĐT để em tư vấn liệu trình phù hợp nhất nhé ạ."

        return {
            "step_1_direct_answer": step1,
            "step_2_followup_question": step2,
            "step_3_safety_gate": step3,
            "step_4_action_cta": step4
        }

    def _format_channel_message(self, four_steps: Dict[str, str], channel: str) -> (str, List[str]):
        s1 = four_steps["step_1_direct_answer"]
        s2 = four_steps["step_2_followup_question"]
        s4 = four_steps["step_4_action_cta"]

        if channel == "facebook":
            # 2-3 short natural bubbles
            bubble1 = s1
            bubble2 = f"{s2}\n{s4}"
            full_text = f"{bubble1}\n\n{bubble2}"
            split_msgs = [bubble1, bubble2]

        elif channel == "zalo":
            # Structured, professional, official
            full_text = f"{s1}\n\n{s2}\n\n{s4}"
            split_msgs = [full_text]

        elif channel == "website":
            # Fast, direct, qualified
            full_text = f"{s1} {s2}\n{s4}"
            split_msgs = [full_text]

        elif channel == "instagram":
            # Instagram Direct Message (Pancake Omni-channel sync)
            bubble1 = s1
            bubble2 = f"{s2}\n{s4}"
            full_text = f"{bubble1}\n\n{bubble2}"
            split_msgs = [bubble1, bubble2]

        elif channel == "tiktok":
            # Super concise strictly under 140 chars, no cure claims
            cta = " Nhắn inbox em hỗ trợ nhé ạ!"
            combined = f"{s1} {s2}{cta}"
            if len(combined) > 135:
                # Shorten question if needed
                s2_clean = s2 if len(s2) <= 50 else (s2[:47] + "...")
                avail = 135 - len(s2_clean) - len(cta)
                if avail >= 25:
                    s1_clean = (s1[:avail - 3] + "...") if len(s1) > avail else s1
                else:
                    s1_clean = s1[:20] + "..."
                    s2_clean = s2_clean[:40] + "..."
                full_text = f"{s1_clean} {s2_clean}{cta}"
            else:
                full_text = combined

            if len(full_text) > 140:
                full_text = full_text[:137] + "..."
            split_msgs = [full_text]

        else:
            full_text = f"{s1}\n{s2}\n{s4}"
            split_msgs = [full_text]

        return full_text, split_msgs

    def _evaluate_qa_compliance(
        self,
        full_text: str,
        red_flags_info: Dict[str, Any],
        four_steps: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Evaluates message against Vistafa QA Standard TL.CSKH.003
        """
        score = 100
        notes = []
        text_lower = full_text.lower()

        # Prohibited terms check (cure, 100%, eliminate disease)
        forbidden = ["chữa khỏi", "chua khoi", "dứt điểm", "dut diem", "cam kết 100%", "cam ket 100%", "khỏi hẳn"]
        for bad in forbidden:
            if bad in text_lower:
                score -= 30
                notes.append(f"[VI PHAM QA TL.CSKH.003 TC 08]: Sử dụng từ cam kết y khoa cấm ('{bad}').")

        # Competitor disparagement check
        disparage = ["hàng rác", "kém chất lượng", "độc hại", "lừa đảo", "vô tác dụng"]
        for d in disparage:
            if d in text_lower:
                score -= 30
                notes.append(f"[VI PHAM QA TL.CSKH.003 TC 05/08]: Nói xấu đối thủ cạnh tranh ('{d}').")

        # Greeting check
        if not any(g in text_lower for g in ["dạ", "chào", "vistafa xin"]):
            score -= 10
            notes.append("[LƯU Ý QA TC 01]: Chưa có từ xưng hô / chào hỏi lễ phép ban đầu.")

        # Question rhythm check (Did it ask 1 followup question?)
        if "?" not in full_text and "ạ" not in four_steps.get("step_2_followup_question", ""):
            score -= 15
            notes.append("[LƯU Ý QA TC 07]: Chưa có câu hỏi làm rõ nhu cầu khách hàng theo nhịp chuẩn.")

        # Pharmacist escalation check when red flags present
        if red_flags_info.get("pharmacist_escalation") and "dược sĩ" not in text_lower:
            score -= 40
            notes.append("[VI PHAM NGHIÊM TRỌNG QA TC 07/08]: Có yếu tố Red flag nhưng chưa chuyển Dược sĩ lâm sàng.")

        if not notes:
            notes.append("[DAT CHUAN QA TL.CSKH.003]: Phản hồi tuân thủ đầy đủ nhịp chuẩn 4 bước và an toàn y dược.")

        return {
            "score": max(score, 0),
            "status": "PASS" if score >= 80 else "NEEDS_REVIEW",
            "notes": notes
        }

    def _get_suggested_shortcuts(self, product_id: str) -> List[Dict[str, str]]:
        prefix_map = {
            "calcium_complex": "/calci-",
            "beauty_collagen": "/colp-",
            "ultimate_omega3": "/omega3-",
            "sleep_well": "/sleep-",
            "ferro_active": "/ferro-"
        }
        prefix = prefix_map.get(product_id, "/calci-")
        all_sc = self.get_shortcuts(product_id)
        filtered = [s for s in all_sc if s["shortcut"].startswith(prefix) or "/sosanh" in s["shortcut"]]
        return filtered[:8]

    def get_conversation_manager(self):
        if not hasattr(self, "_conv_manager") or self._conv_manager is None:
            self._conv_manager = LiveConversationManager(self)
        return self._conv_manager


class LiveConversationManager:
    """
    Manages active multi-turn conversations across Facebook, Zalo, Website, TikTok.
    Provides multi-turn context memory, live thread messaging, and pharmacist handoffs.
    """
    def __init__(self, copilot_ref):
        self.copilot = copilot_ref
        self._conversations = {}
        self._init_default_conversations()

    def _init_default_conversations(self):
        from datetime import datetime
        self._conversations = {
            "CONV-FB-01": {
                "id": "CONV-FB-01",
                "customer_name": "Mai Lan",
                "channel": "facebook",
                "channel_label": "[FB] Facebook Messenger",
                "phone": "0912345678",
                "product_id": "beauty_collagen",
                "product_name": "Beauty Collagen Powder",
                "status": "ACTIVE",
                "lead_priority": "HOT",
                "intent": "Hỏi giá & Khảo sát sạm nám do thức khuya",
                "clinical_profile": {"age": 29, "notes": "Thức khuya làm việc văn phòng, da sạm nám khô ráp"},
                "messages": [
                    {"sender": "customer", "text": "Chào shop, mình hay thức khuya làm việc da dạo này sạm nám và khô ráp quá. Sản phẩm Beauty Collagen này giá bao nhiêu một hộp vậy?", "time": "09:15"},
                    {"sender": "agent", "text": "Dạ chào chị Lan ạ! Beauty Collagen Powder bên em hiện có giá niêm yết 240.000đ/hộp 14 gói tiện lợi ạ. Hiện tại chị muốn tập trung cải thiện độ ẩm căng bóng hay giảm nếp nhăn sạm nám trước ạ?\nChị cho em xin SĐT để em tư vấn liệu trình phù hợp nhất nhé ạ.", "time": "09:16"},
                    {"sender": "customer", "text": "Mình muốn mờ thâm sạm và sáng da trước. SĐT mình 0912345678, uống bao lâu thì thấy hiệu quả vậy em?", "time": "09:18"}
                ],
                "updated_at": "2026-10-20 09:18"
            },
            "CONV-ZA-02": {
                "id": "CONV-ZA-02",
                "customer_name": "Phương Thảo",
                "channel": "zalo",
                "channel_label": "[ZALO] Zalo OA",
                "phone": "0988776655",
                "product_id": "calcium_complex",
                "product_name": "VitGarden Calcium Complex",
                "status": "ACTIVE",
                "lead_priority": "HOT",
                "intent": "Tư vấn thai kỳ & So sánh Canxi Corbiere",
                "clinical_profile": {"pregnancy_week": 20, "notes": "Bầu tuần 20, sợ táo bón, đang uống canxi sủi/ống ngọt sợ tiểu đường thai kỳ"},
                "messages": [
                    {"sender": "customer", "text": "Em ơi cho chị hỏi, chị đang bầu 5 tháng (tuần 20) uống Canxi Complex bên em có bị táo bón nóng trong không? Chị đang uống loại canxi ống ngọt quá chị sợ tiểu đường thai kỳ.", "time": "08:45"}
                ],
                "updated_at": "2026-10-20 08:45"
            },
            "CONV-WEB-03": {
                "id": "CONV-WEB-03",
                "customer_name": "Hoàng Nam",
                "channel": "website",
                "channel_label": "[WEB] Website Live Chat",
                "phone": "0903112233",
                "product_id": "ultimate_omega3",
                "product_name": "VitGarden Ultimate Omega 3",
                "status": "ACTIVE",
                "lead_priority": "WARM",
                "intent": "Đối chiếu hàm lượng EPA/DHA vs Dầu cá 1000mg rẻ",
                "clinical_profile": {"age": 45, "notes": "Mỡ máu triglycerid cao, tìm dầu cá nồng độ cao"},
                "messages": [
                    {"sender": "customer", "text": "Tôi thấy ngoài hiệu thuốc hộp dầu cá 1000mg của Mỹ to đùng bán có 300k, sao lọ Ultimate Omega 3 bên bạn đắt thế? Khác nhau cái gì?", "time": "09:30"}
                ],
                "updated_at": "2026-10-20 09:30"
            },
            "CONV-TT-04": {
                "id": "CONV-TT-04",
                "customer_name": "Thu Trang",
                "channel": "tiktok",
                "channel_label": "[TIKTOK] TikTok Shop",
                "phone": "",
                "product_id": "sleep_well",
                "product_name": "VitGarden Sleep Well",
                "status": "ACTIVE",
                "lead_priority": "WARM",
                "intent": "Hỏi cam kết chữa dứt điểm mất ngủ",
                "clinical_profile": {"notes": "Khó ngủ, thức khuya lướt live lúc 23h"},
                "messages": [
                    {"sender": "customer", "text": "Thuốc ngủ Sleep Well này uống 1 hộp có trị dứt điểm mất ngủ kinh niên không shop?", "time": "09:32"}
                ],
                "updated_at": "2026-10-20 09:32"
            },
            "CONV-ESC-05": {
                "id": "CONV-ESC-05",
                "customer_name": "Bác Nguyễn Văn Đức",
                "channel": "zalo",
                "channel_label": "[ZALO] Zalo OA",
                "phone": "0977889900",
                "product_id": "sleep_well",
                "product_name": "VitGarden Sleep Well",
                "status": "REQUIRES_PHARMACIST",
                "lead_priority": "URGENT",
                "intent": "RED FLAG: Đang dùng thuốc an thần Seduxen kê đơn",
                "clinical_profile": {"age": 68, "notes": "Mất ngủ 5 năm, đang uống Seduxen 5mg và Rotunda mỗi tối theo đơn"},
                "messages": [
                    {"sender": "customer", "text": "Bác năm nay 68 tuổi, bị mất ngủ mấy năm nay đang uống viên Seduxen 5mg và Rotunda mỗi tối theo đơn của bác sĩ Bạch Mai. Bác thấy quảng cáo viên Sleep Well thảo dược, bác uống chung hai loại với nhau được không cháu?", "time": "09:35"}
                ],
                "updated_at": "2026-10-20 09:35"
            },
            "PANCAKE-289596-563141": {
                "id": "PANCAKE-289596-563141",
                "pancake_conv_id": "igo_17841436773289596_2369736243563141",
                "customer_name": "fptu_muayclub",
                "channel": "instagram",
                "channel_label": "[IG] Instagram (Pancake Live)",
                "phone": "",
                "product_id": "calcium_complex",
                "product_name": "VitGarden Calcium Complex",
                "status": "ACTIVE",
                "lead_priority": "WARM",
                "intent": "Hỏi canxi và khoáng chất phục hồi sau tập Muay Thái (fptu_muayclub)",
                "clinical_profile": {"notes": "Đồng bộ trực tiếp qua Pancake Open API từ [IG] Instagram (Pancake Live)"},
                "messages": [
                    {"sender": "customer", "text": "Chào shop, mình bên CLB Muay FPTU, bên mình có dòng canxi hữu cơ hay khoáng chất nào phục hồi cơ khớp sau tập không?", "time": "08:30"}
                ],
                "updated_at": "2026-10-16 08:30",
                "pancake_metadata": {
                    "shop_id": 1943149040,
                    "shop_name": "Trần Giỏi",
                    "page_id": "igo_17841436773289596",
                    "conversation_id": "igo_17841436773289596_2369736243563141",
                    "snippet": ""
                }
            },
            "PANCAKE-289596-645747": {
                "id": "PANCAKE-289596-645747",
                "pancake_conv_id": "igo_17841436773289596_1064261806645747",
                "customer_name": "dicao.vn",
                "channel": "instagram",
                "channel_label": "[IG] Instagram (Pancake Live)",
                "phone": "0334896162",
                "product_id": "beauty_collagen",
                "product_name": "Beauty Collagen Powder",
                "status": "ACTIVE",
                "lead_priority": "HOT",
                "intent": "Khách hàng liên hệ từ Instagram Pancake (dicao.vn)",
                "clinical_profile": {"notes": "Đồng bộ trực tiếp qua Pancake Open API từ [IG] Instagram (Pancake Live)"},
                "messages": [
                    {"sender": "agent", "text": "Mình cao 1m72 , 70kg", "time": "13:26"},
                    {"sender": "customer", "text": "Dạ bạn vừa XXL đó ạ", "time": "13:29"},
                    {"sender": "agent", "text": "Có màu xám ko ạ", "time": "13:31"},
                    {"sender": "customer", "text": "Dạ có trắng ,đen, xanh ,hồng thôi ạ", "time": "13:36"},
                    {"sender": "agent", "text": "Hàng ship về đc xem trước khi nhận đúng ko shop", "time": "13:39"},
                    {"sender": "customer", "text": "Dạ không ạ. Shop sẽ gửi đúng mẫu ạ.", "time": "13:40"},
                    {"sender": "agent", "text": "Thế lấy cho e áo size xxl màu đen nha", "time": "13:43"},
                    {"sender": "customer", "text": "Dạ bạn ơi mẫu bạn đặt phải đợi order 3-5 ngày có hàng mới ship được nha, bạn ráng chờ được không ạ", "time": "13:45"},
                    {"sender": "agent", "text": "Thế phải cần 7-9 ngày mới ship về được ạ", "time": "13:46"},
                    {"sender": "customer", "text": "Dạ đúng rồi ạ", "time": "13:47"},
                    {"sender": "agent", "text": "Đợi được ạ", "time": "13:48"},
                    {"sender": "customer", "text": "Bạn cho shop xin thông tin cụ thể bao gồm : Họ Tên + Số Điện Thoại + Địa chỉ cụ thể nha", "time": "13:48"},
                    {"sender": "agent", "text": "Trần Giỏi Tổ 6, kon Dơng, Mang Yang, Gia Lai 0969649841", "time": "13:49"},
                    {"sender": "customer", "text": "Vâng khi nào hàng về mình ib bạn", "time": "13:50"},
                    {"sender": "agent", "text": "Shop đổi số điện thoại của em thành 0334896162 nha", "time": "14:06"},
                    {"sender": "customer", "text": "Shop gửi dịch vụ chuyển phát nhanh GHTK. Đây là phiếu đơn hàng chính thức của bạn, bạn kiểm tra lại giúp shop ạ.", "time": "04:16"},
                    {"sender": "agent", "text": "Em nhận được hàng rồi ạ. Chất đẹp lắm luôn ý.", "time": "14:22"},
                    {"sender": "customer", "text": "Rảnh cho mình xin ảnh feedback bạn nha, cảm ơn bạn đã tin tưởng và ủng hộ shop ạ.", "time": "15:35"},
                    {"sender": "agent", "text": ".", "time": "07:06"}
                ],
                "updated_at": "2026-10-20 07:06",
                "pancake_metadata": {
                    "shop_id": 1943149040,
                    "shop_name": "Trần Giỏi",
                    "page_id": "igo_17841436773289596",
                    "conversation_id": "igo_17841436773289596_1064261806645747",
                    "snippet": "."
                }
            }
        }

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._conversations.values())

    def get_by_id(self, conv_id: str) -> Optional[Dict[str, Any]]:
        return self._conversations.get(conv_id)

    def add_message(self, conv_id: str, sender: str, text: str, copilot: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        from datetime import datetime
        conv = self._conversations.get(conv_id)
        if not conv:
            return None
        now_str = datetime.now().strftime("%H:%M")
        msg_obj = {"sender": sender, "text": text, "time": now_str}
        conv["messages"].append(msg_obj)
        conv["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        if sender == "customer" and copilot:
            extracted = copilot.extract_clinical_profile(text, conv.get("clinical_profile", {}))
            conv["clinical_profile"] = extracted["profile"]
            if extracted.get("detected_product"):
                conv["product_id"] = extracted["detected_product"]
                p_info = copilot.get_products().get(extracted["detected_product"], {})
                conv["product_name"] = p_info.get("name", conv.get("product_name", ""))
            if extracted.get("intent"):
                conv["intent"] = extracted["intent"]

            rf = copilot.detect_red_flags(text, conv.get("clinical_profile", {}))
            if rf.get("pharmacist_escalation"):
                conv["status"] = "REQUIRES_PHARMACIST"
                conv["lead_priority"] = "URGENT"

        return msg_obj

    def escalate_pharmacist(self, conv_id: str, reason: str, notes: str, pharmacist_name: str = "DS. Lâm Sàng Trực Ban") -> Optional[Dict[str, Any]]:
        from datetime import datetime
        conv = self._conversations.get(conv_id)
        if not conv:
            return None
        conv["status"] = "ESCALATED_PHARMACIST"
        conv["lead_priority"] = "URGENT"
        ticket = {
            "ticket_id": f"TICKET-DS-{conv_id}",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "customer_name": conv.get("customer_name"),
            "phone": conv.get("phone"),
            "channel": conv.get("channel"),
            "product_id": conv.get("product_id"),
            "reason": reason,
            "clinical_notes": notes,
            "assigned_pharmacist": pharmacist_name,
            "patient_context": conv.get("clinical_profile", {})
        }
        conv["pharmacist_ticket"] = ticket
        return ticket

    def convert_order(self, conv_id: str, sku: str, quantity: int, delivery_address: str, total_price: str) -> Optional[Dict[str, Any]]:
        from datetime import datetime
        conv = self._conversations.get(conv_id)
        if not conv:
            return None
        conv["status"] = "CONVERTED_ORDER"
        order_info = {
            "order_id": f"ORD-VIT-{conv_id}",
            "sku": sku,
            "quantity": quantity,
            "delivery_address": delivery_address,
            "total_price": total_price,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        conv["order_info"] = order_info
        return order_info


# Global singleton helper
_copilot_instance = None

def get_vistafa_chat_copilot() -> VistafaChatCopilot:
    global _copilot_instance
    if _copilot_instance is None:
        _copilot_instance = VistafaChatCopilot()
    return _copilot_instance

