# AutoSmoke IDE 元素批量映射验证完整闭环实施方案

> 日期：2026-06-17  
> 约束：方案阶段已确认，允许后续进行代码改造；本文描述完整闭环，不是最小闭环。  
> 目标：避免逐个元素人工核对，通过“上游用例目标驱动 + 批量生成 + 运行态验证 + 高亮证据 + 点击验证 + 用例回放 + 失败反馈 + 版本重验”建立可信 testId / semanticId 映射体系。

---

## 1. 当前 IDE 已具备的相关能力

根据当前 AutoSmoke IDE 实现，已经具备以下能力，可以支撑批量映射闭环。

| 能力 | 当前入口/接口 | 用途 |
|---|---|---|
| UI 元数据导入 | 元数据页签：导入 Project / Current / Runtime / Pages / 手工导入 | 导入 UI 树或增强 UI 树 |
| 从增强 UI 树生成草稿 | `从增强UI树生成草稿` / `/api/mapping/import` | 批量生成映射候选 |
| 草稿审核列表 | 审核页签 / `/api/mapping/drafts` | 查看待审、已匹配、已确认、拒绝等草稿 |
| 草稿详情编辑 | `/api/mapping/get`、保存按钮 | 修改 displayName、testId、semanticId、role、pageId 等 |
| 结构确认 | `结构确认` | 基于路径、名称、页面归属做初级确认 |
| 运行态 UI 刷新 | `/api/runtime_ui/refresh` | 获取当前游戏运行态 UI 树 |
| 运行态匹配 | `/api/mapping/runtime_match` | 将草稿与当前运行态 UI 树匹配 |
| 运行态发现 | `/api/mapping/runtime_discover` | 发现当前页面中未进入映射的运行态元素 |
| 高亮截图 | `/api/mapping/highlight` | 生成红框高亮图，作为视觉证据 |
| 视觉确认 | `视觉确认` / `/api/mapping/drafts/.../visual_confirm` | 人工确认高亮位置正确 |
| 测试点击 | `测试点击` / `/api/mapping/drafts/.../test_click` | 对候选元素执行点击验证 |
| 点击确认 | `点击确认` | 将通过点击验证的草稿升级为可执行映射 |
| 拒绝/忽略 | `拒绝` / `忽略` | 排除错误候选或非自动化元素 |
| 用例导入/执行 | `/api/case/import`、`/api/case/run`、`/api/case/run_batch` | 用真实用例反向验证映射 |
| 代码语义索引 | `ui_code_semantics.json`、`code_semantic_indexer.py`、`current_page_code_resolver.py` | 从代码绑定、类名、方法名、业务命名中识别元素用途 |

当前 IDE 已经支持的审核状态包括：

```text
auto_draft / pending
structure_confirmed
runtime_matched
visual_confirmed
click_confirmed
manual_confirmed
modified
rejected
ignored
```

因此不需要从“逐元素人工确认”开始，而应按状态推进。

---

## 1.1 完整闭环目标态

完整闭环不是只在 IDE 中确认若干元素，而是形成一条持续可用的自动化资产生产线：

```text
A级手工用例
  → 目标名抽取
  → target_name_catalog.draft
  → UI 元数据候选匹配
  → 代码语义候选增强
  → mapping_task 队列
  → runtime_match
  → 高亮截图证据
  → 视觉确认
  → 点击验证
  → 用例回放验证
  → 正式 element_mapping
  → 自动化执行门禁
  → 失败报告反推缺口
  → 新一轮 mapping_task
  → 版本变化重验
```

闭环完成后，IDE 应支持：

1. 从手工用例自动抽目标，而不是从全量 UI 元素开始看。
2. 以“目标名 → 候选元素 → 验证证据”的任务视图审核，而不是逐个路径审核。
3. 对候选批量执行运行态匹配、高亮生成、点击验证。
4. 对正式执行设置 mapping 状态门禁。
5. 用真实用例执行结果反向升级或降级映射。
6. UI 版本变化后批量重验并生成失效清单。

代码语义在闭环中的定位：

```text
它不是最终确认依据，而是候选匹配和解释的强证据。
```

代码语义可以显著提高批量匹配准确率，但正式映射仍需经过运行态、高亮、点击或用例证据确认。

---

## 1.2 完整闭环中的核心资产

| 资产 | 产生方 | 用途 |
|---|---|---|
| `manual_test_cases.v1.xlsx/json` | 上游 | A 级手工用例，提供目标、动作、预期 |
| `target_name_catalog.draft.json` | AutoSmoke 转换层 | 从手工用例抽取目标名和别名 |
| `mapping_task_queue.json` | AutoSmoke IDE | 目标驱动的映射任务队列 |
| `element_mapping_draft.json` | AutoSmoke IDE | UI 元数据生成的候选映射 |
| `ui_code_semantics.json` | AutoSmoke 代码语义索引器 | 元素绑定代码、页面类、方法名、业务命名等语义证据 |
| `runtime_match_result.json` | AutoSmoke IDE | 草稿与运行态 UI 的匹配结果 |
| `mapping_evidence.json` | AutoSmoke IDE | 高亮图、点击结果、用例验证结果证据 |
| `element_mapping_formal.json` | AutoSmoke IDE | 正式可执行映射 |
| `mapping_gap_report.json` | AutoSmoke IDE | 缺 locator、失效映射、冲突候选清单 |
| `case_execution_report.json` | AutoSmoke 执行器 | 用例回放结果，反推映射可信度 |

