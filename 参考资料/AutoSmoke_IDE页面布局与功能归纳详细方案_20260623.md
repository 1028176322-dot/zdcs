# AutoSmoke IDE 页面布局与功能归纳详细方案

> 日期：2026-06-23  
> 定位：AutoSmoke IDE 是自动化测试集成工具，不是单纯的元素映射工具。  
> 目标：让 IDE 支持从数据准备、元素映射、用例管理、自动执行、业务验证、报告分析到问题修复的完整闭环，同时避免界面被调试入口和低频工具淹没。

---

## 1. IDE 产品定位

AutoSmoke IDE 的定位应是：

```text
自动化测试集成控制台
```

它要覆盖完整链路：

```text
项目准备
  → UI / 代码 / 运行态数据采集
  → 元素语义映射
  → 手工用例导入与转换
  → 自动化步骤生成
  → UI 自动执行
  → 业务状态采集与断言
  → 报告输出
  → 问题修复
```

因此，IDE 不应精简成“只做 testId 映射”的小工具。正确方向是：

```text
能力保留
入口分层
主流程清晰
高级调试折叠
低频功能隐藏
重复按钮合并
```

---

## 2. 总体页面结构

推荐采用顶部一级导航 + 左侧上下文列表 + 右侧工作区的结构。

一级导航建议：

```text
1. 总览
2. 项目准备
3. 元素映射
4. 用例管理
5. 执行中心
6. 业务验证
7. 报告中心
8. 问题修复
9. 高级工具
```

每个一级页面只服务一个明确目标，避免所有按钮堆在一个页面。

---

## 3. 总览页

### 3.1 页面目标

总览页回答一个问题：

```text
当前项目是否已经具备自动化测试执行条件？
```

### 3.2 页面布局

```text
总览
├── 项目状态卡片
├── 自动化准入状态
├── 当前任务进度
├── 快捷入口
└── 最近报告 / 最近阻断
```

### 3.3 状态卡片

展示：

```text
Unity / GameView 状态
Bridge 连接状态
UI 数据状态
代码语义状态
MappingStore 状态
用例导入状态
业务状态采集状态
最近一次执行结果
```

示例：

```text
UI 数据：已同步，更新时间 2026-06-23 09:51
元素映射：formal 128 条，待确认 420 条，ignored 80 条
用例：已导入 35 条，P0 8 条
准入：PASS_WITH_GAP，缺少 2 个业务状态查询能力
```

### 3.4 快捷入口

只保留高频入口：

```text
刷新 UI 数据
进入元素映射
导入用例
运行用例
查看失败项
查看报告
```

不放：

```text
API 调试
页面关系图
手工 JSON 导入
截图对比
部署脚本细项
```

这些放到高级工具。

---

## 4. 项目准备页

### 4.1 页面目标

项目准备页负责把测试环境、项目数据、运行态数据准备好。

### 4.2 页面布局

```text
项目准备
├── 环境连接
├── UI 数据同步
├── 代码语义同步
├── MappingStore 状态
├── 账号 / 场景准备
└── 准备结果
```

### 4.3 环境连接

展示：

```text
Unity 编辑器状态
GameView 定位状态
Bridge 状态
截图能力状态
点击注入能力状态
运行态 UI 树状态
```

保留按钮：

```text
刷新连接状态
重新定位 GameView
刷新运行态 UI
截图测试
点击注入测试
```

隐藏到高级工具：

```text
部署检查
一键部署
Bridge 原始日志
定位诊断明细
```

### 4.4 UI 数据同步

主按钮合并为：

```text
刷新 UI 元素
```

点击后按内部流程执行：

```text
1. 刷新运行态 UI
2. 读取当前 UI
3. 同步 enhanced_ui_tree
4. 生成/更新 draft
5. 更新 MappingStore index
```

高级选项折叠：

```text
仅扫描 UI 树
仅扫描 Prefab
导入 Project
导入 Current
导入 Runtime
导入 Pages
手工导入 JSON
查看导入报告
```

### 4.5 代码语义同步

保留：

```text
同步当前页面代码语义
重建代码语义索引
查询当前页面语义
```

展示：

