# Unity 界面有效区域自动定位方案

## 1. 背景问题

在 Unity 游戏自动化测试中，提取界面元素时经常会遇到一个问题：

- 截图中只希望提取红框内的游戏 UI 区域。
- 不希望把 Unity Editor、Console、Scene View、调试按钮等非目标区域识别进去。
- 不希望使用固定截图坐标，因为不同分辨率、窗口缩放、设备比例都会导致坐标失效。
- SLG 游戏中主城、大地图、背包、弹窗等界面区域大小不同，不能写死。

因此，自动化系统不能依赖“截图像素红框”，而应该从 Unity 的 UI 布局系统中自动获取当前有效界面区域。

## 2. 目标

本方案用于解决：

- 自动定位当前页面根区域。
- 自动定位当前弹窗区域。
- 自动过滤非当前界面元素。
- 不受分辨率、屏幕比例、Game View 缩放影响。
- 为 UI 元素提取、自动点击、页面关系图、异常检测提供稳定范围。

最终目标：

```text
不靠截图坐标找红框，而是通过 RectTransform 找到当前有效 UI 容器。
```

## 3. 核心原则

识别有效区域时，应遵循以下优先级：

```text
1. AutoSmokeNode 显式标注的 PageRoot/DialogRoot
2. 当前最上层弹窗 Dialog/Popup
3. Canvas 下最大可见业务面板
4. SceneStateExporter 导出的场景交互区域
5. 图像识别或固定比例兜底
```

其中第 1、2、3 层应作为主要方案。  
第 5 层只能作为临时兜底，不应作为长期主方案。

## 4. 推荐方案一：页面根节点显式标注

### 4.1 适用场景

适用于背包、邮件、任务、建筑升级、商城、联盟、排行榜等明确页面。

### 4.2 标注方式

在 Unity 页面根节点上挂载 `AutoSmokeNode`：

```csharp
using UnityEngine;

public class AutoSmokeNode : MonoBehaviour
{
    public string testId;
    public string nodeType;
    public bool clickable;
    public bool isPageRoot;
    public bool isDialogRoot;
    public bool visible = true;
}
```

示例配置：

```text
testId = bag.page.root
nodeType = PageRoot
isPageRoot = true
isDialogRoot = false
```

弹窗示例：

```text
testId = maincity.popup.upgrade.root
nodeType = DialogRoot
isPageRoot = false
isDialogRoot = true
```

### 4.3 优点

- 最稳定。
- 不依赖节点名称。
- 不依赖截图坐标。
- 不受分辨率影响。
- 可直接作为元素提取范围。

## 5. 推荐方案二：自动推断最大可见业务面板

当项目暂时没有完整标注时，IDE 可以自动推断当前有效区域。

### 5.1 推断条件

候选节点需要满足：

- `activeInHierarchy=true`
- 挂载 `RectTransform`
- 位于有效 `Canvas` 下
- 面积大于最小阈值
- 包含可见子节点
- 包含 `Button`、`Text`、`Image`、`ScrollRect`、`Toggle` 等 UI 组件
- 不属于 Debug、Logo、EventSystem、PocoManager 等系统节点

### 5.2 排序规则

候选面板可按以下规则评分：

| 规则 | 加分 |
| --- | --- |
| 面积较大 | +20 |
| 包含 Button | +20 |
| 包含 Text/TMP_Text | +10 |
| 包含 ScrollRect | +10 |
| siblingIndex 更靠后 | +10 |
| Canvas sortingOrder 更高 | +20 |
| 名称包含 Panel/Dialog/Popup/View/Page | +10 |
| 包含 Mask/Blur | +10 |

扣分项：

| 规则 | 扣分 |
| --- | --- |
| 名称包含 Debug | -50 |
| 名称包含 Logo | -30 |
| 名称包含 EventSystem | -50 |
| 面积过小 | -30 |
| 无任何可见子元素 | -50 |

最终选择分数最高的候选节点作为当前有效页面区域。

## 6. 推荐方案三：优先识别最上层弹窗

当界面上存在弹窗时，自动化应优先处理弹窗，而不是底层页面。

### 6.1 弹窗识别规则

满足以下任一条件，可识别为弹窗候选：

- `AutoSmokeNode.isDialogRoot=true`
- `nodeType=DialogRoot` 或 `nodeType=Popup`
- 节点名称包含 `Dialog`、`Popup`、`Modal`
- 包含 `Mask` 或 `Blur` 子节点
- Canvas `sortingOrder` 高于普通页面
- siblingIndex 靠后
- 面积小于全屏但大于最小弹窗阈值
- 包含关闭、取消、确定等按钮

### 6.2 弹窗优先级

有效区域选择规则：

```text
如果存在弹窗：
    当前有效区域 = 最上层弹窗区域
否则：
    当前有效区域 = 当前页面根区域
```

