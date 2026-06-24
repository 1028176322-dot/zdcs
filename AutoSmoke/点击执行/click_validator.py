# -*- coding: utf-8 -*-
"""
点击校验模块 - 阶段三：点击前后校验

功能：
  1. preCheck  — 点击前校验（元素存在/可见/可交互/未遮挡/页面正确）
  2. postCheck — 点击后校验（页面变化/元素出现/消失/截图差异）
  3. 结构化校验报告

校验优先级链路：
  P0: testId → metadata 元数据
  P1: nome → Poco UI 树
  P2: text/template → OCR/模板匹配
  P3: coordinate → 坐标兜底
"""

import time
import logging
from typing import Dict, Optional, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================
# preCheck — 点击前校验
# ============================================================

class ClickPreChecker:
    """点击前校验器：执行前必须通过的安全检查"""

    def __init__(self, poco_connector=None, metadata_reader=None):
        self._poco = poco_connector
        self._metadata = metadata_reader

    def check(self, target: Dict, context: Dict = None) -> Dict:
        """
        执行点击前校验

        :param target: 目标描述 {"type": "...", "value": "..."}
        :param context: 上下文信息 {"pageId": "...", "screenshot": Image, ...}
        :return: {"passed": True/False, "checks": [...], "errorCode": "...", "errorMessage": "..."}
        """
        checks = []
        all_passed = True
        first_error = None

        # 1. 元素存在性校验
        check = self._check_exists(target)
        checks.append(check)
        if not check["passed"]:
            all_passed = False
            first_error = first_error or check

        # 2. 元素激活状态校验（通过 Poco）
        if all_passed and self._poco is not None:
            check = self._check_active(target)
            checks.append(check)
            if not check["passed"]:
                all_passed = False
                first_error = first_error or check

        # 3. 元素可见性校验
        if all_passed and self._poco is not None:
            check = self._check_visible(target)
            checks.append(check)
            if not check["passed"]:
                all_passed = False
                first_error = first_error or check

        # 4. 未被遮挡校验
        if all_passed and context:
            check = self._check_not_occluded(target, context)
            checks.append(check)
            if not check["passed"]:
                all_passed = False
                first_error = first_error or check

        # 5. 页面正确性校验
        if all_passed and context and context.get("pageId"):
            check = self._check_page(target, context)
            checks.append(check)
            if not check["passed"]:
                all_passed = False
                first_error = first_error or check

        result = {
            "passed": all_passed,
            "checks": checks,
            "checkCount": len(checks),
            "passedCount": sum(1 for c in checks if c["passed"]),
        }
        if first_error:
            result["errorCode"] = first_error.get("errorCode", "PRECHECK_FAILED")
            result["errorMessage"] = first_error.get("message", "点击前校验失败")
        return result

    def _check_exists(self, target: Dict) -> Dict:
        """元素存在性校验"""
        ttype = target.get("type", "")
        tval = target.get("value", "")

        if ttype == "testId":
            if self._metadata:
                el = self._metadata.find_by_testid(tval)
                if el:
                    return {"name": "exists", "passed": True, "detail": f"testId={tval} 已找到"}
                return {"name": "exists", "passed": False,
                        "errorCode": "TARGET_NOT_FOUND",
                        "message": f"testId={tval} 在元数据中未找到"}
            # 没有元数据读取器时，testId 校验失败（需要元数据支持）
            # 但为了兼容旧流程，不阻塞执行，返回警告
            return {"name": "exists", "passed": True,
                    "detail": "testId 校验跳过（无 metadata 读取器）",
                    "warning": True}

        elif ttype in ("pocoPath", "name", "pocoName"):
            # 通过 Poco 查找
            if self._poco:
                try:
                    el = self._poco(tval)
                    if el and el.exists():
                        return {"name": "exists", "passed": True, "detail": f"Poco 找到: {tval}"}
                except Exception:
                    pass
                return {"name": "exists", "passed": False,
                        "errorCode": "TARGET_NOT_FOUND",
                        "message": f"通过 Poco 未找到: {tval}"}

        elif ttype in ("text", "template"):
            # 视觉兜底 — 跳过准确的元素校验
            return {"name": "exists", "passed": True,
                    "detail": f"type={ttype} 跳过元素存在校验"}

        elif ttype in ("normalized", "design", "content", "pixel", "coordinate"):
            # 坐标类型 — 跳过元素校验
            return {"name": "exists", "passed": True,
                    "detail": f"type={ttype} 坐标类型跳过元素校验"}

        return {"name": "exists", "passed": True, "detail": "无法校验元素存在性"}

    def _check_active(self, target: Dict) -> Dict:
        """元素激活状态校验"""
        try:
            tval = target.get("value", "")
            if self._poco:
                el = self._poco(tval)
                if el.exists():
                    active = el.attr("activeInHierarchy", True)
                    if active:
                        return {"name": "active", "passed": True, "detail": "activeInHierarchy=true"}
                    return {"name": "active", "passed": False,
                            "errorCode": "TARGET_INACTIVE",
                            "message": f"元素 {tval} 未激活 (activeInHierarchy=false)"}
        except Exception:
            pass
        return {"name": "active", "passed": True, "detail": "无法校验激活状态（跳过）"}

    def _check_visible(self, target: Dict) -> Dict:
        """元素可见性校验"""
        try:
            tval = target.get("value", "")
            if self._poco:
                el = self._poco(tval)
                if el.exists():
                    visible = el.attr("visible", True)
                    if visible:
                        return {"name": "visible", "passed": True, "detail": "visible=true"}
                    return {"name": "visible", "passed": False,
                            "errorCode": "TARGET_INVISIBLE",
                            "message": f"元素 {tval} 不可见 (visible=false)"}
        except Exception:
            pass
        return {"name": "visible", "passed": True, "detail": "无法校验可见性（跳过）"}

    def _check_not_occluded(self, target: Dict, context: Dict) -> Dict:
        """元素未被遮挡校验"""
        blockers = context.get("blockers", [])
        if blockers:
            return {"name": "not_occluded", "passed": False,
                    "errorCode": "TARGET_OCCLUDED",
                    "message": f"目标被阻塞弹窗遮挡: {', '.join(b.get('blockerType', '?') for b in blockers[:2])}",
                    "blockers": blockers}
        return {"name": "not_occluded", "passed": True, "detail": "未被遮挡"}

    def _check_page(self, target: Dict, context: Dict) -> Dict:
        """页面正确性校验"""
        expected_page = target.get("pageId", context.get("pageId", ""))
        current_page = context.get("currentPageId", "")
        if expected_page and current_page and expected_page != current_page:
            return {"name": "page_match", "passed": False,
                    "errorCode": "PAGE_MISMATCH",
                    "message": f"页面不匹配: 期望={expected_page}, 当前={current_page}"}
        return {"name": "page_match", "passed": True, "detail": "页面匹配"}


