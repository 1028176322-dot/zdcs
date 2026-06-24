#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
Poco RPC?- Poco RPC?irtestocosocketSON-RPC
"""

import socket
import json
import time
from typing import Dict, List, Any, Optional

class PocoRPCClient:
    """Poco RPC?""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5001):
        self.host = host
        self.port = port
        self.socket = None
        self.request_id = 0
        
    def connect(self) -> bool:
        """oco RPC?""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            print(f"?Poco RPC? {self.host}:{self.port}")
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
    
    def send_request(self, method: str, params: List[Any] = None) -> Optional[Dict]:
        """SON-RPC"""
        if not self.socket:
            print("??)
            return None
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": self.request_id
        }
        
        try:
            # ?            request_str = json.dumps(request) + "\n"
            self.socket.sendall(request_str.encode('utf-8'))
            
            # 
            response_str = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response_str += chunk
                if b"\n" in chunk:
                    break
            
            response = json.loads(response_str.decode('utf-8'))
            
            if "error" in response:
                print(f"?RPC: {response['error']}")
                return None
            
            return response.get("result")
            
        except Exception as e:
            print(f"?: {e}")
            return None
    
    def get_ui_tree(self) -> Optional[Dict]:
        """UI?""
        print(" UI?..")
        result = self.send_request("GetUI Tree")
        if result:
            print(f"?UI?)
            return result
        else:
            print("?UI?)
            return None
    
    def dump_ui_tree(self, filepath: str):
        """UI"""
        ui_tree = self.get_ui_tree()
        if ui_tree:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(ui_tree, f, ensure_ascii=False, indent=2)
            print(f"?UI? {filepath}")
        else:
            print("?UI?)
    
    def find_clickable_elements(self, ui_tree: Dict) -> List[Dict]:
        """I?""
        clickable_elements = []
        
        def traverse(node: Dict, path: str = ""):
            if not node or not isinstance(node, dict):
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
        return clickable_elements

def main():
    """?""
    print("=" * 80)
    print("Poco RPC?)
    print("=" * 80)
    
    # ?    client = PocoRPCClient(host='127.0.0.1', port=5001)
    
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
            client.dump_ui_tree(output_file)
            
            # ?            clickable_elements = client.find_clickable_elements(ui_tree)
            print(f"\n? {len(clickable_elements)} :")
            for i, element in enumerate(clickable_elements[:20]):  # 20?                print(f"  {i+1}. {element['name']} ({element['type']}) - {element['path']}")
            
            if len(clickable_elements) > 20:
                print(f"  ...  {len(clickable_elements) - 20} ?)
        
    finally:
        # 
        client.disconnect()

if __name__ == "__main__":
    main()


