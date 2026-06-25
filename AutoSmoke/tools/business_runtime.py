#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run business state collection and assertions from a handoff execution plan."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "metadata"
DEFAULT_RUNTIME_TREE = METADATA / "runtime_ui_tree_current.json"
RESULT_ROOT = METADATA / "handoff" / "business_results"


def now_text() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


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


def norm(value: Any) -> str:
    text = safe_text(value).lower()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)


def state_tokens(state_path: str, state_item: dict[str, Any]) -> list[str]:
    explicit = state_item.get("text_hint") or state_item.get("selector") or state_item.get("target_name")
    tokens = []
    if explicit:
        tokens.append(norm(explicit))
    tail = safe_text(state_path).split(".")[-1]
    tokens.extend([norm(tail), norm(tail.replace("_", "")), norm(tail.replace("_", " "))])
    tokens = [t for t in tokens if t]
    out = []
    for token in tokens:
        if token not in out:
            out.append(token)
    return out


def node_text(node: dict[str, Any]) -> str:
    chunks = [
        node.get("text"),
        node.get("nodeName"),
        node.get("runtimePath"),
        node.get("pageId"),
        node.get("ownerPageId"),
        node.get("spriteName"),
    ]
    return " ".join(safe_text(x) for x in chunks if safe_text(x))


def node_value(node: dict[str, Any]) -> str:
    for key in ("text", "value", "label", "nodeName"):
        value = safe_text(node.get(key))
        if value:
            return value
    return ""


def collect_ui_runtime_tree(state_item: dict[str, Any], runtime_tree: dict[str, Any]) -> dict[str, Any]:
    state_path = safe_text(state_item.get("state_path"))
    nodes = runtime_tree.get("nodes", []) if isinstance(runtime_tree, dict) else []
    if not isinstance(nodes, list):
        return {"success": False, "state_path": state_path, "value": None, "error": "runtime_nodes_invalid"}

    selector = state_item.get("selector")
    if isinstance(selector, dict):
        selector_type = safe_text(selector.get("type"))
        selector_value = safe_text(selector.get("value"))
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if selector_type == "runtimePath" and safe_text(node.get("runtimePath")) == selector_value:
                return {"success": True, "state_path": state_path, "value": node_value(node), "node": compact_node(node), "collector": "ui_runtime_tree"}
            if selector_type == "text" and selector_value and selector_value in safe_text(node.get("text")):
                return {"success": True, "state_path": state_path, "value": node_value(node), "node": compact_node(node), "collector": "ui_runtime_tree"}

    tokens = state_tokens(state_path, state_item)
    best = None
    best_score = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        haystack = norm(node_text(node))
        if not haystack:
            continue
        score = sum(1 for token in tokens if token and token in haystack)
        if score > best_score:
            best = node
            best_score = score
    if best is not None and best_score > 0:
        return {"success": True, "state_path": state_path, "value": node_value(best), "node": compact_node(best), "collector": "ui_runtime_tree", "matchScore": best_score}
    return {"success": False, "state_path": state_path, "value": None, "error": "state_not_found", "collector": "ui_runtime_tree", "tokens": tokens}


def compact_node(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtimePath": safe_text(node.get("runtimePath")),
        "nodeName": safe_text(node.get("nodeName")),
        "text": safe_text(node.get("text")),
        "pageId": safe_text(node.get("pageId") or node.get("ownerPageId")),
        "screenRect": node.get("screenRect", []),
    }


def collect_states(plan: dict[str, Any], runtime_tree: dict[str, Any], manual_values: dict[str, Any] | None = None) -> dict[str, Any]:
    manual_values = manual_values if isinstance(manual_values, dict) else {}
    values = {}
    results = []
    for item in plan.get("state_collection_plan", []) if isinstance(plan.get("state_collection_plan", []), list) else []:
        if not isinstance(item, dict):
            continue
        collector = safe_text(item.get("collector"))
        state_path = safe_text(item.get("state_path"))
        if collector == "ui_runtime_tree":
            result = collect_ui_runtime_tree(item, runtime_tree)
        elif collector == "manual":
            if state_path in manual_values:
                result = {"success": True, "state_path": state_path, "value": manual_values.get(state_path), "collector": collector}
            else:
                result = {"success": False, "state_path": state_path, "value": None, "collector": collector, "error": "manual_collector_requires_input"}
        elif collector == "screenshot_diff":
            result = {"success": False, "state_path": state_path, "value": None, "collector": collector, "error": "screenshot_diff_runtime_not_implemented"}
        else:
            result = {"success": False, "state_path": state_path, "value": None, "collector": collector, "error": "unsupported_collector"}
        values[state_path] = result.get("value")
        results.append(result)
    return {"values": values, "results": results}


