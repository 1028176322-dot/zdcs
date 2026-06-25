# AutoSmoke 基于 wiki_armrace_reviewable 的上游补充内容与格式说明

> 日期：2026-06-25  
> 对比对象：`E:/zdcs/参考资料/wiki_armrace_reviewable`  
> 前提：转换层放在 AutoSmoke  
> 目标：明确上游在当前已提供文件基础上，还需要补充什么、格式是什么、每个文件的用途是什么。

---

## 1. 当前上游已提供内容

当前上游提供的目录为：

```text
wiki_armrace_reviewable/
├── ai_prompt.txt
├── candidate_feature_flow.json
├── render_audit.json
├── review_pack.md
├── source_index.json
├── source_materialized.md
└── validation_report.json
```

这些文件的作用如下：

| 文件 | 当前作用 | 是否可直接执行 |
|---|---|---:|
| `candidate_feature_flow.json` | 功能规则候选图，包含节点、边、流程、review_items | 否 |
| `review_pack.md` | 人工审阅版报告 | 否 |
| `source_materialized.md` | Wiki 源材料汇总 | 否 |
| `source_index.json` | 源材料行号索引 | 否 |
| `validation_report.json` | 结构校验报告 | 否 |
| `render_audit.json` | 渲染审计信息 | 否 |
| `ai_prompt.txt` | 生成提示词 | 否 |

当前包的关键状态：

```text
candidate_feature_flow.status = REVIEW_REQUIRED
FLOW-MAIN-BEHAVIOR.ready_for_case_generation = false
validation_report.status = STRUCTURAL_PASS_REVIEW_REQUIRED
```

结论：

```text
当前文件可以作为 AutoSmoke 的业务理解输入。
当前文件不能直接作为 AutoSmoke 的自动执行输入。
```

---

## 2. 职责边界

因为转换层放在 AutoSmoke，所以：

### 2.1 上游不需要提供

```text
AutoSmoke 执行脚本
Unity/Playwright 操作代码
最终 locator
最终 testId
最终 semanticId
element_mapping_formal.json
mapping_evidence.json
自动化执行报告
```

这些由 AutoSmoke 负责生成、确认、保存和维护。

### 2.2 上游需要提供

```text
业务规则是否审核通过
哪些规则要测
用例意图
自然语言步骤
目标对象名称
目标对象所属页面
目标对象角色
页面入口和返回路径
测试账号和前置状态
配置值、奖励值、阈值
业务状态采集需求
业务断言意图
外部依赖
无法自动化或待确认事项
```

AutoSmoke 根据这些内容完成：

```text
业务输入解析
用例转换
步骤转换
targetName 匹配
semanticId/testId 候选生成
IDE 自动/人工确认
element_mapping 保存
状态采集
断言执行
报告输出
```

---

## 3. 上游需要补充的文件总览

建议在当前目录基础上补充为：

```text
autosmoke_upstream_handoff.armrace.v1/
├── manifest.json
├── candidate_feature_flow.json
├── feature_flow_review_result.v1.json
├── manual_test_cases.v1.json
├── target_name_catalog.v1.json
├── page_flow_catalog.v1.json
├── test_data_profile.v1.json
├── value_assets.v1.json
├── source_trace.v1.json
├── review_items.v1.json
├── business_state_contract.v1.json
├── business_assertions.v1.json
└── optional_external_refs.v1.json
```

文件用途如下：

| 文件 | 是否必需 | 用途 |
|---|---:|---|
| `manifest.json` | 必需 | 交付包入口，声明功能、文件、版本和自动化范围 |
| `candidate_feature_flow.json` | 已提供 | 功能规则候选图，作为业务理解来源 |
| `feature_flow_review_result.v1.json` | 必需 | 把 `REVIEW_REQUIRED` 变为可消费审核结论 |
| `manual_test_cases.v1.json` | 必需 | 明确要执行哪些测试用例 |
| `target_name_catalog.v1.json` | 必需 | 稳定目标名目录，供 AutoSmoke 匹配元素 |
| `page_flow_catalog.v1.json` | 必需 | 页面入口、跳转、返回、恢复路径 |
| `test_data_profile.v1.json` | 必需 | 账号、活动、资源、积分、奖励状态等前置数据 |
| `value_assets.v1.json` | 强烈建议 | 配置值、奖励值、阈值、文案 key、表字段 |
| `source_trace.v1.json` | 必需 | 用例、目标、断言到源文档/节点的追踪 |
| `review_items.v1.json` | 必需 | 阻断项、待确认项、降级项 |
| `business_state_contract.v1.json` | 功能逻辑自动化必需 | 声明可采集的业务状态路径 |
| `business_assertions.v1.json` | 功能逻辑自动化必需 | 声明业务断言 |
| `optional_external_refs.v1.json` | 功能逻辑自动化建议 | 声明 GM、配置、服务端接口、日志等外部依赖 |

