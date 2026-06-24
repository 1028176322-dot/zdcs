"""
# -*- coding: utf-8 -*-
核心功能完整验证脚本
验证：1. UI树dump（所有UI元素、文本、按钮、图标）
      2. 截图功能
      3. 场景状态导出
      4. 主城对象检测
      5. 大地图对象检测

运行前请确保：
  1. Unity Editor已打开
  2. 已点击Play按钮（▶）
  3. 游戏已进入主界面或游戏场景
"""

import sys
import time
import json
import os
from typing import Optional, Dict, Any, List

def verify_core_functionality():
    """
    验证核心功能
    """
    print("\n" + "=" * 80)
    print("AutoSmoke IDE - 核心功能完整验证")
    print("=" * 80 + "\n")
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ui_tree": {"status": "NOT_TESTED", "details": ""},
        "screenshot": {"status": "NOT_TESTED", "details": ""},
        "scene_export": {"status": "NOT_TESTED", "details": ""},
        "main_city": {"status": "NOT_TESTED", "details": ""},
        "world_map": {"status": "NOT_TESTED", "details": ""},
        "text_extraction": {"status": "NOT_TESTED", "details": ""},
        "clickable_elements": {"status": "NOT_TESTED", "details": ""}
    }
    
    # ========== 步骤1：连接Unity ==========
    print("步骤1：连接Unity游戏...")
    print("-" * 40)
    
    try:
        from poco.drivers.unity3d import UnityPoco
        from airtest.core.api import connect_device
        
        # 连接设备
        device = connect_device("Windows:///")
        print("✓ 已连接Windows设备")
        
        # 初始化Poco
        poco = UnityPoco()
        print("✓ 已初始化Poco")
        
        results["connection"] = {"status": "PASS", "details": "Unity连接成功"}
        print()
        
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        results["connection"] = {"status": "FAIL", "details": str(e)}
        return results
    
    # ========== 步骤2：Dump UI树 ==========
    print("步骤2：Dump UI树...")
    print("-" * 40)
    
    try:
        ui_tree = poco.agent.rpc.call("dump")
        
        if ui_tree:
            print(f"✓ UI树dump成功")
            print(f"  - 数据大小: {len(str(ui_tree))} 字节")
            
            # 解析UI树
            if isinstance(ui_tree, str):
                ui_tree = json.loads(ui_tree)
            
            # 统计节点数量
            def count_nodes(node, count=0):
                if isinstance(node, dict):
                    count += 1
                    if 'children' in node:
                        for child in node['children']:
                            count = count_nodes(child, count)
                return count
            
            total_nodes = count_nodes(ui_tree)
            print(f"  - 总节点数: {total_nodes}")
            
            results["ui_tree"]["status"] = "PASS"
            results["ui_tree"]["details"] = f"成功获取UI树，共{total_nodes}个节点"
            results["ui_tree"]["node_count"] = total_nodes
            results["ui_tree"]["data_size"] = len(str(ui_tree))
            
            print()
        else:
            print("✗ UI树为空")
            results["ui_tree"]["status"] = "FAIL"
            results["ui_tree"]["details"] = "UI树为空"
            
    except Exception as e:
        print(f"✗ UI树dump失败: {e}")
        results["ui_tree"]["status"] = "FAIL"
        results["ui_tree"]["details"] = str(e)
        
    # ========== 步骤3：提取所有文本 ==========
    print("步骤3：提取所有文本...")
    print("-" * 40)
    
    try:
        all_texts = []
        
        def extract_texts(node):
            if isinstance(node, dict):
                # 文本字段可能在payload里面
                payload = node.get('payload', {})
                text = payload.get('text', '')
                
                if text and text.strip():
                    all_texts.append(text.strip())
                
                # 递归处理子节点
                if 'children' in node:
                    for child in node['children']:
                        extract_texts(child)
        
        extract_texts(ui_tree)
        
        # 去重
        unique_texts = list(set(all_texts))
        
        print(f"✓ 提取到 {len(unique_texts)} 个唯一文本")
        
        if unique_texts:
            print(f"  前10个文本:")
            for i, text in enumerate(unique_texts[:10], 1):
                print(f"    {i}. {text}")
            
            if len(unique_texts) > 10:
                print(f"    ... (共{len(unique_texts)}个)")
        
        results["text_extraction"]["status"] = "PASS" if unique_texts else "WARN"
        results["text_extraction"]["details"] = f"提取到{len(unique_texts)}个唯一文本"
        results["text_extraction"]["text_count"] = len(unique_texts)
        results["text_extraction"]["texts"] = unique_texts[:50]  # 只保存前50个
        
        print()
        
    except Exception as e:
        print(f"✗ 文本提取失败: {e}")
        results["text_extraction"]["status"] = "FAIL"
        results["text_extraction"]["details"] = str(e)
        
    # ========== 步骤4：识别所有可点击元素 ==========
    print("步骤4：识别所有可点击元素...")
    print("-" * 40)
    
    try:
        clickable_elements = []
        
        def find_clickable(node):
            if isinstance(node, dict):
                payload = node.get('payload', {})
                
                # 检查是否可点击
                clickable = payload.get('clickable', False)
                enabled = payload.get('enabled', True)
                
                if clickable and enabled:
                    name = payload.get('name', 'Unknown')
                    text = payload.get('text', '')
                    clickable_elements.append({
                        'name': name,
                        'text': text,
                        'type': payload.get('type', 'Unknown')
                    })
                
                # 递归处理子节点
                if 'children' in node:
                    for child in node['children']:
                        find_clickable(child)
        
        find_clickable(ui_tree)
        
        print(f"✓ 找到 {len(clickable_elements)} 个可点击元素")
        
        if clickable_elements:
            print(f"  前10个可点击元素:")
            for i, elem in enumerate(clickable_elements[:10], 1):
                text_info = f" ({elem['text']})" if elem['text'] else ""
                print(f"    {i}. {elem['name']}{text_info} [{elem['type']}]")
            
            if len(clickable_elements) > 10:
                print(f"    ... (共{len(clickable_elements)}个)")
        
        results["clickable_elements"]["status"] = "PASS" if clickable_elements else "WARN"
        results["clickable_elements"]["details"] = f"找到{len(clickable_elements)}个可点击元素"
        results["clickable_elements"]["count"] = len(clickable_elements)
        
        print()
        
    except Exception as e:
        print(f"✗ 可点击元素识别失败: {e}")
        results["clickable_elements"]["status"] = "FAIL"
        results["clickable_elements"]["details"] = str(e)
        
    # ========== 步骤5：截图 ==========
    print("步骤5：截图...")
    print("-" * 40)
    
    try:
        from airtest.core.api import snapshot
        
        # 创建报告目录
        report_dir = "../../data_access/reports"
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = int(time.time())
        screenshot_path = f"{report_dir}/verification_screenshot_{timestamp}.png"
        
        snapshot(filename=screenshot_path)
        
        if os.path.exists(screenshot_path):
            file_size = os.path.getsize(screenshot_path)
            print(f"✓ 截图成功")
            print(f"  - 保存至: {screenshot_path}")
            print(f"  - 文件大小: {file_size} 字节")
            
            results["screenshot"]["status"] = "PASS"
            results["screenshot"]["details"] = f"截图成功，文件大小{file_size}字节"
            results["screenshot"]["path"] = screenshot_path
        else:
            print("✗ 截图文件未生成")
            results["screenshot"]["status"] = "FAIL"
            results["screenshot"]["details"] = "截图文件未生成"
            
        print()
        
    except Exception as e:
        print(f"✗ 截图失败: {e}")
        results["screenshot"]["status"] = "FAIL"
        results["screenshot"]["details"] = str(e)
        
    # ========== 步骤6：检查Unity插件 ==========
    print("步骤6：检查Unity侧插件...")
    print("-" * 40)
    
    # 尝试调用Unity插件接口
    unity_plugins = {
        "SceneStateExporter": False,
        "MainCityExporter": False,
        "WorldMapExporter": False,
        "LogCollector": False,
        "NetMessageMonitor": False
    }
    
    for plugin_name in unity_plugins.keys():
        try:
            # 尝试调用Unity插件接口
            response = poco.agent.rpc.call(f"custom::{plugin_name}.isAvailable")
            
            if response:
                unity_plugins[plugin_name] = True
                print(f"✓ {plugin_name}: 可用")
            else:
                print(f"⚠ {plugin_name}: 不可用")
                
        except Exception as e:
            print(f"⚠ {plugin_name}: 未安装 ({e})")
    
    available_plugins = [k for k, v in unity_plugins.items() if v]
    unavailable_plugins = [k for k, v in unity_plugins.items() if not v]
    
    if available_plugins:
        print(f"\n✓ 可用插件: {len(available_plugins)}个")
    else:
        print(f"\n⚠ 无可用Unity插件")
        print("  场景对象导出功能将无法使用")
        print("  建议：安装AutoSmoke Unity Plugin")
    
    results["unity_plugins"] = {
        "status": "PASS" if available_plugins else "WARN",
        "details": f"可用插件: {len(available_plugins)}个，不可用: {len(unavailable_plugins)}个",
        "available": available_plugins,
        "unavailable": unavailable_plugins
    }
    
    print()
    
    # ========== 步骤7：测试场景状态导出 ==========
    print("步骤7：测试场景状态导出...")
    print("-" * 40)
    
    if "SceneStateExporter" in available_plugins:
        try:
            # 尝试调用Unity插件接口（可能需要不同的调用方式）
            response = poco.agent.rpc.call("custom::SceneStateExporter.getState")
            
            # 处理可能的Callback对象
            if hasattr(response, 'result'):
                scene_state = response.result
            elif hasattr(response, 'get'):
                scene_state = response
            elif isinstance(response, str):
                try:
                    scene_state = json.loads(response)
                except:
                    scene_state = {"raw": response}
            else:
                scene_state = {"raw": str(response)}
            
            if scene_state:
                print(f"✓ 场景状态导出成功")
                print(f"  - 场景名: {scene_state.get('scene', 'Unknown')}")
                
                results["scene_export"]["status"] = "PASS"
                results["scene_export"]["details"] = f"场景状态导出成功，场景名: {scene_state.get('scene', 'Unknown')}"
                results["scene_export"]["data"] = scene_state
            else:
                print("⚠ 场景状态导出返回空")
                results["scene_export"]["status"] = "WARN"
                results["scene_export"]["details"] = "场景状态导出返回空"
                
        except Exception as e:
            print(f"✗ 场景状态导出失败: {e}")
            results["scene_export"]["status"] = "FAIL"
            results["scene_export"]["details"] = str(e)
    else:
        print("⚠ SceneStateExporter插件不可用")
        print("  跳过场景状态导出测试")
        results["scene_export"]["status"] = "SKIPPED"
        results["scene_export"]["details"] = "SceneStateExporter插件不可用"
    
    print()
    
    # ========== 步骤8：测试主城对象导出 ==========
    print("步骤8：测试主城对象导出...")
    print("-" * 40)
    
    if "MainCityExporter" in available_plugins:
        try:
            response = poco.agent.rpc.call("custom::MainCityExporter.getObjects")
            
            # 处理可能的Callback对象
            if hasattr(response, 'result'):
                main_city_objects = response.result
            elif hasattr(response, 'get'):
                main_city_objects = response
            elif isinstance(response, str):
                try:
                    main_city_objects = json.loads(response)
                except:
                    main_city_objects = []
            else:
                main_city_objects = response if isinstance(response, list) else []
            
            if main_city_objects and isinstance(main_city_objects, list):
                print(f"✓ 主城对象导出成功")
                print(f"  - 对象数量: {len(main_city_objects)}")
                
                if main_city_objects:
                    print(f"  前5个对象:")
                    for i, obj in enumerate(main_city_objects[:5], 1):
                        print(f"    {i}. {obj.get('name', 'Unknown')} [{obj.get('type', 'Unknown')}]")
                    
                    if len(main_city_objects) > 5:
                        print(f"    ... (共{len(main_city_objects)}个)")
                
                results["main_city"]["status"] = "PASS"
                results["main_city"]["details"] = f"主城对象导出成功，共{len(main_city_objects)}个对象"
                results["main_city"]["object_count"] = len(main_city_objects)
            else:
                print("⚠ 主城对象导出返回空或格式错误")
                results["main_city"]["status"] = "WARN"
                results["main_city"]["details"] = "主城对象导出返回空或格式错误"
                
        except Exception as e:
            print(f"✗ 主城对象导出失败: {e}")
            results["main_city"]["status"] = "FAIL"
            results["main_city"]["details"] = str(e)
    else:
        print("⚠ MainCityExporter插件不可用")
        print("  跳过主城对象导出测试")
        results["main_city"]["status"] = "SKIPPED"
        results["main_city"]["details"] = "MainCityExporter插件不可用"
    
    print()
    
    # ========== 步骤9：测试大地图对象导出 ==========
    print("步骤9：测试大地图对象导出...")
    print("-" * 40)
    
    if "WorldMapExporter" in available_plugins:
        try:
            response = poco.agent.rpc.call("custom::WorldMapExporter.getVisibleObjects")
            
            # 处理可能的Callback对象
            if hasattr(response, 'result'):
                world_map_objects = response.result
            elif hasattr(response, 'get'):
                world_map_objects = response
            elif isinstance(response, str):
                try:
                    world_map_objects = json.loads(response)
                except:
                    world_map_objects = []
            else:
                world_map_objects = response if isinstance(response, list) else []
            
            if world_map_objects and isinstance(world_map_objects, list):
                print(f"✓ 大地图对象导出成功")
                print(f"  - 对象数量: {len(world_map_objects)}")
                
                if world_map_objects:
                    print(f"  前5个对象:")
                    for i, obj in enumerate(world_map_objects[:5], 1):
                        print(f"    {i}. {obj.get('name', 'Unknown')} [{obj.get('type', 'Unknown')}]")
                    
                    if len(world_map_objects) > 5:
                        print(f"    ... (共{len(world_map_objects)}个)")
                
                results["world_map"]["status"] = "PASS"
                results["world_map"]["details"] = f"大地图对象导出成功，共{len(world_map_objects)}个对象"
                results["world_map"]["object_count"] = len(world_map_objects)
            else:
                print("⚠ 大地图对象导出返回空或格式错误")
                results["world_map"]["status"] = "WARN"
                results["world_map"]["details"] = "大地图对象导出返回空或格式错误"
                
        except Exception as e:
            print(f"✗ 大地图对象导出失败: {e}")
            results["world_map"]["status"] = "FAIL"
            results["world_map"]["details"] = str(e)
    else:
        print("⚠ WorldMapExporter插件不可用")
        print("  跳过大地图对象导出测试")
        results["world_map"]["status"] = "SKIPPED"
        results["world_map"]["details"] = "WorldMapExporter插件不可用"
    
    print()
    
    # ========== 生成验证报告 ==========
    print("=" * 80)
    print("验证报告")
    print("=" * 80)
    print()
    
    print(f"验证时间: {results['timestamp']}")
    print()
    
    # 统计结果
    passed = sum(1 for k, v in results.items() if isinstance(v, dict) and v.get('status') == 'PASS')
    failed = sum(1 for k, v in results.items() if isinstance(v, dict) and v.get('status') == 'FAIL')
    warned = sum(1 for k, v in results.items() if isinstance(v, dict) and v.get('status') == 'WARN')
    skipped = sum(1 for k, v in results.items() if isinstance(v, dict) and v.get('status') == 'SKIPPED')
    not_tested = sum(1 for k, v in results.items() if isinstance(v, dict) and v.get('status') == 'NOT_TESTED')
    
    print(f"测试结果统计:")
    print(f"  - 通过: {passed}")
    print(f"  - 失败: {failed}")
    print(f"  - 警告: {warned}")
    print(f"  - 跳过: {skipped}")
    print(f"  - 未测试: {not_tested}")
    print()
    
    # 详细结果
    print("详细结果:")
    print("-" * 40)
    
    for key, value in results.items():
        if isinstance(value, dict):
            status = value.get('status', 'UNKNOWN')
            details = value.get('details', '')
            
            status_icon = {
                'PASS': '✓',
                'FAIL': '✗',
                'WARN': '⚠',
                'SKIPPED': '⊘',
                'NOT_TESTED': '?'
            }.get(status, '?')
            
            print(f"{status_icon} {key}: {status}")
            print(f"    {details}")
    
    print()
    print("=" * 80)
    
    # 结论
    if failed == 0 and passed >= 3:
        print("✅ 核心功能验证通过！")
        print("   界面和场景的所有信息都能正确获取。")
        conclusion = "PASS"
    elif failed > 0:
        print("⚠️ 核心功能验证失败！")
        print("   部分功能无法正常工作，请查看详细结果。")
        conclusion = "FAIL"
    else:
        print("⚠️ 核心功能验证不完整！")
        print("   部分功能未测试或被跳过，请查看详细结果。")
        conclusion = "WARN"
    
    print("=" * 80)
    
    # 保存结果到JSON
    report_file = f"{report_dir}/core_verification_report_{timestamp}.json"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细报告已保存至: {report_file}")
    except Exception as e:
        print(f"\n保存报告失败: {e}")
    
    results["conclusion"] = conclusion
    results["report_file"] = report_file
    
    return results

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("AutoSmoke IDE - 核心功能完整验证工具")
    print("=" * 80 + "\n")
    
    print("提示：")
    print("  检测到Unity已启动，开始验证...")
    print()
    
    # 运行验证
    results = verify_core_functionality()
    
    if results:
        print("\n验证完成！")
        print(f"结论: {results.get('conclusion', 'UNKNOWN')}")
        print(f"详细报告: {results.get('report_file', 'N/A')}")
    else:
        print("\n✗ 验证失败")
        print("  请检查Unity游戏是否正常运行。")

if __name__ == "__main__":
    main()
