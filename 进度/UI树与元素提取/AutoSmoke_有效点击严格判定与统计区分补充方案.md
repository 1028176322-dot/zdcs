# AutoSmoke 有效点击严格判定与统计区分补充方案

## 1. 背景

当前补充可点击图标、格子后，IDE 显示统计类似：

```text
节点：677
组件：11
图标：107
格子：79
有效：305
```

这说明系统已经不再只识别 Button，而是把图标、格子等交互候选也纳入了运行态 UI 树。

但这里的：

```text
有效：305
```

目前更像：

```text
可交互候选数
```

不应该直接理解为：

```text
当前真正适合自动点击的元素数
```

因为里面可能包含：

```text
父子重复节点
装饰图标
资源栏图标
Debug按钮
道具格子的子图标
背景图片
不可见或不可交互节点
被弹窗遮挡的节点
没有 clickTargetNode 的候选
```

因此需要进一步区分：

```text
候选可交互
严格有效点击
已验证点击
```

## 2. 修改目标

把当前单一的“有效”统计拆成多层：

```text
交互候选数
运行态有效数
严格有效点击数
关键有效点击数
已点击确认数
```

建议 IDE 顶部显示：

```text
节点 677
组件 11
图标 107
格子 79
候选 305
严格有效 42
关键 12
已确认 3
```

其中：

```text
候选 305：系统认为可能可交互
严格有效 42：当前真正适合自动点击
关键 12：P0/P1 关键流程元素
已确认 3：已经 click_confirmed
```

## 3. 定义分层

### 3.1 interactionCandidate

含义：

```text
系统认为可能可交互的节点或对象。
```

来源：

```text
Button / Toggle / EventTrigger / IPointerClickHandler
interactive_icon
item_cell / reward_cell
scene_object
blank_close_area
scroll_area / drag_area
```

特点：

```text
数量多
包含误判
不能直接自动点击
```

### 3.2 runtimeInteractable

含义：

```text
当前运行态下可见且可交互的候选。
```

条件：

```text
interactionCandidate=true
activeInHierarchy=true
visible=true
interactable=true
```

仍然不等于最终可点击，因为可能：

```text
没有 clickTargetNode
父子重复
被遮挡
坐标异常
是装饰图标
```

### 3.3 effectiveClickable

含义：

```text
当前界面中可以进入自动点击审核的有效点击元素。
```

条件：

```text
runtimeInteractable=true
clickTargetNode 非空
screenRect 有效
不是纯装饰
不是重复子节点
没有被顶层弹窗遮挡
interactionType=click/blank_close/scene_click
```

### 3.4 strictEffectiveClickable

含义：

```text
严格意义上当前可以执行自动点击验证的元素。
```

条件：

```text
effectiveClickable=true
matchScore >= 0.85
runtimeMatch.status=matched
clickTargetNode 可解析到 Unity GameObject
事件接收对象可预测
```

### 3.5 clickConfirmed

含义：

```text
已经通过 Unity 注入点击验证。
```

条件：

```text
reviewStatus=click_confirmed
clickVerification.status=passed
eventReceiverMatched=true
```

## 4. 统计字段设计

运行态状态建议输出：

```json
{
  "nodeCount": 677,
  "componentClickableCount": 11,
  "interactiveIconCount": 107,
  "interactiveCellCount": 79,
  "sceneObjectCount": 0,
  "blankCloseAreaCount": 1,
  "dragAreaCount": 0,
  "interactionCandidateCount": 305,
  "runtimeInteractableCount": 128,
  "effectiveClickableCount": 64,
  "strictEffectiveClickableCount": 42,
  "keyEffectiveClickableCount": 12,
  "clickConfirmedCount": 3,
  "excludedCount": 241,
  "excludedReasons": {
    "duplicate_child": 80,
    "decorative_icon": 54,
    "no_click_target": 33,
    "not_visible": 21,
    "not_interactable": 10,
    "invalid_rect": 8,
    "blocked_by_modal": 5,
    "debug_ui": 2
  }
}
```

## 5. 严格有效点击判定规则

### 5.1 基础条件

必须满足：

```text
activeInHierarchy=true
visible=true
interactable=true
screenRect 有效
normalizedRect 有效
interactionType 支持点击
```

### 5.2 点击目标条件

必须满足其中之一：

```text
clickTargetNode 非空
runtimePath 可作为点击目标
instanceId 可定位
virtual click strategy 已定义
```

对于图标和格子：

```text
interactive_icon 必须能找到父级 clickTargetNode
item_cell 必须以格子根节点为 clickTargetNode
reward_cell 必须以奖励格子根节点为 clickTargetNode
```

### 5.3 坐标条件

screenRect 必须满足：

```text
width > 4
height > 4
x/y 在 GameContent 范围内
面积不能过小
面积不能大到接近全屏，除非 elementType=blank_close_area/drag_area
```

建议：

```text
普通按钮面积 < GameContent面积 * 0.25
图标/格子面积 < GameContent面积 * 0.15
遮罩/空白区允许大面积，但必须标记 blank_close_area
```

### 5.4 父子重复去重

同一交互目标可能同时存在：

```text
ItemCell
ItemCell/Icon
ItemCell/CountText
ItemCell/Frame
```

实际只应该算一个有效点击：

```text
clickTargetNode = ItemCell
```

去重规则：

```text
按 clickTargetNode 分组
每组只保留一个代表元素
优先保留 elementType=item_cell/reward_cell/button
其次保留 interactive_icon
text/count/background 子节点不作为有效点击
```

### 5.5 装饰图标排除

排除条件：

```text
spriteName 命中 bg/background/deco/frame/line/shadow/effect/light
nodeName 命中 Bg/Background/Decor/Effect/Frame/Shadow
raycastTarget=false
没有 clickTargetNode
父级没有点击能力
```

