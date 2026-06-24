/*
 * AutoSmokeUITreeExporter.cs
 * 运行态 UI 树导出器（UI树方案 阶段二）
 *
 * 按《UI树与元素资料完整提取执行方案》第7章要求实现：
 *   - 16 个运行态字段完整采集
 *   - 图标区分 visualNode / clickTargetNode
 *   - 4 个菜单项
 *   - Bridge 定时导出模式
 *
 * 输出路径配置：
 *   优先读取 ~/.autosmoke/config.json 中的 autosmoke_root
 *   若未配置，回退到 ~/.autosmoke/metadata/
 *
 * 菜单：
 *   AutoSmoke > UI > 导出当前 UI 树
 *   AutoSmoke > UI > 导出当前 UI 树(含截图)
 *   AutoSmoke > UI > 启动 UI 树 Bridge
 *   AutoSmoke > UI > 停止 UI 树 Bridge
 */

using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;

[InitializeOnLoad]
public static class AutoSmokeUITreeExporter
{
    private static string _outputDir;
    private static string _outputPath;
    private static string _screenshotDir;

    private const string CONFIG_FILENAME = "config.json";
    private const string AUTOSMOKE_DIR = ".autosmoke";

    // Bridge 模式
    private static bool _bridgeRunning = false;
    private static double _lastExportTime = 0;
    private const double BRIDGE_INTERVAL = 1.0; // 秒

    static AutoSmokeUITreeExporter()
    {
        string userProfile = Environment.GetEnvironmentVariable("USERPROFILE")
                             ?? Environment.GetEnvironmentVariable("HOME") ?? ".";
        string bridgeRoot = Path.Combine(userProfile, AUTOSMOKE_DIR);

        // 读取配置获取 autosmoke_root
        string autosmokeRoot = TryReadAutosmokeRoot(bridgeRoot);
        if (!string.IsNullOrEmpty(autosmokeRoot))
        {
            _outputDir = Path.Combine(autosmokeRoot, "元数据");
            _screenshotDir = Path.Combine(autosmokeRoot, "screenshots");
        }
        else
        {
            // 回退到 bridge 目录
            _outputDir = Path.Combine(bridgeRoot, "metadata");
            _screenshotDir = Path.Combine(bridgeRoot, "screenshots");
        }

        _outputPath = Path.Combine(_outputDir, "current_ui_tree.json");
        try { Directory.CreateDirectory(_outputDir); } catch { }
        try { Directory.CreateDirectory(_screenshotDir); } catch { }

        Debug.Log($"[AutoSmoke] UITreeExporter 输出目录: {_outputDir}");

        EditorApplication.update += OnEditorUpdate;
    }

    /// <summary>
    /// 从 bridge 配置中读取 autosmoke_root
    /// </summary>
    private static string TryReadAutosmokeRoot(string bridgeRoot)
    {
        try
        {
            string cfgPath = Path.Combine(bridgeRoot, CONFIG_FILENAME);
            if (!File.Exists(cfgPath)) return null;

            string json = File.ReadAllText(cfgPath);
            var cfg = JsonUtility.FromJson<AutoSmokeConfig>(json);
            if (cfg != null && !string.IsNullOrEmpty(cfg.autosmokeRoot))
            {
                string root = cfg.autosmokeRoot.Replace("/", "\\");
                if (Directory.Exists(root))
                    return root;
            }
        }
        catch { }
        return null;
    }

    [Serializable]
    private class AutoSmokeConfig
    {
        public string autosmokeRoot;
    }

    // ============================================================
    // 菜单项
    // ============================================================

    [MenuItem("AutoSmoke/数据采集/导出当前 UI 树")]
    private static void ExportUITree()
    {
        EditorUtility.DisplayProgressBar("AutoSmoke", "正在导出 UI 树...", 0);
        try
        {
            var tree = BuildUITree();
            SaveTree(tree);
            EditorUtility.DisplayDialog("AutoSmoke",
                $"UI 树导出完成！\n节点数: {tree.nodes.Count}\n" +
                $"输出: {_outputPath}", "OK");
        }
        finally { EditorUtility.ClearProgressBar(); }
    }

