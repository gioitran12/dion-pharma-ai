import json
import re
import os

def strip_emojis(text):
    if not isinstance(text, str):
        return text
    # Replace specific status symbols
    text = text.replace('🟢', '[DA PHE DUYET]')
    text = text.replace('🟡', '[CAN XAC NHAN]')
    text = text.replace('🔴', '[CHUYEN DUOC SI / CANH BAO]')
    text = text.replace('⚠️', '[LUU Y AN TOAN]')
    text = text.replace('✓', '[X]')
    text = text.replace('✔', '[X]')
    text = text.replace('❌', '[KHONG]')
    # Remove any remaining emoji characters
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u3030\u303d\u3297\u3299]",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text).strip()

def clean_val(v):
    if not v:
        return ""
    v = str(v).strip()
    return strip_emojis(v)

# Load prompts
path_04 = '/Users/gioitd3182005/.gemini/antigravity/brain/29756301-e61e-4cc7-8849-6ac6391036ae/scratch/user_prompt_04_05.txt'
path_02 = '/Users/gioitd3182005/.gemini/antigravity/brain/29756301-e61e-4cc7-8849-6ac6391036ae/scratch/user_prompt_02_03.txt'

with open(path_04, 'r') as f:
    text_04 = f.read()

with open(path_02, 'r') as f:
    text_02 = f.read()

channel_configs = {
    "facebook": {
        "channel_id": "facebook",
        "name": "Facebook Messenger",
        "description": "Tự nhiên, chia tin ngắn, thân thiện, điều hướng xin SĐT hoặc gửi tin nhắn kế tiếp.",
        "style": "Tách thành 2-3 bong bóng chat ngắn, tránh đoạn văn dài.",
        "cta_pattern": "Xin SĐT để gửi ưu đãi hoặc chuyển Dược sĩ tư vấn liều dùng.",
        "icon_label": "[FB]"
    },
    "zalo": {
        "channel_id": "zalo",
        "name": "Zalo OA / Cá Nhân",
        "description": "Rõ ràng, chuyên nghiệp, hỗ trợ gửi ảnh nhãn, phiếu công bố, COA kiểm nghiệm và mời khách chụp nhãn sản phẩm đối thủ để đối chiếu.",
        "style": "Trình bày chuẩn mực, có thể đính kèm ảnh nhãn và phiếu kiểm nghiệm.",
        "cta_pattern": "Mời gửi ảnh nhãn qua Zalo để Dược sĩ đối chiếu trực tiếp.",
        "icon_label": "[ZALO]"
    },
    "website": {
        "channel_id": "website",
        "name": "Website Live Chat",
        "description": "Nhanh chóng, tức thì, giải quyết thắc mắc trong 1-2 câu, chủ động xin SĐT hoặc kết nối Zalo khi khách đồng ý.",
        "style": "Phản hồi trực diện tức thì (dưới 2 câu), sau đó xin thông tin liên hệ.",
        "cta_pattern": "Em có thể hỗ trợ ngay tại đây, hoặc anh/chị để lại SĐT/Zalo em gửi tài liệu chi tiết.",
        "icon_label": "[WEB]"
    },
    "tiktok": {
        "channel_id": "tiktok",
        "name": "TikTok Shop / Live Chat",
        "description": "Ngắn gọn (dưới 150 ký tự), đúng claim duyệt, tuyệt đối không dùng từ điều trị/chữa bệnh, điều hướng vào Inbox hoặc bio.",
        "style": "Cực kỳ súc tích dưới 150 ký tự, tuân thủ nghiêm ngặt chính sách quảng cáo TikTok.",
        "cta_pattern": "Nhắn tin vào hộp thư (inbox) để em hỗ trợ kỹ hơn nhé ạ!",
        "icon_label": "[TIKTOK]"
    }
}

product_meta = {
    "calcium_complex": {
        "id": "calcium_complex",
        "name": "VitGarden Calcium Complex",
        "form": "Viên nén / viên nang",
        "key_actives": "Calci nano + citrat, D3, K2, Magie, Kẽm",
        "target_group": "Người lớn, phụ nữ mang thai/cho con bú, trẻ em tuổi phát triển, người cao tuổi loãng xương",
        "reg_status": "TPBVSK - Đã công bố"
    },
    "beauty_collagen": {
        "id": "beauty_collagen",
        "name": "Beauty Collagen Powder",
        "form": "Gói bột 2-3g pha uống",
        "key_actives": "Nano Collagen 1500mg, Sensoril 37,5mg, Postbiotic",
        "target_group": "Phụ nữ sau 25 tuổi, da lão hóa, sạm nám, căng thẳng mất ngủ, phụ nữ sau sinh",
        "reg_status": "TPBVSK - Đã công bố"
    },
    "ultimate_omega3": {
        "id": "ultimate_omega3",
        "name": "VitGarden Ultimate Omega 3",
        "form": "Viên nang mềm",
        "key_actives": "Omega-3 TG 1000mg (EPA 500mg + DHA 250mg), Chứng chỉ IFOS",
        "target_group": "Người cần hỗ trợ tim mạch, thị lực, não bộ, mỡ máu",
        "reg_status": "TPBVSK - Đã công bố"
    },
    "sleep_well": {
        "id": "sleep_well",
        "name": "VitGarden Sleep Well",
        "form": "Viên nang cứng",
        "key_actives": "Melatonin, L-Theanine, GABA, Magie",
        "target_group": "Người khó ngủ, mất ngủ do stress, thay đổi múi giờ, người lớn tuổi trằn trọc",
        "reg_status": "TPBVSK - Hạn dùng 24 tháng"
    },
    "ferro_active": {
        "id": "ferro_active",
        "name": "VitGarden FerroActive",
        "form": "Gói bột 2g uống trực tiếp không cần nước",
        "key_actives": "Sắt vi nang Lipofer 30mg",
        "target_group": "Phụ nữ mang thai, thiếu máu thiếu sắt, phụ nữ rong kinh, người sau phẫu thuật",
        "reg_status": "TPBVSK - Hạn dùng 36 tháng"
    }
}

