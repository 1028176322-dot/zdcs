"""
登录模块
"""
from airtest.core.api import *
from modules.common import wait_for_ui, safe_click, handle_popups


def guest_login(poco):
    """
    游客登录流程
    """
    print("[登录] 游客登录")
    
    # 点击游客登录按钮（控件名需要改成你们游戏的）
    if not safe_click(poco, "btn_guest_login"):
        # 兜底：截图识别点击
        touch(Template("imgs/btn_guest_login.png"))
    
    # 等待主界面加载
    if not wait_for_ui(poco, "main_ui", timeout=30):
        return False, "主界面未加载"
    
    # 清除登录后的弹窗
    handle_popups(poco)
    
    return True, "登录成功"


def account_login(poco, account, password):
    """
    账号密码登录
    """
    print(f"[登录] 账号登录: {account}")
    
    safe_click(poco, "btn_switch_login")
    safe_click(poco, "input_account")
    poco("input_account").set_text(account)
    
    safe_click(poco, "input_password")
    poco("input_password").set_text(password)
    
    safe_click(poco, "btn_confirm")
    
    if not wait_for_ui(poco, "main_ui", timeout=15):
        return False, "登录失败"
    
    handle_popups(poco)
    return True, "登录成功"
