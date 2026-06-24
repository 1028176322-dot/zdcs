# AutoSmoke IDE 完整运行方案

## 1. 目标

AutoSmoke IDE 用于 Unity SLG 游戏的自动化冒烟测试、场景探索、异常捕捉和报告生成。它面向主城、大地图、普通 UI 页面、弹窗和活动页面，目标是在一个 IDE 内完成从环境配置到自动执行再到输出报告的完整闭环。

核心目标：

- 自动配置 Unity 项目和 Poco SDK 运行环境。
- 支持同一项目在不同电脑、不同工程路径下运行。
- 自动连接 Unity Editor、Windows 包或 Android 包。
- 自动执行测试用例。
- 自动探索页面、弹窗、主城建筑、大地图对象。
- 自动记录页面和场景关系图。
- 自动发现崩溃、卡死、空页面、Missing Reference、NullReference、点击无响应等问题。
- 自动生成 HTML、JSON、截图和可复现路径报告。

系统定位：

AutoSmoke IDE 不是完全无配置的万能测试机器人，而是一个“通用框架 + 项目配置 + Unity 侧采集插件”的自动化测试平台。Poco 负责 UI 树，截图/OCR 负责视觉补充，Unity 侧 Exporter 负责主城和大地图对象，日志和协议监听负责异常证据。

---

## 2. 总体架构

```text
AutoSmoke IDE
  |
  |-- 环境配置向导
  |-- 项目配置管理
  |-- Poco 连接管理
  |-- 用例管理
  |-- 自动探索引擎
  |-- 主城/大地图场景扫描
  |-- 弹窗遍历引擎
  |-- 异常检测中心
  |-- 页面关系图生成
  |-- 测试报告生成
  |
Unity 游戏工程
  |
  |-- Poco SDK
  |-- AutoSmoke Unity Plugin
      |
      |-- Poco 自动启动脚本
      |-- 日志采集器
      |-- 场景状态导出器
      |-- 主城对象导出器
      |-- 大地图对象导出器
      |-- 可选协议消息采集接口
```

数据来源：

| 数据来源 | 采集内容 | 用途 |
|---|---|---|
| Poco UI 树 | UI 节点、文本、按钮、坐标、层级 | 页面识别、按钮点击、弹窗识别 |
| 截图 | 当前画面、视觉状态、黑屏/空白、图标缺失 | 视觉验证、报告证据 |
| Unity 日志 | Error、Exception、Missing Reference、堆栈 | Bug 判定 |
| Unity 场景导出 | 主城建筑、大地图对象、相机坐标、缩放等级 | 场景探索 |
| 协议日志 | 请求、响应、错误码、超时 | 功能验证 |
| 自动化操作记录 | 点击、输入、滑动、缩放、返回 | 复现路径 |

---

## 3. 目录结构

推荐 AutoSmoke IDE 在本机使用如下结构：

```text
AutoSmoke/
  config/
    ide_config.json
    device_profiles.json
  docs/
  core_engine/
  data_access/
  ide/
  templates/
  unity_integration/
  logs/
  reports/
```

每个 Unity 项目内生成独立配置：

```text
UnityProject/
  Assets/
  ProjectSettings/
  Packages/
  .autosmoke/
    config.json
    rules/
      ui_rules.json
      scene_rules.json
      blacklist.json
    runs/
      20260611_153000/
        screenshots/
        ui_trees/
        scene_states/
        logs/
        reports/
```

路径原则：

- IDE 只保存最近打开的项目路径。
- 项目配置写入 `<UnityProject>/.autosmoke/config.json`。
- 报告、截图、UI 树、场景状态全部写入当前项目的 `.autosmoke/runs/<timestamp>/`。
- 配置中尽量使用相对路径和占位符 `${PROJECT_PATH}`。
- 不允许把 `E:\...` 这类本机绝对路径写死到核心逻辑。

---

## 4. 环境要求

### 4.1 测试机环境

| 类型 | 要求 |
|---|---|
| 操作系统 | Windows 10/11 |
| Python | 3.10+，推荐 3.11 |
| Unity | 与目标项目一致，推荐 2020.3+ |
| Android 调试 | ADB 可用，设备已开启 USB 调试 |
| 网络 | IDE 能访问本机 Poco 端口和可选 LLM/服务端 |
| 显示设置 | 建议缩放 100%，避免坐标偏移 |

Python 依赖：

```text
airtest
pocoui
opencv-python
pandas
openpyxl
pyqt6
pyyaml
networkx
jinja2
Pillow
```

可选依赖：

```text
pytesseract
easyocr
requests
websocket-client
```

### 4.2 Unity 项目要求

基础要求：

- 项目可以在 Unity Editor 或目标设备上正常运行。
- 项目已集成 Poco SDK，或者 IDE 能通过配置向导导入 Poco SDK。
- 如果需要主城/大地图对象级探索，项目需要集成 `AutoSmoke Unity Plugin`。
- 如果需要协议级验证，需要项目提供协议收发 hook 或日志输出。

推荐 Unity 插件能力：

| 插件模块 | 是否必须 | 说明 |
|---|---|---|
| Poco SDK | 必须 | UI 树 dump 和 UI 点击 |
| AutoStartPoco | 推荐 | 游戏启动后自动启动 Poco 服务 |
| LogCollector | 必须 | 捕捉 Unity Error 和 Exception |
| SceneStateExporter | 推荐 | 导出当前场景、相机、缩放 |
| MainCityExporter | 主城测试必须 | 导出建筑、等级、状态、屏幕坐标 |
| WorldMapExporter | 大地图测试必须 | 导出地图对象、坐标、缩放、可点击范围 |
| NetMessageMonitor | 可选 | 捕捉协议请求/响应 |

---

## 5. 首次环境配置流程

### 5.1 打开 IDE

用户打开 AutoSmoke IDE 后进入“环境配置向导”。

输入内容：

| 字段 | 示例 | 说明 |
|---|---|---|
| Unity 工程路径 | `D:\Project\SLGClient` | 包含 `Assets` 的项目根目录 |
| Poco SDK 路径 | `D:\SDK\Poco-SDK-master` | 用于导入或校验 |
| 运行平台 | `Windows Editor` / `Android` | 测试目标 |
| Unity 日志路径 | 自动检测 | Editor 或 Player 日志 |
| 报告输出目录 | 默认 `.autosmoke/runs` | 可修改 |
| Poco 端口 | 默认 `5001` | 按项目实际配置 |

