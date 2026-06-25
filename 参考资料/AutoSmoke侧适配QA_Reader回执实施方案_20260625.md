# AutoSmoke 侧适配 QA_Reader 回执实施方案

> 日期：2026-06-25  
> 依据：`QA_Reader对AutoSmoke回执_20260625.md`  
> 前提：转换层放在 AutoSmoke  
> 目标：明确 QA_Reader 只提供可转换业务输入时，AutoSmoke 侧需要建设什么能力，才能完成从上游包到自动化执行的闭环。

---

## 1. 总体结论

QA_Reader 回执已经确认：

```text
QA_Reader 不提供脚本、locator、最终 testId、最终 semanticId、element_mapping。
QA_Reader 可以提供审核后的功能流、用例意图、目标名、页面路径、测试数据、状态采集需求、断言意图、外部依赖、来源追踪和阻断项。
```

因此，AutoSmoke 侧需要承担完整转换链路：

```text
上游业务输入包
  → 包校验
  → 审核状态准入
  → 用例转换
  → 步骤转换
  → 目标名解析
  → semanticId/testId 候选生成
  → IDE 自动/人工确认
  → element_mapping 保存
  → 执行计划生成
  → UI 自动化执行
  → 业务状态采集
  → 业务断言执行
  → 报告与来源回溯
```

AutoSmoke 侧不能再把“缺少 testId/semanticId/locator”作为上游问题。上游只要提供合格目标名和页面上下文，后续绑定就是 AutoSmoke 的职责。

---

## 2. AutoSmoke 侧需要建设的能力总览

| 模块 | AutoSmoke 需要做什么 | 目的 |
|---|---|---|
| 交付契约层 | 定义 handoff schema、样例、校验规则 | 让 QA_Reader 有明确生成目标 |
| 包接入层 | 支持读取 QA_Reader 生成的 handoff 包 | 统一入口，避免手工导入散文件 |
| 准入判断层 | 识别 `REVIEW_REQUIRED/BLOCKED/APPROVED` | 防止未审核规则进入执行 |
| 转换层 | 把用例意图转为 AutoSmoke 内部 case/step/assertion | 完成从业务输入到执行输入 |
| 目标解析层 | targetName → semanticId/testId 候选 | 解决元素绑定前的语义映射 |
| 映射确认层 | IDE 自动确认/人工确认元素绑定 | 形成正式 element_mapping |
| 执行计划层 | 生成可执行任务、前置准备、恢复策略 | 保证用例可稳定执行 |
| 状态采集层 | 对接业务状态采集契约 | 支撑功能逻辑自动化 |
| 断言层 | 执行 UI 断言和业务断言 | 验证结果，而不仅是点击成功 |
| 报告层 | 输出阻断、降级、执行结果、来源追踪 | 支撑复盘和责任定位 |

---

## 3. 第一件事：AutoSmoke 要定义正式 handoff schema

QA_Reader 回执中明确说：

```text
不建议直接手工补齐 JSON 文件。
应先定义 AutoSmoke handoff 包的 schema。
```

所以 AutoSmoke 侧首先要输出一套正式契约，而不是只给 Markdown 示例。

### 3.1 需要提供给 QA_Reader 的契约文件

AutoSmoke 应提供：

```text
schemas/
├── autosmoke_upstream_handoff.v1.schema.json
├── feature_flow_review_result.v1.schema.json
├── manual_test_cases.v1.schema.json
├── target_name_catalog.v1.schema.json
├── page_flow_catalog.v1.schema.json
├── test_data_profile.v1.schema.json
├── value_assets.v1.schema.json
├── source_trace.v1.schema.json
├── review_items.v1.schema.json
├── business_state_contract.v1.schema.json
├── business_assertions.v1.schema.json
└── optional_external_refs.v1.schema.json
```

并提供：

```text
examples/
└── armrace_handoff_example/
```

### 3.2 schema 必须表达的规则

至少需要校验：

