# AutoSmoke 资产包方案 vs DocReader 对接文档差异对比

> 日期：2026-06-17  
> 对比对象 1：`DocReader_自动化脚本生成工具_首次对接交互文档_v0.1.md`  
> 对比对象 2：AutoSmoke 推荐的 `auto_smoke_asset_package.v1` / `auto_smoke_case_seed.v1` 输入方案  
> 目标：明确 DocReader 当前 v0 文档已覆盖什么、与 AutoSmoke 自动执行框架还有哪些差距、后续应如何升级。

---

## 1. 总体结论

DocReader 当前文档的定位是正确的：它明确说明 `case_seed_package.v0` 只是“用例基础素材 / 测试点候选 / 人工评审辅助”，不承诺直接作为自动化脚本可执行输入。

AutoSmoke 当前需要的不是单一 `case_seed_package.v0`，而是一个更完整的自动化执行资产包：

```text
auto_smoke_asset_package.v1
```

其中核心执行文件是：

```text
case_seed.auto_smoke.v1.json
```

两者关系应该是：

```text
DocReader case_seed_package.v0
  → 转换/补齐/评审
  → auto_smoke_asset_package.v1
  → AutoSmoke 自动执行
```

也就是说，DocReader 文档当前覆盖的是“上游事实资产层”，而 AutoSmoke 需要的是“自动化执行资产层”。

---

## 2. 定位对比

| 维度 | DocReader 当前文档 | AutoSmoke 资产包方案 | 结论 |
|---|---|---|---|
| 核心定位 | QA 资产输入、case seed、评审辅助 | 自动化执行输入、定位、断言、前置状态、报告闭环 | DocReader 是上游事实层，AutoSmoke 是执行层 |
| 是否可直接执行 | 明确不承诺 | 目标就是可执行 | 需要中间转换层 |
| 主要对象 | `business_items`、`relation_items`、`value_assets`、`review_items` | `test_cases`、`steps`、`targets`、`assertions`、`preconditions` | 数据抽象层级不同 |
| 风险控制 | PASS_WITH_GAP / BLOCKED | PASS / PASS_WITH_GAP / BLOCKED / MANUAL_ONLY + blocking rules | AutoSmoke 需要更细的阻断规则 |
| 责任边界 | DocReader 不补文档外信息 | 外部依赖显式列出并阻断或补齐 | 两者一致，但 AutoSmoke 需要落到文件级资产 |

---

## 3. 字段覆盖对比

| AutoSmoke 需要 | DocReader v0 是否覆盖 | 当前差距 | 建议处理 |
|---|---:|---|---|
| `feature_name` | 覆盖 | 可直接复用 | DocReader 提供 |
| `case_id` | 未明确 | DocReader 当前是业务项 ID，不是执行用例 ID | 转换器生成 |
| `title` | 部分覆盖 | 可由 `statement/block_name` 生成 | 转换器生成 |
| `module/submodule` | 部分覆盖 | DocReader 有 block_name，但不一定有测试模块层级 | DocReader 增强或转换器归类 |
| `source_refs` | 覆盖 | 粒度需稳定到 sheet/row/evidence_ref | DocReader 提供 |
| `admission` | 覆盖基础版 | 需要扩展到执行级准入 | DocReader + AutoSmoke 转换器共同判断 |
| `steps` | 不覆盖 | 最大缺口 | 转换器/人工评审生成 |
| `step_order` | 不覆盖 | 当前业务关系不是线性步骤 | 转换器/behavior_flow 生成 |
| `action_type` | 不覆盖 | 最大缺口 | 转换规则或人工补齐 |
| `target` | 部分覆盖 | 只有自然语言目标名，不是可定位目标 | DocReader 提供 target_name，AutoSmoke 映射成 testId |
| `testId/semanticId` | 不覆盖 | DocReader 文档明确不提供 locator | AutoSmoke 元素映射系统提供 |
| `precondition_id` | 不覆盖 | 只有自然语言前置或业务条件 | 外部环境/账号系统提供 |
| `assertions` | 部分覆盖 | preserved_assets 可辅助，但不是断言模型 | 转换器生成 assertion_catalog |
| `test_data` | 部分覆盖 | 缺账号、状态、活动、奖励等可执行数据 | test_data_registry 提供 |
| `config_reference` | 部分覆盖 | DocReader 只有配置来源，不保证实际值 | 配置系统提供 |
| `text_key_map` | 部分覆盖 | 可能识别 KEY，但无最终文案 | 文案表提供 |
| `cleanup_steps` | 不覆盖 | DocReader 文档也明确不提供 | AutoSmoke/测试环境工具提供 |
| `review_blockers` | 覆盖思路 | 需要文件化结构 | 转换器输出 |

---

## 4. 文件结构对比

### 4.1 DocReader 当前建议

DocReader 当前建议首次交付：

