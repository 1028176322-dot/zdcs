"""
战斗模块（PVE）
"""
from airtest.core.api import *
from modules.common import safe_click, wait_for_ui, get_text


def enter_pve(poco):
    """进入PVE关卡选择界面"""
    print("[战斗] 进入PVE")
    if not safe_click(poco, "btn_pve"):
        touch(Template("imgs/btn_pve.png"))
    return wait_for_ui(poco, "pve_level_list", timeout=10)


def start_battle(poco):
    """开始战斗"""
    print("[战斗] 开始")
    if not safe_click(poco, "btn_start_battle"):
        touch(Template("imgs/btn_start_battle.png"))
    return True


def wait_battle_end(poco, timeout=120):
    """
    等待战斗结算出现
    通过检测"结算"UI控件来判断战斗是否结束
    比硬sleep快得多
    """
    print("[战斗] 等待结算...")
    return wait_for_ui(poco, "battle_result_panel", timeout=timeout)


def get_battle_result(poco):
    """获取战斗结果"""
    result = get_text(poco, "txt_battle_result")
    rewards = get_text(poco, "txt_rewards")
    return {
        "result": result,
        "rewards": rewards,
    }
