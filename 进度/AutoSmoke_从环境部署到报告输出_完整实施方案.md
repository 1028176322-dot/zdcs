# AutoSmoke — 从环境部署到报告输出：完整实施方案

> 版本：1.5 | 更新：2026-06-16 18:20 | 前序方案：19 份文档 | 5阶段全部完成 + 交互元素扩展 | 功能验收状态：**待用户逐项确认**

---

## 一、当前状态总览

### 1.1 模块健康度

> 验收状态说明：**待验收** = 等待用户确认通过；**已验收** = 用户确认功能正常；**无需验收** = 纯工具/辅助模块

| 模块 | 文件 | 加载 | 功能 | 验收状态 | 依赖工具 | 备注 |
|------|------|:----:|:----:|:--------:|----------|------|
| 坐标映射 | `坐标截图/coordinate_mapper.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 8种坐标互转 + 副屏偏移 |
| 动态分辨率 | `坐标截图/resolution_manager.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 4层来源优先级 |
| 屏幕裁剪截图 | `坐标截图/screenshot_game_content.py` | ✅ | ⚠️ | 待验收 | Python 3.11+, Pillow 10+ | 三级裁剪 + 元数据绑定；受 GameView 高度/工具栏/DPI 影响，作为兜底 |
| Unity 直出截图 | `tools/AutoSmokeGameContentCapture.cs` | ✅ | ✅ | 待验收 | Unity 2022.3+ | 推荐主方案：Unity 直接输出完整 GameContent PNG |
| 截图差异 | `坐标截图/screenshot_diff.py` | ✅ | ✅ | 无需验收 | numpy 1.26+ | 差异比例 + 高亮图 |
| 点击执行 | `点击执行/click_game_content.py` | ✅ | ✅ | 待验收 | Python 3.11+, pywin32 310+ | 4种坐标类型 |
| 点击模式 | `点击执行/click_mode.py` | ✅ | ✅ | 待验收 | Python 3.11+, pocoui 1.0+ | 3种模式 |
| 点击校验 | `点击执行/click_validator.py` | ✅ | ✅ | 待验收 | Python 3.11+ | preCheck/postCheck |
| OCR/模板 | `视觉识别/game_content_vision.py` | ✅ | ✅ | 待验收 | OpenCV 4.6+, Tesseract 5.4+, pytesseract 0.3+ | OCR 中文+英文已配置 |
| 步骤解析 | `用例层/case_step_parser.py` | ✅ | ✅ | 待验收 | Python 3.11+, openpyxl 3.1+ | 8种动作 + 7种定位 |
| 步骤执行 | `用例层/case_step_executor.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 含 preCheck/postCheck |
| 批量执行 | `用例层/batch_runner.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 用例隔离 + HTML 报告 |
| 报告中心 | `用例层/report_center.py` | ✅ | ✅ | 待验收 | Python 3.11+ | HTML 汇总报告 |
| IDE 面板 | `IDE/debug_panel.py` | ✅ | ✅ | 待验收 | Flask 3.x, Python 3.11+ | 80条 API（含异常检测+审核面板+enhanced流程+运行态Bridge+匹配+交互元素分类） |
| IDE 入口 | `autosmoke_web_ide.py` | ✅ | ✅ | 待验收 | Flask 3.x | 统一启动入口，支持 --check，默认 debug 模式 |
| UI树增强 | `元数据/ui_tree_enhancer.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 工程态清洗增强：205293→10759候选，P0/P1/P2/P3分层，中文描述/置信度/角色/优先级/clickTargetNode/elementType |
| 运行时匹配 | `元数据/runtime_matcher.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 7级匹配规则（P0-P7），匹配评分+冲突检测，支持候选与实时UI树匹配 |
| 合并增强 | `元数据/merged_ui_tree.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 工程态+运行态合并输出 enhanced_ui_tree.json |
| 映射草稿生成 | `元数据/element_mapping.py` + `enhanced_ui_tree.json` | ✅ | ✅ | 待验收 | Python 3.11+ | 从增强UI树生成草稿（enhanced字段优先），6,108条候选草稿（P0/P1/P2/P3分层），支持 normalise_elements_from_payload 兼容多格式 |
| 页面关系图 | `元数据/page_graph.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 记录 fromPage→action→element→toPage，输出 JSON+HTML |
| 阻塞检测 | `阻塞处理/blocker_detector.py` | ✅ | ✅ | 待验收 | OpenCV 4.6+, Tesseract 5.4+ | 10种阻塞类型 |
| 阻塞处理 | `阻塞处理/blocker_resolver.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 关闭/取消/空白区 |
| 执行守卫 | `阻塞处理/post_action_guard.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 每步后检查 |
| UI 状态 | `阻塞处理/ui_state_checker.py` | ✅ | ✅ | 无需验收 | Python 3.11+ | 前置条件检查 |
| 阻塞规则 | `阻塞处理/blocker_rules.py` | ✅ | ✅ | 无需验收 | Python 3.11+ | 关键词/优先级 |
| 元数据读取 | `元数据/metadata_reader.py` | ✅ | ✅ | 待验收 | Python 3.11+ | testId 搜索 |
| 可测性扫描 | `元数据/accessibility_scanner.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 评分 + 问题列表 |
| 元素映射 | `元数据/element_mapping.py` | ✅ | ✅ | 待验收 | Python 3.11+ | CRUD + 反查 |
| 目标定位 | `元数据/target_locator.py` | ✅ | ✅ | 待验收 | Python 3.11+, OpenCV 4.6+ | 5级优先级 |
| Bridge 读取 | `元数据/game_view_state_reader.py` | ✅ | ✅ | 待验收 | Python 3.11+ | Unity Bridge 状态读取 |
| Unity 截图读取 | `元数据/capture_reader.py` | ✅ | ✅ | 待验收 | Python 3.11+ | Unity直出PNG触发与读取 |
| 日志采集器 | `异常检测/unity_log_collector.py` | ✅ | ✅ | 待验收 | Python 3.11+ | Unity Editor.log 实时采集，9种错误模式 |
| 崩溃检测 | `异常检测/crash_detector.py` | ✅ | ✅ | 待验收 | Python 3.11+ | 进程存活+日志关键字+Poco心跳 |
| 卡死检测 | `异常检测/hang_detector.py` | ✅ | ✅ | 待验收 | Python 3.11+, OpenCV 4.6+ | 截图变化率15s阈值+UI树+排除允许静止 |
| 脚本部署 | `部署工具/deploy_tools.py` | ✅ | ✅ | 无需验收 | Python 3.11+ | 13个 C# 脚本 → Unity |
| Poco 连接 | `core_engine/poco_connector/` | ✅ | ✅ | 待验收 | pocoui 1.0.94+ | Unity UI 树连接 |

### 1.2 Unity 侧脚本

| 脚本 | 位置 | 功能 | 部署状态 | 验收状态 |
|------|------|------|:--------:|:--------:|
| `GameViewLocator.cs` | `Assets/Editor/` | GameView 坐标反射读取 | ✅ 已部署 | 待验收 |
| `AutoSmokeClickInjector.cs` | `Assets/Editor/` | EventSystem 点击注入（testId/semanticId/pocoPath/coordinate）+ 原子写入 + consumed 确认信号 | ✅ 已部署 | 待验收 |
| `AutoSmokeMetadataExporter.cs` | `Assets/Editor/` | 元数据导出（5阶段：UI扫描+场景对象+可测性） | ✅ 已部署 | 待验收 |
| `AutoSmokeGameViewBridge.cs` | `Assets/Editor/` | 直连定位状态实时导出（0.5s间隔） | ✅ 已部署 | 待验收 |
| `AutoSmokeLayoutDiagnostics.cs` | `Assets/Editor/` | 布局诊断辅助 | ✅ 已部署 | 无需验收 |
| `AutoSmokeGameContentCapture.cs` | `Assets/Editor/` | Unity 直出完整 GameContent PNG（P0 截图主方案） | ✅ 已部署 | 待验收 |
| `AutoSmokeUIPrefabScanner.cs` | `Assets/Editor/` | 工程态 UI Prefab 扫描（UI树方案 阶段一） | ✅ 已部署 | 待验收 |
| `AutoSmokeUITreeExporter.cs` | `Assets/Editor/` | 运行态 UI 树导出（16字段+图标采集，UI树方案 阶段二） | ✅ 已部署 | 待验收 |
| `AutoSmokeRuntimeBridge.cs` | `Assets/Editor/` | 运行态 Bridge：心跳+请求监听+响应（阶段2） | ✅ 已部署 | 待验收 |
| `AutoSmokeRuntimeUITreeDumper.cs` | `Assets/Editor/` | 运行态 UI 树导出器（交互元素类型扩展，13个扩展字段） | ✅ 已部署 | 待验收 |
| `AutoSmokeSceneInteractionExporter.cs` | `Assets/Editor/` | 场景交互对象导出（建筑/地图/资源点等8种类型） | ✅ 已部署 | 待验收 |

### 1.3 整体进度

```
定位系统: ████████████░░░ 80%
坐标系统: █████████████░░ 85%
截图系统: ███████████████░ 95%  ← Unity 直出已部署
点击系统: ██████████████░░ 85%  ← EventSystem注入+按interactionType分发
用例系统: ████████████░░░ 80%
阻塞处理: ████████████░░░ 80%
元数据:   ████████████████ 100%  ← enhanced+runtime_match+scene_interaction
IDE面板:  ████████████████░ 92%  ← 80条API + 交互元素分类 + 5阶段前端
Unity侧:  ████████████████░ 95%  ← 13个C#脚本全部部署（含SceneInteractionExporter）
5阶段方案:████████████████ 100% ← 全部完成
交互元素扩展:████████████████ 100% ← 补充方案全部完成
──────────────────────
整体:     ████████████████░ 88% (B档)  ← 较此前 80% 提升
```

### 1.4 已废弃/不推荐

| 废弃项 | 原因 | 替代 |
|--------|------|------|
| `contentWidth = height - contentTop × ratio` 算法 | 窗口拉伸时宽度错误 | `_fit_content_rect_in_render_area` aspect-fit |
| 固定屏幕坐标作为用例目标 | 分辨率/窗口变化时失效 | testId / semanticId / normalized |
| 截图→坐标→鼠标点击 作为主链路 | 受GV拉伸/DPI/多屏影响 | Unity EventSystem 注入 |
| Python 屏幕裁剪截图作为唯一截图来源 | 容易受工具栏、GameView 高度、DPI 影响 | Unity 直出 PNG 为主，屏幕裁剪兜底 |

---

## 二、环境部署

### 2.1 系统要求

- Windows 10/11（支持多显示器）
- **Python 3.11+**（当前使用 3.13.12，推荐保持一致）
- **Unity 2022.3+**（Editor 模式，当前使用 2022.3.62f3）

### 2.2 依赖工具清单

| 分类 | 工具 | 需求版本 | 当前版本 | 安装命令 | 用途 |
|------|------|:--------:|:--------:|----------|------|
| **核心语言** | Python | ≥ 3.11 | 3.13.12 | — | 运行时 |
| **核心依赖** | pywin32 | ≥ 310 | 311 | `pip install pywin32` | Windows API（截图/点击/窗口操作） |
| | pillow | ≥ 10.0 | 12.2.0 | `pip install pillow` | 图像处理 |
| | numpy | ≥ 1.26 | 2.4.6 | `pip install numpy` | 数值计算 |
| | flask | ≥ 3.0 | 3.1.3 | `pip install flask` | Web IDE 框架 |
| **Poco SDK** | pocoui | ≥ 1.0.94 | 1.0.94 | `pip install pocoui` | Unity UI 树连接 |
| **图像分析** | opencv-python | ≥ 4.6.0 | 4.13.0 | `pip install opencv-python` | 模板匹配/图像分析 |
| | opencv-contrib-python | ≥ 4.6.0 | 4.13.0 | `pip install opencv-contrib-python` | 增强图像功能 |
| **OCR** | Tesseract-OCR 引擎 | ≥ 5.4.0 | 5.4.0 | [下载安装](https://github.com/UB-Mannheim/tesseract) | 文字识别二进制引擎 |
| | pytesseract | ≥ 0.3.10 | 0.3.13 | `pip install pytesseract` | Python OCR 绑定 |
| | 中文语言包 | chi_sim | ✅ 已装 (44MB) | [下载](https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata) | 中文识别 |
| **Excel** | openpyxl | ≥ 3.1.0 | 3.1.5 | `pip install openpyxl` | .xlsx 文件解析 |
| **Unity** | Unity Editor | ≥ 2022.3 | 2022.3.62f3 | Unity Hub | 脚本运行环境 |
| | Poco SDK (Unity 端) | ≥ 1.0 | ✅ 已集成 | 从 Poco-SDK 复制 | Unity UI 树导出 |
| **IDE** | Flask | ≥ 3.0 | 3.1.3 | `pip install flask` | Web 界面 |

### 2.3 Python 环境

```bash
# 一键安装核心依赖
pip install pywin32 pillow numpy flask opencv-python opencv-contrib-python pocoui

