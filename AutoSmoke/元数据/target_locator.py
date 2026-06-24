#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSmoke - 目标定位器（可测试性元数据驱动）

优先级链路（按文档 4.1 节）：
  1. testId → metadata_reader → screenRect/normalizedCenter
  2. Poco/UI 树 → 元素名/坐标
  3. 模板匹配 → 固定图标
  4. 大号关键文字 OCR
  5. normalized/design 坐标兜底

使用方式：
    locator = TargetLocator()
    result = locator.locate({"type": "testId", "value": "bag.button.use"})
    result = locator.locate({"type": "text", "value": "使用"})
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class TargetLocator:
    """
    目标定位器

    根据目标描述，按优先级链路依次尝试定位，
    返回统一格式的定位结果。
    """

    def __init__(self, mapper=None, metadata_reader=None):
        self._mapper = mapper
        self._reader = metadata_reader
        self._vision = None
        self._poco = None

    # ============================================================
    # 主入口
    # ============================================================

    def locate(self, target: Dict, game_content_img=None) -> Dict:
        """
        按优先级链路定位目标

        :param target: 目标描述
            {"type": "testId", "value": "bag.button.use"}
            {"type": "text", "value": "使用"}
            {"type": "normalized", "nx": 0.5, "ny": 0.5}
        :param game_content_img: gameContent 截图（用于 OCR/模板）
        :return: {"ok": True, "x": 160, "y": 665, "detail": {...}}
        """
        if not target:
            return {"ok": False, "error": "无目标", "source": "none"}

        ttype = target.get("type", "")
        mapper = self._get_mapper()
        if not mapper:
            return {"ok": False, "error": "CoordinateMapper 未就绪", "source": "none"}

        # ── 优先链路 1：坐标类（不依赖元数据）──
        if ttype in ("normalized", "design", "content", "pixel"):
            return self._locate_coordinate(target, mapper)

        # ── 优先链路 2：metadata testId ──
        if ttype == "testId":
            result = self._locate_by_testid(target["value"], mapper)
            if result["ok"]:
                logger.info("testId 定位成功: %s → center=%s",
                           target["value"], result.get("detail", {}).get("center"))
                return result
            logger.warning("testId 未找到: %s, 降级: %s",
                          target["value"], result.get("error", ""))

        # ── 优先链路 3：Poco ──
        if ttype == "poco":
            result = self._locate_by_poco(target.get("value", ""), mapper)
            if result["ok"]:
                logger.info("Poco 定位成功: %s", target.get("value", ""))
                return result

        # ── 优先链路 4：模板匹配 ──
        if ttype == "template":
            result = self._locate_by_template(
                target.get("value", ""), game_content_img, mapper
            )
            if result["ok"]:
                logger.info("模板匹配成功: %s", target.get("value", ""))
                return result

        # ── 优先链路 5：OCR 文字 ──
        if ttype == "text" and game_content_img is not None:
            result = self._locate_by_ocr(
                target.get("value", ""), game_content_img, mapper
            )
            if result["ok"]:
                logger.info("OCR 定位成功: %s", target.get("value", ""))
                return result

        # ── 全部失败：降级到 normalized 兜底 ──
        if ttype in ("testId", "poco", "template", "text"):
            # 检查 metadata 中是否有 testId 前缀匹配
            if ttype == "testId":
                reader = self._get_reader()
                if reader and reader.load():
                    candidates = reader.find_by_testid_prefix(target["value"])
                    if candidates:
                        logger.info("testId 前缀匹配: %s → %d 个候选",
                                   target["value"], len(candidates))
                        return {
                            "ok": True,
                            "x": 0, "y": 0,
                            "candidates": candidates,
                            "message": f"找到 {len(candidates)} 个 testId 前缀匹配",
                            "source": "testid_prefix",
                        }

            return {
                "ok": False,
                "error": f"全部链路失败: {ttype}('{target.get('value', '')}')",
                "source": "none",
                "target": target,
            }

        # ── 未知类型 ──
        return {"ok": False, "error": f"未知定位类型: {ttype}", "source": "none"}

    # ============================================================
    # 链路 1：坐标类
    # ============================================================

    def _locate_coordinate(self, target: Dict, mapper) -> Dict:
        ttype = target.get("type", "")
        if ttype == "normalized":
            nx, ny = target["nx"], target["ny"]
            sx, sy = mapper.normalized_to_screen(nx, ny)
            cx, cy = mapper.screen_to_content(sx, sy)
            return {
                "ok": True, "x": round(cx, 1), "y": round(cy, 1),
                "region": None,
                "source": "normalized",
                "detail": {"type": "normalized", "nx": nx, "ny": ny,
                          "screen": [sx, sy], "content": [round(cx, 1), round(cy, 1)]},
            }
        if ttype == "design":
            dx, dy = int(target["x"]), int(target["y"])
            sx, sy = mapper.design_to_screen(dx, dy)
            cx, cy = mapper.screen_to_content(sx, sy)
            return {
                "ok": True, "x": round(cx, 1), "y": round(cy, 1),
                "region": None,
                "source": "design",
                "detail": {"type": "design", "x": dx, "y": dy,
                          "screen": [sx, sy], "content": [round(cx, 1), round(cy, 1)]},
            }
        if ttype == "content":
            return {
                "ok": True, "x": target["x"], "y": target["y"],
                "region": None,
                "source": "content",
                "detail": {"type": "content", "x": target["x"], "y": target["y"]},
            }
        if ttype == "pixel":
            return {
                "ok": True, "x": target["x"], "y": target["y"],
                "region": None,
                "source": "pixel",
                "detail": {"type": "pixel", "x": target["x"], "y": target["y"]},
            }
        return {"ok": False, "error": f"未知坐标类型: {ttype}", "source": "none"}

    # ============================================================
    # 链路 2：metadata testId
    # ============================================================

    def _locate_by_testid(self, testid: str, mapper) -> Dict:
        formal_result = self._locate_by_formal_mapping(testid, mapper)
        if formal_result["ok"]:
            return formal_result

        reader = self._get_reader()
        if not reader or not reader.load():
            return {"ok": False, "error": "metadata_reader 未就绪", "source": "testid"}

        element = reader.find_by_testid(testid)
        if not element:
            return {"ok": False, "error": f"testId 未找到: {testid}",
                    "source": "testid"}

        # 验证元素
        verify = reader.verify_target(element)
        if not verify["ok"]:
            return {"ok": False, "error": verify["reason"], "source": "testid",
                    "element": element}

        # 获取归一化中心坐标 → 转 content 坐标
        norm = reader.get_normalized_center(element)
        if norm:
            sx, sy = mapper.normalized_to_screen(norm[0], norm[1])
            cx, cy = mapper.screen_to_content(sx, sy)
            return {
                "ok": True, "x": round(cx, 1), "y": round(cy, 1),
                "region": reader.get_screen_rect(element),
                "source": "testid",
                "confidence": 1.0,
                "detail": {
                    "type": "testId",
                    "value": testid,
                    "name": element.get("name", ""),
                    "path": element.get("path", ""),
                    "screenRect": reader.get_screen_rect(element),
                    "center": verify["center"],
                    "normalizedCenter": norm,
                    "clickable": element.get("clickable", False),
                    "clickableReason": element.get("clickableReason", ""),
                },
            }
        else:
            return {"ok": True, "x": 0, "y": 0,
                    "source": "testid_nocenter",
                    "detail": {"type": "testId", "value": testid,
                              "path": element.get("path", "")},
                     "region": reader.get_screen_rect(element)}

    def _locate_by_formal_mapping(self, testid: str, mapper) -> Dict:
        formal = self._load_formal_mapping(testid)
        if not formal:
            return {"ok": False, "error": f"formal mapping 未找到: {testid}", "source": "formal_mapping"}

        screen_rect = self._formal_screen_rect(formal)
        if not screen_rect:
            locator = formal.get("locator") if isinstance(formal.get("locator"), dict) else {}
            if locator.get("type") and locator.get("value"):
                return {
                    "ok": True,
                    "x": 0,
                    "y": 0,
                    "region": None,
                    "source": "formal_mapping_locator",
                    "confidence": 0.95,
                    "detail": {
                        "type": "testId",
                        "value": testid,
                        "name": formal.get("displayName") or formal.get("targetName", ""),
                        "path": formal.get("elementPath", ""),
                        "locator": locator,
                        "screenRect": [],
                        "reviewStatus": formal.get("reviewStatus", ""),
                        "evidenceRef": formal.get("evidenceRef", ""),
                    },
                }
            return {"ok": False, "error": f"formal mapping 缺少 screenRect: {testid}", "source": "formal_mapping"}

        try:
            x1, y1, x2, y2 = [float(v) for v in screen_rect]
            sx = (x1 + x2) / 2.0
            sy = (y1 + y2) / 2.0
            cx, cy = mapper.screen_to_content(sx, sy)
            return {
                "ok": True,
                "x": round(cx, 1),
                "y": round(cy, 1),
                "region": [x1, y1, x2, y2],
                "source": "formal_mapping",
                "confidence": 1.0,
                "detail": {
                    "type": "testId",
                    "value": testid,
                    "name": formal.get("displayName") or formal.get("targetName", ""),
                    "path": formal.get("elementPath", ""),
                    "locator": formal.get("locator", {}),
                    "screenRect": [x1, y1, x2, y2],
                    "center": [sx, sy],
                    "content": [round(cx, 1), round(cy, 1)],
                    "reviewStatus": formal.get("reviewStatus", ""),
                    "evidenceRef": formal.get("evidenceRef", ""),
                },
            }
        except Exception as exc:
            return {"ok": False, "error": f"formal mapping 坐标转换失败: {exc}", "source": "formal_mapping"}

    def _load_formal_mapping(self, testid: str) -> Optional[Dict]:
        try:
            from 元数据.mapping_store import MappingStore
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            item = MappingStore(project_root=base_dir).get_formal_by_testid(testid)
        except Exception:
            item = None
        if not isinstance(item, dict):
            return None
        status = str(item.get("reviewStatus", "")).lower()
        if status and status not in ("click_confirmed", "confirmed", "approved", "case_verified", "manual_confirmed", "template"):
            return None
        return item

    def _formal_screen_rect(self, formal: Dict) -> Optional[List[float]]:
        for locator in formal.get("fallbackLocators") or []:
            if not isinstance(locator, dict):
                continue
            if locator.get("type") == "screenRect" and self._is_screen_rect(locator.get("value")):
                return locator.get("value")
            if locator.get("type") == "runtimeHint":
                hint = locator.get("value") if isinstance(locator.get("value"), dict) else {}
                rect = hint.get("screenRect")
                if self._is_screen_rect(rect):
                    return rect
        hint = formal.get("runtimeHint") if isinstance(formal.get("runtimeHint"), dict) else {}
        rect = hint.get("screenRect")
        if self._is_screen_rect(rect):
            return rect
        return None

    @staticmethod
    def _is_screen_rect(value) -> bool:
        if not isinstance(value, list) or len(value) != 4:
            return False
        return all(isinstance(v, (int, float)) for v in value)

    # ============================================================
    # 链路 3：Poco（封装已有的 Poco SDK 调用）
    # ============================================================

    def _locate_by_poco(self, name: str, mapper) -> Dict:
        try:
            from poco_connector.poco_connector import PocoConnector
            connector = PocoConnector(device_type="Windows")
            if not connector.connect():
                return {"ok": False, "error": "Poco 连接失败", "source": "poco"}

            ui_tree = connector.dump_ui_tree()
            connector.close()

            if not ui_tree:
                return {"ok": False, "error": "Poco dump 失败", "source": "poco"}

            # 搜索 UI 树
            def search(node, depth=0):
                if not isinstance(node, dict):
                    return []
                results = []
                node_name = node.get("name", "")
                p = node.get("payload", {})
                pos = p.get("pos", [0.5, 0.5])
                visible = p.get("visible", False)

                if name.lower() in node_name.lower() and visible:
                    results.append({"name": node_name, "pos": pos,
                                   "size": p.get("size", [0, 0])})

                for ch in node.get("children", []):
                    results.extend(search(ch, depth + 1))
                return results

            matches = search(ui_tree)
            if not matches:
                return {"ok": False, "error": f"Poco 未找到: {name}",
                        "source": "poco"}

            # 取第一个匹配
            m = matches[0]
            nx, ny = m["pos"][0], m["pos"][1]
            sx, sy = mapper.normalized_to_screen(nx, ny)
            cx, cy = mapper.screen_to_content(sx, sy)
            return {
                "ok": True, "x": round(cx, 1), "y": round(cy, 1),
                "region": None,
                "source": "poco",
                "confidence": 0.8,
                "detail": {"type": "poco", "value": name,
                          "matchedName": m["name"],
                          "normalizedPos": [nx, ny],
                          "screen": [sx, sy],
                          "content": [round(cx, 1), round(cy, 1)]},
            }
        except Exception as e:
            logger.warning("Poco 定位异常: %s", e)
            return {"ok": False, "error": str(e), "source": "poco"}

    # ============================================================
    # 链路 4：模板匹配
    # ============================================================

    def _locate_by_template(self, template_name: str,
                            game_content_img, mapper) -> Dict:
        if game_content_img is None:
            return {"ok": False, "error": "需要 gameContent 截图", "source": "template"}
        try:
            from 视觉识别.game_content_vision import GameContentVision
            vision = self._get_vision()
            result = vision.match_template(game_content_img, template_name)
            if result:
                cx, cy = result["center"]
                return {
                    "ok": True, "x": cx, "y": cy,
                    "region": result.get("rect"),
                    "source": "template",
                    "confidence": result.get("confidence", 0.5),
                    "detail": {"type": "template", "value": template_name,
                              "rect": result.get("rect"),
                              "confidence": result.get("confidence", 0.5)},
                }
            return {"ok": False, "error": f"模板匹配未找到: {template_name}",
                    "source": "template"}
        except Exception as e:
            logger.warning("模板匹配异常: %s", e)
            return {"ok": False, "error": str(e), "source": "template"}

    # ============================================================
    # 链路 5：OCR
    # ============================================================

    def _locate_by_ocr(self, text: str, game_content_img, mapper) -> Dict:
        if game_content_img is None:
            return {"ok": False, "error": "需要 gameContent 截图", "source": "ocr"}
        try:
            from 视觉识别.game_content_vision import GameContentVision
            vision = self._get_vision()
            result = vision.ocr_find_text(game_content_img, text)
            if result:
                return {
                    "ok": True,
                    "x": result["center"][0],
                    "y": result["center"][1],
                    "region": result.get("rect"),
                    "source": "ocr",
                    "confidence": result.get("confidence", 0.5),
                    "detail": {"type": "ocr", "value": text,
                              "center": result["center"],
                              "confidence": result.get("confidence", 0.5)},
                }
            return {"ok": False, "error": f"OCR 未找到: {text}", "source": "ocr"}
        except Exception as e:
            logger.warning("OCR 定位异常: %s", e)
            return {"ok": False, "error": str(e), "source": "ocr"}

    # ============================================================
    # 工具
    # ============================================================

    def _get_mapper(self):
        if self._mapper is None:
            try:
                from 坐标截图.coordinate_mapper import CoordinateMapper
                self._mapper = CoordinateMapper.from_config()
            except Exception:
                pass
        return self._mapper

    def _get_reader(self):
        if self._reader is None:
            try:
                from 元数据.metadata_reader import MetadataReader
                self._reader = MetadataReader()
            except Exception:
                pass
        return self._reader

    def _get_vision(self):
        if self._vision is None:
            try:
                from 视觉识别.game_content_vision import GameContentVision
                self._vision = GameContentVision()
            except Exception:
                pass
        return self._vision


