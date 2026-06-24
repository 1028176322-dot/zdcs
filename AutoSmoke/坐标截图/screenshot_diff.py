#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截图差异检测模块 - 阶段五：点击结果判定

功能：
1. 计算两张 gameContent 截图的差异比例
2. 生成差异高亮图（标记变化区域）
3. CLICK_CHANGED / CLICK_NO_CHANGE 分类
4. 输出结构化的 step_result.json

使用方式：
    differ = ScreenshotDiffer()
    result = differ.compare(before_gc_path, after_gc_path)
    # result["diff_ratio"] → 0.0034
    # result["result"] → "CLICK_CHANGED"
    # result["diff_image_path"] → 差异高亮图
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from PIL import Image, ImageChops, ImageDraw
from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = os.path.join(CONFIG_DIR, "screenshots")

# 差异判定阈值（文档 8.1 节）
DIFF_THRESHOLD_NO_CHANGE = 0.001   # 0.1% 以下 → 无变化
DIFF_THRESHOLD_SLIGHT = 0.02      # 2% 以下 → 轻微变化


class ScreenshotDiffer:
    """
    截图差异检测器

    对 gameContent 截图进行像素级差异比对，
    生成差异高亮图和结构化结果。
    """

    def __init__(self, pixel_threshold: int = 10,
                 output_dir: str = None):
        """
        初始化差异检测器

        :param pixel_threshold: 像素差异阈值（0~255），>此值视为变化
        :param output_dir: 输出目录
        """
        self.pixel_threshold = pixel_threshold
        self.output_dir = output_dir or SCREENSHOTS_DIR

    # ============================================================
    # 差异计算
    # ============================================================

    def calc_diff_ratio(self, before_img: Image.Image,
                        after_img: Image.Image) -> float:
        """
        计算两张截图的变化像素比例

        :param before_img: 点击前截图
        :param after_img: 点击后截图
        :return: 差异比例 (0.0 ~ 1.0)
        """
        if before_img.size != after_img.size:
            logger.warning("截图尺寸不一致: %s vs %s",
                          before_img.size, after_img.size)
            return 1.0

        diff = ImageChops.difference(before_img, after_img)
        diff_gray = diff.convert("L")
        changed = sum(1 for p in diff_gray.getdata() if p > self.pixel_threshold)
        total = diff_gray.width * diff_gray.height
        return changed / total if total > 0 else 0.0

    # ============================================================
    # 差异高亮图
    # ============================================================

    def generate_diff_image(self, before_img: Image.Image,
                            after_img: Image.Image) -> Image.Image:
        """
        生成差异高亮图

        将变化区域用红色半透明遮罩标注在 after 图上。

        :param before_img: 点击前截图
        :param after_img: 点击后截图
        :return: 差异高亮 PIL Image
        """
        w, h = after_img.size
        diff = ImageChops.difference(before_img, after_img)
        diff_gray = diff.convert("L")

        # 创建红色遮罩（标记变化区域）
        mask = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        mask_pixels = mask.load()
        diff_pixels = diff_gray.load()

        if mask_pixels and diff_pixels:
            for y in range(h):
                for x in range(w):
                    if diff_pixels[x, y] > self.pixel_threshold:
                        mask_pixels[x, y] = (255, 0, 0, 100)  # 半透明红

        # 叠加到 after 图上
        after_rgba = after_img.convert("RGBA")
        highlighted = Image.alpha_composite(after_rgba, mask)
        result = highlighted.convert("RGB")

        # 添加标注文字
        draw = ImageDraw.Draw(result)
        draw.text((5, 5), "Red = Changed area", fill=(255, 0, 0))

        return result

    # ============================================================
    # 结果分类
    # ============================================================

    @staticmethod
    def classify_result(diff_ratio: float) -> str:
        """
        根据差异比例分类点击结果

        :param diff_ratio: 差异比例
        :return: 结果分类
        """
        if diff_ratio < DIFF_THRESHOLD_NO_CHANGE:
            return "CLICK_NO_CHANGE"
        return "CLICK_CHANGED"

    @staticmethod
    def describe_change(diff_ratio: float) -> str:
        """
        描述变化程度

        :param diff_ratio: 差异比例
        :return: 描述文字
        """
        if diff_ratio < DIFF_THRESHOLD_NO_CHANGE:
            return "无可见变化"
        elif diff_ratio < DIFF_THRESHOLD_SLIGHT:
            return f"轻微变化 ({diff_ratio*100:.2f}%)"
        else:
            return f"明显变化 ({diff_ratio*100:.2f}%)"

    # ============================================================
    # 完整比较流程
    # ============================================================

    def compare(self, before_img: Image.Image,
                after_img: Image.Image,
                run_id: str = None,
                step_id: str = None,
                meta: Dict = None) -> Dict:
        """
        执行完整截图比较流程

        :param before_img: 点击前截图 (gameContent)
        :param after_img: 点击后截图 (gameContent)
        :param run_id: 运行批次 ID
        :param step_id: 步骤 ID
        :param meta: 额外元数据
        :return:
            {
                "status": "OK",
                "diff_ratio": 0.0034,
                "result": "CLICK_CHANGED",
                "description": "轻微变化 (0.34%)",
                "diff_image_path": "...",
                "step_result_path": "..."
            }
        """
        run_id = run_id or time.strftime("run_%Y%m%d_%H%M%S")
        step_id = step_id or f"step_{int(time.time())}"
        output_dir = os.path.join(self.output_dir, run_id)
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 计算差异
        diff_ratio = self.calc_diff_ratio(before_img, after_img)
        result_type = self.classify_result(diff_ratio)
        description = self.describe_change(diff_ratio)

        # 生成差异高亮图
        diff_img = self.generate_diff_image(before_img, after_img)
        diff_path = os.path.join(output_dir, f"diff_{step_id}_{timestamp}.png")
        diff_img.save(diff_path)

        # 构建 step_result
        step_result = {
            "step_id": step_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "diff_ratio": round(diff_ratio, 4),
            "result": result_type,
            "description": description,
            "pixel_threshold": self.pixel_threshold,
            "image_size": list(before_img.size),
        }
        if meta:
            step_result["meta"] = meta

        # 保存 step_result.json
        result_path = os.path.join(output_dir,
                                   f"step_result_{step_id}_{timestamp}.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(step_result, f, indent=2, ensure_ascii=False)

        return {
            "status": "OK",
            "diff_ratio": round(diff_ratio, 4),
            "result": result_type,
            "description": description,
            "diff_image_path": diff_path,
            "step_result_path": result_path,
            "step_result": step_result,
            "diff_image": diff_img,
        }

    # ============================================================
    # 便捷方法：从文件路径比较
    # ============================================================

    def compare_files(self, before_path: str, after_path: str,
                      **kwargs) -> Dict:
        """
        从文件路径加载截图并比较

        :param before_path: 点击前截图路径
        :param after_path: 点击后截图路径
        :return: 比较结果
        """
        before_img = Image.open(before_path)
        after_img = Image.open(after_path)
        meta = {
            "before": os.path.basename(before_path),
            "after": os.path.basename(after_path),
        }
        return self.compare(before_img, after_img, meta=meta, **kwargs)


# ============================================================
# 独立运行入口
# ============================================================

def test_screenshot_diff():
    """测试截图差异检测"""
    print("=" * 60)
    print("截图差异检测测试")
    print("=" * 60)

    differ = ScreenshotDiffer()

    # 测试1：相同图片 → CLICK_NO_CHANGE
    print("\n[测试1] 相同图片 → CLICK_NO_CHANGE...")
    from PIL import Image
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    result = differ.compare(img, img, run_id="test", step_id="test_01")
    assert result["result"] == "CLICK_NO_CHANGE"
    print(f"  result={result['result']}, diff_ratio={result['diff_ratio']}")
    print("  ✅ 通过")

    # 测试2：完全不同 → CLICK_CHANGED
    print("\n[测试2] 完全不同 → CLICK_CHANGED...")
    img1 = Image.new("RGB", (100, 100), (0, 0, 0))
    img2 = Image.new("RGB", (100, 100), (255, 255, 255))
    result = differ.compare(img1, img2, run_id="test", step_id="test_02")
    assert result["result"] == "CLICK_CHANGED"
    assert result["diff_ratio"] > 0.5
    print(f"  result={result['result']}, diff_ratio={result['diff_ratio']}")
    print("  ✅ 通过")

    # 测试3：微小差异 → CLICK_NO_CHANGE
    print("\n[测试3] 微小差异 → CLICK_NO_CHANGE...")
    img1 = Image.new("RGB", (100, 100), (100, 100, 100))
    img2 = Image.new("RGB", (100, 100), (101, 101, 101))  # 1的差异 < 阈值10
    result = differ.compare(img1, img2, run_id="test", step_id="test_03")
    assert result["result"] == "CLICK_NO_CHANGE"
    print(f"  result={result['result']}, diff_ratio={result['diff_ratio']}")
    print("  ✅ 通过")

    # 测试4：差异高亮图生成
    print("\n[测试4] 差异高亮图生成...")
    img1 = Image.new("RGB", (50, 50), (0, 0, 0))
    img2 = Image.new("RGB", (50, 50), (0, 0, 0))
    # 在 img2 中心画一个白点
    for dx in range(20, 30):
        for dy in range(20, 30):
            img2.putpixel((dx, dy), (255, 255, 255))
    result = differ.compare(img1, img2, run_id="test", step_id="test_04")
    assert os.path.exists(result["diff_image_path"]), "差异图应存在"
    diff_img = Image.open(result["diff_image_path"])
    print(f"  差异图尺寸: {diff_img.size}")
    print(f"  diff_ratio: {result['diff_ratio']:.4f}")
    print(f"  diff_image: {result['diff_image_path']}")
    print("  ✅ 通过")

    # 测试5：step_result 结构完整性
    print("\n[测试5] step_result 结构完整性...")
    sr = result["step_result"]
    required = ["step_id", "timestamp", "diff_ratio", "result", "description"]
    for field in required:
        assert field in sr, f"缺少字段: {field}"
    print(f"  字段: {list(sr.keys())}")
    print(f"  step_result_path: {result['step_result_path']}")
    assert os.path.exists(result["step_result_path"])
    print("  ✅ 通过")

    # 测试6：尺寸不一致 → 返回 1.0
    print("\n[测试6] 尺寸不一致...")
    img1 = Image.new("RGB", (100, 100), (0, 0, 0))
    img2 = Image.new("RGB", (200, 200), (255, 255, 255))
    ratio = differ.calc_diff_ratio(img1, img2)
    assert ratio == 1.0
    print(f"  diff_ratio={ratio}")
    print("  ✅ 通过")

    # 测试7：classify_result 边界测试
    print("\n[测试7] classify_result 边界...")
    print(f"  0.0005 → {differ.classify_result(0.0005)} (应=CLICK_NO_CHANGE)")
    print(f"  0.001  → {differ.classify_result(0.001)} (应=CLICK_CHANGED，等于阈值)")
    print(f"  0.01   → {differ.classify_result(0.01)} (应=CLICK_CHANGED)")
    assert differ.classify_result(0.0005) == "CLICK_NO_CHANGE"
    assert differ.classify_result(0.01) == "CLICK_CHANGED"
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)

    # 清理测试文件
    import shutil
    test_dir = os.path.join(SCREENSHOTS_DIR, "test")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    test_screenshot_diff()
