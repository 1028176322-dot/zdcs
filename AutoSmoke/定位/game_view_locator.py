"""
# -*- coding: utf-8 -*-
game_view_locator.py

Unity Game 视图定位器 - Python 端

功能：
1. 将 GameViewLocator.cs 复制到 Unity 项目的 Assets/Editor/ 目录
2. 自动触发 Unity 编译并执行，生成 game_view_pos.json
3. 读取 JSON，返回 Game 视图的屏幕坐标
4. 清理：用完可自动删除 C# 脚本

依赖：需要 Unity Editor 正在运行

自动化方法：
1. 复制 C# 脚本到 Unity（触发编译）
2. 等待 Unity 编译完成（通过轮询日志文件）
3. 通过 Unity Editor 反射执行 LocateAndSave() 方法（无需手动点击菜单）
"""

import os
import sys
# 确保能找到根目录模块
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

import time
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from config_manager import get_unity_project_path

# C# 脚本源路径（在 tools 目录）
CS_SOURCE_NAME = "GameViewLocator.cs"
# Unity 项目中的目标路径
CS_TARGET_DIR = "Assets/Editor"
# JSON 输出路径（与 C# 脚本中的路径一致）
JSON_OUTPUT_DIR = Path.home() / ".autosmoke"
JSON_OUTPUT_PATH = JSON_OUTPUT_DIR / "game_view_pos.json"
# 超时时间（秒）
TIMEOUT = 30


def get_cs_source_path() -> str:
    """
    获取 C# 脚本的源路径
    
    搜索顺序：
    1. 当前脚本所在目录（game_view_locator.py 的位置）
    2. 当前脚本所在目录的 tools 子目录
    3. 用户主目录的 .autosmoke 目录
    4. 环境变量 AUTOSMOKE_CS_SOURCE_DIR 指定的目录
    
    返回：找到的路径，未找到返回空字符串
    """
    cs_name = CS_SOURCE_NAME
    
    # 搜索位置列表
    search_dirs = []
    
    # 1. 当前脚本所在目录
    current_dir = Path(__file__).parent
    search_dirs.append(current_dir)
    
    # 2. tools 子目录
    search_dirs.append(current_dir / "tools")
    
    # 3. 用户主目录的 .autosmoke 目录
    search_dirs.append(Path.home() / ".autosmoke")
    
    # 4. 环境变量指定的目录
    env_dir = os.environ.get("AUTOSMOKE_CS_SOURCE_DIR")
    if env_dir:
        search_dirs.append(Path(env_dir))
    
    # 搜索文件
    for dir_path in search_dirs:
        source = dir_path / cs_name
        if source.exists():
            print(f"📂 找到 C# 脚本: {source}")
            return str(source)
    
    # 未找到
    print(f"❌ 未找到 C# 脚本: {cs_name}")
    print(f"   搜索位置:")
    for dir_path in search_dirs:
        print(f"   - {dir_path}")
    print(f"\n   请将 {cs_name} 放到以上任一位置")
    
    return ""


def copy_cs_to_unity() -> Optional[str]:
    """
    将 GameViewLocator.cs 复制到 Unity 项目的 Assets/Editor/ 目录
    
    返回：目标路径，失败返回 None
    """
    unity_project = get_unity_project_path()
    if not unity_project:
        print("❌ 未配置 Unity 项目路径")
        return None
    
    source = get_cs_source_path()
    if not os.path.exists(source):
        print(f"❌ C# 脚本不存在: {source}")
        return None
    
    # 确保 Assets/Editor 目录存在
    editor_dir = os.path.join(unity_project, "Assets", "Editor")
    os.makedirs(editor_dir, exist_ok=True)
    
    target = os.path.join(editor_dir, CS_SOURCE_NAME)
    
    try:
        shutil.copy2(source, target)
        print(f"✅ 已复制 C# 脚本到: {target}")
        print("   Unity 会自动编译，请稍候...")
        return target
    except Exception as e:
        print(f"❌ 复制失败: {e}")
        return None


