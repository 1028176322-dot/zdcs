# DocReader × 自动化脚本生成工具 首次对接交互文档

- 版本：v0.1
- 日期：2026-06-17
- 用途：首次对接下游自动化脚本生成工具，说明我方当前有什么、能给什么、不能保证什么，并收集下游需要什么、如何接口对齐。
- 使用方式：本文可直接发给下游工具负责人。带“下游填写”的表格由对方补充。

## 0. 对接结论先行

当前 DocReader 可以作为“用例基础素材 / 测试点候选 / 人工评审辅助”的 v0 输入，不应直接承诺为“自动化脚本可执行输入”。

首次对接目标不是一次性定义最终接口，而是先确认：

1. 下游脚本生成工具真正需要哪些字段。
2. 哪些字段必须由 DocReader 提供，哪些字段由下游、配置表、Wiki、UI locator、文案表补齐。
3. 当前 v0 是否可以先作为 case seed 被消费。
4. 后续是否需要升级为 behavior flow / linear test path / qa consumer asset。

## 1. 我方工具定位

我方工具当前定位不是“替代下游生成脚本”，而是：

> 将策划文档转成稳定、可信、可追踪、可评审、可被下游消费的 QA 资产输入。

### 1.1 当前可承诺范围

| 范围 | 当前状态 | 说明 |
|---|---|---|
| 测试点候选 | 可提供 | 适合下游生成测试点草稿。 |
| 手工用例基础素材 | 可提供 | 需要人工评审后进入正式用例。 |
| 业务事实与来源追踪 | 可提供 | 可提供 fact、evidence、source_ref 等。 |
| 表达式 / UI 格式保留 | 部分可提供，需强化 | 例如 `行军时间 > X`、`当前驻防人数/可驻防上限`。 |
| 自动化脚本可执行输入 | 暂不承诺 | 缺少 locator、环境状态、执行动作链、断言方式等。 |
| 最终可运行脚本 | 不提供 | 应由下游自动化脚本生成工具负责。 |

### 1.2 我方与下游边界

| 角色 | 责任 | 不负责 |
|---|---|---|
| DocReader / Handoff | 文档事实抽取、来源追踪、业务陈述、表达式和值资产、待确认项 | 不直接生成最终脚本，不补齐文档外信息 |
| 自动化脚本生成工具 | 基于资产生成用例步骤、脚本骨架、断言、执行逻辑 | 不应重新读原文补 Handoff 缺失语义 |
| 外部资产系统 | 配置表、Wiki、文案 KEY、UI locator、账号/环境状态 | 不由 DocReader 内部脑补 |

## 2. 我方当前有什么

### 2.1 当前已有或可导出的资产

| 资产 | 当前状态 | 下游用途 | 风险 / 备注 |
|---|---|---|---|
| `fact_package.json` | 已有 | 原始事实、实体、关系的基础包 | 不能直接当用例。 |
| `source_index.json` | 已有 | 来源追踪、evidence 映射 | 后续需升级到 sheet + row + evidence_ref。 |
| `relation_facts.json` | 已有 | 表达部分业务关系 | 是关系事实，不是线性步骤。 |
| `structured_business_model.json` | 已有 | 业务流、配置、异常、开放问题 | 可作为 case seed 原料，不能等同脚本路径。 |
| `business_reading.md` | 已有 | 人工阅读和评审 | 不应作为正式机器接口。 |
| `business_model_validation.json` | 已有 | 校验业务模型是否可信 | 下游消费前应检查。 |
| `business_reading_validation.json` | 已有 | 校验阅读报告 | 只用于人读报告。 |

### 2.2 我方建议首次提供的 v0 接口

建议首次对接不要直接交付最终 `qa_consumer_asset.v1`，而是提供受限版本：

```text
case_seed_package.v0.json
```

它的定位是：

```text
用例基础素材 / 测试点候选 / 人工评审辅助
```

不是：

```text
最终用例资产 / 自动化脚本资产 / 可执行脚本输入
```

### 2.3 我方 v0 能提供的信息类型

