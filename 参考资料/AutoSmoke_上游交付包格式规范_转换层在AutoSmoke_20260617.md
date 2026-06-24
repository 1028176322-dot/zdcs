# AutoSmoke 上游交付包格式规范

> 日期：2026-06-17  
> 场景：转换层放在 AutoSmoke  
> 目标：明确任意功能接入 AutoSmoke 时，上游需要提供哪些文件、每个文件的作用、详细字段格式、是否必需，以及 AutoSmoke 如何消费这些文件。

---

## 1. 总体说明

当“转换层”放在 AutoSmoke 时，上游不需要直接提供可执行自动化步骤，也不需要强制提供最终 `testId`。

本规范适配所有需要 UI 自动化或半自动化验证的功能，包括但不限于：

```text
活动功能
背包/道具/资源功能
商城/购买/兑换功能
任务/成就/领取功能
养成/升级/强化/进阶功能
战斗/编队/技能/状态功能
地图/建筑/探索/采集功能
排行榜/积分/结算功能
设置/邮件/公告/弹窗功能
任意新增业务页面或系统入口
```

上游需要提供的是一组结构化原料，让 AutoSmoke 能够完成：

```text
手工用例/业务事实
  → 识别目标对象
  → 推断动作
  → 匹配 semanticId/testId
  → 生成自动化步骤
  → 生成断言
  → 判断准入/阻断
  → 执行并输出报告
```

本规范中的示例可以使用任意具体功能名，但示例不是功能限制。任何功能都必须按相同抽象表达：

```text
功能 feature
模块 module
业务事实 business item
测试用例 manual case
目标对象 target
动作 action
前置状态 precondition
预期断言 assertion
来源追踪 source trace
待确认/阻断 review item
值资产 value asset
外部依赖 external ref
```

推荐交付为一个目录或 zip 包：

```text
autosmoke_upstream_handoff.v1/
├── manifest.json
├── case_seed_package.v0.json
├── manual_test_cases.v1.xlsx
├── target_name_catalog.v1.json
├── source_trace.v1.json
├── review_items.v1.json
├── value_assets.v1.json
├── business_state_contract.v1.json
├── business_assertions.v1.json
└── optional_external_refs.v1.json
```

如果上游当前只能提供 DocReader 原始产物目录，例如：

```text
DATA/fact_package.json
DATA/evidence.json
DATA/source_index.json
HANDOFF_OUTPUT/structured_business_model.json
HANDOFF_OUTPUT/business_reading.md
HANDOFF_OUTPUT/business_reading_render_report.json
执行验收报告.md
```

则这些文件只能作为“转换前原料”。在进入 AutoSmoke 正式转换前，仍需要整理或自动生成成本规范定义的 `autosmoke_upstream_handoff.v1` 目录结构。

---

## 2. 文件总览

| 文件 | 是否必需 | 作用 | AutoSmoke 消费用途 |
|---|---|---|---|
| `manifest.json` | 必需 | 包入口，声明版本、功能、文件清单 | 校验包完整性、确定解析入口 |
| `case_seed_package.v0.json` | 必需 | DocReader 输出的业务事实资产 | 提取业务项、关系、值资产、来源、准入 |
| `manual_test_cases.v1.xlsx` 或 `.json` | 必需 | 手工用例/测试流程骨架 | 转换为自动化用例、步骤顺序、预期结果 |
| `target_name_catalog.v1.json` | 必需 | 业务目标名目录 | 将自然语言目标映射到 semanticId/testId |
| `source_trace.v1.json` | 必需 | 来源追踪 | 报告回溯到文档、sheet、row、evidence |
| `review_items.v1.json` | 必需 | 待确认/阻断项 | 决定 PASS_WITH_GAP、BLOCKED、人工评审 |
| `value_assets.v1.json` | 强烈建议 | 配置、公式、文案、奖励等值资产 | 生成数值断言、配置依赖、文案断言 |
| `business_state_contract.v1.json` | 功能逻辑自动化必需 | 业务状态采集契约 | 声明可采集的玩家、资源、背包、任务、活动、场景、UI 状态路径 |
| `business_assertions.v1.json` | 功能逻辑自动化必需 | 业务断言定义 | 生成 before/after 状态断言、状态 diff、业务规则验证 |
| `optional_external_refs.v1.json` | 可选 | 外部系统引用 | 记录配置表、文案表、Wiki、状态查询依赖 |

最小可用交付：

```text
manifest.json
case_seed_package.v0.json
manual_test_cases.v1.xlsx
target_name_catalog.v1.json
source_trace.v1.json
review_items.v1.json
```

增强交付：

```text
value_assets.v1.json
business_state_contract.v1.json
business_assertions.v1.json
optional_external_refs.v1.json
```

如果目标是“UI + 功能逻辑都自动化”，则 `business_state_contract.v1.json` 和 `business_assertions.v1.json` 从增强文件升级为必需文件。否则 AutoSmoke 只能完成 UI 操作和 UI 可观察断言，无法证明业务状态真实正确。

---

## 3. manifest.json

### 3.1 作用

`manifest.json` 是整个上游交付包的入口文件。AutoSmoke 首先读取它，用来判断：

1. 这是哪个功能的资产包。
2. 包版本是否支持。
3. 里面包含哪些文件。
4. 哪些文件是必需文件。
5. 由谁生成、何时生成、来源是什么。

### 3.2 格式

```json
{
  "schema_version": "autosmoke_upstream_handoff.v1",
  "package_id": "artifact_page_20260617_v1",
  "feature_name": "神器界面功能",
  "feature_domain": "artifact",
  "feature_type": "upgrade_system",
  "source_tool": "DocReader",
  "source_doc": {
    "doc_name": "神器界面功能说明.html",
    "doc_version": "v0.1",
    "generated_at": "2026-06-17T00:00:00+08:00"
  },
  "conversion_owner": "AutoSmoke",
  "encoding": "utf-8",
  "files": {
    "case_seed": "case_seed_package.v0.json",
    "manual_test_cases": "manual_test_cases.v1.xlsx",
    "target_name_catalog": "target_name_catalog.v1.json",
    "source_trace": "source_trace.v1.json",
    "review_items": "review_items.v1.json",
    "value_assets": "value_assets.v1.json",
    "business_state_contract": "business_state_contract.v1.json",
    "business_assertions": "business_assertions.v1.json",
    "optional_external_refs": "optional_external_refs.v1.json"
  },
  "required_files": [
    "case_seed",
    "manual_test_cases",
    "target_name_catalog",
    "source_trace",
    "review_items"
  ]
}
```

### 3.3 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `autosmoke_upstream_handoff.v1` |
| `package_id` | string | 是 | 资产包唯一 ID |
| `feature_name` | string | 是 | 功能名称 |
| `feature_domain` | string | 建议 | 功能域，例如 `activity/bag/shop/artifact/battle/task/mail/settings` |
| `feature_type` | string | 建议 | 功能类型，例如 `entry/reward/upgrade/system_panel/config_display/battle_flow` |
| `source_tool` | string | 是 | 生成工具，例如 `DocReader` |
| `source_doc.doc_name` | string | 是 | 来源文档名 |
| `source_doc.doc_version` | string | 否 | 来源文档版本 |
| `source_doc.generated_at` | string | 是 | 生成时间，ISO 格式 |
| `conversion_owner` | string | 是 | 固定建议为 `AutoSmoke` |
| `encoding` | string | 是 | 推荐 `utf-8` |
| `files` | object | 是 | 文件别名到文件名的映射 |
| `required_files` | array | 是 | AutoSmoke 必须检查存在的文件别名 |

### 3.4 AutoSmoke 消费方式

AutoSmoke 读取顺序：