def eval_one(assertion: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    assertion_id = safe_text(assertion.get("assertion_id"))
    state_paths = assertion.get("state_paths", [])
    if isinstance(state_paths, str):
        state_paths = [state_paths]
    state_paths = [safe_text(x) for x in state_paths if safe_text(x)]
    operator = safe_text(assertion.get("operator") or assertion.get("type") or assertion.get("check")) or "not_empty"
    expected = assertion.get("expected")
    actuals = {sp: values.get(sp) for sp in state_paths}
    missing = [sp for sp in state_paths if sp not in values or values.get(sp) in (None, "")]
    passed = False
    if operator == "not_empty":
        passed = not missing
    elif operator in {"equals", "eq"}:
        passed = bool(state_paths) and all(values.get(sp) == expected for sp in state_paths)
    elif operator in {"contains"}:
        passed = bool(state_paths) and all(safe_text(expected) in safe_text(values.get(sp)) for sp in state_paths)
    elif operator in {"changed"}:
        passed = bool(state_paths) and all(values.get(sp) not in (None, "", expected) for sp in state_paths)
    else:
        return {"assertion_id": assertion_id, "passed": False, "operator": operator, "actual": actuals, "expected": expected, "error": "unsupported_operator"}
    return {"assertion_id": assertion_id, "passed": passed, "operator": operator, "actual": actuals, "expected": expected, "missing": missing}


def evaluate_assertions(plan: dict[str, Any], values: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for assertion in plan.get("business_assertion_plan", []) if isinstance(plan.get("business_assertion_plan", []), list) else []:
        if not isinstance(assertion, dict):
            continue
        source = assertion.get("source") if isinstance(assertion.get("source"), dict) else assertion
        out.append(eval_one(source, values))
    return out


def trace_for_assertions(plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    trace = plan.get("source_trace", {}) if isinstance(plan.get("source_trace"), dict) else {}
    links = trace.get("links", [])
    if not isinstance(links, list):
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for link in links:
        if not isinstance(link, dict):
            continue
        assertion_ids = link.get("assertion_ids") or link.get("assertionRefs") or link.get("assertion_refs") or []
        if isinstance(assertion_ids, str):
            assertion_ids = [assertion_ids]
        if not isinstance(assertion_ids, list):
            continue
        compact = {
            "source_id": safe_text(link.get("source_id") or link.get("sourceId")),
            "case_id": safe_text(link.get("case_id") or link.get("caseId")),
            "target_ids": link.get("target_ids") or link.get("targetIds") or [],
        }
        for assertion_id in assertion_ids:
            aid = safe_text(assertion_id)
            if aid:
                out.setdefault(aid, []).append(compact)
    return out


def run_business_plan(package_id: str, runtime_file: Path | None = None, write_result: bool = True, manual_values: dict[str, Any] | None = None) -> dict[str, Any]:
    plan_path = METADATA / "handoff" / "imports" / package_id / "execution_plan.json"
    plan = read_json(plan_path, {})
    if not isinstance(plan, dict) or not plan:
        return {"success": False, "error": "execution_plan_not_found", "package_id": package_id, "path": str(plan_path)}
    runtime_path = runtime_file or DEFAULT_RUNTIME_TREE
    runtime_tree = read_json(runtime_path, {})
    collected = collect_states(plan, runtime_tree if isinstance(runtime_tree, dict) else {}, manual_values=manual_values)
    assertions = evaluate_assertions(plan, collected["values"])
    traces = trace_for_assertions(plan)
    for item in assertions:
        item["source_trace"] = traces.get(safe_text(item.get("assertion_id")), [])
    success = all(item.get("passed") for item in assertions) if assertions else True
    result = {
        "schema_version": "autosmoke_business_assertion_result.v1",
        "success": success,
        "package_id": package_id,
        "plan_path": str(plan_path),
        "runtime_path": str(runtime_path),
        "state_results": collected["results"],
        "state_values": collected["values"],
        "assertion_results": assertions,
        "executed_at": now_text(),
    }
    if write_result:
        write_json(RESULT_ROOT / f"{package_id}.business_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run business assertions from a handoff execution plan.")
    parser.add_argument("package_id")
    parser.add_argument("--runtime-file", default="")
    parser.add_argument("--manual-values", default="", help="JSON file containing manual state values keyed by state_path.")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    manual_values = read_json(Path(args.manual_values), {}) if args.manual_values else {}
    result = run_business_plan(args.package_id, Path(args.runtime_file) if args.runtime_file else None, write_result=not args.no_write, manual_values=manual_values if isinstance(manual_values, dict) else {})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
