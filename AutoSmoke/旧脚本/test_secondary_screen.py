"""
# -*- coding: utf-8 -*-
测试副屏截图 - 不调用 Unity 反射
"""
import time
import numpy as np
from PIL import Image, ImageGrab
import win32gui
from pathlib import Path

print("=" * 60)
print("测试副屏截图")
print("=" * 60)

# 1. 查找 Unity 窗口
print("\n[1] 查找 Unity 窗口...")
unity_hwnd = None
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

# 2. 获取窗口位置和客户区坐标
print("\n[2] 获取窗口位置...")
rect = win32gui.GetWindowRect(unity_hwnd)
left, top, right, bottom = rect
print(f"  窗口位置 (屏幕坐标): ({left}, {top}, {right}, {bottom})")
print(f"  窗口尺寸: {right - left} x {bottom - top}")

# 检查是否在副屏
if left < 0 or top < 0:
    print(f"  ℹ️ 窗口在副屏上 (left={left}, top={top})")

# 获取客户区在屏幕上的坐标
client_origin = win32gui.ClientToScreen(unity_hwnd, (0, 0))
client_left, client_top = client_origin
_, _, client_right, client_bottom = win32gui.GetClientRect(unity_hwnd)
client_bottom_right = win32gui.ClientToScreen(unity_hwnd, (client_right, client_bottom))
client_screen_right, client_screen_bottom = client_bottom_right

print(f"\n  客户区屏幕坐标:")
print(f"    左上: ({client_left}, {client_top})")
print(f"    右下: ({client_screen_right}, {client_screen_bottom})")
print(f"    尺寸: {client_screen_right - client_left} x {client_screen_bottom - client_top}")

# 3. 截取客户区
print("\n[3] 截取客户区...")
bbox = (client_left, client_top, client_screen_right, client_screen_bottom)
print(f"  ImageGrab.bbox = {bbox}")

try:
    img = ImageGrab.grab(bbox=bbox)
    print(f"  ✅ 截图成功: {img.size[0]} x {img.size[1]}")
    
    # 验证截图
    img_array = np.array(img)
    avg_brightness = np.mean(img_array)
    print(f"  平均亮度: {avg_brightness:.1f}")
    
    if avg_brightness < 5:
        print(f"  ⚠️ 截图可能无效（全黑）")
    elif avg_brightness > 250:
        print(f"  ⚠️ 截图可能无效（全白）")
    else:
        print(f"  ✅ 截图有效")
        
except Exception as e:
    print(f"  ❌ 截图失败: {e}")
    exit(1)

# 4. 保存截图
print("\n[4] 保存截图...")
output_path = str(Path(__file__).parent.parent / "screenshots" / "test_secondary_screen.png")
img.save(output_path)
print(f"  ✅ 截图已保存: {output_path}")

print("\n" + "=" * 60)
print("完成！请查看截图")
print("=" * 60)
