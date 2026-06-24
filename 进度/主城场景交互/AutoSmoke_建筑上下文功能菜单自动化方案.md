# AutoSmoke - 建筑上下文功能菜单自动化方案

## 1. 背景

在 SLG 主城场景中，建筑通常不是普通 UI 按钮，而是场景对象。  
点击建筑后，会呼出该建筑对应的上下文功能菜单，例如：

```text
建筑名称
建筑等级
功能按钮：训练 / 升级 / 详情 / 加速 / 信息
```

该菜单与普通弹窗不同：

```text
它不是阻塞弹窗
它依附于某个建筑对象
点击功能按钮会进入对应功能
点击菜单外安全空白区域会收起菜单
```

因此，需要将其作为独立交互类型处理：

```text
interactionType = building_context_menu
```

不能简单套用普通弹窗关闭或阻塞处理逻辑。

## 2. 目标

本方案目标是实现：

```text
1. 自动识别主城建筑对象。
2. 点击建筑后识别建筑上下文菜单是否出现。
3. 自动识别菜单中的功能按钮。
4. 根据用例步骤点击对应功能按钮。
5. 在需要收起菜单时，点击安全空白区域。
6. 确保空白点击不会点到其它建筑、按钮或底部导航。
7. 所有结果封装进 IDE 的主城场景交互能力。
```

## 3. 设计边界

必须遵守当前项目约束：

```text
不修改游戏业务运行过程代码
允许使用截图、OCR、模板匹配、Poco dump、UI 树、SceneStateExporter
允许使用 Unity Editor 辅助脚本读取只读信息
最终能力封装到 IDE
```

## 4. 状态模型

建筑上下文菜单状态：

```text
NONE
  当前未选中建筑

BUILDING_SELECTED
  已点击建筑，但菜单尚未稳定

MENU_OPENED
  建筑名称、等级、功能按钮已出现

ACTION_TRIGGERED
  已点击某个功能按钮，进入对应功能

MENU_COLLAPSED
  点击安全空白区域后菜单已收起

BLOCKED
  无法识别建筑、菜单或安全空白区域
```

状态转移：

```text
NONE
 -> click building
 -> BUILDING_SELECTED
 -> detect context menu
 -> MENU_OPENED
 -> click action button
 -> ACTION_TRIGGERED
```

收起流程：

```text
MENU_OPENED
 -> click safe blank point
 -> MENU_COLLAPSED
```

## 5. 模块规划

建议新增以下模块：

```text
E:/zdcs/AutoSmoke/scene_interaction_detector.py
E:/zdcs/AutoSmoke/building_context_menu_detector.py
E:/zdcs/AutoSmoke/building_action_executor.py
E:/zdcs/AutoSmoke/safe_blank_point_finder.py
```

### 5.1 scene_interaction_detector.py

职责：

```text
检测当前是否处于主城场景
识别场景对象区域
输出建筑候选列表
识别是否存在建筑上下文菜单
```

### 5.2 building_context_menu_detector.py

职责：

```text
检测建筑菜单是否打开
识别建筑名称
识别建筑等级
识别功能按钮
输出 menu_result
```

### 5.3 building_action_executor.py

职责：

```text
按用例步骤点击建筑
点击建筑菜单中的功能按钮
点击后判断是否进入对应功能
```

### 5.4 safe_blank_point_finder.py

职责：

```text
计算用于收起菜单的安全空白点
避开其它建筑
避开功能按钮
避开底部导航
避开右侧活动按钮
避开 Debug / 返回按钮
```

## 6. 建筑识别方式

推荐多来源融合：

```text
1. SceneStateExporter 导出的建筑对象
2. Poco/UI 树中的场景对象节点
3. 模板匹配建筑图标/建筑上方标记
4. OCR 识别建筑名称/等级
5. 图像区域点击候选
```

优先级：

```text
SceneStateExporter > Poco/UI树 > 模板匹配 > OCR > 图像候选
```

如果当前阶段不接入 Unity 运行时代码，可先使用：

```text
截图 + 模板匹配 + 手动录制建筑区域 + normalized 坐标
```

## 7. 建筑菜单识别

点击建筑后，应检测是否出现：

```text
建筑名称，例如“兵营”
等级，例如“Lv.5”
功能按钮组
按钮图标或按钮文字
按钮围绕建筑出现
```

识别输出：

