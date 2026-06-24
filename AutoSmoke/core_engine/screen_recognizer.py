"""
# -*- coding: utf-8 -*-
自动界面识别模块
通过UI树特征元素判断Unity当前在哪个界面
支持弹窗检测，可在每次点击后自动调用

识别原理：
  1. Dump当前UI树
  2. 提取所有文本 + 关键节点名称
  3. 与签名库匹配，返回最匹配的界面名称
  4. 同时检测是否有弹窗打开
"""

import sys
import os
import json
import time
from typing import Optional, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poco_connector.poco_connector import PocoConnector
from ui_processor.ui_tree_processor import UITreeProcessor


# ============================================================
# 界面签名库
# 每个界面由一组"特征元素"唯一标识
# 优先级：数字越大越优先匹配
# ============================================================

SCREEN_SIGNATURES = [
    # --- 背包界面（最高优先级） ---
    {
        'name': '背包界面',
        'signatures': [
            {'type': 'text_exact', 'value': '背包'},
            {'type': 'text_exact', 'value': '特殊'},
        ],
        'priority': 100,
    },
    # --- 商店界面 ---
    {
        'name': '商店界面',
        'signatures': [
            {'type': 'text_exact', 'value': '商店'},
        ],
        'priority': 100,
    },
    # --- 邮件界面 ---
    {
        'name': '邮件界面',
        'signatures': [
            {'type': 'text_exact', 'value': '邮件'},
        ],
        'priority': 100,
    },
    # --- 联盟界面 ---
    {
        'name': '联盟界面',
        'signatures': [
            {'type': 'text_contains', 'value': '联盟'},
            {'type': 'node_name_pattern', 'value': 'Alliance'},
        ],
        'priority': 100,
    },
    # --- 英雄界面 ---
    {
        'name': '英雄界面',
        'signatures': [
            {'type': 'text_contains', 'value': '英雄'},
            {'type': 'text_contains', 'value': '招募'},
        ],
        'priority': 100,
    },
    # --- 建筑升级面板 ---
    {
        'name': '建筑升级面板',
        'signatures': [
            {'type': 'text_contains', 'value': '升级'},
            {'type': 'text_contains', 'value': '当前等级'},
        ],
        'priority': 100,
    },
    # --- 活动界面 ---
    {
        'name': '活动界面',
        'signatures': [
            {'type': 'text_exact', 'value': '常规活动'},
        ],
        'priority': 100,
    },
    # --- 建造队列面板 ---
    {
        'name': '建造队列面板',
        'signatures': [
            {'type': 'text_exact', 'value': '队列1'},
        ],
        'priority': 100,
    },
    # --- 聊天界面 ---
    {
        'name': '聊天界面',
        'signatures': [
            {'type': 'text_contains', 'value': '聊天'},
        ],
        'priority': 100,
    },
    # --- 主城界面（兜底，最低优先级） ---
    # 条件：有建筑节点 + 无任何面板特征文本
    {
        'name': '主城界面',
        'signatures': [
            {'type': 'node_name_pattern', 'value': 'jianzhu'},
        ],
        'negative_signatures': [
            {'type': 'text_exact', 'value': '背包'},
            {'type': 'text_exact', 'value': '商店'},
            {'type': 'text_exact', 'value': '邮件'},
            {'type': 'text_contains', 'value': '联盟'},
            {'type': 'text_contains', 'value': '升级'},
        ],
        'priority': 1,
    },
]


# ============================================================
# 弹窗签名库
# 检测规则（避免误报）：
#   1. 有"确定"或"取消"按钮 → 一定是弹窗
#   2. 有Dialog/Popup节点 + 同时有按钮文本 → 可能是弹窗
#   3. 仅有Mask/Panel节点名 → 不算弹窗（误报率高）
# ============================================================

POPUP_SIGNATURES = [
    # 强信号：有"确定"按钮 → 一定是弹窗
    {
        'name': '确认按钮弹窗',
        'signatures': [
            {'type': 'text_exact', 'value': '确定'},
        ],
        'require_any': True,   # 任意命中即触发
    },
    # 强信号：有"取消"按钮
    {
        'name': '取消按钮弹窗',
        'signatures': [
            {'type': 'text_exact', 'value': '取消'},
        ],
        'require_any': True,
    },
    # 强信号：有"确认"按钮
    {
        'name': '确认按钮弹窗',
        'signatures': [
            {'type': 'text_exact', 'value': '确认'},
        ],
        'require_any': True,
    },
    # 弱信号：Dialog节点 + 有按钮文本（需同时满足）
    {
        'name': 'Dialog弹窗（含按钮）',
        'signatures': [
            {'type': 'node_name_pattern', 'value': 'Dialog'},
            {'type': 'text_contains', 'value': '定'},   # "确定"/"确认"
        ],
        'require_any': False,  # 全部命中才触发（AND）
    },
    # 弱信号：Popup节点 + 有按钮文本
    {
        'name': 'Popup弹窗（含按钮）',
        'signatures': [
            {'type': 'node_name_pattern', 'value': 'Popup'},
            {'type': 'text_contains', 'value': '定'},
        ],
        'require_any': False,
    },
]


