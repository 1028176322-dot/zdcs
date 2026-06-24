# AutoSmoke - 状态与目标识别引擎实施方案

## 1. 背景

在按用例自动执行时，工具必须先回答两个问题：

```text
1. 当前在哪个界面、弹窗、场景或状态？
2. 当前步骤要点击的按钮、图标、建筑或功能入口在哪里？
```

如果只按固定坐标执行，会遇到：

```text
分辨率变化导致坐标偏移
GameView 拉伸导致点击错位
弹窗/Loading/引导遮挡目标
点击后进入了意外页面
主城建筑、功能菜单、大地图对象位置变化
按钮样式或文字变化导致识别失败
```

因此，需要建设一个统一的：

```text
State & Target Recognition Engine
状态与目标识别引擎
```

该引擎负责：

```text
识别当前状态
解析用例目标
定位目标区域
输出安全点击点
为点击执行器提供可信输入
```

## 2. 目标

本方案目标是实现：

```text
1. 自动判断当前是哪个页面、弹窗、场景或 Loading 状态。
2. 根据用例步骤语义定位目标按钮、图标、建筑、功能按钮。
3. 输出 targetRect、safePoint、confidence、source。
4. 在当前状态不符合用例前置时，触发阻塞处理或失败。
5. 所有识别过程封装进 IDE，支持可视化调试。
```

最终执行链路：

```text
recognize_current_state()
-> resolve_target(step.target, current_state)
-> validate_target()
-> click()
-> verify_after_click()
```

## 3. 设计边界

必须遵守当前项目约束：

```text
不修改游戏业务运行过程代码
允许使用 Unity Editor 辅助脚本读取只读信息
允许使用截图、OCR、模板匹配、Poco dump、UI 树、日志
允许后续低侵入导出 sceneId/pageId/testId
所有能力最终封装到 IDE
```

## 4. 总体架构

建议新增以下核心模块：

```text
E:/zdcs/AutoSmoke/state_registry.py
E:/zdcs/AutoSmoke/feature_matcher.py
E:/zdcs/AutoSmoke/page_state_recognizer.py
E:/zdcs/AutoSmoke/scene_state_recognizer.py
E:/zdcs/AutoSmoke/current_state_service.py
E:/zdcs/AutoSmoke/target_locator.py
E:/zdcs/AutoSmoke/target_validation.py
```

模块关系：

```text
截图 / OCR / 模板 / UI树 / Poco / Unity导出
        |
        v
feature_matcher
        |
        v
page_state_recognizer + scene_state_recognizer
        |
        v
current_state_service
        |
        v
target_locator
        |
        v
target_validation
        |
        v
click_executor
```

## 5. 状态类型定义

当前状态分为：

```text
page
popup
scene
loading
guide
context_menu
unknown
```

示例：

```text
bag_page
main_city
world_map
reward_popup
modal_popup
guide_overlay
scene_transition_loading
building_context_menu
```

## 6. 状态识别数据结构

```json
{
  "stateId": "bag_page",
  "stateType": "page",
  "confidence": 0.94,
  "sources": ["ocr", "template", "layout"],
  "matchedFeatures": [
    "text:背包",
    "text:特殊",
    "text:资源",
    "template:bag_item_card"
  ],
  "gameResolution": [1170, 2532],
  "gameContentRect": [86, 62, 318, 688],
  "timestamp": "2026-06-12T18:30:00"
}
```

未知状态：

```json
{
  "stateId": "unknown",
  "stateType": "unknown",
  "confidence": 0.22,
  "sources": ["screenshot"],
  "matchedFeatures": [],
  "message": "未匹配到足够页面/场景特征"
}
```

## 7. 状态特征库

### 7.1 state_registry.py

用于维护页面、弹窗、场景的特征定义。

示例：

```json
{
  "stateId": "bag_page",
  "stateType": "page",
  "features": {
    "texts": ["背包", "特殊", "资源", "加速", "英雄", "装备"],
    "templates": ["bag_tab_special.png", "bag_item_card.png"],
    "layout": ["top_tabs", "item_grid", "bottom_use_button"],
    "uiNodes": ["bag.page.root"]
  },
  "minConfidence": 0.75
}
```

主城：

```json
{
  "stateId": "main_city",
  "stateType": "scene",
  "features": {
    "texts": ["联盟迁城"],
    "templates": ["building_marker.png", "bottom_nav_city.png"],
    "layout": ["isometric_city", "right_activity_bar", "bottom_nav"],
    "objects": ["building", "activity_icon"]
  },
  "minConfidence": 0.7
}
```

建筑菜单：