### 5.2 项目合法性检查

IDE 自动检查：

- 工程路径是否存在。
- 是否包含 `Assets/`。
- 是否包含 `ProjectSettings/ProjectVersion.txt`。
- 是否已存在 `Assets/Poco` 或 Poco package。
- 是否已存在 `.autosmoke/config.json`。
- 是否可写入 `.autosmoke/`。

检查结果分级：

| 状态 | 含义 |
|---|---|
| `READY` | 可直接运行 |
| `PARTIAL` | 可部分运行，有模块未接入 |
| `NEED_SETUP` | 需要导入 Poco 或 Unity 插件 |
| `BLOCKED` | 路径无效或关键依赖缺失 |

### 5.3 自动导入 Poco SDK

如果项目未集成 Poco，IDE 执行：

1. 校验 `Poco-SDK-master` 结构。
2. 复制 Unity 侧 Poco 目录到 `Assets/Poco`。
3. 复制 AutoSmoke 启动脚本到 `Assets/AutoSmoke/Runtime`。
4. 生成或更新 Poco 启动配置。
5. 提示用户回到 Unity 等待 C# 编译完成。

注意：

- IDE 不应强行覆盖用户已有的 `Assets/Poco`。
- 如果检测到已有 Poco，需要做版本和文件完整性检查。
- 如果项目使用 asmdef，需要提示用户确认引用关系。

### 5.4 生成项目配置

IDE 在项目根目录生成：

```text
<UnityProject>/.autosmoke/config.json
```

示例：

```json
{
  "project": {
    "name": "SLGClient",
    "root": "${PROJECT_PATH}",
    "unity_version": "2020.3.x"
  },
  "runtime": {
    "platform": "WindowsEditor",
    "poco_host": "127.0.0.1",
    "poco_port": 5001,
    "device_uri": "Windows:///?title_re=Unity.*"
  },
  "paths": {
    "log_path": "${PROJECT_PATH}/.autosmoke/logs/unity.log",
    "run_root": "${PROJECT_PATH}/.autosmoke/runs",
    "screenshots": "screenshots",
    "ui_trees": "ui_trees",
    "scene_states": "scene_states",
    "reports": "reports"
  },
  "features": {
    "poco_dump": true,
    "screenshot": true,
    "scene_exporter": true,
    "main_city_exporter": true,
    "world_map_exporter": true,
    "net_monitor": false
  }
}
```

### 5.5 配置迁移

同一项目换电脑、换路径时：

1. 用户选择新的 Unity 工程路径。
2. IDE 读取 `.autosmoke/config.json`。
3. IDE 将 `${PROJECT_PATH}` 替换为当前工程路径。
4. IDE 检查旧绝对路径是否还存在。
5. 对旧绝对路径给出迁移建议。
6. 新运行结果写入新路径下的 `.autosmoke/runs/`。

---

## 6. Unity 侧接入流程

### 6.1 基础 Poco 接入

Poco 接入完成后，IDE 需要验证：

- Unity 运行后 Poco 服务是否启动。
- IDE 是否能连接 Poco。
- `poco.dump()` 是否能返回 UI 树。
- UI 树中是否包含当前页面主要 UI 节点。
- 按钮点击是否生效。

### 6.2 日志采集接入

Unity 侧需要采集：

- `Debug.LogError`
- `Debug.LogException`
- `Application.logMessageReceived`
- `MissingReferenceException`
- `NullReferenceException`
- `Missing Script`
- 资源加载失败
- 场景加载失败

日志输出格式建议：

```json
{
  "time": "2026-06-11 15:30:00.123",
  "level": "Exception",
  "scene": "MainCity",
  "message": "MissingReferenceException: ...",
  "stack": "...",
  "frame": 12345
}
```

### 6.3 主城对象导出

主城需要导出当前屏幕或当前场景中的建筑和可交互对象：

```json
{
  "scene": "MainCity",
  "camera": {
    "position": [0, 10, -20],
    "zoom": 1.0
  },
  "objects": [
    {
      "id": "building_townhall",
      "name": "公馆",
      "type": "building",
      "level": 6,
      "world_pos": [10, 0, 5],
      "screen_pos": [180, 290],
      "clickable": true,
      "states": ["upgrade_available"]
    }
  ]
}
```

### 6.4 大地图对象导出

大地图需要导出相机坐标、缩放等级、当前视野对象：

```json
{
  "scene": "WorldMap",
  "map_center": [1240, 880],
  "zoom": 0.72,
  "visible_objects": [
    {
      "id": "city_10086",
      "type": "player_city",
      "name": "我的城市",
      "level": 13,
      "world_pos": [1248, 876],
      "screen_pos": [185, 333],
      "clickable": true
    }
  ]
}
```

### 6.5 协议消息接入

协议监听不是必须，但建议支持。

输出格式：

```json
{
  "time": "2026-06-11 15:30:01.456",
  "direction": "recv",
  "protocol": "ActivityInfoResponse",
  "code": 0,
  "cost_ms": 120,
  "summary": "活动信息返回成功"
}
```

---

## 7. IDE 完整运行流程

### 7.1 创建运行会话

用户点击“开始测试”后，IDE 创建运行目录：

```text
.autosmoke/runs/20260611_153000/
  screenshots/
  ui_trees/
  scene_states/
  logs/
  reports/
  artifacts/
```

运行会话保存：

```json
{
  "run_id": "20260611_153000",
  "project": "SLGClient",
  "platform": "WindowsEditor",
  "start_time": "2026-06-11 15:30:00",
  "mode": "explore_and_case",
  "status": "running"
}
```

### 7.2 连接游戏

IDE 执行：

1. 连接设备或 Unity Editor。
2. 初始化 Poco。
3. 截取初始截图。
4. dump 初始 UI 树。
5. 拉取初始场景状态。
6. 启动日志监听。
7. 启动可选协议监听。

连接判定：

| 判定项 | 通过条件 |
|---|---|
| 设备连接 | Airtest device 可用 |
| Poco 连接 | `poco.dump()` 成功 |
| 截图 | 生成 PNG |
| 日志监听 | 可读取日志文件或 socket |
| 场景导出 | 可获取 scene state，非必须 |

