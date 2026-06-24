#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯游戏内容截图模块 - 阶段三：纯游戏截图

功能：
1. 从全屏截图中裁剪纯游戏内容区域（gameContent 截图）
2. 输出 game_view 截图（调试用）
3. 输出三层标注图（调试用）
4. 每张截图绑定当前定位周期的元数据

截图链路（文档 6.2 节）：
    all_screens_screenshot
    → gameViewPanel crop
    → gameContentRect crop
    → game_content_screenshot

使用方式：
    capturer = GameContentScreenshot()
    result = capturer.capture()
    # result["game_content_path"]  → 纯游戏内容截图
    # result["game_view_path"]     → GameView 面板截图
    # result["metadata"]           → 绑定的分辨率/坐标/scale
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from PIL import Image
from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SCREENSHOTS_DIR = os.path.join(CONFIG_DIR, "screenshots")


class GameContentScreenshot:
    """
    纯游戏内容截图器

    负责从屏幕截图中裁剪 gameContent 区域，并绑定元数据。
    """

    def __init__(self, mapper=None, config_file: str = None):
        """
        初始化截图器

        :param mapper: CoordinateMapper 实例（可选），不传则自动创建
        :param config_file: 配置文件路径
        """
        self.config_file = config_file or CONFIG_FILE
        self._mapper = mapper
        self._config = None

    # ============================================================
    # 配置读取
    # ============================================================

    def _load_config(self) -> Dict:
        """加载配置文件"""
        if self._config is None:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        return self._config

    def _get_mapper(self):
        """获取 CoordinateMapper（懒加载）"""
        if self._mapper is None:
            from 坐标截图.coordinate_mapper import CoordinateMapper
            self._mapper = CoordinateMapper.from_config(self.config_file)
            if self._mapper is None:
                raise RuntimeError("无法创建 CoordinateMapper，请确保定位已完成")
        return self._mapper

    # ============================================================
    # 截图
    # ============================================================

    def capture(self, all_screens_img: Image = None,
                run_id: str = None) -> Dict:
        """
        执行截图流程

        1. 截取所有屏幕
        2. 裁剪 GameView 面板
        3. 裁剪 gameContent 区域
        4. 绑定元数据
        5. 保存文件

        :param all_screens_img: 可选，传入已有全屏截图，None 则实时截取
        :param run_id: 运行批次 ID，None 自动生成
        :return:
            {
                "status": "OK",
                "game_content_path": "...",
                "game_view_path": "...",
                "game_content_size": [318, 688],
                "metadata": {...}
            }
        """
        mapper = self._get_mapper()
        config = self._load_config()

        # 生成 run_id（复用最近 10 秒内目录，避免同一操作产生多个目录）
        if run_id is None:
            run_id = _find_recent_run_dir(SCREENSHOTS_DIR, 10)
            if not run_id:
                run_id = time.strftime("run_%Y%m%d_%H%M%S")

        # 创建输出目录
        output_dir = os.path.join(SCREENSHOTS_DIR, run_id)
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # ---- 步骤1：截图（全屏） ----
        if all_screens_img is None:
            from PIL import ImageGrab
            logger.info("截取全屏...")
            all_screens_img = ImageGrab.grab(all_screens=True)

        # ---- 步骤2：裁剪 GameView 面板 ----
        gv_coords = config.get("game_view_coords", {})
        gv_left = gv_coords.get("left", 0)
        gv_top = gv_coords.get("top", 0)
        gv_right = gv_coords.get("right", 0)
        gv_bottom = gv_coords.get("bottom", 0)

        logger.info("裁剪 GameView 面板: (%d, %d, %d, %d)",
                    gv_left, gv_top, gv_right, gv_bottom)
        game_view_img = all_screens_img.crop((gv_left, gv_top, gv_right, gv_bottom))

        # ---- 步骤3：裁剪 gameContent 区域 ----
        gc = mapper.get_content_rect()
        logger.info("裁剪 gameContent 区域: (%d, %d, %d, %d)",
                    gc["left"], gc["top"], gc["right"], gc["bottom"])
        game_content_img = game_view_img.crop(
            (gc["left"], gc["top"], gc["right"], gc["bottom"])
        )

        # ---- 步骤4：保存 ----
        # 纯游戏内容截图
        content_path = os.path.join(output_dir, f"game_content_{timestamp}.png")
        game_content_img.save(content_path)
        logger.info("纯游戏内容截图已保存: %s (%dx%d)",
                    content_path, game_content_img.width, game_content_img.height)

        # GameView 面板截图
        view_path = os.path.join(output_dir, f"game_view_{timestamp}.png")
        game_view_img.save(view_path)
        logger.info("GameView 面板截图已保存: %s", view_path)

        # ---- 步骤5：构建元数据 ----
        metadata = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "game_resolution": {
                "width": mapper.design_width,
                "height": mapper.design_height
            },
            "game_content_rect": {
                "left": gc["left"], "top": gc["top"],
                "width": gc["width"], "height": gc["height"],
                "right": gc["right"], "bottom": gc["bottom"]
            },
            "game_view_coords": {
                "left": gv_left, "top": gv_top,
                "right": gv_right, "bottom": gv_bottom,
                "width": gv_right - gv_left,
                "height": gv_bottom - gv_top
            },
            "scale": {
                "x": round(mapper.scale_x, 4),
                "y": round(mapper.scale_y, 4)
            },
            "files": {
                "game_content": f"game_content_{timestamp}.png",
                "game_view": f"game_view_{timestamp}.png"
            },
            "locator": {
                "version": "aspect_fit_v3",
                "cache_policy": "capture_from_latest_config",
                "content_width_source": "config_game_content_rect",
            },
            "ratio_check": {
                "target_ratio": round(mapper.design_width / mapper.design_height, 4),
                "actual_ratio": round(gc["width"] / gc["height"], 4) if gc["height"] > 0 else 0,
            },
        }
        # 计算比例差异
        target_r = metadata["ratio_check"]["target_ratio"]
        actual_r = metadata["ratio_check"]["actual_ratio"]
        metadata["ratio_check"]["diff"] = round(abs(target_r - actual_r), 4)

        # config 快照记录（用于排查缓存不一致问题）
        metadata["config_snapshot"] = {
            "game_view_coords": {
                "left": gv_left, "top": gv_top,
                "right": gv_right, "bottom": gv_bottom,
                "width": gv_right - gv_left,
                "height": gv_bottom - gv_top
            },
            "game_content_rect": {
                "left": gc["left"], "top": gc["top"],
                "width": gc["width"], "height": gc["height"],
                "right": gc["right"], "bottom": gc["bottom"]
            },
            "game_resolution": {
                "width": mapper.design_width,
                "height": mapper.design_height
            },
        }

        # 保存元数据
        meta_path = os.path.join(output_dir, f"metadata_{timestamp}.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info("元数据已保存: %s", meta_path)

        return {
            "status": "OK",
            "game_content_path": content_path,
            "game_content_size": [game_content_img.width, game_content_img.height],
            "game_view_path": view_path,
            "metadata_path": meta_path,
            "metadata": metadata,
            "run_id": run_id,
            "game_content_image": game_content_img,
            "game_view_image": game_view_img
        }

    # ============================================================
    # 便捷方法
    # ============================================================

    def capture_game_content_only(self, all_screens_img: Image = None) -> Image:
        """
        仅返回纯游戏内容截图（不保存文件）

        :param all_screens_img: 全屏截图，None 则实时截取
        :return: PIL Image
        """
        mapper = self._get_mapper()
        config = self._load_config()

        if all_screens_img is None:
            from PIL import ImageGrab
            all_screens_img = ImageGrab.grab(all_screens=True)

        gv = config.get("game_view_coords", {})
        game_view_img = all_screens_img.crop((
            gv["left"], gv["top"], gv["right"], gv["bottom"]
        ))

        gc = mapper.get_content_rect()
        return game_view_img.crop((
            gc["left"], gc["top"], gc["right"], gc["bottom"]
        ))

    def get_latest_metadata(self, run_id: str = None) -> Optional[Dict]:
        """
        获取最新截图的元数据

        :param run_id: 指定运行批次，None 则找最新
        :return: 元数据字典
        """
        if run_id:
            meta_dir = os.path.join(SCREENSHOTS_DIR, run_id)
        else:
            # 找最新的 run_ 目录
            if not os.path.exists(SCREENSHOTS_DIR):
                return None
            runs = sorted(
                [d for d in os.listdir(SCREENSHOTS_DIR)
                 if d.startswith("run_") and os.path.isdir(os.path.join(SCREENSHOTS_DIR, d))],
                reverse=True
            )
            if not runs:
                return None
            meta_dir = os.path.join(SCREENSHOTS_DIR, runs[0])

        if not os.path.exists(meta_dir):
            return None

        metas = sorted(
            [f for f in os.listdir(meta_dir) if f.startswith("metadata_") and f.endswith(".json")],
            reverse=True
        )
        if not metas:
            return None

        meta_path = os.path.join(meta_dir, metas[0])
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)


