"""
全UI节点扫描 - 灰盒模式
带界面识别 + API协议面板监测 + 弹窗自动关闭
每次点击前识别当前界面，点击后检测API面板是否有协议发出
"""
import sys
import time
import os
import base64
import hashlib
import struct
from io import BytesIO
from datetime import datetime
from airtest.core.win.win import Windows
from airtest.core.api import touch as airtest_touch
from airtest.core.helper import G
from poco.drivers.unity3d import UnityPoco
import pywinauto
from PIL import ImageGrab

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')

# 导入网络消息监控（替代API Test面板截图监测）
try:
    from modules.net_monitor_watcher import NetMonitorWatcher
    net_monitor = NetMonitorWatcher()
    HAS_NET_MONITOR = True
    print("📡 网络消息监控器已加载")
except Exception as e:
    print(f"⚠️ 网络消息监控器加载失败: {e}")
    net_monitor = None
    HAS_NET_MONITOR = False


def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)


def snapshot_now():
    """截图GameView返回base64"""
    try:
        arr = G.DEVICE.snapshot()
        if arr is None:
            return None
        from PIL import Image
        img = Image.fromarray(arr)
        buf = BytesIO()
        img.save(buf, format='PNG', optimize=True)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except:
        return None


# ============================================================
#  网络消息灰盒集成（替代 API Test 面板截图监测）
#  C# 端: NetMessageMonitor.cs 挂钩 MessageMgr 收发事件
#  Python端: modules/net_monitor_watcher.py 读取日志文件
# ============================================================


def connect_and_calibrate():
    windows = pywinauto.findwindows.find_elements(class_name='UnityContainerWndClass')
    target = next(w for w in windows if w.rectangle.left > -1000)
    handle = target.handle
    print(f"🎯 Unity窗口: 0x{handle:08x}")

    dev = Windows(handle=handle)
    app = dev._app
    game_view = app.top_window().child_window(title="UnityEditor.GameView")
    gv = game_view.wrapper_object()
    gv_rect = game_view.rectangle()

    dev._top_window = gv
    dev.focus_rect = (0, 40, 0, 0)
    G.DEVICE = dev

    poco = UnityPoco(('localhost', 5001), connect_default_device=False)
    sw, sh = poco.get_screen_size()

    gv_w = gv_rect.right - gv_rect.left
    gv_h = gv_rect.bottom - gv_rect.top
    toolbar = 40
    work_w = gv_w
    work_h = gv_h - toolbar
    render_w = int(work_h * sw / sh)
    bar_l = (work_w - render_w) // 2

    print(f"📐 GameView: {gv_w}x{gv_h} → 渲染: {render_w}x{work_h} 黑边: {bar_l}px")

    calib = {
        'work_w': work_w, 'work_h': work_h,
        'render_w': render_w, 'bar_l': bar_l,
    }
    return dev, poco, calib


def calibrated_click(poco, calib, query=None, pos=None, desc=''):
    """通过节点名或原始坐标点击"""
    if query:
        try:
            elem = poco(query)
            px, py = elem.get_position()
            py = max(0, py - 0.03)
        except:
            print(f"     ⚠️ 找不到节点: {query}")
            return False
    elif pos:
        px, py = pos
    else:
        return False

    gv_x = px * calib['render_w'] + calib['bar_l']
    gv_y = py * calib['work_h']
    airtest_touch([int(gv_x), int(gv_y)])
    return True


# ============================================================
#  界面识别系统
# ============================================================

def get_ui_texts(raw):
    """提取所有UI上的文字"""
    texts = set()
    def extract(n):
        pld = n.get('payload', {})
        for k in ['text', 'Text', 'content', '_text']:
            v = str(pld.get(k, '')).strip()
            if v and len(v) < 40:
                texts.add(v)
        for c in n.get('children', []):
            extract(c)
    extract(raw)
    return texts


def get_ui_names(raw):
    """提取所有节点名（去重）"""
    names = set()
    def walk(n):
        name = n.get('name', '')
        if name:
            names.add(name)
        for c in n.get('children', []):
            walk(c)
    walk(raw)
    return names


def get_active_windows(raw):
    """识别当前UI树中哪些顶层窗口/面板是活跃的"""
    windows_found = []

    def walk(n, depth=0):
        name = n.get('name', '')
        pld = n.get('payload', {})

        # 查找 DeepUI 下的各种面板
        if '[' in name and ']' in name:
            # 提取方括号里的类名: UIMainPopup
            bracket_name = name[name.index('[')+1:name.index(']')] if ']' in name else name
            windows_found.append(bracket_name)

        # 也检查非标准命名的窗口
        keywords = ['Window', 'Panel', 'Popup', 'Dialog', 'View', 'Page']
        if any(k in name for k in keywords) and depth >= 2:
            if name not in [w for w in windows_found]:
                windows_found.append(name)

        for c in n.get('children', []):
            walk(c, depth+1)

    walk(raw)
    return windows_found