```text
case_seed_package.v0.json
```

结构核心：

```json
{
  "schema_version": "case_seed_package.v0",
  "feature_name": "",
  "admission": {},
  "business_items": [],
  "relation_items": [],
  "value_assets": [],
  "review_items": [],
  "source_refs": []
}
```

这适合表达：

1. 文档事实。
2. 业务陈述。
3. 来源追踪。
4. 值资产。
5. 待确认项。
6. 初步准入状态。

### 4.2 AutoSmoke 推荐

AutoSmoke 推荐上游或转换层最终交付：

```text
auto_smoke_asset_package.v1/
├── manifest.json
├── case_seed.auto_smoke.v1.json
├── element_semantic_map.v1.json
├── precondition_registry.v1.json
├── test_data_registry.v1.json
├── assertion_catalog.v1.json
├── external_dependency_manifest.v1.json
├── text_key_map.v1.json
├── config_reference.v1.json
├── source_trace.v1.json
└── review_blockers.v1.json
```

这适合表达：

1. 可执行用例。
2. 可执行步骤。
3. 目标定位。
4. 元素语义映射。
5. 前置状态。
6. 测试数据。
7. 断言规则。
8. 外部依赖。
9. 配置和文案解析。
10. 来源追踪。
11. 阻断缺口。

---

## 5. DocReader 文档已覆盖的部分

DocReader 文档已经覆盖并且可以直接沿用的内容：

1. **定位边界正确**
   - 明确不直接承诺可执行脚本。
   - 明确缺少 locator、环境状态、动作链、断言方式。

2. **准入状态思路正确**
   - `PASS_WITH_GAP / BLOCKED` 可以继续沿用。
   - AutoSmoke 建议补充 `PASS / MANUAL_ONLY`。

3. **来源追踪是 AutoSmoke 报告需要的**
   - `source_refs`、`evidence_ref`、`sheet_name`、`row_number` 都应保留。

4. **preserved_assets 对断言有价值**
   - UI 展示格式、公式、文案格式可进入 `assertion_catalog`。

5. **review_items 可演进为 review_blockers**
   - 不确定项、缺失项、冲突项可直接转为 AutoSmoke 的阻断或评审清单。

6. **下游确认问题覆盖面较全**
   - action_type、target_type、assertion_type、locator、配置表、文案 KEY、阻断规则都已经在文档里提出。

---

## 6. DocReader 文档相对 AutoSmoke 的主要缺口

### 6.1 缺少资产包视角

DocReader 当前只定义一个 `case_seed_package.v0.json`。  
AutoSmoke 实际需要多个文件协同：

```text
用例文件 + 元素映射 + 前置状态 + 测试数据 + 断言目录 + 外部依赖 + 来源追踪
```

建议 DocReader 文档增加：

```text
auto_smoke_asset_package.v1
```

作为下游 AutoSmoke 的目标交付包，而不是只讨论单个 JSON。

### 6.2 缺少执行用例模型

DocReader 的 `business_items` 是业务事实，不是执行用例。

AutoSmoke 需要：

```json
{
  "case_id": "",
  "steps": [],
  "assertions": [],
  "precondition_id": ""
}
```

建议新增：

```text
case_seed.auto_smoke.v1.json
```

### 6.3 缺少 semanticId/testId 映射文件

DocReader 文档说不提供 UI locator，这是合理的。  
但如果要对接 AutoSmoke，需要明确这个文件由谁提供：

```text
element_semantic_map.v1.json
```

它至少需要：

```json
{
  "semanticId": "",
  "testId": "",
  "pageId": "",
  "elementType": "",
  "role": "",
  "clickable": true
}
```

### 6.4 缺少前置状态注册表

DocReader 当前提到环境前置状态不由它负责，但没有定义交付格式。

AutoSmoke 需要：

```text
precondition_registry.v1.json
```

用来表达：

1. 起始页面。
2. 账号状态。
3. 活动状态。
4. 奖励状态。
5. 数据准备方式。
6. 是否阻断。

### 6.5 缺少断言目录

DocReader 有 preserved_assets 和 expected_result，但还不是可执行断言。

AutoSmoke 需要：

```text
assertion_catalog.v1.json
```

用来表达：

```text
element_visible
element_not_exists
page_visible
element_disabled
text_equals
red_dot_visible
state_equals
server_state
```

### 6.6 缺少外部依赖清单

DocReader 文档提到了配置表、Wiki、文案 KEY、环境状态，但建议进一步文件化为：

```text
external_dependency_manifest.v1.json
```

用于明确：

1. 哪些依赖阻断执行。
2. 哪些依赖只影响断言深度。
3. 哪些依赖由 AutoSmoke、配置系统、文案系统或人工提供。

### 6.7 缺少测试数据注册表

七日签到这类功能强依赖账号状态。  
DocReader 文档当前没有定义账号/数据资产结构。

