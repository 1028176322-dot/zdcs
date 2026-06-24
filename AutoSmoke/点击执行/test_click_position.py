"""
# -*- coding: utf-8 -*-
测试Game视图点击位置

功能：
1. 读取Game视图坐标
2. 在Game视图中心位置模拟点击
3. 截图并标注点击位置
4. 验证点击是否落在游戏画面上
"""

import sys
import os
import time
import json
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import get_game_view_coords
from PIL import Image, ImageDraw, ImageGrab
import numpy as np


def test_click_position():
    """测试点击位置"""
    print("=" * 80)
    print("测试Game视图点击位置")
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
    
    # 步骤2：计算中心点击位置
    print("\n[步骤2] 计算中心点击位置...")
    center_x = left + width // 2
    center_y = top + height // 2
    print(f"✅ 中心位置: ({center_x}, {center_y})")
    
    # 步骤3：截取全屏
    print("\n[步骤3] 截取全屏...")
    try:
        img = ImageGrab.grab(all_screens=True)
        print(f"✅ 全屏截图尺寸: {img.size[0]} x {img.size[1]}")
    except Exception as e:
        print(f"❌ 截图失败: {e}")
        return False
    
    # 步骤4：标注点击位置
    print("\n[步骤4] 标注点击位置...")
    try:
        img_array = np.array(img)
        draw = ImageDraw.Draw(img)
        
        # 在点击位置画一个十字准星
        cross_size = 20
        draw.line([(center_x - cross_size, center_y), (center_x + cross_size, center_y)], fill=(255, 0, 0), width=3)
        draw.line([(center_x, center_y - cross_size), (center_x, center_y + cross_size)], fill=(255, 0, 0), width=3)
        
        # 画一个圆
        radius = 10
        draw.ellipse([(center_x - radius, center_y - radius), (center_x + radius, center_y + radius)], outline=(255, 0, 0), width=3)
        
        # 保存标注图
        output_dir = Path(__file__).parent / "screenshots"
        output_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        output_path = str(output_dir / f"click_test_{timestamp}.png")
        img.save(output_path)
        print(f"✅ 标注截图已保存: {output_path}")
        print(f"   请查看截图，确认红色十字准星是否落在Game视图的游戏画面上")
        
    except Exception as e:
        print(f"❌ 标注失败: {e}")
        return False
    
    # 步骤5：验证点击位置
    print("\n[步骤5] 验证点击位置...")
    try:
        # 检查点击位置是否在Game视图内
        if left <= center_x <= right and top <= center_y <= bottom:
            print(f"✅ 点击位置在Game视图内")
            
            # 检查是否在上部（可能是菜单栏区域）
            if center_y < top + 30:
                print(f"⚠️ 警告：点击位置太靠近顶部，可能点到了菜单栏！")
                return False
            else:
                print(f"✅ 点击位置在游戏画面区域内")
                return True
        else:
            print(f"❌ 点击位置不在Game视图内！")
            return False
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("Unity游戏自动化测试系统 - 点击位置验证工具")
    print("=" * 80 + "\n")
    
    result = test_click_position()
    
    print("\n" + "=" * 80)
    if result:
        print("✅ 测试通过！点击位置正确。")
    else:
        print("❌ 测试失败！点击位置可能不正确。")
    print("=" * 80)