---

## 4. manifest.json

### 4.1 用途

`manifest.json` 是 AutoSmoke 读取交付包的入口。

它用于：

1. 确认这是哪个功能的交付包。
2. 确认当前包支持 UI 自动化还是 UI + 功能逻辑自动化。
3. 声明每个文件的路径。
4. 声明哪些文件必须存在。

### 4.2 格式

```json
{
  "schema_version": "autosmoke_upstream_handoff.v1",
  "package_id": "armrace_20260625_v1",
  "feature_id": "feature-17751c8a",
  "feature_name": "军备竞赛",
  "feature_domain": "activity",
  "feature_type": "rank_reward_event",
  "source_tool": "wiki_feature_flow_builder",
  "source_doc": {
    "source_type": "gamewiki",
    "source_name": "系统/军备竞赛|字典/H活动_军备竞赛配置",
    "source_version": "V1.2",
    "generated_at": "2026-06-25T10:47:26+08:00"
  },
  "automation_scope": {
    "ui_automation": true,
    "business_logic_automation": true,
    "requires_manual_review_before_execution": false
  },
  "files": {
    "candidate_feature_flow": "candidate_feature_flow.json",
    "feature_flow_review_result": "feature_flow_review_result.v1.json",
    "manual_test_cases": "manual_test_cases.v1.json",
    "target_name_catalog": "target_name_catalog.v1.json",
    "page_flow_catalog": "page_flow_catalog.v1.json",
    "test_data_profile": "test_data_profile.v1.json",
    "value_assets": "value_assets.v1.json",
    "source_trace": "source_trace.v1.json",
    "review_items": "review_items.v1.json",
    "business_state_contract": "business_state_contract.v1.json",
    "business_assertions": "business_assertions.v1.json",
    "optional_external_refs": "optional_external_refs.v1.json"
  },
  "required_files": [
    "candidate_feature_flow",
    "feature_flow_review_result",
    "manual_test_cases",
    "target_name_catalog",
    "page_flow_catalog",
    "test_data_profile",
    "source_trace",
    "review_items"
  ]
}
```

### 4.3 字段说明

| 字段 | 必需 | 说明 |
|---|---:|---|
| `schema_version` | 是 | 固定为 `autosmoke_upstream_handoff.v1` |
| `package_id` | 是 | 交付包唯一 ID |
| `feature_id` | 是 | 对应 `candidate_feature_flow.json.feature.feature_id` |
| `feature_name` | 是 | 功能名 |
| `feature_domain` | 建议 | 功能域，如 `activity/bag/shop/task/mail` |
| `feature_type` | 建议 | 功能类型，如 `rank_reward_event/reward/entry/upgrade_system` |
| `automation_scope` | 是 | 声明自动化范围 |
| `files` | 是 | 文件别名到文件路径 |
| `required_files` | 是 | AutoSmoke 必须校验存在的文件 |

---

## 5. feature_flow_review_result.v1.json

### 5.1 用途

当前 `candidate_feature_flow.json` 是候选理解，状态为 `REVIEW_REQUIRED`。

AutoSmoke 不能直接把未审核规则转换为正式自动化用例。因此上游必须提供审核结果。

该文件用于说明：

1. 主流程是否确认成立。
2. 哪些节点确认正确。
3. 哪些节点需要修正。
4. 哪些节点只作为参考，不进入用例生成。
5. 哪些节点禁止自动化。

### 5.2 格式

```json
{
  "schema_version": "feature_flow_review_result.v1",
  "feature_id": "feature-17751c8a",
  "source_flow_file": "candidate_feature_flow.json",
  "review_status": "APPROVED_WITH_CHANGES",
  "reviewed_at": "2026-06-25T11:30:00+08:00",
  "reviewer": "feature_owner",
  "flow_results": [
    {
      "flow_id": "FLOW-MAIN-BEHAVIOR",
      "status": "APPROVED",
      "ready_for_case_generation": true,
      "note": "主干行为流程成立，可用于生成测试路径。"
    }
  ],
  "node_results": [
    {
      "node_id": "NODE-05-3-1",
      "status": "APPROVED",
      "corrected_title": "功能开启",
      "corrected_rule_expression": [
        "server_open_day >= 1",
        "player_lighthouse_level >= 7"
      ],
      "automation_scope": [
        "precondition",
        "business_assertion"
      ]
    },
    {
      "node_id": "NODE-19-8-1-UI",
      "status": "APPROVED_WITH_CHANGES",
      "corrected_title": "UI 导航与流转",
      "corrected_rule_expression": [
        "click_armrace_tab -> open_armrace_main_view",
        "click_rule_tips -> show_rule_tips",
        "click_calendar_button -> open_theme_description",
        "click_score_reward_chest -> claim_score_reward"
      ],
      "automation_scope": [
        "ui_action",
        "ui_assertion"
      ]
    }
  ],
  "excluded_nodes": [
    {
      "node_id": "NODE-06-3-2",
      "reason": "当前无活动专属跨服分组规则，仅作为背景信息，不生成用例。"
    }
  ]
}
```

