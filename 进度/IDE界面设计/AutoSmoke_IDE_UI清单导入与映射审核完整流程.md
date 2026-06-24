# AutoSmoke IDE：Unity UI 清单导入与映射审核完整流程

## 1. 目标

本流程解决以下问题：

```text
Unity 已经导出了所有 UI 清单后，
测试人员如何在 IDE 中导入，
如何生成映射草稿，
如何查看每个元素对应游戏里的什么，
如何确认、修改、补充，
最终如何生成可用于自动点击的 element_mapping.json。
```

最终目标：

```text
Unity 导出 UI 数据
  -> IDE 导入
    -> IDE 生成中文映射草稿
      -> 用户通过截图高亮审核
        -> 确认/修改/补充
          -> 生成正式元素映射
            -> 用例可通过 semanticId/testId 精准点击
```

## 2. IDE 所属位置

该功能放在：

```text
准备 → UI树与元素映射
```

推荐拆成 5 个子页面：

```text
1. Unity 数据导入
2. 导入校验报告
3. 映射草稿生成
4. 映射草稿审核
5. 正式映射管理
```

## 3. Unity 侧导出内容

Unity 导出的 UI 数据建议统一放在：

```text
E:\zdcs\AutoSmoke\runtime\ui_tree\
```

### 3.1 必需文件

```text
project_ui_inventory.json
pages\MainCity.json
pages\WorldMap.json
pages\BagPanel.json
pages\RewardPopup.json
screenshots\MainCity.png
screenshots\BagPanel.png
screenshots\RewardPopup.png
```

### 3.2 推荐文件

```text
current_ui_tree.json
enhanced_ui_tree.json
scene_objects.json
icon_inventory.json
accessibility_scan.json
page_graph.json
```

### 3.3 文件含义

| 文件 | 来源 | 作用 |
|---|---|---|
| `project_ui_inventory.json` | 工程态扫描 | 发现所有 prefab、按钮、图标、文本 |
| `pages/*.json` | 运行态采集 | 当前页面真实元素、坐标、可见性 |
| `screenshots/*.png` | Unity 直出截图 | 审核时高亮元素 |
| `scene_objects.json` | 场景对象导出 | 主城/大地图建筑、资源点、NPC |
| `icon_inventory.json` | 图标信息 | 道具图标、奖励图标、活动图标 |
| `accessibility_scan.json` | 可测试性扫描 | 缺 testId、重名、Missing 等问题 |

## 4. 第一步：IDE 导入 Unity 数据

### 4.1 入口

```text
准备 → UI树与元素映射 → Unity 数据导入
```

### 4.2 页面布局

```text
┌──────────────────────────────────────────────┐
│ Unity 数据导入                                │
├──────────────────────────────────────────────┤
│ 导出目录：[E:\zdcs\AutoSmoke\runtime\ui_tree] │
│ [选择目录] [扫描可导入文件] [导入并校验]       │
├──────────────────────────────────────────────┤
│ 文件列表                                      │
│ project_ui_inventory.json   可导入  205000节点 │
│ pages/BagPanel.json         可导入  530节点    │
│ screenshots/BagPanel.png    可导入             │
└──────────────────────────────────────────────┘
```

### 4.3 操作步骤

```text
1. 点击“选择目录”
2. 选择 Unity 导出目录
3. 点击“扫描可导入文件”
4. IDE 展示文件列表
5. 点击“导入并校验”
6. IDE 生成 import_report.json
```

### 4.4 导入模式

| 模式 | 说明 | 使用场景 |
|---|---|---|
| 全量导入 | 重新导入全部 Unity 数据 | 第一次接入或大版本更新 |
| 增量导入 | 只导入新增或变化的页面/节点 | 日常迭代 |
| 页面导入 | 只导入指定页面 | 调试某个功能 |

### 4.5 导入校验

IDE 校验：

```text
文件是否存在
schemaVersion 是否支持
JSON 是否合法
pageId 是否存在
nodes 是否为空
path 是否唯一
screenRect 是否合法
screenshotRef 是否存在
图标是否有 visualNode/clickTargetNode
中文描述字段是否存在
```

### 4.6 校验结果示例

