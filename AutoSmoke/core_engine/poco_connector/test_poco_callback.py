#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
娴嬭瘯Poco杩炴帴 - 浣跨敤Callback.get()鑾峰彇UI鏍?"""
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

# 灏濊瘯鑾峰彇UI鏍?- 浣跨敤Callback.get()
print("\n鑾峰彇UI鏍?..")
print("   (浣跨敤Callback.get()鑾峰彇瀹為檯鏁版嵁...)")

try:
    # 浣跨敤rpc.call('Dump')鑾峰彇UI鏍?    callback = poco.agent.rpc.call('Dump')
    print(f"鉁?RPC璋冪敤鎴愬姛")
    print(f"  Callback瀵硅薄: {callback}")
    
    # 浣跨敤callback.get()鑾峰彇瀹為檯鏁版嵁
    print("\n  绛夊緟RPC杩斿洖缁撴灉...")
    ui_tree = callback.get()
    print(f"鉁?UI鏍戞暟鎹幏鍙栨垚鍔?)
    print(f"  UI鏍戠被鍨? {type(ui_tree)}")
    
    if isinstance(ui_tree, dict):
        print(f"  UI鏍戦敭: {list(ui_tree.keys())[:10]}")
    
    # 淇濆瓨鍒版枃浠?    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = as_abs_path("reports/runtime_capture/ui_tree_{timestamp}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(ui_tree, f, ensure_ascii=False, indent=2)
    print(f"鉁?UI鏍戝凡淇濆瓨鍒? {output_file}")
    
    # 灏濊瘯浣跨敤poco()鑾峰彇鏍硅妭鐐?    print("\n灏濊瘯浣跨敤poco()鑾峰彇鏍硅妭鐐?..")
    root = poco()
    print(f"鉁?鏍硅妭鐐硅幏鍙栨垚鍔?)
    
    # 鏌ヨ鎵€鏈夎妭鐐?    print("\n鏌ヨ鎵€鏈塙I鑺傜偣...")
    all_nodes = poco('//*')
    print(f"  鎵惧埌 {len(all_nodes)} 涓妭鐐?)
    
    if len(all_nodes) > 0:
        print("\n鍓?0涓妭鐐?")
        for i, node in enumerate(all_nodes[:10]):
            try:
                name = node.attr('name')
                print(f"  {i+1}. {name}")
            except:
                print(f"  {i+1}. (鏃犳硶鑾峰彇鍚嶇О)")
    else:
        print("\n鈿狅笍 鏈壘鍒颁换浣昒I鑺傜偣")
        print("  鍙兘鐨勫師鍥狅細")
        print("  1. Unity娓告垙涓病鏈塙I鍏冪礌")
        print("  2. Poco SDK娌℃湁姝ｇ‘璇嗗埆UI鍏冪礌")
        print("  3. UI鍏冪礌娌℃湁姝ｇ‘鐨勫睘鎬?)
    
    print("\n" + "=" * 60)
    print("娴嬭瘯瀹屾垚")
    print("=" * 60)
    
except Exception as e:
    print(f"\n鉂?鑾峰彇UI鏍戝け璐? {e}")
    import traceback
    traceback.print_exc()


