using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using TMPro;

/// <summary>
/// 运行态 UI 树导出器
/// 遍历当前场景中的 Canvas/UI 元素，输出运行态节点数据。
/// 扩展字段：elementType/interactionType/clickTargetNode/effectiveClickable 等
/// </summary>
public static class RuntimeUITreeDumper
{
    public static List<RuntimeUITreeNode> Dump(bool includeInvisible = false)
    {
        var nodes = new List<RuntimeUITreeNode>();
        var canvases = GameObject.FindObjectsOfType<Canvas>();

        foreach (var canvas in canvases)
        {
            if (!canvas.gameObject.activeInHierarchy && !includeInvisible) continue;
            DumpTransform(canvas.transform, "", nodes, includeInvisible);
        }

        return nodes;
    }

    private static void DumpTransform(Transform parent, string parentPath,
                                       List<RuntimeUITreeNode> nodes, bool includeInvisible)
    {
        for (int i = 0; i < parent.childCount; i++)
        {
            Transform child = parent.GetChild(i);
            GameObject go = child.gameObject;

            if (!go.activeInHierarchy && !includeInvisible) continue;

            string path = string.IsNullOrEmpty(parentPath)
                ? go.name
                : parentPath + "/" + go.name;

            string spriteName = GetSpriteName(go);
            string clickTarget = FindClickTargetNode(go);
            bool isIcon = IsIconNode(go);
            bool isCell = IsCellNode(go);
            bool isMask = IsMaskNode(go);
            bool isDragScroll = IsDragOrScrollNode(go);
            bool compClickable = IsClickable(go);
            bool isInteractiveIcon = isIcon && !string.IsNullOrEmpty(spriteName)
                                     && IsRaycastTarget(go) && !string.IsNullOrEmpty(clickTarget);

            string elementType = InferElementType(go, compClickable, isInteractiveIcon,
                                                   isCell, isMask, isDragScroll);
            string interactionType = InferInteractionType(elementType);
            bool effectiveClickable = compClickable || isInteractiveIcon || isCell
                                       || isMask || isDragScroll;

            var node = new RuntimeUITreeNode
            {
                runtimePath = path,
                nodeName = go.name,
                instanceId = go.GetInstanceID(),
                activeInHierarchy = go.activeInHierarchy,
                visible = IsVisible(go),
                clickable = compClickable,
                interactable = IsInteractable(go),
                raycastTarget = IsRaycastTarget(go),
                text = GetText(go),
                components = GetComponentList(go),
                spriteName = spriteName,
                atlasName = GetAtlasName(go),
                screenRect = GetScreenRect(go),
                normalizedRect = GetNormalizedRect(go),
                pageId = GetPageId(go),
                siblingIndex = child.GetSiblingIndex(),
                eventReceivers = GetEventReceivers(go),
                // 扩展字段
                elementType = elementType,
                interactionType = interactionType,
                clickTargetNode = string.IsNullOrEmpty(clickTarget) && compClickable ? path : clickTarget,
                clickableReason = GetClickableReason(go, compClickable, isInteractiveIcon, isCell, isMask),
                effectiveClickable = effectiveClickable,
                isIcon = isIcon,
                isInteractiveIcon = isInteractiveIcon,
                isCell = isCell,
                isMask = isMask,
                isDragArea = isDragScroll && (go.GetComponent<Scrollbar>() != null || go.GetComponent<Slider>() != null),
                isScrollArea = isDragScroll && go.GetComponent<ScrollRect>() != null,
            };

            nodes.Add(node);

            if (child.childCount > 0)
            {
                DumpTransform(child, path, nodes, includeInvisible);
            }
        }
    }

    // ========== 字段推断 ==========

