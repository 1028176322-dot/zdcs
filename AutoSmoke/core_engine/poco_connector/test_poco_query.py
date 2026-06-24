#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
Poco - UI
"""
import sys
import time

# airtest
from airtest.core.api import connect_device, auto_setup
print("?airtest")

# irtest
auto_setup(__file__)
print("?airtest?)

# Windows
print("\nWindows...")
connect_device('Windows://')
print("?Windows")

# nityPoco
from poco.drivers.unity3d import UnityPoco
print("\nUnityPoco...")
poco = UnityPoco()
print("?UnityPoco")

# Poco
print("\nPoco...")
time.sleep(2)

# UI
print("\n" + "=" * 60)
print("UI")
print("=" * 60)

try:
    # 1: ?    print("\n1: ?(poco('//*'))...")
    all_nodes = poco('//*')
    print(f"   {len(all_nodes)} ?)
    
    # 2: utton
    print("\n2: utton...")
    buttons = poco('//Button')
    print(f"   {len(buttons)} utton")
    
    # 3: ?"
    print("\n3: ''...")
    try:
        activity_elements = poco(text="")
        print(f"   {len(activity_elements)} ?'?)
    except Exception as e:
        print(f"   : {e}")
    
    # 4: 
    print("\n4: ?..")
    root = poco()
    print(f"  ? {root}")
    print(f"  ? {type(root)}")
    
    # 5: dump()?    print("\n5: poco.dump()...")
    try:
        ui_tree_str = poco.dump()
        print(f"  ?dump()")
        print(f"  : {len(ui_tree_str)} ")
        
        # ?        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = as_abs_path("reports/runtime_capture/ui_dump_{timestamp}.xml")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(ui_tree_str)
        print(f"  ?UI? {output_file}")
    except Exception as e:
        print(f"   dump(): {e}")
    
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)
    
except Exception as e:
    print(f"\n?: {e}")
    import traceback
    traceback.print_exc()


