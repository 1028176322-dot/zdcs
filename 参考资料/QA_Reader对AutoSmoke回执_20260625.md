# QA_Reader 对 AutoSmoke 回执的客观回复

日期：2026-06-25

对象：AutoSmoke 对 `wiki_armrace_reviewable` 的下游消费反馈

## 1. 结论先行

收到 AutoSmoke 对 `wiki_armrace_reviewable` 的回执。

经拆解，本次反馈的核心不是要求 QA_Reader 提供自动化脚本、locator、testId、semanticId 或执行报告，而是指出当前 `wiki_armrace_reviewable` 仍处于候选/待审核状态，不能直接进入 AutoSmoke 自动执行链路。

AutoSmoke 需要补充的是面向转换层的结构化业务执行输入，包括审核结论、用例意图、目标名、页面路径、测试数据、状态采集、业务断言和阻断项。

该方向整体合理，但不能直接把回执中的全部文件清单视为无条件硬需求。应按自动化范围分级处理，并通过 QA_Reader 工具链固化生成与校验规则。

## 2. 当前状态确认

当前 `wiki_armrace_reviewable` 已提供：

```text
ai_prompt.txt
candidate_feature_flow.json
render_audit.json
review_pack.md
source_index.json
source_materialized.md
validation_report.json
```

这些文件可以作为 AutoSmoke 的业务理解输入，但不能直接作为自动执行输入。

主要原因：

```text
candidate_feature_flow.status = REVIEW_REQUIRED
FLOW-MAIN-BEHAVIOR.ready_for_case_generation = false
validation_report.status = STRUCTURAL_PASS_REVIEW_REQUIRED
```

因此，当前包不能直接生成正式自动化用例，也不能直接进入执行。

## 3. 职责边界确认

QA_Reader 不应提供以下内容：

```text
AutoSmoke 执行脚本
Unity / Playwright 操作代码
最终 locator
最终 testId
最终 semanticId
element_mapping_formal.json
mapping_evidence.json
自动化执行报告
```

这些属于 AutoSmoke 转换层、元素绑定层和执行层职责。

QA_Reader 可以补充的是：

```text
已审核的功能流结论
明确的测试用例意图
稳定目标名
页面入口、跳转、返回、恢复路径
测试账号和前置状态
配置值、奖励值、阈值等结构化资产
业务状态采集需求
业务断言意图
外部依赖
无法自动化或待确认事项
来源追踪
```

## 4. 对 AutoSmoke 需求的分级判断

不建议一次性把 AutoSmoke 列出的所有文件都视为硬性必需。

建议拆成两档。

### 4.1 UI 自动化最小可消费包

如果第一阶段只支持 UI 自动化，建议优先补充：

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

该档可以支持：

```text
进入页面
点击按钮
打开弹窗
关闭弹窗
返回页面
验证 UI 可见状态
输出基础执行报告
```

但不能证明：

```text
积分真实变化
奖励真实到账
邮件真实发放
排行真实更新
配置规则真实生效
```

### 4.2 UI + 业务逻辑自动化完整包

如果目标是 UI + 功能逻辑自动化，则需要在最小包基础上继续补充：

```text
value_assets.v1.json
business_state_contract.v1.json
business_assertions.v1.json
optional_external_refs.v1.json
```

该档可以支持：

```text
业务状态采集
前后状态快照
配置值验证
奖励到账验证
邮件验证
排行验证
UI 与业务状态一致性验证
完整报告回溯
```

## 5. 需要避免的处理方式

不建议直接手工补齐一批 JSON 文件作为闭环。

原因：

```text
1. candidate_feature_flow.json 当前仍是候选理解，不是已确认事实源。
2. review_pack.md 只供人工审核，不能作为下游机器输入。
3. manual_test_cases.v1.json 不能脱离已审核功能流手写，否则会破坏来源追踪。
4. business_assertions.v1.json 必须和可采集状态契约匹配，否则只是不可执行断言。
5. optional_external_refs.v1.json 涉及 GM、配置、服务端接口、日志等能力，需要 AutoSmoke 或环境侧确认真实可用性。
```

因此，回执里的格式可以作为契约设计参考，但不能直接等同于 QA_Reader 已支持的产物格式。

## 6. 建议下一步

建议按以下顺序推进：

```text
1. 确认第一阶段目标：只做 UI 自动化，还是 UI + 业务逻辑自动化。
2. 先定义 AutoSmoke handoff 包的 schema。
3. 固化从 approved_feature_flow.json 到 handoff 包的生成规则。
4. 增加 handoff 包校验规则。
5. 明确 REVIEW_REQUIRED、REFERENCE_ONLY、BLOCKED 等状态如何阻断或降级。
6. 重新生成 wiki_armrace_reviewable 对应的 handoff 包。
7. 用校验结果确认该包是否可交付给 AutoSmoke。
```

## 7. 当前回复结论

AutoSmoke 的反馈方向基本合理，指出了当前 `wiki_armrace_reviewable` 不能直接进入自动执行的问题。

但它提出的是新的上游交付契约，不代表 QA_Reader 当前已经完成支持。

QA_Reader 侧的合理处理方式不是手工补文件，而是将交付包 schema、生成规则、校验规则和分级准入标准固化到工具链中。只有完成工具链改造、重新生成并通过校验后，才能认为该反馈被真正处理。
