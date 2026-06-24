#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阻塞检测器 - 按 AutoSmoke_自动点击阻塞界面处理实施方案.md 第5.2节

职责：
  - 检测当前界面是否存在阻塞
  - 识别阻塞类型
  - 输出 blocker_result

检测来源：OCR 文本 / 截图特征 / 模板匹配
"""

import logging
import time
from typing import Dict, Optional, List, Tuple
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class BlockerDetector:
    """
    阻塞检测器

    使用 OCR 文本识别和截图特征分析来检测界面阻塞。
    """

    def __init__(self, rules=None, mapper=None):
        self._rules = rules
        self._mapper = mapper
        self._vision = None

    def _get_rules(self):
        if self._rules is None:
            from 阻塞处理.blocker_rules import BlockerRules
            self._rules = BlockerRules()
        return self._rules

    def _get_vision(self):
        if self._vision is None:
            from 视觉识别.game_content_vision import GameContentVision
            self._vision = GameContentVision()
        return self._vision

    # ============================================================
    # 主检测
    # ============================================================

    def detect(self, game_content_img: Image.Image,
               prev_img: Image.Image = None) -> Dict:
        """
        检测当前界面是否存在阻塞

        :param game_content_img: 当前 gameContent 截图
        :param prev_img: 上一步的截图（用于检测突变）
        :return: blocker_result 或 {"detected": False}
        """
        if game_content_img is None:
            return {"detected": False, "reason": "无截图"}

        rules = self._get_rules()

        # ---- 1. OCR 文本检测 ----
        ocr_result = self._detect_by_ocr(game_content_img, rules)
        if ocr_result["detected"]:
            return ocr_result

        # ---- 2. 遮罩/弹窗特征检测 ----
        mask_result = self._detect_mask_popup(game_content_img)
        if mask_result["detected"]:
            return mask_result

        # ---- 3. 页面突变检测（与上一步截图对比） ----
        if prev_img is not None:
            change_res = self._detect_sudden_change(game_content_img, prev_img)
            if change_res["detected"]:
                return change_res

        return {"detected": False, "reason": "未检测到阻塞"}

    # ============================================================
    # OCR 文本检测
    # ============================================================

    def _detect_by_ocr(self, img: Image.Image, rules) -> Dict:
        """通过 OCR 文本检测阻塞"""
        vision = self._get_vision()
        ocr_texts = vision.ocr_get_texts(img)
        texts = [t["text"] for t in ocr_texts]

        if not texts:
            return {"detected": False}

        classified = rules.classify_texts(texts)

        # 1. 危险确认弹窗（最高优先级）
        if rules.has_dangerous_confirm(texts):
            return {
                "detected": True,
                "blockerType": "dangerous_confirm",
                "confidence": "high",
                "source": ["ocr"],
                "keywords": classified["dangerous"],
                "dangerous": True,
                "suggestedActions": rules.get_resolve_priority("dangerous_confirm"),
                "forbiddenActions": rules.get_forbidden_actions("dangerous_confirm"),
            }

        # 2. 奖励弹窗
        if classified["reward"] and any(kw in texts for kw in rules.get("reward_confirm_keywords", ["确认"])):
            return {
                "detected": True,
                "blockerType": "reward_popup",
                "confidence": "high",
                "source": ["ocr"],
                "keywords": classified["reward"],
                "dangerous": False,
                "safeConfirmAllowed": True,
                "suggestedActions": rules.get_resolve_priority("reward_popup"),
            }

        # 3. 场景跳转 Loading（检测加载关键词和进度特征）
        if rules.is_scene_loading_related(texts):
            progress = self._detect_loading_progress(img)
            return {
                "detected": True,
                "blockerType": "scene_transition_loading",
                "confidence": "medium",
                "source": ["ocr"] if ocr_texts else ["screenshot"],
                "keywords": classified.get("loading", []),
                "dangerous": False,
                "progress": progress,
                "suggestedActions": rules.get_resolve_priority("scene_transition_loading"),
                "maxWaitMs": rules.get("scene_loading_max_wait_ms", 30000),
                "stuckThresholdMs": rules.get("scene_loading_stuck_threshold_ms", 10000),
                "forbiddenActions": rules.get_forbidden_actions("scene_transition_loading"),
            }

        # 4. 重连弹窗
        if classified["reconnect"]:
            return {
                "detected": True,
                "blockerType": "reconnect_loading",
                "confidence": "medium",
                "source": ["ocr"],
                "keywords": classified["reconnect"],
                "dangerous": False,
                "suggestedActions": rules.get_resolve_priority("reconnect_loading"),
                "maxWaitMs": rules.get("reconnect_max_wait_ms", 10000),
            }

        # 4. 引导
        if classified["guide"]:
            return {
                "detected": True,
                "blockerType": "guide_overlay",
                "confidence": "medium",
                "source": ["ocr"],
                "keywords": classified["guide"],
                "dangerous": False,
                "suggestedActions": rules.get_resolve_priority("guide_overlay"),
                "maxSteps": rules.get("guide_max_steps", 5),
            }

        # 5. 普通弹窗（有关键词 "确定"/"取消"）
        if classified["popup"]:
            return {
                "detected": True,
                "blockerType": "popup",
                "confidence": "medium",
                "source": ["ocr"],
                "keywords": classified["popup"],
                "dangerous": False,
                "suggestedActions": rules.get_resolve_priority("popup"),
            }

        # 6. 公告
        if classified["announcement"]:
            return {
                "detected": True,
                "blockerType": "announcement",
                "confidence": "medium",
                "source": ["ocr"],
                "keywords": classified["announcement"],
                "dangerous": False,
                "suggestedActions": rules.get_resolve_priority("announcement"),
            }

        return {"detected": False}

    # ============================================================
    # 遮罩/弹窗特征检测
    # ============================================================

    def _detect_mask_popup(self, img: Image.Image) -> Dict:
        """通过截图特征检测遮罩弹窗"""
        np_img = np.array(img)
        h, w = np_img.shape[:2]
        gray = np.mean(np_img, axis=2)

        # 检测大面积暗色区域（遮罩特征）
        dark_threshold = 60  # 亮度低于 60 视为暗色
        dark_ratio = np.mean(gray < dark_threshold)

        # 如果超过 40% 的区域变暗，可能有遮罩
        if dark_ratio > 0.4:
            # 找相对明亮的矩形区域（弹窗主体）
            bright_mask = gray > dark_threshold
            rows = np.any(bright_mask, axis=1)
            cols = np.any(bright_mask, axis=0)

            if np.any(rows) and np.any(cols):
                y_min = int(np.argmax(rows))
                y_max = int(h - np.argmax(rows[::-1]))
                x_min = int(np.argmax(cols))
                x_max = int(w - np.argmax(cols[::-1]))

                popup_rect = [x_min, y_min, x_max, y_max]
                popup_area = (x_max - x_min) * (y_max - y_min)
                total_area = w * h
                popup_ratio = popup_area / total_area

                # 弹窗面积在 10%~70% 之间比较合理
                if 0.1 < popup_ratio < 0.7:
                    # 计算弹窗外的空白候选点
                    candidates = self._calc_blank_candidates(popup_rect, w, h)
                    return {
                        "detected": True,
                        "blockerType": "modal_popup",
                        "confidence": "high",
                        "source": ["mask", "popup_rect"],
                        "dangerous": False,
                        "popupRect": popup_rect,
                        "suggestedActions": ["click_close", "click_cancel",
                                              "click_outside_blank_area", "press_back"],
                        "outsideBlankCandidates": candidates,
                    }

        return {"detected": False}

    # ============================================================
    # 页面突变检测
    # ============================================================

    def _detect_sudden_change(self, current: Image.Image,
                              previous: Image.Image) -> Dict:
        """检测页面是否突然变化（可能打开了弹窗）"""
        if current.size != previous.size:
            return {"detected": False}

        from 坐标截图.screenshot_diff import ScreenshotDiffer
        differ = ScreenshotDiffer()
        ratio = differ.calc_diff_ratio(current, previous)

        # 变化超过 30% 可能是打开了弹窗/新页面
        if ratio > 0.3:
            return {
                "detected": True,
                "blockerType": "page_change",
                "confidence": "low",
                "source": ["diff"],
                "diffRatio": ratio,
                "dangerous": False,
                "suggestedActions": ["wait", "detect_again"],
            }

        return {"detected": False}

    # ============================================================
    # 空白区域候选点
    # ============================================================

    def _detect_loading_progress(self, img: Image.Image) -> int:
        """检测加载进度（0~100），无法检测返回 -1"""
        # OCR 找百分比数字
        vision = self._get_vision()
        texts = vision.ocr_get_texts(img)
        for t in texts:
            text = t["text"].strip()
            import re
            m = re.search(r"(\d+)\s*%", text)
            if m:
                return int(m.group(1))
            # 也检测纯数字（可能不是百分比格式）
            m2 = re.search(r"^(\d{1,3})$", text)
            if m2:
                val = int(m2.group(1))
                if 0 <= val <= 100:
                    return val
        return -1

    def _calc_blank_candidates(self, popup_rect: List[int],
                               img_w: int, img_h: int) -> List[List[int]]:
        """计算弹窗外的安全空白点击候选点"""
        rules = self._get_rules()
        offsets = rules.get("blank_area_offsets", [])
        px, py, qx, qy = popup_rect  # left, top, right, bottom
        candidates = []

        for name, dx, dy in offsets:
            if name == "left_bottom":
                cx, cy = px + dx, qy + dy
            elif name == "right_bottom":
                cx, cy = qx + dx, qy + dy
            elif name == "top_left":
                cx, cy = px + dx, py + dy
            elif name == "left_side":
                cx, cy = px + dx, py + dy
            elif name == "right_side":
                cx, cy = qx + dx, py + dy
            else:
                continue

            # 确保在图片范围内
            cx = max(2, min(cx, img_w - 2))
            cy = max(2, min(cy, img_h - 2))

            # 确保不在弹窗区域内
            if px < cx < qx and py < cy < qy:
                continue

            candidates.append([int(cx), int(cy)])

        return candidates
