/*
 * GameViewLocator.cs
 * 自动获取 Unity Editor 中 Game 视图的窗口坐标
 * 
 * 原理：
 * 1. 用反射找到所有 UnityEditor.GameView 实例
 * 2. 读取 EditorWindow.position（屏幕坐标）
 * 3. 写入 JSON 文件
 * 
 * 用法：
 *   - 放入 Assets/Editor/ 后 Unity 自动编译并执行
 *   - 或菜单 AutoSmoke / Locate Game View 手动触发
 *   
 * 输出：%USERPROFILE%\.autosmoke\game_view_pos.json
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
        private static bool _hasRun = false;

        // JSON 输出目录（与 Python 端约定）
        private static string OutputDir
        {
            get
            {
                string env = Environment.GetEnvironmentVariable("AUTOSMOKE_CONFIG_DIR");
                if (!string.IsNullOrEmpty(env))
                    return env;
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    ".autosmoke"
                );
            }
        }

        private static string OutputPath { get { return Path.Combine(OutputDir, "game_view_pos.json"); } }

        // 静态构造：Unity 编译完成后自动执行
        static GameViewLocator()
        {
            EditorApplication.delayCall += OnFirstDelay;
        }

        private static void OnFirstDelay()
        {
            EditorApplication.delayCall -= OnFirstDelay;
            if (!_hasRun)
            {
                _hasRun = true;
                // 再延迟一帧确保界面加载完毕
                EditorApplication.delayCall += OnSecondDelay;
            }
        }

        private static void OnSecondDelay()
        {
            EditorApplication.delayCall -= OnSecondDelay;
            LocateAndSave();
        }

        private static void LocateAndSave()
        {
            try
            {
                var gameViews = FindGameViews();
                if (gameViews.Count == 0)
                {
                    WriteJson(false, 0, 0, 0, 0, "No GameView window found");
                    return;
                }

                // 取第一个可用的 GameView（Unity 2022 无 IsVisible API）
                EditorWindow target = null;
                foreach (var w in gameViews)
                {
                    if (w != null)
                    {
                        target = w;
                        break;
                    }
                }
                if (target == null)
                    target = gameViews[0];

                // EditorWindow.position = 屏幕坐标（含窗口装饰）
                var pos = target.position;
                
                // 反射读取 viewInWindow 属性（游戏渲染区域在GameView窗口中的坐标）
                var gameViewType = target.GetType();
                var viewInWindowProp = gameViewType.GetProperty("viewInWindow", 
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                
                float renderX = 0, renderY = 0, renderW = pos.width, renderH = pos.height;
                if (viewInWindowProp != null)
                {
                    var rect = (UnityEngine.Rect)viewInWindowProp.GetValue(target, null);
                    renderX = rect.x;
                    renderY = rect.y;
                    renderW = rect.width;
                    renderH = rect.height;
                    Debug.Log($"[AutoSmoke] 找到属性 viewInWindow: x={renderX}, y={renderY}, w={renderW}, h={renderH}");
                }
                
                // 计算游戏渲染区域的屏幕坐标
                int screenX = (int)(pos.x + renderX);
                int screenY = (int)(pos.y + renderY);
                int screenW = (int)renderW;
                int screenH = (int)renderH;
                
                WriteJson(true, screenX, screenY, screenW, screenH, "");
                Debug.Log($"[AutoSmoke] GameView: x={pos.x}, y={pos.y}, w={pos.width}, h={pos.height}");
                Debug.Log($"[AutoSmoke] 渲染区域屏幕坐标: x={screenX}, y={screenY}, w={screenW}, h={screenH}");
                Debug.Log($"[AutoSmoke] JSON: {OutputPath}");
            }
            catch (Exception e)
            {
                WriteJson(false, 0, 0, 0, 0, e.Message);
                Debug.LogError($"[AutoSmoke] 失败: {e.Message}");
            }
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
                if (gameViewType == null) return result;

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
                // 手动拼 JSON（避免外部依赖）
                string json = "{\n" +
                    $"  \"found\": {found.ToString().ToLower()},\n" +
                    $"  \"x\": {x},\n" +
                    $"  \"y\": {y},\n" +
                    $"  \"width\": {w},\n" +
                    $"  \"height\": {h},\n" +
                    $"  \"error\": \"{EscapeJson(error)}\",\n" +
                    $"  \"timestamp\": \"{DateTime.UtcNow:o}\",\n" +
                    $"  \"unityVersion\": \"{Application.unityVersion}\"\n" +
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

        // =========== 菜单手动触发 ===========
        [MenuItem("AutoSmoke/Locate Game View")]
        private static void OnMenuClick()
        {
            LocateAndSave();
            EditorUtility.DisplayDialog(
                "AutoSmoke",
                $"Game 视图坐标已保存:\n{OutputPath}",
                "OK"
            );
        }
    }
}
