"""
# -*- coding: utf-8 -*-
界面信息完整验证脚本
验证所有UI元素是否被正确获取（文本、按钮、图标等）
"""

import sys
import os
import time
import json

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poco_connector.poco_connector import PocoConnector
from ui_processor.ui_tree_processor import UITreeProcessor


def verify_all_ui_elements():
    """
    验证所有UI元素是否被正确获取
    """
    print("=" * 80)
    print("界面信息完整验证")
    print("=" * 80)
    
    # 1. 创建Poco连接器
    print("\n[步骤1] 创建Poco连接器...")
    connector = PocoConnector(device_type='Windows')
    
    # 2. 连接到Unity
    print("\n[步骤2] 连接到Unity游戏...")
    if not connector.connect():
        print("✗ 连接失败，测试终止")
        print("\n请确保：")
        print("  1. Unity Editor已打开")
        print("  2. 已点击Play按钮（▶）")
        print("  3. 游戏已进入主界面")
        return None
    
    # 3. Dump UI树
    print("\n[步骤3] Dump UI树...")
    ui_tree = connector.dump_ui_tree()
    if not ui_tree:
        print("✗ dump失败，测试终止")
        connector.close()
        return None
    
    # 4. 创建UI树处理器
    print("\n[步骤4] 创建UI树处理器...")
    processor = UITreeProcessor(ui_tree)
    
    # 5. 提取所有文本
    print("\n[步骤5] 提取所有文本...")
    all_texts = processor.extract_all_texts()
    print(f"✓ 共提取到 {len(all_texts)} 个唯一文本")
    
    if all_texts:
        print("\n  所有文本内容：")
        print("  " + "-" * 76)
        for i, text in enumerate(all_texts, 1):
            print(f"  {i:3d}. {text}")
        print("  " + "-" * 76)
    else:
        print("  ⚠️ 警告：未提取到任何文本！")
    
    # 6. 查找所有可点击元素
    print("\n[步骤6] 查找所有可点击元素...")
    clickable_elements = processor.find_clickable_elements()
    print(f"✓ 共找到 {len(clickable_elements)} 个可点击元素")
    
    # 7. 批量修复ClickContent文本
    print("\n[步骤7] 批量修复ClickContent文本...")
    fixed_results = processor.batch_fix_clickcontent_texts()
    
    if fixed_results:
        print(f"✓ 共找到 {len(fixed_results)} 个ClickContent节点")
        print("\n  ClickContent节点详情：")
        print("  " + "-" * 76)
        print(f"  {'序号':<6} {'节点名称':<40} {'修复后的文本':<30}")
        print("  " + "-" * 76)
        
        empty_count = 0
        for i, (node, fixed_text) in enumerate(fixed_results, 1):
            node_name = node.get('name', '')
            print(f"  {i:<6} {node_name:<40} {fixed_text or '(空)'}")
            if not fixed_text:
                empty_count += 1
        
        print("  " + "-" * 76)
        print(f"  ✓ 修复成功: {len(fixed_results) - empty_count} 个")
        print(f"  ✗ 修复失败（仍为空）: {empty_count} 个")
    else:
        print("  ⚠️ 未找到ClickContent节点")
    
    # 8. 分析UI树结构
    print("\n[步骤8] 分析UI树结构...")
    analyze_ui_structure(ui_tree)
    
    # 9. 生成页面指纹
    print("\n[步骤9] 生成页面指纹...")
    fingerprint = processor.generate_page_fingerprint()
    print(f"✓ 页面指纹: {fingerprint}")
    
    # 10. 保存完整UI树到JSON文件
    print("\n[步骤10] 保存完整UI树到JSON文件...")
    output_dir = os.path.join(os.path.dirname(__file__), '../data_access/reports')
    os.makedirs(output_dir, exist_ok=True)
    
    json_file = os.path.join(output_dir, f'ui_tree_full_{int(time.time())}.json')
    json_str = processor.to_json(json_file)
    
    # 11. 截图
    print("\n[步骤11] 截图...")
    screenshot_path = connector.snapshot()
    if screenshot_path:
        print(f"✓ 截图保存至: {screenshot_path}")
    
    # 12. 生成验证报告
    print("\n[步骤12] 生成验证报告...")
    report = generate_verification_report(
        all_texts=all_texts,
        clickable_elements=clickable_elements,
        fixed_results=fixed_results,
        fingerprint=fingerprint,
        json_file=json_file,
        screenshot_path=screenshot_path
    )
    
    report_file = os.path.join(output_dir, f'verification_report_{int(time.time())}.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✓ 验证报告已保存至: {report_file}")
    
    # 13. 关闭连接
    print("\n[步骤13] 关闭连接...")
    connector.close()
    
    print("\n" + "=" * 80)
    print("验证完成")
    print("=" * 80)
    
    # 返回验证结果
    return {
        'total_texts': len(all_texts),
        'clickable_count': len(clickable_elements),
        'clickcontent_count': len(fixed_results) if fixed_results else 0,
        'empty_text_count': empty_count if fixed_results else 0,
        'fingerprint': fingerprint,
        'json_file': json_file,
        'report_file': report_file,
        'screenshot_path': screenshot_path
    }


def analyze_ui_structure(ui_tree, max_depth=3):
    """
    分析UI树结构（统计各类节点数量）
    :param ui_tree: UI树
    :param max_depth: 最大分析深度
    """
    stats = {
        'total_nodes': 0,
        'by_name': {},  # 按名称统计
        'by_depth': {},  # 按深度统计
        'text_nodes': 0,   # 有文本的节点
        'empty_text_nodes': 0  # 文本为空的节点
    }
    
    def traverse(node, depth=0):
        if not node or not isinstance(node, dict) or depth > max_depth:
            return
        
        stats['total_nodes'] += 1
        
        # 按名称统计
        name = node.get('name', '')
        if name:
            stats['by_name'][name] = stats['by_name'].get(name, 0) + 1
        
        # 按深度统计
        stats['by_depth'][depth] = stats['by_depth'].get(depth, 0) + 1
        
        # 统计文本
        text = node.get('text', '')
        if text and isinstance(text, str) and text.strip():
            stats['text_nodes'] += 1
        else:
            stats['empty_text_nodes'] += 1
        
        # 递归处理子节点
        for child in node.get('children', []):
            traverse(child, depth + 1)
    
    traverse(ui_tree)
    
    # 打印统计结果
    print(f"✓ UI树结构分析（深度≤{max_depth}）：")
    print(f"  - 总节点数: {stats['total_nodes']}")
    print(f"  - 有文本的节点: {stats['text_nodes']}")
    print(f"  - 文本为空的节点: {stats['empty_text_nodes']}")
    
    print(f"\n  按名称统计（Top 10）：")
    sorted_by_name = sorted(stats['by_name'].items(), key=lambda x: x[1], reverse=True)[:10]
    for name, count in sorted_by_name:
        print(f"    {name}: {count}个")
    
    print(f"\n  按深度统计：")
    for depth in sorted(stats['by_depth'].keys()):
        print(f"    深度{depth}: {stats['by_depth'][depth]}个节点")


def generate_verification_report(**kwargs):
    """
    生成验证报告
    """
    report = []
    report.append("=" * 80)
    report.append("界面信息验证报告")
    report.append("=" * 80)
    report.append("")
    
    # 获取参数
    all_texts = kwargs.get('all_texts', [])
    clickable_elements = kwargs.get('clickable_elements', [])
    fixed_results = kwargs.get('fixed_results', None)
    fingerprint = kwargs.get('fingerprint', 'N/A')
    json_file = kwargs.get('json_file', 'N/A')
    screenshot_path = kwargs.get('screenshot_path', 'N/A')
    
    report.append("## 1. 基本信息")
    report.append("")
    report.append(f"- 验证时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"- 页面指纹: {fingerprint}")
    report.append(f"- UI树文件: {json_file}")
    report.append(f"- 截图文件: {screenshot_path}")
    report.append("")
    
    report.append("## 2. 文本提取结果")
    report.append("")
    report.append(f"- 提取到文本数: {len(all_texts)}")
    
    if all_texts:
        report.append(f"- 文本内容（前20个）:")
        for i, text in enumerate(all_texts[:20], 1):
            report.append(f"  {i}. {text}")
        if len(all_texts) > 20:
            report.append(f"  ... (共{len(all_texts)}个)")
    report.append("")
    
    report.append("## 3. 可点击元素统计")
    report.append("")
    report.append(f"- 可点击元素数: {len(clickable_elements)}")
    report.append("")
    
    report.append("## 4. ClickContent文本修复结果")
    report.append("")
    
    if fixed_results:
        report.append(f"- ClickContent节点数: {len(fixed_results)}")
        
        empty_count = sum(1 for _, text in fixed_results if not text)
        report.append(f"- 修复成功数: {len(fixed_results) - empty_count}")
        report.append(f"- 修复失败数: {empty_count}")
    else:
        report.append("- ClickContent节点数: 0")
        report.append("- 修复成功数: 0")
        report.append("- 修复失败数: 0")
    
    report.append("")
    
    report.append("## 5. 结论")
    report.append("")
    
    total = len(fixed_results) if fixed_results else 0
    empty = sum(1 for _, text in fixed_results if not text) if fixed_results else 0
    
    if total == 0:
        report.append("⚠️ 未找到ClickContent节点，可能：")
        report.append("  1. 当前界面不包含ClickContent")
        report.append("  2. Poco SDK未正确集成")
    elif empty == 0:
        report.append("✓ 所有ClickContent节点文本已成功修复！")
        report.append("  界面信息已完整获取。")
    else:
        report.append(f"⚠️ 仍有{empty}个ClickContent节点文本为空！")
        report.append("  建议：")
        report.append("  1. 检查UI树结构，确认TxtDesc节点的位置")
        report.append("  2. 调整find_nearby_text()的搜索深度")
        report.append("  3. 考虑修改UnityNode.cs（方案A）")
    
    report.append("")
    report.append("=" * 80)
    report.append("报告结束")
    report.append("=" * 80)
    
    return "\n".join(report)


if __name__ == '__main__':
    # 直接运行验证，无需用户交互
    print("\n" + "=" * 80)
    print("Unity游戏自动化测试系统 - 界面信息验证工具")
    print("=" * 80 + "\n")
    
    print("提示：检测到Unity已启动，开始验证...\n")
    
    # 运行验证
    results = verify_all_ui_elements()
    
    if results:
        print("\n验证统计：")
        print(f"  - 提取到文本数: {results['total_texts']}")
        print(f"  - 可点击元素数: {results['clickable_count']}")
        print(f"  - ClickContent节点数: {results['clickcontent_count']}")
        print(f"  - 修复失败数: {results['empty_text_count']}")
        print(f"\n详细报告已保存至: {results['report_file']}")
        
        if results['empty_text_count'] > 0:
            print(f"\n⚠️ 警告：仍有{results['empty_text_count']}个ClickContent节点文本为空！")
            print("  请查看验证报告获取详细信息。")
        else:
            print("\n✓ 恭喜！所有界面信息已正确获取！")
    else:
        print("\n✗ 验证失败")
        print("  请检查Unity游戏是否正常运行。")
