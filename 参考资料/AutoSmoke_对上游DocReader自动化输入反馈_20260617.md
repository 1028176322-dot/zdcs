# AutoSmoke 对上游 DocReader 自动化输入反馈

> 日期：2026-06-17  
> 反馈方：AutoSmoke 自动化测试工具  
> 接收方：DocReader / Handoff / 上游文档资产生成工具  
> 目标：明确上游需要提供哪些信息，AutoSmoke 才能稳定、可信、可追踪地执行自动化测试。

---

## 1. 总体结论

结合当前 AutoSmoke 的实现方式，DocReader 当前定义的 `case_seed_package.v0` 可以作为“测试点候选 / 手工用例素材 / 评审辅助输入”，但不能直接作为 AutoSmoke 的可执行自动化输入。

AutoSmoke 当前执行链路需要的是：

```text
明确用例 → 显式步骤 → 动作类型 → 目标定位 → 执行顺序 → 断言 → 报告回溯
```

而 DocReader 当前主要提供的是：

```text
业务陈述 → 业务关系 → 来源追踪 → 值资产 → 待确认项
```

两者之间存在结构化断层。要让 AutoSmoke 完整执行自动化测试，上游必须在 `case_seed_package.v0` 之后，额外提供或通过转换器生成一个面向 AutoSmoke 的中间格式：

```text
auto_smoke_case_seed.v1
```

一句话边界：

> DocReader 负责把策划文档变成可信业务资产；AutoSmoke 负责执行自动化；中间必须有一层把业务资产转换成“可执行步骤、稳定定位、明确断言、环境前置和阻断规则”。

---

## 2. AutoSmoke 当前真正需要什么

当前 AutoSmoke 主要通过以下模块消费用例：

| 模块 | 当前职责 | 对输入的要求 |
|---|---|---|
| `用例层/case_step_parser.py` | 解析步骤文本 | 需要明确动作关键词和定位表达式 |
| `用例层/case_step_executor.py` | 顺序执行步骤 | 需要可定位目标、等待、断言、截图等可执行动作 |
| `用例层/batch_runner.py` | 批量执行用例 | 需要 `{case_id: [step_text, ...]}` 或等价结构 |
| `元数据/target_locator.py` | 定位目标 | 需要 `testId`、`poco`、`text`、`template` 或坐标 |
| `元数据/element_mapping.py` | 维护元素语义映射 | 需要页面、元素语义、testId、路径、可点击性 |

AutoSmoke 不是读取自然语言业务说明后自行脑补步骤的系统。它可以执行：

```text
点击 testId("maincity.garrison.button")
等待 1 秒
断言存在 testId("maincity.garrison.panel")
截图
```

但不能稳定执行：

```text
驻防按钮显示驻防人数信息
```

后者必须先被转换为可执行步骤。

---

## 3. 当前结构化断层

| 信息维度 | DocReader 当前 v0 | AutoSmoke 需要 | 结论 |
|---|---|---|---|
| 功能块名称 | 可提供 `block_name` | 可作为模块/标题 | 可复用 |
| 业务陈述 | 可提供 `statement` | 不能直接执行 | 必须转换 |
| 来源追踪 | 可提供 `source_refs` | 可进入报告 | 可复用 |
| 准入状态 | 可提供 `admission` | 影响是否执行 | 可复用 |
| 动作类型 | 通常没有 | 必须有 `click/wait/assert` | P0 缺口 |
| 执行顺序 | 通常没有 | 必须有 `step_order` | P0 缺口 |
| UI 目标 | 可能隐含在语句中 | 必须显式 target | P0 缺口 |
| UI locator | 不提供 | 必须能定位 | P0/P1 缺口 |
| 断言类型 | 不稳定 | 必须明确 | P1 缺口 |
| 环境前置 | 部分可推断 | 自动化强依赖 | P1 缺口 |
| 配置实际值 | 通常只有来源 | 需要具体值或阻断 | P1/P2 缺口 |
| 文案 KEY | 可能提供 KEY | 需要最终显示文案 | P1/P2 缺口 |
| 清理动作 | 通常没有 | 长跑自动化需要 | P2 缺口 |

---

## 4. P0 必须字段：缺失则不能自动化执行

以下字段是 AutoSmoke 自动化执行的硬门槛。缺失时，AutoSmoke 只能生成待评审项或阻断项，不能可靠运行。

