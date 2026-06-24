"""
# -*- coding: utf-8 -*-
Unity 游戏界面定位 - 简化版（不依赖 Poco/Airtest）
使用图像识别 + 配置文件来定位游戏区域

功能：
1. 读取配置文件中的游戏分辨率
2. 截取屏幕
3. 使用黑色边框检测找到游戏区域
4. 如果没有黑色边框，根据分辨率在中央裁剪
5. 标注并显示结果
"""

import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入配置管理器
from config_manager import load_config, get_game_resolution

from PIL import Image, ImageDraw, ImageFont, ImageGrab
import numpy as np


# ==================== 配置参数 ====================
BLACK_THRESHOLD = 30  # 黑色阈值（RGB 值低于此值视为黑色）


# ==================== 游戏区域检测 ====================
def detect_game_area_by_black_border(
    image_path: str,
    black_threshold: int = 30
) -> Optional[Tuple[int, int, int, int]]:
    """
    通过检测黑色边框来定位游戏区域
    :param image_path: 截图路径
    :param black_threshold: 黑色阈值
    :return: (left, top, right, bottom) 或 None
    """
    print(f"\n[黑色边框检测] 开始分析截图: {image_path}")
    
    # 打开图片
    img = Image.open(image_path)
    img_rgb = img.convert('RGB')
    arr = np.array(img_rgb)
    
    # 转换为灰度图
    img_gray = img.convert('L')
    arr_gray = np.array(img_gray)
    
    height, width = arr_gray.shape
    print(f"  图片尺寸: {width} x {height}")
    
    # 计算每列的平局亮度
    col_means = np.mean(arr_gray, axis=0)
    
    # 计算每行的平均亮度
    row_means = np.mean(arr_gray, axis=1)
    
    # 从左到右扫描
    left = 0
    for x in range(width):
        if col_means[x] > black_threshold:
            left = x
            break
    
    # 从右到左扫描
    right = width - 1
    for x in range(width - 1, -1, -1):
        if col_means[x] > black_threshold:
            right = x
            break
    
    # 从上到下扫描
    top = 0
    for y in range(height):
        if row_means[y] > black_threshold:
            top = y
            break
    
    # 从下到上扫描
    bottom = height - 1
    for y in range(height - 1, -1, -1):
        if row_means[y] > black_threshold:
            bottom = y
            break
    
    # 检查是否有效
    if left >= right or top >= bottom:
        print(f"  ⚠️ 未检测到黑色边框")
        return None
    
    # 检查是否有黑色边框
    has_border = left > 0 or right < width - 1 or top > 0 or bottom < height - 1
    
    if not has_border:
        print(f"  ⚠️ 截图没有黑色边框")
        return None
    
    print(f"  ✅ 检测到游戏区域:")
    print(f"    左: {left}, 上: {top}, 右: {right}, 下: {bottom}")
    print(f"    尺寸: {right - left + 1} x {bottom - top + 1}")
    
    return (left, top, right, bottom)


def locate_game_area_by_resolution(
    screenshot_path: str,
    game_width: int,
    game_height: int
) -> Tuple[str, Tuple[int, int, int, int]]:
    """
    根据游戏分辨率定位游戏区域
    假设游戏在屏幕中央
    :param screenshot_path: 截图路径
    :param game_width: 游戏宽度
    :param game_height: 游戏高度
    :return: (裁剪后的图片路径, 裁剪区域坐标)
    """
    print(f"\n[分辨率定位] 游戏分辨率: {game_width} x {game_height}")
    
    # 打开截图
    img = Image.open(screenshot_path)
    img_width, img_height = img.size
    
    print(f"  截图尺寸: {img_width} x {img_height}")
    
    # 计算游戏区域的左上角坐标（居中）
    left = (img_width - game_width) // 2
    top = (img_height - game_height) // 2
    right = left + game_width - 1
    bottom = top + game_height - 1
    
    # 确保不超出截图范围
    left = max(0, left)
    top = max(0, top)
    right = min(img_width - 1, right)
    bottom = min(img_height - 1, bottom)
    
    print(f"  ✅ 游戏区域（居中）:")
    print(f"    左: {left}, 上: {top}, 右: {right}, 下: {bottom}")
    print(f"    尺寸: {right - left + 1} x {bottom - top + 1}")
    
    # 裁剪图片
    cropped_img = img.crop((left, top, right + 1, bottom + 1))
    cropped_path = screenshot_path.replace('.png', '_cropped.png')
    cropped_img.save(cropped_path)
    
    print(f"  ✅ 已裁剪到: {cropped_path}")
    
    return cropped_path, (left, top, right, bottom)


