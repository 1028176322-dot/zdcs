"""
# -*- coding: utf-8 -*-
第二阶段测试脚本：文本提取优化
测试Poco连接器和UI树处理器，验证Python侧文本修复算法
"""

import sys
import os

# 添加父目录到路径（用于import）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from poco_connector.poco_connector import PocoConnector
from ui_processor.ui_tree_processor import UITreeProcessor


def test_text_extraction():
    """
    测试文本提取优化
    这是方案文档第二阶段的核心任务
    """
    print("=" * 80)
    print("第二阶段测试：文本提取优化")
    print("=" * 80)
    
    # 1. 创建Poco连接器
    print("\n[步骤1] 创建Poco连接器...")
    connector = PocoConnector(device_type='Windows')
    
    # 2. 连接到Unity
    print("\n[步骤2] 连接到Unity游戏...")
    if not connector.connect():
        print("✗ 连接失败，测试终止")
        return
    
    # 3. Dump UI树
    print("\n[步骤3] Dump UI树...")
    ui_tree = connector.dump_ui_tree()
    if not ui_tree:
        print("✗ dump失败，测试终止")
        connector.close()
        return
    
    # 4. 创建UI树处理器
    print("\n[步骤4] 创建UI树处理器...")
    processor = UITreeProcessor(ui_tree)
    
    # 5. 提取所有文本
    print("\n[步骤5] 提取所有文本...")
    all_texts = processor.extract_all_texts()
    print(f"✓ 共提取到 {len(all_texts)} 个唯一文本")
    if all_texts:
        print("  前10个文本：")
        for i, text in enumerate(all_texts[:10], 1):
            print(f"  {i}. {text}")
    
    # 6. 查找所有可点击元素
    print("\n[步骤6] 查找所有可点击元素...")
    clickable_elements = processor.find_clickable_elements()
    print(f"✓ 共找到 {len(clickable_elements)} 个可点击元素")
    
    # 7. 批量修复ClickContent文本（Python侧修复）
    print("\n[步骤7] 批量修复ClickContent文本（Python侧修复）...")
    fixed_results = processor.batch_fix_clickcontent_texts()
    
    if fixed_results:
        print(f"✓ 共找到 {len(fixed_results)} 个ClickContent节点")
        print("\n修复结果：")
        print("-" * 80)
        print(f"{'序号':<6} {'节点名称':<30} {'修复后的文本':<40}")
        print("-" * 80)
        
        empty_count = 0
        for i, (node, fixed_text) in enumerate(fixed_results, 1):
            node_name = node.get('name', '')
            print(f"{i:<6} {node_name:<30} {fixed_text or '(空)'}")
            if not fixed_text:
                empty_count += 1
        
        print("-" * 80)
        print(f"✓ 修复成功: {len(fixed_results) - empty_count} 个")
        print(f"✗ 修复失败（仍为空）: {empty_count} 个")
    else:
        print("⚠ 未找到ClickContent节点")
    
    # 8. 生成页面指纹
    print("\n[步骤8] 生成页面指纹...")
    fingerprint = processor.generate_page_fingerprint()
    print(f"✓ 页面指纹: {fingerprint}")
    
    # 9. 保存UI树到JSON文件
    print("\n[步骤9] 保存UI树到JSON文件...")
    json_file = os.path.join(os.path.dirname(__file__), '../data_access/reports/ui_tree.json')
    os.makedirs(os.path.dirname(json_file), exist_ok=True)
    processor.to_json(json_file)
    
    # 10. 截图
    print("\n[步骤10] 截图...")
    screenshot_path = connector.snapshot()
    if screenshot_path:
        print(f"✓ 截图保存至: {screenshot_path}")
    
    # 11. 关闭连接
    print("\n[步骤11] 关闭连接...")
    connector.close()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    
    # 返回测试结果
    return {
        'total_texts': len(all_texts),
        'clickable_count': len(clickable_elements),
        'fixed_count': len(fixed_results),
        'empty_count': empty_count if fixed_results else 0,
        'fingerprint': fingerprint
    }


def analyze_ui_tree_structure(ui_tree):
    """
    分析UI树结构（调试用）
    查找ClickContent和TxtDesc的层级关系
    """
    print("\n" + "=" * 80)
    print("分析UI树结构")
    print("=" * 80)
    
    clickcontent_nodes = []
    
    def traverse(node, depth=0, path=[]):
        if not node or not isinstance(node, dict):
            return
        
        name = node.get('name', '')
        text = node.get('text', '')
        
        # 记录ClickContent节点
        if 'ClickContent' in name:
            clickcontent_nodes.append({
                'node': node,
                'depth': depth,
                'path': path + [name]
            })
        
        # 递归处理子节点
        for child in node.get('children', []):
            traverse(child, depth + 1, path + [name])
    
    traverse(ui_tree)
    
    print(f"\n✓ 共找到 {len(clickcontent_nodes)} 个ClickContent节点")
    
    # 分析每个ClickContent节点
    for i, item in enumerate(clickcontent_nodes[:5], 1):  # 只分析前5个
        node = item['node']
        depth = item['depth']
        path = item['path']
        
        print(f"\n--- ClickContent节点 #{i} ---")
        print(f"深度: {depth}")
        print(f"路径: {' -> '.join(path)}")
        print(f"text字段: '{node.get('text', '')}'")
        
        # 查找相邻文本
        parent = node.get('parent')
        if parent:
            print("兄弟节点：")
            for sibling in parent.get('children', []):
                sibling_name = sibling.get('name', '')
                sibling_text = sibling.get('text', '')
                if sibling is not node:
                    print(f"  - {sibling_name}: '{sibling_text}'")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    # 运行测试
    results = test_text_extraction()
    
    if results:
        print("\n测试统计：")
        print(f"  - 提取到文本数: {results['total_texts']}")
        print(f"  - 可点击元素数: {results['clickable_count']}")
        print(f"  - ClickContent节点数: {results['fixed_count']}")
        print(f"  - 修复失败数: {results['empty_count']}")
        
        if results['empty_count'] > 0:
            print("\n⚠ 警告：仍有ClickContent节点文本为空！")
            print("   建议：")
            print("   1. 检查UI树结构，确认TxtDesc节点的位置")
            print("   2. 调整find_nearby_text()的搜索深度")
            print("   3. 考虑修改UnityNode.cs（方案A）")
        else:
            print("\n✓ 恭喜！所有ClickContent节点文本已成功修复！")
    else:
        print("\n✗ 测试失败")
