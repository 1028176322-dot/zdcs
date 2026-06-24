#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
浠嶶I鏍戜腑鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О - 鏀硅繘鐗?"""
import sys
import time
import json

# 璇诲彇涔嬪墠淇濆瓨鐨刄I鏍?ui_tree_file = as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json")
print(f"璇诲彇UI鏍戞枃浠? {ui_tree_file}")

with open(ui_tree_file, 'r', encoding='utf-8') as f:
    ui_tree = json.load(f)

print("鉁?UI鏍戣鍙栨垚鍔?)

# 鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О
def find_clickable_elements_with_names(node, path="", clickable_elements=[]):
    """閫掑綊鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌锛屽苟鎻愬彇涓枃鍚嶇О"""
    if not isinstance(node, dict):
        return clickable_elements
    
    # 妫€鏌ュ綋鍓嶈妭鐐规槸鍚﹀彲鐐瑰嚮
    payload = node.get('payload', {})
    if payload.get('clickable') == True:
        # 灏濊瘯鑾峰彇涓枃鍚嶇О
        name = payload.get('name', '')
        text = payload.get('text', '')
        
        # 濡傛灉text涓虹┖锛屽湪瀛愯妭鐐逛腑鏌ユ壘鎵€鏈塼ext
        if not text:
            texts_found = find_all_texts_in_children(node)
            text = ' | '.join(texts_found) if texts_found else '(鏃犳枃鏈?'
        
        # 鑾峰彇鐖惰妭鐐逛俊鎭紙鐢ㄤ簬鐞嗚В杩欎釜鍏冪礌灞炰簬鍝釜鐣岄潰锛?        parent_info = extract_parent_info(path)
        
        clickable_elements.append({
            'name': name,
            'text': text,
            'path': path + '/' + node.get('name', ''),
            'type': payload.get('type', ''),
            'parent_info': parent_info,
            'components': payload.get('components', [])
        })
    
    # 閫掑綊鏌ユ壘瀛愯妭鐐?    children = node.get('children', [])
    for child in children:
        find_clickable_elements_with_names(child, path + '/' + node.get('name', ''), clickable_elements)
    
    return clickable_elements

def find_all_texts_in_children(node, max_depth=5, current_depth=0):
    """鍦ㄥ瓙鑺傜偣涓煡鎵炬墍鏈塼ext锛屾渶澶氭煡鎵?灞?""
    if current_depth >= max_depth:
        return []
    
    texts_found = []
    
    children = node.get('children', [])
    for child in children:
        child_payload = child.get('payload', {})
        
        # 鏌ユ壘鏈塼ext鐨勮妭鐐?        if child_payload.get('text'):
            texts_found.append(child_payload.get('text', ''))
        
        # 鏌ユ壘鐗瑰畾鍚嶇О鐨勮妭鐐癸紙杩欎簺閫氬父鍖呭惈鏂囨湰锛?        child_name = child.get('name', '')
        if child_name in ['Text', 'Title', 'Name', 'Label', 'Desc', 'Description']:
            if child_payload.get('text'):
                texts_found.append(f"{child_name}: {child_payload.get('text', '')}")
        
        # 閫掑綊鏌ユ壘
        child_texts = find_all_texts_in_children(child, max_depth, current_depth + 1)
        texts_found.extend(child_texts)
    
    return texts_found

def extract_parent_info(path):
    """浠庤矾寰勪腑鎻愬彇鐖惰妭鐐逛俊鎭?""
    # 璺緞鏍煎紡: /<Root>/DeepUI/LayerUI/UIActivityMain(Clone)_UIActivityMain [UIActivityMain]/Root/...
    # 鎻愬彇鍏抽敭鐨勭埗鑺傜偣鍚嶇О
    parts = path.split('/')
    relevant_parts = []
    for part in parts:
        if any(keyword in part for keyword in ['UI', 'Page', 'Window', 'Panel', 'Main']):
            # 娓呯悊鎷彿鍐呭
            clean_part = part.split('(')[0].split('[')[0]
            relevant_parts.append(clean_part)
    
    return '/'.join(relevant_parts[-3:]) if relevant_parts else ''

# 鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌
print("\n瑙ｆ瀽UI鏍戯紝鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О...")
clickable_elements = find_clickable_elements_with_names(ui_tree)

print(f"鉁?鎵惧埌 {len(clickable_elements)} 涓彲鐐瑰嚮鍏冪礌")

# 淇濆瓨鍒版枃浠?timestamp = time.strftime("%Y%m%d_%H%M%S")
output_file = as_abs_path("reports/runtime_capture/clickable_elements_with_names_{timestamp}.json")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(clickable_elements, f, ensure_ascii=False, indent=2)
print(f"鉁?鍙偣鍑诲厓绱狅紙鍚腑鏂囧悕绉帮級宸蹭繚瀛樺埌: {output_file}")

# 鏄剧ず鎵€鏈夊彲鐐瑰嚮鍏冪礌
print(f"\n鎵€鏈夊彲鐐瑰嚮鍏冪礌:")
print("=" * 100)
for i, elem in enumerate(clickable_elements):
    text_display = elem['text'][:50] if elem['text'] else '(鏃犳枃鏈?'
    print(f"{i+1:2d}. {elem['name']:<30} | {text_display}")
    if elem['parent_info']:
        print(f"    鐖惰妭鐐? {elem['parent_info']}")
    print()

print("=" * 100)
print("瀹屾垚")


