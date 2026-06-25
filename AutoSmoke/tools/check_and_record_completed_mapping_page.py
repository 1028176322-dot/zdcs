#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check whether one page's mappings are complete, then record progress.

This script is intentionally conservative: it writes the progress ledger only
after formal mappings, evidence, page-level validation, and target-workbench
draft states all agree.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
METADATA = ROOT / "metadata"
PROGRESS_FILE = WORKSPACE / "进度" / "已完成全部元素映射确认界面记录.md"
VALIDATE_URL = "http://127.0.0.1:5000/api/mapping_store/validate"

CONFIRMED_STATUSES = {
    "click_confirmed",
    "visual_confirmed",
    "confirmed",
    "formal_confirmed",
    "mapped",
    "approved",
    "collection_confirmed",
}
TEMPLATE_STATUSES = {"template"}
NON_REQUIRED_STATUSES = {"ignored", "rejected", "deprecated", "superseded"}
TARGET_WORKBENCH_SOURCES = {
    "target_workbench",
    "target_workbench_visual_assert",
    "target_workbench_click_confirm",
    "target_workbench_repair",
}
GENERIC_SEMANTIC_IDS = {
    "ui.entry.icon",
    "ui.entry.action",
    "ui.action",
    "ui.id.action",
    "ui.visual_check.action",
}


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def md_cell(value: Any) -> str:
    text = safe_text(value).replace("|", "\\|")
    return text.replace("\n", " ")


def is_productized_semantic_id(value: str) -> bool:
    text = safe_text(value)
    if not text:
        return False
    if "custom_" in text or ".." in text:
        return False
    if re.search(r"[\u4e00-\u9fff]", text):
        return False
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+", text))


def is_generic_semantic_id(value: str) -> bool:
    text = safe_text(value)
    if not text:
        return False
    if text.startswith("runtime."):
        return True
    base = re.sub(r"\.[0-9a-f]{6,12}$", "", text)
    return base in GENERIC_SEMANTIC_IDS or bool(re.fullmatch(r"ui\.[a-z0-9_]+_(clone_)?[a-z0-9_\.]+", base))


def resolve_page(page_query: str) -> dict[str, str]:
    query = safe_text(page_query)
    page_dict = read_json(METADATA / "mapping_store" / "pages" / "page_name_dictionary.json", {"pages": []})
    for page in page_dict.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_id = safe_text(page.get("pageId"))
        display_name = safe_text(page.get("displayName")) or page_id
        aliases = [safe_text(x) for x in page.get("aliases", [])]
        if query in {page_id, display_name, *aliases}:
            return {"pageId": page_id, "displayName": display_name}

    formal_path = METADATA / "mapping_store" / "formal" / "by_page" / f"{query}.json"
    if formal_path.exists():
        formal = read_json(formal_path)
        return {"pageId": safe_text(formal.get("pageId")) or query, "displayName": safe_text(formal.get("displayName")) or query}

    return {"pageId": query, "displayName": query}