```text
1. 读取 manifest.json
2. 校验 schema_version
3. 检查 required_files 是否都存在
4. 根据 files 映射读取具体资产
5. 进入转换流程
```

### 3.5 通用功能域建议

`feature_domain` 不参与最终定位，但会影响 AutoSmoke 的目标名解析、默认动作推断和阻断策略。建议使用稳定英文小写。

```text
activity       活动/运营活动
bag            背包/道具/资源
shop           商城/购买/兑换
artifact       神器/装备/养成系统
task           任务/成就/日常
battle         战斗/技能/编队
map            地图/探索/采集
rank           排行/积分/结算
mail           邮件/公告/消息
settings       设置/账号/系统功能
common         通用弹窗/通用控件
unknown        无法归类，需人工确认
```

### 3.6 通用功能类型建议

```text
entry                 入口展示与跳转
reward                奖励领取与状态变化
upgrade_system        升级/强化/进阶/合成
config_display        配置、数值、规则展示
state_panel           状态页/详情页/信息页
transaction           购买/兑换/消耗/确认
battle_flow           战斗流程/技能释放/结算
collection            收集/解锁/图鉴/成就
exception_flow        异常/弱网/重登/时间边界
common_dialog         弹窗确认/关闭/二次确认
```

---

## 4. case_seed_package.v0.json

### 4.1 作用

这是 DocReader 当前能力范围内最核心的业务事实资产包。它不要求可执行，但必须稳定表达：

1. 功能名称。
2. 业务项。
3. 业务关系。
4. 值资产。
5. 待确认项。
6. 来源追踪。
7. 初步准入判断。

### 4.2 格式

```json
{
  "schema_version": "case_seed_package.v0",
  "feature_name": "神器界面功能",
  "feature_domain": "artifact",
  "feature_type": "upgrade_system",
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
      "部分环境前置需要外部准备"
    ]
  },
  "business_items": [
    {
      "item_id": "BITEM_001",
      "block_name": "品质升级",
      "item_type": "upgrade_rule",
      "statement": "每次强化提升属性与战力、进度条上涨，可暴击额外涨进度。进度满后可进阶，品质提升。",
      "certainty": "confirmed",
      "target_names": [
        "强化按钮",
        "进阶按钮",
        "品质进度条",
        "神器品质"
      ],
      "preserved_assets": [],
      "source_refs": [
        {
          "evidence_ref": "EVD_0001",
          "sheet_name": "",
          "row_number": null,
          "source_excerpt": "每次强化提升属性与战力、进度条上涨，可暴击额外涨进度。进度满后可进阶，品质提升。"
        }
      ]
    }
  ],
  "relation_items": [],
  "value_assets": [],
  "review_items": [],
  "source_refs": []
}
```

### 4.3 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `case_seed_package.v0` |
| `feature_name` | string | 是 | 功能名 |
| `feature_domain` | string | 建议 | 功能域，与 manifest 保持一致 |
| `feature_type` | string | 建议 | 功能类型，与 manifest 保持一致 |
| `admission` | object | 是 | 当前资产包准入状态 |
| `business_items` | array | 是 | 业务项列表 |
| `business_items[].item_id` | string | 是 | 业务项唯一 ID |
| `business_items[].block_name` | string | 是 | 功能块/模块名 |
| `business_items[].item_type` | string | 是 | 业务项类型 |
| `business_items[].statement` | string | 是 | 标准业务陈述 |
| `business_items[].certainty` | string | 是 | `confirmed/inferred/uncertain/missing/conflict` |
| `business_items[].target_names` | array | 建议 | 从 statement 中提取的目标名 |
| `business_items[].preserved_assets` | array | 否 | UI 格式、公式、文案等保留资产 |
| `business_items[].source_refs` | array | 是 | 来源追踪 |
| `relation_items` | array | 否 | 条件/结果/限制关系 |
| `value_assets` | array | 否 | 值资产，也可独立到 `value_assets.v1.json` |
| `review_items` | array | 否 | 待确认项，也可独立到 `review_items.v1.json` |
| `source_refs` | array | 建议 | 文件级来源索引 |

### 4.4 AutoSmoke 消费方式

AutoSmoke 转换器主要使用：

| 来源字段 | 转换用途 |
|---|---|
| `feature_name` | 生成自动化用例功能归属 |
| `business_items[].statement` | 生成候选测试点、候选断言 |
| `business_items[].target_names` | 匹配 target catalog |
| `business_items[].source_refs` | 写入执行报告 |
| `relation_items` | 推断前置条件、流程分支 |
| `value_assets` | 推断配置/文案/数值断言 |
| `review_items` | 生成阻断或人工评审项 |

### 4.5 通用 item_type 建议

`business_items[].item_type` 必须表达“这条事实在业务上是什么”，不要只写成 `text` 或 `rule`。建议枚举如下：

```text
ui_entry_rule          入口展示、入口跳转、入口隐藏
page_display_rule      页面展示、模块展示、页签展示
button_action_rule     按钮点击后的行为
status_rule            状态显示、状态变化、红点、可领取、已完成
upgrade_rule           强化、升级、进阶、合成、升星、升阶
consume_rule           消耗道具、资源扣减、门票消耗
reward_rule            奖励发放、奖励展示、奖励到账
unlock_rule            解锁条件、开放条件、等级限制、任务限制
config_rule            配置数值、上限、公式、概率、排序
text_rule              文案、标题、说明、提示语
tab_rule               页签切换、分类展示
list_rule              列表项、排行榜、道具列表、奖励列表
dialog_rule            弹窗出现、二次确认、关闭、错误提示
transaction_rule       购买、兑换、确认、取消、支付结果
battle_rule            战斗生效、技能释放、能量、伤害、结算
exception_rule         弱网、断线、重登、时间边界、异常返回
external_state_rule    需要服务端、数据库、日志、配置表验证的状态
```

### 4.6 任意功能业务事实的最低要求

每条 `business_item` 至少要能回答：

```text
这条事实属于哪个模块？
它描述的是入口、按钮、状态、数值、奖励、消耗、解锁、战斗还是异常？
它影响哪些目标对象？
它是否有确定来源？
它是 confirmed、inferred、uncertain、missing 还是 conflict？
```

如果无法回答“影响哪些目标对象”，`target_names` 可以先为空，但必须在 `review_items.v1.json` 中生成 `target_required` 或 `manual_review_required`。

---

## 5. manual_test_cases.v1.xlsx

### 5.1 作用

手工测试用例是 AutoSmoke 转换器最重要的流程骨架。它提供：

1. 用例 ID。
2. 测试模块。
3. 前置条件自然语言。
4. 操作步骤自然语言。
5. 预期结果自然语言。
6. 优先级。

AutoSmoke 负责把这些自然语言转换为自动化执行结构。

### 5.2 推荐 Excel 列

```text
优先级
CaseID
模块
子模块
用例标题
前置条件
操作步骤
预期结果
测试结果
备注
source_ref
```

### 5.3 列说明

| 列名 | 必需 | 说明 | 示例 |
|---|---:|---|---|
| `优先级` | 是 | 用例优先级 | `P0/P1/P2` |
| `CaseID` | 是 | 用例唯一 ID | `ART_UPGRADE_001` |
| `模块` | 是 | 一级模块 | `品质升级` |
| `子模块` | 建议 | 二级模块 | `强化-进度变化` |
| `用例标题` | 建议 | 用例标题，没有时可由子模块生成 | `点击强化后神器进度增加` |
| `前置条件` | 是 | 自然语言前置条件 | `玩家位于神器界面；强化材料充足` |
| `操作步骤` | 是 | 自然语言操作步骤 | `1. 点击强化按钮` |
| `预期结果` | 是 | 自然语言预期结果 | `品质进度条数值增加` |
| `测试结果` | 否 | 手工执行结果 | `待测试/已通过/未通过` |
| `备注` | 否 | 标签、风险、引用 | `#[B3]` |
| `source_ref` | 建议 | 来源位置 | `神器界面.html#EVD_0001` |

