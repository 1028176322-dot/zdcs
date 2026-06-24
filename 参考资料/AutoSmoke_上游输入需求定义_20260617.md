# AutoSmoke 上游（DocReader）输入需求定义

> 基于 DocReader 对接交互文档 v0.1 × AutoSmoke 当前实现分析  
> 生成日期：2026-06-17

---

## 1. 核心结论

DocReader 的 `case_seed_package.v0` 与 AutoSmoke 当前输入格式之间存在 **结构化断层**：

```
DocReader v0 输出：
  业务陈述（statement）+ 关系事实（relation）+ 值资产（value_asset）
  ↓  缺少：动作类型、执行顺序、定位信息
  ↓  需要经过 "业务陈述 → 步骤序列" 转换
AutoSmoke 输入：
  action + target + assertions 的显式步骤序列
```

**AutoSmoke 当前不能直接消费 `case_seed_package.v0`**。需要定义一个新的中间层 `auto_smoke_case_seed.v1`，或者由下游（AutoSmoke 自身或一个专门的转换器）将 DocReader 的资产转化为 AutoSmoke 可执行的步骤格式。

---

## 2. AutoSmoke 当前输入格式（写死的要求）

### 2.1 步骤级输入（case_step_parser）

```python
# === 动作枚举 ===
ACTION_KEYWORDS = {
    "点击": "click",           # 必需 target
    "等待": "wait",            # 必需 seconds
    "断言存在": "assert_exists",   # 必需 target
    "断言不存在": "assert_not_exists",  # 必需 target
    "截图": "screenshot",      # 无参数
    "返回": "back",            # 无参数
    "长按": "long_press",      # 必需 target
    "滑动": "swipe",           # 必需 start + end 坐标
    "输入": "input",           # 可选 target + value
}
```

### 2.2 定位类型（target_locator 消费）

```python
# === 7 种定位格式 ===
# text:        OCR 文本定位
"target": {"type": "text", "value": "使用"}

# template:   模板匹配定位（需 templates/ 下有对应截图）
"target": {"type": "template", "value": "use_button"}

# testId:     Unity 元数据定位（需 element_mapping 已标注）
"target": {"type": "testId", "value": "bag.button.use"}

# normalized: 归一化坐标 [0,1]
"target": {"type": "normalized", "nx": 0.5, "ny": 0.95}

# design:     设计分辨率坐标
"target": {"type": "design", "x": 585, "y": 2400}

# content:    GameContent 内坐标
"target": {"type": "content", "x": 160, "y": 665}

# pixel:      屏幕像素坐标
"target": {"type": "pixel", "x": 100, "y": 200}
```

### 2.3 用例级输入（batch_runner）

```python
# === 当前支持的两种输入方式 ===

# 方式一：文本列表
"TC001": [
    "点击 normalized(0.5,0.5)",
    "等待 2 秒",
    "断言存在 text(\"使用\")",
    "截图",
]

# 方式二：Excel 行（解析为字典列表）
[
    {"用例ID": "TC001", "操作步骤": "点击 normalized(0.5,0.5)", "模块": "背包"},
    {"用例ID": "TC001", "操作步骤": "等待 2 秒", ...},
    {"用例ID": "TC001", "操作步骤": "断言存在 text(\"使用\")", ...},
]
```

### 2.4 元素映射（element_mapping）

```python
# === 元素映射数据模型 ===
{
    "elementPath": "Canvas/BagPanel/ButtonUse",       # Poco 路径
    "name": "ButtonUse",                             # 节点名
    "type": "Button",                                # 元素类型
    "clickable": true,                               # 是否可点击
    "screenRect": [464, 2380, 706, 2490],            # 屏幕矩形
    
    "displayName": "使用按钮",                        # 中文展示名
    "testId": "bag.button.use",                      # Unity testId
    "role": "action",                                # 角色（action/navigation/display/input）
    "pageId": "bag_page",                            # 页面归属
    "meaning": "使用选中的道具",                      # 语义描述
    
    "source": "manual_confirmed",                    # 来源
    "mappedAt": "2026-06-15T12:00:00"               # 映射时间
}
```

---

## 3. DocReader 当前能提供 vs AutoSmoke 需要的映射分析

