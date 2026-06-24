# AutoSmoke 元素审核编辑区字段中文说明补充方案

## 1. 背景

当前 IDE 的“UI树与元素映射”审核页右侧编辑区域展示了很多字段，例如：

```text
components
suggestedTestId
suggestedSemanticId
reviewHint
risk
path
runtimePath
clickTargetNode
visualNode
```

但这些字段如果只显示英文名，测试人员很难判断：

```text
这个字段是什么意思
是否需要修改
修改错了有什么影响
什么情况下必须填写
它和自动点击有什么关系
```

因此右侧编辑区必须增加中文说明。

## 2. 修改目标

右侧编辑区每一项都要显示：

```text
中文字段名
字段作用
是否可编辑
是否必填
错误影响
示例值
```

目标是让审核人员不用理解代码字段，也能完成元素确认。

## 3. 推荐展示方式

每个字段建议显示为：

```text
中文名称
英文字段名
输入框/只读框
简短说明
风险提示
```

示例：

```text
显示名称
字段：displayName
[背包-使用按钮]
说明：在 IDE 中展示给测试人员看的元素名称，建议使用中文。
影响：不会直接影响点击，但会影响审核和报告可读性。
```

## 4. 字段分组

右侧编辑区不要平铺所有字段，建议分组展示。

```text
基础信息
语义标识
页面与类型
点击定位
运行态匹配
视觉确认
点击验证
审核状态
风险与建议
原始来源
```

## 5. 字段中文说明清单

### 5.1 基础信息

| 中文名 | 字段名 | 是否可编辑 | 作用 |
|---|---|---|---|
| 节点路径 | `path` | 否 | 当前元素在候选库中的唯一标识，通常由 prefab 路径或运行态路径生成 |
| 显示名称 | `displayName` | 是 | 给测试人员看的中文名称，审核列表和报告中优先显示 |
| 中文描述 | `chineseDescription` | 是 | 解释这个元素在游戏中的作用，例如“背包界面底部的使用按钮” |
| 显示文本 | `text` | 否 | Unity 节点上真实显示的文字，例如“使用”“确定” |
| 节点名 | `nodeName` | 否 | Unity GameObject 名称，用于辅助判断元素来源 |
| 组件 | `components` | 否 | Unity 节点挂载的组件列表，例如 Button、Image、Text |

说明：

```text
displayName 和 chineseDescription 是审核人员最常改的字段。
path、nodeName、components 不建议人工修改。
```

### 5.2 语义标识

| 中文名 | 字段名 | 是否可编辑 | 作用 |
|---|---|---|---|
| 用例ID | `testId` | 是 | 用例步骤可以直接引用的稳定 ID |
| 推荐用例ID | `suggestedTestId` | 否 | IDE 自动根据页面、节点名、文本生成的建议值 |
| 语义ID | `semanticId` | 是 | 更偏业务语义的元素标识，例如 `bag.use` |
| 推荐语义ID | `suggestedSemanticId` | 否 | IDE 自动生成的语义 ID 建议 |

建议：

```text
testId / semanticId 一旦被用例引用，后续不要轻易改。
如果必须改，需要 IDE 提示哪些用例会受到影响。
```

### 5.3 页面与类型

| 中文名 | 字段名 | 是否可编辑 | 作用 |
|---|---|---|---|
| 所属页面 | `pageId` | 可编辑 | 元素所在页面，例如 BagPanel、RewardPopup、MainCity |
| 元素类型 | `elementType` | 可编辑 | 元素分类，例如 button、interactive_icon、item_cell |
| 交互方式 | `interactionType` | 可编辑 | 自动化应该怎么操作它，例如 click、drag、scroll、blank_close |
| 角色 | `role` | 可编辑 | 元素的业务角色，例如 confirm、close_popup、use_action |
| 优先级 | `priority` | 可编辑 | 审核优先级，例如 P0、P1、P2、LOW |

说明：

```text
pageId 决定“当前页匹配”是否能找到它。
elementType 决定它在 IDE 中归类到按钮、图标、格子还是场景对象。
interactionType 决定后续执行点击、拖拽、滚动还是空白关闭。
```

### 5.4 点击定位

