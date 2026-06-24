"""
网络消息监控测试脚本
验证 C# NetMessageMonitor + Python NetMonitorWatcher 的端到端工作流

用法:
    python test_net_monitor.py                    # 读取当前日志
    python test_net_monitor.py --wait              # 等待 Unity 写入新消息
    python test_net_monitor.py --poll 5            # 轮询 5 秒看有没新消息
"""
import sys
import os
import time

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.net_monitor_watcher import NetMonitorWatcher, NetMessage


def test_parse():
    """测试日志行解析"""
    print("=" * 50)
    print("🧪 测试: 日志行解析")
    print("=" * 50)

    test_lines = [
        "20:30:15.123|SEND|cspb.HeartBeatReq|{}",
        "20:30:15.456|RECV|cspb.HeartBeatAck|{}",
        "20:30:16.000|SEND|cspb.GetPlayerInfoReq|{PlayerId = 10001,}",
    ]

    for line in test_lines:
        msg = NetMessage(line)
        print(f"  ✓ {msg}")
        assert msg.dir in ('SEND', 'RECV'), f"方向解析失败: {msg.dir}"
        assert msg.type.startswith('cspb.'), f"类型解析失败: {msg.type}"
        assert msg.time, f"时间解析失败: {msg.time}"

    print("\n  ✅ 解析测试通过!\n")


def test_file_ops():
    """测试文件读写"""
    print("=" * 50)
    print("🧪 测试: 文件读写操作")
    print("=" * 50)

    test_path = os.path.join(os.path.dirname(__file__), '_test_monitor.log')

    # 模拟写入测试数据
    with open(test_path, 'w', encoding='utf-8') as f:
        f.write("20:30:15.123|SEND|cspb.HeartBeatReq|{}\n")
        f.write("20:30:15.456|RECV|cspb.HeartBeatAck|{}\n")
        f.write("20:30:16.000|SEND|cspb.GetPlayerInfoReq|{PlayerId = 10001,}\n")

    monitor = NetMonitorWatcher(log_path=test_path)
    msgs = monitor.read_all()
    assert len(msgs) == 3, f"应读到3条消息，实际{len(msgs)}"
    print(f"  ✓ 初始读取: {len(msgs)} 条消息")

    # 测试 clear
    monitor.clear()
    msgs = monitor.poll()
    assert len(msgs) == 0, f"clear后应无消息，实际{len(msgs)}"
    print(f"  ✓ clear 后: {len(msgs)} 条消息")

    # 测试增量读取
    with open(test_path, 'a', encoding='utf-8') as f:
        f.write("20:30:17.000|RECV|cspb.SomeAck|{OK = true,}\n")

    msgs = monitor.poll()
    assert len(msgs) == 1, f"增量应读到1条，实际{len(msgs)}"
    print(f"  ✓ 增量读取: {msgs[0]}")

    # 测试 format
    formatted = monitor.format_messages(msgs)
    assert 'SomeAck' in formatted
    print(f"  ✓ format_messages: 正常\n")

    # 清理
    os.remove(test_path)
    print("  ✅ 文件操作测试通过!\n")


def connect_to_unity():
    """连接 Unity 并测试实时监控"""
    print("=" * 50)
    print("🔌 测试: Unity 实时消息监控")
    print("=" * 50)

    monitor = NetMonitorWatcher()

    if not os.path.exists(monitor.log_path):
        print("  ⚠️ 日志文件不存在，请确认:")
        print("     1. Unity 已启动并运行游戏")
        print("     2. NetMessageMonitor.cs 已正确部署")
        print("     3. 文件路径:", monitor.log_path)
        return

    # 读取当前所有消息
    summary = monitor.summary()
    print(f"  📂 日志文件: {monitor.log_path}")
    print(f"  📊 当前统计: SEND={summary['send']}, RECV={summary['recv']}")

    all_msgs = monitor.read_all()
    if all_msgs:
        print(f"  📋 最近 5 条消息:")
        for m in all_msgs[-5:]:
            print(f"     {m}")
    else:
        print("  📋 暂无消息记录")

    print("  ✅ Unity 连接测试完成\n")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='NetMessageMonitor 测试')
    parser.add_argument('--wait', action='store_true', help='等待3秒看新消息')
    parser.add_argument('--poll', type=int, default=0, help='轮询N秒看消息')
    args = parser.parse_args()

    test_parse()
    test_file_ops()

    if args.wait:
        connect_to_unity()
        print("  等待 3 秒...")
        time.sleep(3)
        monitor = NetMonitorWatcher()
        msgs = monitor.read_all()
        print(f"\n  新消息: {len(msgs)} 条")
        for m in msgs[-5:]:
            print(f"    {m}")

    elif args.poll:
        timeout = args.poll
        monitor = NetMonitorWatcher()
        monitor.clear()
        end_time = time.time() + timeout
        all_msgs = []
        print(f"  轮询 {timeout} 秒...")
        while time.time() < end_time:
            msgs = monitor.poll()
            if msgs:
                all_msgs.extend(msgs)
                for m in msgs:
                    print(f"  ➜ {m}")
            time.sleep(0.2)
        print(f"\n  共收到 {len(all_msgs)} 条消息")

    else:
        connect_to_unity()
        print("\n💡 提示: 运行时加 --poll N 可以轮询N秒看实时消息")
