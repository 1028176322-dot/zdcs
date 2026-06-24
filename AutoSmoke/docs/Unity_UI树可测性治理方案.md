# Unity UI 树可测性治理方案

## 1. 背景问题

在 Unity 游戏自动化测试中，直接依赖 Poco 或默认 UI 树时，经常会遇到以下问题：

- 大部分节点 `clickable=False`，无法准确判断是否可点击。
- 大部分节点 `type=Node`，无法区分按钮、文本、输入框、弹窗、列表、建筑等业务对象。
- 只能通过节点名称判断控件类型，但项目命名规范不统一，容易造成大量误判。
- 主城建筑、大地图资源点、部队、城池等对象不一定属于传统 UI 树，单靠 UI 树无法完整覆盖。

因此，自动化系统不能只依赖原始 UI 树字段，而应建立一套“可测性标注 + 自动推断 + 兜底识别”的治理机制。

## 2. 目标

本方案目标是解决以下自动化识别问题：

- 正确识别可点击对象。
- 正确识别节点类型。
- 减少依赖节点名称造成的误判。
- 支持主城与大地图场景对象自动发现。
- 为 IDE 自动探索、用例执行、异常检测和页面关系图提供稳定数据源。

最终目标是将识别方式从“猜控件”升级为“读取明确的测试元数据”。

## 3. 总体解决思路

推荐采用四层识别策略：

```text
1. Unity 显式测试标注
2. Unity 组件类型自动推断
3. Poco 原始属性辅助判断
4. 命名规则与图像/坐标兜底
```

优先级从上到下。  
节点名称只能作为最后兜底，不应作为主要判断依据。

## 4. Unity 侧新增 AutoSmokeNode 标注组件

### 4.1 组件定位

在 Unity 工程中新增统一测试元数据组件，例如 `AutoSmokeNode`。

该组件挂载在关键 UI 节点、弹窗节点、主城建筑、大地图对象、重要按钮或可交互对象上。

### 4.2 示例字段

```csharp
using UnityEngine;

public class AutoSmokeNode : MonoBehaviour
{
    public string testId;
    public string nodeType;
    public bool clickable;
    public bool visible = true;
    public string pageId;
    public string group;
    public string actionType;
    public int priority;
    public bool dangerous;
}
```

### 4.3 字段说明

| 字段 | 说明 | 示例 |
| --- | --- | --- |
| `testId` | 自动化唯一识别 ID | `maincity.building.barracks` |
| `nodeType` | 节点业务类型 | `Button`、`Popup`、`Building`、`MapObject` |
| `clickable` | 是否允许自动点击 | `true` |
| `visible` | 是否当前可见 | `true` |
| `pageId` | 所属页面或场景 | `MainCity` |
| `group` | 所属区域或分组 | `topbar`、`building_area` |
| `actionType` | 点击行为类型 | `open`、`close`、`confirm`、`navigate` |
| `priority` | 探索优先级 | `10` |
| `dangerous` | 是否危险操作 | `true` / `false` |

### 4.4 推荐 testId 命名规范

建议统一使用：

```text
页面.区域.对象.动作
```

示例：

```text
maincity.topbar.power
maincity.building.barracks
maincity.popup.upgrade.confirm
maincity.popup.upgrade.cancel
worldmap.resource.wood.click
worldmap.city.enemy.open
bag.item.use
mail.list.item.open
```

命名要求：

- 全项目唯一，至少在同一页面内唯一。
- 使用小写英文、数字、下划线。
- 不依赖中文显示文本。
- 不依赖 Unity 对象名。
- 动作按钮应体现动作语义，例如 `confirm`、`cancel`、`close`、`open`。

## 5. clickable 修正策略

当 UI 树中 `clickable=False` 时，IDE 不应直接判定不可点击，而应进行二次修正。

### 5.1 可点击判断来源

满足以下任一条件时，可自动修正为可点击：

- 节点挂载 `AutoSmokeNode` 且 `clickable=true`。
- 节点包含 `Button` 组件。
- 节点包含 `Toggle` 组件。
- 节点包含 `Slider` 组件。
- 节点包含 `InputField` 或 `TMP_InputField` 组件。
- 节点包含 `EventTrigger` 组件。
- 节点实现 `IPointerClickHandler`。
- 节点的 `Image.raycastTarget=true` 且存在事件处理脚本。

### 5.2 修正结果记录

IDE 应记录修正来源：

