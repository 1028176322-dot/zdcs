# AutoSmoke - Game 视图截图二级裁剪修正方案

## 1. 当前截图现象

当前截图文件：

```text
E:/zdcs/AutoSmoke/screenshots/debug_20260612_162154/game_view_realtime.png
```

截图中可以看到：

- 上方包含 Unity GameView 的标签栏。
- 上方包含 `Display / 1170x2532 / Scale` 工具栏。
- 左右包含黑边。
- 底部游戏内容没有完整截出，底部按钮区域缺失。

这说明当前截图拿到的是 **GameView 面板附近区域**，还不是可直接用于自动化的 **纯游戏内容区域**。

## 2. 问题本质

当前定位逻辑混淆了三类区域：

```text
1. gameViewPanelRect
   Unity Editor 中 GameView 整个面板区域，包含标签栏和工具栏。

2. gameRenderAreaRect
   GameView 内部渲染容器区域，不包含标签栏和工具栏，但可能包含黑边。

3. gameContentRect
   真实游戏画面内容区域，不包含工具栏，不包含黑边。
```

自动化点击、OCR、模板匹配、空页面检测应使用：

```text
gameContentRect
```

不能直接使用：

```text
gameViewPanelRect
```

## 3. 目标效果

目标是最终生成一张纯游戏内容截图：

```text
game_content_realtime.png
```

该截图应满足：

- 不包含 Unity Editor 标签栏。
- 不包含 `Display / Resolution / Scale` 工具栏。
- 不包含左右黑边。
- 不缺失底部按钮区域。
- 宽高比例与游戏设计分辨率一致。
- GameView 被拉伸后仍可自动重新计算。

## 4. 推荐三层区域模型

### 4.1 第一层：GameView 面板区域

来源：

```text
UnityEditor.GameView.position
```

作用：

- 定位 Unity Editor 中 GameView 面板。
- 用于从全屏截图中裁剪 GameView 面板。

包含内容：

- 标签栏
- 工具栏
- 游戏渲染区域
- 黑边

不适合直接用于自动化点击。

### 4.2 第二层：Game 渲染容器区域

来源：

```text
UnityEditor.GameView.viewInWindow
```

作用：

- 去掉 Unity 标签栏和工具栏。
- 获得游戏渲染容器。

注意：

- 该区域仍可能包含左右黑边或上下黑边。
- `viewInWindow.height` 在部分情况下可能偏小，需要校验。

### 4.3 第三层：真实游戏内容区域

来源：

```text
gameRenderAreaRect + 游戏分辨率比例计算 + 图像边界微调
```

作用：

- 获得真实游戏画面。
- 自动化点击、截图、OCR、模板匹配统一基于此区域。

## 5. 底部截断问题分析

当前截图底部缺失游戏按钮区域，常见原因有两类。

### 5.1 第一层截图高度不够

如果 `game_view_realtime.png` 本身没有包含完整 GameView 底部，那么后续二级裁剪一定无法恢复。

判断方式：

```text
contentTop + contentHeight > gameViewImage.height
```

如果成立，说明第一层 GameView 截图本身偏短，需要重新修正 GameView 面板底部。

### 5.2 图像边界误判

如果用颜色突变检测底部，可能会把游戏中的棕色底栏、分隔线或浅色背景误判为边界。

因此底部不能只靠颜色分析，应优先使用游戏设计分辨率比例反算。

示例：

```text
设计分辨率：1170 x 2532
当前内容宽度：319
scale = 319 / 1170 = 0.2726
内容高度 = 2532 * 0.2726 = 690
```

只要内容宽度准确，就可以反算内容高度。

## 6. 修正算法

### 6.1 输入

```text
gameViewPanelRect
gameRenderAreaRect
gameResolution = 1170 x 2532
gameViewScreenshot
```

### 6.2 计算步骤

```text
1. 使用 C# 反射读取 GameView 面板区域。
2. 使用 viewInWindow 读取渲染容器区域。
3. 在渲染容器中检测左右黑边，得到内容宽度。
4. 根据设计分辨率比例计算内容高度。
5. 检测游戏内容首行，得到 contentTop。
6. 计算 contentBottom = contentTop + contentHeight。
7. 如果 contentBottom 超出截图高度，则扩大第一层截图区域。
8. 输出 gameContentRect。
```

### 6.3 伪代码

```python
def locate_game_content(render_rect, design_width, design_height, image):
    target_ratio = design_width / design_height

    # 1. 检测左右黑边，得到内容 x 与 width
    content_x, content_width = detect_horizontal_content_bounds(image, render_rect)

    # 2. 根据比例反算高度
    scale = content_width / design_width
    content_height = design_height * scale

    # 3. 检测内容顶部
    content_y = detect_content_top(image, render_rect)

    # 4. 计算底部
    content_bottom = content_y + content_height

    # 5. 判断第一层截图是否足够
    if content_bottom > image.height:
        return {
            "ok": False,
            "error": "GAME_VIEW_CAPTURE_TOO_SHORT",
            "requiredHeight": content_bottom
        }

    return Rect(content_x, content_y, content_width, content_height)
```

## 7. GameView 拉伸适配

GameView 被横向或纵向拉伸时，真实游戏内容区应按游戏分辨率比例重新计算。

公式：

```text
targetRatio = designWidth / designHeight
containerRatio = renderAreaWidth / renderAreaHeight
```

如果容器更宽：

```text
contentHeight = renderAreaHeight
contentWidth = contentHeight * targetRatio
offsetX = (renderAreaWidth - contentWidth) / 2
offsetY = 0
```