### 5.4 推荐写法规范

为了让 AutoSmoke 转换器更稳定，手工用例中的自然语言要达到一个目标：

```text
人能读懂，AutoSmoke 也能稳定拆解成前置状态、动作、目标、断言和阻断项。
```

核心标准：

```text
一个前置条件 = 一个明确状态
一个操作步骤 = 一个动作 + 一个目标
一个预期结果 = 一个可观察结果 + 一个目标
```

不要把多个动作、多个目标、多个判断揉在一句话里。

本节示例中的功能名可以替换为任意功能。通用写法模板如下：

```text
前置条件：
1. 玩家位于【起始页面/目标页面】
2. 【功能】已解锁/已开启/已满足开放条件
3. 【目标对象】处于【可点击/可领取/可购买/可强化/未完成/已完成】状态
4. 【资源/道具/次数/时间/配置】满足具体条件

操作步骤：
1. 点击/查看/选择/输入/等待【目标对象】
2. 查看【目标页面/目标状态/目标弹窗/目标数值】

预期结果：
1. 【目标页面/目标对象】可见
2. 【目标状态】显示为【具体状态】
3. 【目标数值】增加/减少/等于【具体值】
4. 【目标弹窗/提示】出现或消失
```

#### 5.4.1 前置条件写法

前置条件应描述“测试开始前系统处于什么状态”，不要描述一长串如何做到这个状态的过程。

推荐：

```text
1. 玩家位于主城界面
2. 玩家位于神器界面
3. 神器功能已解锁
4. 强化材料数量 >= 1
5. 神器品质进度未满
```

不推荐：

```text
玩家登录游戏后做完前置任务然后满足条件
先升级灯塔再通关区域然后活动应该开启
正常账号
```

如果涉及等级、区域进度、活动状态、奖励状态，应尽量写成明确状态：

```text
灯塔等级 >= 5
神秘海域区域1已通关
活动状态 = 进行中
奖励状态 = 可领取
强化材料数量 >= 1
同孔位同等级组件数量 = 3
商品库存 > 0
今日购买次数 = 0
```

AutoSmoke 转换器会尝试将这些状态映射成：

```text
precondition_id，例如 PRE_ARTIFACT_PAGE_MATERIAL_READY
```

#### 5.4.2 操作步骤写法

每一步必须有明确动作词和明确目标名。

推荐动作词：

```text
进入
点击
查看
等待
领取
关闭
返回
输入
选择
滑动
刷新
重登
断网
恢复网络
杀进程
启动游戏
```

推荐：

```text
1. 进入主界面
2. 点击神器入口图标
3. 查看神器主界面
4. 点击强化按钮
5. 查看品质进度条
```

不推荐：

```text
登录后满足条件点一下右上角然后看有没有进入界面
打开活动看看能不能领
点一下签到那里
正常领取
进行操作
查看界面
```

原因是 AutoSmoke 无法稳定判断“活动”是哪一个、“那里”是哪一个、“操作”是什么。

#### 5.4.3 目标名称写法

目标名应稳定，并尽量与 `target_name_catalog.v1.json` 中的 `target_name` 或 `aliases` 一致。

推荐：

```text
神器入口图标
神器主界面
强化按钮
进阶按钮
品质进度条
组件页签
宝物页签
技能页签
奖励获得弹窗
入口红点
关闭按钮
```

不推荐：

```text
右上角那个图标
活动按钮
这个页面
奖励那里
红点
按钮
```

如果同一个对象有多种叫法，上游应在 `target_name_catalog.v1.json` 中统一标准名，并把其他叫法放入 `aliases`：

```json
{
  "target_name": "神器强化按钮",
  "aliases": [
    "强化按钮",
    "强化",
    "点击强化"
  ]
}
```

#### 5.4.4 预期结果写法

预期结果必须是 AutoSmoke 能观察或能通过外部能力查询的结果。

推荐：

```text
神器入口图标可见
神器入口图标不显示
进入神器主界面
强化按钮可点击
品质进度条数值增加
神器品质显示为 B
组件数量显示为 0 / 10
目标状态显示为已领取
入口红点消失
弹出奖励获得弹窗
```

不推荐：

```text
功能正常
展示正确
状态正确
没有问题
奖励正常
符合预期
```

`正确`、`正常`、`符合预期` 不是可执行断言，必须展开为具体可观察结果。

#### 5.4.5 一步一个动作

不推荐：

```text
1. 点击入口进入界面并强化然后关闭弹窗
```

推荐拆成：

```text
1. 点击神器入口图标
2. 查看神器主界面
3. 点击强化按钮
4. 查看品质进度条
5. 点击奖励获得弹窗关闭按钮
```

#### 5.4.6 一个预期一个判断

不推荐：

```text
入口显示且有红点，点击后进入界面，奖励可领取，领取后到账且红点消失
```

推荐拆成多个判断：

```text
1. 神器入口图标可见
2. 入口红点可见
3. 神器主界面可见
4. 强化按钮可点击
5. 品质进度条数值增加
6. 入口红点消失
```

如果判断过多，建议拆成多条用例：

```text
FEATURE_ENTRY_001 入口可见
FEATURE_ENTRY_002 入口红点显示
FEATURE_ACTION_001 按钮可点击
FEATURE_STATE_001 操作后状态变化
```

#### 5.4.7 时间、配置、账号状态写法

涉及时间、配置、账号状态时，不要使用模糊词。

不推荐：

```text
活动快结束时
第二天
新用户
老用户
过一段时间
```

推荐：

```text
活动第7天 23:59
服务器时间 UTC+8 00:00
角色注册后第1天
角色注册后第8天
奖励状态 = 可领取
奖励状态 = 未解锁
活动状态 = 已结束
强化材料数量 = 1
组件等级 = 2
同孔位同等级组件数量 = 3
```

如果依赖配置或文案，应尽量在 `value_assets.v1.json` 或 `optional_external_refs.v1.json` 中提供对应引用。

#### 5.4.8 异常场景写法

异常场景必须写清楚触发点和恢复点。

推荐：

```text
1. 点击目标操作按钮
2. 在领取请求发出后断开网络
3. 恢复网络
4. 重新进入目标功能主界面
```

不推荐：

```text
弱网领取
断线后看看
杀进程重进正常
```

弱网、断线、杀进程、时间篡改等场景，如果没有对应环境控制能力，AutoSmoke 会标记为：

```text
BLOCKED 或 MANUAL_ONLY
```

#### 5.4.9 自然语言质量分级

AutoSmoke 转换器可按以下标准判断手工用例质量：

| 等级 | 特征 | AutoSmoke 处理 |
|---|---|---|
| A | 每步都有动作 + 目标，预期可观察 | 可直接转换 |
| B | 目标明确，但动作或预期略模糊 | 可转换，需人工确认 |
| C | 只有业务描述，没有明确步骤 | 只能生成测试点 |
| D | 依赖环境/时间/网络/服务端且未说明控制方式 | 阻断或人工测试 |

A 级示例：

```text
前置条件：
1. 玩家位于主城界面
2. 神器功能已解锁
3. 玩家位于神器界面
4. 强化材料数量 >= 1

操作步骤：
1. 点击强化按钮
2. 查看品质进度条

预期结果：
1. 品质进度条数值增加
```

C 级示例：

```text
操作步骤：
1. 进入活动

预期结果：
功能正常
```

C 级用例只能用于测试点生成或人工评审，不能稳定转换为自动化执行步骤。

#### 5.4.10 最终写法规则

