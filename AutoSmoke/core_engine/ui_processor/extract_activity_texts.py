#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
绠€鍖栫増锛氱洿鎺ユ彁鍙朥I鏍戜腑鐨勬墍鏈変腑鏂囨枃鏈紝骞跺叧鑱斿埌鏈€杩戠殑鍙偣鍑诲厓绱?"""
import json
import re

# 璇诲彇UI鏍?with open(as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json"), 'r', encoding='utf-8') as f:
    ui_tree = json.load(f)

print("鎻愬彇UI鏍戜腑鐨勪腑鏂囨枃鏈?..\n")

# 瀛樺偍鎵€鏈夋枃鏈強鍏惰矾寰?texts_with_paths = []

def collect_texts(obj, path="", current_item_root=""):
    """鏀堕泦鎵€鏈夋枃鏈瓧娈靛強鍏惰矾寰?""
    if not isinstance(obj, dict):
        return
    
    node_name = obj.get('name', '')
    
    # 鏇存柊current_item_root
    if '(Clone)' in node_name:
        current_item_root = path + '/' + node_name
    
    # 妫€鏌ayload涓殑鏂囨湰
    payload = obj.get('payload', {})
    text_fields = ['text', 'title', 'txt', 'txt1', 'Title', 'Txtdesc', 'name']
    
    for field in text_fields:
        if field in payload and payload[field]:
            value = payload[field]
            if isinstance(value, str) and value.strip():
                # 娓呯悊HTML鏍囩
                cleaned = re.sub(r'<[^>]+>', '', value).strip()
                if cleaned and len(cleaned) > 1 and not cleaned.replace('.', '').isdigit():
                    # 妫€鏌ユ槸鍚﹀寘鍚腑鏂囧瓧绗?                    if any('\u4e00' <= c <= '\u9fff' for c in cleaned):
                        texts_with_paths.append({
                            'text': cleaned,
                            'path': path + '/' + node_name,
                            'item_root': current_item_root,
                            'is_clickable': payload.get('clickable', False)
                        })
    
    # 閫掑綊妫€鏌ュ瓙鑺傜偣
    for child in obj.get('children', []):
        collect_texts(child, path + '/' + node_name, current_item_root)

# 鏀堕泦鎵€鏈夋枃鏈?collect_texts(ui_tree)

print(f"鎵惧埌 {len(texts_with_paths)} 涓腑鏂囨枃鏈琝n")

# 鎸塱tem_root鍒嗙粍
texts_by_item = {}
for item in texts_with_paths:
    item_root = item['item_root']
    if item_root not in texts_by_item:
        texts_by_item[item_root] = []
    texts_by_item[item_root].append(item)

print("=" * 100)
print("鎸夊垪琛ㄩ」鍒嗙粍鐨勪腑鏂囨枃鏈?\n")

# 鏄剧ず缁撴灉
for i, (item_root, texts) in enumerate(texts_by_item.items()):
    # 鎻愬彇item鍚嶇О
    item_name = item_root.split('/')[-1] if item_root else 'Unknown'
    
    print(f"\n{i+1}. {item_name}")
    
    # 鏄剧ず鎵€鏈夋枃鏈?    for text_item in texts:
        if text_item['is_clickable']:
            print(f"    [鍙偣鍑籡 {text_item['text']}")
        else:
            print(f"    {text_item['text']}")
    
    # 鍙樉绀哄墠10涓猧tem
    if i >= 10:
        print(f"\n... 杩樻湁 {len(texts_by_item) - 10} 涓垪琛ㄩ」")
        break

print("\n" + "=" * 100)

# 淇濆瓨鍒版枃浠?output_file = as_abs_path("reports/runtime_capture/activity_texts.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(texts_by_item, f, ensure_ascii=False, indent=2)

print(f"\n鉁?缁撴灉宸蹭繚瀛樺埌: {output_file}")
print("\n瀹屾垚锛?)

