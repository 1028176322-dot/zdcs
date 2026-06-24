#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
Poco RPC?- 
"""

import socket
import json
import time

class PocoRPCClientWithTimeout:
    """Poco RPC?- ?""
    
    def __init__(self, host='127.0.0.1', port=5001, timeout=60):
        self.host = host
        self.port = port
        self.timeout = timeout  # ?        self.socket = None
    
    def connect(self):
        """oco RPC?""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)  # ?            self.socket.connect((self.host, self.port))
            print(f"?Poco RPC? {self.host}:{self.port} (: {self.timeout}?")
            return True
        except Exception as e:
            print(f"?: {e}")
            return False
    
    def disconnect(self):
        """"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("?")
    
    def send_request(self, method, params=None):
        """SON-RPC"""
        if not self.socket:
            print("??)
            return None
        
        request_id = int(time.time() * 1000)
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": request_id
        }
        
        try:
            # ?            request_str = json.dumps(request) + "\n"
            self.socket.sendall(request_str.encode('utf-8'))
            
            # ?            response_str = b""
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response_str += chunk
                    if b"\n" in chunk:
                        break
                except socket.timeout:
                    print(f"   ...")
                    continue
            
            if not response_str:
                print(f"  ?")
                return None
            
            response = json.loads(response_str.decode('utf-8'))
            
            if "error" in response:
                print(f"  ?RPC: {response['error']}")
                return None
            
            return response.get("result")
            
        except socket.timeout:
            print(f"  ? (>{self.timeout}?")
            return None
        except Exception as e:
            print(f"  ?: {e}")
            return None
    
    def get_ui_tree(self):
        """UI?""
        print(f" UI?.. (: {self.timeout}?")
        print("  ?...")
        result = self.send_request("Dump")
        if result:
            print(f"  ?UI?)
            return result
        else:
            print(f"  ?UI?)
            return None

def main():
    """?""
    print("=" * 80)
    print("Poco RPC?- ")
    print("=" * 80)
    
    # 60?    client = PocoRPCClientWithTimeout(host='127.0.0.1', port=5001, timeout=60)
    
    # 
    if not client.connect():
        print("?oco RPC?)
        print("")
        print("1. Unity?)
        print("2. Poco SDK?)
        print("3. Poco RPC?001?)
        return
    
    try:
        # UI?        ui_tree = client.get_ui_tree()
        if ui_tree:
            # ?            timestamp = time.strftime("%Y%m%d_%H%M%S")
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
            
            # 
            node_count = [0]
            def count_nodes(node):
                if not node:
                    return
                node_count[0] += 1
                children = node.get('children', [])
                for child in children:
                    count_nodes(child)
            
            count_nodes(serializable_ui_tree)
            print(f"  ?UI?{node_count[0]} ?)
        else:
            print("\n?UI?)
            print("?")
            print("1. Dump")
            print("2. UnityPoco SDK?)
            print("3. ")
            
    finally:
        # 
        client.disconnect()

if __name__ == "__main__":
    main()


