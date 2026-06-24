#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
鍦║I鏍戜腑鎼滅储鎵€鏈塼ext瀛楁
"""
import json

# 璇诲彇UI鏍?with open(as_abs_path("reports/runtime_capture/ui_tree_20260611_120143.json"), 'r', encoding='utf-8') as f:
    data = json.load(f)

print("鎼滅储UI鏍戜腑鐨勬墍鏈塼ext瀛楁...\n")

texts_found = []

def find_texts(obj, path=''):
    """閫掑綊鏌ユ壘鎵€鏈塼ext瀛楁"""
    if isinstance(obj, dict):
        # 妫€鏌ユ槸鍚︽湁text瀛楁涓斾笉涓虹┖
        if 'text' in obj and obj['text']:
            texts_found.append({
                'path': path,
                'text': obj['text'],
                'name': obj.get('name', '')
            })
        
        # 閫掑綊妫€鏌ユ墍鏈夊瓧娈?        for key, value in obj.items():
            find_texts(value, path + '.' + key)
    
    elif isinstance(obj, list):
        # 閫掑綊妫€鏌ュ垪琛ㄤ腑鐨勬瘡涓厓绱?        for i, item in enumerate(obj):
            find_texts(item, path + '[' + str(i) + ']')

# 鎼滅储
find_texts(data)

print(f"鎵惧埌 {len(texts_found)} 涓猼ext瀛楁\n")
print("=" * 80)

# 鏄剧ず鍓?0涓?for i, item in enumerate(texts_found[:50]):
    print(f"{i+1:2d}. 鏂囨湰: {item['text']:<30} | 鑺傜偣鍚? {item['name']}")
    # 鍙樉绀鸿矾寰勭殑鏈€鍚?0涓瓧绗?    path_short = item['path'][-60:] if len(item['path']) > 60 else item['path']
    print(f"    璺緞: ...{path_short}")
    print()

print("=" * 80)
print(f"鎬诲叡鎵惧埌 {len(texts_found)} 涓猼ext瀛楁")

