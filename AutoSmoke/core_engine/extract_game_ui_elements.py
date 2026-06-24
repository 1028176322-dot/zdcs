"""
# -*- coding: utf-8 -*-
Game窗口UI元素完整提取脚本
结合Poco dump + Game窗口坐标，输出所有UI元素的屏幕像素坐标

功能：
1. 自动获取Game窗口坐标（config.json 或自动定位）
2. 连接Unity并dump完整UI树
3. 将Poco归一化坐标(0-1)转换为Game窗口内像素坐标
4. 输出所有元素信息（文本、坐标、尺寸、可见性、可点击性）
5. 保存为JSON（供后续自动化点击使用）
"""

import sys
import os
import time
import json
from typing import Optional, Dict, List, Any, Tuple

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poco_connector.poco_connector import PocoConnector
from ui_processor.ui_tree_processor import UITreeProcessor


# ============================================================
# Game窗口坐标获取
# ============================================================

def get_game_window_coords() -> Optional[Dict]:
    """
    获取Game窗口坐标，优先从config.json读取，失败则自动定位
    返回: {"left", "top", "right", "bottom", "width", "height"} 屏幕像素坐标
    """
    # 方法1：从config.json读取
    config_file = os.path.join(os.path.dirname(__file__), '../config.json')
    config_file = os.path.abspath(config_file)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            coords = config.get('game_view_coords')
            if coords and coords.get('width', 0) > 0:
                print(f"✓ 从config.json读取Game窗口坐标: "
                      f"({coords['left']}, {coords['top']}, {coords['right']}, {coords['bottom']}) "
                      f"尺寸: {coords['width']}x{coords['height']}")
                return coords
        except Exception as e:
            print(f"⚠ 读取config.json失败: {e}")

    # 方法2：调用locate_game_area_smart自动定位
    print("⚠ config.json中无有效Game窗口坐标，尝试自动定位...")
    try:
        from locate_game_area_smart import get_game_view_coords as locate_func
        result = locate_func()
        if result:
            left, top, right, bottom = result
            coords = {
                'left': left, 'top': top,
                'right': right, 'bottom': bottom,
                'width': right - left, 'height': bottom - top
            }
            print(f"✓ 自动定位Game窗口: ({left}, {top}, {right}, {bottom}) "
                  f"尺寸: {coords['width']}x{coords['height']}")
            return coords
    except Exception as e:
        print(f"✗ 自动定位失败: {e}")

    print("✗ 无法获取Game窗口坐标，请确保Unity Editor已打开并运行Game视图定位脚本")
    return None


# ============================================================
# 坐标转换
# ============================================================

def normalized_to_game_pixel(
    normalized_pos: List[float],
    normalized_size: List[float],
    game_coords: Dict
) -> Tuple[Dict, Dict]:
    """
    将Poco归一化坐标转换为Game窗口内的像素坐标
    
    Poco的pos是归一化中心坐标(0-1)，size是归一化尺寸(0-1)
    Unity的poco SDK中，pos和size是基于游戏分辨率的归一化值
    
    :param normalized_pos: [x, y] 归一化中心坐标，范围[0, 1]
    :param normalized_size: [w, h] 归一化尺寸，范围[0, 1]
    :param game_coords: Game窗口屏幕坐标字典
    :return: (center_pixel, bbox_pixel) 中心像素坐标和边界框像素坐标
    """
    gw = game_coords['width']
    gh = game_coords['height']
    gl = game_coords['left']
    gt = game_coords['top']

    # 归一化中心坐标 → Game窗口内像素坐标
    cx = normalized_pos[0] * gw
    cy = normalized_pos[1] * gh

    # 归一化尺寸 → 像素尺寸
    w = normalized_size[0] * gw
    h = normalized_size[1] * gh

    # 边界框（左上角 + 右下角）在Game窗口内的像素坐标
    x1 = cx - w / 2
    y1 = cy - h / 2
    x2 = cx + w / 2
    y2 = cy + h / 2

    # 屏幕绝对坐标
    center_pixel = {
        'x': round(gl + cx, 1),
        'y': round(gt + cy, 1),
        'game_x': round(cx, 1),
        'game_y': round(cy, 1)
    }
    bbox_pixel = {
        'left': round(gl + x1, 1),
        'top': round(gt + y1, 1),
        'right': round(gl + x2, 1),
        'bottom': round(gt + y2, 1),
        'width': round(w, 1),
        'height': round(h, 1),
        'game_left': round(x1, 1),
        'game_top': round(y1, 1),
        'game_right': round(x2, 1),
        'game_bottom': round(y2, 1)
    }

    return center_pixel, bbox_pixel


