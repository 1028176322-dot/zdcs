#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilities for Chinese semantic correction parsing."""

import hashlib
import json
import os
import re
from datetime import datetime


_DICT_PATH_DEFAULT = "semantic_dictionary.json"


def _safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_text(value):
    text = _safe_text(value)
    if not text:
        return ""
    text = text.lower()
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    for ch in "，。；：,.;:!?！？”“‘’'\"()[]{}<>-_=+/\\|":
        text = text.replace(ch, " ")
    return text.strip()


def _slug(value):
    text = _safe_text(value).lower()
    if not text:
        return ""
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def _semantic_token_id(value):
    slug = _slug(value)
    if slug:
        return slug
    digest = hashlib.sha1(_safe_text(value).encode("utf-8")).hexdigest()[:10]
    return f"custom_{digest}"


def _derive_subject_from_input(text, page_name="", role_name="", type_name="", extra_remove=None):
    subject = _normalize_text(text)
    remove_words = [
        page_name,
        "界面",
        "页面",
        role_name,
        type_name,
        "按钮",
        "组件",
        "图标",
        "文本",
        "状态",
    ]
    remove_words.extend(extra_remove or [])
    for word in remove_words:
        word = _safe_text(word)
        if word:
            subject = subject.replace(word, "")
    return subject.strip()


def _coerce_list(value):
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _coerce_dict(value, default=None):
    return value if isinstance(value, dict) else default if default is not None else {}


def build_default_semantic_dictionary():
    return {
        "schema_version": "semantic_dictionary.v1",
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "pages": {
            "\u80cc\u5305": "bag",
            "\u5546\u5e97": "shop",
            "\u767b\u5f55\u6709\u793c": "activity.login_gift",
            "\u4e03\u65e5\u7b7e\u5230": "activity.login_gift",
            "\u4e3b\u57ce": "main_city",
            "\u5956\u52b1\u5f39\u7a97": "reward_popup",
            "\u89d2\u8272\u4fe1\u606f": "character_info",
        },
        "objects": {
            "\u91d1\u5e01": "gold",
            "\u7cae\u98df": "food",
            "\u6728\u6750": "wood",
            "\u77f3\u6750": "stone",
            "\u94c1\u77ff": "iron",
            "\u77ff\u77f3": "ore",
            "\u94f6\u5e01": "silver",
            "\u94bb\u77f3": "diamond",
            "\u88c5\u5907": "equipment",
            "\u5165\u53e3": "entry",
            "\u7ea2\u70b9": "red_dot",
            "\u5956\u52b1": "reward",
            "\u7b2c1\u5929": "day1",
            "\u7b2c2\u5929": "day2",
            "\u7b2c7\u5929": "day7",
            "\u4f53\u529b": "stamina",
            "\u4f53\u529b\u836f\u5242": "stamina_potion",
            "\u5ba2\u670d": "customer_service",
            "\u6392\u884c\u699c": "ranking",
            "\u6392\u884c": "ranking",
            "\u597d\u53cb": "friend",
            "\u65d7\u5e1c": "flag",
            "\u56fd\u5bb6\u6807\u9898": "country_label",
            "\u56fd\u5bb6": "country",
            "\u6807\u9898": "label",
            "\u8054\u76df": "alliance",
        },
        "roles": {
            "\u9014\u5f84": "resource_source",
            "\u6765\u6e90": "resource_source",
            "\u8d44\u6e90\u6765\u6e90": "resource_source",
            "\u7d22\u53d6": "resource_source",
            "\u9886\u53d6": "claim",
            "\u5173\u95ed": "close",
            "\u786e\u8ba4": "confirm",
            "\u53d6\u6d88": "cancel",
            "\u8fd4\u56de": "back",
            "\u53ef\u9886\u53d6": "claimable_state",
            "\u5df2\u9886\u53d6": "claimed_state",
            "\u672a\u89e3\u9501": "locked_state",
            "\u70b9\u51fb": "action",
            "\u4f7f\u7528": "use",
            "\u6dfb\u52a0": "add",
        },
        "types": {
            "\u6309\u94ae": "Button",
            "\u754c\u9762": "Panel",
            "\u9762\u677f": "Panel",
            "\u5f39\u7a97": "Popup",
            "\u6587\u672c": "Text",
            "\u56fe\u6807": "Icon",
            "\u7ea2\u70b9": "RedDot",
            "\u72b6\u6001": "State",
            "\u683c\u5b50": "Item",
        },
        "test_id_suffix": {
            "Button": "button",
            "Panel": "panel",
            "Popup": "popup",
            "Text": "text",
            "Icon": "icon",
            "RedDot": "red_dot",
            "State": "state",
            "Item": "item",
            "unknown": "target",
        },
        "translation_terms": {
            "\u4e2a\u6027\u8bbe\u7f6e": "personalization_settings",
            "\u4e2a\u6027": "personalization",
            "\u8bbe\u7f6e": "settings",
            "\u4e3b\u89d2": "main_character",
            "\u52a8\u753b": "animation",
            "\u6a21\u578b": "model",
            "\u73a9\u5bb6": "player",
            "\u73a9\u5bb6\u540d\u79f0": "player_name",
            "\u540d\u79f0": "name",
            "\u6027\u522b": "gender",
            "\u6218\u529b": "power",
            "\u80cc\u666f": "background",
            "\u80cc\u666f\u56fe": "background_image",
            "\u6392\u884c\u699c": "ranking",
            "\u6392\u884c": "ranking",
            "\u597d\u53cb": "friend",
            "\u65d7\u5e1c": "flag",
            "\u56fd\u5bb6\u6807\u9898": "country_label",
            "\u56fd\u5bb6": "country",
            "\u6807\u9898": "label",
            "\u8054\u76df": "alliance",
            "\u589e\u76ca": "buff",
        },
    }


