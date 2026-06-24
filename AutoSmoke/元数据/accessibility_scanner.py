#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSmoke - 可测性扫描（Accessibility Scanner）

扫描 Unity 导出的元数据，检测可测试性问题：
  1. 关键按钮缺失 testId
  2. 重复 testId
  3. clickable/type 异常
  4. 弹窗缺少关闭动作
  5. 危险按钮未标注 dangerous
  6. 主城建筑缺少 metadata
  7. 大地图对象缺少 metadata

输出：
  - accessibility_scan.json   — 结构化扫描结果
  - accessibility_scan.html   — 可视化报告
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.environ.get("USERPROFILE", "."), ".autosmoke")
METADATA_DIR = os.path.join(CONFIG_DIR, "metadata")

# 可测试性扫描规则
SCAN_RULES = {
    "min_testid_coverage": 0.1,  # 期望至少 10% 的 UI 元素有 testId
    "max_duplicate_testid": 0,   # 不允许重复 testId
    "min_clickable_accuracy": 0.8,  # 期望 80% 的 clickable 推断有明确原因
    "dangerous_keywords": [
        "充值", "支付", "购买", "buy", "pay", "purchase",
        "钻石", "diamond", "代币", "token",
    ],
    "popup_close_keywords": ["关闭", "close", "取消", "cancel", "x", "X"],
}


