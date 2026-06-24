# AutoSmoke 自动执行框架定义

> 日期：2026-06-17  
> 目标：明确 AutoSmoke 从测试用例输入到自动执行、断言、报告、反馈闭环的完整框架。  
> 适用范围：DocReader 输出、Excel 手工用例、AutoSmoke IDE、自动化执行器、测试报告系统。

---

## 1. 框架总目标

AutoSmoke 自动执行框架的目标不是“读取自然语言后直接猜测点击”，而是建立一条稳定链路：

```text
测试用例资产
  → 自动化用例种子
  → 可执行步骤
  → 目标定位
  → 动作执行
  → 状态/界面断言
  → 报告与失败反馈
```

框架核心原则：

1. 所有自动执行必须基于显式步骤。
2. 所有点击目标必须可定位。
3. 所有预期结果必须转成可判断断言。
4. 所有环境前置必须可声明、可准备或可阻断。
5. 无法确认的信息不脑补，进入 `BLOCKED` 或人工评审。

---

## 2. 总体架构

```text
┌────────────────────────────────────────────┐
│  1. 上游输入层                              │
│  - DocReader case_seed_package.v0           │
│  - Excel 手工测试用例                        │
│  - 人工补充的 testId / semanticId 映射        │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│  2. 自动化转换层                            │
│  - 用例清洗                                 │
│  - 手工步骤 → 自动化步骤                     │
│  - semanticId → testId                      │
│  - 前置条件 → precondition_id               │
│  - 预期结果 → assertion                     │
│  - 缺口 → external_requirements / BLOCKED   │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│  3. 执行输入层                              │
│  - auto_smoke_case_seed.v1                  │
│  - 或 {case_id: [step_text, ...]}            │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│  4. 执行调度层                              │
│  - 批次调度                                 │
│  - 用例隔离                                 │
│  - 前置检查                                 │
│  - fail_fast / retry / stop_on_case_fail    │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│  5. 单步执行层                              │
│  - 解析步骤                                 │
│  - 定位目标                                 │
│  - 点击/等待/输入/返回/截图                  │
│  - 点击前校验                               │
│  - 点击后校验                               │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│  6. 断言验证层                              │
│  - UI 存在/不存在                           │
│  - 页面可见                                 │
│  - 文本/红点/按钮状态                       │
│  - 业务状态/接口/DB 扩展                     │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│  7. 报告反馈层                              │
│  - step_result                              │
│  - case_result                              │
│  - batch_report                             │
│  - screenshot                               │
│  - 缺口反馈                                 │
└────────────────────────────────────────────┘
```

---

## 3. 标准执行输入

AutoSmoke 标准执行输入建议统一为：

```text
auto_smoke_case_seed.v1
```

### 3.1 文件级结构

```json
{
  "schema_version": "auto_smoke_case_seed.v1",
  "feature_name": "登录好礼七日签到",
  "source_type": "excel/doc_reader/manual",
  "generated_at": "2026-06-17T00:00:00+08:00",
  "element_mapping_version": "element_mapping.v1",
  "test_cases": [],
  "precondition_registry": [],
  "external_requirements": []
}
```

### 3.2 用例级结构

```json
{
  "case_id": "DL_RK_003",
  "priority": "P1",
  "module": "功能入口",
  "submodule": "入口-点击跳转",
  "title": "点击登录好礼入口进入主界面",
  "admission": "PASS",
  "blocked_reasons": [],
  "start_page": "main_city",
  "precondition_id": "PRE_LOGIN_GIFT_UNLOCKED_RUNNING",
  "manual_steps": "1. 点击右上角活动入口图标",
  "manual_expected": "进入登录好礼主界面",
  "steps": [],
  "assertions": [],
  "cleanup_steps": [],
  "source_refs": []
}
```

### 3.3 步骤级结构

```json
{
  "step_order": 1,
  "action_type": "click",
  "target": {
    "type": "testId",
    "value": "activity.login_gift.entry"
  },
  "timeout_ms": 5000,
  "retry": {
    "count": 1,
    "interval_ms": 500
  },
  "on_failure": "stop",
  "description": "点击右上角登录好礼入口"
}
```

### 3.4 断言级结构

