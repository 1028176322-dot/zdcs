"""
交互式协议验证工具
你点一下 → 我抓 → 你亲眼看到协议名 → 判断对不对

用法：
    1. 启动 Unity 运行游戏
    2. 运行本脚本: python verify_protocol.py
    3. 按提示操作
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.net_monitor_watcher import NetMonitorWatcher


def print_header(text):
    """打印带框标题"""
    width = 60
    print()
    print('=' * width)
    print(f'  {text}')
    print('=' * width)


def print_msg(m, index):
    """格式化输出一条消息"""
    icon = '↑' if m.is_send() else '↓'
    color = '\033[94m' if m.is_send() else '\033[92m'  # 蓝=发送, 绿=接收
    reset = '\033[0m'
    short = m.short_type()
    print(f'  {color}{icon} #{index:2d}  {m.time}  {short}{reset}')

    # 如果内容短，显示关键字段
    content = m.content.strip()
    if content and len(content) < 200:
        # 提取前2-3个字段名
        fields = content.split('\n')[:2]
        for f in fields:
            f = f.strip()
            if f and '{' not in f and '}' not in f:
                f_short = f[:80]
                print(f'       └ {f_short}')


def print_summary(messages):
    """打印汇总"""
    sends = [m for m in messages if m.is_send()]
    recvs = [m for m in messages if m.is_recv()]
    types = []
    seen = set()
    for m in messages:
        s = m.short_type()
        if s not in seen:
            seen.add(s)
            types.append(s)

    print()
    print(f'  📊 汇总: {len(sends)} 条发送 ↑ + {len(recvs)} 条接收 ↓ = {len(messages)} 条')
    if types:
        type_str = '  →  '.join(types[:6])
        print(f'  🏷️  协议: {type_str}')
    print()


def main():
    monitor = NetMonitorWatcher()

    # 检查文件是否被写入（Unity 是否在运行）
    if not os.path.exists(monitor.log_path) or os.path.getsize(monitor.log_path) == 0:
        print_header('⚠️  等待 Unity 启动...')
        print()
        print('  日志文件为空或不存在。请：')
        print('    1️⃣  启动 Unity 编辑并运行游戏')
        print('    2️⃣  等游戏加载完成')
        print('    3️⃣  确认 Console 有 [NetMonitor] Initialized 日志')
        print('    4️⃣  重新运行本脚本')
        print()
        raw_input('  按 Enter 再试一次...')
        main()
        return

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header('🔍 协议验证器 — 直观判断消息对不对')
        print()
        print(f'  📁 日志: {monitor.log_path}')
        print(f'  📈 总消息数: {monitor.summary()}')

        # 第一步：清空日志
        print()
        print('  ⏳ 清空旧消息...')
        monitor.clear()
        time.sleep(0.3)

        # 第二步：让用户操作
        print()
        print('  🎯 现在去游戏里点一个按钮')
        print('     比如: 主城 / 活动 / 邮件 / 武将 / 背包')
        print()
        try:
            raw_input('  👉 点完之后按 Enter 键...')
        except:
            input('  👉 点完之后按 Enter 键...')

        # 第三步：读取消息
        print()
        print('  ⏳ 读取网络消息...')
        time.sleep(0.5)  # 等服务器回包
        messages = monitor.poll(filter_noise=True)
        all_messages = list(messages)

        # 等一会看还有没有后续消息
        time.sleep(0.5)
        more = monitor.poll(filter_noise=True)
        all_messages.extend(more)

        # 第四步：显示结果
        print()
        if not all_messages:
            print('  ⏺️  没有抓取到与点击相关的网络消息')
            print('     (可能这个操作是纯本地界面切换，不需要请求服务器)')
        else:
            print(f'  ✅ 抓到 {len(all_messages)} 条有效消息（已过滤心跳/BI上报等噪音）')
            print()
            print('  ┌──────────────────────────────────────────────')
            print('  │  ↑ 蓝色 = 客户端发送的请求')
            print('  │  ↓ 绿色 = 服务器返回的应答')
            print('  └──────────────────────────────────────────────')
            print()

            for i, m in enumerate(all_messages, 1):
                print_msg(m, i)

            print_summary(all_messages)

        # 第五步：让用户判断
        print()
        print('  💬 协议名你认识吗？')
        if all_messages:
            short_names = [m.short_type() for m in all_messages]
            print(f'     看到 {short_names[0]} 这种名字')
            print(f'     是不是感觉跟刚才点的功能对得上？')
        print()

        # 继续或退出
        print('  ────────────────────────────────────────────')
        try:
            choice = raw_input('  按 Enter 继续验证 / 输入 q 退出: ')
        except:
            choice = input('  按 Enter 继续验证 / 输入 q 退出: ')
        if choice.lower() in ('q', 'quit', 'exit'):
            break

    print()
    print_header('✅ 验证结束')
    print()


if __name__ == '__main__':
    main()
