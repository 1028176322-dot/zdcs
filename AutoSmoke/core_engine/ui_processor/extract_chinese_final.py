#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
鏈€缁堢増锛氫负姣忎釜ClickContent鎻愬彇涓枃鍚嶇О
閫氳繃鏌ユ壘Item(Clone)鐖惰妭鐐逛笅鐨勬墍鏈夋枃鏈?"""
import json
import re

# 璇诲彇UI鏍?with open(as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json"), 'r', encoding='utf-8') as f:
    ui_tree = json.load(f)

print("鎻愬彇姣忎釜ClickContent鐨勪腑鏂囧悕绉?..\n")

def find_texts_in_node(node):
    """鍦ㄨ妭鐐圭殑鎵€鏈夊瓙鑺傜偣涓煡鎵炬枃鏈?""
    texts = []
    if not isinstance(node, dict):
        return texts
    
    payload = node.get('payload', {})
    text_fields = ['text', 'title', 'txt', 'txt1', 'Title', 'Txtdesc', 'name']
    
    for field in text_fields:
        if field in payload and payload[field]:
            value = payload[field]
            if isinstance(value, str) and value.strip():
                cleaned = re.sub(r'<[^>]+>', '', value).strip()
                if cleaned and cleaned not in texts:
                    texts.append(cleaned)
    
    for child in node.get('children', []):
        texts.extend(find_texts_in_node(child))
    
    return texts

def find_clickable_and_extract_texts(node, parent=None, path="", results=None):
    """鏌ユ壘鍙偣鍑诲厓绱狅紝骞朵粠Item(Clone)鐖惰妭鐐规彁鍙栨枃鏈?""
    if results is None:
        results = []
    
    if not isinstance(node, dict):
        return results
    
    payload = node.get('payload', {})
    
    # 妫€鏌ユ槸鍚﹀彲鐐瑰嚮
    if payload.get('clickable') == True:
        node_name = payload.get('name', '')
        
        # 鏌ユ壘Item(Clone)鐖惰妭鐐?        # 鏂规硶锛氬湪璺緞涓煡鎵炬渶杩戠殑鍖呭惈"(Clone)"鐨勭鍏?        path_parts = [p for p in path.split('/') if p]
        item_root = None
        
        # 鍚戜笂鏌ユ壘璺緞涓殑Item(Clone)
        for i in range(len(path_parts) - 1, -1, -1):
            if 'Item(Clone)' in path_parts[i]:
                # 鎵惧埌浜咺tem(Clone)锛岀幇鍦ㄩ渶瑕佸湪UI鏍戜腑鎵惧埌杩欎釜鑺傜偣
                # 绠€鍖栵細鐩存帴鍦╬arent鐨勫弬鏁颁腑鏌ユ壘
                break
        
        # 绠€鍖栨柟娉曪細鐩存帴鍦ㄧ埗鑺傜偣涓煡鎵炬枃鏈?        texts = []
        if parent:
            texts = find_texts_in_node(parent)
        
        # 涔熸鏌ュ綋鍓嶈妭鐐圭殑瀛愯妭鐐?        texts.extend(find_texts_in_node(node))
        
        # 鍘婚噸骞惰繃婊?        texts = list(dict.fromkeys(texts))
        meaningful_texts = [t for t in texts if len(t) > 1 and not t.replace('.', '').isdigit() and any('\u4e00' <= c <= '\u9fff' for c in t)]
        
        results.append({
            'name': node_name,
            'texts': meaningful_texts if meaningful_texts else texts[:3],
            'path': path + '/' + node.get('name', ''),
            'parent_name': parent.get('name', '') if parent else ''
        })
    
    # 閫掑綊妫€鏌ュ瓙鑺傜偣
    for child in node.get('children', []):
        find_clickable_and_extract_texts(child, node, path + '/' + node.get('name', ''), results)
    
    return results

# 鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌骞舵彁鍙栨枃鏈?clickable_with_texts = find_clickable_and_extract_texts(ui_tree)

print(f"鉁?鎵惧埌 {len(clickable_with_texts)} 涓彲鐐瑰嚮鍏冪礌\n")
print("=" * 100)

# 鏄剧ず缁撴灉
for i, elem in enumerate(clickable_with_texts):
    print(f"\n{i+1:2d}. {elem['name']}")
    if elem['texts']:
        print(f"    涓枃鍚嶇О/鏂囨湰:")
        for text in elem['texts'][:5]:  # 鏄剧ず鍓?涓枃鏈?            print(f"      鈥?{text}")
    else:
        print(f"    鏂囨湰: (鏃犳枃鏈?")
    
    path_short = elem['path'][-60:] if len(elem['path']) > 60 else elem['path']
    print(f"    璺緞: ...{path_short}")

print("\n" + "=" * 100)

# 淇濆瓨鍒版枃浠?output_file = as_abs_path("reports/runtime_capture/clickable_final_report.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(clickable_with_texts, f, ensure_ascii=False, indent=2)

print(f"\n鉁?缁撴灉宸蹭繚瀛樺埌: {output_file}")

# 鐢熸垚鏇磋缁嗙殑HTML鎶ュ憡
html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>娲诲姩鐣岄潰鍙偣鍑诲厓绱犺缁嗘姤鍛?/title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .clickable-item { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }
        .clickable-name { font-size: 18px; font-weight: bold; color: #333; }
        .text-list { margin: 10px 0 0 20px; }
        .text-item { padding: 5px 0; color: #2196F3; }
        .path { font-size: 12px; color: #666; margin-top: 5px; word-break: break-all; }
    </style>
</head>
<body>
    <div class="container">
        <h1>馃幃 娲诲姩鐣岄潰鍙偣鍑诲厓绱犺缁嗘姤鍛?/h1>
        <p><strong>褰撳墠鐣岄潰:</strong> UIActivityMain (娲诲姩涓荤晫闈? - UIActivityExplorersTrial (鎺㈤櫓瀹剁殑璇曠偧)</p>
        <p><strong>鍙偣鍑诲厓绱犳€绘暟:</strong> """ + str(len(clickable_with_texts)) + """</p>
        <hr>
"""

for i, elem in enumerate(clickable_with_texts):
    html_content += f"""
        <div class="clickable-item">
            <div class="clickable-name">{i+1}. {elem['name']}</div>
            <div class="text-list">
                <strong>涓枃鏂囨湰:</strong>
"""
    
    if elem['texts']:
        for text in elem['texts'][:5]:
            html_content += f"""                <div class="text-item">鈥?{text}</div>
"""
    else:
        html_content += """                <div class="text-item">鈥?(鏃犳枃鏈?</div>
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
html_file = as_abs_path("reports/runtime_capture/clickable_detailed_report.html")
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"鉁?HTML鎶ュ憡宸蹭繚瀛樺埌: {html_file}")
print("\n瀹屾垚锛?)