```text
ui_code_semantics 状态
当前 pageId
可用代码语义数量
最近构建时间
```

### 4.6 MappingStore 状态

展示：

```text
store 是否启用
draft 分片数量
formal 分片数量
evidence 文件数量
索引状态
旧文件兼容导出状态
是否存在绝对路径残留
```

保留按钮：

```text
检查存储
重建索引
导出兼容旧文件
检查绝对路径
```

---

## 5. 元素映射页

### 5.1 页面目标

元素映射页负责：

```text
把业务目标名 / 手工用例目标 / UI 元素匹配到 semanticId 和 testId
```

这是 IDE 的核心页面之一。

### 5.2 页面布局

推荐三栏结构：

```text
元素映射
├── 左栏：页面 / 目标列表
├── 中栏：候选元素 / UI 树 / 运行态匹配
└── 右栏：详情编辑 / 验证证据 / 操作按钮
```

### 5.3 左栏：页面 / 目标列表

顶部：

```text
页面筛选
状态筛选
关键词搜索
优先级筛选
```

页面列表来源：

```text
mapping_store/indexes/page.index.json
```

目标列表展示：

```text
targetName
pageId
status
候选数量
是否 formal
是否 evidence 完整
是否被用例引用
```

状态分类：

```text
待处理
候选已匹配
运行态已匹配
高亮已确认
点击已确认
用例已验证
已忽略
已拒绝
阻断
```

### 5.4 中栏：候选匹配区

展示候选来源：

```text
MappingStore draft
运行态 UI
代码语义
UI 文本
历史 formal
动态列表模板
```

候选卡片字段：

```text
候选路径
nodeName
displayName
pageId
role
elementType
score
reasons
risks
runtimePath
screenRect
```

操作：

```text
选择候选
运行态匹配
生成高亮
测试点击
查看详情
```

### 5.5 右栏：详情编辑区

分为简单模式和高级模式。

简单模式字段：

```text
中文描述
目标名称 targetName
所属页面 pageId
控件角色 role
控件类型 elementType
```

高级模式字段：

```text
testId
semanticId
locator
fallbackLocators
runtimePath
elementPath
evidenceRef
source
reviewStatus
```

中文描述输入示例：

```text
神器界面强化按钮
背包界面金币途径按钮
联盟科技界面捐献按钮
```

IDE 自动解析：

```text
pageId
targetName
displayName
semanticId
testId 候选
role
elementType
所属界面文件
```

### 5.6 右栏操作按钮

主按钮只保留一个：

```text
下一步
```

根据当前状态自动变化：

```text
pending              → 匹配候选
候选已选择           → 运行态匹配
runtime_matched      → 生成高亮
highlight_generated  → 视觉确认
visual_confirmed     → 测试点击
click_confirmed      → 保存 formal
formal_saved         → 完成
```

辅助按钮：

```text
保存
忽略
拒绝
手动补充
重新匹配
```

高级按钮折叠：

```text
结构确认
强制确认
同步重命名 testId
迁移引用
查看原始 JSON
```

---

## 6. 用例管理页

### 6.1 页面目标

用例管理页负责：

```text
导入手工用例
解析自然语言步骤
抽取目标名
生成自动化候选步骤
发现缺失映射和阻断项
```

### 6.2 页面布局

```text
用例管理
├── 用例导入
├── 用例列表
├── 用例解析结果
├── 目标抽取
├── 自动化步骤预览
└── review_items
```

### 6.3 用例导入

支持：

```text
xlsx
json
csv
DocReader handoff package
```

展示：

```text
用例总数
P0/P1/P2 数量
A/B/C/D 质量等级
可自动化数量
阻断数量
```

### 6.4 用例解析结果

每条用例展示：

```text
CaseID
优先级
模块
前置条件
操作步骤
预期结果
解析动作
解析目标
断言类型
需要的 testId
```

### 6.5 目标抽取

从用例中抽取：

```text
目标名称
动作类型
断言对象
页面 hint
role hint
source_ref
```

操作：

```text
生成目标任务
匹配已有 formal
进入元素映射
生成 review_items
```

### 6.6 自动化步骤预览

展示转换后的步骤：