    [MenuItem("AutoSmoke/数据采集/导出当前 UI 树(含截图)")]
    private static void ExportUITreeWithScreenshot()
    {
        EditorUtility.DisplayProgressBar("AutoSmoke", "正在导出 UI 树+截图...", 0);
        try
        {
            var tree = BuildUITree();

            // 截取 GameView
            string ts = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string screenshotPath = Path.Combine(_screenshotDir, $"ui_tree_{ts}.png");
            ScreenCapture.CaptureScreenshot(screenshotPath);
            tree.screenshotPath = screenshotPath;

            SaveTree(tree);
            EditorUtility.DisplayDialog("AutoSmoke",
                $"UI 树+截图导出完成！\n节点数: {tree.nodes.Count}\n" +
                $"截图: {screenshotPath}", "OK");
        }
        finally { EditorUtility.ClearProgressBar(); }
    }

    [MenuItem("AutoSmoke/数据采集/启动 UI 树 Bridge")]
    private static void StartBridge()
    {
        _bridgeRunning = true;
        _lastExportTime = EditorApplication.timeSinceStartup;
        Debug.Log("[AutoSmoke] UI 树 Bridge 已启动 (1s 间隔)");
    }

    [MenuItem("AutoSmoke/数据采集/停止 UI 树 Bridge")]
    private static void StopBridge()
    {
        _bridgeRunning = false;
        Debug.Log("[AutoSmoke] UI 树 Bridge 已停止");
    }

    // ============================================================
    // Editor Update（Bridge 模式定时导出）
    // ============================================================

    private static void OnEditorUpdate()
    {
        if (!_bridgeRunning) return;
        double now = EditorApplication.timeSinceStartup;
        if (now - _lastExportTime < BRIDGE_INTERVAL) return;
        _lastExportTime = now;
        try
        {
            var tree = BuildUITree();
            SaveTree(tree);
        }
        catch { }
    }

    // ============================================================
    // 核心：构建 UI 树
    // ============================================================

    private static UITree BuildUITree()
    {
        int screenW = 1170, screenH = 2532;
        TryGetResolution(out screenW, out screenH);

        var tree = new UITree
        {
            schemaVersion = 1,
            timestamp = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss.fffK"),
            scene = GetActiveSceneName(),
            pageId = DetectPageId(),
            gameResolution = new ResInfo { width = screenW, height = screenH },
            nodes = new List<UINode>(),
            icons = new List<IconInfo>(),
        };

        // 遍历所有 Canvas
        var canvases = GameObject.FindObjectsOfType<Canvas>();
        foreach (var canvas in canvases)
        {
            if (!canvas.gameObject.activeInHierarchy) continue;
            string canvasName = canvas.name;
            int sortingOrder = canvas.sortingOrder;

            ScanCanvasTransform(canvas.transform, "", tree.nodes, tree.icons,
                                screenW, screenH, canvasName, sortingOrder);
        }

        tree.nodeCount = tree.nodes.Count;
        tree.iconCount = tree.icons.Count;
        return tree;
    }

    private static void ScanCanvasTransform(Transform parent, string parentPath,
                                            List<UINode> nodes, List<IconInfo> icons,
                                            int screenW, int screenH,
                                            string canvasName, int sortingOrder)
    {
        for (int i = 0; i < parent.childCount; i++)
        {
            Transform child = parent.GetChild(i);
            GameObject go = child.gameObject;
            RectTransform rt = go.GetComponent<RectTransform>();
            if (rt == null) continue;

            string path = string.IsNullOrEmpty(parentPath)
                ? go.name : parentPath + "/" + go.name;

            var components = go.GetComponents<Component>();
            var compTypes = new List<string>();
            foreach (var c in components)
            {
                if (c != null) compTypes.Add(c.GetType().Name);
            }

            // --- 16 个字段 ---
            string text = ExtractText(go, compTypes);
            var screenRect = CalcScreenRect(rt, screenW, screenH);
            var normRect = CalcNormalizedRect(rt);
            bool visible = CheckVisible(go);
            bool clickable = CheckClickable(go, compTypes);
            bool interactable = CheckInteractable(go, compTypes);
            float cgAlpha = GetCanvasGroupAlpha(go);

            var node = new UINode
            {
                path = path,
                name = go.name,
                activeInHierarchy = go.activeInHierarchy,
                visible = visible,
                interactable = interactable,
                clickable = clickable,
                components = compTypes,
                text = text,
                screenRect = screenRect,
                normalizedRect = normRect,
                canvas = canvasName,
                sortingOrder = sortingOrder,
                siblingIndex = child.GetSiblingIndex(),
                raycastTarget = CheckRaycastTarget(go, compTypes),
                buttonInteractable = CheckButtonInteractable(go),
                canvasGroupAlpha = cgAlpha,
                childCount = child.childCount,
            };
            nodes.Add(node);

            // --- 图标采集 ---
            CollectIconInfo(go, node, path, canvasName, nodes, icons);

            // 递归子节点
            ScanCanvasTransform(child, path, nodes, icons,
                               screenW, screenH, canvasName, sortingOrder);
        }
    }

