#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate and import QA_Reader handoff packages into AutoSmoke.

P0 scope:
  - validate the minimum UI automation package
  - classify UI_ONLY / UI_AND_BUSINESS admission
  - convert manual_test_cases into AutoSmoke case JSON
  - convert target_name_catalog into mapping task queue entries
  - write a traceable validation/import report
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "metadata"
IMPORT_ROOT = METADATA / "handoff" / "imports"
REPORT_ROOT = METADATA / "handoff" / "reports"
SEMANTIC_DICTIONARY = METADATA / "semantic_dictionary.json"
SEMANTIC_PENDING = METADATA / "semantic_dictionary_pending.json"

REQUIRED_UI_FILES = {
    "manifest.json",
    "feature_flow_review_result.v1.json",
    "manual_test_cases.v1.json",
    "target_name_catalog.v1.json",
    "page_flow_catalog.v1.json",
    "test_data_profile.v1.json",
    "source_trace.v1.json",
    "review_items.v1.json",
}

BUSINESS_FILES = {
    "value_assets.v1.json",
    "business_state_contract.v1.json",
    "business_assertions.v1.json",
    "optional_external_refs.v1.json",
}

UI_ACTIONS_REQUIRING_TARGET = {"click", "tap", "long_press", "input", "assert_visible", "assert_exists"}
READY_STATUSES = {"READY_UI_ONLY", "READY_UI_AND_BUSINESS", "PASS_WITH_GAP"}
BLOCKING_REVIEW_STATUSES = {"BLOCKED", "REVIEW_REQUIRED"}
SUPPORTED_STATE_COLLECTORS = {"ui_runtime_tree", "screenshot_diff", "manual"}


@dataclass
class Issue:
    code: str
    message: str
    path: str = ""
    severity: str = "ERROR"

    def to_dict(self) -> dict[str, str]:
        data = {"code": self.code, "message": self.message, "severity": self.severity}
        if self.path:
            data["path"] = self.path
        return data


@dataclass
class HandoffContext:
    package_dir: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    files: dict[str, Any] = field(default_factory=dict)
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    blockers: list[Issue] = field(default_factory=list)

    @property
    def package_id(self) -> str:
        return safe_text(self.manifest.get("package_id")) or self.package_dir.name

    @property
    def feature_id(self) -> str:
        return safe_text(self.manifest.get("feature_id"))


def now_text() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def slug(value: str, fallback: str = "item") -> str:
    text = safe_text(value).lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def read_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "file must contain a JSON object"
    return data, ""


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def productized_semantic_id(value: Any) -> bool:
    text = safe_text(value)
    if not text or "custom_" in text or ".." in text:
        return False
    if re.search(r"[\u4e00-\u9fff]", text):
        return False
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+", text))


def generic_semantic_id(value: Any) -> bool:
    text = safe_text(value)
    return text.startswith("ui.") or text.startswith("runtime.")


def add_error(ctx: HandoffContext, code: str, message: str, path: str = "") -> None:
    ctx.errors.append(Issue(code=code, message=message, path=path, severity="ERROR"))


def add_warning(ctx: HandoffContext, code: str, message: str, path: str = "") -> None:
    ctx.warnings.append(Issue(code=code, message=message, path=path, severity="WARNING"))


def add_blocker(ctx: HandoffContext, code: str, message: str, path: str = "") -> None:
    ctx.blockers.append(Issue(code=code, message=message, path=path, severity="BLOCKER"))


def load_package(package_dir: Path) -> HandoffContext:
    ctx = HandoffContext(package_dir=package_dir)
    if not package_dir.exists() or not package_dir.is_dir():
        add_error(ctx, "PACKAGE_NOT_FOUND", f"handoff package directory not found: {package_dir}")
        return ctx

    for name in sorted(REQUIRED_UI_FILES | BUSINESS_FILES):
        path = package_dir / name
        if not path.exists():
            continue
        data, error = read_json(path)
        if error:
            add_error(ctx, "JSON_READ_FAILED", error, name)
        elif data is not None:
            ctx.files[name] = data

    manifest = ctx.files.get("manifest.json")
    if isinstance(manifest, dict):
        ctx.manifest = manifest
    else:
        add_error(ctx, "MANIFEST_MISSING", "manifest.json is required", "manifest.json")
    return ctx


def validate_required_files(ctx: HandoffContext) -> None:
    for name in sorted(REQUIRED_UI_FILES):
        if name not in ctx.files:
            add_error(ctx, "REQUIRED_FILE_MISSING", f"required file is missing: {name}", name)


def validate_schema_versions(ctx: HandoffContext) -> None:
    expected = {
        "manifest.json": "autosmoke_upstream_handoff.v1",
        "feature_flow_review_result.v1.json": "feature_flow_review_result.v1",
        "manual_test_cases.v1.json": "manual_test_cases.v1",
        "target_name_catalog.v1.json": "target_name_catalog.v1",
        "page_flow_catalog.v1.json": "page_flow_catalog.v1",
        "test_data_profile.v1.json": "test_data_profile.v1",
        "source_trace.v1.json": "source_trace.v1",
        "review_items.v1.json": "review_items.v1",
        "value_assets.v1.json": "value_assets.v1",
        "business_state_contract.v1.json": "business_state_contract.v1",
        "business_assertions.v1.json": "business_assertions.v1",
        "optional_external_refs.v1.json": "optional_external_refs.v1",
    }
    for name, schema_version in expected.items():
        data = ctx.files.get(name)
        if not isinstance(data, dict):
            continue
        actual = safe_text(data.get("schema_version"))
        if actual != schema_version:
            add_error(ctx, "SCHEMA_VERSION_MISMATCH", f"{name} schema_version must be {schema_version}, got {actual or '<empty>'}", name)


def validate_feature_id_consistency(ctx: HandoffContext) -> None:
    manifest_feature = ctx.feature_id
    if not manifest_feature:
        add_error(ctx, "FEATURE_ID_MISSING", "manifest feature_id is required", "manifest.json")
        return
    for name, data in ctx.files.items():
        if name == "manifest.json" or not isinstance(data, dict):
            continue
        feature_id = safe_text(data.get("feature_id"))
        if feature_id and feature_id != manifest_feature:
            add_error(ctx, "FEATURE_ID_MISMATCH", f"{name} feature_id {feature_id} differs from manifest {manifest_feature}", name)


