import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update subtab buttons
old_subtab_buttons = """                    <button type="button" onclick="setCareSubTab('caresoft')" id="btn-care-sub-caresoft" class="px-3.5 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 bg-corp-800 text-white shadow-xs cursor-pointer">
                        <span class="pointer-events-none">[POC VISTAFA] 1. TIẾP NHẬN LEAD CARESOFT</span>
                        <span id="cs-sub-lead-count" class="px-1.5 py-0.2 rounded-full text-[10px] bg-white/20 font-mono pointer-events-none">0</span>
                    </button>
                    <button type="button" onclick="setCareSubTab('tasks')" id="btn-care-sub-tasks" class="px-3.5 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer">
                        <span class="pointer-events-none">2. CÔNG VIỆC CHĂM SÓC (30 NGÀY)</span>
                        <span id="care-sub-task-count" class="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 font-mono pointer-events-none">0</span>
                    </button>
                    <button type="button" onclick="setCareSubTab('history')" id="btn-care-sub-history" class="px-3.5 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer">
                        <span class="pointer-events-none">3. KHÁCH HÀNG & LỊCH SỬ</span>
                        <span id="care-sub-cust-count" class="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 font-mono pointer-events-none">0</span>
                    </button>
                    <button type="button" onclick="setCareSubTab('sources')" id="btn-care-sub-sources" class="px-3.5 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer">
                        <span class="pointer-events-none">4. NGUỒN DỮ LIỆU</span>
                        <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-100 text-emerald-800 font-mono pointer-events-none">3 Sẵn sàng</span>
                    </button>"""

new_subtab_buttons = """                    <button type="button" onclick="setCareSubTab('caresoft')" id="btn-care-sub-caresoft" class="px-3.5 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 bg-corp-800 text-white shadow-xs cursor-pointer">
                        <span class="pointer-events-none">[POC VISTAFA] 1. TIẾP NHẬN LEAD CARESOFT</span>
                        <span id="cs-sub-lead-count" class="px-1.5 py-0.2 rounded-full text-[10px] bg-white/20 font-mono pointer-events-none">0</span>
                    </button>
                    <button type="button" onclick="setCareSubTab('multichannel')" id="btn-care-sub-multichannel" class="px-3.5 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer">
                        <span class="pointer-events-none">[VISTAFA] 2. TRỢ LÝ CHAT ĐA KÊNH & ĐỐI THỦ</span>
                        <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-blue-100 text-blue-800 font-mono pointer-events-none">4 Kênh</span>
                    </button>
                    <button type="button" onclick="setCareSubTab('tasks')" id="btn-care-sub-tasks" class="px-3.5 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer">
                        <span class="pointer-events-none">3. CÔNG VIỆC CHĂM SÓC (30 NGÀY)</span>
                        <span id="care-sub-task-count" class="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 font-mono pointer-events-none">0</span>
                    </button>
                    <button type="button" onclick="setCareSubTab('history')" id="btn-care-sub-history" class="px-3.5 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer">
                        <span class="pointer-events-none">4. KHÁCH HÀNG & LỊCH SỬ</span>
                        <span id="care-sub-cust-count" class="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 font-mono pointer-events-none">0</span>
                    </button>
                    <button type="button" onclick="setCareSubTab('sources')" id="btn-care-sub-sources" class="px-3.5 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer">
                        <span class="pointer-events-none">5. NGUỒN DỮ LIỆU</span>
                        <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-100 text-emerald-800 font-mono pointer-events-none">3 Sẵn sàng</span>
                    </button>"""

assert old_subtab_buttons in html, "Could not find old_subtab_buttons!"
html = html.replace(old_subtab_buttons, new_subtab_buttons, 1)

# 2. Insert HTML block before care-subview-tasks
from generate_multichannel_section import html_block

subview_needle = '<!-- ============================================================ -->\n            <!-- PHÂN HỆ 2: CÔNG VIỆC CHĂM SÓC -->'
if subview_needle not in html:
    subview_needle = '<!-- PHÂN HỆ 2: CÔNG VIỆC CHĂM SÓC -->'

assert subview_needle in html, "Could not find subview_needle!"
html = html.replace(subview_needle, html_block + "\n\n            " + subview_needle, 1)

# 3. Update setCareSubTab in JS
old_js_loop = "['caresoft', 'tasks', 'history', 'sources'].forEach(t => {"
new_js_loop = "['caresoft', 'multichannel', 'tasks', 'history', 'sources'].forEach(t => {"
assert old_js_loop in html, "Could not find old_js_loop!"
html = html.replace(old_js_loop, new_js_loop, 1)

# Add multichannel branch in setCareSubTab
old_branch = """            if (tabName === 'caresoft') {
                loadCareSoftLeadsTable();"""

new_branch = """            if (tabName === 'caresoft') {
                loadCareSoftLeadsTable();
            } else if (tabName === 'multichannel') {
                loadMultichannelShortcutsForProduct(curMultichannelProduct);"""

assert old_branch in html, "Could not find old_branch!"
html = html.replace(old_branch, new_branch, 1)

# 4. Insert JS functions
from test_multichannel_js import js_code

js_insert_needle = "async function loadCareSoftLeadsTable() {"
assert js_insert_needle in html, "Could not find js_insert_needle!"
html = html.replace(js_insert_needle, js_code + "\n\n        " + js_insert_needle, 1)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Successfully injected Multi-Channel UI and JavaScript into templates/index.html!")

# Verify zero emojis in templates/index.html
emoji_pattern = re.compile("[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u3030\u303d\u3297\u3299]")
emojis = emoji_pattern.findall(html)
print(f"Total emojis in templates/index.html: {len(emojis)}")
assert len(emojis) == 0, "EMOJIS FOUND IN templates/index.html!"
print("PASSED: ZERO EMOJIS in templates/index.html!")
