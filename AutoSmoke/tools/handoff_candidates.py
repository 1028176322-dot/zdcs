#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate QA_Reader handoff candidate files from AutoSmoke local data."""

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
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slug(value: str) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", safe_text(value)).lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_") or "target"


def compact_node_name(node: dict[str, Any]) -> str:
    text = safe_text(node.get("text"))
    node_name = safe_text(node.get("nodeName"))
    sprite = safe_text(node.get("spriteName"))
    if text:
        return text
    if node_name:
        return node_name
    if sprite:
        return sprite
    return safe_text(node.get("runtimePath")).split("/")[-1] or "未命名节点"


def infer_role(node: dict[str, Any]) -> str:
    if node.get("isScrollArea"):
        return "scroll_area"
    if node.get("isDragArea"):
        return "drag_area"
    if node.get("isCell"):
        return "item"
    if node.get("isIcon") or node.get("isInteractiveIcon"):
        return "icon"
    if node.get("effectiveClickable") or node.get("clickable") or safe_text(node.get("interactionType")) == "click":
        return "button"
    if safe_text(node.get("text")):
        return "text"
    return "element"


def infer_element_type(role: str) -> str:
    if role in {"button", "icon", "item"}:
        return "Button"
    if role == "text":
        return "Text"
    if role in {"scroll_area", "drag_area"}:
        return "Area"
    return "Element"


def node_is_candidate(node: dict[str, Any]) -> bool:
    if not isinstance(node, dict) or not node.get("visible", True):
        return False
    if node.get("effectiveClickable") or node.get("clickable") or node.get("isInteractiveIcon"):
        return True
    if node.get("isCell") or node.get("isScrollArea") or node.get("isDragArea"):
        return True
    if safe_text(node.get("text")):
        return True
    return False


def generate_target_catalog(runtime_file: Path, feature_id: str = "", page_id: str = "", limit: int = 200) -> dict[str, Any]:
    tree = read_json(runtime_file, {})
    nodes = tree.get("nodes", []) if isinstance(tree.get("nodes"), list) else []
    feature = safe_text(feature_id) or slug(tree.get("sceneId") or tree.get("pageId") or "feature")
    page = safe_text(page_id) or safe_text(tree.get("currentBusinessPageId") or tree.get("pageId") or "")
    seen: set[str] = set()
    targets = []
    for node in nodes:
        if not node_is_candidate(node):
            continue
        name = compact_node_name(node)
        role = infer_role(node)
        base = slug(f"{page}_{name}_{role}")
        target_id = f"TGT_{slug(feature).upper()}_{len(targets) + 1:03d}"
        key = safe_text(node.get("runtimePath")) or base
        if key in seen:
            continue
        seen.add(key)
        targets.append(
            {
                "target_id": target_id,
                "target_name": name,
                "page_id": page,
                "role": role,
                "element_type": infer_element_type(role),
                "priority": "P1" if role in {"button", "item", "icon"} else "P2",
                "candidate_source": "runtime_ui_tree",
                "candidate_confidence": 0.72 if role in {"button", "item", "icon"} else 0.55,
                "evidence": {
                    "runtimePath": safe_text(node.get("runtimePath")),
                    "nodeName": safe_text(node.get("nodeName")),
                    "text": safe_text(node.get("text")),
                    "screenRect": node.get("screenRect", []),
                    "clickTargetNode": safe_text(node.get("clickTargetNode")),
                },
            }
        )
        if len(targets) >= limit:
            break
    return {
        "schema_version": "target_name_catalog.v1",
        "feature_id": feature,
        "generated_by": "AutoSmoke.handoff_candidates",
        "generated_at": now_text(),
        "page_id": page,
        "targets": targets,
    }