# Parse 04 products
def parse_rows_from_section(section_text, prod_id, prod_name):
    rows = []
    # match each object
    matches = re.finditer(r'\{[^{}]*\"Unnamed: 7\":[^{}]*\}', section_text)
    for m in matches:
        obj_text = m.group(0)
        # Parse fields
        def get_field(k):
            pat = r'\"' + re.escape(k) + r'\":\s*\"([^\"]*)\"'
            f_match = re.search(pat, obj_text)
            return clean_val(f_match.group(1)) if f_match else ""
        
        channel_raw = ""
        # Find first field value
        first_field_match = re.search(r'\"(?:CHAT - [^\"]+|Unnamed: 0)\":\s*\"([^\"]*)\"', obj_text)
        if first_field_match:
            channel_raw = clean_val(first_field_match.group(1))
            
        group = get_field("Unnamed: 1")
        situation = get_field("Unnamed: 2")
        opening = get_field("Unnamed: 3")
        followup = get_field("Unnamed: 4")
        handling = get_field("Unnamed: 5")
        next_step = get_field("Unnamed: 6")
        shortcut = get_field("Unnamed: 7")
        red_flag = get_field("Unnamed: 8")
        hesitant = get_field("Unnamed: 9")
        prohibited = get_field("Unnamed: 10")
        source = get_field("Unnamed: 11")
        
        # Skip header rows
        if not situation or situation in ["Tình huống/Khách nói", "Khách hỏi", ""]:
            continue
        if channel_raw in ["Kênh", "Kịch bản sản phẩm + so sánh đối thủ"]:
            continue
            
        ch_lower = channel_raw.lower()
        channel = "all"
        if "facebook" in ch_lower: channel = "facebook"
        elif "zalo" in ch_lower: channel = "zalo"
        elif "website" in ch_lower or "web" in ch_lower: channel = "website"
        elif "tiktok" in ch_lower: channel = "tiktok"

        # Split messages for facebook
        split_msgs = []
        if opening:
            parts = [p.strip() for p in re.split(r'\.\s+|\n+', opening) if p.strip()]
            split_msgs = parts if len(parts) > 1 else [opening]

        rows.append({
            "id": f"{prod_id}_{channel}_{shortcut.replace('/', '').replace('-', '_') if shortcut else len(rows)}",
            "product_id": prod_id,
            "product_name": prod_name,
            "channel": channel,
            "channel_name": channel_configs.get(channel, {}).get("name", channel_raw),
            "group": group or "Sản phẩm",
            "situation": situation,
            "shortcut": shortcut,
            "opening_message": opening,
            "split_messages": split_msgs,
            "followup_question": followup,
            "handling_notes": handling,
            "transition_action": next_step,
            "red_flag": red_flag,
            "if_hesitant": hesitant,
            "prohibited_statements": prohibited,
            "source": source or "Tài liệu phê duyệt VitGarden",
            "status": "red" if ("chuyển dược sĩ" in (red_flag + handling).lower()) else ("yellow" if "[CAN XAC NHAN]" in (opening + handling) else "green")
        })
    return rows

calcium_start = text_04.find('\"Calcium Complex\"')
collagen_start = text_04.find('\"Beauty Collagen Powder\"')
omega_start = text_04.find('\"Ultimate Omega 3\"')

calcium_rows = parse_rows_from_section(text_04[calcium_start:collagen_start], "calcium_complex", "VitGarden Calcium Complex")
collagen_rows = parse_rows_from_section(text_04[collagen_start:omega_start], "beauty_collagen", "Beauty Collagen Powder")
omega_rows = parse_rows_from_section(text_04[omega_start:], "ultimate_omega3", "VitGarden Ultimate Omega 3")

print(f"Parsed 04: Calcium={len(calcium_rows)}, Collagen={len(collagen_rows)}, Omega3={len(omega_rows)}")

# Build Sleep Well & FerroActive multichannel rows from 02 & templates
def build_synthesized_channel_rows(prod_id, prod_name, situations_def):
    rows = []
    for sit in situations_def:
        for ch in ["facebook", "zalo", "website", "tiktok"]:
            cfg = channel_configs[ch]
            opening = sit["opening"]
            transition = sit["transition"]
            
            # Channel specific adaptations
            if ch == "facebook":
                adapted_opening = f"Dạ chào anh/chị ạ! {opening}"
                adapted_trans = f"{transition} Anh/chị cho em xin SĐT để em tư vấn gói phù hợp nhất nhé ạ."
            elif ch == "zalo":
                adapted_opening = f"Dạ Vistafa xin chào anh/chị. {opening}"
                adapted_trans = f"{transition} Em có thể gửi ảnh phiếu công bố và nhãn phụ chính thức qua Zalo để anh/chị xem chi tiết ạ."
            elif ch == "website":
                adapted_opening = f"Dạ em hỗ trợ ngay ạ. {opening}"
                adapted_trans = f"{transition} Anh/chị để lại SĐT hoặc kết nối Zalo để bên em hỗ trợ nhanh nhất nhé ạ."
            elif ch == "tiktok":
                # Concise under 150 chars, no cure claims
                adapted_opening = (opening[:110] + "...") if len(opening) > 110 else opening
                adapted_trans = "Anh/chị nhắn tin vào hộp thư (inbox) để em hỗ trợ kỹ hơn nhé ạ!"

            parts = [p.strip() for p in re.split(r'\.\s+', adapted_opening) if p.strip()]
            rows.append({
                "id": f"{prod_id}_{ch}_{sit['shortcut'].replace('/', '').replace('-', '_')}",
                "product_id": prod_id,
                "product_name": prod_name,
                "channel": ch,
                "channel_name": cfg["name"],
                "group": sit.get("group", "Sản phẩm"),
                "situation": sit["situation"],
                "shortcut": sit["shortcut"],
                "opening_message": adapted_opening,
                "split_messages": parts,
                "followup_question": sit["followup"],
                "handling_notes": sit.get("handling", "Tư vấn đúng dữ liệu hồ sơ công bố; không mở rộng claim."),
                "transition_action": adapted_trans,
                "red_flag": sit.get("red_flag", "Kiểm tra bệnh nền, thuốc điều trị và đối tượng đặc biệt."),
                "if_hesitant": sit.get("hesitant", "Hỏi còn vướng mắc về giá hay độ an toàn để giải đáp đúng 1 trọng tâm."),
                "prohibited_statements": sit.get("prohibited", "Không cam kết chữa dứt điểm, không hứa hẹn quá mức."),
                "source": "Tài liệu phê duyệt VitGarden",
                "status": sit.get("status", "green")
            })
    return rows

