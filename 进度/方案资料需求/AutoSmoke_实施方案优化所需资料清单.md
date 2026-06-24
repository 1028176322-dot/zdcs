# AutoSmoke 实施方案优化所需资料清单

## 1. 目的

为了将 AutoSmoke 从当前的通用自动化方案，进一步提升为：

```text
适配当前 SLG 项目
可落地实施
可跨电脑部署
可精准点击
可完整截图
可验证业务逻辑
可输出可信报告
可最终封装进 IDE
```

需要补充一批项目实际数据、配置、样例文件和运行结果。

这些资料将用于完善：

- 环境部署方案
- Unity Bridge 方案
- GameContent 截图方案
- 自动点击精准执行方案
- 元素映射方案
- 用例解析和执行方案
- 阻塞处理方案
- 业务状态断言方案
- 日志 / 崩溃 / 卡死检测方案
- 报告输出方案
- IDE 产品化方案
- 跨电脑 / 跨项目迁移方案

## 2. 总体优先级

| 优先级 | 含义 | 说明 |
|---|---|---|
| P0 | 必须提供 | 没有这些资料，方案只能停留在通用设计 |
| P1 | 强烈建议 | 能显著提升方案准确性和落地性 |
| P2 | 可后续补充 | 用于产品化、增强报告和完善边界场景 |

## 3. 最小必需资料清单

如果只能先提供一批资料，建议优先提供以下内容：

```text
1. 当前 AutoSmoke 目录结构和关键模块源码
2. Unity 侧 Editor 脚本
3. game_view_state.json / current_ui.json / click_result.json 样例
4. 主城、背包、奖励弹窗、大地图 UI tree JSON
5. 2~5 条真实 Excel 用例
6. 3 个完整 screenshots/run_xxx 目录
7. 当前 config.json
8. 正常日志 + 一个异常日志
```

这些资料足够支撑输出：

```text
AutoSmoke 最终实施蓝图 v2
模块级落地清单
接口协议
阶段排期
验收标准
风险清单
```

## 4. 环境与部署资料

### 4.1 需要提供

| 优先级 | 资料 | 示例 |
|---|---|---|
| P0 | Unity 版本 | `Unity 2022.3.62f3` |
| P0 | Python 版本 | `Python 3.11.x` |
| P0 | Windows 版本 | `Windows 10/11` |
| P0 | AutoSmoke 根目录 | `E:/zdcs/AutoSmoke` |
| P0 | Unity 项目路径 | `E:/s1/k3client/client` |
| P0 | Poco-SDK-master 路径 | `E:/zdcs/Poco-SDK-master` |
| P1 | 是否多显示器 | 主屏/副屏/坐标偏移 |
| P1 | Windows DPI 缩放 | `100% / 125% / 150%` |
| P1 | Android 真机/模拟器信息 | 型号、分辨率、ADB |
| P2 | Python 虚拟环境信息 | venv/conda/system |

### 4.2 建议文件

```text
config.json
requirements.txt 或 pip freeze 输出
部署工具运行日志
Unity Console 编译日志
```

### 4.3 用途

用于完善：

- 一键环境配置。
- 跨电脑部署。
- 路径自动发现。
- Poco SDK 自动接入。
- Python 依赖检查。
- Unity 脚本部署。
- 多显示器 / DPI 兼容。

## 5. AutoSmoke 代码资料

### 5.1 需要提供

| 优先级 | 目录/文件 | 用途 |
|---|---|---|
| P0 | `core_engine/` | GameContent 定位、核心逻辑 |
| P0 | `坐标截图/` | 截图和坐标映射 |
| P0 | `点击执行/` | 点击模式和执行链路 |
| P0 | `用例层/` | 用例解析、执行、批量报告 |
| P0 | `阻塞处理/` | 弹窗、Loading、重连、引导处理 |
| P0 | `元数据/` | UI 元数据、元素映射、目标定位 |
| P0 | `ide/` 或 `IDE/` | IDE 面板和 API |
| P1 | `部署工具/` | 一键部署和路径修复 |
| P1 | `视觉识别/` | OCR 和模板匹配 |

### 5.2 推荐命令输出

```powershell
rg --files E:\zdcs\AutoSmoke
```

也可以提供完整目录压缩包。

### 5.3 用途

用于判断：

- 当前哪些模块已经实现。
- 哪些功能只是方案未实现。
- 哪些模块需要重构。
- 文档是否与代码现状一致。
- 后续实施应优先改哪里。

## 6. Unity 侧脚本资料

### 6.1 需要提供