# 屏幕识别规则：界面名 → (必要条件, 可选条件)
SCREEN_RULES = {
    '主城主界面': {
        'must_have_texts': [],  # 任何文字
        'must_have_names': ['MenuRoot', 'UIMainPopup', 'Train'],
        'exclude_names': [],    # 不排除
        'desc': '🏙️ 主城主界面 - 底部导航栏可见，显示主城场景',
    },
    '英雄管理': {
        'must_have_texts': ['英雄'],
        'must_have_names': ['Hero', 'MenuRoot'],
        'desc': '⚔️ 英雄界面 - 英雄列表/羁绊/升级',
    },
    '小游戏界面': {
        'must_have_texts': ['小游戏'],
        'must_have_names': ['Skill', 'MenuRoot'],
        'desc': '🎮 小游戏界面 - 迷你游戏入口',
    },
    '世界地图': {
        'must_have_texts': ['世界'],
        'must_have_names': ['World'],
        'desc': '🌍 世界地图 - 大地图/行军',
    },
    '联盟界面': {
        'must_have_texts': ['联盟'],
        'must_have_names': ['Alliance'],
        'desc': '🏰 联盟界面 - 联盟列表/加入联盟',
    },
    '训练界面': {
        'must_have_texts': ['训练'],
        'must_have_names': ['Train'],
        'desc': '🏋️ 训练界面 - 士兵/部队训练',
    },
    '商店': {
        'must_have_texts': ['商店', '商品'],
        'must_have_names': ['Shop'],
        'desc': '🛒 商店 - 物品购买',
    },
    '背包': {
        'must_have_texts': ['背包', '道具'],
        'must_have_names': ['Bag'],
        'desc': '🎒 背包 - 道具/物品列表',
    },
    '邮件': {
        'must_have_texts': ['邮件'],
        'must_have_names': ['Mail'],
        'desc': '📧 邮件 - 系统邮件列表',
    },
    '活动面板': {
        'must_have_texts': ['活动'],
        'must_have_names': ['UIActivityMain', 'Activity'],
        'desc': '🎉 活动面板 - 限时活动/任务',
    },
    'GM调试窗口': {
        'must_have_names': ['UIGmWindow'],
        'desc': '🔧 GM调试窗口',
    },
    '未知界面(弹窗覆盖)': {
        'must_have_names': [],
        'desc': '❓ 弹窗覆盖中，无法识别主界面',
    },
}


def identify_current_screen(poco, base_info=None):
    """
    识别当前游戏是什么界面
    返回: (界面名, 描述, 活跃窗口列表)
    """
    raw = poco.agent.hierarchy.dump()
    texts = get_ui_texts(raw)
    names = get_ui_names(raw)
    windows = get_active_windows(raw)

    # 1. 检查 DeepUI 是否有额外面板（弹窗/活动覆盖层）
    has_overlay = False
    overlay_name = ''
    def find_deep_panels(n):
        nonlocal has_overlay, overlay_name
        name = n.get('name', '')
        pld = n.get('payload', {})
        # 检查 DeepUI > LayerUI 或 DialogUI 下的非空面板
        if 'UIActivityMain' in name:
            has_overlay = True
            overlay_name = 'UIActivityMain'
        if 'Dialog' in name and 'UI' in name:
            has_overlay = True
            overlay_name = name
        for c in n.get('children', []):
            find_deep_panels(c)

    # 从根部找
    def walk_root(n):
        if n.get('name') == 'DeepUI':
            for child in n.get('children', []):
                if child.get('name') in ('LayerUI', 'DialogUI', 'PanelUI'):
                    for sub in child.get('children', []):
                        sub_name = sub.get('name', '')
                        if sub_name and 'Root' not in sub_name:
                            has_overlay = True
                            find_deep_panels(sub)
        for c in n.get('children', []):
            walk_root(c)

    walk_root(raw)

    # 2. 如果 detects overlay，优先报告
    if has_overlay:
        # 看看是哪种弹窗
        if 'UIActivityMain' in overlay_name:
            return '活动面板', '🎉 活动面板 (DeepUI覆盖层)', windows
        return '未知界面(弹窗覆盖)', '❓ 弹窗/面板覆盖中', windows

    # 3. 规则匹配
    # 底部导航栏哪些按钮在 -> 判断当前主界面是哪个
    nav_buttons = {
        'Train': '主城',
        'Skill': '小游戏',
        'Hero': '英雄',
        'Alliance': '联盟',
        'World': '世界',
    }

    # 先看底部导航栏状态
    active_nav = []
    for btn_name, btn_desc in nav_buttons.items():
        if btn_name in names:
            active_nav.append(btn_desc)

    # 检查GM窗口
    if 'UIGmWindow' in names:
        return 'GM调试窗口', '🔧 GM调试窗口', windows

    # 按规则匹配
    for screen_name, rule in SCREEN_RULES.items():
        if not rule['must_have_names']:
            continue
        # 所有必要条件都满足
        must_match = all(n in names for n in rule['must_have_names'])
        if not must_match:
            continue
        # 文字条件
        if rule.get('must_have_texts'):
            text_match = any(t in texts for t in rule['must_have_texts'])
            if not text_match:
                continue
        return screen_name, rule['desc'], windows

    # 4. 如果都匹配不上，基于活跃窗口和特征推断
    # 检查是否在深处有特别的bracket名称
    deep_windows = [w for w in windows if w not in ('UIRoot', 'UIRoot2', 'DeepUI')]
    if deep_windows:
        # 取最深的那个
        best = deep_windows[-1]
        return f'窗口: {best}', f'📄 当前窗口: {best}', windows

    return '未知界面', '❓ 无法识别当前界面', windows