### 7.3 识别当前场景

IDE 根据多种信号判断当前处于：

- 登录页
- 主城
- 大地图
- 战斗
- 活动页
- 普通 UI 页面
- 弹窗
- 加载页
- 黑屏或空页面

识别依据：

| 信号 | 示例 |
|---|---|
| UI 树 | 页面根节点、按钮、文本 |
| 场景导出 | `scene = MainCity` |
| 截图 | 图像 hash、黑屏占比 |
| 日志 | 场景加载日志 |
| 协议 | 当前功能模块响应 |

### 7.4 执行模式

IDE 支持三种模式：

| 模式 | 说明 |
|---|---|
| 用例模式 | 按测试用例严格执行 |
| 探索模式 | 自动点击和遍历页面/弹窗 |
| 混合模式 | 先按用例进入目标页面，再自动探索 |

---

## 8. 测试用例执行流程

### 8.1 用例格式

IDE 首选兼容现有 Excel 用例模板：`E:\zdcs\参考资料\用例模板.xlsx`。

模板结构：

- 工作表名称：`用例模板`
- 统计区：第 1 行到第 11 行，用于人工查看测试结果统计。
- 表头行：第 13 行。
- 用例数据起始行：第 14 行。

模板字段：

| Excel 列 | 字段名 | 是否必填 | IDE 用途 |
|---|---|---|---|
| B | 优先级 | 是 | 用例优先级，如 `P0`、`P1`、`P2` |
| C | CaseID | 是 | 用例唯一 ID |
| D | 模块 | 是 | 一级功能模块，也可作为页面/场景分类 |
| E | 子模块 | 否 | 二级功能点，也可作为自动探索范围提示 |
| F | 前置条件 | 否 | 执行前状态要求，如主城、活动未开启、大地图指定坐标 |
| G | 操作步骤 | 是 | 人工可读步骤，IDE 解析为自动化动作 |
| H | 预期结果 | 是 | 人工可读预期，IDE 解析为断言 |
| I | 测试结果 | 否 | IDE 执行后自动回填 |
| J | 测试人员 | 否 | 保留人工字段 |
| K | BUG链接 | 否 | IDE 发现 Bug 后回填报告链接或缺陷链接 |
| L | 备注 | 否 | 补充说明，可放自动化标签 |

模板示例：

| 优先级 | CaseID | 模块 | 子模块 | 前置条件 | 操作步骤 | 预期结果 | 测试结果 |
|---|---|---|---|---|---|---|---|
| P0 | K3_DEMO_001 | 签到入口 | UI-未开启 | 活动未开启 | 1.主界面 2.查看签到区域 | 入口不显示 | 待测试 |

导入规则：

1. IDE 从第 13 行读取表头。
2. 从第 14 行开始读取用例。
3. `CaseID` 为空的行跳过。
4. `测试结果` 为 `不适用` 的行默认跳过。
5. `测试结果` 为空或 `待测试` 的行进入执行队列。
6. `已通过`、`未通过`、`被阻碍` 可通过 IDE 配置决定是否重跑。
7. 执行后 IDE 回填 `测试结果`、`BUG链接`、`备注`。

Excel 测试结果枚举：

| 测试结果 | IDE 内部结果 | 说明 |
|---|---|---|
| 待测试 | `PENDING` | 未执行 |
| 已通过 | `PASS` 或 `SMOKE_PASS` | 自动化判定通过 |
| 未通过 | `FAIL` | 期望未满足 |
| 被阻碍 | `ERROR` 或 `BLOCKED` | 环境、连接、前置条件不满足 |
| 不适用 | `SKIPPED` | 不纳入本次执行 |

字段映射：

| Excel 字段 | 内部字段 | 转换说明 |
|---|---|---|
| 优先级 | `priority` | 原样保存 |
| CaseID | `case_id` | 原样保存 |
| 模块 | `module` | 用于报告分类和页面范围 |
| 子模块 | `sub_module` | 用于报告分类和细粒度范围 |
| 前置条件 | `precondition` | 解析为场景、账号状态、功能开关、坐标、缩放等 |
| 操作步骤 | `steps` | 解析为一个或多个自动化动作 |
| 预期结果 | `expected` | 解析为一个或多个断言 |
| 测试结果 | `result` | 执行后回填 |
| BUG链接 | `bug_link` | 执行后回填 |
| 备注 | `notes` | 可承载自动化标签和人工说明 |

IDE 内部执行模型示例：

```json
{
  "priority": "P0",
  "case_id": "K3_DEMO_001",
  "module": "签到入口",
  "sub_module": "UI-未开启",
  "precondition": {
    "raw": "活动未开启",
    "scene": "MainCity",
    "feature_state": {
      "sign_activity": "closed"
    }
  },
  "steps": [
    {
      "step_id": "1",
      "raw": "主界面",
      "action": "ensure_scene",
      "target": {
        "type": "scene",
        "name": "MainCity"
      }
    },
    {
      "step_id": "2",
      "raw": "查看签到区域",
      "action": "inspect",
      "target": {
        "type": "ui_area",
        "name": "签到区域"
      }
    }
  ],
  "expected": [
    {
      "raw": "入口不显示",
      "type": "ui_not_exists",
      "target": {
        "type": "text_or_node",
        "name": "签到入口"
      },
      "timeout": 3
    }
  ]
}
```

操作步骤解析规则：

| 写法示例 | 解析动作 |
|---|---|
| `1.主界面 2.查看签到区域` | `ensure_scene(MainCity)` + `inspect(签到区域)` |
| `点击 邮件` | `click(ui, 邮件)` |
| `点击 公馆` | `click(scene_object, 公馆)` |
| `进入 大地图` | `ensure_scene(WorldMap)` |
| `缩小地图` | `zoom_out` |
| `放大地图` | `zoom_in` |
| `滑动到左上区域` | `pan_to(area, 左上区域)` |
| `输入 名字 测试角色` | `input(target=名字, value=测试角色)` |
| `等待 5秒` | `wait(5)` |

预期结果解析规则：