# ============================================================
# 核心识别逻辑
# ============================================================

def _collect_ui_features(ui_tree: Dict) -> Dict:
    """
    从UI树中提取特征（所有文本、所有节点名、深度信息）
    返回: {
        'texts': set,
        'node_names': set,
        'all_text_list': list,
        'shallow_nodes': list,   # 深度<=3的节点名（弹窗节点通常较浅）
    }
    """
    texts = set()
    node_names = set()
    all_text_list = []
    shallow_nodes = []  # (name, depth)

    def traverse(node, depth=0):
        if not node or not isinstance(node, dict) or depth > 50:
            return
        # 收集文本
        text = node.get('text', '')
        if text and isinstance(text, str) and text.strip():
            t = text.strip()
            texts.add(t)
            all_text_list.append(t)
        # 收集节点名
        name = node.get('name', '')
        if name:
            node_names.add(name)
            if depth <= 5:
                shallow_nodes.append((name, depth))
        # 递归
        for child in node.get('children', []):
            traverse(child, depth + 1)

    traverse(ui_tree)

    return {
        'texts': texts,
        'node_names': node_names,
        'all_text_list': all_text_list,
        'shallow_nodes': shallow_nodes,
    }


def _match_signature(features: Dict, signature: Dict) -> bool:
    """
    判断特征是否匹配某个签名项
    """
    stype = signature['type']
    svalue = signature['value']

    if stype == 'text_exact':
        return svalue in features['texts']

    elif stype == 'text_contains':
        return any(svalue in t for t in features['all_text_list'])

    elif stype == 'node_name':
        return svalue in features['node_names']

    elif stype == 'node_name_pattern':
        svalue_lower = svalue.lower()
        return any(svalue_lower in name.lower() for name in features['node_names'])

    return False


def _match_screen(features: Dict, signatures: List[Dict]) -> Tuple[Optional[str], int, List[str]]:
    """
    匹配界面签名，返回 (界面名称, 匹配分数, 匹配依据列表)
    逻辑：
      - 正签名：全部匹配才算通过（AND）
      - 负向签名：任意一个匹配则排除该界面
    """
    best_name = None
    best_score = -1
    best_reasons = []

    for screen in signatures:
        reasons = []
        score = 0

        # 检查正签名：全部匹配才通过
        all_matched = True
        for sig in screen.get('signatures', []):
            if _match_signature(features, sig):
                reasons.append(f"{sig['type']}:{sig['value']}")
            else:
                all_matched = False
                break
        if not all_matched:
            continue

        # 检查负向签名：任意一个匹配则排除
        neg_sigs = screen.get('negative_signatures', [])
        neg_hit = False
        for sig in neg_sigs:
            if _match_signature(features, sig):
                neg_hit = True
                break
        if neg_hit:
            continue

        # 计算分数
        score = screen['priority'] + len(screen.get('signatures', [])) * 10

        if score > best_score:
            best_name = screen['name']
            best_score = score
            best_reasons = reasons

    return best_name, best_score, best_reasons


def _detect_popup(features: Dict, ui_tree: Dict) -> Tuple[bool, List[str]]:
    """
    检测当前是否有弹窗打开
    返回: (是否有弹窗, 弹窗特征描述列表)

    弹窗签名格式支持：
      - require_any=True：签名列表任意命中一个即匹配（OR）
      - require_any=False：签名列表全部命中才匹配（AND）
    """
    popup_reasons = []

    for popup_sig in POPUP_SIGNATURES:
        sigs = popup_sig.get('signatures', [])
        require_any = popup_sig.get('require_any', True)  # 默认OR

        if require_any:
            # OR逻辑：任意命中一个即匹配
            matched_any = False
            for sig in sigs:
                if _match_signature(features, sig):
                    matched_any = True
                    break
            if matched_any:
                popup_reasons.append(popup_sig['name'])
        else:
            # AND逻辑：全部命中才匹配
            all_matched = True
            for sig in sigs:
                if not _match_signature(features, sig):
                    all_matched = False
                    break
            if all_matched:
                popup_reasons.append(popup_sig['name'])

    has_popup = len(popup_reasons) > 0
    return has_popup, popup_reasons


# ============================================================
# 主入口
# ============================================================

