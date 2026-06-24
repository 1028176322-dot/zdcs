/*
 * GameViewLocator.cs
 * 自动获取 Unity Editor 中 Game 视图的窗口坐标（自动执行版 v2）
 * 
 * 原理：
 * 1. [InitializeOnLoad] 让 Unity 加载时自动执行
 * 2. 用反射找到所有 UnityEditor.GameView 实例
 * 3. 读取 EditorWindow.position（屏幕坐标）
 * 4. 写入 JSON 文件
 * 
 * 输出路径：%USERPROFILE%\.autosmoke\game_view_pos.json
 *   - 可通过环境变量 AUTOSMOKE_CONFIG_DIR 覆盖
 * 
 * 触发方式：
 *   - 自动：Unity 编译完成后自动执行（最多重试 10 次）
 *   - 手动：Unity 菜单 AutoSmoke -> Locate Game View
 */

using System;
using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace AutoSmoke.Editor
{
    [InitializeOnLoad]
    public static class GameViewLocator
    {
        private static int _retryCount = 0;
        private static readonly int MaxRetries = 10;
        private static double _lastRequestCheck = 0;
        private const double REQUEST_CHECK_INTERVAL = 0.5; // 请求文件检测间隔（秒）

        // 请求文件路径
        private static string RequestPath { get { return Path.Combine(OutputDir, "locate_request.json"); } }

        // JSON 输出目录 —— 与 Python 端约定一致
        private static string OutputDir
        {
            get
            {
                // 优先级1：环境变量（可覆盖）
                string env = Environment.GetEnvironmentVariable("AUTOSMOKE_CONFIG_DIR");
                if (!string.IsNullOrEmpty(env))
                    return env;

                // 优先级2：默认路径（%USERPROFILE%\.autosmoke）
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    ".autosmoke"
                );
            }
        }

        private static string OutputPath { get { return Path.Combine(OutputDir, "game_view_pos.json"); } }

        // 静态构造：[InitializeOnLoad] 触发
        static GameViewLocator()
        {
            Debug.Log("[AutoSmoke] GameViewLocator 已加载，将在下一帧执行...");
            EditorApplication.delayCall += TryLocate;
            // 启动请求文件监听（支持外部触发重新定位）
            EditorApplication.update += PollLocateRequest;
            Debug.Log("[AutoSmoke] GameViewLocator 请求监听已启动");
        }

        /// <summary>
        /// 轮询 locate_request.json，收到请求后自动执行定位
        /// </summary>
        private static void PollLocateRequest()
        {
            double now = EditorApplication.timeSinceStartup;
            if (now - _lastRequestCheck < REQUEST_CHECK_INTERVAL)
                return;
            _lastRequestCheck = now;

            string reqPath = RequestPath;
            if (!File.Exists(reqPath))
                return;

            try
            {
                // 删除请求文件（避免重复处理）
                File.Delete(reqPath);
                Debug.Log("[AutoSmoke] 收到定位请求，开始重新定位...");

                var gameViews = FindGameViews();
                if (gameViews.Count == 0)
                {
                    WriteJson(false, 0, 0, 0, 0, "No GameView found from request");
                    Debug.LogWarning("[AutoSmoke] 请求定位失败: 未找到 GameView");
                    return;
                }

                LocateAndSave(gameViews);
                Debug.Log("[AutoSmoke] 请求定位完成");
            }
            catch (Exception e)
            {
                Debug.LogError($"[AutoSmoke] 处理定位请求失败: {e.Message}");
            }
        }

        private static void TryLocate()
        {
            try
            {
                var gameViews = FindGameViews();
                if (gameViews.Count == 0)
                {
                    _retryCount++;
                    if (_retryCount < MaxRetries)
                    {
                        Debug.Log($"[AutoSmoke] 未找到 GameView，{_retryCount}/{MaxRetries} 次重试...");
                        EditorApplication.delayCall += TryLocate;
                        return;
                    }
                    WriteJson(false, 0, 0, 0, 0, $"No GameView found after {MaxRetries} retries");
                    return;
                }

                // 找到 GameView，执行定位
                LocateAndSave(gameViews);
            }
            catch (Exception e)
            {
                WriteJson(false, 0, 0, 0, 0, e.Message);
                Debug.LogError($"[AutoSmoke] 失败: {e.Message}");
            }
        }

        private static void LocateAndSave(List<EditorWindow> gameViews)
        {
            // 取第一个（通常就是可见的那个）
            EditorWindow target = null;
            if (gameViews.Count > 0)
            {
                target = gameViews[0];
            }

            // EditorWindow.position = 屏幕坐标
            var pos = target.position;

            WriteJson(true, (int)pos.x, (int)pos.y, (int)pos.width, (int)pos.height, "");
            Debug.Log($"[AutoSmoke] ✅ GameView: x={pos.x}, y={pos.y}, w={pos.width}, h={pos.height}");
            Debug.Log($"[AutoSmoke] ✅ JSON: {OutputPath}");
        }

        /// <summary>
        /// 反射查找所有 GameView 实例
        /// </summary>
        private static List<EditorWindow> FindGameViews()
        {
            var result = new List<EditorWindow>();
            try
            {
                Type gameViewType = null;
                foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
                {
                    gameViewType = asm.GetType("UnityEditor.GameView");
                    if (gameViewType != null) break;
                }
                if (gameViewType == null)
                {
                    WriteJson(false, 0, 0, 0, 0, "UnityEditor.GameView type not found");
                    return result;
                }

                var windows = Resources.FindObjectsOfTypeAll(gameViewType);
                foreach (var w in windows)
                {
                    if (w is EditorWindow ew)
                        result.Add(ew);
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"[AutoSmoke] 查找失败: {e.Message}");
            }
            return result;
        }

        /// <summary>
        /// 写入 JSON 文件
        /// </summary>
        private static void WriteJson(bool found, int x, int y, int w, int h, string error)
        {
            try
            {
                Directory.CreateDirectory(OutputDir);
                string json = "{\n" +
                    $"  \"found\": {found.ToString().ToLower()},\n" +
                    $"  \"x\": {x},\n" +
                    $"  \"y\": {y},\n" +
                    $"  \"width\": {w},\n" +
                    $"  \"height\": {h},\n" +
                    $"  \"gameWidth\": {Screen.width},\n" +
                    $"  \"gameHeight\": {Screen.height},\n" +
                    $"  \"error\": \"{EscapeJson(error)}\",\n" +
                    $"  \"timestamp\": \"{DateTime.UtcNow:o}\",\n" +
                    $"  \"unityVersion\": \"{Application.unityVersion}\",\n" +
                    $"  \"note\": \"screen_coords\"\n" +
                    "}";
                File.WriteAllText(OutputPath, json);
            }
            catch (Exception e)
            {
                Debug.LogError($"[AutoSmoke] 写JSON失败: {e.Message}");
            }
        }

        private static string EscapeJson(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n");
        }

        // =========== 菜单手动触发（备用）===========
        [MenuItem("AutoSmoke/定位/定位 Game 视图 _&L")]
        private static void OnMenuClick()
        {
            var gameViews = FindGameViews();
            if (gameViews.Count == 0)
            {
                EditorUtility.DisplayDialog("AutoSmoke", "未找到 Game 视图窗口", "OK");
                return;
            }
            LocateAndSave(gameViews);
            EditorUtility.DisplayDialog(
                "AutoSmoke",
                $"Game 视图坐标已保存:\n{OutputPath}",
                "OK"
            );
        }
    }
}
