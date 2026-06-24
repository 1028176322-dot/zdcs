#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture Unity UI tree and extract current page clickable elements."""

from __future__ import annotations

import os
import json
import time
from typing import Any, Dict, List

from AutoSmoke.path_utils import as_abs_path


def _connect_device() -> object:
    from airtest.core.api import connect_device
    from poco.drivers.unity3d import UnityPoco

    connect_device("Windows:///")
    return UnityPoco()


def _safe_html_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def capture_current_ui():
    print("=" * 60)
    print("Capture runtime UI tree")
    print("=" * 60)

    try:
        poco = _connect_device()
    except Exception as exc:  # pragma: no cover
        print(f"connect_device failed: {exc}")
        return None

    print("connected")
    ui_tree = poco.dump()
    if ui_tree is None:
        print("poco.dump() returned None")
        return None

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = as_abs_path(f"reports/runtime_capture/ui_tree_{timestamp}.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(ui_tree, f, ensure_ascii=False, indent=2)

    print(f"UI tree saved: {output_file}")
    return output_file, ui_tree


def extract_current_page_elements(ui_tree: Dict[str, Any]) -> List[Dict[str, str]]:
    clickable: List[Dict[str, str]] = []

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        payload = node.get("payload", {}) if isinstance(node, dict) else {}
        visible = payload.get("visible", True)
        if not visible:
            return

        text = payload.get("text", "")
        name = payload.get("name", "")
        node_type = payload.get("type", "")
        clickable_flag = payload.get("clickable", False)

        if clickable_flag and name:
            clickable.append(
                {
                    "name": str(name),
                    "text": str(text or ""),
                    "type": str(node_type or ""),
                }
            )

        for child in node.get("children", []) if isinstance(node, dict) else []:
            walk(child)

    walk(ui_tree)

    print(f"find {len(clickable)} clickable elements")
    return clickable


def filter_by_current_page(ui_tree: Dict[str, Any]) -> List[Dict[str, str]]:
    # Simple pass-through strategy in current version
    return extract_current_page_elements(ui_tree)


def _build_report(clickable: List[Dict[str, str]], timestamp: str, output_root: str) -> str:
    rows = []
    for i, elem in enumerate(clickable, 1):
        safe_name = _safe_html_escape(elem.get("name", ""))
        safe_text = _safe_html_escape(elem.get("text", "") or "-")
        safe_type = _safe_html_escape(elem.get("type", ""))
        rows.append(
            f"<li class=\"element\"><span>{i}. {safe_name}</span>"
            f" <span class=\"text\">{safe_text}</span>"
            f" <span class=\"type\">{safe_type}</span></li>"
        )

    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Current page elements</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { background: white; padding: 20px; border-radius: 8px; }
        .element { margin: 6px 0; }
        .type, .text { color: #666; margin-left: 8px; }
    </style>
</head>
<body>
<div class="container">
    <h2>Current page clickable elements</h2>
    <p>Count: {count}</p>
    <ul>
        {items}
    </ul>
</div>
</body>
</html>
"""

    html_path = output_root + f"current_page_report_{timestamp}.html"
    report_html = html.format(count=len(clickable), items="\n".join(rows))
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(report_html)
    return html_path


def main() -> None:
    result = capture_current_ui()
    if result is None:
        print("capture failed")
        return

    output_file, ui_tree = result
    clickable = filter_by_current_page(ui_tree)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    json_file = as_abs_path(f"reports/runtime_capture/current_page_elements_{timestamp}.json")
    html_file = as_abs_path(f"reports/runtime_capture/current_page_report_{timestamp}.html")
    os.makedirs(os.path.dirname(json_file), exist_ok=True)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(clickable, f, ensure_ascii=False, indent=2)

    with open(html_file, "w", encoding="utf-8") as f:
        rows = []
        for i, elem in enumerate(clickable, 1):
            rows.append(
                f"<li><strong>{_safe_html_escape(elem.get('name',''))}</strong>"
                f" <span>{_safe_html_escape(elem.get('text','') or '-')}</span>"
                f" <span>({ _safe_html_escape(elem.get('type','')) })</span></li>"
            )
        rows_joined = "\n".join(rows)
        html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Current page elements</title></head>
<body>
<h1>Current page elements</h1>
<p>count={len(clickable)}</p>
<ul>{rows_joined}</ul>
</body>
</html>
"""
        f.write(html)

    print(f"output json: {json_file}")
    print(f"output html: {html_file}")


if __name__ == "__main__":
    main()