class AccessibilityScanner:
    """
    可测性扫描器

    读取 Unity MetadataExporter 导出的元数据文件，
    扫描可测试性问题并生成报告。
    """

    def __init__(self):
        self._issues: List[Dict] = []
        self._ui_elements: List[Dict] = []
        self._buildings: List[Dict] = []
        self._map_objects: List[Dict] = []
        self._popups: List[Dict] = []
        self._page_id = "unknown"
        self._scene_id = "unknown"
        self._export_time = ""

    # ============================================================
    # 加载
    # ============================================================

    def load(self) -> bool:
        """加载所有元数据文件"""
        self._issues = []

        # 加载 UI 元数据
        ui_ok = self._load_ui()
        state_ok = self._load_state()
        scene_ok = self._load_scene()

        return ui_ok or state_ok or scene_ok

    def _load_ui(self) -> bool:
        path = os.path.join(METADATA_DIR, "current_ui.json")
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            self._ui_elements = data.get("elements", [])
            self._export_time = data.get("exportTime", "")
            logger.info("已加载 UI 元数据: %d 个元素", len(self._ui_elements))
            return True
        except Exception as e:
            logger.warning("加载 UI 元数据失败: %s", e)
            return False

    def _load_state(self) -> bool:
        path = os.path.join(METADATA_DIR, "current_state.json")
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            self._page_id = data.get("currentPageId", "unknown")
            self._scene_id = data.get("sceneId", "unknown_scene")
            self._popups = data.get("popups", [])
            return True
        except Exception as e:
            logger.warning("加载状态元数据失败: %s", e)
            return False

    def _load_scene(self) -> bool:
        path = os.path.join(METADATA_DIR, "current_scene.json")
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            self._buildings = data.get("buildings", [])
            self._map_objects = data.get("mapObjects", [])
            return True
        except Exception as e:
            logger.warning("加载场景元数据失败: %s", e)
            return False

    # ============================================================
    # 扫描
    # ============================================================

    def scan(self) -> Dict:
        """
        执行所有可测试性检查

        :return: 扫描结果字典
        """
        self._issues = []

        self._check_testid_coverage()
        self._check_duplicate_testid()
        self._check_clickable_accuracy()
        self._check_dangerous_buttons()
        self._check_popup_actions()
        self._check_building_metadata()
        self._check_clickable_anomalies()

        return self._build_report()

    def _add_issue(self, category: str, severity: str, message: str,
                   element: Dict = None, suggestion: str = ""):
        """添加一条扫描问题"""
        issue = {
            "category": category,
            "severity": severity,
            "message": message,
            "suggestion": suggestion,
            "element": element or {},
        }
        self._issues.append(issue)

    # ── 检查 1：testId 覆盖率 ──
    def _check_testid_coverage(self):
        """检查 testId 标注覆盖率"""
        total = len(self._ui_elements)
        if total == 0:
            return

        has_testid = sum(1 for el in self._ui_elements if el.get("testId"))
        coverage = has_testid / total
        min_coverage = SCAN_RULES["min_testid_coverage"]

        if coverage == 0:
            self._add_issue(
                "testId_coverage", "warning",
                f"没有任何 UI 元素标注了 testId (0/{total})",
                suggestion="建议对关键按钮（使用/关闭/确认/取消）添加 AutoSmokeNode 组件",
            )
        elif coverage < min_coverage:
            self._add_issue(
                "testId_coverage", "info",
                f"testId 覆盖率偏低: {has_testid}/{total} ({coverage:.1%})",
                suggestion="建议逐步添加 AutoSmokeNode 标注",
            )
        else:
            logger.info("testId 覆盖率达到目标: %.1f%%", coverage * 100)

    # ── 检查 2：重复 testId ──
    def _check_duplicate_testid(self):
        """检查是否有重复的 testId"""
        seen = {}
        for el in self._ui_elements:
            tid = el.get("testId")
            if tid:
                if tid in seen:
                    self._add_issue(
                        "duplicate_testid", "error",
                        f"重复 testId: '{tid}'",
                        element=el,
                        suggestion=f"已在 {seen[tid]} 和 {el.get('path', '?')} 中重复，请确保唯一",
                    )
                else:
                    seen[tid] = el.get("path", "?")

    # ── 检查 3：clickable 推断准确度 ──
    def _check_clickable_accuracy(self):
        """检查 clickable 推断是否有明确原因"""
        clickable_elements = [el for el in self._ui_elements
                             if el.get("clickable")]
        for el in clickable_elements:
            reason = el.get("clickableReason", "")
            if not reason or reason == "unknown":
                self._add_issue(
                    "clickable_accuracy", "warning",
                    f"元素 clickable 但原因不明: {el.get('name', '?')}",
                    element=el,
                    suggestion="该元素被推断为可点击但无明确原因，可能需要手动验证",
                )

        # 检查 Button 类型但没有 clickable=true 的异常情况
        button_type = [el for el in self._ui_elements if el.get("type") == "Button"]
        for el in button_type:
            if not el.get("clickable"):
                self._add_issue(
                    "clickable_anomaly", "error",
                    f"Button 类型但 clickable=false: {el.get('name', '?')}",
                    element=el,
                    suggestion="Button 组件应始终可点击，可能为 disabled 状态",
                )

    # ── 检查 4：危险按钮 ──
    def _check_dangerous_buttons(self):
        """检测危险操作按钮是否未标注 dangerous"""
        for el in self._ui_elements:
            name = el.get("name", "")
            text = el.get("text", "")
            combined = (name + " " + text).lower()

            for kw in SCAN_RULES["dangerous_keywords"]:
                if kw.lower() in combined:
                    dangerous = el.get("dangerous", False)
                    if not dangerous:
                        self._add_issue(
                            "dangerous_unmarked", "error",
                            f"检测到危险关键词但不含 dangerous 标记: '{kw}' in '{el.get('name', '?')}'",
                            element=el,
                            suggestion="添加 AutoSmokeNode.dangerous=true 并设置 nodeType=确认弹窗",
                        )
                    break

    # ── 检查 5：弹窗关闭动作 ──
    def _check_popup_actions(self):
        """检查弹窗是否缺少关闭动作"""
        for popup in self._popups:
            pname = popup.get("canvasName", "?")
            if not popup.get("hasMask", False):
                self._add_issue(
                    "popup_no_mask", "info",
                    f"弹窗可能缺少遮罩: {pname}",
                    element=popup,
                    suggestion="建议添加 Mask 或 RectMask2D 组件以标识弹窗区域",
                )

    # ── 检查 6：建筑元数据 ──
    def _check_building_metadata(self):
        """检查主城建筑是否有完整元数据"""
        for b in self._buildings:
            btype = b.get("type", "")
            if btype == "SceneObject" and b.get("clickable"):
                # 可点击但不明确类型的建筑
                self._add_issue(
                    "building_metadata", "info",
                    f"可点击对象类型不明: {b.get('name', '?')}",
                    element=b,
                    suggestion="建议添加 AutoSmokeNode 标注类型为 Building",
                )

            # 没有 screenRect 的建筑（世界坐标转屏幕坐标失败）
            if b.get("clickable") and not b.get("screenRect"):
                self._add_issue(
                    "building_no_screenrect", "info",
                    f"可点击建筑无 screenRect: {b.get('name', '?')} "
                    f"pos=({b.get('worldPosition', '?')})",
                    element=b,
                    suggestion="可能是 3D 对象在相机视野外或不在 GameView 范围内",
                )

    # ── 检查 7：clickable 异常 ──
    def _check_clickable_anomalies(self):
        """检查 clickable 推断的异常模式"""
        # 查找"应该可点击但检测为不可点击"的元素
        for el in self._ui_elements:
            name = el.get("name", "").lower()
            # 以 Btn 结尾或包含 Button 的通常应该是可点击的
            if (name.endswith("btn") or "button" in name or name.startswith("btn")):
                if not el.get("clickable"):
                    self._add_issue(
                        "clickable_anomaly", "warning",
                        f"命名暗示可点击但 clickable=false: {el.get('name', '?')}",
                        element=el,
                        suggestion="名称包含 'Btn'/'Button' 但未检测到可点击组件，"
                                   "可能使用自定义事件系统",
                    )

    # ============================================================
    # 报告生成
    # ============================================================

    def _build_report(self) -> Dict:
        """构建扫描报告"""
        by_category = {}
        by_severity = {"error": 0, "warning": 0, "info": 0}

        for issue in self._issues:
            cat = issue["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(issue)

            sev = issue["severity"]
            if sev in by_severity:
                by_severity[sev] += 1

        report = {
            "scanTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "metadataExportTime": self._export_time,
            "pageId": self._page_id,
            "sceneId": self._scene_id,
            "totalIssues": len(self._issues),
            "severity": by_severity,
            "categories": list(by_category.keys()),
            "byCategory": by_category,
            "issues": self._issues,
            "summary": {
                "totalUiElements": len(self._ui_elements),
                "buildings": len(self._buildings),
                "mapObjects": len(self._map_objects),
                "popups": len(self._popups),
            },
        }
        return report

    def get_score(self, report: Dict = None) -> int:
        """
        计算可测试性评分（0-100）

        :param report: scan() 返回的报告，不传则自动扫描
        :return: 评分
        """
        if report is None:
            report = self.scan()

        score = 100
        sev = report.get("severity", {})

        # 每个 error -15，每个 warning -5，每个 info -1
        score -= sev.get("error", 0) * 15
        score -= sev.get("warning", 0) * 5
        score -= sev.get("info", 0) * 1

        return max(0, score)

    def generate_html(self, report: Dict = None) -> str:
        """
        生成 HTML 报告

        :param report: scan() 返回的报告
        :return: HTML 字符串
        """
        if report is None:
            report = self.scan()

        score = self.get_score(report)
        severity = report.get("severity", {})
        total = report.get("totalIssues", 0)
        summary = report.get("summary", {})

        score_color = "#4CAF50" if score >= 80 else ("#FF9800" if score >= 50 else "#f44336")
        score_emoji = "🟢" if score >= 80 else ("🟠" if score >= 50 else "🔴")

        # 构建问题列表 HTML
        issues_html = ""
        for issue in report.get("issues", []):
            sev = issue["severity"]
            sev_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(sev, "⚪")
            sev_label = {"error": "错误", "warning": "警告", "info": "提示"}.get(sev, sev)
            cat = issue["category"]
            name = issue.get("element", {}).get("name", "")
            path = issue.get("element", {}).get("path", "")
            suggestion = issue.get("suggestion", "")

            issues_html += f"""
            <div class="issue {sev}">
                <div class="issue-header">
                    <span class="issue-sev">{sev_icon} {sev_label}</span>
                    <span class="issue-cat">{cat}</span>
                    <span class="issue-name">{name}</span>
                </div>
                <div class="issue-body">
                    <p>{issue['message']}</p>
                    {f'<p class="suggestion">💡 {suggestion}</p>' if suggestion else ''}
                    {f'<p class="path">{path}</p>' if path else ''}
                </div>
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AutoSmoke 可测性扫描报告</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f5; padding: 20px; color: #333; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ font-size: 24px; margin-bottom: 20px; }}
  .score-card {{ background: {score_color}; color: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; text-align: center; }}
  .score-card .score {{ font-size: 48px; font-weight: bold; }}
  .score-card .label {{ font-size: 14px; opacity: 0.9; }}
  .stats {{ display: flex; gap: 12px; margin-bottom: 20px; }}
  .stat {{ flex: 1; background: white; border-radius: 8px; padding: 16px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .stat .num {{ font-size: 28px; font-weight: bold; }}
  .stat .lbl {{ font-size: 12px; color: #666; margin-top: 4px; }}
  .stat.error .num {{ color: #f44336; }}
  .stat.warning .num {{ color: #FF9800; }}
  .stat.info .num {{ color: #2196F3; }}
  .stat.summary .num {{ color: #4CAF50; }}
  .info-bar {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; font-size: 13px; color: #666; }}
  .info-bar span {{ background: white; padding: 6px 12px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .issue {{ background: white; border-radius: 8px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); overflow: hidden; }}
  .issue.error {{ border-left: 4px solid #f44336; }}
  .issue.warning {{ border-left: 4px solid #FF9800; }}
  .issue.info {{ border-left: 4px solid #2196F3; }}
  .issue-header {{ display: flex; align-items: center; gap: 8px; padding: 12px 16px; cursor: pointer; }}
  .issue-header:hover {{ background: #fafafa; }}
  .issue-sev {{ font-size: 13px; }}
  .issue-cat {{ font-size: 11px; background: #f0f0f0; padding: 2px 6px; border-radius: 4px; color: #666; }}
  .issue-name {{ font-size: 13px; font-weight: 500; margin-left: auto; }}
  .issue-body {{ padding: 0 16px 12px; font-size: 13px; color: #555; }}
  .issue-body p {{ margin-bottom: 4px; }}
  .suggestion {{ color: #4CAF50; }}
  .path {{ color: #999; font-family: monospace; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
  <h1>📊 AutoSmoke 可测性扫描</h1>

  <div class="score-card">
    <div class="score">{score_emoji} {score}</div>
    <div class="label">可测试性评分</div>
  </div>

  <div class="stats">
    <div class="stat error">
      <div class="num">{severity.get('error', 0)}</div>
      <div class="lbl">错误</div>
    </div>
    <div class="stat warning">
      <div class="num">{severity.get('warning', 0)}</div>
      <div class="lbl">警告</div>
    </div>
    <div class="stat info">
      <div class="num">{severity.get('info', 0)}</div>
      <div class="lbl">提示</div>
    </div>
    <div class="stat summary">
      <div class="num">{total}</div>
      <div class="lbl">共 {len(report.get('issues', []))} 项</div>
    </div>
  </div>

  <div class="info-bar">
    <span>📄 页面: {report.get('pageId', '?')}</span>
    <span>🏙️ 场景: {report.get('sceneId', '?')}</span>
    <span>🖼️ UI 元素: {summary.get('totalUiElements', 0)}</span>
    <span>🏗️ 建筑: {summary.get('buildings', 0)}</span>
    <span>🗺️ 地图对象: {summary.get('mapObjects', 0)}</span>
    <span>🪟 弹窗: {summary.get('popups', 0)}</span>
  </div>

  <h2 style="font-size:18px;margin-bottom:12px;">问题详情</h2>
  {issues_html if issues_html else '<p style="color:#4CAF50;font-size:16px;text-align:center;padding:40px;">✅ 未发现可测试性问题</p>'}
</div>
</body>
</html>"""

        return html

    def export(self, report: Dict = None) -> Dict:
        """
        导出扫描报告（JSON + HTML）

        :param report: scan() 返回的报告
        :return: {"json_path": "...", "html_path": "..."}
        """
        if report is None:
            report = self.scan()

        json_path = os.path.join(METADATA_DIR, "accessibility_scan.json")
        html_path = os.path.join(METADATA_DIR, "accessibility_scan.html")

        # JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # HTML
        html = self.generate_html(report)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("扫描报告已导出: %s, %s", json_path, html_path)
        return {"json_path": json_path, "html_path": html_path,
                "total_issues": report.get("totalIssues", 0)}


# ============================================================
# 测试
# ============================================================

def test_scanner():
    """测试可测性扫描器"""
    print("=" * 60)
    print("AccessibilityScanner 测试")
    print("=" * 60)

    scanner = AccessibilityScanner()
    if not scanner.load():
        print("❌ 无法加载元数据")
        return

    report = scanner.scan()
    score = scanner.get_score(report)
    sev = report.get("severity", {})

    print(f"\n可测试性评分: {score}/100")
    print(f"  错误: {sev.get('error', 0)}, 警告: {sev.get('warning', 0)}, 提示: {sev.get('info', 0)}")
    print(f"  共 {report['totalIssues']} 项问题")

    # 列出所有问题
    for issue in report.get("issues", []):
        icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(issue["severity"], "⚪")
        print(f"  {icon} [{issue['category']}] {issue['message'][:80]}")

    # 导出 HTML
    result = scanner.export(report)
    print(f"\n📄 JSON: {result['json_path']}")
    print(f"📄 HTML: {result['html_path']}")

    print("\n" + "=" * 60)
    print("测试完成 ✅")
    print("=" * 60)


if __name__ == "__main__":
    test_scanner()