手工用例自然语言至少应满足：

1. 明确动作词。
2. 明确目标名。
3. 明确起始状态。
4. 明确可观察预期。
5. 一步一个动作。
6. 一条预期一个判断。
7. 避免“正常 / 正确 / 符合预期”。
8. 避免“那里 / 这个 / 活动 / 按钮”等泛称。
9. 涉及时间、账号、网络、配置时写出具体条件。
10. 与 `target_name_catalog.v1.json` 的标准目标名或别名保持一致。

符合以上规则后，AutoSmoke 转换层才能稳定地生成类似：

```text
点击 testId("artifact.upgrade.enhance.button")
等待 1 秒
断言数值变化 testId("artifact.upgrade.progress.text")
截图
```

### 5.5 JSON 等价格式

如果不使用 Excel，可提供：

```json
{
  "schema_version": "manual_test_cases.v1",
  "feature_name": "神器界面功能",
  "test_cases": [
    {
      "priority": "P1",
      "case_id": "ART_UPGRADE_001",
      "module": "品质升级",
      "submodule": "强化-进度变化",
      "title": "点击强化后神器进度增加",
      "precondition": "玩家位于神器界面；强化材料数量 >= 1",
      "steps": "1. 点击强化按钮\n2. 查看品质进度条",
      "expected": "1. 品质进度条数值增加",
      "remark": "#[B3]",
      "source_ref": "神器界面.html#EVD_0001"
    }
  ]
}
```

### 5.6 AutoSmoke 消费方式

AutoSmoke 转换器会执行：

```text
CaseID → case_id
优先级 → priority
模块/子模块 → module/submodule/title
前置条件 → precondition_id 候选
操作步骤 → action_type + target_name 候选
预期结果 → assertion 候选
source_ref → 报告追踪
```

---

## 6. target_name_catalog.v1.json

### 6.1 作用

这是转换层放在 AutoSmoke 时最关键的文件之一。

它不要求上游提供最终 `testId`，但要求上游提供稳定的业务目标名和别名。AutoSmoke 用它把自然语言中的“强化按钮”“背包金币途径按钮”“商城购买按钮”“技能页签”等目标，匹配到已有的 `semanticId/testId/element_mapping`。

### 6.2 格式

```json
{
  "schema_version": "target_name_catalog.v1",
  "feature_name": "神器界面功能",
  "targets": [
    {
      "target_id": "TGT_ARTIFACT_ENHANCE_BUTTON",
      "target_name": "强化按钮",
      "semantic_hint": "artifact.upgrade.enhance_button",
      "target_type": "button",
      "page_hint": "artifact",
      "action_role": "enhance",
      "aliases": [
        "神器强化按钮",
        "强化",
        "点击强化"
      ],
      "expected_locator_owner": "AutoSmoke",
      "source_refs": [
        "神器界面.html#EVD_0001"
      ]
    },
    {
      "target_id": "TGT_ARTIFACT_PROGRESS_TEXT",
      "target_name": "品质进度条",
      "semantic_hint": "artifact.upgrade.progress_text",
      "target_type": "text",
      "page_hint": "artifact",
      "action_role": "progress_display",
      "aliases": [
        "品质升级进度",
        "进度条",
        "强化进度"
      ],
      "expected_locator_owner": "AutoSmoke"
    }
  ]
}
```

### 6.3 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `target_name_catalog.v1` |
| `feature_name` | string | 是 | 功能名 |
| `targets` | array | 是 | 目标对象列表 |
| `targets[].target_id` | string | 是 | 目标对象唯一 ID |
| `targets[].target_name` | string | 是 | 标准业务目标名 |
| `targets[].semantic_hint` | string | 建议 | 建议 semanticId，不要求一定可执行 |
| `targets[].target_type` | string | 是 | 目标类型，见 6.5 |
| `targets[].page_hint` | string | 建议 | 所属页面或场景 |
| `targets[].action_role` | string | 建议 | 动作角色，见 6.6 |
| `targets[].aliases` | array | 强烈建议 | 自然语言别名 |
| `targets[].expected_locator_owner` | string | 建议 | `AutoSmoke/upstream/external` |
| `targets[].source_refs` | array | 建议 | 来源追踪 |

### 6.4 AutoSmoke 消费方式

AutoSmoke 转换器做目标识别时会按以下顺序：

```text
1. 从手工步骤/预期结果中抽取目标短语
2. 精确匹配 target_name
3. 匹配 aliases
4. 使用 page_hint/action_role 缩小范围
5. 使用 semantic_hint 匹配 AutoSmoke element_mapping
6. 解析出 testId
7. 若无法解析，生成 missing_locator/review item
```

### 6.5 通用 target_type 建议

`target_type` 表达目标对象的 UI/业务形态。建议枚举如下：

```text
page              页面/主面板
panel             子面板/区域
tab               页签/分类
button            按钮
icon              图标
interactive_icon  可点击图标
text              文本/数值/标题/说明
status            状态文案/状态标识
red_dot           红点/提示点
dialog            弹窗
toast             飘字/提示
input             输入框
toggle            开关/勾选
slider            滑条
list              列表
list_item         列表项
reward_item       奖励项
goods_item        商品项
resource_item     资源项
equipment_item    装备/神器/组件/宝物项
progress          进度条/经验条
badge             徽标/等级/品质标
image             业务图片/头像/图标展示
container         容器，仅当它承载业务状态时使用
external_state    非 UI 状态，需外部查询
```

不建议把纯装饰背景、阴影、分割线、无业务含义容器放入 `target_name_catalog`。这类对象应在 AutoSmoke 侧标记为 `ignored`。

### 6.6 通用 action_role 建议

`action_role` 表达目标对象在自动化里的业务作用。建议枚举如下：

```text
entry             入口
open              打开
close             关闭
back              返回
confirm           确认
cancel            取消
claim             领取
buy               购买
exchange          兑换
enhance           强化
upgrade           升级
advance           进阶
compose           合成
select            选择
switch_tab        切换页签
input             输入
refresh           刷新
display           展示
page              页面断言
status            状态断言
progress_display  进度断言
count_display     数量断言
price_display     价格断言
resource_source   资源途径/获取途径
skill_release     技能释放
battle_result     战斗结果
rank_display      排行展示
unknown           未识别，需人工确认
```

### 6.7 目标名生成规则

目标名必须让人和 AutoSmoke 都能明确它指向哪个对象。推荐结构：

```text
【页面/功能】 + 【业务对象】 + 【角色/控件类型】
```

示例：

```text
神器强化按钮
神器进阶按钮
神器品质进度条
神器组件页签
背包金币途径按钮
商城每日礼包购买按钮
任务完成状态文案
奖励获得弹窗关闭按钮
```

不推荐：

```text
按钮
这个图标
领取那里
活动页面
正常状态
```

---

## 7. source_trace.v1.json

### 7.1 作用

`source_trace.v1.json` 用于把生成的自动化用例、步骤、断言、阻断项回溯到原始来源。它对问题定位和评审非常重要。

### 7.2 格式

```json
{
  "schema_version": "source_trace.v1",
  "feature_name": "神器界面功能",
  "sources": [
    {
      "source_ref": "神器界面.html#EVD_0001",
      "case_id": "ART_UPGRADE_001",
      "item_id": "BITEM_001",
      "doc_name": "神器界面.html",
      "sheet": "",
      "row": null,
      "column": null,
      "evidence_ref": "EVD_0001",
      "excerpt": "每次强化提升属性与战力、进度条上涨，可暴击额外涨进度。进度满后可进阶，品质提升。"
    }
  ]
}
```

