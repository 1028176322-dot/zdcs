#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
姝ｇ‘鎻愬彇姣忎釜ClickContent瀵瑰簲鐨勪腑鏂囨枃鏈?閫氳繃閬嶅巻UI鏍戯紝涓烘瘡涓猚lickable鍏冪礌鎵惧埌鍏舵墍鍦↖tem(Clone)涓嬬殑鎵€鏈夋枃鏈?"""
import json
import re

# 璇诲彇UI鏍?with open(as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json"), 'r', encoding='utf-8') as f:
    ui_tree = json.load(f)

print("姝ｇ‘鎻愬彇姣忎釜ClickContent瀵瑰簲鐨勪腑鏂囨枃鏈?..\n")

def extract_all_texts(node):
    """鎻愬彇鑺傜偣涓墍鏈夌殑涓枃鏂囨湰"""
    texts = []
    if not isinstance(node, dict):
        return texts
    
    payload = node.get('payload', {})
    
    # 妫€鏌ユ墍鏈夊彲鑳界殑鏂囨湰瀛楁
    for field in ['text', 'title', 'txt', 'txt1', 'Title', 'Txtdesc', 'name', 'time']:
        if field in payload and payload[field]:
            value = payload[field]
            if isinstance(value, str) and value.strip():
                # 娓呯悊HTML鏍囩
                cleaned = re.sub(r'<[^>]+>', '', value).strip()
                # 妫€鏌ユ槸鍚﹀寘鍚腑鏂?                if cleaned and any('\u4e00' <= c <= '\u9fff' for c in cleaned):
                    if cleaned not in texts:
                        texts.append(cleaned)
    
    # 閫掑綊妫€鏌ュ瓙鑺傜偣
    for child in node.get('children', []):
        texts.extend(extract_all_texts(child))
    
    return texts

def find_clickable_with_item_text(ui_tree):
    """鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌锛屽苟鎻愬彇鍏舵墍鍦↖tem(Clone)鐨勬墍鏈夋枃鏈?""
    results = []
    
    def traverse(node, path="", item_root=None):
        if not isinstance(node, dict):
            return
        
        node_name = node.get('name', '')
        
        # 鏇存柊item_root
        if '(Clone)' in node_name and 'Item' in node_name:
            item_root = node
        
        # 妫€鏌ユ槸鍚﹀彲鐐瑰嚮
        payload = node.get('payload', {})
        if payload.get('clickable') == True:
            # 浠巌tem_root鎻愬彇鎵€鏈夋枃鏈?            texts = []
            if item_root:
                texts = extract_all_texts(item_root)
            
            results.append({
                'name': node_name,
                'texts': texts,
                'path': path + '/' + node_name,
                'item_root_name': item_root.get('name', '') if item_root else ''
            })
        
        # 閫掑綊閬嶅巻瀛愯妭鐐?        for child in node.get('children', []):
            traverse(child, path + '/' + node_name, item_root)
    
    traverse(ui_tree)
    return results

# 鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌
print("閬嶅巻UI鏍?..")
clickable_with_texts = find_clickable_with_item_text(ui_tree)

print(f"鉁?鎵惧埌 {len(clickable_with_texts)} 涓彲鐐瑰嚮鍏冪礌\n")
print("=" * 100)

# 鏄剧ず缁撴灉
for i, elem in enumerate(clickable_with_texts):
    print(f"\n{i+1:2d}. {elem['name']} ({elem['item_root_name']})")
    if elem['texts']:
        print(f"    涓枃鏂囨湰:")
        for text in elem['texts'][:5]:
            print(f"      鈥?{text}")
    else:
        print(f"    鏂囨湰: (鏃犱腑鏂囨枃鏈?")

print("\n" + "=" * 100)

# 鐢熸垚HTML鎶ュ憡
html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>娲诲姩鐣岄潰鍙偣鍑诲厓绱?- 鍚腑鏂囧悕绉?/title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .item { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }
        .item-name { font-size: 18px; font-weight: bold; color: #333; }
        .texts { margin: 10px 0 0 20px; }
        .text { color: #2196F3; padding: 3px 0; }
        .path { font-size: 12px; color: #666; margin-top: 5px; word-break: break-all; }
    </style>
</head>
<body>
    <div class="container">
        <h1>馃幃 娲诲姩鐣岄潰鍙偣鍑诲厓绱犳姤鍛婏紙鍚腑鏂囧悕绉帮級</h1>
        <p><strong>褰撳墠鐣岄潰:</strong> 娲诲姩涓荤晫闈?- 鎺㈤櫓瀹剁殑璇曠偧</p>
        <p><strong>鍙偣鍑诲厓绱犳€绘暟:</strong> """ + str(len(clickable_with_texts)) + """</p>
        <hr>
"""

for i, elem in enumerate(clickable_with_texts):
    html_content += f"""
        <div class="item">
            <div class="item-name">{i+1}. {elem['name']} ({elem['item_root_name']})</div>
            <div class="texts">
"""
    
    if elem['texts']:
        for text in elem['texts'][:5]:
            html_content += f"""                <div class="text">鈥?{text}</div>
"""
    else:
        html_content += """                <div class="text">鈥?(鏃犱腑鏂囨枃鏈?</div>
"""
    
    html_content += f"""            </div>
            <div class="path">璺緞: {elem['path']}</div>
        </div>
"""

html_content += """
    </div>
</body>
</html>
"""

# 淇濆瓨HTML鎶ュ憡
html_file = as_abs_path("reports/runtime_capture/activity_clickable_with_chinese.html")
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n鉁?HTML鎶ュ憡宸蹭繚瀛樺埌: {html_file}")

# 淇濆瓨JSON
json_file = as_abs_path("reports/runtime_capture/clickable_with_chinese.json")
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(clickable_with_texts, f, ensure_ascii=False, indent=2)

print(f"鉁?JSON鏁版嵁宸蹭繚瀛樺埌: {json_file}")
print("\n瀹屾垚锛?)