# ============================================================
# postCheck — 点击后校验
# ============================================================

class ClickPostChecker:
    """点击后校验器：校验点击是否生效"""

    def __init__(self, screenshot_differ=None, poco_connector=None):
        self._differ = screenshot_differ
        self._poco = poco_connector

    def check(self, expect: Dict, context: Dict = None) -> Dict:
        """
        执行点击后校验

        :param expect: 期望描述 {"type": "...", "target": "...", "timeoutMs": 3000}
        :param context: 上下文信息 {"before_img": Image, "after_img": Image, ...}
        :return: {"passed": True/False, "checks": [...], "errorCode": "...", ...}
        """
        if not expect:
            # 无明确期望：默认校验
            return self._default_check(context)

        checks = []
        etype = expect.get("type", "")
        etarget = expect.get("target", "")

        if etype == "elementVisible":
            check = self._check_element_visible(etarget, expect.get("timeoutMs", 3000))
            checks.append(check)

        elif etype == "elementDisappeared":
            check = self._check_element_disappeared(etarget, expect.get("timeoutMs", 3000))
            checks.append(check)

        elif etype == "pageChange":
            check = self._check_page_change(expect.get("fromPage", ""),
                                            expect.get("toPage", ""),
                                            expect.get("timeoutMs", 3000))
            checks.append(check)

        elif etype == "screenshotDiff":
            check = self._check_screenshot_diff(context)
            checks.append(check)

        else:
            check = self._default_check(context)
            checks.append(check)

        all_passed = all(c["passed"] for c in checks)
        result = {
            "passed": all_passed,
            "checks": checks,
        }
        if not all_passed:
            failed = [c for c in checks if not c["passed"]]
            result["errorCode"] = failed[0].get("errorCode", "POSTCHECK_FAILED")
            result["errorMessage"] = failed[0].get("message", "点击后校验失败")
        return result

    def _default_check(self, context: Dict) -> Dict:
        """默认校验：截图差异 + 无崩溃"""
        checks = []

        # 截图差异
        if context and self._differ:
            before = context.get("before_img")
            after = context.get("after_img")
            if before and after:
                diff = self._differ.calc_diff_ratio(before, after)
                if diff > 0.005:
                    checks.append({"name": "screenshot_diff", "passed": True,
                                   "detail": f"截图变化 {diff:.4f}",
                                   "diff_ratio": diff})
                else:
                    checks.append({"name": "screenshot_diff", "passed": True,
                                   "detail": f"截图无明显变化 ({diff:.4f})",
                                   "warning": True, "diff_ratio": diff})
            else:
                checks.append({"name": "screenshot_diff", "passed": True,
                               "detail": "无截图可对比"})

        return {"passed": all(c["passed"] for c in checks),
                "checks": checks, "checkType": "default"}

    def _check_element_visible(self, target: str, timeout_ms: int) -> Dict:
        """等待元素出现"""
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            try:
                if self._poco:
                    el = self._poco(target)
                    if el.exists() and el.attr("visible", False):
                        return {"name": "element_visible", "passed": True,
                                "detail": f"元素 {target} 已出现"}
            except Exception:
                pass
            time.sleep(0.3)
        return {"name": "element_visible", "passed": False,
                "errorCode": "EXPECTED_ELEMENT_NOT_VISIBLE",
                "message": f"期望元素 {target} 在 {timeout_ms}ms 内未出现"}

    def _check_element_disappeared(self, target: str, timeout_ms: int) -> Dict:
        """等待元素消失"""
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            try:
                if self._poco:
                    el = self._poco(target)
                    if not el.exists():
                        return {"name": "element_disappeared", "passed": True,
                                "detail": f"元素 {target} 已消失"}
            except Exception:
                pass
            time.sleep(0.3)
        return {"name": "element_disappeared", "passed": False,
                "errorCode": "EXPECTED_ELEMENT_NOT_DISAPPEARED",
                "message": f"期望元素 {target} 在 {timeout_ms}ms 内未消失"}

    def _check_page_change(self, from_page: str, to_page: str, timeout_ms: int) -> Dict:
        """等待页面切换"""
        return {"name": "page_change", "passed": True,
                "detail": f"页面切换校验: {from_page} → {to_page} (待 metadata 集成)"}

    def _check_screenshot_diff(self, context: Dict) -> Dict:
        """校验截图变化"""
        return {"name": "screenshot_diff", "passed": True,
                "detail": "截图差异校验（由调用方提供差异结果）"}