### 7.3 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `source_trace.v1` |
| `feature_name` | string | 是 | 功能名 |
| `sources` | array | 是 | 来源列表 |
| `sources[].source_ref` | string | 是 | 稳定来源引用 |
| `sources[].case_id` | string | 建议 | 对应用例 ID |
| `sources[].item_id` | string/null | 否 | 对应 business_item ID |
| `sources[].doc_name` | string | 是 | 来源文件名 |
| `sources[].sheet` | string | 否 | Excel sheet 名 |
| `sources[].row` | number | 否 | 行号 |
| `sources[].column` | string/null | 否 | 列名或列号 |
| `sources[].evidence_ref` | string | 建议 | evidence ID |
| `sources[].excerpt` | string | 建议 | 原始摘录 |

### 7.4 AutoSmoke 消费方式

AutoSmoke 会把 `source_ref` 写入：

1. 转换结果。
2. 用例报告。
3. 失败步骤报告。
4. 阻断项清单。
5. 人工评审页面。

---

## 8. review_items.v1.json

### 8.1 作用

`review_items.v1.json` 用于表达上游无法确认、需要外部能力、需要人工评审或应阻断自动化的事项。

它不能只写在备注里，必须结构化。

### 8.2 格式

```json
{
  "schema_version": "review_items.v1",
  "feature_name": "神器界面功能",
  "items": [
    {
      "item_id": "REV_001",
      "related_case_id": "ART_UPGRADE_001",
      "related_item_id": null,
      "status": "state_prepare_required",
      "severity": "blocker",
      "description": "强化材料数量需要测试环境或账号资产准备",
      "suggested_handling": "BLOCKED",
      "required_owner": "test_account_pool",
      "source_refs": [
        "神器界面.html#EVD_0001"
      ]
    },
    {
      "item_id": "REV_002",
      "related_case_id": "ART_ADVANCE_001",
      "status": "config_required",
      "severity": "warning",
      "description": "进阶所需材料数量和品质上限需要配置表确认",
      "suggested_handling": "PASS_WITH_GAP",
      "required_owner": "config_table",
      "source_refs": []
    }
  ]
}
```

### 8.3 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `review_items.v1` |
| `feature_name` | string | 是 | 功能名 |
| `items` | array | 是 | 待评审/阻断项 |
| `items[].item_id` | string | 是 | 唯一 ID |
| `items[].related_case_id` | string/null | 建议 | 关联用例 |
| `items[].related_item_id` | string/null | 否 | 关联业务项 |
| `items[].status` | string | 是 | 状态码 |
| `items[].severity` | string | 是 | `info/warning/blocker` |
| `items[].description` | string | 是 | 问题说明 |
| `items[].suggested_handling` | string | 是 | `PASS_WITH_GAP/BLOCKED/MANUAL_ONLY/REVIEW` |
| `items[].required_owner` | string | 否 | 需要谁补齐 |
| `items[].source_refs` | array | 建议 | 来源 |

### 8.4 status 枚举建议

```text
uncertain
missing
conflict
locator_required
config_required
text_key_required
state_query_required
environment_required
state_prepare_required
network_control_required
time_control_required
manual_review_required
target_required
case_required
external_dependency_required
state_contract_required
business_assertion_required
state_path_not_declared
state_export_failed
precondition_failed
```

### 8.5 AutoSmoke 消费方式

AutoSmoke 会把这些项合并到自动化准入判断：

| review item | AutoSmoke 处理 |
|---|---|
| `locator_required` | 无可用 locator 时 BLOCKED |
| `config_required` | 影响断言/分支时 BLOCKED，否则 PASS_WITH_GAP |
| `state_query_required` | UI 可跑但业务深断言降级 |
| `environment_required` | 前置状态不可准备时 BLOCKED |
| `network_control_required` | 异常网络场景 BLOCKED |
| `time_control_required` | 时间推进场景 BLOCKED |
| `state_prepare_required` | 账号状态/资源/进度不可准备时 BLOCKED |
| `target_required` | 缺少目标名或目标过于模糊时 REVIEW/BLOCKED |
| `case_required` | 只有业务事实、没有用例步骤时不能生成正式自动化 |

---

## 9. value_assets.v1.json

### 9.1 作用

`value_assets.v1.json` 用于表达文档中的配置、公式、奖励、数值、文案 KEY、UI 展示格式等值资产。

它帮助 AutoSmoke 判断：

1. 能否生成数值断言。
2. 是否需要配置表查询。
3. 是否需要文案表查询。
4. 是否需要人工评审。
5. 是否只能做 UI 浅断言。

### 9.2 格式

```json
{
  "schema_version": "value_assets.v1",
  "feature_name": "神器界面功能",
  "items": [
    {
      "asset_id": "VAL_ARTIFACT_COMPONENT_COMPOSE_COUNT",
      "asset_type": "numeric_rule",
      "name": "同孔位同等级组件合成数量",
      "raw_expression": "3 个同孔位同等级组件合成 1 个更高等级",
      "normalized_expression": "same_slot_same_level_component_count = 3",
      "value": 3,
      "value_type": "integer",
      "config_source": null,
      "config_key": null,
      "certainty": "confirmed",
      "source_refs": [
        "神器界面.html#EVD_0001"
      ]
    },
    {
      "asset_id": "VAL_ARTIFACT_MAX_COMPONENT_LEVEL",
      "asset_type": "config_reference",
      "name": "组件等级上限",
      "raw_expression": "上限 7 级",
      "normalized_expression": null,
      "value": null,
      "value_type": "integer",
      "config_source": "artifact_config",
      "config_key": "artifact.component.max_level",
      "certainty": "config_required",
      "source_refs": []
    },
    {
      "asset_id": "VAL_ARTIFACT_ENHANCE_TEXT",
      "asset_type": "text_key",
      "name": "强化按钮文案",
      "raw_expression": "强 化",
      "text_key": "ARTIFACT_ENHANCE",
      "resolved_text": "强化",
      "locale": "zh-CN",
      "certainty": "confirmed"
    }
  ]
}
```

### 9.3 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `value_assets.v1` |
| `feature_name` | string | 是 | 功能名 |
| `items` | array | 是 | 值资产列表 |
| `items[].asset_id` | string | 是 | 值资产 ID |
| `items[].asset_type` | string | 是 | 类型 |
| `items[].name` | string | 是 | 名称 |
| `items[].raw_expression` | string | 是 | 原始表达 |
| `items[].normalized_expression` | string/null | 否 | 标准化表达 |
| `items[].value` | any | 否 | 已解析值 |
| `items[].value_type` | string | 是 | 值类型 |
| `items[].config_source` | string/null | 否 | 配置来源 |
| `items[].config_key` | string/null | 否 | 配置 key |
| `items[].text_key` | string/null | 否 | 文案 key |
| `items[].resolved_text` | string/null | 否 | 最终文案 |
| `items[].certainty` | string | 是 | `confirmed/config_required/text_key_required/uncertain/missing` |
| `items[].source_refs` | array | 建议 | 来源 |

### 9.4 asset_type 建议

```text
config_reference
reward_config
text_key
display_format
numeric_rule
time_rule
formula
server_state
consume_rule
progress_rule
unlock_rule
probability_rule
sort_rule
```

### 9.5 AutoSmoke 消费方式

AutoSmoke 用它生成：

1. `config_required` 阻断项。
2. `text_equals` 文案断言。
3. `numeric_equals` 数值断言。
4. `state_equals` 业务状态断言。
5. `PASS_WITH_GAP` 降级说明。

---

## 10. business_state_contract.v1.json

### 10.1 作用

`business_state_contract.v1.json` 用于声明某个功能在自动化执行时可以采集哪些业务状态，以及这些状态的路径、来源、稳定性和用途。

它解决的问题是：

