"""
# -*- coding: utf-8 -*-
可视化验证：在截图上标注可点击元素
让用户直观看到哪些元素被识别了，哪些识别错误，哪些缺失

新增功能：
1. 自动检测游戏区域（方案2 + 方案4 结合）
2. 智能裁剪截图到游戏区域
3. 自动调整坐标到裁剪后的图片
4. 支持从配置文件读取游戏分辨率
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入配置管理器
from config_manager import load_config, get_game_resolution

# Windows API（方案4）
import win32gui
import win32con

from poco.drivers.unity3d import UnityPoco
from airtest.core.api import connect_device, device as current_device
from PIL import Image, ImageDraw, ImageFont


# ==================== Windows API 函数（方案4）====================
def find_unity_window() -> Optional[Tuple[int, int, int, int]]:
    """
    使用 Windows API 查找 Unity 窗口
    :return: (left, top, right, bottom) 或 None
    """
    try:
        # 存储找到的窗口句柄
        found_hwnd = [None]
        
        # 回调函数：枚举所有窗口
        def enum_callback(hwnd, lParam):
            # 获取窗口标题
            title = win32gui.GetWindowText(hwnd)
            
            # 检查是否是 Unity 窗口（标题包含 "Unity"）
            if 'unity' in title.lower():
                # 检查窗口是否可见
                if win32gui.IsWindowVisible(hwnd):
                    found_hwnd[0] = hwnd
                    return False  # 停止枚举
            
            return True  # 继续枚举
        
        # 枚举所有顶层窗口
        win32gui.EnumWindows(enum_callback, 0)
        
        if found_hwnd[0]:
            # 获取窗口矩形（屏幕坐标）
            left, top, right, bottom = win32gui.GetWindowRect(found_hwnd[0])
            
            print(f"✅ 找到 Unity 窗口: ({left}, {top}, {right}, {bottom})")
            return (left, top, right, bottom)
        
        print("⚠️ 未找到 Unity 窗口")
        return None
        
    except Exception as e:
        print(f"⚠️ Windows API 查找失败: {e}")
        return None


# ==================== 游戏区域检测（方案2）====================
def detect_game_region_from_ui_tree(
    ui_tree: Dict,
    screen_width: int,
    screen_height: int
) -> Optional[Tuple[int, int, int, int]]:
    """
    根据 UI 树中的坐标信息，自动检测游戏区域
    :param ui_tree: UI 树
    :param screen_width: 屏幕宽度
    :param screen_height: 屏幕高度
    :return: (left, top, right, bottom) 或 None
    """
    min_x = float('inf')
    min_y = float('inf')
    max_x = 0
    max_y = 0
    valid_count = 0
    
    def traverse(node):
        nonlocal min_x, min_y, max_x, max_y, valid_count
        
        if not node or not isinstance(node, dict):
            return
        
        # 获取 pos 和 size
        pos = None
        size = None
        
        # 先查顶层
        if 'pos' in node:
            pos = node['pos']
        elif 'payload' in node and isinstance(node['payload'], dict) and 'pos' in node['payload']:
            pos = node['payload']['pos']
        
        if 'size' in node:
            size = node['size']
        elif 'payload' in node and isinstance(node['payload'], dict) and 'size' in node['payload']:
            size = node['payload']['size']
        
        # 如果有有效的 pos 和 size，计算边界
        if pos and size and len(pos) >= 2 and len(size) >= 2:
            if not (pos == [0.0, 0.0] and size == [0.0, 0.0]):
                # 计算屏幕坐标
                center_x = pos[0] * screen_width
                center_y = pos[1] * screen_height
                width = size[0] * screen_width
                height = size[1] * screen_height
                
                left = center_x - width / 2
                top = center_y - height / 2
                right = center_x + width / 2
                bottom = center_y + height / 2
                
                min_x = min(min_x, left)
                min_y = min(min_y, top)
                max_x = max(max_x, right)
                max_y = max(max_y, bottom)
                valid_count += 1
        
        # 递归处理子节点
        children = node.get('children', [])
        if not children and 'payload' in node and isinstance(node['payload'], dict):
            children = node['payload'].get('children', [])
        
        for child in children:
            traverse(child)
    
    traverse(ui_tree)
    
    if valid_count == 0:
        print("⚠️ UI 树中没有找到有效的坐标信息")
        return None
    
    # 添加边距（避免裁剪掉边缘的元素）
    padding = 20
    left = max(0, int(min_x) - padding)
    top = max(0, int(min_y) - padding)
    right = min(screen_width, int(max_x) + padding)
    bottom = min(screen_height, int(max_y) + padding)
    
    print(f"✅ 从 UI 树检测到游戏区域: ({left}, {top}, {right}, {bottom})")
    print(f"   共 {valid_count} 个有效 UI 元素")
    
    return (left, top, right, bottom)


def crop_screenshot(
    screenshot_path: str,
    region: Tuple[int, int, int, int]
) -> str:
    """
    裁剪截图到指定区域
    :param screenshot_path: 原始截图路径
    :param region: (left, top, right, bottom)
    :return: 裁剪后的图片路径
    """
    left, top, right, bottom = region
    width = right - left
    height = bottom - top
    
    # 打开原始截图
    img = Image.open(screenshot_path)
    
    # 裁剪到指定区域
    cropped_img = img.crop((left, top, right, bottom))
    
    # 保存裁剪后的图片
    cropped_path = screenshot_path.replace('.png', '_cropped.png')
    cropped_img.save(cropped_path)
    
    print(f"✅ 截图已裁剪到游戏区域: {cropped_path}")
    print(f"   裁剪区域: ({left}, {top}, {right}, {bottom})")
    print(f"   裁剪后尺寸: {width} x {height}")
    
    return cropped_path


def adjust_bounds(
    bounds: Tuple[int, int, int, int],
    crop_region: Tuple[int, int, int, int]
) -> Tuple[int, int, int, int]:
    """
    调整边界框坐标（从原始截图坐标到裁剪后坐标）
    :param bounds: 原始边界框 (left, top, right, bottom)
    :param crop_region: 裁剪区域 (left, top, right, bottom)
    :return: 调整后的边界框
    """
    crop_left, crop_top, _, _ = crop_region
    
    left, top, right, bottom = bounds
    
    # 减去裁剪区域的偏移量
    new_left = max(0, left - crop_left)
    new_top = max(0, top - crop_top)
    new_right = max(0, right - crop_left)
    new_bottom = max(0, bottom - crop_top)
    
    return (new_left, new_top, new_right, new_bottom)


def get_game_region(
    ui_tree: Dict,
    screen_width: int,
    screen_height: int
) -> Optional[Tuple[int, int, int, int]]:
    """
    组合方案：先尝试方案4（Windows API），再尝试方案2（UI 树检测）
    :return: (left, top, right, bottom) 或 None
    """
    print("\n[游戏区域检测] 开始...")
    
    # 方案4：使用 Windows API 查找 Unity 窗口
    print("  [方案4] 尝试使用 Windows API 查找 Unity 窗口...")
    region = find_unity_window()
    
    # 方案2：根据 UI 树检测游戏区域
    if not region:
        print("  [方案2] Windows API 未找到，尝试根据 UI 树检测...")
        region = detect_game_region_from_ui_tree(ui_tree, screen_width, screen_height)
    
    # 如果都失败了，使用全屏
    if not region:
        print("  [Fallback] 所有方案都失败，使用全屏")
        region = (0, 0, screen_width, screen_height)
    
    return region


def get_screen_size() -> Tuple[int, int]:
    """
    获取屏幕分辨率
    优先使用配置文件中的游戏分辨率
    :return: (width, height)
    """
    # 首先尝试从配置文件读取
    config = load_config()
    resolution = config.get("game_resolution", {})
    if resolution.get("width") and resolution.get("height"):
        width = resolution["width"]
        height = resolution["height"]
        print(f"📐 使用配置文件中的游戏分辨率: {width} x {height}")
        return width, height
    
    # 如果配置文件没有，使用 Airtest 获取
    try:
        if current_device():
            w, h = current_device().get_current_resolution()
            return w, h
    except:
        pass
    
    # 默认值（Full HD）
    print("⚠️ 使用默认分辨率: 1920 x 1080")
    return 1920, 1080


def normalized_to_screen(
    pos: List[float], 
    size: List[float], 
    screen_width: int, 
    screen_height: int
) -> Tuple[int, int, int, int]:
    """
    将归一化坐标转换为屏幕坐标
    :param pos: 位置 [x, y] (0-1)
    :param size: 大小 [width, height] (0-1)
    :param screen_width: 屏幕宽度
    :param screen_height: 屏幕高度
    :return: (left, top, right, bottom) 屏幕坐标
    """
    if not pos or not size:
        return 0, 0, 0, 0
    
    # Poco 的 pos 是中心点的坐标
    center_x = pos[0] * screen_width
    center_y = pos[1] * screen_height
    
    # size 是宽高
    width = size[0] * screen_width
    height = size[1] * screen_height
    
    # 计算边界框
    left = int(center_x - width / 2)
    top = int(center_y - height / 2)
    right = int(center_x + width / 2)
    bottom = int(center_y + height / 2)
    
    return left, top, right, bottom


def get_clickable_elements_with_bounds(
    ui_tree: Dict, 
    screen_width: int, 
    screen_height: int
) -> List[Dict]:
    """
    获取所有可点击元素及其屏幕边界
    :param ui_tree: UI 树（可能是原始格式，payload 在里面）
    :param screen_width: 屏幕宽度
    :param screen_height: 屏幕高度
    :return: 可点击元素列表，每个元素包含 name, bounds, text 等
    """
    elements = []
    
    def get_field(node: Dict, field: str):
        """
        从节点中获取字段（先查顶层，再查 payload）
        """
        # 先查顶层
        if field in node:
            return node[field]
        
        # 再查 payload
        payload = node.get('payload', {})
        if isinstance(payload, dict) and field in payload:
            return payload[field]
        
        return None
    
    def traverse(node):
        if not node or not isinstance(node, dict):
            return
        
        name = node.get('name', '')
        node_type = get_field(node, 'type')
        is_clickable = get_field(node, 'clickable')
        pos = get_field(node, 'pos')
        size = get_field(node, 'size')
        visible = get_field(node, 'visible')
        
        # 【过滤条件1】排除不可见的节点
        if visible is not None and not visible:
            # 递归处理子节点（不可见节点的子节点可能可见）
            for child in node.get('children', []):
                traverse(child)
            return
        
        # 【过滤条件2】排除 pos 或 size 为 [0.0, 0.0] 的节点
        # 这些节点在屏幕上没有实际位置，不是真正的 UI 元素
        has_valid_bounds = False
        if pos and size:
            # 检查 pos 和 size 是否都是 [0.0, 0.0]
            if not (pos == [0.0, 0.0] and size == [0.0, 0.0]):
                has_valid_bounds = True
        
        # 如果没有有效的边界框，跳过该节点（但继续处理子节点）
        if not has_valid_bounds:
            # 递归处理子节点（父节点可能是容器，子节点可能有效）
            for child in node.get('children', []):
                traverse(child)
            return
        
        # 判断是否为可点击元素（使用与 find_clickable_elements 相同的逻辑）
        is_clickable_element = False
        
        # 方法1：检查 clickable 属性
        if is_clickable:
            is_clickable_element = True
        
        # 方法2：检查节点类型
        if node_type in ['Button', 'Toggle', 'Slider', 'ScrollBar', 'InputField']:
            is_clickable_element = True
        
        # 方法3：检查 name 是否包含常见可点击组件名
        clickable_names = ['Button', 'Btn', 'ClickContent', 'Item', 'Cell', 'Option', 'Icon', 'Tab']
        if any(cn in name for cn in clickable_names):
            is_clickable_element = True
        
        # 方法4：检查 name 是否以特定后缀结尾
        clickable_suffixes = ['Button', 'Btn', 'Item', 'Cell', 'Icon']
        if any(name.endswith(suffix) for suffix in clickable_suffixes):
            is_clickable_element = True
        
        if is_clickable_element:
            # 获取边界框
            bounds = normalized_to_screen(pos, size, screen_width, screen_height)
            
            elements.append({
                'name': name,
                'type': node_type,
                'clickable': is_clickable,
                'text': get_field(node, 'text'),
                'pos': pos,
                'size': size,
                'bounds': bounds,
                'node': node
            })
        
        # 递归处理子节点
        for child in node.get('children', []):
            traverse(child)
    
    traverse(ui_tree)
    
    # 去重（根据 name）
    seen = set()
    unique_elements = []
    for elem in elements:
        name = elem['name']
        if name not in seen:
            seen.add(name)
            unique_elements.append(elem)
    
    return unique_elements


def draw_elements_on_screenshot(
    screenshot_path: str,
    elements: List[Dict],
    output_path: str,
    max_elements: int = 50
):
    """
    在截图上绘制可点击元素的边界框和编号
    :param screenshot_path: 截图文件路径
    :param elements: 可点击元素列表
    :param output_path: 输出文件路径
    :param max_elements: 最多标注的元素数量（避免太多太乱）
    """
    # 打开截图
    img = Image.open(screenshot_path)
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体（用于绘制编号）
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # 颜色列表（用于区分不同元素）
    colors = [
        'red', 'blue', 'green', 'yellow', 'orange', 
        'purple', 'cyan', 'magenta', 'pink', 'brown'
    ]
    
    # 限制标注数量
    elements_to_draw = elements[:max_elements]
    
    print(f"\n📍 开始标注 {len(elements_to_draw)} 个可点击元素...")
    
    for idx, elem in enumerate(elements_to_draw):
        bounds = elem.get('bounds')
        if not bounds:
            continue
        
        left, top, right, bottom = bounds
        
        # 选择颜色
        color = colors[idx % len(colors)]
        
        # 绘制边界框
        draw.rectangle(
            [left, top, right, bottom],
            outline=color,
            width=3
        )
        
        # 绘制编号（在边界框左上角）
        label = f"{idx + 1}"
        draw.text(
            (left + 5, top + 5),
            label,
            fill=color,
            font=font
        )
        
        # 打印元素信息
        name = elem['name']
        text = elem.get('text', '')
        elem_type = elem.get('type', '')
        print(f"  {idx + 1}. {name} ({elem_type}) text='{text}' bounds={bounds}")
    
    # 保存标注后的图片
    img.save(output_path)
    print(f"\n✅ 标注完成！图片已保存至: {output_path}")
    print(f"   共标注 {len(elements_to_draw)} 个元素")
    if len(elements) > max_elements:
        print(f"   （共识别 {len(elements)} 个元素，仅标注前 {max_elements} 个）")
    
    return output_path


def generate_element_list(elements: List[Dict], output_path: str):
    """
    生成元素列表文件（文本格式）
    让用户可以快速查看所有识别的元素
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("可点击元素列表\n")
        f.write("=" * 80 + "\n\n")
        
        for idx, elem in enumerate(elements):
            name = elem['name']
            text = elem.get('text', '')
            elem_type = elem.get('type', '')
            clickable = elem.get('clickable', False)
            bounds = elem.get('bounds')
            
            f.write(f"{idx + 1}. {name}\n")
            f.write(f"   类型: {elem_type}\n")
            f.write(f"   可点击: {clickable}\n")
            f.write(f"   文本: {text}\n")
            f.write(f"   边界: {bounds}\n")
            f.write("\n")
    
    print(f"✅ 元素列表已保存至: {output_path}")