# 安装 OCR（增强文字识别）
pip install pytesseract
# Tesseract-OCR 引擎 v5.4.0 已安装于: C:\Program Files\Tesseract-OCR\
# 中文语言包 (chi_sim, 44MB) 已安装

# 安装 Excel 读取
pip install openpyxl
```

### 2.4 部署 Unity 脚本

```bash
# 一键部署所有 Editor 脚本
python 部署工具/deploy_tools.py

# 或通过 IDE 面板部署
# 打开 http://localhost:5000 → 脚本部署 → 部署全部
```

部署后会复制以下 **13 个** 脚本到 Unity 项目：
```
AutoSmoke/Assets/Editor/
├── GameViewLocator.cs           # GameView 坐标定位
├── AutoSmokeClickInjector.cs    # EventSystem 点击注入（testId/semanticId/pocoPath/coordinate）
├── AutoSmokeMetadataExporter.cs # 元数据导出（5阶段）
├── AutoSmokeGameViewBridge.cs   # 直连定位状态实时导出
├── AutoSmokeLayoutDiagnostics.cs# 布局诊断
└── AutoSmokeGameContentCapture.cs # Unity 直出完整 GameContent PNG
├── AutoSmokeUIPrefabScanner.cs    # 工程态 UI Prefab 扫描（UI树方案 阶段一）
├── AutoSmokeUITreeExporter.cs     # 运行态 UI 树导出（16字段+图标采集）
├── AutoSmokeRuntimeBridge.cs      # 运行态 Bridge：心跳+请求监听+响应（阶段2）
├── AutoSmokeRuntimeUITreeDumper.cs# 运行态 UI 树导出器（交互元素类型扩展）
└── AutoSmokeSceneInteractionExporter.cs # 场景交互对象导出（补充方案）
```

### 2.5 Unity 项目配置

在 `config.json` 中设置：
```json
{
  "unity_project_path": "E:/s1/k3client/client",
  "game_resolution": { "width": 1170, "height": 2532 },
  "game_view_coords": { "left": 309, "top": 73, "width": 703, "height": 799 },
  "game_content_rect": { "left": 185, "top": 43, "width": 332, "height": 718 }
}
```

### 2.6 启动 IDE 面板

```bash
# 方式一：统一入口（推荐）
python autosmoke_web_ide.py

# 方式二：直接启动
python IDE/debug_panel.py

# 打开 http://localhost:5000

# 环境检查（不启动）
python autosmoke_web_ide.py --check

