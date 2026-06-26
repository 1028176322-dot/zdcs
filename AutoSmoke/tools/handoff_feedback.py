#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate QA_Reader-readable feedback from AutoSmoke handoff outputs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "metadata"
REPORT_ROOT = METADATA / "handoff" / "reports"
IMPORT_ROOT = METADATA / "handoff" / "imports"
BUSINESS_RESULT_ROOT = METADATA / "handoff" / "business_results"
FEEDBACK_ROOT = METADATA / "handoff" / "feedback"
RUN_ROOT = METADATA / "handoff" / "runs"
PREPARE_RESULT_ROOT = METADATA / "handoff" / "prepare_results"


def now_text() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return {} if default is None else default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def result_status(success: bool | None) -> str:
    if success is True:
        return "PASS"
    if success is False:
        return "FAIL"
    return "NOT_RUN"


def latest_handoff_run(package_id: str) -> dict[str, Any]:
    root = RUN_ROOT / package_id
    if not root.exists():
        return {}
    candidates = sorted(root.glob("*/batch_report.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return {}
    report = read_json(candidates[0], {})
    if isinstance(report, dict):
        report["_report_path"] = str(candidates[0])
        return report
    return {}


def summarize_targets(plan: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = []
    unresolved = set(plan.get("unresolved_targets", []) if isinstance(plan.get("unresolved_targets"), list) else [])
    for case in plan.get("cases", []) if isinstance(plan.get("cases"), list) else []:
        for step in case.get("steps", []) if isinstance(case.get("steps"), list) else []:
            target_id = safe_text(step.get("target_id"))
            if target_id and (target_id in unresolved or step.get("binding_required")):
                gaps.append(
                    {
                        "case_id": safe_text(case.get("case_id")),
                        "step_order": step.get("step_order"),
                        "target_id": target_id,
                        "target_name": safe_text(step.get("target_name")),
                        "reason": "target_binding_required",
                    }
                )
    return gaps


def summarize_state_gaps(business_result: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = []
    for item in business_result.get("state_results", []) if isinstance(business_result.get("state_results"), list) else []:
        if not isinstance(item, dict) or item.get("success"):
            continue
        gaps.append(
            {
                "state_path": safe_text(item.get("state_path")),
                "collector": safe_text(item.get("collector")),
                "reason": safe_text(item.get("error")) or "state_collection_failed",
            }
        )
    return gaps


def summarize_assertion_gaps(plan: dict[str, Any], business_result: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = []
    for item in plan.get("business_assertion_plan", []) if isinstance(plan.get("business_assertion_plan"), list) else []:
        if isinstance(item, dict) and item.get("status") == "BLOCKED":
            gaps.append(
                {
                    "assertion_id": safe_text(item.get("assertion_id")),
                    "reason": safe_text(item.get("blocker")) or "assertion_plan_blocked",
                    "missing_external_refs": item.get("missing_external_refs", []),
                }
            )
    for item in business_result.get("assertion_results", []) if isinstance(business_result.get("assertion_results"), list) else []:
        if isinstance(item, dict) and not item.get("passed"):
            gaps.append(
                {
                    "assertion_id": safe_text(item.get("assertion_id")),
                    "reason": safe_text(item.get("error")) or "assertion_failed",
                    "operator": safe_text(item.get("operator")),
                    "expected": item.get("expected"),
                    "actual": item.get("actual"),
                    "external_ref_issues": item.get("external_ref_issues", []),
                    "source_trace": item.get("source_trace", []),
                }
            )
    return gaps


def summarize_navigation_gaps(plan: dict[str, Any]) -> list[dict[str, Any]]:
    nav = plan.get("navigation_plan", {}) if isinstance(plan.get("navigation_plan"), dict) else {}
    gaps = []
    for item in nav.get("pages", []) if isinstance(nav.get("pages"), list) else []:
        if not isinstance(item, dict):
            continue
        missing = []
        if item.get("entry_status") in {"NEEDS_RULE", "MANUAL_REQUIRED", "NEEDS_BINDING"}:
            missing.append("entry_rule")
        if item.get("back_status") in {"NEEDS_RULE", "MANUAL_REQUIRED", "NEEDS_BINDING"}:
            missing.append("back_rule")
        if item.get("recovery_status") in {"NEEDS_RULE", "MANUAL_REQUIRED", "NEEDS_BINDING"}:
            missing.append("recovery_rule")
        if missing:
            gaps.append({
                "page_id": safe_text(item.get("page_id")),
                "page_name": safe_text(item.get("page_name")),
                "reason": ",".join(missing),
                "entry_hint": safe_text(item.get("entry_hint")),
            })
    return gaps


def summarize_test_data_gaps(plan: dict[str, Any], precondition_result: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    data_plan = plan.get("test_data_prepare_plan", {}) if isinstance(plan.get("test_data_prepare_plan"), dict) else {}
    gaps = []
    for item in data_plan.get("preconditions", []) if isinstance(data_plan.get("preconditions"), list) else []:
        if isinstance(item, dict) and item.get("status") in {"BLOCKED", "NEEDS_ADAPTER"}:
            gaps.append({
                "precondition_id": safe_text(item.get("precondition_id")),
                "type": safe_text(item.get("type")),
                "reason": safe_text(item.get("reason")) or safe_text(item.get("status")),
                "description": safe_text(item.get("description")),
            })
    result = precondition_result if isinstance(precondition_result, dict) else {}
    for item in result.get("results", []) if isinstance(result.get("results"), list) else []:
        if not isinstance(item, dict) or item.get("passed"):
            continue
        gaps.append({
            "precondition_id": safe_text(item.get("precondition_id")),
            "type": safe_text(item.get("type")),
            "reason": safe_text(item.get("warning")) or "precondition_failed",
            "severity": safe_text(item.get("severity")),
            "actual": item.get("actual"),
            "expected": item.get("expected"),
        })
    return gaps


def build_feedback(package_id: str) -> dict[str, Any]:
    validation = read_json(REPORT_ROOT / f"{package_id}.validation_report.json", {})
    import_report = read_json(REPORT_ROOT / f"{package_id}.import_report.json", {})
    plan = read_json(IMPORT_ROOT / package_id / "execution_plan.json", {})
    business_result = read_json(BUSINESS_RESULT_ROOT / f"{package_id}.business_result.json", {})
    precondition_result = read_json(PREPARE_RESULT_ROOT / f"{package_id}.precondition_result.json", {})
    ui_run = latest_handoff_run(package_id)
    assertions = business_result.get("assertion_results", []) if isinstance(business_result.get("assertion_results"), list) else []
    passed_assertions = sum(1 for item in assertions if isinstance(item, dict) and item.get("passed"))
    feedback = {
        "schema_version": "autosmoke_qa_reader_feedback.v1",
        "package_id": package_id,
        "feature_id": safe_text(validation.get("feature_id") or plan.get("feature_id") or import_report.get("feature_id")),
        "generated_at": now_text(),
        "handoff_consumption": {
            "status": validation.get("status") or "UNKNOWN",
            "automation_level": validation.get("automation_level") or plan.get("automation_level") or "",
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
            "blockers": validation.get("blockers", []),
        },
        "conversion": {
            "success": bool(import_report.get("success") or import_report.get("outputs")) if import_report else False,
            "outputs": import_report.get("outputs", {}),
            "summary": import_report.get("summary", {}),
            "plan_status": plan.get("plan_status", "MISSING"),
        },
        "target_binding_gaps": summarize_targets(plan),
        "navigation_gaps": summarize_navigation_gaps(plan),
        "test_data_gaps": summarize_test_data_gaps(plan, precondition_result),
        "state_collection_gaps": summarize_state_gaps(business_result),
        "assertion_unexecutable_reasons": summarize_assertion_gaps(plan, business_result),
        "execution_report": {
            "ui_result": result_status(ui_run.get("success") if ui_run else None),
            "ui_mode": safe_text(ui_run.get("mode")) if ui_run else "",
            "ui_cases_passed": ui_run.get("passed_cases", 0) if ui_run else 0,
            "ui_cases_total": ui_run.get("total_cases", 0) if ui_run else 0,
            "ui_report_path": safe_text(ui_run.get("_report_path")) if ui_run else "",
            "business_result": result_status(business_result.get("success") if business_result else None),
            "assertions_passed": passed_assertions,
            "assertions_total": len(assertions),
            "business_result_path": str(BUSINESS_RESULT_ROOT / f"{package_id}.business_result.json") if business_result else "",
            "precondition_result": result_status(precondition_result.get("success") if precondition_result else None),
            "precondition_result_path": str(PREPARE_RESULT_ROOT / f"{package_id}.precondition_result.json") if precondition_result else "",
        },
        "source_trace": plan.get("source_trace", {}),
    }
    return feedback


def write_markdown(path: Path, feedback: dict[str, Any]) -> None:
    lines = [
        f"# QA_Reader 回执 - {feedback.get('package_id')}",
        "",
        f"- feature_id: {feedback.get('feature_id') or '-'}",
        f"- handoff 状态: {feedback.get('handoff_consumption', {}).get('status')}",
        f"- 自动化等级: {feedback.get('handoff_consumption', {}).get('automation_level') or '-'}",
        f"- 执行计划: {feedback.get('conversion', {}).get('plan_status')}",
        f"- UI 执行: {feedback.get('execution_report', {}).get('ui_result')} ({feedback.get('execution_report', {}).get('ui_mode') or 'not_run'})",
        f"- 业务执行: {feedback.get('execution_report', {}).get('business_result')}",
        f"- 断言: {feedback.get('execution_report', {}).get('assertions_passed')}/{feedback.get('execution_report', {}).get('assertions_total')}",
        "",
        "## 阻断项",
    ]
    blockers = feedback.get("handoff_consumption", {}).get("blockers", [])
    if blockers:
        for item in blockers:
            lines.append(f"- {safe_text(item.get('code'))}: {safe_text(item.get('message'))}")
    else:
        lines.append("- 无")
    sections = [
        ("目标绑定缺口", feedback.get("target_binding_gaps", []), "target_id", "reason"),
        ("页面进入/恢复缺口", feedback.get("navigation_gaps", []), "page_id", "reason"),
        ("测试数据准备缺口", feedback.get("test_data_gaps", []), "precondition_id", "reason"),
        ("状态采集缺口", feedback.get("state_collection_gaps", []), "state_path", "reason"),
        ("断言不可执行/失败", feedback.get("assertion_unexecutable_reasons", []), "assertion_id", "reason"),
    ]
    for title, items, key, reason_key in sections:
        lines += ["", f"## {title}"]
        if not items:
            lines.append("- 无")
            continue
        for item in items:
            lines.append(f"- {safe_text(item.get(key)) or '-'}: {safe_text(item.get(reason_key)) or '-'}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_feedback(package_id: str, write_files: bool = True) -> dict[str, Any]:
    feedback = build_feedback(package_id)
    if write_files:
        write_json(FEEDBACK_ROOT / f"{package_id}.qa_reader_feedback.json", feedback)
        write_markdown(FEEDBACK_ROOT / f"{package_id}.qa_reader_feedback.md", feedback)
    return feedback


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate QA_Reader-readable feedback from handoff outputs.")
    parser.add_argument("package_id")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    feedback = generate_feedback(args.package_id, write_files=not args.no_write)
    print(json.dumps(feedback, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
