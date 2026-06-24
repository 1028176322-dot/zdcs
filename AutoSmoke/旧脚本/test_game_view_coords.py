"""
# -*- coding: utf-8 -*-
测试 Game 视图坐标
验证保存的坐标是否能正确使用
"""
import sys
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import get_game_view_coords
from PIL import Image

# 读取坐标
coords = get_game_view_coords()
if not coords:
    print("❌ 未找到 Game 视图坐标")
    sys.exit(1)

left = coords['left']
top = coords['top']
right = coords['right']
bottom = coords['bottom']
width = coords['width']
height = coords['height']

print(f"✅ 读取到 Game 视图坐标：")
print(f"  截图坐标: ({left}, {top}, {right}, {bottom})")
print(f"  尺寸: {width} x {height}")

# 读取最新截图
from pathlib import Path
screenshots_dir = Path(__file__).parent.parent / 'screenshots'
png_files = list(screenshots_dir.glob('editor_*.png'))
if not png_files:
    print("❌ 未找到截图文件")
    sys.exit(1)

latest_png = max(png_files, key=lambda p: p.stat().st_mtime)
print(f"\n📸 读取截图: {latest_png.name}")

img = Image.open(latest_png)
img_array = __import__('numpy').array(img)

# 验证坐标是否在截图范围内
img_height, img_width = img_array.shape[:2]
print(f"  截图尺寸: {img_width} x {img_height}")

if left < 0 or top < 0 or right > img_width or bottom > img_height:
    print(f"❌ 坐标超出截图范围！")
    sys.exit(1)

# 裁剪 Game 视图区域
game_region = img_array[top:bottom, left:right, :]
game_img = Image.fromarray(game_region)
game_img.save(str(Path(__file__).parent.parent / 'screenshots' / 'game_view_test.png'))
print(f"✅ Game 视图区域已保存: E:/zdcs/AutoSmoke/screenshots/game_view_test.png")

# 显示坐标信息
print(f"\n📊 坐标信息：")
print(f"  左: {left}px")
print(f"  上: {top}px")
print(f"  右: {right}px")
print(f"  下: {bottom}px")
print(f"  宽度: {width}px")
print(f"  高度: {height}px")

# 计算宽高比
aspect_ratio = width / height
print(f"  宽高比: {aspect_ratio:.3f}")

print(f"\n✅ 坐标验证成功！")
