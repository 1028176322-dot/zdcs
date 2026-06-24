"""
# -*- coding: utf-8 -*-
Unity 游戏界面定位 - Windows API 版本
使用 Windows API 找到 Unity 窗口，截取 Game 窗口区域

功能：
1. 使用 Windows API 枚举所有窗口，找到 Unity 相关窗口
2. 截取 Unity 窗口区域
3. 在 Unity 窗口内定位 Game 窗口（通过图像分析）
4. 标注并显示结果
"""

import sys
import time
from pathlib import Path
from typing import Optional, Tuple, List

# 导入配置管理器
from config_manager import load_config, get_game_resolution

from PIL import Image, ImageDraw, ImageFont, ImageGrab
import numpy as np

# Windows API
import win32gui
import win32con
import win32ui


# ==================== Windows API 工具函数 ====================
def enum_windows() -> List[Tuple[int, str]]:
    """
    枚举所有窗口
    返回: [(hwnd, title), ...]
    """
    windows = []
    
    def callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append((hwnd, title))
        return True
    
    win32gui.EnumWindows(callback, None)
    return windows


def find_unity_window() -> Optional[Tuple[int, str, Tuple[int, int, int, int]]]:
    """
    查找 Unity 窗口
    返回: (hwnd, title, (left, top, right, bottom)) 或 None
    """
    print("\n[查找 Unity 窗口]")
    
    windows = enum_windows()
    
    # 打印所有窗口（用于调试）
    print("  所有可见窗口:")
    for hwnd, title in windows:
        print(f"    - {title}")
    
    # 查找包含 "Unity" 或游戏名称的窗口
    unity_keywords = ['Unity', 'Game', '游戏', '背包', '商店', '活动']
    
    for hwnd, title in windows:
        title_lower = title.lower()
        
        # 优先查找 Unity Editor 窗口
        if 'unity' in title_lower and ('editor' in title_lower or '202' in title_lower):
            # 获取窗口位置
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            print(f"  ✅ 找到 Unity Editor: '{title}'")
            print(f"     位置: ({left}, {top}, {right}, {bottom})")
            print(f"     尺寸: {right - left} x {bottom - top}")
            return (hwnd, title, rect)
        
        # 查找 Game 窗口
        if 'game' in title_lower and len(title) < 50:
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            print(f"  ✅ 找到 Game 窗口: '{title}'")
            print(f"     位置: ({left}, {top}, {right}, {bottom})")
            print(f"     尺寸: {right - left} x {bottom - top}")
            return (hwnd, title, rect)
    
    # 如果没找到，打印警告
    print("  ⚠️ 未找到 Unity 窗口，尝试查找所有包含 'Unity' 的窗口...")
    for hwnd, title in windows:
        if 'unity' in title.lower():
            rect = win32gui.GetWindowRect(hwnd)
            print(f"  ℹ️ 找到相关窗口: '{title}'")
            print(f"     位置: {rect}")
            return (hwnd, title, rect)
    
    return None


def find_game_window_in_screenshot(
    screenshot: Image.Image,
    game_width: int,
    game_height: int
) -> Optional[Tuple[int, int, int, int]]:
    """
    在截图中查找 Game 窗口位置
    通过分析截图内容，找到游戏界面区域
    
    策略：
    1. 如果截图中有黑色边框，使用黑色边框检测
    2. 否则，查找截图中的矩形区域（Unity Game 窗口有边框）
    3. 如果都找不到，使用分辨率定位（居中）
    
    :param screenshot: PIL Image
    :param game_width: 游戏宽度
    :param game_height: 游戏高度
    :return: (left, top, right, bottom) 或 None
    """
    img_width, img_height = screenshot.size
    
    # 策略1：检测黑色边框
    img_gray = screenshot.convert('L')
    arr_gray = np.array(img_gray)
    
    col_means = np.mean(arr_gray, axis=0)
    row_means = np.mean(arr_gray, axis=1)
    
    # 从左到右扫描
    left = 0
    for x in range(img_width):
        if col_means[x] > 30:
            left = x
            break
    
    # 从右到左扫描
    right = img_width - 1
    for x in range(img_width - 1, -1, -1):
        if col_means[x] > 30:
            right = x
            break
    
    # 从上到下扫描
    top = 0
    for y in range(img_height):
        if row_means[y] > 30:
            top = y
            break
    
    # 从下到上扫描
    bottom = img_height - 1
    for y in range(img_height - 1, -1, -1):
        if row_means[y] > 30:
            bottom = y
            break
    
    # 如果有黑色边框，返回裁剪区域
    if left > 0 or right < img_width - 1 or top > 0 or bottom < img_height - 1:
        print(f"  ✅ 通过黑色边框检测到游戏区域: ({left}, {top}, {right}, {bottom})")
        return (left, top, right, bottom)
    
    # 策略2：使用分辨率定位（居中）
    print(f"  ℹ️ 使用分辨率定位（居中）...")
    left = (img_width - game_width) // 2
    top = (img_height - game_height) // 2
    right = left + game_width - 1
    bottom = top + game_height - 1
    
    # 确保不超出范围
    left = max(0, left)
    top = max(0, top)
    right = min(img_width - 1, right)
    bottom = min(img_height - 1, bottom)
    
    return (left, top, right, bottom)