```text
必需文件是否存在
feature_id 是否一致
case_id 是否唯一
target_id 是否唯一
用例步骤 target_name 是否能在 target_name_catalog 找到
assertion_refs 是否能找到对应 assertion
business_assertions 引用的 state_path 是否存在于 business_state_contract
review_items 中 blocker 是否关闭或允许降级
source_trace 是否覆盖 case/target/assertion
```

---

## 4. 第二件事：AutoSmoke 要支持分级接入

QA_Reader 明确不希望所有文件都是无条件硬需求。

AutoSmoke 侧应支持两档准入。

### 4.1 UI 自动化最小包

必需：

```text
manifest.json
feature_flow_review_result.v1.json
manual_test_cases.v1.json
target_name_catalog.v1.json
page_flow_catalog.v1.json
test_data_profile.v1.json
source_trace.v1.json
review_items.v1.json
```

AutoSmoke 支持能力：

```text
UI 页面进入
点击
弹窗打开/关闭
返回
UI 可见性断言
基础报告
```

不能强行做：

```text
积分到账验证
奖励到账验证
邮件发放验证
排行真实变化验证
配置规则真实生效验证
```

### 4.2 UI + 业务逻辑完整包

在最小包基础上增加：

```text
value_assets.v1.json
business_state_contract.v1.json
business_assertions.v1.json
optional_external_refs.v1.json
```

AutoSmoke 支持能力：

```text
业务状态采集
before/after 快照
状态 diff
配置值验证
奖励到账验证
邮件验证
排行验证
UI 与业务状态一致性验证
```

### 4.3 AutoSmoke 准入结果

AutoSmoke 应输出明确准入状态：

```text
READY_UI_ONLY
READY_UI_AND_BUSINESS
PASS_WITH_GAP
BLOCKED
MANUAL_ONLY
```

---

## 5. 第三件事：AutoSmoke 要实现 handoff 包校验器

QA_Reader 会生成包，但 AutoSmoke 必须自己校验。

### 5.1 校验器输入

```text
autosmoke_upstream_handoff.xxx.v1/
└── manifest.json
```

### 5.2 校验器输出

建议输出：

```json
{
  "schema_version": "autosmoke_handoff_validation_report.v1",
  "package_id": "armrace_20260625_v1",
  "status": "PASS_WITH_GAP",
  "automation_level": "UI_ONLY",
  "errors": [],
  "warnings": [
    {
      "code": "BUSINESS_ASSERTION_NOT_PROVIDED",
      "message": "未提供 business_assertions.v1.json，仅支持 UI 自动化。"
    }
  ],
  "blockers": [],
  "summary": {
    "case_count": 5,
    "target_count": 12,
    "page_count": 2,
    "business_assertion_count": 0
  }
}
```

### 5.3 阻断规则

必须阻断：

```text
feature_flow_review_result 缺失
主流程仍为 REVIEW_REQUIRED
用例缺失
用例步骤缺少 target_name
target_name_catalog 缺失
目标名无法解析到目录
page_flow_catalog 缺失导致无法进入页面
test_data_profile 缺失导致前置条件不可准备
review_items 中存在 blocker 且未关闭
```

允许降级：

```text
缺少 business_state_contract → 降级 UI_ONLY
缺少 business_assertions → 降级 UI_ONLY
缺少 optional_external_refs → 对相关业务断言 BLOCKED，其余 UI 用例可跑
缺少 value_assets → 数值断言降级，UI 流程可跑
```

---

## 6. 第四件事：AutoSmoke 要实现转换器

QA_Reader 不直接生成 AutoSmoke 内部用例，因此 AutoSmoke 需要转换器。

### 6.1 转换输入

```text
manual_test_cases.v1.json
target_name_catalog.v1.json
page_flow_catalog.v1.json
test_data_profile.v1.json
business_assertions.v1.json
source_trace.v1.json
review_items.v1.json
```

### 6.2 转换输出

AutoSmoke 内部建议生成：

