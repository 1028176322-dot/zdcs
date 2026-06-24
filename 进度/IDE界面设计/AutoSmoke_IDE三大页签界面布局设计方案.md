# AutoSmoke IDE 三大页签界面布局设计方案

## 1. 设计目标

AutoSmoke IDE 的核心目标是让测试人员可以完成：

```text
准备环境和数据
执行自动化用例
查看结果和问题
```

因此 IDE 顶层信息架构采用 3 个大页签：

```text
准备
执行
结果
```

设计原则：

- 测试人员按工作流程从左到右使用。
- 每个页签只放当前阶段需要的能力。
- 复杂能力分组收纳，不把所有工具堆在一个页面。
- 点击精准、截图完整、状态断言、报告输出都能在 IDE 中闭环。
- 后续可以打包成独立 EXE。

## 2. 顶层结构

```text
AutoSmoke IDE
├── 准备
│   ├── 系统健康检查
│   ├── 环境配置
│   ├── Unity 连接
│   ├── 脚本部署
│   ├── GameContent 截图源
│   ├── UI树与元素映射
│   ├── 页面关系图配置
│   ├── 测试环境初始化
│   ├── 用例导入
│   ├── 跨电脑迁移
│   └── 预检
├── 执行
│   ├── 单步调试
│   ├── 用例执行
│   ├── 批量执行
│   ├── 自动探索
│   ├── 实时监控
│   ├── 异常检测
│   ├── 阻塞处理
│   ├── Bridge/API 调试
│   └── 手动工具
└── 结果
    ├── 本次结果
    ├── 历史报告
    ├── 失败分析
    ├── 页面关系图报告
    ├── 异常/崩溃/卡死分析
    ├── 截图与日志
    ├── 状态 Diff
    ├── 模块验收报告
    ├── 迁移验收报告
    └── 导出归档
```

## 3. 全局布局

### 3.1 顶部栏

顶部栏始终显示：

| 区域 | 内容 |
|---|---|
| 左侧 | AutoSmoke 标题、当前项目名 |
| 中间 | 三个大页签：准备 / 执行 / 结果 |
| 右侧 | Unity 连接状态、Poco 状态、当前账号、当前场景 |

状态示例：

```text
Unity: 已连接
Poco: 在线
截图源: Unity PNG
点击模式: unity_inject
场景: MainCity
```

### 3.2 全局状态条

页面底部固定状态条：

```text
当前用例：TC_BAG_001
执行状态：Idle / Running / Paused / Failed
最近错误：-
报告目录：screenshots/run_xxx
```

### 3.3 告警提示

全局告警包括：

- Unity 未连接。
- Poco 未连接。
- Unity 脚本未部署。
- GameContent 截图不完整。
- click_result 超时。
- 状态导出失败。
- 检测到 MissingReference。

## 4. 页签一：准备

### 4.1 定位

“准备”页签用于完成自动化运行前的所有准备工作。

目标：

```text
确认环境可用
确认 Unity 已连接
确认脚本已部署
确认截图源可用
确认元素映射可用
确认用例已导入
确认预检通过
```

### 4.2 子功能分组

```text
准备
├── 系统健康检查
├── 环境配置
├── Unity 连接
├── 脚本部署
├── 截图源配置
├── UI树与元素映射
├── 页面关系图配置
├── 测试环境初始化
├── 用例导入
├── 跨电脑迁移
└── 运行预检
```

### 4.2.1 系统健康检查

功能：

- 展示完整实施方案中的模块健康度。
- 检查 Python 模块是否可 import。
- 检查 Unity 侧脚本是否已部署。
- 检查 Bridge 文件是否能读写。
- 检查 Poco 连接。
- 检查截图源。
- 检查点击注入。
- 检查异常检测模块。

展示字段：

| 模块 | 加载 | 功能 | 验收状态 | 依赖 | 最近错误 |
|---|---|---|---|---|---|
| 坐标映射 | ✅ | ✅ | 待验收 | Python | - |
| Unity 直出截图 | ✅ | ✅ | 待验收 | Unity | - |
| 点击注入 | ✅ | ✅ | 待验收 | Unity | - |
| 崩溃检测 | ✅ | ✅ | 待验收 | Python | - |

