using System;
using System.IO;
using System.Collections.Generic;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using TMPro;
using System.Linq;
using System.Reflection;

/// <summary>
/// AutoSmoke - Unity Editor 辅助脚本：可测试性元数据只读导出
/// 
/// 不修改游戏业务逻辑，只在 Unity Editor 中运行。
/// 扫描当前 Canvas / UI 对象，推断 clickable / type / screenRect，
/// 输出结构化元数据到 .autosmoke 目录。
/// 
/// 设计边界：
/// - 允许新增 Assets/Editor/AutoSmokeMetadataExporter.cs
/// - 只在 Unity Editor 中运行
/// - 不进入正式构建包
/// - 不修改游戏业务逻辑
/// - 不修改按钮/界面运行过程代码
/// 
/// 使用方式：
/// 1. 将本脚本放到 Unity 项目的 Assets/Editor/ 目录
/// 2. Unity 编译完成后自动启动，定时导出
/// 3. 菜单手动触发：AutoSmoke > Export Metadata
/// 4. Python 端读取 metadata/current_ui.json
/// 
/// 输出文件（%USERPROFILE%\.autosmoke\metadata\）：
///   current_ui.json      — UI 元素元数据列表
///   current_state.json   — 当前页面/场景/弹窗状态
///   export_log.txt       — 导出日志
/// </summary>
[InitializeOnLoad]
public static class AutoSmokeMetadataExporter
{
    // ============================================================
    // 配置
    // ============================================================
    private static string _configDir;
    private static string _metadataDir;
    private static string _uiJsonPath;
    private static string _stateJsonPath;
    private static string _logPath;
    private static double _lastExportTime = 0;
    private const double EXPORT_INTERVAL = 3.0; // 自动导出间隔（秒）
    private const double MIN_CLICK_INTERVAL = 0.5; // 点击后快速导出间隔

    private static bool _initialized = false;
    private static readonly Encoding _utf8NoBom = new UTF8Encoding(false);

    // 设计分辨率（从 GameViewLocator 一致）
    private static int _designWidth = 1170;
    private static int _designHeight = 2532;

    static AutoSmokeMetadataExporter()
    {
        // 初始化路径
        string userProfile = Environment.GetEnvironmentVariable("USERPROFILE")
                            ?? Environment.GetEnvironmentVariable("HOME")
                            ?? ".";
        _configDir = Path.Combine(userProfile, ".autosmoke");
        _metadataDir = Path.Combine(_configDir, "metadata");
        _uiJsonPath = Path.Combine(_metadataDir, "current_ui.json");
        _stateJsonPath = Path.Combine(_metadataDir, "current_state.json");
        _logPath = Path.Combine(_metadataDir, "export_log.txt");

        try
        {
            Directory.CreateDirectory(_metadataDir);
        }
        catch (Exception ex)
        {
            Debug.LogError($"[AutoSmoke] MetadataExporter 创建目录失败: {ex.Message}");
            return;
        }

        // 注册编辑器更新循环
        EditorApplication.update += OnEditorUpdate;
        AssemblyReloadEvents.afterAssemblyReload += OnAfterAssemblyReload;

        _initialized = true;
        Log("MetadataExporter 已启动，输出: " + _metadataDir);

        // 首次延迟导出（等待场景完全加载）
        EditorApplication.delayCall += () =>
        {
            EditorApplication.delayCall += () =>
            {
                ExportMetadata("startup");
            };
        };
    }

    // ============================================================
    // 菜单项
    // ============================================================
    [MenuItem("AutoSmoke/数据采集/导出元数据", false, 110)]
    private static void MenuExportMetadata()
    {
        ExportMetadata("manual");
        Debug.Log($"[AutoSmoke] 元数据已手动导出到: {_metadataDir}");
    }

    [MenuItem("AutoSmoke/数据采集/导出元数据(详细)", false, 111)]
    private static void MenuExportVerbose()
    {
        var result = ScanUI(verbose: true);
        string path = Path.Combine(_metadataDir, $"ui_verbose_{DateTime.Now:yyyyMMdd_HHmmss}.json");
        File.WriteAllText(path, result, _utf8NoBom);
        Debug.Log($"[AutoSmoke] 详细元数据已导出: {path} ({result.Length} chars)");
    }

    // ============================================================
    // Editor Update 循环
    // ============================================================
    private static void OnEditorUpdate()
    {
        if (!_initialized) return;

        double now = EditorApplication.timeSinceStartup;

        // 检测是否有 click_request.json 刚被处理（说明发生了点击）
        bool recentClick = CheckRecentClick();

        // 定时导出或点击后快速导出
        double interval = recentClick ? MIN_CLICK_INTERVAL : EXPORT_INTERVAL;
        if (now - _lastExportTime < interval)
            return;

        _lastExportTime = now;
        ExportMetadata("timer");
    }

    private static void OnAfterAssemblyReload()
    {
        // 编译完成后延迟导出
        EditorApplication.delayCall += () =>
        {
            ExportMetadata("reload");
        };
    }

