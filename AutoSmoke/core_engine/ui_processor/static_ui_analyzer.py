#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static UI analyzer for Unity C# source code."""

from __future__ import annotations

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from AutoSmoke.path_utils import as_abs_path


def _resolve_scripts_root() -> str:
    env_root = os.environ.get("AUTOSMOKE_UNITY_SCRIPTS_ROOT") or os.environ.get("AUTOSMOKE_UNITY_ROOT")
    if env_root:
        root = Path(env_root).expanduser()
        if root.exists():
            return str(root.resolve())

    fallback = Path(__file__).resolve().parents[3] / "s1" / "k3client" / "client" / "Assets" / "NewGameDemo" / "Scripts"
    if fallback.exists():
        return str(fallback)

    legacy_fallback = Path(__file__).resolve().parents[3] / "s1" / "k3client" / "client" / "Assets"
    return str(legacy_fallback.resolve())


class StaticUIAnalyzer:
    def __init__(self, scripts_root: str) -> None:
        self.scripts_root = scripts_root
        self.results: List[Dict] = []
        self.patterns = {
            "event_trigger_field": re.compile(r"(?:private|public|protected)\\s+EventTriggerListener\\s+(\\w+)\\s*;"),
            "event_trigger_public": re.compile(r"public\\s+EventTriggerListener\\s+(\\w+)\\s*;"),
            "add_listener": re.compile(r"UIHelper\\.AddListener\\s*\\(\\s*TFW\\.EventTriggerType\\.Click\\s*,\\s*([^,]+),\\s*([^,]+)"),
            "add_remove_listener": re.compile(r"AddRemoveListener\\s*\\(\\s*EventTriggerType\\.Click\\s*,\\s*(\\w+)"),
            "add_listener_direct": re.compile(r"(\\w+)\\.AddListener\\s*\\(\\s*TFW\\.EventTriggerType\\.Click\\s*,\\s*(\\w+)"),
            "button_onclick": re.compile(r"(\\w+)\\.onClick\\.AddListener\\s*\\(\\s*(\\w+)"),
            "button_scale_field": re.compile(r"(?:private|public|protected)\\s+ButtonScale\\s+(\\w+)\\s*;"),
            "class_declaration": re.compile(r"(?:public|internal)\\s+(?:partial\\s+)?class\\s+(\\w+)\\s*:?\\s*(\\w*)"),
        }

    def analyze_all_scripts(self) -> List[Dict]:
        print("=" * 60)
        print("Static UI Analyzer")
        print("=" * 60)
        print(f"Scan root: {self.scripts_root}")

        cs_files = []
        for root, _, files in os.walk(self.scripts_root):
            for file in files:
                if file.endswith(".cs"):
                    cs_files.append(os.path.join(root, file))

        print(f"Found {len(cs_files)} C# files")

        for cs_file in cs_files:
            self._analyze_single_file(cs_file)

        print(f"Analyze completed, result count: {len(self.results)}")
        return self.results

    def _analyze_single_file(self, file_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="gbk", errors="ignore") as f:
                content = f.read()

        rel_path = os.path.relpath(file_path, self.scripts_root)
        class_match = self.patterns["class_declaration"].search(content)
        class_name = class_match.group(1) if class_match else "Unknown"
        base_class = class_match.group(2) if class_match else ""

        event_trigger_fields = []
        for match in self.patterns["event_trigger_field"].finditer(content):
            event_trigger_fields.append(match.group(1))
        for match in self.patterns["event_trigger_public"].finditer(content):
            event_trigger_fields.append(match.group(1))

        button_scale_fields = []
        for match in self.patterns["button_scale_field"].finditer(content):
            button_scale_fields.append(match.group(1))

        ui_keywords = ["UI", "Hud", "Panel", "Window", "Dialog", "View", "Layer", "Page", "Popup", "Module"]
        is_ui_class = any(keyword in class_name for keyword in ui_keywords) or any(
            keyword in base_class for keyword in ui_keywords
        )
        has_ui_fields = bool(event_trigger_fields or button_scale_fields)

        if not is_ui_class and not has_ui_fields:
            return

        event_bindings = []
        for match in self.patterns["add_listener"].finditer(content):
            event_bindings.append(
                {
                    "type": "UIHelper.AddListener",
                    "target": match.group(1).strip(),
                    "handler": match.group(2).strip(),
                }
            )
        for match in self.patterns["add_remove_listener"].finditer(content):
            event_bindings.append(
                {"type": "AddRemoveListener", "target": match.group(1).strip(), "handler": "Unknown"}
            )
        for match in self.patterns["add_listener_direct"].finditer(content):
            event_bindings.append(
                {"type": "Direct.AddListener", "target": match.group(1).strip(), "handler": match.group(2).strip()}
            )
        for match in self.patterns["button_onclick"].finditer(content):
            event_bindings.append(
                {"type": "Button.onClick", "target": match.group(1).strip(), "handler": match.group(2).strip()}
            )

        if not (event_trigger_fields or button_scale_fields or event_bindings):
            return

        result = {
            "file": rel_path,
            "ui_class": class_name,
            "base_class": base_class,
            "event_trigger_fields": event_trigger_fields,
            "button_scale_fields": button_scale_fields,
            "event_bindings": event_bindings,
            "clickable_elements": [],
        }

        all_fields = event_trigger_fields + button_scale_fields
        for field in all_fields:
            result["clickable_elements"].append(
                {
                    "field_name": field,
                    "type": "EventTriggerListener" if field in event_trigger_fields else "ButtonScale",
                    "likely_name_in_ui": self._guess_ui_name(field),
                }
            )

        for binding in event_bindings:
            target = binding["target"]
            if ".gameObject" in target:
                var_name = target.split(".")[0].strip()
                result["clickable_elements"].append(
                    {
                        "field_name": var_name,
                        "type": "EventTriggerListener",
                        "likely_name_in_ui": self._guess_ui_name(var_name),
                        "handler": binding["handler"],
                    }
                )
            elif "." not in target:
                result["clickable_elements"].append(
                    {
                        "field_name": target,
                        "type": "Unknown",
                        "likely_name_in_ui": self._guess_ui_name(target),
                        "handler": binding["handler"],
                    }
                )

        self.results.append(result)

    def _guess_ui_name(self, field_name: str) -> str:
        name = field_name
        name = re.sub(r"^_+", "", name)
        name = re.sub(r"^m_", "", name)
        if "." in name:
            parts = name.split(".")
            if len(parts) >= 2:
                return re.sub(r"EventListener$", "", parts[1])
        name = re.sub(r"EventListener$", "", name)
        return re.sub(r"(Btn|Button|btn|button)$", "", name)

    def save_results(self, output_dir: str | None = None):
        if output_dir is None:
            output_dir = as_abs_path("reports/static_ui")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(output_dir, f"static_ui_analysis_{timestamp}.json")
        html_path = os.path.join(output_dir, f"static_ui_report_{timestamp}.html")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        self._generate_html_report(html_path, timestamp)
        print("analysis output:")
        print(f"  JSON: {json_path}")
        print(f"  HTML: {html_path}")
        return json_path, html_path

    def _generate_html_report(self, output_path: str, timestamp: str) -> None:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results_len = len(self.results)
        elements_count = sum(len(r["clickable_elements"]) for r in self.results)

        html_rows: List[str] = []
        for i, result in enumerate(self.results, 1):
            clickables_html: List[str] = []
            for elem in result["clickable_elements"]:
                handler = (
                    f"<p>handler: <span class=\"handler\">{elem.get('handler', '')}</span></p>"
                    if elem.get("handler")
                    else ""
                )
                clickables_html.append(
                    f"""
                    <div class="element">
                      <div class="element-name">Field: {elem['field_name']}</div>
                      <p>Type: <span class="event-type">{elem['type']}</span></p>
                      <p>UI key: <code>{elem['likely_name_in_ui']}</code></p>
                      {handler}
                    </div>
                    """
                )

            event_binding_html = []
            if result["event_bindings"]:
                event_binding_html.append("<h3>Event bindings</h3>")
                event_binding_html.append("<pre>")
                for binding in result["event_bindings"]:
                    event_binding_html.append(f"{binding['type']}: {binding['target']} -> {binding['handler']}\n")
                event_binding_html.append("</pre>")

            rows = "".join(clickables_html + event_binding_html)
            html_rows.append(
                f"""
                <div class="ui-class">
                    <div class="class-name">[{i}] {result['ui_class']}</div>
                    <div class="file-path">File: {result['file']}</div>
                    <p><strong>Base:</strong> {result['base_class']}</p>
                    <h3>Clickable elements ({len(result['clickable_elements'])})</h3>
                    {rows}
                </div>
                """
            )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Static UI Analyzer - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .summary {{ background: white; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .ui-class {{ background: white; padding: 20px; margin: 20px 0; border-radius: 5px; }}
                .class-name {{ color: #2c3e50; font-size: 1.5em; font-weight: bold; }}
                .file-path {{ color: #7f8c8d; font-family: monospace; }}
                .element {{ background: #ecf0f1; padding: 10px; margin: 10px 0; border-left: 4px solid #3498db; }}
                .element-name {{ font-weight: bold; color: #2980b9; }}
                .handler {{ color: #27ae60; font-family: monospace; }}
                .event-type {{ color: #e74c3c; }}
                pre {{ background: #2c3e50; color: #ecf0f1; padding: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Static UI Analyzer</h1>
                <p>Generated: {now_str}</p>
                <p>Scan root: {self.scripts_root}</p>
            </div>
            <div class="summary">
                <h2>Summary</h2>
                <p>UI classes: <strong>{results_len}</strong></p>
                <p>Clickable elements: <strong>{elements_count}</strong></p>
            </div>
            {''.join(html_rows)}
            <hr>
            <p><em>Generated by Static UI Analyzer</em></p>
        </body>
        </html>
        """

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)


def main() -> None:
    analyzer = StaticUIAnalyzer(_resolve_scripts_root())
    if not os.path.isdir(analyzer.scripts_root):
        print(f"Scan root not found: {analyzer.scripts_root}")
        print("Set AUTOSMOKE_UNITY_SCRIPTS_ROOT environment variable.")
        return
    results = analyzer.analyze_all_scripts()
    if not results:
        print("No clickable UI bindings found. Check scripts_root and C# naming pattern.")
        return
    analyzer.save_results()


if __name__ == "__main__":
    main()
