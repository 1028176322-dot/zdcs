#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
Poco
oco
"""

import sys
import os
import time

# Poco
sys.path.append(as_abs_path(""))

print("=" * 60)
print(" Poco")
print("=" * 60)

# 1: nityPoco SDK
print("\n1: oco SDK?..")
try:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 50051))
    if result == 0:
        print("?Poco SDK (50051?")
        print("   nityPoco SDK?)
    else:
        print("?Poco SDK?(50051?")
        print("   ?")
        print("   1. Unity Editor")
        print("   2. Unity?(Play)")
        print("   3. Poco SDK?)
    sock.close()
except Exception as e:
    print(f"  ? {e}")

# 2: Poco
print("\n2: Poco?..")
try:
    from poco.drivers.unity3d import UnityPoco
    print("?Poco?)
    poco_available = True
except ImportError as e:
    print(f"?Poco? {e}")
    print("   ? pip install poco airtest")
    poco_available = False

# 3: ?if poco_available:
    print("\n3: ?..")
    
    # 1: UnityPoco()
    print("\n1: UnityPoco() ()...")
    try:
        poco = UnityPoco()
        print("?1!")
        print(f"   Poco: {poco.version if hasattr(poco, 'version') else 'Unknown'}")
        
        # UI?        print("   UI?..")
        ui_tree = poco.agent.hierarchy.dump()
        print(f"   ?UI?")
        
        # 
        import json
        output_dir = as_abs_path("reports/runtime_capture")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"runtime_ui_{time.strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ui_tree, f, ensure_ascii=False, indent=2)
        print(f"   UI: {output_file}")
        
        poco.stop()
        print("?! Poco")
        sys.exit(0)
        
    except Exception as e1:
        print(f"?1: {e1}")
        
        # 2: UnityPoco(device=None)
        print("\n2: UnityPoco(device=None)...")
        try:
            poco = UnityPoco(device=None)
            print("?2!")
            print(f"   Poco: {poco.version if hasattr(poco, 'version') else 'Unknown'}")
            
            # UI?            print("   UI?..")
            ui_tree = poco.agent.hierarchy.dump()
            print(f"   ?UI?")
            
            # 
            import json
            output_dir = as_abs_path("reports/runtime_capture")
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"runtime_ui_{time.strftime('%Y%m%d_%H%M%S')}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(ui_tree, f, ensure_ascii=False, indent=2)
            print(f"   UI: {output_file}")
            
            poco.stop()
            print("?! Poco")
            sys.exit(0)
            
        except Exception as e2:
            print(f"?2: {e2}")
            
            # 3: rpc?            print("\n3: RPC?..")
            try:
                from poco.drivers.unity3d.unity3d_poco import UnityRpcClient
                client = UnityRpcClient('127.0.0.1', 50051)
                print("?RPC?")
                
                # UI?                print("   UI?..")
                ui_tree = client.dump_hierarchy()
                print(f"   ?UI?(RPC?!")
                
                # 
                import json
                output_dir = as_abs_path("reports/runtime_capture")
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, f"runtime_ui_{time.strftime('%Y%m%d_%H%M%S')}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(ui_tree, f, ensure_ascii=False, indent=2)
                print(f"   UI: {output_file}")
                
                client.close()
                print("?! RPC?)
                sys.exit(0)
                
            except Exception as e3:
                print(f"?3: {e3}")
                
                # 
                print("\n?!")
                print("   ?")
                print("   1. Poco SDKUnity?)
                print("   2. Unitylay")
                print("   3. Poco SDK (AutoStartPoco.cs)")
                print("   4. 50051")
                print("\n   nityPoco")

print("\n" + "=" * 60)
print(" ")
print("=" * 60)