    // ============================================================
    // 主导出函数
    // ============================================================
    private static void ExportMetadata(string trigger)
    {
        try
        {
            // 仅在 Play Mode 或 Editor 正常状态下导出
            if (EditorApplication.isCompiling || EditorApplication.isUpdating)
                return;

            // 导出 UI 元数据
            string uiJson = ScanUI(verbose: false);
            File.WriteAllText(_uiJsonPath, uiJson, _utf8NoBom);

            // 导出状态元数据
            string stateJson = ScanState();
            File.WriteAllText(_stateJsonPath, stateJson, _utf8NoBom);

            // 导出场景对象元数据（建筑/资源等）
            string sceneJsonPath = Path.Combine(_metadataDir, "current_scene.json");
            string sceneJson = ScanSceneObjects();
            File.WriteAllText(sceneJsonPath, sceneJson, _utf8NoBom);

            Log($"元数据导出完成 (trigger={trigger}) UI={uiJson.Length}bytes State={stateJson.Length}bytes Scene={sceneJson.Length}bytes");
        }
        catch (Exception ex)
        {
            Log($"导出失败: {ex.Message}");
            Debug.LogWarning($"[AutoSmoke] MetadataExporter 导出异常: {ex.Message}");
        }
    }

    // ============================================================
    // UI 扫描
    // ============================================================
    private static string ScanUI(bool verbose)
    {
        var elements = new List<Dictionary<string, object>>();
        string currentPageId = "unknown";
        float currentSortingOrder = 0;

        // 获取当前屏幕分辨率用于坐标转换
        int screenW = Screen.width;
        int screenH = Screen.height;

        // 扫描所有活跃的 Canvas
        Canvas[] canvases = GameObject.FindObjectsOfType<Canvas>();
        foreach (var canvas in canvases)
        {
            if (!canvas.gameObject.activeInHierarchy) continue;

            // 确定当前页面 ID
            string canvasName = canvas.gameObject.name;
            int sortingOrder = canvas.sortingOrder;
            if (sortingOrder > currentSortingOrder && canvasName != "OverlayUI")
            {
                currentSortingOrder = sortingOrder;
                currentPageId = InferPageId(canvas.gameObject);
            }

            // 递归扫描子节点
            ScanTransform(canvas.transform, elements, screenW, screenH,
                         canvasName, "", verbose);
        }

        // 如果没有活跃 Canvas，尝试从 EventSystem 扫描
        if (elements.Count == 0)
        {
            EventSystem es = GameObject.FindObjectOfType<EventSystem>();
            if (es != null)
            {
                // 扫描 StandaloneInputModule 等
            }
        }

        // 格式化输出
        var output = new Dictionary<string, object>
        {
            ["exportTime"] = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
            ["gameResolution"] = new int[] { _designWidth, _designHeight },
            ["screenResolution"] = new int[] { screenW, screenH },
            ["totalElements"] = elements.Count,
            ["currentPageId"] = currentPageId,
            ["elements"] = elements,
        };

        return JsonEncode(output);
    }

