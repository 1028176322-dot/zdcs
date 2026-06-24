#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
Poco Unity杩炴帴娴嬭瘯 - 浣跨敤auto_setup
"""

import sys
import os
import time
import json

def test_poco_connection():
    """娴嬭瘯Poco杩炴帴"""
    print("=" * 80)
    print("Poco Unity杩炴帴娴嬭瘯 - 浣跨敤auto_setup")
    print("=" * 80)
    
    try:
        # 瀵煎叆airtest骞惰嚜鍔ㄨ缃幆澧?        print("\n瀵煎叆airtest骞惰嚜鍔ㄨ缃幆澧?..")
        from airtest.core.api import auto_setup
        # 鑷姩璁剧疆鐜锛岃繖浼氬垵濮嬪寲璁惧
        auto_setup(__file__)
        print("  鉁?鐜鑷姩璁剧疆鎴愬姛")
        
        # 瀵煎叆poco
        print("\n瀵煎叆poco妯″潡...")
        from poco.drivers.unity3d import UnityPoco
        
        # 鍒涘缓UnityPoco瀹炰緥
        print("鍒涘缓UnityPoco瀹炰緥...")
        poco = UnityPoco()
        
        # 绛夊緟Poco鍒濆鍖?        print("绛夊緟Poco鍒濆鍖?..")
        time.sleep(2)
        
        # 鑾峰彇UI鏍?- 浣跨敤姝ｇ‘鐨勬柟娉?        print("\n鑾峰彇UI鏍?..")
        
        # 鏂规硶1: 浣跨敤poco.agent.rpc.call('Dump')
        try:
            ui_tree = poco.agent.rpc.call('Dump')
            print(f"  鉁?鏂规硶1鎴愬姛: 浣跨敤rpc.call('Dump')")
        except Exception as e1:
            print(f"  鉂?鏂规硶1澶辫触: {e1}")
            
            # 鏂规硶2: 浣跨敤poco()鑾峰彇鏍硅妭鐐?            try:
                root = poco()
                ui_tree = root.attribute
                print(f"  鉁?鏂规硶2鎴愬姛: 浣跨敤poco()鑾峰彇鏍硅妭鐐?)
            except Exception as e2:
                print(f"  鉂?鏂规硶2澶辫触: {e2}")
                print("  鉂?鎵€鏈夋柟娉曢兘澶辫触浜?)
                return False
        
        # 淇濆瓨鍒版枃浠?        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = as_abs_path("reports/runtime_capture/ui_tree_{timestamp}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ui_tree, f, ensure_ascii=False, indent=2)
        
        print(f"\n  鉁?UI鏍戝凡淇濆瓨鍒? {output_file}")
        
        # 鏌ユ壘鍙偣鍑诲厓绱?        print("\n鏌ユ壘鍙偣鍑诲厓绱?..")
        clickable_elements = []
        
        def traverse(node, path=""):
            if not node:
                return
            
            # 妫€鏌ュ綋鍓嶈妭鐐规槸鍚﹀彲鐐瑰嚮
            name = node.get("name", "")
            node_type = node.get("type", "")
            clickable = node.get("clickable", False)
            
            # 鏋勫缓鑺傜偣璺緞
            current_path = f"{path}/{name}" if path else name
            
            # 濡傛灉鑺傜偣鍙偣鍑伙紝娣诲姞鍒板垪琛?            if clickable or "Button" in node_type or "button" in name.lower():
                clickable_elements.append({
                    "name": name,
                    "type": node_type,
                    "path": current_path,
                    "clickable": clickable
                })
            
            # 閫掑綊閬嶅巻瀛愯妭鐐?            children = node.get("children", [])
            for child in children:
                traverse(child, current_path)
        
        traverse(ui_tree)
        
        print(f"  鉁?鎵惧埌 {len(clickable_elements)} 涓彲鐐瑰嚮鍏冪礌:")
        for i, element in enumerate(clickable_elements[:20]):  # 鍙樉绀哄墠20涓?            print(f"    {i+1}. {element['name']} ({element['type']}) - {element['path']}")
        
        if len(clickable_elements) > 20:
            print(f"    ... 杩樻湁 {len(clickable_elements) - 20} 涓厓绱?)
        
        return True
        
    except Exception as e:
        print(f"\n鉂?娴嬭瘯澶辫触: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_poco_connection()


