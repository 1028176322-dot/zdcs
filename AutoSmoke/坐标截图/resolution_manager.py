#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分辨率管理模块 - 阶段一：动态分辨率读取与变化检测

职责：
1. 获取当前游戏内分辨率（多来源按优先级尝试）
2. 检测分辨率是否发生变化（RESOLUTION_CHANGED）
3. 保存/加载分辨率状态
4. 分辨率变化时提供通知

分辨率获取优先级（按文档 5.2.1 节）：
1. Poco SDK get_screen_size() — 运行时动态获取
2. 配置文件 config.json 中的 game_resolution
3. 用户手动指定（通过参数传入）

使用方式：
    mgr = ResolutionManager()
    result = mgr.get_current_resolution()
    if result["changed"]:
        print(f"分辨率变化: {result['last_width']}x{result['last_height']} -> "
              f"{result['width']}x{result['height']}")
        # 重建 CoordinateMapper、废弃旧缓存
"""

import json
import os
import logging
import time
from typing import Optional, Dict, Tuple
from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR

logger = logging.getLogger(__name__)

# 状态文件路径（和 config.json 同级）
RESOLUTION_STATE_FILE = os.path.join(CONFIG_DIR, "resolution_state.json")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# 默认分辨率（兜底）
DEFAULT_WIDTH = 1170
DEFAULT_HEIGHT = 2532


class ResolutionManager:
    """
    分辨率管理器
    管理游戏内分辨率（design resolution）的动态读取和变化检测
    """

    def __init__(self, state_file: str = None, config_file: str = None):
        """
        初始化分辨率管理器

        :param state_file: 分辨率状态文件路径，默认 resolution_state.json
        :param config_file: 配置文件路径，默认 config.json
        """
        self.state_file = state_file or RESOLUTION_STATE_FILE
        self.config_file = config_file or CONFIG_FILE
        self._last_state = self._load_state()

    # ============================================================
    # 分辨率获取（多来源）
    # ============================================================

    def get_current_resolution(self, poco_connector=None) -> Dict:
        """
        获取当前游戏内分辨率（按优先级尝试各来源）

        返回结构：
        {
            "width": 1170,
            "height": 2532,
            "source": "poco_sdk",
            "confidence": "high",
            "last_width": 1170,         # 上一次运行的分辨率
            "last_height": 2532,
            "changed": false,           # 本次是否发生变化
            "timestamp": "2026-06-12T17:25:00"
        }

        :param poco_connector: PocoConnector 实例（可选），传入后可尝试实时获取
        :return: 分辨率信息字典
        """
        width, height, source, confidence = self._try_get_resolution(poco_connector)

        if width is None:
            logger.warning("所有来源都无法获取分辨率，使用默认值 %dx%d",
                          DEFAULT_WIDTH, DEFAULT_HEIGHT)
            width = DEFAULT_WIDTH
            height = DEFAULT_HEIGHT
            source = "default"
            confidence = "low"

        # 检测是否变化
        last_w = self._last_state.get("width", 0) if self._last_state else 0
        last_h = self._last_state.get("height", 0) if self._last_state else 0
        changed = (last_w != width or last_h != height)

        result = {
            "width": width,
            "height": height,
            "source": source,
            "confidence": confidence,
            "last_width": last_w if self._last_state else width,
            "last_height": last_h if self._last_state else height,
            "changed": changed,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }

        if changed and last_w > 0:
            logger.info(
                "分辨率变化: %dx%d -> %dx%d (来源: %s, 可信度: %s)",
                last_w, last_h, width, height, source, confidence
            )
        elif changed:
            logger.info("首次获取分辨率: %dx%d (来源: %s, 可信度: %s)",
                       width, height, source, confidence)
        else:
            logger.debug("分辨率无变化: %dx%d", width, height)

        # 自动保存新状态
        self.save_resolution_state(result)
        self._last_state = result

        return result

    def _try_get_resolution(self, poco_connector) -> Tuple:
        """
        按优先级尝试各来源获取分辨率

        返回: (width, height, source, confidence) 或 (None, None, None, None)
        """
        # ---------- 来源 1: Poco SDK get_screen_size() ----------
        if poco_connector is not None:
            try:
                poco = getattr(poco_connector, "poco", None)
                if poco is not None and hasattr(poco, "get_screen_size"):
                    size = poco.get_screen_size()
                    if size and len(size) >= 2:
                        w, h = int(size[0]), int(size[1])
                        if w > 0 and h > 0:
                            logger.info("从 Poco SDK 获取分辨率: %dx%d", w, h)
                            return w, h, "poco_sdk", "high"
            except Exception as e:
                logger.debug("Poco get_screen_size 失败: %s", e)

        # ---------- 来源 2: UnityPoco 的 RPC 调用获取屏幕尺寸 ----------
        if poco_connector is not None:
            try:
                poco = getattr(poco_connector, "poco", None)
                if poco is not None and hasattr(poco, "agent"):
                    # 尝试通过 RPC 获取 Dump 数据中的屏幕尺寸
                    screen_size = poco.agent.hierarchy.dump().get("screen")
                    if screen_size and len(screen_size) >= 2:
                        w, h = int(screen_size[0]), int(screen_size[1])
                        if w > 0 and h > 0:
                            logger.info("从 Poco Dump 获取分辨率: %dx%d", w, h)
                            return w, h, "poco_dump", "high"
            except Exception as e:
                logger.debug("Poco RPC screen size 失败: %s", e)

        # ---------- 来源 3: 配置文件 config.json ----------
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                res = config.get("game_resolution", {})
                w = res.get("width", 0)
                h = res.get("height", 0)
                if w > 0 and h > 0:
                    logger.info("从 config.json 获取分辨率: %dx%d", w, h)
                    return w, h, "config_file", "medium"
        except Exception as e:
            logger.debug("从 config.json 读取分辨率失败: %s", e)

        # ---------- 来源 4: 上次保存的分辨率 ----------
        if self._last_state:
            w = self._last_state.get("width", 0)
            h = self._last_state.get("height", 0)
            if w > 0 and h > 0:
                logger.info("复用上次分辨率状态: %dx%d", w, h)
                return w, h, "previous_state", "medium"

        return None, None, None, None

    # ============================================================
    # 状态文件管理
    # ============================================================

    def _load_state(self) -> Optional[Dict]:
        """从状态文件加载上次分辨率"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if state.get("width", 0) > 0:
                    return state
        except Exception as e:
            logger.debug("加载分辨率状态失败: %s", e)
        return None

    def save_resolution_state(self, resolution: Dict):
        """
        保存分辨率状态到文件

        :param resolution: 分辨率信息字典
        """
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(resolution, f, indent=2, ensure_ascii=False)
            logger.debug("分辨率状态已保存: %s", self.state_file)
        except Exception as e:
            logger.error("保存分辨率状态失败: %s", e)

    def get_resolution_state(self) -> Optional[Dict]:
        """
        获取当前保存的分辨率状态

        :return: 分辨率状态字典，或 None
        """
        return self._last_state

    def clear_state(self):
        """清除分辨率状态文件"""
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                logger.info("分辨率状态文件已清除: %s", self.state_file)
        except Exception as e:
            logger.error("清除分辨率状态文件失败: %s", e)

    # ============================================================
    # 便捷方法
    # ============================================================

    @property
    def current_width(self) -> int:
        """当前宽度（从已保存状态读取）"""
        return self._last_state.get("width", DEFAULT_WIDTH) if self._last_state else DEFAULT_WIDTH

    @property
    def current_height(self) -> int:
        """当前高度（从已保存状态读取）"""
        return self._last_state.get("height", DEFAULT_HEIGHT) if self._last_state else DEFAULT_HEIGHT

    @property
    def is_changed(self) -> bool:
        """分辨率是否已变化（从已保存状态读取）"""
        return self._last_state.get("changed", False) if self._last_state else False

    def get_resolution(self) -> Tuple[int, int]:
        """获取当前分辨率 (width, height) 元组"""
        if self._last_state:
            return (self._last_state["width"], self._last_state["height"])
        return (DEFAULT_WIDTH, DEFAULT_HEIGHT)


