#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阻塞处理器 - 按 AutoSmoke_自动点击阻塞界面处理实施方案.md 第5.3节

职责：
  - 根据阻塞类型选择安全动作
  - 执行关闭、取消、返回、等待、点击空白等动作
  - 处理危险阻塞时直接阻断
  - 验证阻塞是否已解除
"""

import logging
import time
from typing import Dict, Optional, List
from PIL import Image

logger = logging.getLogger(__name__)


class BlockerResolver:
    """
    阻塞处理器

    根据 blocker_result 执行安全关闭操作。
    """

    def __init__(self, mapper=None, rules=None):
        self._mapper = mapper
        self._rules = rules

    def _get_mapper(self):
        if self._mapper is None:
            from 坐标截图.coordinate_mapper import CoordinateMapper
            self._mapper = CoordinateMapper.from_config()
        return self._mapper

    def _get_rules(self):
        if self._rules is None:
            from 阻塞处理.blocker_rules import BlockerRules
            self._rules = BlockerRules()
        return self._rules

    # ============================================================
    # 主入口
    # ============================================================

    def resolve(self, blocker: Dict) -> Dict:
        """
        尝试解决阻塞

        :param blocker: blocker_detector 的输出
        :return: {"resolved": True/False, "action": "...", "message": "..."}
        """
        if not blocker.get("detected"):
            return {"resolved": True, "action": "none",
                    "message": "无阻塞需要处理"}

        blocker_type = blocker.get("blockerType", "unknown")
        actions = blocker.get("suggestedActions", ["wait"])
        forbidden = blocker.get("forbiddenActions", [])

        logger.info("处理阻塞: type=%s, suggested=%s", blocker_type, actions)

        for action in actions:
            if action in forbidden:
                logger.info("跳过禁止动作: %s (blockerType=%s)",
                          action, blocker_type)
                continue

            result = self._execute_action(action, blocker)
            if result.get("resolved"):
                return result

            # 动作完成后等待稳定
            time.sleep(0.3)

        return {"resolved": False, "action": "none",
                "message": f"所有动作均未能解决阻塞 ({blocker_type})",
                "blockerType": blocker_type}

    # ============================================================
    # 动作执行
    # ============================================================

    def _execute_action(self, action: str, blocker: Dict) -> Dict:
        """执行单个处理动作"""
        mapper = self._get_mapper()

        if action == "click_close":
            return self._click_close(blocker)

        elif action == "click_cancel":
            return self._click_text(blocker, "取消")

        elif action == "click_reward_confirm":
            return self._click_text(blocker, "确认")

        elif action == "click_outside_blank_area":
            return self._click_outside_blank(blocker)

        elif action == "click_skip":
            return self._click_text(blocker, "跳过")

        elif action == "click_guide_target":
            return self._click_guide_target(blocker)

        elif action == "click_retry":
            return self._click_text(blocker, "重试")

        elif action == "press_back":
            return self._press_back()

        elif action in ("wait", "click_close_if_timeout",
                        "wait_manual", "detect_again"):
            logger.info("动作 %s 需要等待或手动处理，跳过执行", action)
            return {"resolved": False, "action": action,
                    "message": f"动作 {action} 需要外部处理"}

        elif action == "wait_until_progress_complete":
            return self._wait_scene_loading(blocker)

        else:
            logger.warning("未知阻塞处理动作: %s", action)
            return {"resolved": False, "action": action,
                    "message": f"未知动作: {action}"}

    # ============================================================
    # 具体动作实现
    # ============================================================

    def _click_close(self, blocker: Dict) -> Dict:
        """点击关闭按钮"""
        return self._click_text(blocker, "关闭", alt_texts=["X", "×", "close"])

    def _click_text(self, blocker: Dict, target_text: str,
                    alt_texts: List[str] = None) -> Dict:
        """点击包含指定文字的按钮"""
        mapper = self._get_mapper()
        from 点击执行.click_game_content import ClickExecutor
        executor = ClickExecutor(mapper=mapper)

        # 通过 OCR 找文字
        from 视觉识别.game_content_vision import GameContentVision
        vision = GameContentVision()

        # 截取当前画面
        capturer = None
        try:
            from 坐标截图.screenshot_game_content import GameContentScreenshot
            capturer = GameContentScreenshot(mapper=mapper)
            cap = capturer.capture()
            img = cap.get("game_content_image")
        except Exception:
            img = None

        if img is None:
            return {"resolved": False, "action": f"click_{target_text}",
                    "message": "无法获取截图"}

        # 先找目标文字，再找备选文字
        texts_to_try = [target_text] + (alt_texts or [])
        for text in texts_to_try:
            result = vision.ocr_find_text_click(img, text)
            if result:
                click_result = executor.click_content(
                    result["x"], result["y"],
                    description=f"阻塞处理: 点击{text}"
                )
                if click_result.get("result") not in ("CLICK_BLOCKED", "CLICK_ERROR"):
                    logger.info("✅ 阻塞处理成功: 点击 '%s'", text)
                    return {"resolved": True, "action": f"click_{text}",
                            "message": f"已点击: {text}"}
                else:
                    logger.warning("点击 '%s' 被阻断: %s",
                                 text, click_result.get("error"))

        return {"resolved": False, "action": f"click_{target_text}",
                "message": f"未找到按钮: {target_text}"}

    def _click_outside_blank(self, blocker: Dict) -> Dict:
        """点击弹窗外的安全空白区域"""
        candidates = blocker.get("outsideBlankCandidates", [])
        if not candidates:
            return {"resolved": False, "action": "click_outside_blank",
                    "message": "无空白候选点"}

        mapper = self._get_mapper()
        from 点击执行.click_game_content import ClickExecutor
        executor = ClickExecutor(mapper=mapper)

        for point in candidates:
            cx, cy = point
            click_result = executor.click_content(
                cx, cy,
                description=f"阻塞处理: 点击空白区域({cx},{cy})"
            )
            if click_result.get("result") not in ("CLICK_BLOCKED", "CLICK_ERROR"):
                logger.info("✅ 空白区域点击成功: (%d, %d)", cx, cy)
                return {"resolved": True, "action": "click_outside_blank_area",
                        "point": point,
                        "message": f"空白区域点击: ({cx},{cy})"}

        return {"resolved": False, "action": "click_outside_blank",
                "message": "所有空白候选点均无效"}

    def _click_guide_target(self, blocker: Dict) -> Dict:
        """点击引导目标区域"""
        target = blocker.get("guideTarget", {})
        if not target:
            return {"resolved": False, "action": "click_guide_target",
                    "message": "无引导目标"}

        center = target.get("center")
        if center:
            mapper = self._get_mapper()
            from 点击执行.click_game_content import ClickExecutor
            executor = ClickExecutor(mapper=mapper)
            click_result = executor.click_content(
                center[0], center[1],
                description="阻塞处理: 点击引导目标"
            )
            if click_result.get("result") not in ("CLICK_BLOCKED", "CLICK_ERROR"):
                return {"resolved": True, "action": "click_guide_target",
                        "point": center,
                        "message": f"已点击引导目标: {center}"}

        return {"resolved": False, "action": "click_guide_target",
                "message": "引导目标点击失败"}

    def _press_back(self) -> Dict:
        """模拟返回键"""
        import win32api
        import win32con
        try:
            win32api.keybd_event(0x1B, 0, 0, 0)  # ESC
            time.sleep(0.05)
            win32api.keybd_event(0x1B, 0, win32con.KEYEVENTF_KEYUP, 0)
            logger.info("已发送 ESC 返回")
            return {"resolved": True, "action": "press_back",
                    "message": "已发送 ESC"}
        except Exception as e:
            logger.warning("发送 ESC 失败: %s", e)
            return {"resolved": False, "action": "press_back",
                    "message": str(e)}

    def _wait_scene_loading(self, blocker: Dict) -> Dict:
        """等待场景加载完成，不会点击任何按钮或空白区域"""
        max_wait = blocker.get("maxWaitMs", 30000) / 1000.0
        stuck_threshold = blocker.get("stuckThresholdMs", 10000) / 1000.0
        progress_start = blocker.get("progress", -1)

        logger.info("等待场景加载完成 (max=%.1fs, stuck=%.1fs, progress=%d%%)",
                   max_wait, stuck_threshold, progress_start)

        start = time.time()
        last_change = time.time()
        prev_img = None
        last_progress = progress_start

        from 坐标截图.screenshot_game_content import GameContentScreenshot
        capturer = GameContentScreenshot(mapper=self._get_mapper())
        from 坐标截图.screenshot_diff import ScreenshotDiffer
        differ = ScreenshotDiffer()

        while time.time() - start < max_wait:
            time.sleep(1.0)

            try:
                cap = capturer.capture()
                current_img = cap.get("game_content_image")
            except Exception:
                continue

            # 检测进度（如果有 OCR）
            from 阻塞处理.blocker_detector import BlockerDetector
            detector = BlockerDetector()
            new_progress = detector._detect_loading_progress(current_img)

            if new_progress >= 0:
                logger.info("加载进度: %d%%", new_progress)
                if new_progress == 100 or new_progress > last_progress:
                    last_change = time.time()
                last_progress = new_progress

            # 用截图差异判断是否仍在变化
            if prev_img is not None and current_img is not None:
                ratio = differ.calc_diff_ratio(prev_img, current_img)
                if ratio > 0.01:
                    last_change = time.time()

            prev_img = current_img

            # 用 BlockerDetector 重新检测，看加载是否消失
            blocker_check = detector.detect(current_img)
            bt = blocker_check.get("blockerType", "")
            if not blocker_check.get("detected") or bt != "scene_transition_loading":
                elapsed = time.time() - start
                logger.info("场景加载完成 (%.1fs) progress=%d%%",
                          elapsed, last_progress)
                return {
                    "resolved": True, "action": "wait_until_progress_complete",
                    "message": f"场景加载完成 ({elapsed:.1f}s)",
                    "progressEnd": last_progress,
                    "waitMs": int(elapsed * 1000),
                }

            # 检测卡住
            stuck_time = time.time() - last_change
            if stuck_time > stuck_threshold and last_progress >= 0:
                logger.warning("场景加载可能卡住 (%.1fs, progress=%d%%)",
                            stuck_time, last_progress)
                # 不是100%但不一定是卡住，继续等待直到超时

        elapsed = time.time() - start
        if last_progress >= 0 and last_progress < 100:
            logger.error("场景加载超时 (%.1fs, progress=%d%%)",
                       elapsed, last_progress)
            return {
                "resolved": False, "action": "wait_until_progress_complete",
                "message": f"场景加载超时 ({elapsed:.1f}s, progress={last_progress}%)",
                "progressEnd": last_progress,
                "waitMs": int(elapsed * 1000),
            }

        logger.info("场景加载超时但已结束 (%.1fs)", elapsed)
        return {
            "resolved": True, "action": "wait_until_progress_complete",
            "message": f"场景加载结束 ({elapsed:.1f}s)",
            "waitMs": int(elapsed * 1000),
        }