AutoSmoke 需要：

```text
test_data_registry.v1.json
```

用于表达：

```text
账号标签、活动天数、领取状态、是否可重置、服务器、角色 ID
```

---

## 7. 建议的版本演进关系

当前 DocReader 文档里提到后续可能升级为：

```text
behavior_flow / linear_test_path / qa_consumer_asset
```

结合 AutoSmoke，建议演进关系明确为：

```text
case_seed_package.v0
  ↓
auto_smoke_case_seed.v1
  ↓
auto_smoke_asset_package.v1
  ↓
qa_consumer_asset.v1 或 executable_test_plan.v1
```

其中：

| 阶段 | 定位 | 是否可执行 |
|---|---|---|
| `case_seed_package.v0` | 文档事实和测试点素材 | 否 |
| `auto_smoke_case_seed.v1` | AutoSmoke 可执行用例种子 | 部分可执行 |
| `auto_smoke_asset_package.v1` | 完整自动化执行资产包 | 是 |
| `qa_consumer_asset.v1` | 泛化 QA 消费资产 | 视下游能力 |

---

## 8. 建议补充到 DocReader 文档的问题

DocReader 文档的“需要下游确认什么”可以补充以下问题：

1. 下游是否接受资产包目录，而不是单个 JSON？
2. 下游是否需要 `manifest.json` 作为入口？
3. 下游是否要求 `case_seed`、`element_semantic_map`、`precondition_registry` 分文件交付？
4. semanticId 与 testId 的映射由谁维护？
5. 前置状态是否有统一注册表？
6. 测试账号和数据是否能用 `account_tag` 引用？
7. 断言目录是否由上游生成还是下游生成？
8. 配置表和文案表是否需要在资产包里提供解析结果？
9. 外部依赖是否需要结构化标记 blocking/non-blocking？
10. 阻断项是否需要独立输出 `review_blockers.v1.json`？

---

## 9. 建议的 AutoSmoke 对 DocReader 回填接口

可以把 DocReader 文档第 8 节的 `interface_requirements.v0` 扩展为 AutoSmoke 版本：

```json
{
  "consumer_tool_name": "AutoSmoke",
  "consumer_goal": [
    "ui_smoke_test_execution",
    "manual_case_to_auto_case_conversion",
    "automation_report_generation"
  ],
  "accepted_input_versions": [
    "case_seed_package.v0",
    "auto_smoke_case_seed.v1",
    "auto_smoke_asset_package.v1"
  ],
  "preferred_delivery": {
    "type": "asset_package",
    "entry": "manifest.json"
  },
  "required_files_for_full_execution": [
    "case_seed.auto_smoke.v1.json",
    "element_semantic_map.v1.json",
    "precondition_registry.v1.json",
    "assertion_catalog.v1.json",
    "external_dependency_manifest.v1.json"
  ],
  "optional_files": [
    "test_data_registry.v1.json",
    "text_key_map.v1.json",
    "config_reference.v1.json",
    "source_trace.v1.json",
    "review_blockers.v1.json"
  ],
  "action_type_enum": [
    "click",
    "wait",
    "assert_exists",
    "assert_not_exists",
    "screenshot",
    "back",
    "long_press",
    "swipe",
    "input"
  ],
  "target_type_enum": [
    "testId",
    "semanticId",
    "poco",
    "text",
    "template",
    "normalized",
    "design",
    "content",
    "pixel"
  ],
  "assertion_type_enum": [
    "element_visible",
    "element_not_exists",
    "page_visible",
    "element_disabled",
    "text_equals",
    "red_dot_visible",
    "red_dot_not_exists",
    "state_equals",
    "numeric_equals",
    "server_state",
    "network_result"
  ],
  "locator_strategy": {
    "has_locator_map": true,
    "preferred_locator": "testId",
    "semantic_id_allowed": true,
    "semantic_id_must_resolve_to_test_id": true,
    "on_missing_locator": "block"
  },
  "blocking_rules": [
    "missing_action_type",
    "missing_target",
    "missing_locator",
    "missing_precondition",
    "missing_assertion",
    "config_required",
    "state_query_required",
    "environment_required"
  ]
}
```

---

## 10. 最终对比结论

DocReader 文档当前作为“首次对接文档”是合格的，它已经准确声明了 v0 的能力边界和风险。

但如果目标是让 AutoSmoke 稳定自动执行，DocReader v0 还不够。AutoSmoke 最佳上游输入应升级为：

```text
auto_smoke_asset_package.v1
```

最小必需文件：

```text
manifest.json
case_seed.auto_smoke.v1.json
element_semantic_map.v1.json
precondition_registry.v1.json
assertion_catalog.v1.json
external_dependency_manifest.v1.json
```

DocReader 的 `case_seed_package.v0` 应被视为这个资产包的上游原料，而不是最终交付物。