```text
AutoSmoke 点击之后，应该从哪里读取真实业务结果？
哪些状态可以从 Unity/客户端导出？
哪些状态必须通过服务端、GM、DB、日志或配置表查询？
哪些状态只能通过 UI 文本兜底？
```

如果目标只是 UI 自动化，该文件可以不提供；如果目标是功能逻辑自动化，该文件必须提供。

### 10.2 格式

```json
{
  "schema_version": "business_state_contract.v1",
  "feature_name": "神器界面功能",
  "state_domains": [
    {
      "domain": "player",
      "collector": "unity_state_exporter",
      "required": true,
      "paths": [
        {
          "path": "player.uid",
          "value_type": "string",
          "description": "玩家 UID",
          "source": "client_state",
          "stability": "stable",
          "required_for": [
            "report_trace"
          ]
        }
      ]
    },
    {
      "domain": "resources",
      "collector": "unity_state_exporter",
      "required": true,
      "paths": [
        {
          "path": "resources.gold",
          "value_type": "integer",
          "description": "金币数量",
          "source": "client_state",
          "stability": "stable",
          "required_for": [
            "consume_assertion",
            "ui_server_consistency"
          ]
        }
      ]
    },
    {
      "domain": "artifact",
      "collector": "unity_state_exporter",
      "required": true,
      "paths": [
        {
          "path": "artifact.current.quality",
          "value_type": "string",
          "description": "当前神器品质",
          "source": "client_state",
          "stability": "stable",
          "required_for": [
            "state_assertion"
          ]
        },
        {
          "path": "artifact.current.progress",
          "value_type": "integer",
          "description": "当前神器强化进度",
          "source": "client_state",
          "stability": "eventual",
          "required_for": [
            "progress_assertion"
          ]
        },
        {
          "path": "bag.items[itemId=artifact_crystal].count",
          "value_type": "integer",
          "description": "进阶结晶数量",
          "source": "client_state",
          "stability": "eventual",
          "required_for": [
            "consume_assertion"
          ]
        }
      ]
    },
    {
      "domain": "ui",
      "collector": "ui_state_exporter",
      "required": true,
      "paths": [
        {
          "path": "ui.currentPage",
          "value_type": "string",
          "description": "当前 UI 页面",
          "source": "ui_tree",
          "stability": "stable",
          "required_for": [
            "page_assertion"
          ]
        },
        {
          "path": "ui.popupStack",
          "value_type": "array",
          "description": "当前弹窗栈",
          "source": "ui_tree",
          "stability": "stable",
          "required_for": [
            "dialog_assertion"
          ]
        }
      ]
    }
  ],
  "snapshot": {
    "before_required": true,
    "after_required": true,
    "diff_required": true,
    "wait_until_stable": {
      "timeout_ms": 5000,
      "interval_ms": 200
    }
  }
}
```

### 10.3 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `business_state_contract.v1` |
| `feature_name` | string | 是 | 功能名 |
| `state_domains` | array | 是 | 状态域列表 |
| `state_domains[].domain` | string | 是 | 状态域，例如 `player/resources/bag/artifact/ui/scene` |
| `state_domains[].collector` | string | 是 | 采集器名称 |
| `state_domains[].required` | boolean | 是 | 该状态域是否为当前功能逻辑验证必需 |
| `state_domains[].paths` | array | 是 | 可采集状态路径 |
| `paths[].path` | string | 是 | 状态路径表达式 |
| `paths[].value_type` | string | 是 | 值类型 |
| `paths[].description` | string | 是 | 状态含义 |
| `paths[].source` | string | 是 | 状态来源 |
| `paths[].stability` | string | 是 | 状态稳定性 |
| `paths[].required_for` | array | 建议 | 用于哪些断言 |
| `snapshot.before_required` | boolean | 是 | 是否要求动作前快照 |
| `snapshot.after_required` | boolean | 是 | 是否要求动作后快照 |
| `snapshot.diff_required` | boolean | 是 | 是否要求生成 diff |
| `snapshot.wait_until_stable` | object | 建议 | 状态稳定等待策略 |

### 10.4 domain 建议

```text
player          玩家基础状态
resources       资源状态
bag             背包/道具状态
buildings       建筑状态
tasks           任务/成就状态
activities      活动状态
artifact        神器/装备/养成状态
battle          战斗状态
shop            商店/购买/兑换状态
mail            邮件状态
rank            排行/积分状态
scene           场景/加载/重连状态
ui              UI 页面/弹窗/红点状态
external        外部服务端/DB/日志状态
```

### 10.5 source 建议

```text
client_state        Unity/客户端内部状态导出
server_state        服务端状态查询
config_table        配置表查询
db_query            数据库查询
log_query           日志/事件查询
ui_tree             UI 树/Poco/元数据
ui_text             UI 文本组件
ocr                 截图 OCR 兜底
manual              人工确认
```

### 10.6 stability 建议

```text
stable              点击后立即稳定
eventual            需要轮询等待稳定
async               依赖网络/异步回包
external            依赖外部系统刷新
manual_only         无法自动确认
```

### 10.7 AutoSmoke 消费方式

AutoSmoke 会使用该文件生成：

1. 状态采集计划。
2. before / after 快照路径。
3. 状态稳定等待策略。
4. 状态 diff 范围。
5. 业务断言可用性检查。
6. 缺失状态来源的 `review_items`。

如果 `business_assertions.v1.json` 中引用了本文件未声明的状态路径，AutoSmoke 必须标记为：

```text
BLOCKED: STATE_PATH_NOT_DECLARED
```

---

## 11. business_assertions.v1.json

### 11.1 作用

`business_assertions.v1.json` 用于声明用例执行后的功能逻辑断言。它让 AutoSmoke 不只验证 UI 是否变化，还能验证业务状态是否真实变化、变化是否符合配置和规则。

它支持：

```text
资源增加/减少
背包道具数量变化
任务状态变化
活动状态变化
养成进度变化
购买/兑换消耗与获得
UI 与业务状态一致性
配置公式校验
事件/日志触发校验
```

### 11.2 格式

```json
{
  "schema_version": "business_assertions.v1",
  "feature_name": "神器界面功能",
  "assertions": [
    {
      "assertion_id": "BASSERT_ART_UPGRADE_001",
      "case_id": "ART_UPGRADE_001",
      "step_order": 1,
      "description": "点击强化后，神器进度增加，材料减少",
      "pre_checks": [
        {
          "path": "bag.items[itemId=artifact_crystal].count",
          "operator": "greaterThanOrEqual",
          "value": 1,
          "on_failed": "BLOCKED"
        }
      ],
      "checks": [
        {
          "type": "business_state",
          "path": "artifact.current.progress",
          "operator": "increased",
          "expected": null,
          "source": "client_state",
          "required": true
        },
        {
          "type": "business_state",
          "path": "bag.items[itemId=artifact_crystal].count",
          "operator": "decreasedBy",
          "expected": 1,
          "source": "client_state",
          "required": true
        },
        {
          "type": "ui_business_consistency",
          "ui_target": "神器品质进度条",
          "state_path": "artifact.current.progress",
          "operator": "equals_display",
          "required": true
        }
      ],
      "source_refs": [
        "神器界面.html#EVD_0001"
      ]
    }
  ]
}
```

### 11.3 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `business_assertions.v1` |
| `feature_name` | string | 是 | 功能名 |
| `assertions` | array | 是 | 业务断言组 |
| `assertions[].assertion_id` | string | 是 | 业务断言唯一 ID |
| `assertions[].case_id` | string | 是 | 关联用例 ID |
| `assertions[].step_order` | number | 建议 | 关联步骤序号 |
| `assertions[].description` | string | 是 | 断言说明 |
| `assertions[].pre_checks` | array | 否 | 执行动作前置状态检查 |
| `assertions[].checks` | array | 是 | 动作后的业务断言列表 |
| `checks[].type` | string | 是 | 断言类型 |
| `checks[].path` | string | 条件必需 | 业务状态路径 |
| `checks[].operator` | string | 是 | 操作符 |
| `checks[].expected` | any | 否 | 期望值 |
| `checks[].source` | string | 建议 | 状态来源 |
| `checks[].required` | boolean | 是 | 失败或缺失时是否阻断 |
| `source_refs` | array | 建议 | 来源追踪 |