| 信息维度 | DocReader 能提供 | AutoSmoke 需要 | 差距 |
|----------|:---------------:|:--------------:|:----:|
| 功能块/模块名（block_name） | ✅ `"驻防按钮"` | ✅ 可映射到 case 的分组/模块 | ⚠️ 需要约定 pageId/模块名映射 |
| 业务陈述（statement） | ✅ `"驻防按钮显示驻防人数信息"` | ❌ 不能直接当步骤 | 需要拆分为步骤序列 |
| 动作类型 | ❌ 无显式 action_type | ✅ 必须（click/wait等） | **最大缺口** |
| 执行顺序 | ❌ 无 step_order | ✅ 必须显式排序 | **必须补齐** |
| UI 目标（target） | ⚠️ 隐含在 statement 中 | ✅ 必须显式（testId/text等） | **需要从陈述中提取+映射** |
| 定位信息（locator） | ❌ 文档不含 | ✅ 必须（testId/pocoPath等） | 需从 element_mapping 补充 |
| 前置条件 | ⚠️ 部分可推断 | ✅ 需要显式 | 需要环境初始化流程 |
| 预期结果 | ⚠️ 部分（preserved_assets） | ✅ 需要（assert） | 需要转换规则 |
| 断言类型 | ❌ 不区分类型 | ✅ 必须（UI/数值/状态等） | **需要定义断言映射规则** |
| 数据/配置值 | ⚠️ 值资产（value_asset） | ✅ 需要解析到具体值 | 需连接配置表 |
| 来源追踪 | ✅ source_refs + evidence_ref | ✅ 可在报告中保留 | ✅ 可直接复用 |
| UI 文案格式 | ✅ preserved_assets | ✅ 可用于 UI 文案断言 | ✅ 可直接复用 |
| 准入门槛 | ✅ admission | ✅ 影响是否生成脚本 | ✅ 可直接复用 |

---

## 4. AutoSmoke 对上游（DocReader）的必要输入格式定义

### 4.1 建议新增中间格式：`auto_smoke_case_seed.v1`

```json
{
  "schema_version": "auto_smoke_case_seed.v1",
  "generated_from": "doc_reader_case_seed_v0",
  "doc_source": "策划文档名称_v1.2",
  "feature_name": "主城驻防",
  
  "admission": {
    "manual_case_generation": "PASS_WITH_GAP",
    "automation_script_generation": "BLOCKED",
    "blocked_reasons": [
      "缺少部分 UI locator 映射",
      "服务器配置取值需外部确认"
    ]
  },
  
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
  
  "test_cases": [
    {
      "case_id": "TC_GARRISON_001",
      "feature": "主城驻防",
      "title": "驻防按钮显示驻防人数信息",
      "steps": [
        {
          "step_order": 1,
          "action_type": "click",
          "target": {
            "type": "testId",
            "value": "maincity.garrison.button",
            "fallback": [
              {"type": "poco", "value": "MainCityUI/GarrisonPanel/GarrisonButton"},
              {"type": "text", "value": "驻防"}
            ]
          },
          "preconditions": [
            {"type": "element_visible", "target_type": "testId", "target_value": "maincity.garrison.button"}
          ],
          "expected": {
            "type": "element_visible",
            "target_type": "testId",
            "target_value": "maincity.garrison.panel",
            "description": "驻防面板打开"
          },
          "assertions": [
            {
              "assertion_type": "ui_display_assertion",
              "raw_expression": "当前驻防人数/可驻防上限",
              "display_format": "数字/数字",
              "description": "驻防按钮上显示驻防人数信息"
            }
          ],
          "timeout_ms": 5000,
          "on_failure": "stop"
        },
        {
          "step_order": 2,
          "action_type": "screenshot",
          "description": "验证完成后截图留痕"
        }
      ],
      "data_dependencies": [],
      "source_refs": [
        {
          "evidence_ref": "EVD_0051",
          "doc_source": "规则表",
          "row_number": 51,
          "excerpt": "驻防按钮:当前驻防人数/可驻防上限"
        }
      ]
    }
  ],

  "value_assertions": [
    {
      "name": "行军时间检查",
      "expression": "行军时间 > {config:garrison_march_time_min}",
      "value_type": "numeric",
      "source_expression": "行军时间 > X",
      "variables": [
        {
          "var_name": "X",
          "config_source": "D2Config",
          "config_key": "garrison.march_time_min",
          "default_value": null,
          "resolution_status": "config_required"
        }
      ]
    }
  ],

  "external_requirements": [
    {
      "requirement_type": "config_query",
      "description": "D2Config.garrison.march_time_min",
      "resolution_status": "config_required",
      "blocking": true
    },
    {
      "requirement_type": "locator",
      "description": "驻防弹窗确认按钮 locator",
      "hint_name": "驻防弹窗.确认按钮",
      "resolution_status": "locator_required",
      "blocking": true
    }
  ]
}
```

