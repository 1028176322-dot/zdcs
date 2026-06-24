"""
# -*- coding: utf-8 -*-
第二阶段测试脚本：文本提取优化（模拟数据测试）
使用模拟的UI树数据，验证Python侧文本修复算法
"""

import sys
import os
import json

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui_processor.ui_tree_processor import UITreeProcessor


def create_mock_ui_tree():
    """
    创建模拟的UI树数据
    模拟ClickContent和TxtDesc的实际层级关系
    """
    # 模拟结构（根据之前的分析）：
    # Root
    #   +- Panel
    #        +- ScrollView
    #             +- Item1 (包含ClickContent和TxtDesc)
    #             |     +- ClickContent (text为空)
    #             |     +- TxtDesc (text='探险家试炼')
    #             +- Item2
    #             |     +- ClickContent (text为空)
    #             |     +- DescText (text='挑战模式')
    #             +- ...
    
    mock_tree = {
        'name': 'Root',
        'text': '',
        'pos': [0.5, 0.5],
        'size': [1.0, 1.0],
        'children': [
            {
                'name': 'Panel',
                'text': '',
                'pos': [0.5, 0.5],
                'size': [1.0, 1.0],
                'children': [
                    {
                        'name': 'ScrollView',
                        'text': '',
                        'pos': [0.5, 0.5],
                        'size': [0.9, 0.8],
                        'children': [
                            # Item 1: ClickContent + TxtDesc (兄弟节点)
                            {
                                'name': 'Item1',
                                'text': '',
                                'pos': [0.5, 0.9],
                                'size': [0.8, 0.1],
                                'children': [
                                    {
                                        'name': 'ClickContent',
                                        'text': '',  # 文本为空！
                                        'pos': [0.3, 0.5],
                                        'size': [0.6, 0.8],
                                        'children': []
                                    },
                                    {
                                        'name': 'TxtDesc',
                                        'text': '探险家试炼',  # 文本在这里！
                                        'pos': [0.7, 0.5],
                                        'size': [0.4, 0.6],
                                        'children': []
                                    }
                                ]
                            },
                            # Item 2: ClickContent + DescText (兄弟节点)
                            {
                                'name': 'Item2',
                                'text': '',
                                'pos': [0.5, 0.7],
                                'size': [0.8, 0.1],
                                'children': [
                                    {
                                        'name': 'ClickContent',
                                        'text': '',  # 文本为空！
                                        'pos': [0.3, 0.5],
                                        'size': [0.6, 0.8],
                                        'children': []
                                    },
                                    {
                                        'name': 'DescText',
                                        'text': '挑战模式',  # 文本在这里！
                                        'pos': [0.7, 0.5],
                                        'size': [0.4, 0.6],
                                        'children': []
                                    }
                                ]
                            },
                            # Item 3: ClickContent（无兄弟文本节点）
                            {
                                'name': 'Item3',
                                'text': '',
                                'pos': [0.5, 0.5],
                                'size': [0.8, 0.1],
                                'children': [
                                    {
                                        'name': 'ClickContent',
                                        'text': '',  # 文本为空，且无兄弟文本节点
                                        'pos': [0.5, 0.5],
                                        'size': [0.8, 0.8],
                                        'children': []
                                    }
                                ]
                            },
                            # Item 4: 有文本的正常Button
                            {
                                'name': 'Button',
                                'text': '开始游戏',  # 文本正常！
                                'pos': [0.5, 0.3],
                                'size': [0.3, 0.1],
                                'children': []
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    return mock_tree


def test_with_mock_data():
    """
    使用模拟数据测试文本提取优化
    """
    print("=" * 80)
    print("第二阶段测试：文本提取优化（模拟数据）")
    print("=" * 80)
    
    # 1. 创建模拟UI树
    print("\n[步骤1] 创建模拟UI树...")
    mock_tree = create_mock_ui_tree()
    print("✓ 模拟UI树创建成功")
    
    # 2. 创建UI树处理器
    print("\n[步骤2] 创建UI树处理器...")
    processor = UITreeProcessor(mock_tree)
    print("✓ UI树处理器创建成功")
    
    # 3. 提取所有文本
    print("\n[步骤3] 提取所有文本...")
    all_texts = processor.extract_all_texts()
    print(f"✓ 共提取到 {len(all_texts)} 个唯一文本")
    for i, text in enumerate(all_texts, 1):
        print(f"  {i}. {text}")
    
    # 4. 查找所有可点击元素
    print("\n[步骤4] 查找所有可点击元素...")
    clickable_elements = processor.find_clickable_elements()
    print(f"✓ 共找到 {len(clickable_elements)} 个可点击元素")
    
    # 5. 批量修复ClickContent文本（核心测试）
    print("\n[步骤5] 批量修复ClickContent文本（Python侧修复）...")
    fixed_results = processor.batch_fix_clickcontent_texts()
    
    if fixed_results:
        print(f"✓ 共找到 {len(fixed_results)} 个ClickContent节点")
        print("\n修复结果：")
        print("-" * 80)
        print(f"{'序号':<6} {'节点路径':<40} {'修复后的文本':<30}")
        print("-" * 80)
        
        success_count = 0
        for i, (node, fixed_text) in enumerate(fixed_results, 1):
            # 获取节点路径
            path = []
            n = node
            while n:
                path.insert(0, n.get('name', ''))
                n = n.get('parent')
            path_str = ' -> '.join(path)
            
            print(f"{i:<6} {path_str:<40} {fixed_text or '(空)'}")
            
            if fixed_text:
                success_count += 1
        
        print("-" * 80)
        print(f"✓ 修复成功: {success_count}/{len(fixed_results)}")
        print(f"✗ 修复失败（仍为空）: {len(fixed_results) - success_count}/{len(fixed_results)}")
    else:
        print("⚠ 未找到ClickContent节点")
    
    # 6. 生成页面指纹
    print("\n[步骤6] 生成页面指纹...")
    fingerprint = processor.generate_page_fingerprint()
    print(f"✓ 页面指纹: {fingerprint}")
    
    # 7. 保存UI树到JSON文件
    print("\n[步骤7] 保存UI树到JSON文件...")
    output_file = os.path.join(os.path.dirname(__file__), '../data_access/reports/mock_ui_tree.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    processor.to_json(output_file)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    
    # 返回测试结果
    return {
        'total_texts': len(all_texts),
        'clickable_count': len(clickable_elements),
        'fixed_count': len(fixed_results) if fixed_results else 0,
        'success_count': success_count if fixed_results else 0,
        'fingerprint': fingerprint
    }


def test_edge_cases():
    """
    测试边界情况
    """
    print("\n" + "=" * 80)
    print("边界情况测试")
    print("=" * 80)
    
    # 测试用例1：TxtDesc在祖先节点中（不是兄弟节点）
    print("\n[测试用例1] TxtDesc在祖先节点中...")
    mock_tree_1 = {
        'name': 'Root',
        'text': '',
        'children': [
            {
                'name': 'Panel',
                'text': '',
                'children': [
                    {
                        'name': 'TxtDesc',
                        'text': '探险家试炼',  # 文本在祖先节点中
                        'children': [
                            {
                                'name': 'Item',
                                'text': '',
                                'children': [
                                    {
                                        'name': 'ClickContent',
                                        'text': '',  # 需要向上查找
                                        'children': []
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    processor1 = UITreeProcessor(mock_tree_1)
    fixed_results1 = processor1.batch_fix_clickcontent_texts()
    
    if fixed_results1:
        print(f"✓ 找到 {len(fixed_results1)} 个ClickContent节点")
        for node, fixed_text in fixed_results1:
            print(f"  修复后的文本: '{fixed_text}'")
    else:
        print("✗ 未找到ClickContent节点")
    
    # 测试用例2：空UI树
    print("\n[测试用例2] 空UI树...")
    processor2 = UITreeProcessor(None)
    texts2 = processor2.extract_all_texts()
    print(f"✓ 提取到 {len(texts2)} 个文本（应为0）")
    
    # 测试用例3：无ClickContent节点
    print("\n[测试用例3] 无ClickContent节点...")
    mock_tree_3 = {
        'name': 'Root',
        'text': '',
        'children': [
            {
                'name': 'Button',
                'text': '开始游戏',
                'children': []
            }
        ]
    }
    
    processor3 = UITreeProcessor(mock_tree_3)
    fixed_results3 = processor3.batch_fix_clickcontent_texts()
    print(f"✓ 找到 {len(fixed_results3)} 个ClickContent节点（应为0）")
    
    print("\n" + "=" * 80)
    print("边界情况测试完成")
    print("=" * 80)


if __name__ == '__main__':
    # 运行主要测试
    results = test_with_mock_data()
    
    if results:
        print("\n测试统计：")
        print(f"  - 提取到文本数: {results['total_texts']}")
        print(f"  - 可点击元素数: {results['clickable_count']}")
        print(f"  - ClickContent节点数: {results['fixed_count']}")
        print(f"  - 修复成功数: {results['success_count']}")
        
        if results['success_count'] == results['fixed_count']:
            print("\n✓ 恭喜！所有ClickContent节点文本已成功修复！")
        else:
            print(f"\n⚠ 警告：仍有 {results['fixed_count'] - results['success_count']} 个ClickContent节点文本为空！")
    
    # 运行边界情况测试
    test_edge_cases()