| 字段 | 说明 | 推荐来源 |
|---|---|---|
| `case_id` | 用例唯一 ID，用于执行、报告、回放和失败定位 | DocReader 或转换器生成 |
| `steps` | 显式步骤列表 | 转换器生成 |
| `step_order` | 步骤顺序 | DocReader 业务流或转换器排序 |
| `action_type` | 动作类型，如 `click/wait/assert_exists` | 转换器从业务语句推断，复杂场景人工确认 |
| `target.type` | 定位类型，如 `testId/text/template/content` | element mapping 或转换器补齐 |
| `target.value` | 定位值，如 `maincity.garrison.button` | element mapping / UI 元数据 |
| `admission.automation_script_generation` | 是否允许执行自动化 | DocReader + 转换器联合判断 |
| `blocked_reasons` | 阻断原因 | DocReader / 转换器生成 |

### 4.1 AutoSmoke 当前支持的动作类型

| 中文步骤 | 内部动作 | 是否需要 target |
|---|---|---|
| 点击 | `click` | 是 |
| 等待 | `wait` | 否，需要 seconds |
| 断言存在 | `assert_exists` | 是 |
| 断言不存在 | `assert_not_exists` | 是 |
| 截图 | `screenshot` | 否 |
| 返回 | `back` | 否 |
| 长按 | `long_press` | 是 |
| 滑动 | `swipe` | 需要 start/end |
| 输入 | `input` | 建议提供 target 和 value |

### 4.2 AutoSmoke 当前支持的定位类型

| 定位类型 | 示例 | 稳定性 | 说明 |
|---|---|---|---|
| `testId` | `testId("maincity.garrison.button")` | 最高 | 推荐主路径，依赖 UI 元数据/元素映射 |
| `poco` | `poco("MainCityUI/GarrisonButton")` | 高 | 依赖 Poco/UI 树路径 |
| `text` | `text("驻防")` | 中 | 依赖 OCR 或文字可见性 |
| `template` | `template("garrison_button")` | 中 | 依赖模板图片 |
| `normalized` | `normalized(0.5,0.95)` | 低 | 分辨率变化有风险 |
| `design` | `design(585,2400)` | 低 | 依赖设计分辨率 |
| `content` | `content(160,665)` | 低 | GameContent 内坐标 |
| `pixel` | `pixel(100,200)` | 最低 | 屏幕像素，最易漂移 |

推荐优先级：

```text
testId > poco > text/template > normalized/design/content > pixel
```

---

## 5. P1 强烈建议字段：缺失会导致降级或高误判

| 字段 | 说明 | 缺失影响 |
|---|---|---|
| `feature_name` | 功能归属 | 报告和批量管理不清晰 |
| `title` | 用例标题 | 人工评审困难 |
| `page_id` | 页面归属 | 同名元素容易误匹配 |
| `scene_id` | 场景归属 | 跨场景定位风险高 |
| `preconditions` | 执行前置条件 | 可能从错误状态开始执行 |
| `expected` | 步骤预期结果 | 点击后无法判断是否成功 |
| `assertions` | 断言列表 | 只能验证“点了”，不能验证“对了” |
| `timeout_ms` | 等待超时 | 慢加载场景不稳定 |
| `on_failure` | 失败策略 | 无法决定停止、重试或继续 |
| `source_refs` | 来源追踪 | 报告无法回溯原始文档 |
| `element_mapping_hints` | 元素映射线索 | 无法快速补齐 locator |

---

## 6. P2 增强字段：用于提高长期稳定性

| 字段 | 说明 |
|---|---|
| `data_dependencies` | 账号、资源、道具、等级、活动状态等依赖 |
| `config_dependencies` | 配置表来源、key、期望值 |
| `text_key_dependencies` | 文案 KEY 到最终显示文本的映射 |
| `cleanup_steps` | 用例执行后的还原动作 |
| `retry_policy` | 重试次数、间隔、可重试错误 |
| `review_required` | 是否需要人工评审 |
| `risk_level` | 风险等级，如坐标定位、OCR 断言、配置缺失 |
| `tags` | 冒烟、回归、主流程、付费、活动等标签 |

---

## 7. 推荐上游交付格式：auto_smoke_case_seed.v1

建议上游或转换器输出以下结构。

