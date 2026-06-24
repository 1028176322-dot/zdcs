# -*- coding: utf-8 -*-
"""Utilities for querying code semantic index for current page / element."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


def normalize_page_id(value: str) -> str:
    if not value:
        return ""
    txt = (value or "").replace("(Clone)", "")
    if "[" in txt and "]" in txt:
        inner = txt[txt.find("[") + 1:txt.find("]")]
        if inner:
            txt = inner
    txt = txt.strip()
    return txt


def _read_code_semantics(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _page_key_candidates(page_id: str, prefab_path: str) -> List[str]:
    norm_page = normalize_page_id(page_id)
    keys = []
    if norm_page:
        keys.append(norm_page)
    if prefab_path:
        base = os.path.basename(prefab_path)
        if base:
            keys.append(normalize_page_id(os.path.splitext(base)[0]))
    # 常见同义词匹配兜底
    if norm_page.startswith("UI"):
        keys.append(norm_page[2:])
    if norm_page.endswith("Panel"):
        keys.append(norm_page[:-5])
    if norm_page.endswith("Window"):
        keys.append(norm_page[:-6])
    # 去重
    return list(dict.fromkeys([k for k in keys if k]))


def _build_element_list(page_bucket: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    elements = page_bucket.get("elements", {}) if isinstance(page_bucket, dict) else {}
    for key, item in elements.items() if isinstance(elements, dict) else []:
        if not isinstance(item, dict):
            continue
        item_copy = dict(item)
        item_copy["runtimePath"] = item_copy.get("runtimePath") or key
        out.append(item_copy)
    return out


def _select_page_bucket(pages: Dict[str, Any], page_id: str, prefab_path: str = "") -> Optional[Dict[str, Any]]:
    if not isinstance(pages, dict):
        return None
    candidates = _page_key_candidates(page_id, prefab_path)
    for c in candidates:
        for k, v in pages.items():
            if not isinstance(v, dict):
                continue
            if normalize_page_id(str(k)).lower() == c.lower():
                return v
    # 兼容模糊匹配
    for k, v in pages.items():
        if not isinstance(v, dict):
            continue
        nk = normalize_page_id(str(k)).lower()
        if any(c.lower() in nk for c in candidates):
            return v
    return None


def query_current_page_code(page_id: str, prefab_path: str = "", semantic_path: str = "") -> Dict[str, Any]:
    """查询单页语义索引，返回页面级别的语义数据。"""
    if not semantic_path:
        return {"success": False, "error": "语义索引路径为空"}

    payload = _read_code_semantics(semantic_path)
    if not payload:
        return {"success": False, "error": "语义索引不存在", "path": semantic_path}

    pages = payload.get("pages", {}) if isinstance(payload, dict) else {}
    bucket = _select_page_bucket(pages, page_id, prefab_path)
    if not bucket:
        return {
            "success": False,
            "error": "未找到当前页语义",
            "path": semantic_path,
            "pageId": page_id,
            "prefabPath": prefab_path,
        }

    normalized_page = normalize_page_id(page_id) or bucket.get("pageId", "")
    elements = _build_element_list(bucket)
    bucket_prefab = bucket.get("prefab") or bucket.get("prefabPath") or prefab_path or ""
    scripts = bucket.get("scripts", [])
    if not isinstance(scripts, list):
        scripts = []

    return {
        "success": True,
        "path": semantic_path,
        "pageId": normalized_page,
        "prefabPath": bucket_prefab,
        "codeFiles": scripts,
        "elementSemantics": elements,
        "generatedAt": payload.get("generatedAt", ""),
    }


def _match_code_element(page_bucket: Dict[str, Any], node_name: str, runtime_path: str) -> Optional[Dict[str, Any]]:
    if not isinstance(page_bucket, dict):
        return None
    elements = page_bucket.get("elements", {}) if isinstance(page_bucket.get("elements"), dict) else {}
    best = None
    best_score = 0.0
    rn = (runtime_path or "").replace("\\", "/").strip().lower()
    nn = (node_name or "").strip().lower()

    for key, item in elements.items():
        if not isinstance(item, dict):
            continue
        rp = (item.get("runtimePath") or key or "").replace("\\", "/").strip().lower()
        nd = (item.get("nodeName") or "").strip().lower()
        score = 0.0
        if rn and rp and rp == rn:
            score = 1.0
        elif rn and rp and (rn.endswith("/" + rp) or rp.endswith("/" + rn)):
            score = 0.86
        elif nn and nd == nn:
            score = 0.72
        elif nn and (nd and nn in rp):
            score = 0.62
        if score <= best_score:
            continue
        best = item
        best_score = score

    return best


def query_element_code(page_id: str, prefab_path: str, node_name: str = "", runtime_path: str = "", semantic_path: str = "") -> Dict[str, Any]:
    if not semantic_path:
        return {"success": False, "error": "语义索引路径为空"}

    payload = _read_code_semantics(semantic_path)
    if not payload:
        return {"success": False, "error": "语义索引不存在", "path": semantic_path}

    pages = payload.get("pages", {}) if isinstance(payload, dict) else {}
    page_bucket = _select_page_bucket(pages, page_id, prefab_path)
    if not page_bucket:
        return {
            "success": False,
            "error": "未找到页码语义",
            "pageId": page_id,
            "prefabPath": prefab_path,
            "path": semantic_path,
        }

    item = None
    if runtime_path or node_name:
        item = _match_code_element(page_bucket, node_name=node_name, runtime_path=runtime_path)

    if not item:
        return {
            "success": False,
            "error": "未找到匹配语义",
            "pageId": normalize_page_id(page_id),
            "prefabPath": page_bucket.get("prefab", ""),
            "path": semantic_path,
        }

    return {
        "success": True,
        "path": semantic_path,
        "pageId": normalize_page_id(page_id),
        "prefabPath": page_bucket.get("prefab", ""),
        "runtimePath": item.get("runtimePath", ""),
        "nodeName": item.get("nodeName", ""),
        "handler": item.get("handler", ""),
        "actionType": item.get("actionType", "unknown"),
        "businessAction": item.get("businessAction", item.get("actionType", "unknown")),
        "expectedResult": item.get("expectedResult", []),
        "requiresState": item.get("requiresState", []),
        "risk": item.get("risk", []),
        "sourceFiles": item.get("sourceFiles", item.get("handlerFile", [])),
        "confidence": item.get("confidence", 0.0),
    }
