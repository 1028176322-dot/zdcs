/*
 * AutoSmokeGameContentCapture.cs
 * Unity 直出完整 GameContent PNG（P0 截图主方案）
 * 
 * 目标：从 Unity Editor 侧直接输出纯净的 GameContent 区域 PNG，
 *       分辨率为游戏设计分辨率（如 1170×2532），
 *       不含工具栏、不依赖 Python 屏幕裁剪。
 * 
 * 工作方式：
 *   1. ScreenCapture.CaptureScreenshot(path, 1) 获取完整游戏渲染图
 *   2. 直接保存，不裁剪不缩放（CaptureScreenshot 已输出现渲染分辨率）
 *   3. 元数据标记 coordinateSpace = game_design_resolution
 * 
 * 触发方式：
 *   - 菜单：AutoSmoke > 直出截图 > 导出截图 (Ctrl+Alt+Shift+S)
 *   - 请求文件：capture_request.json 触发（Python 侧）
 *   - 定时：AutoSmoke > 直出截图 > 启动自动导出
 * 
 * 输出文件：
 *   - cap_YYYYMMDD_HHmmss.png — 完整游戏界面截图（设计分辨率）
 *   - cap_YYYYMMDD_HHmmss.json — 截图元数据
 * 
 * 设计边界：
 *   - 只在 Unity Editor 中运行（Assets/Editor/）
 *   - 不修改游戏业务代码
 *   - 不进入构建包
 */

