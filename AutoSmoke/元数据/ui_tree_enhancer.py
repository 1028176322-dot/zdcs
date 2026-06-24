# -*- coding: utf-8 -*-
"""
ui_tree_enhancer.py — 工程态 UI 树增强模块

职责：
    读取 project_ui_inventory.json
    → 展开 prefabs.nodes
    → 过滤明显无用节点
    → 识别按钮/页签/图标/弹窗/入口/道具格子
    → 推断 pageId / elementType / role
    → 生成 displayName / chineseDescription
    → 生成 clickTargetNode / visualNode
    → 计算 confidence / priority
    → 输出 enhanced_ui_tree.json

输入：
    project_ui_inventory.json（必需）
    current_ui_tree.json（可选，阶段二）
    pages/*.json（可选，阶段二）

输出：
    enhanced_ui_tree.json

使用方式：
    from 元数据.ui_tree_enhancer import UITreeEnhancer
    enhancer = UITreeEnhancer(source_dir="元数据")
    result = enhancer.run()
"""

import json
import os
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


# ============================================================
# 常量 / 规则表
# ============================================================

# 页面中文名表
PAGE_NAME_MAP: Dict[str, str] = {}

# 元素类型推断表
ELEMENT_TYPE_RULES = [
    (lambda n, t, sp, cl: cl and "Button" in t, "button"),
    (lambda n, t, sp, cl: "Toggle" in t, "tab"),
    (lambda n, t, sp, cl: "Slider" in t, "slider"),
    (lambda n, t, sp, cl: "InputField" in t, "input_field"),
    (lambda n, t, sp, cl: "Dropdown" in t, "dropdown"),
    (lambda n, t, sp, cl: "Scrollbar" in t, "scrollbar"),
    (lambda n, t, sp, cl: "ScrollRect" in t, "scroll_area"),
    (lambda n, t, sp, cl: sp and bool(cl), "interactive_icon"),
    (lambda n, t, sp, cl: sp and not bool(cl), "display_icon"),
    (lambda n, t, sp, cl: bool(re.search(r"Close|X\b|关闭", n)), "close_button"),
    (lambda n, t, sp, cl: bool(re.search(r"Item|Cell|Grid", n)) and bool(sp), "item_cell"),
    (lambda n, t, sp, cl: bool(re.search(r"Reward|奖励", n)), "reward_item"),
    (lambda n, t, sp, cl: bool(re.search(r"Mask|Blocker|遮罩", n)), "mask"),
    (lambda n, t, sp, cl: bool(re.search(r"Tab|页签", n)), "tab"),
    (lambda n, t, sp, cl: bool(cl), "clickable_unknown"),
    (lambda n, t, sp, cl: True, "text"),  # fallback
]

# role 推断表
ROLE_RULES = [
    (lambda n, tx: bool(re.search(r"(关闭|Close|X$)", n)) or tx == "关闭", "close_popup"),
    (lambda n, tx: bool(re.search(r"(确定|Confirm|OK)", n)) or tx in ("确定", "确认"), "confirm"),
    (lambda n, tx: bool(re.search(r"(取消|Cancel)", n)) or tx == "取消", "cancel"),
    (lambda n, tx: bool(re.search(r"(使用|Use)", n)) or tx == "使用", "use_action"),
    (lambda n, tx: bool(re.search(r"(领取|Reward|Get|Claim)", n)) or tx in ("领取", "领取奖励"), "claim_reward"),
    (lambda n, tx: bool(re.search(r"(前往|Go|去)", n)) or tx in ("前往", "去"), "go_to"),
    (lambda n, tx: bool(re.search(r"(返回|Back)", n)) or tx == "返回", "back"),
    (lambda n, tx: bool(re.search(r"(Tab|页签)", n)), "switch_tab"),
    (lambda n, tx: bool(re.search(r"item|Item|道具", n)), "open_item_tip_or_select"),
    (lambda n, tx: bool(re.search(r"activity|Activity|活动", n)), "open_activity"),
    (lambda n, tx: bool(re.search(r"building|Building|建筑", n)), "open_building_menu"),
    (lambda n, tx: "SendBtn|发送|chat|Chat|邮件|Mail" in n, "send_or_chat"),
    (lambda n, tx: "Shop|商店|Mall|Store|购买|Buy" in n, "open_shop"),
    (lambda n, tx: "Mail|邮件|Bag|背包|Task|Quest|Task|任务" in n, "open_menu"),
    (lambda n, tx: True, "normal_action"),
]

