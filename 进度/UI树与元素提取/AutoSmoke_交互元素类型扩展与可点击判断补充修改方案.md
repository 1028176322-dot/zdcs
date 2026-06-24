# AutoSmoke 交互元素类型扩展与可点击判断补充修改方案

## 1. 背景

当前运行态 UI 树中的 `clickable` 主要按 Unity 组件判断：

```text
Button
Toggle
EventTrigger
IPointerClickHandler
```

IDE 中的可点击数量通常是：

```text
clickableCount = nodes 中 clickable=true 的数量
```

这个口径只能表示：

```text
组件层面可能可点击
```

但 SLG 游戏里的交互目标远不止 Button。

例如：

```text
道具图标
奖励图标
活动入口图标
背包格子
商城商品格子
建筑本体
建筑呼出菜单按钮
弹窗空白关闭区域
引导高亮区域
大地图资源点
红点气泡
列表行
地图拖拽区域
缩放区域
```

因此需要把“可点击判断”升级为“交互元素识别”。

## 2. 修改目标

本方案目标：

```text
不再只识别 Button/Toggle/EventTrigger。
将玩家可交互的 UI、图标、格子、场景对象、空白区域、拖拽区域全部纳入统一交互元素库。
```

最终 IDE 中应该能区分：

```text
组件可点击
图标可点击
格子可点击
场景对象可点击
空白关闭区域
拖拽/滚动/缩放区域
已点击确认元素
```

而不是只显示：

```text
可点击：11
```

建议显示：

```text
组件可点击：11
图标可点击：37
格子可点击：24
场景对象：18
拖拽/滚动区域：5
有效可交互：62
点击已确认：8
```

## 3. 核心原则

### 3.1 clickable 不等于最终可自动点击

需要分清：

| 字段 | 含义 |
|---|---|
| `clickable` | 组件层面可能可点击 |
| `interactable` | 当前运行状态下可交互 |
| `effectiveClickable` | 当前可见、可交互、无遮挡、可作为点击目标 |
| `interactionType` | 交互方式，例如 click/drag/scroll/pinch/blank_close |
| `elementType` | 元素类型，例如 button/icon/scene_object |
| `clickTargetNode` | 真正接收点击的节点 |
| `visualNode` | 用户看到的节点 |
| `click_confirmed` | 已通过 Unity 注入点击验证 |

### 3.2 visualNode 与 clickTargetNode 必须分离

很多元素看到的是图标，但真正接收点击的是父级容器。

示例：

```text
visualNode:
BagPanel/List/Item_001/Icon

clickTargetNode:
BagPanel/List/Item_001
```

因此后续自动点击绝不能只点 `Image` 图标本身。

### 3.3 交互元素不一定都是 click

交互方式需要扩展：

```text
click
long_press
double_click
drag
scroll
pinch
blank_close
open_tip
select
```

## 4. 需要扩展的交互元素类型

建议统一定义 `elementType`：

| elementType | 说明 |
|---|---|
| `button` | 标准按钮 |
| `tab` | 页签/Toggle |
| `interactive_icon` | 可点击图标 |
| `item_cell` | 道具格子 |
| `reward_cell` | 奖励格子 |
| `shop_item_cell` | 商城商品格子 |
| `task_row` | 任务条目 |
| `mail_row` | 邮件条目 |
| `activity_entry` | 活动入口 |
| `list_row` | 普通列表行 |
| `popup_mask` | 弹窗遮罩 |
| `blank_close_area` | 点击空白关闭区域 |
| `scene_object` | 场景对象 |
| `building_object` | 主城/外城建筑 |
| `building_menu_button` | 建筑呼出菜单按钮 |
| `map_object` | 大地图对象 |
| `resource_point` | 大地图资源点 |
| `npc_object` | NPC/怪物/敌人 |
| `guide_target` | 引导目标 |
| `loading_retry` | Loading/重连重试 |
| `reconnect_button` | 重连按钮 |
| `drag_area` | 拖拽区域 |
| `scroll_area` | 滚动区域 |
| `pinch_area` | 缩放区域 |
| `bubble_entry` | 红点/气泡/浮标入口 |
| `clickable_unknown` | 未知可交互候选 |

## 5. Unity 运行态 UI 树导出修改

当前文件：

```text
E:\zdcs\AutoSmoke\tools\AutoSmokeUITreeExporter.cs
```

当前 `clickable` 判断：

```csharp
if (comps.Contains("Button") || comps.Contains("Toggle")) return true;
if (comps.Contains("EventTrigger")) return true;
foreach (var comp in go.GetComponents<Component>())
{
    if (comp != null && comp is IPointerClickHandler)
        return true;
}
return false;
```

