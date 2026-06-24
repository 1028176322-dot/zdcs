#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 树合并增强器（UI树方案 阶段三）

读取工程态 + 运行态数据，合并输出 enhanced_ui_tree.json

输入：
  - 元数据/project_ui_inventory.json（工程态 Prefab 清单）
  - 元数据/current_ui_tree.json（运行态 UI 树）
  - 元数据/current_scene.json（场景对象）

输出：
  - 元数据/enhanced_ui_tree.json（合并增强结果）

合并规则：
  - P0: 节点路径匹配（runtimePath suffix matching prefabNodePath）
  - P1: 节点名 + 组件组合匹配
  - P2: 文本 + 位置匹配
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 输出目录
AUTOSMOKE_ROOT = Path(__file__).resolve().parent.parent
META_DIR = AUTOSMOKE_ROOT / "元数据"


def load_json(filename: str) -> Optional[Dict]:
    """从元数据目录加载 JSON 文件"""
    path = META_DIR / filename
    if not path.exists():
        logger.warning("文件不存在: %s", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("读取失败 %s: %s", path, e)
        return None


def build_prefab_index(inventory: Dict) -> Dict:
    """
    构建 Prefab 节点索引：prefabPath -> List[节点信息]

    用于快速查找某个节点可能来自哪个 Prefab
    """
    index = {}
    for prefab in inventory.get("prefabs", []):
        prefab_path = prefab.get("assetPath", "")
        for node in prefab.get("nodes", []):
            node_path = node.get("path", "")
            # 用末段路径作为 key（如 "ButtonUse"）
            key = node_path.split("/")[-1] if "/" in node_path else node_path
            if key not in index:
                index[key] = []
            index[key].append({
                "prefabPath": prefab_path,
                "prefabNodePath": node_path,
                "name": node.get("name", ""),
                "text": node.get("text", ""),
                "components": node.get("componentTypes", []),
                "clickable": node.get("clickable", False),
            })
    return index


def merge(prefab_index: Dict, runtime_tree: Dict) -> Dict:
    """合并工程态和运行态数据"""
    nodes = runtime_tree.get("nodes", [])
    enhanced_nodes = []

    for node in nodes:
        node_name = node.get("name", "")
        node_text = node.get("text", "")
        node_path = node.get("path", "")

        # 查找匹配的 Prefab 节点
        matched_prefabs = prefab_index.get(node_name, [])

        # 按匹配度排序
        scored = []
        for pn in matched_prefabs:
            score = 0
            if pn.get("text") and pn["text"] == node_text:
                score += 3
            if pn.get("name") == node_name:
                score += 1
            # 检查组件相似度
            runtime_comps = set(node.get("components", []))
            prefab_comps = set(pn.get("components", []))
            common = runtime_comps & prefab_comps
            if common:
                score += len(common) * 0.5
            scored.append((score, pn))

        scored.sort(key=lambda x: -x[0])

        # 构建增强节点
        enhanced = dict(node)  # 复制运行态字段
        enhanced["prefabSource"] = ""
        enhanced["prefabNodePath"] = ""
        enhanced["prefabPath"] = ""
        enhanced["mergeConfidence"] = 0.0

        if scored:
            best = scored[0]
            if best[0] >= 2:
                enhanced["prefabSource"] = best[1]["prefabPath"]
                enhanced["prefabNodePath"] = best[1]["prefabNodePath"]
                enhanced["prefabPath"] = best[1]["prefabPath"]
                enhanced["mergeConfidence"] = round(best[0] / 10.0, 2)
                enhanced["mergeMethod"] = "name_text_component"

        enhanced_nodes.append(enhanced)

    result = dict(runtime_tree)
    result["nodes"] = enhanced_nodes
    result["mergeInfo"] = {
        "totalRuntimeNodes": len(nodes),
        "matchedPrefabNodes": sum(1 for n in enhanced_nodes if n.get("mergeConfidence", 0) > 0),
        "mergeVersion": "1.0",
    }
    return result


def run():
    """执行合并增强"""
    logger.info("开始 UI 树合并增强...")

    # 1. 加载工程态数据
    inventory = load_json("project_ui_inventory.json")
    if inventory is None:
        logger.error("无法加载工程态数据，终止合并")
        return False

    prefab_index = build_prefab_index(inventory)
    logger.info("工程态索引: %d 个节点类型", len(prefab_index))

    # 2. 加载运行态数据
    runtime_tree = load_json("current_ui_tree.json")
    if runtime_tree is None:
        logger.error("无法加载运行态数据，终止合并")
        return False

    logger.info("运行态节点: %d 个", len(runtime_tree.get("nodes", [])))

    # 3. 合并
    enhanced = merge(prefab_index, runtime_tree)
    logger.info("合并完成: 匹配 %d/%d 个节点",
                enhanced["mergeInfo"]["matchedPrefabNodes"],
                enhanced["mergeInfo"]["totalRuntimeNodes"])

    # 4. 输出
    output_path = META_DIR / "enhanced_ui_tree.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enhanced, f, indent=2, ensure_ascii=False)

    logger.info("增强 UI 树已保存: %s (%d bytes)", output_path, os.path.getsize(output_path))
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    run()
