#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
Poco Unity - oco API
"""

import sys
import time
import json

def test_poco_connection():
    """Poco"""
    print("=" * 80)
    print("Poco Unity - oco API")
    print("=" * 80)
    
    try:
        # airtest
        print("\nairtest...")
        from airtest.core.api import connect_device
        
        # connect_device
        print("  connect_device('Windows://')...")
        device = connect_device('Windows://')
        print(f"  ?: {device}")
        
        # poco
        print("\npoco...")
        from poco.drivers.unity3d import UnityPoco
        
        # UnityPoco
        print("UnityPoco...")
        poco = UnityPoco()
        
        # Poco?        print("Poco?..")
        time.sleep(2)
        
        # UI?- poco()?        print("\nUI?..")
        
        # poco()?        root = poco()
        print(f"  ?? {root}")
        
        # I
        print("  UI...")
        
        def node_to_dict(node):
            """oco?- PI"""
            result = {}
            
            try:
                # ?- attr()
                result["name"] = node.attr('name')
                result["type"] = node.attr('type')
                result["clickable"] = node.attr('clickable')
                result["text"] = node.attr('text')
                result["enabled"] = node.attr('enabled')
                result["visible"] = node.attr('visible')
                
                # ?                children = []
                for child in node.children():
                    children.append(node_to_dict(child))
                
                result["children"] = children
            except Exception as e:
                print(f"     ? {e}")
            
            return result
        
        ui_tree = node_to_dict(root)
        
        # ?        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = as_abs_path("reports/runtime_capture/ui_tree_{timestamp}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ui_tree, f, ensure_ascii=False, indent=2)
        
        print(f"\n  ?UI? {output_file}")
        
        # ?        print("\n?..")
        clickable_elements = []
        
        def find_clickable(node, path=""):
            """?""
            if not node:
                return
            
            # 
            name = node.get("name", "")
            node_type = node.get("type", "")
            clickable = node.get("clickable", False)
            
            # 
            current_path = f"{path}/{name}" if path else name
            
            # ?            if clickable or "Button" in str(node_type) or "button" in str(name).lower():
                clickable_elements.append({
                    "name": name,
                    "type": node_type,
                    "path": current_path,
                    "clickable": clickable
                })
            
            # ?            children = node.get("children", [])
            for child in children:
                find_clickable(child, current_path)
        
        find_clickable(ui_tree)
        
        print(f"  ? {len(clickable_elements)} :")
        for i, element in enumerate(clickable_elements[:20]):  # 20?            print(f"    {i+1}. {element['name']} ({element['type']}) - {element['path']}")
        
        if len(clickable_elements) > 20:
            print(f"    ...  {len(clickable_elements) - 20} ?)
        
        return True
        
    except Exception as e:
        print(f"\n?: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_poco_connection()