### 5.3 状态枚举

```text
APPROVED              已确认，可转换
APPROVED_WITH_CHANGES 已确认但有修正，以修正内容为准
PARTIAL_APPROVED      部分可转换
REFERENCE_ONLY        仅参考，不生成用例
REJECTED              废弃
REVIEW_REQUIRED       仍需审核
```

### 5.4 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| `flow_results` | 判断主流程能否进入用例生成 |
| `node_results.status` | 判断节点是否可转换 |
| `corrected_rule_expression` | 覆盖候选规则表达式 |
| `automation_scope` | 判断节点用于前置、UI步骤、断言还是配置 |
| `excluded_nodes` | 从转换范围中排除 |

---

## 6. manual_test_cases.v1.json

### 6.1 用途

`candidate_feature_flow.json` 说明“功能有什么规则”，但没有说明“要测哪些用例”。

该文件用于给 AutoSmoke 明确：

1. 用例 ID。
2. 用例标题。
3. 前置条件。
4. 操作步骤。
5. 每步目标名。
6. 每步预期。
7. 用例级预期结果。
8. 是否允许自动化。

### 6.2 格式

```json
{
  "schema_version": "manual_test_cases.v1",
  "feature_id": "feature-17751c8a",
  "feature_name": "军备竞赛",
  "test_cases": [
    {
      "case_id": "ARMRACE_UI_001",
      "title": "从常规活动进入军备竞赛主界面",
      "priority": "P0",
      "case_type": "ui_flow",
      "source_node_ids": [
        "NODE-19-8-1-UI"
      ],
      "preconditions": [
        "活动已开启",
        "玩家灯塔等级 >= 7",
        "玩家位于可打开常规活动入口的场景"
      ],
      "steps": [
        {
          "step_order": 1,
          "action": "open_page",
          "target_name": "常规活动主界面",
          "expected": "显示常规活动主界面"
        },
        {
          "step_order": 2,
          "action": "click",
          "target_name": "军备竞赛页签",
          "expected": "进入军备竞赛主界面"
        }
      ],
      "expected_results": [
        "军备竞赛主界面显示",
        "显示当前阶段、轮次、主题、积分、奖励入口和排行榜入口"
      ],
      "automation_level": "AUTO",
      "assertion_refs": [
        "BASSERT_ARMRACE_UI_001"
      ]
    },
    {
      "case_id": "ARMRACE_REWARD_001",
      "title": "达到积分阈值后领取积分奖励",
      "priority": "P0",
      "case_type": "reward",
      "source_node_ids": [
        "NODE-14-6-1",
        "NODE-19-8-1-UI"
      ],
      "preconditions": [
        "活动已开启",
        "玩家灯塔等级 >= 7",
        "玩家本轮积分达到积分奖励第一档阈值",
        "积分奖励第一档未领取"
      ],
      "steps": [
        {
          "step_order": 1,
          "action": "open_page",
          "target_name": "军备竞赛主界面",
          "expected": "显示军备竞赛主界面"
        },
        {
          "step_order": 2,
          "action": "click",
          "target_name": "积分奖励宝箱",
          "expected": "触发积分奖励领取"
        }
      ],
      "expected_results": [
        "积分奖励领取成功",
        "奖励到账",
        "积分奖励宝箱状态变为已领取"
      ],
      "automation_level": "AUTO",
      "assertion_refs": [
        "BASSERT_ARMRACE_REWARD_001"
      ]
    }
  ]
}
```

### 6.3 字段说明

| 字段 | 必需 | 说明 |
|---|---:|---|
| `case_id` | 是 | 用例唯一 ID |
| `title` | 是 | 用例标题 |
| `priority` | 是 | `P0/P1/P2/P3` |
| `case_type` | 是 | `ui_flow/reward/business_rule/state_boundary/settlement/exception` |
| `source_node_ids` | 是 | 对应功能图节点 |
| `preconditions` | 是 | 执行前置条件 |
| `steps` | 是 | 操作步骤 |
| `steps[].step_order` | 是 | 步骤顺序 |
| `steps[].action` | 是 | 操作类型 |
| `steps[].target_name` | 是 | 目标名，必须能在 `target_name_catalog` 找到 |
| `steps[].expected` | 是 | 步骤预期 |
| `expected_results` | 是 | 用例最终预期 |
| `automation_level` | 是 | `AUTO/PARTIAL_AUTO/MANUAL_ONLY/BLOCKED` |
| `assertion_refs` | 建议 | 关联业务断言 |