操作：

```text
一键健康检查
重新加载模块
查看错误详情
导出健康报告
```

### 4.2.2 依赖工具检查

功能：

- 检查 Python 版本。
- 检查 pywin32、Pillow、NumPy、Flask、OpenCV、pocoui、openpyxl。
- 检查 Tesseract-OCR 和中文语言包。
- 检查 Unity 版本。

展示：

| 工具 | 需求版本 | 当前版本 | 状态 | 修复建议 |
|---|---|---|---|---|
| Python | >=3.11 | 3.13.12 | ✅ | - |
| Tesseract | >=5.4 | 未安装 | ❌ | 安装 OCR 引擎 |

操作：

```text
检查依赖
复制安装命令
打开安装说明
```

### 4.3 环境配置

功能：

- 设置 AutoSmoke 根目录。
- 设置 Unity 项目路径。
- 设置 Poco-SDK-master 路径。
- 设置 Python 环境。
- 设置截图输出目录。
- 设置报告输出目录。

展示字段：

| 字段 | 示例 |
|---|---|
| Unity 项目路径 | `E:/s1/k3client/client` |
| AutoSmoke 根目录 | `E:/zdcs/AutoSmoke` |
| Poco SDK 路径 | `E:/zdcs/Poco-SDK-master` |
| Python 版本 | `3.11.x` |
| Unity 版本 | `2022.3.62f3` |

操作：

```text
选择目录
自动检测
保存配置
检查依赖
```

### 4.4 Unity 连接

功能：

- 检查 Unity Editor 是否打开。
- 检查 Play Mode。
- 检查 AutoSmoke Bridge 状态。
- 检查当前场景。
- 检查当前分辨率。

状态卡片：

```text
Unity Editor：已检测
Play Mode：运行中
Bridge：在线
GameView：已识别
当前场景：MainCity
分辨率：1170x2532
```

操作：

```text
刷新连接
打开 Unity 项目
启动 Bridge
停止 Bridge
导出状态
```

### 4.5 脚本部署

功能：

- 检查 Unity Editor 脚本是否已部署。
- 对比脚本版本。
- 一键部署或更新。
- 显示编译结果。

脚本列表：

| 脚本 | 状态 | 版本 | 说明 |
|---|---|---|---|
| GameViewLocator.cs | 已部署 | v1 | GameView 定位 |
| AutoSmokeClickInjector.cs | 已部署 | v1 | 点击注入 |
| AutoSmokeMetadataExporter.cs | 已部署 | v1 | 元数据导出 |
| AutoSmokeGameContentCapture.cs | 待部署 | v1 | Unity 直出 PNG |
| AutoSmokeStateExporter.cs | 待部署 | v1 | 状态导出 |

操作：

```text
检查部署
部署全部
更新选中
打开部署目录
查看 Unity 编译日志
```

### 4.6 截图源配置

截图源优先级：

```text
Unity 直出 PNG
Unity Bridge 屏幕区域
Python GameView 裁剪
手动区域
```

页面显示：

| 来源 | 状态 | 用途 |
|---|---|---|
| Unity PNG | 推荐 | 报告/识别主图 |
| Bridge Rect | 可用 | 鼠标兜底坐标 |
| Python 裁剪 | 兜底 | 旧流程 |

操作：

```text
测试截图
查看截图
查看 metadata
设置优先级
```

### 4.7 UI 树与元素映射

这是“准备”页签中的重点模块。

子功能：

```text
工程态扫描
运行态采集
元素映射草稿
人工审核
人工补充
可测试性扫描
```

页面布局：

```text
左：页面/状态筛选
中：元素映射草稿列表
右：截图高亮和详情
```

操作：

```text
扫描 UI Prefab
导出当前 UI 树
导入 Unity 元素数据
生成映射草稿
审核映射
新增元素
测试点击
保存正式映射
```

详细能力：