```text
点击 testId("artifact.upgrade.enhance.button")
等待状态稳定
断言 UI 数值变化
断言业务状态变化
截图
```

如果缺失映射：

```text
BLOCKED: locator_required
```

如果缺失业务状态：

```text
PASS_WITH_GAP: state_query_required
```

---

## 7. 执行中心页

### 7.1 页面目标

执行中心负责：

```text
运行单用例
运行批量用例
执行单步调试
查看执行队列
失败重跑
```

### 7.2 页面布局

```text
执行中心
├── 执行配置
├── 单用例执行
├── 批量执行
├── 单步调试
├── 实时监控
└── 执行日志
```

### 7.3 执行配置

配置项：

```text
运行环境
账号
服务器
失败是否停止
失败是否重跑
是否执行 UI 断言
是否执行业务断言
是否截图
是否保存日志
```

### 7.4 单用例执行

展示：

```text
用例选择
运行按钮
执行进度
当前步骤
步骤结果
失败原因
```

### 7.5 批量执行

展示：

```text
批次名称
用例范围
优先级筛选
运行进度
通过/失败/阻断数量
失败重跑
```

### 7.6 单步调试

保留，但不要放在主视觉中心。

用于：

```text
点击 testId(...)
等待
截图
断言 UI
断言业务状态
```

不要展示太多快捷按钮，避免变成调试面板。

---

## 8. 业务验证页

### 8.1 页面目标

业务验证页负责：

```text
业务状态采集
before / after 快照
状态 diff
business_assertions
UI 与业务状态一致性
```

### 8.2 页面布局

```text
业务验证
├── 状态采集契约
├── 状态快照
├── 状态 Diff
├── 业务断言
├── 外部依赖
└── 断言失败分析
```

### 8.3 状态采集契约

对应文件：

```text
business_state_contract.v1.json
```

展示：

```text
domain
path
collector
source
required
stability
required_for
```

例如：

```text
resources.gold
bag.items[itemId=artifact_crystal].count
artifact.current.progress
ui.currentPage
ui.popupStack
```

### 8.4 业务断言

对应文件：

```text
business_assertions.v1.json
```

展示：

```text
assertion_id
case_id
step_order
path
operator
expected
actual
before
after
delta
result
```

### 8.5 状态 Diff

展示：

```text
resources.gold: 1000 → 900, delta -100
artifact.current.progress: 20 → 30, delta +10
bag.items[itemId=artifact_crystal].count: 10 → 9, delta -1
```

### 8.6 外部依赖

展示：

```text
配置表
文案表
服务端状态查询
DB 查询
日志查询
账号资产准备
时间控制
网络控制
```

不能满足时自动生成：

```text
review_items
```

---

## 9. 报告中心页

### 9.1 页面目标

报告中心负责：

```text
查看执行结果
定位失败原因
导出报告
生成失败包
回溯证据
```

### 9.2 页面布局

```text
报告中心
├── 最近执行
├── 用例结果
├── 失败列表
├── 阻断列表
├── 证据查看
└── 导出
```

### 9.3 报告内容

每条用例展示：

```text
CaseID
结果 PASS / FAIL / BLOCKED / PASS_WITH_GAP
步骤数
失败步骤
失败原因
截图
高亮图
点击日志
业务状态 diff
review_items
source_trace
```

### 9.4 导出能力

保留：

```text
导出 HTML 报告
导出 JSON 报告
导出失败包
```

---

## 10. 问题修复页

### 10.1 页面目标

问题修复页负责把执行失败、映射缺失、业务状态缺失转成可处理任务。

### 10.2 页面布局

```text
问题修复
├── 修复任务列表
├── 映射缺失
├── evidence 缺失
├── locator 失败
├── 业务状态缺失
├── 配置缺失
└── 一键跳转处理
```

### 10.3 修复任务来源

```text
mapping gate
case run failure
business assertion failure
review_items
MappingStore 检查
revalidate 结果
```

### 10.4 修复动作

```text
进入元素映射
重新运行态匹配
重新高亮确认
重新测试点击
补充业务状态路径
补充配置引用
忽略该目标
标记人工测试
```

---

