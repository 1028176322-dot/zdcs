"""
公共方法模块
弹窗处理、等待工具等
"""
from airtest.core.api import *


def handle_popups(poco, max_rounds=5):
    """
    自动检测并关闭弹窗
    工作原理：检查是否有常见弹窗控件存在，依次尝试关闭
    """
    close_keywords = [
        "btn_close", "close", "关闭", "取消", "确定",
        "我知道了", "btn_confirm", "ok", "skip", "跳过",
    ]
    
    for _ in range(max_rounds):
        found = False
        for keyword in close_keywords:
            try:
                if poco(keyword).exists():
                    poco(keyword).click()
                    sleep(0.5)
                    found = True
                    print(f"[弹窗] 点击关闭: {keyword}")
                    break
            except Exception:
                continue
        
        if not found:
            return  # 没有弹窗了
    
    print(f"[弹窗] 已达最大轮次 {max_rounds}，疑似死循环")


def wait_for_ui(poco, name, timeout=10):
    """
    等待UI元素出现
    返回: True/False
    """
    try:
        poco(name).wait_for_appearance(timeout=timeout)
        return True
    except Exception:
        return False


def safe_click(poco, name, timeout=5):
    """
    安全点击：等待UI出现 → 点击
    返回: True/False
    """
    if wait_for_ui(poco, name, timeout):
        poco(name).click()
        return True
    print(f"[警告] UI元素未找到: {name}")
    return False


def get_text(poco, name):
    """
    获取UI文本，异常时返回空字符串
    """
    try:
        return poco(name).get_text()
    except Exception:
        return ""


def snapshot_save(tag=""):
    """
    截图保存，用于归档
    """
    from datetime import datetime
    screen = G.DEVICE.snapshot()
    filename = f"reports/snap_{tag}_{datetime.now():%H%M%S}.png"
    screen.save(filename)
    return filename