### 6.4 action 枚举建议

```text
open_page
click
input
select
wait
claim
check
navigate
back
close
refresh
```

### 6.5 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| `test_cases` | 生成自动化用例 |
| `steps` | 生成 UI 操作步骤 |
| `target_name` | 匹配目标名目录，再匹配元素 |
| `expected` | 生成 UI 断言候选 |
| `preconditions` | 关联测试数据准备 |
| `assertion_refs` | 关联业务断言 |

---

## 7. target_name_catalog.v1.json

### 7.1 用途

上游不提供最终 `testId/semanticId`，但必须提供稳定目标名。

该文件用于把自然语言中的目标对象标准化，例如：

```text
军备竞赛页签
规则 tips
日历按钮
目标奖励宝箱
积分奖励宝箱
任务跳转按钮
查看更多任务按钮
排行榜头像
排行奖励宝箱
返回按钮
```

AutoSmoke 使用它完成：

```text
target_name
  → semanticId 候选
  → testId 候选
  → IDE 自动/人工确认
  → element_mapping_formal
```

### 7.2 格式

```json
{
  "schema_version": "target_name_catalog.v1",
  "feature_id": "feature-17751c8a",
  "targets": [
    {
      "target_id": "TGT_ARMRACE_TAB",
      "target_name": "军备竞赛页签",
      "aliases": [
        "军备竞赛入口",
        "军备竞赛活动页签",
        "Arms Race Tab"
      ],
      "page_name": "常规活动主界面",
      "page_id_hint": "activity.main",
      "target_type": "ui_element",
      "role": "tab",
      "action_roles": [
        "click",
        "navigate"
      ],
      "semantic_hint": "activity.armrace.tab",
      "required": true,
      "source_node_ids": [
        "NODE-19-8-1-UI"
      ]
    },
    {
      "target_id": "TGT_ARMRACE_SCORE_REWARD_CHEST",
      "target_name": "积分奖励宝箱",
      "aliases": [
        "积分宝箱",
        "本轮积分奖励宝箱"
      ],
      "page_name": "军备竞赛主界面",
      "page_id_hint": "activity.armrace.main",
      "target_type": "ui_element",
      "role": "chest",
      "action_roles": [
        "click",
        "claim"
      ],
      "semantic_hint": "activity.armrace.score_reward.chest",
      "required": true,
      "source_node_ids": [
        "NODE-14-6-1",
        "NODE-19-8-1-UI"
      ]
    }
  ]
}
```

### 7.3 字段说明

| 字段 | 必需 | 说明 |
|---|---:|---|
| `target_id` | 是 | 目标对象唯一 ID |
| `target_name` | 是 | 标准中文目标名 |
| `aliases` | 建议 | 别名，提升自然语言匹配率 |
| `page_name` | 是 | 目标所在页面 |
| `page_id_hint` | 建议 | 页面英文提示，供 AutoSmoke 生成 pageId |
| `target_type` | 是 | 目标类型 |
| `role` | 是 | UI/业务角色 |
| `action_roles` | 是 | 支持的动作 |
| `semantic_hint` | 建议 | 语义提示，不是最终 semanticId |
| `required` | 是 | 是否关键目标 |
| `source_node_ids` | 建议 | 来源节点 |

### 7.4 target_type 建议

```text
ui_element
page
dialog
list_item
reward_item
state_object
config_item
external_state
```

### 7.5 role 建议

```text
button
tab
text
icon
chest
list
rank_item
avatar
popup
page
resource
timer
progress
```

---

## 8. page_flow_catalog.v1.json

### 8.1 用途

用于说明页面怎么进入、怎么返回、失败后怎么恢复。

如果缺少该文件，AutoSmoke 即使知道“点击军备竞赛页签”，也不知道：

```text
从哪里开始
如何打开常规活动主界面
如何进入军备竞赛主界面
如何返回
弹窗打开后如何关闭
失败后如何恢复页面状态
```

### 8.2 格式