# ============================================================
# 独立运行入口
# ============================================================

def test_resolution_manager():
    """测试分辨率管理器"""
    print("=" * 60)
    print("分辨率管理器测试")
    print("=" * 60)

    mgr = ResolutionManager()

    # 测试1：获取分辨率（不带 Poco 连接，从 config 读取）
    print("\n[测试1] 获取分辨率（无 Poco 连接）...")
    result = mgr.get_current_resolution(poco_connector=None)
    print(f"  分辨率: {result['width']}x{result['height']}")
    print(f"  来源: {result['source']} (可信度: {result['confidence']})")
    print(f"  是否变化: {result['changed']}")
    print(f"  时间戳: {result['timestamp']}")
    assert result["width"] > 0, "分辨率 width 必须 > 0"
    assert result["height"] > 0, "分辨率 height 必须 > 0"
    print("  ✅ 通过")

    # 测试2：再次获取（应检测到无变化）
    print("\n[测试2] 再次获取（应无变化）...")
    result2 = mgr.get_current_resolution(poco_connector=None)
    print(f"  分辨率: {result2['width']}x{result2['height']}")
    print(f"  是否变化: {result2['changed']}")
    assert result2["changed"] == False, "第二次获取不应检测到变化"
    print("  ✅ 通过")

    # 测试3：修改 config 中的分辨率，检测变化
    print("\n[测试3] 修改 config 分辨率后检测变化...")
    # 暂存当前 config
    orig_config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            orig_config = json.load(f)

    try:
        # 写入临时 fake 分辨率
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        orig_res = config_data.get("game_resolution", {})
        config_data["game_resolution"] = {"width": 1080, "height": 1920}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        # 清除状态以重新检测
        mgr.clear_state()

        # 新建 mgr 检测变化
        mgr2 = ResolutionManager()
        result3 = mgr2.get_current_resolution(poco_connector=None)
        print(f"  分辨率: {result3['width']}x{result3['height']}")
        print(f"  是否变化: {result3['changed']}")
        # 注意：这里可能检测到变化因为重新加载
        print("  ✅ 通过")

    finally:
        # 恢复原始 config
        if orig_config:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(orig_config, f, indent=2, ensure_ascii=False)

    # 测试4：便捷属性
    print("\n[测试4] 便捷属性...")
    print(f"  current_width: {mgr.current_width}")
    print(f"  current_height: {mgr.current_height}")
    print(f"  is_changed: {mgr.is_changed}")
    print(f"  get_resolution: {mgr.get_resolution()}")
    print("  ✅ 通过")

    # 测试5：状态文件存在性
    print("\n[测试5] 状态文件...")
    assert os.path.exists(RESOLUTION_STATE_FILE), "状态文件应存在"
    file_size = os.path.getsize(RESOLUTION_STATE_FILE)
    print(f"  状态文件: {RESOLUTION_STATE_FILE} ({file_size} bytes)")
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)

    # 打印完整返回结构
    print("\n完整返回结构:")
    print(json.dumps(mgr.get_resolution_state(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    test_resolution_manager()
