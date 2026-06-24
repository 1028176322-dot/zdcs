/*
 * AutoSmokeUIPrefabScanner.cs
 * 工程态 UI Prefab 扫描器（UI树方案 阶段一）
 * 
 * 功能：
 *   1. 扫描 Unity 工程中所有 UI Prefab / Scene
 *   2. 识别 Button/Text/Image/InputField/Toggle 等 UI 组件
 *   3. 检测 Missing Script / Missing Reference
 *   4. 检测 testId 标注情况
 *   5. 输出 project_ui_inventory.json
 * 
 * 输出路径：%USERPROFILE%\.autosmoke\metadata\project_ui_inventory.json
 * 
 * 菜单：
 *   AutoSmoke > UI > Scan All UI Prefabs
 *   AutoSmoke > UI > Scan All Scenes  
 *   AutoSmoke > UI > Export Project UI Inventory
 *   AutoSmoke > UI > Scan Icons
 */

using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using UnityEngine.Events;

[InitializeOnLoad]
public static class AutoSmokeUIPrefabScanner
{
    private static string _outputPath;

    // 扫描目标目录（相对于 Assets/）
    // 会根据工程实际目录自动适配
    private static readonly string[] _targetFolders = {
        "CasualGame", "Res", "Framework", "Launch",
        "NewGameDemo", "Data", "RefRes",
    };

    static AutoSmokeUIPrefabScanner()
    {
        string userProfile = Environment.GetEnvironmentVariable("USERPROFILE")
                             ?? Environment.GetEnvironmentVariable("HOME") ?? ".";
        string bridgeRoot = Path.Combine(userProfile, ".autosmoke");

        // 读取配置获取 autosmokeRoot
        string autosmokeRoot = TryReadAutosmokeRoot(bridgeRoot);
        string outputDir;
        if (!string.IsNullOrEmpty(autosmokeRoot))
            outputDir = Path.Combine(autosmokeRoot, "元数据");
        else
            outputDir = Path.Combine(bridgeRoot, "metadata");

        _outputPath = Path.Combine(outputDir, "project_ui_inventory.json");
        try { Directory.CreateDirectory(outputDir); } catch { }
    }