---

## 2. 核心原则

### 2.1 不追求全量元素一次标完

第一阶段目标不是：

```text
全项目所有 UI 元素 100% 都有 testId
```

而是：

```text
P0/P1 自动化用例依赖的目标 100% 有可信映射
```

优先处理：

```text
入口
按钮
页面/面板
弹窗
关闭按钮
确认按钮
领取按钮
已领取状态
红点
页签
关键文本
关键奖励格子
```

暂不优先处理：

```text
背景图
装饰图
特效节点
布局容器
纯展示图片
重复子节点
不可见节点
低优先级文本
```

### 2.2 不相信“批量生成”，只相信“验证证据”

批量生成只能产生候选，不能直接视为正确。

可信状态应按证据升级：

```text
auto_draft
  → runtime_matched
  → visual_confirmed
  → click_confirmed
  → case_verified
```

在当前 IDE 中，至少应达到：

```text
visual_confirmed 或 click_confirmed
```

再进入正式自动化执行。

### 2.3 人工只处理异常和关键项

人工审核应只关注：

1. P0/P1 用例依赖目标。
2. 多候选冲突。
3. 低置信度候选。
4. 点击后无变化或变化异常。
5. 缺少 screenRect / runtimeMatch 的元素。
6. 路径明显不稳定的元素。

---

## 3. 总体流程

```text
1. 准备输入
2. 导入 UI 元数据
3. 批量生成映射草稿
4. 按页面/优先级/状态过滤
5. 运行态匹配
6. 生成高亮截图
7. 视觉确认
8. 测试点击
9. 点击确认
10. 用例回放验证
11. 输出正式映射
12. 失败反馈补洞
```

---

## 4. 阶段 0：准备输入

### 4.1 必备输入

| 输入 | 说明 |
|---|---|
| `enhanced_ui_tree.json` | 优先使用，包含 enhanced 字段、角色、优先级、语义建议 |
| `project_ui_inventory.json` | 全项目 UI 库，适合离线补充 |
| `runtime_ui_tree_current.json` | 当前运行态 UI 树 |
| 当前 GameContent 截图 | 用于高亮验证 |
| A 级手工用例 | 用于反推关键目标 |

### 4.2 推荐先准备目标名清单

从 A 级手工用例中抽取目标名，形成待映射目标列表：

```text
右上角登录好礼入口图标
登录好礼主界面
第1天奖励领取按钮
第1天奖励已领取状态
入口红点
奖励获得弹窗
关闭按钮
```

这一步的目的：

```text
让审核从“看所有元素”变成“确认这些目标对应哪个元素”。
```

---

## 5. 阶段 1：导入 UI 元数据

### 5.1 IDE 操作

进入 IDE 元数据相关页面，按优先级导入：

```text
1. 导入 Runtime
2. 导入 Current
3. 导入 Pages
4. 导入 Project
```

如果已有 `enhanced_ui_tree.json`，优先使用：

```text
从增强UI树生成草稿
```

### 5.2 验收标准

导入后检查：

```text
import_report.json 存在
节点数 > 0
草稿数 > 0
页面 pageId 能识别
关键页面能在草稿列表中筛选出来
```

### 5.3 风险

| 风险 | 处理 |
|---|---|
| 导入的是离线 Project，元素运行时不存在 | 后续必须运行态匹配 |
| UI 树太大，草稿过多 | 只筛 P0/P1、clickable、指定 pageId |
| pageId 不准 | 后续通过运行态匹配修正 |

---

## 6. 阶段 2：批量生成映射草稿

### 6.1 生成来源优先级

```text
enhanced_ui_tree.json
  > runtime_ui_tree_current.json
  > current_ui.json
  > project_ui_inventory.json
```

### 6.2 草稿字段应重点检查

当前草稿里通常会有：

```text
displayName
chineseDescription
testId / suggestedTestId
semanticId / suggestedSemanticId
role
pageId
elementType
priority
clickable
confidence
path
screenRect
reviewHint
```

### 6.3 第一轮过滤策略

在审核列表中优先筛：

```text
priority = P0/P1
clickable = true
role 包含 entry / action / confirm / close / claim / page / status
elementType = Button / Panel / Text / Image / Toggle
pageId = 当前目标页面
```

第一阶段不要处理低优先级展示元素。

---

## 7. 阶段 3：运行态匹配

### 7.1 目的

运行态匹配用于确认：

```text
草稿里的结构元素，当前运行画面里是否真的存在。
```

### 7.2 IDE 操作

在当前目标页面打开后：

```text
1. 刷新运行态 UI 树
2. 执行运行态匹配
3. 查看审核列表中的“已匹配”状态
```

对应状态：

```text
runtime_matched
```

### 7.3 通过标准

一条草稿进入下一阶段的条件：

```text
runtimeMatch.status = matched
有有效 screenRect
当前 pageId 与草稿 pageId 一致或可解释
不是 debug UI / 工具自身 UI
```

### 7.4 失败处理

| 失败情况 | 处理 |
|---|---|
| 未匹配 | 确认当前页面是否正确 |
| 多候选 | 进入冲突处理或人工选择 |
| screenRect 无效 | 暂不视觉确认 |
| 匹配到 Debug UI | 拒绝或忽略 |

---

## 8. 阶段 4：高亮截图验证

### 8.1 目的

高亮截图是“位置正确”的证据。

### 8.2 IDE 操作