def _normalize_dictionary_bucket(raw_bucket):
    out = []
    if isinstance(raw_bucket, dict):
        for key, value in raw_bucket.items():
            if isinstance(value, str) and _safe_text(value):
                item_id = value
                item_name = key
            elif isinstance(value, dict):
                item_id = _safe_text(value.get("id"))
                item_name = _safe_text(value.get("name") or key)
            else:
                item_id = _safe_text(key)
                item_name = _safe_text(key)
            out.append({
                "id": item_id or item_name,
                "name": item_name or item_id,
                "aliases": [item_id, item_name, key] if key else [item_id, item_name],
                "keywords": _coerce_list(value.get("keywords")) if isinstance(value, dict) else [item_id, item_name, key],
            })
    elif isinstance(raw_bucket, list):
        for item in raw_bucket:
            if isinstance(item, dict):
                item_id = _safe_text(item.get("id"))
                item_name = _safe_text(item.get("name") or item_id)
                aliases = _coerce_list(item.get("aliases"))
                if not aliases and item_id:
                    aliases = [item_id]
                if item_name and item_name not in aliases:
                    aliases.append(item_name)
                out.append({
                    "id": item_id,
                    "name": item_name or item_id,
                    "aliases": aliases,
                    "keywords": _coerce_list(item.get("keywords")) or aliases,
                })
            else:
                item_id = _safe_text(item)
                if item_id:
                    out.append({
                        "id": item_id,
                        "name": item_id,
                        "aliases": [item_id],
                        "keywords": [item_id],
                    })
    return out


