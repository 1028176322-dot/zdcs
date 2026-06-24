#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poco诊断工具 - 检查Poco在Unity中的实际状态
"""

import socket
import json
import time

class PocoDiagnostics:
    """Poco诊断工具"""
    
    def __init__(self, host='127.0.0.1', port=5001):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        """连接到Poco RPC服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            print(f"✅ 已连接到Poco RPC服务器: {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("✅ 已断开连接")
    
    def send_rpc_request(self, method, params=None):
        """发送RPC请求"""
        if not self.socket:
            print("❌ 未连接到服务器")
            return None
        
        request_id = int(time.time() * 1000)
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": request_id
        }
        
        try:
            # 发送请求
            request_str = json.dumps(request) + "\n"
            self.socket.sendall(request_str.encode('utf-8'))
            
            # 接收响应
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
                print(f"❌ RPC错误: {response['error']}")
                return None
            
            return response.get("result")
            
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
    
    def check_poco_status(self):
        """检查Poco状态"""
        print("\n" + "=" * 80)
        print("检查Poco状态")
        print("=" * 80)
        
        # 1. 检查RPC连接
        print("\n1. 检查RPC连接...")
        if not self.socket:
            print("   ❌ 未连接到RPC服务器")
            return False
        print("   ✅ RPC连接正常")
        
        # 2. 检查Dump方法
        print("\n2. 检查Dump方法...")
        dump_result = self.send_rpc_request("Dump")
        if dump_result:
            print(f"   ✅ Dump方法正常")
            print(f"   Dump结果类型: {type(dump_result)}")
            
            # 检查Dump结果的结构
            if isinstance(dump_result, dict):
                print(f"   Dump结果键: {list(dump_result.keys())}")
                
                # 检查是否有children
                if 'children' in dump_result:
                    children_count = len(dump_result.get('children', []))
                    print(f"   根节点子节点数量: {children_count}")
                    
                    if children_count > 0:
                        print("   ✅ UI树非空")
                        return True
                    else:
                        print("   ⚠️ UI树为空（没有子节点）")
                else:
                    print("   ⚠️ Dump结果中没有'children'键")
            else:
                print(f"   ⚠️ Dump结果不是字典类型")
        else:
            print("   ❌ Dump方法失败")
            return False
        
        # 3. 检查GetSDKVersion方法
        print("\n3. 检查GetSDKVersion方法...")
        version = self.send_rpc_request("GetSDKVersion")
        if version:
            print(f"   ✅ Poco SDK版本: {version}")
        else:
            print("   ⚠️ 无法获取Poco SDK版本")
        
        # 4. 检查Screenshot方法
        print("\n4. 检查Screenshot方法...")
        screenshot = self.send_rpc_request("Screenshot")
        if screenshot:
            print(f"   ✅ Screenshot方法正常")
        else:
            print("   ⚠️ Screenshot方法失败")
        
        return False
    
    def analyze_dump_result(self, dump_result, max_depth=3):
        """分析Dump结果"""
        print("\n" + "=" * 80)
        print("分析Dump结果")
        print("=" * 80)
        
        if not dump_result:
            print("❌ Dump结果为空")
            return
        
        # 统计节点数量
        node_count = [0]  # 使用列表以便在递归中修改
        
        def count_nodes(node, depth=0):
            if not node or depth > max_depth:
                return
            
            node_count[0] += 1
            
            # 打印节点信息
            if depth <= 2:  # 只打印前几层
                indent = "  " * depth
                name = node.get('name', '<unknown>')
                node_type = node.get('type', '<unknown>')
                print(f"{indent}节点: {name} ({node_type})")
            
            # 递归遍历子节点
            children = node.get('children', [])
            for child in children:
                count_nodes(child, depth + 1)
        
        count_nodes(dump_result)
        print(f"\n✅ 共找到 {node_count[0]} 个节点")
    
    def suggest_fixes(self):
        """建议修复方法"""
        print("\n" + "=" * 80)
        print("建议的修复方法")
        print("=" * 80)
        
        print("\n根据诊断结果，可能的修复方法:")
        print("\n1. 检查Unity场景状态:")
        print("   - 确保游戏已经加载到主城界面")
        print("   - 确保UI已经完全加载")
        print("   - 尝试重新加载场景")
        
        print("\n2. 检查Poco SDK初始化:")
        print("   - 检查AutoStartPoco.cs是否正确执行")
        print("   - 检查PocoManager GameObject是否存在")
        print("   - 查看Unity控制台日志，确认Poco初始化成功")
        
        print("\n3. 检查UI系统:")
        print("   - 确认游戏使用的是UGUI还是其他UI系统")
        print("   - 检查UI元素是否有正确的组件")
        
        print("\n4. 尝试重启:")
        print("   - 重启Unity编辑器")
        print("   - 重新运行游戏")
        print("   - 重新连接Poco")

def main():
    """主函数"""
    print("=" * 80)
    print("Poco诊断工具")
    print("=" * 80)
    
    # 创建诊断工具
    diagnostics = PocoDiagnostics(host='127.0.0.1', port=5001)
    
    # 连接到RPC服务器
    if not diagnostics.connect():
        print("❌ 无法连接到Poco RPC服务器")
        print("\n请确保:")
        print("  1. Unity编辑器正在运行")
        print("  2. Poco SDK已正确导入")
        print("  3. Poco RPC服务器已启动（默认端口5001）")
        return
    
    try:
        # 检查Poco状态
        status_ok = diagnostics.check_poco_status()
        
        if status_ok:
            # 如果状态正常，分析Dump结果
            dump_result = diagnostics.send_rpc_request("Dump")
            diagnostics.analyze_dump_result(dump_result)
        else:
            # 如果状态不正常，建议修复方法
            diagnostics.suggest_fixes()
        
    finally:
        # 断开连接
        diagnostics.disconnect()

if __name__ == "__main__":
    main()
