using System;
using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.EventSystems;

/// <summary>
/// AutoSmoke 运行态 Bridge
/// 职责：
///   1. 每 1 秒写心跳文件 unity_heartbeat.json
///   2. 监听请求目录，执行 dump_runtime_ui_tree / test_click_element
///   3. 写响应到响应目录
/// 仅 Editor 工具，不修改游戏业务逻辑。
/// </summary>
[InitializeOnLoad]
public static class AutoSmokeRuntimeBridge
{
    private static string _bridgeRoot;
    private static string _requestsDir;
    private static string _responsesDir;
    private static string _heartbeatPath;
    private static string _metadataDir;
    private static string _clickRequestPath;
    private static string _clickResultPath;
    private static double _lastHeartbeatTime;
    private static double _lastPollTime;
    private static HashSet<string> _processedRequests = new HashSet<string>();

    static AutoSmokeRuntimeBridge()
    {
        EditorApplication.update += OnEditorUpdate;
        _lastHeartbeatTime = EditorApplication.timeSinceStartup;
        _lastPollTime = EditorApplication.timeSinceStartup;

        // 从 ~/.autosmoke/config.json 读取 autosmokeRoot
        string configPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".autosmoke", "config.json");
        try
        {
            if (File.Exists(configPath))
            {
                string json = File.ReadAllText(configPath);
                var cfg = JsonUtility.FromJson<AutoSmokeConfig>(json);
                if (cfg != null && !string.IsNullOrEmpty(cfg.autosmokeRoot))
                {
                    _bridgeRoot = Path.Combine(cfg.autosmokeRoot, "runtime", "bridge").Replace("/", "\\");
                    _metadataDir = Path.Combine(cfg.autosmokeRoot, "metadata").Replace("/", "\\");
                }
            }
        }
        catch { }

        if (string.IsNullOrEmpty(_bridgeRoot))
        {
            _bridgeRoot = Path.Combine(Application.dataPath, "..", "AutoSmoke", "runtime", "bridge");
            _metadataDir = Path.Combine(Application.dataPath, "..", "AutoSmoke", "metadata");
        }

        _requestsDir = Path.Combine(_bridgeRoot, "requests");
        _responsesDir = Path.Combine(_bridgeRoot, "responses");
        _heartbeatPath = Path.Combine(_bridgeRoot, "unity_heartbeat.json");
        string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        string clickRoot = Path.Combine(userProfile, ".autosmoke");
        _clickRequestPath = Path.Combine(clickRoot, "click_request.json");
        _clickResultPath = Path.Combine(clickRoot, "click_result.json");