### 4.2 字段说明与必要性

#### 必要字段（non-blocking = false，缺失则阻断）

| 字段路径 | 格式 | 说明 | 来源 |
|----------|------|------|:----:|
| `test_cases[].case_id` | string | 用例唯一 ID | DocReader 生成 |
| `test_cases[].steps[].action_type` | enum | click/wait/assert_exists/assert_not_exists/screenshot/back/input | **必须由上游或转换器推断** |
| `test_cases[].steps[].target.type` | enum | testId/poco/text/template/normalized/design/content | **必须由上游或转换器推断** |
| `test_cases[].steps[].target.value` | string | 根据 type 不同取值 | 从 statement 提取 + element_mapping |
| `admission.automation_script_generation` | enum | PASS/PASS_WITH_GAP/BLOCKED | DocReader 评估 |

#### 强烈建议字段（缺失时降级运行）

| 字段路径 | 格式 | 说明 |
|----------|------|------|
| `test_cases[].steps[].expected.type` | string | 预期结果类型 |
| `test_cases[].steps[].expected.target_type` | string | 预期目标类型 |
| `test_cases[].steps[].expected.target_value` | string | 预期目标值 |
| `test_cases[].steps[].assertions[].assertion_type` | enum | ui_display_assertion / numeric / state / interface |
| `test_cases[].steps[].timeout_ms` | int | 步骤超时 |
| `test_cases[].steps[].on_failure` | enum | stop/retry/continue |
| `element_mapping_hints[].hint_name` | string | 元素中文名（用于人工审核和映射） |
| `element_mapping_hints[].candidate_test_id` | string | 建议的 testId |
| `element_mapping_hints[].candidate_poco_path` | string | 建议的 Poco 路径 |
| `element_mapping_hints[].page_id` | string | 页面归属 |
| `value_assertions[].expression` | string | 值断言表达式（如 `行军时间 > {config:XXX}`） |
| `source_refs` | array | 来源追踪（保留到报告） |

#### 可选字段（增强体验）

| 字段路径 | 说明 |
|----------|------|
| `test_cases[].title` | 用例标题（从 statement 截取） |
| `test_cases[].feature` | 功能归属 |
| `test_cases[].preconditions` | 前置条件列表 |
| `value_assertions[].variables[].config_key` | 配置表 key 引用 |
| `external_requirements[].requirement_type` | 外部依赖类型 |
| `element_mapping_hints[].meaning` | 元素语义描述（直接写入 element_mapping.meaning） |

### 4.3 业务陈述 → 步骤序列 转换规则

DocReader 的 `statement` 不能直接被 AutoSmoke 消费，需要按以下规则转换：

```
规则表（从业务陈述推断动作和定位）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
statement 包含关键词       → 推断动作       → 推断目标
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"按钮" + "点击/打开/确认"    → click          → buttonName
"按钮" + "显示/展示"        → assert_exists  → buttonName + display check
"弹窗" + "出现/打开"        → wait + assert   → popup check
"输入/填写"                → input           → field name
"选择/选项"               → click          → option name
"XX 页/XX 界面/XX 面板"    → assert_exists  → page check
"等待 XX 秒"              → wait           → seconds
"截图/截屏"               → screenshot     → (无需目标)
"返回/关闭"               → back           → (无需目标)
"数量/值/数值"            → assert         → value expression
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**示例转换：**

| DocReader statement | 转换后步骤 |
|---------------------|-----------|
| `"驻防按钮显示驻防人数信息"` | `[assert_exists(testId="garrison.button"), ui_display_assert("当前驻防人数/可驻防上限")]` |
| `"点击驻防按钮打开驻防弹窗"` | `[click(testId="garrison.button"), wait(1s), assert_exists(testId="garrison.panel")]` |
| `"行军时间大于 X 时弹窗提示"` | `[click(testId="march.button"), assert(value_expression="行军时间 > {config:X}")]` |
| `"等待 3 秒后确认奖励到账"` | `[wait(3s), assert_exists(testId="reward.confirm")]` |

---

## 5. 上游必须补齐的信息缺口

### 5.1 P0 级（无此信息 AutoSmoke 无法生成可执行步骤）

| 缺口 | 说明 | 建议补齐方式 |
|------|------|------------|
| **action_type** | 每步必须明确动作类型 | DocReader 或专门的转换器按规则表推断 |
| **target 格式** | 必须符合 AutoSmoke 的 7 种定位类型之一 | 从 statement 提取目标名，通过 element_mapping 查到 testId/pocoPath |

### 5.2 P1 级（缺失时降级运行）

| 缺口 | 说明 | 建议补齐方式 |
|------|------|------------|
| **step_order** | 步骤执行顺序 | DocReader 保持业务流顺序，或转换器排序 |
| **testId 或 pocoPath** | 自动化定位最稳定的方式 | 从 element_mapping_hints 的 candidate_test_id 导入 |
| **page_id** | 页面归属，辅助定位 | DocReader 从文档结构推断 |

### 5.3 P2 级（缺失时人工审核后可运行）

| 缺口 | 说明 |
|------|------|
| **expected + assertion** | 预期结果和断言类型 |
| **value_assertions 的变量解析** | 配置表查询、文案 KEY 映射 |
| **preconditions** | 前置条件（需环境初始化线程） |

---

## 6. 建议的对齐路径

```
当前状态：
  DocReader: case_seed_package.v0（业务事实）
  AutoSmoke: 期待显式步骤序列
  中间断层：缺少 action_type + target + step_order

