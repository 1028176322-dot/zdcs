#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
姝ｇ‘鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О
閫氳繃閬嶅巻鏃惰褰曠埗鑺傜偣寮曠敤鏉ユ煡鎵惧厔寮熻妭鐐逛腑鐨勬枃鏈?"""
import json

# 璇诲彇UI鏍?with open(as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json"), 'r', encoding='utf-8') as f:
    ui_tree = json.load(f)

print("瑙ｆ瀽UI鏍戯紝鎻愬彇鍙偣鍑诲厓绱犵殑涓枃鍚嶇О...\n")

def find_all_texts_in_node(node):
    """鍦ㄨ妭鐐圭殑鎵€鏈夊瓙鑺傜偣涓煡鎵炬枃鏈?""
    texts = []
    if not isinstance(node, dict):
        return texts
    
    # 妫€鏌ュ綋鍓嶈妭鐐圭殑payload
    payload = node.get('payload', {})
    text_fields = ['text', 'title', 'txt', 'txt1', 'Title', 'Txtdesc', 'name']
    
    for field in text_fields:
        if field in payload and payload[field]:
            value = payload[field]
            if isinstance(value, str) and value.strip():
                # 娓呯悊HTML鏍囩
                import re
                cleaned = re.sub(r'<[^>]+>', '', value).strip()
                if cleaned and cleaned not in texts:
                    texts.append(cleaned)
    
    # 閫掑綊妫€鏌ュ瓙鑺傜偣
    for child in node.get('children', []):
        texts.extend(find_all_texts_in_node(child))
    
    return texts

def find_clickable_with_context(node, parent=None, path="", results=None, depth=0):
    """鏌ユ壘鍙偣鍑诲厓绱狅紝骞惰褰曠埗鑺傜偣寮曠敤"""
    if results is None:
        results = []
    
    if not isinstance(node, dict):
        return results
    
    payload = node.get('payload', {})
    
    # 妫€鏌ユ槸鍚﹀彲鐐瑰嚮
    if payload.get('clickable') == True:
        # 鏌ユ壘鐖惰妭鐐癸紙Item(Clone)鎴栫被浼肩殑鍒楄〃椤瑰鍣級
        ancestor = parent
        item_root = None
        
        # 鍚戜笂鏌ユ壘鍖呭惈"(Clone)"鐨勭埗鑺傜偣锛堥€氬父鏄垪琛ㄩ」瀹瑰櫒锛?        while ancestor:
            ancestor_name = ancestor.get('name', '')
            if '(Clone)' in ancestor_name:
                item_root = ancestor
                break
            # 涔熸鏌ョ鐖惰妭鐐?            if parent and isinstance(parent, dict)):
                for child in parent.get('children', []):
                    if child == node:
                        # 鎵惧埌浜嗭紝鐜板湪鏌ユ壘parent鐨勭埗鑺傜偣
                        pass
                break
        
        # 绠€鍖栵細鐩存帴鍦ㄧ埗鑺傜偣涓煡鎵炬墍鏈夋枃鏈?        texts = []
        if parent:
            texts = find_all_texts_in_node(parent)
        
        results.append({
            'name': payload.get('name', ''),
            'texts': texts,
            'path': path + '/' + node.get('name', ''),
            'parent_name': parent.get('name', '') if parent else ''
        })
    
    # 閫掑綊妫€鏌ュ瓙鑺傜偣锛屼紶閫掑綋鍓嶈妭鐐逛綔涓虹埗鑺傜偣
    for child in node.get('children', []):
        find_clickable_with_context(child, node, path + '/' + node.get('name', ''), results, depth + 1)
    
    return results

# 鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌
print("鏌ユ壘鍙偣鍑诲厓绱?..")
clickable_elements = find_clickable_with_context(ui_tree)

print(f"鉁?鎵惧埌 {len(clickable_elements)} 涓彲鐐瑰嚮鍏冪礌\n")
print("=" * 100)

# 鏄剧ず缁撴灉
for i, elem in enumerate(clickable_elements):
    print(f"\n{i+1:2d}. {elem['name']}")
    if elem['texts']:
        # 杩囨护鎺夌函鏁板瓧鍜屽お鐭殑鏂囨湰锛屼紭鍏堟樉绀轰腑鏂?        meaningful_texts = [t for t in elem['texts'] if len(t) > 1 and not t.replace('.', '').isdigit()]
        if meaningful_texts:
            print(f"    涓枃鍚嶇О: {meaningful_texts[0]}")
            if len(meaningful_texts) > 1:
                print(f"    鍏朵粬鏂囨湰: {' | '.join(meaningful_texts[1:3])}")
        else:
            print(f"    鏂囨湰: {elem['texts'][0]}")
    else:
        print(f"    鏂囨湰: (鏃犳枃鏈?")
    
    print(f"    鐖惰妭鐐? {elem['parent_name']}")
    path_short = elem['path'][-70:] if len(elem['path']) > 70 else elem['path']
    print(f"    璺緞: ...{path_short}")

print("\n" + "=" * 100)

# 淇濆瓨鍒版枃浠?output_file = as_abs_path("reports/runtime_capture/clickable_with_chinese.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(clickable_elements, f, ensure_ascii=False, indent=2)

print(f"\n鉁?缁撴灉宸蹭繚瀛樺埌: {output_file}")
print("\n瀹屾垚锛?)