```text
导入成功：
  project_ui_inventory.json：205000 个节点
  BagPanel.json：530 个运行态节点
  RewardPopup.json：96 个运行态节点

警告：
  128 个节点缺少 screenRect
  35 个图标缺少 clickTargetNode
  12 个元素缺少中文描述

错误：
  WorldMap.json 缺少 pageId，需要重新导出
```

## 5. 第二步：合并增强

### 5.1 入口

```text
准备 → UI树与元素映射 → 合并增强
```

### 5.2 作用

将工程态和运行态数据合并：

```text
project_ui_inventory.json
pages/*.json
screenshots/*.png
icon_inventory.json
scene_objects.json
```

生成：

```text
enhanced_ui_tree.json
```

### 5.3 合并规则

匹配优先级：

```text
P0 prefab source / guid
P1 runtimePath 与 prefabPath 后缀匹配
P2 节点名 + 组件类型
P3 文本 + 坐标
P4 人工绑定
```

### 5.4 合并结果展示

```text
页面数：12
元素数：14140
可点击元素：923
图标元素：1180
场景对象：86
可生成草稿：2100
需要人工补充：35
```

## 6. 第三步：生成映射草稿

### 6.1 入口

```text
准备 → UI树与元素映射 → 生成映射草稿
```

### 6.2 生成内容

输出：

```text
element_mapping_draft.json
```

每条草稿必须包含：

```text
中文名称 displayName
中文描述 chineseDescription
核对提示 reviewHint
建议 testId
建议 semanticId
页面 pageId
类型 role
定位信息 locator
截图引用 screenshotRef
高亮区域 highlightRect
推断依据 evidence
置信度 confidence
审核状态 reviewStatus
```

### 6.3 草稿示例：按钮

```json
{
  "draftId": "draft_0001",
  "reviewStatus": "pending",
  "displayName": "使用按钮",
  "chineseDescription": "背包界面底部的黄色【使用】按钮，用于使用当前选中的道具。",
  "reviewHint": "截图中位于背包界面底部中间，按钮文字为“使用”。",
  "suggestedTestId": "Bag.UseButton",
  "suggestedSemanticId": "背包.使用按钮",
  "pageId": "BagPanel",
  "role": "primary_action_button",
  "runtimePath": "DeepUI/DialogUI/BagPanel/ButtonUse",
  "confidence": 0.88,
  "screenshotRef": "screenshots/BagPanel.png",
  "highlightRect": {
    "x": 465,
    "y": 2180,
    "width": 240,
    "height": 80
  },
  "evidence": {
    "text": "使用",
    "nodeName": "ButtonUse",
    "component": "Button",
    "position": "bottom_center"
  }
}
```

### 6.4 草稿示例：图标

```json
{
  "draftId": "draft_icon_0001",
  "reviewStatus": "pending",
  "displayName": "高级招募券图标",
  "chineseDescription": "奖励弹窗中的【高级招募券】道具图标，数量为 2，点击后应打开高级招募券的道具详情 Tips。",
  "reviewHint": "截图中位于奖励列表内，图标为金色招募券，右下角数量显示 2。",
  "suggestedTestId": "RewardPopup.ItemIcon.1001",
  "suggestedSemanticId": "奖励弹窗.道具图标.高级招募券",
  "pageId": "RewardPopup",
  "role": "interactive_item_icon",
  "visualNode": "RewardPopup/RewardList/Item_0/Icon",
  "clickTargetNode": "RewardPopup/RewardList/Item_0",
  "clickAction": "open_item_tips",
  "expectedAfterClick": "ItemTipsPanel",
  "confidence": 0.86
}
```

## 7. 第四步：观看和审核映射草稿

### 7.1 入口

```text
准备 → UI树与元素映射 → 映射草稿审核
```

### 7.2 三栏布局

```text
┌────────────────────┬──────────────────────────┬────────────────────┐
│ 左：草稿列表         │ 中：截图高亮               │ 右：详情与编辑       │
├────────────────────┼──────────────────────────┼────────────────────┤
│ 待审核 使用按钮      │ BagPanel 截图              │ 中文名称             │
│ 待审核 高级招募券图标 │ 红框：当前元素              │ 中文描述             │
│ 已确认 确认按钮      │ 黄框：点击目标              │ testId              │
│ 已拒绝 装饰图标      │ 蓝框：图标显示节点           │ semanticId          │
└────────────────────┴──────────────────────────┴────────────────────┘
```

