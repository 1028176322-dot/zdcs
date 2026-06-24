#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GameContent 视觉识别模块 - 阶段六：OCR / 模板匹配接入

功能：
1. 模板匹配（基于 OpenCV）— 在 gameContent 截图中查找按钮/图标
2. OCR 文字识别 — 在 gameContent 截图中查找文字
3. 所有识别结果坐标统一为 game_content 坐标
4. 识别结果可直接传入 ClickExecutor 执行点击

坐标约定（文档 9 节）：
    所有输出坐标类型 = "game_content"
    坐标原点为 gameContent 左上角 (0,0)
    可通过 CoordinateMapper.content_to_screen() 转换为屏幕坐标

使用方式：
    vision = GameContentVision()
    
    # 模板匹配
    result = vision.match_template(game_content_img, "template.png")
    # → {"name": "use_button", "coordinateType": "game_content",
    #    "rect": [105, 630, 215, 700], "score": 0.93, "center": [160, 665]}
    
    # OCR 文字识别
    result = vision.ocr_text(game_content_img, "使用")
    # → {"text": "使用", "coordinateType": "game_content",
    #    "rect": [110, 640, 210, 690], "center": [160, 665]}
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image
from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(CONFIG_DIR, "templates")

# 检查 OpenCV 是否可用
_cv2_available = False
try:
    import cv2
    import numpy as np
    _cv2_available = True
except ImportError:
    logger.warning("OpenCV (cv2) 未安装，模板匹配不可用")

# 检查 pytesseract 是否可用
_tesseract_available = False
try:
    import pytesseract
    import os as _tess_os
    # 配置 Tesseract 可执行文件路径（自动查找安装位置）
    _tesseract_paths = [
        os.environ.get("AUTOSMOKE_TESSERACT_CMD", ""),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Tesseract-OCR", "tesseract.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Tesseract-OCR", "tesseract.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tesseract.exe"),
    ]
    for _tp in _tesseract_paths:
        if _tess_os.path.exists(_tp):
            pytesseract.pytesseract.tesseract_cmd = _tp
            _tesseract_available = True
            break

    # 如果 TESSDATA_PREFIX 未设置，自动推导
    if _tesseract_available and not os.environ.get("TESSDATA_PREFIX"):
        _tessdata_candidates = [
            os.path.join(os.path.dirname(_tp), "tessdata"),  # 与 tesseract.exe 同目录下的 tessdata
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Tesseract-OCR", "tessdata"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tessdata"),
        ]
        for _td in _tessdata_candidates:
            if _tess_os.path.exists(_td):
                os.environ["TESSDATA_PREFIX"] = _td
                break
except Exception:
    pass