| 写法示例 | 解析断言 |
|---|---|
| `入口不显示` | `ui_not_exists` |
| `入口显示` | `ui_exists` |
| `打开邮件弹窗` | `popup_opened(邮件)` |
| `跳转到大地图` | `scene_changed(WorldMap)` |
| `出现奖励弹窗` | `popup_opened(奖励)` |
| `无报错` | `log_no_error` |
| `资源增加` | `object_state_changed` 或 `resource_changed` |
| `页面无空白` | `not_empty_page` |

备注字段可选自动化标签：

```text
@auto
@manual
@skip
@scene=MainCity
@scene=WorldMap
@safe
@danger
@timeout=10
@target=BtnMail
@expected=popup_opened:邮件
```

当自然语言步骤无法稳定解析时，IDE 的处理方式：

1. 保留原始 `操作步骤` 和 `预期结果`。
2. 标记该用例为 `NEED_MAPPING`。
3. 在 IDE 中提示用户为步骤选择动作、目标和断言。
4. 保存映射规则到 `.autosmoke/rules/ui_rules.json`。
5. 下次导入同类步骤时自动复用规则。

### 8.2 单步执行

每一步执行前记录：

- 当前截图。
- 当前 UI 树。
- 当前场景状态。
- 当前日志位置。
- 当前协议消息位置。
- 当前页面指纹。

执行动作：

- `click` 点击 UI、场景对象、地图对象。
- `input` 输入文本。
- `swipe` 滑动。
- `zoom_in` 放大。
- `zoom_out` 缩小。
- `set_zoom` 设置缩放等级。
- `pan_to` 移动主城或地图视野。
- `back` 返回。
- `wait` 等待。
- `assert` 断言。

执行后记录：

- 后置截图。
- 后置 UI 树。
- 后置场景状态。
- 新增日志。
- 新增协议。
- 页面指纹变化。
- 异常检测结果。

### 8.3 通过判定

每一步都必须有判定规则。

常见期望类型：

| 期望类型 | 通过条件 |
|---|---|
| `popup_opened` | 指定弹窗出现 |
| `page_changed` | 页面指纹变化且不是错误页 |
| `scene_changed` | 场景名变化 |
| `text_exists` | 指定文本出现 |
| `ui_exists` | 指定 UI 节点出现 |
| `object_exists` | 指定场景对象存在 |
| `object_state_changed` | 建筑、任务、资源状态变化 |
| `net_response_ok` | 收到预期协议且错误码为 0 |
| `log_no_error` | 执行期间无 Error/Exception |
| `screenshot_changed` | 截图变化超过阈值 |
| `no_crash` | 游戏进程和连接正常 |
| `no_freeze` | 心跳、截图或 UI 树在超时内有变化 |

如果用例没有显式 expected，默认只做弱判定：

- 点击动作没有抛异常。
- 游戏没有崩溃。
- 没有新增 Error/Exception。
- 没有卡死。

弱判定只能算 `SMOKE_PASS`，不能算强功能验证通过。

---

## 9. 自动探索流程

### 9.1 页面发现

IDE 对普通 UI 页面执行：

1. dump 当前 UI 树。
2. 识别可点击元素。
3. 生成页面指纹。
4. 对未点击元素执行点击。
5. 点击后判断是否打开新页面或弹窗。
6. 记录页面关系边。
7. 关闭弹窗或返回上一页。
8. 继续遍历。

页面指纹建议包含：

- 可见文本摘要。
- 可点击元素名称和路径。
- 页面根节点。
- 弹窗层级。
- 截图感知 hash。

### 9.2 弹窗遍历

弹窗识别依据：

- 新增 UI 根节点。
- 遮罩层出现。
- UI 层级最高层出现窗口。
- 出现关闭按钮。
- 截图中出现居中面板。

弹窗遍历策略：

1. 进入弹窗后记录 `popup_node`。
2. 点击弹窗内所有安全按钮。
3. 识别二级弹窗。
4. 记录弹窗关系。
5. 优先点击关闭按钮。
6. 如果关闭失败，尝试返回键。
7. 如果返回失败，尝试点击遮罩或取消按钮。

### 9.3 主城场景探索

主城不是普通页面，需要使用场景对象导出。

流程：

1. 获取当前主城相机和缩放。
2. 拉取主城可见建筑和对象。
3. 对每个可点击建筑记录对象节点。
4. 点击建筑。
5. 判断是否打开建筑详情弹窗。
6. 遍历建筑弹窗按钮。
7. 关闭弹窗。
8. 按需要拖动/缩放主城，扫描更多区域。

主城对象指纹：

- `scene = MainCity`
- 建筑 ID
- 建筑类型
- 建筑等级
- 建筑状态
- 屏幕坐标
- 当前缩放等级

### 9.4 大地图探索

大地图是可拖拽、可缩放、可扫描的 Camera Scene。

流程：

1. 获取当前地图中心坐标。
2. 获取当前缩放等级。
3. 设置目标缩放。
4. 按配置范围做网格扫描。
5. 每个网格点拉取可见对象。
6. 点击玩家城、资源点、怪物、船、活动对象。
7. 记录弹窗和页面关系。
8. 关闭弹窗后继续扫描。

大地图扫描范围：

| 范围模式 | 说明 |
|---|---|
| 当前屏 | 只扫描当前视野 |
| 3x3 | 扫描当前中心周围 9 屏 |
| 指定坐标 | 扫描坐标矩形 |
| 联盟区域 | 依赖项目导出联盟范围 |

---

## 10. 安全策略

自动点击必须有安全边界。

黑名单动作：

- 充值。
- 购买。
- 删除账号。
- 退出登录。
- 解散联盟。
- 使用钻石。
- 消耗稀有道具。
- 攻击真实玩家。
- 修改昵称。
- 绑定账号。

黑名单配置示例：

```json
{
  "text_blacklist": ["充值", "购买", "删除", "退出登录", "解散", "钻石加速"],
  "node_blacklist": ["BtnPay", "BtnDelete", "BtnLogout"],
  "scene_object_blacklist": ["enemy_player_city"],
  "confirm_popup_blacklist": ["是否确认购买", "是否消耗钻石"]
}
```

白名单策略：

- 新项目首次运行建议只使用白名单。
- 白名单通过后逐步开放探索范围。
- IDE 应支持“录制一次，生成白名单路径”。

---

## 11. 异常检测

### 11.1 崩溃检测