这样可以避免自动点击到底层页面，减少误操作。

## 7. RectTransform 屏幕区域计算

### 7.1 获取屏幕坐标

Unity UI 的真实位置应通过 `RectTransform.GetWorldCorners` 获取。

```csharp
using UnityEngine;

public static class AutoSmokeRectUtil
{
    public static Rect GetScreenRect(RectTransform rectTransform, Camera uiCamera)
    {
        Vector3[] corners = new Vector3[4];
        rectTransform.GetWorldCorners(corners);

        Vector2 bottomLeft = RectTransformUtility.WorldToScreenPoint(uiCamera, corners[0]);
        Vector2 topRight = RectTransformUtility.WorldToScreenPoint(uiCamera, corners[2]);

        float xMin = Mathf.Min(bottomLeft.x, topRight.x);
        float xMax = Mathf.Max(bottomLeft.x, topRight.x);
        float yMin = Mathf.Min(bottomLeft.y, topRight.y);
        float yMax = Mathf.Max(bottomLeft.y, topRight.y);

        return Rect.MinMaxRect(xMin, yMin, xMax, yMax);
    }
}
```

### 7.2 转为归一化坐标

为了适配不同分辨率，需要同时输出归一化区域。

```csharp
public static Rect ToNormalizedRect(Rect screenRect)
{
    return new Rect(
        screenRect.xMin / Screen.width,
        screenRect.yMin / Screen.height,
        screenRect.width / Screen.width,
        screenRect.height / Screen.height
    );
}
```

### 7.3 输出示例

```json
{
  "testId": "bag.page.root",
  "nodeType": "PageRoot",
  "screenSize": [1170, 2532],
  "screenRect": [0, 120, 1170, 2410],
  "normalizedRect": [0.0, 0.047, 1.0, 0.904],
  "source": "AutoSmokeNode.isPageRoot"
}
```

## 8. 元素过滤规则

定位到有效区域后，元素提取时只保留区域内元素。

### 8.1 中心点过滤

如果元素中心点在有效区域内，则保留：

```text
element.center in activeRect
```

### 8.2 矩形交集过滤

如果元素矩形与有效区域有交集，也可保留：

```text
element.rect intersects activeRect
```

推荐策略：

```text
按钮、输入框、文本：优先使用中心点过滤
大面板、ScrollView、列表项：使用矩形交集过滤
```

### 8.3 遮挡过滤

元素即使在有效区域内，也需要判断是否被遮挡：

- 使用 `GraphicRaycaster.Raycast` 检查点击点最上层命中对象。
- 如果命中对象不是目标元素或其子节点，则标记为 `covered=true`。
- 被遮挡元素不应参与自动点击。

## 9. EventSystem 命中验证

仅靠 RectTransform 判断“在区域内”还不够，还需要判断是否真实可点。

### 9.1 RaycastAll 示例

```csharp
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;

public static class AutoSmokeHitTest
{
    public static List<RaycastResult> RaycastUI(Vector2 screenPoint)
    {
        var results = new List<RaycastResult>();

        if (EventSystem.current == null)
        {
            return results;
        }

        var eventData = new PointerEventData(EventSystem.current)
        {
            position = screenPoint
        };

        EventSystem.current.RaycastAll(eventData, results);
        return results;
    }
}
```

### 9.2 判断用途

可用于：

- 判断按钮是否被弹窗遮挡。
- 判断当前点击点实际命中的对象。
- 判断红框区域内是否存在真实可交互对象。
- 判断空页面或半透明遮罩。

## 10. Game View 缩放与分辨率适配

Unity Editor 的 Game View 可能显示为 `0.27x`、`Scale 0.5x` 等缩放。  
自动化系统不应使用 Editor 窗口截图坐标作为游戏内坐标。

正确做法：

```text
Unity 侧使用 Screen.width / Screen.height
Unity 侧使用 RectTransformUtility 计算屏幕坐标
IDE 接收 Unity 导出的 screenRect / normalizedRect
IDE 点击时按设备或窗口真实分辨率换算
```

错误做法：

```text
从整张桌面截图里裁剪红框
记录 Unity Editor 窗口里的像素坐标
根据 Game View 的显示缩放估算坐标
```

## 11. IDE 与 Unity 的数据接口

Unity 侧导出当前有效区域：

```json
{
  "activeRegion": {
    "testId": "bag.page.root",
    "type": "PageRoot",
    "screenRect": [0, 120, 1170, 2410],
    "normalizedRect": [0.0, 0.047, 1.0, 0.904],
    "source": "AutoSmokeNode",
    "confidence": "high"
  },
  "elements": [
    {
      "testId": "bag.tab.special",
      "type": "Button",
      "screenRect": [20, 260, 180, 340],
      "normalizedRect": [0.017, 0.102, 0.137, 0.032],
      "clickable": true,
      "covered": false
    }
  ]
}
```