```json
{
  "assertion_type": "element_visible",
  "target": {
    "type": "testId",
    "value": "activity.login_gift.main_panel"
  },
  "expected": true,
  "timeout_ms": 5000,
  "description": "登录好礼主界面可见"
}
```

---

## 4. 最小可执行格式

为了兼容当前 AutoSmoke `BatchRunner.run_steps_dict()`，可以把标准结构降级成最小可执行格式：

```json
{
  "DL_RK_003": [
    "点击 testId(\"activity.login_gift.entry\")",
    "等待 1 秒",
    "断言存在 testId(\"activity.login_gift.main_panel\")",
    "截图"
  ]
}
```

这个格式可以直接进入当前执行器，但会损失：

1. 前置状态信息。
2. 用例标题和模块。
3. 结构化断言。
4. 外部依赖。
5. 清理动作。
6. 来源追踪。
7. 阻断原因。

因此推荐长期使用 `auto_smoke_case_seed.v1`，运行前再转换为 `run_steps_dict()`。

---

## 5. 动作模型

AutoSmoke 自动执行框架统一支持以下动作。

| action_type | 文本写法 | 说明 | 是否需要 target |
|---|---|---|---|
| `click` | `点击 testId("xxx")` | 点击目标 | 是 |
| `wait` | `等待 1 秒` | 固定等待 | 否 |
| `assert_exists` | `断言存在 testId("xxx")` | 判断目标存在 | 是 |
| `assert_not_exists` | `断言不存在 testId("xxx")` | 判断目标不存在 | 是 |
| `screenshot` | `截图` | 保存截图 | 否 |
| `back` | `返回` | 返回操作 | 否 |
| `long_press` | `长按 testId("xxx")` | 长按目标 | 是 |
| `swipe` | `滑动 normalized(0.5,0.8,0.5,0.2)` | 滑动操作 | 需要起止点 |
| `input` | `输入 "xxx" 到 testId("xxx")` | 输入文本 | 建议需要 target |

---

## 6. 定位模型

### 6.1 推荐定位优先级

```text
testId > poco > text > template > normalized > design > content > pixel
```

### 6.2 定位类型

| target.type | 示例 | 说明 | 推荐程度 |
|---|---|---|---|
| `testId` | `activity.login_gift.entry` | 由元素映射维护，最稳定 | 强推荐 |
| `poco` | `MainCityUI/LoginGiftEntry` | Poco/UI 树路径 | 推荐 |
| `text` | `登录好礼` | OCR 或可见文本 | 可兜底 |
| `template` | `login_gift_icon` | 模板图像 | 可兜底 |
| `normalized` | `0.5,0.95` | 归一化坐标 | 临时使用 |
| `design` | `585,2400` | 设计分辨率坐标 | 临时使用 |
| `content` | `160,665` | GameContent 内坐标 | 调试使用 |
| `pixel` | `100,200` | 屏幕像素坐标 | 不推荐 |

### 6.3 semanticId 处理策略

如果上游提供的是 `semanticId`，执行前必须转成 `testId`：

```json
{
  "semanticId": "登录好礼.入口按钮",
  "testId": "activity.login_gift.entry"
}
```

执行步骤中推荐只出现：

```text
点击 testId("activity.login_gift.entry")
```

不推荐直接执行：

```text
点击 semanticId("登录好礼.入口按钮")
```

除非 AutoSmoke 后续扩展 `semanticId` 解析器。

---

## 7. 前置状态框架

自动化执行不能只依赖自然语言前置条件。所有前置条件必须映射成 `precondition_id`。

### 7.1 前置状态结构

```json
{
  "precondition_id": "PRE_LOGIN_GIFT_DAY1_CLAIMABLE",
  "start_page": "main_city",
  "account_tag": "login_gift_day1_claimable",
  "state": {
    "lighthouse_level": 5,
    "sea_area_1_cleared": true,
    "activity_status": "running",
    "login_gift_day": 1,
    "reward_status": "claimable"
  },
  "setup_strategy": "prepared_account",
  "blocking_if_unavailable": true
}
```

### 7.2 推荐前置状态来源

| 来源 | 说明 |
|---|---|
| 准备好的测试账号 | 最稳定 |
| GM/测试接口 | 可动态设置状态 |
| 配置表/数据库 | 可校验状态 |
| 手工准备 | 可短期使用，但不可规模化 |

### 7.3 常见前置状态