选择 `runtime_matched` 草稿后：

```text
1. 点击刷新截图并生成高亮
2. 查看预览区红框
3. 若红框框住正确元素，点击视觉确认
```

确认后状态：

```text
visual_confirmed
```

### 8.3 通过标准

```text
红框位置正确
红框大小合理
没有框到父容器/背景/邻近元素
目标在当前页面可见
```

### 8.4 不通过处理

| 问题 | 处理 |
|---|---|
| 框到父容器 | 修改 clickTargetNode / visualNode 或拒绝 |
| 框到相邻按钮 | 拒绝该候选，选择其他候选 |
| 框太大 | 降级为结构确认，不进入点击确认 |
| 没有截图 | 先刷新截图 |

---

## 9. 阶段 5：点击验证

### 9.1 目的

点击验证用于确认：

```text
这个元素不仅位置对，而且行为也对。
```

### 9.2 IDE 操作

对可点击元素：

```text
1. 确保当前页面状态安全
2. 选择 visual_confirmed 或 runtime_matched 草稿
3. 点击“测试点击”
4. 观察点击结果
5. 若命中正确对象且结果符合预期，点击“点击确认”
```

确认后状态：

```text
click_confirmed
```

### 9.3 可点击元素验证标准

| 元素 | 验证方式 |
|---|---|
| 入口按钮 | 点击后目标页面/面板出现 |
| 领取按钮 | 点击后弹窗出现或状态变化 |
| 关闭按钮 | 点击后当前面板消失 |
| 确认按钮 | 点击后弹窗关闭或流程推进 |
| 页签 | 点击后对应页签内容出现 |

### 9.4 点击后必须记录的证据

建议在审核备注中保留：

```text
点击前页面
点击目标
点击后结果
是否有画面变化
是否出现预期面板/状态
验证用例 ID
```

当前 IDE 已有点击结果和截图报告能力，可以作为证据来源。

---

## 10. 阶段 6：用例回放验证

### 10.1 目的

最终验证不是单个元素正确，而是：

```text
真实用例能跑通。
```

### 10.2 操作

选择一条最小闭环用例，例如：

```text
DL_RK_003 点击登录好礼入口进入主界面
```

转换为步骤：

```text
点击 testId("activity.login_gift.entry")
等待 1 秒
断言存在 testId("activity.login_gift.main_panel")
截图
```

通过 IDE 用例执行入口运行。

### 10.3 通过标准

```text
步骤全部 PASS
点击命中正确元素
断言命中正确页面/面板
报告有截图
失败时能定位到具体 testId 或步骤
```

### 10.4 映射升级策略

当前 IDE 没有单独 `case_verified` 状态时，可先用：

```text
click_confirmed + 备注记录 verified_case
```

例如备注：

```text
verified_case=DL_RK_003; result=PASS; date=2026-06-17
```

---

## 11. 分批实施策略

### 11.1 第一批：主流程 P0

目标：

```text
能从主城进入登录好礼主界面
```

映射范围：

```text
右上角登录好礼入口图标
登录好礼主界面
关闭按钮
入口红点
```

通过标准：

```text
入口点击用例可稳定通过
```

### 11.2 第二批：领取流程 P0/P1

映射范围：

```text
第1天奖励领取按钮
第1天奖励已领取状态
奖励获得弹窗
奖励弹窗关闭按钮
```

通过标准：

```text
领取流程 UI 状态可通过
```

如果没有服务端状态查询，奖励到账只标记：

```text
PASS_WITH_GAP
```

### 11.3 第三批：状态展示 P1

映射范围：

```text
第2天未解锁状态
第7天奖励格子
已领取标签
可领取标签
入口红点消失
```

### 11.4 第四批：异常场景

仅在具备环境控制能力后处理：

```text
弱网
断线重连
杀进程
时间篡改
活动结束在线
```

否则全部进入：

```text
BLOCKED / MANUAL_ONLY
```

---

## 12. 状态门禁规则

### 12.1 正式执行允许状态

允许进入正式用例执行：

```text
click_confirmed
manual_confirmed
visual_confirmed（仅用于非点击断言元素）
```

不允许直接执行：

```text
auto_draft
pending
structure_confirmed
runtime_matched
modified
rejected
ignored
```

### 12.2 不同元素的最低状态

| 元素类型 | 最低可用状态 |
|---|---|
| 点击目标 | `click_confirmed` |
| 页面/面板断言 | `visual_confirmed` |
| 红点/状态断言 | `visual_confirmed` |
| 文本断言 | `visual_confirmed` 或 OCR/text 断言通过 |
| 关闭按钮 | `click_confirmed` |
| 奖励领取按钮 | `click_confirmed` |

---

## 13. 置信度与人工审核规则

### 13.1 分层

| 分层 | 条件 | 操作 |
|---|---|---|
| 高置信 | enhanced 字段完整、运行态匹配、高亮正确 | 批量视觉确认或快速确认 |
| 中置信 | 运行态匹配但语义不完全明确 | 人工看高亮图 |
| 低置信 | 无文本、无 pageId、多候选、路径重复 | 人工逐个处理 |
| 冲突 | 多个元素对应同一目标 | 必须人工选择 |

### 13.2 人工审核优先级

按以下顺序处理：

```text
1. 当前 P0 用例缺失的元素
2. 当前页面 runtime_matched 元素
3. clickable=true 的 P0/P1 元素
4. page/panel/status/red_dot 断言元素
5. 其他展示元素
```