```json
{
  "schema_version": "auto_smoke_case_seed.v1",
  "generated_from": "case_seed_package.v0",
  "doc_source": "策划文档名称_v1.2",
  "feature_name": "主城驻防",
  "admission": {
    "manual_case_generation": "PASS_WITH_GAP",
    "automation_script_generation": "PASS",
    "blocked_reasons": []
  },
  "test_cases": [
    {
      "case_id": "TC_GARRISON_001",
      "title": "驻防按钮可打开驻防面板",
      "priority": "P0",
      "preconditions": [
        {
          "type": "page_visible",
          "page_id": "maincity_page",
          "description": "玩家当前位于主城界面"
        }
      ],
      "steps": [
        {
          "step_order": 1,
          "action_type": "click",
          "target": {
            "type": "testId",
            "value": "maincity.garrison.button",
            "fallback": [
              {
                "type": "text",
                "value": "驻防"
              }
            ]
          },
          "expected": {
            "type": "element_visible",
            "target": {
              "type": "testId",
              "value": "maincity.garrison.panel"
            },
            "description": "驻防面板打开"
          },
          "timeout_ms": 5000,
          "on_failure": "stop",
          "source_refs": [
            {
              "evidence_ref": "EVD_0051",
              "sheet_name": "规则",
              "row_number": 51,
              "source_excerpt": "驻防按钮: 当前驻防人数/可驻防上限"
            }
          ]
        },
        {
          "step_order": 2,
          "action_type": "wait",
          "seconds": 1
        },
        {
          "step_order": 3,
          "action_type": "assert_exists",
          "target": {
            "type": "testId",
            "value": "maincity.garrison.panel"
          },
          "timeout_ms": 5000,
          "on_failure": "stop"
        },
        {
          "step_order": 4,
          "action_type": "screenshot",
          "description": "验证完成后截图留痕"
        }
      ],
      "assertions": [
        {
          "assertion_type": "ui_display_assertion",
          "raw_expression": "当前驻防人数/可驻防上限",
          "expected_format": "数字/数字",
          "target": {
            "type": "testId",
            "value": "maincity.garrison.button"
          }
        }
      ],
      "source_refs": [
        {
          "evidence_ref": "EVD_0051",
          "sheet_name": "规则",
          "row_number": 51,
          "source_excerpt": "驻防按钮: 当前驻防人数/可驻防上限"
        }
      ]
    }
  ],
  "element_mapping_hints": [
    {
      "hint_name": "驻防按钮",
      "candidate_test_id": "maincity.garrison.button",
      "candidate_poco_path": "MainCityUI/GarrisonPanel/GarrisonButton",
      "page_id": "maincity_page",
      "element_type": "Button",
      "role": "action",
      "clickable": true,
      "meaning": "点击打开驻防面板"
    }
  ],
  "external_requirements": []
}
```

---

## 8. AutoSmoke 可直接消费的最小格式

如果第一阶段只追求“能跑起来”，可以先给 AutoSmoke 最小步骤字典。

```json
{
  "schema_version": "auto_smoke_case_seed.v1",
  "feature_name": "主城驻防",
  "test_cases": [
    {
      "case_id": "TC_GARRISON_001",
      "title": "驻防按钮可打开驻防面板",
      "admission": "PASS",
      "steps": [
        "点击 testId(\"maincity.garrison.button\")",
        "等待 1 秒",
        "断言存在 testId(\"maincity.garrison.panel\")",
        "截图"
      ],
      "source_refs": [
        {
          "evidence_ref": "EVD_0051",
          "sheet_name": "规则",
          "row_number": 51
        }
      ]
    }
  ]
}
```

AutoSmoke 可转换为内部执行结构：

```python
{
  "TC_GARRISON_001": [
    "点击 testId(\"maincity.garrison.button\")",
    "等待 1 秒",
    "断言存在 testId(\"maincity.garrison.panel\")",
    "截图"
  ]
}
```

---

## 9. 业务陈述到步骤的转换要求

DocReader 输出的 `statement` 不能直接作为 AutoSmoke 步骤。必须经过转换规则。

| 业务陈述特征 | 建议转换动作 | 示例步骤 |
|---|---|---|
| “点击/打开/确认” + 按钮 | `click` | `点击 testId("xxx.button")` |
| “显示/展示” + 文本/格式 | `assert_exists` 或 UI 断言 | `断言存在 text("驻防")` |
| “弹窗出现/面板打开” | `wait` + `assert_exists` | `断言存在 testId("xxx.panel")` |
| “输入/填写” | `input` | `输入 "abc" 到 testId("xxx.input")` |
| “选择/切换” | `click` | `点击 testId("xxx.option")` |
| “等待 N 秒” | `wait` | `等待 3 秒` |
| “返回/关闭” | `back` 或 `click close_button` | `点击 testId("common.close")` |
| “数量/公式/数值” | `numeric_assertion` | 需要配置值或状态接口 |

示例：

| DocReader statement | AutoSmoke 步骤 |
|---|---|
| 驻防按钮显示驻防人数信息 | `断言存在 testId("maincity.garrison.button")` + UI 格式断言 |
| 点击驻防按钮打开驻防面板 | `点击 testId("maincity.garrison.button")` + `断言存在 testId("maincity.garrison.panel")` |
| 行军时间大于 X 时弹窗提示 | 需要 `X` 的配置来源和值，再生成点击和断言 |
| 奖励到账后显示领取成功 | 需要触发步骤 + 状态/接口/UI 断言 |

---

## 10. 阻断规则建议

上游在输出时应明确哪些情况需要阻断，而不是让 AutoSmoke 猜测。

