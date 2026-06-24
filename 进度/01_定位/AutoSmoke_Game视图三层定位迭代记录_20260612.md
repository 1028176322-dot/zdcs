# AutoSmoke - Game 视图三层定位迭代记录

## 1. 本次执行结果

本次调试图：

```text
E:/zdcs/AutoSmoke/screenshots/debug_20260612_163102/debug_three_layers.png
```

图中三层区域已经输出：

```text
1. GameViewPanel：红框
2. GameRenderArea：黄框
3. GameContent：绿框
```

相比上一轮，本次已经可以看到三层模型生效，尤其是 `GameContent` 的左右边界已经基本接近真实游戏画面区域。

## 2. 当前结果判断

### 2.1 已通过部分

```text
GameContent 左边界：基本正确
GameContent 右边界：基本正确
三层调试框：已输出
区域模型：已生效
```

### 2.2 未通过部分

```text
GameContent 顶部定位：未通过
GameContent 底部完整性：未通过
```

具体表现：

- 绿色框顶部从 Unity GameView 工具栏区域开始，而不是从真实游戏画面顶部开始。
- 绿色框底部没有包含完整底部按钮栏。
- 纯游戏内容区域仍不能直接用于点击、OCR、模板匹配。

## 3. 问题分析

### 3.1 GameContent top 错误

当前绿色框的 `top` 明显太靠上。

正确的 `GameContent.top` 应该从游戏画面第一行开始，例如截图中的“背包”顶部区域，而不是从以下区域开始：

```text
Game 标签栏
Display / 分辨率 / Scale 工具栏
Unity GameView 灰色背景
```

说明当前算法可能直接使用了：

```text
contentTop = gameRenderArea.top
```

或者没有正确过滤 Unity 工具栏深灰区域。

### 3.2 GameContent bottom 缺失

当前绿色框底部没有包含完整游戏底栏，例如“使用”按钮区域没有完整出现。

这可能有两个原因：

```text
1. GameContent 高度被当前 GameRenderArea 或截图高度截断。
2. 第一层 GameViewPanel 截图本身高度不够。
```

不能简单通过颜色边界判断底部，因为游戏底部棕色栏、分隔线、浅色背景都可能干扰图像检测。

## 4. 正确修正思路

推荐将 `GameContent` 的定位拆成三步：

```text
1. 先定位 contentLeft / contentRight
2. 再单独定位 contentTop
3. 最后用设计分辨率比例反算 contentHeight
```

不要使用：

```text
contentBottom = 图像检测到的底部边界
```

应该使用：

```text
contentBottom = contentTop + contentHeight
```

## 5. contentTop 检测规则

### 5.1 扫描范围

从 `gameRenderArea.top` 开始向下扫描，到 `gameRenderArea.bottom` 结束。

只检查已经定位到的横向内容范围：

```text
contentLeft ~ contentRight
```

这样可以避开左右黑边。

### 5.2 排除区域

扫描时应跳过以下区域：

- 深灰色 Unity 工具栏。
- 黑边区域。
- 纯灰背景区域。
- GameView 标签文字区域。

### 5.3 判断条件

某一行可作为游戏内容顶部候选，需要满足：

```text
1. 当前行在 contentLeft ~ contentRight 范围内不是深灰/黑色。
2. 当前行颜色均值与 Unity 工具栏颜色差异明显。
3. 当前行后续连续 N 行都满足内容特征。
4. 行内有效像素比例超过阈值。
```

建议初始阈值：

```text
N = 5
有效像素比例 >= 70%
灰色过滤阈值：RGB 三通道差异小且亮度低于 80 的像素视为工具栏/黑边
```

### 5.4 伪代码

```python
def detect_content_top(image, render_rect, content_left, content_right):
    for y in range(render_rect.top, render_rect.bottom):
        ok_count = 0

        for yy in range(y, min(y + 5, render_rect.bottom)):
            row = image[yy, content_left:content_right]
            valid_ratio = calc_non_toolbar_pixel_ratio(row)

            if valid_ratio >= 0.7:
                ok_count += 1

        if ok_count >= 5:
            return y

    return None
```

## 6. contentHeight 与 bottom 计算

游戏设计分辨率：

```text
1170 x 2532
```

根据当前内容宽度计算缩放：

```text
scale = contentWidth / 1170
```

根据缩放反算高度：

```text
contentHeight = 2532 * scale
contentBottom = contentTop + contentHeight
```

不要直接使用图像检测出的底部作为最终底部。

## 7. 截图高度校验

计算出 `contentBottom` 后，需要检查当前截图是否足够高。

```text
如果 contentBottom > image.height:
    标记 GAME_VIEW_CAPTURE_TOO_SHORT
    要求扩大第一层 GameViewPanel 截图底部
```

不要在截图不够高的情况下强行截短 `GameContent`。

错误做法：

```text
contentBottom = min(contentBottom, image.height)
```

正确做法：

```text
返回错误状态并重新截取更大的 GameViewPanel 区域
```

## 8. 下一版需要输出的 Debug 信息

建议下一次调试图旁边或日志中输出以下字段：

```json
{
  "contentLeft": 86,
  "contentRight": 405,
  "contentWidth": 319,
  "detectedContentTop": 62,
  "expectedContentHeight": 690,
  "expectedContentBottom": 752,
  "panelImageHeight": 710,
  "isCaptureTooShort": true
}
```

这些信息可以直接判断：

- 左右边界是否正确。
- 顶部识别是否正确。
- 是否因为第一层截图高度不足导致底部缺失。

## 9. 调试图建议

下一轮建议输出：

```text
debug_three_layers.png
debug_content_top_scan.png
debug_game_content_expected_rect.png
game_content_realtime.png
```

### 9.1 debug_content_top_scan.png

标注：

- 每个候选 contentTop 的扫描行。
- 最终选中的 contentTop。
- 被过滤掉的工具栏区域。

### 9.2 debug_game_content_expected_rect.png

标注：

- 根据比例反算出的完整 `GameContent` 区域。
- 如果超出当前截图，用虚线或警告标记。

### 9.3 game_content_realtime.png

最终纯游戏内容截图，要求：

- 不包含 Unity 工具栏。
- 不包含左右黑边。
- 包含底部按钮栏。

## 10. 验收标准

下一轮修正通过标准：

```text
1. 绿色框顶部从游戏画面顶部开始，而不是 Unity 工具栏。
2. 绿色框底部包含完整底部按钮栏。
3. 绿色框左右边界贴合游戏画面，不包含黑边。
4. 输出 game_content_realtime.png。
5. scaleX 与 scaleY 差异小于 1%。
6. 如果截图高度不足，能明确输出 GAME_VIEW_CAPTURE_TOO_SHORT。
```

## 11. 结论

本次结果证明三层定位模型方向正确，但 `GameContent` 的 top 和 bottom 仍需修正。

下一步重点不是重新设计整体架构，而是修正两个细节：

```text
1. contentTop 必须单独识别游戏画面顶部。
2. contentBottom 必须基于设计分辨率比例反算，并校验截图是否足够高。
```

完成这两个点后，`gameContentRect` 才能作为自动点击、OCR、模板匹配和页面识别的稳定基准。