## 11. 高级工具页

### 11.1 页面目标

高级工具页保留低频、调试、诊断能力，但不干扰主流程。

### 11.2 功能归纳

```text
高级工具
├── 原始 UI 数据
│   ├── 仅扫描 UI 树
│   ├── 仅扫描 Prefab
│   ├── 导入 Project
│   ├── 导入 Current
│   ├── 导入 Runtime
│   ├── 导入 Pages
│   └── 手工导入 JSON
├── 页面关系图
│   ├── 查看关系图
│   └── 开始探索
├── 代码语义
│   ├── 重建语义
│   ├── 查询当前页面
│   └── 查询元素
├── 截图与视觉
│   ├── Before
│   ├── After
│   ├── 对比
│   └── 查看原图
├── 异常与阻塞
│   ├── 异常检测
│   ├── 阻塞检测
│   └── 阻塞处理
├── 部署与预检
│   ├── 部署检查
│   ├── 一键部署
│   └── 预检导出
├── API 调试
│   ├── API 选择器
│   └── 原始返回
└── 存储维护
    ├── MappingStore 状态
    ├── 重建索引
    ├── 导出旧 JSON
    ├── 检查绝对路径
    └── 页面分片整理
```

---

## 12. 当前功能精简归纳

### 12.1 保留为主功能

```text
刷新 UI 元素
代码语义同步
MappingStore 状态
目标列表
候选匹配
中文语义修正
运行态匹配
高亮确认
测试点击
保存 formal
用例导入
用例执行
批量执行
业务断言
报告查看
问题修复
```

### 12.2 移入高级工具

```text
页面关系图
自动探索
高级导入
仅扫描 UI 树
仅扫描 Prefab
导入 Project / Current / Runtime / Pages
手工导入 JSON
截图对比
异常检测
阻塞检测
部署检查
API 调试
metadata 原始搜索
accessibility scan
```

### 12.3 合并入口

```text
生成增强UI树 + 从增强UI树生成草稿
→ 刷新 UI 元素

结构确认 + 视觉确认 + 点击确认
→ 下一步确认

高亮确认 + 视觉确认
→ 生成高亮并确认

测试点击 + 点击确认
→ 测试点击，通过后确认

mapping_store status + rebuild + compaction
→ 存储维护
```

### 12.4 不建议直接删除

这些功能低频，但排查问题时有价值：

```text
页面关系图
自动探索
截图对比
异常检测
阻塞检测
API 调试
原始导入
```

建议隐藏，不建议删除。

---

## 13. 推荐主流程

### 13.1 UI 自动化流程

```text
1. 项目准备：刷新 UI 元素
2. 元素映射：选择页面
3. 元素映射：选择目标
4. 元素映射：匹配候选
5. 元素映射：生成高亮
6. 元素映射：测试点击
7. 元素映射：保存 formal
8. 用例管理：导入用例
9. 执行中心：运行用例
10. 报告中心：查看结果
```

### 13.2 UI + 功能逻辑自动化流程

```text
1. 项目准备：刷新 UI 元素
2. 项目准备：同步代码语义
3. 元素映射：完成 testId 映射
4. 用例管理：导入用例
5. 业务验证：加载 business_state_contract
6. 业务验证：加载 business_assertions
7. 执行中心：运行用例
8. 执行中心：采集 before / after 状态
9. 业务验证：执行状态 diff 和业务断言
10. 报告中心：查看 UI + 业务结果
11. 问题修复：处理失败和阻断项
```

---

## 14. 页面布局草图

### 14.1 顶部导航

```text
[总览] [项目准备] [元素映射] [用例管理] [执行中心] [业务验证] [报告中心] [问题修复] [高级工具]
```

### 14.2 元素映射页布局

```text
┌──────────────────────────────────────────────────────────────┐
│ 页面筛选  状态筛选  搜索  批量推荐  批量忽略                  │
├───────────────┬───────────────────────┬──────────────────────┤
│ 页面/目标列表 │ 候选元素 / UI树 / 高亮 │ 详情编辑 / 证据 / 操作 │
│               │                       │                      │
│ bag           │ 候选1 score 0.92       │ 中文描述              │
│ artifact      │ 候选2 score 0.81       │ targetName            │
│ shop          │ 运行态匹配结果         │ pageId / role         │
│               │ 高亮图                 │ testId / semanticId   │
│               │                       │ [下一步] [保存] [忽略]│
└───────────────┴───────────────────────┴──────────────────────┘
```