这需要保留，但不能作为唯一判断。

### 5.1 新增字段

`UINode` 建议增加：

```csharp
public string elementType;
public string interactionType;
public string clickableReason;
public bool effectiveClickable;
public string visualNode;
public string clickTargetNode;
public string clickTargetReason;
public string spriteName;
public string atlasName;
public bool isIcon;
public bool isInteractiveIcon;
public bool isCell;
public bool isMask;
public bool isDragArea;
public bool isScrollArea;
public List<string> interactionRisks;
```

### 5.2 新增点击目标查找

新增函数：

```csharp
private static string FindClickTargetNode(GameObject go)
{
    Transform t = go.transform;

    for (int depth = 0; depth < 5 && t != null; depth++, t = t.parent)
    {
        GameObject obj = t.gameObject;

        if (obj.GetComponent<Button>() != null)
            return BuildPath(obj.transform);

        if (obj.GetComponent<Toggle>() != null)
            return BuildPath(obj.transform);

        if (obj.GetComponent<EventTrigger>() != null)
            return BuildPath(obj.transform);

        foreach (var comp in obj.GetComponents<Component>())
        {
            if (comp != null && comp is IPointerClickHandler)
                return BuildPath(obj.transform);
        }
    }

    return "";
}
```

说明：

```text
对图标、格子、奖励项，向父级最多查 5 层。
找到真正有点击能力的父级节点后，作为 clickTargetNode。
```

### 5.3 新增图标识别

新增：

```csharp
private static bool IsIconNode(GameObject go)
{
    var img = go.GetComponent<Image>();
    if (img != null && img.sprite != null) return true;

    var raw = go.GetComponent<RawImage>();
    if (raw != null && raw.texture != null) return true;

    return false;
}
```

新增：

```csharp
private static string GetSpriteName(GameObject go)
{
    var img = go.GetComponent<Image>();
    if (img != null && img.sprite != null)
        return img.sprite.name;

    var raw = go.GetComponent<RawImage>();
    if (raw != null && raw.texture != null)
        return raw.texture.name;

    return "";
}
```

### 5.4 新增图标可交互判断

规则：

```text
Image/RawImage 有 sprite
raycastTarget=true
自身或父级有点击接收能力
父级路径/name 命中 Item/Reward/Cell/Slot/Icon/Activity/Building
```

伪代码：

```csharp
bool isIcon = IsIconNode(go);
string spriteName = GetSpriteName(go);
string clickTarget = FindClickTargetNode(go);
bool isInteractiveIcon =
    isIcon
    && !string.IsNullOrEmpty(spriteName)
    && CheckRaycastTarget(go, compTypes)
    && !string.IsNullOrEmpty(clickTarget);
```

如果成立：

```text
elementType = interactive_icon
interactionType = click
visualNode = 当前 path
clickTargetNode = clickTarget
clickable = true
clickableReason = Image.raycastTarget=true + clickable parent
```

### 5.5 新增格子类识别

格子类常见命名：

```text
Item
Cell
Slot
Grid
Reward
Goods
Card
Row
ListItem
```

规则：

```text
节点名或父级路径命中格子关键词
节点或子节点有 sprite/text
自身或父级有点击能力
```

输出：

```text
elementType=item_cell/reward_cell/shop_item_cell/list_row
visualNode=主要图标或当前节点
clickTargetNode=格子根节点
```

### 5.6 新增遮罩/空白关闭区域识别

规则：

```text
name/path 命中 Mask/Blocker/CloseArea/TouchClose/ClickClose/Bg
Image.raycastTarget=true
覆盖面积大
位于弹窗背景层
```

输出：

```text
elementType=blank_close_area 或 popup_mask
interactionType=blank_close
clickStrategy=safe_blank_area
```

注意：

```text
空白关闭区域不一定有 clickTargetNode。
它可能需要计算 safePoint，避开弹窗内容、按钮、建筑和其它可点击对象。
```

### 5.7 新增滚动/拖拽/缩放区域识别

规则：

```text
ScrollRect -> scroll_area
Scrollbar/Slider -> drag_area
地图容器/Camera控制层 -> drag_area/pinch_area
```

输出：

```text
elementType=scroll_area/drag_area/pinch_area
interactionType=scroll/drag/pinch
```

注意：

```text
这些不应该计入普通 clickConfirmedCount。
它们需要单独的 drag/scroll/pinch 验证。
```

## 6. Unity 场景对象导出修改

UI 树只覆盖 Canvas UI，不覆盖主城建筑、大地图资源点等场景对象。

需要单独导出：

```text
scene_interaction_tree.json
```

### 6.1 场景对象类型

```text
building_object
map_object
resource_point
npc_object
monster_object
event_point
ship_object
treasure_object
guide_scene_target
```

