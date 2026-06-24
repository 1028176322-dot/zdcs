"""
# -*- coding: utf-8 -*-
测试副屏截图 - 使用 ImageGrab 截取所有屏幕
"""
import time
import numpy as np
from PIL import Image, ImageGrab
import win32gui
from pathlib import Path

print("=" * 60)
print("测试副屏截图 (ImageGrab 所有屏幕)")
print("=" * 60)

# 1. 查找 Unity 窗口
print("\n[1] 查找 Unity 窗口...")
windows_found = []

def enum_callback(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title and 'unity' in title.lower():
            windows_found.append((hwnd, title))
    return True

win32gui.EnumWindows(enum_callback, None)

print(f"  找到 {len(windows_found)} 个包含 'unity' 的窗口:")
for hwnd, title in windows_found:
    rect = win32gui.GetWindowRect(hwnd)
    print(f"    - [{hwnd}] {title}")
    print(f"      位置: {rect}")

if not windows_found:
    print("  ❌ 未找到 Unity 窗口")
    exit(1)

# 使用第一个 Unity 窗口
unity_hwnd, unity_title = windows_found[0]
print(f"\n  使用窗口: {unity_title}")
print(f"  HWND: {unity_hwnd}")

# 2. 获取 Unity 窗口位置和客户区坐标
print("\n[2] 获取窗口位置和客户区坐标...")
rect = win32gui.GetWindowRect(unity_hwnd)
left, top, right, bottom = rect
print(f"  窗口位置 (屏幕坐标): ({left}, {top}, {right}, {bottom})")

# 获取客户区在屏幕上的坐标
client_origin = win32gui.ClientToScreen(unity_hwnd, (0, 0))
client_left, client_top = client_origin
_, _, client_right, client_bottom = win32gui.GetClientRect(unity_hwnd)
client_bottom_right = win32gui.ClientToScreen(unity_hwnd, (client_right, client_bottom))
client_screen_right, client_screen_bottom = client_bottom_right

print(f"  客户区屏幕坐标: ({client_left}, {client_top}) -> ({client_screen_right}, {client_screen_bottom})")

# 3. 截取所有屏幕
print("\n[3] 截取所有屏幕...")
try:
    # 方法1: 使用 ImageGrab.grab(all_screens=True)
    img_all = ImageGrab.grab(all_screens=True)
    print(f"  ✅ 截取所有屏幕成功: {img_all.size[0]} x {img_all.size[1]}")
    
    # 验证截图
    img_array = np.array(img_all)
    avg_brightness = np.mean(img_array)
    print(f"  平均亮度: {avg_brightness:.1f}")
    
except Exception as e:
    print(f"  ❌ 截取失败: {e}")
    exit(1)

# 4. 裁剪出 Unity 客户区
print("\n[4] 裁剪出 Unity 客户区...")
try:
    # 计算客户区在所有屏幕截图中的位置
    # 假设主屏在 (0, 0)，副屏在左边 (-1920, 0)
    # 所有屏幕截图的左上角是所有显示器的最小坐标
    
    # 获取所有显示器的边界
    monitors = []
    def enum_monitors(hmonitor, hdc_monitor, rect, data):
        monitors.append((
            rect[0],  # left
            rect[1],  # top
            rect[2],  # right
            rect[3]   # bottom
        ))
        return True
    
    win32gui.EnumDisplayMonitors(None, None, enum_monitors, None)
    print(f"  找到 {len(monitors)} 个显示器:")
    for i, mon in enumerate(monitors):
        print(f"    {i+1}. {mon}")
    
    # 计算所有屏幕截图的左上角坐标
    min_left = min(mon[0] for mon in monitors)
    min_top = min(mon[1] for mon in monitors)
    print(f"  所有屏幕截图左上角: ({min_left}, {min_top})")
    
    # 计算客户区在所有屏幕截图中的位置
    crop_left = client_left - min_left
    crop_top = client_top - min_top
    crop_right = client_screen_right - min_left
    crop_bottom = client_screen_bottom - min_top
    
    print(f"  裁剪区域: ({crop_left}, {crop_top}, {crop_right}, {crop_bottom})")
    
    # 裁剪
    img_crop = img_all.crop((crop_left, crop_top, crop_right, crop_bottom))
    print(f"  ✅ 裁剪成功: {img_crop.size[0]} x {img_crop.size[1]}")
    
    # 验证裁剪后的图像
    img_crop_array = np.array(img_crop)
    avg_brightness = np.mean(img_crop_array)
    print(f"  裁剪后平均亮度: {avg_brightness:.1f}")
    
    if avg_brightness < 5:
        print(f"  ⚠️ 裁剪后图像可能无效（全黑）")
    else:
        print(f"  ✅ 裁剪后图像有效")
        
except Exception as e:
    print(f"  ❌ 裁剪失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 5. 保存截图
print("\n[5] 保存截图...")
output_path = str(Path(__file__).parent.parent / "screenshots" / "test_all_screens.png")
img_crop.save(output_path)
print(f"  ✅ 截图已保存: {output_path}")

print("\n" + "=" * 60)
print("完成！请查看截图")
print("=" * 60)
