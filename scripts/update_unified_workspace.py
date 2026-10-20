import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Replace HTML section
from test_unified_workspace import html_snippet

start_html = html.find('<div id="care-subview-multichannel"')
end_html = html.find('<!-- PHÂN HỆ 2: CÔNG VIỆC CHĂM SÓC -->')
assert start_html != -1 and end_html != -1, "Could not find HTML section boundaries!"

html = html[:start_html] + html_snippet.strip() + "\n\n            " + html[end_html:]

# 2. Update setCareSubTab to call initUnifiedWorkspace()
old_subtab_call = "loadMultichannelShortcutsForProduct(curMultichannelProduct);"
new_subtab_call = "initUnifiedWorkspace();"
if old_subtab_call in html:
    html = html.replace(old_subtab_call, new_subtab_call, 1)

# 3. Replace JS section
from test_unified_js import js_code

start_js = html.find("let curMultichannelChannel = 'facebook';")
end_js = html.find("async function loadCareSoftLeadsTable() {")
assert start_js != -1 and end_js != -1, "Could not find JS section boundaries!"

html = html[:start_js] + js_code.strip() + "\n\n        " + html[end_js:]

# 4. Cleanse any potential emojis or unicode icons
html = html.replace('✕', '[X]')
html = html.replace('✓', '[X]')
html = html.replace('➔', '->')
html = html.replace('✔', '[X]')
html = html.replace('❌', '[KHONG]')

emoji_pattern = re.compile("[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u3030\u303d\u3297\u3299]")
emojis = emoji_pattern.findall(html)
print(f"Total emojis found in templates/index.html: {len(emojis)}")
assert len(emojis) == 0, f"Emojis found: {emojis}"

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("SUCCESS: Unified CSKH & AI Consultant Workspace injected into templates/index.html!")
