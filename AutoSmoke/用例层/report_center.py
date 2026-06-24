#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告中心 - 按方案文档第 10 优先级实现

功能：
  1. 从 batch_result.json 生成 HTML 报告
  2. 包含截图对比（before/after/diff）
  3. 包含步骤详情表格
  4. 支持单用例报告和批次汇总报告
  5. 报告可直接在浏览器中查看

使用方式：
    reporter = ReportCenter()
    reporter.from_batch("screenshots/run_xxx/batch_report.json")
"""

import os
import json
import time
import logging
import base64
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
from io import BytesIO
from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = os.path.join(CONFIG_DIR, "screenshots")
REPORTS_DIR = os.path.join(CONFIG_DIR, "reports")


class ReportCenter:
    """测试报告中心"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or REPORTS_DIR
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 图片嵌入（base64，避免路径依赖）
    # ============================================================

    @staticmethod
    def _img_to_base64(img_path: str, max_w: int = 400) -> str:
        """将图片转为 base64 data URI（缩小到 max_w 宽度）"""
        if not img_path or not os.path.exists(img_path):
            return ""
        try:
            img = Image.open(img_path)
            if img.width > max_w:
                ratio = max_w / img.width
                img = img.resize((max_w, int(img.height * ratio)),
                                 Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/png;base64,{b64}"
        except Exception:
            return ""

    def _find_screenshot(self, run_dir: str, keyword: str) -> str:
        """在 run 目录中找包含关键词的截图"""
        if not os.path.exists(run_dir):
            return ""
        for f in sorted(os.listdir(run_dir), reverse=True):
            if keyword in f and f.endswith(".png"):
                return os.path.join(run_dir, f)
        return ""

    # ============================================================
    # 单用例报告
    # ============================================================

    def build_case_html(self, case_result: Dict, run_dir: str) -> str:
        """生成单用例 HTML 片段"""
        status = case_result.get("result", "?")
        icon = "✅" if status == "PASS" else "❌"
        case_id = case_result.get("case_id", "?")
        steps = case_result.get("steps", [])

        rows = ""
        for s in steps:
            sr = s.get("result", "?")
            si = {"PASS": "✅", "FAIL": "❌", "ERROR": "⚠️",
                  "BLOCKED": "🚫", "WARNING": "⚡", "SKIPPED": "⏭️"}.get(sr, "❓")
            raw = s.get("raw", s.get("action", ""))
            err = s.get("error", "")
            dr = s.get("diff_ratio")
            diff_str = f" 差异={dr*100:.2f}%" if dr else ""
            hit = s.get("hit_object", "")

            # 查找该步骤的 before/after 截图
            bc = self._find_screenshot(run_dir, "before_")
            ac = self._find_screenshot(run_dir, "after_")
            b64_before = self._img_to_base64(bc, 300)
            b64_after = self._img_to_base64(ac, 300)

            imgs = ""
            if b64_before and b64_after:
                imgs = f"""
                <div class="step-imgs">
                    <div><img src="{b64_before}"><div class="img-label">点击前</div></div>
                    <div><img src="{b64_after}"><div class="img-label">点击后</div></div>
                </div>"""

            rows += f"""
            <tr>
                <td>{si}</td>
                <td>{sr}</td>
                <td>{raw[:80]}</td>
                <td>{err}</td>
                <td>{diff_str}{hit}</td>
            </tr>
            {imgs}"""

        steps_summary = f"{case_result.get('passed', 0)}/{case_result.get('total', 0)}"

        return f"""
        <div class="case-card">
            <h3>{icon} {case_id} 
                <span class="tag {'tag-pass' if status=='PASS' else 'tag-fail'}">{status}</span>
                <span class="meta">{steps_summary} 步通过</span>
            </h3>
            <table>
                <tr><th></th><th>结果</th><th>步骤</th><th>错误</th><th>详情</th></tr>
                {rows}
            </table>
        </div>
        """

    # ============================================================
    # 批次报告（从 batch_result）
    # ============================================================

    def build_batch_html(self, batch_result: Dict) -> str:
        """生成完整批次 HTML 报告"""
        br = batch_result

        tc = br.get("total_cases", 0)
        pc = br.get("passed_cases", 0)
        fc = br.get("failed_cases", 0)
        ts = br.get("total_steps", 0)
        ps = br.get("passed_steps", 0)
        fs = br.get("failed_steps", 0)
        pct = round(ps / ts * 100, 1) if ts > 0 else 0

        # 用例详情
        case_html = ""
        run_dir = os.path.join(SCREENSHOTS_DIR, br.get("batch_name", ""))
        for cr in br.get("case_results", []):
            case_html += self.build_case_html(cr, run_dir)

        # 整体状态
        overall = "✅ 全部通过" if fc == 0 and fs == 0 else "❌ 存在失败"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<title>AutoSmoke 测试报告</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #f0f2f5; color: #333; padding: 20px; }}
h1 {{ color: #1a1a2e; margin-bottom: 16px; font-size: 22px; }}
h2 {{ font-size: 16px; color: #2c3e50; margin: 16px 0 8px; }}

.summary {{ background: #fff; border-radius: 10px; padding: 20px; margin-bottom: 16px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 12px; }}
.stat-card {{ text-align: center; padding: 12px; border-radius: 8px; background: #f8f9fa; }}
.stat-card .num {{ font-size: 28px; font-weight: bold; }}
.stat-card .label {{ font-size: 12px; color: #888; margin-top: 4px; }}
.num.green {{ color: #27ae60; }}
.num.red {{ color: #e74c3c; }}
.num.blue {{ color: #3498db; }}

.overall {{ font-size: 18px; text-align: center; padding: 12px; border-radius: 8px; margin-bottom: 16px; }}
.overall.pass {{ background: #eafaf1; color: #27ae60; }}
.overall.fail {{ background: #fdedec; color: #e74c3c; }}

.case-card {{ background: #fff; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; 
             box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.case-card h3 {{ margin: 0 0 8px 0; font-size: 15px; }}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 6px; }}
.tag-pass {{ background: #eafaf1; color: #27ae60; }}
.tag-fail {{ background: #fdedec; color: #e74c3c; }}
.meta {{ font-size: 12px; color: #999; margin-left: 8px; }}

table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 6px; }}
th {{ background: #f8f9fa; padding: 6px 8px; text-align: left; border-bottom: 2px solid #eee; font-weight: 600; }}
td {{ padding: 6px 8px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
tr:hover {{ background: #fafafa; }}

.step-imgs {{ display: flex; gap: 8px; padding: 8px; }}
.step-imgs img {{ max-width: 300px; border: 1px solid #ddd; border-radius: 4px; }}
.img-label {{ text-align: center; font-size: 11px; color: #888; margin-top: 2px; }}
.footer {{ text-align: center; color: #aaa; font-size: 12px; margin-top: 30px; padding: 12px; }}
</style></head>
<body>
<h1>📊 AutoSmoke 测试报告</h1>
<div class="overall { 'pass' if fc==0 else 'fail' }">{overall}</div>

<div class="summary">
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;">
        <span><strong>批次:</strong> {br.get('batch_name','')}</span>
        <span><strong>模式:</strong> {br.get('click_mode','real_mouse')}</span>
        <span><strong>时间:</strong> {br.get('timestamp','')}</span>
    </div>
    <div class="summary-grid">
        <div class="stat-card"><div class="num blue">{tc}</div><div class="label">用例总数</div></div>
        <div class="stat-card"><div class="num green">{pc}</div><div class="label">用例通过</div></div>
        <div class="stat-card"><div class="num red">{fc}</div><div class="label">用例失败</div></div>
        <div class="stat-card"><div class="num blue">{ts}</div><div class="label">步骤总数</div></div>
        <div class="stat-card"><div class="num green">{ps}</div><div class="label">步骤通过</div></div>
        <div class="stat-card"><div class="num red">{fs}</div><div class="label">步骤失败</div></div>
        <div class="stat-card"><div class="num green">{pct}%</div><div class="label">通过率</div></div>
    </div>
</div>

<h2>📋 用例详情</h2>
{case_html}

<div class="footer">
    AutoSmoke Test Report · Generated {time.strftime('%Y-%m-%d %H:%M:%S')}
</div>
</body></html>"""
        return html

    # ============================================================
    # 入口
    # ============================================================

    def from_batch(self, batch_report_path: str, output_path: str = None) -> str:
        """
        从 batch_report.json 生成 HTML 报告

        :param batch_report_path: batch_report.json 路径
        :param output_path: HTML 输出路径，默认 reports/ 目录
        :return: HTML 文件路径
        """
        with open(batch_report_path, "r", encoding="utf-8") as f:
            batch_result = json.load(f)

        name = batch_result.get("batch_name", "batch")
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"report_{name}.html")

        html = self.build_batch_html(batch_result)
        Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("报告已生成: %s", output_path)
        return output_path

    def from_batch_result(self, batch_result: Dict, output_path: str = None) -> str:
        """直接从 batch_result 字典生成报告"""
        name = batch_result.get("batch_name", "batch")
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"report_{name}.html")

        html = self.build_batch_html(batch_result)
        Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path


# ============================================================
# 测试
# ============================================================

def test_report_center():
    """测试报告中心"""
    print("=" * 60)
    print("报告中心测试")
    print("=" * 60)

    reporter = ReportCenter()

    # 构建模拟数据
    mock_batch = {
        "batch_name": "test_report_batch",
        "timestamp": "2026-06-12T18:30:00",
        "click_mode": "real_mouse",
        "total_cases": 2,
        "passed_cases": 1,
        "failed_cases": 1,
        "total_steps": 4,
        "passed_steps": 3,
        "failed_steps": 1,
        "case_results": [
            {
                "case_id": "TC001",
                "result": "PASS",
                "total": 2, "passed": 2, "failed": 0,
                "steps": [
                    {"result": "PASS", "raw": "等待 0.5 秒", "action": "wait"},
                    {"result": "PASS", "raw": "截图", "action": "screenshot"},
                ]
            },
            {
                "case_id": "TC002",
                "result": "FAIL",
                "total": 2, "passed": 1, "failed": 1,
                "steps": [
                    {"result": "FAIL", "raw": "断言不存在 normalized(0.5,0.5)",
                     "action": "assert_not_exists", "error": "目标仍存在"},
                    {"result": "SKIPPED", "raw": "截图", "action": "screenshot"},
                ]
            }
        ]
    }

    # 测试1：HTML 生成
    print("\n[测试1] HTML 报告生成...")
    html = reporter.build_batch_html(mock_batch)
    assert "AutoSmoke" in html
    assert "TC001" in html
    assert "TC002" in html
    assert "通过率" in html
    print(f"  HTML 长度: {len(html)} 字符")
    print("  ✅ 通过")

    # 测试2：文件导出
    print("\n[测试2] 报告文件导出...")
    path = reporter.from_batch_result(mock_batch, "test_reports/test_report.html")
    assert os.path.exists(path)
    size = os.path.getsize(path)
    print(f"  路径: {path}")
    print(f"  大小: {size} bytes")
    assert size > 500
    print("  ✅ 通过")

    # 测试3：从真实 batch_report.json 生成
    print("\n[测试3] 从 batch_report.json 生成...")
    real_report = os.path.join(SCREENSHOTS_DIR, "test_stop", "batch_report.json")
    if os.path.exists(real_report):
        path2 = reporter.from_batch(real_report, "test_reports/report_real.html")
        size2 = os.path.getsize(path2)
        print(f"  路径: {path2} ({size2} bytes)")
        print("  ✅ 通过")
    else:
        print("  ⚠ 未找到真实报告文件，跳过")

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    test_report_center()