# 指定端口
python autosmoke_web_ide.py --port 8080
```

### 2.7 首次定位校准

```
1. IDE 面板 → 刷新状态（自动执行全链路定位）
2. 截取 GameContent → 检查截图是否完整
3. 如果底部不完整：自动扩展截图区域（margin < 30px 触发）
4. 确认 Green box 框住完整游戏画面
```

---

## 三、功能完成与验收状态

> 以下表格列出整条执行流程线上每个功能的完成情况、验收标准和验收状态。
> **验收方式**：用户逐项确认功能是否正常，确认通过后修改验收状态为"✅ 已验收"。
> **验收标准**：每个功能有明确的判断标准，用户根据实际情况确认通过/不通过。

### 3.1 定位系统

| 功能 | 文件 | 完成 | 验收状态 | 验收标准（用户确认项） |
|------|------|:----:|:--------:|----------------------|
| GameView 窗口定位 | `定位/locate_game_area_smart.py` | ✅ | ☐ 待验收 | 1. Unity Editor 运行时，能正确识别 GameView 位置<br>2. 多显示器场景下坐标正确<br>3. 红框框出 GameView 完整窗口 |
| GameContent 三层定位 | `core_engine/game_content_locator.py` | ✅ | ☐ 待验收 | 1. aspect-fit 正确计算 content 区域<br>2. contentTop 检测 ≤ ±8px 偏差<br>3. 绿框框出完整游戏内容（顶部头像+底部功能栏均可见） |
| Unity Bridge 直连定位 | `tools/AutoSmokeGameViewBridge.cs` | ✅ | ☐ 待验收 | 1. `game_view_state.json` 正常导出<br>2. 坐标经 IDE 显示正确（≈ config.json 中的值）<br>3. 自动刷新（写请求→等Unity→读结果）周期 ≤ 15s |
| 动态分辨率读取 | `坐标截图/resolution_manager.py` | ✅ | ☐ 待验收 | 1. 4层来源优先级正确<br>2. Bridge > 反射 > 缓存 > 兜底<br>3. 分辨率变化后自动检测 |
| 坐标映射 | `坐标截图/coordinate_mapper.py` | ✅ | ☐ 待验收 | 1. design→screen 坐标转换正确<br>2. 虚拟屏幕偏移正确（副屏场景）<br>3. scaleX 与 scaleY 差异 ≤ 5% |
| 底部缺失自动扩展 | `定位/locate_game_area_smart.py` | ✅ | ☐ 待验收 | 1. GV高度不足时自动向下扩展<br>2. margin < 30px 触发扩展<br>3. 扩展后底部内容完整 |

### 3.2 截图系统

| 功能 | 文件 | 完成 | 验收状态 | 验收标准（用户确认项） |
|------|------|:----:|:--------:|----------------------|
| Python 屏幕裁剪截图 | `坐标截图/screenshot_game_content.py` | ✅ | ☐ 待验收 | 1. 能正常截取 GameContent 区域<br>2. 截图不含工具栏/桌面背景<br>3. 作为 Unity 直出不可用时的兜底 |
| Unity 直出 PNG | `tools/AutoSmokeGameContentCapture.cs` | ✅ | ☐ 待验收 | 1. Unity 菜单 `AutoSmoke > 直出截图 > 导出截图` 可触发<br>2. 输出 PNG 为完整 GameContent 区域（不含工具栏）<br>3. 分辨率为设计分辨率（如 1170×2532）<br>4. 截图内容完整（顶部头像栏 + 底部功能栏均可见）<br>5. 元数据 JSON 随 PNG 同时生成 |
| 截图差异对比 | `坐标截图/screenshot_diff.py` | ✅ | ☐ 待验收 | 1. 点击前后截图差异比例可计算<br>2. 差异高亮图可生成<br>3. 判定阈值可配置 |

### 3.3 点击系统

| 功能 | 文件 | 完成 | 验收状态 | 验收标准（用户确认项） |
|------|------|:----:|:--------:|----------------------|
| 点击模式（3种） | `点击执行/click_mode.py` | ✅ | ☐ 待验收 | 1. real_mouse 模式可点击<br>2. poco_click 模式（需 Poco 连接）<br>3. unity_inject 模式可写入 click_request.json |
| Unity EventSystem 注入 | `tools/AutoSmokeClickInjector.cs` | ✅ | ☐ 待验收 | 1. testId 定位点击 → 目标元素收到事件<br>2. semanticId 定位点击 → 目标元素收到事件<br>3. coordinate 坐标 Raycast → 最近元素收到事件<br>4. click_result.json 正常写回 |
| 点击前校验 (preCheck) | `点击执行/click_validator.py` | ✅ | ☐ 待验收 | 1. 元素不存在时正确返回 BLOCKED<br>2. 元素被遮挡时正确返回 BLOCKED<br>3. 坐标类型跳过元素校验（不阻塞） |
| 点击后校验 (postCheck) | `点击执行/click_validator.py` | ✅ | ☐ 待验收 | 1. 截图差异分析正常<br>2. 元素可见/消失检测正常（需 Poco）<br>3. 期望不满足时正确 FAIL |
| 危险操作拦截 | `阻塞处理/blocker_rules.py` | ✅ | ☐ 待验收 | 1. OCR 识别到"充值/购买/支付"时阻断点击<br>2. 确保不点确认按钮<br>3. 仅点取消或返回 |

### 3.4 用例系统

| 功能 | 文件 | 完成 | 验收状态 | 验收标准（用户确认项） |
|------|------|:----:|:--------:|----------------------|
| 步骤解析（自然语言） | `用例层/case_step_parser.py` | ✅ | ☐ 待验收 | 1. "点击 xxx" → action=click<br>2. "等待 N 秒" → action=wait<br>3. "截图" → action=screenshot<br>4. testId 格式解析正确 |
| Excel 用例导入 | `用例层/case_step_parser.py` | ✅ | ☐ 待验收 | 1. 可读取 .xlsx 文件<br>2. 自动检测表头行（"操作步骤"列）<br>3. CaseID/模块等业务字段保留到 `_excel_row` |
| 步骤执行器 | `用例层/case_step_executor.py` | ✅ | ☐ 待验收 | 1. 步骤按顺序执行<br>2. 失败时短路（skip 后续步骤）<br>3. preCheck/postCheck 集成在流程中 |
| 批量运行 | `用例层/batch_runner.py` | ✅ | ☐ 待验收 | 1. 多用例隔离运行<br>2. 每个用例独立开始/结束时间<br>3. 结果汇总 |
| HTML 报告 | `用例层/report_center.py` | ✅ | ☐ 待验收 | 1. 报告包含用例列表/状态/步骤详情<br>2. 支持 before/after 截图嵌入<br>3. 报告可在浏览器打开查看 |

### 3.5 阻塞处理

| 功能 | 文件 | 完成 | 验收状态 | 验收标准（用户确认项） |
|------|------|:----:|:--------:|----------------------|
| 阻塞检测 | `阻塞处理/blocker_detector.py` | ✅ | ☐ 待验收 | 1. OCR 检测弹窗文字 → 识别具体类型<br>2. 遮罩弹窗识别（亮度分析+弹窗矩形）<br>3. 10种阻塞类型覆盖 |
| 阻塞处理 | `阻塞处理/blocker_resolver.py` | ✅ | ☐ 待验收 | 1. 点击关闭按钮<br>2. 点击取消按钮<br>3. 空白区点击关闭<br>4. 返回键模拟 |
| 执行后守卫 | `阻塞处理/post_action_guard.py` | ✅ | ☐ 待验收 | 1. 每步执行后自动检查阻塞<br>2. 发现阻塞自动处理<br>3. 处理成功后继续下一步 |

### 3.6 元数据系统

| 功能 | 文件 | 完成 | 验收状态 | 验收标准（用户确认项） |
|------|------|:----:|:--------:|----------------------|
| 元数据导出 (C#) | `tools/AutoSmokeMetadataExporter.cs` | ✅ | ☐ 待验收 | 1. Unity 菜单 `AutoSmoke > 导出元数据` 可用<br>2. 输出 `current_ui.json`（含 screenRect/type/clickable）<br>3. 输出 `current_scene.json`（含建筑/地图对象） |
| 元数据读取 (Python) | `元数据/metadata_reader.py` | ✅ | ☐ 待验收 | 1. 正确加载 current_ui.json<br>2. testId 搜索返回正确元素<br>3. type/clickable 筛选项正确 |
| 目标定位器 | `元数据/target_locator.py` | ✅ | ☐ 待验收 | 1. testId → metadata → screenRect<br>2. Poco UI 树 → 元素名/坐标<br>3. 模板匹配 → 图标坐标<br>4. 5级优先级降级正确 |
| 元素语义映射 | `元数据/element_mapping.py` | ✅ | ☐ 待验收 | 1. 标注元素（displayName/testId/role/pageId）<br>2. 截图反查（点击截图→命中候选）<br>3. 映射数据持久化 |
| 可测性扫描 | `元数据/accessibility_scanner.py` | ✅ | ☐ 待验收 | 1. testId覆盖率统计<br>2. 危险按钮检测<br>3. 可测性评分 ≤ 100 |

### 3.7 IDE 面板

| 功能 | 文件 | 完成 | 验收状态 | 验收标准（用户确认项） |
|------|------|:----:|:--------:|----------------------|
| 定位状态显示 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 显示 GameView/GameContent 坐标<br>2. 显示分辨率/缩放比例<br>3. 显示定位来源（Bridge/Python） |
| 刷新定位 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 点击刷新 → 自动执行全链路定位<br>2. 更新 config.json<br>3. 刷新周期 ≤ 15s |
| 截图预览 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 截取 GameContent 并显示<br>2. 双模式支持（Unity直出 / Python裁剪）<br>3. 模式徽标显示正确 |
| Before/After 对比 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 可分别拍摄 Before/After 截图<br>2. 对比显示差异比例<br>3. 差异高亮图可查看 |
| 元数据查看 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 元数据状态卡片（总数/可点击/类型分布）<br>2. 元素列表（按 type/clickable 筛选）<br>3. 元数据搜索 |
| 步骤执行 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 输入步骤文本并执行<br>2. 显示执行结果（PASS/FAIL）<br>3. 日志实时显示 |
| 脚本部署 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 显示 6 个 C# 脚本部署状态<br>2. 一键部署到 Unity 项目<br>3. 部署结果反馈 |
| 语义映射 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 元素标注表单<br>2. 截图反查功能<br>3. 映射列表/删除/筛选 |
| 审核面板 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 三栏布局（草稿列表/截图高亮/详情编辑）<br>2. 5种审核状态（待审核/已确认/已修改/已拒绝/已忽略）<br>3. 搜索/筛选/编辑/测试点击 |
| 日志/崩溃/卡死检测 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. Unity 日志实时采集显示<br>2. 崩溃检测（进程+日志+Poco心跳）<br>3. 卡死检测（截图变化率+UI树） |
| 元素映射草稿审核 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 从工程态数据生成14,140条中文映射草稿<br>2. 三栏审核面板<br>3. 确认后自动导出正式映射 |
| 阻塞检测/处理 | `IDE/debug_panel.py` | ✅ | ☐ 待验收 | 1. 点击阻塞检测 → 显示当前阻塞<br>2. 点击阻塞处理 → 自动处理<br>3. 执行后守卫检查 |

### 3.8 Unity 脚本

| 脚本 | 功能 | 完成 | 验收状态 | 验收标准（用户确认项） |
|------|------|:----:|:--------:|----------------------|
| GameViewLocator.cs | GameView 坐标反射读取 | ✅ | ☐ 待验收 | 1. Unity 反射读取 position/currentGameViewSize<br>2. 输出 game_view_pos.json<br>3. PollLocateRequest 轮询触发 |
| AutoSmokeClickInjector.cs | EventSystem 点击注入 | ✅ | ☐ 待验收 | 1. testId 查找 GameObject<br>2. EventSystem.RaycastAll + ExecuteEvents<br>3. preCheck 通过才注入<br>4. 写回 click_result.json |
| AutoSmokeMetadataExporter.cs | 元数据导出 | ✅ | ☐ 待验收 | 1. 递归扫描所有 Canvas UI 元素<br>2. screenRect + type + clickable 推断<br>3. 场景对象扫描（建筑/地图）<br>4. 自动定时更新（3s） |
| AutoSmokeGameViewBridge.cs | 直连定位状态导出 | ✅ | ☐ 待验收 | 1. game_view_state.json 含完整区域数据<br>2. aspect-fit 计算 GameContent 区域<br>3. 0.5s 定时导出 / 请求文件触发 |
| AutoSmokeGameContentCapture.cs | Unity 直出 GameContent PNG | ✅ | ☐ 待验收 | 1. ScreenCapture 截取 GameView<br>2. aspect-fit 裁剪 GameContent<br>3. 缩放至设计分辨率并保存 PNG<br>4. 3种触发方式（菜单/请求/定时） |
| AutoSmokeUIPrefabScanner.cs | 工程态 UI Prefab 扫描 | ✅ | ☐ 待验收 | 1. 扫描 Assets/**/*.prefab 中 Button/Text/Image 等组件<br>2. 检测 Missing Script / testId / 图标资源<br>3. 输出 project_ui_inventory.json（205K节点/14K可点击） |
| AutoSmokeUITreeExporter.cs | 运行态 UI 树导出 | ✅ | ☐ 待验收 | 1. 16 个运行态字段完整采集<br>2. 图标采集（spriteName/visualNode/clickTargetNode）<br>3. 4 个菜单项（导出/含截图/启动Bridge/停止Bridge） |
| AutoSmokeLayoutDiagnostics.cs | 布局诊断 | ✅ | ☐ 待验收 | — |

---

## 四、从用例到报告：完整执行链路

### 3.1 架构图

```
Excel/DSL 用例
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ case_step_   │────▶│ case_step_   │────▶│ batch_runner │
│ parser.py    │     │ executor.py  │     │ .py          │
│ 步骤文本解析  │     │ 步骤顺序执行  │     │ 批量运行     │
└──────────────┘     └──────────────┘     └──────┬───────┘
       │                  │                      │
       │                  ▼                      ▼
       │          ┌──────────────┐        ┌──────────────┐
       │          │ preCheck     │        │ report_      │
       │          │ ClickValidator│       │ center.py    │
       │          │ 点击前校验    │        │ HTML 报告     │
       │          └──────┬───────┘        └──────────────┘
       │                 │
       │          ┌──────▼───────┐
       │          │ ClickExecutor│
       │          │ · real_mouse │
       │          │ · poco_click │
       │          │ · unity_     │
       │          │   inject     │
       │          └──────┬───────┘
       │                 │
       │          ┌──────▼───────┐
       │          │ postCheck    │
       │          │ · 截图差异    │
       │          │ · 页面变化    │
       │          │ · 元素出现/消失│
       │          └──────────────┘