def load_semantic_dictionary(path=None):
    dictionary_path = os.path.abspath(path or _DICT_PATH_DEFAULT)
    if os.path.exists(dictionary_path):
        try:
            with open(dictionary_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                # 兼容历史结构，确保关键字段存在
                loaded.setdefault("pages", {})
                loaded.setdefault("objects", {})
                loaded.setdefault("roles", {})
                loaded.setdefault("types", {})
                loaded.setdefault("test_id_suffix", {})
                loaded.setdefault("translation_terms", {})
                loaded.setdefault("schema_version", "semantic_dictionary.v1")
                if not loaded.get("updated_at"):
                    loaded["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                return loaded
        except Exception:
            pass

    default_dict = build_default_semantic_dictionary()
    os.makedirs(os.path.dirname(dictionary_path), exist_ok=True)
    with open(dictionary_path, "w", encoding="utf-8") as f:
        json.dump(default_dict, f, ensure_ascii=False, indent=2)
    return default_dict


def _match_dictionary(context_hint, text, dictionary, bucket_name, prefer_text=False):
    buckets = _normalize_dictionary_bucket(dictionary.get(bucket_name, []))
    normalized_text = _normalize_text(text)
    normalized_hint = _normalize_text(context_hint)

    def match_text():
        best_item = None
        best_score = 0
        for item in buckets:
            item_id = _safe_text(item.get("id"))
            if not item_id:
                continue
            candidates = [str(v).lower() for v in _coerce_list(item.get("keywords")) + _coerce_list(item.get("aliases"))]
            for candidate in candidates:
                if not candidate:
                    continue
                if candidate == normalized_text:
                    return item_id, {"name": _safe_text(item.get("name") or item_id), "source": "exact"}
                if candidate in normalized_text:
                    score = len(candidate)
                    if score > best_score:
                        best_score = score
                        best_item = {"id": item_id, "name": item.get("name", item_id), "source": "contains"}
        if best_item:
            return best_item["id"], {"name": best_item["name"], "source": best_item["source"]}
        return "", {"name": "", "source": "fallback"}

    # 目标名里显式写出的中文页面/对象优先于运行态上下文，避免把 UIShop/Shop 等路径片段当业务语义。
    if prefer_text:
        text_id, text_info = match_text()
        if text_id:
            return text_id, text_info

    # 再做上下文精确匹配
    for item in buckets:
        item_id = _safe_text(item.get("id")).lower()
        aliases = [str(v).lower() for v in _coerce_list(item.get("aliases"))]
        if item_id and (item_id == normalized_hint):
            return item_id, {"name": _safe_text(item.get("name") or item_id), "source": "hint"}
        if normalized_hint and normalized_hint in aliases:
            return item_id, {"name": _safe_text(item.get("name") or item_id), "source": "hint"}

    # 最后做文本包含匹配（按命中关键字长度排序）
    return match_text()


def _match_dictionary_all(text, dictionary, bucket_name, max_items=4):
    buckets = _normalize_dictionary_bucket(dictionary.get(bucket_name, []))
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return []

    hits = []
    seen = set()
    seen_ids = set()
    for item in buckets:
        item_id = _safe_text(item.get("id"))
        if not item_id:
            continue
        normalized_item_id = _slug(item_id)
        if normalized_item_id in seen_ids:
            continue
        item_name = _safe_text(item.get("name") or item_id)
        candidates = [str(v).lower() for v in _coerce_list(item.get("keywords")) + _coerce_list(item.get("aliases"))]
        for candidate in candidates:
            if not candidate:
                continue
            if candidate in normalized_text:
                hit_key = f"{item_id}:{item_name}"
                if hit_key in seen:
                    break
                seen.add(hit_key)
                seen_ids.add(normalized_item_id)
                hits.append({
                    "id": item_id,
                    "name": item_name,
                    "keyword": candidate,
                })
                break
    hits.sort(key=lambda x: len(_safe_text(x.get("keyword", ""))), reverse=True)
    filtered = []
    covered_keywords = []
    for hit in hits:
        keyword = _safe_text(hit.get("keyword", ""))
        if keyword and any(keyword != existing and keyword in existing for existing in covered_keywords):
            continue
        filtered.append(hit)
        if keyword:
            covered_keywords.append(keyword)
        if len(filtered) >= max_items:
            break
    return filtered


def _translation_term_items(dictionary):
    raw = dictionary.get("translation_terms", {})
    terms = []
    if isinstance(raw, dict):
        for key, value in raw.items():
            source = _safe_text(key)
            target = _slug(value)
            if source and target:
                terms.append((source, target))
    terms.sort(key=lambda item: len(item[0]), reverse=True)
    return terms


def _translate_chinese_object_id(text, dictionary):
    subject = _normalize_text(text)
    if not subject:
        return "", {"translated": False, "reason": "empty"}
    if not re.search(r"[\u4e00-\u9fff]", subject):
        slug = _slug(subject)
        return slug, {"translated": bool(slug), "source": "ascii_slug" if slug else "empty"}

    terms = _translation_term_items(dictionary)
    if not terms:
        return "", {"translated": False, "reason": "translation_terms_missing"}

    index = 0
    tokens = []
    misses = []
    while index < len(subject):
        ch = subject[index]
        if ch.isspace():
            index += 1
            continue
        matched = None
        for source, target in terms:
            if subject.startswith(source, index):
                matched = (source, target)
                break
        if matched:
            tokens.append(matched[1])
            index += len(matched[0])
            continue
        if re.match(r"[a-z0-9_]", ch):
            j = index + 1
            while j < len(subject) and re.match(r"[a-z0-9_]", subject[j]):
                j += 1
            token = _slug(subject[index:j])
            if token:
                tokens.append(token)
            index = j
            continue
        misses.append(ch)
        index += 1

    if misses or not tokens:
        return "", {"translated": False, "reason": "untranslated_terms", "misses": misses}
    return _slug("_".join(tokens)), {"translated": True, "source": "translation_terms"}


def _extract_suffix_from_test_id(current_test_id):
    if not current_test_id:
        return ""
    parts = _safe_text(current_test_id).replace("/", ".").replace("\\", ".").split(".")
    for p in reversed(parts):
        p = p.strip().lower()
        if not p or p in {"ui", "root", "page"}:
            continue
        if p in {"btn", "button", "cell"}:
            continue
        return p
    return parts[-1] if parts else ""


def build_semantic_id(page_id, object_id, role):
    page_id = _slug(page_id) or "ui"
    object_id = _slug(object_id) or "item"
    role = _safe_text(role).lower() or "action"
    if role == "resource_source":
        return f"{page_id}.{object_id}.source_button"
    if role.endswith("_state"):
        return f"{page_id}.{object_id}.{role}"
    return f"{page_id}.{object_id}.{role}"


def _test_id_suffix(dictionary, element_type, role, context_suffix=""):
    if context_suffix:
        return context_suffix
    role = _safe_text(role).lower()
    if role == "resource_source":
        return "button"
    if role.endswith("_state"):
        return role[:-6] if role.endswith("_state") else role
    type_map = _coerce_dict(dictionary.get("test_id_suffix"), {})
    if type_map and element_type and type_map.get(element_type):
        return _safe_text(type_map[element_type])
    return role.split("_")[-1] or "target"


def build_test_id(page_id, object_id, role, element_type, current_test_id, dictionary):
    page_id = _slug(page_id) or "ui"
    object_id = _slug(object_id) or "item"
    role = _safe_text(role).lower() or "action"
    element_type = _safe_text(element_type) or "unknown"
    suffix = _test_id_suffix(dictionary, element_type, role, context_suffix="")

    if role == "resource_source":
        return f"{page_id}.{object_id}.source.{suffix}"
    if role.endswith("_state"):
        base = role[:-6] if role.endswith("_state") else role
        return f"{page_id}.{object_id}.{base}.state"
    role_part = role.replace("_", ".")
    if suffix and suffix not in role_part:
        return f"{page_id}.{object_id}.{role_part}.{suffix}"
    return f"{page_id}.{object_id}.{role_part}"


def _build_target_name(page_name, object_name, role_name, type_name):
    object_name = _safe_text(object_name)
    role_name = _safe_text(role_name)
    type_name = _safe_text(type_name)
    if type_name and (object_name.endswith(type_name) or role_name.endswith(type_name)):
        type_name = ""
    parts = (
        _safe_text(page_name),
        object_name,
        role_name,
        type_name,
    )
    return "".join([p for p in parts if p])


def _build_display_name(page_name, object_name, role_name, type_name):
    base = _safe_text(page_name)
    object_name = _safe_text(object_name)
    role_name = _safe_text(role_name)
    type_name = _safe_text(type_name)
    if type_name and (object_name.endswith(type_name) or role_name.endswith(type_name)):
        type_name = ""
    subject = "".join([p for p in (object_name, role_name, type_name) if p])
    parts = [subject] if subject else []
    if not base:
        base = _safe_text(object_name)
    return "-".join([p for p in [base] + parts if p]) or base


def parse_chinese_semantic(description, context=None, dictionary_path=None, dictionary=None):
    context = context if isinstance(context, dict) else {}
    dictionary = dictionary or load_semantic_dictionary(dictionary_path)
    if not isinstance(dictionary, dict):
        dictionary = build_default_semantic_dictionary()

    text = _safe_text(description)
    normalized_text = _normalize_text(text)
    page_hint = _safe_text(context.get("pageId") or context.get("page_id") or context.get("page") or "")
    draft_path = _safe_text(context.get("path") or context.get("draftPath") or context.get("elementPath") or "")
    current_test_id = _safe_text(context.get("currentTestId") or context.get("current_test_id"))

    prop_item_click = re.search(r"第\s*(\d+)\s*个?\s*道具\s*点击区", text)
    if prop_item_click:
        index = prop_item_click.group(1)
        page_id, page_info = _match_dictionary(page_hint, text, dictionary, "pages", prefer_text=True)
        if not page_id:
            page_id = "bag" if "背包" in text else "ui"
        page_name = _safe_text(page_info.get("name")) or ("背包" if page_id == "bag" else page_id)
        object_id = f"prop_item_{index}"
        object_name = f"第{index}个道具"
        role_id = "item_click"
        role_name = "点击区"
        type_id = "Button"
        type_name = ""
        target_name = f"{page_name}{object_name}{role_name}"
        display_name = f"{page_name}-{object_name}{role_name}"
        return {
            "targetName": target_name,
            "displayName": display_name,
            "semanticId": f"{page_id}.{object_id}.click_area",
            "testId": current_test_id or f"{page_id}.{object_id}.click_area",
            "pageId": page_id,
            "role": role_id,
            "elementType": type_id,
            "parseEvidence": {
                "page": {
                    "id": page_id,
                    "name": page_name,
                    "source": page_info.get("source"),
                },
                "object": {
                    "id": object_id,
                    "name": object_name,
                    "names": [object_name],
                    "ids": [object_id],
                },
                "role": {
                    "id": role_id,
                    "name": role_name,
                },
                "type": {
                    "id": type_id,
                    "name": type_name,
                },
            },
            "warnings": [],
        }

    page_id, page_info = _match_dictionary(page_hint, text, dictionary, "pages", prefer_text=True)
    if not page_id:
        page_id = "ui"
    page_name = _safe_text(page_info.get("name")) or page_id

    tab_keywords = ("页签", "标签", "Tab", "tab")
    if any(keyword in text for keyword in tab_keywords):
        qualifier = normalized_text
        for word in (page_name, "界面", "页面", "页签", "标签", "Tab", "tab", "按钮"):
            qualifier = qualifier.replace(word, "")
        qualifier = qualifier.strip()
        qualifier_map = {
            "特殊": "special",
            "普通": "normal",
            "全部": "all",
            "道具": "prop_item",
            "材料": "material",
            "资源": "resource",
        }
        if re.fullmatch(r"\d+", qualifier or ""):
            object_id = f"tab_{qualifier}"
            object_name = f"{qualifier}号"
        else:
            qualifier_id, qualifier_info = _match_dictionary("", qualifier, dictionary, "objects")
            object_id = qualifier_map.get(qualifier, qualifier_id or (_semantic_token_id(qualifier) if qualifier else "tab"))
            object_name = _safe_text(qualifier_info.get("name")) if qualifier_id else qualifier
        target_subject = f"{object_name}页签按钮" if object_name else "页签按钮"
        requires_english_id = object_id.startswith("custom_")
        semantic_id = "" if requires_english_id else f"{_slug(page_id) or 'ui'}.{_semantic_token_id(object_id)}.tab.button"
        test_id = current_test_id or semantic_id
        return {
            "targetName": f"{page_name}{target_subject}",
            "displayName": f"{page_name}-{target_subject}",
            "semanticId": semantic_id,
            "testId": test_id,
            "pageId": page_id,
            "role": "tab",
            "elementType": "Button",
            "requiresEnglishId": requires_english_id,
            "parseEvidence": {
                "page": {
                    "id": page_id,
                    "name": page_name,
                    "source": page_info.get("source"),
                },
                "object": {
                    "id": object_id,
                    "name": object_name,
                    "names": [object_name] if object_name else [],
                    "ids": [object_id],
                },
                "role": {
                    "id": "tab",
                    "name": "页签",
                },
                "type": {
                    "id": "Button",
                    "name": "按钮",
                },
                "normalizedDescription": normalized_text,
                "source": {
                    "textLength": len(text),
                    "currentTestId": current_test_id,
                },
            },
            "warnings": ["tab_button_rule"] + (["english_id_required"] if requires_english_id else []),
        }

    object_hits = _match_dictionary_all(text, dictionary, "objects", max_items=4)
    if object_hits:
        object_id = ".".join([_slug(hit.get("id", "")) for hit in object_hits if _slug(hit.get("id", ""))])
        object_name = "".join([_safe_text(hit.get("name", "")) for hit in object_hits])
        object_name_list = [_safe_text(hit.get("name", "")) for hit in object_hits]
        object_id_list = [_safe_text(hit.get("id", "")) for hit in object_hits]
    else:
        object_id = ""
        object_name = ""
        object_name_list = []
        object_id_list = []
    warnings = []
    if not object_id:
        warnings.append("object_not_found_fallback")

    role_id, role_info = _match_dictionary("", text, dictionary, "roles")
    role_name = _safe_text(role_info.get("name")) or "\u64cd\u4f5c"
    if not role_id:
        role_id = "action"
        warnings.append("role_not_found_fallback")

    type_text = _normalize_text(text)
    for word in (page_name, "界面", "页面"):
        word = _safe_text(word)
        if word:
            type_text = type_text.replace(word, "")
    type_id, type_info = _match_dictionary("", type_text or text, dictionary, "types")
    type_name = _safe_text(type_info.get("name")) or "\u7ec4\u4ef6"
    if not type_id:
        type_id = "unknown"
        warnings.append("type_not_found_fallback")

    if "role_not_found_fallback" in warnings and type_id == "Button" and object_id:
        role_id = "button"
        role_name = ""
        warnings = [w for w in warnings if w != "role_not_found_fallback"]
        warnings.append("role_from_button_type")
    if "role_not_found_fallback" in warnings and type_id in {"Text", "Icon", "State", "Model"} and object_id:
        role_id = _slug(type_id)
        role_name = ""
        warnings = [w for w in warnings if w != "role_not_found_fallback"]
        warnings.append("role_from_visual_type")

    objectless_action_roles = {"back", "close", "confirm", "cancel", "use", "claim", "add"}
    objectless_action_button = (
        "object_not_found_fallback" in warnings
        and role_id in objectless_action_roles
        and type_id == "Button"
    )
    if objectless_action_button:
        object_id = role_id
        object_name = ""
        object_name_list = []
        object_id_list = []
        warnings = [w for w in warnings if w != "object_not_found_fallback"]
        warnings.append("objectless_action_button")
    elif "object_not_found_fallback" in warnings:
        derived_subject = _derive_subject_from_input(text, page_name=page_name, role_name=role_name, type_name=type_name)
        object_name = derived_subject or "\u5143\u7d20"
        translated_object_id, translation_info = _translate_chinese_object_id(object_name, dictionary)
        object_id = translated_object_id or _semantic_token_id(object_name)
        object_name_list = [object_name]
        object_id_list = [object_id]
        warnings = [w for w in warnings if w != "object_not_found_fallback"]
        warnings.append("object_auto_translated" if translated_object_id else "object_from_input_fallback")
        if "role_not_found_fallback" in warnings and role_id == "action":
            role_name = ""

    if "role_not_found_fallback" in warnings and type_id == "Button" and object_id:
        role_id = "button"
        role_name = ""
        warnings = [w for w in warnings if w != "role_not_found_fallback"]
        if "role_from_button_type" not in warnings:
            warnings.append("role_from_button_type")
    if "role_not_found_fallback" in warnings and type_id in {"Text", "Icon", "State", "Model"} and object_id:
        role_id = _slug(type_id)
        role_name = ""
        warnings = [w for w in warnings if w != "role_not_found_fallback"]
        if "role_from_visual_type" not in warnings:
            warnings.append("role_from_visual_type")

    if objectless_action_button:
        semantic_id = f"{_slug(page_id) or 'ui'}.{_slug(role_id)}.button"
        test_id = current_test_id or semantic_id
    else:
        requires_english_id = object_id.startswith("custom_")
        semantic_id = "" if requires_english_id else build_semantic_id(page_id, object_id, role_id)
        test_id = build_test_id(page_id, object_id, role_id, type_id, current_test_id, dictionary)
        if requires_english_id and not current_test_id:
            test_id = ""

    target_name = _build_target_name(page_name, object_name, role_name, type_name) or normalized_text[:30]
    display_name = _build_display_name(page_name, object_name, role_name, type_name) or target_name

    return {
        "targetName": target_name,
        "displayName": display_name,
        "semanticId": semantic_id,
        "testId": test_id,
        "pageId": page_id,
        "role": role_id,
        "elementType": type_id,
        "requiresEnglishId": (not objectless_action_button and object_id.startswith("custom_")),
        "parseEvidence": {
            "page": {
                "id": page_id,
                "name": page_name,
                "source": page_info.get("source"),
            },
            "object": {
                "id": object_id,
                "name": object_name,
                "names": object_name_list,
                "ids": object_id_list,
                "translation": translation_info if "translation_info" in locals() else {},
            },
            "role": {
                "id": role_id,
                "name": role_name,
            },
            "type": {
                "id": type_id,
                "name": type_name,
            },
            "normalizedDescription": normalized_text,
            "source": {
                "textLength": len(normalized_text),
                "currentTestId": current_test_id,
            },
        },
        "warnings": warnings,
    }