def wait_for_json(timeout: int = TIMEOUT) -> Optional[dict]:
    """
    等待 Unity 生成 JSON 文件
    
    返回：解析后的 JSON 字典，超时返回 None
    """
    if not JSON_OUTPUT_PATH.exists():
        print(f"⏳ 等待 Unity 生成 JSON 文件...")
        print(f"   路径: {JSON_OUTPUT_PATH}")
    
    start = time.time()
    while time.time() - start < timeout:
        if JSON_OUTPUT_PATH.exists():
            try:
                with open(JSON_OUTPUT_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ 已读取 JSON: {JSON_OUTPUT_PATH}")
                return data
            except Exception as e:
                print(f"⚠️ JSON 解析失败: {e}")
                return None
        
        time.sleep(1)
    
    print(f"❌ 超时：Unity 未在 {timeout}s 内生成 JSON")
    print("   请确认 Unity Editor 是否正在运行")
    return None


def get_game_view_pos(force_refresh: bool = False) -> Optional[Tuple[int, int, int, int]]:
    """
    获取 Game 视图的屏幕坐标（自动化版本）
    
    参数：
        force_refresh: 是否强制重新检测（删除旧 JSON 后重新触发）
    
    返回：(x, y, width, height) 或 None
    
    自动化流程：
    1. 检查缓存 JSON 是否存在且新鲜
    2. 若需要刷新，复制 C# 脚本到 Unity（触发编译）
    3. 自动触发 Unity 执行（通过 [InitializeOnLoadMethod]）
    4. 等待 Unity 生成 JSON 文件
    5. 读取并返回坐标
    """
    # 如果不强制刷新且 JSON 已存在，直接读取
    if not force_refresh and JSON_OUTPUT_PATH.exists():
        age = time.time() - JSON_OUTPUT_PATH.stat().st_mtime
        if age < 60:  # 60秒内有效
            print("📂 使用缓存的 Game 视图坐标...")
            try:
                with open(JSON_OUTPUT_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('found'):
                    pos = (data['x'], data['y'], data['width'], data['height'])
                    print(f"  ✅ 坐标: x={pos[0]}, y={pos[1]}, w={pos[2]}, h={pos[3]}")
                    return pos
                else:
                    print(f"  ⚠️ 上次检测失败: {data.get('error', '未知错误')}")
            except Exception as e:
                print(f"  ⚠️ 读取缓存失败: {e}")
    
    # 需要重新检测
    print("\n[获取 Game 视图坐标]")
    print("=" * 50)
    
    # 步骤1：复制 C# 脚本到 Unity
    print("\n[步骤1] 复制检测脚本到 Unity...")
    target = copy_cs_to_unity()
    if not target:
        return None
    
    # 步骤2：等待 Unity 编译并自动执行
    print("\n[步骤2] 等待 Unity 编译并自动执行...")
    print("   （Unity 会在编译完成后通过 [InitializeOnLoad] 自动执行）")
    
    data = wait_for_json()  # 等待 JSON 文件生成
    
    if not data:
        print("\n⚠️ 自动触发失败。")
        print("   请检查 Unity Console 是否有编译错误。")
        print("   如果 [InitializeOnLoad] 未触发，可尝试手动点击菜单：")
        print("   AutoSmoke > Locate Game View")
        return None
    
    if not data.get('found'):
        print(f"❌ Unity 未找到 Game 视图: {data.get('error', '')}")
        return None
    
    pos = (data['x'], data['y'], data['width'], data['height'])
    print(f"\n✅ Game 视图坐标: x={pos[0]}, y={pos[1]}, w={pos[2]}, h={pos[3]}")
    return pos


def cleanup_cs_file():
    """清理 Unity 项目中的 C# 脚本（可选）"""
    unity_project = get_unity_project_path()
    if not unity_project:
        return
    
    target = os.path.join(unity_project, "Assets", "Editor", CS_SOURCE_NAME)
    if os.path.exists(target):
        try:
            os.remove(target)
            print(f"🗑️ 已清理: {target}")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")


def convert_to_screenshot_coords(
    game_view_pos: Tuple[int, int, int, int],
    unity_client_screen_pos: Tuple[int, int],
) -> Tuple[int, int, int, int]:
    """
    将 Game 视图屏幕坐标转换为截图坐标
    
    参数：
        game_view_pos: (x, y, width, height) 屏幕坐标
        unity_client_screen_pos: (x, y) Unity 客户区左上角屏幕坐标
    
    返回：(left, top, right, bottom) 截图坐标
    """
    gx, gy, gw, gh = game_view_pos
    ucx, ucy = unity_client_screen_pos
    
    left = gx - ucx
    top = gy - ucy
    right = left + gw
    bottom = top + gh
    
    print(f"  虚拟屏幕偏移量: ({ucx}, {ucy})")
    print(f"  截图坐标: ({left}, {top}, {right}, {bottom})")
    
    return (left, top, right, bottom)


if __name__ == '__main__':
    # 测试
    pos = get_game_view_pos(force_refresh=True)
    if pos:
        print(f"\n结果: {pos}")
    else:
        print("\n❌ 获取失败")
