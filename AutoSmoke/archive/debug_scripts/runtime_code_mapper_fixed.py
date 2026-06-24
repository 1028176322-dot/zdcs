#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行时UI与客户端代码智能映射系统 (修复版)
自动识别当前Unity界面，定位对应的C#代码，提取所有可点击项
"""

import sys
import os
import json
import time
import re
import socket
from datetime import datetime
from collections import defaultdict
from pathlib import Path

print("=" * 60)
print("🎯 运行时UI与代码智能映射系统 (修复版)")
print("=" * 60)

# 配置路径
STATIC_JSON = r"E:\zdcs\AutoSmoke\reports\static_ui\static_ui_analysis_20260611_095903.json"
SCRIPTS_ROOT = r"UNITY_PROJECT_PATH"  # TODO: 从配置读取

class RuntimeCodeMapper:
    """运行时UI与代码映射器"""
    
    def __init__(self, static_json, scripts_root):
        self.static_data = self._load_json(static_json, "静态分析")
        self.scripts_root = scripts_root
        self.runtime_ui_tree = None
        self.current_ui_class = None
        self.mapping_results = []
        self.all_runtime_nodes = []  # 存储所有运行时节点
        
    def _load_json(self, file_path, description):
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ 已加载{description}: {file_path}")
            return data
        except Exception as e:
            print(f"❌ 加载{description}失败: {e}")
            return None
    
    def capture_runtime_ui(self):
        """捕获运行时UI树"""
        print("\n" + "=" * 60)
        print("📱 正在捕获运行时UI树...")
        print("=" * 60)
        
        try:
            # 连接到Poco RPC服务器
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', 5001))
            print("✅ TCP连接成功!")
            
            # 发送Dump请求
            request = {
                "jsonrpc": "2.0",
                "method": "Dump",
                "params": [True],
                "id": 1
            }
            
            request_json = json.dumps(request)
            request_bytes = request_json.encode('utf-8')
            
            # Poco协议: 前4字节是长度 (小端)
            length_bytes = len(request_bytes).to_bytes(4, byteorder='little')
            
            # 发送请求
            sock.send(length_bytes + request_bytes)
            print(f"   ✅ 已发送Dump请求")
            
            # 接收响应
            # 先接收4字节长度
            length_bytes = sock.recv(4)
            if len(length_bytes) == 4:
                response_length = int.from_bytes(length_bytes, byteorder='little')
                print(f"   响应长度: {response_length} 字节")
                
                # 接收响应数据
                response_bytes = b''
                while len(response_bytes) < response_length:
                    chunk = sock.recv(response_length - len(response_bytes))
                    if not chunk:
                        break
                    response_bytes += chunk
                
                response_json = response_bytes.decode('utf-8')
                response = json.loads(response_json)
                
                print(f"   ✅ 收到响应!")
                
                # 解析UI树
                if 'result' in response:
                    self.runtime_ui_tree = response['result']
                    print(f"   UI树获取成功!")
                    
                    # 保存UI树
                    output_dir = str(Path(__file__).parent.parent / 'reports' / 'runtime_capture')
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, f"runtime_ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(self.runtime_ui_tree, f, ensure_ascii=False, indent=2)
                    print(f"   UI树已保存: {output_file}")
                    
                    sock.close()
                    return self.runtime_ui_tree
                else:
                    print(f"   ⚠️ 响应格式异常: {response}")
                    sock.close()
                    return None
            else:
                print(f"   ❌ 接收响应长度失败")
                sock.close()
                return None
                
        except Exception as e:
            print(f"❌ 捕获失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_all_nodes(self, node, depth=0):
        """递归提取所有UI节点"""
        if not node:
            return
        
        node_name = node.get('name', 'Unknown')
        node_type = node.get('type', '')
        
        # 收集节点信息
        self.all_runtime_nodes.append({
            'name': node_name,
            'type': node_type,
            'depth': depth,
            'path': node.get('path', '')
        })
        
        # 递归处理子节点
        children = node.get('children', [])
        for child in children:
            self._extract_all_nodes(child, depth + 1)
    
    def identify_current_ui(self):
        """识别当前显示的UI界面 - 改进版"""
        if not self.runtime_ui_tree:
            print("❌ 没有运行时UI树数据")
            return None
        
        print("\n" + "=" * 60)
        print("🔍 识别当前UI界面...")
        print("=" * 60)
        
        # 提取所有运行时节点
        self.all_runtime_nodes = []
        self._extract_all_nodes(self.runtime_ui_tree)
        
        print(f"提取到 {len(self.all_runtime_nodes)} 个UI节点")
        
        # 获取所有运行时节点名称 (小写)
        runtime_node_names = set()
        for node in self.all_runtime_nodes:
            runtime_node_names.add(node['name'].lower())
        
        # 改进匹配算法
        best_match = None
        best_match_score = 0
        
        for ui_class in self.static_data:
            class_name = ui_class['class']
            file_path = ui_class['file']
            
            score = 0
            
            # 1. 检查类名是否出现在运行时节点中
            class_name_lower = class_name.lower()
            for node_name in runtime_node_names:
                if class_name_lower in node_name or node_name in class_name_lower:
                    score += 10  # 类名匹配权重高
            
            # 2. 检查可点击元素的likely_name_in_ui是否出现在运行时节点中
            ui_names = set()
            for elem in ui_class.get('clickable_elements', []):
                name = elem.get('likely_name_in_ui', '').lower()
                if name:
                    ui_names.add(name)
            
            matches = ui_names & runtime_node_names
            score += len(matches) * 5  # 每个匹配的元素加5分
            
            # 3. 检查常见主城界面关键词
            main_city_keywords = ['maincity', 'home', 'city', '主城', '主页', 'main']
            for keyword in main_city_keywords:
                if keyword in class_name.lower():
                    score += 20  # 主城关键词权重很高
                    break
            
            # 4. 检查文件名是否包含主城相关关键词
            file_lower = file_path.lower()
            for keyword in main_city_keywords:
                if keyword in file_lower:
                    score += 15
                    break
            
            # 5. 特殊处理：如果类名包含"MainCity"，直接高分
            if 'maincity' in class_name.lower():
                score += 50
            
            if score > best_match_score:
                best_match = ui_class
                best_match_score = score
        
        if best_match and best_match_score > 0:
            self.current_ui_class = best_match
            print(f"\n✅ 识别到当前UI界面:")
            print(f"   类名: {best_match['class']}")
            print(f"   文件: {best_match['file']}")
            print(f"   可点击元素: {len(best_match.get('clickable_elements', []))} 个")
            print(f"   事件绑定: {len(best_match.get('event_bindings', []))} 个")
            print(f"   匹配分数: {best_match_score}")
            return best_match
        else:
            print(f"\n⚠️ 未能识别当前UI界面")
            print(f"   可能的原因:")
            print(f"   1. 静态分析数据不完整")
            print(f"   2. 当前界面是动态生成的UI")
            print(f"   3. UI类名与节点名不匹配")
            
            # 尝试列出所有可能的UI类
            print(f"\n可能的UI类 (前10个):")
            for i, ui_class in enumerate(self.static_data[:10]):
                print(f"   {i+1}. {ui_class['class']} ({ui_class['file']})")
            
            return None
    
    def extract_clickable_elements(self):
        """提取当前UI的所有可点击元素"""
        if not self.current_ui_class:
            print("❌ 没有识别到当前UI类")
            return []
        
        print("\n" + "=" * 60)
        print("🎯 提取可点击元素...")
        print("=" * 60)
        
        ui_class = self.current_ui_class
        clickable_elements = ui_class.get('clickable_elements', [])
        event_bindings = ui_class.get('event_bindings', [])
        
        # 合并可点击元素和事件绑定
        results = []
        
        # 处理可点击元素
        for elem in clickable_elements:
            result = {
                'field_name': elem.get('field_name', ''),
                'type': elem.get('type', ''),
                'likely_name_in_ui': elem.get('likely_name_in_ui', ''),
                'handler': elem.get('handler', ''),
                'source': 'clickable_elements'
            }
            results.append(result)
        
        # 处理事件绑定 (可能包含额外的可点击元素)
        for binding in event_bindings:
            # 检查是否已经存在
            target = binding.get('target', '')
            handler = binding.get('handler', '')
            
            # 尝试在results中查找
            found = False
            for res in results:
                if res['field_name'] == target or res['likely_name_in_ui'] == target:
                    found = True
                    # 更新handler
                    if handler and not res['handler']:
                        res['handler'] = handler
                    break
            
            if not found:
                result = {
                    'field_name': target,
                    'type': binding.get('type', ''),
                    'likely_name_in_ui': target,
                    'handler': handler,
                    'source': 'event_bindings'
                }
                results.append(result)
        
        print(f"✅ 提取到 {len(results)} 个可点击元素/事件")
        
        self.mapping_results = results
        return results
    
    def locate_source_code(self):
        """定位源代码文件"""
        if not self.current_ui_class:
            print("❌ 没有识别到当前UI类")
            return None
        
        print("\n" + "=" * 60)
        print("📁 定位源代码文件...")
        print("=" * 60)
        
        file_path = self.current_ui_class['file']
        full_path = os.path.join(self.scripts_root, file_path)
        
        if os.path.exists(full_path):
            print(f"✅ 找到源代码文件:")
            print(f"   {full_path}")
            
            # 读取源代码
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                print(f"   文件大小: {len(source_code)} 字节")
                print(f"   行数: {len(source_code.splitlines())} 行")
                
                return {
                    'file_path': full_path,
                    'source_code': source_code,
                    'lines': source_code.splitlines()
                }
                
            except UnicodeDecodeError:
                try:
                    with open(full_path, 'r', encoding='gbk') as f:
                        source_code = f.read()
                    
                    print(f"   文件大小: {len(source_code)} 字节")
                    print(f"   行数: {len(source_code.splitlines())} 行")
                    
                    return {
                        'file_path': full_path,
                        'source_code': source_code,
                        'lines': source_code.splitlines()
                    }
                    
                except Exception as e:
                    print(f"❌ 读取文件失败: {e}")
                    return None
        else:
            print(f"❌ 源代码文件不存在: {full_path}")
            return None
    
    def generate_report(self):
        """生成映射报告"""
        if not self.current_ui_class or not self.mapping_results:
            print("❌ 没有足够的数据生成报告")
            return None
        
        print("\n" + "=" * 60)
        print("📊 生成映射报告...")
        print("=" * 60)
        
        # 创建报告目录
        output_dir = str(Path(__file__).parent.parent / 'reports' / 'ui_code_mapping')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成HTML报告
        html_path = os.path.join(output_dir, f"ui_code_mapping_{timestamp}.html")
        self._generate_html_report(html_path, timestamp)
        
        # 生成JSON报告
        json_path = os.path.join(output_dir, f"ui_code_mapping_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'ui_class': self.current_ui_class,
                'mapping_results': self.mapping_results,
                'timestamp': timestamp
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已生成:")
        print(f"   HTML: {html_path}")
        print(f"   JSON: {json_path}")
        
        return html_path, json_path
    
    def _generate_html_report(self, output_path, timestamp):
        """生成HTML报告"""
        ui_class = self.current_ui_class
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>UI与代码映射报告 - {timestamp}</title>
            <style>
                body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .summary {{ background: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .element {{ 
                    background: #ecf0f1; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-left: 4px solid #3498db;
                    border-radius: 3px;
                }}
                .element:hover {{ box-shadow: 0 5px 15px rgba(0,0,0,0.2); }}
                .element-name {{ font-weight: bold; color: #2980b9; font-size: 1.1em; }}
                .handler {{ color: #27ae60; font-family: monospace; }}
                .event-type {{ color: #e74c3c; font-size: 0.9em; }}
                .source-code {{ background: #2c3e50; color: #ecf0f1; padding: 10px; border-radius: 3px; overflow-x: auto; }}
                .code-line {{ font-family: monospace; white-space: pre-wrap; }}
                .file-path {{ color: #7f8c8d; font-size: 0.9em; font-family: monospace; }}
                pre {{ background: #2c3e50; color: #ecf0f1; padding: 10px; border-radius: 3px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎯 UI与代码映射报告</h1>
                <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p>自动识别当前Unity界面，定位对应的C#代码</p>
            </div>
            
            <div class="summary">
                <h2>📊 映射摘要</h2>
                <p><strong>UI类名:</strong> {ui_class['class']}</p>
                <p><strong>基类:</strong> {ui_class['base_class']}</p>
                <p><strong>源代码文件:</strong> <span class="file-path">{ui_class['file']}</span></p>
                <p><strong>可点击元素:</strong> {len(self.mapping_results)} 个</p>
                <p><strong>事件绑定:</strong> {len(ui_class.get('event_bindings', []))} 个</p>
            </div>
            
            <h2>🎯 可点击元素列表</h2>
        """
        
        for i, elem in enumerate(self.mapping_results):
            html_content += f"""
            <div class="element">
                <div class="element-name">[{i+1}] {elem['field_name']}</div>
                <p><strong>类型:</strong> <span class="event-type">{elem['type']}</span></p>
                <p><strong>UI中可能名称:</strong> <code>{elem['likely_name_in_ui']}</code></p>
                {f'<p><strong>事件处理:</strong> <span class="handler">{elem["handler"]}</span></p>' if elem.get('handler') else ''}
                <p><strong>来源:</strong> {elem['source']}</p>
            </div>
            """
        
        # 添加事件绑定详情
        if ui_class.get('event_bindings'):
            html_content += """
            <h2>🔗 事件绑定详情</h2>
            <pre>
            """
            
            for binding in ui_class['event_bindings']:
                html_content += f"{binding['type']}: {binding['target']} -> {binding['handler']}\n"
            
            html_content += """
            </pre>
            """
        
        html_content += """
            <hr>
            <p><em>报告生成工具: Runtime Code Mapper v1.1 (修复版)</em></p>
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


def main():
    """主函数"""
    print("=" * 60)
    print("🎯 运行时UI与代码智能映射系统")
    print("   自动识别当前Unity界面，定位对应的C#代码")
    print("=" * 60)
    
    # 检查静态分析文件
    if not os.path.exists(STATIC_JSON):
        print(f"❌ 错误: 静态分析文件不存在 {STATIC_JSON}")
        print("请先运行 static_ui_analyzer.py 生成静态分析报告")
        return
    
    # 创建映射器
    mapper = RuntimeCodeMapper(STATIC_JSON, SCRIPTS_ROOT)
    
    # 步骤1: 捕获运行时UI树
    runtime_ui_tree = mapper.capture_runtime_ui()
    if not runtime_ui_tree:
        print("\n❌ 捕获运行时UI树失败")
        print("请确认:")
        print("  1. Unity Editor正在运行")
        print("  2. 游戏已在Unity中启动 (Play模式)")
        print("  3. Poco SDK已正确部署")
        return
    
    # 步骤2: 识别当前UI界面
    current_ui = mapper.identify_current_ui()
    if not current_ui:
        print("\n⚠️ 未能识别当前UI界面")
        print("将尝试显示所有可能的UI类...")
        
        # 显示所有可能的UI类
        print(f"\n静态分析中发现 {len(mapper.static_data)} 个UI类:")
        for i, ui_class in enumerate(mapper.static_data[:10]):  # 只显示前10个
            print(f"  {i+1}. {ui_class['class']} ({ui_class['file']})")
        
        return
    
    # 步骤3: 提取可点击元素
    results = mapper.extract_clickable_elements()
    
    # 步骤4: 定位源代码
    source_info = mapper.locate_source_code()
    
    # 步骤5: 生成报告
    html_path, json_path = mapper.generate_report()
    
    print(f"\n✅ 映射完成!")
    print(f"   报告: {html_path}")
    
    # 自动打开报告
    try:
        os.startfile(html_path)
    except:
        pass


if __name__ == "__main__":
    main()