def run_or_read_validate() -> dict[str, Any]:
    try:
        request = urllib.request.Request(VALIDATE_URL, data=b"{}", method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        report = read_json(METADATA / "mapping_store" / "validation_report.json", {})
        if isinstance(report, dict) and report:
            report = dict(report)
            report["validateSource"] = "validation_report.json"
            report["validateRefreshError"] = str(exc)
            return report
        return {"success": False, "passed": False, "error": str(exc), "validateSource": "unavailable"}


def evidence_exists(page_id: str, test_id: str, evidence_ref: str) -> bool:
    by_testid = METADATA / "mapping_store" / "evidence" / "by_testid" / page_id / f"{test_id}.json"
    if by_testid.exists():
        return True
    by_page = read_json(METADATA / "mapping_store" / "evidence" / "by_page" / f"{page_id}.json", {})
    items = by_page.get("items") if isinstance(by_page, dict) else {}
    if isinstance(items, dict) and evidence_ref in items:
        return (METADATA / safe_text(items[evidence_ref])).exists()
    return False


def is_dynamic_collection_template(mapping: dict[str, Any]) -> bool:
    collection = mapping.get("collection")
    locator = mapping.get("locator")
    if not isinstance(collection, dict):
        return False
    if safe_text(collection.get("type")) == "dynamic_list":
        return True
    if isinstance(locator, dict) and safe_text(locator.get("type")) == "dynamicList":
        return True
    return False


def collection_instance_ids(mapping: dict[str, Any]) -> list[str]:
    collection = mapping.get("collection")
    if not isinstance(collection, dict):
        return []
    pattern = safe_text(collection.get("semanticPattern"))
    indices = collection.get("visibleIndices")
    if not pattern or not isinstance(indices, list):
        return []
    ids: list[str] = []
    for index in indices:
        token = safe_text(index)
        if not token:
            continue
        ids.append(pattern.replace("{index}", token))
    return ids


def collection_template_is_covered(page_id: str, mapping: dict[str, Any], mappings: dict[str, Any]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    instance_ids = collection_instance_ids(mapping)
    if not instance_ids:
        return False, ["visible instance list is empty"]
    for instance_id in instance_ids:
        instance = mappings.get(instance_id)
        if not isinstance(instance, dict):
            missing.append(f"{instance_id}: formal missing")
            continue
        status = safe_text(instance.get("reviewStatus"))
        if status not in CONFIRMED_STATUSES:
            missing.append(f"{instance_id}: reviewStatus {status or '<empty>'}")
            continue
        evidence_ref = safe_text(instance.get("evidenceRef")) or f"EVIDENCE_{instance_id}"
        if not evidence_exists(page_id, instance_id, evidence_ref):
            missing.append(f"{instance_id}: evidence missing")
    return not missing, missing


def formal_mapping_exists(page_id: str, test_id: str) -> bool:
    if not page_id or not test_id:
        return False
    formal = read_json(METADATA / "mapping_store" / "formal" / "by_page" / f"{page_id}.json", {})
    mappings = formal.get("mappings") if isinstance(formal, dict) else {}
    return isinstance(mappings, dict) and test_id in mappings


def draft_is_required(draft: dict[str, Any], strict: bool) -> bool:
    status = safe_text(draft.get("reviewStatus") or draft.get("verify_status"))
    if status in NON_REQUIRED_STATUSES:
        return False
    if strict:
        return True
    if safe_text(draft.get("source")) in TARGET_WORKBENCH_SOURCES:
        return True
    if safe_text(draft.get("targetId")):
        return True
    if status in CONFIRMED_STATUSES:
        return True
    return False


def check_page(page_id: str, strict_drafts: bool) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    formal_path = METADATA / "mapping_store" / "formal" / "by_page" / f"{page_id}.json"
    draft_path = METADATA / "mapping_store" / "draft" / "by_page" / f"{page_id}.json"
    formal = read_json(formal_path, {})
    draft_page = read_json(draft_path, {})
    mappings = formal.get("mappings") if isinstance(formal, dict) else {}
    drafts = draft_page.get("drafts") if isinstance(draft_page, dict) else {}

    if not formal_path.exists():
        issues.append(f"formal page file missing: {formal_path}")
    if not isinstance(mappings, dict) or not mappings:
        issues.append("formal mappings are empty")
        mappings = {}
    if not draft_path.exists():
        warnings.append(f"draft page file missing: {draft_path}")
        drafts = {}
    if not isinstance(drafts, dict):
        drafts = {}

    formal_ids = set()
    click_count = 0
    visual_count = 0
    for key, mapping in sorted(mappings.items()):
        if not isinstance(mapping, dict):
            issues.append(f"formal {key}: mapping is not an object")
            continue
        test_id = safe_text(mapping.get("testId"))
        semantic_id = safe_text(mapping.get("semanticId"))
        target_name = safe_text(mapping.get("targetName"))
        display_name = safe_text(mapping.get("displayName"))
        evidence_ref = safe_text(mapping.get("evidenceRef")) or f"EVIDENCE_{test_id}"
        status = safe_text(mapping.get("reviewStatus"))
        element_type = safe_text(mapping.get("elementType"))
        role = safe_text(mapping.get("role"))
        formal_ids.add(test_id)

        if key != test_id:
            issues.append(f"formal {key}: key differs from testId {test_id}")
        if not test_id or not semantic_id:
            issues.append(f"formal {key}: testId/semanticId missing")
        if test_id != semantic_id:
            issues.append(f"formal {key}: testId differs from semanticId {semantic_id}")
        if not is_productized_semantic_id(semantic_id):
            issues.append(f"formal {key}: semanticId is not productized: {semantic_id}")
        if is_generic_semantic_id(semantic_id):
            issues.append(f"formal {key}: semanticId is generic fallback: {semantic_id}")
        if not target_name or not display_name:
            issues.append(f"formal {key}: targetName/displayName missing")
        if safe_text(mapping.get("pageId")) != page_id:
            issues.append(f"formal {key}: pageId mismatch: {mapping.get('pageId')}")
        if is_dynamic_collection_template(mapping):
            covered, missing_instances = collection_template_is_covered(page_id, mapping, mappings)
            if status not in TEMPLATE_STATUSES | CONFIRMED_STATUSES:
                issues.append(f"formal {key}: dynamic collection template status is invalid: {status or '<empty>'}")
            if not covered:
                issues.append(f"formal {key}: dynamic collection instances are not fully covered: {'; '.join(missing_instances[:8])}")
        else:
            if status not in CONFIRMED_STATUSES:
                issues.append(f"formal {key}: reviewStatus is not confirmed: {status or '<empty>'}")
            if not evidence_exists(page_id, test_id, evidence_ref):
                issues.append(f"formal {key}: evidence missing for {evidence_ref}")

        if role == "button" or element_type == "Button":
            click_count += 1
        else:
            visual_count += 1

    required_draft_count = 0
    pending_drafts = []
    for draft_id, draft in sorted(drafts.items()):
        if not isinstance(draft, dict) or not draft_is_required(draft, strict_drafts):
            continue
        required_draft_count += 1
        status = safe_text(draft.get("reviewStatus") or draft.get("verify_status"))
        test_id = safe_text(draft.get("testId") or draft.get("confirmedTestId") or draft.get("semanticId"))
        if status not in CONFIRMED_STATUSES:
            pending_drafts.append(f"{draft_id}:{status or '<empty>'}:{safe_text(draft.get('targetName') or draft.get('displayName'))}")
        elif test_id and test_id not in formal_ids:
            draft_page_id = safe_text(draft.get("pageId"))
            if draft_page_id and draft_page_id != page_id and formal_mapping_exists(draft_page_id, test_id):
                warnings.append(f"draft {draft_id}: belongs to {draft_page_id}, formal mapping exists there: {test_id}")
            else:
                issues.append(f"draft {draft_id}: confirmed testId has no formal mapping: {test_id}")

    if pending_drafts:
        sample = "; ".join(pending_drafts[:12])
        issues.append(f"required drafts not confirmed: {len(pending_drafts)}; {sample}")

    validate = run_or_read_validate()
    if not validate.get("passed"):
        issues.append(f"mapping_store validate failed: {validate.get('error') or validate.get('identityConflictCount') or validate.get('issueCount')}")

    return {
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "formalCount": len(mappings),
        "requiredDraftCount": required_draft_count,
        "clickCount": click_count,
        "visualCount": visual_count,
        "validate": validate,
    }


def next_sequence(rows: list[str]) -> int:
    max_seq = 0
    for row in rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if cells and cells[0].isdigit():
            max_seq = max(max_seq, int(cells[0]))
    return max_seq + 1


def build_completion_row(seq: int, page_name: str, page_id: str, result: dict[str, Any], complete_date: str, note: str) -> str:
    scope = f"formal {result['formalCount']} 项；目标 draft {result['requiredDraftCount']} 项；点击 {result['clickCount']} 项；视觉 {result['visualCount']} 项"
    validate = result.get("validate", {})
    validate_text = f"已完成；validate passed；identityConflictCount={validate.get('identityConflictCount', 0)}"
    return (
        f"| {seq} | {md_cell(page_name)} | {md_cell(page_id)} | {md_cell(scope)} | "
        f"{md_cell(validate_text)} | {md_cell(complete_date)} | {md_cell(note)} |"
    )


def build_validation_row(complete_date: str, page_id: str, result: dict[str, Any]) -> str:
    validate = result.get("validate", {})
    note = (
        f"pageId={page_id}; formal={result['formalCount']}; "
        f"identityConflictCount={validate.get('identityConflictCount', 0)}; "
        f"absolutePathHitCount={validate.get('absolutePathHitCount', 0)}"
    )
    return f"| {md_cell(complete_date)} | 页面完成检测 | 通过 | {md_cell(note)} |"


def replace_table_row(lines: list[str], header: str, page_id: str, new_row: str) -> list[str]:
    out = list(lines)
    try:
        start = next(i for i, line in enumerate(out) if line.strip() == header)
    except StopIteration:
        return out + ["", header, "", new_row]
    table_start = start + 1
    while table_start < len(out) and not out[table_start].lstrip().startswith("|"):
        table_start += 1
    table_end = table_start
    while table_end < len(out) and out[table_end].lstrip().startswith("|"):
        table_end += 1

    body_start = table_start + 2
    replaced = False
    cleaned = []
    for row in out[body_start:table_end]:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        is_blank_placeholder = cells and all(not cell for cell in cells)
        if is_blank_placeholder:
            continue
        if len(cells) >= 3 and cells[2] == page_id:
            cleaned.append(new_row)
            replaced = True
        else:
            cleaned.append(row)
    if not replaced:
        cleaned.append(new_row)
    out[body_start:table_end] = cleaned
    return out


def append_validation_row(lines: list[str], new_row: str, dedup_key: str = "") -> list[str]:
    """Append or replace a row in the 最近校验记录 table.

    If *dedup_key* (a pageId) is provided, the existing row for the same
    pageId is replaced instead of appended.  The pageId is embedded in
    the note column (column index 3), so we match on ``pageId=<dedup_key>``.
    """
    out = list(lines)
    header = "## 最近校验记录"
    try:
        start = next(i for i, line in enumerate(out) if line.strip() == header)
    except StopIteration:
        return out + ["", header, "", "| 日期 | 校验项 | 结果 | 备注 |", "|------|--------|------|------|", new_row]
    table_start = start + 1
    while table_start < len(out) and not out[table_start].lstrip().startswith("|"):
        table_start += 1
    table_end = table_start
    while table_end < len(out) and out[table_end].lstrip().startswith("|"):
        table_end += 1
    body_start = table_start + 2
    dedup_marker = f"pageId={dedup_key}" if dedup_key else None
    replaced = False
    cleaned = []
    for row in out[body_start:table_end]:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if cells and all(not cell for cell in cells):
            continue
        if dedup_marker and any(dedup_marker in cell for cell in cells):
            cleaned.append(new_row)
            replaced = True
        else:
            cleaned.append(row)
    if not replaced:
        cleaned.append(new_row)
    out[body_start:table_end] = cleaned
    return out


def update_progress_file(page_name: str, page_id: str, result: dict[str, Any], note: str, complete_date: str) -> None:
    text = PROGRESS_FILE.read_text(encoding="utf-8") if PROGRESS_FILE.exists() else ""
    lines = text.splitlines()
    rows = [line for line in lines if line.lstrip().startswith("|")]
    seq = next_sequence(rows)
    completion_row = build_completion_row(seq, page_name, page_id, result, complete_date, note)
    validation_row = build_validation_row(complete_date, page_id, result)
    lines = replace_table_row(lines, "## 已完成界面", page_id, completion_row)
    lines = append_validation_row(lines, validation_row, dedup_key=page_id)
    write_text(PROGRESS_FILE, "\n".join(lines).rstrip() + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and record completed AutoSmoke mapping page.")
    parser.add_argument("page", help="pageId, displayName, or alias, such as character_info")
    parser.add_argument("--note", default="", help="Extra note written to the progress ledger.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Completion date, default is today.")
    parser.add_argument("--strict-drafts", action="store_true", help="Require every non-ignored page draft to be confirmed.")
    parser.add_argument("--dry-run", action="store_true", help="Only check; do not write the progress ledger.")
    args = parser.parse_args()

    page = resolve_page(args.page)
    page_id = page["pageId"]
    page_name = page["displayName"]
    result = check_page(page_id, args.strict_drafts)
    print(json.dumps({"page": page, **result}, ensure_ascii=False, indent=2))

    if not result["passed"]:
        return 2
    if not args.dry_run:
        update_progress_file(page_name, page_id, result, args.note or "自动检测通过后写入", args.date)
        print(json.dumps({"recorded": True, "progressFile": str(PROGRESS_FILE)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