| 信息类型 | 能否提供 | 示例 | 下游建议用法 |
|---|---|---|---|
| 功能块名称 | 可提供 | 驻防按钮、怪物行军时间 | 生成测试点主题。 |
| 标准业务陈述 | 可提供 / 持续增强 | 驻防按钮显示驻防人数信息。 | 生成人工用例描述。 |
| 原始事实来源 | 可提供 | sheet、row、evidence_ref | 用于审查和追溯。 |
| 表达式 / 公式 | 部分可提供 | `行军时间 > X`、`到达时间 = X` | 用于断言或配置依赖。 |
| UI 展示格式 | 部分可提供 | `当前驻防人数/可驻防上限` | 用于 UI 文案 / 格式断言。 |
| 值资产状态 | 可提供 / 持续增强 | 配置取值、未确定、文案 KEY 取值 | 决定是否能生成确定断言。 |
| 待确认项 | 可提供 | 补充KEY、待定、未说明 | 下游应进入人工评审或阻断。 |
| 业务关系 | 可提供 | 条件、结果、限制 | 可辅助生成路径，但不能直接当脚本步骤。 |
| 自动化准入判断 | 可提供基础版 | PASS_WITH_GAP / BLOCKED | 下游据此决定生成级别。 |

## 3. 我方当前不能直接提供什么

| 缺口 | 说明 | 建议归属 |
|---|---|---|
| UI locator | 策划文档通常没有控件定位信息。 | 下游或 UI locator 资产系统。 |
| 可执行动作链 | 当前业务流不等于脚本执行顺序。 | 下游 + 后续 behavior_flow_assets。 |
| 环境前置状态 | 账号等级、开服天数、活动状态、数据准备等。 | 下游或环境管理系统。 |
| 配置表实际值 | 文档里的 `D2Config` 只是配置来源，不是具体值。 | 配置表查询系统。 |
| 文案 KEY 映射 | `补充KEY` 或 text key 不等于最终显示文案。 | 文案表或多语言系统。 |
| 最终断言方式 | OCR、UI text、接口返回、日志、DB 校验等需要下游定义。 | 下游脚本工具。 |
| 清理动作 | 自动化后置清理通常不在策划文档中。 | 下游或测试环境工具。 |

## 4. 建议的 v0 交付接口

### 4.1 文件级结构

```json
{
  "schema_version": "case_seed_package.v0",
  "feature_name": "示例功能",
  "admission": {
    "manual_case_generation": "PASS_WITH_GAP",
    "automation_script_generation": "BLOCKED",
    "allowed_scope": [
      "test_point_seed",
      "manual_case_seed",
      "review_assisted_case_design"
    ],
    "blocked_scope": [
      "fully_trusted_case_asset",
      "final_automation_script"
    ],
    "blocked_reasons": [
      "缺少 UI locator",
      "缺少可执行线性行为链",
      "配置取值需要外部配置表确认"
    ]
  },
  "business_items": [],
  "relation_items": [],
  "value_assets": [],
  "review_items": [],
  "source_refs": []
}
```

### 4.2 单个业务项示例

```json
{
  "item_id": "BITEM_0051",
  "block_name": "驻防按钮",
  "item_type": "ui_display_rule",
  "statement": "驻防按钮显示驻防人数信息。",
  "certainty": "confirmed",
  "preserved_assets": [
    {
      "asset_type": "display_format",
      "raw_expression": "当前驻防人数/可驻防上限",
      "preserve_policy": "exact",
      "downstream_usage": ["ui_display_assertion", "manual_case_expected_result"]
    }
  ],
  "case_seed_hint": {
    "can_generate_test_point": true,
    "can_generate_manual_case": true,
    "can_generate_automation_script": false,
    "blocked_reasons": ["缺少驻防按钮 locator", "缺少执行前置状态"]
  },
  "source_refs": [
    {
      "evidence_ref": "EVD_0051",
      "sheet_name": "规则",
      "row_number": 51,
      "source_excerpt": "R51: 驻防按钮:当前驻防人数/可驻防上限"
    }
  ],
  "review_required": true
}
```

## 5. 需要下游确认什么

### 5.1 下游工具的目标输出

| 问题 | 下游填写 |
|---|---|
| 第一阶段希望生成什么？测试点、手工用例、脚本骨架、可执行脚本？ |  |
| 是否允许先消费 `case_seed_package.v0`？ |  |
| 是否要求输入必须是线性步骤？ |  |
| 是否接受 PASS_WITH_GAP / BLOCKED 这类准入状态？ |  |
| 不确定项是否允许进入“待确认用例”？ |  |

### 5.2 下游输入格式要求

| 问题 | 下游填写 |
|---|---|
| 接收方式：文件、API、消息队列、数据库，还是 Git 仓库？ |  |
| 接收格式：JSON、YAML、Markdown、Excel，还是混合？ |  |
| 是否需要严格 JSON Schema？ |  |
| 是否需要字段版本号和向后兼容策略？ |  |
| 单次输入是一份文档、一个功能、一个版本，还是一个功能块？ |  |