### 7.3 左侧列表

默认显示：

| 状态 | 中文名称 | 页面 | 类型 | 置信度 |
|---|---|---|---|---:|
| 待审核 | 使用按钮 | 背包界面 | 主操作按钮 | 0.88 |
| 待审核 | 高级招募券图标 | 奖励弹窗 | 可点击道具图标 | 0.86 |
| 已确认 | 确认按钮 | 奖励弹窗 | 确认按钮 | 0.94 |

支持筛选：

```text
页面
状态
类型
是否可点击
置信度
关键词
```

### 7.4 中间截图高亮

高亮颜色：

| 颜色 | 含义 |
|---|---|
| 红框 | 当前元素区域 |
| 黄框 | 实际点击区域 clickTargetNode |
| 蓝框 | 图标显示区域 visualNode |
| 绿框 | 父容器 / 面板 |
| 灰框 | 被遮挡或不可点击 |

图标类元素必须显示：

```text
蓝框：Icon 节点
黄框：ItemCell 父节点
```

### 7.5 右侧详情

右侧展示并可编辑：

```text
中文名称
中文描述
核对提示
testId
semanticId
pageId
role
locator
runtimePath
prefabPath
visualNode
clickTargetNode
clickAction
expectedAfterClick
evidence
confidence
```

### 7.6 人工审核操作

每条草稿支持：

```text
确认
修改后确认
拒绝
忽略
标记为纯展示图标
标记为可点击图标
合并重复项
测试点击
```

状态流转：

```text
pending -> confirmed
pending -> modified
pending -> rejected
pending -> ignored
modified -> confirmed
```

## 8. 第五步：修改映射草稿

### 8.1 什么时候需要修改

常见情况：

```text
中文描述不准确
testId 命名不合适
semanticId 不符合习惯
role 判断错误
clickTargetNode 错误
图标被误判为按钮
纯展示图标被误判为可点击
```

### 8.2 修改内容

可以修改：

```text
displayName
chineseDescription
reviewHint
testId
semanticId
role
locator
clickTargetNode
clickAction
expectedAfterClick
```

### 8.3 保存规则

修改后：

```text
reviewStatus = modified
```

点击确认后：

```text
reviewStatus = confirmed
```

## 9. 第六步：补充未扫描元素

### 9.1 入口

```text
准备 → UI树与元素映射 → 映射草稿审核 → 新增元素
```

### 9.2 补充方式

| 方式 | 适用场景 |
|---|---|
| 截图点选补充 | 界面可见但扫描没识别 |
| Unity 当前选中对象补充 | Hierarchy 能选中 |
| 手动路径补充 | 已知 runtimePath / pocoPath |
| 业务对象补充 | 建筑、道具、活动、场景对象 |

### 9.3 截图点选补充

流程：

```text
1. 在截图上框选元素
2. IDE 反查附近 UI 节点
3. 如果找到候选，绑定候选节点
4. 如果找不到，创建 manualRect
5. 填写中文名称、描述、pageId、role、testId
6. 保存为 manual confirmed
```

### 9.4 Unity 当前选中对象补充

流程：

```text
1. 在 Unity Hierarchy 选中目标
2. Unity 菜单：AutoSmoke/UI/Export Selected Element
3. IDE 读取 selected_element.json
4. 自动填入 path、组件、坐标
5. 用户补中文描述和 testId
6. 保存正式映射
```

### 9.5 手动路径补充

流程：

```text
1. 选择 locator 类型：runtimePath / pocoPath / prefabPath
2. 输入路径
3. 点击验证定位
4. 验证成功后保存
```

### 9.6 业务对象补充

适合：

```text
Building.Barracks
Activity.IslandTrial
Item.1001
SceneObject.Monster_001
```

保存时需要：

```text
data.type
data.id
click.method
expectedAfterClick
```

## 10. 第七步：测试点击

### 10.1 目的

确认映射不仅看起来正确，而且 Unity 点击能命中。

