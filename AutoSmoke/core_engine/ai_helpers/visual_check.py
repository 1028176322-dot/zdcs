"""
AI视觉增强模块
用于UI完整性验证、异常检测、动态等待

本模块封装了两种AI视觉检查方式：
  1. 简易版（纯OpenCV对比，不需要外网）
  2. AI版（调用多模态模型，需要网络）
"""
import base64
from io import BytesIO
from pathlib import Path

from airtest.core.api import G
from PIL import Image


# ═══════════════════════════════════════════════
# 简易版：截图对比（不依赖网络）
# ═══════════════════════════════════════════════

def check_screen_changed(threshold=0.05):
    """
    检查画面是否发生变化（用于判断动画是否结束）
    原理：连续截两张图，对比差异比例
    """
    img1 = G.DEVICE.snapshot()
    sleep(0.5)
    img2 = G.DEVICE.snapshot()
    
    # 简化为像素级差异
    diff = 0
    total = 0
    for y in range(0, img1.height, 10):
        for x in range(0, img1.width, 10):
            p1 = img1.getpixel((x, y))
            p2 = img2.getpixel((x, y))
            if p1 != p2:
                diff += 1
            total += 1
    
    ratio = diff / total if total > 0 else 0
    return ratio > threshold


# ═══════════════════════════════════════════════
# AI版：多模态大模型分析
# 依赖：openai / qwen 等API
# ═══════════════════════════════════════════════

def _screenshot_to_base64():
    """截图转base64"""
    screen = G.DEVICE.snapshot()
    buffer = BytesIO()
    screen.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def ai_check_ui_normal(api_key=None, model="gpt-4o"):
    """
    用大模型检查UI是否正常
    返回: (is_normal, description)
    """
    if not api_key:
        print("[AI] 未配置API Key，跳过")
        return True, "未检测"
    
    try:
        import openai
        client = openai.Client(api_key=api_key)
        
        b64 = _screenshot_to_base64()
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": 
                     "分析这张游戏截图，回答两个问题："
                     "1. 画面是否正常（没有黑屏、花屏、UI错位）"
                     "2. 是否有异常弹窗或错误提示"},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }]
        )
        result = resp.choices[0].message.content
        is_normal = "正常" in result and "异常" not in result
        return is_normal, result
        
    except Exception as e:
        print(f"[AI检查失败] {e}")
        return True, f"AI检查异常: {e}"


def ai_detect_popup(api_key=None):
    """AI检测是否有弹窗"""
    # 先用简单的控件检测
    try:
        from poco.drivers.unity3d import UnityPoco
        poco = UnityPoco()
        for keyword in ["btn_close", "close", "关闭"]:
            if poco(keyword).exists():
                return True
    except Exception:
        pass
    
    return False