def extract_element_info(
    node: Dict,
    game_coords: Dict,
    processor: UITreeProcessor,
    depth: int = 0
) -> Optional[Dict]:
    """
    从单个UI树节点提取完整信息（含屏幕坐标）
    
    :param node: UI树节点（已normalize）
    :param game_coords: Game窗口坐标
    :param processor: UITreeProcessor实例（用于修复ClickContent文本）
    :param depth: 当前递归深度
    :return: 元素信息字典，或None（节点无效时）
    """
    if not node or not isinstance(node, dict):
        return None

    name = node.get('name', '')
    pos = node.get('pos', [0, 0])
    size = node.get('size', [0, 0])
    visible = node.get('visible', True)
    clickable = node.get('clickable', False)
    node_type = node.get('type', '')

    # 跳过无效节点（无名称 或 无有效坐标）
    if not name:
        return None
    if not pos or not size or len(pos) < 2 or len(size) < 2:
        return None
    if pos[0] == 0 and pos[1] == 0 and size[0] == 0 and size[1] == 0:
        return None

    # 文本提取（含ClickContent修复）
    raw_text = node.get('text', '')
    if 'ClickContent' in name and (not raw_text or not str(raw_text).strip()):
        fixed_text = processor.fix_clickcontent_text(node)
    else:
        fixed_text = str(raw_text).strip() if raw_text else ''

    # 启发式可点击判断（不依赖Poco的clickable字段）
    likely_clickable = _is_likely_clickable(name, node_type, fixed_text, depth)

    # 坐标转换
    center_pixel = None
    bbox_pixel = None
    try:
        center_pixel, bbox_pixel = normalized_to_game_pixel(pos, size, game_coords)
    except Exception as e:
        pass

    info = {
        'name': name,
        'type': node_type,
        'text': fixed_text,
        'raw_text': str(raw_text).strip() if raw_text else '',
        'visible': visible,
        'clickable': clickable,                      # Poco原始字段
        'likely_clickable': likely_clickable,           # 启发式判断
        'pos_normalized': {'x': round(pos[0], 4), 'y': round(pos[1], 4)},
        'size_normalized': {'w': round(size[0], 4), 'h': round(size[1], 4)},
        'center_pixel': center_pixel,
        'bbox_pixel': bbox_pixel,
        'depth': depth,
        'children_count': len(node.get('children', []))
    }

    return info


def _is_likely_clickable(name: str, node_type: str, text: str, depth: int) -> bool:
    """
    启发式判断节点是否可点击（用于Poco未正确设置clickable字段的情况）
    判断依据：
      1. Poco原始clickable字段为True
      2. type为已知可点击类型（Button/InputField/Toggle等）
      3. 名称包含已知可点击后缀（Button/Btn/ClickContent/Item/Cell/Tab/Icon）
      4. 名称包含Click/click关键词
    """
    # 依据1：Poco已标记
    # （由调用方传入，此处不直接访问，但likely_clickable已单独传入）

    # 依据2：已知可点击类型
    clickable_types = {'Button', 'Toggle', 'Slider', 'ScrollBar', 'InputField',
                       'ScrollRect', 'Dropdown'}
    if node_type in clickable_types:
        return True

    # 依据3：名称后缀匹配
    clickable_suffixes = {'Button', 'Btn', 'ClickContent', 'Item', 'Cell',
                           'Tab', 'Icon', 'Entry', 'Option'}
    if any(name.endswith(sfx) for sfx in clickable_suffixes):
        return True

    # 依据4：名称包含点击关键词
    click_keywords = {'Click', 'click', 'Btn_', '_Btn', 'Button_', '_Button'}
    if any(kw in name for kw in click_keywords):
        return True

    return False


