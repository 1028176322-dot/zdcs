#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSmoke Unity 辅助脚本部署管理器

职责：
  1. 将 tools/*.cs 同步到 Unity 项目的 Assets/Editor/ 目录
  2. 检测脚本是否存在、是否需要更新
  3. 支持自动部署（每次 IDE 启动时检查）
  4. 提供状态查询和部署 API

使用方式：
    python deploy_tools.py                      # 部署到配置中的 Unity 项目
    python deploy_tools.py --path /path/to/other_project  # 指定路径
    python deploy_tools.py --check               # 仅检查状态
"""

import os
import sys
import json
import shutil
import logging
import filecmp
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR

logger = logging.getLogger(__name__)

TOOLS_DIR = os.path.join(CONFIG_DIR, "tools")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# 需要部署的脚本列表
SCRIPT_MANIFEST = [
    {
        "name": "GameViewLocator.cs",
        "source": "tools/GameViewLocator.cs",
        "target": "Assets/Editor/GameViewLocator.cs",
        "description": "Game 视图坐标定位（C# 反射读取 viewInWindow）",
    },
    {
        "name": "AutoSmokeClickInjector.cs",
        "source": "tools/AutoSmokeClickInjector.cs",
        "target": "Assets/Editor/AutoSmokeClickInjector.cs",
        "description": "EventSystem 点击注入（unity_inject 模式）",
    },
    {
        "name": "AutoSmokeLayoutDiagnostics.cs",
        "source": "tools/AutoSmokeLayoutDiagnostics.cs",
        "target": "Assets/Editor/AutoSmokeLayoutDiagnostics.cs",
        "description": "Unity 布局诊断辅助",
    },
    {
        "name": "AutoSmokeMetadataExporter.cs",
        "source": "tools/AutoSmokeMetadataExporter.cs",
        "target": "Assets/Editor/AutoSmokeMetadataExporter.cs",
        "description": "可测试性元数据导出（扫描UI/推断clickable/type/screenRect）",
    },
    {
        "name": "AutoSmokeGameViewBridge.cs",
        "source": "tools/AutoSmokeGameViewBridge.cs",
        "target": "Assets/Editor/AutoSmokeGameViewBridge.cs",
        "description": "Unity GameView 直连定位（导出完整游戏界面区域）",
    },
    {
        "name": "AutoSmokeGameContentCapture.cs",
        "source": "tools/AutoSmokeGameContentCapture.cs",
        "target": "Assets/Editor/AutoSmokeGameContentCapture.cs",
        "description": "Unity 直出完整 GameContent PNG（P0 截图主方案）",
    },
    {
        "name": "AutoSmokeUIPrefabScanner.cs",
        "source": "tools/AutoSmokeUIPrefabScanner.cs",
        "target": "Assets/Editor/AutoSmokeUIPrefabScanner.cs",
        "description": "工程态 UI Prefab 扫描（UI树方案 阶段一）",
    },
    {
        "name": "AutoSmokeUITreeExporter.cs",
        "source": "tools/AutoSmokeUITreeExporter.cs",
        "target": "Assets/Editor/AutoSmokeUITreeExporter.cs",
        "description": "运行态 UI 树导出（UI树方案 阶段二）",
    },
    {
        "name": "AutoSmokeRuntimeBridge.cs",
        "source": "tools/AutoSmokeRuntimeBridge.cs",
        "target": "Assets/Editor/AutoSmokeRuntimeBridge.cs",
        "description": "运行态 Bridge：心跳+请求监听+响应（阶段2）",
    },
    {
        "name": "AutoSmokeRuntimeUITreeDumper.cs",
        "source": "tools/AutoSmokeRuntimeUITreeDumper.cs",
        "target": "Assets/Editor/AutoSmokeRuntimeUITreeDumper.cs",
        "description": "运行态 UI 树导出器（Canvas/UI 遍历，阶段2）",
    },
    {
        "name": "AutoSmokeSceneInteractionExporter.cs",
        "source": "tools/AutoSmokeSceneInteractionExporter.cs",
        "target": "Assets/Editor/AutoSmokeSceneInteractionExporter.cs",
        "description": "场景交互对象导出（建筑/地图/资源点等，补充方案6）",
    },
]


class DeployManager:
    """脚本部署管理器"""

    def __init__(self, unity_project_path: str = None):
        self.unity_project_path = unity_project_path or self._detect_project_path()

    @staticmethod
    def _detect_project_path() -> Optional[str]:
        """从 config.json 检测 Unity 项目路径"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                path = config.get("unity_project_path", "")
                if path and os.path.exists(os.path.join(path, "Assets")):
                    return path
            except Exception:
                pass
        return None

    # ============================================================
    # 状态检查
    # ============================================================

    def check_status(self) -> Dict:
        """
        检查所有脚本的部署状态

        :return: {"project_path": "...", "scripts": [...], "all_ok": bool}
        """
        scripts_status = []
        all_ok = True

        for script in SCRIPT_MANIFEST:
            src_path = os.path.join(CONFIG_DIR, script["source"])
            dst_path = os.path.join(self.unity_project_path, script["target"]) if self.unity_project_path else None

            status = {
                "name": script["name"],
                "description": script["description"],
                "source_exists": os.path.exists(src_path),
                "target_exists": False,
                "up_to_date": False,
                "source_size": os.path.getsize(src_path) if os.path.exists(src_path) else 0,
                "target_size": 0,
            }

            if dst_path and os.path.exists(dst_path):
                status["target_exists"] = True
                status["target_size"] = os.path.getsize(dst_path)
                if os.path.exists(src_path):
                    status["up_to_date"] = filecmp.cmp(src_path, dst_path, shallow=False)

            if not status["target_exists"] or not status["up_to_date"]:
                all_ok = False

            scripts_status.append(status)

        return {
            "project_path": self.unity_project_path or "未检测到 Unity 项目路径",
            "project_valid": self.unity_project_path is not None,
            "scripts": scripts_status,
            "all_ok": all_ok,
            "scripts_count": len(scripts_status),
            "deployed_count": sum(1 for s in scripts_status if s["target_exists"]),
            "uptodate_count": sum(1 for s in scripts_status if s["up_to_date"]),
        }

    # ============================================================
    # 部署
    # ============================================================

    def deploy(self, force: bool = False) -> Dict:
        """
        部署脚本到 Unity 项目

        :param force: 是否强制覆盖（即使文件相同）
        :return: {"success": True/False, "results": [...], "message": "..."}
        """
        if not self.unity_project_path:
            return {"success": False, "message": "未检测到 Unity 项目路径",
                    "results": []}

        editor_dir = os.path.join(self.unity_project_path, "Assets", "Editor")
        Path(editor_dir).mkdir(parents=True, exist_ok=True)

        results = []
        all_ok = True

        for script in SCRIPT_MANIFEST:
            src_path = os.path.join(CONFIG_DIR, script["source"])
            dst_path = os.path.join(self.unity_project_path, script["target"])

            result = {
                "name": script["name"],
                "source": src_path,
                "target": dst_path,
                "action": "skipped",
            }

            if not os.path.exists(src_path):
                result["action"] = "error"
                result["error"] = f"源文件不存在: {src_path}"
                all_ok = False
                results.append(result)
                continue

            # 检查是否需要复制
            if not force and os.path.exists(dst_path):
                try:
                    if filecmp.cmp(src_path, dst_path, shallow=False):
                        result["action"] = "uptodate"
                        results.append(result)
                        continue
                except Exception:
                    pass

            try:
                shutil.copy2(src_path, dst_path)
                result["action"] = "copied"
                logger.info("已部署: %s → %s", script["name"], dst_path)
            except Exception as e:
                result["action"] = "error"
                result["error"] = str(e)
                all_ok = False

            results.append(result)

        return {
            "success": all_ok,
            "project_path": self.unity_project_path,
            "results": results,
            "message": "全部部署完成" if all_ok else "部分部署失败",
            "copied": sum(1 for r in results if r["action"] == "copied"),
            "uptodate": sum(1 for r in results if r["action"] == "uptodate"),
            "errors": sum(1 for r in results if r["action"] == "error"),
        }

    def deploy_single(self, script_name: str, force: bool = False) -> Dict:
        """部署单个脚本"""
        for script in SCRIPT_MANIFEST:
            if script["name"] == script_name:
                old_manifest = SCRIPT_MANIFEST[:]
                SCRIPT_MANIFEST.clear()
                SCRIPT_MANIFEST.append(script)
                result = self.deploy(force)
                SCRIPT_MANIFEST.clear()
                SCRIPT_MANIFEST.extend(old_manifest)
                return result
        return {"success": False, "message": f"未找到脚本: {script_name}"}


# ============================================================
# CLI 入口
# ============================================================

def test_deploy():
    """测试部署管理器"""
    print("=" * 60)
    print("部署管理器测试")
    print("=" * 60)

    dm = DeployManager()
    print(f"\nUnity 项目路径: {dm.unity_project_path}")

    # 测试1：检查状态
    print("\n[测试1] 检查部署状态...")
    status = dm.check_status()
    print(f"  项目有效: {status['project_valid']}")
    print(f"  全部就绪: {status['all_ok']}")
    for s in status["scripts"]:
        icon = "✅" if s["up_to_date"] else ("⚠️" if s["target_exists"] else "❌")
        print(f"  {icon} {s['name']:35s} src={s['source_exists']} dst={s['target_exists']}")
    print("  ✅ 通过")

    # 测试2：部署
    print("\n[测试2] 部署脚本...")
    if status["project_valid"]:
        result = dm.deploy(force=False)
        print(f"  成功: {result['success']}")
        print(f"  复制: {result['copied']}, 已最新: {result['uptodate']}, 错误: {result['errors']}")
        assert result["success"] or result["uptodate"] > 0
        print("  ✅ 通过")
    else:
        print("  ⚠ 无 Unity 项目路径，跳过部署测试")

    # 测试3：重新部署后检查
    print("\n[测试3] 重新检查...")
    status2 = dm.check_status()
    print(f"  全部就绪: {status2['all_ok']}")
    if status["project_valid"]:
        assert status2["all_ok"], "部署后全部脚本应就绪"
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AutoSmoke 脚本部署工具")
    parser.add_argument("--check", action="store_true", help="仅检查状态")
    parser.add_argument("--force", action="store_true", help="强制覆盖")
    parser.add_argument("--path", type=str, help="指定 Unity 项目路径")
    parser.add_argument("--script", type=str, help="部署单个脚本名")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    if args.check:
        dm = DeployManager(args.path)
        status = dm.check_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        dm = DeployManager(args.path)
        if args.script:
            result = dm.deploy_single(args.script, args.force)
        else:
            result = dm.deploy(args.force)
        print(json.dumps(result, indent=2, ensure_ascii=False))