# ============================================================
# 独立运行入口
# ============================================================

def _find_recent_run_dir(screenshots_dir: str, max_age: int = 30) -> str:
    """查找最近 max_age 秒内的 run_* 目录，复用避免碎片"""
    try:
        if not os.path.isdir(screenshots_dir):
            return ""
        dirs = sorted(
            [d for d in os.listdir(screenshots_dir) if d.startswith("run_")],
            reverse=True
        )
        now = time.time()
        for d in dirs:
            dpath = os.path.join(screenshots_dir, d)
            age = now - os.path.getmtime(dpath)
            if age < max_age:
                return d
    except Exception:
        pass
    return ""

def test_screenshot_game_content():
    """测试纯游戏内容截图"""
    print("=" * 60)
    print("纯游戏内容截图测试")
    print("=" * 60)

    from 坐标截图.coordinate_mapper import CoordinateMapper

    # 创建映射器和截图器
    mapper = CoordinateMapper.from_config()
    assert mapper is not None, "CoordinateMapper 创建失败"
    print(f"\n{mapper.summary()}\n")

    capturer = GameContentScreenshot(mapper=mapper)

    # 测试1：捕获并保存（使用实时截图）
    print("\n[测试1] capture() — 实时截图...")
    result = capturer.capture()
    assert result["status"] == "OK"
    print(f"  run_id: {result['run_id']}")
    print(f"  game_content: {result['game_content_path']}")
    print(f"  game_content_size: {result['game_content_size']}")
    print(f"  game_view: {result['game_view_path']}")
    print(f"  metadata: {result['metadata_path']}")
    assert os.path.exists(result["game_content_path"]), "文件应存在"
    assert os.path.exists(result["game_view_path"]), "文件应存在"
    assert os.path.exists(result["metadata_path"]), "元数据文件应存在"
    print("  ✅ 通过")

    # 测试2：验证截图尺寸
    print("\n[测试2] 验证截图尺寸...")
    gc_img = result["game_content_image"]
    mapper = capturer._get_mapper()
    gc = mapper.get_content_rect()
    print(f"  期望尺寸: {gc['width']}x{gc['height']}")
    print(f"  实际尺寸: {gc_img.width}x{gc_img.height}")
    assert gc_img.width == gc["width"], f"宽度不匹配: {gc_img.width} != {gc['width']}"
    assert gc_img.height == gc["height"], f"高度不匹配: {gc_img.height} != {gc['height']}"
    print("  ✅ 通过")

    # 测试3：验证元数据完整性
    print("\n[测试3] 验证元数据...")
    meta = result["metadata"]
    print(f"  game_resolution: {meta['game_resolution']}")
    print(f"  game_content_rect: {meta['game_content_rect']}")
    print(f"  scale: {meta['scale']}")
    assert "game_resolution" in meta
    assert "game_content_rect" in meta
    assert "scale" in meta
    assert meta["game_content_rect"]["width"] == gc["width"]
    print("  ✅ 通过")

    # 测试4：capture_game_content_only
    print("\n[测试4] capture_game_content_only()...")
    img = capturer.capture_game_content_only()
    assert img is not None
    print(f"  尺寸: {img.width}x{img.height}")
    assert img.width == gc["width"]
    assert img.height == gc["height"]
    print("  ✅ 通过")

    # 测试5：get_latest_metadata
    print("\n[测试5] get_latest_metadata()...")
    meta2 = capturer.get_latest_metadata()
    assert meta2 is not None
    assert meta2["game_content_rect"]["width"] == gc["width"]
    print(f"  找到最新元数据: run_id={os.path.basename(os.path.dirname(result['metadata_path']))}")
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)
    print(f"\n截图输出目录:")
    print(f"  {os.path.dirname(result['game_content_path'])}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    test_screenshot_game_content()
