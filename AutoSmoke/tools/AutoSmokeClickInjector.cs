/*
 * AutoSmokeClickInjector.cs
 * Unity EventSystem 注入点击闭环（v2 — 精准点击主方案）
 * 
 * 支持目标类型：
 * - testId: 查找 AutoSmokeNode.testId 匹配的元素
 * - semanticId: 查找 AutoSmokeNode.semanticId 匹配的元素
 * - pocoPath: 按 GameObject 路径匹配
 * - coordinate: 按屏幕坐标 Raycast（兜底）
 * 
 * 执行流程：
 * 1. 接收 click_request.json
 * 2. 查找目标 GameObject
 * 3. preCheck（active/visible/interactable/not occluded）
 * 4. 计算 safePoint
 * 5. EventSystem RaycastAll + ExecuteEvents
 * 6. 校验 eventReceiver == target
 * 7. 写回 click_result.json
 * 
 * 设计边界：
 * - 只在 Unity Editor 中运行（Assets/Editor/）
 * - 不修改游戏业务代码
 * - 不进入正式构建包
 */
using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using System.Reflection;

[InitializeOnLoad]
public static class AutoSmokeClickInjector
{
    private const string INJECTOR_VERSION = "20260624_debug_overlay_bypass";
    private static string _configDir;
    private static string _requestPath;
    private static string _resultPath;
    private static string _lastRequestId = "";
    private static double _lastProcessTime = 0;
    private const double MIN_INTERVAL = 0.02;

    static AutoSmokeClickInjector()
    {
        string userProfile = Environment.GetEnvironmentVariable("USERPROFILE")
                             ?? Environment.GetEnvironmentVariable("HOME")
                             ?? ".";
        _configDir = Path.Combine(userProfile, ".autosmoke");
        _requestPath = Path.Combine(_configDir, "click_request.json");
        _resultPath = Path.Combine(_configDir, "click_result.json");

        try { Directory.CreateDirectory(_configDir); }
        catch (Exception ex)
        {
            Debug.LogError($"[AutoSmoke] 创建目录失败: {ex.Message}");
            return;
        }

        EditorApplication.update += OnEditorUpdate;
        Debug.Log($"[AutoSmoke] ClickInjector v2 已启动，监听: {_requestPath}");
    }

    private static void OnEditorUpdate()
    {
        double now = EditorApplication.timeSinceStartup;
        if (now - _lastProcessTime < MIN_INTERVAL) return;
        _lastProcessTime = now;

        if (!File.Exists(_requestPath)) return;

        try
        {
            string json = File.ReadAllText(_requestPath);
            var request = JsonUtility.FromJson<ClickRequest>(json);
            if (request == null || string.IsNullOrEmpty(request.requestId)) return;
            if (request.requestId == _lastRequestId) return;

            _lastRequestId = request.requestId;
            Debug.Log($"[AutoSmoke] 收到点击请求: {request.requestId} targetType={request.targetType}");

            ProcessClick(request);
        }
        catch (Exception ex)
        {
            Debug.LogError($"[AutoSmoke] 处理请求失败: {ex.Message}");
            WriteResult(new ClickResult
            {
                requestId = _lastRequestId,
                status = "UNITY_EXCEPTION",
                message = $"Exception: {ex.Message}"
            });
        }
    }