```

### 3.2 支持的动作类型

| 动作 | 示例 | 说明 |
|------|------|------|
| `点击` | `点击 testId("Bag.UseButton")` | 主方案 |
| `等待` | `等待 2 秒` | 固定等待 |
| `断言存在` | `断言存在 normalized(0.5,0.5)` | 最多 5 次重试 |
| `断言不存在` | `断言不存在 text("加载中")` | 最多 5 次重试 |
| `截图` | `截图` | 保存 GameContent 截图 |

### 3.3 支持的目标定位（优先级）

| 优先级 | 类型 | 示例 | 依赖 |
|:------:|------|------|------|
| P0 | `testId` | `testId("Bag.UseButton")` | Unity 元数据，主方案 |
| P0 | `semantic` | `semantic("背包.使用按钮")` | element_mapping 映射，主方案 |
| P1 | `pocoPath` | `pocoPath("Root/Panel/Btn")` | Poco SDK，现阶段可用主方案 |
| P1 | `pocoName` | `pocoName("ButtonUse")` | Poco SDK，需结合页面/父节点约束 |
| P2 | `sceneObject` | `sceneObject("Building.Barracks")` | Unity 场景对象元数据 |
| P3 | `normalized` | `normalized(0.5,0.5)` | 归一化坐标，兜底 |
| P4 | `design` | `design(585,2400)` | 设计坐标，兜底 |
| P4 | `content` | `content(159,344)` | 截图坐标，兜底 |
| P5 | `text` | `text("使用")` | OCR（需 Tesseract），最后兜底 |
| P5 | `template` | `template("btn_use.png")` | 模板图片，最后兜底 |

### 3.4 执行步骤

```
步骤1: 解析步骤文本 → 结构化动作
步骤2: 定位目标 → preCheck
步骤3: 点击前状态快照 + 截图（before，仅用于报告/识别）
步骤4: 执行点击（优先 Unity EventSystem 注入）
步骤5: 点击后状态快照 + 截图（after，仅用于报告/识别）
步骤6: postCheck（截图差异/页面变化）
步骤7: guard 检查下一步前置条件
步骤8: 记录 step_result
```

### 3.5 报告结构

```json
{
  "caseId": "TC001",
  "result": "PASS/FAIL",
  "steps": [{
    "stepIndex": 1,
    "action": "click",
    "target": { "type": "testId", "value": "Bag.UseButton" },
    "preCheck": { "passed": true, "checks": [...] },
    "click": {
      "method": "unity_event_system",
      "targetGameObject": "DeepUI/DialogUI/BagPanel/ButtonUse",
      "eventReceiver": "DeepUI/DialogUI/BagPanel/ButtonUse"
    },
    "postCheck": { "passed": true, "diff_ratio": 0.034 },
    "screenshots": { "before": "...", "after": "..." },
    "result": "PASS"
  }]
}
```

---

## 五、模块详细说明

### 4.1 定位层

| 模块 | 功能 | 调用方式 |
|------|------|----------|
| `locate_game_area_smart.py` | GameView 窗口定位 | 自动或 IDE 刷新 |
| `game_content_locator.py` | 三层区域检测（aspect-fit） | `find_game_content_rect()` |
| `game_view_state_reader.py` | Unity Bridge 直连状态 | `GameViewStateReader()` |

**坐标来源优先级：** Bridge 直连 > aspect-fit 算法 > 图像黑边检测 > config 缓存

### 4.2 坐标层

| 函数 | 说明 |
|------|------|
| `design_to_screen(x, y)` | 设计坐标 → 屏幕坐标 |
| `screen_to_design(x, y)` | 屏幕坐标 → 设计坐标 |
| `normalized_to_screen(nx, ny)` | 归一化 → 屏幕坐标 |
| `content_to_screen(x, y)` | GameContent 坐标 → 屏幕坐标 |
| `design_to_content(x, y)` | 设计坐标 → GameContent 坐标 |

### 4.3 截图层

**推荐优先级：**

| 优先级 | 来源 | 说明 |
|:---:|---|---|
| P0 | Unity 直出完整 GameContent PNG | 主方案；Unity 侧直接生成完整游戏画面，用于报告/识别 |
| P1 | Unity Bridge `gameContentRectOnScreen` | 直接裁屏幕上的游戏内容区域 |
| P2 | Python GameView + GameContent 裁剪 | 当前兜底方案 |
| P3 | 手动配置区域裁剪 | 最后兜底 |

当前兜底链路：

```
全屏截图 (ImageGrab.grab(all_screens=True))
  → 裁剪 GameView 面板 (game_view_coords)
    → 裁剪 GameContent (game_content_rect)
      → 保存 game_content.png
      → 保存 metadata.json
