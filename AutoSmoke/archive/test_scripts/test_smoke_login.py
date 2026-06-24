"""
P0 冒烟 — 登录
"""
import pytest
from modules.login import guest_login, account_login


class TestSmokeLogin:
    """登录冒烟测试"""
    
    @pytest.mark.p0
    def test_guest_login(self, poco):
        """P0: 游客登录"""
        success, msg = guest_login(poco)
        assert success, msg
    
    @pytest.mark.p0
    def test_account_login(self, poco):
        """P0: 账号登录"""
        success, msg = account_login(poco, "auto_test_01", "123456")
        assert success, msg