def is_main_screen(poco, base_windows, base_texts):
    """判断当前是否在主画面（和基线对比）"""
    raw = poco.agent.hierarchy.dump()
    curr_windows = get_active_windows(raw)
    curr_texts = get_ui_texts(raw)

    # 如果 DeepUI 下有额外面板，肯定不在主画面
    def has_extra_deep(n):
        if n.get('name') == 'DeepUI':
            for child in n.get('children', []):
                if child.get('name') in ('LayerUI', 'DialogUI', 'PanelUI'):
                    for sub in child.get('children', []):
                        sub_name = sub.get('name', '')
                        if sub_name and sub_name not in ('Root', '') and 'Root' not in sub_name:
                            return True
        for c in n.get('children', []):
            if has_extra_deep(c):
                return True
        return False
    raw = poco.agent.hierarchy.dump()
    if has_extra_deep(raw):
        return False

    # 窗口数量大致相同
    if abs(len(curr_windows) - len(base_windows)) > 3:
        return False

    return True


def try_dismiss_popups(poco, calib, base_info=None, max_attempts=6):
    """尝试关闭弹窗，返回True表示回到了主画面"""
    raw_before = poco.agent.hierarchy.dump()

    dismiss_strategies = [
        # 策略1: 找典型的关闭按钮
        ['buttn_close', 'Close', '关闭', '好的', 'OK', 'Cancel', '取消'],
        # 策略2: 找带EventTrigger的Bg(点击背景关闭)
        ['Bg'],
        # 策略3: 点主城按钮回去
        ['Train'],
        # 策略4: 点底栏第一个(Skill)再点主城
        ['Skill', 'Train'],
        # 策略5: 点击返回/后退
        ['Back', '返回'],
        # 策略6: CloseBtn
        ['CloseBtn', 'BtnClose'],
    ]

    for attempt, strategy in enumerate(dismiss_strategies):
        if attempt >= max_attempts:
            break

        for target_name in strategy:
            try:
                elem = poco(target_name)
                px, py = elem.get_position()
                py = max(0, py - 0.02)
                gv_x = px * calib['render_w'] + calib['bar_l']
                gv_y = py * calib['work_h']
                airtest_touch([int(gv_x), int(gv_y)])
                time.sleep(0.8)
            except:
                continue

            # 检查是否回到主画面：用界面识别判断
            screen_name, _, _ = identify_current_screen(poco)
            if screen_name == '主城主界面':
                return True

    return False


def find_clickable_nodes(poco):
    """找到所有可点击的UI节点"""
    raw = poco.agent.hierarchy.dump()
    clickable = []

    def walk(node):
        name = node.get('name', '')
        payload = node.get('payload', {})
        components = payload.get('components', [])
        has_event = 'EventTriggerListener' in components
        has_button = 'Button' in components

        if has_event or has_button:
            pos = payload.get('pos', [])
            if len(pos) >= 2:
                px, py = float(pos[0]), float(pos[1])
                clickable.append({
                    'name': name,
                    'pos': (px, py),
                })

        for child in node.get('children', []):
            walk(child)

    walk(raw)
    # 去重：保留最后一个(最深层)
    seen = {}
    for n in clickable:
        seen[n['name']] = n
    return list(seen.values())


