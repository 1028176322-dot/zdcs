#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
姝ｇ‘鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О
鏌ユ壘鐖惰妭鐐逛笅鐨勬墍鏈夋枃鏈瓧娈?"""
import json

# 璇诲彇UI鏍?with open(as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json"), 'r', encoding='utf-8') as f:
    ui_tree = json.load(f)

print("瑙ｆ瀽UI鏍戯紝鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О...\n")

def find_all_text_fields(node, texts=None):
    """閫掑綊鏌ユ壘鑺傜偣涓墍鏈夊彲鑳界殑鏂囨湰瀛楁"""
    if texts is None:
        texts = []
    
    if not isinstance(node, dict):
        return texts
    
    payload = node.get('payload', {})
    
    # 妫€鏌ユ墍鏈夊彲鑳界殑鏂囨湰瀛楁
    text_fields = ['text', 'name', 'title', 'txt', 'txt1', 'Title', 'Txtdesc', 'time', 'TimeCountTxt', 'leisure']
    
    for field in text_fields:
        if field in payload and payload[field]:
            text_value = payload[field]
            # 娓呯悊HTML鏍囩
            if isinstance(text_value, str):
                import re
                text_value = re.sub(r'<[^>]+>', '', text_value)
                if text_value.strip():
                    texts.append(text_value.strip())
    
    # 閫掑綊妫€鏌ュ瓙鑺傜偣
    for child in node.get('children', []):
        find_all_text_fields(child, texts)
    
    return texts

def find_clickable_with_parent_text(node, parent_node=None, path="", results=None, depth=0):
    """鏌ユ壘鍙偣鍑诲厓绱狅紝骞跺湪鍏剁埗鑺傜偣涓煡鎵炬枃鏈?""
    if results is None:
        results = []
    
    if not isinstance(node, dict):
        return results
    
    payload = node.get('payload', {})
    
    # 妫€鏌ユ槸鍚﹀彲鐐瑰嚮
    if payload.get('clickable') == True:
        node_name = payload.get('name', '')
        
        # 鍦ㄧ埗鑺傜偣涓煡鎵炬墍鏈夋枃鏈?        all_texts = []
        if parent_node:
            all_texts = find_all_text_fields(parent_node)
        
        # 涔熷湪褰撳墠鑺傜偣鐨勫瓙鑺傜偣涓煡鎵?        all_texts.extend(find_all_text_fields(node))
        
        # 鍘婚噸
        all_texts = list(dict.fromkeys(all_texts))
        
        results.append({
            'name': node_name,
            'texts': all_texts,
            'path': path + '/' + node.get('name', ''),
            'depth': depth
        })
    
    # 閫掑綊妫€鏌ュ瓙鑺傜偣
    for child in node.get('children', []):
        find_clickable_with_parent_text(child, node, path + '/' + node.get('name', ''), results, depth + 1)
    
    return results

# 鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌鍙婂叾鏂囨湰
print("鏌ユ壘鍙偣鍑诲厓绱?..")
clickable_with_text = find_clickable_with_parent_text(ui_tree)

print(f"鉁?鎵惧埌 {len(clickable_with_text)} 涓彲鐐瑰嚮鍏冪礌\n")
print("=" * 100)

# 鏄剧ず缁撴灉
for i, item in enumerate(clickable_with_text):
    print(f"\n{i+1:2d}. {item['name']}")
    if item['texts']:
        print(f"    鏂囨湰: {' | '.join(item['texts'][:3])}")  # 鍙樉绀哄墠3涓枃鏈?    else:
        print(f"    鏂囨湰: (鏃犳枃鏈?")
    
    # 鏄剧ず璺緞鐨勬渶鍚?0涓瓧绗?    path_short = item['path'][-80:] if len(item['path']) > 80 else item['path']
    print(f"    璺緞: ...{path_short}")

print("\n" + "=" * 100)

# 淇濆瓨鍒版枃浠?output_file = as_abs_path("reports/runtime_capture/clickable_with_chinese_names.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(clickable_with_text, f, ensure_ascii=False, indent=2)

print(f"\n鉁?缁撴灉宸蹭繚瀛樺埌: {output_file}")
print("瀹屾垚锛?)

