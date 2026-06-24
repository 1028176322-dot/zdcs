#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSmoke Web IDE — 统一入口

用法：
    python autosmoke_web_ide.py            # 启动 IDE（默认端口 5000，调试模式开）
    python autosmoke_web_ide.py --check     # 仅检查环境状态
    python autosmoke_web_ide.py --port 8080 # 指定端口
    python autosmoke_web_ide.py --no-debug  # 关闭调试模式（生产用）

💡 调试模式（默认开启）：修改 IDE 代码后自动重载，只需刷新浏览器页面

环境检查：
    - Python >= 3.11
    - openpyxl  (Excel 读取)
    - pywin32   (Windows API/截图/点击)
    - opencv-python (图像分析，可选)
    - pytesseract (OCR，可选)
"""

import sys
import os
import json
import subprocess
import shutil
from pathlib import Path

# 确保项目根在 sys.path
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)


# ============================================================
# 环境检查
# ============================================================

def check_python():
    req = (3, 11)
    cur = sys.version_info[:2]
    ok = cur >= req
    print(f"  Python: {sys.version.split()[0]} ({'✅' if ok else '❌ 需要 3.11+'})")
    return ok


def check_module(name, pip_name=None, optional=False):
    try:
        __import__(name)
        pkg = __import__(name)
        ver = getattr(pkg, "__version__", "?")
        print(f"  {pip_name or name}: ✅ {ver}")
        return True
    except ImportError:
        status = "⏳ 可选" if optional else "❌ 缺失"
        print(f"  {pip_name or name}: {status}")
        return optional  # optional=True 时不阻断


def check_tesseract():
    """检查 Tesseract-OCR 二进制是否可用"""
    tesseract_cmd = shutil.which("tesseract")
    # 如果不在 PATH，检查常见安装路径
    if not tesseract_cmd:
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in common_paths:
            if os.path.exists(p):
                tesseract_cmd = p
                break
    if tesseract_cmd:
        try:
            result = subprocess.run(
                [tesseract_cmd, "--version"],
                capture_output=True, text=True, timeout=5
            )
            first_line = result.stdout.split("\n")[0] if result.stdout else "?"
            print(f"  Tesseract-OCR: ✅ {first_line}")
            return True
        except Exception:
            pass
    print("  Tesseract-OCR: ⏳ 未安装（OCR 功能不可用）")
    return True  # 不阻断


def check_unity_project():
    """检查 Unity 项目路径配置"""
    cfg_path = os.path.join(_script_dir, "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            proj = cfg.get("unity_project_path", "")
            if proj and os.path.exists(os.path.join(proj, "Assets")):
                print(f"  Unity 项目: ✅ {proj}")
                return True
            else:
                print(f"  Unity 项目: ⏳ 未配置（部分功能受限）")
                return True
        except Exception:
            pass
    print("  Unity 项目: ⏳ 未配置")
    return True


def write_autosmoke_config():
    """写入 autosmoke_root 到 ~/.autosmoke/config.json，供 Unity C# 脚本读取输出路径"""
    bridge_dir = Path(os.path.expanduser("~")) / ".autosmoke"
    bridge_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = bridge_dir / "config.json"

    # 读取已有配置
    cfg = {}
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    # 写入 autosmoke_root（相对路径，不含绝对硬编码）
    cfg["autosmokeRoot"] = _script_dir.replace("\\", "/")

    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"  AutoSmoke 根目录: ✅ {_script_dir}")
    except Exception as e:
        print(f"  AutoSmoke 根目录: ⚠️ 写入失败: {e}")


def do_check():
    """执行全部环境检查"""
    print("=" * 50)
    print("  AutoSmoke 环境检查")
    print("=" * 50)
    print()

    results = []

    print("--- 基础环境 ---")
    results.append(check_python())

    print()
    print("--- 核心依赖 ---")
    results.append(check_module("flask", "flask"))
    results.append(check_module("PIL", "pillow"))
    results.append(check_module("numpy", "numpy"))
    results.append(check_module("win32api", "pywin32"))

    print()
    print("--- 功能依赖（可选） ---")
    check_module("cv2", "opencv-python", optional=True)
    check_module("openpyxl", "openpyxl", optional=True)
    check_tesseract()

    print()
    print("--- 配置 ---")
    check_unity_project()
    write_autosmoke_config()

    print()
    all_pass = all(r for r in results)
    if all_pass:
        print("✅ 环境检查通过 — 可以启动 IDE")
    else:
        print("❌ 存在缺失依赖，请修复后重试")
    return all_pass


# ============================================================
# 启动 IDE
# ============================================================

def start_ide(port=5000, debug=True):
    """启动 Flask IDE（含 PID 锁 + 端口保护）"""
    print(f"🚀 AutoSmoke Web IDE 启动中...")
    print(f"   地址: http://localhost:{port}")
    print(f"   调试: {'开启' if debug else '关闭'}")
    print(f"   💡 调试模式下修改代码后自动加载，刷新页面即可")
    print()

    # ---- PID 锁 ----
    runtime_dir = Path(_script_dir) / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    pid_file = runtime_dir / "web_ide.pid"

    # 检查旧 PID
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text().strip())
            # 检查进程是否存活（Windows 上 PROCESS_QUERY_INFORMATION）
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0400, False, old_pid)  # PROCESS_QUERY_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                # PID can be stale or reused. Treat it as live only when the IDE port is listening.
                import socket
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        print(f"??  IDE ???? (PID={old_pid})??????")
                        print(f"   ?? http://localhost:{port}")
                        return
                except (ConnectionRefusedError, OSError, TimeoutError):
                    pass
        except (ValueError, OSError, AttributeError):
            pass
        pid_file.unlink(missing_ok=True)

    # 写新 PID
    pid_file.write_text(str(os.getpid()))
    print(f"📌 PID={os.getpid()} (锁文件: runtime/web_ide.pid)")

    # ---- 端口检查 ----
    try:
        import socket
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            print(f"❌ 端口 {port} 已被占用，无法启动")
            return
    except (ConnectionRefusedError, OSError, TimeoutError):
        pass  # 端口空闲

    # 导入并启动
    from IDE.debug_panel import app
    print("✅ IDE 面板已加载")
    print()
    try:
        app.run(host="0.0.0.0", port=port, debug=debug)
    finally:
        # 退出时清理 PID
        if pid_file.exists():
            pid_file.unlink(missing_ok=True)


# ============================================================
# 主函数
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="AutoSmoke Web IDE — Unity 游戏自动化测试系统"
    )
    parser.add_argument("--check", action="store_true",
                        help="仅检查环境状态，不启动")
    parser.add_argument("--port", type=int, default=5000,
                        help="IDE 端口（默认 5000）")
    parser.add_argument("--debug", action="store_true",
                        help="以调试模式启动 Flask（默认已开启）")
    parser.add_argument("--no-debug", dest="debug", action="store_false",
                        help="关闭调试模式（生产环境用）")
    args = parser.parse_args()

    if args.check:
        ok = do_check()
        sys.exit(0 if ok else 1)

    # 默认：先检查再启动
    print()
    ok = do_check()
    print()
    if not ok:
        print("⚠️  依赖检查未通过，仍尝试启动...")
        print()

    start_ide(port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