# 优先级规则（按顺序匹配，第一条命中即返回）
PRIORITY_RULES = [
    # P0：关键动作
    (lambda n, tx, et, rl: rl in ("close_popup", "confirm", "cancel", "use_action", "claim_reward", "go_to", "back"), "P0"),
    # P1：入口/页签/常见菜单
    (lambda n, tx, et, rl: rl in ("switch_tab", "open_item_tip_or_select", "open_activity", "open_building_menu", "send_or_chat", "open_shop", "open_menu"), "P1"),
    (lambda n, tx, et, rl: et in ("tab",), "P1"),
    # P2：道具格子/奖励/活动图标/建筑菜单
    (lambda n, tx, et, rl: et in ("item_cell", "reward_item", "interactive_icon"), "P2"),
    # P3：普通按钮/未知可点击
    (lambda n, tx, et, rl: et in ("button", "clickable_unknown", "slider", "dropdown", "input_field"), "P3"),
    # LOW：调试/工具/装饰
    (lambda n, tx, et, rl: bool(re.search(r"(Debug|Editor|Test|Gizmo|dev)", n, re.I)), "LOW"),
    (lambda n, tx, et, rl: True, "LOW"),
]

# 角色中文名
ROLE_CN: Dict[str, str] = {
    "close_popup": "关闭弹窗",
    "confirm": "确认操作",
    "cancel": "取消操作",
    "use_action": "使用操作",
    "claim_reward": "领取奖励",
    "go_to": "前往",
    "back": "返回",
    "switch_tab": "切换页签",
    "open_item_tip_or_select": "查看/选择道具",
    "open_activity": "打开活动",
    "open_building_menu": "建筑菜单",
    "send_or_chat": "发送/聊天",
    "open_shop": "打开商店",
    "open_menu": "打开菜单",
    "normal_action": "普通操作",
}

# 元素类型中文名
ET_CN: Dict[str, str] = {
    "button": "按钮",
    "tab": "页签",
    "slider": "滑动条",
    "input_field": "输入框",
    "dropdown": "下拉菜单",
    "scrollbar": "滚动条",
    "scroll_area": "滚动区域",
    "interactive_icon": "可交互图标",
    "display_icon": "装饰图标",
    "close_button": "关闭按钮",
    "item_cell": "道具格子",
    "reward_item": "奖励格子",
    "mask": "遮罩",
    "clickable_unknown": "未知可点击",
    "text": "文本",
}

# 低质量节点名关键字（不应进入 enhanced）
LOW_QUALITY_NAMES = {"cont", "item", "node", "clone", "root", "default", "placeholder", "spacer", "separator"}

# 调试/编辑/测试节点名关键字
DEBUG_KEYWORDS = ["debug", "editor", "test", "gizmo", "dev", "temp", "mock", "dummy", "sandbox"]


# ============================================================
# 主类
# ============================================================