# ============================================================
# 测试
# ============================================================

def test_locator():
    """测试目标定位器"""
    print("=" * 60)
    print("TargetLocator 测试")
    print("=" * 60)

    locator = TargetLocator()
    mapper = locator._get_mapper()
    if not mapper:
        print("❌ CoordinateMapper 未就绪")
        return

    # 测试1：坐标定位
    print("\n[测试1] 坐标定位...")
    tests = [
        ("normalized", {"type": "normalized", "nx": 0.5, "ny": 0.5}),
        ("design", {"type": "design", "x": 585, "y": 1266}),
        ("content", {"type": "content", "x": 159, "y": 344}),
    ]
    for name, target in tests:
        result = locator.locate(target)
        icon = "✅" if result["ok"] else "❌"
        print(f"  {icon} {name:12s} → x={result.get('x'):.1f} y={result.get('y'):.1f} src={result.get('source','?')}")

    # 测试2：testId 定位（依赖 metadata）
    print("\n[测试2] testId 定位...")
    testid_target = {"type": "testId", "value": "bag.button.use"}
    result = locator.locate(testid_target)
    print(f"  {'✅' if result['ok'] else '❌'} testId(\"bag.button.use\")")
    if result["ok"]:
        print(f"    path: {result['detail'].get('path', '?')}")
        print(f"    screenRect: {result.get('region')}")
    else:
        print(f"    降级: {result.get('error', '?')}")

    # 测试3：OCR 定位（需要截图）
    print("\n[测试3] OCR/文字定位...")
    try:
        from 坐标截图.screenshot_game_content import GameContentScreenshot
        capturer = GameContentScreenshot(mapper=mapper)
        cap = capturer.capture()
        img = cap.get("game_content_image")
        if img:
            text_target = {"type": "text", "value": "背包"}
            result = locator.locate(text_target, game_content_img=img)
            print(f"  {'✅' if result['ok'] else '❌'} text(\"背包\") → "
                  f"x={result.get('x'):.1f} y={result.get('y'):.1f} "
                  f"conf={result.get('confidence', '?'):.2f} "
                  f"src={result.get('source','?')}")
        else:
            print("  ⚠  截图失败，跳过")
    except Exception as e:
        print(f"  ⚠ 截图/OCR 异常: {e}")

    # 测试4：metadata 摘要
    print("\n[测试4] metadata 状态...")
    reader = locator._get_reader()
    if reader and reader.load():
        from 元数据.metadata_reader import MetadataReader
        print(f"  场景: {reader.get_current_scene_id()}")
        print(f"  页面: {reader.get_current_page_id()}")
        print(f"  元素: {reader.get_total_elements()} 个")
        print(f"  可点击: {len(reader.find_clickable())} 个")
    else:
        print("  ⚠ metadata 未就绪")

    print("\n" + "=" * 60)
    print("测试完成 ✅")
    print("=" * 60)


if __name__ == "__main__":
    test_locator()