    private static void ScanTransform(Transform parent, List<Dictionary<string, object>> elements,
                                       int screenW, int screenH,
                                       string canvasName, string parentPath, bool verbose)
    {
        for (int i = 0; i < parent.childCount; i++)
        {
            Transform child = parent.GetChild(i);
            GameObject go = child.gameObject;

            // 跳过隐藏对象
            if (!go.activeInHierarchy) continue;

            string path = string.IsNullOrEmpty(parentPath)
                ? go.name
                : parentPath + "/" + go.name;

            // 获取 RectTransform
            RectTransform rt = go.GetComponent<RectTransform>();
            if (rt == null) continue;

            // ---- 收集元数据 ----
            var meta = new Dictionary<string, object>
            {
                ["name"] = go.name,
                ["path"] = path,
                ["canvas"] = canvasName,
            };

            // testId：从 AutoSmokeNode 组件读取（如果存在）
            var autoSmokeNode = go.GetComponent<MonoBehaviour>() as dynamic;
            // 通过反射查找 AutoSmokeNode 组件
            var nodeComp = FindAutoSmokeNodeComponent(go);
            if (nodeComp != null)
            {
                string testId = GetComponentField(nodeComp, "testId") as string;
                string pageId = GetComponentField(nodeComp, "pageId") as string;
                string nodeType = GetComponentField(nodeComp, "nodeType") as string;
                bool? clickable = GetComponentField(nodeComp, "clickable") as bool?;
                bool? dangerous = GetComponentField(nodeComp, "dangerous") as bool?;

                if (!string.IsNullOrEmpty(testId)) meta["testId"] = testId;
                if (!string.IsNullOrEmpty(pageId)) meta["autoSmokePageId"] = pageId;
                if (!string.IsNullOrEmpty(nodeType)) meta["autoSmokeType"] = nodeType;
                if (clickable.HasValue) meta["autoSmokeClickable"] = clickable.Value;
                if (dangerous.HasValue) meta["dangerous"] = dangerous.Value;
            }

            // screenRect（设计坐标）
            int[] screenRect = CalcScreenRect(rt, screenW, screenH);
            if (screenRect != null)
                meta["screenRect"] = screenRect;

            // normalizedRect
            float[] normRect = CalcNormalizedRect(rt, screenW, screenH);
            if (normRect != null)
                meta["normalizedRect"] = normRect;

            // 组件列表
            Component[] allComponents = go.GetComponents<Component>();
            var componentNames = new List<string>();
            foreach (var comp in allComponents)
            {
                if (comp != null)
                    componentNames.Add(comp.GetType().Name);
            }
            meta["components"] = componentNames;
            meta["componentCount"] = allComponents.Length;

            // 推断 type
            string inferredType = InferType(go, componentNames);
            meta["type"] = inferredType;

            // 推断 clickable
            ClickableInfo clickInfo = InferClickable(go, componentNames);
            meta["clickable"] = clickInfo.clickable;
            if (clickInfo.clickable)
            {
                meta["clickableReason"] = clickInfo.reason;
                if (clickInfo.interactable.HasValue)
                    meta["interactable"] = clickInfo.interactable.Value;
            }

            // visible 判断
            meta["visible"] = IsVisible(go);

            // 文本内容
            string textContent = ExtractTextContent(go, componentNames);
            if (!string.IsNullOrEmpty(textContent))
                meta["text"] = textContent;

            // 子元素数量
            meta["childCount"] = child.childCount;

            // siblingIndex（同级排序）
            meta["siblingIndex"] = child.GetSiblingIndex();

            // sortingOrder：从当前/父级 Canvas 获取
            Canvas parentCanvas = go.GetComponentInParent<Canvas>();
            if (parentCanvas != null)
                meta["sortingOrder"] = parentCanvas.sortingOrder;

            // canvasGroupAlpha：从当前或父级 CanvasGroup 获取
            CanvasGroup canvasGroup = go.GetComponentInParent<CanvasGroup>();
            if (canvasGroup != null)
                meta["canvasGroupAlpha"] = (double)canvasGroup.alpha;
            else
                meta["canvasGroupAlpha"] = 1.0;

            // 图标信息（Image 组件）
            Image imgComp = go.GetComponent<Image>();
            if (imgComp != null && imgComp.sprite != null)
            {
                meta["spriteName"] = imgComp.sprite.name;
                meta["raycastTarget"] = imgComp.raycastTarget;
                meta["iconType"] = GuessIconType(imgComp.sprite.name, go.name);
                // 尝试获取 atlas/texture 名
                if (imgComp.sprite.texture != null)
                    meta["atlasName"] = imgComp.sprite.texture.name;
            }
            RawImage rawImg = go.GetComponent<RawImage>();
            if (rawImg != null && rawImg.texture != null)
            {
                meta["rawTextureName"] = rawImg.texture.name;
                meta["raycastTarget"] = rawImg.raycastTarget;
            }

            // depth（层级深度）
            int depth = path.Count(c => c == '/');
            meta["depth"] = depth;

            // 详细模式：额外信息
            if (verbose)
            {
                // 位置和尺寸
                meta["localPosition"] = new float[]
                {
                    (float)Math.Round(rt.localPosition.x, 1),
                    (float)Math.Round(rt.localPosition.y, 1),
                    (float)Math.Round(rt.localPosition.z, 1),
                };
                meta["sizeDelta"] = new float[]
                {
                    (float)Math.Round(rt.sizeDelta.x, 1),
                    (float)Math.Round(rt.sizeDelta.y, 1),
                };
                meta["anchorMin"] = new float[]
                {
                    (float)Math.Round(rt.anchorMin.x, 4),
                    (float)Math.Round(rt.anchorMin.y, 4),
                };
                meta["anchorMax"] = new float[]
                {
                    (float)Math.Round(rt.anchorMax.x, 4),
                    (float)Math.Round(rt.anchorMax.y, 4),
                };
                meta["pivot"] = new float[]
                {
                    (float)Math.Round(rt.pivot.x, 4),
                    (float)Math.Round(rt.pivot.y, 4),
                };

                // sorting layer
                Canvas canvasComp = go.GetComponent<Canvas>();
                if (canvasComp != null)
                {
                    meta["sortingOrder"] = canvasComp.sortingOrder;
                    meta["sortingLayer"] = canvasComp.sortingLayerName;
                }
            }

            elements.Add(meta);

            // 递归子节点
            if (child.childCount > 0)
            {
                ScanTransform(child, elements, screenW, screenH,
                            canvasName, path, verbose);
            }
        }
    }

    // ============================================================
    // screenRect 计算
    // ============================================================
    private static int[] CalcScreenRect(RectTransform rt, int screenW, int screenH)
    {
        if (rt == null) return null;

        try
        {
            // 获取世界坐标的四个角
            Vector3[] corners = new Vector3[4];
            rt.GetWorldCorners(corners);

            // 转为屏幕坐标
            Vector2 min = RectTransformUtility.WorldToScreenPoint(null, corners[0]);
            Vector2 max = RectTransformUtility.WorldToScreenPoint(null, corners[2]);

            // Unity 屏幕原点左下角，UI 原点左上角，需翻转 Y
            float screenYMin = screenH - max.y;
            float screenYMax = screenH - min.y;

            // 缩放到设计分辨率
            float scaleX = (float)_designWidth / screenW;
            float scaleY = (float)_designHeight / screenH;

            int dx1 = Mathf.RoundToInt(min.x * scaleX);
            int dy1 = Mathf.RoundToInt(screenYMin * scaleY);
            int dx2 = Mathf.RoundToInt(max.x * scaleX);
            int dy2 = Mathf.RoundToInt(screenYMax * scaleY);

            // 防止负尺寸
            if (dx2 - dx1 <= 0 || dy2 - dy1 <= 0)
                return null;

            return new int[] { dx1, dy1, dx2, dy2 };
        }
        catch (Exception)
        {
            return null;
        }
    }

    private static float[] CalcNormalizedRect(RectTransform rt, int screenW, int screenH)
    {
        int[] screenRect = CalcScreenRect(rt, screenW, screenH);
        if (screenRect == null) return null;

        float nx = (float)screenRect[0] / _designWidth;
        float ny = (float)screenRect[1] / _designHeight;
        float nw = (float)(screenRect[2] - screenRect[0]) / _designWidth;
        float nh = (float)(screenRect[3] - screenRect[1]) / _designHeight;

        return new float[]
        {
            (float)Math.Round(nx, 4),
            (float)Math.Round(ny, 4),
            (float)Math.Round(nw, 4),
            (float)Math.Round(nh, 4),
        };
    }