class UITreeEnhancer:
    """工程态 UI 树增强器"""

    def __init__(self, source_dir: str = "", output_dir: str = ""):
        # 用 Path 计算路径，避免硬编码
        self._script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.source_dir = Path(source_dir) if source_dir else self._script_dir
        self.output_dir = Path(output_dir) if output_dir else self.source_dir

        # 输入文件路径
        self._project_path = self.source_dir / "project_ui_inventory.json"
        self._runtime_tree_path = self.source_dir / "current_ui_tree.json"
        self._pages_dir = self.source_dir / "pages"

        # 输出文件路径
        self._output_path = self.output_dir / "enhanced_ui_tree.json"

        self._project_data: Optional[Dict] = None
        self._runtime_data: Optional[Dict] = None
        self._page_data: List[Dict] = []

        # 统计
        self._stats = {
            "projectNodes": 0,
            "rawClickable": 0,
            "enhancedNodes": 0,
            "filteredNodes": 0,
            "p0": 0, "p1": 0, "p2": 0, "p3": 0, "low": 0,
        }

    # ---- 外部接口 ----

    def run(self, mode: str = "project_only", overwrite: bool = True) -> Dict:
        """
        执行增强流程

        Args:
            mode: "project_only" 仅工程态 / "merge" 工程态+运行态
            overwrite: 是否覆盖已有输出文件

        Returns:
            {"success": bool, "enhancedPath": str, "summary": dict}
        """
        # 1. 加载数据
        if not self._load_project():
            return {"success": False, "error": "未找到 project_ui_inventory.json"}

        if mode == "merge":
            self._load_runtime()
            self._load_pages()

        # 2. 增强
        enhanced_nodes = self._enhance()

        # 3. 输出
        if not overwrite and self._output_path.exists():
            return {"success": False, "error": "增强文件已存在，overwrite=False"}

        output = {
            "schemaVersion": "enhanced_ui_tree/v1",
            "generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "source": {
                "projectInventory": str(self._project_path),
                "runtimeTree": str(self._runtime_tree_path) if self._runtime_data else "",
                "pages": [str(p) for p in self._page_data] if self._page_data else [],
            },
            "summary": {
                "projectNodes": self._stats["projectNodes"],
                "rawClickable": self._stats["rawClickable"],
                "enhancedNodes": len(enhanced_nodes),
                "filteredNodes": self._stats["filteredNodes"],
                "p0": self._stats["p0"],
                "p1": self._stats["p1"],
                "p2": self._stats["p2"],
                "p3": self._stats["p3"],
                "low": self._stats["low"],
            },
            "nodes": enhanced_nodes,
        }

        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(self._output_path), "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "enhancedPath": str(self._output_path),
            "summary": output["summary"],
        }

    # ---- 数据加载 ----

    def _load_project(self) -> bool:
        if not self._project_path.exists():
            return False
        with open(str(self._project_path), "r", encoding="utf-8") as f:
            self._project_data = json.load(f)
        return True

    def _load_runtime(self):
        if self._runtime_tree_path.exists():
            with open(str(self._runtime_tree_path), "r", encoding="utf-8") as f:
                self._runtime_data = json.load(f)

    def _load_pages(self):
        if self._pages_dir.exists():
            for p in sorted(self._pages_dir.glob("*.json")):
                try:
                    with open(str(p), "r", encoding="utf-8") as f:
                        self._page_data.append(json.load(f))
                except Exception:
                    pass

    # ---- 增强核心逻辑 ----

    def _enhance(self) -> List[Dict]:
        if not self._project_data:
            return []

        prefabs = self._project_data.get("prefabs", [])
        project_nodes_total = 0
        project_clickable_total = 0
        enhanced = []

        for prefab in prefabs:
            asset_path = prefab.get("assetPath", "")
            root_name = prefab.get("rootName", "")
            category = prefab.get("category", "")
            nodes = prefab.get("nodes", [])

            for node in nodes:
                project_nodes_total += 1
                if node.get("clickable") or node.get("hasButton"):
                    project_clickable_total += 1

                # 初步过滤：跳过明显无用节点
                if self._should_skip(node):
                    self._stats["filteredNodes"] += 1
                    continue

                # 构建 enhanced node
                en = self._build_enhanced_node(node, prefab)
                if en:
                    enhanced.append(en)

        self._stats["projectNodes"] = project_nodes_total
        self._stats["rawClickable"] = project_clickable_total
        self._stats["enhancedNodes"] = len(enhanced)

        # 增强后过滤：LOW 优先级的节点不在 enhanced 中保留
        enhanced = [en for en in enhanced if en.get("priority") != "LOW"]
        for en in enhanced:
            p = en.get("priority", "LOW")
            if p in ("P0", "P1", "P2", "P3", "LOW"):
                self._stats[p.lower()] = self._stats.get(p.lower(), 0) + 1

        return enhanced

    def _should_skip(self, node: Dict) -> bool:
        """
        判断是否跳过此节点。
        只保留真正有交互/测试价值的节点。
        """
        clickable = node.get("clickable", False)
        has_button = node.get("hasButton", False)
        sprite_name = node.get("spriteName", "") or ""
        text = node.get("text", "") or ""
        name = node.get("name", "") or ""
        comp_types = node.get("componentTypes", []) or []
        raycast = node.get("raycastTarget", False)

        # 关键组件
        key_components = {"Button", "Toggle", "Slider", "InputField", "Dropdown",
                          "EventTrigger", "Scrollbar", "ScrollRect"}
        has_key_comp = any(c in comp_types for c in key_components)

        # 关键动作词
        action_words = {"关闭", "确定", "确认", "取消", "使用", "领取", "前往",
                        "返回", "购买", "发送", "充值", "提取", "合成", "抽奖",
                        "兑换", "分享", "邀请", "签到", "升级", "强化"}
        has_action_text = bool(text and any(w in text for w in action_words))

        # 控件类关键词
        control_kw = {"Close", "Confirm", "Cancel", "Use", "Reward", "Get",
                      "Btn", "Button", "Icon", "Tab", "Toggle", "Item", "Cell",
                      "Input", "Slider", "Scroll", "CloseBtn", "SendBtn",
                      "RewardBtn", "ConfirmBtn", "CancelBtn"}
        has_control_name = any(kw in name for kw in control_kw)

        # 非 clickable 的纯装饰图标 → 跳过
        if sprite_name and not clickable and not has_button:
            return True

        # 非 clickable 的纯文本 → 跳过
        if text and not clickable and not has_button and not has_key_comp:
            return True

        # clickable 但无任何可识别特征的时代 → P3/LOW，跳过
        if clickable and not has_button and not has_key_comp and not has_action_text and not has_control_name:
            return True

        # 可操作按钮/控件 → 保留
        if clickable or has_button or has_key_comp:
            return False

        # 有关键文字 → 保留
        if has_action_text:
            return False

        # 有关键控件名 → 保留
        if has_control_name:
            return False

        return True

    def _build_enhanced_node(self, node: Dict, prefab: Dict) -> Optional[Dict]:
        """为单个节点构建 enhanced 结构"""
        asset_path = prefab.get("assetPath", "")
        root_name = prefab.get("rootName", "")
        category = prefab.get("category", "")
        node_path = node.get("path", "")
        node_name = node.get("name", "")
        text = node.get("text", "") or ""
        comp_types = node.get("componentTypes", []) or []
        clickable = node.get("clickable", False)
        has_button = node.get("hasButton", False)
        sprite_name = node.get("spriteName", "") or ""
        atlas_name = node.get("atlasName", "") or ""
        raycast = node.get("raycastTarget", False)

        # full path
        full_path = f"{asset_path}::{node_path}" if asset_path else node_path

        # elements
        element_type = self._infer_element_type(node_name, comp_types, sprite_name, clickable)
        role = self._infer_role(node_name, text)
        page_id = self._infer_page_id(node, prefab)
        priority = self._infer_priority(node_name, text, element_type, role)
        confidence = self._calc_confidence(node, element_type, role, page_id)
        display_name = self._gen_display_name(page_id, node_name, text, element_type, role)
        chinese_desc = self._gen_chinese_description(page_id, text, element_type, role, node_name, confidence)
        segment = self._get_name_segment(node_name)

        # clickTargetNode / visualNode
        click_target = full_path if clickable else ""
        visual_node = full_path

        # reviewHint / risk
        risk = self._calc_risk(node, element_type, page_id)
        review_hint = self._gen_review_hint(risk, clickable, has_button, sprite_name, text)

        return {
            "path": full_path,
            "prefabPath": asset_path,
            "prefabNodePath": node_path,
            "runtimePath": "",
            "nodeName": node_name,
            "text": text,
            "components": comp_types,
            "componentTypes": comp_types,
            "spriteName": sprite_name,
            "atlasName": atlas_name,
            "clickable": clickable,
            "clickableReason": self._clickable_reason(node),
            "hasButton": has_button,
            "pageId": page_id,
            "pageName": PAGE_NAME_MAP.get(page_id, page_id),
            "elementType": element_type,
            "role": role,
            "roleNameCn": ROLE_CN.get(role, role),
            "elementTypeNameCn": ET_CN.get(element_type, element_type),
            "priority": priority,
            "segment": segment,
            "displayName": display_name,
            "chineseDescription": chinese_desc,
            "suggestedTestId": self._gen_test_id(page_id, node_name, text),
            "suggestedSemanticId": self._gen_semantic_id(page_id, role),
            "clickTargetNode": click_target,
            "visualNode": visual_node,
            "confidence": round(confidence, 2),
            "reviewStatus": "pending",
            "reviewHint": review_hint,
            "risk": risk,
        }

    # ---- 推断函数 ----

    def _infer_element_type(self, name: str, comp_types: List[str],
                            sprite_name: str, clickable: bool) -> str:
        for condition, etype in ELEMENT_TYPE_RULES:
            if condition(name, comp_types, sprite_name, clickable):
                return etype
        return "text"

    def _infer_role(self, name: str, text: str) -> str:
        for condition, role in ROLE_RULES:
            if condition(name, text):
                return role
        return "normal_action"

    def _infer_page_id(self, node: Dict, prefab: Dict) -> str:
        # 优先级：prefab.rootName > assetPath 文件名 > category > nodePath 第一段
        root_name = prefab.get("rootName", "")
        asset_path = prefab.get("assetPath", "")
        category = prefab.get("category", "")
        node_path = node.get("path", "")
        name = node.get("name", "")

        if root_name:
            return root_name
        if asset_path:
            stem = Path(asset_path).stem  # 文件名不含扩展名
            if stem:
                return stem
        if category:
            return category
        if node_path:
            first = node_path.split("/")[0]
            if first:
                return first
        # 尝试从 name/path 中提取 Panel/Dialog/View/Window/Page
        for kw in ("Panel", "Dialog", "View", "Window", "Page"):
            idx = name.find(kw)
            if idx >= 0:
                return name[:idx + len(kw)]
        return "unknown"

    def _infer_priority(self, name: str, text: str, element_type: str, role: str) -> str:
        for condition, pri in PRIORITY_RULES:
            if condition(name, text, element_type, role):
                return pri
        return "LOW"

    def _calc_confidence(self, node: Dict, element_type: str, role: str, page_id: str) -> float:
        """置信度计算（0.30 基础 + 加分 - 减分）"""
        score = 0.30  # 基础：工程态可点击节点
        name = node.get("name", "") or ""
        text = node.get("text", "") or ""
        sprite_name = node.get("spriteName", "") or ""
        has_button = node.get("hasButton", False)
        has_missing = node.get("hasMissingScript", False)
        has_test_id = node.get("hasTestId", False)

        # 加分
        if has_button:
            score += 0.20
        elif element_type in ("button",):
            score += 0.15
        if text:
            score += 0.20
        if page_id and page_id != "unknown":
            score += 0.10
        if role in ("close_popup", "confirm", "use_action", "claim_reward"):
            score += 0.10
        if sprite_name:
            score += 0.05
        if has_test_id:
            score += 0.10
        if node.get("clickable") and node.get("raycastTarget"):
            score += 0.05

        # 减分
        if not node.get("clickable") and not has_button:
            score -= 0.10
        if page_id == "unknown":
            score -= 0.10
        if name.lower() in LOW_QUALITY_NAMES:
            score -= 0.10
        if any(kw in name.lower() for kw in DEBUG_KEYWORDS):
            score -= 0.20
        if has_missing:
            score -= 0.20
        if not node.get("rectTransform"):
            score -= 0.05

        return max(0.0, min(1.0, score))

    def _gen_display_name(self, page_id: str, name: str, text: str,
                          element_type: str, role: str) -> str:
        """生成 displayName"""
        page_cn = PAGE_NAME_MAP.get(page_id, page_id)
        et_cn = ET_CN.get(element_type, element_type)
        rc_cn = ROLE_CN.get(role, "")

        parts = [page_cn]
        if text:
            parts.append(text)
        elif rc_cn:
            parts.append(rc_cn)
        else:
            # 翻译名称
            name_cn = self._translate_name(name)
            parts.append(name_cn if name_cn else name)
        parts.append(et_cn)
        return "-".join(parts)

    def _gen_chinese_description(self, page_id: str, text: str,
                                 element_type: str, role: str,
                                 name: str, confidence: float) -> str:
        """生成 chineseDescription"""
        page_cn = PAGE_NAME_MAP.get(page_id, page_id)
        et_cn = ET_CN.get(element_type, element_type)
        rc_cn = ROLE_CN.get(role, "")

        if text:
            desc = f"{page_cn}界面中用于{rc_cn}的{et_cn}，文字「{text}」"
        elif rc_cn:
            desc = f"{page_cn}界面中用于{rc_cn}的{et_cn}"
        elif confidence >= 0.5:
            name_cn = self._translate_name(name)
            desc = f"{page_cn}界面中的{et_cn}（节点名：{name_cn or name}）"
        else:
            desc = f"根据节点名 {name} 推断为{et_cn}，缺少可见文本和截图，需要人工确认"
        return desc

    def _gen_test_id(self, page_id: str, name: str, text: str) -> str:
        tid = page_id + "." + name.replace(" ", "")
        if text:
            tid += "." + text[:20]
        return tid

    def _gen_semantic_id(self, page_id: str, role: str) -> str:
        rc = ROLE_CN.get(role, role)
        return f"{page_id}.{rc}"

    def _get_name_segment(self, name: str) -> str:
        """从节点名推断位置片段"""
        parts = re.findall(r"[A-Z][a-z]*|[a-z]+|\d+", name)
        return "_".join(parts).lower() if parts else name.lower()

    def _clickable_reason(self, node: Dict) -> str:
        reasons = []
        if node.get("clickable"):
            reasons.append("clickable=true")
        if node.get("hasButton"):
            reasons.append("hasButton=true")
        comps = node.get("componentTypes", []) or []
        if "Button" in comps:
            reasons.append("component=Button")
        if "EventTrigger" in comps:
            reasons.append("component=EventTrigger")
        if "Toggle" in comps:
            reasons.append("component=Toggle")
        if node.get("raycastTarget"):
            reasons.append("raycastTarget=true")
        return ";".join(reasons) if reasons else "unknown"

    def _calc_risk(self, node: Dict, element_type: str, page_id: str) -> List[str]:
        risk = []
        if not node.get("rectTransform"):
            risk.append("no_screen_rect")
        if page_id == "unknown":
            risk.append("no_page_id")
        if not node.get("text"):
            risk.append("no_text")
        if not node.get("clickable"):
            risk.append("not_clickable")
        if not node.get("spriteName"):
            risk.append("no_sprite")
        if node.get("hasMissingScript"):
            risk.append("missing_script")
        if element_type == "clickable_unknown":
            risk.append("unknown_element_type")
        return risk

    def _gen_review_hint(self, risk: List[str], clickable: bool,
                         has_button: bool, sprite_name: str, text: str) -> str:
        hints = []
        if "no_screen_rect" in risk:
            hints.append("缺少运行态坐标")
        if "no_page_id" in risk:
            hints.append("页面归属未知")
        if "no_text" in risk:
            hints.append("缺少可见文本")
        if "missing_script" in risk:
            hints.append("脚本缺失")
        if "unknown_element_type" in risk:
            hints.append("元素类型不确定")

        if hints:
            hint = "；".join(hints[:3])
            if hint:
                hint += "，建议结构确认后做点击验证"
            else:
                hint = "建议结构确认后做点击验证"
        else:
            hint = "工程态高置信节点；建议确认后做点击验证"
        return hint

    def _translate_name(self, name: str) -> str:
        """简单英文节点名翻译"""
        parts = re.findall(r"[A-Z][a-z]*|[a-z]+|\d+", name)
        cn_map = {
            "Btn": "按钮", "Button": "按钮", "Icon": "图标", "Text": "文本",
            "Label": "标签", "Panel": "面板", "Toggle": "开关", "Close": "关闭",
            "Confirm": "确认", "Cancel": "取消", "Use": "使用", "Reward": "奖励",
            "Item": "道具", "Cell": "格子", "Grid": "网格", "List": "列表",
            "Scroll": "滚动", "Input": "输入", "Slider": "滑动",
            "Tab": "页签", "Back": "返回", "Go": "前往", "Get": "领取",
            "Claim": "领取", "Mail": "邮件", "Bag": "背包", "Shop": "商店",
            "Tip": "提示", "Info": "信息", "Setting": "设置", "Head": "头像",
            "Frame": "边框", "Bg": "背景", "Mask": "遮罩",
        }
        result = []
        for p in parts:
            if p in cn_map:
                result.append(cn_map[p])
            else:
                result.append(p)
        return "".join(result)


# ============================================================
# 模块级便捷函数
# ============================================================

def run_enhance(source_dir: str = "", output_dir: str = "",
                mode: str = "project_only", overwrite: bool = True) -> Dict:
    """
    便捷入口：生成 enhanced_ui_tree.json

    Args:
        source_dir: 输入目录（含 project_ui_inventory.json）
        output_dir: 输出目录（默认同 source_dir）
        mode: "project_only" 或 "merge"
        overwrite: 是否覆盖已有文件

    Returns:
        dict
    """
    enhancer = UITreeEnhancer(source_dir=source_dir, output_dir=output_dir)
    return enhancer.run(mode=mode, overwrite=overwrite)


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    result = run_enhance(source_dir=src)
    print(json.dumps(result, ensure_ascii=False, indent=2))
