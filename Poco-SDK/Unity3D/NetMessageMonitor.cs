using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Google.Protobuf;
using Common;
using UnityEngine;

/// <summary>
/// 网络消息监控器
/// 挂钩 MessageMgr 收发消息，写入 net_messages.log
/// 供 Python 端（NetMonitorWatcher）读取实现灰盒测试
/// </summary>
public static class NetMessageMonitor
{
    // ========== 配置 ==========
    private static string _logPath = null;

    // 去重窗口（相同类型的消息在 N 秒内只记录一次，避免刷屏）
    private static readonly Dictionary<string, float> _recentTypes = new Dictionary<string, float>();
    private const float DEDUP_WINDOW = 3.0f;

    // 统计
    public static int SendCount { get; private set; }
    public static int RecvCount { get; private set; }

    // 临时列表（避免 GC）
    private static readonly List<string> _tempNameList = new List<string>();

    // ========== 初始化 ==========

    /// <summary>
    /// 初始化（由 NetMessagePoller.Update() 首次调用）
    /// </summary>
    public static void Init(string logPath = null)
    {
        if (_logPath != null)
            return; // 已初始化

        _logPath = logPath ?? Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "AutoSmoke", "logs", "net_messages.log"));

        // 确保日志目录存在
        var dir = Path.GetDirectoryName(_logPath);
        if (!Directory.Exists(dir))
            Directory.CreateDirectory(dir);

        // 清空旧日志
        File.WriteAllText(_logPath, "");

        // 挂钩接收消息事件（MessageMgr 是 static class，直接访问）
        Common.MessageMgr.OnBeforeNotify += OnMessageReceived;

        Debug.Log($"[NetMonitor] Initialized, log: {_logPath}");
    }

    /// <summary>
    /// 读取全部日志
    /// </summary>
    public static string ReadLog()
    {
        try
        {
            if (File.Exists(_logPath))
                return File.ReadAllText(_logPath);
        }
        catch { }
        return "";
    }

    /// <summary>
    /// 动态设置日志路径（Python 端可通过 Poco 调用）
    /// </summary>
    public static void SetLogPath(string path)
    {
        _logPath = path;
        Debug.Log($"[NetMonitor] Log path changed to: {_logPath}");
    }

    // ========== 接收消息回调 ==========

    /// <summary>
    /// 接收消息回调（挂钩 MessageMgr.OnBeforeNotify）
    /// </summary>
    private static void OnMessageReceived(Type msgType, IMessage msg)
    {
        // 跳过背景噪音消息
        if (IsNoiseType(msgType))
            return;

        RecvCount++;

        var typeName = msgType.FullName ?? msgType.Name;
        var content = Truncate(msg.ToString(), 500);
        WriteLine("RECV", typeName, content);
    }

    // ========== 发送消息轮询（由 NetMessagePoller.Update 驱动）==========

    /// <summary>
    /// 轮询新发送的消息（需在 Update 中每帧调用）
    /// 通过 Common.MessageInfo_Editor 获取发送消息列表
    /// </summary>
    public static void PollSentMessages()
    {
#if !UNITY_EDITOR
        return;
#endif
        _tempNameList.Clear();
        Common.MessageInfo_Editor.GetSendList(_tempNameList);

        foreach (var name in _tempNameList)
        {
            // 跳过背景噪音发送消息
            if (IsNoiseTypeByName(name))
                continue;

            // 去重：相同类型在 DEDUP_WINDOW 秒内只记录一次
            float now = Time.time;
            if (_recentTypes.TryGetValue(name, out float lastTime))
            {
                if (now - lastTime < DEDUP_WINDOW)
                    continue;
            }
            _recentTypes[name] = now;

            SendCount++;
            WriteLine("SEND", name, "");
        }
    }

    // ========== 噪音过滤 ==========

    /// <summary>
    /// 判断是否为背景噪音消息类型（与点击操作无关）
    /// 对照游戏 MessageMgr.CheckIsHide() 的逻辑
    /// </summary>
    private static bool IsNoiseType(Type type)
    {
        if (type == null) return true;
        string name = type.Name ?? "";
        return name == "HeartBeatReq" || name == "HeartBeatAck" ||
               name == "PositionNtf" ||
               name == "RallyNtf" || name == "RallyListAck" || name == "RallyListReq" ||
               name == "GetUnionMessageReq" || name == "GetUnionMessageAck" ||
               name.StartsWith("BIReport");
    }

    private static bool IsNoiseTypeByName(string shortName)
    {
        if (string.IsNullOrEmpty(shortName)) return true;
        return shortName == "HeartBeatReq" || shortName == "HeartBeatAck" ||
               shortName == "PositionNtf" ||
               shortName == "RallyNtf" || shortName == "RallyListAck" || shortName == "RallyListReq" ||
               shortName == "GetUnionMessageReq" || shortName == "GetUnionMessageAck" ||
               shortName.StartsWith("BIReport");
    }

    // ========== 文件写入 ==========

    private static void WriteLine(string dir, string type, string content)
    {
        try
        {
            string time = DateTime.Now.ToString("HH:mm:ss.fff");
            string line = $"{time}|{dir}|{type}|{content}\n";
            File.AppendAllText(_logPath, line, Encoding.UTF8);
        }
        catch { }
    }

    private static string Truncate(string s, int maxLen)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Length <= maxLen ? s : s.Substring(0, maxLen);
    }
}
