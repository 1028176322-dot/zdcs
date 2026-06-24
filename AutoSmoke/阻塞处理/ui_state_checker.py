#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
界面状态检查器 - 按 AutoSmoke_自动点击阻塞界面处理实施方案.md 第5.4节

职责：
  - 判断当前界面是否满足下一步前置条件
  - 判断目标元素是否存在
  - 判断页面是否处于可执行状态
"""

import logging
import time
from typing import Dict, Optional, List
from PIL import Image

logger = logging.getLogger(__name__)


class UIStateChecker:
    """
    界面状态检查器

    检查下一步的前置条件是否满足。
    使用已有模块（CoordinateMapper / GameContentVision）进行定位。
    """

    def __init__(self, mapper=None):
        self._mapper = mapper

    # ============================================================
    # 核心检查
    # ============================================================

    def check_precondition(self, next_step: Dict,
                           game_content_img: Image.Image = None) -> Dict:
        """
        检查下一步的前置条件是否满足

        :param next_step: 解析后的下一步步骤字典
        :param game_content_img: 当前 gameContent 截图
        :return: {"ok": True/False, "reason": "..."}
        """
        action = next_step.get("action", "")
        target = next_step.get("target", {})

        # 不需要前置条件的动作
        no_precondition = ("wait", "screenshot", "back", "swipe", "input")
        if action in no_precondition:
            return {"ok": True, "reason": f"{action} 无需前置条件"}

        # 需要目标存在的动作
        if action in ("click", "long_press", "assert_exists"):
            return self._check_target_exists(target, game_content_img)

        # 断言不存在的反向检查
        if action == "assert_not_exists":
            result = self._check_target_exists(target, game_content_img)
            return {"ok": not result["ok"],
                    "reason": f"目标不应存在: {result.get('reason', '')}" if result["ok"] else "目标不存在，符合预期"}

        return {"ok": True, "reason": "未知动作，默认通过"}

    def _check_target_exists(self, target: Dict,
                             game_content_img: Image.Image) -> Dict:
        """
        检查目标是否存在

        :param target: {"type": "text", "value": "使用"}
        :param game_content_img: 截图
        :return: {"ok": True/False, "reason": "...", "found": {...}}
        """
        if not target:
            return {"ok": False, "reason": "无目标"}

        ttype = target.get("type", "")
        mapper = self._get_mapper()

        # 坐标类目标始终存在（坐标转换总能有结果）
        if ttype in ("normalized", "design", "content", "pixel"):
            return {"ok": True, "reason": f"{ttype} 坐标始终有效"}

        # OCR 文本 — 需要截图
        if ttype == "text":
            if game_content_img is None:
                return {"ok": False, "reason": "检查 text 需要 gameContent 截图"}
            from 视觉识别.game_content_vision import GameContentVision
            vision = GameContentVision()
            result = vision.ocr_find_text(game_content_img, target.get("value", ""))
            if result:
                return {"ok": True, "reason": f"找到文字: {target['value']}",
                        "found": result}
            return {"ok": False, "reason": f"未找到文字: {target['value']}"}

        # 模板匹配
        if ttype == "template":
            if game_content_img is None:
                return {"ok": False, "reason": "检查 template 需要 gameContent 截图"}
            from 视觉识别.game_content_vision import GameContentVision
            vision = GameContentVision()
            result = vision.match_template(game_content_img, target.get("value", ""))
            if result:
                return {"ok": True, "reason": f"模板匹配成功: {target['value']}",
                        "found": result}
            return {"ok": False, "reason": f"模板匹配失败: {target['value']}"}

        return {"ok": False, "reason": f"不支持的定位类型: {ttype}"}

    # ============================================================
    # 通用状态检查
    # ============================================================

    def is_game_content_valid(self, img: Image.Image) -> bool:
        """检查 gameContent 截图是否有效（非空、非全黑）"""
        if img is None:
            return False
        if img.width == 0 or img.height == 0:
            return False
        # 全黑检测
        extrema = img.convert("L").getextrema()
        if extrema == (0, 0):
            return False
        return True

    def is_page_stable(self, img_before: Image.Image,
                       img_after: Image.Image,
                       threshold: float = 0.02) -> bool:
        """检查页面是否稳定（变化小于阈值）"""
        if img_before is None or img_after is None:
            return True
        from 坐标截图.screenshot_diff import ScreenshotDiffer
        differ = ScreenshotDiffer()
        ratio = differ.calc_diff_ratio(img_before, img_after)
        return ratio < threshold

    # ============================================================
    # 内部
    # ============================================================

    def _get_mapper(self):
        if self._mapper is None:
            from 坐标截图.coordinate_mapper import CoordinateMapper
            self._mapper = CoordinateMapper.from_config()
        return self._mapper