---

## 14. 命名规范

### 14.1 推荐 testId 格式

```text
{module}.{feature}.{object}.{role}
```

示例：

```text
activity.login_gift.entry
activity.login_gift.main_panel
activity.login_gift.day1.claim_button
activity.login_gift.day1.claimed_state
activity.login_gift.entry_red_dot
common.close_button
reward_popup.confirm_button
```

### 14.2 semanticId 格式

```text
login_gift.entry_button
login_gift.main_panel
login_gift.day1.claim_button
login_gift.day1.claimed_state
login_gift.entry_red_dot
```

### 14.3 避免

```text
Btn1
Button_123
Image_5
TempClick
右上角按钮
活动按钮
```

---

## 15. 每日/每版本维护流程

UI 可能变化，因此每个版本应执行轻量回归验证。

### 15.1 每日流程

```text
1. 刷新 Runtime UI
2. 对 P0 映射运行 runtime_match
3. 对失败项生成缺口清单
4. 跑 P0 冒烟用例
5. 更新失败映射
```

### 15.2 UI 改版后流程

```text
1. 重新导入 enhanced_ui_tree
2. 重新运行 runtime_match
3. 对失配元素重新高亮验证
4. 对点击元素重新 test_click
5. 跑关键用例
```

---

## 16. 需要新增或改造的 IDE 能力

当前 IDE 已经具备草稿、运行态匹配、高亮、测试点击、确认等单点能力。要形成完整闭环，需要在现有能力上补齐以下模块。

### 16.1 目标名抽取器

输入：

```text
manual_test_cases.v1.xlsx/json
```

输出：

```text
target_name_catalog.draft.json
```

职责：

1. 从 `前置条件 / 操作步骤 / 预期结果` 中抽取目标名。
2. 识别动作词：进入、点击、查看、领取、关闭、返回、输入、选择等。
3. 识别目标短语：入口图标、主界面、领取按钮、已领取状态、红点、弹窗等。
4. 合并别名，例如“登录好礼入口 / 七日签到入口 / 活动入口图标”。
5. 为目标生成候选 `semantic_hint`。

输出示例：

```json
{
  "target_id": "TGT_LOGIN_GIFT_ENTRY",
  "target_name": "右上角登录好礼入口图标",
  "aliases": ["登录好礼入口", "七日签到入口", "活动入口图标"],
  "semantic_hint": "login_gift.entry_button",
  "target_type": "button",
  "page_hint": "main_city",
  "required_by_cases": ["DL_RK_001", "DL_RK_003"]
}
```

### 16.2 目标映射任务队列

新增资产：

```text
mapping_task_queue.json
```

它不是“元素列表”，而是“目标名列表”。

结构示例：

```json
{
  "task_id": "MAP_TASK_LOGIN_GIFT_ENTRY",
  "target_name": "右上角登录好礼入口图标",
  "semantic_hint": "login_gift.entry_button",
  "required_by_cases": ["DL_RK_003"],
  "candidate_elements": [
    {
      "path": "MainCity/TopRight/LoginGiftBtn",
      "suggestedTestId": "activity.login_gift.entry",
      "match_score": 0.91,
      "reason": ["alias_match", "page_match", "clickable", "runtime_visible"]
    }
  ],
  "status": "pending_review"
}
```

IDE 页面应优先展示：

```text
目标名 → 候选元素 → 证据 → 操作
```

而不是直接展示：

```text
所有 UI 节点路径列表
```

### 16.3 候选匹配器

输入：

```text
target_name_catalog.draft.json
enhanced_ui_tree.json
runtime_ui_tree_current.json
project_ui_inventory.json
element_mapping_draft.json
ui_code_semantics.json
```

匹配维度：

```text
target_name / aliases
displayName / chineseDescription
nodeName / path
text
spriteName / atlasName
pageId
role
elementType
clickable
screenRect 位置
runtime visible
代码所属页面/类名
代码绑定方法名
OnClick / EventTrigger / Button listener
业务关键词，例如 LoginGift / Claim / Close / RedPoint / Reward
```

代码语义可提供的关键线索：

| 代码语义线索 | 对映射的帮助 |
|---|---|
| 所属 UI 类 / Panel 类 | 判断 pageId 和页面归属 |
| 点击绑定方法 | 判断按钮用途，例如入口、领取、关闭、确认 |
| 方法名业务词 | 生成更稳定的 semanticId/testId |
| 字段名 / 变量名 | 识别按钮、红点、奖励格子、状态文本 |
| 调用链 | 推断点击后的预期页面或状态 |
| Prefab/脚本关联 | 减少同名节点冲突 |

示例：

```text
UI 节点名：BtnGo
代码绑定：OpenLoginGiftPanel()
页面类：MainCityTopBar

可推断：
target_name = 右上角登录好礼入口图标
role = entry
pageId = main_city
semanticId = login_gift.entry_button
testId 候选 = activity.login_gift.entry
```

输出候选排序：

```text
match_score
match_reasons
risk_flags
```

推荐评分模型：

| 证据 | 建议分值 |
|---|---:|
| target_name / alias 命中 | +30 |
| 代码方法名命中业务词 | +25 |
| 代码所属页面匹配 | +15 |
| pageId 匹配 | +15 |
| role 匹配 | +10 |
| clickable 匹配 | +10 |
| runtime_matched | +20 |
| 有有效 screenRect | +10 |
| 高亮视觉确认 | +30 |
| 点击验证通过 | +40 |
| 用例回放通过 | +50 |
| 多候选冲突 | -30 |
| 只命中容器 | -20 |
| 当前不可见 | -50 |