判定条件：

- Unity 进程退出。
- Android app 进程退出。
- Poco 连接断开且无法重连。
- 截图失败。
- 日志出现 fatal/crash。

报告记录：

- 崩溃前最后一步。
- 崩溃前截图。
- 崩溃前 UI 树。
- 崩溃日志。
- 复现路径。

### 11.2 卡死检测

判定条件：

- 点击后超过 N 秒 UI 树无变化。
- 截图感知 hash 长时间无变化。
- Unity 心跳停止。
- 日志无新增且输入无响应。
- Poco dump 超时。

卡死分级：

| 类型 | 说明 |
|---|---|
| `SOFT_FREEZE` | UI 无变化，但进程存活 |
| `HARD_FREEZE` | Poco 无响应或截图失败 |
| `LOADING_TIMEOUT` | 加载页超过阈值 |

### 11.3 空页面检测

判定条件：

- 可见 UI 节点数量小于阈值。
- 截图大面积纯黑、纯白、纯色。
- 没有可交互对象。
- 当前不是合法加载页。

### 11.4 Missing Reference 检测

日志关键字：

```text
MissingReferenceException
Missing Script
The referenced script on this Behaviour is missing
The object of type ... has been destroyed
```

判定为 `BUG`，严重级别一般为 `P1`。

### 11.5 Null Reference 检测

日志关键字：

```text
NullReferenceException
Object reference not set to an instance of an object
```

判定为 `BUG`，严重级别根据是否阻塞流程决定。

### 11.6 点击无响应检测

判定条件：

- 点击成功但 expected 未满足。
- 页面指纹不变。
- 没有弹窗出现。
- 没有协议响应。
- 没有合理日志。

结果一般为 `FAIL`，如果伴随异常日志则升级为 `BUG`。

---

## 12. 结果状态

单步结果：

| 状态 | 含义 |
|---|---|
| `PASS` | 期望满足且无异常 |
| `SMOKE_PASS` | 未配置强期望，但未发现异常 |
| `FAIL` | 期望未满足 |
| `BUG` | 发现明确游戏异常 |
| `ERROR` | 自动化框架或环境异常 |
| `WARNING` | 可疑问题，需要人工确认 |
| `SKIPPED` | 被黑名单或条件过滤 |

用例结果：

- 全部步骤 `PASS`，用例为 `PASS`。
- 存在 `BUG`，用例为 `BUG`。
- 存在 `FAIL` 且无 `BUG`，用例为 `FAIL`。
- 存在框架异常，标记 `ERROR`。
- 只有弱判定通过，标记 `SMOKE_PASS`。

---

## 13. 页面关系图

关系图节点：

| 节点类型 | 示例 |
|---|---|
| 页面 | 主界面、活动页、背包页 |
| 弹窗 | 奖励弹窗、确认弹窗 |
| 主城对象 | 公馆、城门、训练营 |
| 大地图对象 | 玩家城、资源点、怪物 |
| 异常节点 | 空页面、崩溃、卡死 |

关系图边：

```json
{
  "from": "MainCity",
  "to": "TownHallPopup",
  "action": "click",
  "target": "公馆",
  "result": "PASS",
  "screenshot_before": "screenshots/001_before.png",
  "screenshot_after": "screenshots/001_after.png"
}
```

输出格式：

- `page_graph.json`
- `page_graph.html`
- `page_graph.svg`

---

## 14. 报告输出

### 14.1 报告目录

```text
reports/
  index.html
  summary.json
  cases.json
  bugs.json
  page_graph.json
  page_graph.html
  artifacts/
```

### 14.2 HTML 报告内容

报告首页：

- 项目名称。
- 运行平台。
- 运行时间。
- 总用例数。
- 通过数。
- 失败数。
- Bug 数。
- Warning 数。
- 探索到的页面数。
- 探索到的弹窗数。
- 主城对象数。
- 大地图对象数。

Bug 列表：

| 字段 | 说明 |
|---|---|
| Bug ID | 自动生成 |
| 严重级别 | P0/P1/P2/P3 |
| 类型 | Crash/Freeze/MissingReference/NullReference |
| 场景 | 主城/大地图/活动页 |
| 步骤 | 出问题的动作 |
| 期望 | 期望结果 |
| 实际 | 实际结果 |
| 复现路径 | 从初始状态到问题的步骤 |
| 证据 | 截图、日志、UI 树 |

单步详情：

- 操作前截图。
- 操作后截图。
- UI 树 diff。
- 场景状态 diff。
- 新增日志。
- 新增协议。
- 判定规则。
- 判定结果。

### 14.3 JSON 报告

`summary.json` 示例：

```json
{
  "run_id": "20260611_153000",
  "project": "SLGClient",
  "platform": "WindowsEditor",
  "duration_sec": 820,
  "total_cases": 12,
  "pass": 8,
  "smoke_pass": 1,
  "fail": 2,
  "bug": 1,
  "error": 0,
  "warning": 3,
  "pages": 18,
  "popups": 26,
  "main_city_objects": 15,
  "world_map_objects": 34
}
```

`bugs.json` 示例：

```json
[
  {
    "bug_id": "BUG-20260611-0001",
    "severity": "P1",
    "type": "MissingReferenceException",
    "scene": "MainCity",
    "step": "点击 公馆",
    "expected": "打开公馆详情弹窗",
    "actual": "未打开弹窗，日志出现 MissingReferenceException",
    "repro_path": ["进入主城", "点击 公馆"],
    "screenshots": {
      "before": "screenshots/001_before.png",
      "after": "screenshots/001_after.png"
    },
    "logs": ["MissingReferenceException: ..."],
    "ui_tree_before": "ui_trees/001_before.json",
    "ui_tree_after": "ui_trees/001_after.json"
  }
]
```

---

## 15. 完整运行示例

### 15.1 首次配置

1. 打开 AutoSmoke IDE。
2. 选择 Unity 工程路径。
3. 选择 Poco-SDK-master 路径。
4. 点击“环境检查”。
5. IDE 检查工程、Unity 版本、Poco 状态。
6. 如果未接入 Poco，点击“导入 Poco”。
7. 如果需要主城/大地图测试，点击“导入 AutoSmoke Unity Plugin”。
8. 打开 Unity，等待编译完成。
9. 在 Unity Editor 点击 Play。
10. 回到 IDE 点击“连接测试”。
11. IDE 生成 `.autosmoke/config.json`。

