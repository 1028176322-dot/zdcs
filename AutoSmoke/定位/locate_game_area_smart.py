"""
# -*- coding: utf-8 -*-
Unity 游戏界面定位 - 智能图像分析版本

检测策略（优先级从高到低）：
1. 【最准确】Unity 反射读取：通过 C# Editor 脚本直接读取 Game 视图屏幕坐标
2. 【降级】图像分析：截图上分析颜色/结构特征定位 Game 视图

用法：
    python locate_game_area_smart.py          # 自动选择最佳方法
    python locate_game_area_smart.py --force-image   # 强制使用图像分析
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Optional, Tuple
# 确保能找到根目录模块
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

import ctypes
import ctypes.wintypes

from config_manager import load_config, get_game_resolution, set_game_view_coords

from PIL import Image, ImageDraw, ImageFont, ImageGrab
import numpy as np

import win32gui
import win32con

# ==================== 多显示器支持工具函数 ====================
def get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """
    获取虚拟屏幕边界（所有显示器的联合边界）
    
    返回: (left, top, right, bottom) 虚拟屏幕边界
    """
    user32 = ctypes.windll.user32
    
    # 获取虚拟屏幕的起始坐标和尺寸
    virtual_left = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
    virtual_top = user32.GetSystemMetrics(77)    # SM_YVIRTUALSCREEN
    virtual_width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    virtual_height = user32.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN
    
    virtual_right = virtual_left + virtual_width
    virtual_bottom = virtual_top + virtual_height
    
    return (virtual_left, virtual_top, virtual_right, virtual_bottom)


def capture_all_screens() -> Tuple[Image.Image, int, int]:
    """
    截取所有显示器的屏幕内容
    
    返回: (image, offset_x, offset_y)
        - image: 所有屏幕的拼接图像
        - offset_x: 屏幕坐标 X 到图像坐标 X 的偏移量（image_x = screen_x - offset_x）
        - offset_y: 屏幕坐标 Y 到图像坐标 Y 的偏移量（image_y = screen_y - offset_y）
    """
    # 获取虚拟屏幕边界
    virtual_left, virtual_top, virtual_right, virtual_bottom = get_virtual_screen_bounds()
    
    # 截取所有屏幕
    img = ImageGrab.grab(all_screens=True)
    
    # 计算偏移量
    # 图像坐标 (0, 0) 对应屏幕坐标 (virtual_left, virtual_top)
    offset_x = virtual_left
    offset_y = virtual_top
    
    return (img, offset_x, offset_y)


def screen_to_image_coords(
    screen_left: int,
    screen_top: int,
    screen_right: int,
    screen_bottom: int,
    offset_x: int,
    offset_y: int
) -> Tuple[int, int, int, int]:
    """
    将屏幕坐标转换为图像坐标
    
    参数:
        screen_left, screen_top, screen_right, screen_bottom: 屏幕坐标
        offset_x, offset_y: 屏幕坐标到图像坐标的偏移量
    
    返回: (image_left, image_top, image_right, image_bottom) 图像坐标
    """
    image_left = screen_left - offset_x
    image_top = screen_top - offset_y
    image_right = screen_right - offset_x
    image_bottom = screen_bottom - offset_y
    
    return (image_left, image_top, image_right, image_bottom)


# ==================== Unity 反射读取 + 图像分析修正 ====================
def try_get_unity_game_view_pos(editor_hwnd: int, img_rgb: np.ndarray = None) -> Optional[Tuple[int, int, int, int]]:
    """
    尝试通过 Unity 反射读取 Game 视图坐标，然后用图像分析修正底部位置
    
    流程：
    1. 检查 JSON 缓存是否存在且新鲜（< 60s）
    2. 若过期/不存在，提示用户点击 Unity 菜单
    3. 读取 JSON，转换为截图坐标
    4. 如果提供了截图，在返回的坐标附近用图像分析搜索正确的底部
    
    返回：(left, top, right, bottom) 截图坐标，或 None
    """
    print("\n[方法1] 尝试通过 Unity 反射读取 Game 视图坐标...")
    
    # 延迟导入，避免无 Unity 环境时崩溃
    try:
        from 定位.game_view_locator import (
            get_game_view_pos,
            convert_to_screenshot_coords,
            JSON_OUTPUT_PATH,
        )
    except ImportError as e:
        print(f"  ⚠️ game_view_locator 导入失败: {e}")
        return None
    
    # 检查缓存是否新鲜（60秒内）
    cache_fresh = False
    if JSON_OUTPUT_PATH.exists():
        age = time.time() - JSON_OUTPUT_PATH.stat().st_mtime
        if age < 60:
            print(f"  📂 使用缓存坐标（{age:.0f}s 前）")
            cache_fresh = True
    
    # 获取坐标（会触发 Unity 编译+执行）
    try:
        screen_pos = get_game_view_pos(force_refresh=not cache_fresh)
    except Exception as e:
        print(f"  ❌ 获取坐标失败: {e}")
        return None
    
    if not screen_pos:
        print("  ❌ Unity 未返回有效坐标")
        return None
    
    gx, gy, gw, gh = screen_pos
    print(f"  ✅ Unity 返回屏幕坐标: x={gx}, y={gy}, w={gw}, h={gh}")
    
    # 转换为截图坐标（使用Unity客户区左上角作为偏移量）
    try:
        # 获取Unity客户区左上角屏幕坐标
        import win32gui
        client_origin = win32gui.ClientToScreen(editor_hwnd, (0, 0))
        unity_client_x, unity_client_y = client_origin
        print(f"  Unity客户区屏幕坐标: ({unity_client_x}, {unity_client_y})")
        
        # 转换为截图坐标（截图是Unity客户区的裁剪）
        left = gx - unity_client_x
        top = gy - unity_client_y
        right = left + gw
        bottom = top + gh
        
        print(f"  📐 初步截图坐标: ({left}, {top}, {right}, {bottom})")
        
    except Exception as e:
        print(f"  ❌ 坐标转换失败: {e}")
        return None
    
    # 如果提供了截图，用图像分析修正底部位置
    if img_rgb is not None:
        print(f"\n  🔍 用图像分析修正底部位置...")
        corrected_bottom = correct_game_view_bottom(img_rgb, left, top, right, bottom)
        if corrected_bottom > bottom:
            print(f"  ✅ 修正底部: {bottom} -> {corrected_bottom} (+{corrected_bottom - bottom}px)")
            bottom = corrected_bottom
        else:
            print(f"  ⚠️ 未找到更低的底部，保持原样: {bottom}")
    
    return (left, top, right, bottom)


def correct_game_view_bottom(
    img_rgb: np.ndarray,
    left: int,
    top: int,
    right: int,
    bottom: int
) -> int:
    """
    在当前底部附近，用图像分析搜索正确的 Game 视图底部
    
    参数：
        img_rgb: 截图数据（numpy array）
        left, top, right, bottom: 当前 Game 视图坐标（截图坐标）
    
    返回：修正后的底部 y 坐标
    """
    height, width = img_rgb.shape[:2]
    
    # 搜索范围：从当前底部 -20 到 +50（更保守的范围）
    search_start = max(top + 50, bottom - 20)
    search_end = min(bottom + 50, height - 1)
    
    print(f"    搜索范围: y={search_start} 到 y={search_end}")
    
    if search_start >= search_end:
        print(f"    ⚠️ 搜索范围无效，保持原样")
        return bottom
    
    # 方法1：检测水平分隔线（颜色突变）
    best_divider = None
    best_score = 0
    
    # 取中间 60% 的宽度进行分析（避免边缘干扰）
    mid_left = int(left + (right - left) * 0.2)
    mid_right = int(right - (right - left) * 0.2)
    
    prev_avg = None
    for y in range(search_start, search_end):
        # 计算这一行的平均颜色
        row = img_rgb[y, mid_left:mid_right]
        if row.size == 0:
            continue
        row_avg = np.mean(row, axis=0)  # (3,) RGB 平均值
        
        # 计算这一行与上一行的差异
        if prev_avg is not None:
            diff = np.sqrt(np.sum((row_avg - prev_avg) ** 2))
            
            # 如果差异很大，可能是分隔线
            if diff > 25:  # 提高阈值，减少误判
                # 检查是否是持续的分隔线（连续多行都有差异）
                consistent = True
                for dy in range(1, 5):
                    if y + dy < search_end:
                        next_row = img_rgb[y+dy, mid_left:mid_right]
                        if next_row.size == 0:
                            continue
                        next_avg = np.mean(next_row, axis=0)
                        next_diff = np.sqrt(np.sum((row_avg - next_avg) ** 2))
                        if next_diff < 15:  # 分隔线通常持续几行
                            consistent = False
                            break
                
                if consistent and diff > best_score:
                    best_score = diff
                    best_divider = y
                    print(f"    找到候选分隔线: y={y}, 差异={diff:.1f}")
        
        prev_avg = row_avg
    
    # 方法2：检测 Game 视图底部（从当前底部向下搜索）
    # 原理：向下搜索，找到第一个"颜色丰富"的行（Game 视图内容）
    ref_region = img_rgb[bottom-50:bottom, left:right]
    if ref_region.size > 0:
        ref_std = np.std(ref_region)
    else:
        ref_std = 20
    
    game_bottom = bottom  # 默认值
    for y in range(bottom, min(bottom + 50, height - 1), 5):  # 每次跳 5 行，更保守
        row = img_rgb[y:y+5, left:right]
        if row.size == 0:
            continue
        
        row_std = np.std(row)
        
        # 如果颜色标准差突然变大，说明进入了 Game 视图内容区
        if row_std > ref_std * 1.5 and row_std > 25:
            game_bottom = y
            print(f"    找到颜色丰富区域: y={y}, 标准差={row_std:.1f}")
            break
        
        # 或者，如果这一行与上一行的差异很大，说明找到了 Game 视图底部边界
        if y > bottom:
            prev_row = img_rgb[y-5:y, left:right]
            if prev_row.size > 0:
                prev_std = np.std(prev_row)
                std_diff = abs(row_std - prev_std)
                
                if std_diff > 15:
                    game_bottom = y
                    print(f"    找到底部边界: y={y}, 标准差差异={std_diff:.1f}")
                    break
    
    # 选择更可信的结果（更保守：只有明显更好时才修正）
    if game_bottom > bottom and game_bottom - bottom > 5:  # 至少修正 5px 才采纳
        print(f"    采用方法2结果（找到更低底部）: y={game_bottom}")
        return game_bottom
    elif best_divider and best_score > 40:  # 提高阈值，减少误判
        print(f"    采用方法1结果（找到分隔线）: y={best_divider}")
        return best_divider
    else:
        print(f"    ⚠️ 未找到可信的新底部，保持原样: y={bottom}")
        return bottom


# ==================== Windows API 工具函数 ====================
def find_unity_window() -> Optional[Tuple[int, str, Tuple[int, int, int, int]]]:
    """
    查找 Unity 窗口
    返回: (hwnd, title, (left, top, right, bottom)) 或 None
    """
    print("\n[查找 Unity 窗口]")
    
    def enum_windows():
        windows = []
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append((hwnd, title))
            return True
        win32gui.EnumWindows(callback, None)
        return windows
    
    windows = enum_windows()
    
    # 查找 Unity Editor
    for hwnd, title in windows:
        title_lower = title.lower()
        if 'unity' in title_lower and ('editor' in title_lower or '202' in title_lower):
            rect = win32gui.GetWindowRect(hwnd)
            print(f"  ✅ 找到 Unity Editor: '{title}'")
            print(f"     位置: {rect}")
            return (hwnd, title, rect)
    
    # 查找包含 Unity 的窗口
    for hwnd, title in windows:
        if 'unity' in title.lower():
            rect = win32gui.GetWindowRect(hwnd)
            print(f"  ✅ 找到 Unity 窗口: '{title}'")
            print(f"     位置: {rect}")
            return (hwnd, title, rect)
    
    return None


def capture_window_client(hwnd: int) -> Image.Image:
    """
    截取 Unity Editor 窗口客户区，支持多显示器（不移动窗口）
    
    使用 ImageGrab.grab(all_screens=True) 截取所有屏幕，
    然后裁剪出 Unity 窗口客户区部分。
    """
    print(f"\n[截取 Unity 窗口客户区]")
    
    # 获取窗口当前位置
    original_rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = original_rect
    print(f"  📍 Unity 窗口位置: ({left}, {top}, {right}, {bottom})")
    
    # 获取客户区在屏幕上的坐标
    client_origin = win32gui.ClientToScreen(hwnd, (0, 0))
    client_left, client_top = client_origin
    
    _, _, client_right, client_bottom = win32gui.GetClientRect(hwnd)
    client_bottom_right = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
    client_screen_right, client_screen_bottom = client_bottom_right
    
    print(f"  📐 客户区屏幕坐标: ({client_left}, {client_top}) -> ({client_screen_right}, {client_screen_bottom})")
    
    # 方法：截取所有屏幕，然后裁剪
    try:
        # 截取所有屏幕
        img_all, offset_x, offset_y = capture_all_screens()
        print(f"  📸 截取所有屏幕成功: {img_all.size[0]} x {img_all.size[1]}")
        print(f"  📏 虚拟屏幕偏移量: ({offset_x}, {offset_y})")
        
        # 将客户区屏幕坐标转换为图像坐标
        crop_left, crop_top, crop_right, crop_bottom = screen_to_image_coords(
            client_left, client_top, client_screen_right, client_screen_bottom,
            offset_x, offset_y
        )
        
        print(f"  ✂️ 裁剪区域（图像坐标）: ({crop_left}, {crop_top}, {crop_right}, {crop_bottom})")
        
        # 裁剪
        img = img_all.crop((crop_left, crop_top, crop_right, crop_bottom))
        
        # 验证截图
        img_array = np.array(img)
        avg_brightness = np.mean(img_array)
        print(f"  🔆 截图平均亮度: {avg_brightness:.1f}")
        
        if avg_brightness < 5:
            print(f"  ⚠️ 截图可能无效（平均亮度={avg_brightness:.1f}，可能截到了黑屏）")
            print(f"  💡 建议: 请确保 Unity 窗口未被最小化且未被其他窗口完全遮挡")
        else:
            print(f"  ✅ 截图成功: {img.size[0]}x{img.size[1]}")
        
    except Exception as e:
        print(f"  ❌ 截图失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return img


# ==================== Game 窗口检测辅助函数 ====================
def evaluate_game_view_candidate(
    img_rgb: np.ndarray,
    left: int,
    top: int,
    right: int,
    bottom: int,
    game_ratio: float
) -> float:
    """
    评估一个区域是否是 Game 视图的候选
    返回得分 (0-100)
    """
    score = 0.0
    height = bottom - top
    width = right - left
    
    if height <= 0 or width <= 0:
        return 0.0
    
    # 1. 宽高比匹配得分 (40分)
    actual_ratio = width / height
    ratio_diff = abs(actual_ratio - game_ratio) / max(actual_ratio, game_ratio)
    ratio_score = max(0, 1 - ratio_diff) * 40
    score += ratio_score
    
    # 2. 内容颜色丰富度得分 (30分)
    # Game 视图的游戏内容区域颜色丰富
    # 但需要考虑标签栏和控制栏（它们颜色单一）
    toolbar_height = min(50, height // 3)  # 估计标签栏+控制栏高度
    content_top = top + toolbar_height
    
    if content_top < bottom:
        content_region = img_rgb[content_top:bottom, left:right, :]
        color_std = np.std(content_region)
        color_mean = np.mean(content_region)
        
        # Game 画面通常颜色丰富（标准差大）
        if color_std > 20:
            score += min(color_std / 30, 1.0) * 30
        elif color_std > 10:
            score += (color_std - 10) / 10 * 15
        
        # 避免全黑或全灰的区域
        if color_mean < 30:  # 太暗
            score -= 20
        elif color_mean > 250:  # 太亮（可能是空白）
            score -= 20
    
    # 3. 位置得分 (20分)
    img_height, img_width = img_rgb.shape[:2]
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    
    # Game 视图通常在 Editor 的左侧或中央
    if center_x < img_width * 0.4:
        score += 20
    elif center_x < img_width * 0.6:
        score += 10
    
    # Game 视图通常在 Editor 的上半部分
    if center_y < img_height * 0.5:
        score += 10
    
    # 4. 标签栏特征得分 (10分)
    # 检查顶部是否有深色标签栏
    if top > 0 and top < img_height * 0.3:
        # 检查顶部区域是否是深色（标签栏特征）
        top_region = img_rgb[max(0, top-5):top+5, left:right, :]
        top_brightness = np.mean(top_region)
        if top_brightness < 100:  # 深色标签栏
            score += 10
    
    return score


def get_default_game_area(
    img_width: int,
    img_height: int,
    game_ratio: float
) -> Tuple[int, int, int, int]:
    """
    当自动检测失败时的默认 Game 区域
    假设 Game 视图在 Editor 左侧偏上位置
    """
    # 默认宽度：Editor 宽度的 35%
    default_width = int(img_width * 0.35)
    # 根据宽高比计算高度
    default_height = int(default_width / game_ratio)
    
    # 确保不超出范围
    default_height = min(default_height, int(img_height * 0.6))
    
    # 放置在左侧 15% 处（Unity 默认布局）
    left = max(50, int(img_width * 0.15))
    top = max(50, int(img_height * 0.08))
    right = min(img_width - 50, left + default_width)
    bottom = min(img_height - 50, top + default_height)
    
    return (left, top, right, bottom)

def find_game_window_in_editor(
    editor_img: Image.Image,
    game_width: int,
    game_height: int
) -> Optional[Tuple[int, int, int, int]]:
    """
    在 Unity Editor 截图中查找 Game 视图（改进版）
    
    改进策略：
    1. 识别 Game 视图的完整结构：标签栏 + 控制栏 + 游戏内容
    2. 利用宽高比匹配（考虑标签栏和控制栏的高度）
    3. 验证内容区域是否有丰富的颜色（游戏画面）
    4. 使用多尺度搜索，避免遗漏
    
    返回: (left, top, right, bottom) 或 None
    """
    print("\n[查找 Game 窗口] (改进版)")
    
    img_width, img_height = editor_img.size
    print(f"  Editor 尺寸: {img_width} x {img_height}")
    print(f"  游戏分辨率: {game_width} x {game_height} (宽高比: {game_width/game_height:.3f})")
    
    # 转换为 numpy 数组
    img_rgb = np.array(editor_img)
    
    # 计算游戏分辨率的宽高比
    game_ratio = game_width / game_height
    
    # ==================== 改进：检测 Game 视图的完整结构 ====================
    print("\n  [策略] 检测 Game 视图结构...")
    
    candidates = []
    
    # 搜索参数
    search_step = 30  # 搜索步长（加快速度）
    min_width = int(game_width * 0.2)  # 最小宽度（游戏宽度的 20%）
    max_width = int(game_width * 1.5)  # 最大宽度（游戏宽度的 150%）
    
    # 将最小/最大宽度转换为在 Editor 截图中的可能像素值
    # Game 视图在 Editor 中显示时会被缩放
    min_width_px = int(img_width * 0.1)
    max_width_px = int(img_width * 0.5)  # 限制到左半部分
    
    # 限制搜索区域：Game 视图通常在左半部分和上部分
    max_left = int(img_width * 0.6)  # 只搜索左 60% 区域
    max_top = int(img_height * 0.5)   # 只搜索上 50% 区域
    
    print(f"  搜索范围: 宽度 {min_width_px}-{max_width_px}px, 步长 {search_step}px")
    print(f"  搜索区域: left<{max_left}, top<{max_top}")
    
    # 滑动窗口搜索
    for left in range(0, min(max_left, img_width - min_width_px), search_step):
        for top in range(20, min(max_top, int(img_height * 0.6)), search_step):
            # 尝试不同的宽度
            for width_px in range(min_width_px, min(max_width_px, img_width - left), search_step * 2):
                # 根据宽高比计算高度（包含标签栏和控制栏）
                # 标签栏约 20-30px，控制栏约 20-30px
                toolbar_height = 50  # 标签栏 + 控制栏的总高度估计
                content_height_px = int(width_px / game_ratio)
                total_height_px = content_height_px + toolbar_height
                
                bottom = top + total_height_px
                if bottom > img_height - 20:  # 确保不超出图片
                    continue
                
                # 评估这个区域
                score = evaluate_game_view_candidate(
                    img_rgb, left, top, left + width_px, bottom, game_ratio
                )
                
                if score > 60:  # 只保留得分较高的候选
                    candidates.append({
                        'left': left,
                        'top': top,
                        'right': left + width_px,
                        'bottom': bottom,
                        'width': width_px,
                        'height': total_height_px,
                        'score': score
                    })
    
    print(f"\n  找到 {len(candidates)} 个候选区域")
    
    if not candidates:
        print("  ⚠️ 未找到候选区域，使用默认位置")
        return get_default_game_area(img_width, img_height, game_ratio)
    
    # 按得分排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # 输出前 5 个候选
    print(f"\n  前 5 个最佳候选:")
    for i, c in enumerate(candidates[:5]):
        print(f"    {i+1}. ({c['left']}, {c['top']}, {c['right']}, {c['bottom']})"
              f" 尺寸: {c['width']}x{c['height']} 得分: {c['score']:.1f}")
    
    # 返回最佳候选
    best = candidates[0]
    print(f"\n  ✅ 最佳 Game 窗口区域: ({best['left']}, {best['top']}, {best['right']}, {best['bottom']})")
    print(f"    尺寸: {best['width']} x {best['height']}")
    print(f"    宽高比: {best['width'] / best['height']:.3f} (游戏: {game_ratio:.3f})")
    
    return (best['left'], best['top'], best['right'], best['bottom'])


# ==================== 标注结果 ====================
def draw_game_area(
    img: Image.Image,
    game_area: Tuple[int, int, int, int],
    output_path: str,
    title: str = "Game Window"
):
    """在图片上标注 Game 窗口"""
    # 创建副本，避免修改原图
    img_copy = img.copy()
    draw = ImageDraw.Draw(img_copy)
    left, top, right, bottom = game_area
    
    print(f"  📐 标注区域: ({left}, {top}, {right}, {bottom})")
    print(f"  📏 区域尺寸: {right - left} x {bottom - top}")
    
    # 绘制红色矩形框（使用RGB元组确保颜色正确显示）
    red = (255, 0, 0)
    draw.rectangle([left, top, right, bottom], outline=red, width=6)
    
    # 添加标签
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    label = f"{title}: {right - left}x{bottom - top}"
    text_y = max(0, top - 25)
    draw.text((left, text_y), label, fill=red, font=font)
    
    # 验证标注是否成功
    img_array = np.array(img_copy)
    region = img_array[top:bottom, left:right, :]
    has_red = np.any((region[:,:, 0] > 200) & (region[:,:, 1] < 100) & (region[:,:, 2] < 100))
    print(f"  ✅ 标注验证: 区域包含红色像素 = {has_red}")
    
    img_copy.save(output_path)
    print(f"  ✅ 标注后截图已保存: {output_path}")


# ==================== 主函数 ====================
def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unity Game 视图定位")
    parser.add_argument('--force-image', action='store_true', help='强制使用图像分析（跳过 Unity 反射）')
    args = parser.parse_args()
    
    print("=" * 80)
    print("Unity 游戏界面定位")
    print("=" * 80)
    
    # 1. 加载配置
    print("\n[1/4] 加载配置...")
    game_width, game_height = get_game_resolution()
    print(f"✅ 游戏分辨率: {game_width} x {game_height}")
    
    # 2. 查找 Unity 窗口并截图
    print("\n[2/4] 查找 Unity 窗口...")
    unity_window = find_unity_window()
    
    screenshot_dir = Path(__file__).parent / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    hwnd = None
    if unity_window:
        hwnd, title, rect = unity_window
        try:
            editor_img = capture_window_client(hwnd)
            editor_path = str(screenshot_dir / f"editor_{timestamp}.png")
            editor_img.save(editor_path)
            print(f"✅ Unity Editor 截图已保存: {editor_path}")
        except Exception as e:
            print(f"⚠️ 截图失败: {e}")
            return
    else:
        print("❌ 未找到 Unity 窗口")
        return
    
    # 3. 获取 Game 窗口坐标
    print("\n[3/4] 获取 Game 窗口坐标...")
    
    game_area = None
    
    # 方法1：Unity 反射读取 + 图像分析修正（优先，除非强制图像分析）
    if not args.force_image:
        try:
            # 传入截图数据，用于修正底部位置
            img_rgb = np.array(editor_img)
            game_area = try_get_unity_game_view_pos(hwnd, img_rgb)
        except Exception as e:
            print(f"  ⚠️ Unity 反射读取失败: {e}")
    
    # 方法2：图像分析（降级）
    if game_area is None:
        print("\n  [降级] 使用图像分析...")
        game_area = find_game_window_in_editor(editor_img, game_width, game_height)
    
    if game_area:
        left, top, right, bottom = game_area
        print(f"\n✅ Game 窗口区域: ({left}, {top}, {right}, {bottom})")
        print(f"  尺寸: {right - left} x {bottom - top}")
        
        # 保存坐标到 config.json
        try:
            set_game_view_coords(left, top, right, bottom)
        except Exception as e:
            print(f"⚠️ 保存坐标到配置文件失败: {e}")
        
        # 裁剪到 Game 窗口
        game_img = editor_img.crop((left, top, right, bottom))
        game_path = str(screenshot_dir / f"game_{timestamp}.png")
        game_img.save(game_path)
        print(f"✅ Game 窗口截图已保存: {game_path}")
    else:
        print("\n⚠️ 未找到 Game 窗口")
        game_path = editor_path
    
    # 4. 标注结果
    print("\n[4/4] 标注结果...")
    annotated_path = str(screenshot_dir / f"game_area_{timestamp}.png")
    if game_area:
        draw_game_area(editor_img, game_area, annotated_path)
    else:
        # 未找到时，保存原图
        editor_img.save(annotated_path)
        print(f"  已保存未标注截图: {annotated_path}")
    
    # 完成
    print("\n" + "=" * 80)
    print("✅ 完成！")
    print("=" * 80)
    print(f"\n结果文件:")
    print(f"  1. Editor 截图: {editor_path}")
    if game_area:
        print(f"  2. Game 窗口截图: {game_path}")
    print(f"  3. 标注后截图: {annotated_path}")
    print(f"\n请在标注后的截图上确认 Game 窗口是否正确。")
    print("=" * 80)


if __name__ == '__main__':
    main()