```json
{
  "stateId": "building_context_menu",
  "stateType": "context_menu",
  "features": {
    "texts": ["Lv."],
    "templates": ["building_action_train.png", "building_action_upgrade.png"],
    "layout": ["building_name", "radial_action_buttons"]
  },
  "minConfidence": 0.75
}
```

## 8. 特征匹配

### 8.1 feature_matcher.py

负责统一调度：

```text
OCR 文本匹配
模板匹配
UI 树节点匹配
Poco dump 匹配
截图布局特征匹配
Unity Editor 辅助导出匹配
```

### 8.2 匹配结果结构

```json
{
  "featureType": "text",
  "value": "背包",
  "matched": true,
  "confidence": 0.91,
  "rect": [10, 8, 60, 34],
  "source": "ocr"
}
```

模板：

```json
{
  "featureType": "template",
  "value": "use_button.png",
  "matched": true,
  "confidence": 0.93,
  "rect": [110, 640, 210, 690],
  "source": "template"
}
```

## 9. 页面状态识别

### 9.1 page_state_recognizer.py

适用于：

```text
背包
邮件
任务
商城
联盟
排行榜
建筑升级页
道具详情页
```

识别流程：

```text
1. 截取 game_content_screenshot。
2. 执行 OCR。
3. 执行模板匹配。
4. 如有 UI 树/Poco，读取节点。
5. 与 state_registry 中 page 类型特征打分。
6. 返回最高分 page_state。
```

打分建议：

```text
关键标题文本命中：+40
两个以上标签文本命中：+20
模板命中：+20
布局结构命中：+10
UI 节点命中：+30
```

## 10. 场景状态识别

### 10.1 scene_state_recognizer.py

适用于：

```text
主城
大地图
战斗
Loading
引导
建筑上下文菜单
```

识别流程：

```text
1. 检查是否为 Loading/重连/引导等高优先级状态。
2. 检查是否存在弹窗或上下文菜单。
3. 检查主城/大地图场景特征。
4. 输出 scene_state。
```

优先级：

```text
dangerous_popup
> loading
> guide_overlay
> modal_popup / reward_popup
> building_context_menu
> page
> main_city / world_map
> unknown
```

## 11. 当前状态服务

### 11.1 current_state_service.py

职责：

```text
统一调用 page_state_recognizer 和 scene_state_recognizer
缓存当前状态
判断状态是否变化
输出 current_state
为用例执行器提供状态查询接口
```

接口建议：

```python
get_current_state(force_refresh=False)
wait_until_state(state_id, timeout_ms)
is_state(state_id)
is_blocked_state()
```

## 12. 目标定位

### 12.1 target_locator.py

根据步骤目标和当前状态定位点击区域。

输入：

```json
{
  "step": "点击 text(\"使用\")",
  "currentState": {
    "stateId": "bag_page",
    "stateType": "page"
  }
}
```

输出：

```json
{
  "targetType": "button",
  "targetName": "使用",
  "coordinateType": "game_content",
  "targetRect": [110, 640, 210, 690],
  "safePoint": [160, 665],
  "confidence": 0.93,
  "source": "ocr"
}
```

## 13. 目标类型定位策略

### 13.1 text 目标

```text
点击 text("使用")
```

流程：

```text
OCR 识别文本
-> 找到文本 rect
-> 根据文字附近按钮背景扩展为 buttonRect
-> safePoint = buttonRect.center
```

### 13.2 template 目标

```text
点击 template("use_button")
```

流程：

```text
模板匹配
-> 取最高分 rect
-> score >= 阈值
-> safePoint = rect.center
```

### 13.3 normalized 目标

```text
点击 normalized(0.5,0.95)
```

流程：

```text
normalized -> game_content 坐标
-> safePoint
```

### 13.4 design 目标

```text
点击 design(585,2400)
```

流程：

```text
检查 baseResolution
-> 必要时转换为 normalized
-> 当前 gameResolution 下重映射
```

### 13.5 building 目标

```text
点击 building("兵营")
```

流程：

```text
确认 currentState = main_city
-> SceneStateExporter / 模板 / 录制区域定位建筑
-> 输出 buildingRect
-> 使用 interactionAnchor 或 rect 内安全点
```

### 13.6 buildingAction 目标

```text
点击 buildingAction("升级")
```

流程：

```text
确认 currentState = building_context_menu
-> 识别 actionButtonRects
-> 匹配目标 action
-> 点击 actionButtonRect.center
```

## 14. 点击区域与安全点击点

每个目标必须输出：

```text
targetRect
safePoint
confidence
source
```

点击原则：

```text
优先点击 targetRect 中心
小按钮点击中心
大区域点击 interactionAnchor
弹窗关闭类点击 close/cancel/safeBlankPoint
建筑类点击建筑交互锚点
```

安全点校验：

