"""
Poco点击测试 - 截图+HTML报告版
每次点击前后截图，生成可直观判断的HTML报告
"""
import sys
import time
import os
import base64
from io import BytesIO
from datetime import datetime
from airtest.core.win.win import Windows
from airtest.core.api import touch as airtest_touch
from airtest.core.helper import G
from poco.drivers.unity3d import UnityPoco
import pywinauto


# 报告目录
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')


def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)


def snapshot_vbox(label=''):
    """截图GameView并返回base64"""
    try:
        # G.DEVICE.snapshot() 返回numpy.ndarray (H,W,3)
        arr = G.DEVICE.snapshot()
        if arr is None:
            print(f"   ⚠️ 截图({label})返回空")
            return None
        from PIL import Image
        img = Image.fromarray(arr)
        buf = BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        print(f"   📸 截图({label}): {img.size}")
        return b64
    except Exception as e:
        print(f"   ⚠️ 截图({label})失败: {e}")
        return None


def connect_and_calibrate():
    """连接并计算黑边偏移参数"""
    print("🔍 查找Unity窗口...")
    windows = pywinauto.findwindows.find_elements(class_name='UnityContainerWndClass')
    
    # 调试：列出所有Unity窗口
    print(f"   找到 {len(windows)} 个Unity窗口:")
    for i, w in enumerate(windows):
        rect = w.rectangle
        title = w.name
        print(f"   [{i}] handle=0x{w.handle:08x} left={rect.left} title={title[:30]}")
    
    # 找非最小化的窗口
    visible_windows = [w for w in windows if w.rectangle.left > -1000]
    if not visible_windows:
        print("   ⚠️ 没有找到可见的Unity窗口，尝试使用第一个窗口")
        target = windows[0] if windows else None
    else:
        target = visible_windows[0]
    
    if target is None:
        raise Exception("未找到Unity窗口！请确保Unity编辑器正在运行")
    
    handle = target.handle
    print(f"🎯 Unity窗口: 0x{handle:08x} \"{target.name}\"")
    
    dev = Windows(handle=handle)
    app = dev._app
    
    # 等待窗口就绪
    time.sleep(1)
    
    # 查找GameView窗口
    print("🔍 查找GameView窗口...")
    try:
        # 方法1：直接查找UnityEditor.GameView
        game_view = app.top_window().child_window(title="UnityEditor.GameView")
        gv = game_view.wrapper_object()
        gv_rect = game_view.rectangle()
        print(f"   ✅ 找到GameView: {gv_rect}")
    except Exception as e1:
        print(f"   ⚠️ 方法1失败: {e1}")
        try:
            # 方法2：遍历所有子窗口
            top = app.top_window()
            children = top.children()
            print(f"   顶级窗口有 {len(children)} 个子窗口")
            game_view = None
            for c in children:
                if 'GameView' in str(c):
                    game_view = c
                    break
            if game_view:
                gv = game_view.wrapper_object()
                gv_rect = game_view.rectangle()
                print(f"   ✅ 找到GameView: {gv_rect}")
            else:
                raise Exception("未找到GameView窗口！请确保Game窗口已打开")
        except Exception as e2:
            print(f"   ❌ 方法2也失败: {e2}")
            raise Exception("无法找到GameView窗口，请确保Unity编辑器中打开了Game窗口")
    
    dev._top_window = gv
    dev.focus_rect = (0, 40, 0, 0)
    G.DEVICE = dev
    
    poco = UnityPoco(('localhost', 5001), connect_default_device=False)
    sw, sh = poco.get_screen_size()
    print(f"📱 游戏: {sw:.0f}x{sh:.0f}")
    
    gv_w = gv_rect.right - gv_rect.left
    gv_h = gv_rect.bottom - gv_rect.top
    toolbar = 40
    work_w = gv_w
    work_h = gv_h - toolbar
    render_w = int(work_h * sw / sh)
    bar_l = (work_w - render_w) // 2
    
    print(f"📐 GameView: {gv_w}x{gv_h} → 可用: {work_w}x{work_h}")
    print(f"   游戏渲染: {render_w}x{work_h}  左侧黑边: {bar_l}px")
    
    calib = {
        'gv_left': gv_rect.left,
        'gv_top': gv_rect.top,
        'work_w': work_w,
        'work_h': work_h,
        'render_w': render_w,
        'bar_l': bar_l,
    }
    return dev, poco, calib


def get_ui_sig(raw):
    """提取UI特征：文字+节点名"""
    texts = set()
    names = set()
    def extract(node):
        n = node.get('name', '')
        pld = node.get('payload', {})
        t = ''
        for k in ['text', 'Text', 'content', '_text']:
            v = str(pld.get(k, '')).strip()
            if v and len(v) < 30:
                t = v
                break
        if t:
            texts.add(t)
        if n:
            names.add(n)
        for c in node.get('children', []):
            extract(c)
    extract(raw)
    return texts, names


