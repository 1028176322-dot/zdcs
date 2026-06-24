#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unity Editor 日志采集器

功能：
  1. 实时监听 Unity Editor 日志文件变化
  2. 按级别（ERROR/WARNING/INFO）分类采集
  3. 检测关键错误模式（NullReference/MissingReference/Exception）
  4. 结构化输出供 IDE 和报告使用

日志位置：
  - Editor: %LOCALAPPDATA%\\Unity\\Editor\\Editor.log
  - Play模式: %LOCALAPPDATA%\\Unity\\Editor\\Editor.log（Editor 本身）

用法：
    collector = UnityLogCollector()
    collector.start()        # 启动后台线程
    collector.get_errors()   # 获取错误列表
    collector.stop()         # 停止
"""

import os
import re
import time
import threading
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 关键错误模式
ERROR_PATTERNS = {
    "NullReferenceException": [
        r"NullReferenceException",
        r"NullReferenceException: Object reference not set to an instance of an object",
    ],
    "MissingReferenceException": [
        r"MissingReferenceException",
        r"MissingReferenceException: The object of type .* has been destroyed but you are still trying to access it",
    ],
    "IndexOutOfRange": [
        r"IndexOutOfRangeException",
        r"IndexOutOfRangeException: Index was outside the bounds of the array",
    ],
    "ArgumentException": [
        r"ArgumentException",
        r"ArgumentOutOfRangeException",
    ],
    "UnityException": [
        r"UnityException",
        r"UnassignedReferenceException",
    ],
    "Assertion": [
        r"Assertion failed",
        r"AssertionError",
    ],
    "Crash": [
        r"Fatal error!",
        r"Fatal: ",
        r"crash",
        r"aborting",
        r"crashed",
    ],
    "StackOverflow": [
        r"StackOverflowException",
        r"StackOverflow",
    ],
    "OutOfMemory": [
        r"OutOfMemoryException",
        r"Out of memory",
        r"Not enough memory",
    ],
}


class UnityLogCollector:
    """
    Unity Editor 日志采集器

    启动后台线程轮询 Editor.log，支持：
    - 增量读取（只读取新内容）
    - 错误分类与统计
    - 时间范围过滤
    - 自动清理过期条目（默认保留最近 1000 条）
    """

    DEFAULT_LOG_PATH = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Unity", "Editor", "Editor.log"
    )

    def __init__(self, log_path: str = None, max_entries: int = 1000):
        self._log_path = log_path or self.DEFAULT_LOG_PATH
        self._max_entries = max_entries

        # 采集状态
        self._entries: List[Dict] = []  # 所有日志条目
        self._errors: List[Dict] = []   # 仅错误级别
        self._last_position = 0         # 文件读取位置
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 统计
        self._stats = {
            "total": 0,
            "error": 0,
            "warning": 0,
            "info": 0,
            "by_type": {},  # error_type -> count
        }

    def start(self):
        """启动后台采集线程"""
        if self._running:
            return
        self._running = True
        self._last_position = self._get_file_size()
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="UnityLogCollector"
        )
        self._thread.start()
        logger.info("Unity日志采集器已启动: %s", self._log_path)

    def stop(self):
        """停止采集"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        logger.info("Unity日志采集器已停止")

    def get_entries(self, level: str = None,
                    error_type: str = None,
                    since: float = None,
                    limit: int = 50) -> List[Dict]:
        """
        获取日志条目

        :param level: 过滤级别 (error/warning/info)，None=全部
        :param error_type: 过滤错误类型（如 NullReferenceException）
        :param since: 起始时间戳
        :param limit: 返回条数上限
        :return: 日志条目列表
        """
        with self._lock:
            result = list(self._entries)

        if level:
            result = [e for e in result if e.get("level") == level]
        if error_type:
            result = [e for e in result if e.get("error_type") == error_type]
        if since:
            result = [e for e in result if e.get("timestamp", 0) >= since]

        return result[:limit]

    def get_errors(self, error_type: str = None,
                   limit: int = 50) -> List[Dict]:
        """获取错误日志"""
        return self.get_entries(level="error", error_type=error_type, limit=limit)

    def get_warnings(self, limit: int = 50) -> List[Dict]:
        """获取警告日志"""
        return self.get_entries(level="warning", limit=limit)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            return dict(self._stats)

    def get_log_path(self) -> str:
        """获取日志文件路径"""
        return self._log_path

    def is_file_available(self) -> bool:
        """检查日志文件是否存在"""
        return os.path.exists(self._log_path)

    # ============================================================
    # 内部方法
    # ============================================================

    def _poll_loop(self):
        """后台轮询循环"""
        while self._running:
            try:
                self._read_new_lines()
            except Exception as e:
                logger.debug("日志读取异常: %s", e)
            time.sleep(1.0)  # 每秒轮询

    def _get_file_size(self) -> int:
        try:
            return os.path.getsize(self._log_path)
        except OSError:
            return 0

    def _read_new_lines(self):
        """增量读取新日志行"""
        current_size = self._get_file_size()
        if current_size <= self._last_position:
            return  # 没有新内容

        try:
            with open(self._log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._last_position)
                new_lines = f.readlines()
                self._last_position = f.tell()
        except (IOError, OSError) as e:
            logger.debug("无法读取日志文件: %s", e)
            return

        for line in new_lines:
            line = line.rstrip("\n\r")
            if not line:
                continue
            entry = self._parse_line(line)
            if entry:
                with self._lock:
                    self._entries.append(entry)
                    self._stats["total"] += 1
                    self._stats["by_type"][entry.get("error_type", "other")] = \
                        self._stats["by_type"].get(entry.get("error_type", "other"), 0) + 1
                    if entry["level"] == "error":
                        self._errors.append(entry)
                        self._stats["error"] += 1
                    elif entry["level"] == "warning":
                        self._stats["warning"] += 1
                    else:
                        self._stats["info"] += 1
                    # 清理过期
                    self._trim_entries()

    def _parse_line(self, line: str) -> Optional[Dict]:
        """解析单行日志"""
        entry = {
            "raw": line[:200],  # 截断长行
            "timestamp": time.time(),
            "time_str": datetime.now().strftime("%H:%M:%S"),
            "level": "info",
            "error_type": None,
            "matched_pattern": None,
        }

        # 检测级别
        if line.startswith("[Error]") or line.startswith("Error:"):
            entry["level"] = "error"
        elif line.startswith("[Warning]") or line.startswith("Warning:"):
            entry["level"] = "warning"
        elif "NullReferenceException" in line or "MissingReferenceException" in line:
            entry["level"] = "error"
        elif "Exception" in line or "Assertion" in line:
            entry["level"] = "error"
        elif "error" in line.lower() and "Error" in line:
            entry["level"] = "error"

        # 检测错误类型
        if entry["level"] == "error":
            for etype, patterns in ERROR_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, line, re.IGNORECASE):
                        entry["error_type"] = etype
                        entry["matched_pattern"] = pat
                        break
                if entry["error_type"]:
                    break

        return entry

    def _trim_entries(self):
        """清理过期的日志条目"""
        while len(self._entries) > self._max_entries:
            self._entries.pop(0)
        while len(self._errors) > self._max_entries // 2:
            self._errors.pop(0)


