# AutoSmoke - 可测试性元数据导出详细方案

## 1. 背景

游戏 UI 自动化如果主要依赖截图、OCR、模板匹配，会遇到明显瓶颈：

```text
游戏字体有描边、阴影、自定义字体，OCR 识别率不稳定
按钮图标和文字可能被特效、缩放、遮罩影响
Poco 原始 UI 树中 clickable/type 经常不准确
主城建筑、大地图对象不一定属于传统 UI 树
不同分辨率、GameView 拉伸、UI 动画会影响截图定位
```

因此，长期最稳定的方案不是“从画面猜 UI”，而是让 Unity Editor 辅助层或 Poco 扩展主动导出可测试元数据。

目标是把识别链路从：

```text
截图 -> OCR/模板猜测 -> 坐标点击
```

升级为：

```text
结构化元数据 -> testId/pageId/sceneId/screenRect -> 精准定位和点击
```

## 2. 总体目标

建设 AutoSmoke 可测试性元数据导出能力，用于支持：

```text
当前页面识别
当前场景识别
UI 元素定位
按钮 clickable/type 修正
主城建筑识别
大地图对象识别
建筑上下文菜单识别
弹窗/Loading/引导识别
用例步骤目标定位
IDE 可视化调试
测试报告证据生成
```

最终目标：

```text
优先通过 testId / pageId / sceneId / screenRect 定位目标；
Poco、模板匹配、OCR 作为补充和兜底。
```

## 3. 设计边界

必须遵守当前项目约束：

```text
不修改游戏业务运行过程代码
不修改按钮点击逻辑
不修改 UI 打开/关闭逻辑
不修改主城/地图/战斗业务逻辑
允许新增 Unity Editor 辅助脚本
允许扩展 Poco 接入层或导出层
所有能力最终封装进 IDE
兼容其它电脑、不同项目路径、不同用户环境
```

允许的低侵入方式：

```text
Assets/Editor/AutoSmokeMetadataExporter.cs
Assets/Editor/AutoSmokeGameViewBridge.cs
只在 Unity Editor 环境运行
只读扫描 UI、场景对象和组件信息
输出 JSON 到 .autosmoke 目录
不进入正式构建包
```

## 4. 推荐识别优先级

最终识别优先级建议：

```text
1. Unity 可测试性元数据导出
2. Poco SDK / UI 树增强 dump
3. 模板匹配
4. 大号关键文字 OCR
5. normalized/design 坐标兜底
6. screen 坐标，仅调试允许
```

说明：

```text
testId/screenRect/pageId 是主路径
Poco 原始 UI 树是补充路径
模板匹配适合固定图标和按钮样式
OCR 只识别大号关键文字，例如“恭喜获得”“确认”“取消”
坐标只作为兜底，不作为长期维护方案
```

## 5. 核心数据模型

### 5.1 页面元数据

```json
{
  "pageId": "bag_page",
  "pageName": "背包",
  "visible": true,
  "rootPath": "Canvas/DeepUI/BagPanel",
  "screenRect": [0, 0, 1170, 2532],
  "normalizedRect": [0, 0, 1, 1],
  "sortingOrder": 20,
  "timestamp": "2026-06-15T10:00:00"
}
```

### 5.2 UI 元素元数据

```json
{
  "testId": "bag.button.use",
  "name": "使用",
  "path": "Canvas/DeepUI/BagPanel/ButtonUse",
  "pageId": "bag_page",
  "type": "Button",
  "componentType": ["Button", "Image", "TMP_Text"],
  "clickable": true,
  "visible": true,
  "interactable": true,
  "screenRect": [464, 2380, 706, 2490],
  "normalizedRect": [0.396, 0.94, 0.207, 0.043],
  "text": "使用",
  "zOrder": 120,
  "source": "unity_metadata"
}
```

### 5.3 弹窗元数据

```json
{
  "testId": "reward.popup.root",
  "pageId": "reward_popup",
  "type": "Popup",
  "title": "恭喜获得",
  "visible": true,
  "screenRect": [120, 500, 1050, 1700],
  "hasMask": true,
  "closeActions": ["confirm", "outside_blank"],
  "safeConfirm": true,
  "dangerous": false
}
```

