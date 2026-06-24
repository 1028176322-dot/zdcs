#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSmoke - 可测试性元数据读取器

读取 Unity Editor 导出的 current_ui.json / current_state.json，
提供增强的 UI 树定位能力（testId / pageId / clickable 修正）。

与 Unity 侧的 AutoSmokeMetadataExporter.cs 配套使用。
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# 默认元数据路径
CONFIG_DIR = os.path.join(os.environ.get("USERPROFILE", "."), ".autosmoke")
METADATA_DIR = os.path.join(CONFIG_DIR, "metadata")
UI_JSON_PATH = os.path.join(METADATA_DIR, "current_ui.json")
STATE_JSON_PATH = os.path.join(METADATA_DIR, "current_state.json")


class MetadataReader:
    """
    可测试性元数据读取器

    从 Unity 导出的元数据文件中读取 UI 元素和状态信息，
    支持 testId / name / pageId 搜索。

    使用方式：
        reader = MetadataReader()
        all_elements = reader.get_elements()
        btn = reader.find_by_testid("bag.button.use")
        page = reader.get_current_page()
    """

    def __init__(self, ui_json_path: str = None, state_json_path: str = None):
        self._ui_json_path = ui_json_path or UI_JSON_PATH
        self._state_json_path = state_json_path or STATE_JSON_PATH
        self._ui_cache: Optional[Dict] = None
        self._state_cache: Optional[Dict] = None
        self._index_built = False
        self._by_testid: Dict[str, Dict] = {}
        self._by_name: Dict[str, List[Dict]] = {}
        self._by_type: Dict[str, List[Dict]] = {}

    # ============================================================
    # 加载
    # ============================================================

    def load(self, force: bool = False) -> bool:
        """
        加载最新的元数据文件

        :param force: 是否强制重新读取文件
        :return: 是否成功加载
        """
        changed = False

        # 加载 UI 元数据
        if force or self._ui_cache is None:
            ui_data = self._load_json(self._ui_json_path)
            if ui_data is not None:
                self._ui_cache = ui_data
                changed = True
                logger.info("已加载 UI 元数据: %d 个元素 (来源: %s)",
                           ui_data.get("totalElements", 0), self._ui_json_path)

        # 加载状态元数据
        if force or self._state_cache is None:
            state_data = self._load_json(self._state_json_path)
            if state_data is not None:
                self._state_cache = state_data
                changed = True
                logger.info("已加载状态元数据: pageId=%s",
                           state_data.get("currentPageId", "?"))

        # 重建索引
        if changed:
            self._rebuild_index()

        return self._ui_cache is not None or self._state_cache is not None

    def reload(self) -> bool:
        """强制重新加载（等同于 load(force=True)）"""
        return self.load(force=True)

    def _load_json(self, path: str) -> Optional[Dict]:
        """从文件加载 JSON"""
        if not os.path.exists(path):
            logger.debug("元数据文件不存在: %s", path)
            return None
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("读取元数据文件失败 %s: %s", path, e)
            return None

    def _rebuild_index(self):
        """重建搜索索引"""
        self._by_testid.clear()
        self._by_name.clear()
        self._by_type.clear()

        elements = self.get_elements()
        for el in elements:
            # testId 索引
            testid = el.get("testId")
            if testid:
                self._by_testid[testid] = el

            # name 索引
            name = el.get("name", "")
            if name:
                if name not in self._by_name:
                    self._by_name[name] = []
                self._by_name[name].append(el)

            # type 索引
            etype = el.get("type", "")
            if etype:
                if etype not in self._by_type:
                    self._by_type[etype] = []
                self._by_type[etype].append(el)

        self._index_built = True

    # ============================================================
    # 数据读取
    # ============================================================

    def get_elements(self) -> List[Dict]:
        """获取所有 UI 元素列表"""
        if self._ui_cache is None:
            return []
        return self._ui_cache.get("elements", [])

    def get_total_elements(self) -> int:
        """获取 UI 元素总数"""
        if self._ui_cache is None:
            return 0
        return self._ui_cache.get("totalElements", 0)

    def get_export_time(self) -> Optional[str]:
        """获取导出时间"""
        if self._ui_cache:
            return self._ui_cache.get("exportTime")
        return None

    def get_game_resolution(self) -> tuple:
        """获取游戏设计分辨率 (width, height)"""
        if self._ui_cache:
            res = self._ui_cache.get("gameResolution")
            if res and len(res) >= 2:
                return (res[0], res[1])
        return (1170, 2532)

    # ============================================================
    # 按 testId 搜索
    # ============================================================

    def find_by_testid(self, testid: str) -> Optional[Dict]:
        """
        按 testId 查找 UI 元素

        :param testid: testId 值，如 "bag.button.use"
        :return: 元素字典，未找到返回 None
        """
        if not self._index_built:
            self._rebuild_index()
        return self._by_testid.get(testid)

    def find_by_testid_prefix(self, prefix: str) -> List[Dict]:
        """
        按 testId 前缀查找

        :param prefix: 前缀，如 "bag." 或 "maincity."
        :return: 匹配的元素列表
        """
        if not self._index_built:
            self._rebuild_index()
        results = []
        for tid, el in self._by_testid.items():
            if tid.startswith(prefix):
                results.append(el)
        return results

    # ============================================================
    # 按名称搜索
    # ============================================================

    def find_by_name(self, name: str) -> List[Dict]:
        """按元素名称查找（可能有多个同名）"""
        if not self._index_built:
            self._rebuild_index()
        return self._by_name.get(name, [])

    def find_by_name_contains(self, keyword: str) -> List[Dict]:
        """按名称关键词查找"""
        if not self._index_built:
            self._rebuild_index()
        results = []
        for name, elements in self._by_name.items():
            if keyword.lower() in name.lower():
                results.extend(elements)
        return results

    # ============================================================
    # 按类型搜索
    # ============================================================

    def find_by_type(self, etype: str) -> List[Dict]:
        """按推断类型查找（Button / Text / Image / Node 等）"""
        if not self._index_built:
            self._rebuild_index()
        return self._by_type.get(etype, [])

    def find_clickable(self) -> List[Dict]:
        """查找所有可点击元素"""
        elements = self.get_elements()
        return [el for el in elements if el.get("clickable")]

    def find_buttons(self) -> List[Dict]:
        """查找所有 Button 类型元素"""
        return self.find_by_type("Button")

    def find_by_path_contains(self, keyword: str) -> List[Dict]:
        """按路径包含关键词查找"""
        elements = self.get_elements()
        return [el for el in elements
                if keyword.lower() in el.get("path", "").lower()]

    # ============================================================
    # 状态读取
    # ============================================================

    def get_current_page_id(self) -> str:
        """获取当前页面 ID"""
        if self._state_cache:
            return self._state_cache.get("currentPageId", "unknown")
        return "unknown"

    def get_current_scene_name(self) -> str:
        """获取当前场景名称"""
        if self._state_cache:
            return self._state_cache.get("sceneName", "unknown")
        return "unknown"

    def get_current_scene_id(self) -> str:
        """获取当前场景 ID"""
        if self._state_cache:
            return self._state_cache.get("sceneId", "unknown_scene")
        return "unknown_scene"

    def is_playing(self) -> bool:
        """是否在 Play Mode"""
        if self._state_cache:
            return self._state_cache.get("isPlaying", False)
        return False

    def get_popups(self) -> List[Dict]:
        """获取当前弹窗列表"""
        if self._state_cache:
            return self._state_cache.get("popups", [])
        return []

    def has_active_popup(self) -> bool:
        """是否存在活跃弹窗"""
        return len(self.get_popups()) > 0

    # ============================================================
    # 定位辅助
    # ============================================================

    def get_screen_rect(self, element: Dict) -> Optional[tuple]:
        """
        获取元素的 screenRect（设计坐标）

        :param element: 元素字典
        :return: (left, top, right, bottom) 或 None
        """
        rect = element.get("screenRect")
        if rect and len(rect) >= 4:
            return (rect[0], rect[1], rect[2], rect[3])
        return None

    def get_center(self, element: Dict) -> Optional[tuple]:
        """
        获取元素中心点（设计坐标）

        :param element: 元素字典
        :return: (center_x, center_y) 或 None
        """
        rect = self.get_screen_rect(element)
        if rect:
            cx = (rect[0] + rect[2]) // 2
            cy = (rect[1] + rect[3]) // 2
            return (cx, cy)
        return None

    def get_normalized_center(self, element: Dict) -> Optional[tuple]:
        """
        获取元素归一化中心坐标

        :param element: 元素字典
        :return: (nx, ny) 0~1 或 None
        """
        rect = element.get("normalizedRect")
        if rect and len(rect) >= 4:
            nx = rect[0] + rect[2] / 2
            ny = rect[1] + rect[3] / 2
            return (round(nx, 4), round(ny, 4))
        # 降级计算
        sr = self.get_screen_rect(element)
        if sr:
            gw, gh = self.get_game_resolution()
            nx = ((sr[0] + sr[2]) / 2) / gw
            ny = ((sr[1] + sr[3]) / 2) / gh
            return (round(nx, 4), round(ny, 4))
        return None

    def verify_target(self, element: Dict) -> Dict:
        """
        验证目标元素是否可用

        :param element: 元素字典
        :return: {"ok": bool, "reason": str, ...}
        """
        if not element:
            return {"ok": False, "reason": "元素为空"}
        if not element.get("visible", False):
            return {"ok": False, "reason": "元素不可见"}
        if not element.get("clickable", False):
            return {"ok": False, "reason": "元素不可点击"}
        rect = self.get_screen_rect(element)
        if not rect:
            return {"ok": False, "reason": "缺少 screenRect"}
        if (rect[2] - rect[0]) <= 0 or (rect[3] - rect[1]) <= 0:
            return {"ok": False, "reason": "screenRect 尺寸无效"}
        center = self.get_center(element)
        return {
            "ok": True,
            "reason": "可用",
            "screenRect": rect,
            "center": center,
            "normalizedCenter": self.get_normalized_center(element),
        }

    # ============================================================
    # 摘要
    # ============================================================

    def summary(self) -> str:
        """返回元数据状态摘要"""
        lines = []
        lines.append("─" * 50)
        lines.append("📋 可测试性元数据摘要")
        lines.append("─" * 50)

        # UI 元数据
        if self._ui_cache:
            lines.append(f"  导出时间: {self._ui_cache.get('exportTime', '?')}")
            lines.append(f"  UI 元素: {self._ui_cache.get('totalElements', 0)} 个")
            lines.append(f"  Game 分辨率: {self._ui_cache.get('gameResolution', '?')}")
            lines.append(f"  Screen 分辨率: {self._ui_cache.get('screenResolution', '?')}")
            lines.append(f"  当前页面: {self._ui_cache.get('currentPageId', '?')}")

            # 类型统计
            elements = self.get_elements()
            type_counts = {}
            clickable_count = 0
            for el in elements:
                etype = el.get("type", "?")
                type_counts[etype] = type_counts.get(etype, 0) + 1
                if el.get("clickable"):
                    clickable_count += 1

            lines.append(f"  可点击元素: {clickable_count} 个")
            lines.append(f"  类型分布:")
            for t, c in sorted(type_counts.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"    {t}: {c}")
        else:
            lines.append("  ⚠️ UI 元数据未加载")

        # 状态元数据
        if self._state_cache:
            lines.append(f"  场景: {self._state_cache.get('sceneName', '?')}")
            lines.append(f"  弹窗: {self._state_cache.get('popupCount', 0)} 个")
        else:
            lines.append("  ⚠️ 状态元数据未加载")

        lines.append("─" * 50)
        return "\n".join(lines)

    def search_elements(self, query: str) -> List[Dict]:
        """
        综合搜索（testId / name / path / text）

        :param query: 搜索关键词
        :return: 匹配元素列表
        """
        results = []
        q = query.lower()

        # 精确 testId
        el = self.find_by_testid(query)
        if el:
            results.append(el)

        # testId 前缀
        results.extend(self.find_by_testid_prefix(query))

        # 名称包含
        results.extend(self.find_by_name_contains(q))

        # 路径包含
        results.extend(self.find_by_path_contains(q))

        # 文本包含
        elements = self.get_elements()
        for el in elements:
            text = el.get("text", "")
            if text and q in text.lower():
                if el not in results:
                    results.append(el)

        return results