    // ============================================================
    // 主流程
    // ============================================================
    private static void ProcessClick(ClickRequest request)
    {
        // 1. 检查 EventSystem
        if (EventSystem.current == null)
        {
            WriteResult(new ClickResult
            {
                requestId = request.requestId,
                status = "NO_EVENT_SYSTEM",
                message = "EventSystem.current 为 null（非 Play 模式？）"
            });
            return;
        }

        // 2. 查找目标
        GameObject targetObj = null;
        string targetPath = "";
        string findMethod = request.targetType ?? "coordinate";

        if (findMethod == "testId")
        {
            targetObj = FindByTestId(request.targetValue);
            if (targetObj != null) targetPath = GetGameObjectPath(targetObj);
        }
        else if (findMethod == "semanticId")
        {
            targetObj = FindBySemanticId(request.targetValue);
            if (targetObj != null) targetPath = GetGameObjectPath(targetObj);
        }
        else if (findMethod == "pocoPath" || findMethod == "path")
        {
            targetObj = FindByPath(request.targetValue);
            if (targetObj != null) targetPath = GetGameObjectPath(targetObj);
        }

        // preCheck：目标存在
        var preCheck = new PreCheckResult();
        if (targetObj == null && findMethod != "coordinate")
        {
            preCheck.exists = false;
            WriteResult(new ClickResult
            {
                requestId = request.requestId,
                status = "TARGET_NOT_FOUND",
                target = new TargetInfo { type = findMethod, value = request.targetValue },
                preCheck = preCheck,
                message = $"未找到目标: {findMethod}={request.targetValue}"
            });
            return;
        }

        // 3. preCheck（仅对非坐标模式）
        if (targetObj != null)
        {
            preCheck.exists = true;
            preCheck.activeInHierarchy = targetObj.activeInHierarchy;
            if (!preCheck.activeInHierarchy)
            {
                WriteResult(new ClickResult
                {
                    requestId = request.requestId,
                    status = "TARGET_INACTIVE",
                    target = new TargetInfo
                    {
                        type = findMethod,
                        value = request.targetValue,
                        gameObjectPath = targetPath,
                    },
                    preCheck = preCheck,
                    message = $"目标未激活: {targetPath}"
                });
                return;
            }

            preCheck.visible = IsVisible(targetObj);
            if (!preCheck.visible)
            {
                WriteResult(new ClickResult
                {
                    requestId = request.requestId,
                    status = "TARGET_NOT_VISIBLE",
                    target = new TargetInfo
                    {
                        type = findMethod,
                        value = request.targetValue,
                        gameObjectPath = targetPath,
                    },
                    preCheck = preCheck,
                    message = $"目标不可见: {targetPath}"
                });
                return;
            }

            preCheck.interactable = IsInteractable(targetObj);
            if (!preCheck.interactable)
            {
                WriteResult(new ClickResult
                {
                    requestId = request.requestId,
                    status = "TARGET_NOT_INTERACTABLE",
                    target = new TargetInfo
                    {
                        type = findMethod,
                        value = request.targetValue,
                        gameObjectPath = targetPath,
                    },
                    preCheck = preCheck,
                    message = $"目标不可交互: {targetPath}"
                });
                return;
            }

            preCheck.occluded = IsOccluded(targetObj);
            if (preCheck.occluded)
            {
                WriteResult(new ClickResult
                {
                    requestId = request.requestId,
                    status = "TARGET_OCCLUDED",
                    target = new TargetInfo
                    {
                        type = findMethod,
                        value = request.targetValue,
                        gameObjectPath = targetPath,
                    },
                    preCheck = preCheck,
                    message = $"目标被遮挡: {targetPath}"
                });
                return;
            }
        }

        // 4. 计算点击点
        Vector2 clickPoint;
        if (targetObj != null)
            clickPoint = CalcSafePoint(targetObj, request.safePoint ?? "center");
        else
            clickPoint = new Vector2(request.x, Screen.height - request.y);

        // 5. 执行 Raycast
        var pointer = new PointerEventData(EventSystem.current)
        {
            position = clickPoint,
            button = PointerEventData.InputButton.Left,
            pressPosition = clickPoint,
            clickCount = 1,
        };

        var results = new List<RaycastResult>();
        EventSystem.current.RaycastAll(pointer, results);

        string hitPath = "";
        GameObject hitObject = null;
        if (results.Count > 0)
        {
            hitObject = results[0].gameObject;
            hitPath = GetGameObjectPath(hitObject);
        }

        // 6. 校验 eventReceiver
        bool eventReceiverMatch = false;
        if (targetObj != null && hitObject != null)
            eventReceiverMatch = (hitObject == targetObj) || IsChildOf(hitObject, targetObj);
        bool debugOverlayHit = hitObject != null && IsDebugOverlay(hitObject);
        bool debugOverlayBypassed = false;
        string debugOverlayReceiver = (debugOverlayHit || request.bypassDebugOverlay) ? hitPath : "";

        // 7. 派发点击
        try
        {
            string dispatchPath = "";
            GameObject dispatchObject = hitObject;
            if (targetObj != null && request.bypassDebugOverlay && !eventReceiverMatch)
            {
                dispatchObject = targetObj;
                debugOverlayBypassed = true;
                eventReceiverMatch = true;
            }

            if (dispatchObject != null)
            {
                if (results.Count > 0)
                {
                    pointer.pointerCurrentRaycast = results[0];
                    pointer.pointerPressRaycast = results[0];
                }

                GameObject pressTarget = ExecuteEvents.ExecuteHierarchy(dispatchObject, pointer, ExecuteEvents.pointerDownHandler);
                if (pressTarget == null)
                {
                    pressTarget = ExecuteEvents.GetEventHandler<IPointerClickHandler>(dispatchObject);
                }
                if (pressTarget == null)
                {
                    pressTarget = dispatchObject;
                }

                pointer.pointerPress = pressTarget;
                pointer.rawPointerPress = dispatchObject;
                pointer.eligibleForClick = true;

                ExecuteEvents.Execute(pressTarget, pointer, ExecuteEvents.pointerUpHandler);
                ExecuteEvents.Execute(pressTarget, pointer, ExecuteEvents.pointerClickHandler);
                dispatchPath = GetGameObjectPath(pressTarget);
            }

            var clickInfo = new ClickInfo
            {
                method = "event_system",
                safePoint = request.safePoint ?? "center",
                screenPoint = new int[] { (int)clickPoint.x, (int)clickPoint.y },
                eventReceiver = hitPath,
                dispatchTarget = dispatchPath,
                targetGameObject = targetPath,
                receiverMatchTarget = eventReceiverMatch,
                debugOverlayBypassed = debugOverlayBypassed,
                debugOverlayReceiver = debugOverlayReceiver,
            };

            // 判定：坐标模式有命中就算 OK；目标模式需要 eventReceiver 匹配
            if (findMethod == "coordinate")
            {
                if (hitObject != null)
                {
                    WriteResult(new ClickResult
                    {
                        requestId = request.requestId,
                        status = "OK",
                        target = new TargetInfo { type = "coordinate", value = $"{request.x},{request.y}" },
                        click = clickInfo,
                        preCheck = preCheck,
                        message = $"坐标点击命中: {hitPath}"
                    });
                }
                else
                {
                    WriteResult(new ClickResult
                    {
                        requestId = request.requestId,
                        status = "NO_HIT",
                        target = new TargetInfo { type = "coordinate", value = $"{request.x},{request.y}" },
                        click = clickInfo,
                        message = $"坐标点击未命中任何元素"
                    });
                }
            }
            else
            {
                // 目标模式：eventReceiver 必须匹配
                if (!eventReceiverMatch)
                {
                    WriteResult(new ClickResult
                    {
                        requestId = request.requestId,
                        status = "EVENT_RECEIVER_MISMATCH",
                        target = new TargetInfo
                        {
                            type = findMethod,
                            value = request.targetValue,
                            gameObjectPath = targetPath,
                        },
                        click = clickInfo,
                        preCheck = preCheck,
                        message = $"事件接收对象不等于目标: receiver={hitPath}, target={targetPath}"
                    });
                    return;
                }

                WriteResult(new ClickResult
                {
                    requestId = request.requestId,
                    status = "OK",
                    target = new TargetInfo
                    {
                        type = findMethod,
                        value = request.targetValue,
                        gameObjectPath = targetPath,
                    },
                    click = clickInfo,
                    preCheck = preCheck,
                    message = $"点击命中目标: {targetPath}"
                });
            }
        }
        catch (Exception ex)
        {
            Debug.LogError($"[AutoSmoke] 事件派发失败: {ex.Message}");
            WriteResult(new ClickResult
            {
                requestId = request.requestId,
                status = "EVENT_DISPATCH_ERROR",
                target = new TargetInfo { type = findMethod, value = request.targetValue, gameObjectPath = targetPath },
                message = $"Event dispatch error: {ex.Message}"
            });
        }
    }

