#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Package-level tri-source matcher for QA_Reader handoff targets."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "metadata"
IMPORT_ROOT = METADATA / "handoff" / "imports"
MATCH_ROOT = METADATA / "handoff" / "matches"


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return {} if default is None else default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_text() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def source_breakdown(candidate: dict[str, Any]) -> dict[str, Any]:
    reasons = candidate.get("reasons", []) if isinstance(candidate.get("reasons"), list) else []
    risks = candidate.get("risks", []) if isinstance(candidate.get("risks"), list) else []
    runtime = 0.0
    code = 0.0
    ui_tree = 0.0
    if any(r in reasons for r in ("runtime_path_exact", "runtime_path_match")):
        runtime = 1.0
    elif "runtime_path_similar" in reasons or candidate.get("runtimeMatched"):
        runtime = 0.75
    elif "runtime_not_currently_matched" in risks:
        runtime = 0.2
    if "code_semantic" in reasons:
        code = 1.0
    elif "name_match" in reasons or "role_or_type_match" in reasons:
        code = 0.35
    if "name_match" in reasons and "page_match" in reasons:
        ui_tree = 0.85
    elif "name_match" in reasons or "page_match" in reasons:
        ui_tree = 0.55
    elif "weak_name_match" in reasons:
        ui_tree = 0.35
    if "debug_ui" in risks or "debug_ui_excluded" in risks:
        runtime = min(runtime, 0.1)
        code = min(code, 0.1)
        ui_tree = min(ui_tree, 0.1)
    return {
        "ui_tree": round(ui_tree, 3),
        "code_semantics": round(code, 3),
        "runtime": round(runtime, 3),
        "reasons": reasons,
        "risks": risks,
    }


def recommendation_status(candidate: dict[str, Any] | None, threshold: float) -> str:
    if not candidate:
        return "NO_CANDIDATE"
    risks = candidate.get("risks", []) if isinstance(candidate.get("risks"), list) else []
    score = float(candidate.get("score") or 0)
    if "debug_ui" in risks or "debug_ui_excluded" in risks:
        return "BLOCKED_DEBUG_CANDIDATE"
    if score >= threshold:
        return "RECOMMENDED"
    return "NEEDS_REVIEW"


def match_targets(package_id: str, limit: int = 10, threshold: float = 0.72, write_report: bool = True) -> dict[str, Any]:
    tasks_path = IMPORT_ROOT / package_id / "mapping_tasks_from_handoff.json"
    payload = read_json(tasks_path, {})
    targets = payload.get("targets", []) if isinstance(payload.get("targets"), list) else []
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from 元数据.target_candidate_matcher import recommend_candidates
    except Exception as exc:
        return {
            "success": False,
            "package_id": package_id,
            "error": "target_candidate_matcher_import_failed",
            "detail": str(exc),
        }
    results = []
    recommended = 0
    needs_review = 0
    blocked = 0
    for target in targets:
        if not isinstance(target, dict):
            continue
        rec = recommend_candidates(target, limit=limit)
        candidates = rec.get("candidates", []) if isinstance(rec.get("candidates"), list) else []
        enriched = []
        for cand in candidates:
            if not isinstance(cand, dict):
                continue
            item = dict(cand)
            item["sourceBreakdown"] = source_breakdown(item)
            enriched.append(item)
        best = enriched[0] if enriched else None
        status = recommendation_status(best, threshold)
        if status == "RECOMMENDED":
            recommended += 1
        elif status.startswith("BLOCKED"):
            blocked += 1
        else:
            needs_review += 1
        results.append(
            {
                "targetId": safe_text(target.get("targetId")),
                "targetName": safe_text(target.get("targetName")),
                "pageHint": safe_text(target.get("pageHint")),
                "role": safe_text(target.get("role")),
                "elementType": safe_text(target.get("elementType")),
                "status": status,
                "bestCandidate": best or {},
                "candidates": enriched,
            }
        )
    report = {
        "schema_version": "handoff_tri_source_match_report.v1",
        "success": True,
        "package_id": package_id,
        "tasks_path": str(tasks_path),
        "threshold": threshold,
        "summary": {
            "target_count": len(results),
            "recommended": recommended,
            "needs_review": needs_review,
            "blocked": blocked,
        },
        "results": results,
        "generated_at": now_text(),
    }
    if write_report:
        write_json(MATCH_ROOT / f"{package_id}.tri_source_match_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run tri-source matching for handoff targets.")
    parser.add_argument("package_id")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=0.72)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    report = match_targets(args.package_id, limit=args.limit, threshold=args.threshold, write_report=not args.no_write)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