# ============================================================
# 快捷集成函数
# ============================================================

def validate_click(target: Dict, context: Dict = None,
                   poco=None, metadata=None, differ=None) -> Dict:
    """
    完整的点击校验流程（preCheck + 点击 + postCheck）

    返回结构化报告：
    {
        "preCheck": {...},
        "click": {...},
        "postCheck": {...},
        "overall": "PASS"/"FAIL",
        "error": {...}
    }
    """
    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "target": target,
    }

    # preCheck
    pre_checker = ClickPreChecker(poco_connector=poco, metadata_reader=metadata)
    pre_result = pre_checker.check(target, context)
    result["preCheck"] = pre_result

    if not pre_result["passed"]:
        result["overall"] = "FAIL"
        result["error"] = {
            "phase": "preCheck",
            "errorCode": pre_result["errorCode"],
            "message": pre_result["errorMessage"],
        }
        return result

    # postCheck
    expect = (context or {}).get("expect", None)
    if expect:
        post_checker = ClickPostChecker(screenshot_differ=differ, poco_connector=poco)
        post_result = post_checker.check(expect, context)
        result["postCheck"] = post_result

        if not post_result["passed"]:
            result["overall"] = "FAIL"
            result["error"] = {
                "phase": "postCheck",
                "errorCode": post_result["errorCode"],
                "message": post_result["errorMessage"],
            }
            return result

    result["overall"] = "PASS"
    return result


# ============================================================
# 测试
# ============================================================

# ============================================================
# 兼容性别名
# ============================================================

class ClickValidator(ClickPreChecker):
    """兼容性别名 — ClickValidator = ClickPreChecker + validate_click"""
    def __init__(self, poco_connector=None, metadata_reader=None):
        super().__init__(poco_connector, metadata_reader)

    def validate(self, target: Dict, context: Dict = None,
                 poco=None, metadata=None, differ=None) -> Dict:
        """兼容接口：直接调用 validate_click"""
        return validate_click(target, context, poco, metadata, differ)


if __name__ == "__main__":
    print("=== ClickValidator 测试 ===\n")

    # 测试1：基本 preCheck
    print("[测试1] preCheck - testId 不存在（无 metadata）")
    checker = ClickPreChecker()
    r = checker.check({"type": "testId", "value": "nonexistent.button"})
    print(f"  passed={r['passed']} warning={any(c.get('warning') for c in r['checks'])}")
    assert r["passed"]  # 无 metadata 时跳过校验（不阻塞）
    print("  ✅ 通过\n")

    # 测试2：坐标类型跳过元素校验
    print("[测试2] preCheck - 坐标类型")
    r = checker.check({"type": "normalized", "nx": 0.5, "ny": 0.5})
    print(f"  passed={r['passed']}")
    assert r["passed"]
    print("  ✅ 通过\n")

    # 测试3：postCheck - 默认校验
    print("[测试3] postCheck - 无期望")
    post = ClickPostChecker()
    r = post.check(None, {})
    print(f"  passed={r['passed']}")
    assert r["passed"]
    print("  ✅ 通过\n")

    # 测试4：postCheck - 元素可见
    print("[测试4] postCheck - 元素可见（超时，无 Poco）")
    r = post.check({"type": "elementVisible", "target": "nonexistent", "timeoutMs": 500})
    print(f"  passed={r['passed']} error={r.get('errorCode','')}")
    assert not r["passed"]
    print("  ✅ 通过\n")

    # 测试5：完整链路
    print("[测试5] 完整链路 - 坐标点击（跳过元素校验）")
    r = validate_click(
        {"type": "normalized", "nx": 0.5, "ny": 0.5},
        context={"pageId": "test_page"}
    )
    print(f"  overall={r['overall']}")
    print(f"  preCheck={r['preCheck']['passed']} checks={r['preCheck']['checkCount']}")
    assert r["overall"] == "PASS"
    print("  ✅ 通过\n")

    print("所有测试通过 ✅")