    // ============================================================
    // 图标采集（visualNode vs clickTargetNode）
    // ============================================================

    private static void CollectIconInfo(GameObject go, UINode node, string path,
                                         string canvasName, List<UINode> nodes,
                                         List<IconInfo> icons)
    {
        Image img = go.GetComponent<Image>();
        RawImage rawImg = go.GetComponent<RawImage>();

        string spriteName = "";
        string atlasName = "";
        bool isIcon = false;

        if (img != null && img.sprite != null)
        {
            spriteName = img.sprite.name;
            if (img.sprite.texture != null)
                atlasName = img.sprite.texture.name;
            isIcon = true;
        }
        if (rawImg != null && rawImg.texture != null)
        {
            spriteName = rawImg.texture.name;
            isIcon = true;
        }

        // 只处理非空图标
        if (!isIcon && string.IsNullOrEmpty(spriteName)) return;
        // 跳过纯装饰性 Image（没有 sprite 的 Image）
        if (!isIcon) return;

        // 检测点击目标节点（通常为父节点）
        string clickTargetPath = "";
        if (IsClickTarget(go.transform.parent))
            clickTargetPath = path.Substring(0, path.LastIndexOf('/')) 
                ?? go.transform.parent.name;
        else
            clickTargetPath = path; // 自身就是点击目标

        string iconType = GuessIconType(spriteName, go.name);

        var iconInfo = new IconInfo
        {
            pageId = canvasName,
            spriteName = spriteName,
            atlasName = atlasName,
            visualNode = path,
            clickTargetNode = clickTargetPath,
            iconType = iconType,
            clickable = node.clickable,
            screenRect = node.screenRect,
        };
        icons.Add(iconInfo);
    }

    private static bool IsClickTarget(Transform t)
    {
        if (t == null) return false;
        GameObject go = t.gameObject;
        var comps = go.GetComponents<Component>();
        foreach (var c in comps)
        {
            if (c == null) continue;
            string tn = c.GetType().Name;
            if (tn == "Button" || tn == "Toggle" || tn == "EventTrigger")
                return true;
            if (c is IPointerClickHandler)
                return true;
        }
        return false;
    }

    // ============================================================
    // 字段辅助方法
    // ============================================================

    private static string ExtractText(GameObject go, List<string> comps)
    {
        var textComp = go.GetComponent<Text>();
        if (textComp != null && !string.IsNullOrEmpty(textComp.text))
            return textComp.text;

        // TMP_Text
        var tmpComp = go.GetComponent("TMPro.TMP_Text");
        if (tmpComp != null)
        {
            var textProp = tmpComp.GetType().GetProperty("text");
            if (textProp != null)
            {
                string t = textProp.GetValue(tmpComp)?.ToString();
                if (!string.IsNullOrEmpty(t)) return t;
            }
        }
        return "";
    }

    private static RectInfo CalcScreenRect(RectTransform rt, int screenW, int screenH)
    {
        var corners = new Vector3[4];
        rt.GetWorldCorners(corners);
        int x = Mathf.RoundToInt(corners[0].x);
        int y = Mathf.RoundToInt(corners[0].y);
        int w = Mathf.RoundToInt(corners[2].x - corners[0].x);
        int h = Mathf.RoundToInt(corners[2].y - corners[0].y);
        return new RectInfo { x = x, y = y, width = w, height = h };
    }