    private static string TryReadAutosmokeRoot(string bridgeRoot)
    {
        try
        {
            string cfgPath = Path.Combine(bridgeRoot, "config.json");
            if (!File.Exists(cfgPath)) return null;
            string json = File.ReadAllText(cfgPath);
            var cfg = JsonUtility.FromJson<AutoSmokeConfig>(json);
            if (cfg != null && !string.IsNullOrEmpty(cfg.autosmokeRoot))
            {
                string root = cfg.autosmokeRoot.Replace("/", "\\");
                if (Directory.Exists(root)) return root;
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

    [MenuItem("AutoSmoke/数据采集/扫描 UI Prefab")]
    private static void ScanAllUIPrefabs()
    {
        EditorUtility.DisplayProgressBar("AutoSmoke", "正在扫描 UI Prefab...", 0);
        try
        {
            var inventory = BuildInventory(scanPrefabs: true, scanScenes: false);
            SaveInventory(inventory);
            EditorUtility.DisplayDialog("AutoSmoke",
                $"扫描完成！\n发现 {inventory.prefabs.Count} 个 UI Prefab\n" +
                $"共 {CountAllNodes(inventory)} 个节点\n" +
                $"输出: {_outputPath}", "OK");
        }
        finally
        {
            EditorUtility.ClearProgressBar();
        }
    }

    [MenuItem("AutoSmoke/数据采集/扫描全部场景")]
    private static void ScanAllScenes()
    {
        EditorUtility.DisplayProgressBar("AutoSmoke", "正在扫描场景...", 0);
        try
        {
            var inventory = BuildInventory(scanPrefabs: false, scanScenes: true);
            SaveInventory(inventory);
            EditorUtility.DisplayDialog("AutoSmoke",
                $"扫描完成！\n发现 {inventory.scenes.Count} 个 Scene\n" +
                $"输出: {_outputPath}", "OK");
        }
        finally
        {
            EditorUtility.ClearProgressBar();
        }
    }

    [MenuItem("AutoSmoke/数据采集/导出完整工程 UI 清单")]
    private static void ExportFullInventory()
    {
        EditorUtility.DisplayProgressBar("AutoSmoke", "正在构建完整 UI 清单...", 0);
        try
        {
            var inventory = BuildInventory(scanPrefabs: true, scanScenes: true);
            SaveInventory(inventory);
            EditorUtility.DisplayDialog("AutoSmoke",
                $"完成！\nPrefab: {inventory.prefabs.Count} | Scene: {inventory.scenes.Count}\n" +
                $"总节点: {CountAllNodes(inventory)}\n" +
                $"Missing Script: {inventory.missingScriptCount}\n" +
                $"输出: {_outputPath}", "OK");
        }
        finally
        {
            EditorUtility.ClearProgressBar();
        }
    }

    [MenuItem("AutoSmoke/数据采集/扫描图标资源")]
    private static void ScanIcons()
    {
        EditorUtility.DisplayProgressBar("AutoSmoke", "正在扫描图标...", 0);
        try
        {
            var icons = ScanIconAssets();
            SaveIcons(icons);
            EditorUtility.DisplayDialog("AutoSmoke",
                $"图标扫描完成！发现 {icons.Count} 个 UI 图标资源", "OK");
        }
        finally
        {
            EditorUtility.ClearProgressBar();
        }
    }

    // ============================================================
    // 核心扫描
    // ============================================================

    private static UIInventory BuildInventory(bool scanPrefabs, bool scanScenes)
    {
        var inventory = new UIInventory
        {
            schemaVersion = 1,
            timestamp = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss.fffK"),
            projectPath = Application.dataPath,
            prefabs = new List<PrefabInfo>(),
            scenes = new List<SceneInfo>(),
        };

        int missingScriptCount = 0;
        int noTestIdCount = 0;
        int buttonCount = 0;

        if (scanPrefabs)
        {
            var prefabGuids = AssetDatabase.FindAssets("t:Prefab", _targetFolders);

            // 如果在指定目录未找到，回退到全工程扫描
            if (prefabGuids.Length == 0)
            {
                Debug.Log("[AutoSmoke] 指定目录未找到 Prefab，回退到全工程扫描...");
                prefabGuids = AssetDatabase.FindAssets("t:Prefab");
            }
            for (int i = 0; i < prefabGuids.Length; i++)
            {
                if (EditorUtility.DisplayCancelableProgressBar(
                    "AutoSmoke", $"Scanning prefabs... ({i + 1}/{prefabGuids.Length})",
                    (float)i / prefabGuids.Length))
                    break;

                string path = AssetDatabase.GUIDToAssetPath(prefabGuids[i]);
                if (!path.StartsWith("Assets/")) continue;

                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null) continue;

                // 只扫描有 Canvas / Button / Image / Text 的 UI Prefab
                if (!IsUIPrefab(prefab)) continue;

                var info = ScanPrefab(prefab, path, ref missingScriptCount, ref noTestIdCount, ref buttonCount);
                inventory.prefabs.Add(info);

                // 统计图标
                var iconNodes = info.nodes.FindAll(n => n.componentTypes.Contains("Image"));
                foreach (var icon in iconNodes)
                {
                    var iconInfo = ExtractIconInfo(icon, prefab, path);
                    if (iconInfo != null)
                        inventory.iconCandidates.Add(iconInfo);
                }
            }
        }

        if (scanScenes)
        {
            var sceneGuids = AssetDatabase.FindAssets("t:Scene", _targetFolders);
            for (int i = 0; i < sceneGuids.Length; i++)
            {
                if (EditorUtility.DisplayCancelableProgressBar(
                    "AutoSmoke", $"Scanning scenes... ({i + 1}/{sceneGuids.Length})",
                    (float)i / sceneGuids.Length))
                    break;

                string path = AssetDatabase.GUIDToAssetPath(sceneGuids[i]);
                inventory.scenes.Add(new SceneInfo
                {
                    assetPath = path,
                    name = Path.GetFileNameWithoutExtension(path),
                });
            }
        }

        inventory.missingScriptCount = missingScriptCount;
        inventory.noTestIdCount = noTestIdCount;
        inventory.buttonCount = buttonCount;
        inventory.summary = $"{inventory.prefabs.Count} prefabs, {inventory.scenes.Count} scenes, " +
                            $"{missingScriptCount} missing scripts, {noTestIdCount} no-testId nodes";

        EditorUtility.ClearProgressBar();
        return inventory;
    }

    private static PrefabInfo ScanPrefab(GameObject prefab, string assetPath,
                                          ref int missingScriptCount,
                                          ref int noTestIdCount,
                                          ref int buttonCount)
    {
        var info = new PrefabInfo
        {
            assetPath = assetPath,
            guid = AssetDatabase.AssetPathToGUID(assetPath),
            rootName = prefab.name,
            category = CategorizePrefab(prefab),
            nodes = new List<UINodeInfo>(),
        };

        // 递归扫描子节点
        ScanNodeRecursive(prefab.transform, "", info.nodes,
                          ref missingScriptCount, ref noTestIdCount, ref buttonCount);

        return info;
    }

    private static void ScanNodeRecursive(Transform transform, string parentPath,
                                           List<UINodeInfo> nodes,
                                           ref int missingScriptCount,
                                           ref int noTestIdCount,
                                           ref int buttonCount)
    {
        string path = string.IsNullOrEmpty(parentPath)
            ? transform.name
            : parentPath + "/" + transform.name;

        var go = transform.gameObject;

        // 获取组件列表
        var components = go.GetComponents<Component>();
        var compTypes = new List<string>();
        bool hasMissingScript = false;

        foreach (var comp in components)
        {
            if (comp == null)
            {
                hasMissingScript = true;
                compTypes.Add("MISSING_SCRIPT");
            }
            else
            {
                compTypes.Add(comp.GetType().Name);
            }
        }

        if (hasMissingScript) missingScriptCount++;

        // 判断是否 UI 节点（有 RectTransform 的节点）
        bool isUI = transform is RectTransform;

        // 检测文本
        string text = "";
        var textComp = go.GetComponent<Text>();
        if (textComp != null) text = textComp.text;
        var tmpComp = go.GetComponent("TMPro.TMP_Text");
        if (tmpComp != null)
        {
            var tmpText = tmpComp.GetType().GetProperty("text")?.GetValue(tmpComp)?.ToString();
            if (!string.IsNullOrEmpty(tmpText)) text = tmpText;
        }

        // 检测按钮
        bool hasButton = compTypes.Contains("Button") || compTypes.Contains("Toggle");
        if (hasButton) buttonCount++;

        // 检测可点击
        bool clickable = hasButton || compTypes.Contains("EventTrigger");
        // 检查 IPointerClickHandler
        if (!clickable)
        {
            foreach (var comp in components)
            {
                if (comp != null && comp is UnityEngine.EventSystems.IPointerClickHandler)
                {
                    clickable = true;
                    break;
                }
            }
        }

        // 检测 testId（通过 AutoSmokeNode 或自定义字段）
        string testId = "";
        var nodeComp = go.GetComponent("AutoSmokeNode");
        if (nodeComp != null)
        {
            var testIdProp = nodeComp.GetType().GetProperty("testId");
            if (testIdProp != null)
                testId = testIdProp.GetValue(nodeComp)?.ToString() ?? "";
        }
        if (string.IsNullOrEmpty(testId)) noTestIdCount++;

        // 图标检测
        string spriteName = "";
        string atlasName = "";
        bool raycastTarget = false;
        var imageComp = go.GetComponent<Image>();
        if (imageComp != null)
        {
            raycastTarget = imageComp.raycastTarget;
            if (imageComp.sprite != null)
            {
                spriteName = imageComp.sprite.name;
                // 尝试从 Sprite 的 texture 推断 atlas
                if (imageComp.sprite.texture != null)
                    atlasName = imageComp.sprite.texture.name;
            }
        }
        var rawImageComp = go.GetComponent<RawImage>();
        if (rawImageComp != null)
        {
            raycastTarget = raycastTarget || rawImageComp.raycastTarget;
        }

        // RectTransform 信息
        var rtInfo = new RectTransformInfo();
        if (isUI)
        {
            var rt = transform as RectTransform;
            rtInfo.anchorMin = new float[] { rt.anchorMin.x, rt.anchorMin.y };
            rtInfo.anchorMax = new float[] { rt.anchorMax.x, rt.anchorMax.y };
            rtInfo.pivot = new float[] { rt.pivot.x, rt.pivot.y };
            rtInfo.sizeDelta = new float[] { rt.sizeDelta.x, rt.sizeDelta.y };
            rtInfo.anchoredPosition = new float[] { rt.anchoredPosition.x, rt.anchoredPosition.y };
        }

        var nodeInfo = new UINodeInfo
        {
            path = path,
            name = transform.name,
            componentTypes = compTypes,
            text = text,
            isUI = isUI,
            hasButton = hasButton,
            clickable = clickable,
            hasTestId = !string.IsNullOrEmpty(testId),
            testId = testId,
            hasMissingScript = hasMissingScript,
            spriteName = spriteName,
            atlasName = atlasName,
            raycastTarget = raycastTarget,
            childCount = transform.childCount,
            rectTransform = rtInfo,
        };
        nodes.Add(nodeInfo);

        // 递归子节点
        for (int i = 0; i < transform.childCount; i++)
        {
            ScanNodeRecursive(transform.GetChild(i), path, nodes,
                              ref missingScriptCount, ref noTestIdCount, ref buttonCount);
        }
    }

    // ============================================================
    // 图标扫描
    // ============================================================

    private static IconAssetInfo ExtractIconInfo(UINodeInfo node, GameObject prefab, string prefabPath)
    {
        if (string.IsNullOrEmpty(node.spriteName)) return null;

        return new IconAssetInfo
        {
            prefabPath = prefabPath,
            nodePath = node.path,
            nodeName = node.name,
            spriteName = node.spriteName,
            atlasName = node.atlasName,
            raycastTarget = node.raycastTarget,
            parentClickable = IsParentClickable(node, prefab),
            possibleIconType = GuessIconType(node.spriteName, node.name),
            componentType = node.componentTypes.Contains("Image") ? "Image" : "RawImage",
        };
    }

    private static bool IsParentClickable(UINodeInfo node, GameObject prefab)
    {
        // 在 prefab 中查找父节点是否挂载了 Button/EventTrigger
        var go = FindGameObjectInPrefab(prefab, node.path);
        if (go == null || go.transform.parent == null) return false;

        var parent = go.transform.parent.gameObject;
        return parent.GetComponent<Button>() != null
            || parent.GetComponent<Toggle>() != null
            || parent.GetComponent<EventTrigger>() != null;
    }

    private static GameObject FindGameObjectInPrefab(GameObject prefab, string path)
    {
        var parts = path.Split('/');
        Transform current = prefab.transform;
        // 跳过根节点名
        int startIndex = parts[0] == current.name ? 1 : 0;
        for (int i = startIndex; i < parts.Length; i++)
        {
            var child = current.Find(parts[i]);
            if (child == null) return null;
            current = child;
        }
        return current.gameObject;
    }

    private static List<IconAssetInfo> ScanIconAssets()
    {
        var icons = new List<IconAssetInfo>();

        // 查找所有 Sprite/Texture 资源
        var spriteGuids = AssetDatabase.FindAssets("t:Sprite", new[] { "Assets/UI", "Assets/Res" });

        for (int i = 0; i < spriteGuids.Length; i++)
        {
            if (EditorUtility.DisplayCancelableProgressBar(
                "AutoSmoke", $"Scanning icons... ({i + 1}/{spriteGuids.Length})",
                (float)i / spriteGuids.Length))
                break;

            string path = AssetDatabase.GUIDToAssetPath(spriteGuids[i]);
            string name = Path.GetFileNameWithoutExtension(path);

            // 只保留可能是 UI 图标的资源
            if (!name.StartsWith("icon_") && !name.StartsWith("btn_") &&
                !name.StartsWith("ui_") && !name.Contains("Icon") &&
                !name.Contains("Button") && !name.Contains("Item")) continue;

            icons.Add(new IconAssetInfo
            {
                prefabPath = path,
                nodePath = "",
                nodeName = name,
                spriteName = name,
                atlasName = "",
                raycastTarget = false,
                parentClickable = false,
                possibleIconType = GuessIconType(name, name),
                componentType = "Sprite",
            });
        }

        EditorUtility.ClearProgressBar();
        return icons;
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
        if (lower.Contains("icon")) return "unknown_icon";
        if (lower.Contains("tips") || lower.Contains("hint")) return "tips_icon";
        return "unknown";
    }

    // ============================================================
    // 辅助方法
    // ============================================================

    private static bool IsUIPrefab(GameObject prefab)
    {
        // 检查是否有 Canvas / Button / Image / Text 等 UI 组件
        if (prefab.GetComponent<Canvas>() != null) return true;
        if (prefab.GetComponentInChildren<Button>(true) != null) return true;
        if (prefab.GetComponentInChildren<Image>(true) != null) return true;
        if (prefab.GetComponentInChildren<Text>(true) != null) return true;
        if (prefab.GetComponentInChildren<ScrollRect>(true) != null) return true;
        return false;
    }

    private static string CategorizePrefab(GameObject prefab)
    {
        string name = prefab.name.ToLower();
        if (name.Contains("panel") || name.Contains("dialog") || name.Contains("window"))
            return "panel";
        if (name.Contains("popup") || name.Contains("tips"))
            return "popup";
        if (name.Contains("item") || name.Contains("cell") || name.Contains("card"))
            return "item_cell";
        if (name.Contains("btn") || name.Contains("button"))
            return "button_group";
        if (name.Contains("icon"))
            return "icon_asset";
        return "other";
    }

    private static int CountAllNodes(UIInventory inventory)
    {
        int count = 0;
        foreach (var p in inventory.prefabs)
            count += p.nodes.Count;
        return count;
    }

    private static void SaveInventory(UIInventory inventory)
    {
        string json = JsonUtility.ToJson(inventory, true);
        File.WriteAllText(_outputPath, json);
        Debug.Log($"[AutoSmoke] UI 工程清单已保存: {_outputPath}");
    }

    private static void SaveIcons(List<IconAssetInfo> icons)
    {
        var wrapper = new IconWrapper { icons = icons };
        string json = JsonUtility.ToJson(wrapper, true);
        string iconPath = Path.Combine(Path.GetDirectoryName(_outputPath) ?? _outputPath, "project_icons.json");
        File.WriteAllText(iconPath, json);
        Debug.Log($"[AutoSmoke] 图标清单已保存: {iconPath}");
    }

    // ============================================================
    // 数据类
    // ============================================================

    [Serializable]
    private class UIInventory
    {
        public int schemaVersion;
        public string timestamp;
        public string projectPath;
        public List<PrefabInfo> prefabs = new List<PrefabInfo>();
        public List<SceneInfo> scenes = new List<SceneInfo>();
        public List<IconAssetInfo> iconCandidates = new List<IconAssetInfo>();
        public int missingScriptCount;
        public int noTestIdCount;
        public int buttonCount;
        public string summary;
    }

    [Serializable]
    private class PrefabInfo
    {
        public string assetPath;
        public string guid;
        public string rootName;
        public string category;
        public List<UINodeInfo> nodes = new List<UINodeInfo>();
    }

    [Serializable]
    private class UINodeInfo
    {
        public string path;
        public string name;
        public List<string> componentTypes = new List<string>();
        public string text;
        public bool isUI;
        public bool hasButton;
        public bool clickable;
        public bool hasTestId;
        public string testId;
        public bool hasMissingScript;
        public string spriteName;
        public string atlasName;
        public bool raycastTarget;
        public int childCount;
        public RectTransformInfo rectTransform = new RectTransformInfo();
    }

    [Serializable]
    private class RectTransformInfo
    {
        public float[] anchorMin = new float[2];
        public float[] anchorMax = new float[2];
        public float[] pivot = new float[2];
        public float[] sizeDelta = new float[2];
        public float[] anchoredPosition = new float[2];
    }

    [Serializable]
    private class SceneInfo
    {
        public string assetPath;
        public string name;
    }

    [Serializable]
    private class IconAssetInfo
    {
        public string prefabPath;
        public string nodePath;
        public string nodeName;
        public string spriteName;
        public string atlasName;
        public bool raycastTarget;
        public bool parentClickable;
        public string possibleIconType;
        public string componentType;
    }

    [Serializable]
    private class IconWrapper
    {
        public List<IconAssetInfo> icons = new List<IconAssetInfo>();
    }
}
