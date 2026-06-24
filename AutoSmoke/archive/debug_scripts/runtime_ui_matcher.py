#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用运行时UI树辅助识别当前界面
通过socket直接连接Poco RPC服务器，获取UI树
"""

import socket
import json
import time
from difflib import get_close_matches

class PocoRPCSocketClient:
    """通过socket直接连接Poco RPC服务器"""
    
    def __init__(self, host='127.0.0.1', port=5001):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        """连接RPC服务器"""
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
    
    def get_ui_tree(self):
        """获取UI树"""
        print("📡 正在获取UI树...")
        result = self.send_rpc_request("Dump")
        if result:
            print(f"✅ 获取UI树成功")
            return result
        else:
            print("❌ 获取UI树失败")
            return None
    
    def get_ui_tree_nodes(self):
        """获取UI树并返回所有节点名称"""
        ui_tree = self.get_ui_tree()
        if not ui_tree:
            return []
        
        node_names = []
        
        def traverse(node):
            if not node or not isinstance(node, dict):
                return
            
            name = node.get("name", "")
            if name:
                node_names.append(name)
            
            children = node.get("children", [])
            for child in children:
                traverse(child)
        
        traverse(ui_tree)
        return node_names

def load_static_analysis_results(json_file):
    """加载静态分析结果"""
    print(f"📂 加载静态分析结果: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    print(f"✅ 加载了 {len(results)} 个UI类")
    return results

def find_matching_ui_class(ui_tree_nodes, static_results):
    """根据UI树节点名称，找出最匹配的UI类"""
    print("\n🔍 根据UI树节点名称，查找最匹配的UI类...")
    
    # 提取所有UI类的名称
    ui_class_names = [result['ui_class'] for result in static_results]
    
    # 统计每个UI类在UI树节点中出现的次数
    ui_class_scores = {}
    
    for node_name in ui_tree_nodes:
        # 移除特殊字符，转换为小写
        clean_node_name = node_name.lower().replace('_', '').replace(' ', '')
        
        # 查找匹配的UI类
        for ui_class in ui_class_names:
            clean_ui_class = ui_class.lower().replace('_', '').replace(' ', '')
            
            # 如果UI类名出现在节点名称中，或者节点名称出现在UI类名中
            if clean_ui_class in clean_node_name or clean_node_name in clean_ui_class:
                if ui_class not in ui_class_scores:
                    ui_class_scores[ui_class] = 0
                ui_class_scores[ui_class] += 1
    
    # 按分数排序
    sorted_ui_classes = sorted(ui_class_scores.items(), key=lambda x: x[1], reverse=True)
    
    print(f"✅ 找到 {len(sorted_ui_classes)} 个可能匹配的UI类")
    
    # 返回匹配的UI类和对应的静态分析结果
    matched_results = []
    for ui_class, score in sorted_ui_classes:
        for result in static_results:
            if result['ui_class'] == ui_class:
                matched_results.append((result, score))
                break
    
    return matched_results

def display_matching_results(matched_results, top_n=10):
    """显示匹配结果"""
    print(f"\n📊 最匹配的UI类 (前{top_n}个):")
    for i, (result, score) in enumerate(matched_results[:top_n]):
        print(f"  {i+1}. {result['ui_class']} (匹配分数: {score})")
        print(f"     文件: {result['file']}")
        print(f"     可点击元素: {len(result['clickable_elements'])} 个")

def generate_matching_report(matched_results, output_file):
    """生成匹配报告"""
    print(f"\n📝 生成匹配报告: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("运行时UI树与静态分析匹配报告\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"找到 {len(matched_results)} 个可能匹配的UI类\n\n")
        
        for i, (result, score) in enumerate(matched_results):
            f.write("-" * 80 + "\n")
            f.write(f"[{i+1}] UI类: {result['ui_class']} (匹配分数: {score})\n")
            f.write(f"    文件: {result['file']}\n")
            f.write(f"    基类: {result['base_class']}\n")
            f.write(f"    可点击元素: {len(result['clickable_elements'])} 个\n\n")
            
            if result['clickable_elements']:
                f.write("    可点击元素:\n")
                for j, elem in enumerate(result['clickable_elements']):
                    f.write(f"      {j+1}. {elem['field_name']} ({elem['type']})\n")
                    f.write(f"          UI中可能名称: {elem['likely_name_in_ui']}\n")
                    if 'handler' in elem and elem['handler'] != 'Unknown':
                        f.write(f"          事件处理: {elem['handler']}\n")
                f.write("\n")
    
    print(f"✅ 报告已生成: {output_file}")

def main():
    """主函数"""
    print("=" * 80)
    print("运行时UI树辅助识别当前界面")
    print("=" * 80)
    
    # 静态分析结果文件
    json_file = r"E:\zdcs\AutoSmoke\reports\static_ui\static_ui_analysis_20260611_111322.json"
    
    # 加载静态分析结果
    static_results = load_static_analysis_results(json_file)
    
    # 创建RPC客户端
    client = PocoRPCSocketClient(host='127.0.0.1', port=5001)
    
    # 连接到RPC服务器
    if not client.connect():
        print("❌ 无法连接到Poco RPC服务器")
        print("请确保:")
        print("  1. Unity编辑器正在运行")
        print("  2. Poco SDK已正确导入")
        print("  3. Poco RPC服务器已启动（默认端口5001）")
        return
    
    try:
        # 获取UI树节点名称
        ui_tree_nodes = client.get_ui_tree_nodes()
        
        if not ui_tree_nodes:
            print("❌ 无法获取UI树节点")
            return
        
        print(f"✅ 获取了 {len(ui_tree_nodes)} 个UI树节点")
        
        # 找出最匹配的UI类
        matched_results = find_matching_ui_class(ui_tree_nodes, static_results)
        
        if not matched_results:
            print("\n❌ 未找到匹配的UI类")
            print("可能的原因:")
            print("  1. UI树节点名称与UI类名称不匹配")
            print("  2. 当前界面不是主城界面")
            print("  3. 静态分析结果不完整")
            return
        
        # 显示匹配结果
        display_matching_results(matched_results, top_n=20)
        
        # 生成匹配报告
        output_file = r"E:\zdcs\AutoSmoke\reports\runtime_ui_matching\matching_report.txt"
        generate_matching_report(matched_results, output_file)
        
        # 显示第一个匹配UI类的详细信息
        if matched_results:
            print("\n" + "=" * 80)
            print("第一个匹配UI类的详细信息:")
            result, score = matched_results[0]
            print(f"UI类: {result['ui_class']}")
            print(f"文件: {result['file']}")
            print(f"基类: {result['base_class']}")
            print(f"可点击元素数量: {len(result['clickable_elements'])}")
            
            if result['clickable_elements']:
                print("\n可点击元素:")
                for i, elem in enumerate(result['clickable_elements']):
                    print(f"  {i+1}. {elem['field_name']} ({elem['type']})")
                    print(f"      UI中可能名称: {elem['likely_name_in_ui']}")
                    if 'handler' in elem and elem['handler'] != 'Unknown':
                        print(f"      事件处理: {elem['handler']}")
        
    finally:
        # 断开连接
        client.disconnect()

if __name__ == "__main__":
    main()