# ============================================================
# 快捷函数
# ============================================================

_default_collector = None


def get_collector() -> UnityLogCollector:
    """获取全局单例采集器"""
    global _default_collector
    if _default_collector is None:
        _default_collector = UnityLogCollector()
    return _default_collector


def ensure_running():
    """确保采集器已启动"""
    c = get_collector()
    if not c._running:
        c.start()
    return c


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    print("=== UnityLogCollector 测试 ===\n")

    c = UnityLogCollector()

    # 测试1：文件可用性
    print(f"[测试1] 日志文件: {c.get_log_path()}")
    print(f"  存在: {c.is_file_available()}")

    # 测试2：启动采集（运行3秒）
    print("\n[测试2] 启动采集 (3秒)...")
    c.start()
    time.sleep(3)
    c.stop()

    stats = c.get_stats()
    print(f"  总条目: {stats['total']}")
    print(f"  错误: {stats['error']}")
    print(f"  警告: {stats['warning']}")

    # 测试3：获取错误
    errors = c.get_errors(limit=10)
    if errors:
        print(f"\n[测试3] 最近错误 ({len(errors)} 条):")
        for e in errors[:5]:
            print(f"  [{e['time_str']}] {e.get('error_type','?')}: {e['raw'][:60]}")
    else:
        print("\n[测试3] 无错误（文件不可用或无新日志）")

    print("\n✅ 测试完成")