### 5.3 下游最小必需字段

| 字段 | 我方 v0 能否提供 | 下游是否必需 | 下游用途 | 下游填写备注 |
|---|---|---|---|---|
| feature_name | 能 |  | 功能归属 |  |
| block_name | 能 |  | 测试模块 / 用例标题 |  |
| statement | 能 |  | 用例描述 / 测试点 |  |
| certainty | 能 |  | 是否进入正式生成 |  |
| source_refs | 能 |  | 追溯和审核 |  |
| preserved_assets | 部分能 |  | 断言 / 配置 / UI 格式 |  |
| preconditions | 部分能 |  | 测试前置 |  |
| action_type | 暂不能稳定提供 |  | 脚本动作 |  |
| target_name | 部分能 |  | UI 对象或接口对象 |  |
| locator | 不能 |  | 自动化定位 |  |
| expected_result | 部分能 |  | 预期结果 |  |
| assertion_type | 不能稳定提供 |  | 断言实现 |  |
| test_data | 部分能 |  | 入参 / 配置 / 账号数据 |  |
| cleanup | 不能 |  | 后置清理 |  |

### 5.4 行为步骤模型

请下游确认是否需要如下结构。如果需要，请填写哪些字段必需。

```json
{
  "step_order": 1,
  "actor": "player/system",
  "action_type": "click/input/wait/assert/api_call/config_query",
  "target_type": "button/page/dialog/api/config",
  "target_name": "驻防按钮",
  "locator_ref": "待下游提供",
  "preconditions": [],
  "inputs": [],
  "expected_results": [],
  "assertions": [],
  "source_refs": []
}
```

| 问题 | 下游填写 |
|---|---|
| action_type 需要哪些枚举？ |  |
| target_type 需要哪些枚举？ |  |
| actor 是否必须区分 player / system / server？ |  |
| 是否需要 wait_condition？ |  |
| 是否需要 cleanup_step？ |  |
| 分支步骤如何表达？if/else、path、graph，还是多用例展开？ |  |

### 5.5 Locator 对齐

| 问题 | 下游填写 |
|---|---|
| 下游是否已有 UI locator map？ |  |
| locator key 的命名规则是什么？ |  |
| DocReader 输出 `target_name` 后，下游是否能自动匹配 locator？ |  |
| 匹配失败时，是阻断还是进入人工补齐？ |  |
| 是否需要我方输出 `locator_candidate_name`？ |  |

### 5.6 断言模型对齐

| 断言类型 | 下游是否支持 | 备注 |
|---|---|---|
| UI 文本断言 |  | 例如按钮文案、弹窗提示。 |
| UI 格式断言 |  | 例如 `当前驻防人数/可驻防上限`。 |
| 数值断言 |  | 例如排行榜、奖励、次数。 |
| 公式断言 |  | 例如 `行军时间 > X`、`到达时间 = X`。 |
| 状态断言 |  | 例如活动开启、驻防成功。 |
| 接口断言 |  | 例如服务端返回字段。 |
| 日志 / DB 断言 |  | 需要环境权限。 |

### 5.7 配置表 / Wiki / 文案 KEY 对齐

| 问题 | 下游填写 |
|---|---|
| 下游是否能查询配置表？ |  |
| 配置来源字段如何表达？例如 `D2Config`。 |  |
| `X/Y/Z/%/{0}` 这类变量应由谁解析？ |  |
| 文案 KEY 是否能映射到最终文案？ |  |
| Wiki MCP 是否由下游调用？ |  |
| 查询失败时是否阻断脚本生成？ |  |

### 5.8 不确定项与阻断规则

| 状态 | 建议下游处理 | 下游是否接受 |
|---|---|---|
| confirmed | 可进入正式用例或脚本候选 |  |
| inferred | 可进入待评审用例 |  |
| uncertain | 只能进入待确认项 |  |
| missing | 阻断或生成缺口清单 |  |
| conflict | 必须阻断并人工评审 |  |
| config_required | 需要配置表查询 |  |
| locator_required | 需要 locator 补齐 |  |
| text_key_required | 需要文案表查询 |  |

## 6. 建议的对齐流程