### 5.4 场景对象元数据

```json
{
  "testId": "maincity.building.barracks",
  "sceneId": "main_city",
  "type": "Building",
  "name": "兵营",
  "level": 5,
  "clickable": true,
  "visible": true,
  "worldPos": [12.5, 0, 33.2],
  "screenRect": [380, 920, 620, 1240],
  "interactionAnchor": [500, 1080],
  "actions": ["训练", "升级", "信息"],
  "source": "scene_metadata"
}
```

### 5.5 大地图对象元数据

```json
{
  "testId": "worldmap.resource.wood.1024_2048",
  "sceneId": "world_map",
  "type": "Resource",
  "resourceType": "Wood",
  "level": 5,
  "clickable": true,
  "visible": true,
  "worldPos": [1024, 0, 2048],
  "screenRect": [300, 420, 360, 480],
  "normalizedRect": [0.256, 0.166, 0.051, 0.024]
}
```

## 6. 元素语义映射方案

### 6.1 为什么需要语义映射

Unity/Poco 导出的原始节点通常只能说明“技术上是什么”，例如：

```text
[Panel] Stone
IceBreak(Clone)/2/IceBreak/2/Stone
screenRect: [1,2528,2,2529]
```

这类信息不能直接告诉测试工具：

```text
它在游戏里是什么？
它是不是可点击？
它是不是按钮、建筑、装饰、遮罩、无效节点？
它应该对应哪个用例里的目标？
```

因此，需要在元数据之上增加一层：

```text
Element Semantic Mapping
元素语义映射
```

目标是把技术节点转换成业务元素：

```text
Unity/Poco 节点
-> 位置 + 文本 + 图标 + 页面 + 组件 + 点击结果
-> displayName / role / testId / meaning
```

### 6.2 语义映射数据结构

