# AutoSmoke 自动生成映射字段存储流转补充方案

> 日期：2026-06-17  
> 适用范围：目标映射工作台、手动补充、自动生成 semanticId/testId/role/pageId、正式映射、证据闭环  
> 目标：明确自动生成的 `semanticId / testId / role / pageId` 保存在哪里、何时升级、谁读取、如何回溯证据。

---

## 1. 核心结论

自动生成的映射字段不要只保存一份，也不要一生成就进入正式执行。

推荐分三层保存：

```text
1. 草稿/任务层：mapping_task_queue.json + element_mapping_draft.json
2. 正式映射层：element_mapping_formal.json
3. 证据层：mapping_evidence.json
```

字段流转：

```text
自动生成 / 手动补充
  → 保存为草稿
  → 运行态匹配
  → 高亮确认
  → 点击验证
  → 用例回放
  → 写入正式映射
  → 保存证据
```

一句话：

```text
草稿负责可编辑，正式映射负责可执行，证据负责可信。
```

---

## 2. 文件分层

### 2.1 草稿/任务层

保存位置：

```text
E:/zdcs/AutoSmoke/metadata/mapping_task_queue.json
E:/zdcs/AutoSmoke/元数据/element_mapping_draft.json
```

职责：

1. 保存目标驱动的映射任务。
2. 保存自动生成或手动补充的候选字段。
3. 允许编辑、替换候选、拒绝、忽略。
4. 不能直接视为正式执行数据。

保存字段：

```text
target_name
semanticId
testId
role
pageId
elementType
locator
candidate_elements
reviewStatus
verify_status
source
source_ref
```

### 2.2 正式映射层

保存位置：

```text
E:/zdcs/AutoSmoke/metadata/element_mapping_formal.json
```

职责：

1. 保存已经确认可执行的映射。
2. 提供给执行器、target locator、报告系统读取。
3. 作为正式自动化资产。

写入条件：

```text
visual_confirmed
click_confirmed
case_verified
manual_confirmed
```

点击目标建议至少：

```text
click_confirmed 或 case_verified 或 manual_confirmed
```

页面/状态断言目标建议至少：

```text
visual_confirmed 或 case_verified 或 manual_confirmed
```

### 2.3 证据层

保存位置：

```text
E:/zdcs/AutoSmoke/metadata/mapping_evidence.json
```

职责：

1. 保存为什么这个映射可信。
2. 保存结构证据、代码证据、运行态证据、行为证据。
3. 支撑版本重验和问题回溯。

证据包括：

```text
structure evidence
code semantics evidence
runtime match evidence
highlight image
click result
case replay result
review operator
review time
```

---

## 3. 字段生命周期

### 3.1 自动生成阶段

触发来源：

```text
从手工用例抽目标
从 target_name_catalog 生成
从 enhanced_ui_tree 生成草稿
手动补充表单
运行态发现
```

状态：

```text
auto_generated
manual_added
runtime_discovered
```

保存到：

```text
mapping_task_queue.json
element_mapping_draft.json
```

示例：

```json
{
  "task_id": "MAP_TASK_DAY1_CLAIM",
  "target_name": "第1天奖励领取按钮",
  "semanticId": "login_gift.day1.claim_button",
  "testId": "activity.login_gift.day1.claim.button",
  "role": "claim",
  "pageId": "login_gift",
  "elementType": "Button",
  "source": "manual_added",
  "reviewStatus": "manual_added",
  "verify_status": "pending",
  "required_by_cases": ["DL_REWARD_001"]
}
```

### 3.2 候选匹配阶段

AutoSmoke 根据 UI 元数据、代码语义、运行态 UI 生成候选。

状态：

```text
candidate_matched
runtime_matched
multi_candidate
no_candidate
```

保存到：

```text
mapping_task_queue.json
```

示例：

```json
{
  "task_id": "MAP_TASK_DAY1_CLAIM",
  "candidate_elements": [
    {
      "path": "LoginGiftPanel/Day1/BtnClaim",
      "suggestedTestId": "activity.login_gift.day1.claim.button",
      "match_score": 0.91,
      "match_reasons": [
        "target_alias_match",
        "page_match",
        "clickable",
        "code_method_claim_reward",
        "runtime_visible"
      ],
      "risk_flags": []
    }
  ],
  "reviewStatus": "runtime_matched"
}
```

### 3.3 视觉确认阶段

AutoSmoke 生成高亮截图，人工确认位置正确。

状态：

```text
visual_confirmed
```

保存到：

```text
element_mapping_draft.json
mapping_evidence.json
```

证据：

```json
{
  "visual": {
    "highlightImage": "screenshots/mapping_review/day1_claim_highlight.png",
    "confirmed": true,
    "confirmedBy": "user",
    "confirmedAt": "2026-06-17T12:00:00+08:00"
  }
}
```

