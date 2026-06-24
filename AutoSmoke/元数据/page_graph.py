#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
页面关系图（UI树方案 阶段六/十五）

记录页面间导航关系：
  fromPage → action → element → toPage

输出：
  - page_graph.json（关系图数据）
  - page_graph.html（可视化页面）

用法：
    graph = PageGraph()
    graph.record(from_page="MainCity", action="click", 
                 element="MainCity.BagButton", to_page="BagPanel")
    graph.save()
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

AUTOSMOKE_ROOT = Path(__file__).resolve().parent.parent
META_DIR = AUTOSMOKE_ROOT / "元数据"


class PageGraph:
    """页面关系图"""

    def __init__(self):
        self._edges: List[Dict] = []
        self._pages: Dict[str, Dict] = {}  # pageId -> info
        self._loaded = False

    def load(self, path: str = None) -> bool:
        """从文件加载已有关系图"""
        path = path or os.path.join(META_DIR, "page_graph.json")
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._edges = data.get("edges", [])
            self._pages = {p["id"]: p for p in data.get("pages", [])}
            self._loaded = True
            logger.info("页面关系图已加载: %d 页, %d 条边",
                        len(self._pages), len(self._edges))
            return True
        except Exception as e:
            logger.warning("加载页面关系图失败: %s", e)
            return False

    def record(self, from_page: str, action: str, element: str,
               to_page: str, timestamp: str = None):
        """记录一条页面导航关系"""
        edge = {
            "fromPage": from_page,
            "action": action,
            "element": element,
            "toPage": to_page,
            "timestamp": timestamp or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._edges.append(edge)

        # 确保页面存在
        for pid in [from_page, to_page]:
            if pid and pid not in self._pages:
                self._pages[pid] = {
                    "id": pid,
                    "name": pid,
                    "visitCount": 0,
                    "firstSeen": edge["timestamp"],
                    "lastSeen": edge["timestamp"],
                }
            if pid and pid in self._pages:
                self._pages[pid]["visitCount"] = \
                    self._pages[pid].get("visitCount", 0) + 1
                self._pages[pid]["lastSeen"] = edge["timestamp"]

        logger.info("关系记录: %s --[%s/%s]--> %s",
                    from_page, action, element, to_page)

    def get_page_list(self) -> List[str]:
        """获取所有页面 ID"""
        return list(self._pages.keys())

    def get_edges_from(self, page_id: str) -> List[Dict]:
        """获取从某页面出发的所有边"""
        return [e for e in self._edges if e["fromPage"] == page_id]

    def get_edges_to(self, page_id: str) -> List[Dict]:
        """获取到达某页面的所有边"""
        return [e for e in self._edges if e["toPage"] == page_id]

    def stats(self) -> Dict:
        """获取统计"""
        return {
            "pages": len(self._pages),
            "edges": len(self._edges),
            "pageList": list(self._pages.keys()),
        }

    def save(self, path: str = None) -> str:
        """保存到文件"""
        path = path or os.path.join(META_DIR, "page_graph.json")
        data = {
            "version": 1,
            "updatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "pages": list(self._pages.values()),
            "edges": self._edges,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("页面关系图已保存: %s (%d pages, %d edges)",
                    path, len(self._pages), len(self._edges))
        return path

    def save_html(self, path: str = None) -> str:
        """生成 HTML 可视化"""
        path = path or os.path.join(META_DIR, "page_graph.html")

        nodes_json = json.dumps([
            {"id": p["id"], "label": p["name"],
             "value": p.get("visitCount", 1)}
            for p in self._pages.values()
        ], ensure_ascii=False)

        edges_json = json.dumps([
            {"from": e["fromPage"], "to": e["toPage"],
             "label": e["element"], "title": "%s → %s" % (e["action"], e["element"])}
            for e in self._edges
        ], ensure_ascii=False)

        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<title>AutoSmoke 页面关系图</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: 'Microsoft YaHei', sans-serif; background:#1a1a2e; color:#fff; }
#header { padding:16px 20px; background:#16213e; }
#header h1 { font-size:18px; }
#header .stats { font-size:13px; color:#888; margin-top:4px; }
#mynetwork { width:100%; height:calc(100vh - 60px); }
</style>
</head>
<body>
<div id="header">
<h1>🔗 AutoSmoke 页面关系图</h1>
<div class="stats" id="stats">加载中...</div>
</div>
<div id="mynetwork"></div>
<script src="https://unpkg.com/vis-network@9.1.6/dist/vis-network.min.js"></script>
<script>
var nodes = new vis.DataSet(""" + nodes_json + """);  
var edges = new vis.DataSet(""" + edges_json + """);  
var container = document.getElementById('mynetwork');
var data = { nodes: nodes, edges: edges };
var options = {
    nodes: { shape: 'dot', size: 20, font: { color: '#fff', size: 14 } },
    edges: { arrows: 'to', font: { size: 11, color: '#aaa' } },
    physics: { solver: 'forceAtlas2Based' },
    interaction: { hover: true, tooltipDelay: 200 }
};
var network = new vis.Network(container, data, options);
document.getElementById('stats').textContent = 
    '页面: ' + nodes.length + ' | 导航: ' + edges.length + ' 条';
</script>
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("页面关系图 HTML 已保存: %s", path)
        return path


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    g = PageGraph()
    g.load()

    # 模拟几条导航记录
    g.record("MainCity", "click", "MainCity.BagButton", "BagPanel")
    g.record("BagPanel", "click", "Bag.UseButton", "RewardPopup")
    g.record("RewardPopup", "click", "RewardPopup.CloseButton", "BagPanel")
    g.record("BagPanel", "click", "Bag.CloseButton", "MainCity")
    g.record("MainCity", "click", "MainCity.ActivityButton", "ActivityPanel")

    stats = g.stats()
    print("统计: %s" % stats)
    g.save()
    html = g.save_html()
    print("HTML: %s" % html)
    print("✅ 页面关系图测试通过")
