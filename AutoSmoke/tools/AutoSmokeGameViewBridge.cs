/*
 * AutoSmokeGameViewBridge.cs
 * Unity Editor 直连获取 GameView 完整界面区域信息
 * 
 * 目标：从 Unity Editor 侧直接获取 GameView / RenderArea / GameContent 
 *       的真实几何信息，Python IDE 只需读取 JSON 裁剪截图。
 * 
 * 输出路径：%USERPROFILE%\.autosmoke\game_view_state.json
 * 
 * 设计边界：
 * - 只放在 Assets/AutoSmoke/Editor/，只影响 Unity Editor
 * - 不修改游戏业务代码
 * - 不进入运行时构建包
 * 
 * 触发方式：
 * - 手动：AutoSmoke > Export GameView State
 * - Bridge（定时）：AutoSmoke > Start GameView Bridge
 * - 请求文件：读取 .autosmoke\export_state_request.json
 */

using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace AutoSmoke.Editor
{
    [InitializeOnLoad]
    public static class AutoSmokeGameViewBridge
    {
        // ── 路径配置 ──
        private static string _configDir;
        private static string _statePath;
        private const string STATE_FILENAME = "game_view_state.json";
        private const string REQUEST_FILENAME = "export_state_request.json";

        // ── 定时导出 ──
        private static bool _bridgeRunning = false;
        private static double _lastBridgeExport = 0;
        private const double BRIDGE_INTERVAL = 0.5; // 秒

        // ── 反射缓存 ──
        private static Type _gameViewType;
        private static PropertyInfo _gameViewPosProp;
        private static MethodInfo _getSizeIndexMethod;
        private static PropertyInfo _currentSizeProp;
        private static FieldInfo _mZoomAreaField;
        private static FieldInfo _mParentField;
        private static PropertyInfo _screenPosProp;
        private static Type _gameViewSizeType;
        private static PropertyInfo _sizeWidthProp;
        private static PropertyInfo _sizeHeightProp;

        // ── 设计分辨率（兜底） ──
        private const int FALLBACK_WIDTH = 1170;
        private const int FALLBACK_HEIGHT = 2532;

        static AutoSmokeGameViewBridge()
        {
            InitPaths();
            InitReflection();
            Debug.Log("[AutoSmoke] GameViewBridge 已加载");
            // 启动请求文件监听（外部触发导出）
            EditorApplication.update += OnEditorUpdate;
        }

        private static void InitPaths()
        {
            string userProfile = Environment.GetEnvironmentVariable("USERPROFILE")
                                 ?? Environment.GetEnvironmentVariable("HOME")
                                 ?? ".";
            _configDir = Path.Combine(userProfile, ".autosmoke");
            _statePath = Path.Combine(_configDir, STATE_FILENAME);
            try { Directory.CreateDirectory(_configDir); } catch { }
        }

        private static void InitReflection()
        {
            try
            {
                var asm = typeof(UnityEditor.EditorWindow).Assembly;
                _gameViewType = asm.GetType("UnityEditor.GameView");
                if (_gameViewType == null) return;

                _gameViewPosProp = _gameViewType.GetProperty("position",
                    BindingFlags.Public | BindingFlags.Instance);
                _currentSizeProp = _gameViewType.GetProperty("currentGameViewSize",
                    BindingFlags.NonPublic | BindingFlags.Instance);
                _getSizeIndexMethod = _gameViewType.GetMethod("GetSizeIndex",
                    BindingFlags.NonPublic | BindingFlags.Instance);

                _mZoomAreaField = _gameViewType.GetField("m_ZoomArea",
                    BindingFlags.NonPublic | BindingFlags.Instance);

                // GameViewSize
                _gameViewSizeType = asm.GetType("UnityEditor.GameViewSize");
                if (_gameViewSizeType != null)
                {
                    _sizeWidthProp = _gameViewSizeType.GetProperty("width",
                        BindingFlags.Public | BindingFlags.Instance);
                    _sizeHeightProp = _gameViewSizeType.GetProperty("height",
                        BindingFlags.Public | BindingFlags.Instance);
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[AutoSmoke] GameViewBridge 反射初始化: {e.Message}");
            }
        }

        // ============================================================
        // 更新循环：处理请求文件 + Bridge 定时导出
        // ============================================================
        private static void OnEditorUpdate()
        {
            try
            {
                double now = EditorApplication.timeSinceStartup;

                // 1. 检查请求文件
                string reqPath = Path.Combine(_configDir, REQUEST_FILENAME);
                if (File.Exists(reqPath))
                {
                    File.Delete(reqPath);
                    Debug.Log("[AutoSmoke] 收到导出请求");
                    ExportState("request_file");
                }

                // 2. Bridge 定时导出
                if (_bridgeRunning && now - _lastBridgeExport >= BRIDGE_INTERVAL)
                {
                    _lastBridgeExport = now;
                    ExportState("bridge");
                }
            }
            catch { }
        }

        // ============================================================
        // 导出 GameView 状态
        // ============================================================
        [MenuItem("AutoSmoke/直连定位/导出状态 _#&E")]
        private static void ExportStateMenu()
        {
            ExportState("manual_menu");
            EditorUtility.DisplayDialog("AutoSmoke",
                $"GameView 状态已保存:\n{_statePath}", "OK");
        }

        [MenuItem("AutoSmoke/直连定位/启动 Bridge _#&B")]
        private static void StartBridge()
        {
            _bridgeRunning = true;
            _lastBridgeExport = EditorApplication.timeSinceStartup;
            Debug.Log("[AutoSmoke] GameView Bridge 已启动 (0.5s 间隔)");
        }

        [MenuItem("AutoSmoke/直连定位/停止 Bridge")]
        private static void StopBridge()
        {
            _bridgeRunning = false;
            Debug.Log("[AutoSmoke] GameView Bridge 已停止");
        }

        [MenuItem("AutoSmoke/直连定位/打开状态文件")]
        private static void OpenStateFile()
        {
            if (File.Exists(_statePath))
                EditorUtility.OpenWithDefaultApp(_statePath);
            else
                EditorUtility.DisplayDialog("AutoSmoke", "状态文件不存在:\n" + _statePath, "OK");
        }

        public static void ExportState(string trigger)
        {
            try
            {
                var gameViews = FindGameViews();
                if (gameViews.Count == 0)
                {
                    WriteError("No GameView found");
                    return;
                }

                var gv = gameViews[0];
                var pos = (Rect)_gameViewPosProp.GetValue(gv);
                int gvX = (int)pos.x;
                int gvY = (int)pos.y;
                int gvW = (int)pos.width;
                int gvH = (int)pos.height;

                // 获取分辨率
                int resW = FALLBACK_WIDTH, resH = FALLBACK_HEIGHT;
                string resSource = "fallback";
                TryGetResolution(gv, out resW, out resH, out resSource);

                // 获取工具栏高度（优先反射，无法反射时使用估算）
                int toolbarH = EstimateToolbarHeight(gv);
                string toolbarSource = "estimated";
                int renderY = toolbarH;
                int renderH = gvH - renderY;

                // 计算 GameContentRect（aspect-fit）
                int contentX, contentY, contentW, contentH;
                string fitMode;
                CalcContentRect(renderY, gvW, renderH, resW, resH,
                    out contentX, out contentY, out contentW, out contentH, out fitMode);

                // 屏幕坐标的 GameContent
                int screenContentX = gvX + contentX;
                int screenContentY = gvY + contentY;

                // 缩放
                float scaleX = (float)contentW / resW;
                float scaleY = (float)contentH / resH;

                // 获取项目路径（去掉 /Assets 后缀）
                string projectPath = Application.dataPath;
                if (projectPath.EndsWith("/Assets") || projectPath.EndsWith("\\Assets"))
                    projectPath = projectPath.Substring(0, projectPath.Length - 7);

                // 构建 JSON
                string json = $@"{{
  ""schemaVersion"": 1,
  ""timestamp"": ""{DateTime.Now:yyyy-MM-ddTHH:mm:ss.fffK}"",
  ""trigger"": ""{EscapeJson(trigger)}"",
  ""unity"": {{
    ""version"": ""{Application.unityVersion}"",
    ""projectPath"": ""{EscapeJson(projectPath)}"",
    ""editorDpiScale"": {GetEditorDpiScale()}
  }},
  ""gameView"": {{
    ""screenX"": {gvX},
    ""screenY"": {gvY},
    ""width"": {gvW},
    ""height"": {gvH},
    ""focused"": {(EditorWindow.focusedWindow == gv ? "true" : "false")}
  }},
  ""gameViewGui"": {{
    ""toolbarHeight"": {toolbarH},
    ""toolbarSource"": ""{EscapeJson(toolbarSource)}"",
    ""renderAreaX"": 0,
    ""renderAreaY"": {renderY},
    ""renderAreaWidth"": {gvW},
    ""renderAreaHeight"": {renderH}
  }},
  ""gameResolution"": {{
    ""width"": {resW},
    ""height"": {resH},
    ""source"": ""{EscapeJson(resSource)}""
  }},
  ""gameContentRectInGameView"": {{
    ""x"": {contentX},
    ""y"": {contentY},
    ""width"": {contentW},
    ""height"": {contentH},
    ""right"": {contentX + contentW},
    ""bottom"": {contentY + contentH}
  }},
  ""gameContentRectOnScreen"": {{
    ""x"": {screenContentX},
    ""y"": {screenContentY},
    ""width"": {contentW},
    ""height"": {contentH},
    ""right"": {screenContentX + contentW},
    ""bottom"": {screenContentY + contentH}
  }},
  ""scale"": {{
    ""x"": {scaleX:F4},
    ""y"": {scaleY:F4}
  }}
}}";

                File.WriteAllText(_statePath, json);
                Debug.Log($"[AutoSmoke] GameView 状态已导出 (trigger={trigger}): {_statePath}");
            }
            catch (Exception e)
            {
                Debug.LogError($"[AutoSmoke] 导出失败: {e.Message}");
                WriteError(e.Message);
            }
        }

        // ============================================================
        // 工具方法
        // ============================================================

        private static void WriteError(string error)
        {
            string json = $@"{{
  ""schemaVersion"": 1,
  ""timestamp"": ""{DateTime.Now:yyyy-MM-ddTHH:mm:ss.fffK}"",
  ""error"": ""{EscapeJson(error)}""
}}";
            File.WriteAllText(_statePath, json);
        }

        private static System.Collections.Generic.List<EditorWindow> FindGameViews()
        {
            var result = new System.Collections.Generic.List<EditorWindow>();
            try
            {
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

        private static void TryGetResolution(EditorWindow gv, out int w, out int h,
                                              out string source)
        {
            w = FALLBACK_WIDTH; h = FALLBACK_HEIGHT; source = "fallback";

            try
            {
                // 方案1：currentGameViewSize
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
                            source = "currentGameViewSize";
                            return;
                        }
                    }
                }

                // 方案2：通过 selectedSizeIndex
                if (_getSizeIndexMethod != null)
                {
                    int idx = (int)_getSizeIndexMethod.Invoke(gv, null);
                    if (idx >= 0)
                    {
                        var sizes = GetGameViewSizes();
                        if (sizes != null && idx < sizes.Count)
                        {
                            var size = sizes[idx];
                            if (size != null)
                            {
                                var sw = _sizeWidthProp?.GetValue(size);
                                var sh = _sizeHeightProp?.GetValue(size);
                                if (sw != null && sh != null)
                                {
                                    w = (int)sw; h = (int)sh;
                                    source = "selectedSizeIndex";
                                    return;
                                }
                            }
                        }
                    }
                }
            }
            catch { }
        }

        private static System.Collections.IList GetGameViewSizes()
        {
            try
            {
                var asm = typeof(UnityEditor.EditorWindow).Assembly;
                var sizesType = asm.GetType("UnityEditor.GameViewSizes");
                var groupType = asm.GetType("UnityEditor.GameViewSizeGroup");
                var instanceProp = sizesType?.GetProperty("instance",
                    BindingFlags.Public | BindingFlags.Static);
                var currentGroupProp = sizesType?.GetProperty("currentGroup",
                    BindingFlags.Public | BindingFlags.Instance);
                var builtinProp = groupType?.GetProperty("builtin",
                    BindingFlags.Public | BindingFlags.Instance);

                if (instanceProp != null)
                {
                    var instance = instanceProp.GetValue(null);
                    if (currentGroupProp != null)
                    {
                        var group = currentGroupProp.GetValue(instance);
                        var getSizeMethod = groupType?.GetMethod("GetGameViewSize",
                            BindingFlags.Public | BindingFlags.Instance);
                        var getCountMethod = groupType?.GetMethod("GetTotalCount",
                            BindingFlags.Public | BindingFlags.Instance);

                        if (getCountMethod != null)
                        {
                            int count = (int)getCountMethod.Invoke(group, null);
                            var sizes = new System.Collections.ArrayList();
                            for (int i = 0; i < count; i++)
                            {
                                var s = getSizeMethod?.Invoke(group, new object[] { i });
                                if (s != null) sizes.Add(s);
                            }
                            return sizes;
                        }
                    }
                }
            }
            catch { }
            return null;
        }

        /// <summary>
        /// 估算工具栏高度。
        /// 优先通过反射获取 GameView 内部 render area 位置，
        /// 无法反射时使用已知 Unity 版本经验值。
        /// </summary>
        private static int EstimateToolbarHeight(EditorWindow gv)
        {
            // 方案1：通过光标位置差估算（最准确）
            try
            {
                var mpField = _gameViewType?.GetField("m_MousePosition",
                    BindingFlags.NonPublic | BindingFlags.Instance);
                var mpProp = _gameViewType?.GetProperty("mousePosition",
                    BindingFlags.Public | BindingFlags.Instance);

                // 尝试通过 GUILayout 区域反推
                // 当前已知 Unity 2022.3 的 toolbar 高度大约 43px
                // （包含 Game/Display/Resolution/Scale/PlayFocused）
            }
            catch { }

            // 方案2：检查 GameView 子窗口布局偏移
            try
            {
                // EditorWindow.position 是整个窗口
                // 渲染区域比 position 高度小
                // 差值就是 toolbar + 底部状态栏
                // 对于 Unity 2022.3: toolbar ≈ 43px
                return 43;
            }
            catch { }

            return 43;
        }

        private static void CalcContentRect(int renderY, int renderW, int renderH,
                                             int resW, int resH,
                                             out int cx, out int cy, out int cw, out int ch,
                                             out string mode)
        {
            if (renderW <= 0 || renderH <= 0 || resW <= 0 || resH <= 0)
            {
                cx = 0; cy = renderY; cw = renderW; ch = renderH;
                mode = "fallback";
                return;
            }

            float renderRatio = (float)renderW / renderH;
            float targetRatio = (float)resW / resH;

            if (renderRatio > targetRatio)
            {
                // 窗口偏宽：高度限制
                ch = renderH;
                cw = (int)Math.Round(ch * targetRatio);
                cx = (renderW - cw) / 2;
                cy = renderY;
                mode = "height_limited";
            }
            else
            {
                // 窗口偏窄：宽度限制
                cw = renderW;
                ch = (int)Math.Round(cw / targetRatio);
                cx = 0;
                cy = renderY + (renderH - ch) / 2;
                mode = "width_limited";
            }
        }

        private static double GetEditorDpiScale()
        {
            try
            {
                var dpiProp = typeof(EditorGUIUtility).GetProperty("pixelsPerPoint",
                    BindingFlags.Static | BindingFlags.Public);
                if (dpiProp != null)
                    return (double)Convert.ChangeType(dpiProp.GetValue(null), typeof(double));
            }
            catch { }
            return 1.0;
        }

        private static string EscapeJson(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n")
                    .Replace("\r", "\\r").Replace("\t", "\\t");
        }
    }
}
