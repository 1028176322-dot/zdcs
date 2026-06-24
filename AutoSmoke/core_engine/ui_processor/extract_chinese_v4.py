#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
姝ｇ‘鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О - 鏈€缁堢増
鍚戜笂鏌ユ壘鑻ュ共灞傦紝鐒跺悗鎼滅储鎵€鏈夊瓙瀛欒妭鐐逛腑鐨勬枃鏈?"""
import json

# 璇诲彇UI鏍?with open(as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json"), 'r', encoding='utf-8') as f:
    ui_tree = json.load(f)

print("瑙ｆ瀽UI鏍戯紝鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О...\n")

def find_text_in_subtree(node, max_depth=10, current_depth=0):
    """鍦ㄨ妭鐐圭殑瀛愭爲涓煡鎵炬墍鏈夋枃鏈?""
    texts = []
    
    if current_depth >= max_depth or not isinstance(node, dict):
        return texts
    
    payload = node.get('payload', {})
    
    # 妫€鏌ユ墍鏈夊彲鑳界殑鏂囨湰瀛楁
    text_fields = ['text', 'title', 'txt', 'txt1', 'Title', 'Txtdesc', 'time', 'TimeCountTxt', 'leisure', 'name']
    
    for field in text_fields:
        if field in payload and payload[field]:
            text_value = payload[field]
            if isinstance(text_value, str) and text_value.strip():
                # 娓呯悊HTML鏍囩
                import re
                cleaned = re.sub(r'<[^>]+>', '', text_value).strip()
                if cleaned and cleaned not in texts:
                    texts.append(cleaned)
    
    # 閫掑綊妫€鏌ュ瓙鑺傜偣
    for child in node.get('children', []):
        texts.extend(find_text_in_subtree(child, max_depth, current_depth + 1))
    
    return texts

def find_node_by_path(root, target_path):
    """鏍规嵁璺緞鏌ユ壘鑺傜偣"""
    parts = [p for p in target_path.split('/') if p]
    current = root
    
    for part in parts:
        if not isinstance(current, dict):
            return None
        
        found = False
        for child in current.get('children', []):
            if child.get('name', '') == part.split(' ')[0].split('(')[0]:
                current = child
                found = True
                break
        
        if not found:
            return None
    
    return current

def find_clickable_elements(node, path="", results=None):
    """鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌"""
    if results is None:
        results = []
    
    if not isinstance(node, dict):
        return results
    
    payload = node.get('payload', {})
    
    # 妫€鏌ユ槸鍚﹀彲鐐瑰嚮
    if payload.get('clickable') == True:
        results.append({
            'node': node,
            'path': path + '/' + node.get('name', ''),
            'name': payload.get('name', '')
        })
    
    # 閫掑綊妫€鏌ュ瓙鑺傜偣
    for child in node.get('children', []):
        find_clickable_elements(child, path + '/' + node.get('name', ''), results)
    
    return results

# 鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌
print("鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌...")
clickable_elements = find_clickable_elements(ui_tree)

print(f"鉁?鎵惧埌 {len(clickable_elements)} 涓彲鐐瑰嚮鍏冪礌\n")

# 涓烘瘡涓彲鐐瑰嚮鍏冪礌鏌ユ壘涓枃鍚嶇О
print("涓烘瘡涓彲鐐瑰嚮鍏冪礌鏌ユ壘涓枃鍚嶇О...\n")
print("=" * 100)

for i, elem in enumerate(clickable_elements):
    node = elem['node']
    path = elem['path']
    name = elem['name']
    
    # 鍚戜笂鏌ユ壘3-4灞傦紝鎵惧埌鍒楄〃椤瑰鍣?    # 鏂规硶锛氬湪璺緞涓煡鎵?Item(Clone)"锛岀劧鍚庤幏鍙栭偅涓妭鐐?    path_parts = [p for p in path.split('/') if p]
    
    # 鏌ユ壘鍖呭惈"Item(Clone)"鐨勮矾寰勯儴鍒?    item_root = None
    for j in range(len(path_parts) - 1, -1, -1):
        if 'Item(Clone)' in path_parts[j]:
            # 鎵惧埌杩欎釜Item(Clone)鑺傜偣
            item_path = '/' + '/'.join(path_parts[:j+1])
            item_root = find_node_by_path(ui_tree, item_path)
            break
    
    # 鍦╥tem_root涓煡鎵炬墍鏈夋枃鏈?    texts = []
    if item_root:
        texts = find_text_in_subtree(item_root, max_depth=5)
    
    # 濡傛灉娌℃湁鎵惧埌锛屽氨鍦ㄥ綋鍓嶈妭鐐圭殑瀛愭爲涓煡鎵?    if not texts:
        texts = find_text_in_subtree(node, max_depth=3)
    
    # 鏄剧ず缁撴灉
    print(f"\n{i+1:2d}. {name}")
    if texts:
        # 杩囨护鎺夌函鏁板瓧鍜屽お鐭殑鏂囨湰
        meaningful_texts = [t for t in texts if len(t) > 1 and not t.replace('.', '').isdigit()]
        if meaningful_texts:
            print(f"    涓枃鍚嶇О: {meaningful_texts[0]}")
            if len(meaningful_texts) > 1:
                print(f"    鍏朵粬鏂囨湰: {' | '.join(meaningful_texts[1:4])}")
        else:
            print(f"    鏂囨湰: {' | '.join(texts[:3])}")
    else:
        print(f"    鏂囨湰: (鏃犳枃鏈?")
    
    # 鏄剧ず璺緞鐨勬渶鍚?0涓瓧绗?    path_short = path[-60:] if len(path) > 60 else path
    print(f"    璺緞: ...{path_short}")

print("\n" + "=" * 100)
print("\n瀹屾垚锛?)