```json
{
  "schema_version": "page_flow_catalog.v1",
  "feature_id": "feature-17751c8a",
  "pages": [
    {
      "page_id": "activity.main",
      "page_name": "常规活动主界面",
      "entry_method": "open_activity_panel",
      "required_targets": [
        "TGT_ARMRACE_TAB"
      ],
      "recovery_method": "close_all_dialogs_and_open_activity_panel"
    },
    {
      "page_id": "activity.armrace.main",
      "page_name": "军备竞赛主界面",
      "entry_path": [
        {
          "from_page_id": "activity.main",
          "action": "click",
          "target_id": "TGT_ARMRACE_TAB"
        }
      ],
      "page_assertions": [
        {
          "type": "ui_visible",
          "target_name": "军备竞赛主界面"
        },
        {
          "type": "ui_visible",
          "target_name": "当前主题"
        }
      ],
      "back_path": [
        {
          "action": "click",
          "target_name": "返回按钮"
        }
      ],
      "recovery_method": "back_to_activity_main_then_reopen"
    }
  ]
}
```

### 8.3 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| `entry_method` | 生成进入页面动作 |
| `entry_path` | 生成跨页面路径 |
| `page_assertions` | 判断页面是否进入成功 |
| `back_path` | 用例结束后恢复页面 |
| `recovery_method` | 执行失败后恢复 |

---

## 9. test_data_profile.v1.json

### 9.1 用途

军备竞赛强依赖前置状态。上游必须声明用例需要什么账号和状态。

例如：

```text
活动已开启
服务器开服天数满足
玩家灯塔等级 >= 7
当前处于活动有效期
当前阶段/轮次可控
玩家积分可准备
奖励领取状态可准备
匹配池可准备
邮件状态可检查
```

### 9.2 格式

```json
{
  "schema_version": "test_data_profile.v1",
  "feature_id": "feature-17751c8a",
  "profiles": [
    {
      "profile_id": "ARMRACE_ELIGIBLE_PLAYER",
      "description": "满足军备竞赛参与条件的玩家",
      "required_for_cases": [
        "ARMRACE_UI_001",
        "ARMRACE_REWARD_001"
      ],
      "account_requirements": {
        "player_lighthouse_level": {
          "operator": ">=",
          "value": 7
        },
        "server_open_day": {
          "operator": ">=",
          "value": 1
        },
        "activity_enabled": true
      },
      "activity_requirements": {
        "content_id": 6001,
        "activity_id": 2040100,
        "current_stage": "any_active",
        "current_round": "any_active",
        "timezone": "UTC"
      },
      "state_setup": {
        "method": "gm_or_prepared_account",
        "reset_before_case": true,
        "required_capabilities": [
          "set_player_level",
          "open_activity",
          "set_activity_time",
          "set_armrace_score",
          "clear_reward_claim_state"
        ]
      }
    }
  ]
}
```

### 9.3 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| `account_requirements` | 判断账号是否满足 |
| `activity_requirements` | 判断活动状态是否满足 |
| `state_setup.method` | 决定是否调用 GM 或使用预置账号 |
| `required_capabilities` | 检查环境是否支持自动准备 |
| `required_for_cases` | 关联用例 |

---

## 10. value_assets.v1.json

### 10.1 用途

将文档中的配置值、奖励值、阈值、表字段结构化。

当前 `source_materialized.md` 中已有很多值，但散落在正文中。AutoSmoke 做断言时需要结构化值。

### 10.2 格式

```json
{
  "schema_version": "value_assets.v1",
  "feature_id": "feature-17751c8a",
  "assets": [
    {
      "asset_id": "VAL_ARMRACE_ACTIVITY_CONFIG",
      "asset_type": "config_row",
      "name": "军备竞赛活动调度配置",
      "table": "CActvOnline",
      "keys": {
        "ID": 2040100,
        "Type": 67,
        "ContentID": 6001
      },
      "values": {
        "TriggerVal": "1d",
        "Reopen": 1,
        "TriggerRept": "7d",
        "Duration": "7d",
        "LevelVal": 7,
        "MailUseActvID": 18000016
      },
      "source_refs": [
        "L12-L23"
      ]
    },
    {
      "asset_id": "VAL_ARMRACE_RANK_SEGMENTS",
      "asset_type": "rank_segment",
      "name": "军备竞赛匹配段位",
      "table": "CArmsRaceRank",
      "values": {
        "type1_segments": [
          [7, 9],
          [10, 12],
          [13, 14],
          [15, 16],
          [17, 18],
          [19, 20],
          [21, 22],
          [23, 24],
          [25, 26],
          [27, 28],
          [29, 30]
        ],
        "type2_segments": [
          [7, 30]
        ]
      },
      "source_refs": [
        "L38-L41"
      ]
    }
  ]
}
```

### 10.3 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| 配置行 | 校验活动配置 |
| 阈值 | 生成断言 |
| 奖励 ID | 校验奖励到账 |
| 邮件 ID | 校验补发邮件 |
| 文案 key | 校验 UI 文案 |
| 表字段 | 生成状态路径或外部查询 |