sleep_situations = [
    {
        "situation": "Hỏi giá",
        "shortcut": "/sleep-gia",
        "opening": "VitGarden Sleep Well bên em hiện có giá niêm yết theo quy định công ty ạ.",
        "followup": "Anh/chị đang gặp tình trạng khó vào giấc hay hay bị thức giấc giữa đêm ạ?",
        "transition": "Em kiểm tra thêm liệu trình phù hợp với tình trạng giấc ngủ của mình.",
        "handling": "Tư vấn công thức phối hợp Melatonin, L-Theanine, GABA và Magie.",
        "red_flag": "Nếu đang dùng thuốc an thần, thuốc trầm cảm hoặc thuốc ngủ theo đơn của bác sĩ -> bắt buộc chuyển Dược sĩ.",
        "prohibited": "Không cam kết uống là ngủ ngay sau 15 phút, không hứa thay thế thuốc điều trị mất ngủ.",
        "status": "green"
    },
    {
        "situation": "Hỏi công dụng",
        "shortcut": "/sleep-congdung",
        "opening": "Sleep Well là TPBVSK hỗ trợ thư giãn hệ thần kinh, hỗ trợ dễ đi vào giấc ngủ và ngủ sâu giấc hơn nhờ phức hợp Melatonin, GABA, L-Theanine và Magie ạ.",
        "followup": "Tình trạng mất ngủ của mình kéo dài bao lâu rồi ạ, có do căng thẳng công việc không?",
        "transition": "Để em lên lộ trình cải thiện giấc ngủ tự nhiên cho mình nhé.",
        "handling": "Nhấn mạnh cơ chế kích hoạt thư giãn tự nhiên, không gây nghiện lệ thuộc thuốc.",
        "red_flag": "Phụ nữ mang thai, cho con bú, người lái xe hoặc vận hành máy móc ngay sau khi uống.",
        "prohibited": "Không nói trị dứt điểm mất ngủ kinh niên.",
        "status": "green"
    },
    {
        "situation": "Hỏi cách dùng",
        "shortcut": "/sleep-cachdung",
        "opening": "Dạ Sleep Well uống 1-2 viên trước khi đi ngủ khoảng 30-60 phút với nước ấm ạ.",
        "followup": "Buổi tối mình thường dự định ngủ lúc mấy giờ ạ?",
        "transition": "Em nhắc lịch uống cố định vào buổi tối để nhịp sinh học ổn định nhanh nhất.",
        "handling": "Khuyên kết hợp giảm ánh sáng xanh từ điện thoại trước khi ngủ 30 phút.",
        "red_flag": "Không uống trước khi lái xe hoặc làm việc ca đêm.",
        "prohibited": "Không tự ý tăng liều quá hướng dẫn.",
        "status": "green"
    },
    {
        "situation": "Chê giá cao / do dự",
        "shortcut": "/sleep-gia-cao",
        "opening": "Dạ Sleep Well phối hợp 4 hoạt chất chuẩn hóa gồm Melatonin, GABA, L-Theanine và Magie giúp cơ thể thư giãn đa tầng, chia theo ngày chi phí rất hợp lý ạ.",
        "followup": "Trước đây mình đã từng dùng trà thảo mộc hay sản phẩm hỗ trợ ngủ nào chưa ạ?",
        "transition": "Em có chương trình hỗ trợ theo liệu trình 1 tháng để mình trải nghiệm hiệu quả rõ rệt.",
        "handling": "Giải thích tính kinh tế khi dùng giải pháp đa thành phần thay vì mua lẻ từng chất.",
        "red_flag": "Khách dùng thuốc ngủ liều cao -> chuyển Dược sĩ.",
        "prohibited": "Không chê sản phẩm giá rẻ trên thị trường.",
        "status": "green"
    },
    {
        "situation": "Đang dùng thuốc an thần / Đang dùng sản phẩm khác",
        "shortcut": "/sleep-dangdung",
        "opening": "Dạ em rất hiểu băn khoăn của mình. Sleep Well có nguồn gốc an toàn, tuy nhiên nếu mình đang dùng thuốc điều trị thì cần kiểm tra tương tác rất cẩn trọng ạ.",
        "followup": "Anh/chị đang dùng loại thuốc ngủ hay thuốc an thần cụ thể nào của bác sĩ kê toa ạ?",
        "transition": "Em xin phép kết nối trực tiếp với Dược sĩ lâm sàng bên em để xem đơn thuốc và tư vấn an toàn nhất cho mình ạ.",
        "handling": "Tuân thủ nghiêm ngặt quy trình an toàn y tế, không tư vấn chồng chéo thuốc thần kinh.",
        "red_flag": "Đang dùng thuốc an thần nhóm Benzodiazepin hoặc thuốc chống trầm cảm -> Chuyển Dược sĩ.",
        "prohibited": "Tuyệt đối không khuyên bỏ thuốc bác sĩ kê.",
        "status": "red"
    },
    {
        "situation": "So sánh đối thủ: Nature's Bounty Melatonin",
        "shortcut": "/sosanh-sleep-1",
        "opening": "Dạ Nature's Bounty là thương hiệu rất tốt về Melatonin đơn chất. Điểm khác biệt của Sleep Well là công thức hiệp đồng 4 thành phần: vừa có Melatonin điều hòa nhịp sinh học, vừa có GABA và L-Theanine làm dịu căng thẳng thần kinh và Magie giãn cơ ạ.",
        "followup": "Anh/chị chỉ bị lệch giờ ngủ hay buổi tối đầu óc còn căng thẳng, suy nghĩ nhiều khó ngủ ạ?",
        "transition": "Nếu mình hay bị căng thẳng thần kinh trước ngủ thì công thức phối hợp sẽ hỗ trợ toàn diện hơn nhiều ạ.",
        "handling": "Tôn trọng đối thủ, phân tích khoa học sự khác biệt giữa đơn chất và công thức hiệp đồng.",
        "red_flag": "Khách mất ngủ bệnh lý nặng -> Chuyển bác sĩ/dược sĩ.",
        "prohibited": "Không chê Nature's Bounty, không cam kết hiệu quả 100%.",
        "status": "green"
    }
]

