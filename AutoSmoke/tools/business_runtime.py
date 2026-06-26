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
REPO_ROOT = ROOT.parent
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
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_input_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    root_candidate = ROOT / path
    if root_candidate.exists():
        return root_candidate
    repo_candidate = REPO_ROOT / path
    if repo_candidate.exists():
        return repo_candidate
    return root_candidate


def norm(value: Any) -> str:
    text = safe_text(value).lower()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)


def lookup_path(data: Any, path: str) -> Any:
    cur = data
    for part in [p for p in safe_text(path).replace("/", ".").split(".") if p]:
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            index = int(part)
            cur = cur[index] if 0 <= index < len(cur) else None
        else:
            return None
    return cur


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


def collect_screenshot_diff(state_item: dict[str, Any], manual_values: dict[str, Any]) -> dict[str, Any]:
    state_path = safe_text(state_item.get("state_path"))
    injected = manual_values.get(state_path)
    if isinstance(injected, dict):
        before_path = safe_text(injected.get("before_path") or injected.get("before"))
        after_path = safe_text(injected.get("after_path") or injected.get("after"))
    else:
        before_path = safe_text(state_item.get("before_path") or state_item.get("before"))
        after_path = safe_text(state_item.get("after_path") or state_item.get("after"))
    if not before_path or not after_path:
        return {"success": False, "state_path": state_path, "value": None, "collector": "screenshot_diff", "error": "before_after_paths_required"}
    before = resolve_input_path(before_path)
    after = resolve_input_path(after_path)
    if not before.exists() or not after.exists():
        return {
            "success": False,
            "state_path": state_path,
            "value": None,
            "collector": "screenshot_diff",
            "error": "screenshot_file_missing",
            "before_path": str(before),
            "after_path": str(after),
        }
    try:
        import sys

        sys.path.insert(0, str(ROOT))
        from 坐标截图.screenshot_diff import ScreenshotDiffer
    except Exception:
        import importlib.util

        module_path = ROOT / "\u5750\u6807\u622a\u56fe" / "screenshot_diff.py"
        spec = importlib.util.spec_from_file_location("screenshot_diff_mod", module_path)
        if spec is None or spec.loader is None:
            return {"success": False, "state_path": state_path, "value": None, "collector": "screenshot_diff", "error": "screenshot_differ_import_failed"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ScreenshotDiffer = mod.ScreenshotDiffer
    result = ScreenshotDiffer(output_dir=str(RESULT_ROOT / "diffs")).compare_files(
        str(before),
        str(after),
        run_id=safe_text(state_item.get("domain_id")) or "business",
        step_id=state_path.replace(".", "_") or "state_diff",
    )
    ratio = result.get("diff_ratio")
    threshold = state_item.get("diff_threshold", 0)
    try:
        threshold = float(threshold or 0)
    except Exception:
        threshold = 0
    return {
        "success": True,
        "state_path": state_path,
        "value": ratio,
        "collector": "screenshot_diff",
        "diff_ratio": ratio,
        "changed": bool(float(ratio or 0) > threshold),
        "threshold": threshold,
        "diff_image_path": result.get("diff_image_path", ""),
        "step_result_path": result.get("step_result_path", ""),
    }


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
        if state_path in manual_values:
            result = {"success": True, "state_path": state_path, "value": manual_values.get(state_path), "collector": "manual_override", "source_collector": collector}
        elif lookup_path(runtime_tree, state_path) not in (None, "", [], {}):
            result = {"success": True, "state_path": state_path, "value": lookup_path(runtime_tree, state_path), "collector": "runtime_state_json", "source_collector": collector}
        elif collector == "ui_runtime_tree":
            result = collect_ui_runtime_tree(item, runtime_tree)
        elif collector == "manual":
            if state_path in manual_values:
                result = {"success": True, "state_path": state_path, "value": manual_values.get(state_path), "collector": collector}
            else:
                result = {"success": False, "state_path": state_path, "value": None, "collector": collector, "error": "manual_collector_requires_input"}
        elif collector == "screenshot_diff":
            result = collect_screenshot_diff(item, manual_values)
        else:
            result = {"success": False, "state_path": state_path, "value": None, "collector": collector, "error": "unsupported_collector"}
        values[state_path] = result.get("value")
        results.append(result)
    return {"values": values, "results": results}


def expected_from_asset(assertion: dict[str, Any], value_assets: dict[str, Any]) -> tuple[Any, dict[str, Any] | None]:
    asset_id = safe_text(assertion.get("expected_asset_id") or assertion.get("value_asset_id") or assertion.get("asset_id"))
    if not asset_id:
        return assertion.get("expected"), None
    asset = value_assets.get(asset_id)
    if not isinstance(asset, dict):
        return assertion.get("expected"), {"asset_id": asset_id, "error": "value_asset_not_found"}
    for key in ("expected", "value", "threshold", "text", "amount"):
        if key in asset:
            return asset.get(key), asset
    return assertion.get("expected"), asset


def external_ref_issues(assertion: dict[str, Any], external_refs: dict[str, Any]) -> list[dict[str, Any]]:
    ref_ids = assertion.get("external_ref_ids") or assertion.get("external_refs") or assertion.get("externalRefIds") or []
    if isinstance(ref_ids, str):
        ref_ids = [ref_ids]
    if not isinstance(ref_ids, list):
        return []
    issues = []
    for raw_ref_id in ref_ids:
        ref_id = safe_text(raw_ref_id)
        if not ref_id:
            continue
        ref = external_refs.get(ref_id)
        if not isinstance(ref, dict):
            issues.append({"ref_id": ref_id, "severity": "blocking", "reason": "external_ref_not_found"})
            continue
        required = bool(ref.get("required", False))
        status = safe_text(ref.get("status") or "unknown").lower()
        if status not in {"ready", "ok", "available"}:
            issues.append({
                "ref_id": ref_id,
                "severity": "blocking" if required else "warning",
                "reason": "external_ref_not_ready",
                "status": status,
            })
    return issues


def eval_one(assertion: dict[str, Any], values: dict[str, Any], value_assets: dict[str, Any] | None = None, external_refs: dict[str, Any] | None = None) -> dict[str, Any]:
    value_assets = value_assets if isinstance(value_assets, dict) else {}
    external_refs = external_refs if isinstance(external_refs, dict) else {}
    assertion_id = safe_text(assertion.get("assertion_id"))
    ref_issues = external_ref_issues(assertion, external_refs)
    blocking_refs = [item for item in ref_issues if item.get("severity") == "blocking"]
    if blocking_refs:
        return {
            "assertion_id": assertion_id,
            "passed": False,
            "operator": safe_text(assertion.get("operator") or assertion.get("type") or assertion.get("check")) or "not_empty",
            "actual": {},
            "expected": assertion.get("expected"),
            "missing": [],
            "error": "external_ref_blocked",
            "external_ref_issues": ref_issues,
        }
    state_paths = assertion.get("state_paths", [])
    if isinstance(state_paths, str):
        state_paths = [state_paths]
    state_paths = [safe_text(x) for x in state_paths if safe_text(x)]
    operator = safe_text(assertion.get("operator") or assertion.get("type") or assertion.get("check")) or "not_empty"
    expected, asset = expected_from_asset(assertion, value_assets)
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
    elif operator in {"same_as", "equals_state", "state_equals"}:
        compare_path = safe_text(assertion.get("expected_state_path") or assertion.get("compare_state_path"))
        if compare_path:
            actuals[compare_path] = values.get(compare_path)
            missing += [compare_path] if compare_path not in values or values.get(compare_path) in (None, "") else []
            passed = bool(state_paths) and compare_path in values and all(values.get(sp) == values.get(compare_path) for sp in state_paths)
        else:
            passed = len(state_paths) >= 2 and all(values.get(sp) == values.get(state_paths[0]) for sp in state_paths)
    else:
        return {"assertion_id": assertion_id, "passed": False, "operator": operator, "actual": actuals, "expected": expected, "error": "unsupported_operator"}
    result = {"assertion_id": assertion_id, "passed": passed, "operator": operator, "actual": actuals, "expected": expected, "missing": missing}
    if ref_issues:
        result["external_ref_issues"] = ref_issues
    if isinstance(asset, dict):
        result["value_asset"] = {"asset_id": safe_text(asset.get("asset_id") or asset.get("assetId") or asset.get("id")), "description": safe_text(asset.get("description"))}
        if asset.get("error"):
            result["error"] = asset.get("error")
    return result


def evaluate_assertions(plan: dict[str, Any], values: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    value_assets = plan.get("value_assets", {}) if isinstance(plan.get("value_assets"), dict) else {}
    external_refs = plan.get("optional_external_refs", {}) if isinstance(plan.get("optional_external_refs"), dict) else {}
    for assertion in plan.get("business_assertion_plan", []) if isinstance(plan.get("business_assertion_plan", []), list) else []:
        if not isinstance(assertion, dict):
            continue
        source = assertion.get("source") if isinstance(assertion.get("source"), dict) else assertion
        out.append(eval_one(source, values, value_assets=value_assets, external_refs=external_refs))
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
    runtime_path = resolve_input_path(str(runtime_file)) if runtime_file else DEFAULT_RUNTIME_TREE
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
        "external_refs": plan.get("optional_external_refs", {}) if isinstance(plan.get("optional_external_refs"), dict) else {},
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
