#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行后守卫 - 按 AutoSmoke_自动点击阻塞界面处理实施方案.md 第5.1节

职责：
  - 每步执行后的统一守卫流程
  - 判断是否可以进入下一步
  - 调度 blocker_detector 和 blocker_resolver
  - 控制最大处理次数
  - 输出 guard_result
"""

import logging
import time
import os
from pathlib import Path
from typing import Dict, Optional, List
from PIL import Image

logger = logging.getLogger(__name__)


class PostActionGuard:
    """
    执行后守卫

    在每步执行后检查界面状态，
    如果下一步前置条件不满足，自动检测并处理阻塞。
    """

    def __init__(self, mapper=None, rules=None,
                 max_attempts: int = 3,
                 wait_ms: int = 800):
        """
        :param mapper: CoordinateMapper
        :param rules: BlockerRules
        :param max_attempts: 最大处理尝试次数
        :param wait_ms: 每次动作后等待时间（毫秒）
        """
        self._mapper = mapper
        self._rules = rules
        self.max_attempts = max_attempts
        self.wait_ms = wait_ms
        self._detector = None
        self._resolver = None
        self._checker = None

    def _get_detector(self):
        if self._detector is None:
            from 阻塞处理.blocker_detector import BlockerDetector
            self._detector = BlockerDetector(
                rules=self._rules, mapper=self._mapper)
        return self._detector

    def _get_resolver(self):
        if self._resolver is None:
            from 阻塞处理.blocker_resolver import BlockerResolver
            self._resolver = BlockerResolver(
                mapper=self._mapper, rules=self._rules)
        return self._resolver

    def _get_checker(self):
        if self._checker is None:
            from 阻塞处理.ui_state_checker import UIStateChecker
            self._checker = UIStateChecker(mapper=self._mapper)
        return self._checker

    # ============================================================
    # 守卫流程
    # ============================================================

    def guard_before_next_step(self, next_step: Dict,
                               game_content_img: Image.Image = None,
                               prev_img: Image.Image = None) -> Dict:
        """
        在下一步执行前进行守卫检查

        :param next_step: 解析后的下一步步骤
        :param game_content_img: 当前 gameContent 截图
        :param prev_img: 上一步的截图
        :return: guard_result
        """
        executed_actions = []
        before_screenshots = []
        after_screenshots = []

        for attempt in range(1, self.max_attempts + 1):
            logger.info("守卫检查 第 %d/%d 次", attempt, self.max_attempts)

            # 检查前置条件
            state_check = self._get_checker().check_precondition(
                next_step, game_content_img)
            if state_check["ok"]:
                logger.info("前置条件满足，继续下一步")
                return {
                    "status": "READY",
                    "attempts": attempt,
                    "handled_blockers": executed_actions,
                }

            # 检测阻塞
            blocker = self._get_detector().detect(
                game_content_img, prev_img)
            if not blocker.get("detected"):
                logger.warning("前置条件不满足，但未检测到阻塞: %s",
                             state_check.get("reason"))
                return {
                    "status": "NOT_READY",
                    "attempts": attempt,
                    "reason": state_check.get("reason",
                              "前置条件不满足且未检测到阻塞"),
                    "handled_blockers": executed_actions,
                }

            # 危险阻塞 → 立即阻断
            if blocker.get("dangerous"):
                logger.warning("检测到危险阻塞: %s", blocker.get("keywords"))
                return {
                    "status": "BLOCKED_DANGEROUS_ACTION",
                    "attempts": attempt,
                    "blocker": blocker,
                    "message": f"检测到危险操作: {blocker.get('keywords')}",
                    "handled_blockers": executed_actions,
                }

            # 处理阻塞
            resolver = self._get_resolver()
            resolve_result = resolver.resolve(blocker)
            executed_actions.append({
                "blockerType": blocker.get("blockerType"),
                "action": resolve_result.get("action"),
                "result": "OK" if resolve_result.get("resolved") else "FAIL",
            })

            if resolve_result.get("resolved"):
                # 等待界面稳定
                time.sleep(self.wait_ms / 1000.0)
                # 刷新截图重新检查
                try:
                    from 坐标截图.screenshot_game_content import GameContentScreenshot
                    capturer = GameContentScreenshot(mapper=self._mapper)
                    cap = capturer.capture()
                    game_content_img = cap.get("game_content_image")
                except Exception:
                    pass
                continue
            else:
                return {
                    "status": "BLOCKED_UNRESOLVED",
                    "attempts": attempt,
                    "blocker": blocker,
                    "message": resolve_result.get("message",
                              "阻塞处理失败"),
                    "handled_blockers": executed_actions,
                }

        return {
            "status": "BLOCKED_MAX_ATTEMPTS",
            "attempts": self.max_attempts,
            "message": f"超过最大处理次数 ({self.max_attempts})",
            "handled_blockers": executed_actions,
        }

    # ============================================================
    # 简易检查（不依赖 OCR）
    # ============================================================

    def quick_check(self, game_content_img: Image.Image) -> Dict:
        """
        快速检查当前是否有阻塞（仅截图特征检测，不需要 OCR）

        :param game_content_img: gameContent 截图
        :return: blocker_result
        """
        return self._get_detector().detect(game_content_img)
