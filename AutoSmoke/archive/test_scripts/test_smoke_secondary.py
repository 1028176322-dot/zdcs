"""
P1 冒烟 — 二级功能
部队 / 大地图 / 联盟 / 聊天
"""
import pytest
from modules.common import safe_click, wait_for_ui


class TestSmokeSecondary:
    
    @pytest.mark.p1
    def test_troop_formation(self, poco):
        """部队编成界面"""
        assert safe_click(poco, "btn_troop"), "部队按钮不可用"
        assert wait_for_ui(poco, "troop_panel", timeout=5), "部队界面未加载"
        safe_click(poco, "btn_back")
    
    @pytest.mark.p1
    def test_world_map(self, poco):
        """大地图浏览"""
        assert safe_click(poco, "btn_world_map"), "大地图按钮不可用"
        assert wait_for_ui(poco, "world_map", timeout=10), "大地图未加载"
        # 滚屏测试
        poco("world_map").swipe([0.1, 0.5])
        sleep(1)
        poco("world_map").swipe([-0.1, -0.3])
        sleep(1)
        safe_click(poco, "btn_back")
    
    @pytest.mark.p1
    def test_alliance(self, poco):
        """联盟界面"""
        assert safe_click(poco, "btn_alliance"), "联盟按钮不可用"
        assert wait_for_ui(poco, "alliance_panel", timeout=5), "联盟未加载"
        safe_click(poco, "btn_back")
    
    @pytest.mark.p1
    def test_chat(self, poco):
        """聊天功能"""
        assert safe_click(poco, "btn_chat"), "聊天按钮不可用"
        assert wait_for_ui(poco, "chat_panel", timeout=5), "聊天未加载"
        safe_click(poco, "btn_back")