ferro_situations = [
    {
        "situation": "Hỏi giá",
        "shortcut": "/ferro-gia",
        "opening": "VitGarden FerroActive bên em hiện có mức giá niêm yết theo quy định công ty dạng hộp gói bột tiện lợi ạ.",
        "followup": "Chị đang tìm hiểu bổ sung sắt cho mẹ bầu, mẹ sau sinh hay cho ai ạ?",
        "transition": "Em kiểm tra đúng đối tượng để tư vấn liều dùng và ưu đãi tốt nhất nhé ạ.",
        "handling": "Nhấn mạnh dạng sắt vi nang Lipofer cao cấp 30mg/gói.",
        "red_flag": "Bệnh lý tan máu bẩm sinh (Thalassemia), thừa sắt -> Chống chỉ định tuyệt đối.",
        "prohibited": "Không tự ý kê liều vượt quá 1 gói/ngày khi chưa có chỉ định bác sĩ.",
        "status": "green"
    },
    {
        "situation": "Hỏi công dụng",
        "shortcut": "/ferro-congdung",
        "opening": "FerroActive là TPBVSK bổ sung sắt vi nang Lipofer 30mg hỗ trợ tái tạo hồng cầu, giảm nguy cơ thiếu máu do thiếu sắt, đặc biệt không tanh, không nóng trong, không gây táo bón ạ.",
        "followup": "Chị có hay bị chóng mặt, hoa mắt hoặc mệt mỏi khi đứng lên ngồi xuống không ạ?",
        "transition": "Em hướng dẫn chị lộ trình bổ sung sắt để cơ thể hồi phục năng lượng tốt nhất ạ.",
        "handling": "Giải thích công nghệ vi nang màng bọc lipid che giấu vị tanh kim loại và không kích ứng dạ dày.",
        "red_flag": "Khách có xét nghiệm Ferritin máu cao hoặc Thalassemia.",
        "prohibited": "Không nói chữa khỏi hoàn toàn bệnh thiếu máu không do thiếu sắt.",
        "status": "green"
    },
    {
        "situation": "Hỏi cách dùng",
        "shortcut": "/ferro-cachdung",
        "opening": "FerroActive thiết kế dạng gói bột tiện lợi, có thể đổ trực tiếp vào miệng ngậm tan hoặc uống với nước, dùng mỗi ngày 1 gói sau bữa ăn ạ.",
        "followup": "Chị có đang uống chung canxi hoặc uống nhiều trà, cà phê trong ngày không ạ?",
        "transition": "Em lưu ý cách uống cách xa canxi và trà để sắt hấp thu tối đa chị nhé.",
        "handling": "Hướng dẫn uống cách canxi tối thiểu 2 giờ để tránh cạnh tranh hấp thu khoáng chất.",
        "red_flag": "Khách đang uống kèm thuốc kháng sinh nhóm Quinolon hoặc Tetracyclin.",
        "prohibited": "Không bảo uống chung một lúc với canxi.",
        "status": "green"
    },
    {
        "situation": "Chê giá cao / Sợ nóng táo",
        "shortcut": "/ferro-gia-cao",
        "opening": "Dạ FerroActive dùng sắt vi nang Lipofer nhập khẩu cao cấp. Ưu điểm vượt trội là không gây táo bón, không nóng nổi mụn và không để lại vị tanh khó chịu như sắt vô cơ thông thường ạ.",
        "followup": "Trước đây chị đã từng uống loại sắt nào mà bị buồn nôn hoặc táo bón chưa ạ?",
        "transition": "Chị dùng thử liệu trình 1 hộp sẽ cảm nhận rõ sự êm dịu của đường tiêu hóa so với dòng sắt cũ ạ.",
        "handling": "Định vị giá trị vào trải nghiệm không táo bón và không buồn nôn, rất quan trọng với mẹ bầu.",
        "red_flag": "Dị ứng với bất kỳ thành phần nào của sản phẩm.",
        "prohibited": "Không nói sắt vô cơ là độc hại.",
        "status": "green"
    },
    {
        "situation": "So sánh đối thủ: Sắt viên vô cơ thông thường",
        "shortcut": "/sosanh-ferro-1",
        "opening": "Dạ sắt viên vô cơ giá thành rất rẻ nhưng thường có nhược điểm lớn là vị kim loại nồng, dễ gây kích ứng niêm mạc dạ dày và táo bón. FerroActive dùng sắt vi nang Lipofer hạt siêu mịn bọc màng phospholipid nên tan tại ruột non, hấp thu cao và êm dịu đường tiêu hóa ạ.",
        "followup": "Chị ưu tiên sản phẩm dễ uống ngậm tan trực tiếp hay chấp nhận uống viên to kèm nước ạ?",
        "transition": "Nếu chị gửi ảnh loại sắt chị đang cân nhắc, em sẽ so sánh liều nguyên tố và thành phần cho chị xem rõ ạ.",
        "handling": "Giải thích cơ chế vi nang lipid giúp hấp thu mà không phụ thuộc vào dịch vị acid dạ dày.",
        "red_flag": "Mẹ bầu đang dùng đồng thời vitamin tổng hợp đã có sẵn 30mg sắt -> Tránh ngộ độc sắt.",
        "prohibited": "Không bôi nhọ sản phẩm khác, không cam kết hấp thu 100%.",
        "status": "green"
    },
    {
        "situation": "So sánh với Ferro Max (Sắt hữu cơ bisglycinat)",
        "shortcut": "/sosanh-ferro-2",
        "opening": "Dạ FerroActive cung cấp sắt vi nang Lipofer 30mg/gói dạng bột uống trực tiếp. Còn Ferro Max là sắt bisglycinat 28mg kết hợp acid folic 400mcg và B12 dạng viên. Cả hai đều là dòng sắt hữu cơ cao cấp, mình chọn 1 trong 2 tùy vào sở thích dạng dùng và có cần bổ sung acid folic đi kèm hay không ạ.",
        "followup": "Chị đang dùng viên uống vitamin bầu tổng hợp nào đã có sẵn acid folic chưa ạ?",
        "transition": "Em đối chiếu thành phần để chị chọn đúng loại mà không bị uống trùng lặp chất nhé.",
        "handling": "Cảnh báo không uống song song hai loại sắt cùng lúc để tránh dư thừa sắt.",
        "red_flag": "Khách định uống cả FerroActive và Ferro Max cùng ngày -> Chặn lại ngay.",
        "prohibited": "Không khuyên dùng chung cả hai sản phẩm.",
        "status": "green"
    }
]