```text
safePoint 在 gameContentRect 内
safePoint 在 targetRect 内或目标允许的安全区域内
safePoint 不在 forbiddenRects 内
safePoint 不在遮罩/阻塞区域内
当前状态符合步骤前置
```

## 15. 当前状态不匹配处理

每个步骤可以声明前置状态：

```json
{
  "step": "点击 text(\"使用\")",
  "requiredState": "bag_page"
}
```

执行时：

```text
1. 识别 currentState。
2. 如果 currentState == requiredState，继续定位目标。
3. 如果 currentState 是 blocker，调用 PostActionGuard。
4. 如果 currentState 是其它页面，标记 PAGE_MISMATCH。
5. 如果 unknown，标记 STATE_UNKNOWN。
```

结果：

```text
READY
BLOCKED
PAGE_MISMATCH
STATE_UNKNOWN
TARGET_NOT_FOUND
```

## 16. 与阻塞处理集成

状态识别结果如果是以下类型：

```text
modal_popup
reward_popup
guide_overlay
reconnect_loading
scene_transition_loading
dangerous_confirm
```

则不直接执行当前步骤，而是交给：

```text
PostActionGuard
```

处理完成后重新识别状态。

## 17. 与用例执行集成

用例执行器每步执行前：

```text
current_state = current_state_service.get_current_state()
target = target_locator.locate(step.target, current_state)
validate(target)
click(target.safePoint)
verify_after_click()
```

如果目标找不到：

```text
保存当前截图
保存 OCR/模板/UI树结果
标记 TARGET_NOT_FOUND
进入报告
```

## 18. IDE 封装

IDE 中建议新增：

```text
状态识别面板
目标定位面板
特征库管理面板
当前截图特征调试面板
```

### 18.1 状态识别面板

展示：

```text
当前 stateId
stateType
confidence
matchedFeatures
识别来源
状态变化历史
```

### 18.2 目标定位面板

展示：

```text
当前步骤
目标类型
targetRect
safePoint
confidence
source
点击前校验结果
```

### 18.3 特征库管理

支持：

```text
新增页面特征
新增模板图片
配置关键文字
配置页面最小置信度
查看误识别记录
```

## 19. 配置建议

```json
{
  "state_recognition": {
    "enabled": true,
    "min_confidence": 0.7,
    "unknown_threshold": 0.4,
    "prefer_sources": [
      "unity_export",
      "poco",
      "ocr",
      "template",
      "layout"
    ],
    "state_registry_path": "config/state_registry.json",
    "template_dir": "templates/states"
  },
  "target_location": {
    "min_confidence": 0.75,
    "allow_normalized_fallback": true,
    "allow_design_fallback": true,
    "block_screen_coordinate": true
  }
}
```

## 20. 报告结构

每步报告增加：

```json
{
  "state": {
    "stateId": "bag_page",
    "confidence": 0.94,
    "matchedFeatures": ["text:背包", "text:特殊"]
  },
  "target": {
    "targetType": "button",
    "targetName": "使用",
    "targetRect": [110, 640, 210, 690],
    "safePoint": [160, 665],
    "confidence": 0.93,
    "source": "ocr"
  },
  "validation": {
    "inGameContent": true,
    "notBlocked": true,
    "stateMatched": true
  }
}
```

## 21. 验收标准

### 21.1 状态识别验收

```text
能识别背包页
能识别主城场景
能识别建筑上下文菜单
能识别奖励弹窗
能识别引导
能识别场景跳转 Loading
```

### 21.2 目标定位验收

```text
能定位 text("使用")
能定位 template("use_button")
能定位 building("兵营")
能定位 buildingAction("升级")
定位结果包含 targetRect 和 safePoint
```

### 21.3 状态不匹配验收

```text
当前不是 requiredState 时不盲目点击
遇到弹窗/Loading/引导时交给 PostActionGuard
未知状态时输出 STATE_UNKNOWN
```

### 21.4 IDE 验收

```text
IDE 能显示当前状态
IDE 能显示匹配到的特征
IDE 能在截图上标出 targetRect 和 safePoint
IDE 能显示目标定位失败原因
```

## 22. 实施优先级

```text
1. state_registry.py
2. feature_matcher.py
3. page_state_recognizer.py
4. scene_state_recognizer.py
5. current_state_service.py
6. target_locator.py
7. target_validation.py
8. case_step_executor 集成
9. IDE 状态识别与目标定位面板
```

## 23. 结论

工具要知道当前界面和目标位置，不能依赖固定坐标。

正确方案是建立：

```text
状态识别
目标语义解析
多来源特征匹配
目标区域定位
安全点击点计算
点击前校验
IDE 可视化调试
```

这套能力完成后，AutoSmoke 才能稳定判断“当前在哪、该点哪里、能不能点”，并支撑后续完整用例自动执行。
