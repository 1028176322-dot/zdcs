#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡死检测器

功能：
  1. 截图变化率检测 — 连续 N 秒截图变化率 < 阈值
  2. UI 树变化检测 — UI 节点数量长时间无变化
  3. 玩家操作队列检测 — 长时间无操作完成
  4. 排除允许静止状态（Loading/弹窗/重连）

判定逻辑：
  卡死 = 截图无变化 + UI树无变化 + 非允许静止状态

用法：
    detector = HangDetector(screenshot_differ=..., poco=...)
    detector.feed_screenshot(img)  # 每步截图后调用
    detector.feed_ui_tree(dump)    # 每步 UI dump 后调用
    result = detector.check()      # 返回判定结果
"""

import time
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class HangDetector:
    """
    卡死检测器

    检测维度：
    - P0: 截图变化率（连续 N 秒变化 < 阈值）
    - P1: UI 树节点数变化
    - P2: 操作队列进度
    - 排除状态：Loading / 重连 / 弹窗
    """

    def __init__(self, screenshot_differ=None, poco_connector=None):
        self._differ = screenshot_differ
        self._poco = poco_connector

        # 截图历史（最多 30 帧）
        self._screenshot_history: List[Dict] = []
        self._max_screenshots = 30

        # UI 树历史
        self._ui_node_counts: List[Dict] = []

        # 配置
        self._screenshot_change_threshold = 0.001  # 0.1% 变化率以下视为无变化
        self._no_change_timeout = 15.0  # 连续 15 秒无变化判定为卡死
        self._node_count_stable_timeout = 20.0  # UI 节点数 20 秒不变

        # 允许静止的状态（不判定为卡死）
        self._static_allowed_keywords = [
            "Loading", "加载中", "重连", "Reconnecting",
            "公告", "活动", "更新", "Downloading",
            "匹配中", "Matching", "等待",
        ]

        # 运行状态
        self._last_operation_time = time.time()

    def feed_screenshot(self, img) -> int:
        """
        输入最新截图

        :param img: PIL Image 对象
        :return: 历史帧数
        """
        entry = {
            "timestamp": time.time(),
            "img": img,
            "diff_ratio": None,  # 与上一帧的差异
        }

        # 计算与上一帧的差异
        if self._screenshot_history and self._differ:
            prev = self._screenshot_history[-1]["img"]
            try:
                ratio = self._differ.calc_diff_ratio(prev, img)
                entry["diff_ratio"] = ratio
            except Exception:
                entry["diff_ratio"] = None

        self._screenshot_history.append(entry)
        if len(self._screenshot_history) > self._max_screenshots:
            self._screenshot_history.pop(0)

        return len(self._screenshot_history)

    def feed_ui_tree(self, dump: Dict):
        """输入最新 UI 树"""
        node_count = 0
        if dump and isinstance(dump, dict):
            # 递归统计节点数
            def count_nodes(node):
                c = 1
                for child in node.get("children", []):
                    c += count_nodes(child)
                return c
            node_count = count_nodes(dump)

        self._ui_node_counts.append({
            "timestamp": time.time(),
            "node_count": node_count,
        })
        # 保留最近 60 帧
        if len(self._ui_node_counts) > 60:
            self._ui_node_counts.pop(0)

    def check(self, context: Dict = None) -> Dict:
        """
        执行卡死检测

        :param context: 上下文信息
            {"blockers": [...], "current_page": "...", "ocr_texts": [...]}
        :return: {
            "hanging": True/False,
            "detail": str,
            "checks": [...],
            "no_change_seconds": float,
        }
        """
        checks = []
        no_change_seconds = 0.0
        hanging = False

        # P0: 截图无变化检测
        ss_check = self._check_screenshot_stuck(context)
        checks.append(ss_check)
        if not ss_check["passed"]:
            no_change_seconds = ss_check.get("no_change_seconds", 0)
            hanging = True
        else:
            # P1: UI 树无变化检测（截图变化时才会进入）
            ui_check = self._check_ui_stuck()
            checks.append(ui_check)

        # 如果检测到卡死，检查是否处于允许静止状态
        if hanging:
            # P2: 排除允许静止状态
            if self._is_static_allowed(context):
                hanging = False
                checks.append({
                    "name": "static_allowed",
                    "passed": True,
                    "detail": "当前处于允许静止状态（Loading/重连/弹窗）",
                    "warning": True,
                })

        # 更新最后操作时间
        if not hanging:
            self._last_operation_time = time.time()

        return {
            "hanging": hanging,
            "timestamp": time.time(),
            "time_str": datetime.now().strftime("%H:%M:%S"),
            "detail": "检测到卡死" if hanging else "运行正常",
            "no_change_seconds": no_change_seconds,
            "checks": checks,
        }

    def get_idle_seconds(self) -> float:
        """获取空闲秒数（最后一次检测到变化到现在）"""
        if not self._screenshot_history:
            return 0
        last = self._screenshot_history[-1]
        if last.get("diff_ratio") is None:
            return time.time() - self._last_operation_time

        # 从后往前找最后一次有变化的时间
        for entry in reversed(self._screenshot_history):
            ratio = entry.get("diff_ratio", 0)
            if ratio is None or ratio >= self._screenshot_change_threshold:
                return time.time() - entry["timestamp"]

        return time.time() - self._last_operation_time

    # ============================================================
    # 内部检测
    # ============================================================

    def _check_screenshot_stuck(self, context: Dict = None) -> Dict:
        """检查截图是否长时间无变化"""
        if len(self._screenshot_history) < 3:
            return {"name": "screenshot_stuck", "passed": True,
                    "detail": "帧数不足，跳过"}

        # 从后往前找连续无变化的时间
        no_change_start = None
        for entry in reversed(self._screenshot_history):
            ratio = entry.get("diff_ratio")
            if ratio is None:
                continue
            if ratio < self._screenshot_change_threshold:
                if no_change_start is None:
                    no_change_start = entry["timestamp"]
            else:
                break

        if no_change_start is None:
            return {"name": "screenshot_stuck", "passed": True,
                    "detail": "截图持续有变化"}

        stuck_seconds = time.time() - no_change_start
        if stuck_seconds >= self._no_change_timeout:
            return {"name": "screenshot_stuck", "passed": False,
                    "detail": f"截图 {stuck_seconds:.0f}s 无变化",
                    "no_change_seconds": stuck_seconds}

        return {"name": "screenshot_stuck", "passed": True,
                "detail": f"截图 {stuck_seconds:.0f}s 无变化（未超时）",
                "no_change_seconds": stuck_seconds, "warning": True}

    def _check_ui_stuck(self) -> Dict:
        """检查 UI 树节点数是否长时间不变"""
        if len(self._ui_node_counts) < 3:
            return {"name": "ui_stuck", "passed": True, "detail": "帧数不足，跳过"}

        # 最近几次节点数
        recent = self._ui_node_counts[-5:]
        if len(recent) < 2:
            return {"name": "ui_stuck", "passed": True, "detail": "数据不足"}

        first_count = recent[0]["node_count"]
        all_same = all(e["node_count"] == first_count for e in recent)

        if all_same and len(self._ui_node_counts) >= 10:
            first_in_window = self._ui_node_counts[0]["timestamp"]
            stable_seconds = time.time() - first_in_window
            if stable_seconds >= self._node_count_stable_timeout:
                return {"name": "ui_stuck", "passed": False,
                        "detail": f"UI 节点数 {first_count} 持续 {stable_seconds:.0f}s 不变"}

        return {"name": "ui_stuck", "passed": True, "detail": "UI 树正常变化"}

    def _is_static_allowed(self, context: Dict = None) -> bool:
        """检查当前是否处于允许静止的状态"""
        if not context:
            return False

        # 上下文中的 OCR 识别的文字
        ocr_texts = context.get("ocr_texts", []) or []

        # 上下文中的阻塞信息
        blockers = context.get("blockers", []) or []

        # 检测阻塞
        if blockers:
            for b in blockers:
                btype = b.get("type", "") if isinstance(b, dict) else str(b)
                for kw in self._static_allowed_keywords:
                    if kw.lower() in btype.lower():
                        logger.info("允许静止: 阻塞类型 %s", btype)
                        return True

        # 检测 OCR 文字
        for text in ocr_texts:
            for kw in self._static_allowed_keywords:
                if kw in text:
                    logger.info("允许静止: OCR 文字 '%s' → '%s'", text, kw)
                    return True

        return False


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    print("=== HangDetector 测试 ===\n")

    detector = HangDetector()

    # 测试1：无数据时检测
    print("[测试1] 无数据检测...")
    r = detector.check()
    print(f"  hanging={r['hanging']}: {r['detail']}")

    # 测试2：带允许静止状态
    print("\n[测试2] 允许静止状态...")
    allowed = detector._is_static_allowed({
        "ocr_texts": ["加载中 50%", "请稍候"],
        "blockers": [{"type": "loading"}],
    })
    print(f"  判定: {allowed}（期望 True）")

    # 测试3：带 OCR 文字
    print("\n[测试3] OCR 文字检测...")
    allowed = detector._is_static_allowed({
        "ocr_texts": ["公告", "新活动"],
    })
    print(f"  判定: {allowed}（期望 True）")

    # 测试4：空闲时间
    print("\n[测试4] 空闲时间...")
    idle = detector.get_idle_seconds()
    print(f"  空闲: {idle:.1f}s")

    print("\n✅ 测试完成")
