# -*- coding: utf-8 -*-
"""定位测试"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from 定位.locate_game_area_smart import locate_game_area

if __name__ == '__main__':
    result = locate_game_area()
    print(f"定位结果: {result}")
