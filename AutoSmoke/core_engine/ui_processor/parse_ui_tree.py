#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
姝ｇ‘鑾峰彇骞惰В鏋怭oco UI鏍?"""
import sys
import time
import json

# 瀵煎叆airtest
from airtest.core.api import connect_device, auto_setup
print("鉁?airtest瀵煎叆鎴愬姛")

# 鍒濆鍖朼irtest
auto_setup(__file__)
print("鉁?airtest鍒濆鍖栨垚鍔?)

# 杩炴帴Windows璁惧
print("\n杩炴帴Windows璁惧...")
connect_device('Windows://')
print("鉁?Windows璁惧杩炴帴鎴愬姛")

# 瀵煎叆骞跺垱寤篣nityPoco
from poco.drivers.unity3d import UnityPoco
print("\n鍒涘缓UnityPoco瀹炰緥...")
poco = UnityPoco()
print("鉁?UnityPoco瀹炰緥鍒涘缓鎴愬姛")

# 绛夊緟Poco杩炴帴
print("\n绛夊緟Poco杩炴帴...")
time.sleep(2)

# 浣跨敤poco.dump()鑾峰彇UI鏍?print("\n鑾峰彇UI鏍?..")
ui_tree = poco.dump()
print(f"鉁?UI鏍戣幏鍙栨垚鍔?)
print(f"  鏁版嵁绫诲瀷: {type(ui_tree)}")

# 淇濆瓨UI鏍戝埌鏂囦欢
timestamp = time.strftime("%Y%m%d_%H%M%S")
output_file = as_abs_path("reports/runtime_capture/ui_tree_{timestamp}.json")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(ui_tree, f, ensure_ascii=False, indent=2)
print(f"鉁?UI鏍戝凡淇濆瓨鍒? {output_file}")

# 瑙ｆ瀽UI鏍戯紝鎻愬彇鎵€鏈夊彲鐐瑰嚮鍏冪礌
print("\n瑙ｆ瀽UI鏍戯紝鎻愬彇鍙偣鍑诲厓绱?..")

def find_clickable_elements(node, path="", clickable_elements=[]):
    """閫掑綊鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌"""
    if not isinstance(node, dict):
        return clickable_elements
    
    # 妫€鏌ュ綋鍓嶈妭鐐规槸鍚﹀彲鐐瑰嚮
    payload = node.get('payload', {})
    if payload.get('clickable') == True:
        clickable_elements.append({
            'name': payload.get('name', ''),
            'path': path + '/' + node.get('name', ''),
            'type': payload.get('type', ''),
            'text': payload.get('text', ''),
            'components': payload.get('components', [])
        })
    
    # 閫掑綊鏌ユ壘瀛愯妭鐐?    children = node.get('children', [])
    for child in children:
        find_clickable_elements(child, path + '/' + node.get('name', ''), clickable_elements)
    
    return clickable_elements

# 鏌ユ壘鎵€鏈夊彲鐐瑰嚮鍏冪礌
clickable_elements = find_clickable_elements(ui_tree)
print(f"\n鉁?鎵惧埌 {len(clickable_elements)} 涓彲鐐瑰嚮鍏冪礌")

# 淇濆瓨鍒版枃浠?clickable_file = as_abs_path("reports/runtime_capture/clickable_elements_{timestamp}.json")
with open(clickable_file, 'w', encoding='utf-8') as f:
    json.dump(clickable_elements, f, ensure_ascii=False, indent=2)
print(f"鉁?鍙偣鍑诲厓绱犲凡淇濆瓨鍒? {clickable_file}")

# 鏄剧ず鍓?0涓彲鐐瑰嚮鍏冪礌
print(f"\n鍓?0涓彲鐐瑰嚮鍏冪礌:")
for i, elem in enumerate(clickable_elements[:20]):
    print(f"  {i+1}. {elem['name']} (path: {elem['path']})")

print("\n" + "=" * 60)
print("瀹屾垚")
print("=" * 60)