### 11.4 type 建议

```text
business_state          业务状态断言
ui_state                UI 状态断言
ui_business_consistency UI 显示与业务状态一致性断言
config_assertion        配置值断言
formula_assertion       公式计算断言
event_assertion         事件/日志触发断言
server_state            服务端状态断言
db_state                数据库状态断言
```

### 11.5 operator 建议

```text
equals
notEquals
greaterThan
greaterThanOrEqual
lessThan
lessThanOrEqual
increased
decreased
increasedBy
decreasedBy
changed
notChanged
exists
notExists
contains
notContains
equals_display
matches_config
matches_formula
event_emitted
```

### 11.6 路径表达规则

路径统一使用点号路径，列表筛选使用方括号条件：

```text
resources.gold
bag.items[itemId=1001].count
bag.items[itemId=artifact_crystal].count
tasks.mainTaskProgress
activities.islandTrial.rewardClaimable
artifact.current.quality
artifact.current.progress
ui.currentPage
ui.popupStack
scene.current
```

### 11.7 AutoSmoke 消费方式

AutoSmoke 会按以下顺序消费：

```text
1. 读取用例步骤
2. 找到 case_id + step_order 对应的 business assertions
3. 根据 business_state_contract 检查状态路径是否可采集
4. 执行动作前采集 before_state
5. 执行 pre_checks
6. UI 执行动作
7. 等待状态稳定
8. 采集 after_state
9. 生成 state diff
10. 执行业务断言
11. 输出 expected / actual / before / after / delta
```

如果业务断言无法执行：

| 情况 | 处理 |
|---|---|
| 状态路径未声明 | `BLOCKED: STATE_PATH_NOT_DECLARED` |
| 状态采集器不可用 | `BLOCKED: STATE_EXPORT_FAILED` |
| 前置检查失败 | `BLOCKED: PRECONDITION_FAILED` |
| 断言失败 | `FAIL: ASSERTION_FAILED` |
| 非必需断言缺外部能力 | `PASS_WITH_GAP` |

---

## 12. optional_external_refs.v1.json

### 12.1 作用

该文件用于声明外部系统引用。它不要求上游提供实际数据，只说明哪些外部系统可能需要参与。

### 12.2 格式

```json
{
  "schema_version": "optional_external_refs.v1",
  "feature_name": "神器界面功能",
  "refs": [
    {
      "ref_id": "EXT_CONFIG_ARTIFACT",
      "type": "config_table",
      "name": "artifact_config",
      "keys": [
        "artifact.component.max_level",
        "artifact.enhance.cost",
        "artifact.advance.cost"
      ],
      "required_for": [
        "numeric_assertion",
        "consume_assertion",
        "progress_assertion"
      ],
      "blocking_if_unavailable": true
    },
    {
      "ref_id": "EXT_TEXT_ARTIFACT",
      "type": "text_key_table",
      "name": "TextKey",
      "keys": [
        "ARTIFACT_TITLE",
        "ARTIFACT_ENHANCE",
        "ARTIFACT_ADVANCE"
      ],
      "required_for": [
        "text_assertion"
      ],
      "blocking_if_unavailable": false
    },
    {
      "ref_id": "EXT_STATE_QUERY",
      "type": "state_query",
      "name": "server_state_api",
      "keys": [
        "artifact.quality",
        "artifact.progress",
        "artifact.material_count"
      ],
      "required_for": [
        "state_equals",
        "consume_verified",
        "progress_verified"
      ],
      "blocking_if_unavailable": false
    }
  ]
}
```

### 12.3 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `optional_external_refs.v1` |
| `feature_name` | string | 是 | 功能名 |
| `refs` | array | 是 | 外部引用 |
| `refs[].ref_id` | string | 是 | 引用 ID |
| `refs[].type` | string | 是 | 外部系统类型 |
| `refs[].name` | string | 是 | 系统/表/接口名称 |
| `refs[].keys` | array | 否 | 需要的 key 或字段 |
| `refs[].required_for` | array | 否 | 用于哪些断言或流程 |
| `refs[].blocking_if_unavailable` | boolean | 是 | 缺失时是否阻断 |

### 12.4 type 建议

```text
config_table
text_key_table
wiki
state_query
test_account_pool
server_time_control
network_control
process_control
db_query
log_query
```

### 12.5 AutoSmoke 消费方式

AutoSmoke 不一定直接调用这些系统，但会据此：

1. 生成外部依赖清单。
2. 标记阻断原因。
3. 决定断言是否降级。
4. 在报告中说明“未验证到服务端深状态”的原因。

---

## 13. AutoSmoke 转换产物

上游提供上述文件后，AutoSmoke 转换层负责生成：

```text
auto_smoke_asset_package.v1/
├── manifest.json
├── case_seed.auto_smoke.v1.json
├── element_semantic_map.resolved.json
├── precondition_registry.resolved.json
├── assertion_catalog.resolved.json
├── business_state_contract.resolved.json
├── business_assertions.resolved.json
├── state_collection_plan.resolved.json
├── external_dependency_manifest.resolved.json
├── source_trace.resolved.json
└── review_blockers.resolved.json
```

其中 `case_seed.auto_smoke.v1.json` 会包含可执行步骤：

```json
{
  "case_id": "ART_UPGRADE_001",
  "admission": "PASS",
  "precondition_id": "PRE_ARTIFACT_PAGE_MATERIAL_READY",
  "steps": [
    {
      "step_order": 1,
      "action_type": "click",
      "target": {
        "type": "testId",
        "value": "artifact.upgrade.enhance.button"
      }
    },
    {
      "step_order": 2,
      "action_type": "assert_numeric_changed",
      "target": {
        "type": "testId",
        "value": "artifact.upgrade.progress.text"
      }
    },
    {
      "step_order": 3,
      "action_type": "business_assert",
      "business_assertion_ref": "BASSERT_ART_UPGRADE_001",
      "state_snapshots": {
        "before": "runtime/state/ART_UPGRADE_001/step_001/before_state.json",
        "after": "runtime/state/ART_UPGRADE_001/step_001/after_state.json",
        "diff": "runtime/state/ART_UPGRADE_001/step_001/diff.json"
      }
    }
  ]
}
```

---

## 14. 上游质量要求

为了让 AutoSmoke 转换稳定，上游交付需满足：

1. 所有 JSON 使用 UTF-8。
2. 所有 ID 稳定，不随每次生成随机变化。
3. `CaseID` 不重复。
4. `target_name` 尽量使用统一名称，不同叫法放入 `aliases`。
5. 来源追踪至少到 sheet + row。
6. 不确定信息必须进入 `review_items`，不要藏在备注中。
7. 业务条件、配置来源、文案 KEY 尽量结构化到 `value_assets`。
8. 如果无法提供 testId，可以不提供，但必须提供 `target_name_catalog`。
9. 所有功能都必须区分“可 UI 观察的断言”和“必须外部查询的深状态断言”。
10. 所有功能都必须说明关键前置状态如何满足，无法准备的进入 `review_items`。
11. 非业务装饰元素不要进入目标目录，应由 AutoSmoke 标记为 `ignored`。
12. 任何功能都不能只交付业务阅读结论，必须补充用例骨架或明确 `case_required`。
13. 如果要求功能逻辑自动化，必须提供 `business_state_contract.v1.json`。
14. 如果要求功能逻辑自动化，必须提供 `business_assertions.v1.json`。
15. `business_assertions` 中引用的状态路径必须在 `business_state_contract` 中声明。
16. 每条关键业务断言必须说明是 UI 状态、客户端状态、服务端状态、配置表、DB 还是日志来源。
17. 对于无法自动采集的状态，必须进入 `review_items`，不能隐藏在备注或预期结果中。

