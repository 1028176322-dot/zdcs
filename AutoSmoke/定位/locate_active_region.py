"""
# -*- coding: utf-8 -*-
Unity 界面有效区域自动定位 - 方案二：自动推断最大可见业务面板

实施策略：
1. 扫描 UI 树，找出所有候选面板
2. 根据评分规则计算每个面板的得分
3. 选择得分最高的面板作为当前有效区域
4. 在截图上标注出有效区域

评分规则（来自 Unity_界面有效区域自动定位方案.md）：
 加分项：
 - 面积较大：+20
 - 包含 Button：+20
 - 包含 Text/TMP_Text：+10
 - 包含 ScrollRect：+10
 - siblingIndex 更靠后：+10
 - Canvas sortingOrder 更高：+20
 - 名称包含 Panel/Dialog/Popup/View/Page：+10
 - 包含 Mask/Blur：+10

 扣分项：
 - 名称包含 Debug：-50
 - 名称包含 Logo：-30
 - 名称包含 EventSystem：-50
 - 面积过小：-30
 - 无任何可见子元素：-50

新增功能：
- 支持从配置文件读取游戏分辨率
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入配置管理器
from config_manager import load_config, get_game_resolution

import win32gui

from poco.drivers.unity3d import UnityPoco
from airtest.core.api import connect_device, device as current_device
from PIL import Image, ImageDraw, ImageFont
import numpy as np


# ==================== 配置参数 ====================
MIN_AREA = 10000  # 最小面积阈值（像素）


# ==================== 工具函数 ====================
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
    from airtest.core.api import device as dev
    try:
        w, h = dev().get_current_resolution()
        return w, h
    except:
        # fallback
        from PIL import ImageGrab
        img = ImageGrab.grab()
        return img.width, img.height


def normalized_to_screen(
    pos: List[float],
    size: List[float],
    screen_width: int,
    screen_height: int
) -> Tuple[int, int, int, int]:
    """
    将归一化坐标转换为屏幕像素坐标
    :param pos: [x, y] 中心点归一化坐标 (0-1)
    :param size: [w, h] 尺寸归一化坐标 (0-1)
    :param screen_width: 屏幕宽度
    :param screen_height: 屏幕高度
    :return: (left, top, right, bottom) 屏幕像素坐标
    """
    center_x = pos[0] * screen_width
    center_y = pos[1] * screen_height
    width = size[0] * screen_width
    height = size[1] * screen_height

    left = int(center_x - width / 2)
    top = int(center_y - height / 2)
    right = int(center_x + width / 2)
    bottom = int(center_y + height / 2)

    return (left, top, right, bottom)


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


# ==================== 黑色边框检测 ====================
def detect_game_area(
    image_path: str,
    black_threshold: int = 30
) -> Optional[Tuple[int, int, int, int]]:
    """
    检测截图中的游戏有效区域（去除黑色边框）
    使用更智能的方法：分析每行的平均亮度，找到游戏内容区域
    :param image_path: 截图路径
    :param black_threshold: 黑色阈值（RGB 值低于此值视为黑色）
    :return: (left, top, right, bottom) 或 None（未检测到黑色边框）
    """
    print(f"\n[游戏区域检测] 开始分析截图: {image_path}")

    # 打开图片并转换为 numpy 数组
    img = Image.open(image_path)
    img_rgb = img.convert('RGB')
    arr = np.array(img_rgb)
    
    # 转换为灰度图，便于分析亮度
    img_gray = img.convert('L')
    arr_gray = np.array(img_gray)
    
    height, width = arr_gray.shape
    print(f"  图片尺寸: {width} x {height}")

    # 计算每列的平局亮度
    col_means = np.mean(arr_gray, axis=0)  # 形状: (width,)
    
    # 计算每行的平均亮度
    row_means = np.mean(arr_gray, axis=1)  # 形状: (height,)

    # 1. 从左到右扫描，找到第一个亮度 > 阈值的列
    left = 0
    for x in range(width):
        if col_means[x] > black_threshold:
            left = x
            break

    # 2. 从右到左扫描，找到最后一个亮度 > 阈值的列
    right = width - 1
    for x in range(width - 1, -1, -1):
        if col_means[x] > black_threshold:
            right = x
            break

    # 3. 从上到下扫描，找到第一个亮度 > 阈值的行
    top = 0
    for y in range(height):
        if row_means[y] > black_threshold:
            top = y
            break

    # 4. 从下到上扫描，找到最后一个亮度 > 阈值的行
    bottom = height - 1
    for y in range(height - 1, -1, -1):
        if row_means[y] > black_threshold:
            bottom = y
            break

    # 检查是否检测到有效区域
    if left >= right or top >= bottom:
        print(f"  ⚠️ 未检测到黑色边框")
        return None

    # 检查是否有黑色边框
    has_left_border = left > 0
    has_right_border = right < width - 1
    has_top_border = top > 0
    has_bottom_border = bottom < height - 1

    # 如果没有任何黑色边框，返回 None
    if not any([has_left_border, has_right_border, has_top_border, has_bottom_border]):
        print(f"  ⚠️ 截图没有黑色边框")
        return None

    # 输出检测结果
    print(f"  ✅ 检测到游戏有效区域:")
    print(f"    左边界: {left}")
    print(f"    上边界: {top}")
    print(f"    右边界: {right}")
    print(f"    下边界: {bottom}")
    print(f"    有效区域尺寸: {right - left + 1} x {bottom - top + 1}")
    
    # 计算裁剪比例
    crop_width = right - left + 1
    crop_height = bottom - top + 1
    crop_ratio = (crop_width * crop_height) / (width * height)
    print(f"    裁剪比例: {crop_ratio:.2%}")

    return (left, top, right, bottom)


def crop_to_game_area(
    screenshot_path: str,
    black_threshold: int = 30
) -> Tuple[str, Optional[Tuple[int, int, int, int]]]:
    """
    裁剪截图到游戏有效区域（去除黑色边框）
    :param screenshot_path: 原始截图路径
    :param black_threshold: 黑色阈值
    :return: (裁剪后的图片路径, 裁剪区域坐标)
    """
    # 检测黑色边框
    borders = detect_game_area(screenshot_path, black_threshold)

    if not borders:
        print(f"  ⚠️ 未检测到黑色边框，使用原始截图")
        return screenshot_path, None

    left, top, right, bottom = borders

    # 裁剪图片
    img = Image.open(screenshot_path)
    cropped_img = img.crop((left, top, right + 1, bottom + 1))

    # 保存裁剪后的图片
    cropped_path = screenshot_path.replace('.png', '_cropped.png')
    cropped_img.save(cropped_path)

    print(f"  ✅ 截图已裁剪到游戏区域: {cropped_path}")
    print(f"    裁剪区域: ({left}, {top}, {right + 1}, {bottom + 1})")
    print(f"    裁剪后尺寸: {cropped_img.width} x {cropped_img.height}")

    return cropped_path, (left, top, right, bottom)


def adjust_elements_to_cropped(
    elements: List[Dict],
    crop_offset: Tuple[int, int]
) -> List[Dict]:
    """
    调整元素坐标到裁剪后的图片坐标系
    :param elements: 元素列表
    :param crop_offset: (left, top) 裁剪偏移量
    :return: 调整后的元素列表
    """
    if not crop_offset:
        return elements

    left, top = crop_offset
    adjusted = []

    for elem in elements:
        new_elem = elem.copy()
        bounds = elem.get('bounds')
        if bounds:
            new_bounds = (
                bounds[0] - left,
                bounds[1] - top,
                bounds[2] - left,
                bounds[3] - top
            )
            new_elem['bounds'] = new_bounds
            adjusted.append(new_elem)
        else:
            adjusted.append(new_elem)

    return adjusted


# ==================== 面板评分逻辑 ====================
def calculate_panel_score(node: Dict, screen_width: int, screen_height: int) -> Tuple[int, Dict]:
    """
    根据方案二的评分规则，计算面板得分
    :param node: UI 树节点
    :param screen_width: 屏幕宽度
    :param screen_height: 屏幕高度
    :return: (得分, 评分详情)
    """
    score = 0
    details = {
        'name': node.get('name', ''),
        'bonus': {},
        'penalty': {}
    }

    name = node.get('name', '').lower()

    # ========== 加分项 ==========

    # 1. 面积较大：+20
    pos = get_field(node, 'pos')
    size = get_field(node, 'size')
    if pos and size:
        bounds = normalized_to_screen(pos, size, screen_width, screen_height)
        area = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])
        details['area'] = area
        details['bounds'] = bounds

        # 面积占屏幕百分比
        screen_area = screen_width * screen_height
        area_ratio = area / screen_area
        details['area_ratio'] = area_ratio

        # 面积较大：+20
        if area > MIN_AREA:
            score += 20
            details['bonus']['面积较大'] = 20

        # 新增：面积占屏幕 20%-80%：+10（可能是有效区域）
        if 0.2 <= area_ratio <= 0.8:
            score += 10
            details['bonus']['面积占屏幕 20%-80%'] = 10

        # 新增：面积超过屏幕 90%：-30（可能是全屏窗口）
        if area_ratio > 0.9:
            score -= 30
            details['penalty']['面积超过屏幕 90%（可能是全屏窗口）'] = -30

    # 2. 包含 Button：+20
    has_button = check_component_in_subtree(node, 'Button')
    if has_button:
        score += 20
        details['bonus']['包含 Button'] = 20

    # 3. 包含 Text/TMP_Text：+10
    has_text = check_component_in_subtree(node, 'Text') or check_component_in_subtree(node, 'TMP_Text')
    if has_text:
        score += 10
        details['bonus']['包含 Text/TMP_Text'] = 10

    # 4. 包含 ScrollRect：+10
    has_scroll = check_component_in_subtree(node, 'ScrollRect')
    if has_scroll:
        score += 10
        details['bonus']['包含 ScrollRect'] = 10

    # 5. siblingIndex 更靠后：+10
    # （需要在遍历时动态计算）

    # 6. Canvas sortingOrder 更高：+20
    # （需要获取父 Canvas 的 sortingOrder）

    # 7. 名称包含 Panel/Dialog/Popup/View/Page：+10
    name_original = node.get('name', '')
    if any(kw in name_original for kw in ['Panel', 'Dialog', 'Popup', 'View', 'Page']):
        score += 10
        details['bonus']['名称包含 Panel/Dialog/Popup/View/Page'] = 10

    # 新增：8. 名称包含业务关键词：+5（降低加分，避免选择整个界面）
    business_keywords = ['Bag', 'Shop', 'Mail', 'Task', 'Quest', 'Building', 'Upgrade', 'Alliance', 'Rank', 'Hero', 'Skill', 'Inventory', 'Equipment', 'Backpack']
    if any(kw in name_original for kw in business_keywords):
        score += 5
        details['bonus']['名称包含业务关键词（Bag/Shop/Mail等）'] = 5

    # 9. 包含 Mask/Blur：+10
    has_mask = check_component_in_subtree(node, 'Mask')
    if has_mask:
        score += 10
        details['bonus']['包含 Mask'] = 10

    # ========== 扣分项 ==========

    # 1. 名称包含 Debug：-50
    if 'debug' in name:
        score -= 50
        details['penalty']['名称包含 Debug'] = -50

    # 2. 名称包含 Logo：-30
    if 'logo' in name:
        score -= 30
        details['penalty']['名称包含 Logo'] = -30

    # 3. 名称包含 EventSystem：-50
    if 'eventsystem' in name:
        score -= 50
        details['penalty']['名称包含 EventSystem'] = -50

    # 4. 面积过小：-30
    if 'area' in details and details['area'] < MIN_AREA:
        score -= 30
        details['penalty']['面积过小'] = -30

    # 5. 无任何可见子元素：-50
    children = node.get('children', [])
    if not children:
        # 检查 payload 中的 children
        payload = node.get('payload', {})
        if isinstance(payload, dict):
            children = payload.get('children', [])

    if not children:
        score -= 50
        details['penalty']['无任何可见子元素'] = -50

    details['total_score'] = score
    return score, details


def check_component_in_subtree(node: Dict, component_name: str) -> bool:
    """
    检查节点或其子节点是否包含指定组件
    :param node: UI 树节点
    :param component_name: 组件名称
    :return: 是否包含
    """
    if not node or not isinstance(node, dict):
        return False

    # 检查当前节点
    components = get_field(node, 'components')
    if components and isinstance(components, list):
        if component_name in components:
            return True

    # 递归检查子节点
    children = node.get('children', [])
    if not children:
        payload = node.get('payload', {})
        if isinstance(payload, dict):
            children = payload.get('children', [])

    for child in children:
        if check_component_in_subtree(child, component_name):
            return True

    return False


# ==================== 查找候选面板 ====================
def find_candidate_panels(
    ui_tree: Dict,
    screen_width: int,
    screen_height: int
) -> List[Dict]:
    """
    查找所有候选面板（满足基本条件的节点）
    :param ui_tree: UI 树
    :param screen_width: 屏幕宽度
    :param screen_height: 屏幕高度
    :return: 候选面板列表（每个元素包含节点、得分、评分详情）
    """
    candidates = []

    def traverse(node, depth=0):
        if not node or not isinstance(node, dict):
            return

        name = node.get('name', '')

        # 基本条件检查
        # 1. 排除系统节点
        if any(kw in name.lower() for kw in ['pocomanager', 'eventsystem', 'debug']):
            # 仍然递归处理子节点
            for child in get_children(node):
                traverse(child, depth + 1)
            return

        # 2. 检查是否有有效的 pos 和 size
        pos = get_field(node, 'pos')
        size = get_field(node, 'size')
        if not pos or not size:
            # 递归处理子节点
            for child in get_children(node):
                traverse(child, depth + 1)
            return

        # 3. 检查是否可见
        visible = get_field(node, 'visible')
        if visible is not None and not visible:
            # 递归处理子节点
            for child in get_children(node):
                traverse(child, depth + 1)
            return

        # 计算得分
        score, details = calculate_panel_score(node, screen_width, screen_height)

        # 只保留得分 > 0 的节点
        if score > 0:
            candidates.append({
                'node': node,
                'score': score,
                'details': details,
                'bounds': normalized_to_screen(pos, size, screen_width, screen_height)
            })

        # 递归处理子节点
        for child in get_children(node):
            traverse(child, depth + 1)

    traverse(ui_tree)
    return candidates


def get_children(node: Dict) -> List[Dict]:
    """获取节点的所有子节点"""
    children = node.get('children', [])
    if not children:
        payload = node.get('payload', {})
        if isinstance(payload, dict):
            children = payload.get('children', [])
    return children


# ==================== 选择最佳面板 ====================
def select_best_panel(candidates: List[Dict]) -> Optional[Dict]:
    """
    选择得分最高的面板作为当前有效区域
    :param candidates: 候选面板列表
    :return: 最佳面板（或 None）
    """
    if not candidates:
        return None

    # 按得分降序排序
    sorted_candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)

    # 返回得分最高的面板
    return sorted_candidates[0]


# ==================== 主函数 ====================
def main():
    """主函数"""
    print("=" * 80)
    print("Unity 界面有效区域自动定位 - 方案二：自动推断 + 黑色边框检测")
    print("=" * 80)

    # 1. 连接 Unity
    print("\n[1/8] 连接 Unity...")
    try:
        connect_device('Windows:///')
        poco = UnityPoco()
        print("✅ Unity 连接成功")
    except Exception as e:
        print(f"✗ Unity 连接失败: {e}")
        print("请确保 Unity 编辑器已打开，且游戏已运行")
        return

    # 2. 获取屏幕分辨率
    print("\n[2/8] 获取屏幕分辨率...")
    screen_width, screen_height = get_screen_size()
    print(f"✅ 屏幕分辨率: {screen_width} x {screen_height}")

    # 3. 获取 UI 树
    print("\n[3/8] 获取 UI 树...")
    try:
        ui_tree = poco.dump()
        print(f"✅ UI 树获取成功")
    except Exception as e:
        print(f"✗ UI 树获取失败: {e}")
        return

    # 4. 查找候选面板
    print("\n[4/8] 查找候选面板...")
    candidates = find_candidate_panels(ui_tree, screen_width, screen_height)
    print(f"✅ 找到 {len(candidates)} 个候选面板")

    if len(candidates) == 0:
        print("⚠️ 未找到任何候选面板，请检查 UI 树数据")
        return

    # 5. 选择最佳面板
    print("\n[5/8] 选择最佳面板...")
    best_panel = select_best_panel(candidates)

    if not best_panel:
        print("⚠️ 未找到合适的最佳面板")
        return

    print(f"✅ 最佳面板: {best_panel['details']['name']}")
    print(f"   得分: {best_panel['score']}")
    print(f"   边界: {best_panel['bounds']}")

    # 6. 截图
    print("\n[6/8] 截图...")
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

    # 7. 检测黑色边框并裁剪截图
    print("\n[7/8] 检测黑色边框并裁剪截图...")
    cropped_path, crop_region = crop_to_game_area(screenshot_path, black_threshold=30)

    # 8. 在裁剪后的截图上标注有效区域
    print("\n[8/8] 在裁剪后的截图上标注有效区域...")
    annotated_path = str(screenshot_dir / f"active_region_{timestamp}.png")
    draw_active_region(cropped_path, best_panel, annotated_path, crop_region)

    # 9. 输出评分详情
    print("\n" + "=" * 80)
    print("候选面板评分详情（前 10 名）：")
    print("=" * 80)

    sorted_candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
    for i, candidate in enumerate(sorted_candidates[:10]):
        print(f"\n{i+1}. {candidate['details']['name']}")
        print(f"   得分: {candidate['score']}")
        print(f"   边界: {candidate['bounds']}")
        print(f"   加分项: {candidate['details'].get('bonus', {})}")
        print(f"   扣分项: {candidate['details'].get('penalty', {})}")

    print("\n" + "=" * 80)
    print("完成！请查看以下文件：")
    print("=" * 80)
    print(f"1. 原始截图: {screenshot_path}")
    print(f"2. 裁剪后截图: {cropped_path}")
    print(f"3. 标注后截图: {annotated_path}")
    print("\n请在标注后的截图上确认：")
    print("  - ✅ 红色框：自动推断的有效区域")
    print("  - 如果红色框位置不对，请查看评分详情")
    print("=" * 80)


def draw_active_region(
    screenshot_path: str,
    panel: Dict,
    output_path: str,
    crop_region: Optional[Tuple[int, int, int, int]] = None
):
    """
    在截图上标注有效区域
    :param screenshot_path: 截图路径（可能是裁剪后的）
    :param panel: 面板信息（包含 bounds）
    :param output_path: 输出图片路径
    :param crop_region: 裁剪区域坐标（left, top, right, bottom），用于调整坐标
    """
    # 打开截图
    img = Image.open(screenshot_path)
    draw = ImageDraw.Draw(img)

    # 获取边界框
    left, top, right, bottom = panel['bounds']

    # 如果截图被裁剪了，调整坐标
    if crop_region:
        crop_left, crop_top, _, _ = crop_region
        left = max(0, left - crop_left)
        top = max(0, top - crop_top)
        right = max(0, right - crop_left)
        bottom = max(0, bottom - crop_top)

    # 绘制红色矩形框
    draw.rectangle(
        [left, top, right, bottom],
        outline='red',
        width=5
    )

    # 添加标签
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()

    label = f"Active Region: {panel['details']['name']} (Score: {panel['score']})"
    draw.text((left, top - 40), label, fill='red', font=font)

    # 保存标注后的图片
    img.save(output_path)
    print(f"✅ 标注后截图已保存: {output_path}")


if __name__ == '__main__':
    main()