def validate_review_state(ctx: HandoffContext) -> None:
    review = ctx.files.get("feature_flow_review_result.v1.json", {})
    status = safe_text(review.get("review_status"))
    if status in BLOCKING_REVIEW_STATUSES:
        add_blocker(ctx, "FEATURE_FLOW_NOT_APPROVED", f"feature flow review_status is {status}", "feature_flow_review_result.v1.json")
    elif status != "APPROVED":
        add_error(ctx, "FEATURE_FLOW_STATUS_INVALID", f"feature flow review_status must be APPROVED, got {status or '<empty>'}", "feature_flow_review_result.v1.json")

    review_items = ctx.files.get("review_items.v1.json", {}).get("items", [])
    if not isinstance(review_items, list):
        add_error(ctx, "REVIEW_ITEMS_INVALID", "review_items.items must be a list", "review_items.v1.json")
        return
    for index, item in enumerate(review_items):
        if not isinstance(item, dict):
            continue
        severity = safe_text(item.get("severity") or item.get("level")).upper()
        item_status = safe_text(item.get("status")).upper()
        allow_downgrade = bool(item.get("allow_downgrade") or item.get("degradable"))
        closed = item_status in {"CLOSED", "RESOLVED", "ACCEPTED", "WAIVED"}
        if severity == "BLOCKER" and not closed and not allow_downgrade:
            add_blocker(ctx, "OPEN_REVIEW_BLOCKER", safe_text(item.get("message") or item.get("title")) or "open review blocker", f"review_items.v1.json#/items/{index}")


def collect_targets(ctx: HandoffContext) -> dict[str, dict[str, Any]]:
    catalog = ctx.files.get("target_name_catalog.v1.json", {})
    targets = catalog.get("targets", [])
    if not isinstance(targets, list):
        add_error(ctx, "TARGET_CATALOG_INVALID", "target_name_catalog.targets must be a list", "target_name_catalog.v1.json")
        return {}
    out: dict[str, dict[str, Any]] = {}
    names: dict[str, str] = {}
    for index, item in enumerate(targets):
        if not isinstance(item, dict):
            continue
        target_id = safe_text(item.get("target_id") or item.get("targetId"))
        target_name = safe_text(item.get("target_name") or item.get("targetName"))
        if not target_id:
            add_error(ctx, "TARGET_ID_MISSING", "target_id is required", f"target_name_catalog.v1.json#/targets/{index}")
            continue
        if target_id in out:
            add_error(ctx, "TARGET_ID_DUPLICATE", f"duplicate target_id: {target_id}", f"target_name_catalog.v1.json#/targets/{index}")
            continue
        if not target_name:
            add_error(ctx, "TARGET_NAME_MISSING", f"target_name is required for {target_id}", f"target_name_catalog.v1.json#/targets/{index}")
        name_key = target_name.strip()
        if name_key:
            names.setdefault(name_key, target_id)
        aliases = item.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                alias_key = safe_text(alias)
                if alias_key:
                    names.setdefault(alias_key, target_id)
        out[target_id] = item
    ctx.files["_target_names"] = {name: target_id for name, target_id in names.items()}
    return out


