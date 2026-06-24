"""
# -*- coding: utf-8 -*-
简单点击测试

直接使用Poco点击，验证点击位置是否正确
"""

import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入PocoConnector
from core_engine.poco_connector.poco_connector import PocoConnector


def simple_click_test():
    """简单点击测试"""
    print("=" * 80)
    print("简单点击测试")
    print("=" * 80)
    
    # 步骤1：连接Unity Poco
    print("\n[步骤1] 连接Unity Poco...")
    connector = PocoConnector(device_type='Windows')
    if not connector.connect():
        print("❌ 连接失败，请确保：")
        print("  1. Unity Editor已打开")
        print("  2. 已点击Play按钮（▶）")
        print("  3. Poco SDK已正确集成")
        return False
    print("✅ Poco连接成功")
    
    # 步骤2：Dump UI树
    print("\n[步骤2] Dump UI树...")
    ui_tree = connector.dump_ui_tree()
    if not ui_tree:
        print("❌ dump失败")
        connector.close()
        return False
    print("✅ UI树dump成功")
    
    # 步骤3：查找一个可见的UI元素
    print("\n[步骤3] 查找可见UI元素...")
    
    # 使用UITreeProcessor处理UI树
    from core_engine.ui_processor.ui_tree_processor import UITreeProcessor
    processor = UITreeProcessor(ui_tree)
    
    # 查找第一个有文本的元素（通常是可见的）
    target_name = None
    target_pos = None
    
    def find_text_element(node, depth=0):
        nonlocal target_name, target_pos
        if not node or depth > 30:
            return
        
        name = node.get('name', '')
        text = node.get('text', '')
        pos = node.get('pos', [0, 0])
        visible = node.get('visible', True)
        
        # 查找有文本且可见的元素
        if text and visible and pos and pos[0] > 0 and pos[1] > 0:
            target_name = name
            target_pos = pos
            return True
        
        # 递归查找子节点
        for child in node.get('children', []):
            if find_text_element(child, depth + 1):
                return True
        
        return False
    
    find_text_element(processor.ui_tree)
    
    if not target_name:
        print("⚠️ 未找到有文本的元素，尝试查找任意元素...")
        # 降级：查找第一个有坐标的元素
        def find_any_element(node, depth=0):
            nonlocal target_name, target_pos
            if not node or depth > 30:
                return
            
            name = node.get('name', '')
            pos = node.get('pos', [0, 0])
            
            if pos and pos[0] > 0 and pos[1] > 0:
                target_name = name
                target_pos = pos
                return True
            
            for child in node.get('children', []):
                if find_any_element(child, depth + 1):
                    return True
            
            return False
        
        find_any_element(processor.ui_tree)
    
    if not target_name:
        print("❌ 未找到任何有效元素")
        connector.close()
        return False
    
    print(f"✅ 找到目标元素: {target_name}")
    print(f"   归一化坐标: ({target_pos[0]:.3f}, {target_pos[1]:.3f})")
    
    # 步骤4：使用Poco点击该元素
    print("\n[步骤4] 使用Poco点击元素...")
    try:
        # 查找该元素
        elem = processor.find_node_by_name(target_name)
        if not elem:
            print(f"❌ 无法找到元素: {target_name}")
            connector.close()
            return False
        
        print(f"   元素详情: {elem}")
        
        # 点击该元素
        print(f"   正在点击元素: {target_name}...")
        connector.click_element(elem)
        print(f"   ✅ 点击完成")
        
    except Exception as e:
        print(f"❌ 点击失败: {e}")
        import traceback
        traceback.print_exc()
        connector.close()
        return False
    
    # 步骤5：等待并提示用户
    print("\n[步骤5] 验证点击结果...")
    print(f"✅ 已点击元素: {target_name}")
    print(f"   请查看Unity Game视图，确认点击是否落在正确的位置")
    print(f"   如果点击位置正确（点击到了游戏画面内的UI元素），则测试通过")
    print(f"   如果点击位置不正确（如点击到了Unity菜单栏），则测试失败")
    
    # 关闭连接
    connector.close()
    
    print("\n" + "=" * 80)
    print("测试完成，请手动验证点击位置是否正确。")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("Unity游戏自动化测试系统 - 简单点击测试")
    print("=" * 80 + "\n")
    
    result = simple_click_test()
    
    print("\n" + "=" * 80)
    if result:
        print("✅ 测试执行完成，请验证结果。")
    else:
        print("❌ 测试失败。")
    print("=" * 80)