    // ============================================================
    // type 推断
    // ============================================================
    private static string InferType(GameObject go, List<string> components)
    {
        // 1. 显式标注
        var nodeComp = FindAutoSmokeNodeComponent(go);
        if (nodeComp != null)
        {
            string nodeType = GetComponentField(nodeComp, "nodeType") as string;
            if (!string.IsNullOrEmpty(nodeType))
                return nodeType;
        }

        // 2. 标准组件推断
        if (components.Contains("Button")) return "Button";
        if (components.Contains("Toggle")) return "Toggle";
        if (components.Contains("TMP_InputField") || components.Contains("InputField")) return "Input";
        if (components.Contains("Slider")) return "Slider";
        if (components.Contains("ScrollRect")) return "ScrollView";
        if (components.Contains("TMP_Text") || components.Contains("Text")) return "Text";
        if (components.Contains("Image")) return "Image";
        if (components.Contains("RawImage")) return "RawImage";
        if (components.Contains("Scrollbar")) return "Scrollbar";
        if (components.Contains("Dropdown") || components.Contains("TMP_Dropdown")) return "Dropdown";

        // 3. 容器类型
        if (components.Contains("CanvasGroup") || components.Contains("Panel")) return "Panel";

        // 4. 默认
        return "Node";
    }

    // ============================================================
    // clickable 推断
    // ============================================================
    private struct ClickableInfo
    {
        public bool clickable;
        public string reason;
        public bool? interactable;
    }

    private static ClickableInfo InferClickable(GameObject go, List<string> components)
    {
        var info = new ClickableInfo { clickable = false, reason = "" };

        // 1. AutoSmokeNode 显式标注
        var nodeComp = FindAutoSmokeNodeComponent(go);
        if (nodeComp != null)
        {
            object val = GetComponentField(nodeComp, "clickable");
            if (val is bool && (bool)val)
            {
                info.clickable = true;
                info.reason = "AutoSmokeNode.clickable=true";
                return info;
            }
        }

        // 2. Button 组件
        Button button = go.GetComponent<Button>();
        if (button != null)
        {
            info.clickable = true;
            info.interactable = button.interactable;
            info.reason = button.interactable
                ? "Button.interactable=true"
                : "Button.interactable=false (disabled)";
            return info;
        }

        // 3. Toggle 组件
        Toggle toggle = go.GetComponent<Toggle>();
        if (toggle != null)
        {
            info.clickable = true;
            info.interactable = toggle.interactable;
            info.reason = "Toggle";
            return info;
        }

        // 4. Slider / InputField
        if (go.GetComponent<Slider>() != null || go.GetComponent<InputField>() != null
            || go.GetComponent<TMP_InputField>() != null)
        {
            info.clickable = true;
            info.reason = "Slider/InputField";
            return info;
        }

        // 5. EventTrigger
        EventTrigger trigger = go.GetComponent<EventTrigger>();
        if (trigger != null && trigger.triggers != null && trigger.triggers.Count > 0)
        {
            info.clickable = true;
            info.reason = $"EventTrigger ({trigger.triggers.Count} events)";
            return info;
        }

        // 6. 检查是否有 IPointerClickHandler
        if (HasInterface(go, "IPointerClickHandler"))
        {
            info.clickable = true;
            info.reason = "IPointerClickHandler";
            return info;
        }

        // 7. Image.raycastTarget + 带有事件脚本
        Image image = go.GetComponent<Image>();
        if (image != null && image.raycastTarget)
        {
            // 检查是否有其他事件脚本
            var monoScripts = go.GetComponents<MonoBehaviour>();
            int nonUnityScripts = 0;
            foreach (var ms in monoScripts)
            {
                if (ms != null)
                {
                    string typeName = ms.GetType().FullName ?? "";
                    if (!typeName.StartsWith("UnityEngine.") && !typeName.StartsWith("UnityEditor."))
                        nonUnityScripts++;
                }
            }
            if (nonUnityScripts > 0)
            {
                info.clickable = true;
                info.reason = $"Image.raycastTarget=true + {nonUnityScripts} custom scripts";
                return info;
            }
        }

        // 8. Dropdown
        if (go.GetComponent<Dropdown>() != null || go.GetComponent<TMP_Dropdown>() != null)
        {
            info.clickable = true;
            info.reason = "Dropdown";
            return info;
        }

        // 9. ScrollRect 本身也可滚动
        ScrollRect scrollRect = go.GetComponent<ScrollRect>();
        if (scrollRect != null)
        {
            // 不标记为 clickable，但记下类型
            info.reason = "ScrollRect (not marked clickable)";
        }

        return info;
    }

    // ============================================================
    // visible / 文本 / 工具
    // ============================================================
    private static bool IsVisible(GameObject go)
    {
        if (!go.activeInHierarchy) return false;

        CanvasGroup cg = go.GetComponent<CanvasGroup>();
        if (cg != null && cg.alpha <= 0 && !cg.blocksRaycasts)
            return false;

        return true;
    }