### 6.2 判断规则

场景对象可交互规则：

```text
有 Collider / Collider2D
有自定义点击脚本
有 IPointerClickHandler 或射线点击处理
命名/脚本类型命中 Building/MapObject/Resource/NPC/Monster/Event
位于主城/大地图交互层
```

### 6.3 输出字段

```json
{
  "sceneId": "MainCity",
  "objectType": "building_object",
  "name": "Barrack_01",
  "displayName": "兵营建筑",
  "worldPosition": [12.3, 0, 45.6],
  "screenRect": [120, 500, 220, 640],
  "normalizedRect": [0.1, 0.2, 0.2, 0.25],
  "clickTargetNode": "Scene/MainCity/Barrack_01",
  "visualNode": "Scene/MainCity/Barrack_01",
  "interactionType": "click",
  "clickable": true,
  "clickableReason": "Collider + BuildingClickHandler"
}
```

## 7. enhanced_ui_tree 生成修改

当前 `enhanced_ui_tree.json` 应从候选 UI 扩展为候选交互元素库。

### 7.1 输入增加

```text
project_ui_inventory.json
runtime_ui_tree_current.json
scene_interaction_tree.json
icon_inventory.json
```

### 7.2 输出增加

```json
{
  "summary": {
    "componentClickable": 11,
    "interactiveIcons": 37,
    "interactiveCells": 24,
    "sceneObjects": 18,
    "blankCloseAreas": 3,
    "dragAreas": 5,
    "effectiveClickable": 62
  },
  "nodes": []
}
```

### 7.3 候选入库规则

进入 enhanced 的元素包括：

```text
Button/Toggle/EventTrigger/IPointerClickHandler
interactive_icon
item_cell/reward_cell/shop_item_cell
activity_entry
building_menu_button
blank_close_area
scene_object/building_object/map_object/resource_point
guide_target
scroll_area/drag_area/pinch_area
bubble_entry
```

### 7.4 草稿生成规则

映射草稿必须包含：

```text
elementType
interactionType
visualNode
clickTargetNode
clickStrategy
expectedAfterInteraction
```

示例：

```json
{
  "semanticId": "maincity.building.barrack",
  "displayName": "主城-兵营建筑",
  "elementType": "building_object",
  "interactionType": "click",
  "visualNode": "Scene/MainCity/Barrack_01",
  "clickTargetNode": "Scene/MainCity/Barrack_01",
  "expectedAfterInteraction": {
    "type": "open_building_menu"
  }
}
```

## 8. IDE 后端修改

### 8.1 运行态统计接口

当前统计只返回：

```text
clickableCount
```

建议扩展为：

```json
{
  "nodeCount": 560,
  "componentClickableCount": 11,
  "interactiveIconCount": 37,
  "interactiveCellCount": 24,
  "sceneObjectCount": 18,
  "blankCloseAreaCount": 3,
  "dragAreaCount": 5,
  "effectiveClickableCount": 62,
  "clickConfirmedCount": 8
}
```

### 8.2 新增筛选参数

`/api/mapping/drafts` 增加：

```text
elementType
interactionType
effectiveClickable=true
hasClickTarget=true
source=runtime_ui/scene_object/enhanced
```

示例：

```text
/api/mapping/drafts?elementType=interactive_icon
/api/mapping/drafts?interactionType=blank_close
/api/mapping/drafts?elementType=building_object
```

### 8.3 运行态匹配接口修改

`/api/mapping/runtime_match` 需要同时匹配：

```text
runtime UI nodes
scene interaction objects
virtual interaction areas
```

匹配结果要区分：

```text
ui_node_matched
scene_object_matched
virtual_area_matched
```

## 9. IDE 前端修改

### 9.1 顶部统计修改

UI 树与元素映射区域显示：

```text
组件 11 | 图标 37 | 格子 24 | 场景 18 | 空白关闭 3 | 拖拽 5 | 有效 62 | 已确认 8
```

### 9.2 筛选按钮增加

增加按钮：

```text
按钮
图标
格子
场景
建筑
弹窗空白
引导
红点气泡
滚动
拖拽
缩放
未知交互
```

### 9.3 详情面板增加字段

右侧详情增加：

```text
elementType
interactionType
visualNode
clickTargetNode
clickStrategy
effectiveClickable
clickableReason
clickTargetReason
interactionRisks
expectedAfterInteraction
```

### 9.4 点击确认按钮拆分

当前只有：

```text
测试点击
```

建议拆成：

```text
测试点击
测试长按
测试拖拽
测试滚动
测试缩放
测试空白关闭
```

根据 `interactionType` 自动启用对应按钮。