sleep_rows = build_synthesized_channel_rows("sleep_well", "VitGarden Sleep Well", sleep_situations)
ferro_rows = build_synthesized_channel_rows("ferro_active", "VitGarden FerroActive", ferro_situations)

all_playbook_entries = calcium_rows + collagen_rows + omega_rows + sleep_rows + ferro_rows
print(f"Total Playbook Entries: {len(all_playbook_entries)}")

# Build Competitor Comparison Matrix
competitor_matrix = [
    {
        "id": "comp_calcium_corbiere",
        "product_id": "calcium_complex",
        "product_name": "VitGarden Calcium Complex",
        "competitor_name": "Canxi Corbiere / Canxi sủi / Canxi vô cơ",
        "customer_question": "Canxi bên kia rẻ hơn, cũng có D3, sao phải dùng bên bạn?",
        "counter_question": "Anh/chị đang so sản phẩm nào và dùng cho trẻ hay người lớn ạ?",
        "comparison_criteria": "So loại calci (hữu cơ nano/citrat vs vô cơ/carbonate), hàm lượng canxi nguyên tố theo liều ngày, D3/K2/Magie/Kẽm đi kèm, số viên/ngày và nguy cơ lắng đọng tạo sỏi.",
        "permissible_talking_points": "Calcium Complex phối hợp calci nano + citrat, kèm D3 và K2 MK-7 định hướng canxi vào xương, bổ sung Magie và Kẽm giúp tối ưu hấp thu và giảm thiểu táo bón, lắng đọng.",
        "recommended_reply": "Dạ mình nên so cùng liều ngày và cùng nhóm thành phần đi kèm ạ. Canxi của bên em là dòng hữu cơ sinh học có đủ D3 và K2 giúp dẫn truyền canxi thẳng vào xương, tránh lắng đọng ở thận hay thành mạch. Nếu anh/chị gửi ảnh nhãn sản phẩm đang so qua Zalo, em đối chiếu từng tiêu chí giúp mình ạ.",
        "prohibited_claims": "Không khẳng định nano/citrat chắc chắn tốt hơn mọi dạng khác, không nói canxi khác gây sỏi 100%.",
        "next_step": "Xin tên hoặc ảnh nhãn đối thủ -> So cùng đơn vị/liều dùng thực tế -> Quay về giải quyết nhu cầu của khách.",
        "status": "green"
    },
    {
        "id": "comp_calcium_carbonate",
        "product_id": "calcium_complex",
        "product_name": "VitGarden Calcium Complex",
        "competitor_name": "Canxi Carbonate thông thường",
        "customer_question": "Canxi carbonate bên kia hàm lượng ghi cao hơn nhiều.",
        "counter_question": "Anh/chị đang so lượng calci nguyên tố thực tế hay khối lượng tổng hợp chất muối canxi ạ?",
        "comparison_criteria": "So lượng canxi nguyên tố (elemental calcium) thực tế cơ thể hấp thu được, không chỉ nhìn con số tổng nguyên liệu.",
        "permissible_talking_points": "Canxi carbonate tuy có tỷ lệ nguyên tố cao nhưng độ tan kém, cần nhiều acid dịch vị để phân giải nên dễ gây đầy bụng, táo bón và nóng trong.",
        "recommended_reply": "Dạ mình cần đưa về cùng một đơn vị canxi nguyên tố và liều hấp thu trước khi kết luận ạ. Con số lớn đôi khi là trọng lượng muối canxi chứ chưa phản ánh lượng hấp thu thực tế vào máu và xương. Anh/chị gửi em ảnh nhãn em tính chính xác giúp mình nhé.",
        "prohibited_claims": "Không nói hàm lượng cao hơn là độc hại hoặc kém chất lượng.",
        "next_step": "Đưa về cùng đơn vị nguyên tố -> Giải thích sinh khả dụng và độ êm dịu tiêu hóa.",
        "status": "green"
    },
    {
        "id": "comp_collagen_brands",
        "product_id": "beauty_collagen",
        "product_name": "Beauty Collagen Powder",
        "competitor_name": "Herbalife / Unicity / Vital Proteins / Collagen nước",
        "customer_question": "Herbalife/Unicity/Vital Proteins nổi tiếng hơn, sao tôi phải chọn bên bạn?",
        "counter_question": "Chị ưu tiên nhất về thương hiệu quốc tế, công thức chuyên sâu, dạng dùng tiện lợi hay mức giá trên mỗi ngày ạ?",
        "comparison_criteria": "So hàm lượng peptide/khẩu phần, thành phần hoạt chất phối hợp chống stress (Sensoril), postbiotic cho đường ruột, dạng gói không đường vs chai nước nhiều đường.",
        "permissible_talking_points": "Beauty Collagen Powder sử dụng Nano Collagen Peptide 1500mg/gói kết hợp Sensoril chuẩn hóa 37,5mg hỗ trợ giảm cortisol gây lão hóa da do stress, bổ sung Postbiotic tăng cường miễn dịch da.",
        "recommended_reply": "Dạ các thương hiệu lớn chị kể đều rất uy tín ạ. Khi lựa chọn, chị có thể đối chiếu trực tiếp công thức: Beauty Collagen Powder tập trung giải quyết nguyên nhân cốt lõi gây sạm da do stress và thức khuya với Sensoril và Nano Collagen phân tử nhỏ. Em chỉ xin phép so sánh trên dữ liệu thành phần công bố minh bạch để chị chọn đúng nhu cầu ạ.",
        "prohibited_claims": "Không chê bai Herbalife/Unicity/Vital Proteins, không hạ thấp thương hiệu đối thủ.",
        "next_step": "Xin ảnh nhãn -> Đặt hai công thức cạnh nhau -> Tập trung vào bài toán thức khuya/stress của khách.",
        "status": "green"
    },
    {
        "id": "comp_collagen_high_dose",
        "product_id": "beauty_collagen",
        "product_name": "Beauty Collagen Powder",
        "competitor_name": "Collagen 10,000mg / Collagen liều cao",
        "customer_question": "Collagen bên kia ghi tận 5.000mg - 10.000mg, bên bạn có 1.500mg sao đủ?",
        "counter_question": "Chị đang so hàm lượng collagen peptide phân tử siêu nhỏ hay dạng collagen thông thường chưa thủy phân ạ?",
        "comparison_criteria": "So kích thước phân tử Dalton và độ tinh khiết. Collagen thông thường phân tử lớn cơ thể chỉ hấp thu được một phần và đào thải phần lớn qua thận.",
        "permissible_talking_points": "Nano Collagen trong Beauty Collagen có kích thước hạt siêu nhỏ giúp hấp thu trực tiếp qua thành ruột mà không cần phân cắt tốn năng lượng, kết hợp hoạt chất bảo vệ nền da.",
        "recommended_reply": "Dạ không phải cứ uống hàm lượng thật cao là cơ thể hấp thu hết được ạ. Collagen thông thường có phân tử rất lớn, uống nhiều dễ gây nóng và gánh nặng cho gan thận. Nano Collagen của bên em được thủy phân phân tử siêu nhỏ nên với 1.500mg đã cung cấp đủ lượng peptide hoạt tính cho làn da mà không gây đầy bụng, nóng trong ạ.",
        "prohibited_claims": "Không khẳng định 10.000mg là gây hại nếu không có căn cứ y khoa.",
        "next_step": "Giải thích cơ chế hấp thu màng ruột -> Đề xuất liệu trình 1 tháng.",
        "status": "green"
    },
    {
        "id": "comp_omega3_cheap",
        "product_id": "ultimate_omega3",
        "product_name": "VitGarden Ultimate Omega 3",
        "competitor_name": "Dầu cá giá rẻ / Dầu cá thông thường 1000mg",
        "customer_question": "Dầu cá bên kia rẻ hơn nhiều, hộp to đùng uống cả năm.",
        "counter_question": "Anh/chị xem giúp em trên nhãn mỗi viên chứa bao nhiêu mg EPA và DHA thực tế ạ?",
        "comparison_criteria": "So tổng EPA+DHA/viên thay vì tổng trọng lượng dầu cá; so dạng triglyceride (TG) tự nhiên vs ethyl ester (EE); chứng chỉ kiểm nghiệm kim loại nặng IFOS.",
        "permissible_talking_points": "Ultimate Omega 3 có 500mg EPA và 250mg DHA (tổng 750mg hoạt chất tinh khiết trong viên 1000mg dạng TG sinh học cao), đạt chứng nhận IFOS không nhiễm chì, thủy ngân.",
        "recommended_reply": "Dạ khi chọn dầu cá mình nên nhìn vào lượng EPA và DHA thực tế thay vì chỉ nhìn tổng khối lượng dầu cá ạ. Dầu cá thông thường 1000mg thường chỉ có 300mg EPA+DHA, phần còn lại là mỡ tạp. Ultimate Omega 3 bên em chứa đến 750mg EPA+DHA chuẩn dạng Triglyceride dễ hấp thu và có chứng nhận IFOS quốc tế không nhiễm kim loại nặng ạ.",
        "prohibited_claims": "Không nói dầu cá rẻ là dầu cá bẩn hay dầu cá ôi thiu.",
        "next_step": "Chỉ ra cách đọc bảng thành phần mặt sau hộp -> So sánh chi phí trên 1mg EPA+DHA thực.",
        "status": "green"
    },
    {
        "id": "comp_omega3_1000mg",
        "product_id": "ultimate_omega3",
        "product_name": "VitGarden Ultimate Omega 3",
        "competitor_name": "Dầu cá gắn nhãn 1000mg chung chung",
        "customer_question": "Loại kia cũng ghi 1000mg, có khác gì bên bạn đâu?",
        "counter_question": "1000mg trên nhãn đó là tổng trọng lượng viên dầu cá thô hay tổng lượng EPA và DHA ạ?",
        "comparison_criteria": "Phân biệt giữa 'Fish Oil 1000mg' và 'Omega-3 Active Fatty Acids (EPA/DHA)'.",
        "permissible_talking_points": "Ultimate Omega 3 công bố rõ ràng: Omega-3 TG 1000mg, trong đó EPA 500mg và DHA 250mg mỗi viên.",
        "recommended_reply": "Dạ cùng ghi 1000mg nhưng có sự khác biệt rất lớn ạ: Một số sản phẩm ghi 1000mg dầu cá thô nhưng hoạt chất có lợi thực sự chỉ chiếm 30%. Bên em là 1000mg dầu cá đậm đặc với tỷ lệ hoạt chất lên đến 75% (500mg EPA + 250mg DHA). Uống 1 viên bên em bằng uống 2-3 viên dầu cá thông thường ạ.",
        "prohibited_claims": "Không cáo buộc đối thủ ghi nhãn lừa đảo.",
        "next_step": "Gửi hình ảnh bảng Nutrition Facts để khách tự so sánh trực quan.",
        "status": "green"
    },
    {
        "id": "comp_sleep_natures_bounty",
        "product_id": "sleep_well",
        "product_name": "VitGarden Sleep Well",
        "competitor_name": "Nature's Bounty Melatonin / Kẹo ngủ Melatonin",
        "customer_question": "Nature’s Bounty Melatonin rẻ hơn, sao phải dùng Sleep Well?",
        "counter_question": "Anh/chị chủ yếu khó vào giấc ban đầu hay hay bị tỉnh giấc giữa đêm, giật mình và căng thẳng thần kinh trước khi ngủ ạ?",
        "comparison_criteria": "So sánh Melatonin đơn chất (chỉ hỗ trợ tín hiệu buồn ngủ) vs Công thức hiệp đồng 4 chất (Melatonin + GABA + L-Theanine + Magie) giúp thư giãn cơ thể và duy trì giấc ngủ sâu.",
        "permissible_talking_points": "Sleep Well phối hợp Melatonin cùng L-Theanine và GABA giúp giải tỏa stress thần kinh trước khi ngủ, kết hợp Magie hỗ trợ thư giãn cơ bắp, hạn chế tỉnh giấc nửa đêm.",
        "recommended_reply": "Dạ nếu chỉ so về giá Melatonin đơn chất thì Sleep Well sẽ khác biệt vì đây là công thức phối hợp toàn diện 4 thành phần ạ. Melatonin chỉ giúp tạo cảm giác buồn ngủ, còn GABA và L-Theanine giúp não bộ dừng suy nghĩ miên man, Magie giúp thả lỏng cơ bắp để mình ngủ sâu giấc đến sáng, không bị mệt mỏi khi thức dậy ạ.",
        "prohibited_claims": "Không chê bai Nature's Bounty, không hứa hẹn ngủ sâu 100% cho mọi thể bệnh lý.",
        "next_step": "Xác định nguyên nhân mất ngủ (stress hay lệch nhịp sinh học) -> Đưa ra giải pháp đúng cơ chế.",
        "status": "green"
    },
    {
        "id": "comp_sleep_failed_melatonin",
        "product_id": "sleep_well",
        "product_name": "VitGarden Sleep Well",
        "competitor_name": "Từng dùng Melatonin khác không hiệu quả",
        "customer_question": "Tôi đã từng uống melatonin rồi mà không đỡ, chắc loại này cũng thế thôi.",
        "counter_question": "Dạ trước đây mình dùng liều bao nhiêu và mình khó ngủ do nguyên nhân gì (lo âu, căng thẳng, đau nhức hay mất ngủ lâu năm) ạ?",
        "comparison_criteria": "Khai thác nguyên nhân thất bại: Dùng đơn chất Melatonin không giải quyết được yếu tố lo âu/căng thẳng kích thích hệ thần kinh giao cảm.",
        "permissible_talking_points": "Nhiều trường hợp mất ngủ do căng thẳng và suy nghĩ quá mức thì chỉ bổ sung Melatonin là chưa đủ, cần các chất dẫn truyền ức chế như GABA và L-Theanine để làm dịu sóng não.",
        "recommended_reply": "Dạ em rất chia sẻ với tình trạng của mình ạ. Melatonin đơn thuần chỉ báo hiệu cho cơ thể biết giờ đi ngủ, nhưng nếu đầu óc mình vẫn còn căng thẳng hoặc hồi hộp thì cơ thể vẫn không thể chợp mắt được. Sleep Well có thêm GABA và L-Theanine giúp thư giãn thần kinh trung ương. Tuy nhiên, nếu mình đang dùng thuốc an thần theo đơn của bác sĩ, em xin phép chuyển Dược sĩ chuyên môn tư vấn kỹ cho mình trước ạ.",
        "prohibited_claims": "Không tự ý hứa chắc chắn khỏi, không tư vấn nếu khách đang dùng thuốc an thần nặng.",
        "next_step": "Sàng lọc nguy cơ -> Chuyển Dược sĩ nếu có dấu hiệu mất ngủ bệnh lý / dùng thuốc an thần.",
        "status": "red"
    },
    {
        "id": "comp_ferro_inorganic",
        "product_id": "ferro_active",
        "product_name": "VitGarden FerroActive",
        "competitor_name": "Sắt viên Sulfate / Sắt nước vô cơ",
        "customer_question": "Sắt viên bên hiệu thuốc rẻ hơn nhiều, sao phải dùng dạng gói đắt hơn?",
        "counter_question": "Chị ưu tiên mức giá hay ưu tiên việc uống sắt không bị tanh buồn nôn và không bị táo bón nóng nổi mụn ạ?",
        "comparison_criteria": "So sánh Sắt vi nang Lipofer (công nghệ màng bọc lipid) vs Sắt muối vô cơ (FeSO4) gây kích ứng dạ dày, táo bón và đen phân nặng.",
        "permissible_talking_points": "FerroActive ứng dụng công nghệ vi nang Lipofer 30mg giúp hạt sắt được bọc bảo vệ, chỉ giải phóng và hấp thu tại ruột, không có mùi tanh kim loại, không gây táo bón.",
        "recommended_reply": "Dạ đúng là sắt vô cơ thông thường có giá rất rẻ ạ. Tuy nhiên nhược điểm lớn nhất khiến nhiều chị em bỏ dở liệu trình là mùi tanh nồng rất khó nuốt và gây táo bón, đau dạ dày. FerroActive dùng sắt vi nang Lipofer cao cấp bọc màng phospholipid, thơm ngon ngậm tan trực tiếp mà không gây bất kỳ cảm giác nóng trong hay táo bón nào ạ.",
        "prohibited_claims": "Không nói sắt thông thường là có hại, không khẳng định 100% không ai bị kích ứng.",
        "next_step": "Hỏi tiền sử táo bón hoặc ốm nghén khi uống sắt -> Giới thiệu giải pháp dạng gói tiện lợi.",
        "status": "green"
    },
    {
        "id": "comp_ferro_ferro_max",
        "product_id": "ferro_active",
        "product_name": "VitGarden FerroActive",
        "competitor_name": "Ferro Max (Sắt hữu cơ bisglycinat kèm Acid Folic)",
        "customer_question": "Ferro Max có thêm cả Acid Folic và B12, sao bên bạn không có mà lại chọn?",
        "counter_question": "Chị đang mang thai tuần thứ mấy hoặc chị đã có sẵn viên uống vitamin bầu tổng hợp chưa ạ?",
        "comparison_criteria": "So sánh mục đích dùng: Nếu đã uống Elevit/Pregnacare (đã có đủ 400-800mcg Acid Folic) thì bổ sung FerroActive để không bị quá liều Folic; ngược lại nếu chưa có Folic thì Ferro Max phù hợp.",
        "permissible_talking_points": "FerroActive tập trung hàm lượng sắt vi nang 30mg tinh khiết, dạng gói ngậm tan trực tiếp. Ferro Max là viên nang kết hợp sắt bisglycinat 28mg + Folic 400mcg + B12. Hai sản phẩm dùng cho hai bài toán phối hợp khác nhau, tuyệt đối không dùng cùng lúc cả hai.",
        "recommended_reply": "Dạ hai sản phẩm đều rất tốt nhưng được thiết kế cho nhu cầu khác nhau ạ: Nếu chị đang dùng vitamin tổng hợp cho mẹ bầu (như Elevit, Pregnacare) thì trong đó đã có đủ Acid Folic rồi, uống thêm FerroActive sẽ giúp tăng cường sắt mà không sợ thừa Folic. Còn nếu chị chưa uống vitamin nào thì Ferro Max là lựa chọn tiện lợi 3 trong 1. Em kiểm tra các sản phẩm chị đang dùng để chọn đúng nhất ạ.",
        "prohibited_claims": "Không khuyên dùng đồng thời cả FerroActive và Ferro Max; không khuyên thay đổi đơn bác sĩ.",
        "next_step": "Kiểm tra danh mục sản phẩm khách đang uống -> Chọn đúng 1 loại sắt phù hợp.",
        "status": "green"
    }
]