### 14.3 执行中心页布局

```text
┌──────────────────────────────────────────────────────────────┐
│ 执行配置：环境 账号 失败策略 UI断言 业务断言 截图 日志        │
├───────────────────────────────┬──────────────────────────────┤
│ 用例列表 / 批次                │ 实时执行详情                 │
│ P0 / P1 / P2                  │ 当前步骤                     │
│ PASS / FAIL / BLOCKED         │ 截图                         │
│                               │ 日志                         │
│                               │ 状态 diff                    │
└───────────────────────────────┴──────────────────────────────┘
```

### 14.4 业务验证页布局

```text
┌──────────────────────────────────────────────────────────────┐
│ 状态域筛选  caseId筛选  step筛选  只看失败                   │
├───────────────┬───────────────────────┬──────────────────────┤
│ 状态路径       │ before / after / diff │ 业务断言结果          │
│ resources.gold│ 1000 -> 900 (-100)     │ decreasedBy 100 PASS  │
│ artifact.progress│ 20 -> 30 (+10)     │ increased PASS        │
└───────────────┴───────────────────────┴──────────────────────┘
```

---

## 15. 最终建议

AutoSmoke IDE 的最终形态应该是：

```text
自动化测试集成控制台
```

而不是：

```text
调试按钮集合
```

也不是：

```text
单纯元素映射工具
```

最终页面应围绕自动化测试闭环组织：

```text
准备 → 映射 → 用例 → 执行 → 业务验证 → 报告 → 修复
```

精简原则：

```text
核心链路放主导航
低频调试放高级工具
重复入口合并
危险操作隐藏
原始 JSON 和路径细节不暴露给普通使用流程
```

---

## 16. 按 QA_Reader 回执后的界面更新

### 16.1 是否需要更新

需要更新，但不需要推翻当前设计。

当前页面方案已经覆盖：

```text
项目准备
元素映射
用例管理
执行中心
业务验证
报告中心
问题修复
高级工具
```

这些主模块仍然成立。QA_Reader 回执带来的变化是：IDE 不能只支持“导入用例后执行”，还必须显式承接：

```text
handoff 包导入
handoff schema 校验
UI_ONLY / UI_AND_BUSINESS 分级准入
用例转换预览
目标绑定队列
页面流转预览
测试数据准备状态
业务断言覆盖
阻断 / 降级项处理
QA_Reader 可读回执导出
```

因此，界面设计需要从：

```text
准备 → 映射 → 用例 → 执行 → 业务验证 → 报告 → 修复
```

升级为：

```text
上游包 → 准入校验 → 转换预览 → 目标绑定 → 执行计划 → 执行 → 业务验证 → 报告 → 修复
```

### 16.2 顶部导航建议调整

原导航：

```text
[总览] [项目准备] [元素映射] [用例管理] [执行中心] [业务验证] [报告中心] [问题修复] [高级工具]
```

建议调整为：

```text
[总览] [上游包] [项目准备] [用例管理] [元素映射] [执行中心] [业务验证] [报告中心] [问题修复] [高级工具]
```

如果第一阶段不想新增一级页面，也可以先把“上游包”作为“用例管理”的第一个 Tab。但长期建议独立出来，因为它负责的是准入和转换，不只是用例列表。

### 16.3 新增：上游包页

#### 页面目标

上游包页负责导入 QA_Reader 生成的 handoff 包，并判断它能否进入 AutoSmoke 转换和执行。

它回答：

```text
包是否完整？
功能流是否已审核？
能支持 UI_ONLY 还是 UI_AND_BUSINESS？
哪些问题会阻断执行？
哪些问题可以降级？
哪些问题需要上游补充？
哪些问题由 AutoSmoke 绑定处理？
```

#### 页面布局