def traverse_all_elements(
    node: Dict,
    game_coords: Dict,
    processor: UITreeProcessor,
    depth: int = 0,
    max_depth: int = 50
) -> List[Dict]:
    """
    递归遍历UI树，提取所有节点的完整信息
    
    :return: 元素信息列表
    """
    if not node or not isinstance(node, dict) or depth > max_depth:
        return []

    results = []
    info = extract_element_info(node, game_coords, processor, depth)
    if info:
        results.append(info)

    for child in node.get('children', []):
        results.extend(traverse_all_elements(child, game_coords, processor, depth + 1, max_depth))

    return results


# ============================================================
# 主流程
# ============================================================

def extract_all_game_ui_elements(
    output_json: bool = True,
    output_console: bool = True,
    max_print: int = 100
):
    """
    主函数：提取Game窗口内所有UI元素
    
    :param output_json: 是否保存JSON文件
    :param output_console: 是否在控制台打印
    :param max_print: 控制台最多打印元素数
    :return: 元素列表
    """
    print("=" * 80)
    print("Game窗口UI元素完整提取")
    print("=" * 80)

    # 步骤1：获取Game窗口坐标
    print("\n[步骤1] 获取Game窗口坐标...")
    game_coords = get_game_window_coords()
    if not game_coords:
        return None
    print(f"  Game窗口: 左={game_coords['left']}, 上={game_coords['top']}, "
          f"右={game_coords['right']}, 下={game_coords['bottom']}")
    print(f"  尺寸: {game_coords['width']} x {game_coords['height']} 像素")

    # 步骤2：连接Unity
    print("\n[步骤2] 连接Unity游戏...")
    connector = PocoConnector(device_type='Windows')
    if not connector.connect():
        print("✗ 连接失败，请确保：")
        print("  1. Unity Editor已打开")
        print("  2. 已点击Play按钮（▶）")
        print("  3. Poco SDK已正确集成")
        return None

    # 步骤3：Dump UI树
    print("\n[步骤3] Dump UI树...")
    ui_tree = connector.dump_ui_tree()
    if not ui_tree:
        print("✗ dump失败")
        connector.close()
        return None

    # 步骤4：处理UI树
    print("\n[步骤4] 处理UI树...")
    processor = UITreeProcessor(ui_tree)

    # 步骤5：遍历所有元素，提取信息（使用归一化后的树）
    print("\n[步骤5] 提取所有元素信息（含屏幕坐标）...")
    all_elements = traverse_all_elements(processor.ui_tree, game_coords, processor)
    print(f"✓ 共提取 {len(all_elements)} 个元素")

    # 统计
    visible_count = sum(1 for e in all_elements if e['visible'])
    clickable_count = sum(1 for e in all_elements if e['clickable'])
    likely_clickable_count = sum(1 for e in all_elements if e.get('likely_clickable', False))
    has_text_count = sum(1 for e in all_elements if e['text'])
    coord_valid_count = sum(1 for e in all_elements if e['center_pixel'] is not None)
    print(f"  - 可见元素: {visible_count}")
    print(f"  - Poco标记可点击: {clickable_count}")
    print(f"  - 启发式可点击: {likely_clickable_count}")
    print(f"  - 有文本元素: {has_text_count}")
    print(f"  - 坐标有效元素: {coord_valid_count}")

    # 步骤6：控制台输出
    if output_console:
        print(f"\n{'=' * 80}")
        print(f"元素列表（前{min(max_print, len(all_elements))}个 / 共{len(all_elements)}个）")
        print(f"{'=' * 80}")
        _print_elements_table(all_elements, max_print)

    # 步骤7：保存JSON
    json_path = None
    if output_json:
        print("\n[步骤6] 保存JSON文件...")
        json_path = _save_elements_json(all_elements, game_coords)
        print(f"✓ 已保存至: {json_path}")

        # 同时保存按类型分类的文件
        saved_files = _save_categorized_json(all_elements, game_coords)
        if saved_files:
            for sf in saved_files:
                print(f"✓ 已保存: {sf}")

    # 步骤8：截图
    print("\n[步骤7] 截图...")
    try:
        screenshot_path = connector.snapshot()
        if screenshot_path:
            print(f"✓ 截图保存至: {screenshot_path}")
    except Exception as e:
        print(f"⚠ 截图失败: {e}")

    # 关闭连接
    connector.close()

    print("\n" + "=" * 80)
    print("提取完成")
    print("=" * 80)

    return all_elements


