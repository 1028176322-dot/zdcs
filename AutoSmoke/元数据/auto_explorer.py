#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSmoke 自动探索引擎（UI树方案 阶段六/七）

功能：
  1. 获取当前页面可点击元素 → 逐个点击 → 记录页面变化
  2. 图标 Tips 探索：点击图标 → 等待 Tips → 记录关系
  3. 页面关系图自动构建
  4. 用例驱动采集钩子

用法：
    explorer = AutoExplorer()
    explorer.run(max_clicks=10)        # 自动探索
    explorer.explore_icons()           # 图标探索
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

AUTOSMOKE_ROOT = Path(__file__).resolve().parent.parent
META_DIR = AUTOSMOKE_ROOT / "元数据"

# 导入页面关系图
from 元数据.page_graph import PageGraph
from 元数据.merged_ui_tree import load_json


class AutoExplorer:
    """
    自动探索引擎

    依赖：
      - PageGraph 用于记录页面关系
      - UnityInjectClick 用于点击
      - CoordinatorMapper 用于坐标
    """

    def __init__(self, click_handler=None, mapper=None, poco=None):
        self._click_handler = click_handler
        self._mapper = mapper
        self._poco = poco
        self._graph = PageGraph()
        self._graph.load()

        # 探索配置
        self._max_clicks_per_page = 20
        self._page_change_timeout = 3.0  # 等待页面变化超时
        self._post_click_delay = 0.5     # 点击后等待

        # 已探索的元素路径（避免重复点击）
        self._explored_elements: set = set()

        # 探索结果
        self._icon_interactions: List[Dict] = []

    def run(self, max_clicks: int = 30):
        """
        执行自动探索（阶段六）

        :param max_clicks: 最大点击次数
        """
        logger.info("自动探索启动 (max_clicks=%d)", max_clicks)
        current_page = self._detect_current_page()
        logger.info("起始页面: %s", current_page)

        clicks_done = 0
        while clicks_done < max_clicks:
            # 1. 获取当前页面可点击元素
            elements = self._get_clickable_elements()
            if not elements:
                logger.info("无可点击元素，探索结束")
                break

            # 2. 找到下一个未探索的元素
            target = None
            for e in elements:
                path = e.get("path", "")
                if path not in self._explored_elements:
                    target = e
                    break

            if target is None:
                logger.info("当前页面所有元素已探索")
                break

            # 3. 记录并执行点击
            path = target.get("path", "")
            self._explored_elements.add(path)
            name = target.get("name", "")
            text = target.get("text", "")
            logger.info("[%d/%d] 探索: %s (%s)", clicks_done + 1, max_clicks, path, text or name)

            # 获取坐标并点击
            success = self._click_element(target)
            if not success:
                logger.warning("点击失败，跳过: %s", path)
                continue

            time.sleep(self._post_click_delay)

            # 4. 检测页面变化
            new_page = self._detect_current_page()
            if new_page and new_page != current_page:
                logger.info("页面变化: %s → %s (通过 %s)", current_page, new_page, name)
                self._graph.record(current_page, "click", name, new_page)

                # 如果新页面有可点击元素，递归探索
                sub_elements = self._get_clickable_elements()
                if sub_elements and len(sub_elements) <= self._max_clicks_per_page:
                    # 记录子页面关系
                    self._graph.record(new_page, "auto_discover", "back", current_page)

                current_page = new_page
            else:
                logger.debug("页面无变化: %s", current_page)

            clicks_done += 1

        # 保存结果
        self._graph.save()
        self._graph.save_html()
        logger.info("自动探索完成: %d 次点击, %d 个页面",
                    clicks_done, len(self._graph.get_page_list()))
        return self._graph.stats()

    def explore_icons(self, max_icons: int = 20):
        """
        图标 Tips 探索（阶段七）

        :param max_icons: 最大图标探索数
        """
        logger.info("图标 Tips 探索启动 (max_icons=%d)", max_icons)

        # 从增强 UI 树或运行态中获取图标
        icons = self._get_icon_elements()
        if not icons:
            logger.info("无可探索图标")
            return []

        explored = 0
        for icon in icons:
            if explored >= max_icons:
                break

            path = icon.get("path", "")
            if path in self._explored_elements:
                continue

            sprite_name = icon.get("spriteName", "")
            node_name = icon.get("name", "")
            clickable = icon.get("clickable", False)
            if not clickable:
                continue

            logger.info("[图标 %d/%d] %s sprite=%s",
                       explored + 1, max_icons, path, sprite_name)

            # 记录点击前页面
            before_page = self._detect_current_page()

            success = self._click_element(icon)
            if not success:
                continue

            time.sleep(0.8)  # 等待 Tips 弹出

            # 检测是否出现了 Tips
            after_page = self._detect_current_page()
            is_tips = self._detect_tips()

            interaction = {
                "iconPath": path,
                "spriteName": sprite_name,
                "nodeName": node_name,
                "beforePage": before_page,
                "afterPage": after_page if after_page != before_page else before_page,
                "clickable": clickable,
                "triggeredTips": is_tips,
                "openTipsName": after_page if is_tips else "",
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            }
            self._icon_interactions.append(interaction)

            if is_tips:
                logger.info("  → 触发 Tips: %s", after_page)
                self._graph.record(before_page, "click_icon", sprite_name, after_page)
                # 关闭 Tips（点击空白或关闭按钮）
                self._close_tips()
            else:
                logger.info("  → 未触发 Tips")

            self._explored_elements.add(path)
            explored += 1

        # 保存图标交互映射
        self._save_icon_interactions()
        self._graph.save()

        logger.info("图标探索完成: %d 个图标, %d 个触发 Tips",
                    len(self._icon_interactions),
                    sum(1 for i in self._icon_interactions if i["triggeredTips"]))
        return self._icon_interactions

    # ============================================================
    # 用例驱动采集钩子
    # ============================================================

    def on_step_complete(self, step_result: Dict, page_before: str = None):
        """
        用例步骤完成后的回调（用例驱动采集）

        检测页面变化 → 自动导出 UI 树
        """
        if page_before is None:
            return

        page_after = self._detect_current_page()
        if page_after and page_after != page_before:
            logger.info("页面变化检测: %s → %s → 自动导出 UI 树", page_before, page_after)
            self._graph.record(page_before, "step", step_result.get("action", "?"), page_after)

            # 触发增强 UI 树导出
            try:
                from 元数据.merged_ui_tree import run as merge_run
                merge_run()
            except Exception as e:
                logger.debug("增强导出失败（不阻塞）: %s", e)

    # ============================================================
    # 内部方法
    # ============================================================

    def _detect_current_page(self) -> str:
        """检测当前页面 ID"""
        try:
            if self._poco:
                dump = self._poco.dump()
                if dump:
                    for node in dump.get("children", []):
                        name = node.get("name", "")
                        if "Panel" in name or "Popup" in name or "Dialog" in name:
                            return name
            # 从元数据读取
            state = load_json("current_state.json")
            if state:
                return state.get("pageId", state.get("scene", "Unknown"))
        except Exception:
            pass
        return "Unknown"

    def _get_clickable_elements(self) -> List[Dict]:
        """获取当前页面可点击元素"""
        # 优先使用增强 UI 树
        enhanced = load_json("enhanced_ui_tree.json")
        if enhanced:
            return [n for n in enhanced.get("nodes", []) if n.get("clickable")]

        # 回退到运行态 UI 树
        runtime = load_json("current_ui_tree.json")
        if runtime:
            return [n for n in runtime.get("nodes", []) if n.get("clickable")]

        # 回退到元数据
        ui = load_json("current_ui.json")
        if ui:
            return [n for n in ui.get("elements", []) if n.get("clickable")]

        return []

    def _get_icon_elements(self) -> List[Dict]:
        """获取图标元素"""
        # 优先从运行态 UI 树获取
        runtime = load_json("current_ui_tree.json")
        if runtime and runtime.get("icons"):
            return runtime["icons"]

        # 从元数据获取含 spriteName 的元素
        ui = load_json("current_ui.json")
        if ui:
            return [e for e in ui.get("elements", []) if e.get("spriteName")]

        return []

    def _click_element(self, element: Dict) -> bool:
        """点击元素"""
        try:
            if self._click_handler:
                # 使用 Unity Inject Click
                if element.get("screenRect"):
                    sr = element["screenRect"]
                    # 支持 {x,y,width,height} 或 [x,y,right,bottom]
                    if isinstance(sr, dict):
                        cx = sr["x"] + sr["width"] / 2
                        cy = sr["y"] + sr["height"] / 2
                    else:
                        cx = (sr[0] + sr[2]) / 2
                        cy = (sr[1] + sr[3]) / 2

                    target_info = {
                        "type": element.get("testId", "coordinate"),
                        "value": element.get("testId", "%d,%d" % (cx, cy)),
                    }
                    result = self._click_handler.click(
                        cx, cy, "design", target_info=target_info,
                        description="auto_explore",
                    )
                    return result.get("result") in ("CLICK_OK", "CLICK_CHANGED")

            # 降级：直接使用 Poco
            if self._poco:
                path = element.get("path", "")
                self._poco(path).click()
                return True

        except Exception as e:
            logger.debug("点击失败: %s", e)
        return False

    def _detect_tips(self) -> bool:
        """检测当前是否出现了 Tips 弹窗"""
        page = self._detect_current_page()
        if not page:
            return False
        tips_keywords = ["Tips", "Tip", "详情", "说明", "Hint"]
        return any(kw in page for kw in tips_keywords)

    def _close_tips(self):
        """关闭 Tips 弹窗"""
        try:
            # 尝试点击空白位置关闭 Tips
            if self._click_handler:
                self._click_handler.click(585, 2300, "design")
                time.sleep(0.3)
        except Exception:
            pass

    def _save_icon_interactions(self):
        """保存图标交互映射"""
        path = os.path.join(META_DIR, "icon_interaction_map.json")
        output = {
            "exportTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "totalIcons": len(self._icon_interactions),
            "interactions": self._icon_interactions,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        logger.info("图标交互映射已保存: %s (%d 条)", path, len(self._icon_interactions))