    private static RectInfoF CalcNormalizedRect(RectTransform rt)
    {
        var corners = new Vector3[4];
        rt.GetWorldCorners(corners);
        // 注意：世界坐标可能是屏幕坐标，也可能是 Canvas 空间坐标
        // 此处假设 Canvas 覆盖全屏幕 1170x2532
        float nx = corners[0].x / 1170f;
        float ny = corners[0].y / 2532f;
        float nw = (corners[2].x - corners[0].x) / 1170f;
        float nh = (corners[2].y - corners[0].y) / 2532f;
        return new RectInfoF { x = (float)Math.Round(nx,4), y = (float)Math.Round(ny,4),
                               width = (float)Math.Round(nw,4), height = (float)Math.Round(nh,4) };
    }

    private static bool CheckVisible(GameObject go)
    {
        if (!go.activeInHierarchy) return false;

        // CanvasGroup alpha
        CanvasGroup cg = go.GetComponentInParent<CanvasGroup>();
        if (cg != null && cg.alpha <= 0.01f)
            return false;

        // RectTransform size > 0
        RectTransform rt = go.GetComponent<RectTransform>();
        if (rt != null && (rt.sizeDelta.x <= 0 || rt.sizeDelta.y <= 0))
            return false;

        // Image/Text alpha > 0.01
        var img = go.GetComponent<Image>();
        if (img != null && img.color.a <= 0.01f)
            return false;
        var text = go.GetComponent<Text>();
        if (text != null && text.color.a <= 0.01f)
            return false;

        return true;
    }

    private static bool CheckClickable(GameObject go, List<string> comps)
    {
        if (comps.Contains("Button") || comps.Contains("Toggle")) return true;
        if (comps.Contains("EventTrigger")) return true;
        // IPointerClickHandler
        foreach (var comp in go.GetComponents<Component>())
        {
            if (comp != null && comp is IPointerClickHandler)
                return true;
        }
        return false;
    }

    private static bool CheckInteractable(GameObject go, List<string> comps)
    {
        // interactable 与 clickable 的区别：
        // clickable = 能否点击（组件层面）
        // interactable = 此时能否交互（运行时状态）
        if (!go.activeInHierarchy) return false;
        var button = go.GetComponent<Button>();
        if (button != null) return button.interactable;
        var toggle = go.GetComponent<Toggle>();
        if (toggle != null) return toggle.interactable;
        // 没有 Button/Toggle 时等同 clickable
        return CheckClickable(go, comps);
    }

    private static bool CheckRaycastTarget(GameObject go, List<string> comps)
    {
        var img = go.GetComponent<Image>();
        if (img != null) return img.raycastTarget;
        var rawImg = go.GetComponent<RawImage>();
        if (rawImg != null) return rawImg.raycastTarget;
        var text = go.GetComponent<Text>();
        if (text != null) return text.raycastTarget;
        return false;
    }

    private static bool CheckButtonInteractable(GameObject go)
    {
        var button = go.GetComponent<Selectable>();
        if (button != null) return button.interactable;
        return true;
    }

    private static string InferRoleGuess(string name, string text, List<string> comps)
    {
        string ln = name.ToLower();
        string lt = (text ?? "").ToLower();
        if (ln.Contains("close") || lt.Contains("close") || lt.Contains("\u5173\u95ed")) return "close_button";
        if (ln.Contains("confirm") || lt.Contains("confirm") || lt.Contains("\u786e\u8ba4")) return "confirm_button";
        if (ln.Contains("cancel") || lt.Contains("cancel") || lt.Contains("\u53d6\u6d88")) return "cancel_button";
        if (comps.Contains("Button") || comps.Contains("Toggle"))
        {
            if (ln.Contains("tab")) return "tab_button";
            if (ln.Contains("nav") || ln.Contains("back") || lt.Contains("\u8fd4\u56de")) return "navigation";
            return "primary_action_button";
        }
        if (comps.Contains("InputField") || comps.Contains("TMP_InputField")) return "input";
        if (comps.Contains("Slider")) return "slider";
        if (comps.Contains("Toggle")) return "toggle";
        if (ln.Contains("icon")) return "interactive_icon";
        if (comps.Contains("EventTrigger")) return "action";
        return "unknown";
    }

    private static float GetCanvasGroupAlpha(GameObject go)
    {
        CanvasGroup cg = go.GetComponentInParent<CanvasGroup>();
        if (cg != null) return cg.alpha;
        return 1f;
    }