| precondition_id | 说明 |
|---|---|
| `PRE_MAIN_CITY` | 玩家位于主城 |
| `PRE_LOGIN_GIFT_LOCKED` | 登录好礼未解锁 |
| `PRE_LOGIN_GIFT_UNLOCKED_RUNNING` | 活动已解锁且进行中 |
| `PRE_LOGIN_GIFT_DAY1_CLAIMABLE` | 第 1 天奖励可领取 |
| `PRE_LOGIN_GIFT_DAY1_CLAIMED` | 第 1 天奖励已领取 |
| `PRE_LOGIN_GIFT_DAY7_CLAIMABLE` | 第 7 天奖励可领取 |
| `PRE_LOGIN_GIFT_EXPIRED` | 活动已结束 |

---

## 8. 断言框架

### 8.1 断言类型

| assertion_type | 说明 | 示例 |
|---|---|---|
| `element_visible` | 元素可见 | 入口图标可见 |
| `element_not_exists` | 元素不存在 | 未解锁时入口不显示 |
| `page_visible` | 页面可见 | 登录好礼主界面打开 |
| `element_disabled` | 元素置灰/不可点击 | 明日奖励按钮不可领取 |
| `text_equals` | 文案一致 | 显示“已领取” |
| `red_dot_visible` | 红点显示 | 入口红点存在 |
| `red_dot_not_exists` | 红点消失 | 领取后红点消失 |
| `state_equals` | 业务状态一致 | reward_status = claimed |
| `numeric_equals` | 数值一致 | 奖励数量正确 |
| `server_state` | 服务端状态一致 | 奖励已发放 |
| `network_result` | 网络/协议结果 | 请求成功或失败提示 |

### 8.2 UI 断言示例

```json
{
  "assertion_type": "element_visible",
  "target": {
    "type": "testId",
    "value": "activity.login_gift.entry"
  },
  "expected": true
}
```

### 8.3 业务状态断言示例

```json
{
  "assertion_type": "state_equals",
  "state_path": "login_gift.day1.reward_status",
  "expected": "claimed",
  "data_source": "state_exporter_or_api"
}
```

如果当前没有业务状态采集能力，这类断言必须标记为：

```json
{
  "resolution_status": "state_query_required",
  "blocking": true
}
```

---

## 9. 准入与阻断状态机

### 9.1 用例准入状态

| admission | 含义 | 是否执行 |
|---|---|---|
| `PASS` | 字段完整，可自动执行 | 是 |
| `PASS_WITH_GAP` | 可执行但存在风险或降级 | 视策略 |
| `BLOCKED` | 缺少 P0 信息，不能执行 | 否 |
| `MANUAL_ONLY` | 只适合人工测试 | 否 |

### 9.2 阻断原因

| 阻断原因 | 说明 |
|---|---|
| `missing_action_type` | 缺少动作类型 |
| `missing_target` | 缺少目标 |
| `missing_locator` | 缺少可执行定位 |
| `missing_precondition` | 缺少前置状态 |
| `missing_assertion` | 缺少断言 |
| `config_required` | 需要配置表查询 |
| `text_key_required` | 需要文案映射 |
| `state_query_required` | 需要业务状态查询 |
| `environment_required` | 需要环境能力 |
| `manual_review_required` | 需要人工确认 |

### 9.3 执行状态

| 状态 | 说明 |
|---|---|
| `READY` | 已通过执行前校验 |
| `RUNNING` | 执行中 |
| `PASS` | 通过 |
| `FAIL` | 断言或步骤失败 |
| `BLOCKED` | 前置或定位阻断 |
| `ERROR` | 执行器异常 |
| `SKIPPED` | 因准入或依赖被跳过 |

---

## 10. 执行调度框架

### 10.1 批次执行

批次执行输入：

```json
{
  "batch_name": "login_gift_smoke_20260617",
  "click_mode": "unity_inject",
  "fail_fast_case": true,
  "stop_on_case_fail": false,
  "cases": []
}
```

### 10.2 推荐调度策略

| 策略 | 推荐值 | 说明 |
|---|---|---|
| `fail_fast_case` | `true` | 单个用例失败后停止该用例 |
| `stop_on_case_fail` | `false` | 一个用例失败不影响下一个 |
| `retry_count` | `1-2` | UI 加载可重试 |
| `timeout_ms` | `3000-8000` | 根据页面复杂度设置 |
| `click_mode` | `unity_inject` 或 `real_mouse` | 优先使用更稳定方式 |

