# AutoSmoke - GameContent 定位通过后的下一步落地方案

## 1. 当前状态

当前 Game 视图三层定位已经验证通过。

已完成能力：

```text
1. GameViewPanel 定位
2. GameRenderArea 定位
3. GameContent 定位
4. 顶部 Unity 工具栏排除
5. 左右黑边排除
6. 底部按钮栏完整保留
7. Game 窗口拉伸后可重新计算内容区
```

当前可作为后续自动化基准的核心数据：

```text
gameContentRect
gameResolution
scaleX / scaleY
```

注意：`gameResolution` 必须作为动态输入，不应写死为 `1170x2532`。  
每次执行前都需要重新获取或校验当前游戏内分辨率，并据此重新计算 `scaleX / scaleY`。

后续所有截图、点击、OCR、模板匹配、元素定位都应基于 `gameContentRect`，不再直接使用 GameView 面板坐标。

## 2. 下一阶段目标

下一步目标是把“能定位画面”升级为“能稳定操作画面”。

需要落地以下能力：

```text
1. 统一坐标映射
2. 纯游戏内容截图
3. 设计坐标点击
4. 归一化坐标点击
5. 点击前后截图对比
6. OCR / 模板匹配输入基准
7. 点击结果判定
8. IDE 可视化调试入口
```

阶段目标：

```text
给定一个游戏内坐标或元素位置，AutoSmoke 能在不同 GameView 尺寸、不同屏幕位置、副屏环境下稳定点击到同一个游戏对象。
```

## 3. 总体执行链路

推荐链路：

```text
1. 获取 GameViewPanel 坐标
2. 获取 GameContentRect
3. 动态获取当前 gameResolution
4. 生成 CoordinateMapper
5. 截取 game_content_screenshot
6. 执行点击
7. 点击后重新截图
8. 判断页面/画面/日志是否变化
9. 写入操作报告
```

执行前必须保证：

```text
gameContentRect 与 gameResolution 是同一次定位周期的数据。
如果 gameResolution 改变，必须重新生成 CoordinateMapper。
```

## 4. 坐标体系定义

后续必须统一坐标体系，避免混用。

| 坐标类型 | 说明 | 示例 |
| --- | --- | --- |
| `screen` | Windows 全局屏幕坐标 | 鼠标实际点击位置 |
| `all_screens_image` | `ImageGrab(all_screens=True)` 大图坐标 | 截图分析坐标 |
| `game_view` | GameViewPanel 内部坐标 | 三层图中的红框内部 |
| `game_content` | 真实游戏内容区坐标 | 纯游戏截图内坐标 |
| `design` | 游戏设计分辨率坐标 | `1170x2532` 中的坐标 |
| `normalized` | 归一化坐标 | `0.0~1.0` |

推荐所有测试用例优先使用：

```text
testId > design 坐标 > normalized 坐标 > 图像识别坐标 > screen 坐标
```

不推荐长期使用固定 `screen` 坐标。

## 5. 坐标映射模块

### 5.1 建议新增文件

```text
E:/zdcs/AutoSmoke/coordinate_mapper.py
```

### 5.2 输入

`game_resolution` 是动态输入，由运行前检测结果提供，不允许在坐标映射模块内部写死。

```json
{
  "game_view_coords": {
    "left": 271,
    "top": 51,
    "right": 759,
    "bottom": 803
  },
  "game_content_rect": {
    "left": 86,
    "top": 62,
    "width": 317,
    "height": 686
  },
  "game_resolution": {
    "width": 1170,
    "height": 2532,
    "source": "unity_editor_script",
    "timestamp": "2026-06-12T17:00:00"
  }
}
```

### 5.2.1 gameResolution 获取优先级

推荐按以下优先级获取当前游戏内分辨率：

```text
1. Unity Editor 脚本读取 Screen.width / Screen.height
2. UnityEditor.UnityStats.screenRes
3. GameView 顶部分辨率文本 OCR
4. AutoSmoke 配置文件中的 game_resolution
5. 用户在 IDE 中手动选择
```

其中：

- 低侵入 Unity 方案推荐使用第 1、2 种。
- 不修改 Unity 代码方案推荐使用第 3、4、5 种。
- 如果来源不是 Unity 直接读取，应在报告中标记可信度。