def collect_state_paths(contract: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    domains = contract.get("state_domains", []) if isinstance(contract.get("state_domains"), list) else []
    for domain in domains:
        if not isinstance(domain, dict):
            continue
        domain_id = safe_text(domain.get("domain_id"))
        for item in domain.get("state_paths", []) if isinstance(domain.get("state_paths"), list) else []:
            if not isinstance(item, dict):
                continue
            state_path = safe_text(item.get("state_path"))
            if not state_path:
                continue
            row = dict(item)
            row["domain_id"] = domain_id
            row["collector"] = safe_text(domain.get("collector") or item.get("collector"))
            out.append(row)
    return out


def asset_by_state(value_assets: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for item in value_assets.get("assets", []) if isinstance(value_assets.get("assets"), list) else []:
        if not isinstance(item, dict):
            continue
        for key in ("state_path", "statePath"):
            sp = safe_text(item.get(key))
            if sp:
                out[sp] = item
    return out


def generate_business_assertions(contract_file: Path, value_assets_file: Path | None = None, feature_id: str = "") -> dict[str, Any]:
    contract = read_json(contract_file, {})
    value_assets = read_json(value_assets_file, {}) if value_assets_file else {}
    feature = safe_text(feature_id) or safe_text(contract.get("feature_id")) or "feature"
    assets = asset_by_state(value_assets if isinstance(value_assets, dict) else {})
    assertions = []
    for item in collect_state_paths(contract):
        state_path = safe_text(item.get("state_path"))
        asset = assets.get(state_path, {})
        text_hint = safe_text(item.get("text_hint"))
        assertion = {
            "assertion_id": f"ASSERT_{slug(state_path).upper()}",
            "title": f"{state_path} 状态可采集",
            "state_paths": [state_path],
            "operator": "not_empty",
            "expected": True,
            "candidate_source": "business_state_contract",
        }
        if asset:
            assertion["expected_asset_id"] = safe_text(asset.get("asset_id") or asset.get("assetId") or asset.get("id"))
            assertion.pop("expected", None)
            if safe_text(asset.get("expected") or asset.get("value") or asset.get("text")):
                assertion["operator"] = "contains"
        elif text_hint:
            assertion["operator"] = "contains"
            assertion["expected"] = text_hint
        assertions.append(assertion)
    return {
        "schema_version": "business_assertions.v1",
        "feature_id": feature,
        "generated_by": "AutoSmoke.handoff_candidates",
        "generated_at": now_text(),
        "assertions": assertions,
    }


def generate_for_package(package_dir: Path, runtime_file: Path | None = None, limit: int = 200) -> dict[str, Any]:
    manifest = read_json(package_dir / "manifest.json", {})
    package_id = safe_text(manifest.get("package_id")) or package_dir.name
    feature_id = safe_text(manifest.get("feature_id")) or package_id
    out_dir = CANDIDATE_ROOT / package_id
    runtime = runtime_file or DEFAULT_RUNTIME_TREE
    outputs: dict[str, str] = {}
    if runtime.exists():
        catalog = generate_target_catalog(runtime, feature_id=feature_id, limit=limit)
        path = out_dir / "target_name_catalog.candidates.json"
        write_json(path, catalog)
        outputs["target_name_catalog_candidates"] = str(path)
    contract_path = package_dir / "business_state_contract.v1.json"
    if contract_path.exists():
        value_assets_path = package_dir / "value_assets.v1.json"
        assertions = generate_business_assertions(contract_path, value_assets_path if value_assets_path.exists() else None, feature_id=feature_id)
        path = out_dir / "business_assertions.candidates.json"
        write_json(path, assertions)
        outputs["business_assertions_candidates"] = str(path)
    report = {
        "schema_version": "handoff_candidate_generation_report.v1",
        "package_id": package_id,
        "feature_id": feature_id,
        "outputs": outputs,
        "generated_at": now_text(),
    }
    write_json(out_dir / "candidate_generation_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate QA_Reader handoff candidate files.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    target = sub.add_parser("target-catalog")
    target.add_argument("--runtime-file", default=str(DEFAULT_RUNTIME_TREE))
    target.add_argument("--feature-id", default="")
    target.add_argument("--page-id", default="")
    target.add_argument("--limit", type=int, default=200)
    target.add_argument("--output", default="")
    assertion = sub.add_parser("business-assertions")
    assertion.add_argument("--contract", required=True)
    assertion.add_argument("--value-assets", default="")
    assertion.add_argument("--feature-id", default="")
    assertion.add_argument("--output", default="")
    package = sub.add_parser("package")
    package.add_argument("package_dir")
    package.add_argument("--runtime-file", default="")
    package.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    if args.cmd == "target-catalog":
        result = generate_target_catalog(Path(args.runtime_file), args.feature_id, args.page_id, args.limit)
        if args.output:
            write_json(Path(args.output), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "business-assertions":
        result = generate_business_assertions(Path(args.contract), Path(args.value_assets) if args.value_assets else None, args.feature_id)
        if args.output:
            write_json(Path(args.output), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "package":
        result = generate_for_package(Path(args.package_dir), Path(args.runtime_file) if args.runtime_file else None, args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