### 10.2 流程

```text
1. 用户点击“测试点击”
2. IDE 生成 click_request.json
3. Unity 执行 EventSystem 注入点击
4. Unity 写 click_result.json
5. IDE 展示结果
```

### 10.3 成功标准

```text
eventReceiver == targetGameObject
```

如果有 `expectedAfterClick`：

```text
点击后页面/弹窗符合预期
```

## 11. 第八步：生成正式映射

### 11.1 输出文件

```text
E:\zdcs\AutoSmoke\runtime\ui_tree\element_mapping.json
```

### 11.2 进入正式映射的条件

```text
reviewStatus = confirmed
```

或：

```text
source = manual
review.status = confirmed
```

### 11.3 正式映射示例

```json
{
  "Bag.UseButton": {
    "testId": "Bag.UseButton",
    "semanticId": "背包.使用按钮",
    "displayName": "使用按钮",
    "chineseDescription": "背包界面底部的黄色【使用】按钮，用于使用当前选中的道具。",
    "pageId": "BagPanel",
    "role": "primary_action_button",
    "locator": {
      "type": "runtimePath",
      "value": "DeepUI/DialogUI/BagPanel/ButtonUse"
    },
    "click": {
      "method": "unity_event_system",
      "safePoint": "center"
    },
    "review": {
      "status": "confirmed",
      "reviewedAt": "2026-06-16T12:00:00"
    }
  }
}
```

## 12. 第九步：后续重新导入如何保护人工修改

重新导入 Unity 数据时不能覆盖人工确认结果。

合并优先级：

```text
manual confirmed > confirmed > modified > draft pending
```

如果发现新导入元素疑似匹配已有人工元素：

```text
IDE 提示：发现可能匹配的自动候选，是否合并？
```

合并时：

保留人工字段：

```text
displayName
chineseDescription
semanticId
testId
role
```

补充自动字段：

```text
runtimePath
prefabPath
screenRect
components
evidence
```

## 13. 完整用户操作流

```text
1. Unity 中扫描 UI Prefab
2. Unity 中导出当前页面 UI 树和截图
3. 回到 IDE
4. 准备 → UI树与元素映射 → Unity 数据导入
5. 扫描可导入文件
6. 导入并校验
7. 合并增强
8. 生成映射草稿
9. 打开映射草稿审核面板
10. 查看中文描述
11. 查看截图高亮
12. 确认正确元素
13. 修改错误描述或 testId
14. 补充未扫描元素
15. 测试点击
16. 保存正式 element_mapping.json
17. 用例中使用 semanticId/testId 自动点击
```

## 14. IDE 验收标准

| 编号 | 功能 | 通过标准 |
|---|---|---|
| MAPFLOW-001 | 导入 Unity 数据 | 能识别 project_ui_inventory/pages/screenshots |
| MAPFLOW-002 | 导入校验 | 能报告缺 pageId、缺 screenRect、缺中文描述 |
| MAPFLOW-003 | 生成草稿 | 能生成带中文描述的 element_mapping_draft.json |
| MAPFLOW-004 | 草稿列表 | 能按页面/状态/类型/置信度筛选 |
| MAPFLOW-005 | 截图高亮 | 点击草稿后高亮正确元素 |
| MAPFLOW-006 | 图标审核 | visualNode 和 clickTargetNode 分别显示 |
| MAPFLOW-007 | 修改保存 | 修改 testId/semanticId/描述后可保存 |
| MAPFLOW-008 | 人工补充 | 能新增未扫描元素 |
| MAPFLOW-009 | 测试点击 | eventReceiver 等于 targetGameObject |
| MAPFLOW-010 | 正式映射 | confirmed 元素进入 element_mapping.json |
| MAPFLOW-011 | 重新导入保护 | 人工确认映射不被覆盖 |

## 15. 最终建议

IDE 中这条链路必须做成完整闭环：

```text
导入
  -> 校验
    -> 生成草稿
      -> 查看
        -> 确认 / 修改 / 补充
          -> 测试点击
            -> 保存正式映射
```

不要让用户直接面对 JSON。

用户主要看到：

```text
中文描述
截图高亮
实际点击区域
测试点击结果
```