def main():
    """主函数（使用方案2 + 方案4 组合）"""
    print("=" * 80)
    print("可视化验证：在截图上标注可点击元素")
    print("（使用方案2 + 方案4 组合：自动检测游戏区域）")
    print("=" * 80)
    
    # 1. 连接 Unity
    print("\n[1/6] 连接 Unity...")
    try:
        connect_device('Windows:///')
        poco = UnityPoco()
        print("✅ Unity 连接成功")
    except Exception as e:
        print(f"✗ Unity 连接失败: {e}")
        print("请确保 Unity 编辑器已打开，且游戏已运行")
        return
    
    # 2. 获取屏幕分辨率
    print("\n[2/6] 获取屏幕分辨率...")
    screen_width, screen_height = get_screen_size()
    print(f"✅ 屏幕分辨率: {screen_width} x {screen_height}")
    
    # 3. 获取 UI 树
    print("\n[3/6] 获取 UI 树...")
    try:
        ui_tree = poco.dump()
        print(f"✅ UI 树获取成功")
    except Exception as e:
        print(f"✗ UI 树获取失败: {e}")
        return
    
    # 4. 检测游戏区域（方案2 + 方案4 组合）
    print("\n[4/6] 检测游戏区域...")
    game_region = get_game_region(ui_tree, screen_width, screen_height)
    
    if game_region:
        left, top, right, bottom = game_region
        print(f"✅ 游戏区域: ({left}, {top}, {right}, {bottom})")
        print(f"   尺寸: {right - left} x {bottom - top}")
    else:
        print("⚠️ 未检测到游戏区域，使用全屏")
        game_region = (0, 0, screen_width, screen_height)
    
    # 5. 找到所有可点击元素
    print("\n[5/6] 识别可点击元素...")
    elements = get_clickable_elements_with_bounds(ui_tree, screen_width, screen_height)
    print(f"✅ 识别到 {len(elements)} 个可点击元素")
    
    if len(elements) == 0:
        print("⚠️ 未识别到任何可点击元素，请检查 UI 树数据")
        return
    
    # 5.5 调整元素坐标到裁剪后的图片
    if game_region:
        print("   调整元素坐标到裁剪后的图片...")
        for elem in elements:
            if 'bounds' in elem and elem['bounds']:
                elem['bounds'] = adjust_bounds(elem['bounds'], game_region)
    
    # 6. 截图
    print("\n[6/6] 截图...")
    screenshot_dir = project_root / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = str(screenshot_dir / f"screen_{timestamp}.png")
    
    try:
        current_device().snapshot(filename=screenshot_path)
        print(f"✅ 截图已保存: {screenshot_path}")
    except Exception as e:
        print(f"✗ 截图失败: {e}")
        return
    
    # 7. 裁剪截图到游戏区域
    print("\n[额外] 裁剪截图到游戏区域...")
    cropped_path = crop_screenshot(screenshot_path, game_region)
    
    # 8. 在裁剪后的截图上标注元素
    print("\n[额外] 在裁剪后的截图上标注元素...")
    annotated_path = str(screenshot_dir / f"annotated_{timestamp}.png")
    draw_elements_on_screenshot(cropped_path, elements, annotated_path)
    
    # 9. 生成元素列表文件
    print("\n[额外] 生成元素列表文件...")
    list_path = str(screenshot_dir / f"elements_{timestamp}.txt")
    generate_element_list(elements, list_path)
    
    print("\n" + "=" * 80)
    print("完成！请查看以下文件：")
    print("=" * 80)
    print(f"1. 原始截图: {screenshot_path}")
    print(f"2. 裁剪后截图: {cropped_path}")
    print(f"3. 标注后截图: {annotated_path}")
    print(f"4. 元素列表: {list_path}")
    print("\n请在标注后的截图上确认：")
    print("  - ✅ 彩色框：识别出的可点击元素")
    print("  - ❌ 如果没有框，或者框的位置不对：识别失败")
    print("  - ❓ 如果您知道某个元素应该被识别但未出现在列表中：缺失")
    print("=" * 80)


if __name__ == "__main__":
    main()
