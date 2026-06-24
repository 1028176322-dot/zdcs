#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GameContentLocator v2 - 三层区域模型实现

三层区域模型：
1. gameViewPanelRect  - GameView整个面板（含标签栏、工具栏）
2. gameRenderAreaRect - GameView内部渲染容器（不含标签栏、工具栏，但可能有黑边）
3. gameContentRect    - 真实游戏画面（不含工具栏、不含黑边）

v2 修正（依据 AutoSmoke_Game视图三层定位迭代记录_20260612.md）：
- contentTop 单独检测游戏画面顶部，而非直接使用工具栏底部
- contentHeight 基于设计分辨率比例反算
- 截图高度不足时返回错误状态 GAME_VIEW_CAPTURE_TOO_SHORT
"""

import numpy as np
from PIL import Image, ImageDraw
import logging
import json
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# 设计分辨率（手机竖屏）
DESIGN_WIDTH = 1170
DESIGN_HEIGHT = 2532
TARGET_RATIO = DESIGN_WIDTH / DESIGN_HEIGHT  # ~0.462


# ============================================================
# 第一层 / 第二层 检测
# ============================================================

def detect_toolbar_height(img_rgb: np.ndarray) -> int:
    """
    检测 Unity GameView 顶部工具栏高度

    Unity 工具栏特征：
    - 通常高 20-40 像素
    - 灰色（RGB 三通道接近，值约 120-180）
    - 包含 "Display", "1170x2532", "Scale" 等文字

    返回：
        工具栏高度（像素）
    """
    height, _ = img_rgb.shape[:2]

    gray_low = 100
    gray_high = 200

    toolbar_bottom = 0

    for y in range(min(50, height)):
        row = img_rgb[y, :]
        channel_diff = np.max(row, axis=0) - np.min(row, axis=0)
        row_mean = np.mean(row, axis=0)

        is_gray_row = (
            np.mean(channel_diff) < 30 and
            np.mean(row_mean) > gray_low and
            np.mean(row_mean) < gray_high
        )

        if is_gray_row:
            toolbar_bottom = y + 1
        else:
            break

    if toolbar_bottom == 0:
        toolbar_bottom = 22  # 默认值

    logger.info(f"检测到工具栏高度: {toolbar_bottom} 像素")
    return toolbar_bottom


# ============================================================
# 第三层 - contentTop 检测
# ============================================================

def _calc_non_toolbar_pixel_ratio(row: np.ndarray) -> float:
    """
    计算一行中非工具栏/非黑边像素的比例

    判断条件：
    - 工具栏/黑边像素：RGB 三通道差异 < 30 且 亮度 < 80
    - 其余视为有效像素

    参数：
        row: numpy array, shape (N, 3)

    返回：
        有效像素比例 (0.0 ~ 1.0)
    """
    if row.size == 0:
        return 0.0

    channel_diff = np.max(row, axis=1) - np.min(row, axis=1)
    brightness = np.mean(row, axis=1)

    # 工具栏/黑边条件：三通道非常接近（近乎纯灰）且亮度很低
    # 注意：放宽条件以避免将暗色游戏画面内容误判为"工具栏"
    is_invalid = (channel_diff < 20) & (brightness < 60)

    valid_count = np.sum(~is_invalid)
    total = len(row)

    return valid_count / total


def _save_content_top_scan_debug(img_rgb, detected_top, scan_start, render_top, render_bottom,
                                  content_left, content_right, debug_dir):
    """保存 contentTop 扫描调试图"""
    h, w = img_rgb.shape[:2]
    debug_img = Image.fromarray(img_rgb.copy())
    draw = ImageDraw.Draw(debug_img)

    # 渲染容器范围（黄框）
    draw.rectangle(
        [0, render_top, w - 1, render_bottom - 1],
        outline=(255, 255, 0), width=2
    )
    draw.text((5, render_top + 2), f"renderTop={render_top}", fill=(255, 255, 0))

    # 扫描范围（contentLeft~contentRight，浅蓝框）
    draw.rectangle(
        [content_left, render_top, content_right, render_bottom - 1],
        outline=(0, 165, 255), width=1
    )

    # 扫描起始线（橙色虚线）
    if scan_start > render_top:
        draw.line(
            [(content_left, scan_start), (content_right, scan_start)],
            fill=(255, 165, 0), width=2
        )
        draw.text((content_right + 5, scan_start - 10),
                  f"scanStart={scan_start}", fill=(255, 165, 0))

    # 检测到的 contentTop（绿线）
    if detected_top is not None:
        draw.line(
            [(content_left, detected_top), (content_right, detected_top)],
            fill=(0, 255, 0), width=3
        )
        draw.text((content_left + 5, max(0, detected_top - 20)),
                  f"contentTop={detected_top}", fill=(0, 255, 0))

    debug_img.save(f"{debug_dir}/debug_content_top_scan.png")
    logger.info(f"ContentTop 扫描调试图已保存: {debug_dir}/debug_content_top_scan.png")


def detect_content_horizontal_bounds(
    img_rgb: np.ndarray,
    render_rect: dict,
    scan_start: int = None,
    sample_rows: int = 30
) -> tuple:
    """
    从渲染区域中扫描非黑像素，检测游戏内容的左右边界。

    跳过顶部工具栏区域（Unity 灰色背景及文字影响全宽检测），
    只在下部内容区域扫描。

    参数：
        img_rgb:     截图数据
        render_rect: 渲染容器区域
        scan_start:  扫描起始行（跳过顶部工具栏区域）。默认 = render_top + 40
        sample_rows: 扫描行数（均匀采样）

    返回：
        (left, right, width) 游戏内容左右边界和宽度
    """
    height, width = img_rgb.shape[:2]
    r_top = render_rect['top']
    r_bottom = render_rect.get('bottom', height)

    # 跳过顶部工具栏影响区，从 content 区域开始扫描
    if scan_start is None:
        scan_start = r_top + 40
    scan_start = min(scan_start, r_bottom - sample_rows)

    available = r_bottom - scan_start
    if available < sample_rows:
        sample_rows = max(1, available)

    if sample_rows <= 0:
        logger.warning('渲染区域太小，使用全宽')
        return 0, width, width

    # 在扫描区域内均匀采样若干行
    rows = np.linspace(scan_start, r_bottom - 1, sample_rows, dtype=int)

    # 对每个采样行，标记哪些列不是纯黑像素
    non_black_mask = np.zeros(width, dtype=bool)

    for y in rows:
        # 不是纯黑（任意通道亮度 > 15 即视为有内容）
        row_brightness = np.max(img_rgb[y, :], axis=1)
        non_black_mask |= (row_brightness > 15)

    # 找到最左和最右的非黑列
    non_black_cols = np.where(non_black_mask)[0]
    if len(non_black_cols) == 0:
        logger.warning('未检测到非黑像素，使用全宽作为内容区域')
        return 0, width, width

    content_left = int(non_black_cols[0])
    content_right = int(non_black_cols[-1]) + 1
    content_width = content_right - content_left

    logger.info(f'图像检测内容水平边界: left={content_left}, right={content_right}, width={content_width}')
    return content_left, content_right, content_width


def _fit_content_rect_in_render_area(render_width: int, render_height: int, target_ratio: float) -> dict:
    """Fit the game content into the Unity Game render area while preserving aspect ratio."""
    if render_width <= 0 or render_height <= 0 or target_ratio <= 0:
        return {"left": 0, "top": 0, "width": max(0, render_width), "height": max(0, render_height)}

    render_ratio = render_width / render_height

    if render_ratio > target_ratio:
        content_height = render_height
        content_width = int(round(content_height * target_ratio))
        content_left = (render_width - content_width) // 2
        content_top = 0
        fit_mode = "height_limited"
    else:
        content_width = render_width
        content_height = int(round(content_width / target_ratio))
        content_left = 0
        content_top = (render_height - content_height) // 2
        fit_mode = "width_limited"

    return {
        "left": int(content_left),
        "top": int(content_top),
        "width": int(content_width),
        "height": int(content_height),
        "mode": fit_mode
    }


def detect_content_top(
    img_rgb: np.ndarray,
    render_rect: dict,
    content_left: int,
    content_right: int,
    preferred_top: int = None,
    debug: bool = False,
    debug_dir: str = None
) -> dict:
    """
    检测游戏画面顶部边界

    优先从 preferred_top 附近开始扫描（由 aspect-fit 计算得出），
    只在小范围内向下查找游戏顶部。

    参数：
        img_rgb:       截图数据
        render_rect:   渲染容器区域 {"top": ..., "bottom": ...}
        content_left:  内容左边界
        content_right: 内容右边界
        preferred_top: 比例适配的期望顶部（在截图中的 y 坐标）
        debug:         是否保存调试图像
        debug_dir:     调试图像保存目录

    返回：
        {"top": int, "scan_start": int, "scan_lines": [...]}  成功
        {"top": None, "scan_start": int, "reason": "..."}    失败
    """
    height = img_rgb.shape[0]
    render_top = render_rect["top"]
    render_bottom = render_rect.get("bottom", height)

    # 扫描起点：优先使用比例适配的期望顶部 - 10px 余量
    if preferred_top is not None:
        scan_start = max(preferred_top - 10, render_top)
    else:
        # 无 preferred_top 时回退到旧的安全偏移
        scan_start = max(render_top + 15, render_top)

    scan_lines = []

    for y in range(scan_start, render_bottom - 2):  # 需要至少3行空间
        ok_count = 0

        for yy in range(y, y + 3):
            row = img_rgb[yy, content_left:content_right]
            valid_ratio = _calc_non_toolbar_pixel_ratio(row)
            if debug:
                scan_lines.append({"y": yy, "valid_ratio": round(valid_ratio, 4)})

            if valid_ratio >= 0.5:  # 放宽：50% 有效像素即可
                ok_count += 1

        if ok_count >= 3:  # 3行全部满足
            logger.info(f"检测到游戏画面顶部: y={y}")

            if debug and debug_dir:
                _save_content_top_scan_debug(
                    img_rgb, y, scan_start, render_top, render_bottom,
                    content_left, content_right, debug_dir
                )

            return {"top": int(y), "scan_start": int(scan_start), "scan_lines": scan_lines}

    logger.warning("未检测到游戏画面顶部")
    if debug and debug_dir:
        _save_content_top_scan_debug(
            img_rgb, None, scan_start, render_top, render_bottom,
            content_left, content_right, debug_dir
        )

    return {"top": None, "scan_start": int(scan_start), "reason": "未找到连续3行满足有效像素比例>=50%的条件"}


# ============================================================
# 调试图输出
# ============================================================

def _save_expected_rect_debug(img_rgb, debug_info, debug_dir):
    """保存 expected GameContent rect 调试图"""
    h, w = img_rgb.shape[:2]
    debug_img = Image.fromarray(img_rgb.copy())
    draw = ImageDraw.Draw(debug_img)

    cl = debug_info["contentLeft"]
    ct = debug_info["detectedContentTop"]
    cr = debug_info["contentRight"]
    cb = debug_info["expectedContentBottom"]

    too_short = debug_info["isCaptureTooShort"]
    outline_color = (0, 255, 0) if not too_short else (255, 0, 0)

    draw.rectangle([cl, ct, cr, cb], outline=outline_color, width=3)
    draw.text((cl + 5, max(0, ct - 20)),
              f"GameContent(Expected): ({cl},{ct})-({cr},{cb})",
              fill=outline_color)

    if too_short:
        draw.line(
            [(0, cb), (w - 1, cb)],
            fill=(255, 0, 0), width=2
        )
        draw.text((5, cb - 20),
                  f"OUT OF BOUNDS: expectedBottom={cb} > imageHeight={h}",
                  fill=(255, 0, 0))

    debug_img.save(f"{debug_dir}/debug_game_content_expected_rect.png")
    logger.info(f"Expected rect 调试图已保存: {debug_dir}/debug_game_content_expected_rect.png")


# ============================================================
# 主入口
# ============================================================

def find_game_content_rect(
    img_rgb: np.ndarray,
    design_width: int = DESIGN_WIDTH,
    design_height: int = DESIGN_HEIGHT,
    debug: bool = False,
    debug_dir: str = None
) -> dict:
    """
    从 GameView 截图中找到游戏画面区域（三层模型）

    v2 修正：
    - contentTop 单独检测游戏画面顶部
    - contentHeight 基于设计分辨率比例反算
    - 截图高度不足时返回 GAME_VIEW_CAPTURE_TOO_SHORT

    参数：
        img_rgb:       GameView 截图数据
        design_width:  游戏设计分辨率宽度
        design_height: 游戏设计分辨率高度
        debug:         是否保存调试图像
        debug_dir:     调试图像保存目录

    返回：
        OK 状态：
            {"status": "OK", "gameViewPanelRect": {...},
             "gameRenderAreaRect": {...}, "gameContentRect": {...},
             "scale": {...}, "debug_info": {...}}
        截图不足：
            {"status": "GAME_VIEW_CAPTURE_TOO_SHORT", ...同上...}
    """
    height, width = img_rgb.shape[:2]
    target_ratio = design_width / design_height
    logger.info(
        f"分析 GameView 截图: {width}x{height}, "
        f"设计分辨率: {design_width}x{design_height}, 比例: {target_ratio:.4f}"
    )

    # ==================== 第一层：GameView 面板区域 ====================
    game_view_panel_rect = {
        "left": 0, "top": 0, "width": width, "height": height
    }
    logger.info(f"第一层 - GameView 面板区域: {game_view_panel_rect}")

    # ==================== 第二层：渲染容器区域 ====================
    toolbar_height = detect_toolbar_height(img_rgb)
    render_area_height = height - toolbar_height

    game_render_area_rect = {
        "left": 0, "top": toolbar_height,
        "width": width, "height": render_area_height
    }
    logger.info(f"第二层 - 渲染容器区域: {game_render_area_rect}")

    # ========== 预计算 contentLeft / contentRight ==========
    # Unity GameView 在窗口被上下左右拉伸时，会按目标分辨率比例做 contain 适配。
    # 这里先用渲染区宽高算出理论 GameContent，再用图像左右边界做二次校正。
    fitted_rect = _fit_content_rect_in_render_area(width, render_area_height, target_ratio)
    content_left = fitted_rect["left"]
    content_top_from_fit = toolbar_height + fitted_rect["top"]
    content_width = fitted_rect["width"]
    content_height = fitted_rect["height"]
    content_right = content_left + content_width
    content_width_source = f"aspect_fit:{fitted_rect.get('mode', 'unknown')}"
    logger.info(
        f"按渲染区比例预计算内容区域: left={content_left}, top={content_top_from_fit}, "
        f"width={content_width}, height={content_height}, source={content_width_source}"
    )

    # ==================== 第三层：检测 contentTop ====================
    render_rect = {"top": toolbar_height, "bottom": height}
    content_top_result = detect_content_top(
        img_rgb, render_rect, content_left, content_right,
        preferred_top=content_top_from_fit,
        debug=debug, debug_dir=debug_dir
    )

    # contentTop 优先使用比例适配结果，图像检测只允许小范围修正（±8px）
    max_top_deviation = 8
    if content_top_result["top"] is not None:
        detected_top = content_top_result["top"]
        top_diff = abs(detected_top - content_top_from_fit)
        if top_diff <= max_top_deviation:
            content_top = detected_top
            content_top_source = "image_scan"
            logger.info(
                f"contentTop 使用图像检测: y={detected_top} "
                f"(deviation={top_diff}px ≤ {max_top_deviation}px)"
            )
        else:
            content_top = content_top_from_fit
            content_top_source = "aspect_fit"
            logger.info(
                f"contentTop 使用比例适配: y={content_top_from_fit} "
                f"(图像检测={detected_top}, deviation={top_diff}px > {max_top_deviation}px)"
            )
    else:
        content_top = content_top_from_fit
        content_top_source = "aspect_fit"
        logger.warning(f"contentTop 检测失败，回退到比例适配: {content_top}")

    # ========== 使用实际图像左右边界校正宽度 ==========
    # 不再用 image_height - contentTop 反推宽度，否则窗口上下拉伸或截图高度不足时会错误缩窄。
    bounds_scan_start = min(max(content_top + 20, toolbar_height + 40), max(toolbar_height, height - 1))
    detected_left, detected_right, detected_width = detect_content_horizontal_bounds(
        img_rgb,
        render_rect,
        scan_start=bounds_scan_start
    )

    min_valid_width = max(1, int(width * 0.2))
    detected_is_valid = min_valid_width <= detected_width <= width
    width_diff_ratio = abs(detected_width - content_width) / max(content_width, 1)

    if detected_is_valid and width_diff_ratio <= 0.12:
        content_left = detected_left
        content_right = detected_right
        content_width = detected_width
        content_height = int(round(content_width / target_ratio))
        content_width_source = "horizontal_bounds"
        logger.info(
            f"使用图像检测左右边界校正内容区域: left={content_left}, "
            f"right={content_right}, width={content_width}"
        )
    else:
        logger.info(
            f"保留比例适配内容区域: detectedWidth={detected_width}, "
            f"fitWidth={content_width}, diffRatio={width_diff_ratio:.4f}"
        )

    content_bottom = content_top + content_height
    capture_too_short = content_bottom > height

    if capture_too_short:
        logger.error(
            f"截图高度不足! contentTop={content_top}, contentBottom={content_bottom} > "
            f"imageHeight={height}, 缺失 {content_bottom - height}px"
        )
    
    game_content_rect = {
        "left": int(content_left),
        "top": int(content_top),
        "width": int(content_width),
        "height": int(content_height)
    }
    logger.info(f"第三层 - 游戏内容区域: {game_content_rect}")
    logger.info(f"  反算: contentWidth={content_width}, contentHeight={content_height}, "
                f"contentBottom={content_bottom}")

    # ========== 截图高度校验 ==========
    # ========== 缩放比例 ==========
    scale_x = game_content_rect["width"] / design_width
    scale_y = game_content_rect["height"] / design_height
    logger.info(f"缩放比例: scaleX={scale_x:.4f}, scaleY={scale_y:.4f}")

    # ========== Debug 信息 ==========
    debug_info = {
        "contentLeft": int(content_left),
        "contentRight": int(content_right),
        "contentWidth": int(content_width),
        "detectedContentTop": int(content_top),
        "contentTopScanStart": int(content_top_result.get("scan_start", -1)),
        "expectedContentHeight": int(content_height),
        "expectedContentBottom": int(content_bottom),
        "panelImageHeight": height,
        "isCaptureTooShort": capture_too_short,
        "toolbarHeight": toolbar_height,
        "renderAreaHeight": render_area_height,
        "contentTopFromFit": int(content_top_from_fit),
        "contentTopSource": content_top_source,
        "contentTopDeviation": int(top_diff) if content_top_result.get("top") is not None else 0,
        "contentWidthSource": content_width_source,
        "detectedHorizontalLeft": int(detected_left),
        "detectedHorizontalRight": int(detected_right),
        "detectedHorizontalWidth": int(detected_width)
    }

    # ========== 保存调试图像 ==========
    if debug and debug_dir:
        _save_debug_three_layers(
            img_rgb, width, height, toolbar_height,
            content_left, content_top, content_right, content_bottom,
            capture_too_short, debug_dir
        )
        _save_expected_rect_debug(img_rgb, debug_info, debug_dir)

        # 如果截图足够，保存纯游戏内容截图
        if not capture_too_short:
            _save_content_crop(
                img_rgb, content_left, content_top,
                content_right, content_bottom, debug_dir
            )

    # ========== 构建返回 ==========
    result = {
        "gameViewPanelRect": game_view_panel_rect,
        "gameRenderAreaRect": game_render_area_rect,
        "gameContentRect": game_content_rect,
        "scale": {"x": scale_x, "y": scale_y},
        "debug_info": debug_info
    }

    if capture_too_short:
        result["status"] = "GAME_VIEW_CAPTURE_TOO_SHORT"
        result["message"] = (
            f"截图高度不足: expectedBottom={content_bottom}, "
            f"imageHeight={height}, 缺失 {content_bottom - height}px"
        )
    else:
        result["status"] = "OK"

    return result


def _save_debug_three_layers(img_rgb, width, height, toolbar_height,
                              content_left, content_top, content_right, content_bottom,
                              capture_too_short, debug_dir):
    """保存三层标注调试图"""
    debug_img = Image.fromarray(img_rgb.copy())
    draw = ImageDraw.Draw(debug_img)

    # 第一层：红色
    draw.rectangle([0, 0, width - 1, height - 1], outline=(255, 0, 0), width=3)
    draw.text((10, 10), "1. GameViewPanel", fill=(255, 0, 0))

    # 第二层：黄色
    draw.rectangle([0, toolbar_height, width - 1, height - 1],
                   outline=(255, 255, 0), width=3)
    draw.text((10, toolbar_height + 10), "2. GameRenderArea", fill=(255, 255, 0))

    # 第三层：绿色
    draw.rectangle([content_left, content_top, content_right, content_bottom],
                   outline=(0, 255, 0), width=3)
    draw.text((content_left, max(0, content_top - 20)),
              "3. GameContent", fill=(0, 255, 0))

    # 截图不足时标注
    if capture_too_short:
        draw.line([(0, content_bottom), (width - 1, content_bottom)],
                  fill=(255, 0, 0), width=2)
        draw.text((10, content_bottom - 25),
                  f"Expected Bottom={content_bottom} (OUT OF BOUNDS)",
                  fill=(255, 0, 0))

    debug_img.save(f"{debug_dir}/debug_three_layers.png")
    logger.info(f"三层标注图已保存: {debug_dir}/debug_three_layers.png")


def _save_content_crop(img_rgb, cl, ct, cr, cb, debug_dir):
    """保存纯游戏内容截图"""
    content_img = Image.fromarray(img_rgb[ct:cb, cl:cr])
    path = f"{debug_dir}/game_content_realtime.png"
    content_img.save(path)
    logger.info(f"纯游戏内容截图已保存: {path}")


# ============================================================
# 测试入口
# ============================================================

def test_locator():
    """测试函数"""
    import time

    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    from PIL import ImageGrab

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    debug_dir = f"screenshots/debug_{timestamp}"
    Path(debug_dir).mkdir(parents=True, exist_ok=True)

    print("正在截取所有屏幕...")
    full_img = ImageGrab.grab(all_screens=True)

    game_view_coords = config.get("game_view_coords")
    if not game_view_coords:
        print("❌ 未找到 GameView 坐标配置")
        return

    result = None

    for attempt in range(2):
        left, top, right, bottom = (
            int(game_view_coords["left"]),
            int(game_view_coords["top"]),
            int(game_view_coords["right"]),
            int(game_view_coords["bottom"])
        )

        print(f"裁剪到 GameView 区域: ({left}, {top}, {right}, {bottom})")
        game_view_img = full_img.crop((left, top, right, bottom))
        game_view_np = np.array(game_view_img)

        suffix = "" if attempt == 0 else "_expanded"
        game_view_path = f"{debug_dir}/game_view{suffix}.png"
        game_view_img.save(game_view_path)
        print(f"✅ GameView 截图已保存: {game_view_path}")

        print("\n开始分析游戏画面区域（三层模型 v2）...")
        result = find_game_content_rect(
            game_view_np,
            design_width=config.get("game_resolution", {}).get("width", 1170),
            design_height=config.get("game_resolution", {}).get("height", 2532),
            debug=True,
            debug_dir=debug_dir
        )

        if result["status"] != "GAME_VIEW_CAPTURE_TOO_SHORT":
            break

        if attempt > 0:
            print("\n⚠️ 扩展后仍然高度不足，本次不再继续扩大 bottom，请检查内容区宽度/渲染区识别。")
            break

        di = result["debug_info"]
        missing = di["expectedContentBottom"] - di["panelImageHeight"]
        if missing <= 0:
            break

        if game_view_coords.get("auto_expanded_bottom"):
            print("\n⚠️ GameView bottom 已自动扩展过，本次不再继续扩大。")
            break

        old_bottom = int(game_view_coords["bottom"])
        padding = 4
        new_bottom = old_bottom + missing + padding
        game_view_coords["bottom"] = new_bottom
        game_view_coords["height"] = new_bottom - int(game_view_coords["top"])
        game_view_coords["auto_expanded_bottom"] = True
        game_view_coords["expand_reason"] = (
            f"contentBottom={di['expectedContentBottom']}, "
            f"panelHeight={di['panelImageHeight']}, missing={missing}, padding={padding}"
        )
        config["game_view_coords"] = game_view_coords
        print(
            f"\n⚠️ 截图高度不足，自动扩大 GameView bottom: "
            f"{old_bottom} -> {new_bottom} (+{new_bottom - old_bottom}px)，并重新分析"
        )

    print(f"\n结果状态: {result['status']}")
    print(f"  第一层 - GameViewPanel:    {result['gameViewPanelRect']}")
    print(f"  第二层 - GameRenderArea:   {result['gameRenderAreaRect']}")
    print(f"  第三层 - GameContent:      {result['gameContentRect']}")
    print(f"  缩放比例:                {result['scale']}")

    if "debug_info" in result:
        di = result["debug_info"]
        print(f"\n  Debug 信息:")
        for k, v in di.items():
            print(f"    {k}: {v}")

    if result["status"] == "GAME_VIEW_CAPTURE_TOO_SHORT":
        di = result["debug_info"]
        missing = di["expectedContentBottom"] - di["panelImageHeight"]
        print(f"\n{'=' * 50}")
        print(f"⚠️ 截图高度不足! 需要重新截取更大的 GameViewPanel")
        print(f"  期望底部: {di['expectedContentBottom']}")
        print(f"  实际高度: {di['panelImageHeight']}")
        print(f"  缺失高度: {missing} 像素")
        print(f"{'=' * 50}")

    # 保存结果到 config.json
    config["game_content_result"] = result
    config["game_content_result"]["timestamp"] = timestamp

    content = result.get("gameContentRect")
    if content:
        config["game_content_rect"] = {
            "left": int(content["left"]),
            "top": int(content["top"]),
            "right": int(content["left"] + content["width"]),
            "bottom": int(content["top"] + content["height"]),
            "width": int(content["width"]),
            "height": int(content["height"]),
            "timestamp": timestamp,
            "status": result["status"]
        }

    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 结果已保存到 config.json")

    print(f"\n调试图输出:")
    print(f"  {os.path.abspath(f'{debug_dir}/debug_three_layers.png')}")
    print(f"  {os.path.abspath(f'{debug_dir}/debug_content_top_scan.png')}")
    print(f"  {os.path.abspath(f'{debug_dir}/debug_game_content_expected_rect.png')}")
    if result["status"] == "OK":
        print(f"  {os.path.abspath(f'{debug_dir}/game_content_realtime.png')}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    test_locator()