```json
{
  "path": "DeepUI/BagPanel/ButtonUse",
  "sourceName": "ButtonUse",
  "testId": "bag.button.use",
  "displayName": "使用按钮",
  "role": "Button",
  "pageId": "bag_page",
  "meaning": "点击后使用当前选中的道具",
  "clickable": true,
  "dangerous": false,
  "screenRect": [464, 2380, 706, 2490],
  "source": "manual_confirmed",
  "confidence": 1.0,
  "updatedAt": "2026-06-15T10:30:00"
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `path` | Unity/Poco 原始路径 |
| `sourceName` | 原始节点名 |
| `testId` | 稳定自动化 ID |
| `displayName` | IDE 中展示的人类可读名称 |
| `role` | 业务角色，如 Button、Building、Popup、Decoration |
| `pageId` | 所属页面 |
| `meaning` | 业务含义 |
| `dangerous` | 是否危险操作 |
| `source` | 来源：manual_confirmed / auto_inferred / unity_metadata |
| `confidence` | 可信度 |

### 6.3 element_mapping.json

建议保存到：

```text
%USERPROFILE%\.autosmoke\mappings\element_mapping.json
```

也可以按项目保存：

```text
<UnityProject>/.autosmoke/element_mapping.json
```

推荐结构：

```json
{
  "projectId": "k3client",
  "mappings": [
    {
      "path": "DeepUI/BagPanel/ButtonUse",
      "testId": "bag.button.use",
      "displayName": "使用按钮",
      "role": "Button",
      "pageId": "bag_page"
    }
  ]
}
```

### 6.4 IDE 截图高亮

IDE 元素列表中点击任意节点时，应在当前 GameContent 截图上高亮：

```text
screenRect
normalizedRect
节点路径
推断类型
clickable 状态
```

用途：

```text
让用户直观看到该节点在游戏画面中的位置
判断它是否真实可见
判断它是否可操作
过滤 1x1 像素、不可见、装饰性节点
```

规则：

```text
screenRect 面积过小，例如小于 4x4，默认降权
screenRect 不在 gameContentRect 内，默认标记异常
visible=false 或 alpha=0，默认不作为点击候选
```

### 6.5 反向点选

IDE 应支持用户在游戏截图上点选一个位置，反查该点命中的候选元素。

流程：

```text
用户点击截图上的“使用”按钮
-> IDE 将截图坐标转换成 game_content 坐标
-> 查询包含该点的 metadata nodes
-> 按 zOrder、面积、clickable、type 排序
-> 展示候选元素列表
```

候选排序建议：

```text
clickable=true 优先
Button/Toggle/Input 优先
面积适中优先
zOrder 高优先
文本/图标匹配优先
Panel/Decoration 降权
1x1 节点降权
```

输出示例：

```json
{
  "point": [585, 2435],
  "candidates": [
    {
      "path": "DeepUI/BagPanel/ButtonUse",
      "name": "ButtonUse",
      "type": "Button",
      "clickable": true,
      "screenRect": [464, 2380, 706, 2490],
      "score": 0.96
    }
  ]
}
```

### 6.6 人工确认标注

IDE 需要允许用户对候选节点进行确认标注：

```text
displayName：使用按钮
testId：bag.button.use
role：Button
pageId：bag_page
dangerous：false
meaning：使用当前选中道具
```

保存后，该元素后续优先按 `testId` 定位。

标注来源：

```text
manual_confirmed
```

人工确认优先级高于自动推断。

### 6.7 自动语义推断

IDE 可以辅助推断，但不能替代关键元素确认。

推断规则：

```text
Button 组件 -> role=Button
TMP_Text/Text -> role=Text
ScrollRect -> role=ScrollView
含 Mask/Blur -> role=Popup
附近文字为“使用” -> 可能是使用按钮
父节点为 BagPanel -> pageId=bag_page
点击后出现弹窗 -> actionType=open_popup
点击后页面变化 -> actionType=navigate
```

自动推断结果：

```text
source = auto_inferred
confidence < manual_confirmed
```

### 6.8 无效节点过滤

以下节点默认不作为点击候选：

```text
screenRect 面积过小
screenRect 坐标异常
不可见节点
纯装饰节点
无事件组件的 Panel
背景图
遮罩层
重复 Clone 装饰节点
```

可以标记为：

```json
{
  "role": "Decoration",
  "clickable": false,
  "ignored": true,
  "ignoreReason": "screenRect too small"
}
```

### 6.9 推荐 IDE 工作流

```text
1. 导出 UI/场景元数据
2. IDE 展示元素列表
3. 用户点击元素列表中的节点
4. 截图上高亮该节点位置
5. 用户也可以在截图上反向点选
6. IDE 展示命中候选节点
7. 用户确认业务含义并填写 testId/displayName/role
8. 保存到 element_mapping.json
9. 后续用例使用 testId 执行
```

### 6.10 自动映射草稿

为了降低人工标注成本，IDE 应先自动生成一版元素映射草稿，再由用户核对、补充、修改。

流程：

```text
1. 导出 current_ui.json / current_scene.json
2. element_auto_mapper.py 读取元数据
3. 对每个节点执行自动语义推断
4. 生成 element_mapping_draft.json
5. IDE 展示草稿映射
6. 用户确认/修改/忽略
7. 确认结果写入 element_mapping.json
```

建议新增模块：

```text
E:/zdcs/AutoSmoke/element_auto_mapper.py
```

### 6.11 自动匹配规则

自动映射草稿可使用以下规则：

```text
1. 节点名规则
   ButtonUse / BtnUse / Use -> 使用按钮
   BtnClose / Close / X -> 关闭按钮
   Upgrade -> 升级按钮
   Reward -> 奖励弹窗

2. 组件类型规则
   Button -> role=Button
   TMP_Text/Text -> role=Text
   ScrollRect -> role=ScrollView
   Panel/Dialog/Popup -> role=Popup/Panel

3. 页面归属规则
   BagPanel 下的节点 -> pageId=bag_page
   RewardPopup 下的节点 -> pageId=reward_popup
   MainCity 下的对象 -> sceneId=main_city