### 3.4 点击验证阶段

对可点击目标执行测试点击。

状态：

```text
click_confirmed
click_failed
```

保存到：

```text
element_mapping_draft.json
mapping_evidence.json
```

证据：

```json
{
  "click": {
    "result": "PASS",
    "clickMode": "unity_inject",
    "afterState": "login_gift.main_panel_visible",
    "confirmedAt": "2026-06-17T12:05:00+08:00"
  }
}
```

### 3.5 用例回放阶段

真实用例通过后，映射升级为业务级可信。

状态：

```text
case_verified
```

保存到：

```text
element_mapping_formal.json
mapping_evidence.json
```

证据：

```json
{
  "caseReplay": {
    "caseId": "DL_REWARD_001",
    "result": "PASS",
    "reportPath": "reports/login_gift_smoke/batch_report.json",
    "verifiedAt": "2026-06-17T12:10:00+08:00"
  }
}
```

---

## 4. 文件结构定义

### 4.1 mapping_task_queue.json

用途：

```text
目标驱动的映射任务队列。
```

结构：

```json
{
  "schema_version": "mapping_task_queue.v1",
  "feature_name": "登录好礼七日签到",
  "generated_at": "2026-06-17T12:00:00+08:00",
  "tasks": [
    {
      "task_id": "MAP_TASK_LOGIN_GIFT_ENTRY",
      "target_name": "右上角登录好礼入口图标",
      "semanticId": "login_gift.entry_button",
      "testId": "activity.login_gift.entry.button",
      "role": "entry",
      "pageId": "main_city",
      "elementType": "Button",
      "required_by_cases": ["DL_RK_003"],
      "source": "auto_generated",
      "source_refs": ["登录好礼七日签到!R25"],
      "candidate_elements": [],
      "reviewStatus": "pending",
      "verify_status": "pending",
      "risk_flags": []
    }
  ]
}
```

### 4.2 element_mapping_draft.json

用途：

```text
保存草稿候选，可编辑、可拒绝、可验证。
```

结构：

```json
{
  "schema_version": "element_mapping_draft.v1",
  "feature_name": "登录好礼七日签到",
  "drafts": [
    {
      "path": "LoginGiftPanel/Day1/BtnClaim",
      "targetName": "第1天奖励领取按钮",
      "semanticId": "login_gift.day1.claim_button",
      "testId": "activity.login_gift.day1.claim.button",
      "displayName": "第1天奖励领取按钮",
      "pageId": "login_gift",
      "role": "claim",
      "elementType": "Button",
      "clickable": true,
      "locator": {
        "type": "runtimePath",
        "value": "LoginGiftPanel/Day1/BtnClaim"
      },
      "source": "manual_added",
      "reviewStatus": "visual_confirmed",
      "verify_status": "highlight_confirmed",
      "confidence": 0.93
    }
  ]
}
```

### 4.3 element_mapping_formal.json

用途：

```text
正式执行映射，执行器优先读取。
```

结构：

```json
{
  "schema_version": "element_mapping_formal.v1",
  "feature_name": "登录好礼七日签到",
  "exported_at": "2026-06-17T12:20:00+08:00",
  "mappings": {
    "activity.login_gift.day1.claim.button": {
      "testId": "activity.login_gift.day1.claim.button",
      "semanticId": "login_gift.day1.claim_button",
      "targetName": "第1天奖励领取按钮",
      "displayName": "第1天奖励领取按钮",
      "pageId": "login_gift",
      "role": "claim",
      "elementType": "Button",
      "locator": {
        "type": "runtimePath",
        "value": "LoginGiftPanel/Day1/BtnClaim"
      },
      "fallbackLocators": [
        {
          "type": "text",
          "value": "领取"
        }
      ],
      "reviewStatus": "click_confirmed",
      "source": "manual_added",
      "evidenceRef": "EVIDENCE_activity.login_gift.day1.claim.button"
    }
  }
}
```

### 4.4 mapping_evidence.json

用途：

```text
保存映射可信证据。
```

结构：

```json
{
  "schema_version": "mapping_evidence.v1",
  "feature_name": "登录好礼七日签到",
  "evidence": {
    "EVIDENCE_activity.login_gift.day1.claim.button": {
      "testId": "activity.login_gift.day1.claim.button",
      "semanticId": "login_gift.day1.claim_button",
      "targetName": "第1天奖励领取按钮",
      "structure": {
        "path": "LoginGiftPanel/Day1/BtnClaim",
        "pageId": "login_gift",
        "elementType": "Button"
      },
      "codeSemantics": {
        "matched": true,
        "ownerClass": "LoginGiftPanel",
        "boundMethod": "OnClickClaimReward",
        "businessKeywords": ["Claim", "Reward"]
      },
      "runtime": {
        "matched": true,
        "screenRect": [100, 200, 300, 260],
        "matchScore": 0.91
      },
      "visual": {
        "highlightImage": "screenshots/mapping_review/day1_claim_highlight.png",
        "confirmed": true
      },
      "click": {
        "confirmed": true,
        "result": "PASS"
      },
      "caseReplay": {
        "caseId": "DL_REWARD_001",
        "result": "PASS"
      }
    }
  }
}
```