class GameContentVision:
    """
    GameContent 视觉识别器

    基于 gameContent 截图进行模板匹配和 OCR 文字识别，
    所有输出坐标统一为 game_content 坐标。
    """

    def __init__(self, templates_dir: str = None):
        """
        初始化视觉识别器

        :param templates_dir: 模板图片目录
        """
        self.templates_dir = templates_dir or TEMPLATES_DIR
        Path(self.templates_dir).mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 工具方法
    # ============================================================

    @staticmethod
    def _pil_to_cv2(pil_img: Image.Image) -> Any:
        """PIL Image → OpenCV 图像（RGB→BGR）"""
        np_img = np.array(pil_img)
        return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

    @staticmethod
    def _cv2_to_pil(cv2_img: Any) -> Image.Image:
        """OpenCV 图像 → PIL Image"""
        rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    # ============================================================
    # 模板匹配
    # ============================================================

    def match_template(self, game_content_img: Image.Image,
                       template_path: str,
                       threshold: float = 0.8,
                       name: str = None) -> Optional[Dict]:
        """
        在 gameContent 截图中匹配模板

        :param game_content_img: gameContent PIL Image
        :param template_path: 模板图片路径
        :param threshold: 匹配阈值 (0.0~1.0)
        :param name: 模板名称，默认用文件名
        :return:
            {
                "name": "use_button",
                "coordinateType": "game_content",
                "rect": [left, top, right, bottom],
                "center": [cx, cy],
                "score": 0.93,
                "width": w,
                "height": h
            }
            未匹配到返回 None
        """
        if not _cv2_available:
            logger.error("OpenCV 不可用，无法执行模板匹配。pip install opencv-python")
            return None

        # 加载模板
        if not os.path.exists(template_path):
            # 在 templates 目录中搜索
            alt_path = os.path.join(self.templates_dir, template_path)
            if os.path.exists(alt_path):
                template_path = alt_path
            else:
                logger.error("模板文件不存在: %s", template_path)
                return None

        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            logger.error("无法加载模板: %s", template_path)
            return None

        tw, th = template.shape[1], template.shape[0]
        if tw > game_content_img.width or th > game_content_img.height:
            logger.warning("模板 (%dx%d) 大于截图 (%dx%d)",
                         tw, th, game_content_img.width, game_content_img.height)
            return None

        # 执行模板匹配
        source = self._pil_to_cv2(game_content_img)
        result = cv2.matchTemplate(source, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        logger.info("模板匹配 '%s': score=%.4f (threshold=%.2f)",
                    name or os.path.basename(template_path), max_val, threshold)

        if max_val < threshold:
            return None

        # 匹配成功：输出 game_content 坐标
        left, top = max_loc
        right = left + tw
        bottom = top + th
        cx = left + tw // 2
        cy = top + th // 2

        return {
            "name": name or os.path.splitext(os.path.basename(template_path))[0],
            "coordinateType": "game_content",
            "rect": [int(left), int(top), int(right), int(bottom)],
            "center": [int(cx), int(cy)],
            "score": round(float(max_val), 4),
            "width": tw,
            "height": th,
        }

    def match_templates(self, game_content_img: Image.Image,
                        template_dir: str = None,
                        threshold: float = 0.8) -> List[Dict]:
        """
        批量匹配 templates 目录下的所有模板

        :param game_content_img: gameContent PIL Image
        :param template_dir: 模板目录
        :param threshold: 匹配阈值
        :return: 匹配结果列表（按 score 降序）
        """
        template_dir = template_dir or self.templates_dir
        if not os.path.exists(template_dir):
            logger.warning("模板目录不存在: %s", template_dir)
            return []

        results = []
        for fname in sorted(os.listdir(template_dir)):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                tpl_path = os.path.join(template_dir, fname)
                result = self.match_template(
                    game_content_img, tpl_path,
                    threshold=threshold,
                    name=os.path.splitext(fname)[0]
                )
                if result:
                    results.append(result)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    # ============================================================
    # OCR 文字识别
    # ============================================================

    def ocr_get_texts(self, game_content_img: Image.Image,
                      lang: str = 'chi_sim+eng') -> List[Dict]:
        """
        对 gameContent 截图进行 OCR 识别，返回所有文字及其位置

        :param game_content_img: gameContent PIL Image
        :param lang: 识别语言（默认中文+英文）
        :return:
            [
                {
                    "text": "使用",
                    "coordinateType": "game_content",
                    "rect": [110, 640, 210, 690],
                    "center": [160, 665],
                    "confidence": 0.95
                },
                ...
            ]
            如果 pytesseract 不可用返回空列表
        """
        if not _tesseract_available:
            logger.error(
                "pytesseract 不可用。安装: pip install pytesseract\n"
                "同时需要安装 Tesseract-OCR: https://github.com/UB-Mannheim/tesseract/wiki"
            )
            return []

        try:
            import pytesseract
            # 使用 pytesseract 获取文字+位置
            data = pytesseract.image_to_data(
                game_content_img, lang=lang,
                output_type=pytesseract.Output.DICT
            )

            results = []
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                if text and conf > 0:
                    left = data['left'][i]
                    top = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    right = left + w
                    bottom = top + h
                    cx = left + w // 2
                    cy = top + h // 2

                    results.append({
                        "text": text,
                        "coordinateType": "game_content",
                        "rect": [left, top, right, bottom],
                        "center": [cx, cy],
                        "confidence": round(conf / 100.0, 2),
                        "size": [w, h],
                    })

            logger.info("OCR 识别到 %d 个文字", len(results))
            return results

        except Exception as e:
            logger.error("OCR 识别失败: %s", e)
            return []

    def ocr_find_text(self, game_content_img: Image.Image,
                      target_text: str,
                      lang: str = 'chi_sim+eng') -> Optional[Dict]:
        """
        在 gameContent 截图中搜索指定文字

        :param game_content_img: gameContent PIL Image
        :param target_text: 要搜索的文字
        :param lang: 识别语言
        :return: 第一个匹配的文字位置，未找到返回 None
        """
        all_texts = self.ocr_get_texts(game_content_img, lang)
        for item in all_texts:
            if target_text in item["text"]:
                logger.info("OCR 找到文字 '%s' → center=%s, conf=%.2f",
                          target_text, item["center"], item["confidence"])
                return item
        logger.info("OCR 未找到文字 '%s'", target_text)
        return None

    def ocr_find_text_click(self, game_content_img: Image.Image,
                            target_text: str,
                            lang: str = 'chi_sim+eng') -> Optional[Dict]:
        """
        找到文字并返回可直接用于 ClickExecutor.click_content() 的坐标

        :param game_content_img: gameContent PIL Image
        :param target_text: 要搜索的文字
        :param lang: 识别语言
        :return:
            {
                "text": "使用",
                "coordinateType": "content",
                "x": 160,
                "y": 665,
                "description": "点击文字: 使用"
            }
            未找到返回 None
        """
        result = self.ocr_find_text(game_content_img, target_text, lang)
        if not result:
            return None

        cx, cy = result["center"]
        return {
            "text": result["text"],
            "coordinateType": "content",
            "x": cx,
            "y": cy,
            "description": f"点击文字: {result['text']}",
            "rect": result["rect"],
            "confidence": result["confidence"],
        }

    # ============================================================
    # 综合识别
    # ============================================================

    def recognize(self, game_content_img: Image.Image,
                  template_dir: str = None,
                  ocr_lang: str = 'chi_sim+eng',
                  template_threshold: float = 0.8) -> Dict:
        """
        综合识别：模板匹配 + OCR

        :param game_content_img: gameContent PIL Image
        :param template_dir: 模板目录
        :param ocr_lang: OCR 语言
        :param template_threshold: 模板匹配阈值
        :return: 综合识别结果
        """
        result = {
            "image_size": [game_content_img.width, game_content_img.height],
            "templates": [],
            "ocr_texts": [],
            "matched_templates_count": 0,
            "ocr_texts_count": 0,
        }

        # 模板匹配
        templates = self.match_templates(
            game_content_img, template_dir, template_threshold
        )
        result["templates"] = templates
        result["matched_templates_count"] = len(templates)

        # OCR
        texts = self.ocr_get_texts(game_content_img, ocr_lang)
        result["ocr_texts"] = texts
        result["ocr_texts_count"] = len(texts)

        return result


# ============================================================
# 独立运行入口
# ============================================================

def test_game_content_vision():
    """测试视觉识别模块"""
    print("=" * 60)
    print("GameContent 视觉识别测试")
    print("=" * 60)

    vision = GameContentVision()

    # 测试1：模板匹配（如无可跳过）
    print("\n[测试1] 模板匹配...")
    test_img = Image.new("RGB", (318, 688), (50, 50, 50))
    if _cv2_available:
        # 创建一个临时模板
        tpl_path = os.path.join(vision.templates_dir, "_test_template.png")
        tpl = Image.new("RGB", (30, 30), (200, 200, 200))
        tpl.save(tpl_path)

        # 把模板贴在测试图左上角
        test_img.paste(tpl, (50, 50))

        result = vision.match_template(test_img, tpl_path, threshold=0.5)
        if result:
            print(f"  匹配成功: name={result['name']}, center={result['center']}, score={result['score']}")
            assert result["coordinateType"] == "game_content"
            print("  ✅ 通过")
        else:
            print("  ⚠ 未匹配到（阈值可能偏高）")

        # 清理
        os.remove(tpl_path)
    else:
        print("  ⚠ OpenCV 不可用，跳过")
        print("  ❌ 跳过测试")

    # 测试2：OCR 文字识别（如 pytesseract 不可用则跳过）
    print("\n[测试2] OCR 文字识别...")
    if _tesseract_available:
        # 创建一个带文字的测试图
        from PIL import ImageDraw, ImageFont
        ocr_img = Image.new("RGB", (318, 200), (255, 255, 255))
        draw = ImageDraw.Draw(ocr_img)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        draw.text((50, 50), "使用", fill=(0, 0, 0), font=font)

        texts = vision.ocr_get_texts(ocr_img)
        print(f"  识别到 {len(texts)} 个文字")
        for t in texts:
            print(f"    text=\"{t['text']}\" center={t['center']} conf={t['confidence']}")

        found = vision.ocr_find_text(ocr_img, "使用")
        if found:
            print(f"  找到文字 '使用': center={found['center']}")
            print("  ✅ 通过")
        else:
            print("  ⚠ 未找到文字（可能字体/语言问题）")

        click_info = vision.ocr_find_text_click(ocr_img, "使用")
        if click_info:
            print(f"  点击信息: content({click_info['x']},{click_info['y']})")
            assert click_info["coordinateType"] == "content"
            print("  ✅ 通过")
    else:
        print("  ⚠ pytesseract 不可用，跳过 OCR 测试")
        print("  安装: pip install pytesseract + Tesseract-OCR 引擎")

    # 测试3：综合识别
    print("\n[测试3] 综合识别...")
    result = vision.recognize(test_img)
    print(f"  模板匹配: {result['matched_templates_count']} 个")
    print(f"  OCR 文字: {result['ocr_texts_count']} 个")
    assert "image_size" in result
    assert "templates" in result
    assert "ocr_texts" in result
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print(f"\n模板目录: {vision.templates_dir}")
    if not _cv2_available:
        print("⚠ 提示: pip install opencv-python 启用模板匹配")
    if not _tesseract_available:
        print("⚠ 提示: pip install pytesseract + 安装Tesseract-OCR 启用OCR")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    test_game_content_vision()