    private static string GuessIconType(string spriteName, string nodeName)
    {
        string lower = (spriteName + " " + nodeName).ToLower();
        if (lower.Contains("item")) return "item";
        if (lower.Contains("reward")) return "reward";
        if (lower.Contains("icon") && lower.Contains("building")) return "building_icon";
        if (lower.Contains("activity") || lower.Contains("event")) return "activity";
        if (lower.Contains("btn") || lower.Contains("button")) return "button";
        if (lower.Contains("icon") && lower.Contains("resource")) return "resource";
        if (lower.Contains("tips") || lower.Contains("hint")) return "tips_icon";
        if (lower.Contains("icon")) return "unknown_icon";
        return "unknown";
    }

    private static string ExtractTextContent(GameObject go, List<string> components)
    {
        // TMP_Text
        if (components.Contains("TMP_Text"))
        {
            var tmp = go.GetComponent<TMP_Text>();
            if (tmp != null && !string.IsNullOrEmpty(tmp.text))
                return tmp.text;
        }

        // Text (Legacy)
        if (components.Contains("Text"))
        {
            var text = go.GetComponent<Text>();
            if (text != null && !string.IsNullOrEmpty(text.text))
                return text.text;
        }

        return null;
    }

    // ============================================================
    // AutoSmokeNode 组件查找（反射）
    // ============================================================
    private static Component FindAutoSmokeNodeComponent(GameObject go)
    {
        // 通过反射查找名为 AutoSmokeNode 的组件
        var components = go.GetComponents<Component>();
        foreach (var comp in components)
        {
            if (comp != null)
            {
                string typeName = comp.GetType().Name;
                if (typeName == "AutoSmokeNode")
                    return comp;
            }
        }
        return null;
    }

    private static object GetComponentField(Component comp, string fieldName)
    {
        try
        {
            var field = comp.GetType().GetField(fieldName,
                BindingFlags.Public | BindingFlags.Instance);
            if (field != null)
                return field.GetValue(comp);
        }
        catch { }
        return null;
    }

    // ============================================================
    // 接口检测
    // ============================================================
    private static bool HasInterface(GameObject go, string interfaceName)
    {
        var components = go.GetComponents<MonoBehaviour>();
        foreach (var comp in components)
        {
            if (comp != null)
            {
                Type type = comp.GetType();
                var interfaces = type.GetInterfaces();
                foreach (var iface in interfaces)
                {
                    if (iface.Name == interfaceName)
                        return true;
                }
            }
        }
        return false;
    }

    // ============================================================
    // 页面 ID 推断
    // ============================================================
    private static string InferPageId(GameObject canvasGo)
    {
        string name = canvasGo.name.ToLower();

        // 常见页面命名映射
        if (name.Contains("bag") || name.Contains("backpack") || name.Contains("背包"))
            return "bag_page";
        if (name.Contains("main") || name.Contains("主城") || name.Contains("city"))
            return "main_city_page";
        if (name.Contains("战斗") || name.Contains("battle") || name.Contains("fight"))
            return "battle_page";
        if (name.Contains("shop") || name.Contains("store") || name.Contains("商城") || name.Contains("商店"))
            return "shop_page";
        if (name.Contains("mail") || name.Contains("消息") || name.Contains("信件"))
            return "mail_page";
        if (name.Contains("setting") || name.Contains("设置") || name.Contains("options"))
            return "setting_page";
        if (name.Contains("login") || name.Contains("登录") || name.Contains("login"))
            return "login_page";
        if (name.Contains("reward") || name.Contains("奖励") || name.Contains("领取"))
            return "reward_page";
        if (name.Contains("guide") || name.Contains("引导") || name.Contains("新手"))
            return "guide_page";

        // 取 Canvas 上活跃子面板的名称
        for (int i = 0; i < canvasGo.transform.childCount; i++)
        {
            Transform child = canvasGo.transform.GetChild(i);
            if (child.gameObject.activeInHierarchy)
            {
                string childName = child.name.ToLower();
                if (childName.Contains("panel") || childName.Contains("页面") || childName.Contains("ui"))
                {
                    return $"{SanitizeId(child.name)}_page";
                }
            }
        }

        return SanitizeId(canvasGo.name) + "_page";
    }

    private static string SanitizeId(string name)
    {
        // 转为小写下划线格式
        string id = "";
        foreach (char c in name)
        {
            if (char.IsLetterOrDigit(c))
                id += char.ToLower(c);
            else if (c == '_' || c == '-')
                id += c;
            else
                id += '_';
        }
        return id.Trim('_');
    }

