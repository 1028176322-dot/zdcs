# -*- coding: utf-8 -*-
"""Candidate recommendation for target-driven mapping tasks.

The matcher ranks existing mapping drafts for one target. It keeps scoring
simple and explainable so reviewers can see why a candidate was recommended.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _autosmoke_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _metadata_dir() -> Path:
    return _autosmoke_root() / "metadata"


def _read_json(path: Path, fallback: Any):
    try:
        if not path.exists():
            return fallback
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", _text(value).lower())


def _semantic_id_is_productized(value: Any) -> bool:
    text = _text(value)
    if not text or "custom_" in text or ".." in text:
        return False
    if re.search(r"[\u4e00-\u9fff]", text):
        return False
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+", text))


def _candidate_is_debug_overlay(value: Any) -> bool:
    if isinstance(value, dict):
        chunks = [
            value.get("path"),
            value.get("elementPath"),
            value.get("runtimePath"),
            value.get("prefabPath"),
            value.get("prefabNodePath"),
            value.get("pageId"),
            value.get("displayName"),
            value.get("chineseDescription"),
            value.get("nodeName"),
            value.get("text"),
        ]
        text = " ".join(_text(x) for x in chunks)
    else:
        text = _text(value)
    text = text.lower().replace("\\", "/")
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


def _tokens(value: Any) -> List[str]:
    raw = _text(value).lower()
    parts = [p for p in re.split(r"[^a-z0-9\u4e00-\u9fff]+", raw) if p]
    compact = _norm(value)
    if compact and compact not in parts:
        parts.append(compact)
    return parts


def _contains_any(haystack: str, needles: List[str]) -> bool:
    if not haystack:
        return False
    return any(n and n in haystack for n in needles)


def _path_similarity(a: str, b: str) -> float:
    aa = [p for p in _text(a).lower().split("/") if p]
    bb = [p for p in _text(b).lower().split("/") if p]
    if not aa or not bb:
        return 0.0
    overlap = len(set(aa) & set(bb))
    return overlap / max(len(set(aa)), len(set(bb)))


def _load_drafts() -> List[Dict[str, Any]]:
    try:
        from 元数据.element_mapping import ElementMappingManager
        mgr = ElementMappingManager()
        mgr.load()
        return list(mgr._mappings.values()) if hasattr(mgr, "_mappings") else []
    except Exception:
        return []


def _load_runtime_index() -> Dict[str, Dict[str, Any]]:
    data = _read_json(_metadata_dir() / "runtime_match_result.json", {})
    out = {}
    for item in data.get("results", []) if isinstance(data, dict) else []:
        if isinstance(item, dict) and item.get("draftPath"):
            out[item["draftPath"]] = item
    return out


def _load_code_semantic_text() -> Dict[str, str]:
    data = _read_json(_metadata_dir() / "ui_code_semantics.json", {})
    out = {}
    pages = data.get("pages", {}) if isinstance(data, dict) else {}
    if not isinstance(pages, dict):
        return out
    for page_id, page in pages.items():
        elements = page.get("elements", {}) if isinstance(page, dict) else {}
        if not isinstance(elements, dict):
            continue
        for path, item in elements.items():
            if not isinstance(item, dict):
                continue
            chunks = [page_id, path]
            for key in ("runtimePath", "nodeName", "handler", "businessAction", "actionType", "targetPage"):
                chunks.append(_text(item.get(key)))
            code_semantic = item.get("codeSemantic", {})
            if isinstance(code_semantic, dict):
                for key in ("handler", "actionType", "businessAction", "expectedResult"):
                    chunks.append(_text(code_semantic.get(key)))
            out[_norm(path)] = _norm(" ".join(chunks))
    return out


def _runtime_synthetic_candidate(target: Dict[str, Any]) -> Dict[str, Any]:
    runtime_hint = target.get("runtimeHint", {}) if isinstance(target.get("runtimeHint", {}), dict) else {}
    runtime_path = _text(runtime_hint.get("runtimePath"))
    if not runtime_path:
        return {}
    interaction = _text(target.get("interactionType"))
    role = _text(target.get("role"))
    assertion = target.get("assertion", {}) if isinstance(target.get("assertion"), dict) else {}
    is_assert_visible = interaction == "assert_visible" or role == "visual_assert" or assertion.get("clickRequired") is False
    if not is_assert_visible:
        return {}
    page_id = _text(runtime_hint.get("ownerPageId") or runtime_hint.get("pageId") or target.get("pageHint") or "RUNTIME_CURRENT_PAGE")
    node_name = _text(runtime_hint.get("nodeName") or runtime_path.rsplit("/", 1)[-1])
    label = _text(runtime_hint.get("text")) or node_name or "runtime node"
    draft_path = f"__runtime__::{page_id}::{runtime_path}"
    element_type = _text(target.get("elementType")) or "display_region"
    return {
        "displayName": f"{label} visual check",
        "draftPath": draft_path,
        "elementType": element_type,
        "pageId": page_id,
        "reasons": ["runtime_path_exact", "runtime_node_current", "assert_visible"],
        "reviewStatus": "runtime_node",
        "risks": [],
        "role": role or "visual_assert",
        "runtimeMatched": True,
        "score": 1.0,
        "semanticId": _text(target.get("semanticId")),
        "testId": _text(target.get("testId")) or draft_path.replace("/", ".").replace("::", ".").strip("."),
    }


def _semantic_hit(draft: Dict[str, Any], semantic_text: Dict[str, str], target_tokens: List[str]) -> bool:
    keys = [
        draft.get("path"),
        draft.get("elementPath"),
        draft.get("runtimePath"),
        draft.get("prefabNodePath"),
        draft.get("prefabPath"),
    ]
    combined = []
    for key in keys:
        nk = _norm(key)
        if not nk:
            continue
        if nk in semantic_text:
            combined.append(semantic_text[nk])
        if "::" in _text(key):
            tail = _norm(_text(key).split("::", 1)[1])
            if tail in semantic_text:
                combined.append(semantic_text[tail])
    if not combined:
        code = draft.get("codeSemantic", {})
        if isinstance(code, dict):
            combined.append(_norm(json.dumps(code, ensure_ascii=False)))
    return _contains_any(" ".join(combined), target_tokens)


def _score_candidate(
    target: Dict[str, Any],
    draft: Dict[str, Any],
    runtime_index: Dict[str, Dict[str, Any]],
    semantic_text: Dict[str, str],
) -> Tuple[float, List[str], List[str]]:
    if _candidate_is_debug_overlay(draft) and not _candidate_is_debug_overlay(target):
        return 0.0, [], ["debug_ui_excluded"]
    target_name = target.get("targetName", "")
    target_tokens = _tokens(" ".join([
        target_name,
        target.get("targetId", ""),
        target.get("role", ""),
        target.get("elementType", ""),
        target.get("expectedBehavior", ""),
    ]))
    draft_text = _norm(" ".join([
        draft.get("displayName", ""),
        draft.get("chineseDescription", ""),
        draft.get("name", ""),
        draft.get("nodeName", ""),
        draft.get("text", ""),
        draft.get("testId", ""),
        draft.get("semanticId", ""),
        draft.get("suggestedTestId", ""),
        draft.get("suggestedSemanticId", ""),
        draft.get("path", ""),
    ]))
    score = 0.0
    reasons: List[str] = []
    risks: List[str] = []
    runtime_hint = target.get("runtimeHint", {}) if isinstance(target.get("runtimeHint", {}), dict) else {}
    hint_path = _text(runtime_hint.get("runtimePath"))
    hint_page = _norm(runtime_hint.get("ownerPageId") or runtime_hint.get("pageId"))
    draft_path_text = _text(draft.get("runtimePath") or draft.get("path") or draft.get("elementPath"))
    draft_path_norm = _norm(draft_path_text)
    hint_path_norm = _norm(hint_path)
    if hint_path_norm:
        if hint_path_norm and hint_path_norm in draft_path_norm:
            score += 0.40
            reasons.append("runtime_path_match")
        else:
            similarity = _path_similarity(hint_path, draft_path_text)
            if similarity >= 0.35:
                score += 0.25
                reasons.append("runtime_path_similar")
            else:
                risks.append("runtime_path_mismatch")

    if _contains_any(draft_text, target_tokens):
        score += 0.25
        reasons.append("name_match")

    page_hint = _norm(target.get("pageHint"))
    draft_page = _norm(draft.get("pageId"))
    page_ok = False
    if page_hint and draft_page and (page_hint in draft_page or draft_page in page_hint):
        page_ok = True
    if hint_page and draft_page and (hint_page in draft_page or draft_page in hint_page):
        page_ok = True
    if hint_page and hint_page in draft_path_norm:
        page_ok = True
    if page_ok:
        score += 0.20
        reasons.append("page_match")
    elif page_hint and not draft_page:
        risks.append("draft_page_missing")
    elif page_hint and draft_page:
        score -= 0.25
        risks.append("page_mismatch")

    target_role = _norm(target.get("role"))
    draft_role = _norm(draft.get("role"))
    target_type = _norm(target.get("elementType"))
    draft_type = _norm(draft.get("elementType"))
    if (target_role and draft_role and (target_role in draft_role or draft_role in target_role)) or (
        target_type and draft_type and (target_type in draft_type or draft_type in target_type)
    ):
        score += 0.20
        reasons.append("role_or_type_match")

    if _semantic_hit(draft, semantic_text, target_tokens):
        score += 0.20
        reasons.append("code_semantic")

    path = draft.get("path") or draft.get("elementPath") or ""
    runtime = runtime_index.get(path) or {}
    runtime_match = draft.get("runtimeMatch", {})
    runtime_ok = bool(runtime.get("matched")) or runtime_match.get("status") == "matched" or draft.get("reviewStatus") == "runtime_matched"
    if runtime_ok:
        score += 0.15
        reasons.append("runtime_matched")
    elif target.get("status") in ("runtime_matched", "highlight_generated", "visual_confirmed", "click_confirmed"):
        risks.append("runtime_not_currently_matched")

    if not reasons and _norm(target_name) and _norm(target_name) in draft_text:
        score += 0.10
        reasons.append("weak_name_match")
    if draft.get("reviewStatus") in ("rejected", "ignored"):
        score -= 0.30
        risks.append(f"draft_{draft.get('reviewStatus')}")
    if draft.get("elementType") in ("debug_ui",) or draft.get("excludeReason") == "debug_ui" or _candidate_is_debug_overlay(draft):
        score -= 0.80
        risks.append("debug_ui")
    if not draft.get("screenRect") and not (runtime_match or {}).get("screenRect"):
        risks.append("screen_rect_missing")
    if hint_path_norm and "runtime_path_mismatch" in risks:
        score -= 0.35
    if hint_path_norm and "runtime_path_mismatch" in risks and "page_mismatch" in risks:
        score -= 0.30

    return max(0.0, min(1.0, score)), reasons, risks


def recommend_candidates(target: Dict[str, Any], limit: int = 10) -> Dict[str, Any]:
    drafts = _load_drafts()
    runtime_index = _load_runtime_index()
    semantic_text = _load_code_semantic_text()
    candidates = []
    runtime_candidate = _runtime_synthetic_candidate(target)
    if runtime_candidate:
        candidates.append(runtime_candidate)
    seen_names = {}
    for draft in drafts:
        if not isinstance(draft, dict):
            continue
        path = draft.get("path") or draft.get("elementPath") or ""
        if not path:
            continue
        score, reasons, risks = _score_candidate(target, draft, runtime_index, semantic_text)
        if score <= 0 and not reasons:
            continue
        if target.get("runtimeHint") and "runtime_path_mismatch" in risks and "page_mismatch" in risks:
            continue
        name_key = _norm(draft.get("displayName") or draft.get("name") or draft.get("nodeName"))
        if name_key:
            seen_names[name_key] = seen_names.get(name_key, 0) + 1
        semantic_id = draft.get("semanticId") or draft.get("suggestedSemanticId", "")
        if not _semantic_id_is_productized(semantic_id):
            semantic_id = ""
        candidates.append({
            "draftPath": path,
            "displayName": draft.get("displayName") or draft.get("name") or draft.get("nodeName") or path.split("/")[-1],
            "pageId": draft.get("pageId", ""),
            "role": draft.get("role", ""),
            "elementType": draft.get("elementType", ""),
            "reviewStatus": draft.get("reviewStatus", draft.get("source", "")),
            "score": round(score, 3),
            "reasons": reasons,
            "risks": risks,
            "runtimeMatched": "runtime_matched" in reasons,
            "testId": draft.get("testId") or draft.get("suggestedTestId", ""),
            "semanticId": semantic_id,
        })
    for cand in candidates:
        name_key = _norm(cand.get("displayName"))
        if name_key and seen_names.get(name_key, 0) > 1:
            cand.setdefault("risks", []).append("duplicate_name")
    candidates.sort(
        key=lambda c: (
            "runtime_path_exact" in c.get("reasons", []),
            "runtime_path_match" in c.get("reasons", []),
            "runtime_path_similar" in c.get("reasons", []),
            c.get("score", 0),
            "debug_ui" not in c.get("risks", []),
        ),
        reverse=True,
    )
    limit = max(1, min(int(limit or 10), 50))
    return {
        "success": True,
        "targetId": target.get("targetId", ""),
        "totalCandidates": len(candidates),
        "candidates": candidates[:limit],
    }
