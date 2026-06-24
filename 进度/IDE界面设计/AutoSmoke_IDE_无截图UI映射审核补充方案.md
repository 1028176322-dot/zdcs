# AutoSmoke IDE 无截图 UI 映射审核补充方案

## 1. 背景

当前 IDE 的 UI 树与元素映射页面采用三栏布局：

```text
左侧：草稿列表
中间：截图高亮
右侧：详情编辑
```

这是正确方向。

但当前实际情况是：

```text
Unity 已导出所有 UI 清单
但没有对应页面截图
```

此时中间“截图高亮”区域无法显示元素在游戏中的真实位置，导致用户无法直接判断映射是否正确。

因此需要补充：

```text
无截图情况下的结构审核模式
```

## 2. 核心结论

没有截图时，不能进行完整视觉审核。

但仍然可以基于结构信息进行初步审核：

```text
节点路径
中文描述
文本
组件
spriteName
prefabPath
runtimePath
role
evidence
clickTargetNode
visualNode
```

因此 IDE 需要支持两种审核模式：

| 模式 | 条件 | 用途 |
|---|---|---|
| 截图审核模式 | 有页面截图 + highlightRect | 最推荐，可视觉确认 |
| 结构审核模式 | 无页面截图 | 初步确认，不能等同最终点击确认 |

## 3. 审核状态分级

当前“已映射”过于笼统。

建议扩展为分级审核状态：

| 状态 | 含义 | 是否可用于自动点击 |
|---|---|---|
| `pending` | 待审核 | 否 |
| `structure_confirmed` | 结构确认，未看截图 | 谨慎使用 |
| `visual_confirmed` | 视觉确认，截图高亮正确 | 可用 |
| `click_confirmed` | 点击确认，Unity 注入命中 | 推荐使用 |
| `modified` | 人工修改过 | 视确认级别 |
| `ignored` | 忽略 | 否 |
| `rejected` | 拒绝 | 否 |

推荐自动点击默认只使用：

```text
click_confirmed
visual_confirmed
```

如果使用 `structure_confirmed`，报告中必须标记：

```text
映射仅结构确认，未视觉/点击验证
```

## 4. 页面布局调整

### 4.1 顶部状态区

在映射审核页面顶部增加：

```text
当前审核模式：截图审核 / 结构审核
截图状态：已加载 / 缺失
草稿状态：已生成 / 未生成
导入状态：已导入 / 未导入
```

示例：

```text
当前审核模式：结构审核
截图状态：缺失
可视化可信度：中
建议：导入页面截图后再执行视觉确认
```

### 4.2 中间区域无截图提示

如果没有截图，中间区域不要空白显示“截图高亮”，而应显示：

```text
暂无页面截图，当前为结构审核模式

你可以：
1. 从 Unity 导出当前页面截图
2. 导入已有页面截图
3. 仅进行结构确认
4. 跳过该元素
```

按钮：

```text
从 Unity 获取截图
导入页面截图
仅结构确认
跳过该元素
```

### 4.3 左侧列表增强

左侧列表需要明确不同空状态。

#### 状态一：未导入数据

显示：

```text
未导入 Unity UI 数据
请先导入 project_ui_inventory.json 或 pages/*.json
```

按钮：

```text
导入 Unity 元素数据
```

#### 状态二：已导入但未生成草稿

显示：

```text
已导入 UI 清单，但尚未生成映射草稿
```

按钮：

```text
生成映射草稿
```

#### 状态三：草稿被筛选条件过滤

显示：

```text
当前筛选条件下无草稿
```

按钮：

```text
清空筛选
```

### 4.4 右侧详情增强

无截图时，右侧详情需要强化结构信息展示。

必须展示：

```text
中文名称
中文描述
核对提示
pageId
role
text
runtimePath
prefabPath
nodeName
components
spriteName
visualNode
clickTargetNode
clickAction
expectedAfterClick
confidence
evidence
```

## 5. 结构审核模式

### 5.1 适用场景

结构审核用于：

- 没有截图。
- 当前只有工程态 UI 清单。
- 当前只有运行态 UI tree，但没有页面截图。
- 需要先批量处理高置信度元素。

### 5.2 结构审核依据

结构审核主要看：

| 信息 | 示例 | 说明 |
|---|---|---|
| 页面 | `BagPanel` | 是否属于正确页面 |
| 节点名 | `ButtonUse` | 是否符合语义 |
| 文本 | `使用` | 是否明确 |
| 组件 | `Button` | 是否可点击 |
| 父节点 | `Bottom` | 是否位置合理 |
| prefabPath | `Assets/UI/Bag/BagPanel.prefab` | 是否属于正确 prefab |
| spriteName | `icon_item_1001` | 图标含义 |
| evidence | text/nodeName/component/position | 自动推断依据 |

### 5.3 结构确认条件

允许标记为 `structure_confirmed` 的条件：

```text
1. displayName 和 chineseDescription 明确
2. pageId 明确
3. role 明确
4. locator 存在
5. evidence 至少包含 text/nodeName/component 中两个
6. confidence >= 0.75
```

否则只能保持：

```text
pending
```

或标记：

```text
ignored / rejected
```

### 5.4 结构审核风险

结构审核无法确认：

- 元素真实显示位置。
- 是否被遮挡。
- visualNode 是否对应实际图标。
- clickTargetNode 是否是正确点击区域。
- Clone 列表项是否对应正确数据。
- 当前 UI 层级是否会变化。