    private static string GuessIconType(string spriteName, string nodeName)
    {
        string lower = (spriteName + " " + nodeName).ToLower();
        if (lower.Contains("item")) return "item";
        if (lower.Contains("reward")) return "reward";
        if (lower.Contains("building") && lower.Contains("icon")) return "building_icon";
        if (lower.Contains("activity") || lower.Contains("event")) return "activity";
        if (lower.Contains("btn") || lower.Contains("button")) return "button";
        if (lower.Contains("resource")) return "resource";
        if (lower.Contains("tips") || lower.Contains("hint")) return "tips_icon";
        if (lower.Contains("icon")) return "unknown_icon";
        return "unknown";
    }

    // ============================================================
    // 辅助
    // ============================================================

    private static void TryGetResolution(out int w, out int h)
    {
        w = 1170; h = 2532;
        try
        {
            var asm = typeof(EditorWindow).Assembly;
            var gvType = asm.GetType("UnityEditor.GameView");
            if (gvType == null) return;
            var sizeProp = gvType.GetProperty("currentGameViewSize",
                BindingFlags.NonPublic | BindingFlags.Instance);
            var windows = Resources.FindObjectsOfTypeAll(gvType);
            if (windows.Length == 0) return;
            var size = sizeProp?.GetValue(windows[0]);
            if (size == null) return;
            var sizeType = asm.GetType("UnityEditor.GameViewSize");
            var wp = sizeType?.GetProperty("width");
            var hp = sizeType?.GetProperty("height");
            if (wp != null && hp != null)
            {
                w = (int)wp.GetValue(size);
                h = (int)hp.GetValue(size);
            }
        }
        catch { }
    }

    private static string GetActiveSceneName()
    {
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        return scene.IsValid() ? scene.name : "Unknown";
    }

    private static string DetectPageId()
    {
        // 从 Canvas 名称推断页面 ID
        var canvases = GameObject.FindObjectsOfType<Canvas>();
        foreach (var c in canvases)
        {
            string name = c.name;
            if (name.Contains("Panel") || name.Contains("Dialog") ||
                name.Contains("Popup") || name.Contains("Window"))
                return name;
        }
        return "MainCanvas";
    }

    private static void SaveTree(UITree tree)
    {
        string json = JsonUtility.ToJson(tree, true);
        File.WriteAllText(_outputPath, json);
    }

    // ============================================================
    // 数据类
    // ============================================================

    [Serializable]
    private class UITree
    {
        public int schemaVersion;
        public string timestamp;
        public string scene;
        public string pageId;
        public ResInfo gameResolution;
        // 运行时路径（不序列化，仅标记）
        public List<UINode> nodes = new List<UINode>();
        public List<IconInfo> icons = new List<IconInfo>();
        public int nodeCount;
        public int iconCount;
        public string screenshotPath;
    }

    [Serializable]
    private class ResInfo
    {
        public int width;
        public int height;
    }

    [Serializable]
    private class RectInfo
    {
        public int x;
        public int y;
        public int width;
        public int height;
    }

    [Serializable]
    private class RectInfoF
    {
        public float x;
        public float y;
        public float width;
        public float height;
    }

    [Serializable]
    private class UINode
    {
        // 16+ 个字段（方案第7.2节）
        public string path;
        public string name;
        public bool activeInHierarchy;
        public bool visible;
        public bool interactable;
        public bool clickable;
        public List<string> components;
        public string text;
        public RectInfo screenRect;       // 方案格式 {x,y,width,height}
        public RectInfoF normalizedRect;  // 方案格式 {x,y,width,height}
        public string canvas;
        public int sortingOrder;
        public int siblingIndex;
        public bool raycastTarget;
        public bool buttonInteractable;
        public float canvasGroupAlpha;
        public int childCount;
        public string roleGuess;          // 方案新增：角色推断
        public RectInfo gameContentRect;  // 方案新增：GameContent 坐标
    }

    [Serializable]
    private class IconInfo
    {
        public string pageId;             // 所属页面
        public string spriteName;         // Sprite 名
        public string atlasName;          // Atlas/Texture 名
        public string visualNode;         // 显示图标的节点路径
        public string clickTargetNode;    // 实际接收点击的节点路径
        public string iconType;           // 图标类型
        public bool clickable;            // 是否可点击
        public RectInfo screenRect;       // 屏幕坐标
    }
}