def validate_cases(ctx: HandoffContext, targets: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cases = ctx.files.get("manual_test_cases.v1.json", {}).get("test_cases", [])
    if not isinstance(cases, list):
        add_error(ctx, "TEST_CASES_INVALID", "manual_test_cases.test_cases must be a list", "manual_test_cases.v1.json")
        return []
    seen: set[str] = set()
    target_names = ctx.files.get("_target_names", {})
    for case_index, case in enumerate(cases):
        if not isinstance(case, dict):
            continue
        case_id = safe_text(case.get("case_id") or case.get("caseId"))
        if not case_id:
            add_error(ctx, "CASE_ID_MISSING", "case_id is required", f"manual_test_cases.v1.json#/test_cases/{case_index}")
            continue
        if case_id in seen:
            add_error(ctx, "CASE_ID_DUPLICATE", f"duplicate case_id: {case_id}", f"manual_test_cases.v1.json#/test_cases/{case_index}")
        seen.add(case_id)
        steps = case.get("steps", [])
        if not isinstance(steps, list) or not steps:
            add_error(ctx, "CASE_STEPS_MISSING", f"case {case_id} has no steps", f"manual_test_cases.v1.json#/test_cases/{case_index}/steps")
            continue
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            action = normalize_action(step.get("action"))
            target_id = safe_text(step.get("target_id") or step.get("targetId"))
            target_name = safe_text(step.get("target_name") or step.get("targetName"))
            if action in UI_ACTIONS_REQUIRING_TARGET and not target_id and not target_name:
                add_error(ctx, "STEP_TARGET_MISSING", f"case {case_id} step {step_index + 1} action {action} requires target_id or target_name", f"manual_test_cases.v1.json#/test_cases/{case_index}/steps/{step_index}")
            if target_id and target_id not in targets:
                add_error(ctx, "STEP_TARGET_ID_UNKNOWN", f"case {case_id} step {step_index + 1} target_id not found in target catalog: {target_id}", f"manual_test_cases.v1.json#/test_cases/{case_index}/steps/{step_index}")
            if target_name and target_name not in target_names:
                add_error(ctx, "STEP_TARGET_NAME_UNKNOWN", f"case {case_id} step {step_index + 1} target_name not found in target catalog: {target_name}", f"manual_test_cases.v1.json#/test_cases/{case_index}/steps/{step_index}")
    return cases


def collect_state_contract(ctx: HandoffContext) -> dict[str, dict[str, Any]]:
    contract = ctx.files.get("business_state_contract.v1.json", {})
    domains = contract.get("state_domains", [])
    if not domains:
        domains = contract.get("states", [])
    if not isinstance(domains, list):
        add_error(ctx, "BUSINESS_STATE_CONTRACT_INVALID", "business_state_contract state_domains/states must be a list", "business_state_contract.v1.json")
        return {}

    out: dict[str, dict[str, Any]] = {}
    for domain_index, domain in enumerate(domains):
        if not isinstance(domain, dict):
            continue
        domain_id = safe_text(domain.get("domain_id") or domain.get("domain") or domain.get("id"))
        collector = safe_text(domain.get("collector") or domain.get("collector_id") or domain.get("collectorId"))
        state_paths = domain.get("state_paths")
        if state_paths is None:
            state_paths = domain.get("paths")
        if state_paths is None:
            state_paths = domain.get("states")
        if state_paths is None and domain.get("state_path"):
            state_paths = [domain.get("state_path")]
        if not isinstance(state_paths, list):
            state_paths = []
        if not state_paths:
            add_error(ctx, "STATE_PATHS_MISSING", f"state domain {domain_id or domain_index} has no state_paths", f"business_state_contract.v1.json#/state_domains/{domain_index}")
        if not collector:
            add_blocker(ctx, "STATE_COLLECTOR_MISSING", f"state domain {domain_id or domain_index} has no collector", f"business_state_contract.v1.json#/state_domains/{domain_index}")
        elif collector not in SUPPORTED_STATE_COLLECTORS:
            add_blocker(ctx, "STATE_COLLECTOR_UNSUPPORTED", f"collector is not supported by AutoSmoke yet: {collector}", f"business_state_contract.v1.json#/state_domains/{domain_index}")
        for item in state_paths:
            if isinstance(item, dict):
                state_path = safe_text(item.get("state_path") or item.get("path") or item.get("id"))
                merged = dict(domain)
                merged.update(item)
            else:
                state_path = safe_text(item)
                merged = dict(domain)
                merged["state_path"] = state_path
            if not state_path:
                continue
            if state_path in out:
                add_error(ctx, "STATE_PATH_DUPLICATE", f"duplicate state_path: {state_path}", f"business_state_contract.v1.json#/state_domains/{domain_index}")
                continue
            merged["domain_id"] = domain_id
            merged["collector"] = collector
            merged["state_path"] = state_path
            out[state_path] = merged
    ctx.files["_state_contract"] = out
    return out


def collect_business_assertions(ctx: HandoffContext, state_contract: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    payload = ctx.files.get("business_assertions.v1.json", {})
    assertions = payload.get("assertions", [])
    if not isinstance(assertions, list):
        add_error(ctx, "BUSINESS_ASSERTIONS_INVALID", "business_assertions.assertions must be a list", "business_assertions.v1.json")
        return {}
    out: dict[str, dict[str, Any]] = {}
    for index, assertion in enumerate(assertions):
        if not isinstance(assertion, dict):
            continue
        assertion_id = safe_text(assertion.get("assertion_id") or assertion.get("assertionId") or assertion.get("id"))
        if not assertion_id:
            add_error(ctx, "BUSINESS_ASSERTION_ID_MISSING", "assertion_id is required", f"business_assertions.v1.json#/assertions/{index}")
            continue
        if assertion_id in out:
            add_error(ctx, "BUSINESS_ASSERTION_ID_DUPLICATE", f"duplicate assertion_id: {assertion_id}", f"business_assertions.v1.json#/assertions/{index}")
            continue
        state_paths = assertion.get("state_paths")
        if state_paths is None:
            state_paths = assertion.get("state_path")
        if isinstance(state_paths, str):
            state_paths = [state_paths]
        if not isinstance(state_paths, list):
            state_paths = []
        if not state_paths:
            add_error(ctx, "BUSINESS_ASSERTION_STATE_PATH_MISSING", f"assertion {assertion_id} has no state_path/state_paths", f"business_assertions.v1.json#/assertions/{index}")
        for state_path in state_paths:
            sp = safe_text(state_path)
            if sp and sp not in state_contract:
                add_blocker(ctx, "BUSINESS_ASSERTION_STATE_PATH_UNKNOWN", f"assertion {assertion_id} references unknown state_path: {sp}", f"business_assertions.v1.json#/assertions/{index}")
        normalized = dict(assertion)
        normalized["assertion_id"] = assertion_id
        normalized["state_paths"] = [safe_text(x) for x in state_paths if safe_text(x)]
        out[assertion_id] = normalized
    ctx.files["_business_assertions"] = out
    return out


def collect_value_assets(ctx: HandoffContext) -> dict[str, dict[str, Any]]:
    payload = ctx.files.get("value_assets.v1.json", {})
    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        add_error(ctx, "VALUE_ASSETS_INVALID", "value_assets.assets must be a list", "value_assets.v1.json")
        return {}
    out: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(assets):
        if not isinstance(item, dict):
            add_error(ctx, "VALUE_ASSET_INVALID", f"value asset at index {index} must be an object", f"value_assets.v1.json#/assets/{index}")
            continue
        asset_id = safe_text(item.get("asset_id") or item.get("assetId") or item.get("id"))
        if not asset_id:
            add_error(ctx, "VALUE_ASSET_ID_MISSING", "asset_id is required", f"value_assets.v1.json#/assets/{index}")
            continue
        if asset_id in out:
            add_error(ctx, "VALUE_ASSET_ID_DUPLICATE", f"duplicate asset_id: {asset_id}", f"value_assets.v1.json#/assets/{index}")
            continue
        out[asset_id] = item
    ctx.files["_value_assets"] = out
    return out


def collect_external_refs(ctx: HandoffContext) -> dict[str, dict[str, Any]]:
    payload = ctx.files.get("optional_external_refs.v1.json", {})
    refs = payload.get("refs", [])
    if not isinstance(refs, list):
        add_error(ctx, "OPTIONAL_EXTERNAL_REFS_INVALID", "optional_external_refs.refs must be a list", "optional_external_refs.v1.json")
        return {}
    out: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(refs):
        if not isinstance(item, dict):
            add_error(ctx, "OPTIONAL_EXTERNAL_REF_INVALID", f"external ref at index {index} must be an object", f"optional_external_refs.v1.json#/refs/{index}")
            continue
        ref_id = safe_text(item.get("ref_id") or item.get("refId") or item.get("id"))
        if not ref_id:
            add_error(ctx, "OPTIONAL_EXTERNAL_REF_ID_MISSING", "ref_id is required", f"optional_external_refs.v1.json#/refs/{index}")
            continue
        if ref_id in out:
            add_error(ctx, "OPTIONAL_EXTERNAL_REF_ID_DUPLICATE", f"duplicate ref_id: {ref_id}", f"optional_external_refs.v1.json#/refs/{index}")
            continue
        out[ref_id] = item
        status = safe_text(item.get("status") or item.get("availability")).lower()
        if item.get("required") is True and status not in {"", "ok", "ready", "available", "pass"}:
            add_blocker(ctx, "REQUIRED_EXTERNAL_REF_NOT_READY", f"required external ref is not ready: {ref_id}", f"optional_external_refs.v1.json#/refs/{index}")
    ctx.files["_optional_external_refs"] = out
    return out


def validate_assertion_refs(ctx: HandoffContext, cases: list[dict[str, Any]], assertions: dict[str, dict[str, Any]]) -> None:
    if "business_assertions.v1.json" not in ctx.files:
        return
    for case_index, case in enumerate(cases):
        if not isinstance(case, dict):
            continue
        case_id = safe_text(case.get("case_id") or case.get("caseId"))
        for step_index, step in enumerate(case.get("steps", []) if isinstance(case.get("steps"), list) else []):
            if not isinstance(step, dict):
                continue
            refs = step.get("assertion_refs", [])
            if isinstance(refs, str):
                refs = [refs]
            if not isinstance(refs, list):
                add_error(ctx, "ASSERTION_REFS_INVALID", f"case {case_id} step {step_index + 1} assertion_refs must be a list", f"manual_test_cases.v1.json#/test_cases/{case_index}/steps/{step_index}")
                continue
            for ref in refs:
                ref_id = safe_text(ref)
                if ref_id and ref_id not in assertions:
                    add_blocker(ctx, "ASSERTION_REF_UNKNOWN", f"case {case_id} step {step_index + 1} references unknown assertion: {ref_id}", f"manual_test_cases.v1.json#/test_cases/{case_index}/steps/{step_index}")


def validate_business_files(ctx: HandoffContext) -> tuple[str, str]:
    present = {name for name in BUSINESS_FILES if name in ctx.files}
    if {"business_state_contract.v1.json", "business_assertions.v1.json"}.issubset(present):
        state_contract = collect_state_contract(ctx)
        value_assets = collect_value_assets(ctx) if "value_assets.v1.json" in ctx.files else {}
        external_refs = collect_external_refs(ctx) if "optional_external_refs.v1.json" in ctx.files else {}
        assertions = collect_business_assertions(ctx, state_contract)
        for assertion_id, assertion in assertions.items():
            asset_id = safe_text(assertion.get("expected_asset_id") or assertion.get("value_asset_id") or assertion.get("asset_id"))
            if asset_id and asset_id not in value_assets:
                add_blocker(ctx, "BUSINESS_ASSERTION_VALUE_ASSET_UNKNOWN", f"assertion {assertion_id} references unknown value asset: {asset_id}", "business_assertions.v1.json")
            ref_ids = assertion.get("external_ref_ids") or assertion.get("external_refs") or assertion.get("externalRefIds") or []
            if isinstance(ref_ids, str):
                ref_ids = [ref_ids]
            if isinstance(ref_ids, list):
                for ref_id_raw in ref_ids:
                    ref_id = safe_text(ref_id_raw)
                    if ref_id and ref_id not in external_refs:
                        add_blocker(ctx, "BUSINESS_ASSERTION_EXTERNAL_REF_UNKNOWN", f"assertion {assertion_id} references unknown external ref: {ref_id}", "business_assertions.v1.json")
        cases = ctx.files.get("manual_test_cases.v1.json", {}).get("test_cases", [])
        validate_assertion_refs(ctx, cases if isinstance(cases, list) else [], assertions)
        missing_optional = BUSINESS_FILES - present
        for name in sorted(missing_optional):
            add_warning(ctx, "BUSINESS_OPTIONAL_FILE_MISSING", f"{name} is missing; related business assertions may be downgraded", name)
        return "READY_UI_AND_BUSINESS", "UI_AND_BUSINESS"
    if present:
        missing = BUSINESS_FILES - present
        for name in sorted(missing):
            add_warning(ctx, "BUSINESS_PACKAGE_INCOMPLETE", f"{name} is missing; package is admitted as UI_ONLY", name)
        return "PASS_WITH_GAP", "UI_ONLY"
    add_warning(ctx, "BUSINESS_ASSERTION_NOT_PROVIDED", "business state/assertion files are not provided; package is admitted as UI_ONLY")
    return "READY_UI_ONLY", "UI_ONLY"


def validate_package(package_dir: Path) -> dict[str, Any]:
    ctx = load_package(package_dir)
    if ctx.errors:
        status, automation_level = "BLOCKED", "UNKNOWN"
    else:
        validate_required_files(ctx)
        validate_schema_versions(ctx)
        validate_feature_id_consistency(ctx)
        validate_review_state(ctx)
        targets = collect_targets(ctx)
        cases = validate_cases(ctx, targets)
        status, automation_level = validate_business_files(ctx)
        if ctx.errors or ctx.blockers:
            status = "BLOCKED"
            automation_level = "UNKNOWN"

    targets = ctx.files.get("target_name_catalog.v1.json", {}).get("targets", [])
    cases = ctx.files.get("manual_test_cases.v1.json", {}).get("test_cases", [])
    assertions = ctx.files.get("business_assertions.v1.json", {}).get("assertions", [])
    state_contract = ctx.files.get("_state_contract", {})
    pages = ctx.files.get("page_flow_catalog.v1.json", {}).get("pages", [])
    report = {
        "schema_version": "autosmoke_handoff_validation_report.v1",
        "package_id": ctx.package_id,
        "feature_id": ctx.feature_id,
        "status": status,
        "automation_level": automation_level,
        "errors": [item.to_dict() for item in ctx.errors],
        "warnings": [item.to_dict() for item in ctx.warnings],
        "blockers": [item.to_dict() for item in ctx.blockers],
        "summary": {
            "case_count": len(cases) if isinstance(cases, list) else 0,
            "target_count": len(targets) if isinstance(targets, list) else 0,
            "page_count": len(pages) if isinstance(pages, list) else 0,
            "business_state_count": len(state_contract) if isinstance(state_contract, dict) else 0,
            "business_assertion_count": len(assertions) if isinstance(assertions, list) else 0,
        },
        "validated_at": now_text(),
    }
    return report


def normalize_action(value: Any) -> str:
    text = safe_text(value).lower()
    aliases = {
        "点击": "click",
        "tap": "click",
        "等待": "wait",
        "返回": "back",
        "断言可见": "assert_visible",
        "断言存在": "assert_exists",
        "输入": "input",
    }
    return aliases.get(text, text or "unknown")


def semantic_candidate_for_target(target: dict[str, Any]) -> dict[str, Any]:
    target_name = safe_text(target.get("target_name") or target.get("targetName"))
    page_hint = safe_text(target.get("page_id") or target.get("page_name") or target.get("pageHint"))
    role = safe_text(target.get("role"))
    element_type = safe_text(target.get("elementType") or target.get("target_type"))
    if not target_name:
        return {}
    sys.path.insert(0, str(ROOT))
    try:
        from 元数据.semantic_correction import parse_chinese_semantic
    except Exception:
        module_path = ROOT / "\u5143\u6570\u636e" / "semantic_correction.py"
        import importlib.util

        spec = importlib.util.spec_from_file_location("semantic_correction_mod", module_path)
        if spec is None or spec.loader is None:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        parse_chinese_semantic = mod.parse_chinese_semantic

    parsed = parse_chinese_semantic(
        target_name,
        context={
            "pageId": page_hint,
            "role": role,
            "elementType": element_type,
        },
        dictionary_path=str(SEMANTIC_DICTIONARY),
    )
    if not isinstance(parsed, dict):
        return {}
    semantic_id = safe_text(parsed.get("semanticId"))
    test_id = safe_text(parsed.get("testId"))
    if semantic_id and not productized_semantic_id(semantic_id):
        semantic_id = ""
    if test_id and not productized_semantic_id(test_id):
        test_id = semantic_id
    parsed["semanticId"] = semantic_id
    parsed["testId"] = test_id or semantic_id
    return parsed


def semantic_fallback_from_handoff(target: dict[str, Any], feature_id: str, parsed: dict[str, Any] | None = None) -> dict[str, str]:
    parsed = parsed if isinstance(parsed, dict) else {}
    domain = slug(feature_id, "ui")
    target_id = safe_text(target.get("target_id") or target.get("targetId"))
    role = slug(target.get("role"), "")
    element_type = safe_text(target.get("elementType") or target.get("target_type"))
    action_roles = target.get("action_roles", [])
    if not role and isinstance(action_roles, list) and action_roles:
        role = slug(action_roles[0], "")
    if not role:
        role = slug(parsed.get("role"), "target")

    tokens = [part for part in re.split(r"[^A-Za-z0-9]+", target_id.lower()) if part]
    ignored = {"tgt", "target", domain, role}
    object_tokens = [part for part in tokens if part not in ignored]
    object_id = "_".join(object_tokens) or role or "target"

    type_suffix = "target"
    role_lower = role.lower()
    if role_lower in {"tab", "button", "back", "close", "confirm", "cancel", "claim", "use", "add"}:
        type_suffix = "button"
    elif role_lower in {"title", "label", "text"} or element_type.lower() == "text":
        type_suffix = "text"
    elif element_type.lower() == "icon":
        type_suffix = "icon"
    elif element_type.lower() == "reddot":
        type_suffix = "red_dot"
    elif element_type:
        type_suffix = slug(element_type, "target")

    if object_id == role:
        semantic_id = f"{domain}.{object_id}.{type_suffix}"
    elif role == type_suffix:
        semantic_id = f"{domain}.{object_id}.{type_suffix}"
    else:
        semantic_id = f"{domain}.{object_id}.{role}.{type_suffix}"
    semantic_id = re.sub(r"\.+", ".", semantic_id).strip(".")
    return {
        "semanticId": semantic_id,
        "testId": semantic_id,
        "reason": "handoff_feature_target_id_fallback",
    }


def feed_semantic_pending_from_candidates(candidates: list[dict[str, Any]], package_id: str) -> dict[str, Any]:
    updates = []
    pending = read_json(SEMANTIC_PENDING)[0] if SEMANTIC_PENDING.exists() else None
    if not isinstance(pending, dict):
        pending = {"schema_version": "semantic_dictionary_pending.v1", "objects": {}, "updated_at": now_text()}
    objects = pending.setdefault("objects", {})
    if not isinstance(objects, dict):
        objects = {}
        pending["objects"] = objects

    for candidate in candidates:
        semantic = candidate.get("semanticCandidate")
        if not isinstance(semantic, dict):
            continue
        warnings = semantic.get("warnings", [])
        if not isinstance(warnings, list):
            warnings = []
        if "object_from_input_fallback" not in warnings and "object_auto_translated" not in warnings and "tab_button_rule" not in warnings:
            continue
        evidence = semantic.get("parseEvidence", {}) if isinstance(semantic.get("parseEvidence"), dict) else {}
        obj = evidence.get("object", {}) if isinstance(evidence.get("object"), dict) else {}
        object_name = safe_text(obj.get("name"))
        object_id = safe_text(obj.get("id"))
        if not object_name or not object_id or object_id.startswith("custom_"):
            continue
        existing = objects.get(object_name)
        if isinstance(existing, dict) and safe_text(existing.get("id")) == object_id:
            continue
        objects[object_name] = {
            "id": object_id,
            "name": object_name,
            "keywords": sorted(set([object_name, safe_text(candidate.get("targetName"))]) - {""}),
            "source": "qa_reader_handoff_targetName",
            "packageId": package_id,
            "targetId": safe_text(candidate.get("targetId")),
            "fedAt": now_text(),
        }
        updates.append({"objectName": object_name, "objectId": object_id, "targetId": safe_text(candidate.get("targetId"))})

    if updates:
        pending["updated_at"] = now_text()
        write_json(SEMANTIC_PENDING, pending)
    return {"updated": len(updates), "pendingPath": str(SEMANTIC_PENDING), "updates": updates}


def convert_cases(package_dir: Path) -> list[dict[str, Any]]:
    ctx = load_package(package_dir)
    package_id = ctx.package_id
    cases = ctx.files.get("manual_test_cases.v1.json", {}).get("test_cases", [])
    target_catalog = collect_targets(ctx)
    target_names = ctx.files.get("_target_names", {})
    converted: list[dict[str, Any]] = []
    if not isinstance(cases, list):
        return converted
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = safe_text(case.get("case_id") or case.get("caseId"))
        steps_out = []
        for order, step in enumerate(case.get("steps", []) if isinstance(case.get("steps"), list) else [], start=1):
            if not isinstance(step, dict):
                continue
            target_id = safe_text(step.get("target_id") or step.get("targetId"))
            target_name = safe_text(step.get("target_name") or step.get("targetName"))
            if not target_id and target_name:
                target_id = safe_text(target_names.get(target_name))
            target = target_catalog.get(target_id, {}) if target_id else {}
            action = normalize_action(step.get("action"))
            value = safe_text(step.get("value") or step.get("expected"))
            converted_step = {
                "step_order": int(step.get("step_order") or step.get("order") or order),
                "action": action,
                "target": target_id or target_name,
                "target_id": target_id,
                "target_name": target_name or safe_text(target.get("target_name") or target.get("targetName")),
                "page_name": safe_text(step.get("page_name") or target.get("page_name") or target.get("pageHint")),
                "page_id": safe_text(step.get("page_id") or target.get("page_id") or target.get("pageHint")),
                "value": value,
                "timeout": int(step.get("timeout") or 10),
                "source_node_ids": step.get("source_node_ids", []) if isinstance(step.get("source_node_ids", []), list) else [],
                "assertion_refs": step.get("assertion_refs", []) if isinstance(step.get("assertion_refs", []), list) else [],
                "raw": step,
            }
            steps_out.append(converted_step)
        converted.append(
            {
                "case_id": case_id,
                "name": safe_text(case.get("name") or case.get("title")) or case_id,
                "description": safe_text(case.get("description")),
                "automation_level": safe_text(case.get("automation_level")) or "UI_ONLY",
                "source": "qa_reader_handoff",
                "source_package": package_id,
                "steps": steps_out,
                "result": None,
                "error_message": "",
            }
        )
    return converted


def convert_targets(package_dir: Path) -> list[dict[str, Any]]:
    ctx = load_package(package_dir)
    package_id = ctx.package_id
    catalog = ctx.files.get("target_name_catalog.v1.json", {})
    targets = catalog.get("targets", [])
    if not isinstance(targets, list):
        return []
    source_cases = {}
    for case in ctx.files.get("manual_test_cases.v1.json", {}).get("test_cases", []):
        if not isinstance(case, dict):
            continue
        case_id = safe_text(case.get("case_id") or case.get("caseId"))
        for step in case.get("steps", []) if isinstance(case.get("steps"), list) else []:
            if not isinstance(step, dict):
                continue
            target_id = safe_text(step.get("target_id") or step.get("targetId"))
            target_name = safe_text(step.get("target_name") or step.get("targetName"))
            key = target_id or target_name
            if key and case_id:
                source_cases.setdefault(key, set()).add(case_id)
    out: list[dict[str, Any]] = []
    for item in targets:
        if not isinstance(item, dict):
            continue
        target_id = safe_text(item.get("target_id") or item.get("targetId"))
        target_name = safe_text(item.get("target_name") or item.get("targetName"))
        key_cases = sorted(source_cases.get(target_id, set()) | source_cases.get(target_name, set()))
        task = {
            "targetId": target_id or f"{slug(package_id)}.{slug(target_name)}",
            "targetName": target_name or target_id,
            "aliases": item.get("aliases", []) if isinstance(item.get("aliases", []), list) else [],
            "pageHint": safe_text(item.get("page_id") or item.get("page_name") or item.get("pageHint")),
            "role": safe_text(item.get("role")),
            "elementType": safe_text(item.get("elementType") or item.get("target_type")),
            "interactionType": safe_text(item.get("interactionType")),
            "sourceCases": key_cases,
            "priority": safe_text(item.get("priority")) or "P1",
            "expectedBehavior": safe_text(item.get("expected_behavior") or item.get("expectedBehavior")),
            "status": "pending_match",
            "source": "qa_reader_handoff",
            "handoffPackageId": package_id,
            "handoffFeatureId": safe_text(ctx.manifest.get("feature_id")),
            "handoffTargetId": target_id,
        }
        semantic_candidate = semantic_candidate_for_target(item)
        if semantic_candidate:
            semantic_id = safe_text(semantic_candidate.get("semanticId"))
            test_id = safe_text(semantic_candidate.get("testId"))
            used_handoff_fallback = False
            if not semantic_id or generic_semantic_id(semantic_id):
                fallback = semantic_fallback_from_handoff(item, safe_text(ctx.manifest.get("feature_id")), semantic_candidate)
                semantic_id = fallback["semanticId"]
                test_id = fallback["testId"]
                used_handoff_fallback = True
                warnings = semantic_candidate.get("warnings", [])
                if not isinstance(warnings, list):
                    warnings = []
                semantic_candidate["warnings"] = warnings + [fallback["reason"]]
                semantic_candidate["semanticId"] = semantic_id
                semantic_candidate["testId"] = test_id
                semantic_candidate["displayName"] = target_name or semantic_candidate.get("displayName")
            if semantic_id:
                task["semanticId"] = semantic_id
                task["testId"] = test_id or semantic_id
            if used_handoff_fallback and target_name:
                task["displayName"] = target_name
            elif semantic_candidate.get("displayName"):
                task["displayName"] = semantic_candidate.get("displayName")
            if semantic_candidate.get("pageId") and not task["pageHint"]:
                task["pageHint"] = semantic_candidate.get("pageId")
            if semantic_candidate.get("role") and not task["role"]:
                task["role"] = semantic_candidate.get("role")
            if semantic_candidate.get("elementType") and not task["elementType"]:
                task["elementType"] = semantic_candidate.get("elementType")
            task["semanticCandidate"] = semantic_candidate
        out.append(task)
    return out


def business_plan_from_package(package_dir: Path) -> dict[str, Any]:
    ctx = load_package(package_dir)
    state_contract = collect_state_contract(ctx) if "business_state_contract.v1.json" in ctx.files else {}
    value_assets = collect_value_assets(ctx) if "value_assets.v1.json" in ctx.files else {}
    external_refs = collect_external_refs(ctx) if "optional_external_refs.v1.json" in ctx.files else {}
    assertions = collect_business_assertions(ctx, state_contract) if "business_assertions.v1.json" in ctx.files else {}
    collection_plan = []
    for state_path, item in sorted(state_contract.items()):
        plan_item = {
            "state_path": state_path,
            "domain_id": safe_text(item.get("domain_id")),
            "collector": safe_text(item.get("collector")),
            "collection_timing": item.get("collection_timing") or ["before", "after"],
            "status": "READY" if safe_text(item.get("collector")) in SUPPORTED_STATE_COLLECTORS else "BLOCKED",
        }
        for key in ("selector", "text_hint", "target_id", "target_name", "value_type", "description", "before_path", "after_path", "diff_threshold"):
            if item.get(key) not in (None, "", [], {}):
                plan_item[key] = item.get(key)
        collection_plan.append(plan_item)
    assertion_plan = []
    for assertion_id, item in sorted(assertions.items()):
        state_paths = item.get("state_paths", [])
        asset_id = safe_text(item.get("expected_asset_id") or item.get("value_asset_id") or item.get("asset_id"))
        ref_ids = item.get("external_ref_ids") or item.get("external_refs") or item.get("externalRefIds") or []
        if isinstance(ref_ids, str):
            ref_ids = [ref_ids]
        if not isinstance(ref_ids, list):
            ref_ids = []
        missing_asset = bool(asset_id and asset_id not in value_assets)
        missing_refs = [safe_text(ref_id) for ref_id in ref_ids if safe_text(ref_id) and safe_text(ref_id) not in external_refs]
        plan_item = {
            "assertion_id": assertion_id,
            "state_paths": state_paths,
            "operator": safe_text(item.get("operator") or item.get("type") or item.get("check")),
            "expected": item.get("expected"),
            "expected_asset_id": asset_id,
            "external_ref_ids": [safe_text(ref_id) for ref_id in ref_ids if safe_text(ref_id)],
            "status": "READY" if state_paths and all(sp in state_contract for sp in state_paths) and not missing_asset and not missing_refs else "BLOCKED",
            "source": item,
        }
        if asset_id and asset_id in value_assets:
            plan_item["expected_from_asset"] = value_assets[asset_id]
        if missing_asset:
            plan_item["blocker"] = "value_asset_not_found"
        if missing_refs:
            plan_item["blocker"] = "external_ref_not_found"
            plan_item["missing_external_refs"] = missing_refs
        assertion_plan.append(plan_item)
    return {
        "state_contract": state_contract,
        "assertions": assertions,
        "value_assets": value_assets,
        "optional_external_refs": external_refs,
        "state_collection_plan": collection_plan,
        "business_assertion_plan": assertion_plan,
        "source_trace": ctx.files.get("source_trace.v1.json", {}),
    }


def _hint_to_navigation_action(hint: str, targets: list[dict[str, Any]], action_kind: str) -> dict[str, Any]:
    hint_text = safe_text(hint)
    if not hint_text:
        return {"status": "NEEDS_RULE", "action_kind": action_kind, "hint": ""}
    lowered = hint_text.lower()
    if "返回" in hint_text or "back" in lowered:
        return {"status": "READY_ACTION", "action_kind": action_kind, "action": "back", "hint": hint_text, "step_text": "返回"}
    if "等待" in hint_text or "wait" in lowered:
        return {"status": "READY_ACTION", "action_kind": action_kind, "action": "wait", "hint": hint_text, "step_text": "等待 2 秒"}
    click_like = any(token in hint_text for token in ("点击", "点选", "进入", "打开")) or "click" in lowered
    if click_like:
        for target in targets:
            names = [safe_text(target.get("targetName")), safe_text(target.get("displayName"))]
            aliases = target.get("aliases", []) if isinstance(target.get("aliases"), list) else []
            names.extend(safe_text(x) for x in aliases)
            if any(name and name in hint_text for name in names):
                test_id = safe_text(target.get("testId") or target.get("semanticId"))
                return {
                    "status": "READY_ACTION" if test_id else "NEEDS_BINDING",
                    "action_kind": action_kind,
                    "action": "click",
                    "hint": hint_text,
                    "target_id": safe_text(target.get("targetId")),
                    "target_name": safe_text(target.get("targetName")),
                    "test_id": test_id,
                    "step_text": f'点击 testId("{test_id}")' if test_id else "",
                }
    return {"status": "MANUAL_REQUIRED", "action_kind": action_kind, "action": "manual", "hint": hint_text}


def page_flow_plan_from_package(package_dir: Path) -> dict[str, Any]:
    ctx = load_package(package_dir)
    payload = ctx.files.get("page_flow_catalog.v1.json", {})
    pages = payload.get("pages", []) if isinstance(payload.get("pages"), list) else []
    targets = convert_targets(package_dir)
    out = []
    for item in pages:
        if not isinstance(item, dict):
            continue
        page_id = safe_text(item.get("page_id") or item.get("pageId"))
        if not page_id:
            continue
        entry_hint = safe_text(item.get("entry_hint") or item.get("entryHint"))
        back_hint = safe_text(item.get("back_hint") or item.get("backHint") or item.get("return_hint") or item.get("returnHint"))
        recovery_hint = safe_text(item.get("recovery_hint") or item.get("recoveryHint"))
        entry_action = _hint_to_navigation_action(entry_hint, targets, "entry")
        back_action = _hint_to_navigation_action(back_hint, targets, "back")
        recovery_action = _hint_to_navigation_action(recovery_hint, targets, "recovery")
        out.append({
            "page_id": page_id,
            "page_name": safe_text(item.get("page_name") or item.get("pageName")),
            "entry_hint": entry_hint,
            "back_hint": back_hint,
            "recovery_hint": recovery_hint,
            "entry_status": entry_action.get("status"),
            "back_status": back_action.get("status"),
            "recovery_status": recovery_action.get("status"),
            "entry_action": entry_action,
            "back_action": back_action,
            "recovery_action": recovery_action,
            "source": item,
        })
    return {
        "schema_version": "autosmoke_page_flow_execution_plan.v1",
        "pages": out,
        "unresolved_pages": [p["page_id"] for p in out if p["entry_status"] in {"NEEDS_RULE", "MANUAL_REQUIRED", "NEEDS_BINDING"}],
    }


def test_data_plan_from_package(package_dir: Path) -> dict[str, Any]:
    ctx = load_package(package_dir)
    payload = ctx.files.get("test_data_profile.v1.json", {})
    profiles = payload.get("profiles", []) if isinstance(payload.get("profiles"), list) else []
    preconditions = payload.get("preconditions", []) if isinstance(payload.get("preconditions"), list) else []
    profile_plan = []
    for item in profiles:
        if not isinstance(item, dict):
            continue
        profile_plan.append({
            "profile_id": safe_text(item.get("profile_id") or item.get("profileId") or item.get("id")) or "default",
            "description": safe_text(item.get("description")),
            "status": "READY_HINT",
            "source": item,
        })
    precondition_plan = []
    for index, item in enumerate(preconditions):
        if not isinstance(item, dict):
            precondition_plan.append({"precondition_id": f"precondition_{index + 1}", "status": "BLOCKED", "reason": "invalid_precondition"})
            continue
        check_type = safe_text(item.get("type") or item.get("check_type") or item.get("checkType") or "manual")
        precondition_plan.append({
            "precondition_id": safe_text(item.get("precondition_id") or item.get("preconditionId") or item.get("id")) or f"precondition_{index + 1}",
            "type": check_type,
            "description": safe_text(item.get("description")),
            "status": "READY_HINT" if check_type in {"manual", "account_state", "resource", "feature_flag"} else "NEEDS_ADAPTER",
            "source": item,
        })
    return {
        "schema_version": "autosmoke_test_data_prepare_plan.v1",
        "profiles": profile_plan,
        "preconditions": precondition_plan,
        "unresolved_preconditions": [p["precondition_id"] for p in precondition_plan if p["status"] == "NEEDS_ADAPTER"],
    }


def build_execution_plan(
    package_id: str,
    validation: dict[str, Any],
    cases: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    business_plan: dict[str, Any] | None = None,
    page_flow_plan: dict[str, Any] | None = None,
    test_data_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    business_plan = business_plan if isinstance(business_plan, dict) else {}
    page_flow_plan = page_flow_plan if isinstance(page_flow_plan, dict) else {}
    test_data_plan = test_data_plan if isinstance(test_data_plan, dict) else {}
    target_by_id = {safe_text(t.get("targetId")): t for t in targets if isinstance(t, dict)}
    assertion_by_id = business_plan.get("assertions", {}) if isinstance(business_plan.get("assertions"), dict) else {}
    used_assertions: set[str] = set()
    planned_cases = []
    unresolved_targets: set[str] = set()
    unresolved_assertions: set[str] = set()
    for case in cases:
        steps = []
        case_unresolved: set[str] = set()
        for step in case.get("steps", []) if isinstance(case.get("steps"), list) else []:
            target_id = safe_text(step.get("target_id"))
            target = target_by_id.get(target_id, {})
            semantic_id = safe_text(target.get("semanticId") or target.get("testId"))
            binding_required = bool(target_id and not semantic_id)
            if binding_required:
                unresolved_targets.add(target_id)
                case_unresolved.add(target_id)
            assertion_refs = step.get("assertion_refs", [])
            if not isinstance(assertion_refs, list):
                assertion_refs = []
            step_assertions = []
            for ref in assertion_refs:
                ref_id = safe_text(ref)
                if not ref_id:
                    continue
                used_assertions.add(ref_id)
                assertion = assertion_by_id.get(ref_id)
                if not isinstance(assertion, dict):
                    unresolved_assertions.add(ref_id)
                    case_unresolved.add(ref_id)
                    step_assertions.append({"assertion_id": ref_id, "status": "BLOCKED", "reason": "assertion_not_found"})
                else:
                    step_assertions.append({"assertion_id": ref_id, "status": "READY", "state_paths": assertion.get("state_paths", [])})
            steps.append(
                {
                    "step_order": step.get("step_order"),
                    "action": step.get("action"),
                    "target_id": target_id,
                    "target_name": step.get("target_name"),
                    "semantic_id": semantic_id,
                    "test_id": safe_text(target.get("testId")) or semantic_id,
                    "page_hint": step.get("page_id") or step.get("page_name"),
                    "value": step.get("value"),
                    "binding_required": binding_required,
                    "assertion_refs": assertion_refs,
                    "business_assertions": step_assertions,
                    "source_node_ids": step.get("source_node_ids", []),
                }
            )
        planned_cases.append(
            {
                "case_id": case.get("case_id"),
                "name": case.get("name"),
                "automation_level": case.get("automation_level") or validation.get("automation_level"),
                "status": "WAITING_DEPENDENCIES" if case_unresolved else "READY_TO_RUN",
                "steps": steps,
            }
        )
    if unresolved_targets:
        plan_status = "WAITING_TARGET_BINDING"
    elif unresolved_assertions:
        plan_status = "WAITING_DEPENDENCIES"
    else:
        plan_status = "READY_TO_RUN"
    return {
        "schema_version": "autosmoke_execution_plan.v1",
        "package_id": package_id,
        "feature_id": validation.get("feature_id"),
        "automation_level": validation.get("automation_level"),
        "admission_status": validation.get("status"),
        "plan_status": plan_status,
        "unresolved_targets": sorted(unresolved_targets),
        "unresolved_assertions": sorted(unresolved_assertions),
        "navigation_plan": page_flow_plan,
        "test_data_prepare_plan": test_data_plan,
        "state_collection_plan": business_plan.get("state_collection_plan", []),
        "business_assertion_plan": business_plan.get("business_assertion_plan", []),
        "value_assets": business_plan.get("value_assets", {}),
        "optional_external_refs": business_plan.get("optional_external_refs", {}),
        "source_trace": business_plan.get("source_trace", {}),
        "unused_business_assertions": sorted(set(assertion_by_id.keys()) - used_assertions),
        "cases": planned_cases,
        "generated_at": now_text(),
    }


def import_package(package_dir: Path, write_queue: bool = True, write_semantic_pending: bool = True) -> dict[str, Any]:
    validation = validate_package(package_dir)
    if validation["status"] not in READY_STATUSES:
        return {"success": False, "validation": validation, "error": "handoff package is not admitted"}

    package_id = validation["package_id"]
    output_dir = IMPORT_ROOT / package_id
    cases = convert_cases(package_dir)
    targets = convert_targets(package_dir)
    business_plan = business_plan_from_package(package_dir)
    page_flow_plan = page_flow_plan_from_package(package_dir)
    test_data_plan = test_data_plan_from_package(package_dir)
    execution_plan = build_execution_plan(
        package_id,
        validation,
        cases,
        targets,
        business_plan=business_plan,
        page_flow_plan=page_flow_plan,
        test_data_plan=test_data_plan,
    )
    semantic_pending = (
        feed_semantic_pending_from_candidates(targets, package_id)
        if write_semantic_pending
        else {"skipped": True, "reason": "semantic pending write disabled"}
    )

    write_json(output_dir / "autosmoke_cases.json", {"schema_version": "autosmoke_cases_from_handoff.v1", "package_id": package_id, "cases": cases})
    write_json(output_dir / "mapping_tasks_from_handoff.json", {"schema_version": "mapping_tasks_from_handoff.v1", "package_id": package_id, "targets": targets})
    write_json(output_dir / "execution_plan.json", execution_plan)

    queue_result: dict[str, Any] = {"skipped": True}
    if write_queue and targets:
        sys.path.insert(0, str(ROOT))
        from 元数据.target_catalog import TargetCatalog

        queue_result = TargetCatalog(metadata_dir=str(METADATA)).import_targets({"targets": targets})

    report = {
        "success": True,
        "schema_version": "autosmoke_handoff_import_report.v1",
        "package_id": package_id,
        "feature_id": validation["feature_id"],
        "validation": validation,
        "outputs": {
            "cases": str((output_dir / "autosmoke_cases.json").relative_to(ROOT)),
            "mapping_tasks": str((output_dir / "mapping_tasks_from_handoff.json").relative_to(ROOT)),
            "execution_plan": str((output_dir / "execution_plan.json").relative_to(ROOT)),
            "queue_import": queue_result,
            "semantic_pending": semantic_pending,
        },
        "summary": {
            "converted_cases": len(cases),
            "converted_targets": len(targets),
            "queue_imported": queue_result.get("imported", 0) if isinstance(queue_result, dict) else 0,
            "semantic_pending_updates": semantic_pending.get("updated", 0),
        },
        "imported_at": now_text(),
    }
    write_json(REPORT_ROOT / f"{package_id}.import_report.json", report)
    return {"success": True, **report}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate/import QA_Reader handoff packages for AutoSmoke.")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate", help="Validate a handoff package.")
    validate_parser.add_argument("package_dir")
    validate_parser.add_argument("--write-report", action="store_true")
    import_parser = sub.add_parser("import", help="Validate and import a handoff package.")
    import_parser.add_argument("package_dir")
    import_parser.add_argument("--no-queue", action="store_true", help="Only write converted outputs; do not import target tasks into mapping_task_queue.")
    args = parser.parse_args()

    package_dir = Path(args.package_dir).resolve()
    if args.command == "validate":
        report = validate_package(package_dir)
        if args.write_report:
            REPORT_ROOT.mkdir(parents=True, exist_ok=True)
            write_json(REPORT_ROOT / f"{report['package_id']}.validation_report.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] in READY_STATUSES else 2

    result = import_package(package_dir, write_queue=not args.no_queue, write_semantic_pending=not args.no_queue)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
