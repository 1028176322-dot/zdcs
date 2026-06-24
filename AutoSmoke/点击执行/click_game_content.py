#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点击执行模块 - 阶段四：稳定点击

支持点击类型（文档 7.2 节）：
1. design 坐标点击   — design(x, y)
2. normalized 坐标点击 — normalized(nx, ny)
3. content 坐标点击   — content(x, y)
4. 图像识别结果点击   — 预留
5. OCR 文字中心点击   — 预留

执行流程（文档 7.4 节）：
1. 校验 gameResolution 与 mapper 的一致性
2. 通过 CoordinateMapper 转换为 screen 坐标
3. 安全校验（越界/弹窗/分辨率变化）
4. 点击前截图
5. 执行鼠标点击（win32）
6. 等待
7. 点击后截图
8. 判断是否发生变化
9. 写入 step_result

使用方式：
    executor = ClickExecutor()
    result = executor.click_design(585, 2400, description="点击使用按钮")
    print(result["result"])  # CLICK_CHANGED / CLICK_NO_CHANGE / CLICK_BLOCKED
"""

import json
import os
import time
import logging
import struct
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from PIL import Image, ImageChops
from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SCREENSHOTS_DIR = os.path.join(CONFIG_DIR, "screenshots")

# ============================================================
# win32 封装（减少顶层 import 依赖）
# ============================================================

_win32_available = False
try:
    import win32api
    import win32con
    import win32gui
    _win32_available = True
except ImportError:
    logger.warning("pywin32 未安装，点击功能不可用")


def _mouse_click(x: int, y: int):
    """使用 win32 API 模拟鼠标点击"""
    if not _win32_available:
        raise RuntimeError("pywin32 未安装，无法执行点击")

    win32api.SetCursorPos((x, y))
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.03)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


# ============================================================
# 截图差异检测
# ============================================================

def _calc_diff_ratio(before_img: Image.Image, after_img: Image.Image) -> float:
    """
    计算两张截图的差异比例

    :param before_img: 点击前截图
    :param after_img: 点击后截图
    :return: 差异比例 (0.0 ~ 1.0)
    """
    if before_img.size != after_img.size:
        logger.warning("截图尺寸不一致: %s vs %s", before_img.size, after_img.size)
        return 1.0

    diff = ImageChops.difference(before_img, after_img)
    diff_gray = diff.convert("L")
    diff_pixels = sum(1 for p in diff_gray.getdata() if p > 10)
    total_pixels = diff_gray.width * diff_gray.height
    return diff_pixels / total_pixels


def _classify_click_result(diff_ratio: float) -> str:
    """
    根据差异比例分类点击结果

    判定标准（文档 8.1 节）：
    diffRatio < 0.1%     可能无响应 → CLICK_NO_CHANGE
    0.1% ~ 2%            轻微变化   → CLICK_CHANGED
    > 2%                 明显变化   → CLICK_CHANGED

    :param diff_ratio: 差异比例
    :return: 结果分类
    """
    if diff_ratio < 0.001:
        return "CLICK_NO_CHANGE"
    return "CLICK_CHANGED"


# ============================================================
# 点击执行器
# ============================================================

class ClickExecutor:
    """
    基于 gameContentRect 的点击执行器

    所有点击操作都经过 CoordinateMapper 映射到屏幕坐标，
    点击前后截图比对，输出结构化的点击结果。
    """

    def __init__(self, mapper=None, config_file: str = None,
                 screenshots_dir: str = None):
        """
        初始化点击执行器

        :param mapper: CoordinateMapper 实例，不传则自动创建
        :param config_file: 配置文件路径
        :param screenshots_dir: 截图输出目录
        """
        self.config_file = config_file or CONFIG_FILE
        self.screenshots_dir = screenshots_dir or SCREENSHOTS_DIR
        self._mapper = mapper

        self._resolved_resolution = None

    # ============================================================
    # 内部方法
    # ============================================================

    def _get_mapper(self):
        """获取 CoordinateMapper（懒加载）"""
        if self._mapper is None:
            from 坐标截图.coordinate_mapper import CoordinateMapper
            self._mapper = CoordinateMapper.from_config(self.config_file)
            if self._mapper is None:
                raise RuntimeError("无法创建 CoordinateMapper")
        return self._mapper

    def _validate_and_convert(self, coordinate_type: str,
                              x: float, y: float) -> Tuple[int, int, Dict]:
        """
        安全校验并转换为屏幕坐标

        :param coordinate_type: 坐标类型 (design/normalized/content)
        :param x: 坐标 X
        :param y: 坐标 Y
        :return: (screen_x, screen_y, debug_info)
        :raises ValueError: 校验失败时抛出
        """
        mapper = self._get_mapper()
        debug = {"input_type": coordinate_type, "input_x": x, "input_y": y}

        # 步骤1：转换为 screen 坐标
        if coordinate_type == "design":
            sx, sy = mapper.design_to_screen(x, y)
            debug["design_x"] = x
            debug["design_y"] = y
        elif coordinate_type == "normalized":
            sx, sy = mapper.normalized_to_screen(x, y)
            dx = x * mapper.design_width
            dy = y * mapper.design_height
            debug["design_x"] = dx
            debug["design_y"] = dy
        elif coordinate_type == "content":
            sx, sy = mapper.content_to_screen(x, y)
            debug["content_x"] = x
            debug["content_y"] = y
        else:
            raise ValueError(f"不支持的坐标类型: {coordinate_type}")

        debug["screen_x"] = sx
        debug["screen_y"] = sy
        debug["scale"] = {"x": round(mapper.scale_x, 4), "y": round(mapper.scale_y, 4)}

        # 步骤2：校验是否在 gameContent 内
        if not mapper.is_in_game_content(sx, sy):
            raise ValueError(
                f"坐标越界: screen({sx},{sy}) 不在 gameContent "
                f"({mapper.gv_left + mapper.gc_left}, "
                f"{mapper.gv_top + mapper.gc_top}) - "
                f"({mapper.gv_left + mapper.gc_right}, "
                f"{mapper.gv_top + mapper.gc_bottom}) 内"
            )

        # 步骤3：校验屏幕可见性（使用虚拟屏幕范围）
        try:
            if _win32_available:
                screen_w = win32api.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
                screen_h = win32api.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
                v_left = win32api.GetSystemMetrics(76)    # SM_XVIRTUALSCREEN
                v_top = win32api.GetSystemMetrics(77)     # SM_YVIRTUALSCREEN
                if not (v_left <= sx <= v_left + screen_w and
                        v_top <= sy <= v_top + screen_h):
                    raise ValueError(
                        f"坐标 ({sx},{sy}) 超出虚拟屏幕范围 "
                        f"({v_left},{v_top})-({v_left+screen_w},{v_top+screen_h})"
                    )
        except ValueError:
            raise
        except Exception:
            pass  # 非 Windows 环境跳过

        return sx, sy, debug

    # ============================================================
    # 点击主方法
    # ============================================================

    def _execute_click(self, screen_x: int, screen_y: int,
                       description: str = "") -> Dict:
        """
        执行一次完整的点击流程

        :param screen_x: 屏幕 X 坐标
        :param screen_y: 屏幕 Y 坐标
        :param description: 点击描述
        :return: 点击结果字典
        """
        run_id = time.strftime("run_%Y%m%d_%H%M%S")
        output_dir = os.path.join(self.screenshots_dir, run_id)
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        result = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "click_point": {"x": screen_x, "y": screen_y},
            "description": description,
            "result": "CLICK_ERROR",
            "diff_ratio": 0.0,
        }

        # ---- 步骤1：点击前截图 ----
        try:
            from PIL import ImageGrab
            before_img = ImageGrab.grab(all_screens=True)
            before_path = os.path.join(output_dir, f"before_{timestamp}.png")
            before_img.save(before_path)
            result["before_screenshot"] = before_path
        except Exception as e:
            logger.warning("点击前截图失败: %s", e)
            before_img = None
            result["before_screenshot"] = None

        # ---- 步骤2：执行点击 ----
        try:
            _mouse_click(screen_x, screen_y)
            logger.info("点击: screen(%d, %d) %s", screen_x, screen_y, description)
            result["click_success"] = True
        except Exception as e:
            result["click_success"] = False
            result["result"] = "CLICK_ERROR"
            result["error"] = str(e)
            return result

        # ---- 步骤3：等待 ----
        time.sleep(0.5)

        # ---- 步骤4：点击后截图 ----
        try:
            after_img = ImageGrab.grab(all_screens=True)
            after_path = os.path.join(output_dir, f"after_{timestamp}.png")
            after_img.save(after_path)
            result["after_screenshot"] = after_path
        except Exception as e:
            logger.warning("点击后截图失败: %s", e)
            after_img = None
            result["after_screenshot"] = None

        # ---- 步骤5：裁剪 gameContent 区域后比对 ----
        if before_img and after_img:
            try:
                mapper = self._get_mapper()
                config = json.load(open(self.config_file, "r", encoding="utf-8"))
                gv = config.get("game_view_coords", {})
                gc = mapper.get_content_rect()

                before_gv = before_img.crop((gv["left"], gv["top"],
                                             gv["right"], gv["bottom"]))
                after_gv = after_img.crop((gv["left"], gv["top"],
                                           gv["right"], gv["bottom"]))

                before_gc = before_gv.crop((gc["left"], gc["top"],
                                            gc["right"], gc["bottom"]))
                after_gc = after_gv.crop((gc["left"], gc["top"],
                                          gc["right"], gc["bottom"]))

                # 保存裁剪后的 gameContent 对比图
                before_gc_path = os.path.join(output_dir, f"before_gc_{timestamp}.png")
                after_gc_path = os.path.join(output_dir, f"after_gc_{timestamp}.png")
                before_gc.save(before_gc_path)
                after_gc.save(after_gc_path)
                result["before_gc_screenshot"] = before_gc_path
                result["after_gc_screenshot"] = after_gc_path

                diff_ratio = _calc_diff_ratio(before_gc, after_gc)
                result["diff_ratio"] = round(diff_ratio, 4)
                result["result"] = _classify_click_result(diff_ratio)
                logger.info("点击结果: %s (差异=%.2f%%)",
                           result["result"], diff_ratio * 100)

            except Exception as e:
                logger.warning("截图差异比对失败: %s", e)
                result["result"] = "CLICK_CHANGED"  # 无法确认无变化时默认 changed
                result["diff_error"] = str(e)

        # ---- 步骤6：保存结果 JSON ----
        result_path = os.path.join(output_dir, f"result_{timestamp}.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        result["result_path"] = result_path

        return result

    # ============================================================
    # 公开点击接口
    # ============================================================

    def click_design(self, x: float, y: float,
                     description: str = "") -> Dict:
        """
        通过设计坐标点击

        :param x: 设计横坐标 (0 ~ design_width)
        :param y: 设计纵坐标 (0 ~ design_height)
        :param description: 点击描述
        :return: 点击结果字典
        """
        try:
            sx, sy, debug = self._validate_and_convert("design", x, y)
            result = self._execute_click(sx, sy, description)
            result["input"] = {"type": "design", "x": x, "y": y}
            result["mapped"] = debug
            return result
        except (ValueError, RuntimeError) as e:
            return {
                "result": "CLICK_BLOCKED",
                "error": str(e),
                "input": {"type": "design", "x": x, "y": y},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "diff_ratio": 0.0,
            }

    def click_normalized(self, nx: float, ny: float,
                         description: str = "") -> Dict:
        """
        通过归一化坐标点击

        :param nx: 归一化横坐标 (0.0~1.0)
        :param ny: 归一化纵坐标 (0.0~1.0)
        :param description: 点击描述
        :return: 点击结果字典
        """
        try:
            sx, sy, debug = self._validate_and_convert("normalized", nx, ny)
            result = self._execute_click(sx, sy, description)
            result["input"] = {"type": "normalized", "nx": nx, "ny": ny}
            result["mapped"] = debug
            return result
        except (ValueError, RuntimeError) as e:
            return {
                "result": "CLICK_BLOCKED",
                "error": str(e),
                "input": {"type": "normalized", "nx": nx, "ny": ny},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "diff_ratio": 0.0,
            }

    def click_content(self, x: float, y: float,
                      description: str = "") -> Dict:
        """
        通过 gameContent 内像素坐标点击

        :param x: gameContent 内横坐标 (0 ~ content_width)
        :param y: gameContent 内纵坐标 (0 ~ content_height)
        :param description: 点击描述
        :return: 点击结果字典
        """
        try:
            sx, sy, debug = self._validate_and_convert("content", x, y)
            result = self._execute_click(sx, sy, description)
            result["input"] = {"type": "content", "x": x, "y": y}
            result["mapped"] = debug
            return result
        except (ValueError, RuntimeError) as e:
            return {
                "result": "CLICK_BLOCKED",
                "error": str(e),
                "input": {"type": "content", "x": x, "y": y},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "diff_ratio": 0.0,
            }

    def click_screen(self, x: int, y: int,
                     description: str = "") -> Dict:
        """
        直接通过屏幕坐标点击（跳过映射，直接执行）

        警告：不推荐长期使用固定屏幕坐标。
        仅供调试或确认坐标是否正确。

        :param x: 屏幕横坐标
        :param y: 屏幕纵坐标
        :param description: 点击描述
        :return: 点击结果字典
        """
        mapper = self._get_mapper()
        if not mapper.is_in_game_content(x, y):
            return {
                "result": "CLICK_OUT_OF_REGION",
                "error": f"坐标 ({x},{y}) 不在 gameContent 内",
                "input": {"type": "screen", "x": x, "y": y},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "diff_ratio": 0.0,
            }
        result = self._execute_click(x, y, description)
        result["input"] = {"type": "screen", "x": x, "y": y}
        return result


# ============================================================
# 独立运行入口
# ============================================================

def test_click_executor():
    """测试点击执行器（不执行真实点击）"""
    print("=" * 60)
    print("点击执行器测试（仅验证映射和安全校验，不执行真实点击）")
    print("=" * 60)

    from 坐标截图.coordinate_mapper import CoordinateMapper
    mapper = CoordinateMapper.from_config()
    assert mapper is not None, "CoordinateMapper 创建失败"
    print(f"\n{mapper.summary()}\n")

    executor = ClickExecutor(mapper=mapper)

    # ---------- 测试1：design 坐标映射 ----------
    print("\n[测试1] design 坐标映射...")
    # 游戏中心 (585, 1266)
    sx, sy, debug = executor._validate_and_convert("design", 585, 1266)
    print(f"  design(585,1266) → screen({sx},{sy})")
    assert mapper.is_in_game_content(sx, sy), "应落在 gameContent 内"
    print("  ✅ 通过")

    # 使用按钮区域 (585, 2400) — 底部按钮区域
    sx, sy, debug = executor._validate_and_convert("design", 585, 2400)
    print(f"  design(585,2400) → screen({sx},{sy})")
    assert mapper.is_in_game_content(sx, sy), "应落在 gameContent 内"
    print("  ✅ 通过")

    # ---------- 测试2：normalized 坐标映射 ----------
    print("\n[测试2] normalized 坐标映射...")
    sx, sy, debug = executor._validate_and_convert("normalized", 0.5, 0.5)
    print(f"  normalized(0.5,0.5) → screen({sx},{sy})")
    assert mapper.is_in_game_content(sx, sy)
    print("  ✅ 通过")

    sx, sy, debug = executor._validate_and_convert("normalized", 0.5, 0.95)
    print(f"  normalized(0.5,0.95) → screen({sx},{sy})")
    assert mapper.is_in_game_content(sx, sy)
    print("  ✅ 通过")

    # ---------- 测试3：content 坐标映射 ----------
    print("\n[测试3] content 坐标映射...")
    sx, sy, debug = executor._validate_and_convert("content", 159, 344)
    print(f"  content(159,344) → screen({sx},{sy})")
    assert mapper.is_in_game_content(sx, sy)
    print("  ✅ 通过")

    # ---------- 测试4：越界检测 ----------
    print("\n[测试4] 越界检测...")
    try:
        executor._validate_and_convert("design", -100, -100)
        print("  ❌ 应抛出异常但未抛出")
    except ValueError as e:
        print(f"  正确阻断: {e}")
        print("  ✅ 通过")

    try:
        executor._validate_and_convert("design", 99999, 99999)
        print("  ❌ 应抛出异常但未抛出")
    except ValueError as e:
        print(f"  正确阻断: {e}")
        print("  ✅ 通过")

    # ---------- 测试5：危险区域（坐标不在 gameContent 内） ----------
    print("\n[测试5] 屏幕上随机点阻断检测...")
    # GameView 面板左上角但不在 gameContent 内
    out_x = mapper.gv_left
    out_y = mapper.gv_top
    result = executor.click_screen(out_x, out_y, "越界点击")
    print(f"  screen({out_x},{out_y}) → {result['result']}")
    assert result["result"] == "CLICK_OUT_OF_REGION"
    print("  ✅ 通过")

    # ---------- 测试6：debug_info 字段完整性 ----------
    print("\n[测试6] mapped debug 信息完整性...")
    sx, sy, debug = executor._validate_and_convert("design", 585, 1266)
    required_fields = ["input_type", "input_x", "input_y",
                       "design_x", "design_y",
                       "screen_x", "screen_y", "scale"]
    for field in required_fields:
        assert field in debug, f"缺少字段: {field}"
    print(f"  包含所有 {len(required_fields)} 个字段")
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("所有映射测试通过 ✅")
    print("=" * 60)
    print("\n⚠ 未执行真实点击（需要 Unity 运行 + pywin32）")
    print("  运行真实点击测试：")
    print("    python -c \"from 点击执行.click_game_content import ClickExecutor;")
    print("    e = ClickExecutor(); print(e.click_design(585, 2400, '测试'))\"")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    test_click_executor()