如果容器更高：

```text
contentWidth = renderAreaWidth
contentHeight = contentWidth / targetRatio
offsetX = 0
offsetY = (renderAreaHeight - contentHeight) / 2
```

实际实现中，可以先用比例计算，再用图像黑边检测进行 1 到 2 像素微调。

## 8. 输出结构

建议最终输出统一定位结果：

```json
{
  "found": true,
  "gameViewPanelRect": {
    "left": 0,
    "top": 0,
    "width": 488,
    "height": 710
  },
  "gameRenderAreaRect": {
    "left": 0,
    "top": 40,
    "width": 488,
    "height": 670
  },
  "gameContentRect": {
    "left": 85,
    "top": 62,
    "width": 319,
    "height": 690
  },
  "gameResolution": {
    "width": 1170,
    "height": 2532
  },
  "scale": {
    "x": 0.2726,
    "y": 0.2725
  },
  "status": "ok"
}
```

如果发现底部截断：

```json
{
  "found": false,
  "status": "GAME_VIEW_CAPTURE_TOO_SHORT",
  "requiredBottom": 752,
  "currentImageHeight": 710,
  "suggestion": "expand gameViewPanelRect bottom and recapture"
}
```

## 9. 调试图输出

每次定位建议输出两类调试图。

### 9.1 三层框标注图

文件名：

```text
game_view_layers_marked.png
```

标注内容：

- 红框：`gameViewPanelRect`
- 黄框：`gameRenderAreaRect`
- 绿框：`gameContentRect`

用途：

- 快速判断是第一层截错，还是第二层裁错。

### 9.2 纯游戏内容截图

文件名：

```text
game_content_realtime.png
```

要求：

- 只包含游戏画面。
- 不包含 Unity 工具栏。
- 不包含左右黑边。
- 不缺失底部按钮。

## 10. 点击坐标换算

自动点击必须基于 `gameContentRect`。

设计分辨率坐标转屏幕坐标：

```text
scaleX = gameContentRect.width / gameResolution.width
scaleY = gameContentRect.height / gameResolution.height

screenX = gameViewScreenLeft + gameContentRect.left + designX * scaleX
screenY = gameViewScreenTop + gameContentRect.top + designY * scaleY
```

注意：

- 点击时应使用按钮中心点。
- 最后一步再四舍五入为整数像素。
- 不要基于 GameView 面板坐标直接点击。

## 11. 不修改 Unity 代码方案

如果不能修改 Unity 工程，可以采用：

```text
Windows 截图
+ GameView 图像定位
+ 分辨率配置
+ 黑边检测
+ 比例反算内容区
```

优点：

- 不修改项目。
- 接入快。

缺点：

- 真实游戏分辨率需要配置或 OCR 获取。
- 全黑、全白、低对比画面可能影响边界检测。
- GameView 工具栏高度需要通过图像规则识别。

适用：

- 快速验证。
- 临时自动化。
- 不允许写入 Unity 工程的项目。

## 12. 低侵入修改 Unity 代码方案

如果允许低侵入改动，推荐添加 Editor 脚本：

```text
Assets/Editor/GameViewLocator.cs
```

脚本职责：

- 读取 `GameView.position`。
- 读取 `GameView.viewInWindow`。
- 读取 `Screen.width / Screen.height`。
- 读取 `UnityStats.screenRes`。
- 输出 JSON 给 Python/IDE。

优点：

- 定位稳定。
- 可自动获取真实游戏分辨率。
- 不依赖 OCR。
- 不进入正式游戏包。

缺点：

- 需要写入 Unity 工程。
- Unity 版本升级时反射字段可能需要适配。

## 13. 验收标准

### 13.1 裁剪准确性

- 纯游戏截图不包含 Unity 工具栏。
- 纯游戏截图不包含左右黑边。
- 纯游戏截图不缺失底部按钮栏。
- 边界误差不超过 2 像素。

### 13.2 拉伸适配

- 横向拉伸 GameView 后，左右黑边变化但内容区仍正确。
- 纵向拉伸 GameView 后，上下黑边变化但内容区仍正确。
- Scale 改变后，内容区重新计算。

### 13.3 点击验证

- 点击背包界面“使用”按钮中心，连续 5 次命中。
- GameView 移动到副屏后仍能命中。
- GameView 拉伸后仍能命中。

### 13.4 截图验证

- `game_content_realtime.png` 与期望纯游戏截图一致。
- OCR 不识别到 Unity 工具栏文字。
- 模板匹配不受黑边影响。

## 14. 落地建议

第一步：

- 在当前截图基础上增加三层框调试输出。
- 明确当前错误发生在第一层还是第二层。

第二步：

- 先保证 `game_view_realtime.png` 完整包含底部游戏按钮区域。
- 如果缺失，修正第一层 GameView 截图高度。

第三步：

- 新增 `gameContentRect` 计算。
- 使用设计分辨率比例反算高度，避免颜色误判底部。

第四步：

- 输出纯游戏截图 `game_content_realtime.png`。
- 使用该图作为 OCR、模板匹配和点击坐标换算基础。

## 15. 结论

当前截图已经证明 GameView 定位方向是正确的，但还不能直接用于自动化执行。

必须把定位拆成：

```text
GameView 面板区域
Game 渲染容器区域
真实游戏内容区域
```

最终自动化只使用 `gameContentRect`。  
这样才能做到精准裁剪、适配 Game 窗口拉伸，并避免 Unity 工具栏、黑边、底部截断对点击和识别造成影响。