## 10. 点击验证修改

### 10.1 普通点击

适用于：

```text
button
interactive_icon
item_cell
reward_cell
building_menu_button
scene_object
```

验证：

```text
runtimePath/instanceId 命中
eventReceiverMatched=true
点击后状态符合预期
```

### 10.2 空白关闭

适用于：

```text
blank_close_area
popup_mask
```

验证：

```text
点击 safePoint
弹窗关闭
不误点弹窗按钮
不误点建筑/场景对象
```

需要字段：

```json
{
  "clickStrategy": "safe_blank_area",
  "avoidRegions": ["popup_content", "buttons", "scene_objects"]
}
```

### 10.3 场景对象点击

适用于：

```text
building_object
map_object
resource_point
npc_object
```

验证：

```text
Unity Raycast 命中目标对象
hitObject == expectedObject
点击后呼出菜单/打开界面/选中对象
```

### 10.4 拖拽/滚动/缩放

适用于：

```text
drag_area
scroll_area
pinch_area
```

验证：

```text
执行动作后 camera/map/list 位置变化
没有误触按钮
没有打开错误界面
```

## 11. 自动点击执行层修改

自动执行时根据 `interactionType` 分发：

```text
click -> Unity EventSystem 点击
long_press -> PointerDown 等待后 PointerUp
blank_close -> 计算 safePoint 点击
scene_click -> Unity Raycast/对象点击
drag -> 拖拽
scroll -> ScrollRect 滚动
pinch -> 双指缩放或 Unity 内部缩放接口
```

伪代码：

```python
if element.interactionType == "click":
    click_by_runtime_target(element)
elif element.interactionType == "blank_close":
    click_safe_blank_area(element)
elif element.interactionType == "scene_click":
    click_scene_object(element)
elif element.interactionType == "scroll":
    scroll_area(element)
elif element.interactionType == "drag":
    drag_area(element)
elif element.interactionType == "pinch":
    pinch_area(element)
```

## 12. 验收标准

### 12.1 运行态导出验收

```text
Button/Toggle 仍能识别为 clickable
Image 图标能识别 spriteName
可点击图标能生成 visualNode/clickTargetNode
道具格子能识别 item_cell
奖励格子能识别 reward_cell
弹窗空白关闭区域能识别 blank_close_area
ScrollRect 能识别 scroll_area
场景建筑能通过 scene_interaction_tree 导出
```

### 12.2 IDE 显示验收

```text
顶部统计能区分组件/图标/格子/场景/有效可交互
筛选按钮能过滤图标、格子、场景对象
详情面板能显示 visualNode/clickTargetNode
图标类不再误把 Image 节点当点击目标
```

### 12.3 映射草稿验收

```text
可点击图标生成 interactive_icon 草稿
道具格子生成 item_cell 草稿
奖励格子生成 reward_cell 草稿
建筑对象生成 building_object 草稿
空白关闭区域生成 blank_close_area 草稿
拖拽/滚动区域生成 drag_area/scroll_area 草稿
```

### 12.4 点击验证验收

```text
interactive_icon 点击命中父级 clickTargetNode
item_cell 点击后选中或打开 tips
reward_cell 点击后打开奖励详情或领取
building_object 点击后呼出建筑菜单
blank_close_area 点击后弹窗关闭且不误点其它目标
scroll_area 能滚动列表
drag_area 能拖动地图
pinch_area 能缩放地图
```

## 13. 实施优先级

建议按以下顺序做：

```text
P0：interactive_icon
P0：item_cell / reward_cell
P0：blank_close_area
P0：building_menu_button
P1：building_object / scene_object
P1：activity_entry / bubble_entry
P1：scroll_area
P2：drag_area / pinch_area
P2：npc_object / resource_point / map_object
P3：clickable_unknown
```

优先原因：

```text
图标、格子、弹窗空白关闭、建筑菜单按钮最影响当前自动点击闭环。
场景对象和拖拽缩放很重要，但可以在基础 UI 点击稳定后逐步接入。
```

## 14. 最终结论

AutoSmoke 的“可点击”不应该只等于 Unity 组件里的 Button。

最终应升级为：

```text
玩家可交互元素库
```

这个库包含：

```text
UI按钮
图标
格子
列表行
弹窗空白区域
建筑
大地图对象
引导目标
红点气泡
拖拽/滚动/缩放区域
```

每个元素都必须明确：

```text
看见谁：visualNode
点谁：clickTargetNode
怎么交互：interactionType
为什么认为可交互：clickableReason
是否当前真正可交互：effectiveClickable
是否已通过验证：click_confirmed
```

这样才能覆盖 SLG 游戏真实玩家操作路径，并保证后续自动点击准确可靠。
