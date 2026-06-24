# -*- coding: utf-8 -*-
"""
GameView State Reader - 读取 Unity Bridge 导出的 game_view_state.json

优先级链路：
  1. Unity Bridge 直连状态（P0）- 最新且未过期
  2. Python 图像定位（P1）- 兜底
  3. config.json 缓存（P2）- 最后兜底

用法：
    reader = GameViewStateReader()
    state = reader.get_valid_state()  # 返回有效 state 或 None
    if state:
        print(state["gameContentRectInGameView"])
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# 默认状态文件路径
DEFAULT_STATE_DIR = Path(os.environ.get("USERPROFILE", ".")) / ".autosmoke"
DEFAULT_STATE_FILE = DEFAULT_STATE_DIR / "game_view_state.json"

# state 有效期限（毫秒）
DEFAULT_MAX_AGE_MS = 2000


class GameViewStateReader:
    """读取并校验 Unity Bridge 导出的 GameView 状态"""

    def __init__(self, state_file: str = None, max_age_ms: int = DEFAULT_MAX_AGE_MS):
        self._state_file = Path(state_file) if state_file else DEFAULT_STATE_FILE
        self._max_age_ms = max_age_ms
        self._last_state: Optional[Dict] = None

    # ── 公共接口 ──

    def get_valid_state(self) -> Optional[Dict]:
        """获取有效的 Unity state，无效时返回 None"""
        state = self._load()
        if state is None:
            return None
        if not self._validate(state):
            return None
        self._last_state = state
        return state

    def get_game_view_coords(self) -> Optional[Dict]:
        """获取 GameView 截图坐标 {left, top, right, bottom, width, height}"""
        state = self.get_valid_state()
        if state is None or "gameView" not in state:
            return None
        gv = state["gameView"]
        return {
            "left": gv["screenX"],
            "top": gv["screenY"],
            "right": gv["screenX"] + gv["width"],
            "bottom": gv["screenY"] + gv["height"],
            "width": gv["width"],
            "height": gv["height"],
        }

    def get_game_content_rect(self) -> Optional[Dict]:
        """获取 GameContent 在 GameView 截图内的 rect"""
        state = self.get_valid_state()
        if state is None:
            return None
        gc = state.get("gameContentRectInGameView")
        if not gc:
            return None
        return {
            "left": gc["x"],
            "top": gc["y"],
            "width": gc["width"],
            "height": gc["height"],
            "right": gc["right"],
            "bottom": gc["bottom"],
        }

    def get_game_resolution(self) -> Optional[Dict]:
        """获取游戏分辨率"""
        state = self.get_valid_state()
        if state is None:
            return None
        gr = state.get("gameResolution")
        if not gr:
            return None
        return {"width": gr["width"], "height": gr["height"]}

    def get_scale(self) -> Optional[Dict]:
        """获取缩放比例"""
        state = self.get_valid_state()
        if state is None:
            return None
        s = state.get("scale")
        if not s:
            return None
        return {"x": s["x"], "y": s["y"]}

    def get_toolbar_height(self) -> Optional[int]:
        """获取 Unity 工具栏高度"""
        state = self.get_valid_state()
        if state is None:
            return None
        gui = state.get("gameViewGui")
        if not gui:
            return None
        return gui.get("toolbarHeight")

    def get_state_age_ms(self) -> Optional[int]:
        """获取当前 state 的年龄（毫秒），无效返回 None"""
        state = self._load()
        if state is None:
            return None
        try:
            ts = state.get("timestamp", "")
            # 尝试解析 ISO 8601
            from datetime import datetime
            dt = datetime.fromisoformat(ts)
            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
            age = (now - dt).total_seconds() * 1000
            return int(age)
        except Exception:
            return None

    def is_available(self) -> bool:
        """检查 Unity Bridge 状态是否可用"""
        return self.get_valid_state() is not None

    # ── 内部方法 ──

    def _load(self) -> Optional[Dict]:
        """读取 state 文件"""
        if not self._state_file.exists():
            return None
        try:
            with open(str(self._state_file), "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.debug("读取 state 文件失败: %s", e)
            return None

    def _validate(self, state: Dict) -> bool:
        """校验 state 是否有效且未过期"""
        # 是否有错误
        if state.get("error"):
            logger.debug("Unity state 含错误: %s", state["error"])
            return False

        # 基本字段校验
        gv = state.get("gameView")
        gc = state.get("gameContentRectInGameView")
        gr = state.get("gameResolution")
        if not gv or not gc or not gr:
            logger.debug("Unity state 缺少必要字段")
            return False

        # 尺寸有效性
        if gv.get("width", 0) <= 0 or gv.get("height", 0) <= 0:
            logger.debug("Unity state 中 GameView 尺寸无效")
            return False
        if gc.get("width", 0) <= 0 or gc.get("height", 0) <= 0:
            logger.debug("Unity state 中 GameContentRect 尺寸无效")
            return False
        if gr.get("width", 0) <= 0 or gr.get("height", 0) <= 0:
            logger.debug("Unity state 中分辨率无效")
            return False

        # 时间戳有效性（未过期）
        age = self.get_state_age_ms()
        if age is not None and age > self._max_age_ms:
            logger.debug("Unity state 已过期: %dms > %dms", age, self._max_age_ms)
            return False

        return True


# ── 快捷函数 ──

def get_bridge_state() -> Optional[Dict]:
    """快速获取有效 Unity Bridge 状态"""
    return GameViewStateReader().get_valid_state()


def apply_bridge_state_to_config(config: Dict, state: Dict) -> Dict:
    """将 Unity state 写入 config dict（Bridge 输出的是屏幕坐标，需转为截图坐标）"""
    gv = state["gameView"]

    # 屏幕坐标 → 截图坐标（减去虚拟屏幕偏移）
    _screen_offset_x = 0
    _screen_offset_y = 0
    try:
        import win32api
        _screen_offset_x = win32api.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        _screen_offset_y = win32api.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    except Exception:
        pass

    config["game_view_coords"] = {
        "left": gv["screenX"] - _screen_offset_x,
        "top": gv["screenY"] - _screen_offset_y,
        "right": gv["screenX"] - _screen_offset_x + gv["width"],
        "bottom": gv["screenY"] - _screen_offset_y + gv["height"],
        "width": gv["width"],
        "height": gv["height"],
        "source": "unity_bridge",
    }

    gc = state["gameContentRectInGameView"]
    config["game_content_rect"] = {
        "left": gc["x"],
        "top": gc["y"],
        "width": gc["width"],
        "height": gc["height"],
        "right": gc["right"],
        "bottom": gc["bottom"],
        "source": "unity_bridge",
    }

    gr = state["gameResolution"]
    config["game_resolution"] = {
        "width": gr["width"],
        "height": gr["height"],
        "source": "unity_bridge",
    }

    return config
