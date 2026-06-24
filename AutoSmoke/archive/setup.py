#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署环境自动配置脚本
==================================================

用法（二选一）：
  1. 交互模式：python setup.py
  2. 修改本文件顶部 WORK_ROOT / UNITY_PROJECT 后运行（非交互模式）

功能：
  根据输入的路径，自动生成所有脚本文件（C# / Python / Bat）
  生成的文件含正确路径，可直接用于部署
"""

import os
import sys

# ============================================================
#  请在下方修改路径，然后直接运行 python setup.py
# ============================================================
WORK_ROOT     = r""     # 例：D:\AutoTest
UNITY_PROJECT = r""     # 例：E:\s1\k3client\client
# ============================================================


def mkdirs(path):
    os.makedirs(path, exist_ok=True)
    return path


def write_file(path, content, encoding="utf-8"):
    mkdirs(os.path.dirname(path))
    with open(path, "w", encoding=encoding) as f:
        f.write(content)
    print(f"  ✅ {path}")


def read_template(name):
    """读取模板文件，找不到则返回 None"""
    base = os.path.dirname(os.path.abspath(__file__))
    tpl = os.path.join(base, "templates", name)
    if os.path.exists(tpl):
        with open(tpl, "r", encoding="utf-8") as f:
            return f.read()
    return None


def main():
    print("=" * 60)
    print("  Poco + NetMessageMonitor 环境 — 首次配置")
    print("=" * 60)
    print()

    # ---------- 获取路径 ----------
    if WORK_ROOT and UNITY_PROJECT:
        work_root    = WORK_ROOT.replace("\\", "/").rstrip("/")
        unity_project = UNITY_PROJECT.replace("\\", "/").rstrip("/")
        print(f"【使用预设路径】")
        print(f"  WORK_ROOT    = {work_root}")
        print(f"  UNITY_PROJECT = {unity_project}")
    else:
        print("【第一步】设置工作根目录（脚本/日志/报告存放处）")
        print("  例：D:/AutoTest  或  E:/zdcs")
        work_root = input("  路径：").strip().replace("\\", "/").rstrip("/")
        while not work_root:
            print("  ⚠️  不能为空")
            work_root = input("  路径：").strip().replace("\\", "/").rstrip("/")

        print()
        print("【第二步】设置 Unity 工程根目录（含 Assets/ 的那层）")
        print("  例：E:/s1/k3client/client")
        unity_project = input("  路径：").strip().replace("\\", "/").rstrip("/")
        while not unity_project:
            print("  ⚠️  不能为空")
            unity_project = input("  路径：").strip().replace("\\", "/").rstrip("/")

    print()
    print(f"  工作目录：{work_root}")
    print(f"  Unity 工程：{unity_project}")
    print()

    # 推导路径
    log_path_unix = work_root + "/AutoSmoke/logs/net_messages.log"
    log_path_cs   = log_path_unix.replace("/", "\\\\")   # C# 字符串用双反斜杠
    poco_target    = unity_project + "/Assets/Poco"
    poco_backup    = work_root    + "/Poco-SDK/Unity3D"

    # ---------- 创建目录 ----------
    print("【第三步】创建目录结构...")
    for d in [
        work_root    + "/AutoSmoke",
        work_root    + "/AutoSmoke/modules",
        work_root    + "/AutoSmoke/logs",
        work_root    + "/AutoSmoke/reports",
        work_root    + "/Poco-SDK/Unity3D",
        unity_project + "/Assets/Poco",
    ]:
        mkdirs(d)
        print(f"  ✅ {d}")
    print()

    # ---------- 生成 NetMessageMonitor.cs ----------
    print("【第四步】生成 C# 脚本...")

    tpl = read_template("NetMessageMonitor.cs.template")
    if tpl:
        cs1 = tpl.replace("__LOG_PATH__", log_path_cs)
        write_file(unity_project + "/Assets/Poco/NetMessageMonitor.cs", cs1)
    else:
        print("  ⚠️  找不到模板：templates/NetMessageMonitor.cs.template")
        print("      请确认 setup.py 与 templates/ 在同一目录")

    # ---------- 生成 AutoStartPoco.cs ----------
    tpl2 = read_template("AutoStartPoco.cs.template")
    if tpl2:
        cs2 = tpl2.replace("__LOG_PATH__", log_path_cs)
        write_file(unity_project + "/Assets/Poco/AutoStartPoco.cs", cs2)
    else:
        print("  ⚠️  找不到模板：templates/AutoStartPoco.cs.template")

    print()

    # ---------- 生成 net_monitor_watcher.py ----------
    print("【第五步】生成 Python 模块...")

    py_content = read_template("net_monitor_watcher.py.template")
    if py_content:
        py = py_content.replace("__LOG_PATH__", log_path_unix)
        write_file(work_root + "/AutoSmoke/modules/net_monitor_watcher.py", py)
    else:
        # 内置模板
        py = _get_net_monitor_py(log_path_unix)
        write_file(work_root + "/AutoSmoke/modules/net_monitor_watcher.py", py)
        print("  ⚠️  使用内置模板（templates/ 目录未找到）")

    print()

    # ---------- 生成 redeploy_poco.bat ----------
    print("【第六步】生成重新部署脚本...")

    bat = read_template("redeploy_poco.bat.template")
    if bat:
        bat = bat.replace("__UNITY_PROJECT__", unity_project.replace("/", "\\\\"))
        bat = bat.replace("__POCO_BACKUP__",   poco_backup.replace("/", "\\\\"))
        bat = bat.replace("__POCO_TARGET__",   poco_target.replace("/", "\\\\"))
        write_file(work_root + "/redeploy_poco.bat", bat, encoding="gbk")
    else:
        bat = _get_redeploy_bat(unity_project, work_root, poco_backup, poco_target)
        write_file(work_root + "/redeploy_poco.bat", bat, encoding="gbk")
        print("  ⚠️  使用内置模板（templates/ 目录未找到）")

    print()

    # ---------- 生成 requirements.txt ----------
    print("【第七步】生成 requirements.txt...")
    req = "airtest>=1.2.0\npocoui>=1.0.0\nPillow>=9.0.0\nopencv-python>=4.5.0\npywin32>=300\n"
    write_file(work_root + "/AutoSmoke/requirements.txt", req)
    print()

    # ---------- 完成 ----------
    print("=" * 60)
    print("  ✅  配置完成！")
    print("=" * 60)
    print()
    print("📁 已生成的文件：")
    print(f"  C#:  {unity_project}/Assets/Poco/NetMessageMonitor.cs")
    print(f"        {unity_project}/Assets/Poco/AutoStartPoco.cs")
    print(f"  Python: {work_root}/AutoSmoke/modules/net_monitor_watcher.py")
    print(f"  Bat:   {work_root}/redeploy_poco.bat")
    print(f"  Req:   {work_root}/AutoSmoke/requirements.txt")
    print()
    print("📌 下一步：")
    print("   1. 下载 Poco SDK（https://github.com/AirtestProject/Poco-Sdk/archive/refs/heads/master.zip）")
    print(f"   2. 解压后，将 Unity3D/ 目录复制到：")
    print(f"      {poco_backup}")
    print(f"   3. 在 Unity 编辑器中打开工程，等待编译")
    print(f"   4. 确认 Console 出现：[NetMonitor] Initialized")
    print(f"   5. 安装 Python 依赖：cd {work_root.replace('/', '\\\\')}\\AutoSmoke && pip install -r requirements.txt")
    print()
    try:
        input("按 Enter 退出...")
    except:
        pass


# ============================================================
#  内置模板（当 templates/ 目录不存在时使用）
# ============================================================

def _get_net_monitor_py(log_path_unix):
    """返回 net_monitor_watcher.py 内容（内置）"""
    return '''"""
