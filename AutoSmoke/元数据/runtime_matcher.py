# -*- coding: utf-8 -*-
"""runtime_matcher.py
运行时 UI 与映射草稿的匹配器（兼容旧接口）。

新增能力
- P1_CODE 语义优先级
- 运行态当前页识别规范化
- 运行时节点归一化 ownerPageId
- 匹配结果携带 codeSemantic 证据
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple


def normalize_rect(rect, fmt=None):
    """normalize rect to dict{x,y,width,height}"""
    if isinstance(rect, dict):
        return {
            "x": rect.get("x", 0),
            "y": rect.get("y", 0),
            "width": rect.get("width", 0),
            "height": rect.get("height", 0),
        }
    if isinstance(rect, (list, tuple)) and len(rect) >= 4:
        a, b, c, d = rect[:4]
        if fmt == "xywh":
            return {"x": a, "y": b, "width": c, "height": d}
        if fmt == "xyxy":
            return {"x": a, "y": b, "width": c - a, "height": d - b}
        if c > a and d > b:
            return {"x": a, "y": b, "width": c - a, "height": d - b}
        return {"x": a, "y": b, "width": c, "height": d}
    return None


def is_valid_rect(r, image_width=None, image_height=None):
    if not r:
        return False
    if not isinstance(r, dict):
        nr = normalize_rect(r)
        if not nr:
            return False
        r = nr
    if r.get("width", 0) <= 4 or r.get("height", 0) <= 4:
        return False
    if r.get("x", 0) < 0 or r.get("y", 0) < 0:
        return False
    if image_width is not None and image_height is not None:
        if r["x"] >= image_width or r["y"] >= image_height:
            return False
        if r["x"] + r["width"] <= 0 or r["y"] + r["height"] <= 0:
            return False
    return True


DEBUG_UI_PATTERNS = [
    "debug", "graphicdebug", "ui_debug_", "gm", "console",
    "testpanel", "dev", "editor",
]


def is_debug_ui(draft: Dict) -> bool:
    prefab_path = (draft.get("prefabPath", "") or "").lower()
    page_id = (draft.get("pageId", "") or "").lower()
    name = (draft.get("nodeName", "") or draft.get("name", "") or "").lower()
    path = (draft.get("path", "") or "").lower()
    for pat in DEBUG_UI_PATTERNS:
        if pat in prefab_path or pat in page_id or pat in name or pat in path:
            return True
    return False


def page_matches(draft_page: str, runtime_page: str) -> bool:
    dp = (draft_page or "").strip().lower()
    rp = (runtime_page or "").strip().lower()
    if not dp or not rp:
        return False
    if dp == rp or dp in rp:
        return True
    compact = rp.replace("(clone)", "").replace("[", " ").replace("]", " ")
    return dp in compact


def _normalize_page_token(value: str) -> str:
    if not value:
        return ""
    v = value.replace("(Clone)", "").replace("(clone)", "")
    m = re.search(r"\[([^\]]+)\]", v)
    if m and m.group(1):
        v = m.group(1)
    v = v.replace(" ", "").replace("\t", "")
    return v.strip()


GENERIC_RUNTIME_PAGE_IDS = {
    "", "unknown", "root", "bg", "view", "viewport", "scrollview", "tab", "page",
    "content", "animation", "menuroot", "topres", "top_top", "left_top", "right_top",
    "left_bottom", "right_bottom", "normalchatcanvas", "chatcanvas", "cont_chat",
    "btnclose", "closebtn", "closebutton",
}


def is_business_page_id(page_id: str) -> bool:
    p = (page_id or "").strip()
    if not p:
        return False
    pl = p.lower()
    if pl in GENERIC_RUNTIME_PAGE_IDS:
        return False
    if any(x in pl for x in ("debug", "gmwindow", "console", "editor")):
        return False
    if p.startswith("UI") or p.startswith("ui") or p.startswith("EXPORT_"):
        return True
    if "(Clone)" in p or "[UI" in p or "Pop" in p:
        return True
    return False


def page_matches_any(draft_page: str, runtime_pages: List[str]) -> bool:
    return any(page_matches(draft_page, p) for p in runtime_pages)


def normalize_runtime_path(path: str) -> str:
    p = (path or "").replace("\\", "/")
    p = re.sub(r"/", "/", p)
    p = re.sub(r"/+$", "", p)
    p = re.sub(r"/+", "/", p)
    return p


def draft_runtime_path(draft: Dict) -> str:
    raw = draft.get("prefabNodePath", "") or draft.get("path", "") or ""
    if "::" in raw:
        raw = raw.split("::", 1)[1]
    raw = normalize_runtime_path(raw)
    if not raw:
        return ""
    page = (draft.get("pageId", "") or "").lower()
    parts = [p for p in raw.split("/") if p]
    if parts and parts[0].lower() == page.lower():
        parts = parts[1:]
    return "/".join(parts)


def _normalize_current_page_hint(raw_page_id: str) -> str:
    return _normalize_page_token(raw_page_id)


def enrich_runtime_nodes(runtime_nodes: List[Dict]) -> Tuple[List[Dict], str]:
    owner_by_path: Dict[str, str] = {}
    for n in runtime_nodes:
        path = n.get("runtimePath", "") or n.get("path", "") or ""
        if not path:
            continue
        raw_page = n.get("pageId", "") or n.get("ownerPageId", "")
        parent_owner = ""
        parts = normalize_runtime_path(path).split("/")
        for i in range(len(parts) - 1, 0, -1):
            parent_path = "/".join(parts[:i])
            parent_owner = owner_by_path.get(parent_path, "")
            if parent_owner:
                break
        owner = raw_page if is_business_page_id(raw_page) else parent_owner
        owner_by_path[normalize_runtime_path(path)] = owner
        n["ownerPageId"] = owner or raw_page

    current_owner = infer_current_business_page_id(runtime_nodes)
    for n in runtime_nodes:
        if current_owner:
            n["currentBusinessPageId"] = current_owner
    return runtime_nodes, current_owner


def infer_current_business_page_id(runtime_nodes: List[Dict]) -> str:
    scores: Dict[str, float] = {}
    for n in runtime_nodes:
        owner = n.get("ownerPageId", "") or n.get("pageId", "") or ""
        if not is_business_page_id(owner):
            continue
        score = 1.0
        path = n.get("runtimePath", "") or n.get("path", "") or ""
        if "uimain" in owner.lower():
            score -= 0.75
        if "pop" in owner.lower() and "umain" not in owner.lower():
            score += 3.0
        if path == "Root" or path.startswith("Root/"):
            score += 2.0
        if n.get("effectiveClickable"):
            score += 4.0
        if n.get("visible"):
            score += 1.0
        rect = normalize_rect(n.get("screenRect", []))
        if rect and is_valid_rect(rect, 1170, 2532):
            area = max(0, rect.get("width", 0)) * max(0, rect.get("height", 0))
            if area > 1170 * 2532 * 0.20:
                score += 5.0
        scores[owner] = scores.get(owner, 0.0) + score
    if not scores:
        return ""
    return max(scores.items(), key=lambda kv: kv[1])[0]


def _normalize_code_action(action: str) -> str:
    return (action or "unknown").strip().lower() or "unknown"


def _normalize_code_key(text: str) -> str:
    return normalize_runtime_path(text).replace("/", "_").strip().lower()


def _load_code_semantics(path: str) -> Dict:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        pages = data.get("pages", {}) if isinstance(data.get("pages"), dict) else {}
        index = {}
        for page_key, page_bucket in pages.items():
            if not isinstance(page_bucket, dict):
                continue
            norm_page = _normalize_page_token(str(page_key))
            entry = index.setdefault(norm_page, {"bucket": page_bucket, "path": {}, "node": {}})
            elements = page_bucket.get("elements", {})
            if not isinstance(elements, dict):
                continue
            for elem_key, elem in elements.items():
                if not isinstance(elem, dict):
                    continue
                rp = elem.get("runtimePath") or elem_key
                nk = _normalize_code_key(rp)
                if nk:
                    entry["path"][nk] = elem
                node = (elem.get("nodeName") or "").strip().lower()
                if node:
                    entry["node"].setdefault(node, elem)
        data["__index"] = index
        return data
    except Exception:
        return {}


def _safe_float(value: float, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _resolve_code_semantics(page_id: str, draft: Dict, runtime_path: str, semantics: Dict) -> Dict:
    if not isinstance(semantics, dict):
        return {}
    bucket = semantics.get("pages", {}) or {}
    index = semantics.get("__index", {}) if isinstance(semantics.get("__index"), dict) else {}
    norm_page = _normalize_page_token(page_id) or _normalize_page_token(draft.get("pageId", ""))
    candidates = []

    runtime_norm = _normalize_code_key(runtime_path)
    node_name = (draft.get("nodeName", "") or draft.get("name", "")).strip()

    page_index = index.get(norm_page)
    if page_index is None:
        for k, v in index.items():
            if norm_page and norm_page in k:
                page_index = v
                break

    if isinstance(page_index, dict):
        by_path = page_index.get("path", {})
        if runtime_norm and runtime_norm in by_path:
            return by_path[runtime_norm]
        if runtime_norm:
            suffix = runtime_norm.split("_")[-4:]
            suffix_key = "_".join(suffix)
            if suffix_key:
                for k, v in by_path.items():
                    if k.endswith(suffix_key) or runtime_norm.endswith(k):
                        return v
        if node_name:
            hit = (page_index.get("node", {}) or {}).get(node_name.lower())
            if hit:
                return hit

    return {}


class RuntimeElementMatcher:
    def __init__(self, drafts: List[Dict], runtime_nodes: List[Dict], current_page_id: str = "", code_semantics: Dict = None):
        self.drafts = drafts
        self.runtime_nodes = runtime_nodes
        self.current_page_id = current_page_id
        self.code_semantics = code_semantics or {}
        self._results: List[Dict] = []

    def match_all(self, page_id: str = "", priority: str = "") -> List[Dict]:
        candidates = self.drafts
        if page_id:
            candidates = [d for d in candidates if d.get("pageId", "") == page_id]
        if priority:
            pri_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5, "LOW": 6}
            level_limit = pri_order.get(priority, 99)
            candidates = [d for d in candidates if pri_order.get((d.get("priority", "") or "P3"), 99) <= level_limit]

        results = []
        for draft in candidates:
            results.append(self.match_one(draft, candidates))

        self._results = results
        return results

    def match_one(self, draft: Dict, all_candidates: List[Dict] = None) -> Dict:
        path = draft.get("path", "")
        if is_debug_ui(draft) or not draft.get("allowRuntimeMatch", True):
            return {
                "draftPath": path,
                "semanticId": draft.get("suggestedSemanticId", ""),
                "matched": False,
                "matchLevel": "",
                "matchScore": 0.0,
                "runtimePath": "",
                "instanceId": 0,
                "screenRect": [],
                "visible": False,
                "interactable": False,
                "conflicts": [],
                "matchFailReason": "debug_ui（调试界面元素，不参与业务匹配）",
                "draftPageId": draft.get("pageId", ""),
                "currentPageId": self.current_page_id,
                "codeSemantic": {
                    "status": "rejected",
                    "confidence": 0.0,
                },
            }

        best_match = None
        best_score = 0.0
        best_level = ""
        best_code = {}
        for rn in self.runtime_nodes:
            if (draft.get("clickable") or draft.get("effectiveClickable") or draft.get("elementType")) and not rn.get("effectiveClickable", False):
                continue
            score, level, code_ev = self._calc_match_score(draft, rn)
            if score > best_score:
                best_score = score
                best_level = level
                best_match = rn
                best_code = code_ev

        conflicts = []
        if best_match and best_score < 0.95:
            for rn in self.runtime_nodes:
                if rn is best_match:
                    continue
                s, _, _ = self._calc_match_score(draft, rn)
                if s > best_score * 0.85:
                    conflicts.append({
                        "runtimePath": rn.get("runtimePath", ""),
                        "matchScore": round(s, 2),
                    })

        screen_rect = best_match.get("screenRect", []) if best_match else []
        is_matched = best_match is not None and best_score >= 0.5

        rect_valid = True
        rect_fail_reason = ""
        if is_matched and screen_rect:
            nr = normalize_rect(screen_rect)
            if not is_valid_rect(nr):
                rect_valid = False
                rect_fail_reason = "invalid_rect"
                is_matched = False
                best_score = 0.0

        return {
            "draftPath": path,
            "semanticId": draft.get("suggestedSemanticId", ""),
            "matched": is_matched,
            "matchLevel": best_level if best_match else "",
            "matchScore": round(best_score, 2) if best_match and rect_valid else 0.0,
            "runtimePath": best_match.get("runtimePath", "") if best_match else "",
            "instanceId": best_match.get("instanceId", 0) if best_match else 0,
            "screenRect": screen_rect,
            "visible": best_match.get("visible", False) if best_match else False,
            "interactable": best_match.get("interactable", False) if best_match else False,
            "runtimePageId": best_match.get("pageId", "") if best_match else "",
            "ownerPageId": best_match.get("ownerPageId", "") if best_match else "",
            "conflicts": conflicts[:5],
            "codeSemantic": best_code or {"status": "unknown", "confidence": 0.0},
            "matchFailReason": "" if is_matched else self._fail_reason(draft, rect_fail_reason),
            "draftPageId": draft.get("pageId", ""),
            "currentPageId": self.current_page_id,
        }

    def _calc_match_score_legacy(self, draft: Dict, rn: Dict) -> Tuple[float, str, Dict]:
        draft_page = draft.get("pageId", "")
        rn_page = rn.get("pageId", "")
        rn_owner = rn.get("ownerPageId", "")
        rn_path = rn.get("runtimePath", rn.get("path", ""))
        rn_name = (rn.get("nodeName", "") or "").lower()
        rn_text = (rn.get("text", "") or "").lower()
        rn_sprite = (rn.get("spriteName", "") or "").lower()
        rn_comps = [c.lower() for c in (rn.get("components", []) or [])]

        draft_text = (draft.get("text", "") or "").lower()
        draft_name = (draft.get("nodeName", "") or draft.get("name", "") or "").lower()
        draft_path = draft.get("path", "")
        draft_sprite = (draft.get("spriteName", "") or "").lower()
        draft_rt = draft_runtime_path(draft)
        rn_path_norm = normalize_runtime_path(rn_path).lower()
        draft_rt_norm = normalize_runtime_path(draft_rt).lower()

        if draft_page and self.current_page_id and is_business_page_id(self.current_page_id):
            if not page_matches(draft_page, self.current_page_id):
                return 0.0, "", {}

        runtime_pages = [rn_owner, rn_page, rn.get("currentBusinessPageId", "")]
        if draft_page and not page_matches_any(draft_page, runtime_pages):
            return 0.0, "", {}

        page_score_bonus = 0.0
        if draft_page and self.current_page_id:
            if page_matches(draft_page, self.current_page_id) or page_matches_any(draft_page, runtime_pages):
                page_score_bonus = 0.15

        code = _resolve_code_semantics(draft_page, draft, rn_path_norm, self.code_semantics)
        code_match = False
        code_score = 0.0
        if code:
            code_score = 0.15
            if code.get("handler") and (code.get("handler") in (rn_name, draft_name) or code.get("handler") in draft_rt_norm):
                code_score += 0.10
            if code.get("actionType"):
                code_score += 0.03
            code_match = True

        # 0. runtimePath exact
        if draft_rt_norm and rn_path_norm:
            if rn_path_norm == draft_rt_norm or rn_path_norm.endswith("/" + draft_rt_norm):
                score = 1.20 + page_score_bonus + code_score
                return score, "P0_RUNTIME_PATH", self._pack_code_evidence(code, score)

        # 1. code semantic binding
        if code_match:
            score = 0.95 + page_score_bonus + code_score
            return min(score, 1.15), "P1_CODE", self._pack_code_evidence(code, score)

        # 2. testId based
        draft_test_id = draft.get("suggestedTestId", "") or draft.get("testId", "")
        if draft_test_id:
            parts = [p for p in re.split(r"[./:_\-]+", str(draft_test_id)) if p]
            leaf = parts[-1].lower() if parts else ""
            rn_leaf = rn_path_norm.split("/")[-1] if rn_path_norm else ""
            if leaf and (leaf == rn_name or leaf == rn_leaf or rn_path_norm.endswith("/" + leaf)):
                return 1.00 + page_score_bonus, "P2_CLICK_TARGET", {}

        # 3. prefabPath suffix
        prefab_path = draft.get("prefabNodePath", "") or draft.get("path", "")
        if prefab_path and draft_name and rn_path_norm:
            pn = normalize_runtime_path(prefab_path).lower()
            if pn in rn_path_norm:
                return 0.95 + page_score_bonus, "P2_CLICK_TARGET", {}
            if rn_path_norm.endswith("/" + draft_name):
                return 0.86 + page_score_bonus, "P3_PREFAB_PATH", {}

        # 4. runtimePath suffix
        if draft_rt_norm and rn_path_norm and draft_rt_norm.replace(draft_rt_norm.split("/")[-1], "") in rn_path_norm:
            return 0.85 + page_score_bonus, "P4_TEXT_SPRITE", {}

        # 5. text/name + component
        if draft_text and draft_text == rn_text:
            s = 0.54 + page_score_bonus
            if any(c in rn_comps for c in draft.get("components", []) or []):
                s += 0.10
            if rn.get("visible"):
                s += 0.05
            return s, "P5_VISUAL", {}

        if draft_name and draft_name == rn_name:
            s = 0.44 + page_score_bonus
            if any(c in rn_comps for c in draft.get("components", []) or []):
                s += 0.12
            if rn.get("visible"):
                s += 0.05
            return s, "P6_MANUAL", {}

        return max(0.0 + page_score_bonus / 4, 0.0), "", {}


    def _calc_match_score(self, draft: Dict, rn: Dict) -> Tuple[float, str, Dict]:
        draft_page = draft.get("pageId", "")
        code = _resolve_code_semantics(draft_page, draft, rn.get("runtimePath", rn.get("path", "")), self.code_semantics)
        score = 0.0
        level = ""
        evidence = {}
        try:
            from 元数据.semantic_fusion_matcher import match_runtime_node
            score, level, evidence = match_runtime_node(
                draft,
                rn,
                current_page_id=self.current_page_id,
                code=code,
                draft_page=draft_page,
            )
        except Exception:
            return self._calc_match_score_legacy(draft, rn)

        fused = self._pack_fusion_evidence(code or {}, evidence, score)
        if level is None:
            level = ""
        if score and score > 1.0:
            score = 1.0
        return score, str(level), fused

    def _pack_fusion_evidence(self, code: Dict, evidence: Dict, score: float) -> Dict:
        base = self._pack_code_evidence(code or {}, score)
        if isinstance(evidence, dict):
            for key, val in evidence.items():
                if key in ("status", "confidence"):
                    continue
                if key and val not in (None, ""):
                    base[key] = val
            if evidence.get("status") == "matched":
                base["status"] = "matched"
            elif code:
                base["status"] = "matched"
            else:
                base.setdefault("status", base.get("status", "unknown"))
            if "risk" not in base:
                base["risk"] = []
        return base

    def _pack_code_evidence(self, code: Dict, score: float) -> Dict:
        if not code:
            return {
                "status": "unmatched",
                "confidence": 0.0,
            }
        return {
            "status": "matched",
            "handler": code.get("handler") or code.get("function") or "",
            "actionType": _normalize_code_action(code.get("actionType") or code.get("businessAction")),
            "businessAction": code.get("businessAction") or code.get("actionType") or "",
            "expectedResult": code.get("expectedResult") or [],
            "sourceFiles": code.get("sourceFiles") or code.get("handlerFile") or [],
            "requiresState": code.get("requiresState") or [],
            "confidence": min(max(_safe_float(code.get("confidence", 0.0)) + score * 0.05, 1.0), 1.0),
        }

    def _fail_reason(self, draft: Dict, rect_fail_reason: str = "") -> str:
        if rect_fail_reason == "invalid_rect":
            return "invalid_rect（解析到的 screenRect 无效）"
        page_id = draft.get("pageId", "")
        runtime_pages = set(n.get("pageId", "") for n in self.runtime_nodes)
        if page_id and page_id not in runtime_pages:
            return f"page_not_open（当前界面未包含 {page_id}）"
        if not self.runtime_nodes:
            return "runtime_tree_missing（未刷新运行时 UI 树）"
        return "name_not_found（未找到匹配项）"


def run_runtime_match(draft_path: str = "", page_id: str = "",
                      priority: str = "", metadata_dir: str = "",
                      code_semantics_path: str = "") -> Dict:
    if not metadata_dir:
        import pathlib
        script_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
        metadata_dir = str(script_dir.parent / "metadata")

    if not draft_path:
        from pathlib import Path
        script_dir2 = Path(os.path.dirname(os.path.abspath(__file__)))
        checks = [
            os.path.join(metadata_dir, "element_mapping.json"),
            os.path.join(metadata_dir, "enhanced_ui_tree.json"),
            os.path.join(str(script_dir2), "element_mapping.json"),
            os.path.join(str(script_dir2), "enhanced_ui_tree.json"),
        ]
        for p in checks:
            if os.path.exists(p):
                draft_path = p
                break
    if not draft_path or not os.path.exists(draft_path):
        return {"success": False, "error": f"元素文件不存在: {draft_path}"}

    with open(draft_path, "r", encoding="utf-8") as f:
        draft_data = json.load(f)

    if "nodes" in draft_data:
        drafts = draft_data["nodes"]
    elif "mappings" in draft_data:
        drafts = draft_data["mappings"]
    elif isinstance(draft_data, list):
        drafts = draft_data
    else:
        drafts = [draft_data]

    for d in drafts:
        if is_debug_ui(d):
            d["elementType"] = d.get("elementType", "debug_ui")
            d["excludeReason"] = "debug_ui"
            d["allowRuntimeMatch"] = False
            d["businessCandidate"] = False

    runtime_path = os.path.join(metadata_dir, "runtime_ui_tree_current.json")
    if not os.path.exists(runtime_path):
        runtime_path = os.path.join(str(Path := __import__('pathlib').Path(os.path.abspath(__file__)).parent), "runtime_ui_tree_current.json")
    if not os.path.exists(runtime_path):
        return {"success": False, "error": "运行时UI树不存在，请先刷新运行态UI"}

    with open(runtime_path, "r", encoding="utf-8") as f:
        runtime_data = json.load(f)

    runtime_nodes = runtime_data.get("nodes", [])
    raw_current_page_id = runtime_data.get("pageId", "")
    runtime_nodes, inferred_page_id = enrich_runtime_nodes(runtime_nodes)
    current_page_id = inferred_page_id or raw_current_page_id

    if not code_semantics_path:
        code_semantics_path = os.path.join(metadata_dir, "ui_code_semantics.json")
    code_semantics = _load_code_semantics(code_semantics_path)

    matcher = RuntimeElementMatcher(drafts, runtime_nodes, current_page_id=current_page_id, code_semantics=code_semantics)
    results = matcher.match_all(page_id=page_id if page_id else "", priority=priority)

    business_results = [r for r in results if r.get("matchFailReason") != "debug_ui（调试界面元素，不参与业务匹配）"]
    total = len(business_results)
    matched = sum(1 for r in business_results if r.get("matched"))
    conflicts = sum(1 for r in business_results if r.get("conflicts"))
    debug_count = sum(1 for r in results if r.get("matchFailReason") == "debug_ui（调试界面元素，不参与业务匹配）")
    code_match_count = 0
    for r in business_results:
        cs = (r.get("codeSemantic") or {})
        if isinstance(cs, dict) and cs.get("status") == "matched":
            code_match_count += 1

    return {
        "success": True,
        "pageId": current_page_id,
        "rawPageId": raw_current_page_id,
        "currentBusinessPageId": current_page_id,
        "totalCandidates": total,
        "matched": matched,
        "conflicts": conflicts,
        "missing": total - matched,
        "debugUiExcluded": debug_count,
        "codeSemanticMatched": code_match_count,
        "results": results,
    }


__all__ = [
    "normalize_rect",
    "is_valid_rect",
    "normalize_runtime_path",
    "is_debug_ui",
    "draft_runtime_path",
    "RuntimeElementMatcher",
    "run_runtime_match",
    "infer_current_business_page_id",
    "enrich_runtime_nodes",
]