代码语义可以把候选提升为高置信候选，但不能单独把候选升级为正式映射。正式映射仍必须经过：

```text
runtime_match / highlight / visual_confirm / test_click / case_replay
```

风险标记示例：

```text
multi_candidate
no_runtime_match
no_screen_rect
container_like
low_confidence
debug_ui_suspected
duplicate_test_id
code_semantic_ambiguous
generic_onclick_only
code_page_mismatch
```

### 16.4 批量验证控制台

在 IDE 中新增或增强“批量验证”入口，支持对选中的任务批量执行：

```text
1. runtime_match
2. highlight
3. visual_ready
4. test_click
5. case_replay
```

批量动作不要自动把所有结果确认，应分为：

```text
自动生成证据
自动计算建议状态
人工批量确认或拒绝
```

### 16.5 证据中心

新增或固化：

```text
mapping_evidence.json
```

映射可信度来自四类证据：

```text
1. 结构证据：UI 树 / enhanced_ui_tree / path / pageId / role
2. 代码证据：绑定方法 / 所属类 / 业务命名 / 调用链
3. 运行态证据：runtime_match / visible / screenRect
4. 行为证据：highlight / test_click / case_replay
```

只有结构 + 代码，不足以进入正式执行。  
结构 + 代码 + 运行态可以进入高置信候选。  
结构 + 代码 + 运行态 + 行为，才是正式可信映射。

每条映射保存证据：

```json
{
  "semanticId": "login_gift.entry_button",
  "testId": "activity.login_gift.entry",
  "mapping_path": "MainCity/TopRight/LoginGiftBtn",
  "evidence": {
    "structure": {
      "pageId": "main_city",
      "role": "entry",
      "elementType": "Button",
      "path": "MainCity/TopRight/LoginGiftBtn"
    },
    "code_semantics": {
      "matched": true,
      "owner_class": "MainCityTopBar",
      "bound_method": "OpenLoginGiftPanel",
      "business_keywords": ["LoginGift", "OpenPanel"],
      "semantic_score": 0.92
    },
    "runtime_match": {
      "status": "matched",
      "match_score": 0.91,
      "runtime_path": "MainCity/TopRight/LoginGiftBtn"
    },
    "visual": {
      "highlight_image": "screenshots/mapping_review/20260617_123000_highlight.png",
      "confirmed": true,
      "confirmed_at": "2026-06-17T12:30:00"
    },
    "click": {
      "result": "PASS",
      "after_state": "login_gift.main_panel_visible"
    },
    "case_replay": {
      "case_id": "DL_RK_003",
      "result": "PASS"
    }
  },
  "final_status": "case_verified"
}
```

正式映射不能只保存 `testId`，还要保存为什么可信。

### 16.6 正式执行门禁

在用例执行前增加映射门禁：

```text
点击目标必须 click_confirmed / case_verified / manual_confirmed
页面/状态断言目标必须 visual_confirmed / case_verified / manual_confirmed
auto_draft / runtime_matched / structure_confirmed 不允许直接正式执行
```

门禁失败时输出：

```text
mapping_gap_report.json
```

示例：

```json
{
  "case_id": "DL_RK_003",
  "blocked": true,
  "reason": "mapping_not_verified",
  "target": "login_gift.entry_button",
  "current_status": "runtime_matched",
  "required_status": "click_confirmed",
  "suggested_action": "run_test_click"
}
```

### 16.7 用例回放反向升级

用例执行通过后，AutoSmoke 应回写映射证据：

```text
用例 DL_RK_003 PASS
  → activity.login_gift.entry 参与点击且成功
  → activity.login_gift.main_panel 参与断言且成功
  → 两者升级为 case_verified 或记录 verified_case
```

用例失败后，生成缺口：

```text
定位失败 → missing_locator / stale_locator
点击无变化 → click_behavior_mismatch
断言失败 → assertion_target_missing
页面错误 → wrong_target_mapping
```

### 16.8 UI 版本重验

新增“版本重验”流程：

```text
1. 重新导入 enhanced/runtime UI
2. 对 formal mapping 全量 runtime_match
3. 对失配项生成 stale_mapping_report
4. 对 P0/P1 失配项重新生成 mapping_task
5. 跑 P0 用例确认
```

---

## 17. 完整闭环开发阶段

### 17.1 阶段 A：目标驱动输入

目标：

```text
从手工用例自动生成目标映射任务。
```

产出：

```text
target_name_catalog.draft.json
mapping_task_queue.json
```

验收：

```text
登录好礼用例中的入口、主界面、领取按钮、红点、关闭按钮能自动进入任务队列。
```

### 17.2 阶段 B：UI + 代码语义融合候选匹配与任务视图

目标：

```text
每个目标名展示 1-N 个候选元素，并显示 UI 结构分数、代码语义分数、运行态分数和匹配原因。
```

产出：

```text
mapping_task_queue.json 中 candidate_elements 完整
candidate_elements 中包含 code_semantics 证据
IDE 新增“按目标审核”视图
```

验收：

```text
人工审核对象从“所有 UI 节点”变为“用例目标”。
同名按钮能通过代码所属类/绑定方法区分。
候选推荐原因能解释为 alias/page/role/code/runtime 等证据组合。
```