| 阶段 | 我方动作 | 下游动作 | 产出 |
|---|---|---|---|
| 1. 样例确认 | 提供 1 份 `case_seed_package.v0` 样例 | 判断是否能消费 | 字段差异清单 |
| 2. 字段对齐 | 根据差异调整 v0 schema | 提供必需字段、枚举、阻断规则 | `interface_requirements.v0` |
| 3. 试消费 | 提供真实文档生成的 v0 包 | 生成测试点 / 用例草稿 | 消费结果与错误清单 |
| 4. 评审闭环 | 输出 review_packet | 标记误用、缺失、阻断项 | review_decisions |
| 5. v1 决策 | 判断是否升级行为流 / 线性路径资产 | 确认脚本所需结构 | v1 范围确认 |

## 7. 首次对接验收标准

| 验收项 | 通过标准 |
|---|---|
| 下游能读取 v0 包 | 不报结构错误。 |
| 下游能识别准入状态 | 能区分 PASS / PASS_WITH_GAP / BLOCKED。 |
| 下游能生成测试点草稿 | 至少能基于 business_items 生成候选测试点。 |
| 下游不会误生成自动化脚本 | 当 automation_script_generation=BLOCKED 时必须阻断。 |
| 下游能展示来源 | 每条测试点能回显 source_refs。 |
| 下游能处理不确定项 | uncertain / missing / conflict 不进入确定预期。 |
| 下游能反馈缺失字段 | 返回字段缺口，而不是静默失败。 |

## 8. 需要下游返回的接口说明模板

请下游按以下结构返回一份 `interface_requirements.v0` 或等价说明。

```json
{
  "consumer_tool_name": "",
  "consumer_goal": [
    "test_point_generation",
    "manual_case_generation",
    "automation_script_generation"
  ],
  "accepted_input_versions": ["case_seed_package.v0"],
  "required_fields": [],
  "optional_fields": [],
  "unsupported_fields": [],
  "action_type_enum": [],
  "target_type_enum": [],
  "assertion_type_enum": [],
  "locator_strategy": {
    "has_locator_map": false,
    "locator_key_rule": "",
    "on_missing_locator": "block / review / ignore"
  },
  "external_asset_requirements": [
    "config_table",
    "wiki",
    "text_key_table",
    "test_account",
    "environment_state"
  ],
  "blocking_rules": [],
  "feedback_format": {
    "schema_error": "",
    "missing_fields": [],
    "unsupported_values": [],
    "generation_result": ""
  }
}
```

## 9. 首次会议问题清单

1. 你们第一阶段要生成的是测试点、手工用例、脚本骨架，还是可执行脚本？
2. 你们是否接受先消费 `case_seed_package.v0`，只作为用例基础素材？
3. 你们生成脚本必须依赖哪些字段？缺少哪些字段会直接阻断？
4. 你们是否要求线性步骤？如果要求，step schema 是什么？
5. 你们的 action_type / target_type / assertion_type 枚举是什么？
6. UI locator 如何提供？能否从 target_name 自动映射？
7. 配置表、Wiki、文案 KEY 由谁查询？查询失败如何处理？
8. 不确定项、配置取值、文案 KEY、缺失信息如何进入评审或阻断？
9. 每条生成结果是否必须带 source_ref？source_ref 展示到什么粒度？
10. 下游失败时能否返回结构化错误，方便我方修 schema？
11. 下游是否需要 review_packet，用于人工确认后再生成脚本？
12. v1 是否需要 behavior_flow_assets / linear_test_paths，而不仅是 case seed？

## 10. 本次对接的预期结论

首次对接后，希望明确以下结果：

- 是否接受 `case_seed_package.v0` 作为第一版输入。
- 下游最小必需字段清单。
- 自动化脚本生成的阻断条件。
- locator、配置表、文案 KEY、环境状态的责任边界。
- 下游返回错误和反馈的格式。
- 是否需要进入 v1：`behavior_flow_assets`、`linear_test_paths`、`qa_consumer_asset`。

## 11. 会议记录区

| 项目 | 结论 | 负责人 | 后续动作 |
|---|---|---|---|
| v0 输入是否接受 |  |  |  |
| 必需字段 |  |  |  |
| 阻断规则 |  |  |  |
| locator 对齐 |  |  |  |
| 配置 / Wiki / 文案表 |  |  |  |
| 评审闭环 |  |  |  |
| v1 范围 |  |  |  |

---

一句话边界：DocReader 负责把策划文档资产化和可信化；下游工具负责把资产转成用例、脚本骨架或可执行脚本；无法确认的信息必须进入评审、外部查询或阻断，不应脑补。