using UnityEngine;

/// <summary>
/// 游戏启动时自动初始化 PocoManager + NetMessageMonitor
/// 不需要手动挂载到任何 GameObject
/// </summary>
public static class AutoStartPoco
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    private static void Initialize()
    {
        // 防止重复创建
        if (GameObject.Find("PocoManager") != null)
            return;

        var go = new GameObject("PocoManager");

        // Poco 服务
        go.AddComponent<PocoManager>();

        // 网络消息轮询器（每帧驱动 NetMessageMonitor.PollSentMessages()）
        go.AddComponent<NetMessagePoller>();

        Object.DontDestroyOnLoad(go);

        Debug.Log("[AutoStartPoco] PocoManager + NetMessagePoller initialized");
    }
}

/// <summary>
/// 网络消息轮询器（MonoBehaviour，每帧驱动 NetMessageMonitor 的发送消息轮询）
/// </summary>
public class NetMessagePoller : MonoBehaviour
{
    private void Start()
    {
        // 初始化网络消息监控器（设置日志路径）
        NetMessageMonitor.Init();
    }

    private void Update()
    {
        // 每帧轮询发送消息
        NetMessageMonitor.PollSentMessages();
    }

    private void OnDestroy()
    {
        Debug.Log($"[NetMonitor] Stats - Send: {NetMessageMonitor.SendCount}, Recv: {NetMessageMonitor.RecvCount}");
    }
}