# ============================================================
# 测试
# ============================================================

def test_reader():
    """测试元数据读取器"""
    print("=" * 60)
    print("MetadataReader 测试")
    print("=" * 60)

    reader = MetadataReader()

    # 测试1：加载
    print("\n[测试1] 加载元数据...")
    loaded = reader.load()
    print(f"  加载成功: {loaded}")
    print(f"  UI 文件存在: {os.path.exists(UI_JSON_PATH)}")
    print(f"  State 文件存在: {os.path.exists(STATE_JSON_PATH)}")

    if not loaded:
        print("  ⚠️  元数据文件不存在，请确保 Unity 已编译并运行 AutoSmokeMetadataExporter.cs")
        print("  → 菜单触发: AutoSmoke > Export Metadata")
        print("  → 或等待自动导出（每 3 秒）")
        print("\n  ⏭ 跳过后续测试")
        return

    # 测试2：摘要
    print("\n[测试2] 摘要信息...")
    print(reader.summary())
    assert reader.get_total_elements() > 0
    print("  ✅ 通过")

    # 测试3：搜索功能
    print("\n[测试3] 搜索功能...")
    clickable = reader.find_clickable()
    print(f"  可点击元素: {len(clickable)} 个")

    buttons = reader.find_buttons()
    print(f"  Button 类型: {len(buttons)} 个")

    # 按名称搜索
    if clickable:
        sample = clickable[0]
        name = sample.get("name", "")
        by_name = reader.find_by_name(name)
        print(f"  按名称 \"{name}\": 找到 {len(by_name)} 个")

        # 验证
        verify = reader.verify_target(sample)
        print(f"  验证目标: {verify.get('ok')} - {verify.get('reason')}")

    # 测试4：testId 搜索
    print("\n[测试4] testId 搜索...")
    # 列出所有含 testId 的元素
    testid_elements = []
    for el in reader.get_elements():
        if el.get("testId"):
            testid_elements.append(el)
    print(f"  含 testId 元素: {len(testid_elements)} 个")
    for el in testid_elements[:10]:
        print(f"    {el['testId']:40s} name={el.get('name','')}")

    # 测试5：状态信息
    print("\n[测试5] 状态信息...")
    print(f"  当前页面: {reader.get_current_page_id()}")
    print(f"  当前场景: {reader.get_current_scene_name()}")
    print(f"  Play Mode: {reader.is_playing()}")
    print(f"  弹窗数量: {len(reader.get_popups())}")

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)


