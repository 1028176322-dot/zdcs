using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

/// <summary>
/// 场景交互对象导出器
/// 遍历场景中的 Collider/Collider2D、自定义点击脚本等，
/// 输出 scene_interaction_tree.json。
/// 不修改游戏业务逻辑，仅 Editor 工具。
/// </summary>
[InitializeOnLoad]
public static class AutoSmokeSceneInteractionExporter
{
    private static string _outputDir;
    private static double _lastExportTime;

    static AutoSmokeSceneInteractionExporter()
    {
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
                    _outputDir = Path.Combine(cfg.autosmokeRoot, "metadata").Replace("/", "\\");
            }
        }
        catch { }

        if (string.IsNullOrEmpty(_outputDir))
            _outputDir = Path.Combine(Application.dataPath, "..", "AutoSmoke", "metadata");

        EditorApplication.update += OnEditorUpdate;
    }

    private static void OnEditorUpdate()
    {
        if (!EditorApplication.isPlaying) return;
        double now = EditorApplication.timeSinceStartup;
        if (now - _lastExportTime < 3.0) return;
        _lastExportTime = now;

        try
        {
            var objects = ScanSceneInteractiveObjects();
            if (objects.Count == 0) return;

            var output = new SceneInteractionData
            {
                schemaVersion = "scene_interaction_tree/v1",
                exportedAt = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
                sceneId = GetActiveScene(),
                objectCount = objects.Count,
                objects = objects
            };

            string json = JsonUtility.ToJson(output, true);
            File.WriteAllText(Path.Combine(_outputDir, "scene_interaction_tree.json"), json);
        }
        catch { }
    }

    private static List<SceneInteractionObject> ScanSceneInteractiveObjects()
    {
        var results = new List<SceneInteractionObject>();

        // 扫描所有 GameObject
        var allGOs = GameObject.FindObjectsOfType<GameObject>();
        foreach (var go in allGOs)
        {
            if (!go.activeInHierarchy) continue;

            string objectType = ClassifySceneObject(go);
            if (string.IsNullOrEmpty(objectType)) continue;

            var obj = new SceneInteractionObject
            {
                sceneId = GetActiveScene(),
                objectType = objectType,
                name = go.name,
                gameObjectPath = BuildPath(go.transform),
                worldPosition = new List<float>
                {
                    (float)Math.Round(go.transform.position.x, 2),
                    (float)Math.Round(go.transform.position.y, 2),
                    (float)Math.Round(go.transform.position.z, 2)
                },
                screenRect = GetScreenBounds(go),
                clickTargetNode = BuildPath(go.transform),
                visualNode = BuildPath(go.transform),
                interactionType = "click",
                clickable = true,
                clickableReason = GetClickableReason(go, objectType),
            };
            results.Add(obj);
        }

        return results;
    }

    private static string ClassifySceneObject(GameObject go)
    {
        string name = go.name.ToLower();
        var comps = go.GetComponents<Component>();

        // 必须有 Collider 或者点击脚本
        bool hasCollider = go.GetComponent<Collider>() != null || go.GetComponent<Collider2D>() != null;
        bool hasClickHandler = false;
        foreach (var c in comps)
        {
            if (c != null && (c is IPointerClickHandler))
            {
                hasClickHandler = true;
                break;
            }
        }
        // 检查自定义脚本
        foreach (var c in comps)
        {
            if (c == null) continue;
            string tn = c.GetType().Name.ToLower();
            if (tn.Contains("click") || tn.Contains("touch") || tn.Contains("interact")
                || tn.Contains("select") || tn.Contains("handle"))
            {
                hasClickHandler = true;
                break;
            }
        }

        if (!hasCollider && !hasClickHandler) return "";

        // 分类
        if (name.Contains("building") || name.Contains("build_") || name.Contains("construction"))
            return "building_object";
        if (name.Contains("resource") || name.Contains("mine_") || name.Contains("wood")
            || name.Contains("stone") || name.Contains("iron") || name.Contains("food"))
            return "resource_point";
        if (name.Contains("npc") || name.Contains("monster") || name.Contains("enemy_")
            || name.Contains("boss_") || name.Contains("creep"))
            return "npc_object";
        if (name.Contains("map_") || name.Contains("terrain") || name.Contains("world_"))
            return "map_object";
        if (name.Contains("event_") || name.Contains("activity_"))
            return "event_point";
        if (name.Contains("treasure") || name.Contains("chest") || name.Contains("loot"))
            return "treasure_object";
        if (name.Contains("ship") || name.Contains("boat") || name.Contains("vessel"))
            return "ship_object";
        if (name.Contains("guide") || name.Contains("arrow") || name.Contains("hint"))
            return "guide_scene_target";

        // 有 Collider 但不知道类型的
        if (hasCollider) return "scene_object";

        return "";
    }

    private static string GetClickableReason(GameObject go, string objectType)
    {
        if (go.GetComponent<Collider>() != null) return "Collider + " + objectType;
        if (go.GetComponent<Collider2D>() != null) return "Collider2D + " + objectType;
        return "script handler + " + objectType;
    }

    private static List<float> GetScreenBounds(GameObject go)
    {
        var rectTransform = go.GetComponent<RectTransform>();
        if (rectTransform != null)
        {
            var corners = new Vector3[4];
            rectTransform.GetWorldCorners(corners);
            return new List<float>
            {
                Mathf.Round(corners[0].x),
                Mathf.Round(corners[1].y),
                Mathf.Round(corners[2].x),
                Mathf.Round(corners[3].y)
            };
        }

        var collider = go.GetComponent<Collider>();
        if (collider != null)
        {
            var bounds = collider.bounds;
            var min = Camera.main != null ? Camera.main.WorldToScreenPoint(bounds.min) : bounds.min;
            var max = Camera.main != null ? Camera.main.WorldToScreenPoint(bounds.max) : bounds.max;
            return new List<float>
            {
                Mathf.Round(min.x), Mathf.Round(min.y),
                Mathf.Round(max.x), Mathf.Round(max.y)
            };
        }

        return new List<float>();
    }

    private static string BuildPath(Transform t)
    {
        if (t == null) return "";
        var segs = new List<string>();
        var cur = t;
        while (cur != null)
        {
            segs.Insert(0, cur.name);
            cur = cur.parent;
        }
        return string.Join("/", segs);
    }

    private static string GetActiveScene()
    {
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        return scene != null ? scene.name : "unknown";
    }

    [Serializable]
    private class AutoSmokeConfig
    {
        public string autosmokeRoot;
    }

    [Serializable]
    public class SceneInteractionObject
    {
        public string sceneId;
        public string objectType;
        public string name;
        public string gameObjectPath;
        public List<float> worldPosition;
        public List<float> screenRect;
        public string clickTargetNode;
        public string visualNode;
        public string interactionType;
        public bool clickable;
        public string clickableReason;
    }

    [Serializable]
    public class SceneInteractionData
    {
        public string schemaVersion;
        public string exportedAt;
        public string sceneId;
        public int objectCount;
        public List<SceneInteractionObject> objects;
    }
}
