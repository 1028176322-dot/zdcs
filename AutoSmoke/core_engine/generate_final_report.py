#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
鐢熸垚娲诲姩鐣岄潰鍙偣鍑诲厓绱犵殑鏈€缁堟姤鍛?"""
import json

# 璇诲彇涔嬪墠鐢熸垚鐨勬暟鎹?with open(as_abs_path("reports/runtime_capture/activity_texts.json"), 'r', encoding='utf-8') as f:
    texts_by_item = json.load(f)

# 璇诲彇鍙偣鍑诲厓绱犳暟鎹?with open(as_abs_path("reports/runtime_capture/clickable_elements_20260611_120143.json"), 'r', encoding='utf-8') as f:
    clickable_elements = json.load(f)

print("=" * 100)
print("娲诲姩鐣岄潰鍙偣鍑诲厓绱犳姤鍛?)
print("=" * 100)

print("\n馃摫 褰撳墠鐣岄潰: UIActivityMain (娲诲姩涓荤晫闈?")
print("馃搫 褰撳墠椤甸潰: UIActivityExplorersTrial (鎺㈤櫓瀹剁殑璇曠偧)\n")

print("=" * 100)
print("\n馃搵 鎵惧埌 34 涓彲鐐瑰嚮鍏冪礌锛歕n")

# 鍒嗙被鏄剧ず鍙偣鍑诲厓绱?tab_elements = []
activity_elements = []
reward_elements = []
other_elements = []

for elem in clickable_elements:
    path = elem['path']
    
    if 'Tab' in path:
        tab_elements.append(elem)
    elif 'loopListView' in path or 'TargetReward' in path:
        activity_elements.append(elem)
    elif 'Btn' in elem['name'] or 'Button' in elem['name']:
        other_elements.append(elem)
    else:
        other_elements.append(elem)

# 鏄剧ず鏍囩椤?if tab_elements:
    print("馃搼 鏍囩椤垫寜閽?")
    for i, elem in enumerate(tab_elements):
        print(f"  {i+1}. {elem['name']}")
    print()

# 鏄剧ず娲诲姩鍒楄〃椤?if activity_elements:
    print(f"馃摑 娲诲姩鍒楄〃椤?({len(activity_elements)} 涓?:")
    print("  (姣忎釜鍒楄〃椤瑰搴斾竴涓垬鍔涚洰鏍?")
    
    # 浠巘exts_by_item涓彁鍙朓tem(Clone)鐨勬枃鏈?    if 'Item(Clone)' in texts_by_item:
        item_texts = texts_by_item['Item(Clone)']
        # 鍘婚噸骞惰繃婊?        unique_texts = []
        for item in item_texts:
            text = item['text']
            if text not in [t['text'] for t in unique_texts]:
                unique_texts.append(item)
        
        print("\n  鍒楄〃椤瑰唴瀹圭ず渚?")
        for i, item in enumerate(unique_texts[:10]):
            print(f"    鈥?{item['text']}")
    
    print(f"\n  鉁?鍏?{len(activity_elements)} 涓彲鐐瑰嚮鐨勫垪琛ㄩ」 (ClickContent)")
    print()

# 鏄剧ず鍏朵粬鍙偣鍑诲厓绱?if other_elements:
    print("馃敇 鍏朵粬鍙偣鍑诲厓绱?")
    for i, elem in enumerate(other_elements[:10]):
        print(f"  {i+1}. {elem['name']} (璺緞: {elem['path'][-50:]})")
    print()

print("=" * 100)
print("\n馃挕 璇存槑:")
print("  1. 褰撳墠鍦?鎺㈤櫓瀹剁殑璇曠偧'娲诲姩椤甸潰")
print("  2. 椤甸潰涓湁澶氫釜鎴樺姏鐩爣鍒楄〃椤癸紝姣忎釜閮芥槸涓€涓彲鐐瑰嚮鍏冪礌")
print("  3. 姣忎釜鍒楄〃椤规樉绀? '鎬绘垬鍔涜揪鍒帮細XXX' + '鍓嶅線'/'棰嗗彇'鎸夐挳")
print("  4. 鐐瑰嚮鍒楄〃椤瑰彲浠ユ煡鐪嬭鎯呮垨棰嗗彇濂栧姳")
print("\n" + "=" * 100)

# 鐢熸垚HTML鎶ュ憡
html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>娲诲姩鐣岄潰鍙偣鍑诲厓绱犳姤鍛?/title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #4CAF50; margin-top: 30px; }
        .info { background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .clickable-list { background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .clickable-item { padding: 8px; margin: 5px 0; background: white; border-left: 3px solid #4CAF50; }
        .path { font-size: 12px; color: #666; margin-left: 20px; }
        .text { color: #2196F3; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>馃幃 娲诲姩鐣岄潰鍙偣鍑诲厓绱犳姤鍛?/h1>
        
        <div class="info">
            <p><strong>馃摫 褰撳墠鐣岄潰:</strong> UIActivityMain (娲诲姩涓荤晫闈?</p>
            <p><strong>馃搫 褰撳墠椤甸潰:</strong> UIActivityExplorersTrial (鎺㈤櫓瀹剁殑璇曠偧)</p>
            <p><strong>馃敘 鍙偣鍑诲厓绱犳€绘暟:</strong> 34 涓?/p>
        </div>
        
        <h2>馃搵 鍙偣鍑诲厓绱犲垪琛?/h2>
        <div class="clickable-list">
"""

# 娣诲姞鍙偣鍑诲厓绱犲埌HTML
for i, elem in enumerate(clickable_elements):
    path = elem['path']
    
    # 鍒ゆ柇鍏冪礌绫诲瀷
    if 'Tab' in path:
        elem_type = "馃搼 鏍囩椤?
    elif 'loopListView' in path or 'TargetReward' in path:
        elem_type = "馃摑 娲诲姩鍒楄〃椤?
    else:
        elem_type = "馃敇 鍏朵粬"
    
    html_content += f"""
            <div class="clickable-item">
                <strong>{i+1}. {elem['name']}</strong>
                <span class="text"> ({elem_type})</span>
                <div class="path">璺緞: {path}</div>
            </div>
"""

html_content += """
        </div>
        
        <h2>馃挕 璇存槑</h2>
        <div class="info">
            <p>1. 褰撳墠鍦?鎺㈤櫓瀹剁殑璇曠偧'娲诲姩椤甸潰</p>
            <p>2. 椤甸潰涓湁澶氫釜鎴樺姏鐩爣鍒楄〃椤癸紝姣忎釜閮芥槸涓€涓彲鐐瑰嚮鍏冪礌</p>
            <p>3. 姣忎釜鍒楄〃椤规樉绀? '鎬绘垬鍔涜揪鍒帮細XXX' + '鍓嶅線'/'棰嗗彇'鎸夐挳</p>
            <p>4. 鐐瑰嚮鍒楄〃椤瑰彲浠ユ煡鐪嬭鎯呮垨棰嗗彇濂栧姳</p>
        </div>
        
        <hr style="margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">鎶ュ憡鐢熸垚鏃堕棿: 2026-06-11 12:10</p>
    </div>
</body>
</html>
"""

# 淇濆瓨HTML鎶ュ憡
output_file = as_abs_path("reports/runtime_capture/activity_clickable_report.html")
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n鉁?HTML鎶ュ憡宸蹭繚瀛樺埌: {output_file}")
print("\n瀹屾垚锛?)

