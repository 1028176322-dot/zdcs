#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSmoke - 元素语义映射管理器

管理 element_mapping.json，支持：
  - 元素 ↔ 语义标注（displayName/testId/role/pageId/meaning）
  - screenRect 高亮
  - 截图反查命中候选节点
  - 手工确认 / 自动推断 标记

数据模型：
  {
    "elementPath": "Canvas/BagPanel/ButtonUse",
    "name": "ButtonUse",
    "type": "Button",
    "clickable": true,
    "screenRect": [464, 2380, 706, 2490],

    "displayName": "使用按钮",
    "testId": "bag.button.use",
    "role": "action",
    "pageId": "bag_page",
    "meaning": "使用选中的道具",

    "source": "manual_confirmed",
    "mappedAt": "2026-06-15T12:00:00"
  }
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.environ.get("USERPROFILE", "."), ".autosmoke")
METADATA_DIR = os.path.join(CONFIG_DIR, "metadata")
MAPPING_PATH = os.path.join(METADATA_DIR, "element_mapping.json")


class ElementMappingManager:
    """
    元素语义映射管理器

    支持从 metadata 列表中选取元素，添加语义标注，
    保存到 element_mapping.json 供测试脚本使用。
    """

    def __init__(self, mapping_path: str = None):
        self._path = mapping_path or MAPPING_PATH
        self._mappings: Dict[str, Dict] = {}  # key = elementPath
        self._metadata_cache: List[Dict] = []

    @staticmethod
    def _coerce_bool(v, default=False):
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            sv = v.strip().lower()
            if sv in ("1", "true", "yes", "y", "on"):
                return True
            if sv in ("0", "false", "no", "n", "off"):
                return False
        return default

    @staticmethod
    def _coerce_review_status(value):
        s = (value or "").strip().lower()
        if s == "manual_confirmed":
            return "click_confirmed"
        return s or "pending"

    @staticmethod
    def _coerce_review_level(status):
        status = (status or "").lower()
        if status.endswith("_confirmed"):
            return status[:-10]
        return "manual"

    def _extract_page_id(self, path: str, canvas: str = ""):
        return canvas or (path.split("/")[0] if path else "unknown")

    def _coerce_field(self, data, field, default=None):
        return data[field] if isinstance(data, dict) and data.get(field) else default

    def _build_review_flags(self, element, screenshot_ref=""):
        has_screenshot = self._coerce_bool(screenshot_ref) or False
        has_highlight = False
        screen_rect = element.get("screenRect") if isinstance(element, dict) else None
        if isinstance(screen_rect, (list, tuple)) and len(screen_rect) >= 4:
            has_highlight = True
        return {
            "hasScreenshot": has_screenshot,
            "hasHighlightRect": has_highlight,
            "visualReviewRequired": has_screenshot,
            "clickReviewRequired": self._coerce_bool(element.get("clickable", False)),
            "reviewWarnings": (
                []
                if has_screenshot
                else ["缺少页面截图，当前仅可进行结构确认"]
            ),
        }

    def _coerce_dict(self, payload, default=None):
        return payload if isinstance(payload, dict) else (default or {})

    def upsert(self, path: str, mapping: Dict[str, Any]):
        if not isinstance(mapping, dict):
            mapping = {}
        item = dict(mapping)
        item_path = path or item.get("path", "")
        if not item_path:
            return None
        item["elementPath"] = item_path
        if "path" not in item:
            item["path"] = item_path
        item["source"] = item.get("source", "manual_confirmed")
        item["reviewStatus"] = self._coerce_review_status(item.get("reviewStatus", item.get("source", "pending")))
        item["reviewLevel"] = self._coerce_review_level(item["reviewStatus"])
        self._mappings[item_path] = item
        return item

    def get_unmapped_elements(self, elements: List[Dict] = None):
        if elements is None:
            p = os.path.join(METADATA_DIR, "current_ui.json")
            if not os.path.exists(p):
                return []
            with open(p, "r", encoding="utf-8") as f:
                payload = json.load(f)
            elements = payload.get("elements", [])
        mapped = set(self._mappings.keys()) if isinstance(self._mappings, dict) else set()
        return [e for e in elements if isinstance(e, dict) and e.get("path") not in mapped]

    def reverse_lookup(self, x: int, y: int, elements: List[Dict] = None):
        if elements is None:
            p = os.path.join(METADATA_DIR, "current_ui.json")
            if not os.path.exists(p):
                return []
            with open(p, "r", encoding="utf-8") as f:
                payload = json.load(f)
            elements = payload.get("elements", [])
        out = []
        for e in elements:
            sr = e.get("screenRect", [])
            if not isinstance(sr, (list, tuple)) or len(sr) < 4:
                continue
            x0,y0,x1,y1 = sr[:4]
            if x >= x0 and x <= x1 and y >= y0 and y <= y1:
                cx = (x0 + x1) / 2
                cy = (y0 + y1) / 2
                area = (x1-x0)*(y1-y0)
                out.append({
                    "name": e.get("name",""),
                    "path": e.get("path",""),
                    "pathDepth": len((e.get("path") or "").split("/")),
                    "area": round(area, 2),
                    "distance": round(abs(x-cx)+abs(y-cy), 2)
                })
        out.sort(key=lambda i: (i["distance"], -i["area"]))
        return out

    def delete(self, path: str):
        if not isinstance(path, str):
            return False
        if path in self._mappings:
            del self._mappings[path]
            return self.save()
        return False

    def stats(self):
        total = len(self._mappings)
        manual = sum(1 for m in self._mappings.values()
                     if self._coerce_review_status(m.get("source", "")) == "click_confirmed")
        with_testid = sum(1 for m in self._mappings.values() if m.get("testId"))
        return {
            "totalMappings": total,
            "manualConfirmed": manual,
            "withTestId": with_testid,
        }

    def get(self, element_path: str):
        return (self._mappings.get(element_path) if hasattr(self, "_mappings") else None) or {}

    # ============================================================
    # 加载/保存
    # ============================================================

    def load(self) -> bool:
        """加载映射文件"""
        if not os.path.exists(self._path):
            self._mappings = {}
            return False
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._mappings = {}
                for item in data:
                    key = item.get("elementPath", item.get("path", ""))
                    if key:
                        self._mappings[key] = item
            elif isinstance(data, dict):
                raw = data.get("mappings", {})
                if isinstance(raw, list):
                    self._mappings = {}
                    for item in raw:
                        key = item.get("elementPath", item.get("path", ""))
                        if key:
                            self._mappings[key] = item
                elif isinstance(raw, dict):
                    self._mappings = raw
                else:
                    self._mappings = {}
            logger.info("已加载 %d 个元素映射", len(self._mappings))
            return True
        except Exception as e:
            logger.warning("加载映射文件失败: %s", e)
            self._mappings = {}
            return False

    def save(self) -> bool:
        """保存映射文件"""
        try:
            os.makedirs(METADATA_DIR, exist_ok=True)
            # 保存为列表格式，兼容前端展示
            mappings_list = list(self._mappings.values())
            output = {
                "exportTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "totalMappings": len(mappings_list),
                "mappings": mappings_list,
            }
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            logger.info("已保存 %d 个元素映射", len(mappings_list))
            return True
        except Exception as e:
            logger.warning("保存映射文件失败: %s", e)
            return False

    def export_drafts(self, output_path: str = None) -> str:
        """
        映射草稿独立输出：从 current_ui.json 生成草稿，写入 mapping_store。
        旧 element_mapping_draft.json 只通过 MappingStore.export_legacy_files() 兼容导出。
        """
        drafts = self.generate_drafts()
        if not drafts:
            logger.info("无新草稿生成")
            return ""

        try:
            from 元数据.mapping_store import MappingStore
            store = MappingStore()
            old_suspend = getattr(store, "_suspend_rebuild", False)
            store._suspend_rebuild = True
            try:
                for draft in drafts:
                    store.save_draft(draft)
            finally:
                store._suspend_rebuild = old_suspend
            store.rebuild_indexes()
            if output_path:
                store.export_legacy_files()
                logger.info("草稿已通过 mapping_store 导出 legacy: %s (%d 条)", output_path, len(drafts))
                return output_path
            logger.info("草稿已写入 mapping_store (%d 条)", len(drafts))
            return store.metadata_relpath(store.draft_page_dir)
        except Exception as exc:
            logger.warning("写入草稿到 mapping_store 失败: %s", exc)
            return ""

    def export_formal(self, output_path: str = None) -> str:
        """
        正式映射输出（方案第11.4节格式）：以 testId 为 key 的字典，主写入 mapping_store。
        旧 element_mapping_formal.json 只通过 MappingStore.export_legacy_files() 兼容导出。
        """
        formal = {}
        for path, m in self._mappings.items():
            tid = m.get("testId", "")
            if not tid:
                # 用路径片段生成 testId
                parts = path.replace("/", ".").split(".")
                tid = ".".join(p for p in parts if p and not p.startswith("Canvas"))
            formal[tid] = {
                "testId": tid,
                "semanticId": m.get("semanticId", ""),
                "displayName": m.get("displayName", ""),
                "chineseDescription": m.get("chineseDescription", ""),
                "pageId": m.get("pageId", ""),
                "role": m.get("role", ""),
                "locator": {
                    "type": "runtimePath",
                    "value": path,
                },
                "fallbackLocators": [
                    {"type": "text", "value": m.get("name", "")},
                    {"type": "screenRect", "value": m.get("screenRect", [])},
                ],
                "click": {
                    "method": "unity_event_system",
                    "safePoint": "center",
                },
            }
        try:
            from 元数据.mapping_store import MappingStore
            store = MappingStore()
            old_suspend = getattr(store, "_suspend_rebuild", False)
            store._suspend_rebuild = True
            try:
                for item in formal.values():
                    store.upsert_formal(item)
            finally:
                store._suspend_rebuild = old_suspend
            store.rebuild_indexes()
            if output_path:
                store.export_legacy_files()
                logger.info("正式映射已通过 mapping_store 导出 legacy: %s (%d 条)", output_path, len(formal))
                return output_path
            logger.info("正式映射已写入 mapping_store (%d 条)", len(formal))
            return store.metadata_relpath(store.formal_page_dir)
        except Exception as exc:
            logger.warning("写入正式映射到 mapping_store 失败: %s", exc)
            return ""

    def generate_icon_drafts(self, elements: List[Dict] = None) -> List[Dict]:
        """
        从元数据中提取图标元素，生成图标映射草稿

        :param elements: UI 元素列表（含 spriteName 字段）
        :return: 图标草稿列表
        """
        screenshot_ref = ""
        if elements is None:
            ui_path = os.path.join(METADATA_DIR, "current_ui.json")
            if os.path.exists(ui_path):
                try:
                    with open(ui_path, "r", encoding="utf-8") as f:
                        ui_data = json.load(f)
                    elements = ui_data.get("elements", [])
                    screenshot_ref = ui_data.get("screenshotRef", "")
                except Exception:
                    return []
            else:
                return []
        else:
            screenshot_ref = ""

        status = self._coerce_review_status("pending")
        icon_drafts = []
        for elem in elements:
            sprite_name = elem.get("spriteName", "")
            if not sprite_name:
                continue
            path = elem.get("path", "")
            if path in self._mappings:
                continue

            page_id = self._extract_page_id(path, elem.get("canvas", ""))
            page_cn = self.PAGE_NAME_MAP.get(page_id, page_id)
            node_name = elem.get("name", "")
            icon_type = GuessIconTypeStatic(sprite_name, node_name)
            role = "interactive_icon" if elem.get("clickable", False) else "display_icon"

            display_name = "%s图标" % (node_name.replace("Icon", "").replace("icon", "") or sprite_name)
            if icon_type != "unknown":
                display_name = "%s%s图标" % (page_cn, icon_type)

            desc = "%s的%s" % (page_cn, display_name)
            if elem.get("clickable", False):
                desc += "，点击后可能打开详情或弹窗"

            elem_screenshot_ref = elem.get("screenshotRef") or elem.get("pageRef") or screenshot_ref
            flags = self._build_review_flags(elem, screenshot_ref=elem_screenshot_ref)
            icon_drafts.append({
                "draftType": "icon",
                "pageId": page_id,
                "spriteName": sprite_name,
                "iconType": icon_type,
                "nodeName": node_name,
                "path": path,
                "screenRect": elem.get("screenRect", []),
                "clickable": elem.get("clickable", False),
                "displayName": display_name,
                "chineseDescription": desc,
                "role": role,
                "source": "auto_draft",
                "screenshotRef": elem_screenshot_ref,
                "review": {
                    "status": status,
                    "level": self._coerce_review_level(status),
                    "visualConfirmed": False,
                    "clickConfirmed": False,
                    "warnings": flags["reviewWarnings"],
                },
                "reviewStatus": status,
                "reviewLevel": self._coerce_review_level(status),
                "hasScreenshot": flags["hasScreenshot"],
                "hasHighlightRect": flags["hasHighlightRect"],
                "visualReviewRequired": flags["visualReviewRequired"],
                "clickReviewRequired": flags["clickReviewRequired"],
                "reviewWarnings": flags["reviewWarnings"],
                "confidence": 0.6 if elem.get("clickable", False) else 0.3,
            })

        logger.info("图标草稿: 从 %d 个元素中生成 %d 个", len(elements), len(icon_drafts))
        return icon_drafts

    PAGE_NAME_MAP = {
        "MainCity": "主城界面", "BagPanel": "背包界面",
        "RewardPopup": "奖励弹窗", "BuildingMenu": "建筑菜单",
        "ShopPanel": "商店界面", "ActivityPanel": "活动界面",
    }
    ROLE_NAME_MAP = {
        "primary_action_button": "主操作按钮", "confirm_button": "确认按钮",
        "close_button": "关闭按钮", "cancel_button": "取消按钮",
        "interactive_icon": "可点击图标",
    }

    @staticmethod
    def normalize_elements_from_payload(payload: dict, source_name: str = "") -> List[Dict]:
        """
        兼容读取多种数据源格式，返回统一元素列表。

        支持的格式：
        - enhanced_ui_tree.json: nodes
        - current_ui_tree.json: nodes
        - current_ui.json: elements
        - project_ui_inventory.json: prefabs[].nodes
        - pages/*.json: nodes 或 elements

        Args:
            payload: 原始 JSON 数据
            source_name: 数据源名称，用于调试

        Returns:
            统一元素列表，每个元素至少包含 path/name/clickable 字段
        """
        # enhanced_ui_tree.json / current_ui_tree.json → nodes
        if "nodes" in payload:
            return payload["nodes"]

        # current_ui.json → elements
        if "elements" in payload:
            return payload["elements"]

        # project_ui_inventory.json → prefabs[].nodes
        if "prefabs" in payload:
            elements = []
            for prefab in payload.get("prefabs", []):
                elements.extend(prefab.get("nodes", []))
            return elements

        # pages/*.json → 尝试 nodes 或 elements
        if "pageId" in payload or "sceneId" in payload:
            for key in ("nodes", "elements"):
                if key in payload:
                    return payload[key]

        return []

    def generate_drafts(self, elements=None, min_priority: str = None,
                        include_low: bool = False, source_type: str = ""):
        """
        从 UI 元素列表自动生成映射草稿

        Args:
            elements: UI 元素列表，None 则从 current_ui.json 读取
            min_priority: 最低优先级（P0/P1/P2/P3/LOW），None 表示不限制
            include_low: 是否包含 LOW 优先级
            source_type: "enhanced" 表示元素来自 enhanced_ui_tree.json
        """
        if elements is None:
            p = os.path.join(METADATA_DIR, "current_ui.json")
            if not os.path.exists(p): return []
            with open(p, "r", encoding="utf-8") as f:
                payload = json.load(f)
                elements = payload.get("elements", [])
                screenshot_ref = payload.get("screenshotRef", "")
        else:
            screenshot_ref = ""
        drafts = []
        for e in elements:
            if e.get("path", "") in self._mappings: continue
            if not e.get("clickable", False): continue

            # 优先级过滤
            pri = e.get("priority", "")
            if min_priority:
                pri_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "LOW": 4}
                if pri_order.get(pri, 99) < pri_order.get(min_priority, 0):
                    continue
            if not include_low and pri == "LOW":
                continue

            if source_type == "enhanced":
                d = self._build_draft_from_enhanced(e)
            else:
                element_screenshot = e.get("screenshotRef") or e.get("pageRef") or e.get("pageScreenshotRef") or screenshot_ref
                d = self._build_draft(e, screenshot_ref=element_screenshot)
            if d: drafts.append(d)
        return drafts

    def _build_draft_from_enhanced(self, e: dict) -> dict:
        """
        从 enhanced 节点直接构建草稿，使用 enhanced 预计算字段。

        相比 _build_draft 的推断逻辑，此方法直接使用 enhanced 字段：
        displayName/chineseDescription/role/pageId/confidence/clickTargetNode/visualNode
        """
        import re
        nm = e.get("nodeName", "") or e.get("name", "")
        tx = e.get("text", "") or ""
        pi = e.get("pageId", "unknown")
        pc = self.PAGE_NAME_MAP.get(pi, pi)

        # 直接使用 enhanced 字段
        dn = e.get("displayName", "") or nm
        desc = e.get("chineseDescription", "")
        rl = e.get("role", "normal_action")
        sc = e.get("confidence", 0.3)
        tid = e.get("suggestedTestId", "") or (pi + "." + nm.replace(" ", ""))
        if tx: tid += "." + tx
        sid = e.get("suggestedSemanticId", "") or (pc + "." + rl)
        priority = e.get("priority", "P3")
        element_type = e.get("elementType", "")
        risk = e.get("risk", []) or []
        ct_node = e.get("clickTargetNode", "") or e.get("path", "")
        v_node = e.get("visualNode", "") or e.get("path", "")
        review_hint = e.get("reviewHint", "")
        src_name = e.get("spriteName", "") or ""
        at_name = e.get("atlasName", "") or ""
        comps = e.get("components", []) or e.get("componentTypes", []) or []
        et = e.get("componentType", "") or (comps[0] if comps else "Node")

        rc = self.ROLE_NAME_MAP.get(rl, "")
        if not dn and rc:
            dn = tx + rc if tx else rc
        if not desc:
            desc = pc + "的" + (dn or nm)
        if not review_hint:
            review_hint = "来自 enhanced_ui_tree.json；建议结构确认后做点击验证"
        if not sc:
            sc = 0.3

        # 处理 source
        item_source = "auto_draft"

        review_status = self._coerce_review_status("pending")
        info = {
            "path": e.get("path", ""),
            "nodeName": nm,
            "componentType": et,
            "clickable": e.get("clickable", False),
            "pageId": pi,
            "displayName": dn,
            "chineseDescription": desc,
            "reviewHint": review_hint,
            "suggestedTestId": tid,
            "suggestedSemanticId": sid,
            "role": rl,
            "roleNameCn": self.ROLE_NAME_MAP.get(rl, rl),
            "confidence": round(min(sc, 1.0), 2),
            "source": item_source,
            "dataSource": "enhanced_ui_tree",
            "priority": priority,
            "elementType": element_type,
            "clickTargetNode": ct_node,
            "visualNode": v_node,
            "risk": risk,
            "spriteName": src_name,
            "atlasName": at_name,
            "components": comps,
            "reviewStatus": review_status,
            "reviewLevel": self._coerce_review_level(review_status),
        }
        return info

    def _build_draft(self, e, screenshot_ref=""):
        """为单个元素构建映射草稿"""
        import re
        nm = e.get("name",""); tx = e.get("text","")
        et = e.get("type","Node"); sr = e.get("screenRect",[])
        ca = e.get("canvas","")
        pi = ca if ca and ca != "Canvas" else (e.get("path","").split("/")[0] or "unknown")
        pc = self.PAGE_NAME_MAP.get(pi, pi)
        nps = re.findall(r"[A-Z][a-z]*|[a-z]+|\d+", nm)
        ncm = {"Btn":"按钮","Icon":"图标","Text":"文本","Label":"标签",
               "Panel":"面板","Toggle":"开关","Close":"关闭","Confirm":"确认",
               "Cancel":"取消","Use":"使用"}
        nc = "".join(ncm.get(p,p) for p in nps) or nm
        tid = pi + "." + nm.replace(" ","")
        if tx: tid += "." + tx
        sid = pc + "." + nc
        if tx: sid += "." + tx
        ln,lt = nm.lower(),(tx or "").lower()
        if "close" in ln: rl = "close_button"
        elif "confirm" in ln: rl = "confirm_button"
        elif "cancel" in ln: rl = "cancel_button"
        elif "btn" in ln or "button" in ln: rl = "primary_action_button"
        elif "icon" in ln: rl = "interactive_icon"
        elif et in ("Button","EventTrigger"): rl = "primary_action_button"
        else: rl = "action"
        rc = self.ROLE_NAME_MAP.get(rl,"")
        dn = tx + rc if tx and rc else (tx or nc)
        pos = ""
        if sr and len(sr)>=4:
            yc,xc = (sr[1]+sr[3])/2,(sr[0]+sr[2])/2
            if yc < 500: pos = "顶部"
            elif yc > 2000: pos = "底部"
            else: pos = "中部"
            pos += "左侧" if xc < 200 else "右侧" if xc > 900 else ""
        desc = pc + pos + "的" + dn
        if tx and dn != tx: desc += "，文字「" + tx + "」"
        rh = {"close_button":"关闭界面","confirm_button":"确认操作",
              "primary_action_button":"执行操作","interactive_icon":"打开详情"}
        if rl in rh: desc += "，用于" + rh[rl]
        hint = "截图位于" + pc + pos
        if tx: hint += "，显示「" + tx + "」"
        sc = 0.3 + (0.3 if tx else 0) + (0.2 if et in ("Button","Toggle") else 0)
        review_status = self._coerce_review_status("pending")
        flags = self._build_review_flags(e, screenshot_ref=screenshot_ref)
        return dict(
            path=e.get("path",""),
            nodeName=nm,
            componentType=et,
            clickable=e.get("clickable",False),
            pageId=pi,
            displayName=dn,
            chineseDescription=desc,
            reviewHint=hint,
            suggestedTestId=tid,
            suggestedSemanticId=sid,
            role=rl,
            confidence=round(min(sc,1.0),2),
            source="auto_draft",
            screenshotRef=screenshot_ref,
            review={
                "status": review_status,
                "level": self._coerce_review_level(review_status),
                "visualConfirmed": False,
                "clickConfirmed": False,
                "warnings": flags["reviewWarnings"],
            },
            reviewStatus=review_status,
            reviewLevel=self._coerce_review_level(review_status),
            hasScreenshot=flags["hasScreenshot"],
            hasHighlightRect=flags["hasHighlightRect"],
            visualReviewRequired=flags["visualReviewRequired"],
            clickReviewRequired=flags["clickReviewRequired"],
            reviewWarnings=flags["reviewWarnings"]
        )