```

最终主链路：

```
Unity Editor / Play Mode
  → AutoSmokeGameContentCapture.cs 直接输出完整 GameContent PNG
    → IDE 读取 PNG
      → 保存到 run 目录
      → OCR / 模板 / 报告复用该 PNG
```

截图不再作为点击精准性的主依据。截图只用于报告、识别、失败留痕和人工核对。

### 4.4 点击层

| 模式 | 原理 | 优势 |
|------|------|------|
| `unity_inject` | EventSystem 注入 | 主方案；不依赖鼠标、窗口、DPI、GameView 坐标 |
| `poco_click` | Poco SDK `.click()` | 过渡方案；不需要屏幕坐标，但依赖 Poco 节点可点击性 |
| `real_mouse` | win32 鼠标真实点击 | 兜底；用于验证真实鼠标路径或 Unity 注入不可用场景 |

点击精准性主链路：

```
testId / semanticId / pocoPath
  → Unity 内部查找目标 GameObject
    → 校验 active / visible / interactable / not occluded
      → EventSystem pointerDown / pointerUp / pointerClick
        → 校验 eventReceiver == targetGameObject
          → postCheck 验证结果
```

真实鼠标点击只在以下情况下使用：

- Unity 注入不可用。
- 需要验证真实用户鼠标路径。
- 目标是特殊场景对象，暂未接入 Unity 对象点击。
- 用例明确指定 `clickMode=real_mouse`。

### 4.5 阻塞处理

检测 → 分类 → 安全处理 → 确认 → 继续

| 阻塞类型 | 处理策略 |
|----------|----------|
| 普通弹窗 | 关闭 X → 取消 → 空白区 → 返回 |
| 奖励弹窗 | 确认（白名单）|
| Loading | 等待超时 |
| 重连弹窗 | 等待 → 重试 → 超时阻断 |
| 新手引导 | 跳过 → 点引导目标 |
| 危险确认 | **不点确定 → 阻断用例** |

---

## 五、IDE 面板功能

### 5.1 当前功能

| 卡片 | 功能 |
|:----|------|
| 📐 定位状态 | GV/GC 坐标、分辨率、Scale |
| 📸 截图 | 截取 GameContent 预览 |
| 🚧 阻塞 | 检测 + 处理阻塞 |
| 📊 元数据 | 状态/元素列表/搜索 |
| 🔍 before/after | 三栏对比 + 差异高亮 |
| 📦 部署 | 检查/部署 Unity 脚本 |
| 📋 步骤执行 | 手动输入 + 预设 + 日志 |

### 5.2 API 接口（80条）

| 路由 | 说明 |
|------|------|
| `GET /api/status` | 定位状态 |
| `POST /api/relocate` | 全自动重新定位 |
| `GET /api/capture` | 截取 GameContent |
| `POST /api/compare` | 截图差异对比 |
| `POST /api/execute` | 执行步骤 |
| `GET /api/metadata` | 元数据摘要 |
| `GET /api/metadata/elements` | 元素列表筛选 |
| `GET /api/metadata/search?q=` | 搜索元素 |
| `GET /api/mapping/list` | 语义映射列表 |
| `POST /api/mapping/save` | 保存映射 |
| `GET /api/mapping/reverse_lookup` | 截图反查元素 |
| `GET /api/blocker_detect` | 检测阻塞 |
| `POST /api/blocker_resolve` | 处理阻塞 |
| `GET /api/deploy_check` | 检查部署状态 |
| `POST /api/deploy_run` | 执行部署 |
| `POST /api/ui/enhance` | **阶段1** 生成 enhanced_ui_tree.json |
| `GET /api/ui/enhance/status` | **阶段1** 查询增强UI树状态 |
| `GET /api/mapping/drafts?priority=&elementType=&role=&dataSource=` | **阶段1** 草稿列表（支持筛选参数） |
| `GET /api/unity/bridge/status` | **阶段2** 检测 Unity 运行态连接 |
| `POST /api/runtime_ui/refresh` | **阶段2** 请求实时 UI 树导出（含交互元素分类统计） |
| `POST /api/mapping/runtime_match` | **阶段3** 候选元素与实时UI树+场景对象匹配 |
| `GET /api/mapping/runtime_match/result` | **阶段3** 查询匹配结果 |
| `POST /api/mapping/runtime_match/resolve_conflict` | **阶段3** 解决匹配冲突 |
| `POST /api/mapping/highlight` | **阶段4** 截图高亮匹配元素 |
| `POST /api/mapping/drafts/<path>/test_click` | **阶段5** 测试点击（优先runtimePath/instanceId） |
| `POST /api/mapping/drafts/<path>/visual_confirm` | **阶段5** 视觉确认 |

---

## 六、输出产物

### 6.1 截图输出

```
screenshots/{run_id}/
├── game_content_{timestamp}.png   # 纯游戏内容截图
├── game_view_{timestamp}.png      # GameView 面板截图
├── before_{timestamp}.png         # 点击前截图
├── after_{timestamp}.png          # 点击后截图
├── diff_{timestamp}.png           # 差异高亮图
└── metadata_{timestamp}.json      # 元数据（分辨率/坐标/scale）
```

### 6.2 元数据输出

```
%USERPROFILE%\.autosmoke\
├── game_view_pos.json             # GameView 坐标（C# 脚本输出）
├── game_view_state.json           # Bridge 直连状态
├── click_request.json             # 点击请求
├── click_result.json              # 点击结果
├── metadata/
│   ├── current_ui.json            # UI 元数据
│   ├── current_state.json         # 状态元数据
│   ├── current_scene.json         # 场景对象元数据
│   ├── element_mapping.json       # 语义映射
│   ├── element_mapping_draft.json # 映射草稿（待审核）
│   ├── enhanced_ui_tree.json      # 增强 UI 树（工程态候选清单，10759节点）
│   ├── project_ui_inventory.json  # 工程态 Prefab 扫描原始数据（205293节点）
│   ├── scene_interaction_tree.json# 场景交互对象库（建筑/地图/资源点/建筑菜单）
│   ├── runtime_ui_tree_current.json# 当前运行态 UI 树快照（含交互元素分类）
│   ├── current_runtime_state.json  # 当前运行态状态摘要（含分类统计）
│   └── accessibility_scan.json    # 可测性扫描报告
```

### 6.3 报告输出

```
screenshots/{case_id}/
├── case_result_{case_id}_{time}.json   # 用例结果
├── step_1_before.png                   # 步骤1 点击前
├── step_1_after.png                    # 步骤1 点击后
├── step_2_before.png
├── step_2_after.png
└── ...
```

批量报告：
```
batch_report_{timestamp}.json     # 批量结果 JSON
batch_report_{timestamp}.html     # 批量结果 HTML
```

---

## 七、故障排查

### 7.1 定位状态不刷新

```
1. 点击 Unity 窗口（触发脚本编译）
2. Unity 菜单 → AutoSmoke → 定位 → 定位 Game 视图
3. IDE 面板 → 🔄 刷新状态
```

### 7.2 截图全黑

```
根因：Bridge 输出的屏幕坐标未转换为截图坐标
修复：game_view_state_reader.py 已修复，刷新即可
```

### 7.3 点击位置不准

```
1. 确认定位状态正确（Scale mismatch < 1%）
2. 确认不在多显示器场景（或已配置偏移）
3. 优先使用 unity_inject 模式（不需要鼠标）
```

### 7.4 OCR 不可用

```
安装 Tesseract-OCR 引擎：
1. 下载安装 https://github.com/UB-Mannheim/tesseract
2. 安装中文语言包 chi_sim.traineddata
3. 重启 IDE 面板
```

---

## 八、待实施方案

> 以下为 2026-06-16 会话中全部完成的内容。

### ✅ 本次完成（2026-06-15 / 2026-06-16）

| 项目 | 状态 | 说明 |
|------|:----:|------|
| 安装 pytesseract + Tesseract-OCR | ✅ | v5.4.0 + 中文语言包 chi_sim (44MB) |
| P0 阻塞问题修复 | ✅ | OpenCV/Tesseract/入口脚本/Unity部署 |
| P1 异常检测模块 | ✅ | 日志采集/崩溃检测/卡死检测 |
| EventSystem 注入全链路 | ✅ | 坐标映射/原子写入/竞态修复 |
| 工程态 Prefab 扫描 | ✅ | AutoSmokeUIPrefabScanner.cs 输出 205K 节点 |
| 运行态 UI 树导出 | ✅ | AutoSmokeUITreeExporter.cs 16字段+图标采集 |
| 合并增强 | ✅ | merged_ui_tree.py 工程态+运行态合并 |
| 页面关系图 | ✅ | page_graph.py JSON+HTML可视化 |
| 映射草稿中文生成 | ✅ | element_mapping.py 自动推断中文描述 |
| 图标采集与映射 | ✅ | spriteName/visualNode/clickTargetNode |
| 自动探索引擎 | ✅ | auto_explorer.py + 图标Tips探索 |
| IDE 审核面板 | ✅ | 三栏布局/80条API/5种审核状态 |
| UI树方案25项 | ✅ | 全部完成（工程态+运行态+合并+映射+审核+探索） |
| **enhanced_ui_tree 完整方案** | **✅** | **5 个子任务全部完成** |
| ┣ ui_tree_enhancer.py | ✅ | 工程态清洗增强模块（205293→10759候选） |
| ┣ /api/ui/enhance + /api/ui/enhance/status | ✅ | 增强生成+状态查询 API |
| ┣ /api/mapping/import 优先 enhanced | ✅ | 自动增强+enhanced优先导入 |
| ┣ /api/mapping/drafts 筛选增强 | ✅ | 支持 priority/elementType/role/dataSource 筛选 |
| ┣ IDE 前端增强 | ✅ | 状态卡片+P0-P3筛选+详情区增强+结构审核模式 |
| **5 个阶段全部实现** | **✅** | **阶段1-5全部前后端完整实现** |
| ┣ 阶段1：工程态 enhanced 候选生成 | ✅ | ui_tree_enhancer.py + 2 API + 前端 |
| ┣ 阶段2：IDE 连接 Unity 实时 UI 树 | ✅ | 2个 C# Bridge + 2 API + 前端连接状态 |
| ┣ 阶段3：候选元素匹配实时界面 | ✅ | runtime_matcher.py + 3 API + 匹配状态列 |
| ┣ 阶段4：截图高亮+视觉确认 | ✅ | highlight + visual_confirm API |
| ┣ 阶段5：Unity 注入点击验证 | ✅ | test_click 优先 runtimePath + 点击结果 |
| **交互元素类型扩展补充方案** | **✅** | **全部完成** |
| ┣ C# 运行时扩展字段 | ✅ | elementType/interactionType/clickTargetNode 等13字段 |
| ┣ 图标/格子/遮罩/滚动检测 | ✅ | IsIconNode/IsCellNode/IsMaskNode/IsDragOrScrollNode |
| ┣ 场景交互对象导出 | ✅ | AutoSmokeSceneInteractionExporter.cs（12种分类） |
| ┣ IDE 统计/筛选/详情分类 | ✅ | 组件/图标/格子/场景/空白关闭/滚分类统计+筛选+详情 |
| ┣ 运行态匹配+场景对象 | ✅ | runtime_match 同时匹配UI节点+场景对象 |

### ⏳ 未完成（后续迭代）

| 项目 | 说明 | 预计工作量 |
|------|------|:----------:|
| 真实 Excel 用例第一条 | 编写并跑通完整闭环 | 1小时 |
| IDE 面板代码清理 | 解决当前 4335 行单一文件，代码混乱问题 | 2小时 |
| 模板图标收集 | 截取常用按钮放入 templates/ | 30分钟 |
| 产品化打包 | 打包为 Windows EXE | 4小时 |

| 项目 | 说明 |
|------|------|
| 自动探索引擎 | 发现页面、遍历弹窗、生成关系图 |
| 大地图交互 | 缩放/拖动/网格扫描 |
| IDE 产品化 | 打包为 EXE、跨电脑、图形化运行监控 |
| Unity 直出 PNG | RenderTexture 合成导出 |
| 状态与目标识别引擎 | 统一的状态/目标定位 |

---

## 九、关键验收标准

### 9.1 GameContent 截图

```
✅ 左边界：不包含黑边
✅ 右边界：不裁掉右侧 UI
✅ 顶部：不包含 Unity 工具栏
✅ 底部：不裁掉底部按钮栏
✅ 比例：宽高比接近 gameResolution
✅ 来源：metadata 标记 unity_bridge 或 aspect_fit
```

### 9.2 点击精准性

```
P0: testId → Unity EventSystem 注入 → 元素命中确认
P1: Poco 坐标 → Unity 注入 → 元素命中确认
P2: 截图坐标 → 鼠标点击 → 截图差异验证
```

### 9.3 阻塞处理

```
✅ 普通弹窗：自动关闭
✅ 危险弹窗：阻断 + 报告
✅ Loading：等待超时
✅ 重连：等待 + 重试
```

---

## 十、点击绝对精准主链路

### 10.1 原则

自动点击的精准性不由截图保证，而由 Unity 内部目标身份和事件注入保证。

主链路必须满足：

```
用例目标 = Unity 实际目标 GameObject = 点击事件接收对象
```

如果三者不一致，步骤不能判定为通过。

### 10.2 点击目标优先级

| 优先级 | 目标来源 | 示例 | 说明 |
|:---:|---|---|---|
| P0 | `testId` | `Bag.UseButton` | 最稳定，推荐长期主方案 |
| P0 | `semanticId` | `背包.使用按钮` | 由 element_mapping 映射到 testId/Poco |
| P1 | `pocoPath` | `DeepUI/DialogUI/BagPanel/ButtonUse` | 现阶段可用主方案 |
| P1 | `pocoName + pageId` | `ButtonUse + BagPanel` | 需要页面约束，避免重名 |
| P2 | `sceneObjectId` | `Building.Barracks` | 主城/大地图对象 |
| P3 | `normalized/design/content` | `normalized(0.5,0.5)` | 兜底，不作为精准主链路 |
| P4 | `text/template` | `text("确定")` | 视觉兜底 |

### 10.3 Unity EventSystem 注入点击流程

```
1. IDE 发送 click_request.json
2. Unity Bridge 读取请求
3. 根据 testId / semanticId / pocoPath 查找目标 GameObject
4. 校验目标存在、激活、可见、可交互
5. 检查是否被弹窗/遮罩/引导阻塞
6. 计算 safePoint
7. 构造 PointerEventData
8. 派发 pointerDown
9. 派发 pointerUp
10. 派发 pointerClick
11. 等待 1~2 帧
12. 导出 click_result.json
13. IDE 执行 postCheck
```

### 10.4 点击请求协议

```json
{
  "requestId": "click_20260615_180000",
  "action": "click",
  "target": {
    "type": "testId",
    "value": "Bag.UseButton"
  },
  "options": {
    "safePoint": "center",
    "timeoutMs": 3000,
    "retry": 1,
    "waitAfterMs": 300
  }
}
```

### 10.5 点击结果协议

```json
{
  "requestId": "click_20260615_180000",
  "success": true,
  "target": {
    "testId": "Bag.UseButton",
    "semanticId": "背包.使用按钮",
    "gameObjectPath": "DeepUI/DialogUI/BagPanel/ButtonUse",
    "activeInHierarchy": true,
    "visible": true,
    "interactable": true
  },
  "click": {
    "method": "unity_event_system",
    "safePoint": "center",
    "eventReceiver": "DeepUI/DialogUI/BagPanel/ButtonUse",
    "targetGameObject": "DeepUI/DialogUI/BagPanel/ButtonUse"
  },
  "preCheck": {
    "exists": true,
    "visible": true,
    "interactable": true,
    "occluded": false
  },
  "postCheck": {
    "type": "elementVisible",
    "target": "RewardPopup.ConfirmButton",
    "passed": true
  }
}
```

### 10.6 点击失败分类

| 错误码 | 含义 | 处理 |
|---|---|---|
| `TARGET_NOT_FOUND` | 找不到目标 | 失败，提示补充映射 |
| `TARGET_NOT_VISIBLE` | 元素不可见 | 等待/失败 |
| `TARGET_NOT_INTERACTABLE` | 元素不可交互 | 失败或等待状态变化 |
| `TARGET_OCCLUDED` | 被弹窗或遮罩挡住 | 进入阻塞处理 |
| `EVENT_RECEIVER_MISMATCH` | 事件接收对象不是目标 | 判定点击风险，默认失败 |
| `POSTCHECK_FAILED` | 点击后未达到期望 | 失败并截图留痕 |
| `UNITY_EXCEPTION` | Unity 异常 | 失败并记录日志 |

---

## 十一、Unity 直出 PNG 截图主链路

### 11.1 目的

截图用于报告、识别和调试，不作为点击精准性的主依据。

推荐截图主链路：

```
Unity 直接输出完整 GameContent PNG
  → IDE 读取 PNG
    → OCR / 模板 / 报告复用
