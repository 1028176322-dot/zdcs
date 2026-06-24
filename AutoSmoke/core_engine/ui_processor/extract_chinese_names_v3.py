#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
浠嶶I鏍戜腑鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О - 鏈€缁堢増
鏌ユ壘鍏勫紵鑺傜偣涓殑鏂囨湰
"""
import sys
import time
import json

# 璇诲彇涔嬪墠淇濆瓨鐨刄I鏍?ui_tree_file = as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json")
print(f"璇诲彇UI鏍戞枃浠? {ui_tree_file}")

with open(ui_tree_file, 'r', encoding='utf-8') as f:
    ui_tree = json.load(f)

print("鉁?UI鏍戣鍙栨垚鍔?)

def find_text_in_node_or_siblings(node, parent_node=None):
    """鍦ㄨ妭鐐规湰韬垨鍏勫紵鑺傜偣涓煡鎵炬枃鏈?""
    texts = []
    
    # 妫€鏌ュ綋鍓嶈妭鐐?    payload = node.get('payload', {})
    if payload.get('text'):
        texts.append(payload.get('text', ''))
    
    # 妫€鏌ュ厔寮熻妭鐐癸紙閫氳繃parent_node锛?    if parent_node:
        siblings = parent_node.get('children', [])
        for sibling in siblings:
            if sibling != node:  # 涓嶆槸鑷繁
                sibling_payload = sibling.get('payload', {})
                if sibling_payload.get('text'):
                    texts.append(sibling_payload.get('text', ''))
                
                # 涔熸鏌ュ厔寮熻妭鐐圭殑瀛愯妭鐐?                for child in sibling.get('children', []):
                    child_payload = child.get('payload', {})
                    if child_payload.get('text'):
                        texts.append(child_payload.get('text', ''))
    
    # 妫€鏌ュ瓙鑺傜偣
    for child in node.get('children', []):
        child_payload = child.get('payload', {})
        if child_payload.get('text'):
            texts.append(child_payload.get('text', ''))
        # 閫掑綊妫€鏌ュ瓙鑺傜偣鐨勫瓙鑺傜偣
        texts.extend(find_text_in_node_or_siblings(child, node))
    
    return texts

def find_clickable_elements_with_names(node, parent_node=None, path="", clickable_elements=[]):
    """閫掑綊鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌锛屽苟鍦ㄥ厔寮熻妭鐐逛腑鏌ユ壘涓枃鍚嶇О"""
    if not isinstance(node, dict):
        return clickable_elements
    
    # 妫€鏌ュ綋鍓嶈妭鐐规槸鍚﹀彲鐐瑰嚮
    payload = node.get('payload', {})
    if payload.get('clickable') == True:
        # 灏濊瘯鑾峰彇涓枃鍚嶇О
        name = payload.get('name', '')
        
        # 鍦ㄨ妭鐐规湰韬€佸瓙鑺傜偣銆佸厔寮熻妭鐐逛腑鏌ユ壘鏂囨湰
        texts_found = find_text_in_node_or_siblings(node, parent_node)
        
        # 鍘婚噸
        texts_found = list(dict.fromkeys(texts_found))
        text = ' | '.join(texts_found) if texts_found else '(鏃犳枃鏈?'
        
        # 鑾峰彇鐖惰妭鐐逛俊鎭?        parent_info = extract_parent_info(path)
        
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
        find_clickable_elements_with_names(child, node, path + '/' + node.get('name', ''), clickable_elements)
    
    return clickable_elements

def extract_parent_info(path):
    """浠庤矾寰勪腑鎻愬彇鐖惰妭鐐逛俊鎭?""
    parts = path.split('/')
    relevant_parts = []
    for part in parts:
        if any(keyword in part for keyword in ['UI', 'Page', 'Window', 'Panel', 'Main', 'Tab']):
            clean_part = part.split('(')[0].split('[')[0]
            relevant_parts.append(clean_part)
    
    return '/'.join(relevant_parts[-2:]) if relevant_parts else ''

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
    text_display = elem['text'][:60] if elem['text'] else '(鏃犳枃鏈?'
    print(f"{i+1:2d}. {elem['name']:<30} | {text_display}")
    if elem['parent_info']:
        print(f"    浣嶇疆: {elem['parent_info']}")
    print()

print("=" * 100)
print("瀹屾垚")