    private static string InferElementType(GameObject go, bool compClickable,
                                            bool isInteractiveIcon, bool isCell,
                                            bool isMask, bool isDragScroll)
    {
        if (compClickable)
        {
            if (go.GetComponent<Toggle>() != null) return "tab";
            if (go.GetComponent<Button>() != null)
            {
                string name = go.name.ToLower();
                if (name.Contains("close") || name.Contains("关闭")) return "close_button";
                return "button";
            }
            if (go.GetComponent<Dropdown>() != null) return "list_row";
            if (go.GetComponent<Slider>() != null) return "drag_area";
            if (go.GetComponent<EventTrigger>() != null)
            {
                string pn = go.name.ToLower();
                if (pn.Contains("scroll") || pn.Contains("drag")) return isDragScroll ? "scroll_area" : "clickable_unknown";
                return "clickable_unknown";
            }
            return "button";
        }
        if (isInteractiveIcon) return "interactive_icon";
        if (isCell) return "item_cell";
        if (isMask) return "popup_mask";
        if (isDragScroll)
        {
            if (go.GetComponent<ScrollRect>() != null) return "scroll_area";
            return "drag_area";
        }
        return "";
    }

    private static string InferInteractionType(string elementType)
    {
        switch (elementType)
        {
            case "scroll_area": return "scroll";
            case "drag_area":   return "drag";
            case "popup_mask":
            case "blank_close_area": return "blank_close";
            case "tab": return "click";
            default: return "click";
        }
    }

    private static string GetClickableReason(GameObject go, bool compClickable,
                                               bool isIcon, bool isCell, bool isMask)
    {
        if (compClickable)
        {
            if (go.GetComponent<Button>() != null) return "Button component";
            if (go.GetComponent<Toggle>() != null) return "Toggle component";
            if (go.GetComponent<EventTrigger>() != null) return "EventTrigger component";
            if (go.GetComponent<Dropdown>() != null) return "Dropdown component";
            return "has interactive component";
        }
        if (isIcon) return "Image.raycastTarget=true + clickable parent";
        if (isCell) return "cell naming + parent clickable";
        if (isMask) return "mask/blocker naming + raycastTarget";
        return "";
    }

    // ========== 原有判断 ==========

    private static bool IsVisible(GameObject go)
    {
        if (!go.activeInHierarchy) return false;
        if (!go.GetComponent<RectTransform>()) return false;
        var graphic = go.GetComponent<Graphic>();
        if (graphic != null) return graphic.IsActive() && graphic.enabled;
        var renderer = go.GetComponent<Renderer>();
        if (renderer != null) return renderer.enabled;
        return true;
    }

    private static bool IsClickable(GameObject go)
    {
        if (go.GetComponent<Button>() != null) return true;
        if (go.GetComponent<Toggle>() != null) return true;
        if (go.GetComponent<Dropdown>() != null) return true;
        if (go.GetComponent<Slider>() != null) return true;
        if (go.GetComponent<EventTrigger>() != null) return true;
        return false;
    }

    private static bool IsInteractable(GameObject go)
    {
        var button = go.GetComponent<Button>();
        if (button != null) return button.interactable;
        var toggle = go.GetComponent<Toggle>();
        if (toggle != null) return toggle.interactable;
        var slider = go.GetComponent<Slider>();
        if (slider != null) return slider.interactable;
        return true;
    }

    private static bool IsRaycastTarget(GameObject go)
    {
        var graphic = go.GetComponent<Graphic>();
        if (graphic != null) return graphic.raycastTarget;
        return false;
    }

    // ========== 新增检测 ==========

    private static string FindClickTargetNode(GameObject go)
    {
        Transform t = go.transform;
        for (int depth = 0; depth < 5 && t != null; depth++, t = t.parent)
        {
            GameObject obj = t.gameObject;
            if (obj.GetComponent<Button>() != null) return BuildPath(obj.transform);
            if (obj.GetComponent<Toggle>() != null) return BuildPath(obj.transform);
            if (obj.GetComponent<EventTrigger>() != null) return BuildPath(obj.transform);
            if (obj.GetComponent<Dropdown>() != null) return BuildPath(obj.transform);
            if (obj.GetComponent<Slider>() != null) return BuildPath(obj.transform);
            var comps = obj.GetComponents<Component>();
            foreach (var c in comps)
            {
                if (c != null && c is IPointerClickHandler)
                    return BuildPath(obj.transform);
            }
        }
        return "";
    }