```text
工程态 Prefab 扫描
运行态 UI 树导出
工程态 + 运行态合并增强
映射草稿生成
三栏审核面板
截图高亮
人工补充元素
测试点击
合并候选
可测试性扫描
```

### 4.7.3 导入 Unity 元素数据

Unity 侧导出的 UI 树、工程态扫描、页面截图、图标信息，不能直接手动改 JSON 使用。

IDE 中需要提供固定导入入口：

```text
准备 → UI树与元素映射 → 导入 Unity 元素数据
```

#### 4.7.3.1 推荐导入流程

```text
1. Unity 导出元素数据
2. IDE 检测导出目录
3. IDE 导入并校验
4. 生成/更新 enhanced_ui_tree.json
5. 生成/更新 element_mapping_draft.json
6. 进入映射草稿审核面板
7. 人工确认后保存 element_mapping.json
```

#### 4.7.3.2 Unity 侧推荐输出目录

```text
E:\zdcs\AutoSmoke\runtime\ui_tree\
```

推荐文件：

```text
project_ui_inventory.json      # 工程态 UI prefab 扫描结果
current_ui_tree.json           # 当前运行态 UI 树
pages\MainCity.json            # 页面级运行态 UI 树
pages\WorldMap.json
pages\BagPanel.json
pages\RewardPopup.json
screenshots\MainCity.png       # 页面截图
screenshots\BagPanel.png
scene_objects.json             # 主城/大地图对象
icon_inventory.json            # 图标资源/道具图标信息
accessibility_scan.json        # 可测试性扫描结果
```

#### 4.7.3.3 IDE 导入页面功能

页面按钮：

```text
选择导出目录
扫描可导入文件
导入工程态 UI
导入运行态 UI
导入页面截图
导入图标信息
导入场景对象
合并增强
生成映射草稿
进入审核
```

展示导入状态：

| 文件 | 状态 | 节点数 | 页面 | 警告 |
|---|---|---:|---|---|
| project_ui_inventory.json | 可导入 | 205000 | - | 12 个 Missing |
| pages/BagPanel.json | 可导入 | 530 | BagPanel | 35 个节点无 screenRect |
| screenshots/BagPanel.png | 可导入 | - | BagPanel | - |

#### 4.7.3.4 导入校验

IDE 导入时必须校验：

```text
文件是否存在
schemaVersion 是否支持
timestamp 是否有效
pageId 是否为空
nodes 数量是否大于 0
节点 path 是否唯一
screenRect 是否合法
screenshotRef 是否存在
图标是否有 visualNode/clickTargetNode
是否包含 displayName/chineseDescription
```

导入问题展示：

```text
错误：BagPanel.json 缺少 pageId
警告：128 个节点缺少 screenRect
警告：35 个图标缺少 clickTargetNode
警告：12 个元素缺少中文描述
```

#### 4.7.3.5 导入模式

| 模式 | 说明 | 使用场景 |
|---|---|---|
| 全量导入 | 清空旧草稿，重新导入全部 | 第一次使用 |
| 增量导入 | 只导入新增页面/新增节点 | 日常更新 |
| 页面导入 | 只导入指定页面 | 单功能调试 |

#### 4.7.3.6 导入后的输出

IDE 导入后统一整理到：

```text
runtime/ui_tree/imported/
├── project_ui_inventory.json
├── pages/
│   ├── MainCity.json
│   ├── BagPanel.json
│   └── RewardPopup.json
├── screenshots/
│   ├── MainCity.png
│   └── BagPanel.png
└── import_report.json
```

并生成或更新：

```text
enhanced_ui_tree.json
element_mapping_draft.json
accessibility_scan.json
```

#### 4.7.3.7 人工映射保护

导入时不能覆盖人工确认或人工补充的元素。

合并优先级：

```text
manual confirmed > confirmed > modified > draft pending
```

如果新导入的自动元素疑似匹配已有人工元素，IDE 应提示：

```text
发现可能匹配的自动元素，是否合并？
```

合并后保留人工填写的：

```text
displayName
chineseDescription
semanticId
testId
role
```

自动导入只补充：

```text
runtimePath
prefabPath
screenRect
components
evidence
```