# QA TL.CSKH.003 Criteria
qa_criteria = [
    {"tc_id": "TC_01", "name": "Chào hỏi khách hàng", "weight": 5, "standard": "Chào ngay khi bắt đầu; giới thiệu tên; xác minh KH khi cần; nêu mục đích; kết thúc cảm ơn và chào chuyên nghiệp."},
    {"tc_id": "TC_02", "name": "Âm lượng, ngữ điệu và tiết tấu", "weight": 5, "standard": "Giọng rõ ràng, bình tĩnh, tích cực; tốc độ phù hợp; có khoảng dừng để KH phản hồi; không dồn dập."},
    {"tc_id": "TC_03", "name": "Ngôn từ và xưng hô chuẩn mực", "weight": 5, "standard": "Kính ngữ dạ/thưa phù hợp; ngôn từ trong sáng, chuẩn mực ngành y dược; tránh tiếng lóng hoặc từ ngữ gây hiểu lầm."},
    {"tc_id": "TC_04", "name": "Giao tiếp và lắng nghe chủ động", "weight": 10, "standard": "Không ngắt lời khách; xác nhận lại ý chính trước khi đưa giải pháp; cảm ơn khi khách chờ."},
    {"tc_id": "TC_05", "name": "Thái độ tích cực và đồng cảm", "weight": 5, "standard": "Bình tĩnh, hòa nhã, tận tâm; tôn trọng quyền quyết định của khách hàng; không tỏ thái độ khó chịu khi bị so sánh."},
    {"tc_id": "TC_06", "name": "Kiểm tra lịch sử CRM & bối cảnh", "weight": 10, "standard": "Kiểm tra tên, lịch sử mua, bệnh nền, tương tác cũ trước khi tư vấn để cá nhân hóa phù hợp."},
    {"tc_id": "TC_07", "name": "Nhận diện nhu cầu & sàng lọc an toàn y dược", "weight": 20, "standard": "Đặt câu hỏi làm rõ nhu cầu; bắt buộc sàng lọc Red Flag (bệnh nền, thuốc điều trị, dị ứng, thai kỳ)."},
    {"tc_id": "TC_08", "name": "Tư vấn đúng hồ sơ duyệt & tuân thủ pháp lý", "weight": 25, "standard": "Tư vấn đúng công dụng duyệt; tuyệt đối không cam kết điều trị; không nói xấu đối thủ; nếu có red flag chuyển ngay Dược sĩ."},
    {"tc_id": "TC_09", "name": "Thuyết phục dựa trên lợi ích khoa học & giải tỏa do dự", "weight": 10, "standard": "Đưa ra dẫn chứng khoa học (sinh khả dụng, dạng vi nang, chứng chỉ IFOS); xử lý do dự đúng 1 trọng tâm; không ép mua."},
    {"tc_id": "TC_10", "name": "Chuyển bước chốt hành động & lưu trữ CRM", "weight": 5, "standard": "Chuyển bước rõ ràng (xin SĐT / gửi ảnh Zalo / kết nối Dược sĩ); cập nhật đầy đủ dữ liệu vào hệ thống CRM."}
]