---

## 11. source_trace.v1.json

### 11.1 用途

当前已有 `source_index.json`，但它只是源文档行号索引。AutoSmoke 还需要知道：

```text
哪个用例来自哪个节点
哪个目标名来自哪行
哪个断言来自哪条规则
哪个配置值来自哪个来源
```

### 11.2 格式

```json
{
  "schema_version": "source_trace.v1",
  "feature_id": "feature-17751c8a",
  "sources": [
    {
      "trace_id": "TRACE_ARMRACE_UI_001",
      "case_id": "ARMRACE_UI_001",
      "target_ids": [
        "TGT_ARMRACE_TAB"
      ],
      "assertion_ids": [
        "BASSERT_ARMRACE_UI_001"
      ],
      "node_ids": [
        "NODE-19-8-1-UI"
      ],
      "source_refs": [
        "L89-L92"
      ],
      "source_file": "source_materialized.md",
      "evidence_excerpt": [
        "常规活动主界面点击军备竞赛页签进入主界面。",
        "主界面支持货币区图标跳通用货币获取弹窗、规则 tips、日历按钮打开竞赛主题说明..."
      ]
    }
  ]
}
```

### 11.3 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| `case_id` | 报告回溯用例来源 |
| `target_ids` | 报告回溯目标来源 |
| `assertion_ids` | 报告回溯断言来源 |
| `node_ids` | 关联功能图 |
| `source_refs` | 定位源文档行 |
| `evidence_excerpt` | 失败报告展示依据 |

---

## 12. review_items.v1.json

### 12.1 用途

当前 `candidate_feature_flow.json` 里已有 `review_items`，但它是功能流审核项，不是 AutoSmoke 执行准入阻断项。

上游需要提供 AutoSmoke 格式的阻断项，说明：

```text
什么没有确认
什么不能自动化
什么需要外部系统
什么可以降级为 UI 验证
谁负责补充
不补充时如何处理
```

### 12.2 格式

```json
{
  "schema_version": "review_items.v1",
  "feature_id": "feature-17751c8a",
  "items": [
    {
      "item_id": "REVIEW_ARMRACE_RULES_001",
      "related_node_id": "REVIEW-DERIVED-RULES",
      "related_case_id": null,
      "status": "manual_review_required",
      "severity": "blocker",
      "description": "14 个规则/行为表达式仍为 RULE_PACK_DERIVED，需要业务负责人确认后才能生成正式自动化用例。",
      "suggested_handling": "BLOCKED",
      "required_owner": "feature_owner"
    },
    {
      "item_id": "REVIEW_ARMRACE_TARGET_001",
      "related_node_id": "NODE-19-8-1-UI",
      "related_case_id": "ARMRACE_UI_001",
      "status": "target_required",
      "severity": "blocker",
      "description": "需要补充军备竞赛页签、规则 tips、日历按钮、奖励宝箱、返回按钮等目标名目录。",
      "suggested_handling": "BLOCKED",
      "required_owner": "upstream_doc_owner"
    }
  ]
}
```

### 12.3 status 枚举建议

```text
manual_review_required
case_required
target_required
target_binding_required
page_flow_required
state_prepare_required
state_query_required
state_contract_required
business_assertion_required
external_dependency_required
manual_only
```

### 12.4 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| `severity=blocker` | 阻止生成正式自动化执行 |
| `suggested_handling=BLOCKED` | 标记阻断 |
| `suggested_handling=PASS_WITH_GAP` | 允许降级执行 |
| `required_owner` | 报告中标注责任方 |

---

## 13. business_state_contract.v1.json

### 13.1 用途

如果只做 UI 自动化，该文件可以暂不提供。

如果要做 UI + 功能逻辑自动化，则必须提供。

它用于告诉 AutoSmoke 执行时能采集哪些业务状态，例如：

```text
活动是否开启
当前阶段
当前轮次
当前主题
玩家本轮积分
目标积分道具数量
奖励领取状态
排行状态
邮件状态
当前 UI 页面
当前弹窗
```

### 13.2 格式