    // ============================================================
    // 状态扫描
    // ============================================================
    private static string ScanState()
    {
        // 获取当前场景
        string sceneName = "unknown";
        try
        {
            var scene = UnityEditor.SceneManagement.EditorSceneManager.GetActiveScene();
            sceneName = scene.name;
        }
        catch { }

        // 检测弹窗（通过 Canvas 排序或遮罩检测）
        var popups = new List<Dictionary<string, object>>();
        Canvas[] canvases = GameObject.FindObjectsOfType<Canvas>();
        foreach (var canvas in canvases.OrderByDescending(c => c.sortingOrder))
        {
            if (!canvas.gameObject.activeInHierarchy) continue;

            // 检测是否有遮罩组件（Mask/Image filled）
            bool hasMask = canvas.GetComponent<Mask>() != null
                        || canvas.GetComponent<RectMask2D>() != null;

            // 检测是否有 CanvasGroup 控制透明度
            CanvasGroup cg = canvas.GetComponent<CanvasGroup>();
            bool isTransparent = cg != null && cg.alpha < 0.1f;

            if (isTransparent) continue;

            // 深度大的浮层可能是弹窗
            if (canvas.sortingOrder > 10 || hasMask)
            {
                string pageId = InferPageId(canvas.gameObject);
                var popup = new Dictionary<string, object>
                {
                    ["canvasName"] = canvas.gameObject.name,
                    ["pageId"] = pageId,
                    ["sortingOrder"] = canvas.sortingOrder,
                    ["hasMask"] = hasMask,
                    ["visible"] = canvas.gameObject.activeInHierarchy,
                };
                popups.Add(popup);
            }
        }

        // 检测点击状态（最近是否有 click_request 被处理）
        bool recentClick = CheckRecentClick();

        var state = new Dictionary<string, object>
        {
            ["exportTime"] = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
            ["sceneName"] = sceneName,
            ["sceneId"] = SanitizeId(sceneName) + "_scene",
            ["currentPageId"] = InferPageIdFromCanvases(canvases),
            ["isPlaying"] = Application.isPlaying,
            ["gameResolution"] = new int[] { _designWidth, _designHeight },
            ["screenResolution"] = new int[] { Screen.width, Screen.height },
            ["popupCount"] = popups.Count,
            ["popups"] = popups,
            ["recentClick"] = recentClick,
            ["totalCanvasCount"] = canvases.Length,
        };

        return JsonEncode(state);
    }

    private static string InferPageIdFromCanvases(Canvas[] canvases)
    {
        if (canvases == null || canvases.Length == 0)
            return "unknown";

        // 取排序最高的可见 Canvas
        var top = canvases
            .Where(c => c.gameObject.activeInHierarchy)
            .OrderByDescending(c => c.sortingOrder)
            .FirstOrDefault();

        if (top == null) return "unknown";
        return InferPageId(top.gameObject);
    }

    // ============================================================
    // 场景对象扫描（建筑/资源/地图对象）
    // ============================================================
    private static string ScanSceneObjects()
    {
        var buildings = new List<Dictionary<string, object>>();
        var mapObjects = new List<Dictionary<string, object>>();
        int buildingCount = 0;
        int mapObjectCount = 0;

        // 获取主相机用于世界→屏幕坐标转换
        Camera mainCam = Camera.main;
        int screenW = Screen.width;
        int screenH = Screen.height;

        // 在场景中查找所有活跃对象
        GameObject[] allObjects = GameObject.FindObjectsOfType<GameObject>();
        HashSet<string> processedPaths = new HashSet<string>();

        foreach (var go in allObjects)
        {
            if (!go.activeInHierarchy) continue;
            if (go.transform.parent != null) continue; // 只处理根对象

            // 递归扫描场景对象树
            ScanSceneTransform(go.transform, buildings, mapObjects, mainCam,
                             screenW, screenH, processedPaths, "");
        }

        var output = new Dictionary<string, object>
        {
            ["exportTime"] = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
            ["sceneName"] = GetSceneName(),
            ["buildingCount"] = buildings.Count,
            ["mapObjectCount"] = mapObjects.Count,
            ["buildings"] = buildings,
            ["mapObjects"] = mapObjects,
        };

        return JsonEncode(output);
    }

    private static void ScanSceneTransform(Transform parent,
        List<Dictionary<string, object>> buildings,
        List<Dictionary<string, object>> mapObjects,
        Camera cam, int screenW, int screenH,
        HashSet<string> processedPaths, string parentPath)
    {
        string path = string.IsNullOrEmpty(parentPath)
            ? parent.name
            : parentPath + "/" + parent.name;

        if (processedPaths.Contains(path)) return;
        processedPaths.Add(path);

        GameObject go = parent.gameObject;
        string name = go.name;
        string nameLower = name.ToLower();

        // 判断是否是建筑对象
        bool isBuilding = IsBuildingObject(nameLower);
        bool isMapObject = IsMapObject(nameLower);

        if (isBuilding || isMapObject)
        {
            // 计算屏幕坐标
            var screenRect = CalcWorldScreenRect(go, cam, screenW, screenH);
            var normalizedRect = CalcWorldNormalizedRect(screenRect);

            // 检测是否可点击
            bool clickable = IsSceneObjectClickable(go);
            string clickableReason = clickable ? GetClickableReason(go) : "";

            // 提取等级信息
            int level = ExtractLevel(name);

            // 提取类型
            string objType = InferSceneObjectType(nameLower);

            var meta = new Dictionary<string, object>
            {
                ["name"] = name,
                ["path"] = path,
                ["type"] = objType,
                ["clickable"] = clickable,
                ["childCount"] = parent.childCount,
            };

            if (level > 0) meta["level"] = level;
            if (clickable) meta["clickableReason"] = clickableReason;
            if (screenRect != null) meta["screenRect"] = screenRect;
            if (normalizedRect != null) meta["normalizedRect"] = normalizedRect;

            // 世界坐标（设计坐标，用于验证）
            meta["worldPosition"] = new float[]
            {
                (float)Math.Round(parent.position.x, 1),
                (float)Math.Round(parent.position.y, 1),
                (float)Math.Round(parent.position.z, 1),
            };

            if (isBuilding)
                buildings.Add(meta);
            else
                mapObjects.Add(meta);
        }

        // 递归子节点（只扫描 1 层子对象，避免过深）
        for (int i = 0; i < parent.childCount && i < 5; i++)
        {
            Transform child = parent.GetChild(i);
            ScanSceneTransform(child, buildings, mapObjects, cam,
                             screenW, screenH, processedPaths, path);
        }
    }