def main():
    ensure_dir(REPORT_DIR)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 为本次测试创建独立文件夹
    run_dir = os.path.join(REPORT_DIR, timestamp)
    ensure_dir(run_dir)
    print(f"📁 测试报告目录: {run_dir}")
    
    print("=" * 50)
    print("🖱️ 截图+报告版 点击测试")
    print("=" * 50)

    dev, poco, calib = connect_and_calibrate()
    time.sleep(1)

    # 记录所有步骤
    steps = []

    # 底部导航栏按钮
    tests = [
        ('Train', '主城', 0.03),
        ('Skill', '小游戏', 0.03),
        ('Hero', '英雄', 0.03),
        ('Alliance', '联盟', 0.03),
        ('World', '世界地图', 0.03),
    ]

    # === 第一步：截一张初始画面 ===
    print("\n📸 截取初始画面...")
    b64_init = snapshot_vbox('初始画面')
    init_img_path = ''
    if b64_init:
        init_img_path = os.path.join(run_dir, f'00_初始画面.png')
        with open(init_img_path, 'wb') as f:
            f.write(base64.b64decode(b64_init))

    ok = 0
    for idx, (query, desc, y_off) in enumerate(tests):
        step_num = idx + 1
        print(f"\n{'=' * 50}")
        print(f"🖱️ 第{step_num}步: {desc} ({query})")

        step = {'desc': desc, 'query': query, 'result': '未执行'}

        try:
            elem = poco(query)
            px, py = elem.get_position()
            py = max(0, py - y_off)
            full_text = elem.get_text()
            print(f"   Poco: ({px:.3f}, {py:.3f}) 文字: \"{full_text}\"")
        except Exception as e:
            print(f"   ❌ 找不到元素: {e}")
            step['result'] = '找不到元素'
            steps.append(step)
            continue

        gv_x = px * calib['render_w'] + calib['bar_l']
        gv_y = py * calib['work_h']

        raw_before = poco.agent.hierarchy.dump()
        b64_before = snapshot_vbox(f'{desc}_前')

        airtest_touch([int(gv_x), int(gv_y)])
        print(f"   ✅ 点击执行")
        time.sleep(1.5)

        raw_after = poco.agent.hierarchy.dump()
        b64_after = snapshot_vbox(f'{desc}_后')

        b_texts, b_names = get_ui_sig(raw_before)
        a_texts, a_names = get_ui_sig(raw_after)
        added_t = a_texts - b_texts
        removed_t = b_texts - a_texts
        added_n = a_names - b_names
        removed_n = b_names - a_names

        changed = bool(added_t or removed_t or len(added_n) > 3 or len(removed_n) > 3)
        if changed:
            print(f"   ✅ 点击生效!")
            step['result'] = '生效'
            ok += 1
        else:
            print(f"   ⚠️ 无变化")
            step['result'] = '无变化'

        before_path = ''
        after_path = ''
        if b64_before:
            before_path = os.path.join(run_dir, f'{step_num:02d}_{desc}_前.png')
            with open(before_path, 'wb') as f:
                f.write(base64.b64decode(b64_before))
        if b64_after:
            after_path = os.path.join(run_dir, f'{step_num:02d}_{desc}_后.png')
            with open(after_path, 'wb') as f:
                f.write(base64.b64decode(b64_after))

        step.update({
            'before_img': before_path,
            'after_img': after_path,
            'coord': (gv_x, gv_y),
            'added_text': list(added_t)[:8],
            'removed_text': list(removed_t)[:8],
            'node_change': (len(added_n), len(removed_n)),
        })
        steps.append(step)

    # === 生成HTML报告 ===
    print(f"\n📝 生成HTML报告...")
    report_path = os.path.join(run_dir, f'report_{timestamp}.html')

    html_parts = [f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>冒烟测试报告 - {timestamp}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #f0f2f5; color: #333; padding: 20px; }}
.container {{ max-width: 1200px; margin: auto; }}
.header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
.header h1 {{ font-size: 24px; margin-bottom: 8px; }}
.header .meta {{ opacity: 0.9; font-size: 14px; }}
.summary {{ display: flex; gap: 20px; margin-bottom: 24px; }}
.summary-card {{ flex: 1; background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }}
.summary-card .num {{ font-size: 36px; font-weight: bold; }}
.summary-card .label {{ font-size: 13px; color: #666; margin-top: 4px; }}
.pass {{ color: #52c41a; }}
.fail {{ color: #ff4d4f; }}
.warn {{ color: #faad14; }}
.step-card {{ background: #fff; border-radius: 10px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }}
.step-header {{ padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #eee; }}
.step-title {{ font-size: 16px; font-weight: 600; }}
.step-badge {{ padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 500; }}
.badge-pass {{ background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }}
.badge-fail {{ background: #fff2f0; color: #ff4d4f; border: 1px solid #ffccc7; }}
.step-body {{ padding: 20px; }}
.img-row {{ display: flex; gap: 16px; flex-wrap: wrap; }}
.img-box {{ flex: 1; min-width: 200px; }}
.img-box h4 {{ font-size: 13px; color: #666; margin-bottom: 6px; }}
.img-box img {{ width: 100%; border-radius: 6px; border: 1px solid #eee; cursor: pointer; transition: transform .2s; }}
.img-box img:hover {{ transform: scale(1.02); box-shadow: 0 4px 16px rgba(0,0,0,0.12); }}
.diff-info {{ margin-top: 12px; font-size: 13px; line-height: 1.8; }}
.diff-info .tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 4px; margin-bottom: 2px; }}
.tag-added {{ background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }}
.tag-removed {{ background: #fff2f0; color: #ff4d4f; border: 1px solid #ffccc7; }}
.coord {{ font-size: 12px; color: #999; margin-top: 4px; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📋 SLG 冒烟测试报告</h1>
<div class="meta">运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 窗口: {calib['work_w']}x{calib['work_h']} | 游戏: 1170x2532</div>
</div>
''']

    total = len(steps)
    passed = sum(1 for s in steps if s['result'] == '生效')
    failed = sum(1 for s in steps if s['result'] not in ('生效',))
    ratio = passed / total * 100 if total > 0 else 0

    html_parts.append(f'''
<div class="summary">
<div class="summary-card"><div class="num pass">{passed}</div><div class="label">✅ 成功</div></div>
<div class="summary-card"><div class="num fail">{failed}</div><div class="label">❌ 失败</div></div>
<div class="summary-card"><div class="num">{total}</div><div class="label">📊 总计</div></div>
<div class="summary-card"><div class="num">{ratio:.0f}%</div><div class="label">🎯 通过率</div></div>
</div>
''')

    for s in steps:
        is_pass = s['result'] == '生效'
        badge_cls = 'badge-pass' if is_pass else 'badge-fail'
        badge_txt = '✅ 生效' if is_pass else f'❌ {s["result"]}'

        before_img = s.get('before_img', '')
        after_img = s.get('after_img', '')
        # 使用相对路径（图片和HTML在同一文件夹）
        before_src = os.path.basename(before_img) if before_img else ''
        after_src = os.path.basename(after_img) if after_img else ''

        diff_html = ''
        if s.get('added_text'):
            diff_html += '<div>' + ''.join(f'<span class="tag tag-added">+ {t}</span>' for t in s['added_text']) + '</div>'
        if s.get('removed_text'):
            diff_html += '<div>' + ''.join(f'<span class="tag tag-removed">- {t}</span>' for t in s['removed_text']) + '</div>'
        if s.get('node_change'):
            diff_html += f'<div style="margin-top:4px;">节点变化: +{s["node_change"][0]} / -{s["node_change"][1]} 个</div>'

        html_parts.append(f'''
<div class="step-card">
<div class="step-header">
<span class="step-title">🖱️ {s["desc"]}</span>
<span class="step-badge {badge_cls}">{badge_txt}</span>
</div>
<div class="step-body">
<div class="img-row">
<div class="img-box"><h4>点击前</h4><img src="{before_src}" onclick="window.open(this.src)" alt="before"></div>
<div class="img-box"><h4>点击后</h4><img src="{after_src}" onclick="window.open(this.src)" alt="after"></div>
</div>
<div class="diff-info">{diff_html}</div>
<div class="coord">坐标: ({s["coord"][0]:.0f}, {s["coord"][1]:.0f}) 点击位</div>
</div>
</div>
''')

    if init_img_path and os.path.exists(init_img_path):
        init_src = os.path.basename(init_img_path)
        html_parts.append(f'''
<div class="step-card">
<div class="step-header"><span class="step-title">📸 初始画面（测试前）</span></div>
<div class="step-body">
<div class="img-row"><div class="img-box"><img src="{init_src}" onclick="window.open(this.src)" alt="initial"></div></div>
</div>
</div>
''')

    html_parts.append('</div></body></html>')

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))

    print(f"\n{'=' * 50}")
    print(f"📊 结果: {ok}/{len(tests)} 个生效")
    print(f"📄 报告: {report_path}")
    print(f"{'=' * 50}")


if __name__ == '__main__':
    main()
