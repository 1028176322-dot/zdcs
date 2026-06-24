"""
# -*- coding: utf-8 -*-
测试副屏截图 - 使用 ImageGrab 截取所有屏幕 (简化版)
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

# 2. 获取 Unity 客户区屏幕坐标
print("\n[2] 获取客户区屏幕坐标...")
client_origin = win32gui.ClientToScreen(unity_hwnd, (0, 0))
client_left, client_top = client_origin
_, _, client_right, client_bottom = win32gui.GetClientRect(unity_hwnd)
client_bottom_right = win32gui.ClientToScreen(unity_hwnd, (client_right, client_bottom))
client_screen_right, client_screen_bottom = client_bottom_right

print(f"  客户区屏幕坐标: ({client_left}, {client_top}) -> ({client_screen_right}, {client_screen_bottom})")

# 3. 截取所有屏幕
print("\n[3] 截取所有屏幕...")
try:
    img_all = ImageGrab.grab(all_screens=True)
    print(f"  ✅ 截取所有屏幕成功: {img_all.size[0]} x {img_all.size[1]}")
    
    # 验证截图
    img_array = np.array(img_all)
    avg_brightness = np.mean(img_array)
    print(f"  平均亮度: {avg_brightness:.1f}")
    
except Exception as e:
    print(f"  ❌ 截取失败: {e}")
    exit(1)

# 4. 计算裁剪区域
print("\n[4] 计算裁剪区域...")
# 假设：副屏在左边，主屏在右边
# 副屏: (-1920, 0, 0, 1080)
# 主屏: (0, 0, 1920, 1080)
# 所有屏幕截图: (0, 0, 3840, 1080)  [Pillow 会自动调整坐标]

# 实际上，ImageGrab.grab(all_screens=True) 返回的图像坐标是 (0, 0) 到 (total_width, total_height)
# 我们需要把屏幕坐标映射到图像坐标

# 方法：假设最小左边坐标是 -1920（副屏）
# 那么，屏幕坐标 (x, y) 在图像中的位置是 (x - (-1920), y - 0) = (x + 1920, y)

offset_x = 1920  # 假设副屏在左边，左边坐标是 -1920
offset_y = 0      # 假设所有显示器的顶部对齐

crop_left = client_left + offset_x
crop_top = client_top + offset_y
crop_right = client_screen_right + offset_x
crop_bottom = client_screen_bottom + offset_y

print(f"  偏移量: ({offset_x}, {offset_y})")
print(f"  裁剪区域: ({crop_left}, {crop_top}, {crop_right}, {crop_bottom})")

# 5. 裁剪出 Unity 客户区
print("\n[5] 裁剪出 Unity 客户区...")
try:
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

# 6. 保存截图
print("\n[6] 保存截图...")
output_path = str(Path(__file__).parent.parent / "screenshots" / "test_all_screens_simple.png")
img_crop.save(output_path)
print(f"  ✅ 截图已保存: {output_path}")

# 也保存完整截图（用于调试）
output_path_full = str(Path(__file__).parent.parent / "screenshots" / "test_all_screens_simple.png")
img_all.save(output_path_full)
print(f"  ✅ 完整截图已保存: {output_path_full}")

print("\n" + "=" * 60)
print("完成！请查看截图")
print("=" * 60)
print(f"\n提示: 如果截图还是全黑，请检查 offset_x 和 offset_y 是否正确")
print(f"  Unity 客户区屏幕坐标: ({client_left}, {client_top}) -> ({client_screen_right}, {client_screen_bottom})")
print(f"  所有屏幕截图尺寸: {img_all.size[0]} x {img_all.size[1]}")