#### 4.7.3.8 推荐用户操作流程

```text
1. 打开 Unity
2. Unity 菜单执行：AutoSmoke/UI/Scan All UI Prefabs
3. Unity 菜单执行：AutoSmoke/UI/Export Current UI Tree
4. 回到 IDE
5. 准备 → UI树与元素映射 → 导入 Unity 元素数据
6. 点击“扫描可导入文件”
7. 点击“导入并生成草稿”
8. 进入映射草稿审核面板
9. 审核并保存正式 element_mapping.json
```

### 4.7.1 映射草稿审核面板

三栏布局：

```text
左：草稿列表
中：截图高亮
右：详情与编辑
```

必须支持：

- 中文名称。
- 中文描述。
- 核对提示。
- visualNode / clickTargetNode。
- 确认 / 修改 / 拒绝 / 忽略。
- 截图点选新增。
- Unity 当前选中对象新增。
- 手动路径新增。
- 业务对象新增。

### 4.7.2 可测试性扫描

展示：

- 缺少 testId 的元素。
- 重名节点。
- Missing Reference。
- Missing Script。
- 不可点击但疑似按钮的节点。
- 图标缺少业务 dataId。

输出：

```text
accessibility_scan.json
accessibility_report.html
```

### 4.10 页面关系图配置

功能：

- 配置自动探索入口页面。
- 配置探索深度。
- 配置危险按钮黑名单。
- 配置忽略元素。
- 配置返回策略。
- 生成页面关系图。

展示：

| 配置 | 示例 |
|---|---|
| 起始页面 | MainCity |
| 最大深度 | 3 |
| 每页最大点击数 | 50 |
| 危险关键词 | 充值、购买、支付 |

操作：

```text
生成可点击元素列表
预览探索计划
开始探索
查看 page_graph
```

### 4.11 测试环境初始化

功能：

- 选择测试账号。
- 选择服务器。
- 检查登录状态。
- 检查当前场景。
- 执行 GM 初始化。
- 设置资源。
- 跳过或固定新手引导阶段。
- 清理测试数据。

展示：

```text
账号：test_001
服务器：dev_01
场景：MainCity
引导：已完成
资源初始化：已完成
```

操作：

```text
登录检查
进入主城
执行 GM 初始化
导出初始化状态
```

### 4.8 用例导入

功能：

- 导入 Excel。
- 解析用例。
- 校验字段。
- 展示用例列表。
- 展示步骤预览。
- 校验目标是否存在映射。

展示：

```text
用例数量
步骤数量
缺失目标数量
无效断言数量
```

操作：

```text
导入 Excel
重新解析
校验用例
导出解析结果
```

### 4.9 运行预检

运行前预检项：

| 预检项 | 通过标准 |
|---|---|
| Unity 连接 | Bridge 在线 |
| 截图源 | Unity PNG 可用 |
| 点击模式 | unity_inject 可用 |
| 元素映射 | 用例目标可定位 |
| 状态导出 | latest_state 可用 |
| 阻塞检测 | blocker rules 加载 |
| 日志监听 | Unity log 可读 |

预检结果：

```text
全部通过 -> 允许执行
存在警告 -> 允许执行但标记风险
存在阻断 -> 不允许执行
```

### 4.12 跨电脑迁移

功能：

- 导出当前项目配置。
- 导入其它电脑配置。
- 检查 Unity 项目路径。
- 检查 AutoSmoke 根目录。
- 检查 Poco SDK 路径。
- 检查 Python 依赖。
- 检查 Unity 脚本部署。
- 执行迁移验收。

操作：

```text
导出配置包
导入配置包
路径重映射
一键迁移检查
生成迁移验收报告
```

验收项：

```text
Python 依赖通过
Unity 脚本已部署
Bridge 可写入
Unity PNG 可截图
testId 点击命中
示例 Excel 用例通过
```

## 5. 页签二：执行

### 5.1 定位

“执行”页签用于运行自动化。

目标：

```text
单步调试
执行用例
批量运行
实时观察
处理阻塞
暂停/继续/停止
```

### 5.2 子功能分组