| 优先级 | 脚本 | 用途 |
|---|---|---|
| P0 | `GameViewLocator.cs` | 判断 GameView 坐标获取能力 |
| P0 | `AutoSmokeClickInjector.cs` | 判断 Unity 注入点击能力 |
| P0 | `AutoSmokeMetadataExporter.cs` | 判断 UI 元数据导出能力 |
| P0 | `AutoSmokeGameViewBridge.cs` | 判断 Unity 直连定位能力 |
| P1 | `AutoSmokeLayoutDiagnostics.cs` | 判断布局诊断能力 |
| P1 | `AutoSmokeGameContentCapture.cs` | 判断 Unity 直出 PNG 能力 |
| P1 | `AutoSmokeStateExporter.cs` | 判断业务状态导出能力 |

### 6.2 需要配套输出

```text
game_view_state.json
click_request.json
click_result.json
current_ui.json
current_scene.json
current_state.json
layout_diagnostics.json
```

### 6.3 用途

用于完善：

- Unity Bridge 通信协议。
- 精准点击实现方式。
- GameContent 截图方案。
- 业务状态采集方案。
- 跨项目脚本部署方案。
- Editor-only 代码边界。

## 7. UI 树与元素资料

### 7.1 需要提供的界面

| 优先级 | 界面 | 用途 |
|---|---|---|
| P0 | 主城 | 场景对象、底部菜单、任务栏 |
| P0 | 大地图 | 缩放、拖动、场景对象 |
| P0 | 背包 | 列表、道具、使用按钮 |
| P0 | 奖励弹窗 | 弹窗关闭和确认 |
| P0 | 建筑功能菜单 | 建筑点击和功能按钮 |
| P1 | 获取更多弹窗 | 空白关闭、列表按钮 |
| P1 | Loading | 转场和进度识别 |
| P1 | 重连 | 网络恢复等待 |
| P1 | 引导遮罩 | 高亮目标点击 |
| P1 | 活动入口 | 右侧活动按钮 |

### 7.2 文件格式

优先提供：

```text
Poco UI tree JSON
current_ui.json
enhanced_ui_tree.json
accessibility_scan.json
```

每个界面建议一组：

```text
ui_tree_main_city.json
ui_tree_bag.json
ui_tree_reward_popup.json
ui_tree_world_map.json
```

### 7.3 用途

用于完善：

- 元素映射规则。
- 自动生成 element_mapping_draft。
- 页面识别。
- 弹窗识别。
- 可点击元素判断。
- 重名节点消歧。
- testId / semanticId 设计。

## 8. 截图与 metadata 样本

### 8.1 需要提供

完整保留运行目录，例如：

```text
screenshots/run_20260615_170342/
├── game_content_20260615_170342.png
├── game_view_20260615_170342.png
└── metadata_20260615_170342.json
```

如果有调试图，也一起提供：

```text
debug_three_layers.png
debug_content_top_scan.png
debug_game_content_expected_rect.png
```

### 8.2 建议场景

| 优先级 | 场景 |
|---|---|
| P0 | 主城完整图 |
| P0 | 大地图完整图 |
| P0 | 背包界面 |
| P0 | 奖励弹窗 |
| P1 | 获取更多弹窗 |
| P1 | Loading |
| P1 | 重连 |
| P1 | 引导 |
| P1 | 建筑菜单 |

### 8.3 用途

用于完善：

- Unity 直出 PNG 验收。
- 屏幕裁剪兜底策略。
- metadata 结构。
- 截图完整性判断。
- 报告截图展示。
- OCR / 模板兜底策略。

## 9. 用例与测试流程资料

### 9.1 需要提供

| 优先级 | 资料 | 说明 |
|---|---|---|
| P0 | `用例模板.xlsx` | 当前测试模板 |
| P0 | 2~5 条真实用例 | 测试人员实际写法 |
| P0 | 用例执行期望 | 每步如何判断通过 |
| P1 | 批量执行需求 | 是否按模块/版本/账号分组 |
| P1 | 失败处理策略 | stop/retry/continue |

### 9.2 推荐真实用例

```text
背包使用道具
领取任务奖励
升级建筑
打开活动并领取奖励
建筑菜单呼出和进入功能
```

### 9.3 用途

用于完善：

- Excel 字段规范。
- 用例 DSL。
- 步骤解析器。
- 目标定位表达。
- 业务断言写法。
- 批量报告结构。

## 10. 业务状态与数据结构资料

### 10.1 需要提供

| 优先级 | 状态 | 示例 |
|---|---|---|
| P0 | 玩家基础状态 | level、uid、server |
| P0 | 资源状态 | gold、food、wood、diamond |
| P0 | 背包状态 | itemId、count |
| P1 | 建筑状态 | level、upgradeState |
| P1 | 任务状态 | progress、canClaim |
| P1 | 活动状态 | progress、rewardClaimable |
| P1 | 场景状态 | currentScene、loading |