| 状态 | AutoSmoke 建议处理 |
|---|---|
| `PASS` | 可直接进入自动化执行 |
| `PASS_WITH_GAP` | 可进入执行候选，但必须标记风险；缺少 P0 字段时仍阻断 |
| `BLOCKED` | 不执行，仅生成缺口清单 |
| `locator_required` | 阻断自动化执行，进入元素映射补齐 |
| `config_required` | 如果影响断言或流程分支，则阻断 |
| `text_key_required` | 如果依赖 OCR/text 断言，则阻断 |
| `environment_required` | 如果无法保证前置状态，则阻断 |
| `uncertain` | 不进入确定断言，只能进入人工评审 |
| `conflict` | 必须人工评审 |
| `missing` | 输出缺失清单 |

---

## 11. 对上游的具体反馈问题

请上游确认以下问题：

1. 是否接受在 `case_seed_package.v0` 之后新增 `auto_smoke_case_seed.v1`？
2. 是否能输出显式步骤序列，而不仅是业务陈述？
3. `action_type` 是否由 DocReader 生成，还是由 AutoSmoke 转换器生成？
4. `step_order` 是否能按文档业务流程稳定输出？
5. `target_name` 是否能稳定抽取，例如“驻防按钮”“驻防面板”“确认按钮”？
6. 上游是否能提供 `candidate_test_id` 或 `candidate_poco_path`？
7. 如果不能提供 locator，是否允许输出 `locator_required` 并阻断自动化？
8. 配置表实际值由谁查询？
9. 文案 KEY 到最终文案由谁映射？
10. 环境前置条件由谁提供，例如账号等级、资源、活动状态、入口页面？
11. 断言类型是否能明确区分 UI 文本、UI 格式、数值、状态、接口、日志或 DB？
12. 每条步骤或用例是否都必须带 `source_refs`？
13. 失败时是否能返回结构化缺口，如缺 locator、缺配置、缺文案、缺环境？

---

## 12. 验收标准

首次对接可以按以下标准验收。

| 验收项 | 通过标准 |
|---|---|
| AutoSmoke 能读取输入 | JSON 结构合法，schema_version 可识别 |
| 能生成执行步骤 | 每条用例至少有一组有序步骤 |
| 动作可解析 | 所有步骤 action_type 属于 AutoSmoke 支持枚举 |
| 目标可定位 | P0 步骤具备 `testId/poco/text/template/坐标` 之一 |
| 阻断可识别 | `BLOCKED` 或缺 P0 字段时不会误执行 |
| 来源可回溯 | 用例或步骤能回显 `source_refs` |
| 缺口可反馈 | 缺字段时返回结构化错误，而不是静默失败 |
| 报告可读 | 执行报告能展示 case_id、步骤、结果、截图和失败原因 |

---

## 13. 建议实施路径

### 阶段 1：字段对齐

产出：

```text
auto_smoke_case_seed.v1.schema.json
```

目标：

- 明确必需字段。
- 明确 action_type 枚举。
- 明确 target.type 枚举。
- 明确阻断规则。

### 阶段 2：转换器

产出：

```text
doc_reader_to_auto_smoke.py
```

职责：

- 将 `business_items` 转为 `test_cases`。
- 将 `statement` 转为显式步骤。
- 将 `source_refs` 绑定到用例或步骤。
- 将缺失 locator/config/text_key/environment 输出为 `external_requirements`。

### 阶段 3：AutoSmoke 导入器

产出：

```text
/api/case/import_from_case_seed
```

职责：

- 读取 `auto_smoke_case_seed.v1`。
- 校验 P0 字段。
- 转换为 `BatchRunner.run_steps_dict()` 可消费格式。
- 对 `BLOCKED` 用例只展示缺口，不执行。

### 阶段 4：真实样例试跑

输入：

```text
1 份真实策划文档
1 份 case_seed_package.v0
1 份 auto_smoke_case_seed.v1
```

输出：

```text
执行报告
失败步骤清单
缺口字段清单
locator 补齐清单
schema 修订建议
```

---

## 14. 最终反馈结论

AutoSmoke 要想“完美进行自动化测试”，上游至少需要提供：

1. 可执行用例 ID。
2. 有序步骤序列。
3. 每步明确动作类型。
4. 每步明确目标定位。
5. 每步或用例明确预期结果和断言。
6. 页面、场景、环境前置条件。
7. 配置值、文案值、账号状态等外部依赖的解析结果或阻断标记。
8. 来源追踪。
9. 自动化准入状态。
10. 结构化缺口反馈。

如果上游只能提供 `case_seed_package.v0`，AutoSmoke 可以辅助生成测试点和待评审用例，但不能承诺稳定自动化执行。

如果上游能提供 `auto_smoke_case_seed.v1`，AutoSmoke 可以进入自动化执行、报告回溯、失败分析和持续迭代闭环。

