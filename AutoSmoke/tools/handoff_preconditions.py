#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evaluate test_data_profile preconditions from a handoff execution plan."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "metadata"
IMPORT_ROOT = METADATA / "handoff" / "imports"
PREPARE_ROOT = METADATA / "handoff" / "prepare_results"
DEFAULT_STATE = METADATA / "current_runtime_state.json"


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return {} if default is None else default
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_text() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def resolve_state_file(path: Path | None) -> Path:
    if path is None:
        return DEFAULT_STATE
    if path.is_absolute() or path.exists():
        return path
    candidates = [ROOT.parent / path, ROOT / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def lookup_path(data: Any, path: str) -> Any:
    cur = data
    for part in [p for p in safe_text(path).replace("/", ".").split(".") if p]:
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            idx = int(part)
            cur = cur[idx] if 0 <= idx < len(cur) else None
        else:
            return None
    return cur


def compare(actual: Any, operator: str, expected: Any) -> bool:
    op = safe_text(operator) or "exists"
    if op in {"exists", "not_empty"}:
        return actual not in (None, "", [], {})
    if op in {"equals", "eq"}:
        return actual == expected
    if op == "contains":
        return safe_text(expected) in safe_text(actual)
    if op in {"gte", ">="}:
        try:
            return float(actual) >= float(expected)
        except Exception:
            return False
    if op in {"lte", "<="}:
        try:
            return float(actual) <= float(expected)
        except Exception:
            return False
    return False


def evaluate_one(item: dict[str, Any], state: dict[str, Any], manual_values: dict[str, Any]) -> dict[str, Any]:
    precondition_id = safe_text(item.get("precondition_id"))
    kind = safe_text(item.get("type") or "manual")
    source = item.get("source", {}) if isinstance(item.get("source"), dict) else {}
    severity = safe_text(source.get("severity") or item.get("severity") or "blocking")
    key = safe_text(source.get("key") or source.get("path") or item.get("key") or item.get("path") or precondition_id)
    expected = source.get("expected", item.get("expected", True))
    operator = safe_text(source.get("operator") or item.get("operator") or "exists")

    if kind == "manual":
        if precondition_id in manual_values:
            ok = bool(manual_values.get(precondition_id))
            return {"precondition_id": precondition_id, "type": kind, "passed": ok, "severity": severity, "actual": manual_values.get(precondition_id), "expected": expected}
        return {"precondition_id": precondition_id, "type": kind, "passed": False, "severity": severity, "warning": "manual_precondition_not_confirmed"}

    if kind in {"account_state", "resource", "feature_flag"}:
        actual = manual_values.get(precondition_id)
        if actual is None and key:
            actual = lookup_path(state, key)
        ok = compare(actual, operator, expected)
        return {"precondition_id": precondition_id, "type": kind, "passed": ok, "severity": severity, "key": key, "operator": operator, "actual": actual, "expected": expected}

    return {"precondition_id": precondition_id, "type": kind, "passed": severity != "blocking", "severity": severity, "warning": "unsupported_precondition_adapter"}


def evaluate_preconditions(package_id: str, state_file: Path | None = None, manual_values: dict[str, Any] | None = None, write_result: bool = True) -> dict[str, Any]:
    plan_path = IMPORT_ROOT / package_id / "execution_plan.json"
    plan = read_json(plan_path, {})
    if not isinstance(plan, dict) or not plan:
        return {"success": False, "error": "execution_plan_not_found", "package_id": package_id, "path": str(plan_path)}
    resolved_state_file = resolve_state_file(state_file)
    state = read_json(resolved_state_file, {})
    manual_values = manual_values if isinstance(manual_values, dict) else {}
    data_plan = plan.get("test_data_prepare_plan", {}) if isinstance(plan.get("test_data_prepare_plan"), dict) else {}
    preconditions = data_plan.get("preconditions", []) if isinstance(data_plan.get("preconditions"), list) else []
    results = [evaluate_one(item, state if isinstance(state, dict) else {}, manual_values) for item in preconditions if isinstance(item, dict)]
    blockers = [item for item in results if not item.get("passed") and item.get("severity", "blocking") == "blocking"]
    warnings = [item for item in results if not item.get("passed") and item.get("severity") != "blocking"]
    result = {
        "schema_version": "autosmoke_handoff_precondition_result.v1",
        "success": len(blockers) == 0,
        "package_id": package_id,
        "plan_path": str(plan_path),
        "state_path": str(resolved_state_file),
        "total": len(results),
        "passed": sum(1 for item in results if item.get("passed")),
        "blocked": len(blockers),
        "warnings": len(warnings),
        "results": results,
        "executed_at": now_text(),
    }
    if write_result:
        write_json(PREPARE_ROOT / f"{package_id}.precondition_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate handoff test data preconditions.")
    parser.add_argument("package_id")
    parser.add_argument("--state-file", default="")
    parser.add_argument("--manual-values", default="")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    manual = read_json(Path(args.manual_values), {}) if args.manual_values else {}
    result = evaluate_preconditions(args.package_id, Path(args.state_file) if args.state_file else None, manual if isinstance(manual, dict) else {}, write_result=not args.no_write)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
