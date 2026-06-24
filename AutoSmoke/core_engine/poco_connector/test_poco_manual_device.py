#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
Poco Unity - ?"""

import sys
import time
import json

def test_poco_connection():
    """Poco"""
    print("=" * 80)
    print("Poco Unity - ?)
    print("=" * 80)
    
    try:
        # airtest
        print("\nairtest...")
        from airtest.core.api import connect_device, init_device
        
        # 1: connect_device
        try:
            print("  1: connect_device('Windows://')...")
            device = connect_device('Windows://')
            print(f"  ?: {device}")
        except Exception as e1:
            print(f"  ?1: {e1}")
            
            # 2: init_device
            try:
                print("  2: init_device('Windows')...")
                init_device('Windows')
                print("  ??)
            except Exception as e2:
                print(f"  ?2: {e2}")
                print("  ??)
                return False
        
        # poco
        print("\npoco...")
        from poco.drivers.unity3d import UnityPoco
        
        # UnityPoco
        print("UnityPoco...")
        poco = UnityPoco()
        
        # Poco?        print("Poco?..")
        time.sleep(2)
        
        # UI?- ?        print("\nUI?..")
        
        # 1: poco.agent.rpc.call('Dump')
        try:
            ui_tree = poco.agent.rpc.call('Dump')
            print(f"  ?1: rpc.call('Dump')")
        except Exception as e1:
            print(f"  ?1: {e1}")
            
            # 2: poco()?            try:
                root = poco()
                ui_tree = root.attribute
                print(f"  ?2: poco()?)
            except Exception as e2:
                print(f"  ?2: {e2}")
                print("  ??)
                return False
        
        # ?        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = as_abs_path("reports/runtime_capture/ui_tree_{timestamp}.json")
        
        # UISON
        def convert_to_serializable(obj):
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                return str(obj)
            else:
                return obj
        
        serializable_ui_tree = convert_to_serializable(ui_tree)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_ui_tree, f, ensure_ascii=False, indent=2)
        
        print(f"\n  ?UI? {output_file}")
        
        # ?        print("\n?..")
        clickable_elements = []
        
        def traverse(node, path=""):
            if not node:
                return
            
            # 
            name = node.get("name", "")
            node_type = node.get("type", "")
            clickable = node.get("clickable", False)
            
            # 
            current_path = f"{path}/{name}" if path else name
            
            # ?            if clickable or "Button" in node_type or "button" in name.lower():
                clickable_elements.append({
                    "name": name,
                    "type": node_type,
                    "path": current_path,
                    "clickable": clickable
                })
            
            # ?            children = node.get("children", [])
            for child in children:
                traverse(child, current_path)
        
        traverse(ui_tree)
        
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


