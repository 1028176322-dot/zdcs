# -*- coding: utf-8 -*-
"""Build UI code semantic index for current Unity project."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CODE_EXTS = {".lua", ".cs"}
MAX_CODE_FILES = 1200
MAX_CODE_FILE_BYTES = 1024 * 1024

UI_CODE_HINTS = (
    "/ui/", "/uis/", "/panel/", "/panels/", "/popup/", "/view/", "/views/",
    "/window/", "/windows/", "/controller/", "/controllers/", "/module/",
)

_EXCLUDED_DIRS = {
    ".git", ".idea", ".vscode", "Library", "Temp", "Obj", "obj", "bin", "Build",
    "build", "packages", ".gradle", "Packages", "dist", "Plugins", "ThirdSdk",
    "PlatformSDK", "TextMesh Pro", "FastShadowReceiver", "DynamicShadowProjector",
    "Bugly", "SDKConfig", "HybridCLRGenerate", "Editor", "CasualGameEditor",
    "Generate", "Generated",
}

LUA_BIND_PATTERNS = [
    re.compile(r"self\s*:\s*AddClick\(\s*([^,\)]+)\s*,\s*self\.([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE),
    re.compile(r"self\.([A-Za-z0-9_]+)\.onClick\s*:AddListener\(\s*function\(\)\s*self\.([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE),
    re.compile(r"UIEventListener\.Get\(([^\)]+)\)\.onClick\s*=\s*(?:self\.|this\.)?([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE),
    re.compile(r"self\.([A-Za-z0-9_]+)\.AddClick\(\s*self\.([A-Za-z0-9_]+)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE),
]

CS_BIND_PATTERNS = [
    re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\.onClick\.AddListener\(\s*(?:this\.|)?([A-Za-z_][A-Za-z0-9_]*)\s*\)", re.IGNORECASE),
    re.compile(r"UIEventListener\.Get\([^\)]+\)\.onClick\s*=\s*(?:this\.|)?([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE),
    re.compile(r"self\.([A-Za-z_][A-Za-z0-9_]*)\.onClick\.AddListener\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", re.IGNORECASE),
    re.compile(r"new\s+Button\([^\)]*\)\.onClick\.AddListener\(\(\)\s*=>\s*([A-Za-z_][A-Za-z0-9_]*)\(\)\)", re.IGNORECASE),
]

LUA_FUNCTION_RE = re.compile(r"\blocal\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\b")
CS_FUNCTION_RE = re.compile(r"\b(?:public|private|protected|internal|static)?\s*(?:async\s+)?(?:void|bool|int|string|float|double|object|var|Task|IEnumerator|dynamic)?\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def normalize_runtime_path(path: str) -> str:
    if not path:
        return ""
    p = path.replace("\\", "/")
    p = "/".join(seg for seg in p.split("/") if seg)
    return p


def normalize_page_id(value: str) -> str:
    if not value:
        return ""
    s = value.replace("(Clone)", "")
    s = re.sub(r"\[[^\]]+\]", lambda m: m.group(0), s)
    m = re.search(r"\[([^\]]+)\]", value)
    if m and m.group(1):
        s = m.group(1)
    s = s.replace(" ", "").replace("\t", "")
    return s.strip()


def _should_parse_file(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    lower = path.replace("\\", "/").lower()
    if "/temp/" in lower or "\\temp\\" in lower:
        return False
    if not any(lower.endswith(ext) for ext in CODE_EXTS):
        return False
    try:
        if os.path.getsize(path) > MAX_CODE_FILE_BYTES:
            return False
    except Exception:
        return False
    for block in _EXCLUDED_DIRS:
        if f"/{block.lower()}/" in lower or f"\\{block.lower()}\\" in lower:
            return False
    return True


def _looks_like_ui_code(path: str, page_lookup: Optional[Dict[str, str]] = None) -> bool:
    lower = path.replace("\\", "/").lower()
    stem = Path(path).stem.lower()
    if any(h in lower for h in UI_CODE_HINTS):
        return True
    if stem.startswith("ui") or stem.endswith(("panel", "popup", "window", "view", "ctrl", "controller")):
        return True
    if page_lookup and stem in page_lookup:
        return True
    return False


def _iter_code_files_fast(root: str) -> List[str]:
    try:
        proc = subprocess.run(
            ["rg", "--files", root, "-g", "*.lua", "-g", "*.cs"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=20,
        )
        if proc.returncode not in (0, 1):
            return []
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _guess_page_candidates_from_filename(path: str) -> List[str]:
    base = Path(path).stem
    if not base:
        return []
    candidates = [normalize_page_id(base)]
    for suffix in ["Panel", "Window", "Popup", "Dialog", "Page", "UI", "View"]:
        if base.endswith(suffix):
            core = base[: -len(suffix)]
            candidates.append(core)
    return [x for x in dict.fromkeys([c for c in candidates if c])]


def _iter_bindings_from_lua(text: str, source_file: str) -> List[Dict[str, Any]]:
    bindings: List[Dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for rex in LUA_BIND_PATTERNS:
            for m in rex.finditer(line):
                node = (m.group(1) or m.group(0) or "").strip()
                handler = ""
                if m.lastindex and m.lastindex >= 2:
                    handler = (m.group(2) or m.group(1) or "").strip()
                if not handler:
                    handler = (m.group(m.lastindex or 1) or "").strip()
                bindings.append({
                    "target": node,
                    "handler": handler,
                    "handlerLine": i,
                    "sourceFile": source_file,
                    "bindingType": "lua_bind",
                    "lang": "lua",
                })
    return bindings


def _iter_bindings_from_cs(text: str, source_file: str) -> List[Dict[str, Any]]:
    bindings: List[Dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for rex in CS_BIND_PATTERNS:
            for m in rex.finditer(line):
                if not m:
                    continue
                groups = m.groups()
                target = (groups[0] if len(groups) > 0 else "").strip()
                handler = (groups[1] if len(groups) > 1 else "").strip()
                if not handler and len(groups) == 1:
                    handler = target
                bindings.append({
                    "target": target,
                    "handler": handler,
                    "handlerLine": i,
                    "sourceFile": source_file,
                    "bindingType": "cs_bind",
                    "lang": "cs",
                })
    return bindings


def _iter_functions(text: str, source_file: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    ignored = {
        "if", "for", "while", "switch", "catch", "using", "return", "new",
        "get", "set", "var", "int", "string", "bool", "float", "double",
    }
    for i, line in enumerate(text.splitlines(), start=1):
        for rex in (LUA_FUNCTION_RE, CS_FUNCTION_RE):
            for m in rex.finditer(line):
                name = (m.group(1) or "").strip()
                if len(name) >= 3 and name.lower() not in ignored:
                    out.append({
                        "handler": name,
                        "handlerLine": i,
                        "sourceFile": source_file,
                        "kind": "lua" if rex is LUA_FUNCTION_RE else "cs",
                    })
    return out


def _guess_action_type(text: str, handler_name: str) -> str:
    key = ((text or "") + " " + (handler_name or "")).lower()
    if re.search(r"\b(open|enter|show|进入|跳转|goto|go_to|switch)\b", key):
        return "open_page"
    if re.search(r"\b(close|关闭|退出|dismiss|hide|hidewindow)\b", key):
        return "close_popup"
    if re.search(r"\b(switch|tab|切换|change_tab)\b", key):
        return "switch_tab"
    if re.search(r"\b(select|选择|select_item|chosen|选中)\b", key):
        return "select_item"
    if re.search(r"\b(use|使用|consume|消耗)\b", key):
        return "use_item"
    if re.search(r"\b(buy|购买|purchase|支付|pay)\b", key):
        return "buy"
    if re.search(r"\b(claim|领取|get_reward|reward|领取奖励)\b", key):
        return "claim_reward"
    if re.search(r"\b(go|goto|jump|跳转场景|enter_scene)\b", key):
        return "go_to"
    if re.search(r"\b(drag|拖拽|滑动)\b", key):
        return "drag"
    if re.search(r"\b(scroll|滚动)\b", key):
        return "scroll"
    if re.search(r"\b(blank|cancel|取消|confirm|确认|ok)\b", key):
        return "close_popup"
    return "unknown"


def _guess_action_from_node(node_name: str, path: str, text: str = "") -> str:
    key = f"{node_name} {path} {text}".lower()
    if any(x in key for x in ("close", "btnclose", "back", "cancel", "关闭", "返回", "取消")):
        return "close_popup"
    if any(x in key for x in ("tab", "/tabs/", "/tab/", "页签")):
        return "switch_tab"
    if any(x in key for x in ("use", "usedbtn", "使用")):
        return "use_item"
    if any(x in key for x in ("propitem", "item_", "item/", "clickcontent", "icon")):
        return "select_item"
    if any(x in key for x in ("buy", "purchase", "shop", "购买")):
        return "buy"
    if any(x in key for x in ("claim", "reward", "award", "get", "领取", "奖励")):
        return "claim_reward"
    if any(x in key for x in ("goto", "go", "前往")):
        return "go_to"
    if key.endswith("/add") or "topres" in key and "add" in key:
        return "go_to"
    return "unknown"


def _infer_action_from_binding_text(text: str, handler_name: str = "") -> List[str]:
    key = ((text or "") + " " + (handler_name or "")).lower()
    out: List[str] = []
    if re.search(r"\b(selected|选择|current|isSelected|selectedIndex)\b", key):
        out.append("requires_selected_item")
    if re.search(r"\b(disabled|灰显|不可用|enable == false|not enough)\b", key):
        out.append("may_be_disabled")
    if re.search(r"\b(item|道具|prop|id|itemId)\b", key):
        out.append("item_related")
    if re.search(r"\b(net|协议|request|send|rpc|http)\b", key):
        out.append("server_action")
    if re.search(r"\b(open|enter|show|跳转|go_to|goto)\b", key):
        out.append("requires_scene_switch")
    return out


def _extract_rich_info(text: str, handler: str) -> Tuple[List[str], List[str], List[str]]:
    if not text or not handler:
        return [], [], []
    snippets = [line.strip() for line in text.splitlines() if handler in line][:4]
    lower = " ".join(snippets).lower()
    req = _infer_action_from_binding_text(lower, handler)
    exp = []
    risk = []

    if any(x in lower for x in ("openui", "showui", "switch")):
        exp.append("open_new_page")
    if any(x in lower for x in ("refresh", "刷新", "reload", "reload_ui")):
        exp.append("refresh_ui")
    if any(x in lower for x in ("close", "closeui", "hide", "dismiss")):
        exp.append("close_panel")

    if any(x in lower for x in ("null", "nil", "empty")):
        risk.append("可能空指针")
    if any(x in lower for x in ("request", "send", "protocol", "rpc", "server")):
        risk.append("服务器交互")
    return req, exp, risk


def _collect_code_symbols(project_root: str, page_nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    assets_root = os.path.join(project_root, "Assets") if os.path.isdir(os.path.join(project_root, "Assets")) else project_root
    pages = set([normalize_page_id(str(p.get("pageId") or "")) for p in page_nodes if p.get("pageId")])
    pages = {p for p in pages if p}
    page_lookup = {p.lower(): p for p in pages}
    for p in list(pages):
        low = p.lower()
        if low.startswith("ui"):
            page_lookup.setdefault(low[2:], p)
        for suffix in ("panel", "popup", "window", "view", "page"):
            if low.endswith(suffix):
                page_lookup.setdefault(low[: -len(suffix)], p)

    scripts = []
    fast_files = _iter_code_files_fast(assets_root)
    if fast_files:
        for f in fast_files:
            if _should_parse_file(f) and _looks_like_ui_code(f, page_lookup):
                scripts.append(f)
                if len(scripts) >= MAX_CODE_FILES:
                    break
    else:
        for root, dirs, files in os.walk(assets_root):
            dirs[:] = [d for d in dirs if d.lower() not in {x.lower() for x in _EXCLUDED_DIRS}]
            for fn in files:
                f = os.path.join(root, fn)
                if _should_parse_file(f) and _looks_like_ui_code(f, page_lookup):
                    scripts.append(f)
                    if len(scripts) >= MAX_CODE_FILES:
                        break
            if len(scripts) >= MAX_CODE_FILES:
                break

    buckets: Dict[str, List[str]] = {}
    for p in pages:
        buckets.setdefault(p, [])

    collected = {}
    for sf in sorted(scripts):
        try:
            rel = os.path.relpath(sf, project_root)
        except Exception:
            rel = sf
        txt = _read_text(sf)
        bindings = []
        if sf.lower().endswith(".lua"):
            bindings.extend(_iter_bindings_from_lua(txt, rel))
        else:
            bindings.extend(_iter_bindings_from_cs(txt, rel))

        handlers = _iter_functions(txt, rel)
        related_pages = set()
        low_sf = sf.lower().replace("\\", "/")
        for cand in _guess_page_candidates_from_filename(sf):
            c = cand.lower()
            if c in page_lookup:
                related_pages.add(page_lookup[c].lower())
            elif c.startswith("ui") and c[2:] in page_lookup:
                related_pages.add(page_lookup[c[2:]].lower())
        if not related_pages:
            parts = re.split(r"[/_.\-\\]+", low_sf)
            for part in parts:
                if part in page_lookup:
                    related_pages.add(page_lookup[part].lower())
        if not related_pages and (bindings or handlers):
            related_pages.add("")

        for pid in related_pages:
            collected.setdefault(pid, {
                "scripts": set(),
                "bindings": [],
                "handlers": [],
            })
            entry = collected[pid]
            entry["scripts"].add(rel)
            entry["bindings"].extend(bindings)
            entry["handlers"].extend(handlers)

    normalized: Dict[str, Dict[str, Any]] = {}
    for pid in collected:
        normalized[pid.lower()] = collected[pid]
    # 全局兜底索引：只保留明确无法归属页面的 UI 相关脚本，避免所有页面共用巨量脚本。
    normalized[""] = {
        "scripts": set(),
        "bindings": [],
        "handlers": [],
    }
    if "" in collected:
        normalized[""]["scripts"].update(collected[""].get("scripts", set()))
        normalized[""]["bindings"].extend(collected[""].get("bindings", []))
        normalized[""]["handlers"].extend(collected[""].get("handlers", []))
    return normalized


def _collect_node_records(ui_payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    if not isinstance(ui_payload, dict):
        return nodes

    if isinstance(ui_payload.get("nodes"), list):
        for n in ui_payload.get("nodes", []):
            if isinstance(n, dict) and isinstance(n.get("path"), str):
                p = dict(n)
                p.setdefault("runtimePath", p.get("path") )
                p.setdefault("pageId", "Unknown")
                nodes.append(p)

    if isinstance(ui_payload.get("prefabs"), list):
        for p in ui_payload.get("prefabs") or []:
            if not isinstance(p, dict):
                continue
            prefab_path = p.get("assetPath") or p.get("prefab") or p.get("path") or ""
            page_id = p.get("pageId") or p.get("name") or os.path.splitext(os.path.basename(prefab_path))[0] or "Unknown"
            for node in p.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                nn = dict(node)
                nn.setdefault("runtimePath", nn.get("path", ""))
                nn["pageId"] = page_id
                nn["prefabPath"] = prefab_path
                if nn.get("path"):
                    nodes.append(nn)

    if isinstance(ui_payload.get("pages"), list):
        for page in ui_payload.get("pages") or []:
            if not isinstance(page, dict):
                continue
            page_id = page.get("pageId") or page.get("name") or "Unknown"
            prefab_path = page.get("prefab") or page.get("prefabPath") or ""
            for node in page.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                nn = dict(node)
                nn.setdefault("runtimePath", nn.get("path", ""))
                nn["pageId"] = page_id
                nn["prefabPath"] = prefab_path
                if nn.get("path"):
                    nodes.append(nn)

    # 去重
    uniq = {}
    for n in nodes:
        key = f"{n.get('pageId')}|{n.get('runtimePath')}|{n.get('path')}"
        if key not in uniq:
            uniq[key] = n
    return list(uniq.values())


def _match_node_to_binding(node_name: str, node_path: str, binding: Dict[str, Any]) -> float:
    target = (binding.get("target") or "").strip().lower()
    if not target:
        return 0.0
    n = (node_name or "").strip().lower()
    p = normalize_runtime_path(node_path).lower()
    score = 0.0
    if n and n == target:
        score = 1.0
    elif n and n in target:
        score = 0.72
    elif target in n and n and len(n) > 2:
        score = 0.60
    elif target and p and target in p:
        score = 0.55
    return score


def build_ui_code_semantics(
    project_root: str,
    ui_payload: Optional[Dict[str, Any]] = None,
    output_path: str = "",
    alias_rules: Optional[Dict[str, Any]] = None,
    page_type_rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not project_root or not os.path.isdir(project_root):
        return {"success": False, "error": "未配置可用的 Unity 工程目录"}

    project_root = os.path.abspath(project_root)
    if not isinstance(ui_payload, dict):
        return {"success": False, "error": "未找到可用UI数据"}

    nodes = _collect_node_records(ui_payload)
    if not nodes:
        return {"success": False, "error": "未解析到UI节点（nodes/pages/prefabs空）"}

    symbol_bucket = _collect_code_symbols(project_root, [{"pageId": n.get("pageId", "") } for n in nodes])
    if not symbol_bucket:
        return {"success": False, "error": "未扫描到可用代码文件"}

    alias_rules = alias_rules or {}
    aliases = alias_rules.get("rules", []) if isinstance(alias_rules, dict) else []

    result: Dict[str, Any] = {
        "schemaVersion": "ui_code_semantics/v1",
        "generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "projectRoot": project_root,
        "rules": {
            "runtimePathAliases": aliases,
            "pageTypeRules": page_type_rules or {},
        },
        "pages": {},
    }

    def normalize_alias(path_value: str) -> str:
        p = normalize_runtime_path(path_value)
        for rule in aliases:
            if not isinstance(rule, dict):
                continue
            pattern = rule.get("pattern")
            replacement = rule.get("replace")
            if not pattern or replacement is None:
                continue
            p = p.replace(pattern, replacement)
        return p

    for node in nodes:
        page_id = normalize_page_id(str(node.get("pageId", "") or "Unknown")) or "Unknown"
        page_bucket = result["pages"].setdefault(page_id, {
            "prefab": node.get("prefabPath", ""),
            "scripts": [],
            "elements": {},
        })
        path = normalize_alias(node.get("runtimePath") or node.get("path") or "")
        if not path:
            continue
        node_name = node.get("nodeName") or node.get("name") or ""
        text = str(node.get("text") or node.get("textContent") or "").strip()
        page_bucket["prefab"] = page_bucket.get("prefab") or node.get("prefabPath", "")

        page_key = page_id.lower()
        bucket = symbol_bucket.get(page_key)

        candidates = bucket.get("bindings", []) if isinstance(bucket, dict) else []
        handlers = bucket.get("handlers", []) if isinstance(bucket, dict) else []
        script_names = list(bucket.get("scripts", set()) if isinstance(bucket, dict) else []) if isinstance(bucket, dict) else []

        best = None
        best_score = 0.0
        for b in candidates:
            s = _match_node_to_binding(node_name, path, b)
            if s > best_score:
                best_score = s
                best = b

        if not best:
            for h in handlers:
                handler = (h.get("handler") or "").strip()
                if not handler:
                    continue
                low = handler.lower()
                if (low in (node_name or "").lower()) or (low in text.lower()) or (low in path.lower()):
                    if 0.35 > best_score:
                        best_score = 0.35
                        best = {
                            "target": node_name,
                            "handler": handler,
                            "handlerLine": h.get("handlerLine", 0),
                            "sourceFile": h.get("sourceFile", ""),
                            "bindingType": "function_infer",
                            "lang": h.get("kind", ""),
                        }

        if not best:
            confidence = 0.0
            handler_name = ""
            action = "unknown"
        else:
            handler_name = best.get("handler", "")
            source_file = best.get("sourceFile", "")
            handler_key = str(source_file) + "::" + str(handler_name)
            requires = _infer_action_from_binding_text(text, handler_name)
            req, exp, risk = _extract_rich_info(text, handler_name)
            action = _guess_action_type(text, handler_name)
            confidence = round(float(best_score + (0.1 if action != "unknown" else 0.0)), 3)
            if confidence > 1.0:
                confidence = 1.0
            page_bucket["elements"][path] = {
                "runtimePath": path,
                "nodeName": node_name,
                "handler": handler_name,
                "businessAction": handler_name or action,
                "handlerFile": [source_file] if source_file else [],
                "handlerLine": best.get("handlerLine", 0),
                "requiresState": list(dict.fromkeys(requires + req)) if isinstance(requires, list) else [],
                "expectedResult": exp,
                "targetPage": page_id,
                "risk": risk if risk else (["matched_by_code_pattern"] if best else ["unresolved"]),
                "sourceFiles": [source_file] if source_file else [],
                "actionType": action,
                "confidence": confidence,
                "codeSemantic": {
                    "status": "matched" if confidence >= 0.6 else "weak_match",
                    "handler": handler_name,
                    "actionType": action,
                    "businessAction": handler_name or action,
                    "expectedResult": exp,
                    "sourceFiles": [source_file] if source_file else [],
                    "confidence": confidence,
                },
            }
            for sf in script_names:
                if sf not in page_bucket["scripts"]:
                    page_bucket["scripts"].append(sf)

        if not best:
            fallback_action = _guess_action_from_node(node_name, path, text)
            fallback_conf = 0.35 if fallback_action != "unknown" else 0.0
            page_bucket["elements"][path] = {
                "runtimePath": path,
                "nodeName": node_name,
                "handler": "",
                "businessAction": fallback_action,
                "handlerFile": [],
                "handlerLine": 0,
                "targetPage": page_id,
                "requiresState": [],
                "expectedResult": [],
                "risk": ["heuristic_semantic"] if fallback_action != "unknown" else ["unresolved"],
                "sourceFiles": [],
                "actionType": fallback_action,
                "confidence": fallback_conf,
                "codeSemantic": {
                    "status": "heuristic" if fallback_action != "unknown" else "unmatched",
                    "handler": "",
                    "actionType": fallback_action,
                    "businessAction": fallback_action,
                    "expectedResult": [],
                    "sourceFiles": [],
                    "confidence": fallback_conf,
                },
            }

            
    total_elements = sum(len(v.get("elements", {})) for v in result["pages"].values())
    matched_elements = 0
    for page_bucket in result["pages"].values():
        for item in (page_bucket.get("elements") or {}).values():
            if isinstance(item, dict) and item.get("codeSemantic", {}).get("status") == "matched":
                matched_elements += 1

    result["stats"] = {
        "pages": len(result["pages"]),
        "elements": total_elements,
        "pageCount": len(result["pages"]),
        "elementCount": total_elements,
        "matchedElements": matched_elements,
        "unmatchedElements": max(total_elements - matched_elements, 0),
        "scriptFiles": len({
            sf for page in result["pages"].values() for sf in page.get("scripts", []) if sf
        }),
    }

    if not output_path:
        output_path = os.path.join(project_root, "metadata", "ui_code_semantics.json")

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return {
        "success": True,
        "summary": result["stats"],
        "path": output_path,
        "data": result,
    }