```

### 11.2 Unity 截图请求协议

```json
{
  "requestId": "cap_20260615_181000",
  "resolution": {
    "width": 1170,
    "height": 2532
  },
  "outputDir": "E:/zdcs/AutoSmoke/runtime/unity_capture",
  "includeMetadata": true
}
```

### 11.3 Unity 截图输出

```
runtime/unity_capture/
├── cap_20260615_181000.png
├── cap_20260615_181000.json
└── cap_20260615_181000.done
```

metadata 示例：

```json
{
  "source": "unity_capture_png",
  "timestamp": "2026-06-15T18:10:00",
  "gameResolution": {
    "width": 1170,
    "height": 2532
  },
  "image": {
    "path": "E:/zdcs/AutoSmoke/runtime/unity_capture/cap_20260615_181000.png",
    "width": 1170,
    "height": 2532
  },
  "capture": {
    "method": "game_view",
    "containsOverlayUI": true,
    "frame": 123456
  }
}
```

### 11.4 截图兜底顺序

| 优先级 | 方案 | 说明 |
|:---:|---|---|
| P0 | Unity 直出 PNG | 主方案 |
| P1 | Unity Bridge `gameContentRectOnScreen` | 屏幕直裁 |
| P2 | Python GameView/GameContent 裁剪 | 兜底 |
| P3 | 手动区域裁剪 | 最后兜底 |

### 11.5 截图验收

截图必须包含：

- 顶部头像和资源栏完整
- 右侧活动按钮完整
- 左侧按钮完整
- 任务栏完整
- 聊天按钮完整
- 底部功能栏完整
- Debug 标签完整

截图不得包含：

- Unity GameView 工具栏
- `Display / Scale / Play Focused`
- Windows 桌面背景
- PIL 补黑

---

## 十二、Excel 用例模板字段规范

### 12.1 推荐字段

| 字段 | 是否必填 | 示例 | 说明 |
|---|:---:|---|---|
| 用例ID | 是 | `TC_BAG_001` | 唯一 ID |
| 模块 | 是 | `背包` | 功能模块 |
| 标题 | 是 | `使用道具` | 用例名称 |
| 前置条件 | 否 | `已打开背包` | 可为空 |
| 步骤序号 | 是 | `1` | 数字 |
| 动作 | 是 | `点击` | 点击/等待/断言/截图 |
| 目标类型 | 是 | `testId` | testId/semantic/pocoPath/text |
| 目标值 | 是 | `Bag.UseButton` | 元素标识 |
| 输入值 | 否 | `100` | 输入/滑动等动作使用 |
| 期望类型 | 否 | `elementVisible` | 点击后期望 |
| 期望值 | 否 | `RewardPopup.ConfirmButton` | 期望目标 |
| 超时ms | 否 | `3000` | 默认 3000 |
| 失败策略 | 否 | `stop` | stop/retry/continue |

### 12.2 示例

| 用例ID | 模块 | 标题 | 步骤序号 | 动作 | 目标类型 | 目标值 | 期望类型 | 期望值 |
|---|---|---|---:|---|---|---|---|---|
| TC_BAG_001 | 背包 | 使用道具 | 1 | 点击 | semantic | 背包.使用按钮 | elementVisible | 奖励弹窗.确认按钮 |
| TC_BAG_001 | 背包 | 使用道具 | 2 | 点击 | semantic | 奖励弹窗.确认按钮 | elementGone | 奖励弹窗 |
| TC_BAG_001 | 背包 | 使用道具 | 3 | 截图 | - | - | - | - |

---

## 十三、元素映射生成与人工审核

### 13.1 自动生成草稿

输入：

- Poco UI 树
- Unity 元数据
- 当前截图
- 文本组件
- 节点路径

输出：

```json
{
  "candidateId": "auto_001",
  "suggestedSemanticId": "背包.使用按钮",
  "pocoPath": "DeepUI/DialogUI/BagPanel/ButtonUse",
  "screenRect": [465, 730, 570, 798],
  "confidence": 0.82,
  "reviewStatus": "pending"
}
```

### 13.2 人工审核状态

| 状态 | 含义 |
|---|---|
| `pending` | 待审核 |
| `confirmed` | 已确认 |
| `modified` | 人工修改 |
| `ignored` | 暂不处理 |
| `rejected` | 错误映射 |

### 13.3 IDE 能力

- 截图上高亮元素 rect。
- 点击截图区域反查 Poco/Unity 元素。
- 列表中编辑 semanticId/testId/role/pageId。
- 保存到 `element_mapping.json`。

---

## 十四、日志、崩溃、卡死检测

### 14.1 日志来源

| 来源 | 用途 |
|---|---|
| Unity Editor Console 日志 | Editor 自动化 |
| Player.log | Standalone |
| Android logcat | Android 真机/模拟器 |
| AutoSmoke 执行日志 | 框架自身问题 |

### 14.2 关键错误

| 类型 | 关键字 |
|---|---|
| Missing Reference | `MissingReferenceException` |
| 空引用 | `NullReferenceException` |
| Unity 异常 | `Exception` / `Error` |
| 崩溃 | 进程退出 / crash log |
| 卡死 | 心跳停止 / 画面长时间无变化 |
| 加载超时 | Loading 超过阈值 |

### 14.3 卡死检测

卡死判定建议组合：

```
1. Unity 心跳未更新
2. 截图连续 N 秒变化率 < 阈值
3. 当前不处于允许静止的页面
4. 无 Loading / 重连 / 弹窗可解释状态
```

---

## 十五、账号与测试环境初始化

完整自动化需要稳定起点。

建议增加：

- 账号登录状态检查。
- 服务器选择。
- 角色状态检查。
- GM 初始化资源。
- 清理/重置测试数据。
- 跳过或固定新手引导阶段。
- 网络状态检查。
- 进入指定主场景。

初始化结果写入：

```json
{
  "account": "test_001",
  "server": "dev_01",
  "scene": "MainCity",
  "guideState": "completed",
  "resourceReady": true
}
```

---

## 十六、失败分类与报告标准

### 16.1 失败分类

| 分类 | 错误码 | 说明 |
|---|---|---|
| 定位失败 | `TARGET_NOT_FOUND` | 找不到目标 |
| 不可见 | `TARGET_NOT_VISIBLE` | 目标存在但不可见 |
| 被遮挡 | `TARGET_OCCLUDED` | 被弹窗/遮罩遮挡 |
| 不可交互 | `TARGET_NOT_INTERACTABLE` | 按钮灰态或禁用 |
| 点击不一致 | `EVENT_RECEIVER_MISMATCH` | 事件接收对象不等于目标 |
| 后置失败 | `POSTCHECK_FAILED` | 点击后期望未达成 |
| 阻塞 | `BLOCKER_DETECTED` | 遇到未处理阻塞 |
| 崩溃 | `CRASH_DETECTED` | 游戏或 Unity 崩溃 |
| 卡死 | `HANG_DETECTED` | 长时间无响应 |
| 截图异常 | `SCREENSHOT_INCOMPLETE` | 截图不完整 |

### 16.2 报告必须包含

- 用例 ID。
- 步骤 ID。
- 目标类型和值。
- 定位来源。
- 点击方式。
- 目标 GameObject。
- 事件接收 GameObject。
- 点击前校验。
- 点击后校验。
- before/after 截图。
- Unity 日志片段。
- 失败原因和建议处理。

---

## 十七、替代方案与降级策略

| 能力 | 主方案 | 替代 | 最后兜底 |
|---|---|---|---|
| 截图 | Unity 直出 PNG | Bridge 屏幕直裁 | Python 裁剪 |
| 点击 | Unity EventSystem 注入 | Poco click | 鼠标点击 |
| UI 定位 | testId/semanticId | Poco path | OCR/模板 |
| 弹窗识别 | pageId/panelStack | testId | OCR/模板 |
| 文本识别 | Unity Text/TMP 导出 | Poco text | OCR |
| 场景对象 | sceneObjectId | GameObject path/tag | 视觉模板 |

降级必须写入报告：

```json
{
  "fallback": {
    "from": "unity_event_system",
    "to": "real_mouse",
    "reason": "UNITY_BRIDGE_TIMEOUT"
  }
}
```

---

## 十八、跨电脑 / 跨项目迁移验收

### 18.1 必须动态配置

- Unity 项目路径。
- Poco SDK 路径。
- AutoSmoke 根目录。
- Unity 输出目录。
- Python 环境路径。
- 游戏分辨率。
- 多显示器/DPI。

### 18.2 迁移验收清单

| 项 | 通过标准 |
|---|---|
| Python 依赖 | 一键检查通过 |
| Unity 脚本 | 自动部署成功 |
| Unity 菜单 | AutoSmoke 菜单出现 |
| Bridge | 能生成 state/click/capture 文件 |
| 元数据 | 能导出 current_ui.json |
| 截图 | Unity 直出 PNG 完整 |
| 点击 | testId 点击命中 |
| 用例 | 示例 Excel 用例通过 |
| 报告 | HTML/JSON 报告生成 |

---

## 十九、推荐实施顺序（已完成）

1. ✅ Unity EventSystem 注入点击闭环 — **已完成**（坐标映射/原子写入/竞态修复）
2. ✅ testId / semanticId / Poco 映射闭环 — **已完成**（5级优先级/元素映射/审核面板）
3. ✅ Unity 直出 PNG — **已完成**（GameContentCapture + capture_reader）
4. ✅ Excel 用例导入和批量报告 — **已完成**（parse_from_excel_file + batch_runner）
5. ✅ 异常检测（日志/崩溃/卡死） — **已完成**（3个检测模块 + IDE集成）
6. ✅ 自动探索、页面关系图 — **已完成**（auto_explorer + page_graph）
7. ✅ UI树方案25项 — **全部完成**（工程态+运行态+合并+映射+审核+探索）
8. ✅ 映射草稿生成 — **已完成**（14,140条中文草稿）

当前最关键的优先级（下一迭代）：

```
P1 真实用例：编写第一条真实 Excel 用例并跑通完整闭环
P1 IDE重写：统一布局，解决代码混乱问题
P2 产品化：打包为 Windows EXE
```