def capture_window(hwnd: int) -> Image.Image:
    """
    截取指定窗口的内容
    使用 ImageGrab.grab(bbox=...) 方式，更可靠
    :param hwnd: 窗口句柄
    :return: PIL Image
    """
    # 获取窗口位置（包含边框）
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    
    # 获取客户端区域（不包含边框和标题栏）
    client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
    
    # 将客户端坐标转换为屏幕坐标
    # 获取窗口左上角在屏幕上的位置（包含边框）
    window_rect = win32gui.GetWindowRect(hwnd)
    
    # 计算客户端区域在屏幕上的位置
    # 由于 GetClientRect 返回的是相对于窗口左上角的坐标
    # 我们需要加上窗口左上角的屏幕坐标
    # 但是要注意：窗口左上角 (left, top) 包含边框，所以客户端区域的起始点需要加上边框宽度
    
    # 更简单的方法：直接使用窗口矩形（包含边框），然后裁剪掉边框
    # 或者用 ClientToScreen 转换点坐标
    
    # 获取 (0, 0) 在客户端区域的屏幕坐标
    client_origin = win32gui.ClientToScreen(hwnd, (0, 0))
    client_screen_left, client_screen_top = client_origin
    
    # 客户端区域的右下角
    client_bottom_right = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
    client_screen_right, client_screen_bottom = client_bottom_right
    
    # 使用 ImageGrab 截取客户端区域
    bbox = (client_screen_left, client_screen_top, client_screen_right, client_screen_bottom)
    img = ImageGrab.grab(bbox=bbox)
    
    return img


# ==================== 主函数 ====================
def main():
    """主函数"""
    print("=" * 80)
    print("Unity 游戏界面定位 - Windows API 版本")
    print("=" * 80)
    
    # 1. 加载配置
    print("\n[1/5] 加载配置...")
    config = load_config()
    game_width, game_height = get_game_resolution()
    print(f"✅ 游戏分辨率: {game_width} x {game_height}")
    
    # 2. 查找 Unity 窗口
    print("\n[2/5] 查找 Unity 窗口...")
    unity_window = find_unity_window()
    
    # 3. 截图
    print("\n[3/5] 截图...")
    screenshot_dir = Path(__file__).parent / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    if unity_window:
        # 截取 Unity 窗口
        hwnd, title, rect = unity_window
        try:
            screenshot = capture_window(hwnd)
            screenshot_path = str(screenshot_dir / f"unity_window_{timestamp}.png")
            screenshot.save(screenshot_path)
            print(f"✅ Unity 窗口截图已保存: {screenshot_path}")
            print(f"  截图尺寸: {screenshot.width} x {screenshot.height}")
        except Exception as e:
            print(f"⚠️ 截取 Unity 窗口失败: {e}")
            print("  回退到全屏截图...")
            screenshot = ImageGrab.grab()
            screenshot_path = str(screenshot_dir / f"screen_{timestamp}.png")
            screenshot.save(screenshot_path)
            print(f"✅ 全屏截图已保存: {screenshot_path}")
    else:
        # 全屏截图
        print("  未找到 Unity 窗口，使用全屏截图...")
        screenshot = ImageGrab.grab()
        screenshot_path = str(screenshot_dir / f"screen_{timestamp}.png")
        screenshot.save(screenshot_path)
        print(f"✅ 全屏截图已保存: {screenshot_path}")
    
    # 4. 在截图中定位 Game 窗口
    print("\n[4/5] 定位 Game 窗口...")
    game_area = find_game_window_in_screenshot(screenshot, game_width, game_height)
    
    if game_area:
        left, top, right, bottom = game_area
        print(f"✅ Game 窗口区域: ({left}, {top}, {right}, {bottom})")
        print(f"  尺寸: {right - left + 1} x {bottom - top + 1}")
        
        # 裁剪到 Game 窗口
        cropped_img = screenshot.crop((left, top, right + 1, bottom + 1))
        cropped_path = str(screenshot_dir / f"game_window_{timestamp}.png")
        cropped_img.save(cropped_path)
        print(f"✅ 已裁剪到: {cropped_path}")
    else:
        print("⚠️ 未找到 Game 窗口，使用原图")
        cropped_path = screenshot_path
    
    # 5. 标注结果
    print("\n[5/5] 标注结果...")
    annotated_path = str(screenshot_dir / f"game_area_{timestamp}.png")
    
    draw = ImageDraw.Draw(screenshot)
    if game_area:
        left, top, right, bottom = game_area
        # 绘制红色矩形框
        draw.rectangle([left, top, right, bottom], outline='red', width=5)
        # 添加标签
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except:
            font = ImageFont.load_default()
        label = f"Game Window: {right - left + 1} x {bottom - top + 1}"
        draw.text((left, top - 40), label, fill='red', font=font)
    
    screenshot.save(annotated_path)
    print(f"✅ 标注后截图已保存: {annotated_path}")
    
    # 完成
    print("\n" + "=" * 80)
    print("✅ 完成！")
    print("=" * 80)
    print(f"\n结果文件:")
    print(f"  1. 原始/窗口截图: {screenshot_path}")
    if game_area:
        print(f"  2. Game 窗口截图: {cropped_path}")
    print(f"  3. 标注后截图: {annotated_path}")
    print(f"\n请在标注后的截图上确认 Game 窗口区域是否正确。")
    print("=" * 80)


if __name__ == '__main__':
    main()
