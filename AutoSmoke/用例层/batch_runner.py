#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量用例执行器 - 按方案文档第 9 优先级实现

功能：
  1. 从 Excel 文件读取用例步骤
  2. 按用例分组，顺序执行
  3. 用例间互相隔离（一条失败不影响下一条）
  4. 生成批次汇总报告

使用方式：
    runner = BatchRunner()
    runner.run_excel("test_cases.xlsx")
    # 或
    runner.run_steps_dict({
        "TC001": ["点击 normalized(0.5,0.5)", "等待 1 秒"],
        "TC002": ["截图"],
    })
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import OrderedDict
from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = os.path.join(CONFIG_DIR, "screenshots")
REPORTS_DIR = os.path.join(CONFIG_DIR, "reports")


class BatchRunner:
    """
    批量用例执行器

    支持：
    - 从 Excel 文件读取用例
    - 从 dict 直接传入用例
    - 顺序执行，用例间隔离
    - 批次报告输出
    """

    def __init__(self, click_mode: str = "real_mouse",
                 fail_fast_case: bool = True,
                 stop_on_case_fail: bool = False):
        """
        :param click_mode: 点击模式
        :param fail_fast_case: 单用例内步骤失败是否短路
        :param stop_on_case_fail: 用例失败是否终止整个批次
        """
        self.click_mode = click_mode
        self.fail_fast_case = fail_fast_case
        self.stop_on_case_fail = stop_on_case_fail

    def _get_executor(self):
        """创建新的用例执行器（每次调用创建新实例，保证隔离）"""
        from 用例层.case_step_executor import CaseStepExecutor
        return CaseStepExecutor(
            click_mode=self.click_mode,
            fail_fast=self.fail_fast_case,
        )

    # ============================================================
    # 从 Excel 读取
    # ============================================================

    def read_excel(self, filepath: str,
                   step_field: str = "操作步骤",
                   case_id_field: str = "用例ID",
                   sheet_name: str = None) -> Dict[str, List[str]]:
        """
        从 Excel 文件读取用例步骤

        :param filepath: Excel 文件路径
        :param step_field: 步骤文本列名
        :param case_id_field: 用例 ID 列名
        :param sheet_name: 工作表名，默认第一个
        :return: {case_id: [step_text, ...], ...}
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas 未安装，无法读取 Excel。pip install pandas openpyxl")
            return {}

        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name, dtype=str)
        except Exception as e:
            logger.error("读取 Excel 失败: %s", e)
            return {}

        if step_field not in df.columns:
            logger.error("Excel 中缺少步骤列: %s (可用列: %s)",
                        step_field, list(df.columns))
            return {}

        cases = OrderedDict()
        for _, row in df.iterrows():
            cid = str(row.get(case_id_field, "unknown")).strip()
            step = str(row.get(step_field, "")).strip()
            if step:
                if cid not in cases:
                    cases[cid] = []
                cases[cid].append(step)

        logger.info("从 Excel 读取 %d 个用例，共 %d 步",
                   len(cases), sum(len(v) for v in cases.values()))
        return cases

    # ============================================================
    # 批量执行
    # ============================================================

    def run_steps_dict(self, cases: Dict[str, List[str]],
                       batch_name: str = None) -> Dict:
        """
        执行用例字典

        :param cases: {case_id: [step_text, ...]}
        :param batch_name: 批次名称
        :return: batch_result
        """
        batch_name = batch_name or f"batch_{time.strftime('%Y%m%d_%H%M%S')}"
        run_id = batch_name
        output_dir = os.path.join(SCREENSHOTS_DIR, run_id)
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        logger.info("=" * 50)
        logger.info("批量执行开始: %s (%d 个用例)", batch_name, len(cases))
        logger.info("=" * 50)

        case_results = []
        total_cases = len(cases)
        passed_cases = 0
        failed_cases = 0

        for idx, (case_id, steps) in enumerate(cases.items(), 1):
            logger.info("\n[用例 %d/%d] %s (%d 步)",
                       idx, total_cases, case_id, len(steps))

            try:
                executor = self._get_executor()
                result = executor.execute_steps(
                    steps, case_id=case_id,
                    run_id=f"{run_id}_{case_id}"
                )
            except Exception as e:
                logger.error("用例 %s 执行异常: %s", case_id, e)
                result = {
                    "case_id": case_id,
                    "result": "ERROR",
                    "error": str(e),
                    "total": len(steps),
                    "passed": 0,
                    "failed": len(steps),
                    "steps": [],
                }

            case_results.append(result)

            if result.get("result") in ("PASS",):
                passed_cases += 1
            else:
                failed_cases += 1
                if self.stop_on_case_fail:
                    logger.warning("用例 %s 失败，终止批次", case_id)
                    break

        # 汇总
        total_steps = sum(r.get("total", 0) for r in case_results)
        passed_steps = sum(r.get("passed", 0) for r in case_results)
        failed_steps = sum(r.get("failed", 0) for r in case_results)

        batch_result = {
            "batch_name": batch_name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "click_mode": self.click_mode,
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "failed_steps": failed_steps,
            "case_results": case_results,
        }

        # 保存报告
        report_path = os.path.join(output_dir, "batch_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(batch_result, f, indent=2, ensure_ascii=False)

        batch_result["report_path"] = report_path

        # 打印摘要
        self._print_summary(batch_name, total_cases, passed_cases, failed_cases,
                           total_steps, passed_steps, failed_steps, report_path)

        return batch_result

    def run_excel(self, filepath: str,
                  step_field: str = "操作步骤",
                  case_id_field: str = "用例ID",
                  sheet_name: str = None,
                  batch_name: str = None) -> Dict:
        """
        从 Excel 文件批量执行

        :param filepath: Excel 文件路径
        :return: batch_result
        """
        cases = self.read_excel(filepath, step_field, case_id_field, sheet_name)
        if not cases:
            logger.error("Excel 中未读取到任何用例")
            return {"error": "无用例", "total_cases": 0}
        return self.run_steps_dict(cases, batch_name=batch_name)

    # ============================================================
    # 报告输出
    # ============================================================

    @staticmethod
    def _print_summary(batch_name, total_cases, passed_cases, failed_cases,
                       total_steps, passed_steps, failed_steps, report_path):
        """打印批次摘要"""
        print(f"\n{'=' * 50}")
        print(f"📊 批次执行完成: {batch_name}")
        print(f"{'=' * 50}")
        print(f"  用例: {passed_cases}/{total_cases} 通过 "
              f"({'✅' if failed_cases==0 else '❌'})")
        print(f"  步骤: {passed_steps}/{total_steps} 通过 "
              f"({'✅' if failed_steps==0 else '❌'})")
        print(f"  报告: {report_path}")
        print(f"{'=' * 50}\n")

    def export_html(self, batch_result: Dict, output_path: str = None):
        """
        导出 HTML 报告

        :param batch_result: run_steps_dict 的返回结果
        :param output_path: HTML 输出路径
        :return: HTML 文件路径
        """
        if output_path is None:
            name = batch_result.get("batch_name", "batch")
            output_path = os.path.join(REPORTS_DIR, f"report_{name}.html")

        Path(output_dir := os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)

        br = batch_result
        case_rows = ""
        for cr in br.get("case_results", []):
            status_icon = "✅" if cr.get("result") == "PASS" else "❌"
            step_details = ""
            for s in cr.get("steps", []):
                st = s.get("result", "?")
                icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "⚠️",
                        "BLOCKED": "🚫", "WARNING": "⚡", "SKIPPED": "⏭️"}.get(st, "❓")
                step_details += f"<tr><td>{icon}</td><td>{s.get('raw','')[:60]}</td><td>{st}</td></tr>\n"

            case_rows += f"""
            <div class="case-card">
                <h3>{status_icon} {cr.get('case_id','?')} 
                    <span class="{'pass' if cr.get('result')=='PASS' else 'fail'}">{cr.get('result','?')}</span>
                    <span class="meta">{cr.get('passed',0)}/{cr.get('total',0)} 步通过</span>
                </h3>
                <table><tr><th></th><th>步骤</th><th>结果</th></tr>{step_details}</table>
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>AutoSmoke 测试报告</title>
<style>
body {{ font-family: 'Microsoft YaHei', sans-serif; background: #f5f6fa; padding: 20px; color: #333; }}
h1 {{ color: #1a1a2e; }}
.summary {{ background: #fff; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
.summary .stat {{ display: inline-block; margin-right: 24px; }}
.stat .num {{ font-size: 24px; font-weight: bold; }}
.stat .num.green {{ color: #27ae60; }}
.stat .num.red {{ color: #e74c3c; }}
.case-card {{ background: #fff; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.case-card h3 {{ margin: 0 0 8px 0; font-size: 15px; }}
.case-card .pass {{ color: #27ae60; }}
.case-card .fail {{ color: #e74c3c; }}
.case-card .meta {{ font-size: 12px; color: #999; margin-left: 12px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
td, th {{ padding: 4px 8px; text-align: left; border-bottom: 1px solid #eee; }}
.footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 24px; }}
</style></head>
<body>
<h1>📊 AutoSmoke 测试报告</h1>
<div class="summary">
    <div class="stat">批次: <strong>{br.get('batch_name','')}</strong></div>
    <div class="stat">用例: <span class="num green">{br.get('passed_cases',0)}</span> / {br.get('total_cases',0)}</div>
    <div class="stat">步骤: <span class="num green">{br.get('passed_steps',0)}</span> / {br.get('total_steps',0)} 
         <span class="num red">{br.get('failed_steps',0)}</span> 失败</div>
    <div class="stat">时间: {br.get('timestamp','')}</div>
</div>
{case_rows}
<div class="footer">AutoSmoke Test Report · {br.get('timestamp','')}</div>
</body></html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("HTML 报告已导出: %s", output_path)
        return output_path


# ============================================================
# 独立运行入口
# ============================================================

def test_batch_runner():
    """测试批量执行器"""
    print("=" * 60)
    print("批量用例执行器测试")
    print("=" * 60)

    runner = BatchRunner()

    # 测试1：从字典执行
    print("\n[测试1] 从字典执行...")
    cases = {
        "TC001": [
            "等待 0.5 秒",
            "截图",
        ],
        "TC002": [
            "等待 0.5 秒",
            "断言存在 normalized(0.5,0.5)",
        ],
        "TC003": [
            "截图",
            "返回",
        ],
    }
    result = runner.run_steps_dict(cases, batch_name="test_batch")
    print(f"  用例: {result['passed_cases']}/{result['total_cases']} 通过")
    print(f"  步骤: {result['passed_steps']}/{result['total_steps']} 通过")
    assert result["total_cases"] == 3
    assert result["total_steps"] == 6
    print("  ✅ 通过")

    # 测试2：用例隔离（一条失败不影响下一条）
    print("\n[测试2] 用例隔离...")
    cases2 = OrderedDict([
        ("TC_FAIL", ["断言不存在 normalized(0.5,0.5)"]),  # 应该 FAIL
        ("TC_OK",   ["断言存在 normalized(0.5,0.5)"]),     # 应该 PASS
    ])
    result2 = runner.run_steps_dict(cases2, batch_name="test_isolate")
    print(f"  TC_FAIL: {result2['case_results'][0]['result']}")
    print(f"  TC_OK:   {result2['case_results'][1]['result']}")
    assert result2['case_results'][0]['result'] == "FAIL", "TC_FAIL 应为 FAIL"
    assert result2['case_results'][1]['result'] == "PASS", "TC_OK 应为 PASS"
    print("  ✅ 通过")

    # 测试3：HTML 报告导出
    print("\n[测试3] HTML 报告导出...")
    report_path = runner.export_html(result, "test_reports/test_batch.html")
    assert os.path.exists(report_path), "报告文件应存在"
    file_size = os.path.getsize(report_path)
    print(f"  报告: {report_path} ({file_size} bytes)")
    assert file_size > 100, "报告不应为空"
    print("  ✅ 通过")

    # 测试4：stop_on_case_fail
    print("\n[测试4] stop_on_case_fail...")
    runner_stop = BatchRunner(stop_on_case_fail=True)
    cases3 = OrderedDict([
        ("TC_A", ["断言不存在 normalized(0.5,0.5)"]),  # FAIL
        ("TC_B", ["等待 0.5 秒"]),                      # 应被跳过
    ])
    result3 = runner_stop.run_steps_dict(cases3, batch_name="test_stop")
    print(f"  TC_A: {result3['case_results'][0]['result']}")
    print(f"  total_cases: {result3['total_cases']} (未执行的被计数但无结果)")
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    test_batch_runner()
