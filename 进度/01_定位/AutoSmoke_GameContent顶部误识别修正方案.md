# AutoSmoke - GameContent 顶部误识别修正方案

## 1. 当前执行结果

本次调试图：

```text
E:/zdcs/AutoSmoke/screenshots/debug_20260612_165130/debug_three_layers.png
```

从图中可以看到：

- 第一层 `GameViewPanel` 已经覆盖完整高度。
- 底部按钮栏已经完整出现。
- “使用”按钮和 `Debug` 按钮均未被截断。
- 说明上一轮“扩大第一层 GameViewPanel 底部”的方向正确。

但当前仍存在一个问题：

```text
GameContent.top 太靠上，绿色框仍然包含 Unity GameView 工具栏。
```

因此，后续不应继续扩大 `bottom`，而应修正 `contentTop` 检测逻辑。

## 2. 当前问题判断

### 2.1 已解决

```text
底部截图不完整：已解决
GameViewPanel 高度不足：已解决
底部按钮栏缺失：已解决
```

### 2.2 未解决

```text
GameContent 顶部误识别：未解决
```

表现为：

- 绿色框从 Unity 工具栏区域开始。
- `Display / 1170x2532 / Scale` 区域被包含进 `GameContent`。
- 真实 `GameContent.top` 应从游戏画面顶部开始，也就是“背包”标题所在的游戏内容区域。

## 3. 问题原因

当前 `detect_content_top()` 的扫描起点过早。

可能当前逻辑类似：

```python
for y in range(render_top, render_bottom):
    ...
```

由于 Unity 工具栏中也存在文字、线条和非黑色像素，当前有效像素判断条件会把工具栏误判为游戏内容。

因此，仅依赖“非黑/非灰有效像素比例”不足以区分：

```text
Unity GameView 工具栏
真实游戏画面顶部
```

## 4. 修正目标

修正后应满足：

```text
1. GameContent.top 不再包含 Unity 工具栏。
2. GameContent.top 从游戏画面顶部开始。
3. GameContent.bottom 继续保持完整，不再截断底部按钮栏。
4. 不再继续扩大 game_view_coords.bottom。
5. 输出的 game_content_realtime.png 是纯游戏内容图。
```

## 5. 核心修正策略

### 5.1 增加 contentTop 扫描安全偏移

在检测 `contentTop` 时，不允许从 `render_top` 直接开始扫描。

应设置最小扫描起点：

```text
scan_start = max(render_top + toolbar_safe_gap, min_content_top)
```

建议初始值：

```text
toolbar_safe_gap = 35
min_content_top = 50
```

示例：

```text
toolbarHeight = 22
scan_start = max(22 + 35, 50) = 57
```

当前图中真实游戏顶部大约在：

```text
y ≈ 62
```

因此该规则可以避开 Unity 工具栏，同时不会跳过真实游戏内容顶部。

### 5.2 不再根据当前结果继续扩大 bottom

当前底部已经完整，不应再扩展。

保护规则：

```python
if game_view_coords.get("auto_expanded_bottom"):
    不再继续扩大 bottom
```

后续如果仍然出现 `GAME_VIEW_CAPTURE_TOO_SHORT`，应优先排查：

```text
contentTop 是否太靠上
contentWidth 是否因为黑边识别错误被放大
renderArea 是否被错误计算
```

而不是继续扩大第一层截图。

## 6. 建议代码修改点

目标文件：

```text
E:/zdcs/AutoSmoke/core_engine/game_content_locator.py
```

目标函数：

```python
detect_content_top()
```

### 6.1 修改扫描起点

将原逻辑：

```python
for y in range(render_top, render_bottom - 2):
    ...
```

修改为：

```python
toolbar_safe_gap = 35
min_content_top = 50
scan_start = max(render_top + toolbar_safe_gap, min_content_top)

for y in range(scan_start, render_bottom - 2):
    ...
```

### 6.2 Debug 信息增加扫描起点

建议返回值中增加：

```python
{
    "top": int(y),
    "scan_start": int(scan_start),
    "scan_lines": scan_lines
}
```

失败时也返回：

```python
{
    "top": None,
    "scan_start": int(scan_start),
    "reason": "..."
}
```

### 6.3 主结果 debug_info 增加字段

在 `find_game_content_rect()` 的 `debug_info` 中增加：

```python
"contentTopScanStart": int(content_top_result.get("scan_start", -1))
```

这样调试图或日志中可以明确看到：

```text
从哪一行开始扫描 contentTop
是否跳过了 Unity 工具栏
```

## 7. 建议伪代码

```python
def detect_content_top(
    img_rgb,
    render_rect,
    content_left,
    content_right,
    debug=False,
    debug_dir=None
):
    height = img_rgb.shape[0]
    render_top = render_rect["top"]
    render_bottom = render_rect.get("bottom", height)

    toolbar_safe_gap = 35
    min_content_top = 50
    scan_start = max(render_top + toolbar_safe_gap, min_content_top)

    scan_lines = []

    for y in range(scan_start, render_bottom - 2):
        ok_count = 0

        for yy in range(y, y + 3):
            row = img_rgb[yy, content_left:content_right]
            valid_ratio = calc_non_toolbar_pixel_ratio(row)

            if valid_ratio >= 0.5:
                ok_count += 1

        if ok_count >= 3:
            return {
                "top": int(y),
                "scan_start": int(scan_start),
                "scan_lines": scan_lines
            }

    return {
        "top": None,
        "scan_start": int(scan_start),
        "reason": "未找到连续3行满足有效像素比例>=50%的条件"
    }
```

## 8. 验收标准

修正后需要满足：

```text
1. 绿色 GameContent 框顶部不再覆盖 Unity 工具栏。
2. 绿色 GameContent 框顶部贴近“背包”游戏画面顶部。
3. 绿色 GameContent 框底部仍包含完整“使用”按钮和 Debug 按钮。
4. 绿色 GameContent 框左右边界不包含黑边。
5. 输出 game_content_realtime.png。
6. game_content_realtime.png 不包含 Unity 工具栏、不包含黑边、不缺底部。
```

## 9. 风险与注意事项

### 9.1 safe gap 不宜过大

如果 `toolbar_safe_gap` 过大，可能跳过游戏顶部内容。

建议初始使用：

```text
35px
```

后续可根据更多 GameView 截图微调。

### 9.2 不要继续扩大 bottom

当前底部问题已经解决。

如果后续仍提示截图高度不足，应先检查：

```text
contentWidth 是否变大
contentTop 是否太靠上
scale 是否异常
```

不要简单继续把 `game_view_coords.bottom` 往下推。

### 9.3 后续可改为配置项

建议后续将以下值放入配置：

```json
{
  "game_content_locator": {
    "toolbar_safe_gap": 35,
    "min_content_top": 50
  }
}
```

不同 Unity 版本或不同 Editor 布局可通过配置调整。

## 10. 结论

当前定位链路已经完成了底部截断问题修正。

下一步只需要修正 `contentTop` 扫描起点：

```text
从 render_top 直接扫描
改为
从 render_top + toolbar_safe_gap 开始扫描
```

这样可以避免 Unity GameView 工具栏被误识别为游戏内容，让 `GameContent` 真正贴合纯游戏画面区域。