### 17.3 阶段 C：批量运行态验证

目标：

```text
对任务批量执行 runtime_match + highlight。
```

产出：

```text
runtime_match_result.json
highlightImage
mapping_evidence.json
```

验收：

```text
P0 目标可批量生成高亮证据。
```

### 17.4 阶段 D：批量点击验证

目标：

```text
对可点击目标执行安全点击验证。
```

产出：

```text
click_verified / click_failed
click evidence
```

验收：

```text
入口按钮点击后能验证登录好礼主界面出现。
关闭按钮点击后能验证面板消失。
```

### 17.5 阶段 E：正式执行门禁

目标：

```text
正式用例执行前检查 mapping 状态。
```

产出：

```text
mapping_gap_report.json
case blocked reason
```

验收：

```text
未 click_confirmed 的点击目标不能进入正式执行。
```

### 17.6 阶段 F：用例回放闭环

目标：

```text
用真实用例结果升级映射状态或生成补洞任务。
```

产出：

```text
case_verified evidence
mapping_task_queue 新增失败补洞任务
```

验收：

```text
DL_RK_003 通过后，入口按钮和主界面映射带 verified_case 证据。
```

### 17.7 阶段 G：版本重验

目标：

```text
UI 变化后识别失效 mapping。
```

产出：

```text
stale_mapping_report.json
remap task
```

验收：

```text
变更后的 UI 能识别哪些 P0/P1 映射失效。
```

---

## 18. 完整闭环成功验收标准

### 18.1 目标抽取验收

```text
1. A 级手工用例中的目标名抽取准确率 >= 90%
2. 每个 P0/P1 用例至少能生成目标映射任务
3. 目标别名能合并到同一 target
```

### 18.2 映射候选验收

```text
1. P0 目标至少有 1 个候选元素
2. 候选元素包含匹配分数和匹配原因
3. 冲突候选能被识别并进入人工选择
```

### 18.3 验证证据验收

```text
1. 每个正式映射都有 runtime_match 证据
2. 每个页面/状态断言映射有 highlightImage
3. 每个点击目标有 click 证据或 manual_confirmed 证据
4. 每个 case_verified 映射记录 verified_case
```

### 18.4 执行门禁验收

```text
1. auto_draft / runtime_matched 不能作为点击目标正式执行
2. 缺少映射证据时用例进入 BLOCKED
3. BLOCKED 报告能提示下一步动作，例如 run_test_click / generate_highlight / manual_review
```

### 18.5 用例闭环验收

```text
1. P0 用例依赖的点击元素 100% click_confirmed
2. P0 用例依赖的页面/状态元素 100% visual_confirmed
3. 登录好礼入口点击用例可稳定通过
4. 失败报告能指出缺失 testId / 定位失败 / 断言失败
5. 被拒绝和忽略的元素不会进入正式执行
```

### 18.6 覆盖率验收

```text
1. P0/P1 用例依赖元素覆盖率 >= 95%
2. 每个正式映射都有运行态或视觉证据
3. 领取流程 UI 层可自动回放
4. 缺少服务端状态验证的用例明确 PASS_WITH_GAP
```

### 18.7 长期目标

```text
1. P0/P1 自动化用例依赖目标 100% 有 confirmed 映射
2. UI 版本变化后能自动识别失效映射
3. 新用例缺 locator 时能自动生成待审核任务
```

---

## 19. 最终实施建议

基于当前 IDE 已实现能力和允许代码改造后的目标态，完整实施方案是：

```text
A级手工用例
  → 目标名抽取
  → 目标映射任务队列
  → 代码语义索引
  → 候选元素匹配
  → UI + 代码语义融合评分
  → 批量导入 enhanced/runtime UI
  → 批量生成草稿
  → runtime_match
  → 高亮截图
  → 视觉确认
  → 测试点击
  → 点击确认
  → 用例回放
  → case_verified 证据
  → 正式执行门禁
  → 失败补洞任务
  → UI 版本重验
```

不要全量逐元素审核。  
不要把 `auto_draft` 直接当可信映射。  
不要停留在最小闭环。

完整闭环的关键不是“批量生成 testId”，而是：

```text
每个正式 testId 都必须有证据：
runtime_match 证据
highlight 证据
click 证据
case replay 证据
```

最终目标：

```text
AutoSmoke 不只是生成映射，而是维护一套可验证、可回放、可失效检测、可持续更新的 UI 自动化映射资产。
```

---

## 20. 简洁易用的 IDE 界面设计

完整闭环的界面不能做成复杂后台，也不能让用户一上来面对几千个 UI 节点。推荐把 UI 树与元素映射模块升级为：

```text
目标驱动的三步工作台
```

核心问题只有三个：

```text
要测什么 → 匹配到了谁 → 能不能放心用
```

### 20.1 主界面结构

主界面只保留四个区域：

```text
1. 目标列表
2. 候选匹配
3. 验证证据
4. 批量操作
```

默认不展示全量 UI 树。

推荐布局：

