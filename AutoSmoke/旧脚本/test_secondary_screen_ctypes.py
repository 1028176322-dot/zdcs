"""
# -*- coding: utf-8 -*-
测试副屏截图 - 使用 ctypes 调用 PrintWindow API
"""
import time
import numpy as np
from PIL import Image
import win32gui
import ctypes
from ctypes import wintypes
from pathlib import Path

print("=" * 60)
print("测试副屏截图 (ctypes PrintWindow)")
print("=" * 60)

# 定义常量
PW_RENDERFULLCONTENT = 0x00000002

# 加载 user32.dll
user32 = ctypes.windll.user32

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

# 2. 获取客户区尺寸
print("\n[2] 获取客户区尺寸...")
_, _, client_right, client_bottom = win32gui.GetClientRect(unity_hwnd)
client_width = client_right
client_height = client_bottom
print(f"  客户区尺寸: {client_width} x {client_height}")

# 3. 使用 PrintWindow API 截取窗口
print("\n[3] 使用 PrintWindow API 截取窗口...")

try:
    # 创建 DC 和位图
    hwnd_dc = win32gui.GetWindowDC(unity_hwnd)
    src_dc = ctypes.windll.gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hwnd_dc, client_width, client_height)
    old_bitmap = ctypes.windll.gdi32.SelectObject(src_dc, bitmap)
    
    # 调用 PrintWindow
    result = user32.PrintWindow(unity_hwnd, src_dc, PW_RENDERFULLCONTENT)
    
    if result:
        print(f"  ✅ PrintWindow 成功")
        
        # 读取位图数据
        bmp_info = win32gui.GetObjectBitmap(bitmap)
        # 使用 PIL 直接从 DC 读取
        # 更简单的方法：使用 ImageGrab 截取整个窗口
        # 但是，我们可以使用 BitBlt 从 src_dc 复制到内存 DC
        
        # 创建 PIL Image
        import struct
        bmp_data = ctypes.create_string_buffer(client_width * client_height * 4)
        ctypes.windll.gdi32.GetDIBits(src_dc, bitmap, 0, client_height, bmp_data, None, 0)
        
        # 转换为 PIL Image (BGRA -> RGB)
        img = Image.frombuffer('RGB', (client_width, client_height), bmp_data, 'raw', 'BGRX', 0, 1)
        
    else:
        print(f"  ⚠️ PrintWindow 失败")
        img = None
    
    # 清理
    ctypes.windll.gdi32.SelectObject(src_dc, old_bitmap)
    ctypes.windll.gdi32.DeleteObject(bitmap)
    ctypes.windll.gdi32.DeleteDC(src_dc)
    win32gui.ReleaseDC(unity_hwnd, hwnd_dc)
    
    if img is None:
        print(f"  ❌ 截图失败")
        exit(1)
    
    print(f"  ✅ 截图成功: {img.size[0]} x {img.size[1]}")
    
    # 验证截图
    img_array = np.array(img)
    avg_brightness = np.mean(img_array)
    print(f"  平均亮度: {avg_brightness:.1f}")
    
    if avg_brightness < 5:
        print(f"  ⚠️ 截图可能无效（全黑）")
        print(f"  💡 可能原因：Unity 窗口最小化、被遮挡、或者在其他虚拟桌面")
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
output_path = str(Path(__file__).parent.parent / "screenshots" / "test_secondary_screen_ctypes.png")
img.save(output_path)
print(f"  ✅ 截图已保存: {output_path}")

print("\n" + "=" * 60)
print("完成！请查看截图")
print("=" * 60)