IDE 使用规则：

- 只展示 `activeRegion` 内元素。
- 自动点击前验证 `covered=false`。
- 报告中保存 `screenRect` 和 `normalizedRect`。
- 失败时保存有效区域截图、UI 树、Raycast 命中结果。

## 12. 主城和大地图的特殊处理

主城和大地图中很多元素不是 UGUI，而是场景对象。

这类对象应通过 `SceneStateExporter` 导出：

```json
{
  "scene": "WorldMap",
  "camera": "MainCamera",
  "screenSize": [1170, 2532],
  "activeRegion": {
    "testId": "worldmap.visible.region",
    "type": "SceneRegion",
    "screenRect": [0, 0, 1170, 2532],
    "normalizedRect": [0, 0, 1, 1]
  },
  "objects": [
    {
      "testId": "worldmap.resource.wood.1024_2048",
      "type": "Resource",
      "worldPos": [1024, 0, 2048],
      "screenRect": [320, 800, 390, 870],
      "normalizedRect": [0.273, 0.316, 0.059, 0.027],
      "clickable": true,
      "visible": true
    }
  ]
}
```

场景对象屏幕坐标通过：

```csharp
Camera.main.WorldToScreenPoint(worldPosition)
```

必要时结合 `Renderer.bounds` 或 `Collider.bounds` 计算屏幕矩形。

## 13. 异常情况处理

### 13.1 找不到 PageRoot

处理方式：

- 回退到最大可见业务面板。
- 若仍失败，回退到当前 Canvas 区域。
- 报告标记 `activeRegion.confidence=low`。

### 13.2 多个弹窗同时存在

处理方式：

- 选择 Canvas sortingOrder 最高的弹窗。
- sortingOrder 相同则选 siblingIndex 最大的弹窗。
- 若仍冲突，报告 `MULTI_DIALOG_CONFLICT`。

### 13.3 有遮罩但无弹窗

处理方式：

- 检查是否是 Loading、Mask、Guide 引导层。
- 若持续超过阈值，标记为卡死或阻断。
- 输出遮罩节点路径与截图。

### 13.4 有效区域为空

处理方式：

- 检查 Canvas 是否激活。
- 检查可见元素数量。
- 检查截图是否纯色或近似纯色。
- 标记为空页面风险。

## 14. 验收标准

### 14.1 分辨率适配验收

- 在至少 2 种分辨率下，有效区域 `normalizedRect` 基本一致。
- 同一页面在不同设备上能定位到同一 `testId` 的 PageRoot。
- 不依赖 Unity Editor Game View 的显示缩放。

### 14.2 页面区域识别验收

- 有 `AutoSmokeNode.isPageRoot=true` 时，优先使用标注区域。
- 无标注时，最大可见业务面板可被正确识别。
- Debug、Logo、Console、EventSystem 不会进入有效区域。

### 14.3 弹窗区域识别验收

- 弹窗存在时，优先提取弹窗内元素。
- 弹窗关闭后，自动恢复到底层 PageRoot。
- 多弹窗时选择最上层弹窗。

### 14.4 元素过滤验收

- 有效区域外元素不会进入执行候选。
- 被弹窗遮挡的底层按钮不会被自动点击。
- 每个可点击元素都带 `screenRect` 和 `normalizedRect`。

## 15. 落地建议

第一阶段：

- IDE 支持读取 Unity 导出的 `activeRegion`。
- Unity 侧实现 RectTransform 区域导出。
- 先用最大可见业务面板兜底。

第二阶段：

- 关键页面根节点补充 `AutoSmokeNode.isPageRoot=true`。
- 关键弹窗根节点补充 `AutoSmokeNode.isDialogRoot=true`。
- 报告中展示有效区域来源与可信度。

第三阶段：

- 接入 EventSystem RaycastAll，判断遮挡与真实命中。
- 主城和大地图接入 `SceneStateExporter`。
- 将区域识别失败加入验收门禁。

## 16. 结论

要自动定位截图中的红框区域，不能依赖截图像素坐标。  
正确做法是从 Unity 内部导出当前有效 UI 容器的 `RectTransform` 区域，并同时保存屏幕坐标和归一化坐标。

推荐最终方案：

```text
AutoSmokeNode 标注 PageRoot/DialogRoot
+ 最大可见业务面板自动推断
+ RectTransform 屏幕区域计算
+ normalizedRect 分辨率适配
+ EventSystem RaycastAll 遮挡验证
+ SceneStateExporter 覆盖主城和大地图
```

这样可以稳定定位当前页面或弹窗区域，并保证元素提取、点击执行和测试报告在不同分辨率下保持一致。