### 15.2 执行用例

1. 在 IDE 选择“用例模式”。
2. 导入 JSON 或 Excel 用例。
3. 选择运行平台。
4. 点击“开始执行”。
5. IDE 逐步执行点击、输入、滑动、缩放、断言。
6. 每一步保存截图、UI 树、日志、协议。
7. 执行完成后生成报告。

### 15.3 自动探索

1. 在 IDE 选择“探索模式”。
2. 设置最大深度。
3. 设置黑名单和白名单。
4. 选择探索范围：普通页面、弹窗、主城、大地图。
5. 点击“开始探索”。
6. IDE 自动点击安全按钮。
7. IDE 自动关闭弹窗。
8. IDE 自动扫描主城和大地图视野。
9. IDE 记录页面关系图。
10. IDE 输出探索报告。

### 15.4 输出报告

运行结束后打开：

```text
<UnityProject>/.autosmoke/runs/<run_id>/reports/index.html
```

报告包含：

- 总览。
- 用例执行结果。
- Bug 列表。
- 页面关系图。
- 主城对象覆盖。
- 大地图对象覆盖。
- 每一步截图和日志。
- 可复现路径。

---

## 16. 跨电脑运行

同一个项目在其他电脑运行：

1. 安装 AutoSmoke IDE。
2. 安装 Python 依赖或使用打包好的 IDE。
3. 拉取同一个 Unity 项目。
4. 打开 IDE，选择新的 Unity 工程路径。
5. IDE 读取项目内 `.autosmoke/config.json`。
6. IDE 将 `${PROJECT_PATH}` 指向当前路径。
7. IDE 检查 Poco 和 Unity 插件是否存在。
8. IDE 创建新的运行目录。
9. 正常连接并运行。

注意事项：

- 不同电脑的 Unity 安装路径可以不同。
- 不同电脑的项目路径可以不同。
- 报告和截图写入当前项目目录。
- Android 设备、ADB、驱动、分辨率需要重新检查。
- Windows Editor 窗口标题可能不同，需要配置 `device_uri`。

---

## 17. IDE 功能模块清单

| 模块 | 功能 |
|---|---|
| 环境配置向导 | 项目路径、Poco SDK、Unity 插件、依赖检查 |
| 项目配置 | `.autosmoke/config.json` 管理 |
| 设备连接 | Windows/Android/iOS 连接 |
| UI 树查看 | 展示 Poco dump 结果 |
| 场景状态查看 | 展示主城/大地图导出对象 |
| 用例管理 | JSON/Excel 导入、编辑、执行 |
| 自动探索 | 页面、弹窗、主城、大地图遍历 |
| 安全规则 | 黑名单、白名单、危险操作过滤 |
| 异常中心 | Crash、Freeze、Missing Reference、空页面 |
| 页面关系图 | 页面、弹窗、对象关系 |
| 报告中心 | HTML/JSON/SVG/截图输出 |

---

## 18. IDE 各功能实现方案

### 18.1 项目配置向导

目标：

让用户通过向导完成项目接入，避免手动修改路径、端口和插件文件。

界面入口：

- 新建项目。
- 打开已有项目。
- 重新检测环境。
- 导入 Poco SDK。
- 导入 AutoSmoke Unity Plugin。

输入：

| 字段 | 来源 |
|---|---|
| Unity 工程路径 | 用户选择 |
| Poco-SDK-master 路径 | 用户选择 |
| 运行平台 | 用户选择 |
| Poco 端口 | 默认值或用户填写 |
| Unity 日志路径 | 自动检测或用户选择 |
| 报告目录 | 默认 `.autosmoke/runs` |

实现方式：

1. 检查工程路径是否包含 `Assets`、`ProjectSettings`、`Packages`。
2. 读取 `ProjectSettings/ProjectVersion.txt` 获取 Unity 版本。
3. 检查 `Assets/Poco` 或 Package 中是否已经存在 Poco。
4. 检查 `.autosmoke/config.json` 是否存在。
5. 生成检测结果列表，按 `READY`、`PARTIAL`、`NEED_SETUP`、`BLOCKED` 展示。
6. 用户点击“应用配置”后写入 `.autosmoke/config.json`。

输出：

- `.autosmoke/config.json`
- `.autosmoke/rules/ui_rules.json`
- `.autosmoke/rules/scene_rules.json`
- `.autosmoke/rules/blacklist.json`
- 环境检测报告 `setup_report.json`

### 18.2 环境检查与 Poco 导入

目标：

自动检查 Poco 是否可用，并在用户确认后把 Poco SDK 接入 Unity 工程。

实现方式：

1. 校验 `Poco-SDK-master` 中是否包含 Unity SDK 目录。
2. 如果目标项目没有 Poco，复制 Poco Unity 目录到 `Assets/Poco`。
3. 如果目标项目已有 Poco，只做版本和关键文件检查，不覆盖。
4. 复制 AutoSmoke 自动启动脚本到 `Assets/AutoSmoke/Runtime`。
5. 生成 Unity 侧配置文件，如端口、日志路径、导出开关。
6. 提示用户等待 Unity 编译完成。

关键检测项：

| 检测项 | 失败处理 |
|---|---|
| Poco 目录不存在 | 提示重新选择 SDK 路径 |
| 目标项目不可写 | 标记 `BLOCKED` |
| 已有 Poco 版本未知 | 标记 `PARTIAL`，允许继续 |
| Unity 编译未完成 | 提示进入 Unity 等待编译 |

### 18.3 设备连接面板

目标：

统一管理 Windows Editor、Windows 包、Android 设备的连接状态。

界面状态：

- 未连接。
- 设备已连接。
- Poco 已连接。
- 截图可用。
- 日志监听中。
- 场景导出可用。

实现方式：

1. 根据配置构造 `device_uri`。
2. 调用 Airtest 连接设备。
3. 初始化 `UnityPoco`。
4. 执行 `poco.dump()` 作为连接自检。
5. 执行截图自检。
6. 启动日志监听。
7. 请求一次场景状态导出。

输出：

```json
{
  "device": "connected",
  "poco": "connected",
  "screenshot": "ok",
  "log_watcher": "running",
  "scene_exporter": "available"
}
```