```json
{
  "detected": true,
  "interactionType": "building_context_menu",
  "buildingName": "兵营",
  "level": 5,
  "menuRect": [130, 330, 270, 470],
  "actions": [
    {
      "name": "train",
      "label": "训练",
      "rect": [135, 405, 170, 440],
      "confidence": 0.91
    },
    {
      "name": "upgrade",
      "label": "升级",
      "rect": [230, 380, 270, 420],
      "confidence": 0.94
    },
    {
      "name": "info",
      "label": "信息",
      "rect": [200, 430, 235, 465],
      "confidence": 0.88
    }
  ]
}
```

## 8. 功能按钮点击

用例步骤示例：

```text
点击 building("兵营")
点击 buildingAction("升级")
点击 buildingAction("训练")
点击 buildingAction("信息")
```

执行流程：

```text
1. 确认当前处于主城场景。
2. 定位建筑。
3. 点击建筑。
4. 等待菜单稳定。
5. 检测 building_context_menu。
6. 找到目标功能按钮。
7. 点击按钮中心。
8. 判断是否进入对应功能页面/弹窗。
```

结果判定：

```text
菜单出现且目标按钮存在 -> READY
按钮点击后页面变化 -> PASS
目标按钮不存在 -> FAIL_ACTION_NOT_FOUND
点击后无变化 -> WARNING_CLICK_NO_CHANGE
出现危险确认 -> BLOCKED_DANGEROUS_ACTION
```

## 9. 收起建筑菜单

用例步骤示例：

```text
收起 building_context_menu
点击 safeBlank()
```

执行流程：

```text
1. 检测当前是否存在建筑菜单。
2. 计算安全空白点。
3. 点击安全空白点。
4. 验证建筑功能按钮消失。
5. 验证未误打开其它建筑菜单或其它页面。
```

## 10. 安全空白点计算

### 10.1 输入

```text
gameContentRect
buildingRect
menuRect
actionButtonRects
otherBuildingRects
uiButtonRects
bottomNavRect
rightActivityRect
debugButtonRect
```

### 10.2 候选区域

安全空白点优先选择：

```text
1. 当前建筑菜单外侧的非建筑空地
2. 水面、道路、草地等不可交互区域
3. 当前建筑周围但不覆盖功能按钮的位置
4. 屏幕中部没有 UI 按钮覆盖的区域
```

### 10.3 禁止区域

不能点击：

```text
其它建筑
当前建筑
建筑功能按钮
右侧活动按钮
底部导航栏
返回按钮
Debug 按钮
任务按钮
商店按钮
邮件按钮
任何已识别的可点击 UI 按钮
```

### 10.4 候选点评分

候选点可按网格扫描生成，并评分：

```text
距离菜单越远，分数越高
距离其它建筑越远，分数越高
位于 UI 按钮区域，直接淘汰
位于其它建筑矩形内，直接淘汰
位于屏幕边缘危险区域，降分
命中水面/空地模板，升分
```

伪代码：

```python
def find_safe_blank_point(context):
    candidates = generate_grid_points(context.gameContentRect, step=24)
    valid_points = []

    for point in candidates:
        if point_in_any_rect(point, context.forbiddenRects):
            continue
        if distance_to_rect(point, context.menuRect) < 40:
            continue
        if distance_to_any_rect(point, context.otherBuildingRects) < 30:
            continue

        score = 0
        score += distance_to_rect(point, context.menuRect)
        score += min_distance_to_rects(point, context.otherBuildingRects)

        if is_likely_empty_terrain(point):
            score += 100

        valid_points.append((point, score))

    if not valid_points:
        return None

    return max(valid_points, key=lambda x: x[1])[0]
```

### 10.5 收起成功验证

点击安全空白点后，必须验证：

```text
建筑名称/等级消失
功能按钮组消失
没有打开其它建筑菜单
没有进入新页面/弹窗
下一步目标状态满足
```

如果验证失败：

```text
尝试下一个安全空白点
超过 maxAttempts 后 BLOCKED_SAFE_BLANK_NOT_FOUND
```

## 11. 与阻塞处理的关系

建筑上下文菜单不是普通阻塞弹窗。

区别：

| 类型 | 是否阻塞 | 是否可空白关闭 | 是否有业务上下文 |
| --- | --- | --- | --- |
| 普通弹窗 | 是 | 可能 | 弱 |
| 奖励弹窗 | 是 | 可能 | 奖励 |
| 建筑上下文菜单 | 不一定 | 是 | 强，绑定建筑 |