```text
generated_cases/
├── autosmoke_cases.json
├── autosmoke_steps.json
├── autosmoke_assertions.json
├── target_binding_tasks.json
├── state_prepare_tasks.json
└── conversion_report.json
```

### 6.3 转换规则

```text
manual_test_cases.test_cases[] → AutoSmoke case
steps[].action → AutoSmoke action
steps[].target_name → target resolver 输入
steps[].expected → UI assertion 候选
preconditions → state_prepare_tasks
assertion_refs → business_assertions 绑定
source_node_ids → source_trace/report
automation_level → 执行策略
```

### 6.4 自然语言步骤处理

AutoSmoke 应支持两种输入：

```text
结构化步骤：推荐，直接转换
自然语言步骤：可选，进入步骤解析器
```

但 AutoSmoke 的转换输出必须统一成结构化步骤：

```json
{
  "step_order": 1,
  "action": "click",
  "page_name": "常规活动主界面",
  "target_name": "军备竞赛页签",
  "expected": "进入军备竞赛主界面"
}
```

---

## 7. 第五件事：AutoSmoke 要建设 targetName 解析与绑定队列

上游只提供目标名，不提供最终 `testId/semanticId`。

AutoSmoke 需要完成：

```text
target_name
  → 目标标准化
  → 页面上下文匹配
  → role/action 匹配
  → semanticId 候选生成
  → testId 候选生成
  → UI 树/代码元素/运行态元素候选匹配
  → 自动确认或进入人工确认
```

### 7.1 自动确认条件

建议满足全部条件才自动确认：

```text
页面匹配一致
目标名或别名高置信匹配
role 一致
action_roles 支持当前动作
UI 树候选唯一
代码语义候选唯一或高置信
运行态点击/高亮验证通过
没有同名歧义元素
```

### 7.2 人工确认队列

无法自动确认时，AutoSmoke IDE 应生成任务：

```json
{
  "task_id": "BIND_ARMRACE_TAB",
  "case_id": "ARMRACE_UI_001",
  "target_id": "TGT_ARMRACE_TAB",
  "target_name": "军备竞赛页签",
  "page_name": "常规活动主界面",
  "role": "tab",
  "action": "click",
  "candidate_elements": [],
  "status": "NEEDS_HUMAN_CONFIRM"
}
```

### 7.3 保存结果

确认后由 AutoSmoke 保存到：

```text
metadata/mapping_store/
```

并通过 MappingStore 输出兼容视图：

```text
element_mapping_formal.json
mapping_evidence.json
```

---

## 8. 第六件事：AutoSmoke IDE 要有对应页面能力

IDE 需要承接上游 handoff 包导入和转换结果。

### 8.1 建议新增或强化的页面

```text
上游包导入
准入校验
用例转换预览
目标绑定队列
页面流转预览
测试数据准备
业务断言预览
阻断项处理
执行计划生成
```

### 8.2 页面操作流

```text
导入 handoff 包
  → 查看校验结果
  → 查看可执行范围 UI_ONLY / UI_AND_BUSINESS
  → 查看生成用例
  → 查看目标绑定任务
  → 自动绑定/人工确认
  → 查看测试数据准备状态
  → 查看断言覆盖
  → 生成执行计划
  → 执行
  → 查看报告
```

### 8.3 阻断项展示

IDE 需要清楚告诉用户：

```text
哪些是上游必须补
哪些是 AutoSmoke 需要绑定
哪些是环境能力缺失
哪些可以降级执行
哪些必须人工测试
```

---

## 9. 第七件事：AutoSmoke 要接入业务状态采集和断言

如果目标是 UI + 业务逻辑自动化，AutoSmoke 侧必须具备状态采集和断言执行。

### 9.1 状态采集

根据 `business_state_contract.v1.json`：

```text
读取 state_domains
校验 state_path
调用对应 collector
采集 before snapshot
执行 UI 操作
采集 after snapshot
生成 diff
```

### 9.2 断言执行

根据 `business_assertions.v1.json`：