```json
{
  "testId": "maincity.popup.upgrade.confirm",
  "originClickable": false,
  "fixedClickable": true,
  "reason": "Unity Button component detected"
}
```

### 5.3 风险控制

以下对象即使可点击，也不应自动点击：

- `dangerous=true` 的节点。
- 支付、充值、删除账号、退出登录、消耗钻石等危险操作。
- 未标注但命中危险关键词的对象。
- 当前用例未授权执行的高风险动作。

危险动作应标记为 `BLOCKED`，并进入报告。

## 6. type 修正策略

当 UI 树中大部分节点 `type=Node` 时，IDE 应根据 Unity 组件与测试标注推断真实类型。

### 6.1 类型推断规则

| 判断来源 | 推断类型 |
| --- | --- |
| `AutoSmokeNode.nodeType` | 使用显式标注类型 |
| `Button` | `Button` |
| `Toggle` | `Toggle` |
| `Slider` | `Slider` |
| `InputField` / `TMP_InputField` | `Input` |
| `Text` / `TMP_Text` | `Text` |
| `ScrollRect` | `ScrollView` |
| `Canvas` | `PageRoot` |
| `CanvasGroup` + 子节点 | `Panel` |
| 含关闭按钮的浮层 | `Popup` |
| 场景建筑标注 | `Building` |
| 地图资源/城池/部队标注 | `MapObject` |

### 6.2 输出示例

```json
{
  "name": "Button_Confirm",
  "originType": "Node",
  "fixedType": "Button",
  "testId": "maincity.popup.upgrade.confirm",
  "source": "Button component"
}
```

## 7. IDE 可测性扫描

IDE 接入 Unity 项目后，应提供“可测性扫描”功能，用于提前发现自动化不可控问题。

### 7.1 扫描内容

- 是否存在重复 `testId`。
- 关键按钮是否缺少 `testId`。
- 弹窗是否缺少关闭按钮。
- 可点击对象是否缺少 `clickable=true` 标注。
- `dangerous` 动作是否已标记。
- 主城建筑是否已标注为 `Building`。
- 大地图对象是否已标注为 `MapObject`。
- Poco 原始属性与 IDE 推断属性是否冲突。

### 7.2 扫描输出示例

```text
[ERROR] duplicate testId: maincity.popup.upgrade.confirm
[WARNING] Button object missing testId: Canvas/Main/Upgrade/Button_Confirm
[WARNING] clickable=false but Button component detected, fixed automatically
[ERROR] popup missing close/cancel node: maincity.popup.upgrade
[WARNING] main city building missing AutoSmokeNode: Barracks
```

### 7.3 输出文件

建议输出：

```text
.autosmoke/reports/accessibility_scan.json
.autosmoke/reports/accessibility_scan.html
```

其中 `json` 供程序消费，`html` 供测试与开发人员查看。

## 8. 主城场景对象导出

SLG 主城中，建筑、装饰、可点击区域通常不是传统 UI 控件。  
建议单独提供 `SceneStateExporter`，导出主城可交互对象。

### 8.1 导出内容

```json
{
  "scene": "MainCity",
  "objects": [
    {
      "testId": "maincity.building.barracks",
      "type": "Building",
      "clickable": true,
      "screenRect": [120, 300, 180, 360],
      "state": "idle",
      "level": 12,
      "visible": true
    }
  ]
}
```

### 8.2 验收标准

- 至少能导出当前屏幕内可见建筑。
- 每个可点击建筑都有稳定 `testId`。
- 点击建筑后能记录页面跳转、弹窗打开或状态变化。
- 建筑被遮挡或不可见时不应自动点击。

## 9. 大地图对象导出

SLG 大地图支持缩放、拖拽、网格扫描，不能只依赖单屏 UI 树。

### 9.1 导出内容

```json
{
  "scene": "WorldMap",
  "zoom": 3,
  "center": [1024, 2048],
  "objects": [
    {
      "testId": "worldmap.resource.wood.1024_2048",
      "type": "Resource",
      "clickable": true,
      "worldPos": [1024, 2048],
      "screenRect": [300, 420, 360, 480],
      "level": 5,
      "visible": true
    }
  ]
}
```

### 9.2 扫描策略

- 按缩放等级扫描。
- 按网格中心点拖拽扫描。
- 每次扫描记录 `zoom`、中心坐标、对象数量。
- 对重复对象按 `testId` 或世界坐标去重。
- 对不可点击或危险对象跳过。