def GuessIconTypeStatic(sprite_name, node_name):
    """静态图标类型推断（类外部可调用）"""
    lower = (sprite_name + " " + node_name).lower()
    if lower.find("item") >= 0: return "item"
    if lower.find("reward") >= 0: return "reward"
    if lower.find("activity") >= 0: return "activity"
    if lower.find("building") >= 0 and lower.find("icon") >= 0: return "building_icon"
    if lower.find("btn") >= 0 or lower.find("button") >= 0: return "button"
    if lower.find("resource") >= 0: return "resource"
    if lower.find("tips") >= 0: return "tips"
    return "unknown"


def test_mapping():
    """测试映射管理器"""
    print("=" * 60)
    print("ElementMappingManager 测试")
    print("=" * 60)

    mgr = ElementMappingManager()
    mgr.load()

    # 测试1：创建映射
    print("\n[测试1] 创建映射...")
    result = mgr.upsert("Canvas/BagPanel/ButtonUse", {
        "name": "ButtonUse",
        "type": "Button",
        "clickable": True,
        "displayName": "使用按钮",
        "testId": "bag.button.use",
        "role": "action",
        "pageId": "bag_page",
        "meaning": "使用选中的道具",
        "source": "manual_confirmed",
    })
    print(f"  已创建: {result['elementPath']} → testId={result['testId']}")
    assert result["testId"] == "bag.button.use"
    print("  ✅ 通过")

    # 测试2：统计
    print("\n[测试2] 统计...")
    stats = mgr.stats()
    print(f"  总映射数: {stats['totalMappings']}")
    print(f"  手动确认: {stats['manualConfirmed']}")
    print(f"  含 testId: {stats['withTestId']}")
    print("  ✅ 通过")

    # 测试3：反查
    print("\n[测试3] 截图反查...")
    test_elements = [
        {"name": "Root", "path": "Root", "screenRect": [0, 0, 1170, 2532], "depth": 0},
        {"name": "BagBtn", "path": "Canvas/BagBtn", "screenRect": [980, 2000, 1080, 2200], "depth": 2},
        {"name": "ButtonUse", "path": "Canvas/BagPanel/ButtonUse",
         "screenRect": [464, 2380, 706, 2490], "depth": 3},
    ]
    candidates = mgr.reverse_lookup(585, 2435, test_elements)
    print(f"  点击 (585,2435) 命中 {len(candidates)} 个候选:")
    for c in candidates:
        print(f"    {c['name']:20s} path={c['path']} area={c['area']}")
    assert len(candidates) >= 2  # 应命中 Root + ButtonUse
    assert candidates[0]["name"] == "ButtonUse"  # 最精确的排第一
    print("  ✅ 通过")

    # 测试4：未映射元素
    print("\n[测试4] 未映射元素...")
    unmapped = mgr.get_unmapped_elements(test_elements)
    print(f"  未映射的关键元素: {len(unmapped)} 个")
    for el in unmapped:
        print(f"    {el['name']:20s} path={el['path']}")
    print("  ✅ 通过")

    # 清理测试数据
    mgr.delete("Canvas/BagPanel/ButtonUse")

    print("\n" + "=" * 60)
    print("测试完成 ✅")
    print("=" * 60)


if __name__ == "__main__":
    test_mapping()