```text
执行 pre_checks
执行 steps
执行 checks
引用 value_assets
引用 optional_external_refs
输出断言结果
```

### 9.3 缺失处理

```text
state_path 未声明 → BLOCKED
collector 不存在 → BLOCKED
外部接口不可用 → BLOCKED 或 PASS_WITH_GAP
value_assets 缺失 → 数值断言 BLOCKED
```

---

## 10. 第八件事：AutoSmoke 报告要支持来源追踪

报告不能只说“失败”，需要回溯到：

```text
用例 ID
步骤
目标名
semanticId/testId
业务节点
来源行号
审核结论
阻断项
状态快照
断言结果
```

### 10.1 报告字段建议

```json
{
  "case_id": "ARMRACE_UI_001",
  "status": "FAILED",
  "failed_step": 2,
  "target_name": "军备竞赛页签",
  "semantic_id": "activity.armrace.tab",
  "test_id": "activity_armrace_tab",
  "source_refs": ["L89-L92"],
  "node_ids": ["NODE-19-8-1-UI"],
  "failure_type": "ELEMENT_BINDING_FAILED",
  "suggested_action": "请在 IDE 目标绑定队列中确认军备竞赛页签元素。"
}
```

---

## 11. AutoSmoke 侧实施优先级

### P0：必须先做

```text
1. 定义 handoff schema
2. 实现 handoff 包导入
3. 实现 handoff 校验器
4. 支持 UI_ONLY / UI_AND_BUSINESS 分级准入
5. 实现 manual_test_cases → AutoSmoke case 转换
6. 实现 target_name_catalog → 绑定任务转换
7. IDE 展示目标绑定队列
8. review_items 阻断/降级规则
```

### P1：形成可执行闭环

```text
1. targetName → semanticId/testId 候选生成
2. UI 树/代码语义/运行态元素联合匹配
3. IDE 人工确认并保存 MappingStore
4. page_flow_catalog 转执行入口/返回/恢复策略
5. test_data_profile 转前置状态检查
6. 执行计划生成
7. 基础 UI 执行报告
```

### P2：支持业务逻辑自动化

```text
1. business_state_contract 状态采集
2. business_assertions 断言执行
3. value_assets 配置/奖励/阈值引用
4. optional_external_refs 外部依赖管理
5. before/after 快照和 diff 报告
6. UI 与业务状态一致性校验
```

### P3：工具链增强

```text
1. 自动从 candidate_feature_flow 生成候选用例
2. 自动从 UI 节点生成 target_name_catalog 候选
3. 自动从规则节点生成 business_assertions 候选
4. 自动生成上游反馈清单
5. 自动回写 QA_Reader 可读校验报告
```

---

## 12. AutoSmoke 与 QA_Reader 的接口关系

### 12.1 QA_Reader 输出

```text
approved feature flow
handoff package
handoff validation report
```

### 12.2 AutoSmoke 输入

```text
manifest.json
handoff package files
```

### 12.3 AutoSmoke 输出给 QA_Reader 或上游

```text
handoff 消费校验报告
缺失字段清单
阻断项清单
目标绑定缺口
状态采集缺口
断言不可执行原因
执行报告
```

---

## 13. 最终结论

按照 QA_Reader 的回执，AutoSmoke 侧需要从“执行器”升级为“业务输入转换与自动化集成平台”。

最关键的不是让上游手工补 JSON，而是 AutoSmoke 先提供明确的契约和消费能力：

```text
1. schema
2. validator
3. importer
4. converter
5. target binder
6. MappingStore
7. execution planner
8. state collector
9. assertion engine
10. traceable report
```

只有这些能力具备后，QA_Reader 生成的 handoff 包才有明确落点，AutoSmoke 也才能稳定完成：

```text
功能流审核包
  → 可转换 handoff 包
  → AutoSmoke 用例
  → 元素绑定
  → 自动执行
  → UI + 业务逻辑验证
  → 可追溯报告
```
