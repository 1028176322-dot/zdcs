#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run AutoSmoke cases generated from a QA_Reader handoff package."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "metadata"
IMPORT_ROOT = METADATA / "handoff" / "imports"
RUN_ROOT = METADATA / "handoff" / "runs"


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


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


def now_text() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def step_to_text(step: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    action = safe_text(step.get("action")).lower()
    test_id = safe_text(step.get("test_id") or step.get("semantic_id"))
    target_name = safe_text(step.get("target_name"))
    if action in {"click", "tap"}:
        if not test_id:
            return "", {"reason": "test_id_missing", "target_id": step.get("target_id"), "target_name": target_name}
        return f'点击 testId("{quote(test_id)}")', {}
    if action in {"assert_visible", "assert_exists", "visible"}:
        if not test_id:
            return "", {"reason": "test_id_missing", "target_id": step.get("target_id"), "target_name": target_name}
        return f'断言存在 testId("{quote(test_id)}")', {}
    if action in {"assert_not_visible", "assert_not_exists"}:
        if not test_id:
            return "", {"reason": "test_id_missing", "target_id": step.get("target_id"), "target_name": target_name}
        return f'断言不存在 testId("{quote(test_id)}")', {}
    if action in {"wait", "sleep"}:
        timeout = step.get("timeout") or step.get("seconds") or 2
        return f"等待 {timeout} 秒", {}
    if action in {"back", "return"}:
        return "返回", {}
    if action in {"screenshot"}:
        return "截图", {}
    if action in {"input"}:
        value = safe_text(step.get("value"))
        if not test_id:
            return "", {"reason": "test_id_missing", "target_id": step.get("target_id"), "target_name": target_name}
        return f'输入 "{quote(value)}" 到 testId("{quote(test_id)}")', {}
    return "", {"reason": "unsupported_action", "action": action, "target_id": step.get("target_id"), "target_name": target_name}


def navigation_action_to_text(action: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(action, dict):
        return "", {"reason": "invalid_navigation_action"}
    status = safe_text(action.get("status"))
    kind = safe_text(action.get("action_kind"))
    act = safe_text(action.get("action")).lower()
    if status in {"NEEDS_RULE", "MANUAL_REQUIRED", "NEEDS_BINDING"}:
        return "", {"reason": status.lower(), "action_kind": kind, "hint": safe_text(action.get("hint")), "target_id": safe_text(action.get("target_id"))}
    if act == "click":
        test_id = safe_text(action.get("test_id"))
        if not test_id:
            return "", {"reason": "test_id_missing", "action_kind": kind, "target_id": safe_text(action.get("target_id"))}
        return f'点击 testId("{quote(test_id)}")', {}
    if act == "back":
        return "返回", {}
    if act == "wait":
        return safe_text(action.get("step_text")) or "等待 2 秒", {}
    return "", {"reason": "unsupported_navigation_action", "action_kind": kind, "action": act, "hint": safe_text(action.get("hint"))}


def navigation_steps_for_case(plan: dict[str, Any], case: dict[str, Any]) -> list[dict[str, Any]]:
    nav = plan.get("navigation_plan", {}) if isinstance(plan.get("navigation_plan"), dict) else {}
    pages = nav.get("pages", []) if isinstance(nav.get("pages"), list) else []
    if not pages:
        return []
    steps = case.get("steps", []) if isinstance(case.get("steps"), list) else []
    first_page = safe_text((steps[0] or {}).get("page_hint")) if steps and isinstance(steps[0], dict) else ""
    selected = None
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_name = safe_text(page.get("page_name"))
        page_id = safe_text(page.get("page_id"))
        if first_page and (first_page == page_name or first_page == page_id or first_page in page_name):
            selected = page
            break
    if selected is None and pages:
        selected = pages[0] if isinstance(pages[0], dict) else None
    if not selected:
        return []
    return [selected.get("entry_action", {})] if isinstance(selected.get("entry_action"), dict) else []


def build_cases_from_plan(plan: dict[str, Any]) -> dict[str, list[str]]:
    cases: dict[str, list[str]] = {}
    for case in plan.get("cases", []) if isinstance(plan.get("cases"), list) else []:
        case_id = safe_text(case.get("case_id")) or f"CASE_{len(cases) + 1:03d}"
        steps = []
        for nav_action in navigation_steps_for_case(plan, case if isinstance(case, dict) else {}):
            text, issue = navigation_action_to_text(nav_action)
            if issue:
                continue
            steps.append(text)
        for step in case.get("steps", []) if isinstance(case.get("steps"), list) else []:
            text, issue = step_to_text(step if isinstance(step, dict) else {})
            if issue:
                continue
            steps.append(text)
        cases[case_id] = steps
    return cases


def collect_plan_issues(plan: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    if safe_text(plan.get("plan_status")) not in {"", "READY_TO_RUN"}:
        issues.append({"code": "PLAN_NOT_READY", "message": safe_text(plan.get("plan_status"))})
    for target_id in plan.get("unresolved_targets", []) if isinstance(plan.get("unresolved_targets"), list) else []:
        issues.append({"code": "TARGET_UNRESOLVED", "target_id": safe_text(target_id)})
    for assertion_id in plan.get("unresolved_assertions", []) if isinstance(plan.get("unresolved_assertions"), list) else []:
        issues.append({"code": "ASSERTION_UNRESOLVED", "assertion_id": safe_text(assertion_id)})
    for case in plan.get("cases", []) if isinstance(plan.get("cases"), list) else []:
        case_id = safe_text(case.get("case_id"))
        for index, nav_action in enumerate(navigation_steps_for_case(plan, case if isinstance(case, dict) else {}), 1):
            text, issue = navigation_action_to_text(nav_action)
            if issue:
                issue["code"] = "NAVIGATION_NOT_EXECUTABLE"
                issue["severity"] = "warning" if issue.get("reason") in {"manual_required", "needs_rule"} else "blocking"
                issue["case_id"] = case_id
                issue["step_order"] = f"nav_{index}"
                issues.append(issue)
        for step in case.get("steps", []) if isinstance(case.get("steps"), list) else []:
            if not isinstance(step, dict):
                continue
            text, issue = step_to_text(step)
            if issue:
                issue["code"] = "STEP_NOT_EXECUTABLE"
                issue["severity"] = "blocking"
                issue["case_id"] = case_id
                issue["step_order"] = step.get("step_order")
                issues.append(issue)
    return issues


def blocking_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in issues if isinstance(item, dict) and item.get("severity", "blocking") != "warning"]


def precondition_issues(precondition_result: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    for item in precondition_result.get("results", []) if isinstance(precondition_result.get("results"), list) else []:
        if not isinstance(item, dict) or item.get("passed"):
            continue
        issues.append({
            "code": "PRECONDITION_FAILED",
            "severity": item.get("severity", "blocking"),
            "precondition_id": item.get("precondition_id"),
            "type": item.get("type"),
            "actual": item.get("actual"),
            "expected": item.get("expected"),
            "warning": item.get("warning", ""),
        })
    return issues


def dry_run_result(package_id: str, plan: dict[str, Any], cases: dict[str, list[str]], issues: list[dict[str, Any]], batch_name: str, precondition_result: dict[str, Any] | None = None) -> dict[str, Any]:
    case_results = []
    global_blockers = blocking_issues([i for i in issues if not i.get("case_id")])
    for case in plan.get("cases", []) if isinstance(plan.get("cases"), list) else []:
        case_id = safe_text(case.get("case_id")) or f"CASE_{len(case_results) + 1:03d}"
        case_issues = [i for i in issues if i.get("case_id") == case_id]
        case_blockers = blocking_issues(case_issues) + global_blockers
        steps = cases.get(case_id, [])
        case_results.append(
            {
                "case_id": case_id,
                "run_id": f"{batch_name}_{case_id}",
                "result": "BLOCKED" if case_blockers else "DRY_RUN_PASS",
                "total": len(steps),
                "passed": len(steps) if not case_blockers else 0,
                "failed": 0 if not case_blockers else len(case_blockers),
                "steps": [{"step_index": idx + 1, "raw": text, "result": "DRY_RUN"} for idx, text in enumerate(steps)],
                "issues": case_issues + global_blockers,
            }
        )
    failed = sum(1 for item in case_results if item.get("result") == "BLOCKED")
    return {
        "batch_name": batch_name,
        "timestamp": now_text(),
        "mode": "dry_run",
        "package_id": package_id,
        "total_cases": len(case_results),
        "passed_cases": len(case_results) - failed,
        "failed_cases": failed,
        "total_steps": sum(item.get("total", 0) for item in case_results),
        "passed_steps": sum(item.get("passed", 0) for item in case_results),
        "failed_steps": sum(item.get("failed", 0) for item in case_results),
        "case_results": case_results,
        "plan_issues": issues,
        "precondition_result": precondition_result or {},
    }


def run_handoff_package(
    package_id: str,
    dry_run: bool = True,
    batch_name: str = "",
    manual_values: dict[str, Any] | None = None,
    state_file: str | Path | None = None,
) -> dict[str, Any]:
    plan_path = IMPORT_ROOT / package_id / "execution_plan.json"
    plan = read_json(plan_path, {})
    if not isinstance(plan, dict) or not plan:
        return {"success": False, "error": "execution_plan_not_found", "package_id": package_id, "path": str(plan_path)}
    batch_name = batch_name or f"handoff_{package_id}_{time.strftime('%Y%m%d_%H%M%S')}"
    cases = build_cases_from_plan(plan)
    issues = collect_plan_issues(plan)
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from tools.handoff_preconditions import evaluate_preconditions
        preconditions = evaluate_preconditions(
            package_id,
            Path(state_file) if state_file else None,
            manual_values=manual_values or {},
            write_result=True,
        )
    except Exception as exc:
        preconditions = {"success": False, "error": "precondition_evaluator_failed", "detail": str(exc), "results": []}
    issues.extend(precondition_issues(preconditions))
    if dry_run or issues:
        batch_result = dry_run_result(package_id, plan, cases, issues, batch_name, precondition_result=preconditions)
    else:
        sys.path.insert(0, str(ROOT))
        from 用例层.batch_runner import BatchRunner

        runner = BatchRunner()
        batch_result = runner.run_steps_dict(cases, batch_name=batch_name)
        batch_result["mode"] = "execute"
        batch_result["package_id"] = package_id
        batch_result["plan_path"] = str(plan_path)
        batch_result["precondition_result"] = preconditions
    out_dir = RUN_ROOT / package_id / batch_name
    report_path = out_dir / "batch_report.json"
    batch_result["success"] = batch_result.get("failed_cases", 0) == 0
    batch_result["package_id"] = package_id
    batch_result["plan_path"] = str(plan_path)
    batch_result["generated_steps"] = cases
    write_json(report_path, batch_result)
    batch_result["report_path"] = str(report_path)
    return {"success": bool(batch_result["success"]), "batch": batch_result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run handoff-generated AutoSmoke cases.")
    parser.add_argument("package_id")
    parser.add_argument("--execute", action="store_true", help="Run real UI actions. Default is dry-run.")
    parser.add_argument("--batch-name", default="")
    parser.add_argument("--state-file", default="", help="Runtime state JSON for test_data_profile preconditions.")
    parser.add_argument("--manual-values", default="", help="JSON file with manual precondition values.")
    args = parser.parse_args()
    manual_values = read_json(Path(args.manual_values), {}) if args.manual_values else {}
    result = run_handoff_package(
        args.package_id,
        dry_run=not args.execute,
        batch_name=args.batch_name,
        manual_values=manual_values if isinstance(manual_values, dict) else {},
        state_file=args.state_file or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