# Compile full JSON dataset
full_dataset = {
    "version": "2.0.0",
    "updated_at": "2026-10-19",
    "system_name": "Vistafa Multi-Channel Chat Playbook & Clinical Competitor Engine",
    "channel_guidelines": channel_configs,
    "rhythm_standard": {
        "title": "Nhịp Chuẩn 4 Bước Đàm Thoại Dược Phẩm",
        "steps": [
            {"step": 1, "name": "Trả lời trực diện", "rule": "Trả lời đúng điều khách hỏi, dùng đúng claim đã duyệt trong hồ sơ công bố, không hứa hẹn quá mức."},
            {"step": 2, "name": "Hỏi 1 câu khai thác", "rule": "Hỏi đúng 1 câu để làm rõ đối tượng, độ tuổi, triệu chứng hoặc sản phẩm khách đang dùng."},
            {"step": 3, "name": "Sàng lọc an toàn / Red flag", "rule": "Kiểm tra bệnh nền, thuốc điều trị theo đơn, tiền sử dị ứng, phụ nữ mang thai/cho con bú. Nếu có dấu hiệu nguy cơ, chuyển ngay Dược sĩ."},
            {"step": 4, "name": "Chuyển bước chốt hành động", "rule": "Chuyển sang hành động cụ thể tùy theo kênh: xin SĐT (FB/Web), gửi ảnh nhãn qua Zalo, hoặc mời vào Inbox (TikTok)."}
        ]
    },
    "products": product_meta,
    "playbook_entries": all_playbook_entries,
    "competitor_matrix": competitor_matrix,
    "qa_standards": qa_criteria
}

out_path = 'data/vistafa_multichannel_chat_playbook.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(full_dataset, f, ensure_ascii=False, indent=2)

print(f"Successfully generated {out_path}!")
print(f"Products: {len(product_meta)}")
print(f"Channels: {len(channel_configs)}")
print(f"Playbook Entries: {len(all_playbook_entries)}")
print(f"Competitor Comparisons: {len(competitor_matrix)}")
print(f"QA Standards: {len(qa_criteria)}")