标记：

```text
excludeReason=decorative_icon
```

### 5.6 Debug/工具 UI 排除

排除条件：

```text
pageId/name/path 命中 Debug/GM/Test/Ctrl/Console/Editor
```

默认：

```text
不进入 keyEffectiveClickable
可以进入 LOW/debug_ui 分组
```

除非用户打开：

```text
包含调试UI
```

### 5.7 遮挡判断

如果当前有顶层弹窗：

```text
只有弹窗自身、弹窗按钮、弹窗遮罩、弹窗空白关闭区域算有效。
底层主城/背包/大地图元素应标记 blocked_by_modal。
```

遮挡规则：

```text
根据 sortingOrder / canvas 层级 / siblingIndex 判断顶层 UI。
如果节点中心点被更高层 raycastTarget 覆盖，则排除。
```

### 5.8 当前页关键元素判定

`keyEffectiveClickable` 只统计：

```text
priority=P0/P1
或 role in close_popup/confirm/cancel/use_action/claim_reward/go_to/back/switch_tab
或 elementType in button/tab/item_cell/reward_cell/building_menu_button/blank_close_area
```

## 6. Unity 导出字段补充

运行态 UI 节点建议增加：

```json
{
  "interactionCandidate": true,
  "runtimeInteractable": true,
  "effectiveClickable": true,
  "strictEffectiveClickable": false,
  "effectiveReason": "visible+interactable+clickTargetNode+validRect",
  "excludeReason": "",
  "dedupeKey": "BagPanel/List/Item_001",
  "representativeNode": true,
  "clickTargetNode": "BagPanel/List/Item_001",
  "visualNode": "BagPanel/List/Item_001/Icon",
  "interactionType": "click",
  "elementType": "item_cell"
}
```

## 7. IDE 后端处理流程

建议新增模块：

```text
E:\zdcs\AutoSmoke\元数据\effective_click_analyzer.py
```

职责：

```text
读取 runtime_ui_tree_current.json
读取 scene_interaction_tree.json
进行候选分类
进行父子去重
排除装饰/Debug/不可见/不可交互/遮挡
计算 effectiveClickable
计算 strictEffectiveClickable
输出统计和有效点击列表
```

输出：

```text
effective_clicks_current.json
```

结构：

```json
{
  "generatedAt": "...",
  "pageId": "BagPanel",
  "summary": {},
  "items": []
}
```

## 8. IDE 前端展示修改

### 8.1 顶部统计

从：

```text
组件11 图标107 格子79 有效305
```

改为：

```text
组件11 图标107 格子79 候选305 运行态128 严格有效42 关键12 已确认3
```

### 8.2 筛选按钮

增加：

```text
候选
运行态有效
严格有效
关键有效
已确认
已排除
重复子节点
装饰图标
无点击目标
被遮挡
```

### 8.3 详情区

右侧显示：

```text
是否候选：是
运行态可交互：是
严格有效点击：否
原因：未匹配到 clickTargetNode
排除原因：duplicate_child
去重主节点：BagPanel/List/Item_001
```

## 9. 与映射审核的关系

进入人工审核主列表的建议默认条件：

```text
strictEffectiveClickable=true
或 keyEffectiveClickable=true
或 reviewStatus in runtime_matched/visual_confirmed/click_confirmed
```

不要默认展示所有：

```text
interactionCandidate=true
```

否则候选量会太大。

## 10. 点击确认准入规则

允许点击确认：

```text
strictEffectiveClickable=true
runtimeMatch.status=matched
clickTargetNode 非空
visible=true
interactable=true
```

禁止点击确认：

```text
interactionCandidate=true 但 strictEffectiveClickable=false
excludeReason 非空
blocked_by_modal
duplicate_child
decorative_icon
no_click_target
invalid_rect
```

如果用户强制测试点击，需要弹出提示：

```text
该元素未通过严格有效点击判定，存在误点风险，是否继续？
```

## 11. 当前背包界面建议预期

以当前截图背包界面为例，严格有效点击不应是 305。

更合理的关键有效元素大概包括：

```text
返回/关闭按钮：1
页签：5
道具格子：4
使用按钮：1
Debug按钮：1，可归为调试UI
可能的滚动区域：1
顶部资源入口：若可点，约4
```

因此：

```text
候选：可能 305
严格有效：可能 20-50
关键有效：可能 10-20
```

如果严格有效仍然接近 305，说明：

```text
去重不足
装饰排除不足
父子节点重复
clickTargetNode 归并不足
```

## 12. 验收标准

### 12.1 统计验收

```text
候选数可以较大
严格有效数明显小于候选数
关键有效数符合当前页面实际可操作数量
已确认数只统计 click_confirmed
```

### 12.2 去重验收

```text
一个道具格子只算一个严格有效点击
图标、数量文本、边框、背景不重复计数
```

### 12.3 排除验收

```text
背景图不算严格有效
装饰图标不算严格有效
Debug UI 可单独归类
不可见节点不算严格有效
被弹窗遮挡的底层节点不算严格有效
```

### 12.4 点击验收

```text
严格有效元素可以进入视觉确认和点击确认
非严格有效元素默认不能直接点击确认
失败原因能在详情区显示
```

## 13. 结论

当前“有效 305”说明系统已经能发现大量交互候选，这是好事。

但自动化需要的是：

```text
严格有效点击
```

不是：

```text
候选可交互
```

下一步必须引入：

```text
候选 -> 运行态可交互 -> 严格有效点击 -> 关键有效点击 -> 点击确认
```

这套分层后，IDE 才能把大量候选收敛成测试人员真正需要审核和确认的元素。