def _print_elements_table(elements: List[Dict], max_count: int):
    """在控制台以表格形式打印元素信息"""
    header = f"{'序号':<5} {'名称':<35} {'文本':<20} {'可见':<4} {'可点':<4} {'中心坐标(x,y)':<25} {'尺寸(w,h)'}"
    print(header)
    print("-" * 120)

    for i, elem in enumerate(elements[:max_count], 1):
        name = elem['name'][:33] + '..' if len(elem['name']) > 35 else elem['name']
        text = (elem['text'][:18] + '..') if elem['text'] and len(elem['text']) > 20 else (elem['text'] or '')
        visible = '✓' if elem['visible'] else '✗'
        clickable = '✓' if elem['clickable'] else '✗'

        cx = elem['center_pixel']
        coord_str = f"({cx['game_x']:.0f}, {cx['game_y']:.0f})" if cx else '(N/A)'

        bs = elem['bbox_pixel']
        size_str = f"{bs['width']:.0f}x{bs['height']:.0f}" if bs else 'N/A'

        print(f"{i:<5} {name:<35} {text:<20} {visible:<4} {clickable:<4} {coord_str:<25} {size_str}")

    if len(elements) > max_count:
        print(f"... 还有 {len(elements) - max_count} 个元素未显示")


def _save_elements_json(elements: List[Dict], game_coords: Dict) -> str:
    """保存完整元素列表为JSON"""
    output_dir = os.path.join(os.path.dirname(__file__), '../data_access/reports')
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    timestamp = int(time.time())
    json_file = os.path.join(output_dir, f'game_ui_elements_{timestamp}.json')

    output = {
        'extract_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'game_coords': game_coords,
        'total_elements': len(elements),
        'statistics': {
            'visible': sum(1 for e in elements if e['visible']),
            'clickable': sum(1 for e in elements if e['clickable']),
            'has_text': sum(1 for e in elements if e['text']),
            'has_valid_coords': sum(1 for e in elements if e['center_pixel'] is not None)
        },
        'elements': elements
    }

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return json_file


def _save_categorized_json(elements: List[Dict], game_coords: Dict) -> Optional[str]:
    """按类型分类保存（可点击元素、有文本元素等）"""
    output_dir = os.path.join(os.path.dirname(__file__), '../data_access/reports')
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    timestamp = int(time.time())

    categories = {
        'clickable': ([e for e in elements if e['clickable']], 'Poco标记可点击'),
        'likely_clickable': ([e for e in elements if e.get('likely_clickable', False)], '启发式可点击'),
        'has_text': ([e for e in elements if e['text']], '有文本元素'),
        'clickcontent': ([e for e in elements if 'ClickContent' in e['name']], 'ClickContent节点'),
    }

    saved_files = []
    for key, (elems, desc) in categories.items():
        if not elems:
            continue
        json_file = os.path.join(output_dir, f'game_ui_{key}_{timestamp}.json')
        output = {
            'category': key,
            'description': desc,
            'extract_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'game_coords': game_coords,
            'count': len(elems),
            'elements': elems
        }
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        saved_files.append(json_file)

    return saved_files


# ============================================================
# 独立运行入口
# ============================================================

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("Unity游戏自动化测试系统 - Game窗口UI元素提取工具")
    print("=" * 80 + "\n")

    import argparse
    parser = argparse.ArgumentParser(description='提取Game窗口内所有UI元素（含屏幕像素坐标）')
    parser.add_argument('--no-console', action='store_true', help='不在控制台打印元素列表')
    parser.add_argument('--max-print', type=int, default=100, help='控制台最多打印元素数（默认100）')
    parser.add_argument('--no-json', action='store_true', help='不保存JSON文件')
    args = parser.parse_args()

    results = extract_all_game_ui_elements(
        output_json=not args.no_json,
        output_console=not args.no_console,
        max_print=args.max_print
    )

    if results:
        print(f"\n✓ 共提取 {len(results)} 个UI元素")
        print(f"  查看 data_access/reports/ 目录获取完整JSON数据")
    else:
        print("\n✗ 提取失败")
        sys.exit(1)
