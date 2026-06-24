"""修复所有被损坏的 Python 文件"""
import os, sys, re, py_compile
from pathlib import Path

ROOT = Path('E:/zdcs/AutoSmoke')

# ── 修复清单 ──

# 1. detect_game_bottom.py - 完全被压扁了，重建
fixed_detect = """# -*- coding: utf-8 -*-
\"\"\"Game 视图底部检测\"\"\"
import sys
import os
import json
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

def detect_horizontal_divider(img_array, search_left, search_right, search_top, search_bottom):
    \"\"\"检测水平分割线（工具栏与游戏内容交界）\"\"\"
    best_divider = None
    best_score = 0
    mid_left = int(search_left + (search_right - search_left) * 0.2)
    mid_right = int(search_right - (search_right - search_left) * 0.2)
    for y in range(search_top, search_bottom):
        row = img_array[y, mid_left:mid_right]
        row_avg = np.mean(row, axis=0)
        if y > search_top:
            prev_row = img_array[y - 1, mid_left:mid_right]
            prev_avg = np.mean(prev_row, axis=0)
            diff = np.sqrt(np.sum((row_avg - prev_avg) ** 2))
            if diff > 20:
                consistent = True
                for dy in range(1, 5):
                    if y + dy < search_bottom:
                        next_row = img_array[y + dy, mid_left:mid_right]
                        next_avg = np.mean(next_row, axis=0)
                        next_diff = np.sqrt(np.sum((row_avg - next_avg) ** 2))
                        if next_diff < 10:
                            consistent = False
                            break
                if consistent and diff > best_score:
                    best_score = diff
                    best_divider = y
    return best_divider, best_score


def detect_game_area_bottom(img_array, current_box):
    \"\"\"检测 Game 视图底部\"\"\"
    left, top, right, bottom = current_box
    search_end = min(bottom + 200, img_array.shape[0] - 1)
    ref_region = img_array[bottom - 50:bottom, left:right]
    ref_std = np.std(ref_region) if ref_region.size > 0 else 20
    for y in range(bottom, search_end, 5):
        row = img_array[y:y + 5, left:right]
        if row.size == 0:
            continue
        row_std = np.std(row)
        if y > bottom:
            prev_row = img_array[y - 5:y, left:right]
            if prev_row.size > 0:
                prev_std = np.std(prev_row)
                std_diff = abs(row_std - prev_std)
                if std_diff > 15:
                    return y
        if row_std > ref_std * 1.5 and row_std > 25:
            return y
    return bottom


if __name__ == '__main__':
    screenshots_dir = Path('screenshots')
    png_files = list(screenshots_dir.glob('editor_*.png'))
    if not png_files:
        print("未找到截图")
        sys.exit(1)
    latest_png = max(png_files, key=lambda p: p.stat().st_mtime)
    img = Image.open(latest_png)
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    current_box = (271, 30, 759, 741)
    search_top = current_box[3] - 50
    search_bottom = min(current_box[3] + 150, height - 1)
    search_left = current_box[0]
    search_right = current_box[2]
    divider_y, divider_score = detect_horizontal_divider(
        img_array, search_left, search_right, search_top, search_bottom)
    game_bottom = detect_game_area_bottom(img_array, current_box)

    if game_bottom > current_box[3]:
        final_bottom = game_bottom
    elif divider_y and divider_score > 30:
        final_bottom = divider_y
    else:
        final_bottom = current_box[3]

    new_top = current_box[1]
    new_height = final_bottom - new_top
    print(f"left={current_box[0]}, top={new_top}")
    print(f"right={current_box[2]}, bottom={final_bottom}")
    print(f"height={new_height}")

    output_path = ROOT / 'config' / 'game_view_detected_bottom.json'
    result = {
        'left': current_box[0], 'top': new_top,
        'right': current_box[2], 'bottom': final_bottom,
        'width': current_box[2] - current_box[0],
        'height': new_height, 'method': 'auto_detect',
    }
    output_path.write_text(json.dumps(result, indent=2), encoding='utf-8')

    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)
    draw.rectangle([current_box[0], new_top, current_box[2], final_bottom],
                   outline=(255, 0, 0), width=3)
    label = f"Game View: {current_box[2] - current_box[0]}x{new_height}"
    draw.text((current_box[0] + 5, new_top + 5), label, fill=(255, 0, 0))
    output_png = latest_png.parent / f"game_area_detected_{latest_png.stem.split('_')[1]}.png"
    annotated.save(output_png)
    print(f"输出: {output_png}")
"""

