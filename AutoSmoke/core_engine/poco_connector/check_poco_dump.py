#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
oco dump()?"""
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

# ump()?print("\n" + "=" * 60)
print("ump()?)
print("=" * 60)

try:
    # dump()
    print("\npoco.dump()...")
    dump_data = poco.dump()
    print(f"?dump()")
    print(f"  : {type(dump_data)}")
    print(f"  : {dump_data}")
    print(f"  : {len(str(dump_data))} ")
    
    # dump_data?    if isinstance(dump_data, dict):
        print(f"\n  dump()?")
        print(f"  ? {list(dump_data.keys())}")
        
        # ?        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = as_abs_path("reports/runtime_capture/ui_dump_{timestamp}.json")
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dump_data, f, ensure_ascii=False, indent=2)
        print(f"  ?dump: {output_file}")
    
    # 
    print("\n...")
    root = poco()
    print(f"  ? {root}")
    
    try:
        children = root.children()
        print(f"  ? {len(children)}")
        
        if len(children) > 0:
            print("\n  ?:")
            for i, child in enumerate(children[:5]):
                try:
                    name = child.attr('name')
                    print(f"    {i+1}. {name}")
                except:
                    print(f"    {i+1}. ()")
    except Exception as e:
        print(f"   ? {e}")
    
    print("\n" + "=" * 60)
    print("?)
    print("=" * 60)
    
except Exception as e:
    print(f"\n?? {e}")
    import traceback
    traceback.print_exc()