```json
{
  "schema_version": "business_state_contract.v1",
  "feature_id": "feature-17751c8a",
  "state_domains": [
    {
      "domain": "activity.armrace",
      "collector": "activity_state_exporter",
      "required": true,
      "paths": [
        {
          "path": "activity.armrace.enabled",
          "type": "boolean",
          "source": "server_state",
          "stability": "stable",
          "usage": [
            "precondition",
            "state_assertion"
          ]
        },
        {
          "path": "activity.armrace.current_stage",
          "type": "number",
          "source": "server_state",
          "stability": "time_sensitive",
          "usage": [
            "precondition",
            "state_assertion"
          ]
        },
        {
          "path": "activity.armrace.round_score",
          "type": "number",
          "source": "server_state",
          "stability": "dynamic",
          "usage": [
            "before_after_diff",
            "score_assertion"
          ]
        },
        {
          "path": "activity.armrace.reward_claim_state",
          "type": "object",
          "source": "server_state",
          "stability": "dynamic",
          "usage": [
            "reward_assertion"
          ]
        }
      ]
    },
    {
      "domain": "ui.armrace",
      "collector": "ui_state_exporter",
      "required": true,
      "paths": [
        {
          "path": "ui.current_page",
          "type": "string",
          "source": "client_ui",
          "stability": "stable",
          "usage": [
            "page_assertion"
          ]
        },
        {
          "path": "ui.visible_dialog",
          "type": "string",
          "source": "client_ui",
          "stability": "stable",
          "usage": [
            "dialog_assertion"
          ]
        }
      ]
    }
  ]
}
```

### 13.3 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| `state_domains` | 建立状态采集范围 |
| `paths` | 校验断言引用是否合法 |
| `source` | 决定从客户端、服务端、DB、日志还是 UI 采集 |
| `stability` | 决定断言容忍和重试策略 |
| `usage` | 决定前置检查、前后快照、业务断言 |

---

## 14. business_assertions.v1.json

### 14.1 用途

声明用例执行后要验证的业务结果。

没有该文件时，AutoSmoke 只能验证 UI 层结果，例如“页面打开了”“弹窗显示了”。

有该文件后，AutoSmoke 可以验证：

```text
积分是否增加
奖励是否到账
奖励领取状态是否改变
邮件是否发放
排行是否变化
UI 显示是否与业务状态一致
```

### 14.2 格式

```json
{
  "schema_version": "business_assertions.v1",
  "feature_id": "feature-17751c8a",
  "assertions": [
    {
      "assertion_id": "BASSERT_ARMRACE_UI_001",
      "case_id": "ARMRACE_UI_001",
      "description": "进入军备竞赛主界面后，页面和核心状态显示正确。",
      "pre_checks": [
        {
          "type": "business_state",
          "state_path": "activity.armrace.enabled",
          "operator": "==",
          "expected": true
        }
      ],
      "checks": [
        {
          "type": "ui_state",
          "state_path": "ui.current_page",
          "operator": "==",
          "expected": "activity.armrace.main"
        },
        {
          "type": "business_state",
          "state_path": "activity.armrace.current_stage",
          "operator": "between",
          "expected": [
            1,
            7
          ]
        }
      ]
    },
    {
      "assertion_id": "BASSERT_ARMRACE_REWARD_001",
      "case_id": "ARMRACE_REWARD_001",
      "description": "领取积分奖励后，奖励状态变为已领取并且奖励到账。",
      "pre_checks": [
        {
          "type": "business_state",
          "state_path": "activity.armrace.round_score",
          "operator": ">=",
          "expected_from_asset": "VAL_ARMRACE_SCORE_REWARD_FIRST_THRESHOLD"
        }
      ],
      "checks": [
        {
          "type": "business_state",
          "state_path": "activity.armrace.reward_claim_state.score_reward_1",
          "operator": "==",
          "expected": "claimed"
        },
        {
          "type": "reward_received",
          "expected_from_asset": "VAL_ARMRACE_SCORE_REWARD_FIRST_REWARD"
        }
      ]
    }
  ]
}
```

### 14.3 断言类型建议

```text
ui_state
business_state
before_after_diff
config_match
reward_received
mail_received
ranking_changed
task_progress_changed
ui_business_consistency
```

### 14.4 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| `pre_checks` | 执行前检查 |
| `checks` | 执行后断言 |
| `state_path` | 对接状态采集契约 |
| `expected_from_asset` | 引用配置和值资产 |
| `case_id` | 绑定具体用例 |

---

## 15. optional_external_refs.v1.json

### 15.1 用途

声明外部依赖，例如：

```text
配置表导出
GM 指令
服务端状态查询接口
数据库查询
日志查询
邮件查询
多账号匹配池准备
```

### 15.2 格式