```text
执行
├── 单步调试
├── 用例执行
├── 批量执行
├── 自动探索
├── 实时监控
├── 异常检测
├── 阻塞处理
├── Bridge/API 调试
└── 手动工具
```

### 5.3 单步调试

适合调试目标定位和点击。

功能：

- 输入一步操作。
- 选择目标。
- 选择点击模式。
- 执行 preCheck。
- 执行点击。
- 查看 click_result。
- 查看 before/after 截图。

示例：

```text
动作：点击
目标类型：semantic
目标值：背包.使用按钮
点击模式：unity_inject
```

操作：

```text
定位目标
测试点击
执行一步
查看结果
```

### 5.4 用例执行

功能：

- 选择单个用例。
- 查看步骤列表。
- 执行 / 暂停 / 停止。
- 当前步骤高亮。
- 展示每步状态。

步骤表：

| 步骤 | 动作 | 目标 | 期望 | 状态 |
|---|---|---|---|---|
| 1 | 点击 | 背包.使用按钮 | 奖励弹窗出现 | PASS |
| 2 | 点击 | 奖励弹窗.确认按钮 | 弹窗消失 | RUNNING |

### 5.5 批量执行

功能：

- 选择多个用例。
- 按模块执行。
- 按标签执行。
- 设置失败策略。
- 设置账号。
- 设置重复次数。

失败策略：

```text
遇错停止
继续后续用例
重试当前用例
只运行失败用例
```

### 5.5.1 自动探索

功能：

- 从当前页面开始探索。
- 自动点击可点击元素。
- 自动识别新页面和弹窗。
- 自动处理可关闭弹窗。
- 自动探索图标 Tips。
- 记录页面关系图。
- 避开危险按钮。

执行参数：

| 参数 | 示例 |
|---|---|
| 起始页面 | MainCity |
| 最大深度 | 3 |
| 每页最大点击数 | 50 |
| 是否探索图标 Tips | 是 |
| 是否自动关闭弹窗 | 是 |
| 危险关键词 | 充值、购买、支付 |

实时展示：

```text
当前页面
当前点击元素
发现新页面
发现新弹窗
已探索数量
跳过危险元素数量
```

输出：

```text
page_graph.json
page_graph.html
auto_explorer_report.json
```

### 5.6 实时监控

实时展示：

- 当前 GameContent 截图。
- 当前 UI 页面。
- 当前阻塞状态。
- 当前点击目标。
- 当前业务状态摘要。
- Unity 日志片段。
- 最近错误。

监控卡片：

```text
当前页面：MainCity
当前步骤：3/12
点击目标：Bag.UseButton
阻塞：无
日志错误：无
```

### 5.6.1 异常检测

功能：

- 实时采集 Unity Editor.log。
- 检测 MissingReferenceException。
- 检测 NullReferenceException。
- 检测 Unity Error / Exception。
- 检测进程崩溃。
- 检测卡死。
- 检测 Loading 超时。
- 检测 Poco 心跳异常。

展示：

| 类型 | 状态 | 最近时间 | 详情 |
|---|---|---|---|
| MissingReference | 无 | - | - |
| NullReference | 发现 | 10:32:01 | 查看日志 |
| 卡死 | 无 | - | - |

操作：

```text
开始监听
停止监听
清空异常
查看日志片段
导出异常报告
```

### 5.7 阻塞处理

功能：

- 自动检测弹窗、Loading、重连、引导。
- 展示阻塞类型。
- 展示处理策略。
- 手动触发处理。
- 标记危险弹窗。

展示：

| 阻塞类型 | 置信度 | 策略 | 状态 |
|---|---|---|---|
| RewardPopup | 0.92 | 点击确认 | 已处理 |
| Reconnect | 0.88 | 等待 | 处理中 |

### 5.8 手动工具

提供辅助操作：

```text
截取 Unity PNG
导出 UI 树
导出状态
清空报告目录
打开报告目录
执行 GM 初始化
刷新日志
```

### 5.9 Bridge/API 调试

功能：

