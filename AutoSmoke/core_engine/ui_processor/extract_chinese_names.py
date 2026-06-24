#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
浠嶶I鏍戜腑鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О
"""
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
        
        # 濡傛灉text涓虹┖锛屽皾璇曞湪瀛愯妭鐐逛腑鏌ユ壘text
        if not text:
            children = node.get('children', [])
            for child in children:
                child_payload = child.get('payload', {})
                if child_payload.get('text'):
                    text = child_payload.get('text', '')
                    break
        
        # 濡傛灉杩樻槸娌℃湁text锛屽皾璇曞湪鏇存繁灞傜殑瀛愯妭鐐逛腑鏌ユ壘
        if not text:
            text = find_text_in_children(node)
        
        clickable_elements.append({
            'name': name,
            'text': text,
            'path': path + '/' + node.get('name', ''),
            'type': payload.get('type', ''),
            'components': payload.get('components', [])
        })
    
    # 閫掑綊鏌ユ壘瀛愯妭鐐?    children = node.get('children', [])
    for child in children:
        find_clickable_elements_with_names(child, path + '/' + node.get('name', ''), clickable_elements)
    
    return clickable_elements

def find_text_in_children(node, max_depth=3):
    """鍦ㄥ瓙鑺傜偣涓煡鎵総ext锛屾渶澶氭煡鎵?灞?""
    if max_depth <= 0:
        return ''
    
    children = node.get('children', [])
    for child in children:
        child_payload = child.get('payload', {})
        if child_payload.get('text'):
            return child_payload.get('text', '')
        
        # 閫掑綊鏌ユ壘
        text = find_text_in_children(child, max_depth - 1)
        if text:
            return text
    
    return ''

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
print("=" * 80)
for i, elem in enumerate(clickable_elements):
    text_display = elem['text'] if elem['text'] else '(鏃犳枃鏈?'
    print(f"{i+1:2d}. {elem['name']:<30} | 鏂囨湰: {text_display}")
    # 濡傛灉璺緞澶暱锛屽彧鏄剧ず鏈€鍚庝竴閮ㄥ垎
    path_short = elem['path'][-80:] if len(elem['path']) > 80 else elem['path']
    print(f"    璺緞: ...{path_short}")
    print()

print("=" * 80)
print("瀹屾垚")