    // ============================================================
    // 建筑/对象判断
    // ============================================================
    private static bool IsBuildingObject(string nameLower)
    {
        // 建筑关键词
        string[] keywords = {
            "building", "castle", "主城", "兵营", "barracks", "farm", "mine",
            "lumber", "wood", "stone", "iron", "trade", "ship", "warehouse",
            "仓库", "market", "市场", "wall", "城墙", "tower", "塔",
            "camp", "军营", "fort", "堡垒", "academy", "学院",
            "hospital", "医院", "tavern", "酒馆", "stable",
            "post", "岗哨", "gate", "城门",
        };
        foreach (var kw in keywords)
        {
            if (nameLower.Contains(kw)) return true;
        }
        return false;
    }

    private static bool IsMapObject(string nameLower)
    {
        // 地图对象关键词
        string[] keywords = {
            "resource", "资源", "wood", "石头", "iron", "gold",
            "ore", "矿", "tree", "树", "herb", "草",
            "monster", "野怪", "creep", "camp", "npc",
            "treasure", "宝箱", "chest", "传送", "portal",
        };
        foreach (var kw in keywords)
        {
            if (nameLower.Contains(kw)) return true;
        }
        return false;
    }

    private static string InferSceneObjectType(string nameLower)
    {
        if (nameLower.Contains("castle") || nameLower.Contains("主城"))
            return "Building";
        if (nameLower.Contains("barracks") || nameLower.Contains("兵营"))
            return "Building";
        if (nameLower.Contains("hospital") || nameLower.Contains("医院"))
            return "Building";
        if (nameLower.Contains("trade") || nameLower.Contains("ship"))
            return "Building";
        if (nameLower.Contains("tower") || nameLower.Contains("塔"))
            return "Building";
        if (nameLower.Contains("wall") || nameLower.Contains("城墙"))
            return "Building";
        if (nameLower.Contains("watch") || nameLower.Contains("岗哨"))
            return "Building";
        if (nameLower.Contains("market") || nameLower.Contains("市场"))
            return "Building";
        if (nameLower.Contains("farm") || nameLower.Contains("农田"))
            return "Building";
        if (nameLower.Contains("warehouse") || nameLower.Contains("仓库"))
            return "Building";
        if (nameLower.Contains("resource") || nameLower.Contains("资源"))
            return "MapObject";
        if (nameLower.Contains("gold") || nameLower.Contains("ore") || nameLower.Contains("矿"))
            return "Resource";
        if (nameLower.Contains("tree") || nameLower.Contains("wood"))
            return "Resource";
        if (nameLower.Contains("monster") || nameLower.Contains("野怪"))
            return "Monster";
        if (nameLower.Contains("npc"))
            return "NPC";
        return "SceneObject";
    }

