#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阻塞规则配置 - 按 AutoSmoke_自动点击阻塞界面处理实施方案.md 第5.5节

维护：
  - 阻塞类型规则
  - 危险关键词
  - 安全关闭动作优先级
  - 弹窗外空白区域配置
  - 不同项目的自定义规则
"""

from typing import Dict, List, Optional

# ============================================================
# 默认配置
# ============================================================

DEFAULT_RULES = {
    "danger_keywords": [
        "充值", "购买", "钻石", "支付", "删除", "解散",
        "退出登录", "重置账号", "消耗", "确认支付",
    ],
    "safe_close_keywords": [
        "关闭", "取消", "返回", "稍后", "忽略", "跳过",
    ],
    "popup_keywords": [
        "确定", "取消", "关闭",
    ],
    "reward_keywords": [
        "恭喜获得", "获得", "奖励", "领取", "领取成功",
    ],
    "reward_confirm_keywords": [
        "确认", "领取",
    ],
    "loading_keywords": [
        "加载中", "Loading", "请稍候", "请稍后",
    ],
    "scene_loading_keywords": [
        "%", "加载中", "Loading",
    ],
    "reconnect_keywords": [
        "正在重连", "重新连接", "网络异常", "重试", "正在连接",
    ],
    "guide_keywords": [
        "下一步", "跳过", "点击这里", "我知道了",
    ],
    "announcement_keywords": [
        "公告", "活动", "更新", "今日提示",
    ],
    "blank_area_offsets": [
        ("left_bottom", 20, 10),
        ("right_bottom", -20, 10),
        ("top_left", 20, -10),
        ("left_side", -10, 20),
        ("right_side", 10, 20),
    ],
    "safe_area_blacklist": [
        "bottom_action_bar", "debug_button", "back_button", "danger_buttons",
    ],
    "max_attempts": 3,
    "wait_after_action_ms": 800,
    "blocker_timeout_ms": 10000,
    "loading_wait_interval_ms": 1000,
    "scene_loading_max_wait_ms": 30000,
    "scene_loading_stuck_threshold_ms": 10000,
    "reconnect_max_wait_ms": 10000,
    "guide_max_steps": 5,
}


class BlockerRules:
    """阻塞规则管理器"""

    def __init__(self, custom_rules: Dict = None):
        self._rules = DEFAULT_RULES.copy()
        if custom_rules:
            self._merge(custom_rules)

    def _merge(self, custom: Dict):
        """合并自定义规则"""
        for k, v in custom.items():
            if k in self._rules and isinstance(self._rules[k], list) and isinstance(v, list):
                self._rules[k] = list(set(self._rules[k] + v))
            elif k in self._rules and isinstance(self._rules[k], dict) and isinstance(v, dict):
                self._rules[k].update(v)
            else:
                self._rules[k] = v

    def get(self, key: str, default=None):
        return self._rules.get(key, default)

    # ============================================================
    # 关键词匹配
    # ============================================================

    def is_dangerous(self, text: str) -> bool:
        """是否包含危险关键词"""
        text_lower = text.lower()
        for kw in self._rules["danger_keywords"]:
            if kw.lower() in text_lower:
                return True
        return False

    def is_safe_close(self, text: str) -> bool:
        """是否是安全关闭关键词"""
        text_lower = text.lower()
        for kw in self._rules["safe_close_keywords"]:
            if kw.lower() in text_lower:
                return True
        return False

    def is_popup_related(self, text: str) -> bool:
        """是否是弹窗相关关键词"""
        text_lower = text.lower()
        for kw in self._rules["popup_keywords"]:
            if kw.lower() in text_lower:
                return True
        return False

    def is_reward_related(self, text: str) -> bool:
        """是否是奖励弹窗关键词"""
        text_lower = text.lower()
        for kw in self._rules["reward_keywords"]:
            if kw.lower() in text_lower:
                return True
        return False

    def is_loading_related(self, text: str) -> bool:
        """是否是 Loading 关键词"""
        text_lower = text.lower()
        for kw in self._rules["loading_keywords"]:
            if kw.lower() in text_lower:
                return True
        return False

    def is_scene_loading_related(self, texts: list) -> bool:
        """文本列表中是否有场景加载关键词"""
        for t in texts:
            for kw in self._rules.get("scene_loading_keywords", ["%", "加载"]):
                if kw.lower() in t.lower():
                    return True
        return False

    def is_reconnect_related(self, text: str) -> bool:
        """是否是重连关键词"""
        text_lower = text.lower()
        for kw in self._rules["reconnect_keywords"]:
            if kw.lower() in text_lower:
                return True
        return False

    def is_guide_related(self, text: str) -> bool:
        """是否是引导关键词"""
        text_lower = text.lower()
        for kw in self._rules["guide_keywords"]:
            if kw.lower() in text_lower:
                return True
        return False

    def is_announcement_related(self, text: str) -> bool:
        """是否是公告关键词"""
        text_lower = text.lower()
        for kw in self._rules["announcement_keywords"]:
            if kw.lower() in text_lower:
                return True
        return False

    def has_dangerous_confirm(self, texts: List[str]) -> bool:
        """文本列表中是否存在危险确认弹窗"""
        has_danger = any(self.is_dangerous(t) for t in texts)
        has_confirm = any(kw in t for t in texts for kw in ["确定", "确认", "购买"])
        return has_danger and has_confirm

    def classify_texts(self, texts: List[str]) -> Dict:
        """
        对文本列表进行分类

        :return: {"dangerous": [...], "popup": [...], "loading": [...], ...}
        """
        result = {
            "dangerous": [],
            "popup": [],
            "safe_close": [],
            "reward": [],
            "loading": [],
            "reconnect": [],
            "guide": [],
            "announcement": [],
        }
        for t in texts:
            if self.is_dangerous(t):
                result["dangerous"].append(t)
            if self.is_popup_related(t):
                result["popup"].append(t)
            if self.is_safe_close(t):
                result["safe_close"].append(t)
            if self.is_reward_related(t):
                result["reward"].append(t)
            if self.is_loading_related(t):
                result["loading"].append(t)
            if self.is_reconnect_related(t):
                result["reconnect"].append(t)
            if self.is_guide_related(t):
                result["guide"].append(t)
            if self.is_announcement_related(t):
                result["announcement"].append(t)
        return result

    # ============================================================
    # 动作优先级
    # ============================================================

    def get_resolve_priority(self, blocker_type: str) -> List[str]:
        """获取指定阻塞类型的处理动作优先级"""
        priorities = {
            "popup": ["click_close", "click_cancel",
                      "click_outside_blank_area", "press_back"],
            "modal_popup": ["click_close", "click_cancel",
                            "click_outside_blank_area", "press_back"],
            "reward_popup": ["click_reward_confirm",
                             "click_outside_blank_area", "press_back"],
            "dangerous_confirm": ["click_cancel", "click_close"],
            "loading": ["wait"],
            "scene_transition_loading": ["wait_until_progress_complete"],
            "reconnect_loading": ["wait", "click_retry",
                                  "click_close_if_timeout"],
            "guide_overlay": ["click_skip", "click_guide_target",
                              "wait_manual"],
            "announcement": ["click_close", "press_back"],
            "network": ["click_retry", "wait"],
        }
        return priorities.get(blocker_type, ["wait"])

    def get_forbidden_actions(self, blocker_type: str) -> List[str]:
        """获取指定阻塞类型的禁止动作"""
        forbidden = {
            "dangerous_confirm": ["click_confirm", "click_outside_blank_area"],
            "scene_transition_loading": ["click_close", "click_cancel",
                                          "click_outside_blank_area",
                                          "press_back"],
            "guide_overlay": ["click_outside_blank_area", "click_random_area"],
            "reconnect_loading": ["click_random_area"],
        }
        return forbidden.get(blocker_type, [])

    def is_action_forbidden(self, blocker_type: str, action: str) -> bool:
        """判断动作是否被禁止"""
        return action in self.get_forbidden_actions(blocker_type)
