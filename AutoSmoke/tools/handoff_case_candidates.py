#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate manual_test_cases candidates from QA_Reader feature-flow shapes."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "metadata"
IMPORT_ROOT = METADATA / "handoff" / "imports"
CANDIDATE_ROOT = METADATA / "handoff" / "candidates"


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


def slug(value: Any, fallback: str = "case") -> str:
    text = safe_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or fallback


def resolve_package(package_or_dir: str) -> tuple[str, Path]:
    raw = Path(package_or_dir)
    candidates = [raw]
    if not raw.is_absolute():
        candidates.extend([ROOT.parent / raw, ROOT / raw])
    else:
        raw_text = str(raw)
        doubled = f"{ROOT.name}\\{ROOT.name}"
        if doubled in raw_text:
            candidates.insert(0, Path(raw_text.replace(doubled, ROOT.name, 1)))
    for candidate in candidates:
        if candidate.exists():
            package_dir = candidate
            manifest = read_json(package_dir / "manifest.json", {})
            package_id = safe_text(manifest.get("package_id") or manifest.get("packageId") or package_dir.name)
            return package_id, package_dir
    if raw.exists():
        package_dir = raw
        manifest = read_json(package_dir / "manifest.json", {})
        package_id = safe_text(manifest.get("package_id") or manifest.get("packageId") or package_dir.name)
        return package_id, package_dir
    package_id = safe_text(package_or_dir)
    return package_id, IMPORT_ROOT / package_id


def load_flow_payload(package_dir: Path) -> tuple[dict[str, Any], str]:
    for name in ("candidate_feature_flow.v1.json", "feature_flow_review_result.v1.json"):
        payload = read_json(package_dir / name, {})
        if isinstance(payload, dict) and payload:
            return payload, name
    return {}, ""


def list_flows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("candidate_feature_flows", "candidate_flows", "feature_flows", "flows", "cases", "review_items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    steps = payload.get("steps")
    if isinstance(steps, list):
        return [payload]
    return []


def flow_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("steps", "actions", "path", "flow_steps", "flowSteps"):
        value = flow.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def normalize_action(value: Any) -> str:
    text = safe_text(value).lower()
    aliases = {
        "tap": "click",
        "press": "click",
        "点击": "click",
        "输入": "input",
        "断言可见": "assert_visible",
        "断言存在": "assert_exists",
        "等待": "wait",
        "返回": "back",
    }
    return aliases.get(text, text or "unknown")


def convert_step(step: dict[str, Any], order: int) -> dict[str, Any]:
    target_id = safe_text(step.get("target_id") or step.get("targetId") or step.get("target"))
    target_name = safe_text(step.get("target_name") or step.get("targetName") or step.get("name") or step.get("label"))
    out = {
        "step_order": int(step.get("step_order") or step.get("order") or order),
        "action": normalize_action(step.get("action") or step.get("type")),
        "target_id": target_id,
        "target_name": target_name,
        "page_id": safe_text(step.get("page_id") or step.get("pageId")),
        "page_name": safe_text(step.get("page_name") or step.get("pageName")),
        "expected": safe_text(step.get("expected") or step.get("expect")),
        "assertion_refs": step.get("assertion_refs") if isinstance(step.get("assertion_refs"), list) else [],
        "source_node_ids": step.get("source_node_ids") if isinstance(step.get("source_node_ids"), list) else [],
        "source": step,
    }
    return {k: v for k, v in out.items() if v not in ("", [], {})}


def generate_case_candidates(package_or_dir: str, write_files: bool = True) -> dict[str, Any]:
    package_id, package_dir = resolve_package(package_or_dir)
    payload, source_file = load_flow_payload(package_dir)
    feature_id = safe_text(payload.get("feature_id") or payload.get("featureId") or package_id)
    flows = list_flows(payload) if payload else []
    cases = []
    skipped = []
    if payload and not flows:
        skipped.append({"reason": "no_feature_flows_found", "source_file": source_file})
    if not payload:
        skipped.append({"reason": "feature_flow_payload_not_found"})
    for index, flow in enumerate(flows, start=1):
        steps = [convert_step(step, order) for order, step in enumerate(flow_steps(flow), start=1)]
        executable_steps = [step for step in steps if safe_text(step.get("action")) and (step.get("target_id") or step.get("target_name") or step.get("action") in {"wait", "back"})]
        if not executable_steps:
            skipped.append({"index": index, "reason": "flow_has_no_executable_steps", "title": safe_text(flow.get("title") or flow.get("name"))})
            continue
        flow_id = safe_text(flow.get("flow_id") or flow.get("flowId") or flow.get("case_id") or flow.get("id") or index)
        case_id = safe_text(flow.get("case_id") or flow.get("caseId")) or f"CAND_{slug(feature_id).upper()}_{slug(flow_id, str(index)).upper()}"
        cases.append({
            "case_id": case_id,
            "title": safe_text(flow.get("title") or flow.get("name") or case_id),
            "automation_level": safe_text(flow.get("automation_level") or flow.get("automationLevel") or payload.get("automation_level")) or "UI_ONLY",
            "steps": executable_steps,
            "source_flow": {"source_file": source_file, "flow_id": flow_id, "index": index},
        })
    candidate = {
        "schema_version": "manual_test_cases.v1",
        "feature_id": feature_id,
        "test_cases": cases,
    }
    report = {
        "schema_version": "autosmoke_handoff_case_candidate_report.v1",
        "success": bool(cases),
        "package_id": package_id,
        "package_dir": str(package_dir),
        "source_file": source_file,
        "candidate_count": len(cases),
        "skipped": skipped,
        "output": "",
        "generated_at": now_text(),
    }
    if write_files:
        out_path = CANDIDATE_ROOT / package_id / "manual_test_cases.candidate.json"
        write_json(out_path, candidate)
        report["output"] = str(out_path)
        write_json(CANDIDATE_ROOT / package_id / "case_candidate_report.json", report)
    return {"success": bool(cases), "candidate": candidate, "report": report}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate handoff manual_test_cases candidates from feature flow data.")
    parser.add_argument("package_or_dir")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    result = generate_case_candidates(args.package_or_dir, write_files=not args.no_write)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