---

## 15. 通用适配流程

### 15.1 适配目标

为了让本规范适配所有功能，上游产物进入 AutoSmoke 前必须统一成同一个抽象模型：

```text
原始文档 / DocReader 产物 / 手工用例 / 业务配置
  → autosmoke_upstream_handoff.v1
  → AutoSmoke 转换层
  → AutoSmoke 可执行资产
```

无论功能是活动、神器、背包、商城、战斗还是设置，最终都必须落到：

```text
case_seed_package.v0.json
manual_test_cases.v1.xlsx/json
target_name_catalog.v1.json
source_trace.v1.json
review_items.v1.json
value_assets.v1.json
business_state_contract.v1.json
business_assertions.v1.json
optional_external_refs.v1.json
```

### 15.2 DocReader 当前产物到标准交付包的映射

如果上游提供的是 DocReader 当前输出目录，可按以下规则适配：

| DocReader 当前文件 | 标准交付包文件 | 转换规则 |
|---|---|---|
| `DATA/fact_package.json` | `case_seed_package.v0.json` | `fact_entries` 转成 `business_items`，`fact_objects` 辅助生成 `target_names` |
| `HANDOFF_OUTPUT/structured_business_model.json` | `case_seed_package.v0.json` | `business_flows/config_constraints/exceptions/open_questions` 合并进业务项、关系项、评审项 |
| `HANDOFF_OUTPUT/business_reading.md` | 辅助输入 | 只作为人工阅读摘要，不作为唯一自动化输入 |
| `HANDOFF_OUTPUT/business_reading_render_report.json` | `value_assets.v1.json` | `value_assets` 转成配置、数值、文案、公式资产 |
| `HANDOFF_OUTPUT/fact_filter_report.json` | `case_seed_package.v0.json` / `review_items.v1.json` | included 进入业务项，excluded 仅作背景或忽略 |
| `DATA/evidence.json` | `source_trace.v1.json` | `evidence_id/source_file/raw_text` 转成来源追踪 |
| `DATA/source_index.json` | `source_trace.v1.json` | 构建稳定 `source_ref` |
| `DATA/ui.json` | `target_name_catalog.v1.json` 的辅助输入 | 只能辅助生成目标名，不能替代人工确认 |
| `DATA/flow_candidates.json` | `manual_test_cases` 或 `review_items` 的辅助输入 | 高置信度可生成候选流程，低置信度进入评审 |
| `执行验收报告.md` | `manifest.json` / `review_items.v1.json` | 读取交付等级、PASS/BLOCKED、缺失项 |

### 15.3 自动生成标准包的步骤

AutoSmoke 或上游适配器可以按以下步骤生成标准包：

```text
1. 读取 DocReader 目录
2. 生成 manifest.json
3. 从 fact_package / structured_business_model 生成 case_seed_package.v0.json
4. 从人工用例文件生成 manual_test_cases.v1.xlsx/json
5. 从业务事实、UI 文本、用例目标生成 target_name_catalog.v1.json
6. 从 evidence/source_index 生成 source_trace.v1.json
7. 从 open_questions、缺失目标、缺失配置、外部依赖生成 review_items.v1.json
8. 从 render_report、配置字段、文案字段生成 value_assets.v1.json
9. 从功能逻辑断言、业务字段、状态字段生成 business_state_contract.v1.json
10. 从手工预期、业务规则、配置规则生成 business_assertions.v1.json
11. 从配置表、文案表、状态查询、账号池、时间/网络控制生成 optional_external_refs.v1.json
12. 运行包完整性校验
```

### 15.4 各功能通用准入判断

AutoSmoke 对所有功能使用同一套准入判断：

| 条件 | 结果 |
|---|---|
| 有 A/B 级手工用例、目标名完整、locator 可解析、前置可准备 | `PASS` |
| 有用例和目标名，但部分深状态只能外部查询 | `PASS_WITH_GAP` |
| 只有业务事实，没有手工用例 | `BLOCKED: case_required` |
| 用例中目标名模糊，例如“按钮”“那里”“活动” | `REVIEW/BLOCKED: target_required` |
| 目标名明确，但没有 locator/testId/semanticId 映射 | `BLOCKED: locator_required` |
| 前置账号状态无法准备 | `BLOCKED: state_prepare_required` |
| 关键数值或规则缺配置来源 | `PASS_WITH_GAP` 或 `BLOCKED: config_required` |
| 弱网、断线、杀进程、时间推进无环境能力 | `BLOCKED: environment_required` |
| 要求功能逻辑自动化但缺少状态契约 | `BLOCKED: state_contract_required` |
| 要求功能逻辑自动化但缺少业务断言 | `BLOCKED: business_assertion_required` |
| 业务断言引用了未声明状态路径 | `BLOCKED: STATE_PATH_NOT_DECLARED` |

### 15.5 所有功能的最低可执行闭环

任意功能要进入 AutoSmoke 正式自动执行，最低需要满足：

```text
1. 至少 1 条 A/B 级手工用例
2. 用例中的每个动作都有明确目标名
3. 用例中的每个预期都有可观察目标或外部查询说明
4. target_name_catalog 中能找到所有目标名或别名
5. AutoSmoke 能把目标名解析到 semanticId/testId
6. 点击类目标至少达到 click_confirmed 或 case_verified
7. 页面/状态类目标至少达到 visual_confirmed 或 case_verified
8. 前置状态可准备，或明确 BLOCKED/MANUAL_ONLY
9. 所有阻断项进入 review_items
10. 报告能回溯到 source_trace
11. 如果要求功能逻辑自动化，每条关键步骤都有 before / after 状态采集
12. 如果要求功能逻辑自动化，每条关键步骤都有 business assertion
13. 如果要求功能逻辑自动化，报告包含 state diff、expected、actual、delta
```

---

## 16. 最终结论

当转换层放在 AutoSmoke 时，上游最好的交付不是可执行脚本，也不是最终 AutoSmoke 用例，而是：

```text
autosmoke_upstream_handoff.v1
```

它的必需文件是：

```text
manifest.json
case_seed_package.v0.json
manual_test_cases.v1.xlsx
target_name_catalog.v1.json
source_trace.v1.json
review_items.v1.json
```

增强文件是：

```text
value_assets.v1.json
business_state_contract.v1.json
business_assertions.v1.json
optional_external_refs.v1.json
```

如果目标是 UI 自动化，上游至少提供必需文件即可，AutoSmoke 主要验证：

```text
能否进入页面
能否点击目标
UI 元素是否可见
UI 文案/状态是否变化
```

如果目标是 UI + 功能逻辑自动化，则 `business_state_contract.v1.json` 和 `business_assertions.v1.json` 必须提供，AutoSmoke 需要进一步验证：

```text
点击前业务状态
点击后业务状态
状态 diff
资源/背包/任务/活动/养成等真实状态变化
UI 显示与业务状态是否一致
业务变化是否符合配置或公式
```

责任边界：

```text
上游负责：业务事实、手工用例、目标名、来源、值资产、业务状态契约、业务断言、待确认项
AutoSmoke 负责：动作推断、步骤生成、semanticId/testId 解析、前置状态映射、UI 断言生成、业务断言执行、状态采集、状态 diff、阻断判断、执行报告
```
