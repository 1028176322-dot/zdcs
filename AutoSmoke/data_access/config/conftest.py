"""
pytest 全局配置
设备连接、全局fixture、报告生成
"""
import pytest
from pathlib import Path
from poco.drivers.std import StdPoco

# ── MockDevice：模拟设备，用于直连Unity Editor ──────
class MockDevice:
    """模拟设备，不需要连手机/模拟器"""
    def __init__(self):
        self.uuid = 'localhost:5001'
    def display_info(self):
        return {'width': 1170, 'height': 2532}
    def get_default_device(self, **kw):
        return self
    def touch(self, *a, **kw):
        pass
    def swipe(self, *a, **kw):
        pass
    def snapshot(self, *a, **kw):
        pass


# ── 全局fixture ──────────────────────────────────────
@pytest.fixture(scope="session")
def poco():
    """连接Unity Editor中的Poco"""
    dev = MockDevice()
    p = StdPoco(5001, dev, ip='localhost')
    print(f"\n[Poco就绪] 屏幕: {p.get_screen_size()}")
    yield p


@pytest.fixture(autouse=True)
def auto_handle_popup(poco):
    """每一条用例执行前先清除弹窗"""
    from modules.common import handle_popups
    yield
    try:
        handle_popups(poco)
    except Exception:
        pass