处理原则：

```text
如果下一步就是点击建筑功能按钮：
    不收起菜单，直接点击目标功能按钮。

如果下一步与当前建筑菜单无关：
    先安全收起菜单。
```

## 12. step_result 数据结构

点击建筑：

```json
{
  "stepIndex": 1,
  "rawStep": "点击 building(\"兵营\")",
  "action": "click_building",
  "target": {
    "type": "building",
    "name": "兵营"
  },
  "result": "PASS",
  "interaction": {
    "type": "building_context_menu",
    "state": "MENU_OPENED",
    "buildingName": "兵营",
    "level": 5
  },
  "beforeScreenshot": "...",
  "afterScreenshot": "..."
}
```

点击功能按钮：

```json
{
  "stepIndex": 2,
  "rawStep": "点击 buildingAction(\"升级\")",
  "action": "click_building_action",
  "target": {
    "building": "兵营",
    "action": "升级"
  },
  "result": "PASS",
  "clickedButton": {
    "label": "升级",
    "rect": [230, 380, 270, 420]
  },
  "afterState": "upgrade_popup_opened"
}
```

收起菜单：

```json
{
  "stepIndex": 3,
  "rawStep": "收起 building_context_menu",
  "action": "collapse_building_context_menu",
  "result": "PASS",
  "safeBlankPoint": [84, 510],
  "verify": "menu_disappeared"
}
```

## 13. IDE 封装

IDE 中建议提供：

```text
主城场景交互面板
当前识别到的建筑列表
当前建筑菜单状态
建筑名称/等级
功能按钮列表
安全空白点候选
点击建筑调试
点击功能按钮调试
收起菜单调试
```

调试图：

```text
building_rect 标注
menu_rect 标注
action_button_rects 标注
safe_blank_candidates 标注
chosen_safe_blank_point 标注
```

## 14. 配置建议

```json
{
  "building_context_menu": {
    "enabled": true,
    "detect_timeout_ms": 3000,
    "action_click_wait_ms": 800,
    "collapse_enabled": true,
    "collapse_max_attempts": 3,
    "safe_blank_grid_step": 24,
    "min_distance_to_menu": 40,
    "min_distance_to_building": 30,
    "forbidden_regions": [
      "bottom_nav",
      "right_activity_bar",
      "debug_button",
      "back_button",
      "known_ui_buttons"
    ]
  }
}
```

## 15. 用例格式建议

支持自然语言：

```text
点击建筑 兵营
点击兵营的升级
点击兵营的训练
收起建筑菜单
```

支持结构化表达：

```text
点击 building("兵营")
点击 buildingAction("升级")
collapse building_context_menu
```

推荐结构化表达，方便解析和降低歧义。

## 16. 验收标准

### 16.1 建筑点击验收

```text
能定位兵营建筑
点击建筑后能呼出功能菜单
能识别建筑名称和等级
能识别至少 2 个功能按钮
```

### 16.2 功能按钮点击验收

```text
能点击“升级”按钮
点击后进入对应升级页面/弹窗
能点击“训练/士兵”等按钮
点击后进入对应功能
```

### 16.3 安全收起验收

```text
能计算安全空白点
点击空白点后菜单收起
不会点到其它建筑
不会点到底部导航
不会点到右侧活动按钮
不会打开其它页面
```

### 16.4 报告验收

```text
报告记录建筑名称
报告记录功能按钮
报告记录点击坐标
报告记录安全空白点
失败时记录原因和截图
```

## 17. 实施优先级

```text
1. building_context_menu_detector.py
2. safe_blank_point_finder.py
3. building_action_executor.py
4. 用例解析支持 building/buildingAction
5. case_step_executor 集成
6. IDE 主城交互调试面板
7. 报告接入
```

## 18. 结论

建筑功能按钮呼出是主城场景自动化的核心交互，不应当作普通弹窗处理。

正确做法是将其建模为：

```text
building_context_menu
```

并围绕它实现：

```text
建筑识别
菜单检测
功能按钮点击
安全空白点收起
状态验证
报告记录
IDE 调试
```

该能力完成后，AutoSmoke 才能稳定覆盖 SLG 主城建筑类操作流程。