- 查看 Unity Bridge 状态。
- 手动发送 click_request。
- 手动读取 click_result。
- 手动触发 Unity 直出 PNG。
- 手动导出 UI 树。
- 手动导出状态快照。
- 查看 API 响应。

常用调试项：

| 功能 | 输入 | 输出 |
|---|---|---|
| 点击注入 | target / mode | click_result.json |
| Unity 截图 | resolution | capture png/json |
| UI 树导出 | pageId | current_ui.json |
| 状态导出 | modules | latest_state.json |
| 反查元素 | x/y/pageId | matchedElements |

用途：

```text
开发调试
现场排障
验证 Unity Bridge 是否正常
```

## 6. 页签三：结果

### 6.1 定位

“结果”页签用于查看执行结果、定位问题和导出报告。

目标：

```text
看结果
看失败
看截图
看日志
看状态变化
导出报告
```

### 6.2 子功能分组

```text
结果
├── 本次结果
├── 历史报告
├── 失败分析
├── 页面关系图报告
├── 异常/崩溃/卡死分析
├── 截图与日志
├── 状态 Diff
├── 模块验收报告
├── 迁移验收报告
└── 导出归档
```

### 6.3 本次结果

展示：

```text
总用例数
通过数
失败数
跳过数
通过率
总耗时
失败分类统计
```

用例列表：

| 用例ID | 标题 | 结果 | 耗时 | 失败原因 |
|---|---|---|---|---|
| TC_BAG_001 | 使用道具 | PASS | 12s | - |
| TC_BUILD_001 | 升级建筑 | FAIL | 18s | POSTCHECK_FAILED |

### 6.4 历史报告

功能：

- 按日期查看报告。
- 按版本查看报告。
- 按模块筛选。
- 对比两次报告。
- 打开 HTML 报告。

### 6.5 失败分析

按失败类型归类：

```text
TARGET_NOT_FOUND
TARGET_OCCLUDED
EVENT_RECEIVER_MISMATCH
POSTCHECK_FAILED
BLOCKER_DETECTED
CRASH_DETECTED
HANG_DETECTED
SCREENSHOT_INCOMPLETE
```

点击失败项展示：

- 失败步骤。
- 失败截图。
- 目标元素。
- 点击结果。
- 业务断言。
- Unity 日志。
- 建议处理。

### 6.5.1 页面关系图报告

展示：

- 页面节点。
- 弹窗节点。
- 点击边。
- 返回路径。
- 死路页面。
- 危险入口。
- 未探索元素。

示例：

```text
MainCity --点击 背包按钮--> BagPanel
BagPanel --点击 使用按钮--> RewardPopup
RewardPopup --点击 确认按钮--> BagPanel
```

操作：

```text
查看图谱
筛选页面
查看边详情
跳转到对应截图
导出 HTML
```

### 6.5.2 异常/崩溃/卡死分析

展示：

| 类型 | 数量 | 首次出现 | 关联用例 |
|---|---:|---|---|
| MissingReference | 2 | 10:32:01 | TC_BAG_001 |
| NullReference | 1 | 10:33:12 | TC_BUILD_001 |
| HANG_DETECTED | 1 | 10:35:00 | TC_MAP_001 |

详情：

- 日志片段。
- 发生步骤。
- before/after 截图。
- 当前页面。
- 当前点击目标。
- 建议处理。

### 6.6 截图与日志

三栏对比：

```text
before screenshot
after screenshot
diff / highlight
```

同时展示：

```text
Unity log excerpt
AutoSmoke execution log
click_result.json
metadata.json
```

### 6.7 状态 Diff

展示 before/after 业务状态变化：

```text
resources.gold: 168922 -> 169922 (+1000)
bag.items[1001].count: 3 -> 2 (-1)
tasks.canClaim: true -> false
```

断言结果：

| 路径 | 期望 | 实际 | 结果 |
|---|---|---|---|
| resources.gold | +1000 | +1000 | PASS |
| tasks.canClaim | false | true | FAIL |

### 6.8 导出归档

支持：

```text
导出 HTML 报告
导出 JSON 报告
导出失败包
导出截图包
导出日志包
```

失败包包含：