def recognize_screen(connector: Optional[PocoConnector] = None,
                     ui_tree: Optional[Dict] = None,
                     processor: Optional[UITreeProcessor] = None,
                     detect_popup: bool = True) -> Dict:
    """
    识别当前Unity界面

    :param connector: 已有连接可传入，None则自动连接
    :param ui_tree: 已有UI树可传入，None则自动dump
    :param processor: 已有processor可传入
    :param detect_popup: 是否检测弹窗（默认True）
    :return: 识别结果字典
    """
    result = {
        'success': False,
        'screen_name': None,
        'confidence': 0,
        'match_reasons': [],
        'all_texts': [],
        'has_popup': False,
        'popup_reasons': [],
        'error': None,
    }

    # 连接Unity
    should_close = False
    if connector is None:
        connector = PocoConnector(device_type='Windows')
        if not connector.connect():
            result['error'] = '无法连接Unity，请确保Unity Editor正在运行并已点击Play'
            return result
        should_close = True

    try:
        # Dump UI树
        if ui_tree is None:
            ui_tree = connector.dump_ui_tree()
        if not ui_tree:
            result['error'] = 'dump UI树失败'
            return result

        # 处理UI树
        if processor is None:
            processor = UITreeProcessor(ui_tree)

        # 提取特征
        features = _collect_ui_features(processor.ui_tree)

        # 匹配界面
        screen_name, score, reasons = _match_screen(features, SCREEN_SIGNATURES)

        result['success'] = True
        result['screen_name'] = screen_name
        result['confidence'] = score
        result['match_reasons'] = reasons
        result['all_texts'] = sorted(list(features['texts']))

        # 检测弹窗
        if detect_popup:
            has_popup, popup_reasons = _detect_popup(features, processor.ui_tree)
            result['has_popup'] = has_popup
            result['popup_reasons'] = popup_reasons

        if screen_name is None and not has_popup:
            result['error'] = '未匹配到已知界面，可能是新界面或UI树不完整'

    except Exception as e:
        result['error'] = str(e)

    finally:
        if should_close:
            connector.close()

    return result


def click_and_recognize(element_name: str,
                        game_coords: Dict = None,
                        wait_time: float = 1.0,
                        connector: Optional[PocoConnector] = None) -> Dict:
    """
    点击元素后自动识别界面（点击 → 等待 → 识别）

    适用于：每次点击操作后调用，自动判断点击后进入了哪个界面/是否弹出弹窗
    用法：
        result = click_and_recognize('BagBtn')
        print(result['screen_name'])   # 点击后所在的界面
        print(result['has_popup'])    # 点击后是否有弹窗

    :param element_name: 要点击的元素名称（Poco节点名）
    :param game_coords: Game视图坐标（用于坐标转换），None则自动获取
    :param wait_time: 点击后等待时间（秒）
    :param connector: 已有连接可传入，None则自动连接并关闭
    :return: 识别结果字典（含点击是否成功）
    """
    from action_executor.action_executor import ActionExecutor

    result = {
        'click_success': False,
        'click_error': None,
        'screen_result': None,
    }

    should_close = False
    if connector is None:
        connector = PocoConnector(device_type='Windows')
        if not connector.connect():
            result['click_error'] = '无法连接Unity'
            return result
        should_close = True

    try:
        # 步骤1：点击元素
        executor = ActionExecutor(connector=connector)
        click_result = executor.click_element_by_name(element_name, game_coords)
        result['click_success'] = click_result.get('success', False)
        result['click_error'] = click_result.get('error', None)

        if not result['click_success']:
            return result

        # 步骤2：等待界面响应
        time.sleep(wait_time)

        # 步骤3：识别点击后的界面
        screen_result = recognize_screen(connector, detect_popup=True)
        result['screen_result'] = screen_result

    except Exception as e:
        result['click_error'] = str(e)

    finally:
        if should_close:
            connector.close()

    return result


def recognize_screen_and_print(connector=None, ui_tree=None, processor=None,
                              detect_popup: bool = True) -> Dict:
    """
    识别并打印结果（含弹窗信息）
    """
    result = recognize_screen(connector, ui_tree, processor, detect_popup)

    print("\n" + "=" * 60)
    print("界面识别结果")
    print("=" * 60)

    if not result['success']:
        print(f"✗ 识别失败: {result['error']}")
        return result

    # 弹窗信息（优先显示）
    if result.get('has_popup'):
        reasons = result.get('popup_reasons', [])
        print(f"⚠ 检测到弹窗！")
        for r in reasons:
            print(f"    - {r}")
        print()

    if result['screen_name']:
        print(f"✓ 当前界面: 【{result['screen_name']}】")
        print(f"  匹配依据:")
        for r in result['match_reasons']:
            print(f"    - {r}")
    else:
        print(f"⚠ 未识别到已知界面")
        if result['error']:
            print(f"  ({result['error']})")

    print(f"\n  当前界面所有文本（共{len(result['all_texts'])}个）:")
    for t in result['all_texts'][:30]:
        print(f"    - {t}")
    if len(result['all_texts']) > 30:
        print(f"    ... 还有 {len(result['all_texts']) - 30} 个文本未显示")

    print("=" * 60)
    return result


# ============================================================
# 独立运行入口
# ============================================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("AutoSmoke - 自动界面识别")
    print("=" * 60 + "\n")

    result = recognize_screen_and_print()

    # 保存结果
    output_dir = os.path.join(os.path.dirname(__file__), '../data_access/reports')
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())
    out_file = os.path.join(output_dir, f'screen_recognize_{timestamp}.json')

    save_data = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'result': result
    }
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {out_file}")
