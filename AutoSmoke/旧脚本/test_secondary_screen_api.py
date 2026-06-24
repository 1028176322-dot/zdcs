"""
# -*- coding: utf-8 -*-
测试副屏截图 - 使用 Windows API (BitBlt)
"""
import time
import numpy as np
from PIL import Image, ImageGrab
import win32gui
import win32ui
import win32con
from pathlib import Path

print("=" * 60)
print("测试副屏截图 (Windows API)")
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

# 2. 获取客户区尺寸
print("\n[2] 获取客户区尺寸...")
_, _, client_right, client_bottom = win32gui.GetClientRect(unity_hwnd)
client_width = client_right
client_height = client_bottom
print(f"  客户区尺寸: {client_width} x {client_height}")

# 3. 使用 Windows API 截取客户区
print("\n[3] 使用 Windows API 截取客户区...")

try:
    # 获取窗口 DC
    window_dc = win32gui.GetWindowDC(unity_hwnd)
    src_dc = win32ui.CreateDCFromHandle(window_dc)
    mem_dc = src_dc.CreateCompatibleDC()
    
    # 创建位图
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(src_dc, client_width, client_height)
    mem_dc.SelectObject(bitmap)
    
    # 复制客户区内容 (0, 0) 是客户区原点
    mem_dc.BitBlt((0, 0), (client_width, client_height), src_dc, (0, 0), win32con.SRCCOPY)
    
    # 转换为 PIL Image
    bmp_info = bitmap.GetInfo()
    bmp_str = bitmap.GetBitmapBits(True)
    img = Image.frombuffer(
        'RGB',
        (bmp_info['bmWidth'], bmp_info['bmHeight']),
        bmp_str, 'raw', 'BGRX', 0, 1
    )
    
    # 清理
    win32gui.ReleaseDC(unity_hwnd, window_dc)
    mem_dc.DeleteDC()
    src_dc.DeleteDC()
    win32ui.DeleteObject(bitmap)
    
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
    import traceback
    traceback.print_exc()
    exit(1)

# 4. 保存截图
print("\n[4] 保存截图...")
output_path = str(Path(__file__).parent.parent / "screenshots" / "test_secondary_screen_api.png")
img.save(output_path)
print(f"  ✅ 截图已保存: {output_path}")

print("\n" + "=" * 60)
print("完成！请查看截图")
print("=" * 60)