```text
case_result.json
before.png
after.png
metadata.json
click_result.json
before_state.json
after_state.json
log_excerpt.txt
```

### 6.9 模块验收报告

展示完整实施方案中的模块验收状态：

| 模块 | 验收状态 | 通过项 | 失败项 | 备注 |
|---|---|---:|---:|---|
| Unity 直出 PNG | 通过 | 5 | 0 | - |
| 点击注入 | 待验收 | 2 | 1 | semanticId 未验证 |
| UI 树导出 | 通过 | 4 | 0 | - |

支持：

```text
按模块筛选
查看验收标准
导出验收报告
```

### 6.10 迁移验收报告

展示跨电脑/跨项目迁移检查结果：

| 项 | 状态 | 详情 |
|---|---|---|
| Python 依赖 | 通过 | 版本满足 |
| Unity 脚本 | 通过 | 已部署 |
| Bridge | 通过 | state/click/capture 可写入 |
| 截图 | 通过 | Unity PNG 完整 |
| 点击 | 失败 | testId 未命中 |

输出：

```text
migration_report.json
migration_report.html
```

## 7. 三大页签之间的数据流

```mermaid
flowchart LR
    A["准备: 配置/映射/用例"] --> B["执行: 单步/用例/批量"]
    B --> C["结果: 报告/失败/日志"]
    C --> A
```

闭环：

```text
结果中发现 TARGET_NOT_FOUND
  -> 回到准备/元素映射
    -> 补充映射
      -> 再执行
```

```text
结果中发现 POSTCHECK_FAILED
  -> 回到准备/业务断言或状态导出
    -> 修正规则
      -> 再执行
```

## 8. 最小可用版本

第一版 IDE 可以实现：

```text
准备：
  环境配置
  脚本部署
  截图测试
  元素映射审核
  用例导入

执行：
  单步执行
  单用例执行
  实时日志

结果：
  本次结果
  截图查看
  JSON/HTML 报告
```

## 9. 完整版本

完整 IDE 版本实现：

```text
准备：
  系统健康检查
  依赖工具检查
  一键环境检查
  Unity Bridge 状态
  Unity 直出 PNG
  UI 树扫描
  映射草稿审核
  人工补充元素
  页面关系图配置
  测试环境初始化
  用例导入校验
  跨电脑迁移
  运行预检

执行：
  单步调试
  用例执行
  批量执行
  自动探索
  阻塞处理
  异常检测
  实时监控
  Bridge/API 调试
  暂停/继续/停止

结果：
  报告汇总
  失败分析
  页面关系图报告
  异常/崩溃/卡死分析
  截图对比
  状态 Diff
  日志查看
  模块验收报告
  迁移验收报告
  导出失败包
```

## 10. 验收标准

| 编号 | 功能 | 通过标准 |
|---|---|---|
| IDE-001 | 三大页签 | 顶部显示准备/执行/结果 |
| IDE-002 | 准备页 | 能完成环境检查、脚本部署、元素映射、用例导入 |
| IDE-003 | 执行页 | 能执行单步、单用例、批量用例 |
| IDE-004 | 结果页 | 能查看报告、失败、截图、日志 |
| IDE-005 | 状态联动 | 准备未通过时执行页提示阻断 |
| IDE-006 | 失败闭环 | 结果页失败项可跳转到准备页补映射 |
| IDE-007 | 报告导出 | 能导出 HTML/JSON/失败包 |
| IDE-008 | 系统健康检查 | 能展示模块加载、功能、验收状态 |
| IDE-009 | 自动探索 | 能运行探索并生成 page_graph |
| IDE-010 | 异常检测 | 能展示 MissingReference/崩溃/卡死 |
| IDE-011 | 映射审核 | 能三栏审核草稿并人工补充元素 |
| IDE-012 | 迁移验收 | 能生成跨电脑迁移验收报告 |

## 11. 最终建议

三大页签设计符合测试工作流：

```text
准备：把环境、元素、用例准备好
执行：把用例跑起来
结果：把问题看清楚并导出
```

后续所有 IDE 功能都应归入这三个阶段，避免界面变成工具堆叠。