4. 文本关联规则
   按钮附近有“使用” -> displayName=使用按钮
   弹窗标题是“恭喜获得” -> reward_popup
   附近有“确认” -> 确认按钮候选

5. 位置/布局规则
   顶部 tab 区域 -> role=Tab
   底部导航区域 -> role=Navigation
   右侧活动图标 -> role=ActivityEntry
   中心遮罩区域 -> role=Popup

6. 点击能力规则
   clickable=true + Button组件 -> 可点击按钮
   clickable=false + 面积很小 -> ignored=true
   screenRect 不在 gameContentRect 内 -> invalidRect
```

### 6.12 element_mapping_draft.json

草稿文件建议保存到：

```text
%USERPROFILE%\.autosmoke\mappings\element_mapping_draft.json
```

结构示例：

```json
{
  "projectId": "k3client",
  "generatedAt": "2026-06-15T10:45:00",
  "sourceFiles": [
    "current_ui.json",
    "current_scene.json"
  ],
  "draftMappings": [
    {
      "path": "DeepUI/BagPanel/ButtonUse",
      "sourceName": "ButtonUse",
      "suggestedTestId": "bag.button.use",
      "suggestedDisplayName": "使用按钮",
      "suggestedRole": "Button",
      "pageId": "bag_page",
      "clickable": true,
      "screenRect": [464, 2380, 706, 2490],
      "confidence": 0.87,
      "sources": ["name_rule", "component_rule", "nearby_text"],
      "reviewStatus": "pending"
    }
  ]
}
```

### 6.13 审核状态

草稿中的每条映射需要有审核状态：

```text
pending      待确认
confirmed    已确认
modified     已修改后确认
ignored      忽略
rejected     拒绝该建议
```

确认后的正式映射：

```json
{
  "path": "DeepUI/BagPanel/ButtonUse",
  "testId": "bag.button.use",
  "displayName": "使用按钮",
  "role": "Button",
  "pageId": "bag_page",
  "clickable": true,
  "source": "manual_confirmed",
  "reviewStatus": "confirmed"
}
```

### 6.14 置信度评分

建议评分规则：

```text
组件类型命中：+0.25
节点名命中：+0.25
附近文本命中：+0.25
页面归属命中：+0.15
位置布局命中：+0.10
screenRect 异常：-0.40
面积过小：-0.30
不可见：-0.50
```

置信度分级：

```text
>= 0.85  高可信，可推荐直接确认
0.60~0.84 中可信，需要人工核对
< 0.60  低可信，仅作为候选或默认忽略
```

### 6.15 IDE 草稿审核流程

IDE 中应提供：

```text
自动生成映射草稿
按置信度排序
只看高可信
只看待确认
只看低可信
截图高亮当前候选
反向点选修改候选
确认 / 修改 / 忽略 / 拒绝
批量确认高可信项
导出正式 element_mapping.json
```

推荐审核界面字段：

```text
原始节点名
原始路径
截图高亮
建议 testId
建议 displayName
建议 role
pageId
clickable
confidence
sources
reviewStatus
```

## 7. Unity Editor 元数据导出方案

### 7.1 建议新增脚本

```text
Assets/Editor/AutoSmokeMetadataExporter.cs
```

职责：

```text
扫描当前 Canvas/UI 对象
扫描当前场景对象
推断 clickable/type/visible/screenRect
读取 AutoSmokeNode 标注
读取 Button/Text/Image/ScrollRect/InputField 等组件
输出 metadata JSON
```

### 7.2 触发方式

```text
1. IDE 请求导出
2. Editor 脚本定时导出
3. 菜单手动触发：AutoSmoke > Export Metadata
4. PlayMode 状态变化时导出
5. 每次点击前/点击后导出
```

推荐：

```text
点击执行前导出一次
点击执行后导出一次
状态识别时按需导出
```

### 7.3 输出路径

默认：

```text
%USERPROFILE%\.autosmoke\metadata\current_ui.json
%USERPROFILE%\.autosmoke\metadata\current_scene.json
%USERPROFILE%\.autosmoke\metadata\current_state.json
```

可配置：

```text
AUTOSMOKE_CONFIG_DIR
```

### 7.4 多电脑兼容

必须支持：

```text
不同 Windows 用户
不同 Unity 项目路径
不同盘符
不同 Unity 布局
不同 GameView 分辨率
不同屏幕数量
```

策略：

```text
输出到用户目录，不写死工程目录
IDE 自动复制 Editor 脚本到 Assets/Editor
每台电脑运行时重新定位 GameView 和 gameResolution
所有 screenRect 都按当前运行环境重新计算
缓存只用于加速，不跨机器复用绝对坐标
```

## 8. AutoSmokeNode 标注方案

### 8.1 组件定位

为了让关键对象有稳定语义，建议提供可选标注组件：

```csharp
public class AutoSmokeNode : MonoBehaviour
{
    public string testId;
    public string pageId;
    public string nodeType;
    public bool clickable;
    public bool dangerous;
    public string actionType;
    public int priority;
}
```

注意：

```text
这是测试元数据组件，不改变业务逻辑。
可以只在测试分支或测试模式下接入。
如果项目不允许运行时代码改动，可以先不强制挂载，改用 Editor 扫描推断。
```

### 8.2 testId 命名规范

```text
页面.区域.对象.动作
```

示例：

```text
bag.button.use
bag.tab.special
reward.popup.confirm
maincity.building.barracks
maincity.building.barracks.upgrade
worldmap.resource.wood
```

### 8.3 标注优先级

```text
AutoSmokeNode 显式标注
> Unity 组件推断
> Poco/UI 树
> 模板/OCR
```

## 9. clickable/type 修正

Poco 原始 UI 树中经常出现：

```text
clickable=false
type=Node
```

元数据导出层应修正：

### 9.1 clickable 判断

满足以下任一条件即可认为可点击：

```text
AutoSmokeNode.clickable=true
Button.interactable=true
Toggle/Slider/InputField 可交互
EventTrigger 存在点击事件
实现 IPointerClickHandler
Image.raycastTarget=true 且存在事件脚本
场景对象存在 Collider 或可点击组件
```

### 9.2 type 推断

```text
Button -> Button
TMP_Text/Text -> Text
InputField/TMP_InputField -> Input
ScrollRect -> ScrollView
CanvasGroup/Panel -> Panel
含 Mask/Blur 的浮层 -> Popup
主城建筑组件/标注 -> Building
地图资源/城池/部队 -> MapObject
```

输出示例：

```json
{
  "originType": "Node",
  "fixedType": "Button",
  "originClickable": false,
  "fixedClickable": true,
  "reason": "Button component detected"
}
```

## 10. Poco 增强方案

如果 Poco SDK 可扩展，建议让 Poco dump 增加字段：

```text
testId
pageId
fixedType
fixedClickable
screenRect
componentType
visible
interactable
zOrder
```

如果不能改 Poco SDK，则由 AutoSmoke IDE 侧合并：

```text
Poco dump
+ Unity metadata
+ GameContentRect
+ gameResolution
= enhanced_ui_tree
```

增强输出：

```json
{
  "source": "poco+unity_metadata",
  "nodes": [
    {
      "name": "ButtonUse",
      "testId": "bag.button.use",
      "type": "Button",
      "clickable": true,
      "screenRect": [464, 2380, 706, 2490]
    }
  ]
}
```

## 11. State & Target Recognition 接入

元数据导出后，状态识别优先使用：

```text
pageId
sceneId
popupId
contextMenuId
```

目标定位优先使用：

```text
testId
screenRect
interactionAnchor
actionButtonRects
```

执行链路：

```text
导出 metadata
-> recognize currentState by pageId/sceneId
-> locate target by testId/action
-> validate targetRect/safePoint
-> click by selected click_mode
-> after click export metadata again
```

## 12. 用例格式升级

推荐长期用例写法：

```text
点击 testId("bag.button.use")
点击 testId("reward.popup.confirm")
点击 building("maincity.building.barracks")
点击 buildingAction("upgrade")
断言存在 testId("bag.page.root")
```

兼容写法：

```text
点击 text("使用")
点击 template("use_button")
点击 normalized(0.5,0.95)
```

优先级：

```text
testId > building/action metadata > Poco/UI 树 > template > OCR > coordinate
```

## 13. IDE 集成

IDE 中应提供：

```text
元数据导出状态
当前 pageId / sceneId
当前 UI 元素列表
当前场景对象列表
testId 搜索
screenRect 可视化
clickable/type 修正报告
缺失 testId 扫描报告
重复 testId 检测
元素截图高亮
截图反向点选
自动生成映射草稿
映射草稿审核
人工语义标注
element_mapping 管理
一键重新导出
一键复制 Editor 脚本
```

### 13.1 元数据面板

展示：

```text
testId
name
type
clickable
visible
screenRect
pageId
source
confidence
```

### 13.2 元素语义映射面板

功能：

```text
一键生成 element_mapping_draft.json
展示自动建议 testId/displayName/role
按 confidence 排序和筛选
点击元素列表后，在 GameContent 截图上高亮 screenRect
点击截图位置后，反查命中候选节点
展示候选节点的 path/name/type/clickable/screenRect
允许用户填写 displayName/testId/role/pageId/meaning
保存到 element_mapping.json
标记 manual_confirmed / auto_inferred
支持 pending/confirmed/modified/ignored/rejected 审核状态
支持批量确认高可信草稿
```

### 13.3 可测性扫描

扫描：

```text
关键按钮缺失 testId
重复 testId
clickable/type 异常
弹窗缺少关闭动作
危险按钮未标注 dangerous
主城建筑缺少 metadata
大地图对象缺少 metadata
1x1 或极小节点自动降权
未映射关键元素提示人工确认
```

## 14. 报告体现

每次点击报告中记录：

```json
{
  "target": {
    "locator": "testId",
    "value": "bag.button.use",
    "screenRect": [464, 2380, 706, 2490],
    "safePoint": [585, 2435],
    "source": "unity_metadata",
    "confidence": 1.0
  },
  "metadata": {
    "pageId": "bag_page",
    "gameResolution": [1170, 2532],
    "exportTimestamp": "2026-06-15T10:00:00"
  }
}
```

如果回退到 OCR/模板：

```json
{
  "target": {
    "locator": "ocr",
    "value": "使用",
    "confidence": 0.72,
    "fallbackReason": "testId not found"
  }
}
```

## 15. 异常与降级策略

### 15.1 元数据导出失败

处理：

```text
记录 METADATA_EXPORT_FAILED
降级到 Poco dump
再降级到模板匹配
再降级到大号 OCR
最后才允许 normalized/design 坐标
```

### 15.2 testId 找不到

处理：

```text
检查当前 pageId 是否正确
检查元素是否可见
检查是否被弹窗/Loading/引导遮挡
降级到模板/OCR
报告 TARGET_TESTID_NOT_FOUND
```

### 15.3 screenRect 异常

处理：

```text
screenRect 不在 gameContentRect 内 -> BLOCKED_RECT_INVALID
screenRect 面积过小 -> WARNING_RECT_TOO_SMALL
screenRect 被遮挡 -> BLOCKED_TARGET_COVERED
```

## 16. 分阶段实施计划

### 阶段一：Unity Editor 只读导出

交付：

```text
AutoSmokeMetadataExporter.cs
current_ui.json
current_state.json
```

验收：

```text
能导出当前 Canvas 下 UI 元素
能导出 screenRect
能修正 Button 的 clickable/type
不修改游戏业务逻辑
```

### 阶段二：IDE 元数据面板

交付：

```text
IDE 展示 UI 元素列表
IDE 可视化 screenRect
IDE 显示 pageId/stateId
IDE 支持元素高亮
IDE 支持截图反向点选
```

验收：

```text
能搜索 testId/name
能看到 clickable/type 修正原因
能导出 enhanced_ui_tree.json
点击元素列表时截图能高亮对应区域
点击截图时能反查候选节点
```

### 阶段三：元素语义映射

交付：

```text
element_auto_mapper.py
element_mapping_draft.json
element_mapping.json
语义标注面板
草稿审核面板
manual_confirmed 映射保存
auto_inferred 映射建议
```

验收：

```text
能基于 current_ui.json 自动生成映射草稿
每条草稿包含 suggestedTestId/suggestedDisplayName/suggestedRole/confidence
能将技术节点映射为 displayName/testId/role
能保存并重新加载 element_mapping.json
人工确认映射优先级高于自动推断
极小/不可见/装饰节点能被过滤或降权
高可信草稿可批量确认
```

### 阶段四：目标定位接入

交付：

```text
target_locator 支持 testId
case_step_parser 支持 testId("xxx")
click_executor 支持 metadata target
```

验收：

```text
点击 testId("bag.button.use") 成功
点击后报告记录 metadata source
testId 找不到时能降级或失败
```

### 阶段五：主城/大地图对象导出

交付：

```text
current_scene.json
building metadata
map object metadata
interactionAnchor
```

验收：

```text
能导出兵营/灯塔等建筑
能点击 building testId
能识别 building_context_menu
```

### 阶段六：可测性扫描

交付：

```text
accessibility_scan.json
accessibility_scan.html
IDE 可测性扫描面板
```

验收：

```text
能发现重复 testId
能发现关键按钮缺失 testId
能发现危险按钮未标注
能发现 clickable/type 异常
```

## 17. 验收标准

### 17.1 UI 元数据验收

```text
至少导出当前页面 90% 可见 UI 元素
Button clickable 修正准确率 >= 95%
Button/Text/Input/ScrollView 类型推断准确率 >= 90%
每个元素包含 screenRect
```

### 17.2 元素语义映射验收

```text
能自动生成 element_mapping_draft.json
草稿项包含置信度和推断来源
元素列表点击后能在截图上高亮对应 screenRect
截图反向点选能返回候选节点列表
用户能将候选节点标注为 displayName/testId/role
标注结果能保存到 element_mapping.json
重新打开 IDE 后能加载已确认映射
1x1 或不可见节点默认不作为点击候选
用户能确认/修改/忽略/拒绝草稿项
批量确认高可信项后能写入正式映射
```

### 17.3 状态识别验收

```text
能通过 pageId 识别背包页
能通过 popupId 识别奖励弹窗
能通过 sceneId 识别主城
识别结果写入 current_state.json
```

### 17.4 点击定位验收

```text
testId 定位优先于 OCR/模板
testId 点击“使用”按钮成功
screenRect 中心点在 gameContentRect 内
点击报告记录 source=unity_metadata
人工确认的 element_mapping 优先于自动推断
```

### 17.5 多电脑兼容验收

```text
不同项目路径可自动复制 Editor 脚本
不同用户目录输出到各自 .autosmoke
不同 GameView 位置重新计算 screenRect
不同分辨率重新计算 normalizedRect
```

## 18. 风险与规避

### 18.1 Unity 版本反射差异

规避：

```text
尽量使用公开组件 API
反射字段只用于 GameView/Editor 辅助
保留字段诊断输出
保留 Poco/模板/OCR 降级
```

### 18.2 项目不允许挂 AutoSmokeNode

规避：

```text
先使用 Editor 扫描推断
只对关键 UI 后续补标注
标注组件作为可选增强，不作为第一阶段强依赖
```

### 18.3 元数据与画面不同步

规避：

```text
点击前导出一次
点击后导出一次
记录 timestamp
超过 TTL 的元数据不用于点击
```

## 19. 结论

比 `Poco + 大字 OCR + 模板匹配` 更稳定的长期方案是：

```text
Unity/Poco 可测试性元数据导出
```

它的核心价值是：

```text
不用猜文字
不用猜按钮
不用依赖固定截图坐标
直接使用 testId/pageId/sceneId/screenRect/clickable/type
```

最终推荐识别链路：

```text
Unity metadata / testId
> Poco/UI 树
> 模板匹配
> 大号关键 OCR
> normalized/design 坐标兜底
```

该方案完成后，AutoSmoke 的识别能力会从"视觉猜测自动化"升级为"可测试性驱动自动化"，更适合长期封装进 IDE 并支持多项目、多电脑运行。

---

## 20. 实施完成总结（2026-06-15）

### 20.1 阶段完成状态

| 阶段 | 交付 | 状态 | 日期 |
|:----:|------|:----:|:----:|
| 一 | Unity Editor 只读导出 | ✅ | 2026-06-15 |
| 二 | IDE 元数据面板 | ✅ | 2026-06-15 |
| 三 | 目标定位接入（testId） | ✅ | 2026-06-15 |
| 四 | 主城/大地图对象导出 | ✅ | 2026-06-15 |
| 五 | 可测性扫描 | ✅ | 2026-06-15 |

### 20.2 阶段一交付物

**C# 脚本**：`AutoSmokeMetadataExporter.cs`（968行）

| 功能 | 说明 |
|------|------|
| 自动启动 | `[InitializeOnLoad]` + `EditorApplication.update` 定时导出（3秒间隔） |
| UI 扫描 | 递归扫描所有活跃 Canvas 的 UI 元素 |
| screenRect | 世界坐标 → 游戏设计坐标（1170x2532） |
| type 推断 | Button / Toggle / Text / Input / Panel / Slider / ScrollView / Image / Node |
| clickable 修正 | Button.interactable / Toggle / Slider / EventTrigger / IPointerClickHandler / Image.raycastTarget+customScript |
| 文本提取 | TMP_Text 和 Text 组件文字内容 |
| AutoSmokeNode | 反射读取标注组件（如已挂载） |
| 状态导出 | 当前场景名、pageId、弹窗列表、Play Mode 状态 |
| 菜单项 | Export Metadata / Verbose / Open Output Folder / Force Export Now |

**Python 模块**：`metadata_reader.py`

| 功能 | 说明 |
|------|------|
| find_by_testid() | 精确 testId 搜索 |
| search_elements() | 按 testId / name / path / text 综合搜索 |
| find_by_type() / find_clickable() / find_buttons() | 类型和可点击搜索 |
| verify_target() | 验证元素是否可用（可见/可点击/screenRect 有效） |
| get_center() / get_normalized_center() | 获取点击坐标 |
| 状态读取 | get_current_page_id() / get_current_scene_name() / get_popups() |

**部署**：已注册到 `deploy_tools.py`，IDE 面板一键部署。

### 20.3 阶段二交付物

**debug_panel.py 元数据面板**

| 标签页 | 功能 |
|--------|------|
| 状态 | pageId、场景、Play Mode、UI 元素总数、可点击数、弹窗数、类型分布 |
| 元素列表 | 按 type + clickable 下拉筛选，展示路径、screenRect、clickable 修正原因 |
| 搜索 | 搜索 testId/name/path/text，显示归一化坐标和 design 坐标 |

**新增 API**：

| 路由 | 说明 |
|------|------|
| GET /api/metadata | 元数据摘要 |
| GET /api/metadata/elements?type=&clickable= | 过滤后的元素列表 |
| GET /api/metadata/search?q= | 综合搜索 |
| GET /api/metadata/export_enhanced | 导出 enhanced_ui_tree.json |

### 20.4 实测指标

| 指标 | 值 | 说明 |
|------|:----:|------|
| UI 元素扫描 | 725 个 | 当前 Loading 界面 |
| 可点击元素 | 199 个 | 修正后（Poco 原始 clickable 多不准确）|
| 类型分布 | Node 667, Image 29, Panel 26, Text 1, Button 1, ScrollView 1 | — |
| 活跃弹窗 | 5 个 | 3 个主要 Canvas + 2 个浮层 |
| 增强树导出 | 560 个 | 含 normalizedCenter + screenCenter |
