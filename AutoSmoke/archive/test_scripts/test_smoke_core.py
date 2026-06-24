"""
P0 — 核心功能冒烟
主界面验证 / 建筑操作 / 商城 / 战斗
"""
import pytest
from modules.common import safe_click, wait_for_ui, handle_popups
from modules.battle import enter_pve, start_battle, wait_battle_end


class TestSmokeCore:
    
    @pytest.mark.p0
    def test_main_ui(self, poco):
        """主界面加载完整性"""
        assert wait_for_ui(poco, "main_ui", timeout=10), "主界面未加载"
        
        # 检查关键UI元素是否存在
        key_elements = ["resource_bar", "btn_building", "btn_battle", "btn_shop"]
        for elem in key_elements:
            assert poco(elem).exists(), f"缺少关键UI: {elem}"
    
    @pytest.mark.p0
    def test_building_click(self, poco):
        """建筑点击→返回"""
        # 点第一个建筑
        buildings = poco("building_root").child("building_item")
        if buildings:
            buildings[0].click()
            sleep(1)
            assert wait_for_ui(poco("building_detail"), timeout=5), "建筑详情未打开"
            # 关闭
            safe_click(poco, "btn_back")
    
    @pytest.mark.p0
    def test_shop_open(self, poco):
        """商城打开→关闭"""
        assert safe_click(poco, "btn_shop"), "商城按钮不可点击"
        assert wait_for_ui(poco, "shop_panel", timeout=5), "商城未打开"
        safe_click(poco, "btn_close")
    
    @pytest.mark.p1
    def test_pve_battle(self, poco):
        """PVE战斗完整流程"""
        assert enter_pve(poco), "进入PVE失败"
        start_battle(poco)
        assert wait_battle_end(poco, timeout=120), "战斗超时未结束"
        handle_popups(poco)