### 10.3 执行顺序

```text
1. 读取 auto_smoke_case_seed.v1
2. 校验 schema
3. 过滤 BLOCKED / MANUAL_ONLY 用例
4. 检查前置状态
5. 转换为步骤文本或结构化步骤
6. 按 case_id 顺序执行
7. 每步执行前截图或读取状态
8. 定位目标
9. 执行动作
10. 执行断言
11. 失败时按策略 stop/retry/continue
12. 执行 cleanup
13. 写入报告
```

---

## 11. 报告框架

### 11.1 step_result

```json
{
  "case_id": "DL_RK_003",
  "step_order": 1,
  "raw": "点击 testId(\"activity.login_gift.entry\")",
  "action": "click",
  "target": {
    "type": "testId",
    "value": "activity.login_gift.entry"
  },
  "result": "PASS",
  "location": {
    "type": "game_content",
    "x": 960,
    "y": 120
  },
  "screenshot": "screenshots/xxx.png",
  "timestamp": "2026-06-17T12:00:00"
}
```

### 11.2 case_result

```json
{
  "case_id": "DL_RK_003",
  "result": "PASS",
  "total": 4,
  "passed": 4,
  "failed": 0,
  "blocked": 0,
  "steps": []
}
```

### 11.3 batch_report

```json
{
  "batch_name": "login_gift_smoke_20260617",
  "total_cases": 20,
  "passed_cases": 18,
  "failed_cases": 1,
  "blocked_cases": 1,
  "case_results": []
}
```

---

## 12. Excel 用例接入规范

如果继续使用 Excel 作为上游用例来源，建议列结构如下：

```text
优先级
CaseID
模块
子模块
用例标题
自动化准入
阻断原因
起始页面
前置状态ID
前置状态描述
操作步骤
预期结果
自动化步骤
自动化断言
测试数据
清理步骤
source_ref
备注
```

### 12.1 必填列

| 列名 | 说明 |
|---|---|
| `CaseID` | 用例唯一 ID |
| `自动化准入` | `PASS/PASS_WITH_GAP/BLOCKED/MANUAL_ONLY` |
| `前置状态ID` | 自动化起始条件 |
| `自动化步骤` | AutoSmoke 可执行步骤 |
| `自动化断言` | 自动化可判断预期 |

### 12.2 示例

| 字段 | 示例 |
|---|---|
| CaseID | `DL_RK_003` |
| 自动化准入 | `PASS` |
| 起始页面 | `main_city` |
| 前置状态ID | `PRE_LOGIN_GIFT_UNLOCKED_RUNNING` |
| 自动化步骤 | `点击 testId("activity.login_gift.entry")\n等待 1 秒\n断言存在 testId("activity.login_gift.main_panel")\n截图` |
| 自动化断言 | `page_visible: activity.login_gift.main_panel` |
| 清理步骤 | `点击 testId("common.close")` |

---

## 13. 七日签到场景落地示例

### 13.1 入口可见

```json
{
  "case_id": "DL_RK_001",
  "admission": "PASS",
  "precondition_id": "PRE_LOGIN_GIFT_UNLOCKED_RUNNING",
  "steps": [
    {
      "step_order": 1,
      "action_type": "assert_exists",
      "target": {
        "type": "testId",
        "value": "activity.login_gift.entry"
      }
    },
    {
      "step_order": 2,
      "action_type": "screenshot"
    }
  ],
  "assertions": [
    {
      "assertion_type": "element_visible",
      "target": {
        "type": "testId",
        "value": "activity.login_gift.entry"
      },
      "expected": true
    }
  ]
}
```

### 13.2 点击入口进入界面

```json
{
  "case_id": "DL_RK_003",
  "admission": "PASS",
  "precondition_id": "PRE_LOGIN_GIFT_UNLOCKED_RUNNING",
  "steps": [
    {
      "step_order": 1,
      "action_type": "click",
      "target": {
        "type": "testId",
        "value": "activity.login_gift.entry"
      }
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
        "value": "activity.login_gift.main_panel"
      }
    },
    {
      "step_order": 4,
      "action_type": "screenshot"
    }
  ]
}
```