### 10.2 可以提供的形式

```text
字段说明文档
Manager 类接口说明
状态 JSON 样例
before/after 手工记录
```

### 10.3 用途

用于完善：

- AutoSmokeStateExporter。
- 业务断言 DSL。
- 状态 Diff。
- 业务规则库。
- 逻辑验证报告。

## 11. 日志与异常资料

### 11.1 需要提供

| 优先级 | 日志 | 用途 |
|---|---|---|
| P0 | 正常运行日志 | 建立基线 |
| P0 | 点击成功日志 | 点击链路验证 |
| P1 | MissingReference 日志 | 异常识别 |
| P1 | NullReference 日志 | 异常识别 |
| P1 | 重连日志 | 网络阻塞 |
| P1 | Loading 超时日志 | 卡死/转场问题 |
| P2 | 崩溃日志 | 崩溃检测 |
| P2 | Android logcat | 真机扩展 |

### 11.2 用途

用于完善：

- 崩溃检测。
- 卡死检测。
- Missing Reference 识别。
- Unity 异常归类。
- 报告日志片段。

## 12. 阻塞界面资料

### 12.1 需要提供

| 优先级 | 阻塞类型 | 需要信息 |
|---|---|---|
| P0 | 普通弹窗 | 标题、关闭方式、按钮 |
| P0 | 奖励弹窗 | 确认按钮、奖励内容 |
| P0 | Loading | 识别特征、超时时间 |
| P0 | 重连 | 识别特征、恢复条件 |
| P1 | 引导 | 高亮区域、跳过按钮 |
| P1 | 危险确认 | 哪些不能点确定 |
| P1 | 空白关闭弹窗 | 可点击安全区域 |

### 12.2 用途

用于完善：

- blocker_rules。
- blocker_detector。
- blocker_resolver。
- 阻塞报告。
- 用例恢复策略。

## 13. IDE 产品化需求

### 13.1 需要明确

| 优先级 | 问题 |
|---|---|
| P0 | 谁使用 IDE：测试、策划、开发？ |
| P0 | 是否需要一键部署 Unity 脚本？ |
| P0 | 是否需要一键执行 Excel？ |
| P0 | 是否需要实时日志窗口？ |
| P0 | 是否需要报告历史记录？ |
| P1 | 是否需要元素映射编辑器？ |
| P1 | 是否需要截图反查元素？ |
| P1 | 是否需要用例编辑器？ |
| P1 | 是否需要打包 EXE？ |
| P2 | 是否需要多人共享报告？ |

### 13.2 用途

用于完善：

- IDE 信息架构。
- 菜单设计。
- 页面布局。
- API 路由。
- 打包部署。
- 用户操作流程。

## 14. 推荐资料打包结构

建议统一打包为：

```text
AutoSmoke资料包_YYYYMMDD/
├── 01_环境/
│   ├── config.json
│   ├── pip_freeze.txt
│   └── 部署日志.txt
├── 02_AutoSmoke代码/
│   └── rg_files.txt
├── 03_Unity脚本/
│   ├── GameViewLocator.cs
│   ├── AutoSmokeClickInjector.cs
│   └── ...
├── 04_Unity输出/
│   ├── game_view_state.json
│   ├── click_result.json
│   └── current_ui.json
├── 05_UI树/
│   ├── ui_tree_main_city.json
│   ├── ui_tree_bag.json
│   └── ...
├── 06_截图样本/
│   ├── run_20260615_170342/
│   └── run_20260615_165315/
├── 07_用例/
│   ├── 用例模板.xlsx
│   └── 真实用例样例.xlsx
├── 08_日志/
│   ├── normal.log
│   ├── missing_reference.log
│   └── reconnect.log
└── 09_需求说明/
    ├── IDE期望.md
    └── 报告期望.md
```

## 15. 提供资料后的产出

收到资料后，可以进一步输出：

```text
AutoSmoke 最终实施蓝图 v2
模块级实施清单
Unity Bridge 协议定稿
Excel 用例模板定稿
元素映射规则定稿
点击精准执行落地方案 v2
Unity 直出 PNG 落地方案 v2
业务断言规则库初版
报告字段规范
跨电脑部署验收清单
阶段排期与风险清单
```

## 16. 当前最建议优先补充

第一批优先：

```text
1. 当前 config.json
2. game_view_state.json
3. click_result.json
4. current_ui.json 或 enhanced_ui_tree.json
5. 主城 UI tree JSON
6. 背包 UI tree JSON
7. 奖励弹窗 UI tree JSON
8. 一份真实 Excel 用例
9. 一个完整 screenshots/run_xxx 目录
10. Unity 侧 Editor 脚本
```

这 10 项是把方案继续细化到项目实际落地的关键资料。