```text
┌─────────────────────────────────────────────┐
│ 自动化目标映射                              │
│ [生成目标] [批量匹配] [批量高亮] [批量验证] [导出正式映射] │
├───────────────┬─────────────────────────────┤
│ 目标列表       │ 目标详情                    │
│               │                             │
│ 登录好礼入口   │ 目标名：登录好礼入口图标      │
│ 登录好礼主界面 │ 来源用例：DL_RK_003          │
│ 第1天领取按钮  │ 状态：已匹配                 │
│ 关闭按钮       │                             │
│               │ 候选元素：                   │
│               │ 1. LoginGiftBtn  0.93        │
│               │ 2. ActivityBtn   0.71        │
│               │                             │
│               │ [高亮截图]                   │
│               │                             │
│               │ [确认这个] [换候选] [手动补充] [测试点击] │
└───────────────┴─────────────────────────────┘
```

### 20.2 首页目标列表

首页不显示 UI 节点，显示自动化需要的目标。

表格列：

```text
目标名
来源用例
推荐候选
置信度
状态
下一步
```

示例：

| 目标名 | 来源用例 | 推荐候选 | 置信度 | 状态 | 下一步 |
|---|---|---|---:|---|---|
| 登录好礼入口图标 | DL_RK_003 | LoginGiftBtn | 0.93 | 已匹配 | 看高亮 |
| 登录好礼主界面 | DL_RK_003 | LoginGiftPanel | 0.88 | 已确认 | 可执行 |
| 第1天领取按钮 | DL_REWARD_001 | BtnClaimDay1 | 0.81 | 待点击验证 | 测试点击 |

状态用人能理解的名称：

```text
待匹配
已匹配
已高亮
已确认
点击通过
可执行
```

失败状态：

```text
无候选
多候选
点击失败
运行态失效
```

内部状态可以继续保留，但界面展示应翻译成人话。

### 20.3 目标详情页

点开一个目标后，只看该目标的候选，不看全树。

详情信息：

```text
目标名
来源用例
用途
预期行为
当前状态
```

候选列表：

| 推荐 | 候选元素 | 分数 | 原因 |
|---|---|---:|---|
| 1 | MainCity/TopRight/LoginGiftBtn | 0.93 | 名称匹配 + 代码匹配 + 可点击 |
| 2 | MainCity/ActivityBtn | 0.71 | 位置匹配 + 可点击 |
| 3 | LoginGiftIcon | 0.62 | 图标匹配 |

右侧展示：

```text
高亮截图
代码语义
运行态匹配
点击结果
用例验证
```

用户主要操作：

```text
确认这个
换候选
手动补充
拒绝
测试点击
跑关联用例
```

### 20.4 下一步按钮

每个目标可以显示一个主按钮：`下一步`。按钮动作根据状态自动变化：

```text
待匹配       → 运行匹配
已匹配       → 生成高亮
已高亮       → 视觉确认
已视觉确认   → 测试点击
点击通过     → 加入正式映射
正式映射     → 可执行
```

这样用户不需要理解底层接口。

### 20.5 批量操作

顶部只放五个批量按钮：

```text
生成目标
批量匹配
批量高亮
批量验证
导出正式映射
```

| 按钮 | 作用 |
|---|---|
| 生成目标 | 从手工用例抽取目标名 |
| 批量匹配 | 给目标找 UI 候选 |
| 批量高亮 | 给已匹配目标生成红框截图 |
| 批量验证 | 对可点击目标测试点击 |
| 导出正式映射 | 输出 confirmed mapping |

复杂功能放到：

```text
高级详情
调试模式
查看原始数据
```

---

## 21. 手动补充设计

自动匹配不可能覆盖所有元素，因此必须支持手动补充。但手动补充不应要求用户填写完整 JSON，而应是：

```text
业务目标表单
  → 自动生成 semanticId/testId
  → 自动检查唯一性
  → 自动进入验证流程
```

### 21.1 手动补充入口

目标详情中提供：

```text
确认这个
换候选
手动补充
```

缺口页中每条缺口提供：

```text
重新匹配
运行态发现
手动补充
忽略
```

适用场景：

```text
无候选
候选都不对
动态元素没出现在 UI 树
代码语义不明确
需要临时文本/模板/坐标兜底
```

### 21.2 简单模式表单

默认只要求少量字段：

```text
目标名 *
所属页面 *
元素类型 *
定位方式 *
定位值 *
```

表单示例：

```text
手动补充目标
--------------------------------
目标名 *：
[ 第1天奖励领取按钮 ]

所属页面 *：
[ 登录好礼主界面 ▼ ]

元素类型 *：
[ 按钮 ▼ ]

定位方式 *：
[ testId ▼ ]

定位值 *：
[ activity.login_gift.day1.claim.button ]

--------------------------------
自动生成：
semanticId: login_gift.day1.claim_button
testId:     activity.login_gift.day1.claim.button
role:       claim
pageId:     login_gift

[重新生成] [检查唯一性]

--------------------------------
验证方式：
[x] 生成高亮
[x] 测试点击
[ ] 跑关联用例

关联用例：
[ DL_REWARD_001 ▼ ]

[保存并验证] [仅保存草稿] [取消]
```

### 21.3 高级模式字段

高级模式默认折叠，需要时展开：

```text
semanticId
testId
role
pageId
priority
source_ref
备注
验证策略
```

### 21.4 定位方式

手动补充支持：

```text
testId
semanticId
poco
text
template
normalized
content
pixel
```

推荐顺序：

```text
testId > semanticId > poco > text > template > normalized > content > pixel
```

如果使用 `text/template/normalized/content/pixel`，界面必须显示风险：

```text
临时映射，建议后续替换为 testId。
```

### 21.5 自动生成规则

目标名到 role：

