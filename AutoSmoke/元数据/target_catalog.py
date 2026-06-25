# -*- coding: utf-8 -*-
"""Target-driven mapping task storage.

This module owns the target task queue used by the Target Workbench. It does
not validate low-level Unity locators; it persists target intent, selected
candidate paths, statuses, and evidence summaries.
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _autosmoke_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _slug(value: str) -> str:
    text = _safe_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", ".", text).strip(".")
    if text:
        return text[:80]
    digest = hashlib.sha1(_safe_text(value).encode("utf-8")).hexdigest()[:10]
    return f"target.{digest}"


_STATUS_RANK = {
    "pending_match": 0,
    "candidate_found": 10,
    "not_applicable": 15,
    "runtime_matched": 20,
    "blocked": 25,
    "modified": 30,
    "highlight_generated": 35,
    "collection_confirmed": 50,
    "visual_confirmed": 45,
    "click_confirmed": 55,
    "case_verified": 65,
    "ignored": 90,
}

_CONFIRMED_STATUSES = {
    "highlight_generated",
    "collection_confirmed",
    "visual_confirmed",
    "click_confirmed",
    "case_verified",
}

_CONFIRMED_MAPPING_FIELDS = {
    "selectedDraftPath",
    "confirmedDraftPath",
    "confirmedTestId",
    "testId",
    "formalRef",
    "evidenceRef",
}


def _path_variants(value: Any) -> set:
    text = _safe_text(value).replace("\\", "/").strip("/")
    if not text:
        return set()
    values = {text}
    if "::" in text:
        tail = text.split("::")[-1].strip("/")
        if tail:
            values.add(tail)
            values.add(tail.replace("::", "/").strip("/"))
    parts = text.split("/")
    if "Root" in parts:
        root_tail = "/".join(parts[parts.index("Root"):]).strip("/")
        if root_tail:
            values.add(root_tail)
            values.add(root_tail.removeprefix("Root/").strip("/"))
    for prefix in ("DeepUI/LayerUI/", "content/"):
        if text.startswith(prefix):
            values.add(text[len(prefix):].strip("/"))
    return {v for v in values if v}


def _identity_keys(task: Dict[str, Any]) -> set:
    if not isinstance(task, dict):
        return set()
    keys = set()
    value = _safe_text(task.get("targetId"))
    if value:
        keys.add(f"id:{value}")
    for key in ("selectedDraftPath", "elementPath", "path", "draftPath"):
        for value in _path_variants(task.get(key)):
            keys.add(f"path:{value}")
    runtime_hint = task.get("runtimeHint")
    if isinstance(runtime_hint, dict):
        for value in _path_variants(runtime_hint.get("runtimePath")):
            keys.add(f"path:{value}")
    return keys


def _runtime_rect_visible_ratio(rect: Any, width: int = 1170, height: int = 2532) -> float:
    if not (isinstance(rect, list) and len(rect) >= 4):
        return 0.0
    try:
        x1, y1, x2, y2 = [float(v) for v in rect[:4]]
    except Exception:
        return 0.0
    if x2 <= x1 or y2 <= y1:
        return 0.0
    area = (x2 - x1) * (y2 - y1)
    ix1 = max(0.0, min(float(width), x1))
    iy1 = max(0.0, min(float(height), y1))
    ix2 = max(0.0, min(float(width), x2))
    iy2 = max(0.0, min(float(height), y2))
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    return max(0.0, min(1.0, ((ix2 - ix1) * (iy2 - iy1)) / max(area, 1.0)))


def _runtime_rect_screen_coverage(rect: Any, width: int = 1170, height: int = 2532) -> float:
    if not (isinstance(rect, list) and len(rect) >= 4):
        return 0.0
    try:
        x1, y1, x2, y2 = [float(v) for v in rect[:4]]
    except Exception:
        return 0.0
    ix1 = max(0.0, min(float(width), x1))
    iy1 = max(0.0, min(float(height), y1))
    ix2 = max(0.0, min(float(width), x2))
    iy2 = max(0.0, min(float(height), y2))
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    return max(0.0, min(1.0, ((ix2 - ix1) * (iy2 - iy1)) / max(float(width * height), 1.0)))


def _runtime_node_is_onscreen(node: Dict[str, Any], width: int = 1170, height: int = 2532) -> bool:
    ratio = _runtime_rect_visible_ratio(node.get("screenRect", []), width=width, height=height)
    return ratio >= 0.15


def _runtime_node_is_debug_overlay(node: Dict[str, Any]) -> bool:
    if not isinstance(node, dict):
        return False
    chunks = [
        node.get("runtimePath"),
        node.get("path"),
        node.get("prefabPath"),
        node.get("prefabNodePath"),
        node.get("pageId"),
        node.get("ownerPageId"),
        node.get("pageName"),
        node.get("nodeName"),
        node.get("displayName"),
        node.get("text"),
        node.get("chineseDescription"),
    ]
    text = " ".join(_safe_text(x) for x in chunks).lower().replace("\\", "/")
    return any(token in text for token in (
        "ui_debuggraphic",
        "graphicdebug",
        "framework/debug",
        "/debug/",
        "debuggraphic",
        "uigmwindow",
        "gmwindow",
        "uiroot2/uigmwindow",
        "/btnshow",
        "btnshow/text",
    ))


def _merge_unique_list(left: Any, right: Any) -> List[Any]:
    out = []
    for seq in (left, right):
        if isinstance(seq, str):
            seq = [seq]
        if not isinstance(seq, list):
            continue
        for item in seq:
            if item not in out:
                out.append(item)
    return out


def _safe_test_id(value: Any) -> str:
    text = _safe_text(value)
    return text.replace("/", ".").replace("\\", ".").strip(".")


def _page_from_mapping_path(value: Any) -> str:
    text = _safe_text(value).replace("\\", "/")
    match = re.search(r"mapping_store/formal/by_page/([^/]+)\.json$", text)
    if match:
        return match.group(1)
    match = re.search(r"mapping_store/evidence/by_testid/([^/]+)/", text)
    if match:
        return match.group(1)
    return ""


def _logical_recommendation_ref(value: Any) -> str:
    text = _safe_text(value).replace("\\", "/")
    if not text:
        return ""
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"recommendation://{digest}"


class TargetCatalog:
    """Read and write mapping target tasks."""

    STATUSES = {
        "pending_match",
        "candidate_found",
        "runtime_matched",
        "highlight_generated",
        "collection_confirmed",
        "visual_confirmed",
        "click_confirmed",
        "case_verified",
        "not_applicable",
        "modified",
        "blocked",
        "ignored",
    }

    def __init__(self, metadata_dir: str = ""):
        root = _autosmoke_root()
        self.metadata_dir = Path(metadata_dir) if metadata_dir else root / "metadata"
        self.queue_path = self.metadata_dir / "mapping_task_queue.json"
        self.catalog_path = self.metadata_dir / "target_name_catalog.json"

    def load(self) -> Dict[str, Any]:
        if not self.queue_path.exists():
            return {
                "schema_version": "mapping_task_queue.v1",
                "generated_at": _now_text(),
                "updated_at": _now_text(),
                "tasks": [],
            }
        try:
            with self.queue_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("mapping_task_queue must be a JSON object")
            data.setdefault("schema_version", "mapping_task_queue.v1")
            data.setdefault("tasks", [])
            return data
        except Exception as exc:
            return {
                "schema_version": "mapping_task_queue.v1",
                "generated_at": _now_text(),
                "updated_at": _now_text(),
                "load_error": str(exc),
                "tasks": [],
            }

    def save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data = data if isinstance(data, dict) else {}
        data.setdefault("schema_version", "mapping_task_queue.v1")
        data.setdefault("generated_at", _now_text())
        data["updated_at"] = _now_text()
        data.setdefault("tasks", [])
        data["tasks"] = [self._normalize_task_refs(t) for t in data.get("tasks", []) if isinstance(t, dict)]
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        with self.queue_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def list_tasks(self, status: str = "", keyword: str = "", limit: int = 200) -> Dict[str, Any]:
        data = self.load()
        tasks = [t for t in data.get("tasks", []) if isinstance(t, dict)]
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        if keyword:
            kw = keyword.lower()
            tasks = [
                t for t in tasks
                if kw in _safe_text(t.get("targetName")).lower()
                or kw in _safe_text(t.get("targetId")).lower()
                or kw in _safe_text(t.get("pageHint")).lower()
            ]
        limit = max(1, min(int(limit or 200), 1000))
        return {
            "success": True,
            "total": len(tasks),
            "returned": min(len(tasks), limit),
            "queuePath": str(self.queue_path),
            "tasks": tasks[:limit],
        }

    def import_targets(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        incoming = payload.get("targets", payload.get("tasks", [])) if isinstance(payload, dict) else []
        if isinstance(incoming, dict):
            incoming = [incoming]
        if not isinstance(incoming, list):
            return {"success": False, "error": "targets must be a list"}

        data = self.load()
        tasks = [t for t in data.get("tasks", []) if isinstance(t, dict)]
        by_id = {t.get("targetId"): t for t in tasks if t.get("targetId")}
        by_identity = {}
        for index, task in enumerate(tasks):
            for key in _identity_keys(task):
                by_identity.setdefault(key, index)
        imported = []
        for raw in incoming:
            if not isinstance(raw, dict):
                continue
            task = self._normalize_task_refs(self.normalize_task(raw))
            old = by_id.get(task["targetId"])
            old_index = tasks.index(old) if old in tasks else None
            if old is None:
                for identity_key in _identity_keys(task):
                    if identity_key in by_identity:
                        old_index = by_identity[identity_key]
                        old = tasks[old_index]
                        break
            if old:
                merged = self._normalize_task_refs(self._merge_runtime_task(old, task))
                if old_index is None:
                    old_index = tasks.index(old)
                tasks[old_index] = merged
                by_id[merged.get("targetId")] = merged
                for key in _identity_keys(merged):
                    by_identity.setdefault(key, old_index)
                imported.append(merged)
            else:
                task = self._normalize_task_refs(task)
                tasks.append(task)
                task_index = len(tasks) - 1
                by_id[task["targetId"]] = task
                for key in _identity_keys(task):
                    by_identity.setdefault(key, task_index)
                imported.append(task)
        data["tasks"] = tasks
        self.save(data)
        self._write_catalog(tasks)
        return {
            "success": True,
            "imported": len(imported),
            "total": len(tasks),
            "queuePath": str(self.queue_path),
            "tasks": imported,
        }

    def _merge_runtime_task(self, old: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        old_status = _safe_text(old.get("status")) or "pending_match"
        new_status = _safe_text(incoming.get("status")) or "pending_match"
        old_rank = _STATUS_RANK.get(old_status, 0)
        new_rank = _STATUS_RANK.get(new_status, 0)

        merged = dict(old)
        for key, value in incoming.items():
            if value in ("", None, [], {}):
                continue
            if key == "targetId" and old.get("targetId"):
                continue
            incoming_assertion = incoming.get("assertion") if isinstance(incoming.get("assertion"), dict) else {}
            allow_assertion_reclassify = incoming_assertion.get("clickRequired") is False
            if key in {"status", "targetName", "displayName", "semanticId", "role", "elementType", "priority", "expectedBehavior", "interactionType", "assertion"} and old_rank > new_rank and not (allow_assertion_reclassify and key in {"role", "elementType", "priority", "expectedBehavior", "interactionType", "assertion"}):
                continue
            if key in {"candidates", "selectedDraftPath", "evidence", "confirmedTestId", "testId", "matchSummary", "blockedReason"} and old_rank > new_rank:
                continue
            merged[key] = value

        merged["sourceCases"] = _merge_unique_list(old.get("sourceCases"), incoming.get("sourceCases"))
        old_evidence = old.get("evidence") if isinstance(old.get("evidence"), dict) else {}
        new_evidence = incoming.get("evidence") if isinstance(incoming.get("evidence"), dict) else {}
        if old_evidence or new_evidence:
            evidence = dict(new_evidence)
            evidence.update(old_evidence)
            merged["evidence"] = evidence
        if old_rank >= new_rank:
            merged["status"] = old_status
        merged["updatedAt"] = _now_text()
        return merged

    def _dedupe_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        key_to_index = {}
        for task in tasks:
            if not isinstance(task, dict):
                continue
            keys = _identity_keys(task)
            hit_index = None
            for key in keys:
                if key in key_to_index:
                    hit_index = key_to_index[key]
                    break
            if hit_index is None:
                key_to_index.update({key: len(out) for key in keys})
                out.append(task)
                continue
            merged = self._merge_runtime_task(out[hit_index], task)
            out[hit_index] = merged
            for key in _identity_keys(merged):
                key_to_index.setdefault(key, hit_index)
        return out

    def _normalize_task_refs(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task = dict(task or {})
        legacy = dict(task.get("legacyPaths") or {})
        for old_key, new_key in (
            ("formalPath", "legacyFormalPath"),
            ("evidencePath", "legacyEvidencePath"),
            ("recommendationPath", "legacyRecommendationPath"),
        ):
            if old_key in legacy:
                legacy.setdefault(new_key, legacy.pop(old_key))

        status = _safe_text(task.get("status"))
        has_confirmed_mapping = bool(
            task.get("confirmedTestId")
            or task.get("testId")
            or status in {"visual_confirmed", "click_confirmed", "case_verified", "manual_confirmed", "collection_confirmed"}
        )
        test_id = _safe_test_id(task.get("confirmedTestId") or task.get("testId"))
        page_id = _safe_text(task.get("pageId") or task.get("pageHint"))

        formal_path = _safe_text(task.pop("formalPath", ""))
        if formal_path:
            legacy.setdefault("legacyFormalPath", formal_path.replace("\\", "/"))
            page_id = page_id or _page_from_mapping_path(formal_path)
        if test_id and page_id and has_confirmed_mapping and not task.get("formalRef"):
            task["formalRef"] = f"formal://{page_id}/{test_id}"

        evidence_path = _safe_text(task.pop("evidencePath", ""))
        if evidence_path:
            legacy.setdefault("legacyEvidencePath", evidence_path.replace("\\", "/"))
            page_id = page_id or _page_from_mapping_path(evidence_path)
        if test_id and has_confirmed_mapping and not task.get("evidenceRef"):
            task["evidenceRef"] = f"EVIDENCE_{test_id}"

        recommendation_path = _safe_text(task.pop("recommendationPath", ""))
        if recommendation_path:
            legacy.setdefault("legacyRecommendationPath", recommendation_path.replace("\\", "/"))
            task.setdefault("recommendationRef", _logical_recommendation_ref(recommendation_path))

        match_summary = task.get("matchSummary")
        if isinstance(match_summary, dict):
            match_summary = dict(match_summary)
            recommendation_path = _safe_text(match_summary.pop("recommendationPath", ""))
            if recommendation_path:
                legacy.setdefault("legacyRecommendationPath", recommendation_path.replace("\\", "/"))
                match_summary.setdefault("recommendationRef", _logical_recommendation_ref(recommendation_path))
            task["matchSummary"] = match_summary

        evidence = task.get("evidence")
        if isinstance(evidence, dict):
            normalized_evidence = {}
            for key, item in evidence.items():
                if not isinstance(item, dict):
                    normalized_evidence[key] = item
                    continue
                ev = dict(item)
                ev_formal_path = _safe_text(ev.pop("formalPath", ""))
                if ev_formal_path:
                    legacy.setdefault("legacyFormalPath", ev_formal_path.replace("\\", "/"))
                    ev.setdefault("formalRef", task.get("formalRef") or (f"formal://{page_id}/{test_id}" if page_id and test_id else ""))
                ev_evidence_path = _safe_text(ev.pop("evidencePath", ""))
                if ev_evidence_path:
                    legacy.setdefault("legacyEvidencePath", ev_evidence_path.replace("\\", "/"))
                    ev.setdefault("evidenceRef", task.get("evidenceRef") or (f"EVIDENCE_{test_id}" if test_id else ""))
                if task.get("formalRef") and not ev.get("formalRef"):
                    ev["formalRef"] = task.get("formalRef")
                if task.get("evidenceRef") and not ev.get("evidenceRef"):
                    ev["evidenceRef"] = task.get("evidenceRef")
                normalized_evidence[key] = ev
            task["evidence"] = normalized_evidence

        if legacy:
            task["legacyPaths"] = legacy
        return task

    def generate_from_runtime_current(self, limit: int = 80) -> Dict[str, Any]:
        runtime_path = self.metadata_dir / "runtime_ui_tree_current.json"
        if not runtime_path.exists():
            return {"success": False, "error": "runtime_tree_missing", "path": str(runtime_path)}
        try:
            with runtime_path.open("r", encoding="utf-8") as f:
                runtime_data = json.load(f)
        except Exception as exc:
            return {"success": False, "error": "runtime_tree_read_failed", "detail": str(exc)}

        nodes = runtime_data.get("nodes", []) if isinstance(runtime_data, dict) else []
        if not isinstance(nodes, list):
            return {"success": False, "error": "runtime_nodes_invalid"}

        design_w = int(runtime_data.get("designWidth") or runtime_data.get("width") or 1170)
        design_h = int(runtime_data.get("designHeight") or runtime_data.get("height") or 2532)
        scope_owner = self._runtime_foreground_owner(nodes, runtime_data)
        clickable_paths = {
            _safe_text(n.get("runtimePath"))
            for n in nodes
            if isinstance(n, dict) and not _runtime_node_is_debug_overlay(n) and (n.get("effectiveClickable") or n.get("clickable"))
        }
        descendant_click_target_paths = {
            _safe_text(n.get("runtimePath"))
            for n in nodes
            if isinstance(n, dict)
            and not _runtime_node_is_debug_overlay(n)
            and _safe_text(n.get("runtimePath"))
            and _safe_text(n.get("clickTargetNode"))
        }
        targets = []
        seen = set()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if _runtime_node_is_debug_overlay(node):
                continue
            if scope_owner and _safe_text(node.get("ownerPageId") or node.get("pageId")) != scope_owner:
                continue
            if not _runtime_node_is_onscreen(node, width=design_w, height=design_h):
                continue
            if not self._runtime_node_is_target(node, clickable_paths, descendant_click_target_paths):
                continue
            task = self._runtime_node_to_task(node, runtime_data)
            key = task.get("targetId")
            if key in seen:
                continue
            seen.add(key)
            targets.append(task)
            if len(targets) >= max(1, min(int(limit or 80), 300)):
                break

        promoted_targets = self._runtime_promoted_click_targets(nodes, runtime_data, scope_owner, seen)
        for task in promoted_targets:
            key = task.get("targetId")
            if key in seen:
                continue
            seen.add(key)
            targets.append(task)
            if len(targets) >= max(1, min(int(limit or 80), 300)):
                break

        for task in self._runtime_dynamic_collection_targets(nodes, runtime_data, scope_owner):
            key = task.get("targetId")
            if key in seen:
                continue
            seen.add(key)
            targets.append(task)

        result = self.import_targets({"targets": targets})
        result["generated"] = len(targets)
        result["runtimePageId"] = runtime_data.get("pageId", "")
        result["currentBusinessPageId"] = runtime_data.get("currentBusinessPageId", "")
        result["scopeOwner"] = scope_owner
        return result

    def _runtime_collection_signature(self, runtime_path: str) -> Dict[str, Any]:
        normalized = _safe_text(runtime_path).replace("\\", "/").strip("/")
        if not normalized:
            return {}
        parts = [p for p in normalized.split("/") if p]
        indexed_at = -1
        index_value = None
        for idx in range(len(parts) - 1, -1, -1):
            part = parts[idx]
            match = re.search(r"^(.*?)(?:[_-]?)(\d+)$", part)
            if match:
                indexed_at = idx
                index_value = int(match.group(2))
                break
        if indexed_at < 0 or index_value is None:
            return {}
        lower_path = normalized.lower()
        collection_tokens = ("scroll", "list", "grid", "item", "cell", "slot", "reward", "prop", "content")
        if not any(token in lower_path for token in collection_tokens):
            return {}
        if "/tab" in lower_path or lower_path.endswith("/tab") or re.search(r"/\d+$", lower_path):
            return {}
        indexed_part = parts[indexed_at]
        pattern_part = re.sub(r"\d+$", "{index}", indexed_part)
        pattern_parts = list(parts)
        pattern_parts[indexed_at] = pattern_part
        container_parts = parts[:indexed_at]
        suffix_parts = parts[indexed_at + 1:]
        if not container_parts or not suffix_parts:
            return {}
        item_name = re.sub(r"[_-]?\d+$", "", indexed_part).strip("_-") or indexed_part
        action_name = suffix_parts[-1]
        pattern = "/".join(pattern_parts)
        key = pattern.lower()
        return {
            "key": key,
            "index": index_value,
            "containerPath": "/".join(container_parts),
            "itemPattern": "/".join([pattern_part] + suffix_parts),
            "pattern": pattern,
            "itemName": item_name,
            "actionName": action_name,
        }

    def _runtime_dynamic_collection_targets(self, nodes: List[Dict[str, Any]], runtime_data: Dict[str, Any], scope_owner: str) -> List[Dict[str, Any]]:
        groups = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if _runtime_node_is_debug_overlay(node):
                continue
            if scope_owner and _safe_text(node.get("ownerPageId") or node.get("pageId")) != scope_owner:
                continue
            runtime_path = _safe_text(node.get("runtimePath")).replace("\\", "/")
            signature = self._runtime_collection_signature(runtime_path)
            if not signature:
                continue
            if (
                _safe_text(signature.get("actionName")).lower() == "add"
                and "topres" in _safe_text(signature.get("containerPath")).replace("\\", "/").lower()
            ):
                continue
            rect = node.get("screenRect", [])
            if not node.get("visible", False) or not isinstance(rect, list) or len(rect) < 4:
                continue
            if not (node.get("effectiveClickable") or node.get("clickable") or _safe_text(node.get("clickTargetNode"))):
                continue
            group = groups.setdefault(signature["key"], {
                "signature": signature,
                "instances": [],
                "pageHint": _safe_text(node.get("ownerPageId") or runtime_data.get("currentBusinessPageId") or node.get("pageId")),
                "elementType": _safe_text(node.get("elementType")) or "Button",
            })
            group["instances"].append({
                "index": signature["index"],
                "runtimePath": runtime_path,
                "screenRect": rect,
            })
        targets = []
        for group in groups.values():
            instances = group["instances"]
            if len(instances) < 2:
                continue
            instances.sort(key=lambda item: item["index"])
            signature = group["signature"]
            page_hint = group["pageHint"] or scope_owner or "current_page"
            page_slug = _slug(page_hint).replace(".", "_") or "current_page"
            item_slug = _slug(signature.get("itemName") or "item").replace(".", "_")
            action_slug = _slug(signature.get("actionName") or "click").replace(".", "_")
            if action_slug in {"clickcontent", "click", "btn", "button"}:
                action_slug = "click_area"
            collection_slug = f"{page_slug}.{item_slug}.{action_slug}"
            collection_id = f"collection.{collection_slug}"
            label = signature.get("itemName") or "item"
            action_label = signature.get("actionName") or "click"
            targets.append({
                "targetId": collection_id,
                "testId": collection_slug,
                "targetName": f"{page_hint} {label} {action_label} dynamic list",
                "displayName": f"{page_hint}-{label} {action_label}",
                "semanticId": collection_slug,
                "sourceCases": ["RUNTIME_CURRENT_PAGE"],
                "pageHint": page_hint,
                "role": "item_click",
                "elementType": group.get("elementType") or "Button",
                "priority": "P1",
                "expectedBehavior": "click visible collection item; scroll list when the requested item is not visible",
                "status": "pending_match",
                "collection": {
                    "type": "dynamic_list",
                    "collectionId": collection_id,
                    "containerPath": signature["containerPath"],
                    "itemPattern": signature["itemPattern"],
                    "semanticPattern": f"{page_slug}.{item_slug}_{{index}}.{action_slug}",
                    "targetNamePattern": f"{page_hint}第{{index}}个{label}{action_label}",
                    "indexBase": 1,
                    "visibleInstanceCount": len(instances),
                    "visibleIndices": [item["index"] for item in instances],
                    "visibleRuntimePaths": [item["runtimePath"] for item in instances],
                    "requiresScrollForMissingIndex": True,
                    "rule": "runtime_repeated_indexed_path",
                },
                "runtimeHint": {
                    "runtimePath": signature["containerPath"],
                    "nodeName": f"{label}Collection",
                    "ownerPageId": page_hint,
                    "pageId": page_hint,
                    "capturedAt": runtime_data.get("capturedAt", ""),
                },
            })
        return targets

    def save_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = payload or {}
        task = self._normalize_task_refs(self.normalize_task(raw))
        data = self.load()
        tasks = [t for t in data.get("tasks", []) if isinstance(t, dict)]
        for index, old in enumerate(tasks):
            if old.get("targetId") == task["targetId"]:
                aliases = {
                    "targetName": {"targetName", "target_name", "name"},
                    "sourceCases": {"sourceCases", "source_cases", "required_by_cases"},
                    "pageHint": {"pageHint", "page_hint", "pageId"},
                    "elementType": {"elementType", "target_type"},
                    "expectedBehavior": {"expectedBehavior", "expected_behavior"},
                    "selectedDraftPath": {"selectedDraftPath", "selected_draft_path"},
                }
                updates = {}
                for key, value in task.items():
                    if key in {"targetId", "createdAt", "updatedAt"}:
                        continue
                    names = aliases.get(key, {key})
                    if any(name in raw for name in names):
                        updates[key] = value
                saved = self.update_task(task["targetId"], updates)
                saved["created"] = False
                return saved
        tasks.append(self._normalize_task_refs(task))
        data["tasks"] = tasks
        self.save(data)
        self._write_catalog(tasks)
        return {"success": True, "task": task, "created": True}

    def get_task(self, target_id: str) -> Dict[str, Any]:
        for task in self.load().get("tasks", []):
            if isinstance(task, dict) and task.get("targetId") == target_id:
                return task
        return {}

    def update_task(self, target_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if not target_id:
            return {"success": False, "error": "targetId is required"}
        requested_updates = self._normalize_task_refs(dict(updates or {}))
        allow_status_regression = bool(requested_updates.pop("allowStatusRegression", False))
        data = self.load()
        tasks = [t for t in data.get("tasks", []) if isinstance(t, dict)]
        for index, task in enumerate(tasks):
            if task.get("targetId") == target_id:
                old_status = _safe_text(task.get("status")) or "pending_match"
                new_status = _safe_text(requested_updates.get("status"))
                guard = {}
                if new_status and new_status not in self.STATUSES:
                    guard = {
                        "blockedStatus": new_status,
                        "reason": "invalid_status",
                        "blockedAt": _now_text(),
                    }
                    requested_updates.pop("status", None)
                    new_status = ""
                elif new_status and not allow_status_regression:
                    old_rank = _STATUS_RANK.get(old_status, 0)
                    new_rank = _STATUS_RANK.get(new_status, 0)
                    if old_status in _CONFIRMED_STATUSES and new_rank < old_rank:
                        guard = {
                            "from": old_status,
                            "to": new_status,
                            "reason": "confirmed_status_regression_blocked",
                            "blockedAt": _now_text(),
                        }
                        requested_updates.pop("status", None)
                        requested_updates["lastTransientStatus"] = new_status
                        if "blockedReason" in requested_updates and new_status in {"blocked", "not_applicable"}:
                            requested_updates["lastTransientBlockedReason"] = requested_updates.pop("blockedReason")
                        for field in _CONFIRMED_MAPPING_FIELDS:
                            requested_updates.pop(field, None)
                if guard:
                    guards = list(task.get("statusGuards") or [])
                    guards.append(guard)
                    requested_updates["statusGuards"] = guards[-20:]
                task.update(requested_updates)
                status = task.get("status")
                if status and status not in self.STATUSES:
                    task["status"] = old_status
                    task["blockedReason"] = f"invalid_status:{status}"
                task["updatedAt"] = _now_text()
                tasks[index] = task
                data["tasks"] = tasks
                self.save(data)
                self._write_catalog(tasks)
                return {"success": True, "task": task}
        return {"success": False, "error": "target_not_found", "targetId": target_id}

    def ignore_task(self, target_id: str, reason: str = "") -> Dict[str, Any]:
        return self.update_task(target_id, {
            "status": "ignored",
            "ignoredReason": reason or "user_ignored",
            "ignoredAt": _now_text(),
            "allowStatusRegression": True,
        })

    def restore_task(self, target_id: str) -> Dict[str, Any]:
        return self.update_task(target_id, {
            "status": "pending_match",
            "blockedReason": "",
            "ignoredReason": "",
            "ignoredAt": "",
            "restoredAt": _now_text(),
            "allowStatusRegression": True,
        })

    def select_candidate(self, target_id: str, draft_path: str) -> Dict[str, Any]:
        task = self.get_task(target_id)
        if not task:
            return {"success": False, "error": "target_not_found", "targetId": target_id}
        if not draft_path:
            return {"success": False, "error": "draftPath is required"}
        candidates = task.get("candidates", [])
        if candidates and not any(c.get("draftPath") == draft_path for c in candidates if isinstance(c, dict)):
            task.setdefault("riskFlags", []).append("selected_candidate_not_in_recommendations")
        return self.update_task(target_id, {
            "selectedDraftPath": draft_path,
            "status": "candidate_found",
            "blockedReason": "",
            "selectedAt": _now_text(),
        })

    def record_evidence(self, target_id: str, key: str, evidence: Dict[str, Any], status: str = "") -> Dict[str, Any]:
        task = self.get_task(target_id)
        if not task:
            return {"success": False, "error": "target_not_found", "targetId": target_id}
        merged = dict(task.get("evidence") or {})
        item = dict(evidence or {})
        item.setdefault("recordedAt", _now_text())
        merged[key] = item
        updates = {"evidence": merged}
        if status:
            updates["status"] = status
        return self.update_task(target_id, updates)

    def normalize_task(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        target_name = _safe_text(raw.get("targetName") or raw.get("target_name") or raw.get("name"))
        target_id = _safe_text(raw.get("targetId") or raw.get("target_id") or raw.get("testId"))
        if not target_id:
            target_id = _slug(target_name or json.dumps(raw, ensure_ascii=False))
        status = _safe_text(raw.get("status")) or "pending_match"
        if status not in self.STATUSES:
            status = "pending_match"
        source_cases = raw.get("sourceCases", raw.get("source_cases", raw.get("required_by_cases", [])))
        if isinstance(source_cases, str):
            source_cases = [x.strip() for x in re.split(r"[,;，；\s]+", source_cases) if x.strip()]
        if not isinstance(source_cases, list):
            source_cases = []
        task = {
            "targetId": target_id,
            "targetName": target_name or target_id,
            "sourceCases": source_cases,
            "pageHint": _safe_text(raw.get("pageHint") or raw.get("page_hint") or raw.get("pageId")),
            "role": _safe_text(raw.get("role")),
            "elementType": _safe_text(raw.get("elementType") or raw.get("target_type")),
            "priority": _safe_text(raw.get("priority")) or "P1",
            "expectedBehavior": _safe_text(raw.get("expectedBehavior") or raw.get("expected_behavior")),
            "status": status,
            "candidates": raw.get("candidates", []) if isinstance(raw.get("candidates", []), list) else [],
            "selectedDraftPath": _safe_text(raw.get("selectedDraftPath") or raw.get("selected_draft_path")),
            "evidence": raw.get("evidence", {}) if isinstance(raw.get("evidence", {}), dict) else {},
            "createdAt": raw.get("createdAt") or _now_text(),
            "updatedAt": _now_text(),
        }
        for key in ("testId", "semanticId", "displayName", "notes", "blockedReason", "collectionRef", "itemIndex", "interactionType"):
            if raw.get(key):
                task[key] = raw.get(key)
        if isinstance(raw.get("collection"), dict):
            task["collection"] = raw.get("collection")
        if isinstance(raw.get("availability"), dict):
            task["availability"] = raw.get("availability")
        if isinstance(raw.get("assertion"), dict):
            task["assertion"] = raw.get("assertion")
        if isinstance(raw.get("runtimeHint"), dict):
            task["runtimeHint"] = raw.get("runtimeHint")
        return task

    def _runtime_node_is_assertion_target(self, node: Dict[str, Any]) -> bool:
        if _runtime_node_is_debug_overlay(node):
            return False
        if not node.get("visible", False):
            return False
        rect = node.get("screenRect", [])
        if not isinstance(rect, list) or len(rect) < 4:
            return False
        x1, y1, x2, y2 = rect[:4]
        if x2 <= x1 + 8 or y2 <= y1 + 8:
            return False
        element_type = _safe_text(node.get("elementType")).lower()
        if element_type in {"popup_mask", "scroll_area", "drag_area", "blank_close_area"}:
            return False
        if _safe_text(node.get("clickTargetNode")):
            return False
        if node.get("eventReceivers"):
            return False
        node_name = _safe_text(node.get("nodeName")).lower()
        if node_name in {"bg", "topbg", "downbg", "view", "content", "scrollbar", "on", "off"}:
            return False
        components = " ".join([_safe_text(x).lower() for x in node.get("components", []) if _safe_text(x)])
        if any(token in components for token in ("text", "image", "sprite", "canvasrenderer")):
            return True
        if _safe_text(node.get("text")) or _safe_text(node.get("spriteName")):
            return True
        return element_type in {"item_cell", "reward_cell", "shop_item_cell"}

    def _runtime_node_is_target(self, node: Dict[str, Any], clickable_paths: set, descendant_click_target_paths: set = None) -> bool:
        if _runtime_node_is_debug_overlay(node):
            return False
        if not node.get("visible", False):
            return False
        if not (node.get("effectiveClickable") or node.get("clickable") or self._runtime_node_is_assertion_target(node)):
            return False
        rect = node.get("screenRect", [])
        if not isinstance(rect, list) or len(rect) < 4:
            return False
        x1, y1, x2, y2 = rect[:4]
        if x2 <= x1 + 4 or y2 <= y1 + 4:
            return False
        element_type = _safe_text(node.get("elementType")).lower()
        if element_type in {"popup_mask", "scroll_area", "drag_area", "blank_close_area"}:
            return False
        runtime_path = _safe_text(node.get("runtimePath"))
        node_name = _safe_text(node.get("nodeName"))
        lower_name = node_name.lower()
        if lower_name in {"quality", "icon", "on", "off"}:
            parent = runtime_path.rsplit("/", 1)[0] if "/" in runtime_path else ""
            if parent in clickable_paths:
                return False
        if lower_name in {"bg", "topbg", "downbg", "view", "content", "scrollbar"}:
            return False
        click_target_node = _safe_text(node.get("clickTargetNode"))
        if not click_target_node and self._runtime_node_is_assertion_target(node):
            return True
        if not click_target_node and descendant_click_target_paths:
            runtime_prefix = runtime_path.rstrip("/") + "/"
            if any(path.startswith(runtime_prefix) for path in descendant_click_target_paths):
                return False
        return True

    def _runtime_promoted_click_targets(self, nodes: List[Dict[str, Any]], runtime_data: Dict[str, Any], scope_owner: str, seen: set) -> List[Dict[str, Any]]:
        by_runtime = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if _runtime_node_is_debug_overlay(node):
                continue
            runtime_path = _safe_text(node.get("runtimePath"))
            if runtime_path:
                by_runtime[runtime_path] = node
        promoted = []
        promoted_paths = set()
        scope_marker = f"/{scope_owner}/" if scope_owner else ""
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if _runtime_node_is_debug_overlay(node):
                continue
            if not node.get("visible", False):
                continue
            click_target = _safe_text(node.get("clickTargetNode"))
            if not click_target:
                continue
            owner = _safe_text(node.get("ownerPageId") or node.get("pageId"))
            if scope_owner and owner != scope_owner and scope_marker not in click_target:
                continue
            target_runtime = click_target.split(scope_marker, 1)[-1] if scope_marker and scope_marker in click_target else click_target
            target_runtime = target_runtime.removeprefix("DeepUI/LayerUI/").strip("/")
            if target_runtime.startswith(scope_owner + "/"):
                target_runtime = target_runtime[len(scope_owner):].strip("/")
            if not target_runtime or target_runtime in promoted_paths:
                continue
            target_node = by_runtime.get(target_runtime)
            if target_node and self._runtime_node_is_target(target_node, set(), set()):
                continue
            node_name = _safe_text(target_runtime.rsplit("/", 1)[-1])
            if not node_name or node_name.lower() in {"on", "off", "icon", "quality"}:
                continue
            promoted_node = dict(node)
            promoted_node["runtimePath"] = target_runtime
            promoted_node["nodeName"] = node_name
            promoted_node["ownerPageId"] = scope_owner or owner
            if node_name.isdigit() or "/Tab/" in target_runtime or "/tab" in target_runtime.lower():
                promoted_node["elementType"] = "tab"
            promoted_paths.add(target_runtime)
            promoted.append(self._runtime_node_to_task(promoted_node, runtime_data))
        return promoted

    def _runtime_foreground_owner(self, nodes: List[Dict[str, Any]], runtime_data: Dict[str, Any]) -> str:
        ignored_tokens = (
            "scen",
            "hud",
            "menuroot",
            "chat",
            "left_",
            "right_",
            "viewport",
            "bg",
        )
        design_w = int(runtime_data.get("designWidth") or runtime_data.get("width") or 1170)
        design_h = int(runtime_data.get("designHeight") or runtime_data.get("height") or 2532)
        owner_scores = {}
        owner_visible_clicks = {}
        owner_screen_coverage = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if _runtime_node_is_debug_overlay(node):
                continue
            if not node.get("visible", False):
                continue
            owner_for_coverage = _safe_text(node.get("ownerPageId") or node.get("pageId"))
            if owner_for_coverage:
                coverage = _runtime_rect_screen_coverage(node.get("screenRect", []), width=design_w, height=design_h)
                if coverage > owner_screen_coverage.get(owner_for_coverage, 0.0):
                    owner_screen_coverage[owner_for_coverage] = coverage
            if not (node.get("effectiveClickable") or node.get("clickable")):
                continue
            owner = _safe_text(node.get("ownerPageId") or node.get("pageId"))
            if not owner:
                continue
            owner_lower = owner.lower()
            runtime_path = _safe_text(node.get("runtimePath"))
            visible_ratio = _runtime_rect_visible_ratio(node.get("screenRect", []), width=design_w, height=design_h)
            if visible_ratio < 0.15:
                continue
            score = 1 + visible_ratio * 10
            if "[ui" in owner_lower or "ui" in owner_lower:
                score += 4
            if "player" in owner_lower or "panel" in owner_lower or "pop" in owner_lower:
                score += 4
            if "overview" in owner_lower:
                score -= 8
            if runtime_path.startswith(("Root/", "Content/", "content/")):
                score += 2
            if any(token in owner_lower for token in ignored_tokens):
                score -= 8
            owner_scores[owner] = owner_scores.get(owner, 0) + score
            owner_visible_clicks[owner] = owner_visible_clicks.get(owner, 0) + 1

        for owner, coverage in owner_screen_coverage.items():
            if coverage >= 0.60 and owner_visible_clicks.get(owner, 0) >= 3:
                owner_lower = owner.lower()
                overlay_bonus = 220 if owner != _safe_text(runtime_data.get("currentBusinessPageId") or runtime_data.get("pageId")) else 120
                if "uimain" == owner_lower.replace("(clone)", "").strip().lower():
                    overlay_bonus = 0
                if "maincityhud" in owner_lower or "scene" in owner_lower:
                    overlay_bonus = 0
                owner_scores[owner] = owner_scores.get(owner, 0) + overlay_bonus

        current_owner = _safe_text(runtime_data.get("currentBusinessPageId") or runtime_data.get("pageId"))
        overlay_candidates = []
        for owner, coverage in owner_screen_coverage.items():
            if owner == current_owner:
                continue
            owner_lower = owner.lower()
            if owner_visible_clicks.get(owner, 0) < 3 or coverage < 0.60:
                continue
            if any(token in owner_lower for token in ("scene", "hud", "overview", "menuroot", "chat")):
                continue
            if any(token in owner_lower for token in ("player", "panel", "pop", "shop", "bag", "activity", "main")):
                overlay_candidates.append((coverage, owner_visible_clicks.get(owner, 0), owner_scores.get(owner, 0), owner))
        if overlay_candidates:
            overlay_candidates.sort(reverse=True)
            return overlay_candidates[0][3]

        candidates = [
            (score, owner)
            for owner, score in owner_scores.items()
            if score > 0 and owner_visible_clicks.get(owner, 0) >= 2
        ]
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return _safe_text(runtime_data.get("currentBusinessPageId") or runtime_data.get("pageId"))

    def _runtime_node_to_task(self, node: Dict[str, Any], runtime_data: Dict[str, Any]) -> Dict[str, Any]:
        runtime_path = _safe_text(node.get("runtimePath"))
        node_name = _safe_text(node.get("nodeName")) or runtime_path.rsplit("/", 1)[-1]
        page_hint = _safe_text(node.get("ownerPageId") or runtime_data.get("currentBusinessPageId") or node.get("pageId"))
        element_type = _safe_text(node.get("elementType")) or "clickable"
        text = _safe_text(node.get("text"))
        role = self._guess_role(node_name, element_type, runtime_path)
        assertion_target = self._runtime_node_is_assertion_target(node)
        if assertion_target:
            role = "visual_assert"
            if element_type in {"", "clickable"}:
                element_type = "display_region"
        target_name = self._runtime_target_name(page_hint, node_name, text, role, element_type)
        digest = hashlib.sha1(runtime_path.encode("utf-8")).hexdigest()[:10]
        task = {
            "targetId": f"runtime.{digest}",
            "targetName": target_name,
            "sourceCases": ["RUNTIME_CURRENT_PAGE"],
            "pageHint": page_hint,
            "role": role,
            "elementType": element_type,
            "interactionType": "assert_visible" if assertion_target else "click",
            "priority": self._runtime_priority(role, element_type),
            "expectedBehavior": self._expected_behavior(role),
            "status": "pending_match",
            "runtimeHint": {
                "runtimePath": runtime_path,
                "clickTargetNode": node.get("clickTargetNode", ""),
                "instanceId": node.get("instanceId", 0),
                "nodeName": node_name,
                "text": text,
                "screenRect": node.get("screenRect", []),
                "pageId": node.get("pageId", ""),
                "ownerPageId": page_hint,
                "capturedAt": runtime_data.get("capturedAt", ""),
            },
        }
        if assertion_target:
            task["assertion"] = {
                "type": "visual",
                "mode": "assert_visible",
                "clickRequired": False,
                "text": text,
                "spriteName": _safe_text(node.get("spriteName")),
                "rule": "visible_non_clickable_runtime_node",
            }
        collection_signature = self._runtime_collection_signature(runtime_path)
        if collection_signature:
            index = int(collection_signature["index"])
            page_slug = _slug(page_hint).replace(".", "_") or "current_page"
            item_slug = _slug(collection_signature.get("itemName") or "item").replace(".", "_")
            action_slug = _slug(collection_signature.get("actionName") or "click").replace(".", "_")
            if action_slug in {"clickcontent", "click", "btn", "button"}:
                action_slug = "click_area"
            collection_slug = f"{page_slug}.{item_slug}.{action_slug}"
            item_label = collection_signature.get("itemName") or node_name
            action_label = collection_signature.get("actionName") or "click"
            task.update({
                "targetName": f"{page_hint}第{index}个{item_label}{action_label}",
                "displayName": f"{page_hint}-{item_label}_{index} {action_label}",
                "semanticId": f"{page_slug}.{item_slug}_{index}.{action_slug}",
                "role": "item_click",
                "elementType": "Button",
                "priority": "P1",
                "expectedBehavior": "click visible collection item",
                "collectionRef": f"collection.{collection_slug}",
                "itemIndex": index,
            })
            task["runtimeHint"]["pageId"] = page_hint
            task["runtimeHint"]["ownerPageId"] = page_hint
        conditional = self._conditional_action_metadata(task, runtime_path, node_name, role)
        if conditional:
            task.update(conditional)
        return task

    def _conditional_action_metadata(self, task: Dict[str, Any], runtime_path: str, node_name: str, role: str) -> Dict[str, Any]:
        normalized_path = _safe_text(runtime_path).replace("\\", "/")
        lower = f"{normalized_path}/{node_name}/{role}".lower()
        if role in {"close", "tab", "item", "item_click", "entry"}:
            return {}
        if role == "add" and "/topres/" in lower:
            return {}
        action_roles = {"use", "claim", "confirm", "delete", "merge", "equip", "unequip", "upgrade", "goto", "add"}
        action_keywords = (
            "usedbtn",
            "usebtn",
            "claim",
            "receive",
            "deletebtn",
            "mergebtn",
            "gotobtn",
            "equip",
            "upgrade",
            "confirm",
            "okbtn",
            "btnok",
        )
        if role not in action_roles and not any(keyword in lower for keyword in action_keywords):
            return {}

        page_slug = _slug(task.get("pageHint", "") or "current_page").replace(".", "_")
        depends_on = f"state://{page_slug}/current_context"
        condition_subject = "current_context"
        page_hint = task.get("pageHint", "")
        test_id = ""
        semantic_id = ""
        target_name = ""
        display_name = ""
        expected = "click action when the current UI state allows it"

        role_name = role or "action"
        availability = {
            "type": "conditional",
            "dependsOn": depends_on,
            "condition": f"{condition_subject}.{role_name}_available == true",
            "stateRefresh": "after_dependency_action",
            "missingBehavior": "not_applicable",
            "missingReason": "condition_not_met",
            "runtimeRecheckRequired": True,
            "rule": "state_dependent_action",
        }
        out = {
            "availability": availability,
            "expectedBehavior": expected,
        }
        if page_hint:
            out["pageHint"] = page_hint
        if test_id:
            out["testId"] = test_id
            out["semanticId"] = semantic_id or test_id
            out["targetName"] = target_name or task.get("targetName")
            out["displayName"] = display_name or task.get("displayName", "")
            out["elementType"] = "Button"
            out["role"] = role_name
            out["priority"] = "P1"
        return out

    def _guess_role(self, node_name: str, element_type: str, runtime_path: str) -> str:
        text = f"{node_name} {runtime_path}".lower()
        if "close" in text or "btnclose" in text:
            return "close"
        if "add" in text:
            return "add"
        if "claim" in text or "reward" in text:
            return "claim"
        if "use" in text or "usedbtn" in text:
            return "use"
        if element_type == "tab":
            return "tab"
        if element_type == "item_cell":
            return "item"
        if element_type == "interactive_icon":
            return "entry"
        return "action"

    def _runtime_target_name(self, page_hint: str, node_name: str, text: str, role: str, element_type: str) -> str:
        label = text or node_name
        role_text = {
            "close": "close button",
            "add": "add button",
            "claim": "claim button",
            "use": "use button",
            "tab": "tab",
            "item": "item cell",
            "entry": "entry icon",
            "visual_assert": "visual check",
            "action": "action",
        }.get(role, element_type or "target")
        page = page_hint or "current page"
        return f"{page} {label} {role_text}"

    def _runtime_priority(self, role: str, element_type: str) -> str:
        if role in {"visual_assert"}:
            return "P2"
        if role in {"close", "use", "claim", "entry"}:
            return "P1"
        if role in {"tab", "item", "add"}:
            return "P2"
        return "P3"

    def _expected_behavior(self, role: str) -> str:
        return {
            "close": "click closes current panel",
            "use": "click uses selected item",
            "claim": "click claims reward",
            "entry": "click opens target panel",
            "tab": "click switches tab content",
            "add": "click opens resource add flow",
            "item": "click selects item cell",
            "visual_assert": "assert visible UI content without clicking",
        }.get(role, "click triggers current UI action")

    def _write_catalog(self, tasks: List[Dict[str, Any]]) -> None:
        catalog = {
            "schema_version": "target_name_catalog.v1",
            "updated_at": _now_text(),
            "targets": [
                {
                    "targetId": t.get("targetId", ""),
                    "targetName": t.get("targetName", ""),
                    "aliases": t.get("aliases", []),
                    "pageHint": t.get("pageHint", ""),
                    "role": t.get("role", ""),
                    "elementType": t.get("elementType", ""),
                    "interactionType": t.get("interactionType", ""),
                    "sourceCases": t.get("sourceCases", []),
                    "priority": t.get("priority", "P1"),
                    "collection": t.get("collection", {}),
                    "collectionRef": t.get("collectionRef", ""),
                    "itemIndex": t.get("itemIndex", ""),
                    "availability": t.get("availability", {}),
                    "assertion": t.get("assertion", {}),
                }
                for t in tasks
                if isinstance(t, dict)
            ],
        }
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        with self.catalog_path.open("w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
