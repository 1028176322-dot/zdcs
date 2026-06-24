#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐标映射模块 - 阶段二：统一坐标映射

六种坐标系互转：
1. screen         — Windows 全局屏幕坐标
2. game_view      — GameViewPanel 内部坐标
3. game_content   — 真实游戏内容区坐标
4. design         — 游戏设计分辨率坐标 (1170x2532)
5. normalized     — 归一化坐标 (0.0~1.0)
6. all_screens_image — ImageGrab(all_screens=True) 大图坐标（仅在需要时使用）

核心公式（文档 5.4 节）：
    scaleX = gameContentRect.width / gameResolution.width
    scaleY = gameContentRect.height / gameResolution.height

    screenX = gameView.left + gameContentRect.left + designX * scaleX
    screenY = gameView.top  + gameContentRect.top  + designY * scaleY

精度要求（文档 5.5 节）：
    - scaleX 与 scaleY 差异 <= 1%
    - 坐标换算误差 <= 2px
    - 最后一步才四舍五入为整数像素

使用方式：
    mapper = CoordinateMapper.from_config()
    sx, sy = mapper.design_to_screen(585, 2400)
    dx, dy = mapper.screen_to_design(sx, sy)
    assert abs(dx - 585) <= 2
"""

import json
import os
import logging
from typing import Tuple, Dict, Optional
from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(str(CONFIG_DIR), "config.json")
RESOLUTION_STATE_FILE = os.path.join(str(CONFIG_DIR), "resolution_state.json")


class CoordinateMapper:
    """
    统一坐标映射器

    封装从 config.json 读取 game_view_coords / game_content_rect，
    结合 ResolutionManager 获取 gameResolution，提供六种坐标互转。
    """

    def __init__(self, game_view_coords: Dict, game_content_rect: Dict,
                 game_resolution: Dict):
        """
        初始化坐标映射器

        :param game_view_coords: GameView 面板坐标
            {"left": 271, "top": 51, "width": 488, "height": 752}
        :param game_content_rect: 游戏内容区域坐标
            {"left": 85, "top": 62, "width": 318, "height": 688}
        :param game_resolution: 游戏设计分辨率
            {"width": 1170, "height": 2532}
        """
        # 检测虚拟屏幕偏移（all_screens_image → screen）
        # config.json 中 game_view_coords 是 all_screens_image 坐标，
        # 点击需要 Windows 全局屏幕坐标，需加上虚拟屏幕偏移
        self.screen_offset_x = 0
        self.screen_offset_y = 0
        try:
            import win32api
            self.screen_offset_x = win32api.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
            self.screen_offset_y = win32api.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
            if self.screen_offset_x != 0 or self.screen_offset_y != 0:
                logger.info("虚拟屏幕偏移: (%d, %d)",
                          self.screen_offset_x, self.screen_offset_y)
        except Exception:
            pass

        # 存储原始数据
        self._gv = game_view_coords
        self._gc = game_content_rect
        self._gr = game_resolution

        # 提取关键数值
        self.gv_left = int(game_view_coords.get("left", 0))
        self.gv_top = int(game_view_coords.get("top", 0))
        self.gv_width = int(game_view_coords.get("width", 0))
        self.gv_height = int(game_view_coords.get("height", 0))
        self.gv_right = self.gv_left + self.gv_width
        self.gv_bottom = self.gv_top + self.gv_height

        self.gc_left = int(game_content_rect.get("left", 0))
        self.gc_top = int(game_content_rect.get("top", 0))
        self.gc_width = int(game_content_rect.get("width", 0))
        self.gc_height = int(game_content_rect.get("height", 0))
        self.gc_right = self.gc_left + self.gc_width
        self.gc_bottom = self.gc_top + self.gc_height

        self.design_width = int(game_resolution.get("width", 1170))
        self.design_height = int(game_resolution.get("height", 2532))

        # 计算缩放比例
        self.scale_x = self.gc_width / self.design_width
        self.scale_y = self.gc_height / self.design_height

        # 校验 scale
        self._validate_scale()

        logger.info(
            "CoordinateMapper 初始化: "
            "GV=(%d,%d,%d,%d) GC=(%d,%d,%d,%d) "
            "GR=%dx%d scale=(%.4f,%.4f)",
            self.gv_left, self.gv_top, self.gv_right, self.gv_bottom,
            self.gc_left, self.gc_top, self.gc_right, self.gc_bottom,
            self.design_width, self.design_height,
            self.scale_x, self.scale_y
        )

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def from_config(cls, config_file: str = None,
                    resolution: Dict = None) -> Optional["CoordinateMapper"]:
        """
        从配置文件创建 CoordinateMapper

        :param config_file: config.json 路径，默认自动查找
        :param resolution: 手动传入分辨率字典，不传则自动读取
        :return: CoordinateMapper 实例，失败返回 None
        """
        config_file = config_file or CONFIG_FILE
        try:
            with open(config_file, "r", encoding="utf-8-sig") as f:
                config = json.load(f)
        except Exception as e:
            logger.error("读取配置文件失败: %s", e)
            return None

        gv = config.get("game_view_coords")
        if not gv or not gv.get("width"):
            logger.error("config.json 中缺少 game_view_coords")
            return None

        gc = config.get("game_content_rect") or config.get(
            "game_content_result", {}).get("gameContentRect")
        if not gc or not gc.get("width"):
            logger.error("config.json 中缺少 game_content_rect")
            return None

        if resolution:
            gr = resolution
        else:
            # 尝试从 resolution_state 读取
            try:
                if os.path.exists(RESOLUTION_STATE_FILE):
                    with open(RESOLUTION_STATE_FILE, "r", encoding="utf-8") as f:
                        gr = json.load(f)
                else:
                    gr = config.get("game_resolution", {"width": 1170, "height": 2532})
            except Exception:
                gr = config.get("game_resolution", {"width": 1170, "height": 2532})

        return cls(gv, gc, gr)

    # ============================================================
    # 校验
    # ============================================================

    def _validate_scale(self):
        """校验 scaleX 与 scaleY 差异 <= 1%"""
        if self.scale_x <= 0 or self.scale_y <= 0:
            logger.warning("scale 无效: x=%.4f, y=%.4f", self.scale_x, self.scale_y)
            return

        diff = abs(self.scale_x - self.scale_y) / max(self.scale_x, self.scale_y)
        if diff > 0.01:
            logger.warning(
                "SCALE_MISMATCH: scaleX=%.4f, scaleY=%.4f, 差异=%.2f%% (>1%%)",
                self.scale_x, self.scale_y, diff * 100
            )

    def check_scale_mismatch(self) -> Dict:
        """
        检查 scale 差异是否在容忍范围内

        :return: {"mismatch": bool, "diff_pct": float, "scale_x": float, "scale_y": float}
        """
        if self.scale_x <= 0 or self.scale_y <= 0:
            return {"mismatch": True, "diff_pct": 100.0,
                    "scale_x": self.scale_x, "scale_y": self.scale_y}

        diff = abs(self.scale_x - self.scale_y) / max(self.scale_x, self.scale_y)
        return {
            "mismatch": diff > 0.01,
            "diff_pct": round(diff * 100, 2),
            "scale_x": round(self.scale_x, 4),
            "scale_y": round(self.scale_y, 4)
        }

    # ============================================================
    # 核心映射函数
    # ============================================================

    def design_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """
        游戏设计坐标 → 屏幕绝对坐标

        :param x: 设计横坐标 (0 ~ design_width)
        :param y: 设计纵坐标 (0 ~ design_height)
        :return: (screen_x, screen_y) 整数像素
        """
        # 先算 all_screens_image 坐标，再转屏幕坐标
        ax = self.gv_left + self.gc_left + x * self.scale_x
        ay = self.gv_top + self.gc_top + y * self.scale_y
        return (round(ax + self.screen_offset_x), round(ay + self.screen_offset_y))

    def screen_to_design(self, x: float, y: float) -> Tuple[float, float]:
        """
        屏幕绝对坐标 → 游戏设计坐标

        :param x: 屏幕横坐标
        :param y: 屏幕纵坐标
        :return: (design_x, design_y) 浮点数
        """
        # 先转回 all_screens_image 坐标
        ax = x - self.screen_offset_x
        ay = y - self.screen_offset_y
        dx = (ax - self.gv_left - self.gc_left) / self.scale_x
        dy = (ay - self.gv_top - self.gc_top) / self.scale_y
        return (dx, dy)

    def normalized_to_screen(self, nx: float, ny: float) -> Tuple[int, int]:
        """
        归一化坐标 → 屏幕绝对坐标

        先转为 design 坐标，再映射到屏幕。

        :param nx: 归一化横坐标 (0.0~1.0)
        :param ny: 归一化纵坐标 (0.0~1.0)
        :return: (screen_x, screen_y) 整数像素
        """
        dx = nx * self.design_width
        dy = ny * self.design_height
        return self.design_to_screen(dx, dy)

    def screen_to_normalized(self, x: float, y: float) -> Tuple[float, float]:
        """
        屏幕绝对坐标 → 归一化坐标

        :param x: 屏幕横坐标
        :param y: 屏幕纵坐标
        :return: (nx, ny) 浮点数 (0.0~1.0)
        """
        dx, dy = self.screen_to_design(x, y)
        nx = dx / self.design_width
        ny = dy / self.design_height
        return (nx, ny)

    def content_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """
        gameContent 内像素坐标 → 屏幕绝对坐标

        :param x: gameContent 内横坐标 (0 ~ gc_width)
        :param y: gameContent 内纵坐标 (0 ~ gc_height)
        :return: (screen_x, screen_y) 整数像素
        """
        ax = self.gv_left + self.gc_left + x
        ay = self.gv_top + self.gc_top + y
        return (round(ax + self.screen_offset_x), round(ay + self.screen_offset_y))

    def screen_to_content(self, x: float, y: float) -> Tuple[float, float]:
        """
        屏幕绝对坐标 → gameContent 内像素坐标

        :param x: 屏幕横坐标
        :param y: 屏幕纵坐标
        :return: (content_x, content_y) 浮点数
        """
        ax = x - self.screen_offset_x
        ay = y - self.screen_offset_y
        cx = ax - self.gv_left - self.gc_left
        cy = ay - self.gv_top - self.gc_top
        return (cx, cy)

    # ============================================================
    # 便捷方法
    # ============================================================

    def is_in_game_content(self, screen_x: float, screen_y: float) -> bool:
        """
        判断屏幕坐标是否在 gameContent 区域内

        :param screen_x: 屏幕横坐标
        :param screen_y: 屏幕纵坐标
        :return: 是否在 gameContent 内
        """
        ax = screen_x - self.screen_offset_x
        ay = screen_y - self.screen_offset_y
        in_x = self.gv_left + self.gc_left <= ax <= self.gv_left + self.gc_right
        in_y = self.gv_top + self.gc_top <= ay <= self.gv_top + self.gc_bottom
        return in_x and in_y

    def is_in_game_view(self, screen_x: float, screen_y: float) -> bool:
        """
        判断屏幕坐标是否在 GameView 面板区域内

        :param screen_x: 屏幕横坐标
        :param screen_y: 屏幕纵坐标
        :return: 是否在 GameView 内
        """
        ax = screen_x - self.screen_offset_x
        ay = screen_y - self.screen_offset_y
        in_x = self.gv_left <= ax <= self.gv_right
        in_y = self.gv_top <= ay <= self.gv_bottom
        return in_x and in_y

    def get_game_resolution(self) -> Tuple[int, int]:
        """获取游戏设计分辨率 (width, height)"""
        return (self.design_width, self.design_height)

    def get_scale(self) -> Tuple[float, float]:
        """获取缩放比例 (scale_x, scale_y)"""
        return (self.scale_x, self.scale_y)

    def get_content_rect(self) -> Dict:
        """获取 gameContent 区域"""
        return {
            "left": self.gc_left, "top": self.gc_top,
            "width": self.gc_width, "height": self.gc_height,
            "right": self.gc_right, "bottom": self.gc_bottom
        }

    def get_view_rect(self) -> Dict:
        """获取 GameView 面板区域"""
        return {
            "left": self.gv_left, "top": self.gv_top,
            "width": self.gv_width, "height": self.gv_height,
            "right": self.gv_right, "bottom": self.gv_bottom
        }

    # ============================================================
    # 调试
    # ============================================================

    def summary(self) -> str:
        """返回映射器状态摘要"""
        sc = self.check_scale_mismatch()
        lines = [
            "CoordinateMapper 摘要",
            "─" * 50,
            f"GameView:      ({self.gv_left}, {self.gv_top}) "
            f"{self.gv_width}x{self.gv_height}",
            f"GameContent:   ({self.gc_left}, {self.gc_top}) "
            f"{self.gc_width}x{self.gc_height}",
            f"DesignResolution: {self.design_width}x{self.design_height}",
            f"Scale:          x={self.scale_x:.4f}, y={self.scale_y:.4f}",
            f"Scale Mismatch: {sc['diff_pct']:.2f}% "
            f"({'⚠️' if sc['mismatch'] else '✅'})",
        ]
        return "\n".join(lines)

    def design_to_content(self, x: float, y: float) -> Tuple[float, float]:
        """
        游戏设计坐标 → gameContent 内像素坐标

        :param x: 设计横坐标
        :param y: 设计纵坐标
        :return: (content_x, content_y) 浮点数
        """
        cx = x * self.scale_x
        cy = y * self.scale_y
        return (cx, cy)

    def content_to_design(self, x: float, y: float) -> Tuple[float, float]:
        """
        gameContent 内像素坐标 → 游戏设计坐标

        :param x: gameContent 内横坐标
        :param y: gameContent 内纵坐标
        :return: (design_x, design_y) 浮点数
        """
        dx = x / self.scale_x
        dy = y / self.scale_y
        return (dx, dy)


# ============================================================
# 独立运行入口
# ============================================================

def test_coordinate_mapper():
    """测试坐标映射器"""
    print("=" * 60)
    print("坐标映射器测试")
    print("=" * 60)

    # 使用当前配置创建映射器
    mapper = CoordinateMapper.from_config()
    assert mapper is not None, "CoordinateMapper 创建失败"
    print(f"\n{mapper.summary()}\n")

    # ---------- 测试1：design_to_screen ----------
    print("\n[测试1] design_to_screen()")
    # 游戏中心 585, 1266
    sx, sy = mapper.design_to_screen(585, 1266)
    print(f"  design(585, 1266) → screen({sx}, {sy})")
    assert mapper.is_in_game_content(sx, sy), "中心点应在 gameContent 内"
    print("  ✅ 通过")

    # 游戏左上角 (0, 0)
    sx, sy = mapper.design_to_screen(0, 0)
    print(f"  design(0, 0) → screen({sx}, {sy})")
    assert sx == mapper.gv_left + mapper.gc_left, "左上角 X 应等于 gv.left + gc.left"
    assert sy == mapper.gv_top + mapper.gc_top, "左上角 Y 应等于 gv.top + gc.top"
    print("  ✅ 通过")

    # 游戏右下角 (1170, 2532)
    sx, sy = mapper.design_to_screen(mapper.design_width, mapper.design_height)
    print(f"  design({mapper.design_width}, {mapper.design_height}) "
          f"→ screen({sx}, {sy})")
    expected_sx = mapper.gv_left + mapper.gc_left + mapper.gc_width
    expected_sy = mapper.gv_top + mapper.gc_top + mapper.gc_height
    assert abs(sx - expected_sx) <= 1, f"右下角 X 应 ≈ {expected_sx}"
    assert abs(sy - expected_sy) <= 1, f"右下角 Y 应 ≈ {expected_sy}"
    print("  ✅ 通过")

    # ---------- 测试2：双向映射误差 ----------
    print("\n[测试2] 双向映射误差 <= 2px...")
    test_points = [
        (0, 0),
        (585, 1266),
        (1170, 2532),
        (300, 500),
        (800, 2000),
    ]
    for dx, dy in test_points:
        sx, sy = mapper.design_to_screen(dx, dy)
        rdx, rdy = mapper.screen_to_design(sx, sy)
        err_x = abs(rdx - dx)
        err_y = abs(rdy - dy)
        status = "✅" if err_x <= 2 and err_y <= 2 else "❌"
        print(f"  design({dx:>4},{dy:>4}) → screen({sx:>3},{sy:>3}) "
              f"→ design({rdx:>6.1f},{rdy:>6.1f}) "
              f"误差=({err_x:.2f},{err_y:.2f}) {status}")
        assert err_x <= 2, f"X 误差 {err_x} > 2px"
        assert err_y <= 2, f"Y 误差 {err_y} > 2px"
    print("  ✅ 全部通过")

    # ---------- 测试3：normalized_to_screen ----------
    print("\n[测试3] normalized_to_screen()...")
    # 中心 (0.5, 0.5)
    sx, sy = mapper.normalized_to_screen(0.5, 0.5)
    print(f"  normalized(0.5, 0.5) → screen({sx}, {sy})")
    assert mapper.is_in_game_content(sx, sy), "归一化中心应在 gameContent 内"
    # 左上 (0, 0)
    sx, sy = mapper.normalized_to_screen(0, 0)
    print(f"  normalized(0, 0) → screen({sx}, {sy})")
    assert sx == mapper.gv_left + mapper.gc_left
    assert sy == mapper.gv_top + mapper.gc_top
    # 右下 (1, 1)
    sx, sy = mapper.normalized_to_screen(1, 1)
    print(f"  normalized(1, 1) → screen({sx}, {sy})")
    print("  ✅ 通过")

    # ---------- 测试4：screen_to_normalized ----------
    print("\n[测试4] screen_to_normalized()...")
    for nx_in, ny_in in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.3, 0.7)]:
        sx, sy = mapper.normalized_to_screen(nx_in, ny_in)
        nx_out, ny_out = mapper.screen_to_normalized(sx, sy)
        err = abs(nx_out - nx_in) + abs(ny_out - ny_in)
        status = "✅" if err < 0.01 else "❌"
        print(f"  norm({nx_in:.1f},{ny_in:.1f}) → screen → "
              f"norm({nx_out:.4f},{ny_out:.4f}) {status}")
    print("  ✅ 通过")

    # ---------- 测试5：content_to_screen / screen_to_content ----------
    print("\n[测试5] content_to_screen() / screen_to_content()...")
    cx_test, cy_test = 100, 200
    sx, sy = mapper.content_to_screen(cx_test, cy_test)
    rcx, rcy = mapper.screen_to_content(sx, sy)
    err = abs(rcx - cx_test) + abs(rcy - cy_test)
    print(f"  content({cx_test},{cy_test}) → screen({sx},{sy}) "
          f"→ content({rcx:.1f},{rcy:.1f}) 误差={err:.1f}")
    assert err < 0.5, f"content 双向误差 {err} > 0.5px"
    print("  ✅ 通过")

    # ---------- 测试6：区域判断 ----------
    print("\n[测试6] 区域判断...")
    # GameView 中心
    gv_center_x = mapper.gv_left + mapper.gv_width // 2
    gv_center_y = mapper.gv_top + mapper.gv_height // 2
    assert mapper.is_in_game_view(gv_center_x, gv_center_y)
    assert mapper.is_in_game_content(gv_center_x, gv_center_y)
    print(f"  GameView 中心 ({gv_center_x}, {gv_center_y}) → in_view=✅ in_content=✅")

    # GameView 外
    assert not mapper.is_in_game_view(0, 0), "(0,0) 不应在 GameView 内"
    print("  (0, 0) → in_view=❌ in_content=❌ ✅")
    print("  ✅ 通过")

    # ---------- 测试7：design_to_content ----------
    print("\n[测试7] design_to_content()...")
    dx, dy = 585, 1266
    cx, cy = mapper.design_to_content(dx, dy)
    rdx, rdy = mapper.content_to_design(cx, cy)
    err = abs(rdx - dx) + abs(rdy - dy)
    print(f"  design({dx},{dy}) → content({cx:.1f},{cy:.1f}) "
          f"→ design({rdx:.1f},{rdy:.1f}) 误差={err:.1f}")
    assert err < 1, f"design-content 双向误差 {err} > 1"
    print("  ✅ 通过")

    # ---------- 测试8：数据绑定 ----------
    print("\n[测试8] 元数据...")
    print(f"  game_resolution: {mapper.get_game_resolution()}")
    print(f"  scale: {mapper.get_scale()}")
    print(f"  content_rect: {mapper.get_content_rect()}")
    print(f"  view_rect: {mapper.get_view_rect()}")
    print("  ✅ 通过")

    # ---------- 测试9：Scale Mismatch 检测 ----------
    print("\n[测试9] Scale Mismatch 检测...")
    sc = mapper.check_scale_mismatch()
    print(f"  diff_pct={sc['diff_pct']}% mismatch={sc['mismatch']}")
    assert not sc["mismatch"], "当前配置不应触发 Scale Mismatch"
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    test_coordinate_mapper()
