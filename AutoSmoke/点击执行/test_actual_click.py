"""
# -*- coding: utf-8 -*-
实际点击测试

功能：
1. 读取Game视图坐标
2. 连接Unity Poco
3. Dump UI树
4. 找到一个可点击元素
5. 计算点击位置并实际点击
6. 截图验证点击结果
"""

import sys
import os
import time
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageGrab
import numpy as np

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import get_game_view_coords
from poco_connector.poco_connector import PocoConnector


def test_actual_click():
    """测试实际点击"""
    print("=" * 80)
    print("测试实际点击")
    print("=" * 80)
    
    # 步骤1：读取Game视图坐标
    print("\n[步骤1] 读取Game视图坐标...")
    coords = get_game_view_coords()
    if not coords:
        print("❌ 未找到Game视图坐标，请先运行 locate_game_area_smart.py")
        return False
    
    left, top, right, bottom = coords['left'], coords['top'], coords['right'], coords['bottom']
    width, height = coords['width'], coords['height']
    print(f"✅ Game视图坐标: ({left}, {top}, {right}, {bottom})")
    print(f"   尺寸: {width} x {height}")
    
    # 步骤2：连接Unity Poco
    print("\n[步骤2] 连接Unity Poco...")
    connector = PocoConnector(device_type='Windows')
    if not connector.connect():
        print("❌ 连接失败，请确保：")
        print("  1. Unity Editor已打开")
        print("  2. 已点击Play按钮（▶）")
        print("  3. Poco SDK已正确集成")
        return False
    print("✅ Poco连接成功")
    
    # 步骤3：Dump UI树
    print("\n[步骤3] Dump UI树...")
    ui_tree = connector.dump_ui_tree()
    if not ui_tree:
        print("❌ dump失败")
        connector.close()
        return False
    print("✅ UI树dump成功")
    
    # 步骤4：找到一个可点击元素
    print("\n[步骤4] 查找可点击元素...")
    
    # 使用UITreeProcessor处理UI树
    from ui_processor.ui_tree_processor import UITreeProcessor
    processor = UITreeProcessor(ui_tree)
    
    # 查找第一个可点击的元素
    target_elem = None
    target_path = None
    
    def find_clickable(node, path='', depth=0):
        nonlocal target_elem, target_path
        if not node or depth > 20:
            return
        
        name = node.get('name', '')
        clickable = node.get('clickable', False)
        pos = node.get('pos', [0, 0])
        size = node.get('size', [0, 0])
        
        # 检查是否可点击且有有效坐标
        if clickable and pos and size and pos[0] > 0 and pos[1] > 0:
            # 转换为Game视图坐标
            elem_x = int(pos[0] * width) + left
            elem_y = int(pos[1] * height) + top
            
            # 检查是否在Game视图内
            if left <= elem_x <= right and top <= elem_y <= bottom:
                target_elem = {
                    'name': name,
                    'pos': pos,
                    'size': size,
                    'screen_x': elem_x,
                    'screen_y': elem_y
                }
                target_path = path + '/' + name
                return True
        
        # 递归查找子节点
        for i, child in enumerate(node.get('children', [])):
            if find_clickable(child, path + '/' + node.get('name', 'root'), depth + 1):
                return True
        
        return False
    
    find_clickable(processor.ui_tree)
    
    if not target_elem:
        print("⚠️ 未找到可点击元素，尝试查找任意元素...")
        # 降级：查找第一个有坐标的元素
        def find_any(node, path='', depth=0):
            nonlocal target_elem, target_path
            if not node or depth > 20:
                return
            
            name = node.get('name', '')
            pos = node.get('pos', [0, 0])
            size = node.get('size', [0, 0])
            
            if pos and size and pos[0] > 0 and pos[1] > 0:
                elem_x = int(pos[0] * width) + left
                elem_y = int(pos[1] * height) + top
                
                if left <= elem_x <= right and top <= elem_y <= bottom:
                    target_elem = {
                        'name': name,
                        'pos': pos,
                        'size': size,
                        'screen_x': elem_x,
                        'screen_y': elem_y
                    }
                    target_path = path + '/' + name
                    return True
            
            for child in node.get('children', []):
                if find_any(child, path + '/' + node.get('name', 'root'), depth + 1):
                    return True
            
            return False
        
        find_any(processor.ui_tree)
    
    if not target_elem:
        print("❌ 未找到任何有效元素")
        connector.close()
        return False
    
    print(f"✅ 找到目标元素: {target_elem['name']}")
    print(f"   归一化坐标: ({target_elem['pos'][0]:.3f}, {target_elem['pos'][1]:.3f})")
    print(f"   屏幕坐标: ({target_elem['screen_x']}, {target_elem['screen_y']})")
    
    # 步骤5：截图（点击前）
    print("\n[步骤5] 截图（点击前）...")
    try:
        screenshot_dir = Path(__file__).parent / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        
        # 截取全屏
        img_before = ImageGrab.grab(all_screens=True)
        img_before_path = str(screenshot_dir / f"click_before_{timestamp}.png")
        img_before.save(img_before_path)
        print(f"✅ 点击前截图已保存: {img_before_path}")
    except Exception as e:
        print(f"⚠️ 截图失败: {e}")
        img_before_path = None
    
    # 步骤6：执行点击
    print("\n[步骤6] 执行点击...")
    try:
        # 方法1：使用Poco点击（推荐）
        elem = processor.find_node_by_name(target_elem['name'])
        if elem:
            print(f"   使用Poco点击元素: {target_elem['name']}")
            result = connector.click_element(elem)
            print(f"   点击结果: {result}")
        else:
            # 方法2：使用屏幕坐标点击（降级）
            print(f"   使用屏幕坐标点击: ({target_elem['screen_x']}, {target_elem['screen_y']})")
            # 这里需要使用Windows API点击
            print(f"   ⚠️ 降级方案：需要手动验证点击位置")
        
        time.sleep(1)  # 等待点击生效
    except Exception as e:
        print(f"❌ 点击失败: {e}")
        connector.close()
        return False
    
    # 步骤7：截图（点击后）
    print("\n[步骤7] 截图（点击后）...")
    try:
        img_after = ImageGrab.grab(all_screens=True)
        img_after_path = str(screenshot_dir / f"click_after_{timestamp}.png")
        img_after.save(img_after_path)
        print(f"✅ 点击后截图已保存: {img_after_path}")
    except Exception as e:
        print(f"⚠️ 截图失败: {e}")
        img_after_path = None
    
    # 步骤8：标注点击位置
    if img_before_path:
        print("\n[步骤8] 标注点击位置...")
        try:
            img = Image.open(img_before_path)
            draw = ImageDraw.Draw(img)
            
            # 在点击位置画十字准星
            cx, cy = target_elem['screen_x'], target_elem['screen_y']
            cross_size = 20
            draw.line([(cx - cross_size, cy), (cx + cross_size, cy)], fill=(255, 0, 0), width=3)
            draw.line([(cx, cy - cross_size), (cx, cy + cross_size)], fill=(255, 0, 0), width=3)
            
            # 保存标注图
            annotated_path = str(screenshot_dir / f"click_annotated_{timestamp}.png")
            img.save(annotated_path)
            print(f"✅ 标注截图已保存: {annotated_path}")
            print(f"   请查看截图，确认红色十字准星是否落在正确的UI元素上")
        except Exception as e:
            print(f"⚠️ 标注失败: {e}")
    
    # 关闭连接
    connector.close()
    
    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)
    print(f"\n请查看以下截图：")
    if img_before_path:
        print(f"  1. 点击前: {img_before_path}")
    if img_after_path:
        print(f"  2. 点击后: {img_after_path}")
    print(f"  3. 标注图: {annotated_path if img_before_path else 'N/A'}")
    print(f"\n确认：")
    print(f"  1. 红色十字准星是否落在正确的UI元素上？")
    print(f"  2. 点击后游戏是否有预期的反应？")
    
    return True


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("Unity游戏自动化测试系统 - 实际点击测试")
    print("=" * 80 + "\n")
    
    result = test_actual_click()
    
    print("\n" + "=" * 80)
    if result:
        print("✅ 测试完成，请查看截图验证结果。")
    else:
        print("❌ 测试失败。")
    print("=" * 80)