### 18.4 Excel 用例导入与映射

目标：

兼容现有 `用例模板.xlsx`，把人工测试用例转换为 IDE 可执行步骤。

实现方式：

1. 使用 `openpyxl` 读取工作表。
2. 定位第 13 行表头。
3. 从第 14 行读取数据。
4. 跳过 `CaseID` 为空的行。
5. 解析 `操作步骤` 为动作列表。
6. 解析 `预期结果` 为断言列表。
7. 对无法解析的步骤标记 `NEED_MAPPING`。
8. 用户在 IDE 中手动选择目标和动作后保存映射规则。

映射规则文件：

```text
.autosmoke/rules/ui_rules.json
```

示例：

```json
{
  "查看签到区域": {
    "action": "inspect",
    "target": {
      "type": "ui_area",
      "name": "签到区域"
    }
  },
  "入口不显示": {
    "assert": "ui_not_exists",
    "target": {
      "type": "text_or_node",
      "name": "签到入口"
    }
  }
}
```

### 18.5 测试执行控制台

目标：

按测试用例执行自动化动作，并实时展示进度、截图、日志和结果。

界面组成：

- 用例列表。
- 当前步骤。
- 执行日志。
- 当前截图。
- UI 树摘要。
- 新增异常。
- 操作按钮：开始、暂停、继续、停止、重跑失败。

实现方式：

1. 根据优先级和筛选条件生成执行队列。
2. 每个用例执行前检查前置条件。
3. 每一步执行前保存前置证据。
4. 执行动作。
5. 等待 UI 稳定或超时。
6. 保存后置证据。
7. 执行断言。
8. 更新结果状态。
9. 回写 Excel 或导出新的结果文件。

每步证据：

- `before.png`
- `after.png`
- `before_ui.json`
- `after_ui.json`
- `before_scene.json`
- `after_scene.json`
- `step_logs.json`
- `step_protocols.json`

### 18.6 自动探索控制台

目标：

自动发现页面、按钮、弹窗关系，并生成页面图谱。

界面输入：

- 最大深度。
- 单页面最大点击数。
- 是否遍历弹窗。
- 是否探索主城。
- 是否探索大地图。
- 黑名单规则。
- 白名单规则。

实现方式：

1. 获取当前页面指纹。
2. 识别安全可点击元素。
3. 按优先级排序按钮。
4. 点击按钮。
5. 判断页面、弹窗、场景是否变化。
6. 记录关系边。
7. 自动关闭弹窗或返回。
8. 加入未访问队列。
9. 达到深度、时间、按钮数量上限后停止。

探索队列结构：

```json
{
  "node_id": "MainCity",
  "depth": 0,
  "path": ["MainCity"],
  "pending_actions": ["邮件", "背包", "活动"]
}
```

### 18.7 主城扫描面板

目标：

识别主城建筑和场景对象，点击后记录建筑弹窗和功能入口。

实现方式：

1. 通过 `MainCityExporter` 获取建筑列表。
2. 根据屏幕坐标过滤当前可见对象。
3. 根据黑名单过滤危险对象。
4. 点击建筑。
5. 判断是否打开建筑弹窗。
6. 遍历弹窗内按钮。
7. 关闭弹窗并恢复主城视角。

对象记录：

```json
{
  "id": "building_townhall",
  "name": "公馆",
  "type": "building",
  "level": 6,
  "screen_pos": [180, 290],
  "states": ["upgrade_available"],
  "visited": true
}
```

### 18.8 大地图扫描面板

目标：

支持大地图缩放、拖动、网格扫描和对象遍历。

界面输入：

- 扫描范围：当前屏、3x3、指定坐标矩形。
- 缩放等级。
- 对象类型过滤：玩家城、资源点、怪物、队列、活动对象。
- 是否允许攻击类操作。

实现方式：

1. 获取当前地图中心坐标和缩放。
2. 设置目标缩放。
3. 生成扫描网格。
4. 移动到网格点。
5. 拉取当前视野对象。
6. 点击安全对象。
7. 遍历对象弹窗。
8. 记录对象关系和异常。

网格记录：

```json
{
  "grid_id": "world_1240_880_z072",
  "center": [1240, 880],
  "zoom": 0.72,
  "objects": 34,
  "visited": true
}
```

### 18.9 弹窗遍历器

目标：

统一处理普通 UI 弹窗、建筑弹窗、大地图对象弹窗。

实现方式：

1. 检测新出现的顶层窗口。
2. 生成弹窗指纹。
3. 识别关闭按钮、确认按钮、取消按钮。
4. 遍历安全按钮。
5. 对二级弹窗递归处理。
6. 尝试关闭弹窗。
7. 如果关闭失败，执行返回键或遮罩点击。

弹窗关闭优先级：

1. 明确关闭按钮。
2. 取消按钮。
3. 返回键。
4. 点击遮罩。
5. 标记 `BLOCKED`，停止当前分支。

### 18.10 异常检测中心

目标：

统一处理所有运行中异常，并将异常转换成报告中的 Bug 或 Warning。

实现方式：

1. 每一步执行后收集新增日志。
2. 对日志做关键字匹配。
3. 对截图做黑屏、空白、变化率检测。
4. 对 UI 树做节点数量和可点击元素检测。
5. 对连接状态做崩溃和断连检测。
6. 对等待时间做卡死判断。
7. 对协议做超时和错误码判断。

异常输出：

```json
{
  "type": "MissingReferenceException",
  "severity": "P1",
  "scene": "MainCity",
  "step_id": "TC001-2",
  "message": "MissingReferenceException: ...",
  "evidence": {
    "screenshot": "after.png",
    "log": "step_logs.json",
    "ui_tree": "after_ui.json"
  }
}
```

### 18.11 页面关系图视图

目标：

展示自动探索发现的页面、弹窗、主城对象、大地图对象之间的关系。

实现方式：

1. 每次页面变化生成节点。
2. 每次点击生成边。
3. 节点保存截图缩略图、类型、指纹、异常数。
4. 边保存动作、目标、结果、耗时。
5. 使用 `page_graph.json` 作为主数据。
6. IDE 内部可用图组件展示，报告中导出 HTML 图。

节点类型：