### 5.2.2 gameResolution 数据结构

建议保存完整来源信息：

```json
{
  "game_resolution": {
    "width": 1170,
    "height": 2532,
    "source": "unity_editor_script",
    "confidence": "high",
    "last_width": 1170,
    "last_height": 2532,
    "changed": false,
    "timestamp": "2026-06-12T17:00:00"
  }
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `width` / `height` | 当前游戏内真实分辨率 |
| `source` | 获取来源 |
| `confidence` | 可信度：`high/medium/low` |
| `last_width` / `last_height` | 上一次运行使用的分辨率 |
| `changed` | 本次是否发生分辨率变化 |
| `timestamp` | 获取时间 |

### 5.3 输出能力

需要提供以下函数：

```python
design_to_screen(x, y)
screen_to_design(x, y)
normalized_to_screen(nx, ny)
screen_to_normalized(x, y)
content_to_screen(x, y)
screen_to_content(x, y)
```

### 5.4 核心公式

设计坐标转屏幕坐标：

```text
scaleX = gameContentRect.width / gameResolution.width
scaleY = gameContentRect.height / gameResolution.height

screenX = gameView.left + gameContentRect.left + designX * scaleX
screenY = gameView.top + gameContentRect.top + designY * scaleY
```

屏幕坐标转设计坐标：

```text
designX = (screenX - gameView.left - gameContentRect.left) / scaleX
designY = (screenY - gameView.top - gameContentRect.top) / scaleY
```

归一化坐标转屏幕坐标：

```text
designX = nx * gameResolution.width
designY = ny * gameResolution.height
screen = design_to_screen(designX, designY)
```

### 5.4.1 分辨率变化时的映射重建

每次运行前必须执行：

```text
1. 获取 currentGameResolution
2. 比较 lastGameResolution
3. 如果不同，标记 RESOLUTION_CHANGED
4. 重新计算 scaleX / scaleY
5. 重新创建 CoordinateMapper
6. 重新截图作为当前基准图
```

不能复用旧的：

```text
scaleX / scaleY
design 坐标映射结果
模板匹配缓存
OCR 坐标缓存
```

### 5.5 精度要求

```text
scaleX 和 scaleY 差异 <= 1%
坐标换算误差 <= 2px
点击时使用元素中心点
最后一步才四舍五入为整数像素
```

当 `gameResolution` 变化时，需要额外校验：

```text
gameContentRect.width / currentGameResolution.width
gameContentRect.height / currentGameResolution.height
```

两者差异仍应小于 1%。  
如果超过 1%，说明当前分辨率、内容区定位或黑边计算存在不一致，应阻断点击并标记 `SCALE_MISMATCH`。

## 6. 纯游戏内容截图模块

### 6.1 建议新增文件

```text
E:/zdcs/AutoSmoke/screenshot_game_content.py
```

### 6.2 功能

从所有屏幕截图中裁剪纯游戏内容：

```text
all_screens_screenshot
-> gameViewPanel crop
-> gameContentRect crop
-> game_content_screenshot
```

### 6.3 输出

建议输出：

```text
screenshots/run_<run_id>/game_content_<timestamp>.png
screenshots/run_<run_id>/game_view_<timestamp>.png
screenshots/run_<run_id>/debug_three_layers_<timestamp>.png
```

### 6.4 用途

```text
OCR
模板匹配
空页面检测
颜色变化检测
点击前后对比
报告截图证据
```

### 6.5 分辨率绑定

每张 `game_content_screenshot` 必须绑定当时的 `gameResolution`：

```json
{
  "path": "screenshots/run_x/game_content_001.png",
  "gameResolution": {
    "width": 1170,
    "height": 2532,
    "source": "unity_editor_script"
  },
  "gameContentRect": [86, 62, 317, 686],
  "scale": [0.2709, 0.2709]
}
```

OCR、模板匹配、点击前后对比必须使用同一定位周期的数据。  
如果截图对应的 `gameResolution` 与当前运行分辨率不同，应废弃旧截图和识别缓存。

## 7. 点击执行模块

### 7.1 建议新增文件

```text
E:/zdcs/AutoSmoke/click_game_content.py
```

### 7.2 支持点击类型

```text
1. design 坐标点击
2. normalized 坐标点击
3. content 坐标点击
4. 图像识别结果点击
5. OCR 文字中心点击
```

### 7.3 点击接口示例

```json
{
  "action": "click",
  "coordinateType": "design",
  "x": 585,
  "y": 2400,
  "description": "点击使用按钮"
}
```

### 7.4 执行流程

```text
1. 读取当前 gameResolution
2. 读取最新 gameContentRect
3. 校验 gameResolution 与 gameContentRect 是否来自同一定位周期
4. 创建 CoordinateMapper
5. 通过 CoordinateMapper 转换为 screen 坐标
6. 点击前截图
7. 执行鼠标点击
8. 等待短时间
9. 点击后截图
10. 判断是否发生变化
11. 写入 step_result
```

### 7.5 点击安全规则

点击前需要校验：

```text
screen 坐标是否在 GameContent 内
坐标是否在当前屏幕范围内
是否命中危险区域
是否被弹窗/遮罩阻挡
当前 GameView 是否仍然有效
当前 gameResolution 是否与 CoordinateMapper 一致
```

如果校验失败：

```text
不执行点击
记录 BLOCKED
输出原因
```

分辨率变化时：

```text
不允许复用旧 CoordinateMapper
不允许复用旧 OCR 坐标
不允许复用旧模板匹配结果
必须重新截图、重新识别、重新映射
```

## 8. 点击结果判定

点击后需要判断是否成功，而不是只看“鼠标点下去了”。

推荐判定方式：

```text
1. 截图差异
2. OCR 文本变化
3. UI 树变化
4. Poco dump 变化
5. 页面 ID 变化
6. 日志变化
7. 弹窗出现/关闭
```

### 8.1 最低可用判定

第一阶段可以先使用：

```text
点击前截图
点击后截图
计算差异比例
```

判定：

```text
diffRatio < 0.1%     可能无响应
0.1%~2%              轻微变化
>2%                  明显变化
```

结果分类：

```text
CLICK_CHANGED
CLICK_NO_CHANGE
CLICK_BLOCKED
CLICK_OUT_OF_REGION
RESOLUTION_CHANGED
SCALE_MISMATCH
```

## 9. OCR 与模板匹配接入

GameContent 定位通过后，OCR 和模板匹配必须只处理纯游戏截图。

输入：

```text
game_content_screenshot
```

不应再输入：

```text
Unity Editor 截图
GameViewPanel 截图
包含黑边/工具栏的截图
```

### 9.1 OCR 输出坐标

OCR 输出一般是图片内坐标，需要标记坐标类型：

```json
{
  "text": "使用",
  "coordinateType": "game_content",
  "rect": [110, 640, 210, 690]
}
```

点击 OCR 结果时：

```text
OCR rect center
-> game_content 坐标
-> screen 坐标
-> 点击
```

OCR 结果必须记录识别时的 `gameResolution`。  
如果点击时分辨率已变化，应重新 OCR，不应使用旧 OCR 坐标。

### 9.2 模板匹配输出坐标

模板匹配也应输出 `game_content` 坐标：

```json
{
  "template": "use_button",
  "coordinateType": "game_content",
  "rect": [105, 630, 215, 700],
  "score": 0.93
}
```

模板匹配结果必须记录：

```json
{
  "template": "use_button",
  "coordinateType": "game_content",
  "rect": [105, 630, 215, 700],
  "score": 0.93,
  "gameResolution": [1170, 2532],
  "scale": [0.2709, 0.2709]
}
```

如果分辨率变化：

```text
1. 优先重新截图并重新匹配。
2. 若使用固定模板，启用多尺度匹配。
3. 若不同分辨率模板差异明显，按分辨率维护模板目录。
```

## 10. UI 用例执行接入

Excel 用例中可以新增或兼容以下写法：

```text
点击 design(585,2400)
点击 normalized(0.5,0.95)
点击 text("使用")
点击 template("use_button")
```

优先级：

```text
testId / UI 树定位
OCR / 文本定位
模板匹配
design 坐标
normalized 坐标
```

对于当前阶段，建议先支持：

```text
design 坐标
normalized 坐标
OCR 文本中心点击
```

## 11. IDE 界面建议

IDE 中建议新增 “Game 视图定位” 调试面板。

### 11.1 面板展示

展示：

```text
GameViewPanel 坐标
GameContentRect 坐标
gameResolution
gameResolution 来源与可信度
是否发生 RESOLUTION_CHANGED
scaleX / scaleY
定位状态
最后更新时间
```

### 11.2 操作按钮

提供：

```text
重新定位
截取 GameContent
显示三层框
测试点击中心点
测试点击使用按钮
复制坐标
重新读取分辨率
```

### 11.3 调试图

显示：

```text
debug_three_layers.png
game_content_realtime.png
before_click.png
after_click.png
```

## 12. 数据结构建议

统一定位结果：

```json
{
  "status": "OK",
  "gameViewPanelRect": {
    "left": 271,
    "top": 51,
    "width": 488,
    "height": 752
  },
  "gameContentRect": {
    "left": 86,
    "top": 62,
    "width": 317,
    "height": 686
  },
  "gameResolution": {
    "width": 1170,
    "height": 2532,
    "source": "unity_editor_script",
    "confidence": "high",
    "changed": false
  },
  "scale": {
    "x": 0.2709,
    "y": 0.2709
  },
  "source": "game_content_locator",
  "timestamp": "2026-06-12T17:00:00"
}
```

点击结果：

```json
{
  "stepId": "step_001",
  "action": "click",
  "input": {
    "coordinateType": "design",
    "x": 585,
    "y": 2400
  },
  "mapped": {
    "coordinateType": "screen",
    "x": 515,
    "y": 763,
    "gameResolution": [1170, 2532],
    "scale": [0.2709, 0.2709]
  },
  "result": "CLICK_CHANGED",
  "beforeScreenshot": "...",
  "afterScreenshot": "...",
  "diffRatio": 0.034
}
```

## 13. 动态分辨率管理

### 13.1 为什么必须动态管理

GameView 拉伸只会改变显示尺寸，但 GameView 分辨率下拉框变化会改变游戏内坐标基准。

例如：

```text
1170x2532 -> 1080x1920
```

这种变化会影响：

```text
design 坐标
scaleX / scaleY
OCR 坐标回放
模板匹配结果
点击位置
```

因此 `gameResolution` 必须在每次运行前作为动态输入读取。

### 13.2 运行前检查

每次执行用例前，需要执行：

```text
1. 获取 currentGameResolution
2. 获取 currentGameContentRect
3. 比较 lastGameResolution
4. 如果分辨率变化，标记 RESOLUTION_CHANGED
5. 清空旧坐标缓存、OCR 缓存、模板匹配缓存
6. 重建 CoordinateMapper
7. 重新生成 game_content_screenshot
```

### 13.3 分辨率变化处理策略

如果分辨率变化：

```text
normalized 坐标：可继续使用，但必须重新映射
design 坐标：需确认是否属于当前分辨率坐标系
OCR/text：需要重新截图重新识别
template：需要重新匹配或使用多尺度匹配
screen 坐标：必须废弃
```

建议结果分类：

```text
RESOLUTION_CHANGED_REBUILT
RESOLUTION_CHANGED_BLOCKED
SCALE_MISMATCH
```

### 13.4 用例坐标策略

抗分辨率能力排序：

```text
testId > normalized > OCR/text > template > design > screen
```

建议：

- 长期用例优先使用 `testId` 或 `normalized`。
- `design` 坐标必须声明对应分辨率。
- `screen` 坐标只允许调试，不建议进入正式用例。

示例：

```json
{
  "action": "click",
  "coordinateType": "design",
  "x": 585,
  "y": 2400,
  "baseResolution": [1170, 2532]
}
```

如果当前分辨率不是 `[1170, 2532]`：

```text
1. 若允许自动转换：先转 normalized，再映射当前分辨率
2. 若不允许自动转换：阻断并提示 RESOLUTION_CHANGED_BLOCKED
```

### 13.5 配置建议

```json
{
  "resolution_policy": {
    "dynamic_game_resolution": true,
    "on_resolution_changed": "rebuild_mapper",
    "allow_design_coordinate_rescale": true,
    "block_screen_coordinate_on_change": true
  }
}
```

## 14. 实施步骤

### 阶段一：动态分辨率读取

交付：

```text
get_game_resolution()
resolution_state.json
RESOLUTION_CHANGED 检测
```

验收：

```text
能读取当前 GameView 分辨率
分辨率变化后能识别 changed=true
能记录 source/confidence/timestamp
```

### 阶段二：坐标映射

交付：

```text
coordinate_mapper.py
design_to_screen()
screen_to_design()
normalized_to_screen()
screen_to_normalized()
```

验收：

```text
设计坐标中心点能映射到游戏内容中心
scaleX 与 scaleY 差异小于 1%
映射结果落在 GameContent 范围内
分辨率变化后能重建 CoordinateMapper
```

### 阶段三：纯游戏截图

交付：

```text
screenshot_game_content.py
game_content_screenshot
```

验收：

```text
截图不含 Unity 工具栏
截图不含左右黑边
截图包含完整底部按钮栏
截图元数据包含 gameResolution
```

### 阶段四：点击执行

交付：

```text
click_game_content.py
支持 design / normalized 点击
点击前后截图
```

验收：

```text
点击“使用”按钮中心连续 5 次命中
GameView 移动后仍命中
GameView 拉伸后重新定位仍命中
分辨率变化后能重新映射再点击
```

### 阶段五：点击结果判定

交付：

```text
截图差异检测
CLICK_CHANGED / CLICK_NO_CHANGE 分类
step_result.json
```

验收：

```text
点击有效按钮能识别画面变化
点击空白区域能识别无明显变化
结果写入报告
分辨率变化时输出 RESOLUTION_CHANGED 或重建记录
```

### 阶段六：OCR / 模板匹配接入

交付：

```text
OCR 输入 game_content_screenshot
模板匹配输入 game_content_screenshot
识别结果坐标统一为 game_content 坐标
```

验收：

```text
识别“使用”文字
点击 OCR 中心点命中按钮
模板匹配按钮图标命中按钮
分辨率变化后不复用旧 OCR/模板匹配坐标
```

## 15. 不修改 Unity 代码与低侵入方案关系

当前下一步能力大部分可以不修改 Unity 代码完成：

```text
坐标映射：不需要修改 Unity
纯游戏截图：不需要修改 Unity
点击执行：不需要修改 Unity
截图差异判定：不需要修改 Unity
OCR / 模板匹配：不需要修改 Unity
```

但以下能力如果要更稳定，建议低侵入接入 Unity：

```text
自动获取游戏分辨率
自动获取 UI testId
自动判断遮挡
自动导出场景对象
自动获取页面 ID
```

推荐策略：

```text
当前阶段先不修改 Unity 代码，把外部点击链路跑通。
后续再接入 Unity 导出器提升准确率。
```

## 16. 验收标准

### 15.1 坐标映射验收

- `design_to_screen()` 输出坐标在 GameContent 内。
- `screen_to_design()` 能反解回原坐标，误差 <= 2px。
- GameView 拉伸后重新定位，映射仍正确。
- 分辨率变化后不复用旧 CoordinateMapper。
- `SCALE_MISMATCH` 能阻断点击。

### 15.2 点击验收

- 能点击“使用”按钮中心。
- 能点击背包第一个物品格子中心。
- 点击空白区域不会误判为按钮成功。
- 点击结果有截图证据。
- 分辨率变化后，先重新映射再点击。

### 15.3 截图验收

- `game_content_screenshot` 为纯游戏内容。
- 截图尺寸与 `gameContentRect.width/height` 一致。
- 截图可用于 OCR 和模板匹配。
- 截图元数据包含当前 `gameResolution`。

### 15.4 报告验收

- 每次点击记录输入坐标、映射坐标、结果状态。
- 每次点击保存 before / after 截图。
- 失败时说明原因：越界、无变化、截图失败、定位失效。
- 分辨率变化时记录 `RESOLUTION_CHANGED`、旧分辨率、新分辨率和处理动作。

### 16.5 动态分辨率验收

- 能识别当前 GameView 分辨率。
- 分辨率从 `1170x2532` 变为其他值时，能标记 `changed=true`。
- 分辨率变化后，OCR/模板匹配缓存被废弃。
- 固定 `screen` 坐标在分辨率变化后被阻断。

## 17. 推荐下一步优先级

建议按以下顺序实施：

```text
1. 动态 gameResolution 读取与变化检测
2. coordinate_mapper.py
3. screenshot_game_content.py
4. click_game_content.py
5. before/after screenshot diff
6. OCR/模板匹配接入
7. IDE 调试面板
```

理由：

```text
坐标映射是所有点击能力的基础。
动态分辨率是坐标映射正确的前提。
纯游戏截图是 OCR、模板匹配和报告证据的基础。
点击执行验证后，才能进入自动用例执行。
```

## 18. 结论

GameContent 定位通过后，AutoSmoke 已经具备进入自动化执行阶段的基础。

下一阶段不应继续纠结 GameView 边界，而应围绕 `gameContentRect` 建立：

```text
统一坐标映射
动态 gameResolution 管理
纯游戏截图
稳定点击
点击结果判定
OCR / 模板匹配输入标准
```

完成这些能力后，就可以把 Excel 用例中的"点击、断言、等待、截图、结果判定"真正串成可执行闭环。

---

## 19. 实施完成总结（2026-06-12）

### 19.1 六阶段交付物

| 阶段 | 模块 | 文件 | 状态 | 核心功能 |
|:----:|------|------|:----:|----------|
| 一 | 动态分辨率读取 | `resolution_manager.py` | ✅ | 4层来源优先级 + RESOLUTION_CHANGED 检测 + 状态持久化 |
| 二 | 坐标映射 | `coordinate_mapper.py` | ✅ | 8种坐标互转 + 副屏偏移修正 + Scale Mismatch 检测 |
| 三 | 纯游戏截图 | `screenshot_game_content.py` | ✅ | 全屏→GameView→GameContent 三级裁剪 + 元数据绑定 |
| 四 | 点击执行 | `click_game_content.py` | ✅ | 4种点击类型 + 虚拟屏幕校验 + before/after 截图 |
| 五 | 截图差异判定 | `screenshot_diff.py` | ✅ | 差异比例计算 + 高亮图生成 + step_result 输出 |
| 六 | OCR/模板匹配 | `game_content_vision.py` | ✅ | 模板匹配 + OCR接口 + 统一 game_content 坐标输出 |

### 19.2 实测验证

```text
链路：Poco定位 → CoordinateMapper映射 → ClickExecutor点击 → ScreenshotDiffer验证
目标：金币图标 normalized(0.2484, 0.0280)
结果：CLICK_CHANGED (0.91%)  ✅  用户确认"点到了"
```

### 19.3 关键修复

```text
1. CoordinateMapper 加入虚拟屏幕偏移 screen_offset，解决副屏点击偏移
2. 安全校验从主屏范围(GetSystemMetrics 0/1)改为虚拟屏幕范围(76/77/78/79)
3. contentTop 自适应重算：当 contentTop > toolbar_height 时用实际可用高度重算 contentWidth
```

### 19.4 依赖情况

| 依赖 | 用途 | 状态 |
|------|------|:----:|
| pywin32 (win32api) | 屏幕坐标 + 鼠标模拟点击 | ✅ 已安装 |
| opencv-python (cv2) | 模板匹配 | ✅ 已安装（系统 Python 3.11） |
| pytesseract + Tesseract-OCR | OCR 文字识别 | ⏳ 未安装，需手动装 |
| PIL (Pillow) | 图像处理 | ✅ 内置依赖 |
| numpy | 图像数组运算 | ✅ 内置依赖 |

### 19.5 后续建议

```text
短期：
1. 安装 pytesseract + Tesseract-OCR 启用 OCR 识别
2. 收集常用 UI 按钮的模板图片放入 templates/ 目录
3. 用 click_game_content.py 编写实际测试用例脚本

中期：
4. 将 Excel 用例中的"点击/断言/等待"串入执行闭环
5. 接入 test_runner.py 的自动化执行流程
6. 增加 IDE 调试面板

长期：
7. 低侵入 Unity 侧接入（自动分辨率获取、testId 导出）
8. 弹窗自动检测与处理
9. 跨分辨率用例坐标自动适配
```
