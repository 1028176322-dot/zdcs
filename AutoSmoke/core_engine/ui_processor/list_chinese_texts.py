#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
鏈€绠€鍗曠洿鎺ョ殑鏂规硶锛氭悳绱I鏍戜腑鐨勬墍鏈変腑鏂囨枃鏈紝鐒跺悗鎵嬪姩鍏宠仈鍒癈lickContent
"""
import json
import re

# 璇诲彇UI鏍?with open(as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json"), 'r', encoding='utf-8') as f:
    data = json.load(f)

print("鎼滅储UI鏍戜腑鐨勬墍鏈変腑鏂囨枃鏈?..\n")

# 瀛樺偍鎵€鏈変腑鏂囨枃鏈強鍏跺畬鏁磋妭鐐逛俊鎭?chinese_texts = []

def find_chinese_texts(obj, path=""):
    """閫掑綊鏌ユ壘鎵€鏈夊寘鍚腑鏂囨枃鏈殑鑺傜偣"""
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        
        # 妫€鏌ユ墍鏈夊瓧娈?        for key, value in obj.items():
            if key != 'children':
                if isinstance(value, dict):
                    # 妫€鏌ayload涓殑text瀛楁
                    if 'text' in value and value['text']:
                        text_value = value['text']
                        if isinstance(text_value, str) and any('\u4e00' <= c <= '\u9fff' for c in text_value):
                            chinese_texts.append({
                                'text': text_value,
                                'path': path + '.' + key,
                                'node_name': obj.get('name', ''),
                                'parent_path': path
                            })
        
        # 閫掑綊妫€鏌ュ瓙鑺傜偣
        for child in obj.get('children', []):
            find_chinese_texts(child, path + '/' + obj.get('name', ''))
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_chinese_texts(item, path + '[' + str(i) + ']')

# 鎼滅储涓枃鏂囨湰
find_chinese_texts(data)

print(f"鎵惧埌 {len(chinese_texts)} 涓寘鍚腑鏂囩殑鑺傜偣\n")

# 鎸夎矾寰勫垎缁勶紝鎵惧嚭灞炰簬鍚屼竴涓狪tem(Clone)鐨勪腑鏂囨枃鏈?print("=" * 100)
print("娲诲姩鐣岄潰涓殑涓枃鏂囨湰:\n")

# 杩囨护鍑轰笌娲诲姩鐩稿叧鐨勬枃鏈?activity_texts = []
for item in chinese_texts:
    path = item['path']
    text = item['text']
    
    # 杩囨护鎺夊お鐭殑鎴栫函鏁板瓧鐨?    if len(text) > 1 and not text.replace('.', '').isdigit():
        # 娓呯悊HTML鏍囩
        cleaned = re.sub(r'<[^>]+>', '', text)
        activity_texts.append({
            'text': cleaned,
            'path': path,
            'node_name': item['node_name']
        })

# 鍘婚噸
unique_texts = []
for item in activity_texts:
    if item['text'] not in [t['text'] for t in unique_texts]:
        unique_texts.append(item)

# 鏄剧ず鍓?0涓?print(f"鎵惧埌 {len(unique_texts)} 涓敮涓€鐨勪腑鏂囨枃鏈?\n")
for i, item in enumerate(unique_texts[:30]):
    print(f"{i+1:2d}. {item['text']}")
    print(f"    鑺傜偣: {item['node_name']}")

print("\n" + "=" * 100)

# 鐜板湪锛岃繖浜涙枃鏈氨鏄椿鍔ㄧ晫闈腑鏄剧ず鐨勪腑鏂?# 瀵逛簬ClickContent鍏冪礌锛屽畠浠搴旂殑涓枃鏂囨湰灏辨槸鍏舵墍鍦ㄧ殑Item(Clone)涓嬬殑杩欎簺鏂囨湰
print("\n馃挕 璇存槑:")
print("  1. 浠ヤ笂灏辨槸鍦?鎺㈤櫓瀹剁殑璇曠偧'娲诲姩椤甸潰涓壘鍒扮殑鎵€鏈変腑鏂囨枃鏈?)
print("  2. 姣忎釜ClickContent鍏冪礌锛堝垪琛ㄩ」锛夐兘瀵瑰簲鍏朵腑鐨勪竴浜涙枃鏈?)
print("  3. 渚嬪锛氫竴涓垪琛ㄩ」鍙兘鍖呭惈 '鎬绘垬鍔涜揪鍒帮細2000000' + '鍓嶅線'")
print("  4. 鐢变簬UI鏍戠粨鏋勫鏉傦紝鏃犳硶鑷姩涓烘瘡涓狢lickContent绮剧‘鍖归厤涓枃鍚?)
print("  5. 浣嗗彲浠ョ‘瀹氱殑鏄細杩欎簺ClickContent瀵瑰簲鐨勬槸鎴樺姏鐩爣鍒楄〃椤?)

print("\n" + "=" * 100)

# 鐢熸垚鏈€缁堟姤鍛?html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>娲诲姩鐣岄潰涓枃鏂囨湰鍒楄〃</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; }
        .text-item { background: #e8f5e9; padding: 10px; margin: 5px 0; border-radius: 3px; }
        .text { font-size: 16px; color: #4CAF50; }
        .node { font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>馃幃 娲诲姩鐣岄潰涓枃鏂囨湰鍒楄〃</h1>
        <p><strong>褰撳墠椤甸潰:</strong> 鎺㈤櫓瀹剁殑璇曠偧</p>
        <p><strong>璇存槑:</strong> 浠ヤ笅鏄椤甸潰涓墍鏈夌殑涓枃鏂囨湰锛屾瘡涓狢lickContent鍒楄〃椤归兘瀵瑰簲鍏朵腑鐨勪竴浜涙枃鏈?/p>
        <hr>
"""

for i, item in enumerate(unique_texts):
    html_content += f"""
        <div class="text-item">
            <div class="text">{i+1}. {item['text']}</div>
            <div class="node">鑺傜偣: {item['node_name']}</div>
        </div>
"""

html_content += """
    </div>
</body>
</html>
"""

# 淇濆瓨HTML鎶ュ憡
html_file = as_abs_path("reports/runtime_capture/activity_chinese_texts.html")
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n鉁?涓枃鏂囨湰鍒楄〃宸蹭繚瀛樺埌: {html_file}")
print("\n瀹屾垚锛?)