| 目标名包含 | role |
|---|---|
| 入口 | `entry` |
| 领取 | `claim` |
| 已领取 | `claimed_state` |
| 未解锁 | `locked_state` |
| 红点 | `red_dot` |
| 关闭 | `close` |
| 确认 | `confirm` |
| 返回 | `back` |
| 弹窗 | `popup` |
| 主界面/页面 | `panel/page` |
| 奖励 | `reward_item` |

元素类型到 testId 后缀：

| 元素类型 | testId 结尾 |
|---|---|
| 按钮 | `.button` |
| 面板 | `.panel` |
| 页面 | `.page` |
| 弹窗 | `.popup` |
| 红点 | `.red_dot` |
| 文本 | `.text` |
| 状态 | `.state` |
| 奖励格子 | `.item` |
| 页签 | `.tab` |

页面到前缀：

| 页面 | 前缀 |
|---|---|
| 主城 | `main_city` |
| 登录好礼 | `activity.login_gift` |
| 奖励弹窗 | `reward_popup` |
| 通用 | `common` |

### 21.6 保存后的状态

手动补充后不要直接可执行，应进入同一套验证流程：

```text
manual_added
  → 待验证
  → 高亮确认
  → 点击确认
  → 可执行
```

保存按钮：

| 按钮 | 行为 |
|---|---|
| 保存草稿 | 状态为 `manual_added` |
| 保存并高亮 | 保存后自动执行 highlight |
| 保存并验证 | 保存后执行 highlight + test_click |

### 21.7 手动补充证据

手动补充也必须记录证据：

```json
{
  "source": "manual_added",
  "operator": "user",
  "created_at": "2026-06-17T12:00:00",
  "reason": "auto_match_no_candidate",
  "locator": {
    "type": "testId",
    "value": "activity.login_gift.day1.claim.button"
  },
  "verify_status": "pending"
}
```

验证后追加：

```json
{
  "highlight_confirmed": true,
  "click_confirmed": true,
  "verified_case": "DL_REWARD_001"
}
```

---

## 22. testId 命名与唯一性规则

### 22.1 推荐命名格式

统一采用：

```text
{domain}.{feature}.{object}.{role}
```

活动类推荐：

```text
activity.{feature}.{object}.{role}
```

登录好礼示例：

```text
activity.login_gift.entry.button
activity.login_gift.entry.red_dot
activity.login_gift.main.panel
activity.login_gift.close.button
activity.login_gift.day1.reward.item
activity.login_gift.day1.claim.button
activity.login_gift.day1.claimed.state
activity.login_gift.day2.locked.state
activity.login_gift.reward_popup.panel
activity.login_gift.reward_popup.confirm.button
```

一句话规则：

```text
testId 不描述“它在 UI 树哪里”，而描述“它在业务里是什么”。
```

### 22.2 基本规则

1. 全小写英文。
2. 用点号分层。
3. 不使用中文。
4. 不使用 Unity 路径。
5. 不带临时编号。
6. 语义稳定优先于 UI 层级稳定。

不推荐：

```text
BtnClose
Button1
Image_02
Root.Panel.Btn
loginGiftBtn
登录好礼入口
activity.login_gift.xxx
maincity.top.right.button
```

### 22.3 role 推荐枚举

```text
button
panel
page
dialog
icon
text
label
input
toggle
tab
item
slot
red_dot
state
progress
list
cell
popup
toast
```

动作型按钮把动作放在 object 中，元素类型放最后：

```text
activity.login_gift.day1.claim.button
activity.login_gift.reward_popup.confirm.button
activity.login_gift.close.button
```

不推荐：

```text
activity.login_gift.day1.button.claim
```

### 22.4 唯一性要求

`testId` 必须具备唯一性。

推荐规则：

```text
testId 必须全局唯一。
如确实需要复用，必须通过 pageId + testId 保证唯一。
同一运行态页面内绝不允许多个可见元素共享同一个 testId。
```

最推荐：

```text
全项目全局唯一
```

可接受：

```text
pageId + testId 唯一
```

不推荐：

```text
同一运行态多个元素共享同一个 testId
```

### 22.5 重复元素命名

七日签到奖励：

```text
activity.login_gift.day1.claim.button
activity.login_gift.day2.claim.button
activity.login_gift.day3.claim.button
activity.login_gift.day7.claim.button
activity.login_gift.day1.claimed.state
activity.login_gift.day2.locked.state
activity.login_gift.day7.reward.item
```

商品列表：

```text
shop.daily.goods_1001.cell
shop.daily.goods_1001.buy.button
```

如果只有排序位置，可临时使用：

```text
shop.daily.item_01.cell
shop.daily.item_01.buy.button
```

但排序位置不如业务 ID 稳定。

### 22.6 通用按钮命名

关闭按钮可有两种策略。

全局通用：

```text
common.close.button
```

页面内唯一，更推荐：

```text
activity.login_gift.close.button
reward_popup.close.button
shop.close.button
```

如果多个弹窗可能叠加，必须使用页面内唯一策略。

### 22.7 唯一性校验

进入正式映射前必须检查：

```text
同一个 testId 是否对应多个 path
同一个 testId 是否在同一 pageId 下对应多个元素
同一运行态是否出现多个可见命中
同一个 semanticId 是否映射到多个 testId
同一个 target_name 是否有多个 confirmed 候选
```

发现冲突时进入：

```text
duplicate_test_id
multi_candidate
manual_review_required
```

手动补充保存前必须自动执行唯一性检查。