因此结构审核不能替代视觉确认和点击确认。

## 6. 截图审核模式

### 6.1 进入条件

需要具备：

```text
screenshotRef
highlightRect
```

或：

```text
pageId 对应页面截图存在
元素 screenRect / normalizedRect 存在
```

### 6.2 截图审核能力

支持：

- 红框高亮当前元素。
- 黄框高亮实际点击目标。
- 蓝框高亮图标显示节点。
- 缩放 / 拖动截图。
- 点击截图反查元素。
- 测试点击。

### 6.3 视觉确认条件

允许标记为 `visual_confirmed` 的条件：

```text
1. 截图中能看到元素
2. 高亮区域正确
3. 中文描述与画面一致
4. 如果是图标，visualNode 与 clickTargetNode 区分正确
5. 用户点击确认
```

## 7. 点击确认模式

### 7.1 目的

点击确认是最高可信状态。

它证明：

```text
该映射不仅看起来正确，而且 Unity 点击能命中正确目标。
```

### 7.2 流程

```text
1. 用户点击“测试点击”
2. IDE 生成 click_request.json
3. Unity 执行 EventSystem 注入点击
4. Unity 写 click_result.json
5. IDE 校验 eventReceiver == targetGameObject
6. 如果有 expectedAfterClick，再校验页面/弹窗变化
7. 标记 click_confirmed
```

### 7.3 点击确认条件

```text
eventReceiver == targetGameObject
```

如果是图标 Tips：

```text
expectedAfterClick == ItemTipsPanel
```

## 8. 无截图时的推荐用户流程

```text
1. 导入 Unity UI 清单
2. 生成映射草稿
3. 进入映射草稿审核
4. IDE 显示：当前为结构审核模式
5. 用户筛选 confidence >= 0.85 的草稿
6. 查看中文描述 + path + text + components + evidence
7. 对明确元素标记 structure_confirmed
8. 对不明确元素保持 pending
9. 后续导入截图
10. 批量转入截图审核模式
11. 做 visual_confirmed
12. 关键点击目标执行测试点击
13. 做 click_confirmed
```

## 9. 有截图后的升级流程

当后续导入页面截图后：

```text
1. IDE 根据 pageId 匹配截图
2. 根据 screenRect / normalizedRect 生成 highlightRect
3. 将 structure_confirmed 元素加入“待视觉确认”列表
4. 用户逐个查看截图高亮
5. 正确则升级 visual_confirmed
6. 错误则修改或拒绝
```

## 10. 列表状态建议

左侧状态筛选建议增加：

```text
待审核
结构确认
视觉确认
点击确认
已修改
已忽略
已拒绝
缺截图
缺点击目标
低置信度
```

颜色建议：

| 状态 | 颜色 |
|---|---|
| pending | 蓝色 |
| structure_confirmed | 橙色 |
| visual_confirmed | 绿色 |
| click_confirmed | 深绿色 |
| modified | 紫色 |
| ignored | 灰色 |
| rejected | 红色 |

## 11. 数据结构补充

映射草稿增加：

```json
{
  "reviewStatus": "structure_confirmed",
  "reviewLevel": "structure",
  "hasScreenshot": false,
  "hasHighlightRect": false,
  "visualReviewRequired": true,
  "clickReviewRequired": true,
  "reviewWarnings": [
    "缺少页面截图，尚未视觉确认"
  ]
}
```

正式映射增加：

```json
{
  "review": {
    "status": "structure_confirmed",
    "level": "structure",
    "visualConfirmed": false,
    "clickConfirmed": false,
    "warnings": [
      "该映射仅结构确认"
    ]
  }
}
```

## 12. 自动点击使用策略

默认策略：

```text
click_confirmed：允许
visual_confirmed：允许
structure_confirmed：默认警告，可配置是否允许
pending：不允许
rejected：不允许
ignored：不允许
```

执行用例时，如果目标只达到 `structure_confirmed`：

```text
报告中标记风险：
目标仅结构确认，未完成视觉/点击确认。
```

## 13. IDE 验收标准

| 编号 | 场景 | 通过标准 |
|---|---|---|
| MAP-NOIMG-001 | 无截图进入审核 | IDE 显示结构审核模式 |
| MAP-NOIMG-002 | 无截图中间区域 | 显示导入截图/结构确认提示 |
| MAP-NOIMG-003 | 结构审核 | 能基于 path/text/component/evidence 确认 |
| MAP-NOIMG-004 | 状态分级 | 支持 structure/visual/click confirmed |
| MAP-NOIMG-005 | 后续导入截图 | structure_confirmed 可升级 visual_confirmed |
| MAP-NOIMG-006 | 测试点击 | visual_confirmed 可升级 click_confirmed |
| MAP-NOIMG-007 | 用例执行 | structure_confirmed 目标执行时报告风险 |

## 14. 最终建议

当前界面布局方向是对的：

```text
左列表 + 中截图 + 右编辑
```

但必须补充：

```text
无截图结构审核模式
审核状态分级
缺截图提示
结构确认到视觉确认再到点击确认的升级流程
```

这样即使 Unity 暂时只导出了 UI 清单，没有截图，也可以先做结构审核。

等后续补截图和测试点击后，再把关键元素升级为高可信映射。