    private static int ExtractLevel(string name)
    {
        // 从名称中提取等级，例如 "Castle_lv5" 或 "Building_lv3"
        var match = System.Text.RegularExpressions.Regex.Match(name,
            @"[_.]lv(\d+)|Level(\d+)|_(\d+)$|^(\d+)_", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
        if (match.Success)
        {
            for (int i = 1; i <= 4; i++)
            {
                if (match.Groups[i].Success && int.TryParse(match.Groups[i].Value, out int lv))
                    return lv;
            }
        }
        return 0;
    }

    // ============================================================
    // 世界坐标 → 屏幕坐标
    // ============================================================
    private static int[] CalcWorldScreenRect(GameObject go, Camera cam,
                                             int screenW, int screenH)
    {
        if (cam == null) return null;
        try
        {
            // 获取包围盒或直接使用位置
            Renderer renderer = go.GetComponent<Renderer>();
            Vector3 worldPos = go.transform.position;

            if (renderer != null && renderer.bounds.size.magnitude > 0.01f)
            {
                // 使用包围盒中心
                worldPos = renderer.bounds.center;
            }

            // 世界坐标 → 屏幕坐标（左下角原点）
            Vector3 screenPos = cam.WorldToScreenPoint(worldPos);

            if (screenPos.z < 0) return null; // 在相机后面

            // 翻转 Y（Unity 屏幕左下角 → UI 左上角）
            float screenY = screenH - screenPos.y;

            // 缩放到设计分辨率
            float scaleX = (float)_designWidth / screenW;
            float scaleY = (float)_designHeight / screenH;

            int dx = Mathf.RoundToInt(screenPos.x * scaleX);
            int dy = Mathf.RoundToInt(screenY * scaleY);

            // 估算尺寸（默认 40x40 设计像素）
            int size = 40;
            return new int[] {
                dx - size / 2,
                dy - size / 2,
                dx + size / 2,
                dy + size / 2,
            };
        }
        catch
        {
            return null;
        }
    }

    private static float[] CalcWorldNormalizedRect(int[] screenRect)
    {
        if (screenRect == null) return null;
        float cx = (screenRect[0] + screenRect[2]) / 2f / _designWidth;
        float cy = (screenRect[1] + screenRect[3]) / 2f / _designHeight;
        float w = (float)(screenRect[2] - screenRect[0]) / _designWidth;
        float h = (float)(screenRect[3] - screenRect[1]) / _designHeight;
        return new float[]
        {
            (float)Math.Round(cx - w/2, 4),
            (float)Math.Round(cy - h/2, 4),
            (float)Math.Round(w, 4),
            (float)Math.Round(h, 4),
        };
    }

    // ============================================================
    // 场景对象可点击判断
    // ============================================================
    private static bool IsSceneObjectClickable(GameObject go)
    {
        // Collider
        if (go.GetComponent<Collider>() != null) return true;
        // 子对象 Collider
        Collider[] colliders = go.GetComponentsInChildren<Collider>();
        if (colliders.Length > 0) return true;

        // UI 事件脚本
        if (HasInterface(go, "IPointerClickHandler")) return true;
        if (go.GetComponent<EventTrigger>() != null) return true;

        return false;
    }

    private static string GetClickableReason(GameObject go)
    {
        if (go.GetComponent<Collider>() != null)
            return $"Collider ({go.GetComponent<Collider>().GetType().Name})";
        Collider[] colliders = go.GetComponentsInChildren<Collider>();
        if (colliders.Length > 0)
            return $"ChildCollider ({colliders[0].GetType().Name})";
        if (HasInterface(go, "IPointerClickHandler"))
            return "IPointerClickHandler";
        if (go.GetComponent<EventTrigger>() != null)
            return "EventTrigger";
        return "unknown";
    }

    private static string GetSceneName()
    {
        try
        {
            var scene = UnityEditor.SceneManagement.EditorSceneManager.GetActiveScene();
            return scene.name;
        }
        catch { return "unknown"; }
    }

    // ============================================================
    // 点击检测
    // ============================================================
    private static bool CheckRecentClick()
    {
        try
        {
            string resultPath = Path.Combine(_configDir, "click_result.json");
            if (!File.Exists(resultPath)) return false;

            string json = File.ReadAllText(resultPath);
            if (string.IsNullOrEmpty(json)) return false;

            // 检查时间戳（最近 1 秒内的点击）
            string logPath = Path.Combine(_configDir, "click_log.txt");
            // 简化：检查 click_result.json 是否存在且非空则认为最近有点击
            var info = new FileInfo(resultPath);
            return (DateTime.Now - info.LastWriteTime).TotalSeconds < 2.0;
        }
        catch
        {
            return false;
        }
    }

    // ============================================================
    // JSON 编码（手动，避免 Newtonsoft 依赖）
    // ============================================================
    private static string JsonEncode(Dictionary<string, object> dict)
    {
        var sb = new StringBuilder();
        sb.Append("{");
        bool first = true;
        foreach (var kv in dict)
        {
            if (!first) sb.Append(",\n  ");
            first = false;
            sb.AppendFormat("\"{0}\":", kv.Key);
            sb.Append(JsonValue(kv.Value, 1));
        }
        sb.Append("\n}");
        return sb.ToString();
    }

    private static string JsonValue(object value, int indent)
    {
        if (value == null) return "null";
        if (value is string s) return $"\"{EscapeJson(s)}\"";
        if (value is bool b) return b ? "true" : "false";
        if (value is int i) return i.ToString();
        if (value is float f) return f.ToString("0.####");
        if (value is double d) return d.ToString("0.####");

        if (value is int[] arr)
        {
            return "[" + string.Join(", ", arr) + "]";
        }
        if (value is float[] farr)
        {
            return "[" + string.Join(", ", farr.Select(f => f.ToString("0.####"))) + "]";
        }
        if (value is List<string> list)
        {
            return "[" + string.Join(", ", list.Select(s => $"\"{EscapeJson(s)}\"")) + "]";
        }
        if (value is List<Dictionary<string, object>> listDict)
        {
            var sb = new StringBuilder();
            sb.Append("[\n");
            bool first = true;
            foreach (var entry in listDict)
            {
                if (!first) sb.Append(",\n");
                first = false;
                sb.Append(new string(' ', (indent + 1) * 2));
                sb.Append(JsonEncode(entry));
            }
            sb.Append("\n" + new string(' ', indent * 2) + "]");
            return sb.ToString();
        }
        if (value is List<object> objList)
        {
            var sb = new StringBuilder();
            sb.Append("[\n");
            bool first = true;
            foreach (var v in objList)
            {
                if (!first) sb.Append(",\n");
                first = false;
                sb.Append(new string(' ', (indent + 1) * 2));
                sb.Append(JsonValue(v, indent + 1));
            }
            sb.Append("\n" + new string(' ', indent * 2) + "]");
            return sb.ToString();
        }

        return $"\"{EscapeJson(value.ToString())}\"";
    }

    private static string EscapeJson(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace("\\", "\\\\")
                .Replace("\"", "\\\"")
                .Replace("\n", "\\n")
                .Replace("\r", "\\r")
                .Replace("\t", "\\t");
    }

    // ============================================================
    // 日志
    // ============================================================
    private static void Log(string message)
    {
        try
        {
            string line = $"[{DateTime.Now:HH:mm:ss}] {message}";
            File.AppendAllText(_logPath, line + "\n");
        }
        catch { }
    }

    // ============================================================
    // 额外菜单：诊断
    // ============================================================
    [MenuItem("AutoSmoke/数据采集/打开输出目录", false, 210)]
    private static void MenuOpenOutputFolder()
    {
        if (Directory.Exists(_metadataDir))
        {
            EditorUtility.RevealInFinder(_metadataDir);
        }
        else
        {
            Debug.LogWarning($"[AutoSmoke] 输出目录不存在: {_metadataDir}");
        }
    }

    [MenuItem("AutoSmoke/数据采集/强制立即导出", false, 211)]
    private static void MenuForceExport()
    {
        ExportMetadata("manual_force");
        Debug.Log($"[AutoSmoke] 强制导出完成");
    }
}