    // ============================================================
    // 目标查找
    // ============================================================
    private static GameObject FindByTestId(string testId)
    {
        if (string.IsNullOrEmpty(testId)) return null;
        var all = Resources.FindObjectsOfTypeAll<GameObject>();
        foreach (var go in all)
        {
            if (!go.scene.IsValid()) continue;
            var node = go.GetComponent("AutoSmokeNode") as MonoBehaviour;
            if (node != null)
            {
                var t = GetFieldValue<string>(node, "testId");
                if (t == testId) return go;
            }
        }
        return null;
    }

    private static GameObject FindBySemanticId(string semanticId)
    {
        if (string.IsNullOrEmpty(semanticId)) return null;
        var all = Resources.FindObjectsOfTypeAll<GameObject>();
        foreach (var go in all)
        {
            if (!go.scene.IsValid()) continue;
            var node = go.GetComponent("AutoSmokeNode") as MonoBehaviour;
            if (node != null)
            {
                var s = GetFieldValue<string>(node, "semanticId");
                if (s == semanticId) return go;
            }
        }
        return null;
    }

    private static GameObject FindByPath(string path)
    {
        if (string.IsNullOrEmpty(path)) return null;
        var all = Resources.FindObjectsOfTypeAll<GameObject>();
        var suffixMatches = new List<GameObject>();
        foreach (var go in all)
        {
            if (!go.scene.IsValid()) continue;
            string goPath = GetGameObjectPath(go);
            if (goPath == path) return go;
            if (goPath.EndsWith("/" + path) || path.EndsWith("/" + goPath))
            {
                suffixMatches.Add(go);
            }
        }
        if (suffixMatches.Count == 1) return suffixMatches[0];
        return null;
    }