    private static string BuildPath(Transform t)
    {
        if (t == null) return "";
        var segments = new List<string>();
        var current = t;
        while (current != null)
        {
            segments.Insert(0, current.name);
            current = current.parent;
        }
        return string.Join("/", segments);
    }

    private static bool IsIconNode(GameObject go)
    {
        var img = go.GetComponent<Image>();
        if (img != null && img.sprite != null) return true;
        var raw = go.GetComponent<RawImage>();
        if (raw != null && raw.texture != null) return true;
        return false;
    }

    private static bool IsCellNode(GameObject go)
    {
        string name = go.name.ToLower();
        if (name.Contains("item") || name.Contains("cell") || name.Contains("slot")
            || name.Contains("grid") || name.Contains("reward") || name.Contains("goods")
            || name.Contains("card") || name.Contains("row") || name.Contains("listitem"))
        {
            // 确认自身或子节点有 sprite/text
            if (go.GetComponent<Image>() != null || go.GetComponent<RawImage>() != null
                || go.GetComponentInChildren<Image>() != null
                || go.GetComponentInChildren<TMP_Text>() != null)
                return true;
        }
        // 父级路径包含格子关键词
        Transform p = go.transform.parent;
        if (p != null)
        {
            string pn = p.name.ToLower();
            if ((pn.Contains("item") || pn.Contains("cell") || pn.Contains("slot")
                 || pn.Contains("grid") || pn.Contains("reward") || pn.Contains("content"))
                && (go.GetComponent<Image>() != null || go.GetComponent<TMP_Text>() != null))
                return true;
        }
        return false;
    }

    private static bool IsMaskNode(GameObject go)
    {
        string name = go.name.ToLower();
        if (name.Contains("mask") || name.Contains("blocker") || name.Contains("closearea")
            || name.Contains("touchclose") || name.Contains("clickclose") || name.Contains("bg"))
        {
            var img = go.GetComponent<Image>();
            if (img != null && img.raycastTarget) return true;
        }
        return false;
    }

    private static bool IsDragOrScrollNode(GameObject go)
    {
        if (go.GetComponent<ScrollRect>() != null) return true;
        if (go.GetComponent<Scrollbar>() != null) return true;
        if (go.GetComponent<Slider>() != null) return true;
        return false;
    }

    // ========== 原字段提取 ==========

    private static string GetText(GameObject go)
    {
        var tmp = go.GetComponent<TMP_Text>();
        if (tmp != null && !string.IsNullOrEmpty(tmp.text)) return tmp.text;
        var text = go.GetComponent<Text>();
        if (text != null && !string.IsNullOrEmpty(text.text)) return text.text;
        return "";
    }

    private static List<string> GetComponentList(GameObject go)
    {
        var comps = new List<string>();
        var components = go.GetComponents<Component>();
        foreach (var c in components)
        {
            if (c != null)
                comps.Add(c.GetType().Name);
        }
        return comps;
    }

    private static string GetSpriteName(GameObject go)
    {
        var image = go.GetComponent<Image>();
        if (image != null && image.sprite != null) return image.sprite.name;
        var raw = go.GetComponent<RawImage>();
        if (raw != null && raw.texture != null) return raw.texture.name;
        return "";
    }

    private static string GetAtlasName(GameObject go)
    {
        var image = go.GetComponent<Image>();
        if (image != null && image.sprite != null) return image.sprite.texture.name;
        return "";
    }