- `page`
- `popup`
- `main_city_object`
- `world_map_object`
- `bug`
- `blocked`

### 18.12 报告中心

目标：

把执行数据、探索数据、异常数据汇总成可阅读报告。

实现方式：

1. 从运行目录读取 `cases.json`、`bugs.json`、`page_graph.json`。
2. 汇总通过率、失败率、Bug 数、页面覆盖。
3. 生成 `summary.json`。
4. 使用 HTML 模板渲染 `index.html`。
5. 复制或引用截图、日志、UI 树、场景状态。
6. 支持按用例、Bug、页面、场景对象筛选。

报告生成器输入：

```text
run_session.json
cases.json
steps.json
bugs.json
page_graph.json
screenshots/
ui_trees/
scene_states/
logs/
```

### 18.13 后台任务与状态管理

目标：

保证长时间执行时 IDE 不阻塞，并支持暂停、继续、停止。

实现方式：

1. UI 主线程只负责展示。
2. 连接、执行、探索、报告生成放入后台任务。
3. 后台任务通过事件队列向 UI 推送状态。
4. 暂停时停止取新步骤，但保留当前上下文。
5. 停止时结束队列并生成中断报告。
6. 断线时尝试重连，超过阈值标记 `ERROR`。

任务状态：

| 状态 | 说明 |
|---|---|
| `idle` | 空闲 |
| `checking` | 环境检查 |
| `connecting` | 正在连接 |
| `running_case` | 执行用例 |
| `exploring` | 自动探索 |
| `paused` | 已暂停 |
| `stopping` | 正在停止 |
| `reporting` | 生成报告 |
| `finished` | 完成 |
| `error` | 异常 |

### 18.14 配置文件和数据落盘

目标：

所有运行结果可复查、可迁移、可复现。

落盘文件：

| 文件 | 说明 |
|---|---|
| `.autosmoke/config.json` | 项目配置 |
| `.autosmoke/rules/ui_rules.json` | UI 步骤映射 |
| `.autosmoke/rules/scene_rules.json` | 场景对象映射 |
| `.autosmoke/rules/blacklist.json` | 黑名单 |
| `run_session.json` | 本次运行信息 |
| `cases.json` | 用例结果 |
| `steps.json` | 步骤明细 |
| `bugs.json` | Bug 列表 |
| `page_graph.json` | 页面关系图 |
| `summary.json` | 汇总 |

数据原则：

- 每次运行创建独立目录。
- 所有证据文件按步骤 ID 命名。
- 报告只引用当前运行目录内的相对路径。
- 原始 Excel 不强制覆盖，默认导出带结果的新 Excel。

---

## 19. 分阶段落地计划

### 第一阶段：基础闭环

目标：

- 环境配置。
- Poco 连接。
- UI 树 dump。
- 截图。
- JSON 用例执行。
- 基础 HTML 报告。

验收标准：

- 能连接 Unity。
- 能点击指定按钮。
- 能断言文本或弹窗。
- 能输出报告。

### 第二阶段：异常检测

目标：

- 日志监听。
- 崩溃检测。
- 卡死检测。
- 空页面检测。
- Missing Reference 检测。

验收标准：

- 出现异常时报告中有截图、日志、复现路径。

### 第三阶段：自动探索

目标：

- 页面指纹。
- 自动点击安全按钮。
- 弹窗遍历。
- 页面关系图。

验收标准：

- 能发现多个页面和弹窗。
- 能生成页面关系图。

### 第四阶段：主城和大地图

目标：

- 主城对象导出。
- 大地图对象导出。
- 缩放、拖动、网格扫描。
- 场景对象点击和弹窗记录。

验收标准：

- 能识别主城建筑。
- 能识别大地图当前视野对象。
- 能记录场景关系。

### 第五阶段：IDE 产品化

目标：

- 图形化配置。
- 图形化运行监控。
- 图形化报告。
- 打包为 Windows 可执行程序。

验收标准：

- 其他电脑可安装使用。
- 同项目不同路径可运行。
- 新项目可通过配置向导接入。

---

## 20. 风险与处理

| 风险 | 影响 | 处理方式 |
|---|---|---|
| Poco 无法识别部分场景对象 | 主城/大地图漏测 | 使用 Unity 场景导出器补充 |
| ClickContent 文本为空 | 无法按中文定位按钮 | 使用结构、坐标、兄弟文本、配置规则 |
| 自动点击误触危险操作 | 造成账号或资源损失 | 默认黑名单和白名单 |
| 大地图扫描不稳定 | 漏对象或重复对象 | 依赖地图坐标和缩放导出 |
| 不同电脑路径不同 | 配置失效 | 使用 `${PROJECT_PATH}` 和项目内配置 |
| Unity 版本差异 | 插件编译失败 | 接入时做版本检测和编译报告 |
| 日志过多 | 报告噪声大 | 按运行步骤切片，只记录新增日志 |
| UI 动效导致误判 | 假卡死或截图差异 | 等待稳定帧和多信号判定 |

---

## 21. 最终交付物

IDE 交付：

- `AutoSmokeIDE.exe`
- `config/`
- `templates/`
- `docs/`

Unity 插件交付：

- `AutoSmokeUnityPlugin.unitypackage`
- Poco 接入脚本。
- 日志采集脚本。
- 场景导出脚本。
- 主城和大地图导出接口。

项目配置交付：

- `.autosmoke/config.json`
- `.autosmoke/rules/ui_rules.json`
- `.autosmoke/rules/scene_rules.json`
- `.autosmoke/rules/blacklist.json`

报告交付：

- `index.html`
- `summary.json`
- `bugs.json`
- `cases.json`
- `page_graph.json`
- 截图。
- UI 树。
- 场景状态。
- 日志片段。

---

## 22. 结论

AutoSmoke IDE 可以实现从环境配置、项目接入、自动执行、自动探索、异常检测到报告输出的完整流程。对 SLG 主城和大地图这类可缩放、可拖拽场景，不能只依赖 Poco，需要结合 Unity 场景导出、截图识别和日志监听。

推荐优先落地基础闭环，然后逐步扩展到自动探索、主城/大地图扫描和 IDE 产品化。只要配置体系、Unity 插件和报告证据链设计稳，后续换电脑、换路径、接入同项目或新项目都可以做到可控迁移。
