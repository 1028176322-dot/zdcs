#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unity 直出 PNG 触发与读取模块

配合 AutoSmokeGameContentCapture.cs 工作：
1. Python 写入 capture_request.json 触发 Unity 截图
2. Unity 捕获、裁剪、保存 PNG
3. Python 读取最新截图

输出文件：
  ~/.autosmoke/capture/cap_YYYYMMDD_HHmmss.png
  ~/.autosmoke/capture/cap_YYYYMMDD_HHmmss.json
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# 配置文件目录
CONFIG_DIR = Path(os.path.expanduser("~")) / ".autosmoke"
CAPTURE_DIR = CONFIG_DIR / "capture"


def _autosmoke_root() -> Optional[Path]:
    cfg_path = CONFIG_DIR / "config.json"
    if not cfg_path.exists():
        return None
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        root = cfg.get("autosmokeRoot") or cfg.get("autosmoke_root")
        return Path(root) if root else None
    except Exception:
        return None


def _iter_capture_pngs():
    if CAPTURE_DIR.exists():
        yield from CAPTURE_DIR.glob("cap_*.png")
    root = _autosmoke_root()
    if root:
        shots = root / "screenshots"
        if shots.exists():
            yield from shots.glob("run_*/cap_*.png")


def _capture_key(path: Path) -> str:
    return str(path.resolve()).lower()


def request_capture(timeout: float = 10.0, poll_interval: float = 0.3) -> Optional[str]:
    """
    请求 Unity 截图并等待完成

    流程：
    1. 记录当前已存在的截图数量
    2. 写入 capture_request.json
    3. 轮询 capture 目录，等待新文件出现
    4. 返回最新 PNG 路径

    :param timeout: 超时秒数
    :param poll_interval: 轮询间隔秒数
    :return: PNG 文件路径，或 None（超时）
    """
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    # 记录当前截图数量
    existing = set(_capture_key(p) for p in _iter_capture_pngs())

    # 写入请求文件
    req_path = CONFIG_DIR / "capture_request.json"
    req = {
        "action": "capture",
        "requestId": f"cap_{int(time.time() * 1000)}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(req_path, "w", encoding="utf-8") as f:
        json.dump(req, f, indent=2)

    logger.info("截图请求已写入: %s", req_path)

    # 等待截图完成
    start = time.time()
    while time.time() - start < timeout:
        current_paths = list(_iter_capture_pngs())
        current = set(_capture_key(p) for p in current_paths)
        new_files = current - existing
        if new_files:
            # 找到最新 PNG
            png_paths = sorted(
                [p for p in current_paths if _capture_key(p) in new_files],
                key=lambda p: os.path.getmtime(p),
                reverse=True,
            )
            if png_paths:
                logger.info("截图完成: %s", png_paths[0])
                return str(png_paths[0])
        time.sleep(poll_interval)

    logger.warning("截图请求超时 (%.1fs)", timeout)
    return None


def get_latest_capture() -> Optional[Dict]:
    """
    获取最新的截图信息

    :return: {"png_path": str, "meta": dict} 或 None
    """
    if not CAPTURE_DIR.exists():
        return None

    # 按修改时间排序找最新 PNG
    png_files = sorted(
        CAPTURE_DIR.glob("cap_*.png"),
        key=lambda p: os.path.getmtime(p),
        reverse=True,
    )
    if not png_files:
        return None

    png_path = png_files[0]

    # 找对应的 meta JSON
    stem = png_path.stem  # cap_20260615_181000
    meta_path = CAPTURE_DIR / f"{stem}.json"

    meta = None
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            logger.warning("读取元数据失败: %s", e)

    return {
        "png_path": str(png_path),
        "meta": meta,
    }


def get_capture_dir() -> str:
    """获取截图输出目录"""
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    return str(CAPTURE_DIR)


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    print("=== CaptureReader 测试 ===\n")

    # 测试1：检查目录
    print("[测试1] 获取截图目录...")
    d = get_capture_dir()
    print(f"  目录: {d}")
    assert os.path.exists(d)
    print("  ✅ 通过\n")

    # 测试2：获取最新截图
    print("[测试2] 获取最新截图...")
    info = get_latest_capture()
    if info:
        print(f"  PNG: {info['png_path']}")
        print(f"  Meta: {info['meta']}")
    else:
        print("  暂无截图")
    print("  ✅ 通过\n")

    # 测试3：请求截图（需要 Unity 运行中才能实际触发）
    print("[测试3] 发送截图请求（Unity 未运行则超时）...")
    # 只写入请求但不等待（不阻塞测试）
    req_path = CONFIG_DIR / "capture_request.json"
    with open(req_path, "w", encoding="utf-8") as f:
        json.dump({"action": "capture", "requestId": "test"}, f)
    print(f"  请求文件已写入: {req_path}")
    print("  ✅ 通过\n")

    print("所有测试通过 ✅")
