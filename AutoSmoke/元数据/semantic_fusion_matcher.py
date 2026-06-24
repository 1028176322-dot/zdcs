# -*- coding: utf-8 -*-
"""语义融合评分器：融合运行态路径 + 页面 + 代码语义评分。"""

from __future__ import annotations

from typing import Dict, Tuple


def _normalize(v: str) -> str:
    return (v or "").replace("\\", "/").strip().lower()


def _is_bad_leaf(name: str) -> bool:
    return _normalize(name) in {
        "quality", "icon", "text", "effect", "particle", "bg", "background", "view", "content",
    }


def _business_page_match(page_id: str, owner: str) -> bool:
    p = _normalize(page_id)
    o = _normalize(owner)
    if not p or not o:
        return False
    return p == o or p in o or o in p


def _code_score(code: Dict) -> Tuple[float, bool, float]:
    if not isinstance(code, dict):
        return 0.0, False, 0.0
    handler = (code.get("handler") or code.get("handlerName") or "").strip()
    action = (code.get("actionType") or code.get("businessAction") or "unknown").strip().lower()
    conf = float(code.get("confidence", 0.0) or 0.0)
    score = 0.0
    if handler:
        score += 0.10
    if action and action != "unknown":
        score += 0.05
    return score, bool(handler), min(max(conf * 0.15, 0.0), 0.15)


def _runtime_visibility_bonus(node: Dict) -> float:
    bonus = 0.0
    if node.get("visible"):
        bonus += 0.10
    if node.get("effectiveClickable"):
        bonus += 0.15
    return bonus


def match_runtime_node(
    draft: Dict,
    runtime_node: Dict,
    current_page_id: str = "",
    code: Dict = None,
    draft_page: str = "",
) -> Tuple[float, str, Dict]:
    draft_path = _normalize(draft.get("path", "") or draft.get("runtimePath", "") or "")
    draft_name = _normalize(draft.get("nodeName") or draft.get("name", "") or "")
    draft_runtime = _normalize(draft.get("runtimePath", "") or "")
    if draft_path and draft_path in draft_runtime:
        draft_runtime = draft_path

    rn_path = _normalize(runtime_node.get("runtimePath", runtime_node.get("path", "") or ""))
    rn_name = _normalize(runtime_node.get("nodeName", runtime_node.get("name", "") or ""))
    rn_owner = _normalize(runtime_node.get("ownerPageId", "") or runtime_node.get("pageId", "") or "")
    rn_text = _normalize(runtime_node.get("text", "") or "")

    score = 0.0
    evidence = {
        "matchLayers": [],
        "actionType": "unknown",
        "businessAction": "",
        "handler": "",
        "sourceFiles": [],
        "confidence": 0.0,
        "penalties": [],
    }

    # 页面一致性
    if current_page_id and not _business_page_match(draft_page or _normalize(draft.get("pageId", "")), rn_owner):
        if draft_page:
            return 0.0, "", evidence

    if draft_page:
        dcp = _normalize(draft_page)
        if dcp and (dcp in rn_owner or rn_owner in dcp):
            score += 0.20
            evidence["matchLayers"].append("page_consistency")

    # 可见性与交互可用性
    if runtime_node.get("clickable") or runtime_node.get("effectiveClickable"):
        score += _runtime_visibility_bonus(runtime_node)
        evidence["matchLayers"].append("runtime_interactive")

    # 运行态路径精确
    if draft_runtime and rn_path and (rn_path == draft_runtime or rn_path.endswith("/" + draft_runtime) or draft_runtime.endswith("/" + rn_path)):
        score += 0.40
        evidence["matchLayers"].append("runtime_path_exact")
        return min(1.0, score), "P0_RUNTIME_PATH", evidence

    # 代码语义绑定
    cs_score, has_handler, conf_bonus = _code_score(code or {})
    if has_handler:
        score += 0.15 + conf_bonus + cs_score
        evidence["matchLayers"].append("code_bind")
        evidence["handler"] = code.get("handler", "")
        evidence["actionType"] = code.get("actionType", code.get("businessAction", "unknown"))
        evidence["businessAction"] = code.get("businessAction", "")
        evidence["expectedResult"] = code.get("expectedResult", [])
        evidence["sourceFiles"] = code.get("sourceFiles", code.get("handlerFile", []))
        evidence["confidence"] = min(1.0, float(code.get("confidence", 0.0) or 0.0) + conf_bonus)
        if evidence["handler"]:
            return min(1.0, score), "P1_CODE_BINDING", evidence

    # click target 相关
    suggested = _normalize(draft.get("suggestedTestId", ""))
    if suggested:
        leaf = suggested.split(".")[-1]
        if leaf and (leaf == rn_name or rn_path.endswith("/" + leaf)):
            score += 0.32
            evidence["matchLayers"].append("click_target")
            return min(1.0, score), "P2_CLICK_TARGET", evidence

    if draft_name and rn_name and (rn_name == draft_name or rn_name in draft_name or draft_name in rn_name):
        score += 0.20

    # 文本/图标辅助
    draft_text = _normalize(draft.get("text", "") or "")
    if draft_text and draft_text == rn_text:
        score += 0.08
        evidence["matchLayers"].append("text_match")

    # 质量/图标等视觉子节点降权
    if _is_bad_leaf(rn_name) or _is_bad_leaf(rn_path.split("/")[-1] if rn_path else ""):
        score -= 0.30
        evidence["penalties"].append("visual_leaf")

    # debug/gm过滤
    if any(x in rn_owner for x in ("debug", "gm", "editor", "console")):
        score -= 1.0
        evidence["penalties"].append("debug_context")

    if draft_path and rn_path and (rn_path in draft_path or draft_path in rn_path):
        score += 0.30
        evidence["matchLayers"].append("prefab_like")
        if score >= 0.80:
            return min(1.0, score), "P3_PREFAB_PATH", evidence

    if score <= 0.0:
        return 0.0, "", evidence

    # 收敛到等级
    if score >= 0.65:
        return min(1.0, score), "P4_TEXT_SPRITE", evidence
    if score >= 0.40:
        return min(1.0, score), "P5_RUNTIME_ONLY", evidence
    return min(1.0, score), "", evidence