## 10. 自动化识别优先级

IDE 在执行点击、探索和断言时，应按以下顺序识别对象：

```text
1. testId 精确匹配
2. AutoSmokeNode 显式标注
3. Unity 组件推断
4. Poco 原始属性
5. 节点名称规则
6. OCR / 图像识别 / 坐标兜底
```

任何通过第 5、6 层识别出的对象，都应在报告中标记为低可信度。

## 11. 用例执行中的对象定位建议

Excel 用例中建议优先使用 `testId` 定位。

示例：

```text
点击 maincity.building.barracks
点击 maincity.popup.upgrade.confirm
断言 maincity.popup.upgrade.title 存在
点击 worldmap.resource.wood.1024_2048
```

不推荐写法：

```text
点击 确定
点击 Button_1
点击 第三个按钮
点击 屏幕右下角
```

对于旧用例，可由 IDE 提供一次性映射功能，将中文名称、旧节点名映射到新的 `testId`。

## 12. 报告体现方式

当自动化系统发现 UI 树属性不可信时，报告中应清晰体现：

- 原始 `clickable/type` 值。
- 修正后的 `clickable/type` 值。
- 修正来源。
- 是否为低可信度识别。
- 是否需要开发补充标注。

示例：

```json
{
  "node": "Canvas/Main/Button_Confirm",
  "origin": {
    "clickable": false,
    "type": "Node"
  },
  "fixed": {
    "clickable": true,
    "type": "Button"
  },
  "source": "Unity Button component",
  "confidence": "high",
  "suggestion": "add testId: maincity.popup.upgrade.confirm"
}
```

## 13. 验收标准

### 13.1 clickable 治理验收

- 原始 `clickable=False` 的 Button 节点可被正确修正。
- 修正后的可点击节点可以被 IDE 执行点击。
- 危险按钮不会被自动点击。
- 修正原因写入报告。

### 13.2 type 治理验收

- 原始 `type=Node` 的 Button、Text、Input、ScrollView 可被正确推断。
- 业务对象如 `Building`、`MapObject` 可通过 `AutoSmokeNode` 识别。
- 推断失败时保留原始信息并输出警告。

### 13.3 testId 治理验收

- 重复 `testId` 能被扫描发现。
- 缺失 `testId` 的关键节点能被扫描提示。
- 同一用例在不同机器、不同项目路径下仍能通过 `testId` 定位。

### 13.4 主城与大地图验收

- 主城可导出建筑对象列表。
- 大地图可按缩放和网格导出对象列表。
- 点击对象后能记录前后状态差异。
- 不依赖节点名称也能完成基本探索。

## 14. 分阶段落地建议

### 阶段一：IDE 自动推断

先不要求项目大规模改造。  
IDE 基于 Unity 组件修正 `clickable/type`，并生成可测性扫描报告。

目标：

- 解决大部分 Button 识别失败问题。
- 暂时允许通过名称兜底。
- 产出缺失标注清单。

### 阶段二：关键页面补 testId

优先给高频页面和核心链路补充 `AutoSmokeNode`。

建议范围：

- 登录
- 主城
- 建筑升级弹窗
- 背包
- 邮件
- 任务
- 大地图资源点

目标：

- 核心用例不再依赖节点名称。
- 关键路径可稳定复跑。

### 阶段三：主城与大地图导出

接入 `SceneStateExporter`，独立导出场景对象。

目标：

- 主城建筑可自动发现。
- 大地图对象可按网格扫描。
- 页面关系图可记录 UI 与场景对象之间的跳转关系。

### 阶段四：质量门禁

将可测性扫描加入 CI 或版本提测流程。

目标：

- 重复 `testId` 阻断提测。
- 核心页面缺少关闭按钮阻断提测。
- 危险动作未标注阻断自动探索。
- 自动化可维护性变成项目质量的一部分。

## 15. 结论

对于 Unity 游戏，尤其是 SLG 主城和大地图场景，原始 UI 树的 `clickable` 和 `type` 不可信是常态。

可靠方案不是继续依赖节点名称猜测，而是建立：

```text
AutoSmokeNode 显式标注
+ Unity 组件类型推断
+ IDE 可测性扫描
+ SceneStateExporter 场景对象导出
+ 命名/OCR/坐标兜底
```

这样可以显著降低误判，提高自动探索、用例执行、异常检测和报告分析的稳定性。