# ==================== 标注结果 ====================
def draw_game_area(
    screenshot_path: str,
    game_area: Tuple[int, int, int, int],
    output_path: str
):
    """
    在截图上标注游戏区域
    :param screenshot_path: 截图路径
    :param game_area: 游戏区域 (left, top, right, bottom)
    :param output_path: 输出路径
    """
    # 打开截图
    img = Image.open(screenshot_path)
    draw = ImageDraw.Draw(img)
    
    left, top, right, bottom = game_area
    
    # 绘制红色矩形框
    draw.rectangle(
        [left, top, right, bottom],
        outline='red',
        width=5
    )
    
    # 添加标签
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()
    
    label = f"Game Area: {right - left + 1} x {bottom - top + 1}"
    draw.text((left, top - 40), label, fill='red', font=font)
    
    # 保存
    img.save(output_path)
    print(f"  ✅ 标注后截图已保存: {output_path}")


# ==================== 主函数 ====================
def main():
    """主函数"""
    print("=" * 80)
    print("Unity 游戏界面定位 - 简化版（图像识别）")
    print("=" * 80)
    
    # 1. 加载配置
    print("\n[1/5] 加载配置...")
    config = load_config()
    game_width, game_height = get_game_resolution()
    print(f"✅ 游戏分辨率: {game_width} x {game_height}")
    
    # 2. 截图
    print("\n[2/5] 截图...")
    screenshot_dir = project_root / "AutoSmoke" / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = str(screenshot_dir / f"screen_{timestamp}.png")
    
    try:
        # 使用 PIL 截图
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path)
        print(f"✅ 截图已保存: {screenshot_path}")
        print(f"  截图尺寸: {screenshot.width} x {screenshot.height}")
    except Exception as e:
        print(f"❌ 截图失败: {e}")
        return
    
    # 3. 尝试通过黑色边框检测游戏区域
    print("\n[3/5] 检测游戏区域...")
    game_area = detect_game_area_by_black_border(screenshot_path, BLACK_THRESHOLD)
    
    # 4. 如果黑色边框检测失败，使用分辨率定位
    if not game_area:
        print("\n[4/5] 黑色边框检测失败，使用分辨率定位...")
        cropped_path, game_area = locate_game_area_by_resolution(
            screenshot_path,
            game_width,
            game_height
        )
    else:
        # 裁剪到游戏区域
        print("\n[4/5] 裁剪到游戏区域...")
        img = Image.open(screenshot_path)
        left, top, right, bottom = game_area
        cropped_img = img.crop((left, top, right + 1, bottom + 1))
        cropped_path = screenshot_path.replace('.png', '_cropped.png')
        cropped_img.save(cropped_path)
        print(f"✅ 已裁剪到: {cropped_path}")
    
    # 5. 标注结果
    print("\n[5/5] 标注结果...")
    annotated_path = str(screenshot_dir / f"game_area_{timestamp}.png")
    draw_game_area(screenshot_path, game_area, annotated_path)
    
    # 完成
    print("\n" + "=" * 80)
    print("✅ 完成！")
    print("=" * 80)
    print(f"\n结果文件:")
    print(f"  1. 原始截图: {screenshot_path}")
    print(f"  2. 裁剪后截图: {cropped_path}")
    print(f"  3. 标注后截图: {annotated_path}")
    print(f"\n请在标注后的截图上确认游戏区域是否正确。")
    print("=" * 80)


if __name__ == '__main__':
    main()