```text
上游包
├── 包导入
├── 包信息
├── 文件覆盖
├── schema 校验
├── 准入结果
├── 阻断 / 降级项
├── 转换入口
└── 回执导出
```

#### 包导入

普通用户只需要选择：

```text
handoff 目录
manifest.json
```

不建议让普通用户逐个导入 JSON 文件。

#### schema 校验

展示：

```text
manifest 是否存在
feature_id 是否一致
required_files 是否齐全
case_id 是否唯一
target_id 是否唯一
用例步骤 target_name 是否存在于 target_name_catalog
assertion_refs 是否能找到对应 business_assertions
business_assertions 引用的 state_path 是否在 business_state_contract 中声明
source_trace 覆盖率
review_items blocker 数量
```

#### 准入状态

IDE 应展示明确准入状态：

```text
READY_UI_ONLY
READY_UI_AND_BUSINESS
PASS_WITH_GAP
BLOCKED
MANUAL_ONLY
```

示例显示：

```text
当前包可执行 UI 自动化。
业务逻辑自动化降级：缺少 business_state_contract.v1.json 和 business_assertions.v1.json。
```

#### 转换入口

按钮：

```text
生成用例转换预览
生成目标绑定任务
生成执行计划
进入用例管理
进入目标绑定队列
进入业务验证
```

按钮受准入状态控制：

```text
BLOCKED：不允许生成正式执行计划
PASS_WITH_GAP：允许生成降级执行计划
READY_UI_ONLY：只生成 UI 执行计划
READY_UI_AND_BUSINESS：生成 UI + 业务断言执行计划
```

### 16.4 总览页需要增加的状态

总览页新增状态卡片：

```text
上游包：未导入 / 已导入 / 校验失败 / 校验通过
handoff 校验：PASS / PASS_WITH_GAP / BLOCKED
准入等级：READY_UI_ONLY / READY_UI_AND_BUSINESS / MANUAL_ONLY
转换状态：未转换 / 已转换 / 部分转换 / 转换失败
目标绑定：已确认数量 / 待人工确认数量 / 无候选数量
业务断言覆盖：已覆盖 / 缺失 / 降级
```

快捷入口新增：

```text
导入上游包
查看准入校验
查看转换预览
查看目标绑定队列
导出上游补充清单
```

### 16.5 用例管理页需要调整

用例管理页不再只是“导入手工用例”，而是承接上游包转换后的用例。

新增 Tab：

```text
用例来源
转换预览
结构化步骤
自然语言步骤解析
目标抽取
阻断项
```

用例来源分为：

```text
handoff 包转换
Excel/JSON 手工导入
IDE 临时新建
```

转换预览展示：

```text
manual_test_cases → AutoSmoke case
steps → AutoSmoke steps
expected → UI assertion 候选
assertion_refs → business assertions
preconditions → state prepare tasks
target_name → binding tasks
```

每条用例新增状态：

```text
转换状态
目标绑定状态
页面流转状态
测试数据准备状态
业务断言状态
自动化等级
阻断原因
来源追踪
```

### 16.6 元素映射页需要强化为目标绑定队列

QA_Reader 不提供最终 `testId/semanticId`。所以元素映射页必须承担：

```text
targetName → semanticId 候选
targetName → testId 候选
候选元素匹配
自动确认
人工确认
保存 MappingStore
```

左侧目标列表增加字段：

```text
targetId
targetName
aliases
pageName
pageIdHint
role
actionRoles
sourceNodeIds
caseIds
绑定状态
```

绑定状态建议：

```text
AUTO_CONFIRMED
NEEDS_HUMAN_CONFIRM
AMBIGUOUS
NO_CANDIDATE
CONFIRMED
IGNORED
```

中栏候选区展示：

```text
UI 树候选
代码语义候选
运行态候选
历史 mapping 候选
置信度
高亮结果
测试点击结果
```

右侧详情区展示：

```text
上游 target 信息
AutoSmoke 生成的 semanticId 候选
AutoSmoke 生成的 testId 候选
最终确认 semanticId
最终确认 testId
evidence
source_trace
review_items
```

### 16.7 项目准备页需要增加测试数据准备视角

QA_Reader 会提供 `test_data_profile`，AutoSmoke IDE 需要展示它是否可满足。