def generate_html_report(timestamp, steps, output_path, calib):
    total = len(steps)
    passed = sum(1 for s in steps if s['result'] == '生效')
    partial = sum(1 for s in steps if s['result'] == '微变')
    blocked = sum(1 for s in steps if s['result'] == '弹窗未关闭')
    failed = sum(1 for s in steps if s['result'] in ('无反应', '点击失败'))

    parts = [f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>全UI扫描报告 - {timestamp}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,'Microsoft YaHei',sans-serif; background:#f0f2f5; color:#333; padding:20px; }}
.container {{ max-width:1400px; margin:auto; }}
.header {{ background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; padding:30px; border-radius:12px; margin-bottom:24px; }}
.header h1 {{ font-size:24px; margin-bottom:8px; }}
.header .meta {{ opacity:.9; font-size:14px; }}
.summary {{ display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap; }}
.summary-card {{ flex:1; min-width:120px; background:#fff; border-radius:10px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,.08); text-align:center; }}
.summary-card .num {{ font-size:36px; font-weight:bold; }}
.summary-card .label {{ font-size:13px; color:#666; margin-top:4px; }}
.pass {{ color:#52c41a; }} .partial {{ color:#faad14; }} .blocked {{ color:#722ed1; }} .fail {{ color:#ff4d4f; }}
.collapse-all {{ text-align:right; margin-bottom:12px; }}
.collapse-all button {{ background:#667eea; color:#fff; border:none; padding:6px 16px; border-radius:6px; cursor:pointer; font-size:13px; }}
.step-card {{ background:#fff; border-radius:10px; margin-bottom:12px; box-shadow:0 2px 6px rgba(0,0,0,.06); overflow:hidden; }}
.step-header {{ padding:12px 16px; display:flex; align-items:center; gap:12px; cursor:pointer; user-select:none; }}
.step-header:hover {{ background:#fafafa; }}
.step-index {{ background:#eee; color:#666; border-radius:50%; width:28px; height:28px; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:600; flex-shrink:0; }}
.step-name {{ font-size:14px; font-weight:500; flex:1; word-break:break-all; }}
.step-screen {{ font-size:12px; color:#722ed1; background:#f9f0ff; padding:2px 8px; border-radius:4px; flex-shrink:0; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.step-badge {{ padding:3px 10px; border-radius:20px; font-size:12px; font-weight:500; flex-shrink:0; }}
.badge-pass {{ background:#f6ffed; color:#52c41a; border:1px solid #b7eb8f; }}
.badge-partial {{ background:#fffbe6; color:#faad14; border:1px solid #ffe58f; }}
.badge-blocked {{ background:#f9f0ff; color:#722ed1; border:1px solid #d3adf7; }}
.badge-fail {{ background:#fff2f0; color:#ff4d4f; border:1px solid #ffccc7; }}
.step-body {{ padding:0 16px 16px; display:none; }}
.step-body.open {{ display:block; }}
.img-row {{ display:flex; gap:12px; flex-wrap:wrap; }}
.img-box {{ flex:1; min-width:160px; }}
.img-box h4 {{ font-size:12px; color:#666; margin-bottom:4px; }}
.img-box img {{ width:100%; border-radius:4px; border:1px solid #eee; cursor:pointer; }}
.dismiss-note {{ margin-top:6px; padding:6px 10px; background:#f9f0ff; border-radius:4px; font-size:12px; color:#722ed1; }}
.diff {{ margin-top:8px; font-size:12px; line-height:1.6; }}
.diff .tag {{ display:inline-block; padding:1px 6px; border-radius:3px; font-size:11px; margin-right:3px; margin-bottom:2px; }}
.tag-add {{ background:#f6ffed; color:#52c41a; border:1px solid #b7eb8f; }}
.tag-remove {{ background:#fff2f0; color:#ff4d4f; border:1px solid #ffccc7; }}
.coord {{ font-size:11px; color:#999; margin-top:4px; }}
.toggle-icon {{ font-size:10px; color:#999; transition:transform .2s; }}
.toggle-icon.open {{ transform:rotate(90deg); }}
.api-badge {{ font-size:11px; padding:2px 8px; border-radius:4px; flex-shrink:0; }}
.api-triggered {{ background:#f6ffed; color:#52c41a; border:1px solid #b7eb8f; }}
.api-silent {{ background:#fafafa; color:#999; border:1px solid #e8e8e8; }}
.reset-badge {{ background:#e6f7ff; color:#1890ff; font-size:11px; border:1px solid #91d5ff; padding:1px 6px; border-radius:3px; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📋 全UI自动扫描报告</h1>
<div class="meta">时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 总计: {total}个节点</div>
</div>
<div class="summary">
<div class="summary-card"><div class="num pass">{passed}</div><div class="label">✅ 生效</div></div>
<div class="summary-card"><div class="num partial">{partial}</div><div class="label">🔶 微变</div></div>
<div class="summary-card"><div class="num blocked">{blocked}</div><div class="label">🛑 弹窗未关闭</div></div>
<div class="summary-card"><div class="num fail">{failed}</div><div class="label">❌ 无反应</div></div>
<div class="summary-card"><div class="num">{total}</div><div class="label">📊 总计</div></div>
<div class="summary-card"><div class="num">{passed/total*100:.0f}%</div><div class="label">🎯 生效率</div></div>
</div>
<div class="collapse-all"><button onclick="toggleAll()">折叠/展开全部</button></div>
''']

    for i, s in enumerate(steps):
        result = s['result']
        if result == '生效':
            badge_cls, badge_txt = 'badge-pass', '✅ 生效'
        elif result == '微变':
            badge_cls, badge_txt = 'badge-partial', '🔶 微变'
        elif result == '弹窗未关闭':
            badge_cls, badge_txt = 'badge-blocked', '🛑 待处理'
        else:
            badge_cls, badge_txt = 'badge-fail', f'❌ {result}'

        before_src = f'data:image/png;base64,{s.get("before","")}' if s.get('before') else ''
        after_src = f'data:image/png;base64,{s.get("after","")}' if s.get('after') else ''

        diff_html = ''
        if s.get('added'):
            diff_html += '<div>' + ''.join(f'<span class="tag tag-add">+ {t}</span>' for t in s['added']) + '</div>'
        if s.get('removed'):
            diff_html += '<div>' + ''.join(f'<span class="tag tag-remove">- {t}</span>' for t in s['removed']) + '</div>'
        diff_html += f'<div>结构变化: {s.get("node_delta",0)}b</div>'

        dismiss_note = ''
        if s.get('dismiss'):
            dismiss_note = f'<div class="dismiss-note">弹窗关闭方式: {s["dismiss"]}</div>'

        # 界面信息
        screen_info = s.get('screen_before', '')
        screen_tag = f'<span class="step-screen">{screen_info}</span>' if screen_info else ''
        reset_tag = f'<span class="reset-badge">🔁 {s.get("reset_before",0)}次复位</span>' if s.get('reset_before', 0) > 0 else ''
        # 网络消息标记（替代旧API协议标记）
        api_tag = ''
        net_msgs = s.get('net_messages', [])
        net_protocols = s.get('net_protocols', [])
        if net_msgs:
            sends = sum(1 for m in net_msgs if m.get('dir') == 'SEND')
            recvs = sum(1 for m in net_msgs if m.get('dir') == 'RECV')
            proto_str = ','.join([p.split('.')[-1] for p in net_protocols[:3]])
            api_tag = f'<span class="api-badge api-triggered">📡 {sends}↑{recvs}↓ {proto_str}</span>'
        else:
            api_tag = f'<span class="api-badge api-silent">⏺️ 本地</span>'

        # 网络消息详情（折叠在body里）
        net_detail = ''
        if net_msgs:
            net_lines = ''.join(
                f'<div style="font-size:11px;color:{"#1890ff" if m.get("dir")=="SEND" else "#52c41a"};padding:0 0 2px 0;">'
                f'{"↑" if m.get("dir")=="SEND" else "↓"} {m.get("time","")} | {m.get("type","")}</div>'
                for m in net_msgs[:8]
            )
            net_detail = f'<div class="dismiss-note"><b>📡 网络消息 ({len(net_msgs)}条):</b><br>{net_lines}</div>'

        parts.append(f'''
<div class="step-card">
<div class="step-header" onclick="toggle(this.nextElementSibling,this.querySelector('.toggle-icon'))">
<span class="step-index">{i+1}</span>
<span class="step-name">{s["name"]}</span>
{screen_tag}
{api_tag}
{reset_tag}
<span class="step-badge {badge_cls}">{badge_txt}</span>
<span class="toggle-icon">▶</span>
</div>
<div class="step-body">
<div class="img-row">
<div class="img-box"><h4>点击前</h4><img src="{before_src}" onclick="window.open(this.src)" alt="b"></div>
<div class="img-box"><h4>点击后</h4><img src="{after_src}" onclick="window.open(this.src)" alt="a"></div>
</div>
<div class="diff">{diff_html}</div>
{net_detail}
{dismiss_note}
<div class="coord">坐标: {s.get("coord","?")} | 界面: {screen_info}</div>
</div>
</div>
''')

    parts.append('''</div>
<script>
function toggle(el, icon) {
  el.classList.toggle('open');
  if(icon) icon.classList.toggle('open');
}
function toggleAll() {
  const bodies = document.querySelectorAll('.step-body');
  const icons = document.querySelectorAll('.toggle-icon');
  const allOpen = Array.from(bodies).every(b => b.classList.contains('open'));
  bodies.forEach(b => b.classList.toggle('open', !allOpen));
  icons.forEach(i => i.classList.toggle('open', !allOpen));
}
</script>
</body></html>''')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))
    return output_path


def main():
    ensure_dir(REPORT_DIR)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print("=" * 60)
    print("🍊 全UI自动扫描 (灰盒模式: 界面识别 + API协议监测)")
    print("=" * 60)

    dev, poco, calib = connect_and_calibrate()
    time.sleep(1)

    # === 初始化网络消息监控（替代 API Test 面板） ===
    print("\n🔌 检测灰盒接口(NetMessageMonitor)...")
    has_net_monitor = HAS_NET_MONITOR and os.path.exists(net_monitor.log_path if net_monitor else '')
    if has_net_monitor:
        net_monitor.clear()
        # 先等一会儿收集一些心跳消息，建立去重基线
        time.sleep(1)
        net_monitor.clear()
        net_msg_sends, net_msg_recvs = set(), set()
        print(f"   📡 网络消息监控就绪: {net_monitor.log_path}")
    else:
        net_msg_sends, net_msg_recvs = None, None
        if not HAS_NET_MONITOR:
            print("   ⚠️ NetMonitorWatcher 模块未加载")
        else:
            print(f"   ⚠️ 日志文件未找到: {net_monitor.log_path}")
        print("   ℹ️  使用UI变化作为点击判定依据")

    # === 记录主画面的基线 ===
    print("\n📸 记录主画面基线...")
    _, _, _, base_texts = get_ui_fingerprint(poco)
    base_raw = poco.agent.hierarchy.dump()
    base_windows = get_active_windows(base_raw)
    base_screen, base_desc, _ = identify_current_screen(poco)
    print(f"   界面: {base_desc}")
    print(f"   活跃窗口: {base_windows}")

    # === 获取可点击节点 ===
    print("\n🔍 扫描可点击节点...")
    nodes = find_clickable_nodes(poco)
    print(f"   共找到 {len(nodes)} 个可点击节点")

    if not nodes:
        print("   ❌ 未找到任何可点击节点")
        return

    # 排个序
    dismiss_keywords = ['Close', 'close', '关闭', '返回', '好的', 'OK', 'Bg', 'buttn_close', 'CloseBtn']
    normal_nodes = []
    dismiss_nodes = []
    for n in nodes:
        is_dismiss = any(k in n['name'] for k in dismiss_keywords)
        if is_dismiss:
            dismiss_nodes.append(n)
        else:
            normal_nodes.append(n)

    ordered_nodes = normal_nodes + dismiss_nodes
    print(f"   正常节点: {len(normal_nodes)}  关闭类节点: {len(dismiss_nodes)} (放最后)")

    # === 逐个点击测试 ===
    print(f"\n{'='*60}")
    print(f"开始测试 {len(ordered_nodes)} 个节点...")
    print(f"{'='*60}")

    steps = []
    start_time = time.time()
    reset_count = 0
    api_trigger_count = 0

    for idx, node in enumerate(ordered_nodes):
        name = node['name']
        px, py = node['pos']
        gv_x = px * calib['render_w'] + calib['bar_l']
        gv_y = py * calib['work_h']

        # ETA
        elapsed = time.time() - start_time
        eta = elapsed / (idx + 1) * (len(ordered_nodes) - idx - 1) if idx > 0 else 0
        print(f"\n{'─'*60}")
        print(f"[{idx+1}/{len(ordered_nodes)}] {name}  ({px:.3f}, {py:.3f})  ETA: {eta:.0f}s")
        print(f"{'─'*60}")

        # === 第一步：识别当前界面 ===
        current_screen, current_desc, current_windows = identify_current_screen(poco)
        print(f"   📍 当前界面: {current_desc}")

        if current_windows:
            print(f"   🪟 活跃窗口: {current_windows}")

        # === 第二步：如果不在主画面，尝试关闭弹窗回到主画面 ===
        if current_screen != '主城主界面' and current_screen not in ('未知界面(弹窗覆盖)',):
            print(f"   ⚠️ 当前不在主画面，尝试回到主画面...")
            restored = try_dismiss_popups(poco, calib)
            if restored:
                reset_count += 1
                # 重新识别
                current_screen, current_desc, current_windows = identify_current_screen(poco)
                print(f"   ✅ 已回到主画面 (第{reset_count}次复位)")
                print(f"   📍 当前界面: {current_desc}")
            else:
                # 硬复位：狂点主城按钮
                print(f"   ❌ 弹窗关闭失败，强制复位...")
                for _ in range(3):
                    calibrated_click(poco, calib, query='Train')
                    time.sleep(1)
                current_screen, current_desc, current_windows = identify_current_screen(poco)
                if current_screen == '主城主界面':
                    reset_count += 1
                    print(f"   ✅ 强制复位成功 (第{reset_count}次)")
                else:
                    print(f"   ⚠️ 强制复位后仍在: {current_desc}，继续尝试")

        # === 第三步：点前记录（截图 + 清理网络消息日志） ===
        b64_before = snapshot_now()
        raw_before = poco.agent.hierarchy.dump()
        texts_before = get_ui_texts(raw_before)
        # 清空网络消息日志，准备记录本次点击的消息
        if has_net_monitor:
            net_monitor.clear()

        # === 第四步：点击 ===
        try:
            print(f"   🖱️ 点击坐标: ({gv_x:.0f}, {gv_y:.0f})")
            airtest_touch([int(gv_x), int(gv_y)])
        except:
            steps.append({
                'name': name, 'result': '点击失败',
                'before': b64_before, 'after': None,
                'added': [], 'removed': [], 'node_delta': 0,
                'coord': f'({gv_x:.0f}, {gv_y:.0f})', 'dismiss': '',
                'screen_before': current_desc,
                'net_messages': [],
                'net_protocols': [],
            })
            print(f"   ❌ 点击失败")
            continue

        time.sleep(1.5)

        # === 第五步：点后分析（界面 + 网络消息） ===
        raw_after = poco.agent.hierarchy.dump()
        texts_after = get_ui_texts(raw_after)
        b64_after = snapshot_now()

        # 读取网络消息（代替 API 面板指纹）
        click_net_msgs = []
        click_protocols = []
        if has_net_monitor:
            click_net_msgs = net_monitor.poll()
            click_protocols = net_monitor.get_message_types(click_net_msgs)
            net_send_types = [m.type for m in click_net_msgs if m.is_send()]
            net_recv_types = [m.type for m in click_net_msgs if m.is_recv()]
            net_msg_sends.update(net_send_types)
            net_msg_recvs.update(net_recv_types)

        has_net_activity = len(click_net_msgs) > 0

        # 识别点击后的界面
        after_screen, after_desc, after_windows = identify_current_screen(poco)

        added = list(texts_after - texts_before)[:6]
        removed = list(texts_before - texts_after)[:6]
        before_count = len(str(raw_before))
        after_count = len(str(raw_after))
        delta = abs(after_count - before_count)

        # 综合判断点击结果
        result = '无反应'
        reasons = []
        if after_screen != current_screen:
            result = '生效'
            reasons.append(f'界面切换: {current_screen}→{after_screen}')
        elif has_net_activity:
            result = '生效'
            type_str = ','.join(net_monitor.get_message_types(click_net_msgs)[:3])
            reasons.append(f'网络消息: {type_str}')
            if has_net_monitor:
                api_trigger_count += 1
        elif added or removed or delta > 500:
            result = '生效'
            reasons.append(f'UI文字变化(+{len(added)}/-{len(removed)})')
        elif delta > 100:
            result = '微变'
            reasons.append(f'UI结构微变({delta}b)')

        print(f"   📍 点击后界面: {after_desc}")
        if after_windows != current_windows:
            print(f"   🪟 窗口变化: {current_windows} → {after_windows}")

        # 网络消息状态
        if has_net_monitor:
            if click_net_msgs:
                print(f"   📡 触发 {len(click_net_msgs)} 条网络消息:")
                for m in click_net_msgs[:5]:
                    print(f"      {'↑' if m.is_send() else '↓'} {m.short_type()}")
                if len(click_net_msgs) > 5:
                    print(f"      ... 还有 {len(click_net_msgs)-5} 条")
            else:
                print(f"   ⏺️ 无网络消息（本地操作）")
        if reasons:
            print(f"   📝 {', '.join(reasons)}")

        step = {
            'name': name, 'result': result,
            'before': b64_before, 'after': b64_after,
            'added': added, 'removed': removed, 'node_delta': delta,
            'coord': f'({gv_x:.0f}, {gv_y:.0f})', 'dismiss': '',
            'screen_before': current_desc,
            'screen_after': after_desc,
            'reset_before': reset_count,
            'net_messages': [
                {'dir': m.dir, 'type': m.type, 'short': m.short_type(), 'time': m.time}
                for m in click_net_msgs[:10]  # 只存前10条，太多了占内存
            ],
            'net_protocols': click_protocols[:5],
            'api_triggered': has_net_activity,
        }

        # === 第六步：如果出现弹窗，尝试关闭 ===
        if after_screen not in ('主城主界面',) and after_screen != current_screen:
            print(f"   🔔 切换到了 {after_screen}，尝试关闭回到主画面...")
            restored = try_dismiss_popups(poco, calib)
            if restored:
                step['dismiss'] = '自动关闭'
                reset_count += 1
                print(f"   ✅ 已关闭，回到主画面")
            else:
                step['dismiss'] = '关闭失败'
                print(f"   ⚠️ 未能关闭")

        steps.append(step)

        # 打印摘要
        icon = '✅' if result == '生效' else ('🔶' if result == '微变' else '⏺️')
        print(f"   {icon} {result}", end='')
        if after_screen != current_screen:
            print(f"  [{current_screen} → {after_screen}]", end='')
        elif has_net_activity and has_net_monitor:
            types_str = ','.join(net_monitor.get_message_types(click_net_msgs)[:2])
            print(f"  [📡{types_str}]", end='')
        elif added:
            print(f"  +文字:{','.join(added[:3])}", end='')
        if step['dismiss']:
            print(f"  [弹窗:{step['dismiss']}]", end='')
        print()

    # === 统计 ===
    elapsed_total = time.time() - start_time
    passed = sum(1 for s in steps if s['result'] == '生效')
    partial = sum(1 for s in steps if s['result'] == '微变')
    blocked = sum(1 for s in steps if s['dismiss'] == '关闭失败')
    failed = sum(1 for s in steps if s['result'] in ('无反应', '点击失败'))
    api_triggers = sum(1 for s in steps if s.get('api_triggered'))
    local_ops = passed - api_triggers

    # 生成报告
    print(f"\n📝 生成HTML报告...")
    report_path = os.path.join(REPORT_DIR, f'full_scan_report_{timestamp}.html')
    generate_html_report(timestamp, steps, report_path, calib)

    total_img_size = 0
    for s in steps:
        if s.get('before'):
            total_img_size += len(s['before']) * 0.75
        if s.get('after'):
            total_img_size += len(s['after']) * 0.75

    print(f"\n{'='*60}")
    print(f"📊 扫描完成!")
    print(f"   耗时: {elapsed_total:.0f}s ({elapsed_total/60:.1f}min)")
    print(f"   图片: ~{total_img_size/1024/1024:.1f}MB")
    print(f"   主画面复位: {reset_count} 次")
    print(f"   灰盒监测: 📡 {api_triggers}次网络消息触发  |  📍 {local_ops}次本地UI变化")
    if has_net_monitor and (net_msg_sends or net_msg_recvs):
        print(f"   协议概览:")
        if net_msg_sends:
            print(f"     ↑ 发送: {', '.join(sorted(net_msg_sends)[:10])}")
        if net_msg_recvs:
            print(f"     ↓ 接收: {', '.join(sorted(net_msg_recvs)[:10])}")
        if len(net_msg_sends) > 10 or len(net_msg_recvs) > 10:
            print(f"       ... 共 {len(net_msg_sends)} 种发送, {len(net_msg_recvs)} 种接收")
    print(f"   结果: ✅ {passed}  |  🔶 {partial}  |  🛑 {blocked}  |  ⏺️ {failed}")
    print(f"   报告: {report_path}")
    print(f"{'='*60}")


# 需要保留这个函数给 is_main_screen 用
def get_ui_fingerprint(poco):
    raw = poco.agent.hierarchy.dump()
    texts = set()
    names = set()
    def walk(n):
        name = n.get('name', '')
        pld = n.get('payload', {})
        if name:
            names.add(name)
        for k in ['text', 'Text', 'content', '_text']:
            v = str(pld.get(k, '')).strip()
            if v and len(v) < 40:
                texts.add(v)
        for c in n.get('children', []):
            walk(c)
    walk(raw)
    hash_str = str(sorted(names)) + str(sorted(texts))
    fp = hashlib.md5(hash_str.encode()).hexdigest()[:12]
    return fp, len(names), texts, names


if __name__ == '__main__':
    main()