建议实施顺序：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
阶段 1：定义中间格式
  输出：auto_smoke_case_seed.v1 schema
  动作：编写 formal_schema.json，双方确认字段
  产出：两个工具的接口规范

阶段 2：编写转换器（DocReader → AutoSmoke 中间格式）
  输出：doc_reader_to_auto_smoke.py
  动作：
    · 将 business_items → test_cases + steps
    · 按规则表推断 action_type 和 target
    · 将 source_refs 保留到每步
    · 输出 auto_smoke_case_seed.v1.json
  产出：转换器脚本 + 手动测试样例

阶段 3：编写导入器（中间格式 → AutoSmoke 执行）
  输出：IDE debug_panel API 新路由 /api/case/import_from_case_seed
  动作：
    · 读取 case_seed 的 test_cases
    · 解析 steps → case_step_parser 可消费格式
    · 使用 target_locator 定位元素
    · 使用 element_mapping 对照 candidate 补充映射
  产出：IDE 可一键导入 case_seed 并执行

阶段 4：试跑
  动作：
    · 提供 1 份真实游戏文档 → DocReader 输出 case_seed
    · 转换器 → auto_smoke_case_seed.v1
    · 导入 AutoSmoke IDE → 执行
    · 记录失败步骤和原因
  产出：闭环结果 + 差距清单

阶段 5：迭代
  动作：
    · 根据试跑结果调整规则表
    · 补齐 element_mapping_hints 的 testId 映射
    · 处理 value_assertions 的配置表查询
  产出：v1.1 alignment 完成
```

---

## 7. 关键接口协议总结

| 层面 | 协议格式 | 必须字段 | 产生方 | 消费方 |
|------|:--------:|:--------:|:------:|:------:|
| 原始文档事实 | `case_seed_package.v0` | business_items + admission | DocReader | 转换器 |
| 可执行用例种子 | `auto_smoke_case_seed.v1`（新增） | case_id + action_type + target | 转换器 | AutoSmoke |
| 元素映射 | `element_mapping.json`（已有） | testId + pageId + role | AutoSmoke IDE 审核 | target_locator |
| 增强 UI 树 | `enhanced_ui_tree.json`（已有） | elementType + priority + confidence | AutoSmoke 元数据 | element_mapping |
| Excel 用例 | `.xlsx`（已有） | 用例ID + 操作步骤 | 手工编写 / DocReader 生成 | batch_runner |

---

## 8. 最小可行接口（第一阶段可交付）

如果第一阶段只要求 AutoSmoke 能消费 DocReader 的 v0 输出，最小接口可以简化为：

```json
{
  "schema_version": "auto_smoke_case_seed.v1",
  "feature_name": "示例功能",
  "test_cases": [
    {
      "case_id": "TC_001",
      "title": "按钮显示信息",
      "admission": "PASS_WITH_GAP",
      "blocked_reasons": ["缺少.locator"],
      "steps": [
        "点击 testId(\"maincity.garrison.button\")",
        "等待 1 秒",
        "截图"
      ],
      "source_refs": [],
      "element_mapping_hints": []
    }
  ]
}
```

这个格式可以直接被 `batch_runner.run_steps_dict()` 消费：
```python
case_step_dict = {
    "TC_001": [
        "点击 testId(\"maincity.garrison.button\")",
        "等待 1 秒",
        "截图"
    ]
}
runner.run_steps_dict(case_step_dict)
```