新增模块：

```text
测试数据准备
├── 账号条件
├── 活动状态
├── 资源状态
├── 积分状态
├── 奖励领取状态
├── 邮件状态
├── GM / 后台能力
└── 准备结果
```

状态：

```text
READY
NEEDS_PREPARE
UNSUPPORTED
BLOCKED
MANUAL_ONLY
```

### 16.8 执行中心页需要增加执行模式

执行配置新增：

```text
执行模式：UI_ONLY / UI_AND_BUSINESS
降级策略：允许 PASS_WITH_GAP / 阻断即停止
前置准备：自动准备 / 仅检查 / 跳过
断言策略：UI 断言 / 业务断言 / UI+业务一致性
```

批量执行列表新增：

```text
准入状态
目标绑定状态
测试数据状态
业务断言覆盖
降级原因
```

### 16.9 业务验证页需要对接 handoff

业务验证页新增：

```text
business_state_contract 覆盖
business_assertions 覆盖
value_assets 引用
optional_external_refs 可用性
state_path 未声明列表
collector 不可用列表
断言不可执行列表
```

如果当前是 `READY_UI_ONLY`，业务验证页应明确显示：

```text
当前仅支持 UI 自动化，业务逻辑验证未启用。
原因：缺少 business_state_contract 或 business_assertions。
```

### 16.10 报告中心需要增加来源追踪和回执

报告中心新增：

```text
handoff 消费校验报告
转换报告
目标绑定报告
阻断 / 降级报告
来源追踪
QA_Reader 回执缺口清单
```

每条失败记录需要展示：

```text
case_id
step_order
target_name
semanticId
testId
source_node_ids
source_refs
review_item
failure_type
suggested_action
```

### 16.11 问题修复页需要区分责任归属

问题修复页需要把问题分为：

```text
上游需补充
AutoSmoke 需绑定
环境需支持
可降级执行
必须人工测试
```

新增修复任务来源：

```text
handoff validator
converter
target binder
state collector
assertion engine
executor
```

新增动作：

```text
跳转上游包页
重新运行 handoff 校验
跳转目标绑定队列
导出上游补充清单
标记降级执行
标记人工执行
```

### 16.12 高级工具页增加 schema 调试

高级工具新增低频能力：

```text
Handoff Schema 调试
manifest 原始查看
schema validation 原始结果
转换中间产物查看
source_trace 查询
review_items 原始编辑
```

这些不应放在主流程页面，避免普通用户被原始 JSON 淹没。

### 16.13 更新后的推荐主流程

#### UI 自动化流程

```text
1. 上游包：导入 handoff 包
2. 上游包：运行 schema 校验
3. 上游包：确认准入为 READY_UI_ONLY 或 PASS_WITH_GAP
4. 用例管理：查看用例转换预览
5. 元素映射：处理目标绑定队列
6. 项目准备：检查环境和测试数据
7. 执行中心：生成并运行 UI 执行计划
8. 报告中心：查看执行报告和来源追踪
9. 问题修复：处理阻断、失败、缺失绑定
```

#### UI + 业务逻辑自动化流程

```text
1. 上游包：导入 handoff 包
2. 上游包：确认准入为 READY_UI_AND_BUSINESS
3. 用例管理：查看用例、步骤、断言转换结果
4. 元素映射：完成目标绑定
5. 项目准备：准备账号、活动、资源、奖励状态
6. 业务验证：检查 state_contract、business_assertions、value_assets、external_refs
7. 执行中心：运行 UI + 业务断言执行计划
8. 业务验证：查看 before/after/diff 和断言结果
9. 报告中心：查看可追溯报告
10. 问题修复：处理失败并导出补充清单
```

### 16.14 最终调整结论

按 QA_Reader 回执，IDE 的定位要从：

```text
自动化测试执行 + 元素映射工具
```

进一步明确为：

```text
业务输入转换与自动化测试集成控制台
```

新增“上游包”页面是最清晰的设计。它能把 QA_Reader 交付包、准入校验、转换入口和阻断项统一起来，避免这些能力散落在用例管理、业务验证和高级工具里。