---

## 5. 读写优先级

### 5.1 执行器读取优先级

执行时读取顺序：

```text
1. element_mapping_formal.json
2. 当前兼容的 element_mapping.json
3. element_mapping_draft.json 中明确 manual_confirmed/click_confirmed 的项
4. fallback locator，例如 text/template/坐标
```

原则：

```text
正式执行优先读 formal，不直接信任 draft。
```

### 5.2 IDE 审核读取优先级

审核时读取：

```text
1. mapping_task_queue.json
2. element_mapping_draft.json
3. runtime_match_result.json
4. mapping_evidence.json
5. element_mapping_formal.json
```

### 5.3 报告读取优先级

报告展示：

```text
1. case execution result
2. formal mapping
3. evidence
4. source_trace
5. draft/gap 信息
```

---

## 6. 状态与文件写入关系

| 状态 | 写入任务队列 | 写入草稿 | 写入正式映射 | 写入证据 |
|---|---:|---:|---:|---:|
| `auto_generated` | 是 | 可选 | 否 | 否 |
| `manual_added` | 是 | 是 | 否 | 否 |
| `runtime_matched` | 是 | 是 | 否 | 是 |
| `visual_confirmed` | 是 | 是 | 页面/状态目标可选 | 是 |
| `click_confirmed` | 是 | 是 | 是 | 是 |
| `case_verified` | 是 | 是 | 是 | 是 |
| `manual_confirmed` | 是 | 是 | 是 | 建议 |
| `rejected` | 是 | 是 | 否 | 可选 |
| `ignored` | 是 | 是 | 否 | 可选 |

---

## 7. 手动补充保存策略

手动补充时，用户填写：

```text
目标名
所属页面
元素类型
定位方式
定位值
```

IDE 自动生成：

```text
semanticId
testId
role
pageId
priority
```

保存按钮：

| 按钮 | 写入 |
|---|---|
| 保存草稿 | `mapping_task_queue.json` + `element_mapping_draft.json` |
| 保存并高亮 | 草稿 + `mapping_evidence.json.visual` |
| 保存并验证 | 草稿 + visual + click evidence |
| 加入正式映射 | `element_mapping_formal.json` + `mapping_evidence.json` |

手动补充不能绕过唯一性检查。

---

## 8. 唯一性检查保存点

以下动作前必须检查唯一性：

```text
保存草稿
保存并验证
加入正式映射
导出正式映射
执行前门禁
```

检查内容：

```text
同一个 testId 是否对应多个 path
同一个 testId 是否在同一 pageId 下对应多个元素
同一运行态是否出现多个可见命中
同一个 semanticId 是否映射到多个 testId
同一个 target_name 是否有多个 confirmed 候选
```

冲突处理：

```text
使用已有
替换已有
标记冲突
取消保存
进入人工评审
```

不建议自动生成：

```text
xxx_2
xxx_copy
button_1
```

除非用户明确确认该元素确实是独立业务对象。

---

## 9. 与现有 element_mapping.json 的兼容关系

当前项目已有 `element_mapping.json` / `element_mapping_formal.json` 的概念。补充方案不要求立刻废弃旧文件。

建议兼容期：

```text
1. 继续支持现有 element_mapping.json
2. 新闭环生成 element_mapping_formal.json
3. 执行器优先读 formal
4. 若 formal 不存在，回退旧 mapping
5. 稳定后再把旧 mapping 迁移到 formal
```

迁移步骤：

```text
旧 element_mapping.json
  → 按 reviewStatus 分类
  → confirmed 项进入 formal
  → pending 项进入 draft
  → rejected/ignored 保留在 draft/gap
  → 补 mapping_evidence
```

---

## 10. 最终落地建议

最终文件关系：

```text
草稿和任务：
E:/zdcs/AutoSmoke/metadata/mapping_task_queue.json
E:/zdcs/AutoSmoke/元数据/element_mapping_draft.json

正式映射：
E:/zdcs/AutoSmoke/metadata/element_mapping_formal.json

验证证据：
E:/zdcs/AutoSmoke/metadata/mapping_evidence.json
```

执行层只信任：

```text
element_mapping_formal.json
```

审核层主要处理：

```text
mapping_task_queue.json
element_mapping_draft.json
```

证据层回答：

```text
为什么这个 testId 可以被信任？
```

最重要的规则：

```text
自动生成的 semanticId/testId/role/pageId 先进入草稿。
只有经过验证或人工确认后，才进入正式映射。
所有正式映射都必须能追溯到证据。
```