网络消息监控 - Python端
读取 NetMessageMonitor (C#) 输出的 net_messages.log 文件
提供 clear / poll / summary 接口
"""

import os
import re
import time
from datetime import datetime
from typing import List, Dict, Optional


DEFAULT_LOG_PATH = "''' + log_path_unix + '''"


class NetMessage:
    """一条网络消息记录"""
    def __init__(self, line: str):
        self.raw = line.strip()
        self.time: str = ''
        self.dir: str = ''
        self.type: str = ''
        self.content: str = ''
        self._parse()

    def _parse(self):
        parts = self.raw.split('|', 3)
        if len(parts) >= 4:
            self.time = parts[0].strip()
            self.dir = parts[1].strip()
            self.type = parts[2].strip()
            self.content = parts[3].strip()
        elif len(parts) == 3:
            self.time = parts[0].strip()
            self.dir = parts[1].strip()
            self.type = parts[2].strip()

    def is_send(self) -> bool:
        return self.dir == 'SEND'

    def is_recv(self) -> bool:
        return self.dir == 'RECV'

    def short_type(self) -> str:
        return self.type.split('.')[-1] if '.' in self.type else self.type

    def __repr__(self):
        return f"[{self.time}][{self.dir}] {self.short_type()}"


class NetMonitorWatcher:
    """网络消息日志阅读器（自动过滤噪音）"""

    NOISE_TYPES = {
        'heartbeatreq', 'heartbeatack',
        'positionntf',
        'rallyntf', 'rallylistack', 'rallylistreq',
        'getunionmessagereq', 'getunionmessageack',
    }

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or DEFAULT_LOG_PATH
        self._cursor = 0

    def clear(self):
        """清空日志文件 + 重置游标"""
        try:
            open(self.log_path, 'w').close()
        except:
            pass
        self._cursor = 0

    def poll(self, filter_noise: bool = True) -> List[NetMessage]:
        if not os.path.exists(self.log_path):
            return []
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                f.seek(self._cursor)
                lines = f.readlines()
                self._cursor = f.tell()
        except:
            return []

        messages = []
        for line in lines:
            line = line.strip()
            if not line or '|' not in line:
                continue
            try:
                msg = NetMessage(line)
                if filter_noise and self._is_noise(msg):
                    continue
                messages.append(msg)
            except:
                pass
        return messages

    def poll_blocking(self, timeout: float = 2.0) -> List[NetMessage]:
        deadline = time.time() + timeout
        all_msgs = []
        while time.time() < deadline:
            msgs = self.poll()
            if msgs:
                all_msgs.extend(msgs)
                deadline = time.time() + 0.5
            time.sleep(0.1)
        return all_msgs

    def summary(self) -> Dict:
        if not os.path.exists(self.log_path):
            return {"send": 0, "recv": 0}
        send_count = 0
        recv_count = 0
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('|', 2)
                    if len(parts) >= 2:
                        if parts[1].strip() == 'SEND':
                            send_count += 1
                        elif parts[1].strip() == 'RECV':
                            recv_count += 1
        except:
            pass
        return {"send": send_count, "recv": recv_count}

    def get_message_types(self, messages: List[NetMessage]) -> List[str]:
        seen = set()
        types = []
        for m in messages:
            if m.type not in seen:
                seen.add(m.type)
                types.append(m.type)
        return types

    def _is_noise(self, msg: NetMessage) -> bool:
        short = msg.short_type().lower()
        if short.startswith('bireport'):
            return True
        return short in self.NOISE_TYPES


def quick_test():
    monitor = NetMonitorWatcher()
    print(f"📁 日志文件: {monitor.log_path}")
    print(f"📊 总计: {monitor.summary()}")
    msgs = monitor.read_all()
    print(f"📋 当前消息 ({len(msgs)} 条):")
    for m in msgs[-5:]:
        print(f"   {m}")

if __name__ == '__main__':
    quick_test()
'''


def _get_redeploy_bat(unity_project, work_root, poco_backup, poco_target):
    """返回 redeploy_poco.bat 内容（内置）"""
    up = unity_project.replace('/', '\\\\')
    pb = poco_backup.replace('/', '\\\\')
    pt = poco_target.replace('/', '\\\\')
    wr = work_root.replace('/', '\\\\')
    return f"""@echo off
REM =========================================================
REM  Poco SDK 一键重新部署脚本
REM   当 Unity 清理/还原工程后，双击此脚本即可恢复
REM =========================================================

set UNITY_PROJECT={up}
set POCO_BACKUP={pb}
set POCO_TARGET=%UNITY_PROJECT%\\Assets\\Poco

echo.
echo ========== Poco SDK 部署 ==========
echo.

if not exist "%POCO_BACKUP%\\PocoManager.cs" (
    echo [错误] 备份文件不存在：%POCO_BACKUP%
    echo 请先将 Poco SDK 备份到 %POCO_BACKUP%
    pause
    exit /b 1
)

if exist "%POCO_TARGET%" (
    echo [1/4] 清理旧的 Poco 目录...
    rmdir /s /q "%POCO_TARGET%"
)

echo [2/4] 从备份恢复 Poco SDK...
mkdir "%POCO_TARGET%"
xcopy /E /I /Y "%POCO_BACKUP%\\3rdLib" "%POCO_TARGET%\\3rdLib\\" >nul
xcopy /E /I /Y "%POCO_BACKUP%\\sdk" "%POCO_TARGET%\\sdk\\" >nul
xcopy /E /I /Y "%POCO_BACKUP%\\uguiWithTMPro" "%POCO_TARGET%\\uguiWithTMPro\\" >nul
copy /Y "%POCO_BACKUP%\\*.cs" "%POCO_TARGET%\\" >nul

echo [3/4] 清理不需要的 UI 框架（fairygui / ngui / ugui）...
if exist "%POCO_TARGET%\\fairygui" rmdir /s /q "%POCO_TARGET%\\fairygui"
if exist "%POCO_TARGET%\\ngui" rmdir /s /q "%POCO_TARGET%\\ngui"
if exist "%POCO_TARGET%\\ugui" rmdir /s /q "%POCO_TARGET%\\ugui"

echo [4/4] 部署完成！
echo.
echo =========================================================
echo  已恢复 Poco SDK -> %POCO_TARGET%
echo  请回到 Unity 编辑器，等待编译完成
echo  确认 Console 出现：[NetMonitor] Initialized
echo =========================================================
echo.
pause
"""


if __name__ == "__main__":
    main()
