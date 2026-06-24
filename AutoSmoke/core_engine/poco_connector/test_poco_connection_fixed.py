#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
Poco (?
?001
"""

import sys
import os
import time
import json
import socket

sys.path.append(as_abs_path(""))

print("=" * 60)
print(" Poco (?")
print("=" * 60)

# 1: ?001
print("\n1: oco SDK?(5001)...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 5001))
    if result == 0:
        print("?Poco SDK (5001?")
    else:
        print("?Poco SDK?(5001?")
        print("   nityPlay")
    sock.close()
except Exception as e:
    print(f"  ? {e}")

# 2: TCPPC
print("\n2: TCPPoco RPC?..")
try:
    # oco RPC?    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 5001))
    print("?TCP!")
    
    # ump
    request = {
        "jsonrpc": "2.0",
        "method": "Dump",
        "params": [True],
        "id": 1
    }
    
    request_json = json.dumps(request)
    request_bytes = request_json.encode('utf-8')
    
    # Poco: ??()
    length_bytes = len(request_bytes).to_bytes(4, byteorder='little')
    
    # ?    sock.send(length_bytes + request_bytes)
    print(f"   ?ump")
    
    # 
    # ?
    length_bytes = sock.recv(4)
    if len(length_bytes) == 4:
        response_length = int.from_bytes(length_bytes, byteorder='little')
        print(f"   : {response_length} ")
        
        # 
        response_bytes = b''
        while len(response_bytes) < response_length:
            chunk = sock.recv(response_length - len(response_bytes))
            if not chunk:
                break
            response_bytes += chunk
        
        response_json = response_bytes.decode('utf-8')
        response = json.loads(response_json)
        
        print(f"   ?!")
        
        # UI?        if 'result' in response:
            ui_tree = response['result']
            print(f"   UI?")
            
            # UI?            output_dir = as_abs_path("reports/runtime_capture")
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"runtime_ui_{time.strftime('%Y%m%d_%H%M%S')}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(ui_tree, f, ensure_ascii=False, indent=2)
            print(f"   UI: {output_file}")
            
            print("\n?Poco!")
            print("    runtime UI ?)
        else:
            print(f"     : {response}")
    else:
        print(f"   ?")
    
    sock.close()
    
except Exception as e:
    print(f"?TCP: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print(" ")
print("=" * 60)

# UI?runtime_file = None
runtime_dir = as_abs_path("reports/runtime_capture")
if os.path.exists(runtime_dir):
    files = [f for f in os.listdir(runtime_dir) if f.endswith('.json')]
    if files:
        runtime_file = os.path.join(runtime_dir, max(files, key=lambda f: os.path.getmtime(os.path.join(runtime_dir, f))))

if runtime_file:
    print(f"\nI: {runtime_file}")
    print("UI...")
    print(f"   python ui_comparator_simple.py")