# 2. test_locate.py - 修复被压扁的第一行
fixed_test_locate = """# -*- coding: utf-8 -*-
\"\"\"定位测试\"\"\"
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from 定位.locate_game_area_smart import locate_game_area

if __name__ == '__main__':
    result = locate_game_area()
    print(f"定位结果: {result}")
"""

# 3. _organize_files.py - 修复中文损坏
# (读取原文件并修复中文)

# 4. 旧脚本 7 个文件 - 修复 output_path 被破坏为 'output_path = 文件名"'
# 原始模式应该是 'output_path = str(Path(__file__).parent.parent / ...)'

fixes = {
    '定位/detect_game_bottom.py': fixed_detect,
    '元数据/test_locate.py': fixed_test_locate,
}

for rel_path, content in fixes.items():
    full = ROOT / rel_path
    full.write_text(content, encoding='utf-8')
    try:
        py_compile.compile(str(full), doraise=True)
        print(f'✅ {rel_path}')
    except py_compile.PyCompileError as e:
        print(f'❌ {rel_path}: {str(e)[:100]}')

# 5. 修复旧脚本 7 个文件
import glob as _glob
legacy_dir = ROOT / '旧脚本'
for py_file in sorted(legacy_dir.glob('test_secondary_screen*.py')):
    try:
        text = py_file.read_text(encoding='utf-8')
    except:
        continue
    original = text
    # 修复 output_path = 文件名" 模式（被破坏的替换）
    text = re.sub(r'output_path\s*=\s*test_', 'output_path = str(Path(__file__).parent.parent / "screenshots"/"test_', text)
    if text != original:
        # 还需要修复末尾的引号
        text = text.replace('/"screenshots"/"test_', '/screenshots/test_')
        # 确保字符串闭合
        text = re.sub(r'(test_[a-z_]+\.png)"', r'\1"', text)
        py_file.write_text(text, encoding='utf-8')
        try:
            py_compile.compile(str(py_file), doraise=True)
            print(f'✅ 旧脚本/{py_file.name}')
        except py_compile.PyCompileError as e:
            print(f'❌ 旧脚本/{py_file.name}: {str(e)[:100]}')

# Also fix test_all_screens*.py
for py_file in sorted(legacy_dir.glob('test_all_screens*.py')):
    try:
        text = py_file.read_text(encoding='utf-8')
    except:
        continue
    original = text
    text = re.sub(r'output_path\s*=\s*test_', 'output_path = str(Path(__file__).parent.parent / "screenshots"/"test_', text)
    text = text.replace('/"screenshots"/"test_', '/screenshots/test_')
    text = re.sub(r'(test_[a-z_]+\.png)"', r'\1"', text)
    if text != original:
        py_file.write_text(text, encoding='utf-8')
        try:
            py_compile.compile(str(py_file), doraise=True)
            print(f'✅ 旧脚本/{py_file.name}')
        except py_compile.PyCompileError as e:
            print(f'❌ 旧脚本/{py_file.name}: {str(e)[:100]}')

# 6. 修复 _organize_files.py 中的中文损坏
org_file = ROOT / '部署工具' / '_organize_files.py'
if org_file.exists():
    text = org_file.read_text(encoding='utf-8')
    original = text
    # 中文目录名被损坏
    dir_fixes = {
        '鐢ㄤ緥灞': '用例层',
        '鍏冩暟鎹': '元数据',
        '闃诲澶勭悊': '阻塞处理',
        '閮ㄧ讲宸ュ叿': '部署工具',
        '鐐瑰嚮鎵ц': '点击执行',
        '鍧愭爣鎴浘': '坐标截图',
    }
    for old, new in dir_fixes.items():
        text = text.replace(old, new)
    if text != original:
        org_file.write_text(text, encoding='utf-8')
        try:
            py_compile.compile(str(org_file), doraise=True)
            print(f'✅ 部署工具/_organize_files.py')
        except py_compile.PyCompileError as e:
            print(f'❌ 部署工具/_organize_files.py: {str(e)[:100]}')

print('\n修复完成')
