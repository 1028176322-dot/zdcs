"""
网络消息监控 - Python端
读取 NetMessageMonitor (C#) 输出的 net_messages.log 文件
提供 clear / poll / summary 接口

日志行格式:  HH:mm:ss.fff | DIR | cspb.TypeName | ContentSummary

用法:
    monitor = NetMonitorWatcher(log_path)
    monitor.clear()
    # ... 执行点击 ...
    time.sleep(1)
    messages = monitor.poll()
    for m in messages:
        print(m['type'], m['dir'])          # e.g. "cspb.SomeReq"  "SEND"
        print(m['content'][:100])            # protobuf 内容摘要
    print(monitor.summary())                 # {"send": 3, "recv": 5}
"""
import os
import re
import time
from datetime import datetime
from typing import List, Dict, Optional

# Unity 工程根目录（相对于 AutoSmoke 项目）
DEFAULT_LOG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'logs', 'net_messages.log')
)


class NetMessage:
    """一条网络消息记录"""
    def __init__(self, line: str):
        self.raw = line.strip()
        self.time: str = ''          # HH:mm:ss.fff
        self.dir: str = ''           # SEND / RECV
        self.type: str = ''          # 消息类型全称
        self.content: str = ''       # protobuf 文本内容
        self._parse()

    def _parse(self):
        # 格式: 时间|方向|类型全称|内容摘要
        parts = self.raw.split('|', 3)
        if len(parts) >= 4:
            self.time = parts[0].strip()
            self.dir = parts[1].strip()
            self.type = parts[2].strip()
            self.content = parts[3].strip()
        elif len(parts) == 3:
            self.time = parts[0].strip()
            self.dir = parts[1].strip()
            self.type = parts[2].strip()

    def is_send(self) -> bool:
        return self.dir == 'SEND'

    def is_recv(self) -> bool:
        return self.dir == 'RECV'

    def short_type(self) -> str:
        """返回短类型名（去掉命名空间前缀）"""
        return self.type.split('.')[-1] if '.' in self.type else self.type

    def __repr__(self):
        return f"[{self.time}][{self.dir}] {self.short_type()}"


class NetMonitorWatcher:
    """
    网络消息日志阅读器
    每次 poll() 只返回新产生的消息（基于文件位置游标）
    自动过滤背景噪音（心跳/BI/位置同步等）
    """

    # 噪音类型表（小写，匹配短名）
    NOISE_TYPES = {
        'heartbeatreq', 'heartbeatack',
        'positionntf',
        'rallyntf', 'rallylistack', 'rallylistreq',
        'getunionmessagereq', 'getunionmessageack',
    }

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or DEFAULT_LOG_PATH
        self._cursor = 0          # 已读取的字节偏移

        # 允许 3 秒内找不到文件（Unity 可能还没启动）
        self._wait_for_file(max_wait=3)

    def _wait_for_file(self, max_wait: float = 3):
        """等待日志文件出现"""
        start = time.time()
        while not os.path.exists(self.log_path):
            if time.time() - start > max_wait:
                print(f"⚠️ [NetMonitor] 日志文件未找到: {self.log_path}")
                print(f"   请确认 Unity 已启动且 NetMessageMonitor 脚本已部署")
                return
            time.sleep(0.3)

    # ---------- 公开接口 ----------

    def clear(self):
        """
        清空日志文件 + 重置游标
        在每次点击前调用
        """
        try:
            open(self.log_path, 'w').close()
        except:
            pass
        self._cursor = 0

    def poll(self, filter_noise: bool = True) -> List[NetMessage]:
        """
        读取自上次 poll()/clear() 以来的新消息
        filter_noise=True: 自动过滤心跳/BI/位置同步等背景噪音
        返回 NetMessage 列表，按时间顺序排列
        """
        if not os.path.exists(self.log_path):
            return []

        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                f.seek(self._cursor)
                lines = f.readlines()
                self._cursor = f.tell()
        except:
            return []

        messages = []
        for line in lines:
            line = line.strip()
            if not line or '|' not in line:
                continue
            try:
                msg = NetMessage(line)
                if filter_noise and self._is_noise(msg):
                    continue
                messages.append(msg)
            except:
                pass

        return messages

    def poll_blocking(self, timeout: float = 2.0) -> List[NetMessage]:
        """
        阻塞等待新消息（最多 timeout 秒）
        适用于点击后等待服务器回包
        """
        deadline = time.time() + timeout
        all_msgs = []
        while time.time() < deadline:
            msgs = self.poll()
            if msgs:
                all_msgs.extend(msgs)
                # 如果收到了新消息，再给一点时间收完
                deadline = time.time() + 0.5
            time.sleep(0.1)
        return all_msgs

    def summary(self) -> Dict:
        """统计当前文件中的消息概况"""
        if not os.path.exists(self.log_path):
            return {"send": 0, "recv": 0}

        send_count = 0
        recv_count = 0
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('|', 2)
                    if len(parts) >= 2:
                        if parts[1].strip() == 'SEND':
                            send_count += 1
                        elif parts[1].strip() == 'RECV':
                            recv_count += 1
        except:
            pass

        return {"send": send_count, "recv": recv_count}

    def read_all(self) -> List[NetMessage]:
        """读取全部消息（重置游标到文件尾）"""
        msgs = self.poll()
        return msgs

    # ---------- 便捷方法 ----------

    def format_messages(self, messages: List[NetMessage]) -> str:
        """格式化消息列表为可读字符串"""
        if not messages:
            return "   (无网络消息)"

        lines = []
        for m in messages:
            icon = '↑' if m.is_send() else '↓'
            lines.append(f"   {icon} {m.time} | {m.type}")

            # 截取内容摘要的前 3 个字段
            content = m.content[:120]
            if content:
                lines.append(f"     {content}")
        return '\n'.join(lines)

    def has_any_activity(self, messages: List[NetMessage]) -> bool:
        """是否有任何协议活动"""
        return len(messages) > 0

    def get_sends(self, messages: List[NetMessage]) -> List[NetMessage]:
        """筛选出发送消息"""
        return [m for m in messages if m.is_send()]

    def get_recvs(self, messages: List[NetMessage]) -> List[NetMessage]:
        """筛选出接收消息"""
        return [m for m in messages if m.is_recv()]

    def get_message_types(self, messages: List[NetMessage]) -> List[str]:
        """获取消息类型列表（去重保序）"""
        seen = set()
        types = []
        for m in messages:
            if m.type not in seen:
                seen.add(m.type)
                types.append(m.type)
        return types

    # ---------- 噪音过滤 ----------

    def _is_noise(self, msg: NetMessage) -> bool:
        """判断是否为背景噪音消息"""
        short = msg.short_type().lower()
        if short.startswith('bireport'):
            return True
        return short in self.NOISE_TYPES


# ============================================================
#  快速测试
# ============================================================

def quick_test():
    """读取当前日志输出摘要"""
    monitor = NetMonitorWatcher()
    print(f"📁 日志文件: {monitor.log_path}")
    print(f"📊 总计: {monitor.summary()}")
    msgs = monitor.read_all()
    print(f"📋 当前消息 ({len(msgs)} 条):")
    for m in msgs[-5:]:  # 只显示最后 5 条
        print(f"   {m}")
    if msgs:
        print(f"\n📝 最近一条内容预览:")
        print(f"   {msgs[-1].content[:200]}")


if __name__ == '__main__':
    quick_test()