    private static List<float> GetScreenRect(GameObject go)
    {
        var rectTransform = go.GetComponent<RectTransform>();
        if (rectTransform == null) return new List<float>();

        var corners = new Vector3[4];
        rectTransform.GetWorldCorners(corners);

        Camera uiCamera = GetUICamera(rectTransform);
        Vector2 p0 = RectTransformUtility.WorldToScreenPoint(uiCamera, corners[0]); // bottom-left
        Vector2 p1 = RectTransformUtility.WorldToScreenPoint(uiCamera, corners[1]); // top-left
        Vector2 p2 = RectTransformUtility.WorldToScreenPoint(uiCamera, corners[2]); // top-right
        Vector2 p3 = RectTransformUtility.WorldToScreenPoint(uiCamera, corners[3]); // bottom-right

        float minX = Mathf.Min(p0.x, p1.x, p2.x, p3.x);
        float maxX = Mathf.Max(p0.x, p1.x, p2.x, p3.x);
        float minY = Mathf.Min(p0.y, p1.y, p2.y, p3.y);
        float maxY = Mathf.Max(p0.y, p1.y, p2.y, p3.y);

        // Unity screen coordinates are bottom-left origin; screenshots use top-left origin.
        float top = Screen.height - maxY;
        float bottom = Screen.height - minY;

        return new List<float>
        {
            Mathf.Round(minX),
            Mathf.Round(top),
            Mathf.Round(maxX),
            Mathf.Round(bottom)
        };
    }

    private static List<float> GetNormalizedRect(GameObject go)
    {
        var rectTransform = go.GetComponent<RectTransform>();
        if (rectTransform == null) return new List<float>();

        int screenW = Screen.width;
        int screenH = Screen.height;
        if (screenW == 0 || screenH == 0) return new List<float>();

        var sr = GetScreenRect(go);
        if (sr == null || sr.Count < 4) return new List<float>();

        return new List<float>
        {
            (float)Math.Round(sr[0] / screenW, 4),
            (float)Math.Round(sr[1] / screenH, 4),
            (float)Math.Round(sr[2] / screenW, 4),
            (float)Math.Round(sr[3] / screenH, 4)
        };
    }

    private static Camera GetUICamera(RectTransform rectTransform)
    {
        Canvas canvas = rectTransform.GetComponentInParent<Canvas>();
        if (canvas == null) return null;
        if (canvas.renderMode == RenderMode.ScreenSpaceOverlay) return null;
        if (canvas.worldCamera != null) return canvas.worldCamera;
        return Camera.main;
    }

    private static string GetPageId(GameObject go)
    {
        Transform current = go.transform;
        while (current != null)
        {
            if (current.GetComponent<Canvas>() != null)
                return current.gameObject.name;
            string name = current.gameObject.name;
            if (name.Contains("Panel") || name.Contains("Dialog") ||
                name.Contains("View") || name.Contains("Window") || name.Contains("Page"))
                return name;
            current = current.parent;
        }
        return "unknown";
    }

    private static List<string> GetEventReceivers(GameObject go)
    {
        var receivers = new List<string>();
        if (go.GetComponent<Button>() != null) receivers.Add("Button");
        if (go.GetComponent<Toggle>() != null) receivers.Add("Toggle");
        if (go.GetComponent<Slider>() != null) receivers.Add("Slider");
        if (go.GetComponent<Dropdown>() != null) receivers.Add("Dropdown");
        if (go.GetComponent<InputField>() != null) receivers.Add("InputField");
        if (go.GetComponent<EventTrigger>() != null) receivers.Add("EventTrigger");
        if (go.GetComponent<IPointerClickHandler>() != null) receivers.Add("IPointerClickHandler");
        return receivers;
    }

    [Serializable]
    public class RuntimeUITreeNode
    {
        public string runtimePath;
        public string nodeName;
        public int instanceId;
        public bool activeInHierarchy;
        public bool visible;
        public bool clickable;
        public bool interactable;
        public bool raycastTarget;
        public string text;
        public List<string> components;
        public string spriteName;
        public string atlasName;
        public List<float> screenRect;
        public List<float> normalizedRect;
        public string pageId;
        public int siblingIndex;
        public List<string> eventReceivers;
        // 扩展字段
        public string elementType;
        public string interactionType;
        public string clickTargetNode;
        public string clickableReason;
        public bool effectiveClickable;
        public bool isIcon;
        public bool isInteractiveIcon;
        public bool isCell;
        public bool isMask;
        public bool isDragArea;
        public bool isScrollArea;
    }
}