### 13.3 入口不显示

```json
{
  "case_id": "DL_KJ_001",
  "admission": "PASS",
  "precondition_id": "PRE_LOGIN_GIFT_LOCKED",
  "steps": [
    {
      "step_order": 1,
      "action_type": "assert_not_exists",
      "target": {
        "type": "testId",
        "value": "activity.login_gift.entry"
      }
    },
    {
      "step_order": 2,
      "action_type": "screenshot"
    }
  ]
}
```

### 13.4 领取奖励

```json
{
  "case_id": "DL_REWARD_001",
  "admission": "PASS_WITH_GAP",
  "precondition_id": "PRE_LOGIN_GIFT_DAY1_CLAIMABLE",
  "steps": [
    {
      "step_order": 1,
      "action_type": "click",
      "target": {
        "type": "testId",
        "value": "activity.login_gift.entry"
      }
    },
    {
      "step_order": 2,
      "action_type": "click",
      "target": {
        "type": "testId",
        "value": "activity.login_gift.day1.claim_button"
      }
    },
    {
      "step_order": 3,
      "action_type": "assert_exists",
      "target": {
        "type": "testId",
        "value": "activity.login_gift.day1.claimed_state"
      }
    }
  ],
  "external_requirements": [
    {
      "type": "state_query",
      "description": "需要确认奖励是否真实到账",
      "blocking": false
    }
  ]
}
```

---

## 14. 能自动化与不能自动化的边界

### 14.1 可优先自动化

| 类型 | 示例 |
|---|---|
| UI 可见性 | 入口显示/不显示 |
| 页面跳转 | 点击入口进入主界面 |
| 按钮状态 | 可领取/已领取/置灰 |
| 红点状态 | 红点出现/消失 |
| 基本文案 | 标题、按钮文案 |
| 简单领取流程 | 点击领取后 UI 状态变化 |

### 14.2 需要外部能力后才能自动化

| 类型 | 需要能力 |
|---|---|
| 奖励真实到账 | 服务端状态/API/DB 查询 |
| 活动第 N 天 | 账号状态或服务器时间控制 |
| 注册日绑定 | 账号注册时间数据 |
| 活动结束在线 | 时间推进/活动开关控制 |
| 弱网 | 网络模拟工具 |
| 断线重连 | 网络控制/重连检测 |
| 杀进程重进 | 进程控制和重登能力 |
| 客户端时间篡改 | 系统时间控制与恢复 |

---

## 15. 框架落地分阶段

### 阶段 1：可执行用例输入

目标：

- Excel 增加 `自动化准入 / 前置状态ID / 自动化步骤 / 自动化断言`。
- 支持导入 `auto_smoke_case_seed.v1`。
- 能跑 UI 可见性、入口点击、页面打开类用例。

### 阶段 2：前置状态管理

目标：

- 建立 `precondition_registry`。
- 建立测试账号池。
- 支持按 `precondition_id` 选择账号或准备环境。

### 阶段 3：业务断言

目标：

- 接入状态导出、接口查询或日志/DB 验证。
- 支持奖励到账、领取状态、活动周期等断言。

### 阶段 4：异常场景自动化

目标：

- 接入弱网、断线、杀进程、重登、时间控制能力。
- 覆盖异常场景。

---

## 16. 最终框架结论

AutoSmoke 自动执行框架应固定为：

```text
Excel/DocReader
  → auto_smoke_case_seed.v1
  → schema 校验
  → 准入过滤
  → 前置状态准备
  → semanticId/testId 映射
  → 步骤解析
  → 目标定位
  → 动作执行
  → 断言验证
  → 清理动作
  → 报告输出
  → 缺口反馈
```

当前阶段最重要的不是扩大用例数量，而是先把输入框架固定下来：

1. 用例必须有 `case_id`。
2. 用例必须有 `admission`。
3. 自动化必须从 `自动化步骤` 执行，而不是从自然语言 `操作步骤` 执行。
4. 所有目标必须最终落到 `testId` 或其他 AutoSmoke 支持的定位类型。
5. 所有预期结果必须转成断言。
6. 所有前置条件必须转成 `precondition_id`。
7. 缺少前置、定位、断言、配置、状态查询时必须阻断或降级。