def cli_search():
    """CLI 搜索工具"""
    import argparse
    parser = argparse.ArgumentParser(description="元数据搜索")
    parser.add_argument("query", type=str, nargs="?", help="搜索关键词")
    parser.add_argument("--type", "-t", type=str, help="按类型过滤")
    parser.add_argument("--clickable", "-c", action="store_true", help="仅可点击元素")
    parser.add_argument("--limit", "-l", type=int, default=20, help="输出数量限制")
    args = parser.parse_args()

    reader = MetadataReader()
    if not reader.load():
        print("❌ 无法加载元数据，请确保 Unity 已编译并运行")
        return

    if args.query:
        results = reader.search_elements(args.query)
    elif args.type:
        results = reader.find_by_type(args.type)
    elif args.clickable:
        results = reader.find_clickable()
    else:
        print(reader.summary())
        return

    if args.type and not args.query:
        pass  # already filtered
    if args.clickable:
        results = [r for r in results if r.get("clickable")]

    # 去重
    seen = set()
    unique = []
    for r in results:
        key = r.get("path", id(r))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    results = unique[:args.limit]

    if not results:
        print("未找到匹配元素")
        return

    print(f"找到 {len(results)} 个元素:\n")
    for i, el in enumerate(results):
        clickable = "🖱️" if el.get("clickable") else "  "
        etype = el.get("type", "?")
        name = el.get("name", "")
        path = el.get("path", "")
        rect = el.get("screenRect", "")
        center = reader.get_center(el)
        norm = reader.get_normalized_center(el)

        print(f"  {i+1:2d}. {clickable} [{etype:8s}] {name}")
        print(f"       路径: {path}")
        print(f"       testId: {el.get('testId', '-')}")
        print(f"       文本:  {el.get('text', '-')}")
        if rect:
            print(f"       screenRect: {rect}")
        if center:
            print(f"       中心: design({center[0]}, {center[1]})")
        if norm:
            print(f"       归一化: ({norm[0]}, {norm[1]})")
        print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cli_search()
    else:
        test_reader()
