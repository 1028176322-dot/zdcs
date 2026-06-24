#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
崩溃检测器

功能：
  1. 检测 Unity Editor 进程是否存活
  2. 检测 Poco 连接是否断开
  3. 检测 Editor.log 中的崩溃关键字
  4. 输出结构化崩溃报告

工作方式：
  - 通过进程名 "Unity.exe" 检测 Editor 存活
  - 通过日志关键字检测崩溃
  - 可选 Poco 心跳检测

用法：
    detector = CrashDetector()
    result = detector.check()  # {"crashed": True/False, "detail": "...", "time": ...}
"""

import os
import time
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CrashDetector:
    """
    崩溃检测器

    检测维度：
    - P0: Unity Editor 进程是否存在
    - P1: Editor.log 中是否有崩溃关键字
    - P2: Poco 连接心跳（可选，需外部提供）
    """

    def __init__(self, unity_process_name: str = "Unity.exe",
                 poco_connector=None):
        self._process_name = unity_process_name
        self._poco = poco_connector
        self._last_ok_time = time.time()
        self._consecutive_failures = 0
        self._max_failures = 3  # 连续 3 次检测失败才判定崩溃

    def check(self) -> Dict:
        """
        执行崩溃检测

        :return: {
            "crashed": bool,
            "timestamp": float,
            "detail": str,
            "checks": [{"name": str, "passed": bool, "detail": str}, ...],
        }
        """
        checks = []
        crashed = False

        # P0: 进程存在性
        proc_check = self._check_process()
        checks.append(proc_check)
        if not proc_check["passed"]:
            crashed = True

        # P1: 日志崩溃关键字
        if not crashed:
            log_check = self._check_log_for_crash()
            checks.append(log_check)
            if not log_check["passed"]:
                crashed = True

        # P2: Poco 心跳（如有）
        if not crashed and self._poco:
            poco_check = self._check_poco_heartbeat()
            checks.append(poco_check)
            if not poco_check["passed"]:
                crashed = True

        result = {
            "crashed": crashed,
            "timestamp": time.time(),
            "time_str": datetime.now().strftime("%H:%M:%S"),
            "detail": "检测到崩溃" if crashed else "运行正常",
            "checks": checks,
        }

        if crashed:
            self._consecutive_failures += 1
        else:
            self._consecutive_failures = 0
            self._last_ok_time = time.time()

        return result

    def is_crashed(self) -> bool:
        """快速检查是否已崩溃（连续失败超过阈值）"""
        return self._consecutive_failures >= self._max_failures

    def get_uptime(self) -> float:
        """获取正常运行时间（秒）"""
        if self._consecutive_failures >= self._max_failures:
            return 0
        return time.time() - self._last_ok_time

    # ============================================================
    # 内部检测方法
    # ============================================================

    def _check_process(self) -> Dict:
        """
        检查 Unity Editor 进程是否存在

        使用 tasklist 命令（Windows 通用）
        """
        try:
            import subprocess
            result = subprocess.run(
                ["tasklist", "/NH", "/FI", f"IMAGENAME eq {self._process_name}"],
                capture_output=True, text=True, timeout=5,
            )
            if self._process_name in result.stdout:
                return {"name": "process_exists", "passed": True,
                        "detail": f"进程 {self._process_name} 运行中"}
            else:
                return {"name": "process_exists", "passed": False,
                        "detail": f"进程 {self._process_name} 未找到"}
        except Exception as e:
            return {"name": "process_exists", "passed": True,
                    "detail": f"进程检测异常（放行）: {e}"}

    def _check_log_for_crash(self) -> Dict:
        """
        检查 Editor.log 中最近的崩溃关键字

        查看最近的日志行中是否有 Fatal/crash/aborting 等关键字
        """
        log_path = os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Unity", "Editor", "Editor.log"
        )
        if not os.path.exists(log_path):
            return {"name": "log_crash_check", "passed": True,
                    "detail": "日志文件不存在，跳过"}

        try:
            # 只读最后 50 行
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-50:]

            crash_keywords = ["Fatal error!", "Fatal:", "crash", "aborting",
                              "crashed", "0xC0000005", "access violation"]
            for line in lines:
                for kw in crash_keywords:
                    if kw.lower() in line.lower():
                        return {"name": "log_crash_check", "passed": False,
                                "detail": f"日志发现崩溃关键字 '{kw}': {line[:100].strip()}"}
        except Exception as e:
            return {"name": "log_crash_check", "passed": True,
                    "detail": f"日志读取异常（放行）: {e}"}

        return {"name": "log_crash_check", "passed": True,
                "detail": "未发现崩溃关键字"}

    def _check_poco_heartbeat(self) -> Dict:
        """检查 Poco 连接心跳"""
        try:
            if self._poco and hasattr(self._poco, "ping"):
                ok = self._poco.ping()
                if ok:
                    return {"name": "poco_heartbeat", "passed": True,
                            "detail": "Poco 连接正常"}
                else:
                    return {"name": "poco_heartbeat", "passed": False,
                            "detail": "Poco 心跳无响应"}
            else:
                return {"name": "poco_heartbeat", "passed": True,
                        "detail": "Poco 未配置，跳过"}
        except Exception as e:
            return {"name": "poco_heartbeat", "passed": False,
                    "detail": f"Poco 检测异常: {e}"}


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    print("=== CrashDetector 测试 ===\n")

    detector = CrashDetector()

    # 测试1：进程存在性
    print("[测试1] 进程检测...")
    r = detector._check_process()
    print(f"  passed={r['passed']}: {r['detail']}")

    # 测试2：日志崩溃检测
    print("\n[测试2] 日志崩溃检测...")
    r = detector._check_log_for_crash()
    print(f"  passed={r['passed']}: {r['detail']}")

    # 测试3：完整检测
    print("\n[测试3] 完整检测...")
    r = detector.check()
    print(f"  crashed={r['crashed']}: {r['detail']}")
    for c in r["checks"]:
        print(f"    [{c['name']}] passed={c['passed']}: {c['detail']}")

    print("\n✅ 测试完成")
