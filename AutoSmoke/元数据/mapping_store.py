#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Page-sharded mapping store for AutoSmoke.

This module is the compatibility layer between the legacy large JSON files and
the new mapping_store layout. Business code should use this class instead of
reading or writing mapping JSON files directly.
"""

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


CONFIRMED_FORMAL_STATUSES = {
    "visual_confirmed",
    "click_confirmed",
    "case_verified",
    "manual_confirmed",
    "collection_confirmed",
    "template",
}

REVIEW_STATUS_RANK = {
    "": 0,
    "pending": 0,
    "auto_draft": 0,
    "manual": 1,
    "confirmed": 1,
    "manual_confirmed": 2,
    "runtime_matched": 3,
    "visual_confirmed": 4,
    "click_confirmed": 5,
    "collection_confirmed": 5,
    "case_verified": 6,
    "template": 6,
}


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _status_from_evidence(evidence: Dict[str, Any]) -> str:
    if not isinstance(evidence, dict):
        return ""
    click = _coerce_dict(evidence.get("click"))
    visual = _coerce_dict(evidence.get("visual"))
    runtime = _coerce_dict(evidence.get("runtime"))
    if click.get("confirmed") is True or _safe_text(click.get("result")).upper() == "PASS":
        return "click_confirmed"
    if visual.get("confirmed") is True:
        return "visual_confirmed"
    if runtime.get("matched") is True:
        return "runtime_matched"
    return ""


def _stronger_review_status(current: Any, evidence_status: Any) -> str:
    current_text = _safe_text(current)
    evidence_text = _safe_text(evidence_status)
    if not evidence_text:
        return "manual_confirmed" if current_text in {"manual", "confirmed"} else current_text
    return evidence_text if REVIEW_STATUS_RANK.get(evidence_text, 0) > REVIEW_STATUS_RANK.get(current_text, 0) else current_text


def _safe_file_id(value: Any, fallback: str = "item") -> str:
    text = _safe_text(value).lower()
    text = text.replace("/", ".").replace("\\", ".")
    text = re.sub(r"[^a-z0-9_.]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_.")
    return text or fallback


def _path_variants(value: Any) -> set:
    text = _safe_text(value).replace("\\", "/").strip()
    if not text:
        return set()
    values = {text.strip("/")}
    if text.startswith("__runtime__::"):
        tail = text[len("__runtime__::"):]
        values.add(tail.strip("/"))
        if "::" in tail:
            values.add(tail.split("::")[-1].strip("/"))
        values.add(tail.replace("::", "/").strip("/"))
    if "::" in text:
        values.add(text.split("::")[-1].strip("/"))
    for prefix in ("DeepUI/LayerUI/", "content/"):
        if text.startswith(prefix):
            values.add(text[len(prefix):].strip("/"))
    parts = text.split("/")
    if "Root" in parts:
        tail = "/".join(parts[parts.index("Root") + 1:]).strip("/")
        if tail:
            values.add(tail)
    return {v for v in values if v}


def _paths_overlap(left: Any, right: Any) -> bool:
    lv = _path_variants(left)
    rv = _path_variants(right)
    if not lv or not rv:
        return False
    if lv.intersection(rv):
        return True
    for a in lv:
        for b in rv:
            if a.endswith("/" + b) or b.endswith("/" + a):
                return True
    return False


def _stable_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha1(_safe_text(value).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _coerce_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _looks_mojibake(value: Any) -> bool:
    text = _safe_text(value)
    if not text:
        return False
    markers = ("鑳", "鍟", "绁", "涓", "瑙", "鏈", "璋", "閬", "鐣", "潰", "교관")
    return any(marker in text for marker in markers)


_PAGE_WORD_EN = {
    "背包": "bag",
    "道具": "prop",
    "物品": "item",
    "神器": "artifact",
    "商城": "shop",
    "商店": "shop",
    "任务": "task",
    "主城": "main_city",
    "角色": "character",
    "信息": "info",
    "联盟": "alliance",
    "科技": "tech",
    "英雄": "hero",
    "装备": "equipment",
    "资源": "resource",
    "加速": "speedup",
    "活动": "activity",
    "奖励": "reward",
    "邮件": "mail",
    "好友": "friend",
    "设置": "settings",
    "客服": "customer_service",
    "排行": "ranking",
    "竞技": "arena",
    "战斗": "battle",
}


def _suggest_english_id_from_zh(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    tokens = []
    rest = text
    for zh, en in sorted(_PAGE_WORD_EN.items(), key=lambda kv: len(kv[0]), reverse=True):
        if zh in rest:
            tokens.append(en)
            rest = rest.replace(zh, " ")
    if tokens:
        out = "_".join(tokens)
        out = re.sub(r"_+", "_", out).strip("_")
        return out[:80]
    ascii_id = re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_").lower()
    return re.sub(r"_+", "_", ascii_id)[:80]


class MappingStore:
    """Read/write AutoSmoke mappings through the new sharded storage layout."""

    def __init__(self, project_root: Any = None):
        self.project_root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parents[1]
        self.metadata_dir = self.project_root / "metadata"
        self.legacy_draft_path = self.project_root / "元数据" / "element_mapping_draft.json"
        self.legacy_formal_path = self.metadata_dir / "element_mapping_formal.json"
        self.legacy_evidence_path = self.metadata_dir / "mapping_evidence.json"
        self.store_dir = self.metadata_dir / "mapping_store"
        self.index_dir = self.store_dir / "indexes"
        self.page_dir = self.store_dir / "pages"
        self.draft_page_dir = self.store_dir / "draft" / "by_page"
        self.draft_queue_dir = self.store_dir / "draft" / "queues"
        self.formal_page_dir = self.store_dir / "formal" / "by_page"
        self.formal_global_dir = self.store_dir / "formal" / "global"
        self.evidence_page_dir = self.store_dir / "evidence" / "by_page"
        self.evidence_testid_dir = self.store_dir / "evidence" / "by_testid"
        self.asset_dir = self.store_dir / "evidence" / "assets"
        self.highlight_dir = self.asset_dir / "highlights"
        self.screenshot_asset_dir = self.asset_dir / "screenshots"
        self.click_log_dir = self.asset_dir / "click_logs"
        self._suspend_rebuild = False

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _ensure_dirs(self) -> None:
        for path in [
            self.index_dir,
            self.page_dir,
            self.draft_page_dir,
            self.draft_queue_dir,
            self.formal_page_dir,
            self.formal_global_dir,
            self.evidence_page_dir,
            self.evidence_testid_dir,
            self.highlight_dir,
            self.screenshot_asset_dir,
            self.click_log_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def metadata_relpath(self, path: Any) -> str:
        text = _safe_text(path)
        if not text:
            return ""
        p = Path(text)
        try:
            if p.is_absolute():
                return p.resolve().relative_to(self.metadata_dir.resolve()).as_posix()
        except Exception:
            pass
        try:
            if p.is_absolute():
                return p.resolve().relative_to(self.project_root.resolve()).as_posix()
        except Exception:
            pass
        return text.replace("\\", "/")

    def resolve_metadata_path(self, value: Any) -> Path:
        text = _safe_text(value).replace("\\", "/")
        if not text:
            return self.metadata_dir
        p = Path(text)
        if p.is_absolute():
            return p
        if text.startswith("metadata/"):
            return self.project_root / text
        return self.metadata_dir / text

    @staticmethod
    def _read_json(path: Path, fallback: Any = None) -> Any:
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            return fallback
        return fallback

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Page resolution
    # ------------------------------------------------------------------

    def _default_page_dictionary(self) -> Dict[str, Any]:
        return {
            "schema_version": "page_name_dictionary.v1",
            "updated_at": _now_text(),
            "pages": [
                {"pageId": "bag", "displayName": "背包界面", "aliases": ["背包", "道具背包", "物品界面"]},
                {"pageId": "artifact", "displayName": "神器界面", "aliases": ["神器", "神器功能", "神器养成"]},
                {"pageId": "shop", "displayName": "商城界面", "aliases": ["商店", "商城"]},
                {"pageId": "task", "displayName": "任务界面", "aliases": ["任务"]},
                {"pageId": "main_city", "displayName": "主城界面", "aliases": ["主城"]},
                {"pageId": "character_info", "displayName": "角色信息界面", "aliases": ["角色信息", "角色界面"]},
                {"pageId": "unknown", "displayName": "未知界面", "aliases": ["未知"]},
                {"pageId": "debug", "displayName": "调试界面", "aliases": ["debug", "Debug", "GraphicDebug", "Framework"]},
            ],
        }

    def page_dictionary_path(self) -> Path:
        return self.page_dir / "page_name_dictionary.json"

    def load_page_dictionary(self) -> Dict[str, Any]:
        self._ensure_dirs()
        path = self.page_dictionary_path()
        data = self._read_json(path)
        if not isinstance(data, dict):
            data = self._default_page_dictionary()
            self._write_json(path, data)
        pages = _coerce_list(data.get("pages"))
        changed = False
        defaults = self._default_page_dictionary()["pages"]
        existing = {_safe_text(p.get("pageId")) for p in pages if isinstance(p, dict)}
        defaults_by_id = {_safe_text(p.get("pageId")): p for p in defaults if isinstance(p, dict)}
        for item in defaults:
            if item["pageId"] not in existing:
                pages.append(item)
                changed = True
        for item in pages:
            if not isinstance(item, dict):
                continue
            page_id = self.normalize_page_id(item.get("pageId"))
            item["pageId"] = page_id
            default_item = defaults_by_id.get(page_id)
            if default_item:
                if _looks_mojibake(item.get("displayName")):
                    item["displayName"] = default_item.get("displayName", item.get("displayName"))
                    changed = True
                aliases = _coerce_list(item.get("aliases"))
                if aliases and any(_looks_mojibake(alias) for alias in aliases):
                    item["aliases"] = list(default_item.get("aliases", aliases))
                    changed = True
            item.setdefault("files", {
                "draft": f"mapping_store/draft/by_page/{page_id}.json",
                "formal": f"mapping_store/formal/by_page/{page_id}.json",
            })
        data["pages"] = pages
        if changed:
            data["updated_at"] = _now_text()
            self._write_json(path, data)
        return data

    def normalize_page_id(self, value: Any) -> str:
        text = _safe_text(value)
        if not text:
            return "unknown"
        lowered = text.lower()
        if any(token in lowered for token in ["debug", "graphicdebug", "framework"]):
            return "debug"
        text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
        text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
        text = re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_").lower()
        text = re.sub(r"_+", "_", text)
        if not text:
            return "unknown"
        if text in {"ui", "uishop", "root", "page"}:
            return "unknown"
        return text[:80]

    def resolve_page_id(self, target_name: str = "", current_page_id: str = "", item: Dict[str, Any] = None) -> Dict[str, Any]:
        item = item if isinstance(item, dict) else {}
        dictionary = self.load_page_dictionary()
        text = " ".join([
            _safe_text(target_name),
            _safe_text(item.get("targetName")),
            _safe_text(item.get("displayName")),
            _safe_text(item.get("chineseDescription")),
        ])
        lowered = text.lower()
        best = None
        for page in _coerce_list(dictionary.get("pages")):
            if not isinstance(page, dict):
                continue
            aliases = [_safe_text(page.get("displayName"))] + [_safe_text(v) for v in _coerce_list(page.get("aliases"))]
            aliases += [_safe_text(page.get("pageId"))]
            for alias in aliases:
                if alias and alias.lower() in lowered:
                    if not best or len(alias) > len(best.get("alias", "")):
                        best = {"pageId": self.normalize_page_id(page.get("pageId")), "displayName": page.get("displayName", ""), "source": "dictionary", "alias": alias}
        if best:
            return best
        for key in ["pageId", "pageHint"]:
            if item.get(key):
                page_id = self.normalize_page_id(item.get(key))
                return {"pageId": page_id, "displayName": page_id, "source": key}
        if current_page_id:
            page_id = self.normalize_page_id(current_page_id)
            return {"pageId": page_id, "displayName": page_id, "source": "current_page_id"}
        path_text = " ".join([_safe_text(item.get(k)) for k in ["elementPath", "path", "runtimePath", "selectedDraftPath"]])
        lower_path = path_text.lower()
        if any(token in lower_path for token in ["debug", "graphicdebug", "framework"]):
            return {"pageId": "debug", "displayName": "调试界面", "source": "path_debug"}
        if "shop" in lower_path or "uishop" in lower_path:
            return {"pageId": "bag" if "bag" in lower_path else "shop", "displayName": "背包界面" if "bag" in lower_path else "商城界面", "source": "path_hint"}
        return {"pageId": "unknown", "displayName": "未知界面", "source": "fallback"}

    def suggest_page(self, target_name: str = "", current_page_id: str = "", item: Dict[str, Any] = None) -> Dict[str, Any]:
        item = item if isinstance(item, dict) else {}
        resolved = self.resolve_page_id(target_name, current_page_id, item)
        if resolved.get("pageId") not in {"", "unknown"} and resolved.get("source") == "dictionary":
            resolved["exists"] = True
            resolved["createRequired"] = False
            return resolved
        text = " ".join([
            _safe_text(target_name),
            _safe_text(item.get("targetName")),
            _safe_text(item.get("displayName")),
            _safe_text(item.get("chineseDescription")),
        ])
        page_name = ""
        marker = "界面"
        marker_index = text.find(marker)
        if marker_index >= 0:
            start = marker_index
            while start > 0:
                ch = text[start - 1]
                if re.match(r"[\u4e00-\u9fffA-Za-z0-9_]", ch):
                    start -= 1
                    continue
                break
            page_name = text[start:marker_index + len(marker)]
        elif current_page_id:
            page_name = current_page_id
        suggested = _suggest_english_id_from_zh(page_name.replace("界面", "")) if page_name else ""
        if not suggested or suggested == "unknown":
            suggested = resolved.get("pageId") if resolved.get("pageId") != "unknown" else ""
        suggested = self.normalize_page_id(suggested)
        exists = False
        dictionary = self.load_page_dictionary()
        for page in _coerce_list(dictionary.get("pages")):
            if isinstance(page, dict) and self.normalize_page_id(page.get("pageId")) == suggested:
                exists = True
                break
        return {
            "pageId": suggested or "unknown",
            "displayName": page_name or resolved.get("displayName") or suggested or "未知界面",
            "source": "suggested_from_target_name" if page_name else resolved.get("source", "fallback"),
            "exists": exists,
            "createRequired": bool(suggested and not exists and suggested != "unknown"),
            "files": {
                "draft": f"mapping_store/draft/by_page/{suggested or 'unknown'}.json",
                "formal": f"mapping_store/formal/by_page/{suggested or 'unknown'}.json",
            },
            "resolved": resolved,
        }

    def ensure_page(self, page_id: str, display_name: str = "", aliases: List[str] = None) -> Dict[str, Any]:
        page_id = self.normalize_page_id(page_id)
        if not page_id or page_id == "unknown":
            return {"success": False, "error": "valid pageId is required"}
        display_name = _safe_text(display_name) or page_id
        aliases = [a for a in _coerce_list(aliases) if _safe_text(a)]
        dictionary = self.load_page_dictionary()
        pages = _coerce_list(dictionary.get("pages"))
        found = None
        for page in pages:
            if isinstance(page, dict) and self.normalize_page_id(page.get("pageId")) == page_id:
                found = page
                break
        is_new = found is None
        if found is None:
            found = {"pageId": page_id, "displayName": display_name, "aliases": aliases}
            pages.append(found)
        else:
            found["displayName"] = found.get("displayName") or display_name
            merged_aliases = list(found.get("aliases") or [])
            for alias in aliases:
                if alias not in merged_aliases:
                    merged_aliases.append(alias)
            found["aliases"] = merged_aliases
        found["files"] = {
            "draft": f"mapping_store/draft/by_page/{page_id}.json",
            "formal": f"mapping_store/formal/by_page/{page_id}.json",
        }
        final_display_name = _safe_text(found.get("displayName")) or display_name
        dictionary["pages"] = pages
        dictionary["updated_at"] = _now_text()
        self._write_json(self.page_dictionary_path(), dictionary)
        draft = self._load_page_drafts(page_id)
        if is_new or not _safe_text(draft.get("displayName")):
            draft["displayName"] = final_display_name
        self._save_page_drafts(page_id, draft)
        formal = self._load_page_formal(page_id)
        if is_new or not _safe_text(formal.get("displayName")):
            formal["displayName"] = final_display_name
        self._save_page_formal(page_id, formal)
        indexes = self.rebuild_indexes()
        return {
            "success": True,
            "page": found,
            "pageId": page_id,
            "displayName": final_display_name,
            "files": found["files"],
            "indexes": indexes,
        }

    # ------------------------------------------------------------------
    # Legacy loading
    # ------------------------------------------------------------------

    def has_store(self) -> bool:
        return (self.store_dir / "manifest.json").exists()

    def list_pages(self, keyword: str = "", limit: int = 300, offset: int = 0) -> Dict[str, Any]:
        if self.has_store():
            page_index = self._read_json(self.index_dir / "page.index.json", {})
            alias_index = self._read_json(self.index_dir / "page_alias.index.json", {})
        else:
            self.migrate_from_legacy(export_legacy=False)
            page_index = self._read_json(self.index_dir / "page.index.json", {})
            alias_index = self._read_json(self.index_dir / "page_alias.index.json", {})
        pages = _coerce_dict(page_index.get("pages")) if isinstance(page_index, dict) else {}
        keyword = _safe_text(keyword).lower()
        limit = max(1, min(int(limit or 300), 2000))
        offset = max(0, int(offset or 0))
        items = []
        for page_id, info in pages.items():
            if not isinstance(info, dict):
                continue
            item = dict(info)
            item["pageId"] = page_id
            item["totalCount"] = int(item.get("draftCount", 0) or 0) + int(item.get("mappingCount", 0) or 0)
            if keyword and keyword not in json.dumps(item, ensure_ascii=False).lower():
                continue
            items.append(item)
        items.sort(key=lambda x: (-(x.get("totalCount") or 0), x.get("pageId", "")))
        return {
            "success": True,
            "total": len(items),
            "returned": len(items[offset:offset + limit]),
            "offset": offset,
            "limit": limit,
            "pages": items[offset:offset + limit],
            "aliasCount": len(_coerce_dict(alias_index.get("aliases"))) if isinstance(alias_index, dict) else 0,
            "aliasPath": self.metadata_relpath(self.index_dir / "page_alias.index.json"),
        }

    def _legacy_drafts(self) -> List[Dict[str, Any]]:
        data = self._read_json(self.legacy_draft_path, {})
        drafts = data.get("drafts") if isinstance(data, dict) else []
        if isinstance(drafts, dict):
            drafts = list(drafts.values())
        return [d for d in _coerce_list(drafts) if isinstance(d, dict)]

    def _legacy_formal(self) -> Dict[str, Dict[str, Any]]:
        data = self._read_json(self.legacy_formal_path, {})
        mappings = data.get("mappings") if isinstance(data, dict) else {}
        if isinstance(mappings, list):
            return {m.get("testId") or _stable_id("formal", m.get("elementPath") or m.get("path")): m for m in mappings if isinstance(m, dict)}
        return {k: v for k, v in _coerce_dict(mappings).items() if isinstance(v, dict)}

    def _legacy_evidence(self) -> Dict[str, Dict[str, Any]]:
        data = self._read_json(self.legacy_evidence_path, {})
        evidence = data.get("evidence") if isinstance(data, dict) else {}
        if isinstance(evidence, list):
            return {e.get("evidenceRef") or f"EVIDENCE_{e.get('testId')}" or _stable_id("evidence", e): e for e in evidence if isinstance(e, dict)}
        return {k: v for k, v in _coerce_dict(evidence).items() if isinstance(v, dict)}

    # ------------------------------------------------------------------
    # Draft operations
    # ------------------------------------------------------------------

    def draft_id_for(self, draft: Dict[str, Any]) -> str:
        return _safe_text(draft.get("draftId")) or _stable_id("DRAFT", draft.get("elementPath") or draft.get("path") or draft)

    def _draft_page_path(self, page_id: str) -> Path:
        return self.draft_page_dir / f"{self.normalize_page_id(page_id)}.json"

    def _formal_page_path(self, page_id: str) -> Path:
        return self.formal_page_dir / f"{self.normalize_page_id(page_id)}.json"

    def _formal_global_path(self, scope: str) -> Path:
        return self.formal_global_dir / f"{_safe_file_id(scope)}.json"

    def _evidence_testid_path(self, page_id: str, test_id: str) -> Path:
        return self.evidence_testid_dir / self.normalize_page_id(page_id) / f"{_safe_file_id(test_id)}.json"

    def _load_page_drafts(self, page_id: str) -> Dict[str, Any]:
        path = self._draft_page_path(page_id)
        data = self._read_json(path, {})
        if not isinstance(data, dict):
            data = {}
        data.setdefault("schema_version", "element_mapping_draft.page.v1")
        data.setdefault("pageId", self.normalize_page_id(page_id))
        data.setdefault("displayName", data.get("pageId", ""))
        data.setdefault("drafts", {})
        data.setdefault("groups", {})
        if isinstance(data.get("drafts"), list):
            data["drafts"] = {self.draft_id_for(d): d for d in data["drafts"] if isinstance(d, dict)}
        if not isinstance(data.get("drafts"), dict):
            data["drafts"] = {}
        return data

    def _save_page_drafts(self, page_id: str, data: Dict[str, Any]) -> None:
        data["pageId"] = self.normalize_page_id(page_id)
        data["updated_at"] = _now_text()
        data["count"] = len(_coerce_dict(data.get("drafts")))
        self._write_json(self._draft_page_path(page_id), data)

    def save_draft(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_dirs()
        if not isinstance(draft, dict):
            return {"success": False, "error": "draft must be object"}
        page = self.resolve_page_id(item=draft)
        page_id = page["pageId"]
        draft_id = self.draft_id_for(draft)
        item = dict(draft)
        item["draftId"] = draft_id
        item["pageId"] = page_id
        for key in ["path", "elementPath"]:
            if item.get(key):
                item[key] = self.metadata_relpath(item[key])
        data = self._load_page_drafts(page_id)
        data["displayName"] = page.get("displayName") or data.get("displayName") or page_id
        data["drafts"][draft_id] = item
        self._save_page_drafts(page_id, data)
        if not self._suspend_rebuild:
            self.rebuild_indexes()
        return {"success": True, "draft": item, "draftId": draft_id, "pageId": page_id, "draftPath": self.metadata_relpath(self._draft_page_path(page_id))}

    def list_drafts(self, page_id: str = "", status: str = "", keyword: str = "", limit: int = 300, offset: int = 0, group: str = "") -> Dict[str, Any]:
        page_id = self.canonicalize_page_alias(page_id) if page_id else ""
        group = _safe_text(group)
        if not self.has_store():
            drafts = self._legacy_drafts()
        else:
            drafts = []
            paths = [self._draft_page_path(page_id)] if page_id else sorted(self.draft_page_dir.glob("*.json"))
            for path in paths:
                data = self._read_json(path, {})
                raw = data.get("drafts") if isinstance(data, dict) else {}
                if group and isinstance(raw, dict):
                    group_ids = []
                    groups = data.get("groups") if isinstance(data, dict) else {}
                    if isinstance(groups, dict):
                        group_ids = groups.get(group) or []
                    if isinstance(group_ids, list):
                        if group_ids:
                            drafts.extend([raw.get(draft_id) for draft_id in group_ids if isinstance(raw.get(draft_id), dict)])
                        else:
                            drafts.extend([d for d in raw.values() if isinstance(d, dict) and self.classify_group(d) == group])
                        continue
                values = raw.values() if isinstance(raw, dict) else raw if isinstance(raw, list) else []
                drafts.extend([d for d in values if isinstance(d, dict)])
        if group and not self.has_store():
            drafts = [d for d in drafts if self.classify_group(d) == group]
        if status:
            drafts = [d for d in drafts if (d.get("reviewStatus") or d.get("source") or d.get("status")) == status]
        if keyword:
            kw = keyword.lower()
            drafts = [d for d in drafts if kw in json.dumps(d, ensure_ascii=False).lower()]
        total = len(drafts)
        offset = max(0, int(offset or 0))
        limit = max(1, min(int(limit or 300), 50000))
        return {"success": True, "total": total, "returned": min(max(total - offset, 0), limit), "drafts": drafts[offset:offset + limit]}

    def get_draft(self, draft_id_or_path: str) -> Dict[str, Any]:
        key = _safe_text(draft_id_or_path)
        if not key:
            return {}
        result = self.list_drafts(limit=50000)
        for draft in result.get("drafts", []):
            if key in {_safe_text(draft.get("draftId")), _safe_text(draft.get("path")), _safe_text(draft.get("elementPath"))}:
                return draft
        return {}

    def ignore_draft(self, draft_id_or_path: str, reason: str = "") -> Dict[str, Any]:
        draft = self.get_draft(draft_id_or_path)
        if not draft:
            return {"success": False, "error": "draft_not_found"}
        draft["reviewStatus"] = "ignored"
        draft["ignoredReason"] = reason or "user_ignored"
        draft["ignoredAt"] = _now_text()
        return self.save_draft(draft)

    def reject_draft(self, draft_id_or_path: str, reason: str = "") -> Dict[str, Any]:
        draft = self.get_draft(draft_id_or_path)
        if not draft:
            return {"success": False, "error": "draft_not_found"}
        draft["reviewStatus"] = "rejected"
        draft["rejectedReason"] = reason or "user_rejected"
        draft["rejectedAt"] = _now_text()
        return self.save_draft(draft)

    # ------------------------------------------------------------------
    # Formal/evidence operations
    # ------------------------------------------------------------------

    def _load_page_formal(self, page_id: str) -> Dict[str, Any]:
        data = self._read_json(self._formal_page_path(page_id), {})
        if not isinstance(data, dict):
            data = {}
        data.setdefault("schema_version", "element_mapping_formal.page.v1")
        data.setdefault("pageId", self.normalize_page_id(page_id))
        data.setdefault("displayName", data.get("pageId", ""))
        data.setdefault("mappings", {})
        data.setdefault("groups", {})
        if not isinstance(data.get("mappings"), dict):
            data["mappings"] = {}
        return data

    def _save_page_formal(self, page_id: str, data: Dict[str, Any]) -> None:
        data["pageId"] = self.normalize_page_id(page_id)
        data["updated_at"] = _now_text()
        data["count"] = len(_coerce_dict(data.get("mappings")))
        self._write_json(self._formal_page_path(page_id), data)

    def upsert_formal(self, item: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_dirs()
        if not isinstance(item, dict):
            return {"success": False, "error": "formal item must be object"}
        test_id = _safe_text(item.get("testId"))
        if not test_id:
            return {"success": False, "error": "testId is required"}
        page = self.resolve_page_id(item.get("targetName") or item.get("displayName"), item.get("pageId"), item)
        page_id = page["pageId"]
        saved = dict(item)
        saved["pageId"] = page_id
        saved.setdefault("evidenceRef", f"EVIDENCE_{test_id}")
        evidence_status = _status_from_evidence(self.get_evidence(evidence_ref=saved.get("evidenceRef", ""), test_id=test_id))
        normalized_status = _stronger_review_status(saved.get("reviewStatus"), evidence_status)
        if normalized_status:
            saved["reviewStatus"] = normalized_status
            if normalized_status in {"click_confirmed", "visual_confirmed", "case_verified", "collection_confirmed"} and saved.get("source") in {"manual", "manual_corrected", "confirmed", ""}:
                saved["source"] = "target_workbench"
        for key in ["formalPath", "evidencePath"]:
            saved.pop(key, None)
        incoming_path = saved.get("elementPath") or saved.get("path") or saved.get("draftPath") or _coerce_dict(saved.get("locator")).get("value")
        existing = self.get_formal_by_testid(test_id)
        if isinstance(existing, dict) and existing:
            existing_path = existing.get("elementPath") or existing.get("path") or existing.get("draftPath") or _coerce_dict(existing.get("locator")).get("value")
            if (
                incoming_path
                and existing_path
                and not _paths_overlap(incoming_path, existing_path)
                and not saved.get("allowPathConflictOverwrite")
            ):
                return {
                    "success": False,
                    "error": "formal_test_id_path_conflict",
                    "testId": test_id,
                    "existingPath": existing_path,
                    "incomingPath": incoming_path,
                    "hint": "Use a distinct semantic/test id for different runtime elements.",
                }
        saved.pop("allowPathConflictOverwrite", None)
        data = self._load_page_formal(page_id)
        data["displayName"] = page.get("displayName") or data.get("displayName") or page_id
        data["mappings"][test_id] = saved
        self._save_page_formal(page_id, data)
        for other_path in sorted(self.formal_page_dir.glob("*.json")):
            other_page_id = self.normalize_page_id(other_path.stem)
            if other_page_id == page_id:
                continue
            other_data = self._read_json(other_path, {})
            mappings = _coerce_dict(other_data.get("mappings"))
            if test_id not in mappings:
                continue
            mappings.pop(test_id, None)
            other_data["mappings"] = mappings
            groups = self._empty_groups()
            for mapping_id, mapping in mappings.items():
                if isinstance(mapping, dict):
                    groups.setdefault(self.classify_group(mapping), []).append(mapping_id)
            other_data["groups"] = groups
            self._save_page_formal(other_page_id, other_data)
        if not self._suspend_rebuild:
            self.rebuild_indexes()
        return {
            "success": True,
            "item": saved,
            "pageId": page_id,
            "formalRef": f"formal://{page_id}/{test_id}",
            "formalPath": self.metadata_relpath(self._formal_page_path(page_id)),
        }

    def list_formal_by_page(self, page_id: str) -> Dict[str, Any]:
        data = self._load_page_formal(page_id)
        return {"success": True, "pageId": data.get("pageId"), "mappings": data.get("mappings", {})}

    def get_formal_by_testid(self, test_id: str) -> Dict[str, Any]:
        test_id = _safe_text(test_id)
        if not test_id:
            return {}
        if self.has_store():
            index = self._read_json(self.index_dir / "testid.index.json", {})
            item = _coerce_dict(_coerce_dict(index.get("items")).get(test_id))
            if item.get("formalPath"):
                data = self._read_json(self.resolve_metadata_path(item["formalPath"]), {})
                mapping = _coerce_dict(data.get("mappings")).get(test_id)
                if isinstance(mapping, dict):
                    return mapping
            for path in self.formal_page_dir.glob("*.json"):
                data = self._read_json(path, {})
                mapping = _coerce_dict(data.get("mappings")).get(test_id)
                if isinstance(mapping, dict):
                    return mapping
            for path in self.formal_global_dir.glob("*.json"):
                data = self._read_json(path, {})
                mapping = _coerce_dict(data.get("mappings")).get(test_id)
                if isinstance(mapping, dict):
                    return mapping
        return self._legacy_formal().get(test_id, {})

    def _copy_or_rel_asset(self, value: Any, subdir: str, stem: str) -> str:
        text = _safe_text(value)
        if not text:
            return ""
        if text.startswith("mapping_store/") or text.startswith("screenshots/"):
            return text.replace("\\", "/")
        src = Path(text)
        if not src.is_absolute():
            return text.replace("\\", "/")
        if not src.exists():
            return self.metadata_relpath(src)
        target_dir = self.asset_dir / subdir
        suffix = src.suffix or ".dat"
        target = target_dir / f"{_safe_file_id(stem)}{suffix}"
        if target.resolve() != src.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, target)
            except Exception:
                return self.metadata_relpath(src)
        return self.metadata_relpath(target)

    def _normalize_evidence_paths(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(evidence)
        test_id = _safe_text(item.get("testId")) or _safe_text(item.get("evidenceRef")).removeprefix("EVIDENCE_")
        visual = _coerce_dict(item.get("visual"))
        if visual.get("highlightImage"):
            visual["highlightImage"] = self._copy_or_rel_asset(visual.get("highlightImage"), "highlights", test_id or "highlight")
            item["visual"] = visual
        click = _coerce_dict(item.get("click"))
        detail = click.get("detail")
        if isinstance(detail, dict) and len(json.dumps(detail, ensure_ascii=False)) > 1200:
            detail_ref = self.asset_dir / "click_logs" / f"{_safe_file_id(test_id)}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            self._write_json(detail_ref, detail)
            click["detailRef"] = self.metadata_relpath(detail_ref)
            click.pop("detail", None)
            item["click"] = click
        return item

    def upsert_evidence(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_dirs()
        if not isinstance(evidence, dict):
            return {"success": False, "error": "evidence must be object"}
        test_id = _safe_text(evidence.get("testId"))
        evidence_ref = _safe_text(evidence.get("evidenceRef")) or f"EVIDENCE_{test_id}"
        if not test_id and evidence_ref.startswith("EVIDENCE_"):
            test_id = evidence_ref[len("EVIDENCE_"):]
        if not test_id:
            return {"success": False, "error": "testId is required"}
        page = self.resolve_page_id(evidence.get("targetName"), evidence.get("pageId") or _coerce_dict(evidence.get("structure")).get("pageId"), evidence)
        page_id = page["pageId"]
        item = self._normalize_evidence_paths(dict(evidence))
        item["testId"] = test_id
        item["evidenceRef"] = evidence_ref
        item["pageId"] = page_id
        item["updated_at"] = _now_text()
        path = self._evidence_testid_path(page_id, test_id)
        self._write_json(path, item)
        by_page = self._read_json(self.evidence_page_dir / f"{page_id}.json", {})
        if not isinstance(by_page, dict):
            by_page = {}
        by_page.setdefault("schema_version", "mapping_evidence.page.v1")
        by_page.setdefault("pageId", page_id)
        by_page.setdefault("items", {})
        by_page["items"][evidence_ref] = self.metadata_relpath(path)
        by_page["updated_at"] = _now_text()
        self._write_json(self.evidence_page_dir / f"{page_id}.json", by_page)
        for other_path in sorted(self.evidence_page_dir.glob("*.json")):
            other_page_id = self.normalize_page_id(other_path.stem)
            if other_page_id == page_id:
                continue
            other_data = self._read_json(other_path, {})
            if not isinstance(other_data, dict):
                continue
            touched = False
            for section in ("items", "evidence"):
                bucket = other_data.get(section)
                if not isinstance(bucket, dict):
                    continue
                for key, value in list(bucket.items()):
                    value_text = _safe_text(value)
                    if key == evidence_ref or (test_id and test_id in value_text):
                        bucket.pop(key, None)
                        touched = True
            if touched:
                other_data["updated_at"] = _now_text()
                self._write_json(other_path, other_data)
        for other_path in sorted(self.evidence_testid_dir.glob(f"*/{test_id}.json")):
            if other_path.resolve() == path.resolve():
                continue
            try:
                other_path.unlink()
            except Exception:
                pass
        if not self._suspend_rebuild:
            self.rebuild_indexes()
        return {
            "success": True,
            "item": item,
            "pageId": page_id,
            "evidenceRef": evidence_ref,
            "evidencePath": self.metadata_relpath(path),
        }

    def get_evidence(self, evidence_ref: str = "", test_id: str = "") -> Dict[str, Any]:
        evidence_ref = _safe_text(evidence_ref)
        test_id = _safe_text(test_id)
        if self.has_store():
            index = self._read_json(self.index_dir / "evidence.index.json", {})
            items = _coerce_dict(index.get("items"))
            record = _coerce_dict(items.get(evidence_ref)) if evidence_ref else {}
            if not record and test_id:
                for value in items.values():
                    if isinstance(value, dict) and value.get("testId") == test_id:
                        record = value
                        break
            if record.get("evidencePath"):
                data = self._read_json(self.resolve_metadata_path(record["evidencePath"]), {})
                if isinstance(data, dict):
                    return data
        legacy = self._legacy_evidence()
        if evidence_ref and evidence_ref in legacy:
            return legacy[evidence_ref]
        if test_id:
            for item in legacy.values():
                if item.get("testId") == test_id:
                    return item
        return {}

    def resolve_ref(self, ref: str = "", test_id: str = "") -> Dict[str, Any]:
        ref = _safe_text(ref)
        test_id = _safe_text(test_id)
        if ref.startswith("formal://"):
            payload = ref[len("formal://"):]
            page_id = ""
            if "/" in payload:
                page_id, test_id = payload.split("/", 1)
            else:
                test_id = payload or test_id
            item = self.get_formal_by_testid(test_id)
            path = ""
            if self.has_store() and test_id:
                index = self._read_json(self.index_dir / "testid.index.json", {})
                record = _coerce_dict(_coerce_dict(index.get("items")).get(test_id))
                path = _safe_text(record.get("formalPath"))
                page_id = page_id or _safe_text(record.get("pageId"))
            return {
                "success": bool(item),
                "type": "formal",
                "ref": ref,
                "testId": test_id,
                "pageId": self.normalize_page_id(page_id or item.get("pageId")),
                "path": path,
                "item": item,
            }
        if ref.startswith("EVIDENCE_") or test_id:
            evidence_ref = ref if ref.startswith("EVIDENCE_") else f"EVIDENCE_{test_id}"
            item = self.get_evidence(evidence_ref=evidence_ref, test_id=test_id)
            path = ""
            page_id = ""
            if self.has_store():
                index = self._read_json(self.index_dir / "evidence.index.json", {})
                record = _coerce_dict(_coerce_dict(index.get("items")).get(evidence_ref))
                path = _safe_text(record.get("evidencePath"))
                page_id = _safe_text(record.get("pageId"))
                test_id = test_id or _safe_text(record.get("testId"))
            return {
                "success": bool(item),
                "type": "evidence",
                "ref": evidence_ref,
                "testId": test_id or _safe_text(item.get("testId")),
                "pageId": self.normalize_page_id(page_id or item.get("pageId")),
                "path": path,
                "item": item,
            }
        return {"success": False, "error": "unsupported_ref", "ref": ref}

    def resolve_paths(self, ref: str = "", test_id: str = "", page_id: str = "", draft_id: str = "", include_abs: bool = False) -> Dict[str, Any]:
        """Resolve logical refs to store-relative paths for UI/debug use.

        The returned main fields are relative to AutoSmoke/metadata. Absolute
        paths are opt-in and should be treated as runtime-only diagnostics.
        """
        ref = _safe_text(ref)
        test_id = _safe_text(test_id)
        page_id = self.normalize_page_id(page_id) if page_id else ""
        draft_id = _safe_text(draft_id)
        out = {
            "success": True,
            "ref": ref,
            "testId": test_id,
            "pageId": page_id,
            "draftId": draft_id,
            "paths": {},
            "refs": {},
        }
        if ref:
            resolved = self.resolve_ref(ref=ref, test_id=test_id)
            out["resolved"] = resolved
            test_id = test_id or _safe_text(resolved.get("testId"))
            page_id = page_id or self.normalize_page_id(resolved.get("pageId"))
            if resolved.get("type") == "formal":
                out["refs"]["formalRef"] = ref
                if resolved.get("path"):
                    out["paths"]["formal"] = resolved.get("path")
            elif resolved.get("type") == "evidence":
                out["refs"]["evidenceRef"] = resolved.get("ref")
                if resolved.get("path"):
                    out["paths"]["evidence"] = resolved.get("path")
        if test_id:
            out["testId"] = test_id
            index = self._read_json(self.index_dir / "testid.index.json", {}) if self.has_store() else {}
            record = _coerce_dict(_coerce_dict(index.get("items")).get(test_id))
            page_id = page_id or self.normalize_page_id(record.get("pageId"))
            formal_path = _safe_text(record.get("formalPath"))
            evidence_path = _safe_text(record.get("evidencePath"))
            evidence_ref = _safe_text(record.get("evidenceRef")) or f"EVIDENCE_{test_id}"
            if formal_path:
                out["paths"].setdefault("formal", formal_path)
            if evidence_path:
                out["paths"].setdefault("evidence", evidence_path)
            if page_id:
                out["refs"].setdefault("formalRef", f"formal://{page_id}/{test_id}")
            out["refs"].setdefault("evidenceRef", evidence_ref)
        if draft_id:
            draft_index = self._read_json(self.index_dir / "draft.index.json", {}) if self.has_store() else {}
            record = _coerce_dict(_coerce_dict(draft_index.get("items")).get(draft_id))
            draft_path = _safe_text(record.get("draftPath"))
            page_id = page_id or self.normalize_page_id(record.get("pageId"))
            if draft_path:
                out["paths"].setdefault("draft", draft_path)
        if page_id:
            out["pageId"] = page_id
            out["paths"].setdefault("draftPage", f"mapping_store/draft/by_page/{page_id}.json")
            out["paths"].setdefault("formalPage", f"mapping_store/formal/by_page/{page_id}.json")
        if include_abs:
            out["absolutePaths"] = {
                key: str(self.resolve_metadata_path(value))
                for key, value in out["paths"].items()
                if value
            }
        out["success"] = bool(out["paths"] or out["refs"] or out.get("resolved", {}).get("success"))
        if not out["success"]:
            out["error"] = "not_found"
        return out

    # ------------------------------------------------------------------
    # Page compaction
    # ------------------------------------------------------------------

    def canonical_page_id(self, page_id: Any, known_pages: Dict[str, Any] = None) -> Tuple[str, str]:
        page_id = self.normalize_page_id(page_id)
        known_pages = known_pages if isinstance(known_pages, dict) else {}
        lowered = page_id.lower()
        debug_tokens = (
            "debug",
            "gm",
            "graphic",
            "guide_",
            "timeline",
            "test_",
            "mock",
            "sample",
        )
        if any(token in lowered for token in debug_tokens):
            return "debug", "debug_or_guide_page"
        if lowered.startswith("export_"):
            stripped = self.normalize_page_id(lowered[len("export_"):])
            if stripped and stripped in known_pages:
                return stripped, "export_prefix_duplicate"
        return page_id, "self"

    def page_compaction_plan(self) -> Dict[str, Any]:
        self.rebuild_indexes()
        page_index = self._read_json(self.index_dir / "page.index.json", {})
        pages = _coerce_dict(page_index.get("pages"))
        aliases = {}
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for page_id, info in sorted(pages.items()):
            canonical, reason = self.canonical_page_id(page_id, pages)
            if canonical == page_id:
                continue
            aliases[page_id] = {"canonicalPageId": canonical, "reason": reason}
            groups.setdefault(canonical, []).append({
                "pageId": page_id,
                "reason": reason,
                "draftCount": _coerce_dict(info).get("draftCount", 0),
                "mappingCount": _coerce_dict(info).get("mappingCount", 0),
            })
        return {
            "success": True,
            "totalPages": len(pages),
            "aliasCount": len(aliases),
            "groupCount": len(groups),
            "aliases": aliases,
            "groups": groups,
        }

    def _merge_json_map_file(self, source_path: Path, target_path: Path, map_key: str, page_id: str) -> int:
        source = self._read_json(source_path, {})
        if not isinstance(source, dict):
            return 0
        source_map = _coerce_dict(source.get(map_key))
        if not source_map:
            try:
                source_path.unlink()
            except Exception:
                pass
            return 0
        target = self._read_json(target_path, {})
        if not isinstance(target, dict):
            target = {}
        target.setdefault("schema_version", source.get("schema_version", "mapping_store.page.v1"))
        target["pageId"] = page_id
        target.setdefault("displayName", page_id)
        target_map = _coerce_dict(target.get(map_key))
        moved = 0
        for key, item in source_map.items():
            if not isinstance(item, dict):
                continue
            new_key = key
            if new_key in target_map:
                new_key = f"{key}__{hashlib.sha1(str(source_path).encode('utf-8')).hexdigest()[:6]}"
            updated = dict(item)
            updated["pageId"] = page_id
            target_map[new_key] = updated
            moved += 1
        target[map_key] = target_map
        target["updated_at"] = _now_text()
        target["count"] = len(target_map)
        self._write_json(target_path, target)
        try:
            source_path.unlink()
        except Exception:
            pass
        return moved

    def _move_evidence_page(self, source_page: str, target_page: str) -> int:
        moved = 0
        source_dir = self.evidence_testid_dir / source_page
        target_dir = self.evidence_testid_dir / target_page
        if source_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            for path in sorted(source_dir.glob("*.json")):
                data = self._read_json(path, {})
                if isinstance(data, dict):
                    data["pageId"] = target_page
                    structure = data.get("structure")
                    if isinstance(structure, dict):
                        structure["pageId"] = target_page
                target_path = target_dir / path.name
                if target_path.exists():
                    target_path = target_dir / f"{path.stem}_{hashlib.sha1(str(path).encode('utf-8')).hexdigest()[:6]}{path.suffix}"
                self._write_json(target_path, data)
                try:
                    path.unlink()
                except Exception:
                    pass
                moved += 1
            try:
                source_dir.rmdir()
            except Exception:
                pass
        source_page_file = self.evidence_page_dir / f"{source_page}.json"
        target_page_file = self.evidence_page_dir / f"{target_page}.json"
        source = self._read_json(source_page_file, {})
        source_items = _coerce_dict(source.get("items")) if isinstance(source, dict) else {}
        if source_items:
            target = self._read_json(target_page_file, {})
            if not isinstance(target, dict):
                target = {"schema_version": "mapping_evidence.page.v1", "items": {}}
            target["pageId"] = target_page
            target_items = _coerce_dict(target.get("items"))
            for evidence_ref, rel_path in source_items.items():
                target_items[evidence_ref] = str(rel_path).replace(f"/{source_page}/", f"/{target_page}/")
            target["items"] = target_items
            target["updated_at"] = _now_text()
            self._write_json(target_page_file, target)
            try:
                source_page_file.unlink()
            except Exception:
                pass
        return moved

    def compact_pages(self, dry_run: bool = True) -> Dict[str, Any]:
        plan = self.page_compaction_plan()
        aliases = plan.get("aliases", {})
        if dry_run:
            plan["dryRun"] = True
            return plan
        moved = {"drafts": 0, "formal": 0, "evidence": 0, "pages": 0}
        for source_page, alias in sorted(aliases.items()):
            target_page = self.normalize_page_id(alias.get("canonicalPageId"))
            if not target_page or target_page == source_page:
                continue
            moved["drafts"] += self._merge_json_map_file(
                self.draft_page_dir / f"{source_page}.json",
                self.draft_page_dir / f"{target_page}.json",
                "drafts",
                target_page,
            )
            moved["formal"] += self._merge_json_map_file(
                self.formal_page_dir / f"{source_page}.json",
                self.formal_page_dir / f"{target_page}.json",
                "mappings",
                target_page,
            )
            moved["evidence"] += self._move_evidence_page(source_page, target_page)
            moved["pages"] += 1
        alias_path = self.index_dir / "page_alias.index.json"
        self._write_json(alias_path, {
            "schema_version": "mapping_index.page_alias.v1",
            "updated_at": _now_text(),
            "aliases": aliases,
        })
        indexes = self.rebuild_indexes()
        return {
            "success": True,
            "dryRun": False,
            "aliasCount": len(aliases),
            "moved": moved,
            "aliasPath": self.metadata_relpath(alias_path),
            "indexes": indexes,
        }

    def canonicalize_page_alias(self, page_id: Any) -> str:
        page_id = self.normalize_page_id(page_id)
        alias_index = self._read_json(self.index_dir / "page_alias.index.json", {})
        aliases = _coerce_dict(alias_index.get("aliases")) if isinstance(alias_index, dict) else {}
        seen = set()
        while page_id in aliases and page_id not in seen:
            seen.add(page_id)
            page_id = self.normalize_page_id(_coerce_dict(aliases.get(page_id)).get("canonicalPageId"))
        return page_id

    def runtime_page_candidates(self, runtime_page_id: Any) -> List[str]:
        text = _safe_text(runtime_page_id)
        if not text:
            return []
        raw_parts = [text]
        raw_parts.extend(re.findall(r"\[([^\]]+)\]", text))
        raw_parts.extend(re.findall(r"([A-Za-z0-9_]+)\(Clone\)", text))
        raw_parts.append(re.sub(r"\(Clone\)", " ", text))
        raw_parts.append(re.sub(r"\[[^\]]+\]", " ", text))
        candidates = []
        for part in raw_parts:
            base = self.normalize_page_id(part)
            variants = [base]
            for suffix in ("_popup", "_panel", "_clone", "_ui"):
                if base.endswith(suffix):
                    variants.append(base[:-len(suffix)])
            variants.append(base.replace("_clone_", "_"))
            variants.append(base.replace("_popup", ""))
            variants.append(base.replace("_panel", ""))
            for value in variants:
                value = self.normalize_page_id(value)
                if value and value not in candidates:
                    candidates.append(value)
        return candidates

    def resolve_existing_page_id(self, runtime_page_id: Any) -> Dict[str, Any]:
        page_index = self._read_json(self.index_dir / "page.index.json", {})
        pages = _coerce_dict(page_index.get("pages")) if isinstance(page_index, dict) else {}
        candidates = self.runtime_page_candidates(runtime_page_id)
        for candidate in candidates:
            canonical = self.canonicalize_page_alias(candidate)
            if canonical in pages:
                return {
                    "matched": True,
                    "pageId": canonical,
                    "source": "exact_candidate",
                    "runtimePageId": _safe_text(runtime_page_id),
                    "candidates": candidates,
                    "page": pages.get(canonical, {}),
                }
        for candidate in candidates:
            for page_id in pages.keys():
                if candidate and (page_id == candidate or page_id.startswith(candidate + "_") or candidate.startswith(page_id + "_")):
                    canonical = self.canonicalize_page_alias(page_id)
                    return {
                        "matched": True,
                        "pageId": canonical,
                        "source": "prefix_candidate",
                        "runtimePageId": _safe_text(runtime_page_id),
                        "candidates": candidates,
                        "page": pages.get(canonical, {}),
                    }
        fallback = self.canonicalize_page_alias(candidates[0]) if candidates else "unknown"
        return {
            "matched": False,
            "pageId": fallback,
            "source": "fallback",
            "runtimePageId": _safe_text(runtime_page_id),
            "candidates": candidates,
            "page": pages.get(fallback, {}),
        }

    # ------------------------------------------------------------------
    # Page groups
    # ------------------------------------------------------------------

    def classify_group(self, item: Dict[str, Any]) -> str:
        item = item if isinstance(item, dict) else {}
        blob = " ".join([
            _safe_text(item.get("path")),
            _safe_text(item.get("elementPath")),
            _safe_text(item.get("runtimePath")),
            _safe_text(item.get("nodeName")),
            _safe_text(item.get("displayName")),
            _safe_text(item.get("targetName")),
            _safe_text(item.get("role")),
            _safe_text(item.get("elementType")),
            _safe_text(item.get("interactionType")),
        ]).lower()
        role = _safe_text(item.get("role")).lower()
        element_type = _safe_text(item.get("elementType")).lower()
        interaction = _safe_text(item.get("interactionType")).lower()
        if item.get("collection") or "dynamic_list" in blob or "list_template" in blob:
            return "list_templates"
        if any(token in blob for token in ["popup", "dialog", "tips", "mask", "弹窗"]):
            return "dialogs"
        if role in {"back", "close", "cancel", "navigation"} or any(token in blob for token in ["back", "close", "btn_close", "button_close", "返回", "关闭"]):
            return "navigation"
        if role == "tab" or element_type == "tab" or any(token in blob for token in ["tab", "页签", "标签"]):
            return "tabs"
        if role in {"resource_source", "top_bar"} or any(token in blob for token in ["topres", "top_res", "topbar", "top_bar", "resource", "resitem"]):
            return "top_bar"
        if role in {"use", "confirm", "claim", "add"} or any(token in blob for token in ["bottom", "buttom", "footer", "usedbtn", "btn_use", "使用", "确认", "领取", "添加"]):
            return "bottom_actions"
        if element_type in {"item_cell", "reward_item", "shop_item_cell", "cell"} or any(token in blob for token in ["scrollview", "viewport", "content", "item", "cell", "resitem", "propitem"]):
            return "content"
        if interaction in {"drag", "scroll"} or any(token in blob for token in ["scroll", "drag"]):
            return "content"
        return "unknown"

    def _empty_groups(self) -> Dict[str, List[str]]:
        return {
            "top_bar": [],
            "tabs": [],
            "content": [],
            "bottom_actions": [],
            "navigation": [],
            "dialogs": [],
            "list_templates": [],
            "unknown": [],
        }

    def _count_groups(self, groups: Any) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        if not isinstance(groups, dict):
            return counts
        for group_name, members in groups.items():
            group = _safe_text(group_name)
            if not group:
                continue
            if isinstance(members, list):
                count = len(members)
            elif isinstance(members, dict):
                count = len(members)
            elif members:
                count = 1
            else:
                count = 0
            if count:
                counts[group] = counts.get(group, 0) + count
        return counts

    def _global_scope_for_mapping(self, mapping: Dict[str, Any]) -> str:
        group = self.classify_group(mapping)
        if group == "top_bar":
            return "top_bar"
        if group == "navigation":
            return "navigation"
        if group == "dialogs":
            return "common_dialog"
        return ""

    def rebuild_global_formal(self) -> Dict[str, Any]:
        self._ensure_dirs()
        scopes: Dict[str, Dict[str, Any]] = {}
        for path in sorted(self.formal_page_dir.glob("*.json")):
            data = self._read_json(path, {})
            if not isinstance(data, dict):
                continue
            page_id = self.normalize_page_id(data.get("pageId") or path.stem)
            for test_id, mapping in _coerce_dict(data.get("mappings")).items():
                if not isinstance(mapping, dict):
                    continue
                scope = self._global_scope_for_mapping(mapping)
                if not scope:
                    continue
                item = dict(mapping)
                item.setdefault("pageId", page_id)
                item["globalScope"] = scope
                bucket = scopes.setdefault(scope, {})
                bucket[test_id] = item
        written = {}
        for scope, mappings in scopes.items():
            groups = self._empty_groups()
            for test_id, mapping in mappings.items():
                groups.setdefault(self.classify_group(mapping), []).append(test_id)
            path = self._formal_global_path(scope)
            self._write_json(path, {
                "schema_version": "element_mapping_formal.global.v1",
                "scope": scope,
                "displayName": scope,
                "updated_at": _now_text(),
                "count": len(mappings),
                "mappings": mappings,
                "groups": groups,
            })
            written[scope] = {"count": len(mappings), "path": self.metadata_relpath(path)}
        for path in sorted(self.formal_global_dir.glob("*.json")):
            if path.stem not in scopes:
                path.unlink()
        indexes = self.rebuild_indexes()
        return {"success": True, "scopes": written, "indexes": indexes}

    def rebuild_page_groups(self) -> Dict[str, Any]:
        self._ensure_dirs()
        summary = {
            "success": True,
            "draftPages": 0,
            "formalPages": 0,
            "draftItems": 0,
            "formalItems": 0,
            "groups": {},
        }
        for path in sorted(self.draft_page_dir.glob("*.json")):
            data = self._read_json(path, {})
            if not isinstance(data, dict):
                continue
            drafts = _coerce_dict(data.get("drafts"))
            groups = self._empty_groups()
            for draft_id, draft in drafts.items():
                if not isinstance(draft, dict):
                    continue
                group = self.classify_group(draft)
                groups.setdefault(group, []).append(draft_id)
                summary["groups"][group] = summary["groups"].get(group, 0) + 1
            data["groups"] = groups
            data["updated_at"] = _now_text()
            data["count"] = len(drafts)
            self._write_json(path, data)
            summary["draftPages"] += 1
            summary["draftItems"] += len(drafts)
        for path in sorted(self.formal_page_dir.glob("*.json")):
            data = self._read_json(path, {})
            if not isinstance(data, dict):
                continue
            mappings = _coerce_dict(data.get("mappings"))
            groups = self._empty_groups()
            for test_id, mapping in mappings.items():
                if not isinstance(mapping, dict):
                    continue
                group = self.classify_group(mapping)
                groups.setdefault(group, []).append(test_id)
                summary["groups"][group] = summary["groups"].get(group, 0) + 1
            data["groups"] = groups
            data["updated_at"] = _now_text()
            data["count"] = len(mappings)
            self._write_json(path, data)
            summary["formalPages"] += 1
            summary["formalItems"] += len(mappings)
        indexes = self.rebuild_indexes()
        summary["indexes"] = indexes
        return summary

    # ------------------------------------------------------------------
    # Indexes and migration
    # ------------------------------------------------------------------

    def rebuild_indexes(self) -> Dict[str, Any]:
        self._ensure_dirs()
        page_index: Dict[str, Any] = {"schema_version": "mapping_index.page.v1", "updated_at": _now_text(), "pages": {}}
        draft_index: Dict[str, Any] = {"schema_version": "mapping_index.draft.v1", "updated_at": _now_text(), "items": {}}
        formal_index: Dict[str, Any] = {"schema_version": "mapping_index.formal.v1", "updated_at": _now_text(), "items": {}}
        evidence_index: Dict[str, Any] = {"schema_version": "mapping_index.evidence.v1", "updated_at": _now_text(), "items": {}}
        testid_index: Dict[str, Any] = {"schema_version": "mapping_index.testid.v1", "updated_at": _now_text(), "items": {}}
        semantic_index: Dict[str, Any] = {"schema_version": "mapping_index.semantic.v1", "updated_at": _now_text(), "items": {}}

        pages = {}
        for path in sorted(self.draft_page_dir.glob("*.json")):
            data = self._read_json(path, {})
            page_id = self.normalize_page_id(data.get("pageId") or path.stem)
            drafts = _coerce_dict(data.get("drafts"))
            page = pages.setdefault(page_id, {"displayName": data.get("displayName") or page_id, "draftCount": 0, "mappingCount": 0, "confirmedCount": 0, "ignoredCount": 0})
            page["draftPath"] = self.metadata_relpath(path)
            page["draftCount"] += len(drafts)
            draft_groups = self._count_groups(data.get("groups"))
            if draft_groups:
                page["draftGroups"] = draft_groups
                combined_groups = page.setdefault("groups", {})
                for group_name, count in draft_groups.items():
                    combined_groups[group_name] = int(combined_groups.get(group_name, 0) or 0) + count
            for draft_id, draft in drafts.items():
                if not isinstance(draft, dict):
                    continue
                review_status = draft.get("reviewStatus") or draft.get("status") or draft.get("source") or ""
                if review_status == "ignored":
                    page["ignoredCount"] += 1
                draft_index["items"][draft_id] = {"pageId": page_id, "draftPath": self.metadata_relpath(path), "reviewStatus": review_status, "elementPath": draft.get("elementPath") or draft.get("path") or ""}

        for path in sorted(self.formal_page_dir.glob("*.json")):
            data = self._read_json(path, {})
            page_id = self.normalize_page_id(data.get("pageId") or path.stem)
            mappings = _coerce_dict(data.get("mappings"))
            page = pages.setdefault(page_id, {"displayName": data.get("displayName") or page_id, "draftCount": 0, "mappingCount": 0, "confirmedCount": 0, "ignoredCount": 0})
            page["formalPath"] = self.metadata_relpath(path)
            page["mappingCount"] += len(mappings)
            formal_groups = self._count_groups(data.get("groups"))
            if formal_groups:
                page["formalGroups"] = formal_groups
                combined_groups = page.setdefault("groups", {})
                for group_name, count in formal_groups.items():
                    combined_groups[group_name] = int(combined_groups.get(group_name, 0) or 0) + count
            for test_id, mapping in mappings.items():
                if not isinstance(mapping, dict):
                    continue
                status = mapping.get("reviewStatus") or ""
                if status in CONFIRMED_FORMAL_STATUSES:
                    page["confirmedCount"] += 1
                formal_index["items"][test_id] = {"pageId": page_id, "formalPath": self.metadata_relpath(path), "reviewStatus": status}
                evidence_ref = mapping.get("evidenceRef") or f"EVIDENCE_{test_id}"
                testid_index["items"].setdefault(test_id, {"pageId": page_id, "formalPath": self.metadata_relpath(path), "reviewStatus": status})
                testid_index["items"][test_id]["evidenceRef"] = evidence_ref
                semantic_id = _safe_text(mapping.get("semanticId"))
                if semantic_id:
                    semantic_index["items"].setdefault(semantic_id, [])
                    semantic_index["items"][semantic_id].append({"testId": test_id, "pageId": page_id, "formalPath": self.metadata_relpath(path)})

        for path in sorted(self.formal_global_dir.glob("*.json")):
            data = self._read_json(path, {})
            if not isinstance(data, dict):
                continue
            scope = _safe_text(data.get("scope") or path.stem)
            mappings = _coerce_dict(data.get("mappings"))
            for test_id, mapping in mappings.items():
                if not isinstance(mapping, dict):
                    continue
                page_id = self.normalize_page_id(mapping.get("pageId") or scope or "global")
                status = mapping.get("reviewStatus") or ""
                formal_index["items"][test_id] = {
                    "pageId": page_id,
                    "scope": scope,
                    "formalPath": self.metadata_relpath(path),
                    "reviewStatus": status,
                    "global": True,
                }
                evidence_ref = mapping.get("evidenceRef") or f"EVIDENCE_{test_id}"
                testid_index["items"].setdefault(test_id, {"pageId": page_id})
                testid_index["items"][test_id].update({
                    "pageId": page_id,
                    "scope": scope,
                    "formalPath": self.metadata_relpath(path),
                    "reviewStatus": status,
                    "evidenceRef": evidence_ref,
                    "global": True,
                })
                semantic_id = _safe_text(mapping.get("semanticId"))
                if semantic_id:
                    semantic_index["items"].setdefault(semantic_id, [])
                    semantic_index["items"][semantic_id].append({"testId": test_id, "pageId": page_id, "scope": scope, "formalPath": self.metadata_relpath(path), "global": True})

        for path in sorted(self.evidence_testid_dir.glob("*/*.json")):
            data = self._read_json(path, {})
            if not isinstance(data, dict):
                continue
            evidence_ref = data.get("evidenceRef") or f"EVIDENCE_{data.get('testId')}"
            test_id = data.get("testId") or ""
            page_id = self.normalize_page_id(data.get("pageId") or path.parent.name)
            evidence_index["items"][evidence_ref] = {"pageId": page_id, "testId": test_id, "evidencePath": self.metadata_relpath(path)}
            if test_id:
                testid_index["items"].setdefault(test_id, {"pageId": page_id})
                testid_index["items"][test_id]["evidencePath"] = self.metadata_relpath(path)

        for page_id, page in pages.items():
            page.setdefault("draftPath", f"mapping_store/draft/by_page/{page_id}.json")
            page.setdefault("formalPath", f"mapping_store/formal/by_page/{page_id}.json")
            page_index["pages"][page_id] = page

        self._write_json(self.index_dir / "page.index.json", page_index)
        self._write_json(self.index_dir / "draft.index.json", draft_index)
        self._write_json(self.index_dir / "formal.index.json", formal_index)
        self._write_json(self.index_dir / "evidence.index.json", evidence_index)
        self._write_json(self.index_dir / "testid.index.json", testid_index)
        self._write_json(self.index_dir / "semantic.index.json", semantic_index)
        self._write_json(self.store_dir / "manifest.json", {
            "schema_version": "mapping_store.v1",
            "store_version": 1,
            "layout": "page_sharded_mapping_store",
            "updated_at": _now_text(),
            "files": {
                "page_index": "mapping_store/indexes/page.index.json",
                "draft_index": "mapping_store/indexes/draft.index.json",
                "formal_index": "mapping_store/indexes/formal.index.json",
                "evidence_index": "mapping_store/indexes/evidence.index.json",
                "testid_index": "mapping_store/indexes/testid.index.json",
                "semantic_index": "mapping_store/indexes/semantic.index.json",
                "page_dictionary": "mapping_store/pages/page_name_dictionary.json",
            },
        })
        self._write_queues_from_drafts()
        return {"success": True, "pages": len(pages), "drafts": len(draft_index["items"]), "formal": len(formal_index["items"]), "evidence": len(evidence_index["items"])}

    def _write_queues_from_drafts(self) -> None:
        queues: Dict[str, List[Dict[str, Any]]] = {"pending": [], "needs_review": [], "ignored": [], "rejected": []}
        for page_path in sorted(self.draft_page_dir.glob("*.json")):
            data = self._read_json(page_path, {})
            page_id = self.normalize_page_id(data.get("pageId") or page_path.stem)
            for draft_id, draft in _coerce_dict(data.get("drafts")).items():
                if not isinstance(draft, dict):
                    continue
                status = draft.get("reviewStatus") or draft.get("status") or "pending"
                queue = status if status in queues else "needs_review" if status in {"modified", "auto_draft"} else "pending"
                queues[queue].append({"draftId": draft_id, "pageId": page_id, "draftPath": self.metadata_relpath(page_path), "reason": draft.get("ignoredReason") or draft.get("rejectedReason") or ""})
        for status, items in queues.items():
            self._write_json(self.draft_queue_dir / f"{status}.json", {"schema_version": "draft_queue.v1", "status": status, "updated_at": _now_text(), "items": items})

    def migrate_from_legacy(self, export_legacy: bool = False) -> Dict[str, Any]:
        self._ensure_dirs()
        old_suspend = self._suspend_rebuild
        self._suspend_rebuild = True
        try:
            draft_count = 0
            for draft in self._legacy_drafts():
                self.save_draft(draft)
                draft_count += 1
            formal_count = 0
            for test_id, mapping in self._legacy_formal().items():
                item = dict(mapping)
                item["testId"] = item.get("testId") or test_id
                if (item.get("reviewStatus") or "") in {"pending", "needs_review", "ignored", "rejected", "blocked", "auto_draft", "runtime_matched"}:
                    continue
                self.upsert_formal(item)
                formal_count += 1
            evidence_count = 0
            for evidence_ref, evidence in self._legacy_evidence().items():
                item = dict(evidence)
                item["evidenceRef"] = item.get("evidenceRef") or evidence_ref
                self.upsert_evidence(item)
                evidence_count += 1
        finally:
            self._suspend_rebuild = old_suspend
        indexes = self.rebuild_indexes()
        exported = self.export_legacy_files() if export_legacy else {}
        return {"success": True, "drafts": draft_count, "formal": formal_count, "evidence": evidence_count, "indexes": indexes, "exported": exported}

    def export_legacy_files(self) -> Dict[str, Any]:
        drafts = []
        for path in sorted(self.draft_page_dir.glob("*.json")):
            data = self._read_json(path, {})
            drafts.extend([d for d in _coerce_dict(data.get("drafts")).values() if isinstance(d, dict)])
        self._write_json(self.legacy_draft_path, {"schema_version": "element_mapping_draft.legacy_export.v1", "exportTime": _now_text(), "source": "mapping_store.export_legacy_files", "totalDrafts": len(drafts), "drafts": drafts})

        formal = {}
        for path in sorted(self.formal_page_dir.glob("*.json")):
            data = self._read_json(path, {})
            formal.update({k: v for k, v in _coerce_dict(data.get("mappings")).items() if isinstance(v, dict)})
        for path in sorted(self.formal_global_dir.glob("*.json")):
            data = self._read_json(path, {})
            formal.update({k: v for k, v in _coerce_dict(data.get("mappings")).items() if isinstance(v, dict)})
        self._write_json(self.legacy_formal_path, {"schema_version": "element_mapping_formal.v1", "feature_name": "AutoSmoke", "exported_at": _now_text(), "mappings": formal})

        evidence = {}
        for path in sorted(self.evidence_testid_dir.glob("*/*.json")):
            item = self._read_json(path, {})
            if isinstance(item, dict):
                evidence[item.get("evidenceRef") or f"EVIDENCE_{item.get('testId')}"] = item
        self._write_json(self.legacy_evidence_path, {"schema_version": "mapping_evidence.v1", "feature_name": "AutoSmoke", "updated_at": _now_text(), "evidence": evidence})
        return {"success": True, "drafts": len(drafts), "formal": len(formal), "evidence": len(evidence)}


if __name__ == "__main__":
    store = MappingStore()
    print(json.dumps(store.migrate_from_legacy(export_legacy=False), ensure_ascii=False, indent=2))
