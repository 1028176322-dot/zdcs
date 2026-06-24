"""
配置文件管理工具

配置优先级（从高到低）：
1. 环境变量：AUTOSMOKE_UNITY_PROJECT_PATH
2. 配置文件：~/.autosmoke/config.json
3. 自动检测：查找当前目录及父目录中的 Assets 文件夹
"""

import json
import os
import sys
from pathlib import Path

# 配置文件路径（用户主目录下，跨项目共享）
CONFIG_DIR = Path.home() / ".autosmoke"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """加载配置文件"""
    # 如果配置文件不存在，尝试从旧位置迁移
    if not CONFIG_FILE.exists():
        old_config = Path(__file__).parent / "config.json"
        if old_config.exists():
            print(f"📂 迁移配置文件: {old_config} -> {CONFIG_FILE}")
            CONFIG_DIR.mkdir(exist_ok=True)
            import shutil
            shutil.copy2(old_config, CONFIG_FILE)
    
    if not CONFIG_FILE.exists():
        return create_default_config()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 配置文件读取失败: {e}")
        return create_default_config()


def save_config(config: dict):
    """保存配置文件"""
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ 配置已保存到: {CONFIG_FILE}")
    except Exception as e:
        print(f"❌ 配置保存失败: {e}")


def create_default_config() -> dict:
    """创建默认配置"""
    default_config = {
        "game_resolution": {
            "width": 1170,
            "height": 2532
        },
        "auto_detect_region": True,
        "black_threshold": 30
    }
    save_config(default_config)
    return default_config


def get_game_resolution() -> tuple:
    """
    获取游戏分辨率
    返回: (width, height)
    """
    config = load_config()
    resolution = config.get("game_resolution", {})
    width = resolution.get("width", 1170)
    height = resolution.get("height", 2532)
    return width, height


def get_unity_project_path() -> str:
    """
    获取 Unity 项目路径
    优先级（从高到低）：
    1. 环境变量：AUTOSMOKE_UNITY_PROJECT_PATH
    2. 配置文件：~/.autosmoke/config.json
    3. 自动检测：查找当前目录及父目录中的 Assets 文件夹
    
    返回：路径字符串，未找到返回空字符串
    """
    # 优先级1：环境变量
    env_path = os.environ.get("AUTOSMOKE_UNITY_PROJECT_PATH")
    if env_path and Path(env_path).exists():
        print(f"📂 Unity 项目路径（环境变量）: {env_path}")
        return env_path
    
    # 优先级2：配置文件
    config = load_config()
    saved_path = config.get("unity_project_path", "")
    if saved_path and Path(saved_path).exists():
        print(f"📂 Unity 项目路径（配置文件）: {saved_path}")
        return saved_path
    
    # 优先级3：自动检测
    detected_path = auto_detect_unity_project_path()
    if detected_path:
        print(f"📂 Unity 项目路径（自动检测）: {detected_path}")
        # 保存到配置文件
        config["unity_project_path"] = detected_path
        save_config(config)
        return detected_path
    
    # 未找到
    print("⚠️ 未找到 Unity 项目路径")
    print("   请设置环境变量 AUTOSMOKE_UNITY_PROJECT_PATH")
    print("   或在配置文件中指定 unity_project_path")
    return ""


def auto_detect_unity_project_path() -> str:
    """
    自动检测 Unity 项目路径
    
    方法：
    1. 查找当前目录及父目录中是否有 Assets 文件夹
    2. 查找子目录中是否有 Assets 文件夹（最多 3 层）
    
    返回：路径字符串，未找到返回空字符串
    """
    # 方法1：查找当前目录及父目录
    try:
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / "Assets").exists():
                return str(parent)
    except Exception:
        pass
    
    # 方法2：查找脚本所在目录及父目录
    try:
        script_dir = Path(__file__).parent
        for parent in [script_dir] + list(script_dir.parents):
            if (parent / "Assets").exists():
                return str(parent)
    except Exception:
        pass
    
    # 未找到
    return ""


def set_unity_project_path(path: str):
    """设置 Unity 项目路径并保存到配置文件"""
    config = load_config()
    config["unity_project_path"] = path
    save_config(config)
    print(f"✅ Unity 项目路径已保存: {path}")


def set_game_resolution(width: int, height: int):
    """设置游戏分辨率"""
    config = load_config()
    config["game_resolution"] = {
        "width": width,
        "height": height
    }
    save_config(config)
    print(f"✅ 游戏分辨率已设置为: {width}x{height}")


def get_game_view_coords() -> dict:
    """
    获取 Game 视图坐标（截图坐标）
    返回: {"left": 271, "top": 51, "right": 759, "bottom": 761, "width": 488, "height": 710}
    如果配置文件不存在或无效，返回 None
    """
    config = load_config()
    return config.get("game_view_coords")


def set_game_view_coords(left: int, top: int, right: int, bottom: int):
    """设置 Game 视图坐标（截图坐标）并保存到配置文件"""
    config = load_config()
    config["game_view_coords"] = {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left,
        "height": bottom - top,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }
    save_config(config)
    print(f"✅ Game 视图坐标已保存: ({left}, {top}, {right}, {bottom})")


def prompt_for_resolution() -> tuple:
    """
    提示用户输入分辨率
    返回: (width, height)
    """
    print("\n" + "="*60)
    print("📐 游戏分辨率设置")
    print("="*60)
    
    config = load_config()
    current = config.get("game_resolution", {})
    current_width = current.get("width", 1170)
    current_height = current.get("height", 2532)
    
    print(f"当前分辨率: {current_width}x{current_height}")
    print(f"输入新的分辨率或直接回车使用当前值")
    
    try:
        width_input = input(f"宽度 [{current_width}]: ").strip()
        height_input = input(f"高度 [{current_height}]: ").strip()
        
        width = int(width_input) if width_input else current_width
        height = int(height_input) if height_input else current_height
        
        set_game_resolution(width, height)
        return width, height
    except ValueError:
        print("❌ 输入无效，使用默认值")
        return current_width, current_height


def prompt_for_resolution_if_needed() -> tuple:
    """
    如果需要，提示用户输入分辨率
    如果配置文件存在且有效，直接返回
    否则提示用户输入
    """
    config = load_config()
    resolution = config.get("game_resolution", {})
    
    if resolution.get("width") and resolution.get("height"):
        width = resolution["width"]
        height = resolution["height"]
        print(f"📐 使用已保存的分辨率: {width}x{height}")
        modify = input("是否修改? (y/N): ").strip().lower()
        if modify == 'y':
            return prompt_for_resolution()
        return width, height
    else:
        return prompt_for_resolution()


if __name__ == "__main__":
    # 测试
    width, height = prompt_for_resolution_if_needed()
    print(f"最终分辨率: {width}x{height}")