| 中文名 | 字段名 | 是否可编辑 | 作用 |
|---|---|---|---|
| 点击目标 | `clickTargetNode` | 可编辑 | 真正接收点击事件的节点 |
| 视觉节点 | `visualNode` | 可编辑 | 用户在界面上看到的节点 |
| 运行态路径 | `runtimePath` | 否/谨慎编辑 | Unity 当前运行时真实路径 |
| Prefab 路径 | `prefabPath` | 否 | 工程中 prefab 文件路径 |
| Prefab 节点路径 | `prefabNodePath` | 否 | prefab 内部节点路径 |
| 屏幕区域 | `screenRect` | 否 | 当前运行态元素在截图上的区域 |

重点说明：

```text
visualNode 是“看见谁”。
clickTargetNode 是“点谁”。
```

示例：

```text
道具图标：
visualNode = BagPanel/List/Item_001/Icon
clickTargetNode = BagPanel/List/Item_001
```

风险：

```text
clickTargetNode 错了，自动点击就会点错对象。
visualNode 错了，高亮图就会框错位置。
```

### 5.5 运行态匹配

| 中文名 | 字段名 | 是否可编辑 | 作用 |
|---|---|---|---|
| 运行态匹配 | `runtimeMatch.status` | 否 | 当前元素是否匹配到 Unity 实时 UI 树 |
| 匹配分数 | `runtimeMatch.matchScore` | 否 | 匹配可信度，越高越可靠 |
| 匹配级别 | `runtimeMatch.matchLevel` | 否 | 使用哪种规则匹配成功，例如 runtimePath、text、spriteName |
| 运行态实例ID | `runtimeMatch.instanceId` | 否 | Unity 当前对象实例 ID |
| 是否可见 | `runtimeMatch.visible` | 否 | 当前对象是否可见 |
| 是否可交互 | `runtimeMatch.interactable` | 否 | 当前对象是否处于可交互状态 |
| 匹配时间 | `runtimeMatch.matchedAt` | 否 | 最近一次匹配时间 |

说明：

```text
runtimeMatch 是判断“工程草稿是否对应当前真实界面元素”的核心依据。
没有 runtimeMatch，不应该进入点击确认。
```

### 5.6 视觉确认

| 中文名 | 字段名 | 是否可编辑 | 作用 |
|---|---|---|---|
| 是否有截图 | `hasScreenshot` | 否 | 当前元素是否有可用于审核的页面截图 |
| 是否有高亮区域 | `hasHighlightRect` | 否 | 是否能在截图上画出元素区域 |
| 高亮图片 | `visualReview.highlightImage` | 否 | IDE 生成的带红框截图 |
| 视觉确认状态 | `visualReview.confirmed` | 否 | 用户是否确认高亮正确 |

说明：

```text
视觉确认表示“人眼看过红框，确认框的是正确元素”。
视觉确认不等于点击确认。
```

### 5.7 点击验证

| 中文名 | 字段名 | 是否可编辑 | 作用 |
|---|---|---|---|
| 点击验证状态 | `clickVerification.status` | 否 | 点击验证是否通过 |
| 点击方式 | `clickVerification.method` | 否 | 使用 Unity 注入点击还是其它方式 |
| 命中对象 | `clickVerification.hitRuntimePath` | 否 | 实际收到点击事件的对象 |
| 期望对象 | `clickVerification.expectedRuntimePath` | 否 | 预期应该被点击的对象 |
| 事件是否匹配 | `clickVerification.eventReceiverMatched` | 否 | 实际命中对象是否等于期望对象 |
| 验证时间 | `clickVerification.verifiedAt` | 否 | 最近一次点击验证时间 |
| 失败原因 | `clickVerification.reason` | 否 | 点击失败原因 |

说明：

```text
clickVerification.status=passed 后，元素才能升级为 click_confirmed。
```

## 6. 审核状态字段说明

| 中文状态 | 字段值 | 含义 |
|---|---|---|
| 待审核 | `pending` / `auto_draft` | 自动生成的候选，还没有人工确认 |
| 结构确认 | `structure_confirmed` | 仅通过路径、名称、文本判断，未实时匹配 |
| 运行态匹配 | `runtime_matched` | 已在 Unity 当前实时 UI 树中匹配到 |
| 视觉确认 | `visual_confirmed` | 截图高亮已人工确认正确 |
| 点击确认 | `click_confirmed` | Unity 注入点击验证通过 |
| 人工修改 | `modified` | 人工修改过字段，需要重新确认 |
| 已忽略 | `ignored` | 确认不参与自动化 |
| 已拒绝 | `rejected` | 确认该草稿错误 |