using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class AutoSmokeGameContentCapture
{
    // ── 路径配置 ──
    private static string _configDir;
    private static string _captureDir;
    private const string REQUEST_FILENAME = "capture_request.json";

    // ── 定时导出 ──
    private static bool _autoCapture = false;
    private static double _lastCaptureTime = 0;
    private const double CAPTURE_INTERVAL = 1.0; // 秒

    // ── 延时捕获 ──
    private static bool _pendingCapture = false;
    private static string _pendingCaptureReason = "";
    private static int _pendingFrameDelay = 0;
    // ── 异步文件读取 ──
    private static bool _pendingFileRead = false;
    private static string _pendingFilePath = "";
    private static double _pendingFileReadStart = 0;

    // ── 兜底设计分辨率 ──
    private const int FALLBACK_WIDTH = 1170;
    private const int FALLBACK_HEIGHT = 2532;

    // ── 反射缓存 ──
    private static Type _gameViewType;
    private static PropertyInfo _gameViewPosProp;
    private static PropertyInfo _currentSizeProp;
    private static Type _gameViewSizeType;
    private static PropertyInfo _sizeWidthProp;
    private static PropertyInfo _sizeHeightProp;

    static AutoSmokeGameContentCapture()
    {
        string userProfile = Environment.GetEnvironmentVariable("USERPROFILE")
                             ?? Environment.GetEnvironmentVariable("HOME")
                             ?? ".";
        _configDir = Path.Combine(userProfile, ".autosmoke");
        // 从 config.json 读取 AutoSmoke 根目录
        string cfgPath = Path.Combine(_configDir, "config.json");
        if (File.Exists(cfgPath))
        {
            try
            {
                string cfgJson = File.ReadAllText(cfgPath);
                var cfg = JsonUtility.FromJson<AutoSmokeCaptureConfig>(cfgJson);
                if (cfg != null && !string.IsNullOrEmpty(cfg.autosmokeRoot))
                {
                    _captureDir = Path.Combine(cfg.autosmokeRoot, "screenshots").Replace("/", "\\");
                }
            }
            catch { }
        }
        if (string.IsNullOrEmpty(_captureDir))
        {
            _captureDir = Path.Combine(_configDir, "capture");
        }
        try { Directory.CreateDirectory(_captureDir); } catch { }

        CacheReflectionTypes();

        EditorApplication.update += OnEditorUpdate;
        Debug.Log($"[AutoSmoke] GameContentCapture 已启动，输出: {_captureDir}");
    }

    private static void CacheReflectionTypes()
    {
        try
        {
            var asm = typeof(EditorWindow).Assembly;
            _gameViewType = asm.GetType("UnityEditor.GameView");
            _gameViewPosProp = _gameViewType?.GetProperty("position",
                BindingFlags.Public | BindingFlags.Instance);
            _currentSizeProp = _gameViewType?.GetProperty("currentGameViewSize",
                BindingFlags.NonPublic | BindingFlags.Instance);
            _gameViewSizeType = asm.GetType("UnityEditor.GameViewSize");
            if (_gameViewSizeType != null)
            {
                _sizeWidthProp = _gameViewSizeType.GetProperty("width",
                    BindingFlags.Public | BindingFlags.Instance);
                _sizeHeightProp = _gameViewSizeType.GetProperty("height",
                    BindingFlags.Public | BindingFlags.Instance);
            }
        }
        catch { }
    }

    // ============================================================
    // 更新循环
    // ============================================================
    private static void OnEditorUpdate()
    {
        try
        {
            double now = EditorApplication.timeSinceStartup;

            // 处理异步文件读取（CaptureScreenshot 写入完成后读取）
            if (_pendingFileRead)
            {
                if (File.Exists(_pendingFilePath))
                {
                    try
                    {
                        long size = new FileInfo(_pendingFilePath).Length;
                        if (size > 1000)
                        {
                            byte[] bytes = File.ReadAllBytes(_pendingFilePath);
                            Texture2D tex = new Texture2D(2, 2);
                            tex.LoadImage(bytes);
                            _pendingFileRead = false;
                            ProcessCapturedTexture(tex, _pendingCaptureReason);
                            return;
                        }
                    }
                    catch { }
                }
                if (EditorApplication.timeSinceStartup - _pendingFileReadStart > 5.0)
                {
                    Debug.LogError("[AutoSmoke] CaptureScreenshot 截图超时");
                    _pendingFileRead = false;
                }
                return;
            }

            // 处理延时捕获（等 2 帧触发 CaptureScreenshot）
            if (_pendingCapture && _pendingFrameDelay > 0)
            {
                _pendingFrameDelay--;
            }
            else if (_pendingCapture)
            {
                _pendingCapture = false;
                string reason = _pendingCaptureReason;
                _pendingCaptureReason = "";
                // 发起异步文件捕获，然后在后面帧读取
                StartAsyncCapture(reason);
                return;
            }

            // 1. 检查请求文件
            string reqPath = Path.Combine(_configDir, REQUEST_FILENAME);
            if (File.Exists(reqPath))
            {
                try { File.Delete(reqPath); } catch { }
                Debug.Log("[AutoSmoke] 收到截图请求");
                ScheduleCapture("request_file");
            }

            // 2. 自动定时导出
            if (_autoCapture && now - _lastCaptureTime >= CAPTURE_INTERVAL)
            {
                _lastCaptureTime = now;
                ScheduleCapture("auto");
            }
        }
        catch { }
    }

    private static void ScheduleCapture(string reason)
    {
        _pendingCapture = true;
        _pendingCaptureReason = reason;
        _pendingFrameDelay = 2;
    }

    // ============================================================
    // 菜单项
    // ============================================================

    [MenuItem("AutoSmoke/直出截图/导出截图 _#&S")]
    private static void CaptureMenuItem()
    {
        ScheduleCapture("manual_menu");
        EditorUtility.DisplayDialog("AutoSmoke",
            "截图将在下一帧导出", "OK");
    }

    [MenuItem("AutoSmoke/直出截图/启动自动导出")]
    private static void StartAutoCapture()
    {
        _autoCapture = true;
        _lastCaptureTime = EditorApplication.timeSinceStartup;
        Debug.Log("[AutoSmoke] 自动截图已启动 (1s 间隔)");
    }

    [MenuItem("AutoSmoke/直出截图/停止自动导出")]
    private static void StopAutoCapture()
    {
        _autoCapture = false;
        Debug.Log("[AutoSmoke] 自动截图已停止");
    }

    [MenuItem("AutoSmoke/直出截图/打开输出目录")]
    private static void OpenCaptureDir()
    {
        if (Directory.Exists(_captureDir))
            EditorUtility.OpenWithDefaultApp(_captureDir);
        else
            EditorUtility.DisplayDialog("AutoSmoke",
                $"目录不存在:\n{_captureDir}", "OK");
    }

    // ============================================================
    // 主截图流程（异步：CaptureScreenshot + 后续帧读取）
    // ============================================================
    private static void StartAsyncCapture(string trigger)
    {
        try
        {
            // 获取 GameView（仅用于确认窗口存在）
            var gameViews = FindGameViews();
            if (gameViews.Count == 0)
            {
                Debug.LogWarning("[AutoSmoke] 未找到 GameView 窗口");
                return;
            }
            var gv = gameViews[0];

            // 获取 GameView 窗口尺寸
            int gvW = 0, gvH = 0;
            if (_gameViewPosProp != null)
            {
                var pos = (Rect)_gameViewPosProp.GetValue(gv);
                gvW = (int)pos.width;
                gvH = (int)pos.height;
            }
            if (gvW <= 0 || gvH <= 0) return;

            _captureGvW = gvW; _captureGvH = gvH;

            // 发起异步文件截图（CaptureScreenshot 在帧结束时自动输出设计分辨率渲染图）
            string fbDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                ".autosmoke", "runtime");
            Directory.CreateDirectory(fbDir);
            string fbPath = Path.Combine(fbDir, "capture_frame.png");
            _pendingFilePath = fbPath;
            _pendingFileReadStart = EditorApplication.timeSinceStartup;

            ScreenCapture.CaptureScreenshot(fbPath, 1);
            _pendingFileRead = true;
            _pendingCaptureReason = trigger;
        }
        catch (Exception ex)
        {
            Debug.LogError("[AutoSmoke] StartAsyncCapture error: " + ex.Message);
        }
    }

    private static void ProcessCapturedTexture(Texture2D fullTex, string trigger)
    {
        try
        {
            int texW = fullTex.width;
            int texH = fullTex.height;

            // 方案 A：直接保存完整纹理，不裁剪不缩放
            // ScreenCapture.CaptureScreenshot(path, 1) 输出的已经是游戏设计分辨率渲染图
            byte[] pngBytes = fullTex.EncodeToPNG();
            string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string runDir = FindOrCreateRunDir(_captureDir, 10);
            string pngPath = Path.Combine(runDir, $"cap_{timestamp}.png");
            File.WriteAllBytes(pngPath, pngBytes);

            string metaPath = Path.Combine(runDir, $"cap_{timestamp}.json");
            string metaJson = $@"{{
  ""schema"": ""capture/game_design_resolution/v1"",
  ""timestamp"": ""{DateTime.Now:yyyy-MM-ddTHH:mm:ss.fffK}"",
  ""trigger"": ""{EscapeJson(trigger)}"",
  ""coordinateSpace"": ""game_design_resolution"",
  ""resolution"": {{ ""width"": {texW}, ""height"": {texH} }},
  ""fileSize"": {pngBytes.Length},
  ""filePath"": ""{EscapeJson(pngPath)}""
}}";
            File.WriteAllText(metaPath, metaJson);

            Debug.Log($"[AutoSmoke] 截图已保存: {pngPath} ({texW}x{texH}, {pngBytes.Length} bytes)");

            UnityEngine.Object.DestroyImmediate(fullTex);
        }
        catch (Exception ex)
        {
            Debug.LogError("[AutoSmoke] ProcessCapturedTexture error: " + ex.Message);
        }
    }

    // 异步捕获参数（保留用于元数据的 GameView 尺寸）
    private static int _captureGvW, _captureGvH;

    // ============================================================
    // 辅助方法
    // ============================================================

    private static List<EditorWindow> FindGameViews()
    {
        var result = new List<EditorWindow>();
        try
        {
            if (_gameViewType == null) return result;
            var windows = Resources.FindObjectsOfTypeAll(_gameViewType);
            foreach (var w in windows)
            {
                if (w is EditorWindow ew)
                    result.Add(ew);
            }
        }
        catch { }
        return result;
    }

    private static void TryGetResolution(EditorWindow gv, out int w, out int h)
    {
        w = FALLBACK_WIDTH; h = FALLBACK_HEIGHT;
        try
        {
            if (_currentSizeProp != null)
            {
                var size = _currentSizeProp.GetValue(gv);
                if (size != null && _gameViewSizeType != null)
                {
                    var sw = _sizeWidthProp?.GetValue(size);
                    var sh = _sizeHeightProp?.GetValue(size);
                    if (sw != null && sh != null)
                    {
                        w = (int)sw; h = (int)sh;
                        return;
                    }
                }
            }
        }
        catch { }
    }

    private static int EstimateToolbarHeight()
    {
        // Unity 2022.3: 工具栏约 43px
        // 包含 Game / Display / Resolution / Scale / PlayFocused
        return 43;
    }

    private static void CalcContentRect(int renderY, int renderW, int renderH,
                                         int resW, int resH,
                                         out int cx, out int cy, out int cw, out int ch)
    {
        if (renderW <= 0 || renderH <= 0 || resW <= 0 || resH <= 0)
        {
            cx = 0; cy = renderY; cw = renderW; ch = renderH;
            return;
        }

        float renderRatio = (float)renderW / renderH;
        float targetRatio = (float)resW / resH;

        if (renderRatio > targetRatio)
        {
            // 窗口偏宽：高度限制（上下黑边）
            ch = renderH;
            cw = (int)Math.Round(ch * targetRatio);
            cx = (renderW - cw) / 2;
            cy = renderY;
        }
        else
        {
            // 窗口偏窄：宽度限制（左右黑边）
            cw = renderW;
            ch = (int)Math.Round(cw / targetRatio);
            cx = 0;
            cy = renderY + (renderH - ch) / 2;
        }
    }

    private static Texture2D ScaleTexture(Texture2D source, int targetW, int targetH)
    {
        RenderTexture rt = RenderTexture.GetTemporary(targetW, targetH, 24);
        RenderTexture.active = rt;
        Graphics.Blit(source, rt);

        Texture2D result = new Texture2D(targetW, targetH, TextureFormat.RGBA32, false);
        result.ReadPixels(new Rect(0, 0, targetW, targetH), 0, 0);
        result.Apply();

        RenderTexture.active = null;
        RenderTexture.ReleaseTemporary(rt);
        return result;
    }

    private static string EscapeJson(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n")
                .Replace("\r", "\\r").Replace("\t", "\\t");
    }

    [Serializable]
    private class AutoSmokeCaptureConfig
    {
        public string autosmokeRoot;
    }

    private static string FindOrCreateRunDir(string baseDir, int maxAgeSec)
    {
        try
        {
            if (Directory.Exists(baseDir))
            {
                var dirs = new List<string>(Directory.GetDirectories(baseDir, "run_*"));
                dirs.Sort();
                dirs.Reverse();
                double now = (DateTime.Now - new DateTime(1970, 1, 1)).TotalSeconds;
                foreach (var d in dirs)
                {
                    try
                    {
                        double age = now - new FileInfo(d).LastWriteTime.ToUniversalTime()
                                             .Subtract(new DateTime(1970, 1, 1)).TotalSeconds;
                        if (age < maxAgeSec)
                            return d;
                    }
                    catch { }
                }
            }
            // 没有找到最近的目录，新建一个
            string newDir = Path.Combine(baseDir, "run_" + DateTime.Now.ToString("yyyyMMdd_HHmmss"));
            Directory.CreateDirectory(newDir);
            return newDir;
        }
        catch
        {
            return baseDir;
        }
    }
}