        try
        {
            Directory.CreateDirectory(_requestsDir);
            Directory.CreateDirectory(_responsesDir);
        }
        catch { }
    }

    private static void OnEditorUpdate()
    {
        if (!EditorApplication.isPlaying) return;

        double now = EditorApplication.timeSinceStartup;

        // 每 1 秒写心跳
        if (now - _lastHeartbeatTime >= 1.0)
        {
            WriteHeartbeat();
            _lastHeartbeatTime = now;
        }

        // 每 0.5 秒轮询请求
        if (now - _lastPollTime >= 0.5)
        {
            PollRequests();
            _lastPollTime = now;
        }
    }

    private static void WriteHeartbeat()
    {
        try
        {
            var hb = new HeartbeatData
            {
                alive = true,
                playMode = EditorApplication.isPlaying,
                sceneId = GetActiveScene(),
                pageId = GetActivePage(),
                updatedAt = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss")
            };
            string json = JsonUtility.ToJson(hb, true);
            File.WriteAllText(_heartbeatPath, json);
        }
        catch { }
    }

    private static void PollRequests()
    {
        if (!Directory.Exists(_requestsDir)) return;
        foreach (string reqFile in Directory.GetFiles(_requestsDir, "*.json"))
        {
            string fileName = Path.GetFileName(reqFile);
            if (_processedRequests.Contains(fileName)) continue;
            _processedRequests.Add(fileName);

            try
            {
                string reqJson = File.ReadAllText(reqFile);
                var req = JsonUtility.FromJson<BridgeRequestData>(reqJson);
                if (req == null) continue;
                req.rawJson = reqJson;

                string respId = req.requestId ?? fileName.Replace(".json", "");
                string respFile = Path.Combine(_responsesDir, respId + ".json");
                string doneFile = Path.Combine(_responsesDir, respId + ".done");

                if (req.type == "dump_runtime_ui_tree")
                {
                    HandleDumpRuntimeTree(req, respFile, doneFile);
                }
                else if (req.type == "get_current_state")
                {
                    HandleGetCurrentState(req, respFile, doneFile);
                }
                else if (req.type == "test_click_element")
                {
                    // 委托给 AutoSmokeClickInjector（通过 request/response 文件）
                    HandleTestClick(req, respFile, doneFile);
                }
            }
            catch { }
            finally
            {
                try { File.Delete(reqFile); } catch { }
            }
        }

        // 清理旧记录，防止内存泄漏
        if (_processedRequests.Count > 100)
        {
            _processedRequests.Clear();
        }
    }

    private static void HandleDumpRuntimeTree(BridgeRequestData req, string respFile, string doneFile)
    {
        var nodes = RuntimeUITreeDumper.Dump(false);

        var resp = new BridgeResponseData
        {
            requestId = req.requestId,
            success = true,
            type = "dump_runtime_ui_tree",
            finishedAt = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
            payload = new Dictionary<string, object>
            {
                ["sceneId"] = GetActiveScene(),
                ["pageId"] = GetActivePage(),
                ["nodeCount"] = nodes.Count,
                ["clickableCount"] = nodes.Count > 0 ? nodes.FindAll(n => n.clickable).Count : 0,
                ["nodes"] = nodes
            }
        };
        WriteResponse(resp, respFile, doneFile);
    }

    private static void HandleGetCurrentState(BridgeRequestData req, string respFile, string doneFile)
    {
        var nodes = RuntimeUITreeDumper.Dump(false);
        var resp = new BridgeResponseData
        {
            requestId = req.requestId,
            success = true,
            type = "get_current_state",
            finishedAt = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
            payload = new Dictionary<string, object>
            {
                ["sceneId"] = GetActiveScene(),
                ["pageId"] = GetActivePage(),
                ["playMode"] = EditorApplication.isPlaying,
                ["nodeCount"] = nodes.Count,
            }
        };
        WriteResponse(resp, respFile, doneFile);
    }

    private static void HandleTestClick(BridgeRequestData req, string respFile, string doneFile)
    {
        string runtimePath = ExtractJsonString(req.rawJson, "runtimePath");
        int instanceId = ExtractJsonInt(req.rawJson, "instanceId", 0);
        bool bypassDebugOverlay = ExtractJsonBool(req.rawJson, "bypassDebugOverlay", false);
        var resp = new BridgeResponseData
        {
            requestId = req.requestId,
            success = false,
            type = "test_click_element",
            finishedAt = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
            payload = new Dictionary<string, object>
            {
                ["expectedRuntimePath"] = runtimePath,
                ["hitRuntimePath"] = "",
                ["eventReceiverMatched"] = false,
                ["clickResult"] = "NOT_EXECUTED",
                ["instanceId"] = instanceId,
                ["debugOverlayBypassed"] = false,
            }
        };

        if (string.IsNullOrEmpty(runtimePath))
        {
            resp.payload["clickResult"] = "INVALID_REQUEST";
            resp.payload["error"] = "runtimePath is empty";
            WriteResponse(resp, respFile, doneFile);
            return;
        }

        string clickRequestId = req.requestId;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(_clickRequestPath));
            if (File.Exists(_clickResultPath))
            {
                File.Delete(_clickResultPath);
            }
            string clickReq = "{\n"
                + "  \"action\": \"click\",\n"
                + "  \"targetType\": \"path\",\n"
                + "  \"targetValue\": \"" + EscapeJson(runtimePath) + "\",\n"
                + "  \"safePoint\": \"center\",\n"
                + "  \"bypassDebugOverlay\": " + (bypassDebugOverlay ? "true" : "false") + ",\n"
                + "  \"requestId\": \"" + EscapeJson(clickRequestId) + "\",\n"
                + "  \"timestamp\": \"" + EscapeJson(DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss")) + "\"\n"
                + "}\n";
            File.WriteAllText(_clickRequestPath, clickReq);

            DateTime deadline = DateTime.Now.AddSeconds(8);
            string clickJson = "";
            bool matchedClickResult = false;
            while (DateTime.Now < deadline)
            {
                if (File.Exists(_clickResultPath))
                {
                    clickJson = File.ReadAllText(_clickResultPath);
                    if (clickJson.Contains("\"requestId\": \"" + clickRequestId + "\"") || clickJson.Contains("\"requestId\":\"" + clickRequestId + "\""))
                    {
                        matchedClickResult = true;
                        break;
                    }
                }
                System.Threading.Thread.Sleep(25);
            }

            if (!matchedClickResult && File.Exists(_clickResultPath))
            {
                clickJson = File.ReadAllText(_clickResultPath);
                matchedClickResult = clickJson.Contains("\"requestId\": \"" + clickRequestId + "\"") || clickJson.Contains("\"requestId\":\"" + clickRequestId + "\"");
            }

            if (!matchedClickResult)
            {
                resp.payload["clickResult"] = "CLICK_TIMEOUT";
                resp.payload["error"] = "AutoSmokeClickInjector did not write click_result.json";
                WriteResponse(resp, respFile, doneFile);
                return;
            }

            string status = ExtractJsonString(clickJson, "status");
            string message = ExtractJsonString(clickJson, "message");
            string eventReceiver = ExtractJsonString(clickJson, "eventReceiver");
            string targetGameObject = ExtractJsonString(clickJson, "targetGameObject");
            string dispatchTarget = ExtractJsonString(clickJson, "dispatchTarget");
            string debugOverlayReceiver = ExtractJsonString(clickJson, "debugOverlayReceiver");
            bool receiverMatchTarget = ExtractJsonBool(clickJson, "receiverMatchTarget", false);
            bool debugOverlayBypassed = ExtractJsonBool(clickJson, "debugOverlayBypassed", false);
            resp.success = status == "OK";
            resp.payload["clickResult"] = status == "OK" ? "CLICK_CONFIRMED" : status;
            resp.payload["expectedRuntimePath"] = runtimePath;
            resp.payload["hitRuntimePath"] = eventReceiver;
            resp.payload["targetGameObject"] = targetGameObject;
            resp.payload["dispatchTarget"] = dispatchTarget;
            resp.payload["eventReceiverMatched"] = receiverMatchTarget;
            resp.payload["debugOverlayBypassed"] = debugOverlayBypassed;
            resp.payload["debugOverlayReceiver"] = debugOverlayReceiver;
            resp.payload["message"] = message;
        }
        catch (Exception ex)
        {
            resp.payload["clickResult"] = "BRIDGE_EXCEPTION";
            resp.payload["error"] = ex.Message;
        }
        WriteResponse(resp, respFile, doneFile);
    }

    private static string GetActiveScene()
    {
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        return scene != null ? scene.name : "unknown";
    }

    private static string GetActivePage()
    {
        var canvases = GameObject.FindObjectsOfType<Canvas>();
        foreach (var c in canvases)
        {
            if (c.gameObject.activeInHierarchy && c.gameObject.name != "Canvas")
                return c.gameObject.name;
        }
        if (canvases.Length > 0)
            return canvases[0].gameObject.name;
        return "unknown";
    }

    private static void WriteResponse(BridgeResponseData resp, string respFile, string doneFile)
    {
        try
        {
            // 手动构建 JSON，因为 JsonUtility 不支持 Dictionary
            var sb = new System.Text.StringBuilder();
            sb.Append("{\n");
            sb.Append("  \"requestId\": \"" + EscapeJson(resp.requestId) + "\",\n");
            sb.Append("  \"success\": " + (resp.success ? "true" : "false") + ",\n");
            sb.Append("  \"type\": \"" + EscapeJson(resp.type) + "\",\n");
            sb.Append("  \"finishedAt\": \"" + EscapeJson(resp.finishedAt) + "\",\n");
            sb.Append("  \"payload\": {\n");

            bool first = true;
            foreach (var kv in resp.payload)
            {
                if (!first) sb.Append(",\n");
                first = false;
                sb.Append("    \"" + EscapeJson(kv.Key) + "\": ");
                sb.Append(ValueToJson(kv.Value));
            }
            sb.Append("\n  }\n");
            sb.Append("}\n");

            File.WriteAllText(respFile, sb.ToString());
            File.WriteAllText(doneFile, "done");
        }
        catch (Exception ex)
        {
            Debug.LogError("[AutoSmokeBridge] WriteResponse error: " + ex.Message);
        }
    }

    private static string EscapeJson(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"")
                .Replace("\n", "\\n").Replace("\r", "\\r")
                .Replace("\t", "\\t");
    }

    private static string ExtractJsonString(string json, string key)
    {
        if (string.IsNullOrEmpty(json) || string.IsNullOrEmpty(key)) return "";
        string pattern = "\"" + key + "\"";
        int keyIndex = json.IndexOf(pattern, StringComparison.Ordinal);
        if (keyIndex < 0) return "";
        int colon = json.IndexOf(':', keyIndex + pattern.Length);
        if (colon < 0) return "";
        int quote = json.IndexOf('"', colon + 1);
        if (quote < 0) return "";
        var sb = new System.Text.StringBuilder();
        bool escape = false;
        for (int i = quote + 1; i < json.Length; i++)
        {
            char c = json[i];
            if (escape)
            {
                if (c == 'n') sb.Append('\n');
                else if (c == 'r') sb.Append('\r');
                else if (c == 't') sb.Append('\t');
                else sb.Append(c);
                escape = false;
                continue;
            }
            if (c == '\\')
            {
                escape = true;
                continue;
            }
            if (c == '"') break;
            sb.Append(c);
        }
        return sb.ToString();
    }

    private static int ExtractJsonInt(string json, string key, int defaultValue)
    {
        if (string.IsNullOrEmpty(json) || string.IsNullOrEmpty(key)) return defaultValue;
        string pattern = "\"" + key + "\"";
        int keyIndex = json.IndexOf(pattern, StringComparison.Ordinal);
        if (keyIndex < 0) return defaultValue;
        int colon = json.IndexOf(':', keyIndex + pattern.Length);
        if (colon < 0) return defaultValue;
        int start = colon + 1;
        while (start < json.Length && char.IsWhiteSpace(json[start])) start++;
        int end = start;
        while (end < json.Length && (char.IsDigit(json[end]) || json[end] == '-')) end++;
        if (int.TryParse(json.Substring(start, end - start), out int value)) return value;
        return defaultValue;
    }

    private static bool ExtractJsonBool(string json, string key, bool defaultValue)
    {
        if (string.IsNullOrEmpty(json) || string.IsNullOrEmpty(key)) return defaultValue;
        string pattern = "\"" + key + "\"";
        int keyIndex = json.IndexOf(pattern, StringComparison.Ordinal);
        if (keyIndex < 0) return defaultValue;
        int colon = json.IndexOf(':', keyIndex + pattern.Length);
        if (colon < 0) return defaultValue;
        string tail = json.Substring(colon + 1).TrimStart();
        if (tail.StartsWith("true", StringComparison.OrdinalIgnoreCase)) return true;
        if (tail.StartsWith("false", StringComparison.OrdinalIgnoreCase)) return false;
        return defaultValue;
    }

    private static string ValueToJson(object val)
    {
        if (val == null) return "null";
        if (val is bool b) return b ? "true" : "false";
        if (val is int i) return i.ToString();
        if (val is long l) return l.ToString();
        if (val is float f) return f.ToString("0.####");
        if (val is double d) return d.ToString("0.####");
        if (val is string s) return "\"" + EscapeJson(s) + "\"";
        if (val is List<RuntimeUITreeDumper.RuntimeUITreeNode> nodeList)
        {
            return NodesToJson(nodeList);
        }
        return "\"" + EscapeJson(val.ToString()) + "\"";
    }

    private static string NodesToJson(List<RuntimeUITreeDumper.RuntimeUITreeNode> nodes)
    {
        var sb = new System.Text.StringBuilder();
        sb.Append("[\n");
        for (int i = 0; i < nodes.Count; i++)
        {
            if (i > 0) sb.Append(",\n");
            var n = nodes[i];
            sb.Append("    {\n");
            sb.Append("      \"runtimePath\": \"" + EscapeJson(n.runtimePath) + "\",\n");
            sb.Append("      \"nodeName\": \"" + EscapeJson(n.nodeName) + "\",\n");
            sb.Append("      \"instanceId\": " + n.instanceId + ",\n");
            sb.Append("      \"activeInHierarchy\": " + (n.activeInHierarchy ? "true" : "false") + ",\n");
            sb.Append("      \"visible\": " + (n.visible ? "true" : "false") + ",\n");
            sb.Append("      \"clickable\": " + (n.clickable ? "true" : "false") + ",\n");
            sb.Append("      \"interactable\": " + (n.interactable ? "true" : "false") + ",\n");
            sb.Append("      \"raycastTarget\": " + (n.raycastTarget ? "true" : "false") + ",\n");
            sb.Append("      \"text\": \"" + EscapeJson(n.text) + "\",\n");
            sb.Append("      \"components\": " + ListToJson(n.components) + ",\n");
            sb.Append("      \"spriteName\": \"" + EscapeJson(n.spriteName) + "\",\n");
            sb.Append("      \"atlasName\": \"" + EscapeJson(n.atlasName) + "\",\n");
            sb.Append("      \"screenRect\": " + FloatListToJson(n.screenRect) + ",\n");
            sb.Append("      \"normalizedRect\": " + FloatListToJson(n.normalizedRect) + ",\n");
            sb.Append("      \"pageId\": \"" + EscapeJson(n.pageId) + "\",\n");
            sb.Append("      \"siblingIndex\": " + n.siblingIndex + ",\n");
            sb.Append("      \"eventReceivers\": " + ListToJson(n.eventReceivers) + ",\n");
            sb.Append("      \"elementType\": \"" + EscapeJson(n.elementType ?? "") + "\",\n");
            sb.Append("      \"interactionType\": \"" + EscapeJson(n.interactionType ?? "") + "\",\n");
            sb.Append("      \"clickTargetNode\": \"" + EscapeJson(n.clickTargetNode ?? "") + "\",\n");
            sb.Append("      \"clickableReason\": \"" + EscapeJson(n.clickableReason ?? "") + "\",\n");
            sb.Append("      \"effectiveClickable\": " + (n.effectiveClickable ? "true" : "false") + ",\n");
            sb.Append("      \"isIcon\": " + (n.isIcon ? "true" : "false") + ",\n");
            sb.Append("      \"isInteractiveIcon\": " + (n.isInteractiveIcon ? "true" : "false") + ",\n");
            sb.Append("      \"isCell\": " + (n.isCell ? "true" : "false") + ",\n");
            sb.Append("      \"isMask\": " + (n.isMask ? "true" : "false") + ",\n");
            sb.Append("      \"isDragArea\": " + (n.isDragArea ? "true" : "false") + ",\n");
            sb.Append("      \"isScrollArea\": " + (n.isScrollArea ? "true" : "false") + "\n");
            sb.Append("    }");
        }
        sb.Append("\n  ]");
        return sb.ToString();
    }

    private static string ListToJson(List<string> list)
    {
        if (list == null || list.Count == 0) return "[]";
        var sb = new System.Text.StringBuilder();
        sb.Append("[");
        for (int i = 0; i < list.Count; i++)
        {
            if (i > 0) sb.Append(",");
            sb.Append("\"" + EscapeJson(list[i]) + "\"");
        }
        sb.Append("]");
        return sb.ToString();
    }

    private static string FloatListToJson(List<float> list)
    {
        if (list == null || list.Count == 0) return "[]";
        var sb = new System.Text.StringBuilder();
        sb.Append("[");
        for (int i = 0; i < list.Count; i++)
        {
            if (i > 0) sb.Append(",");
            sb.Append(list[i].ToString("0.####"));
        }
        sb.Append("]");
        return sb.ToString();
    }

    [Serializable]
    private class BridgeRequestData
    {
        public string requestId;
        public string type;
        public string createdAt;
        [NonSerialized]
        public string rawJson;
    }

    private class BridgeResponseData
    {
        public string requestId;
        public bool success;
        public string type;
        public string finishedAt;
        public Dictionary<string, object> payload;
    }

    [Serializable]
    private class AutoSmokeConfig
    {
        public string autosmokeRoot;
    }

    [Serializable]
    private class HeartbeatData
    {
        public bool alive;
        public bool playMode;
        public string sceneId;
        public string pageId;
        public string updatedAt;
    }
}