右侧状态区应该显示：

```text
当前状态：运行态匹配
下一步建议：生成高亮图并进行视觉确认
```

## 7. 风险字段说明

| 中文名 | 字段名 | 含义 |
|---|---|---|
| 风险列表 | `risk` | IDE 自动识别出的风险 |
| 审核提示 | `reviewHint` | IDE 给审核人员的建议 |
| 匹配冲突 | `runtimeMatch.conflicts` | 一个草稿匹配到多个运行态节点 |
| 缺少点击目标 | `missingClickTarget` | 没有明确 clickTargetNode |
| 缺少截图 | `no_screenshot` | 当前无法视觉确认 |
| 缺少坐标 | `no_screen_rect` | 无法生成高亮图 |

常见风险解释：

```text
no_runtime_path：没有运行态路径，只能结构审核
no_screen_rect：没有截图坐标，不能高亮
no_screenshot：没有当前截图，不能视觉确认
multiple_candidates：匹配到多个候选，需要人工选择
not_visible：当前不可见，不能点击确认
not_interactable：当前不可交互，不能点击确认
blocked_by_popup：被弹窗遮挡，需先处理阻塞
```

## 8. 前端展示建议

### 8.1 每个字段增加说明图标

建议在字段标签旁增加：

```text
?
```

鼠标悬停显示：

```text
字段作用
是否可编辑
修改影响
示例
```

### 8.2 详情区分组折叠

右侧编辑区建议改为：

```text
基础信息
语义标识
页面与类型
点击定位
运行态匹配
视觉确认
点击验证
风险与建议
原始来源
```

默认展开：

```text
基础信息
点击定位
运行态匹配
风险与建议
```

默认折叠：

```text
原始来源
组件列表
Prefab 信息
```

### 8.3 必填字段标记

正式自动点击必须具备：

```text
displayName
semanticId 或 testId
pageId
elementType
interactionType
clickTargetNode
reviewStatus=click_confirmed
```

这些字段旁边显示：

```text
必填
```

### 8.4 字段校验提示

保存时检查：

```text
displayName 为空：提示“请填写中文显示名称”
semanticId/testId 都为空：提示“用例无法引用该元素”
clickTargetNode 为空：提示“无法执行自动点击”
pageId 为空：提示“无法进行当前页匹配”
elementType 为空：提示“无法分类审核”
```

## 9. 前端实现建议

不要在 `shDraft()` 里硬编码字段数组，例如：

```javascript
[['path','节点路径',1], ...]
```

建议改成字段配置：

```javascript
var FIELD_DEFS = [
  {
    key: 'displayName',
    label: '显示名称',
    group: '基础信息',
    editable: true,
    required: true,
    help: '给测试人员看的中文名称，审核列表和报告中优先显示。',
    example: '背包-使用按钮'
  },
  {
    key: 'clickTargetNode',
    label: '点击目标',
    group: '点击定位',
    editable: true,
    required: true,
    help: '真正接收点击事件的 Unity 节点。自动点击会优先点击该节点。',
    example: 'BagPanel/List/Item_001'
  }
];
```

渲染时按 group 分组。

## 10. 验收标准

### 10.1 字段说明验收

```text
右侧每个字段都有中文名称
每个字段都有用途说明
每个字段标明是否可编辑
关键字段标明是否必填
风险字段有中文解释
```

### 10.2 审核体验验收

```text
测试人员无需理解英文代码字段，也能判断该字段是否需要修改
点击目标和视觉节点的区别能看懂
运行态匹配状态能看懂
视觉确认和点击确认的区别能看懂
```

### 10.3 保存校验验收

```text
缺 displayName 时不能正式确认
缺 semanticId/testId 时提示用例无法引用
缺 clickTargetNode 时不能点击确认
缺 runtimeMatch 时不能视觉确认
缺 clickVerification 时不能标为 click_confirmed
```

## 11. 结论

右侧编辑区不是给开发人员看的 JSON 调试面板，而是给测试人员审核元素映射用的工作台。

因此它必须从：

```text
字段名 + 输入框
```

升级为：

```text
中文字段名 + 作用说明 + 示例 + 风险提示 + 校验规则
```

这样测试人员才能准确确认：

```text
这个元素是什么
它属于哪个页面
看到的是哪个节点
真正点的是哪个节点
有没有实时匹配
有没有视觉确认
有没有点击确认
是否能进入正式自动点击
```