```json
{
  "schema_version": "optional_external_refs.v1",
  "feature_id": "feature-17751c8a",
  "refs": [
    {
      "ref_id": "EXT_ARMRACE_CONFIG",
      "ref_type": "config_table",
      "name": "H活动_军备竞赛配置",
      "required": true,
      "usage": [
        "config_match",
        "test_data_prepare",
        "business_assertion"
      ],
      "access_method": "config_export",
      "owner": "upstream_config"
    },
    {
      "ref_id": "EXT_ARMRACE_STATE_QUERY",
      "ref_type": "server_state_api",
      "name": "军备竞赛状态查询",
      "required": true,
      "usage": [
        "before_after_snapshot",
        "business_assertion"
      ],
      "access_method": "api_or_debug_bridge",
      "owner": "server"
    },
    {
      "ref_id": "EXT_GM_PREPARE",
      "ref_type": "gm_tool",
      "name": "活动和账号状态准备",
      "required": true,
      "usage": [
        "precondition_prepare"
      ],
      "access_method": "gm_command_or_prepared_account",
      "owner": "qa_ops"
    }
  ]
}
```

### 15.3 AutoSmoke 消费用途

| 内容 | AutoSmoke 用途 |
|---|---|
| `ref_type=config_table` | 配置校验 |
| `ref_type=gm_tool` | 前置状态准备 |
| `ref_type=server_state_api` | 业务状态采集 |
| `ref_type=db_query` | 数据库验证 |
| `ref_type=log_query` | 日志验证 |
| `required=true` | 缺失时阻断 |

---

## 16. 最小补充和完整补充

### 16.1 只做 UI 自动化的最小补充

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

能支持：

```text
进入页面
点击按钮
打开弹窗
关闭弹窗
返回页面
验证 UI 可见状态
输出基础执行报告
```

不能证明：

```text
积分真实变化
奖励真实到账
邮件真实发放
排行真实更新
配置规则真实生效
```

### 16.2 UI + 功能逻辑自动化的完整补充

```text
manifest.json
candidate_feature_flow.json
feature_flow_review_result.v1.json
manual_test_cases.v1.json
target_name_catalog.v1.json
page_flow_catalog.v1.json
test_data_profile.v1.json
value_assets.v1.json
source_trace.v1.json
review_items.v1.json
business_state_contract.v1.json
business_assertions.v1.json
optional_external_refs.v1.json
```

能支持：

```text
UI 自动化
业务状态采集
前后状态快照
配置值验证
奖励到账验证
邮件验证
排行验证
UI 与业务状态一致性验证
完整报告回溯
```

---

## 17. 针对军备竞赛建议优先补充的用例

建议上游第一批补充这些用例：

| 用例 ID | 用例标题 | 类型 | 优先级 |
|---|---|---|---|
| `ARMRACE_UI_001` | 从常规活动进入军备竞赛主界面 | UI 流程 | P0 |
| `ARMRACE_UI_002` | 打开规则 tips | UI 流程 | P1 |
| `ARMRACE_UI_003` | 打开主题说明 | UI 流程 | P1 |
| `ARMRACE_UI_004` | 打开查看更多任务弹窗 | UI 流程 | P1 |
| `ARMRACE_UI_005` | 返回上级界面 | UI 流程 | P1 |
| `ARMRACE_RULE_001` | 等级不足时不可参与 | 业务规则 | P0 |
| `ARMRACE_RULE_002` | 等级满足且活动开启时可进入 | 业务规则 | P0 |
| `ARMRACE_SCORE_001` | 完成任务后本轮积分增加 | 功能逻辑 | P0 |
| `ARMRACE_REWARD_001` | 达到积分阈值后领取积分奖励 | 奖励 | P0 |
| `ARMRACE_REWARD_002` | 达到目标积分后领取目标奖励 | 奖励 | P0 |
| `ARMRACE_SETTLE_001` | 每日结算后排行奖励邮件发放 | 结算 | P1 |
| `ARMRACE_BOUNDARY_001` | 0 积分玩家无排行奖励 | 边界 | P1 |

---

## 18. 最终结论

基于这次上游已提供的 `wiki_armrace_reviewable`，还需要补充的不是自动化脚本，而是 AutoSmoke 转换层需要的业务执行输入。

最关键的补充是：

```text
1. feature_flow_review_result.v1.json
   解决：候选规则未审核，不能生成正式用例

2. manual_test_cases.v1.json
   解决：只有功能规则，没有明确测试用例

3. target_name_catalog.v1.json
   解决：自然语言目标无法稳定匹配元素

4. page_flow_catalog.v1.json
   解决：页面入口、跳转、返回路径不明确

5. test_data_profile.v1.json
   解决：账号、活动、积分、奖励状态无法准备

6. business_state_contract.v1.json
   解决：不知道可采集哪些业务状态

7. business_assertions.v1.json
   解决：没有正式业务断言
```

这些补齐后，AutoSmoke 才能完成：

```text
上游业务输入
  → AutoSmoke 转换
  → 目标名匹配
  → semanticId/testId 候选生成
  → IDE 自动/人工确认
  → 自动化执行
  → UI + 业务断言报告
```