    private static T GetFieldValue<T>(MonoBehaviour mb, string fieldName) where T : class
    {
        try
        {
            var f = mb.GetType().GetField(fieldName,
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (f != null) return f.GetValue(mb) as T;
        }
        catch { }
        return null;
    }

    // ============================================================
    // preCheck 辅助
    // ============================================================
    private static bool IsVisible(GameObject go)
    {
        if (go == null || !go.activeInHierarchy) return false;

        // 检查 CanvasGroup
        var canvasGroup = go.GetComponentInParent<CanvasGroup>();
        if (canvasGroup != null && canvasGroup.alpha < 0.01f) return false;

        // RectTransform 有有效面积即可参与点击。很多游戏 UI 的点击热区
        // 使用透明/低 alpha Graphic 承接事件，不能仅因 Graphic alpha 为 0
        // 判定不可见；否则会与 Runtime UI 树的 visible/effectiveClickable 结果冲突。
        var rt = go.GetComponent<RectTransform>();
        if (rt != null)
        {
            if (rt.rect.width <= 0.5f || rt.rect.height <= 0.5f) return false;
            return true;
        }

        // 检查 Renderer
        var renderer = go.GetComponent<Renderer>();
        if (renderer != null && !renderer.enabled) return false;

        // 检查 Graphic
        var graphic = go.GetComponent<Graphic>();
        if (graphic != null && graphic.color.a < 0.01f) return false;

        return true;
    }

    private static bool IsInteractable(GameObject go)
    {
        var button = go.GetComponent<Button>();
        if (button != null && !button.interactable) return false;

        var toggle = go.GetComponent<Toggle>();
        if (toggle != null && !toggle.interactable) return false;

        var slider = go.GetComponent<Slider>();
        if (slider != null && !slider.interactable) return false;

        return true;
    }

    private static bool IsOccluded(GameObject go)
    {
        // 简单遮挡检测：检查是否有活跃弹窗在最上层
        var allCanvas = Resources.FindObjectsOfTypeAll<Canvas>();
        int targetSort = GetSortingOrder(go);
        foreach (var c in allCanvas)
        {
            if (!c.gameObject.activeInHierarchy) continue;
            int csort = GetSortingOrder(c.gameObject);
            if (csort > targetSort)
            {
                // 上层 Canvas 包含弹窗相关组件
                var graphic = c.GetComponent<Graphic>();
                if (graphic != null && graphic.raycastTarget)
                    return true;
            }
        }
        return false;
    }

    private static int GetSortingOrder(GameObject go)
    {
        var canvas = go.GetComponentInParent<Canvas>();
        if (canvas != null) return canvas.sortingOrder;
        return 0;
    }

    // ============================================================
    // 点击点计算
    // ============================================================
    private static Vector2 CalcSafePoint(GameObject go, string strategy)
    {
        RectTransform rt = go.GetComponent<RectTransform>();
        if (rt != null)
        {
            Vector3[] corners = new Vector3[4];
            rt.GetWorldCorners(corners);
            Canvas canvas = rt.GetComponentInParent<Canvas>();
            Camera uiCamera = (canvas == null || canvas.renderMode == RenderMode.ScreenSpaceOverlay)
                ? null
                : (canvas.worldCamera != null ? canvas.worldCamera : Camera.main);
            float minX = float.MaxValue, minY = float.MaxValue;
            float maxX = float.MinValue, maxY = float.MinValue;
            foreach (var c in corners)
            {
                Vector2 sp = RectTransformUtility.WorldToScreenPoint(uiCamera, c);
                if (sp.x < minX) minX = sp.x;
                if (sp.y < minY) minY = sp.y;
                if (sp.x > maxX) maxX = sp.x;
                if (sp.y > maxY) maxY = sp.y;
            }

            float cx = (minX + maxX) / 2f;
            float cy = (minY + maxY) / 2f;

            if (strategy == "center")
                return new Vector2(cx, cy);

            // innerCenter：向内缩 15%（最小 2px，最大 10px）
            // innerCenter
            float shrinkW = Mathf.Clamp((maxX - minX) * 0.15f, 2f, 10f);
            float shrinkH = Mathf.Clamp((maxY - minY) * 0.15f, 2f, 10f);
            return new Vector2(
                Mathf.Clamp(cx, minX + shrinkW, maxX - shrinkW),
                Mathf.Clamp(cy, minY + shrinkH, maxY - shrinkH)
            );
        }

        // 非 RectTransform：直接用位置
        Vector3 pos = go.transform.position;
        Camera cam = Camera.main;
        if (cam != null)
        {
            Vector3 sp = cam.WorldToScreenPoint(pos);
            return new Vector2(sp.x, sp.y);
        }
        return new Vector2(pos.x, pos.y);
    }

    private static Camera GetUICamera(RectTransform rt)
    {
        Canvas canvas = rt.GetComponentInParent<Canvas>();
        if (canvas == null || canvas.renderMode == RenderMode.ScreenSpaceOverlay)
        {
            return null;
        }
        return canvas.worldCamera != null ? canvas.worldCamera : Camera.main;
    }

    // ============================================================
    // 工具
    // ============================================================
    private static string GetGameObjectPath(GameObject obj)
    {
        if (obj == null) return "";
        string path = obj.name;
        Transform p = obj.transform.parent;
        while (p != null) { path = p.name + "/" + path; p = p.parent; }
        return path;
    }

    private static bool IsChildOf(GameObject child, GameObject parent)
    {
        Transform t = child.transform;
        while (t != null)
        {
            if (t.gameObject == parent) return true;
            t = t.parent;
        }
        return false;
    }

    private static bool IsDebugOverlay(GameObject obj)
    {
        if (obj == null) return false;
        string path = GetGameObjectPath(obj).ToLowerInvariant().Replace("\\", "/");
        if (path.Contains("ui_debuggraphic")
            || path.Contains("graphicdebug")
            || path.Contains("framework/debug")
            || path.Contains("/debug/")
            || path.Contains("debuggraphic")
            || path.Contains("uigmwindow")
            || path.Contains("gmwindow")
            || path.Contains("uiroot2/uigmwindow")
            || path.Contains("/btnshow")
            || path.Contains("btnshow/text"))
        {
            return true;
        }
        Text text = obj.GetComponent<Text>();
        return text != null && string.Equals(text.text, "Debug", StringComparison.OrdinalIgnoreCase);
    }

    private static void WriteResult(ClickResult result)
    {
        try
        {
            result.injectorVersion = INJECTOR_VERSION;
            string json = JsonUtility.ToJson(result, true);
            File.WriteAllText(_resultPath, json);
            Debug.Log($"[AutoSmoke] 结果已写入: {_resultPath} status={result.status}");
        }
        catch (Exception ex)
        {
            Debug.LogError($"[AutoSmoke] 写入结果失败: {ex.Message}");
        }
    }

    // ============================================================
    // 数据类
    // ============================================================
    [Serializable]
    private class ClickRequest
    {
        public string action;
        public string targetType;     // testId / semanticId / pocoPath / coordinate
        public string targetValue;    // testId 值 / 路径等
        public string safePoint;      // center / innerCenter
        public int x;                 // 坐标兜底
        public int y;
        public int[] gameResolution;
        public string requestId;
        public string timestamp;
        public bool bypassDebugOverlay;
    }

    [Serializable]
    private class ClickResult
    {
        public string injectorVersion;
        public string requestId;
        public string status;          // OK / TARGET_NOT_FOUND / TARGET_INACTIVE / etc.
        public string message;

        public TargetInfo target;      // 目标元素信息
        public ClickInfo click;        // 点击详情
        public PreCheckResult preCheck; // 点击前校验
    }

    [Serializable]
    private class TargetInfo
    {
        public string type;             // testId / semanticId / pocoPath / coordinate
        public string value;            // 原始值
        public string gameObjectPath;   // 实际 GameObject 路径
    }

    [Serializable]
    private class ClickInfo
    {
        public string method;           // event_system
        public string safePoint;        // center / innerCenter
        public int[] screenPoint;       // 实际点击的屏幕坐标
        public string eventReceiver;    // 收到事件的对象路径
        public string dispatchTarget;
        public string targetGameObject; // 目标对象路径
        public bool receiverMatchTarget;// 事件接收对象 == 目标
        public bool debugOverlayBypassed;
        public string debugOverlayReceiver;
    }

    [Serializable]
    private class PreCheckResult
    {
        public bool exists;
        public bool activeInHierarchy = true;
        public bool visible = true;
        public bool interactable = true;
        public bool occluded;
    }
}
