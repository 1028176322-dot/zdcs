# AutoSmoke - Unity Game 视图定位落地方案

## 1. 文档目标

本文档基于 `AutoSmoke_Game视图定位_技术文档.md`，用于指导 AutoSmoke IDE 落地 Unity Editor 中 Game 视图定位能力。

本方案重点解决：

- 自动定位 Unity Editor 中 Game 视图位置。
- 自动裁剪出真实游戏画面区域。
- 支持 Game 窗口被拉伸、缩放、移动、副屏显示。
- 自动获取 Game 窗口显示尺寸与游戏内分辨率。
- 为后续截图、点击、OCR、图像识别、UI 自动化提供统一坐标基准。
- 明确区分“不修改 Unity 代码”和“低侵入修改 Unity 代码”的实现路线。

## 2. 当前已验证能力

根据现有技术文档，目前已经验证通过的能力包括：

- 使用 `ImageGrab.grab(all_screens=True)` 支持多显示器截图。
- 支持副屏、负坐标屏幕环境。
- 可通过 C# Editor 脚本反射读取 `UnityEditor.GameView`。
- 可读取 `GameView.position` 获取 GameView 面板位置。
- 可读取 `viewInWindow` 获取 GameView 内部渲染区域近似位置。
- 可通过图像分析修正底部边界。
- 可自动复制 `GameViewLocator.cs` 到 Unity 项目。
- 可通过 `[InitializeOnLoad] + EditorApplication.delayCall` 自动触发定位。
- 可将 C# 结果写入 `%USERPROFILE%\.autosmoke\game_view_pos.json`。
- Python 端可读取 JSON 并转换为截图坐标。

当前验证结果：

```text
GameView 截图坐标：(271, 51, 759, 761)
尺寸：488 x 710
验证状态：红框标注已确认覆盖 Game 视图
```

## 3. 需要进一步落地的问题

当前定位已经能找到 Unity GameView 区域，但要用于自动化测试，还需要继续解决以下问题：

1. 只定位 GameView 面板还不够，需要进一步定位真实游戏内容区。
2. GameView 顶部工具栏、左右黑边不应进入点击坐标计算。
3. Game 窗口被拉伸后，真实游戏内容区会变化，需要自动重算。
4. 需要自动获取游戏内分辨率，例如 `1170x2532`。
5. 需要统一坐标换算模型，支持设计分辨率坐标、截图坐标、屏幕坐标互转。
6. 需要明确当 Unity 代码不可修改时的降级方案。
7. 需要形成 IDE 可调用的稳定接口。

## 4. 总体落地架构

推荐采用双路线架构：

```text
优先路线：低侵入 Unity Editor 脚本
备用路线：不修改 Unity 代码的图像分析
```

整体流程：

```text
1. 查找 Unity Editor 窗口
2. 定位 GameView 面板区域
3. 定位真实游戏内容区域
4. 获取游戏内分辨率
5. 计算显示缩放比例
6. 保存坐标与分辨率信息
7. IDE 使用该信息执行截图、点击、OCR、图像识别
```

最终输出统一为：

```json
{
  "found": true,
  "source": "unity_editor_reflection",
  "screen": {
    "virtualLeft": -1920,
    "virtualTop": 0
  },
  "gameViewRect": {
    "left": 271,
    "top": 51,
    "right": 759,
    "bottom": 761,
    "width": 488,
    "height": 710
  },
  "gameContentRect": {
    "left": 86,
    "top": 20,
    "right": 405,
    "bottom": 710,
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
  "blackBars": {
    "left": 86,
    "right": 84,
    "top": 20,
    "bottom": 0
  },
  "timestamp": "2026-06-12T15:52:04"
}
```

## 5. 方案 A：不修改 Unity 代码

### 5.1 适用场景

适用于以下情况：

- 不能向 Unity 工程写入任何脚本。
- 不能修改 `Assets/Editor`。
- 只能从外部通过 Python、截图、Windows API 获取信息。
- 用于快速验证或临时自动化。

### 5.2 可获得的信息

可稳定获得：

- Unity Editor 窗口位置。
- Unity Editor 客户区截图。
- GameView 近似区域。
- 游戏内容区显示尺寸。
- 当前截图中的游戏画面坐标。

较难稳定获得：

- Unity 内部真实分辨率 `Screen.width/height`。
- GameView 顶部下拉框选中的分辨率。
- GameView 内部 Scale 精确值。

### 5.3 实现方式

无修改方案主要依赖：

```text
Windows API
+ 多显示器截图
+ 图像边界检测
+ 设计分辨率比例计算
+ OCR 兜底读取顶部 GameView 分辨率
```

### 5.4 GameView 定位

优先使用已有 `locate_game_area_smart.py --force-image` 的图像分析能力：

- 通过 Unity Editor 截图分析 GameView 区域。
- 检测顶部标签栏特征。
- 检测颜色丰富度。
- 检测目标宽高比。
- 输出 GameView 面板截图坐标。

### 5.5 真实游戏内容区定位

在 GameView 区域内继续定位真实游戏内容区。

算法：

```text
输入：
  gameViewImage
  designResolution = 1170 x 2532

步骤：
  1. 去掉顶部 GameView 工具栏候选区域。
  2. 在剩余区域中检测非黑色内容范围。
  3. 根据设计分辨率比例计算最大可显示矩形。
  4. 用图像边界对左右黑边、上下黑边进行微调。
  5. 输出 gameContentRect。
```

核心比例：

```text
targetRatio = designWidth / designHeight
```

适配拉伸：

```text
containerRatio = renderAreaWidth / renderAreaHeight

如果 containerRatio > targetRatio:
    contentHeight = renderAreaHeight
    contentWidth = contentHeight * targetRatio
    offsetX = (renderAreaWidth - contentWidth) / 2
    offsetY = 0
否则:
    contentWidth = renderAreaWidth
    contentHeight = contentWidth / targetRatio
    offsetX = 0
    offsetY = (renderAreaHeight - contentHeight) / 2
```

### 5.6 游戏内分辨率获取

不修改 Unity 代码时，推荐按以下优先级获取：

```text
1. 读取 AutoSmoke 配置中的 game_resolution
2. 从 GameView 顶部文字 OCR 识别，例如 1170x2532
3. 从历史成功记录中复用
4. 由用户在 IDE 中选择一次
```

配置示例：

```json
{
  "game_resolution": {
    "width": 1170,
    "height": 2532
  }
}
```

### 5.7 优点

- 不改 Unity 工程。
- 接入速度快。
- 适合先跑通截图、点击和图像识别。

### 5.8 缺点

- 对 Unity 布局、颜色、黑边识别有依赖。
- 如果游戏画面全黑、全白或内容极少，图像修正可能失败。
- 无法可靠读取 Unity 内部真实分辨率。
- 多 Unity 实例时容易误选。

## 6. 方案 B：低侵入修改 Unity 代码

### 6.1 适用场景

适用于以下情况：

- 可以向 Unity 项目的 `Assets/Editor` 放入一个只读 Editor 脚本。
- 不修改业务逻辑。
- 不影响运行包。
- 需要稳定、可复现、跨分辨率的坐标定位。

这是推荐作为 IDE 默认能力的方案。

### 6.2 修改范围

只新增 Editor 脚本：

```text
Assets/Editor/GameViewLocator.cs
```

该脚本仅在 Unity Editor 中运行，不进入正式游戏包。

### 6.3 C# 脚本职责

`GameViewLocator.cs` 负责：

- 反射查找 `UnityEditor.GameView` 实例。
- 读取 GameView 面板坐标。
- 读取 `viewInWindow` 渲染区域。
- 读取当前游戏分辨率。
- 读取或推导 GameView Scale。
- 输出 JSON 到 `%USERPROFILE%\.autosmoke\game_view_pos.json`。

### 6.4 需要输出的字段

建议扩展当前 JSON：

```json
{
  "found": true,
  "unityVersion": "2022.3.62f3",
  "gameViewPanel": {
    "x": -1649,
    "y": 73,
    "width": 488,
    "height": 711
  },
  "viewInWindow": {
    "x": 0,
    "y": 21,
    "width": 488,
    "height": 690
  },
  "gameResolution": {
    "width": 1170,
    "height": 2532,
    "source": "Screen.width_height"
  },
  "unityStatsScreenRes": "1170x2532",
  "timestamp": "2026-06-12T15:52:04"
}
```

### 6.5 游戏分辨率读取方式

优先级：

```text
1. Play 模式下读取 Screen.width / Screen.height
2. 读取 UnityEditor.UnityStats.screenRes
3. 反射读取 GameView 当前选中的分辨率项
4. 回退到 AutoSmoke 配置 game_resolution
```

示例：

```csharp
int width = Screen.width;
int height = Screen.height;
string screenRes = UnityEditor.UnityStats.screenRes;
```

注意：

- `Screen.width/height` 在 Play 模式下更有意义。
- `UnityStats.screenRes` 可能返回字符串，需要解析。
- 不同 Unity 版本内部字段可能不同，因此需要保留 fallback。

### 6.6 Python 端职责

Python 端负责：

- 自动复制 `GameViewLocator.cs` 到 Unity 项目。
- 等待 Unity 编译并输出 JSON。
- 读取 C# 输出的屏幕坐标。
- 转换为截图坐标。
- 计算 `gameContentRect`。
- 保存到统一配置。
- 生成标注截图用于验证。

### 6.7 优点

- 精度高。
- 不依赖 OCR。
- 不依赖颜色特征。
- 支持副屏、负坐标。
- 可自动获取游戏分辨率。
- 适合长期集成到 IDE。

### 6.8 缺点

- 需要向 Unity 工程写入 Editor 脚本。
- 首次接入需要等待 Unity 编译。
- Unity 版本升级后，反射字段可能需要适配。

## 7. 推荐最终方案

推荐采用混合方案：

```text
优先使用低侵入 Editor 脚本
失败时使用图像分析
仍失败时要求用户手动校准一次
```

运行优先级：

```text
1. C# Editor 反射读取 GameView 信息
2. Python 多显示器截图转换坐标
3. 用设计分辨率比例计算真实内容区
4. 用图像分析微调边界
5. 写入配置与报告
```

失败降级：

```text
C# 读取失败 -> 图像分析定位 GameView
游戏分辨率读取失败 -> 读取配置 game_resolution
内容区检测失败 -> 使用比例计算
比例计算失败 -> 手动校准 normalizedContentRect
```

## 8. 坐标体系定义

为避免后续混乱，统一定义 5 种坐标：

| 坐标类型 | 说明 | 示例 |
| --- | --- | --- |
| 屏幕坐标 | Windows 全局屏幕坐标，副屏可能为负数 | `(-1649, 94)` |
| 截图坐标 | `ImageGrab(all_screens=True)` 大图中的坐标 | `(271, 51)` |
| GameView 坐标 | Unity GameView 面板内部坐标 | `(0, 0)` |
| 内容区坐标 | 真实游戏画面内容区内部坐标 | `(0, 0)` |
| 设计分辨率坐标 | 游戏逻辑分辨率坐标 | `(585, 1266)` |

## 9. 坐标换算公式

### 9.1 设计坐标转屏幕点击坐标

```text
scaleX = gameContentRect.width / gameResolution.width
scaleY = gameContentRect.height / gameResolution.height

screenX = gameViewScreenLeft + gameContentRect.left + designX * scaleX
screenY = gameViewScreenTop + gameContentRect.top + designY * scaleY
```

### 9.2 屏幕坐标转设计坐标

```text
designX = (screenX - gameViewScreenLeft - gameContentRect.left) / scaleX
designY = (screenY - gameViewScreenTop - gameContentRect.top) / scaleY
```

### 9.3 截图坐标转内容区坐标

```text
contentX = screenshotX - gameViewRect.left - gameContentRect.left
contentY = screenshotY - gameViewRect.top - gameContentRect.top
```

## 10. Game 窗口拉伸适配

当 GameView 被拉伸时，不保存固定像素坐标，而是每次重新计算：

```text
contentRect = fitAspectRect(renderAreaRect, gameResolutionRatio)
```

伪代码：

```python
def fit_aspect_rect(container, design_width, design_height):
    target_ratio = design_width / design_height
    container_ratio = container.width / container.height

    if container_ratio > target_ratio:
        content_h = container.height
        content_w = content_h * target_ratio
        x = container.x + (container.width - content_w) / 2
        y = container.y
    else:
        content_w = container.width
        content_h = content_w / target_ratio
        x = container.x
        y = container.y + (container.height - content_h) / 2

    return Rect(x, y, content_w, content_h)
```

验收要求：

- 拉宽 GameView 后，左右黑边变化，但内容区仍准确。
- 拉高 GameView 后，上下黑边变化，但内容区仍准确。
- Scale 改变后，设计坐标点击仍命中同一游戏对象。

## 11. 文件落地规划

### 11.1 现有文件

```text
E:\zdcs\AutoSmoke\locate_game_area_smart.py
E:\zdcs\AutoSmoke\game_view_locator.py
E:\zdcs\AutoSmoke\config_manager.py
E:\zdcs\AutoSmoke\tools\GameViewLocator.cs
E:\zdcs\AutoSmoke\config\config.json
```

### 11.2 建议新增模块

```text
E:\zdcs\AutoSmoke\game_content_locator.py
E:\zdcs\AutoSmoke\coordinate_mapper.py
E:\zdcs\AutoSmoke\screenshot_game_view.py
E:\zdcs\AutoSmoke\click_game_view.py
E:\zdcs\AutoSmoke\diagnostics\verify_game_view_location.py
```

### 11.3 模块职责

| 文件 | 职责 |
| --- | --- |
| `game_content_locator.py` | 从 GameView 中定位真实游戏内容区 |
| `coordinate_mapper.py` | 统一处理屏幕、截图、内容区、设计坐标互转 |
| `screenshot_game_view.py` | 截取 GameView 或真实内容区 |
| `click_game_view.py` | 根据设计坐标或相对坐标执行点击 |
| `verify_game_view_location.py` | 生成标注图，验证定位结果 |

## 12. 配置设计

推荐统一配置存放在：

```text
%USERPROFILE%\.autosmoke\config.json
```

示例：

```json
{
  "unity_project_path": "E:/s1/k3client/client",
  "game_resolution": {
    "width": 1170,
    "height": 2532
  },
  "game_view": {
    "cache_ttl_seconds": 60,
    "prefer_unity_editor_script": true,
    "allow_image_fallback": true,
    "allow_manual_calibration": true
  },
  "last_location": {
    "gameViewRect": [271, 51, 759, 761],
    "gameContentRect": [86, 20, 405, 710],
    "scale": [0.2726, 0.2725],
    "timestamp": "2026-06-12T15:52:04"
  }
}
```

## 13. IDE 操作流程

### 13.1 首次接入

```text
1. 用户选择 Unity 项目路径
2. IDE 检查是否允许写入 Editor 脚本
3. 若允许，复制 GameViewLocator.cs
4. 等待 Unity 自动编译
5. 读取 game_view_pos.json
6. 生成定位验证图
7. 用户确认一次
8. 保存配置
```

### 13.2 日常运行

```text
1. 检查缓存是否过期
2. 若未过期，直接复用
3. 若过期，重新读取 GameView 坐标
4. 检查 GameView 是否变化
5. 重新计算 gameContentRect
6. 执行截图、点击、OCR 或 UI 自动化
```

### 13.3 Game 窗口变化

触发重新定位的条件：

- Unity 窗口位置变化。
- GameView 面板大小变化。
- 分辨率下拉框变化。
- Scale 变化。
- 用户拖动 Unity 布局。
- 超过缓存有效期。

## 14. 自动点击落地方式

支持三种点击输入：

```text
1. 设计分辨率坐标
2. 当前内容区归一化坐标
3. 图像/OCR 检测出的内容区坐标
```

推荐优先使用设计分辨率坐标或归一化坐标。

点击示例：

```json
{
  "action": "click",
  "coordinateType": "design",
  "x": 585,
  "y": 2400
}
```

转换后执行：

```text
screenX = gameViewScreenLeft + gameContentLeft + x * scaleX
screenY = gameViewScreenTop + gameContentTop + y * scaleY
```

## 15. 截图落地方式

建议同时支持：

- `editor_screenshot`：完整 Unity Editor 截图。
- `game_view_screenshot`：GameView 面板截图。
- `game_content_screenshot`：真实游戏内容截图。

自动化测试默认使用：

```text
game_content_screenshot
```

这样 OCR、模板匹配、空页面检测不会受到 Unity 工具栏和黑边影响。

## 16. 不同电脑运行策略

### 16.1 路径配置

优先级：

```text
1. 环境变量 AUTOSMOKE_UNITY_PROJECT_PATH
2. 用户配置 ~/.autosmoke/config.json
3. 当前目录及父目录自动查找 Assets
4. IDE 手动选择路径
```

### 16.2 C# 脚本来源

优先级：

```text
1. AutoSmoke/tools/GameViewLocator.cs
2. 环境变量 AUTOSMOKE_CS_SOURCE_DIR
3. ~/.autosmoke/GameViewLocator.cs
```

### 16.3 输出目录

默认：

```text
%USERPROFILE%\.autosmoke\
```

可通过环境变量覆盖：

```text
AUTOSMOKE_CONFIG_DIR
```

## 17. 异常处理

| 异常 | 处理方式 |
| --- | --- |
| 找不到 Unity 窗口 | 提示启动 Unity，或选择目标窗口 |
| 多个 Unity 实例 | IDE 列出窗口标题供选择 |
| GameView 不可见 | 提示打开 Game 视图 |
| C# 脚本编译失败 | 展示 Unity Console 错误，并切换图像分析 |
| C# JSON 超时未生成 | 重新触发一次，仍失败则降级 |
| 图像分析失败 | 使用缓存或要求手动校准 |
| 分辨率未知 | 使用配置值或要求用户选择 |
| GameView 被拉伸 | 重新计算 `gameContentRect` |

## 18. 验收标准

### 18.1 GameView 定位验收

- 支持主屏与副屏。
- 支持副屏负坐标。
- 支持 Unity 窗口移动后重新定位。
- 生成的红框覆盖 GameView 面板。

### 18.2 游戏内容区定位验收

- 裁剪结果不包含 Unity 顶部工具栏。
- 裁剪结果不包含左右黑边。
- 裁剪结果与实际游戏画面边界误差不超过 2 像素。
- GameView 拉伸后仍能自动重算。

### 18.3 分辨率获取验收

- 能自动获取或配置 `1170x2532` 这类游戏内分辨率。
- 计算出的 `scaleX` 与 `scaleY` 差异不超过 1%。
- 当分辨率变化时能更新配置或发出提示。

### 18.4 点击验收

- 使用设计分辨率坐标点击“使用”按钮，至少连续 5 次命中。
- GameView 拉伸后，点击同一设计坐标仍命中同一 UI。
- Unity 窗口移动到副屏后，点击仍正确。

### 18.5 截图验收

- `game_content_screenshot` 只包含真实游戏画面。
- OCR 不受 Unity 工具栏影响。
- 模板匹配不受左右黑边影响。

## 19. 分阶段实施计划

### 阶段一：基础可用

目标：

- 复用现有 `locate_game_area_smart.py`。
- 输出 GameView 坐标。
- 生成验证截图。

交付：

- GameView 面板定位可用。
- 副屏截图可用。
- 坐标缓存可用。

### 阶段二：真实内容区定位

目标：

- 新增 `game_content_locator.py`。
- 基于设计分辨率比例裁剪真实游戏内容区。
- 支持 GameView 拉伸。

交付：

- `gameContentRect`。
- `game_content_screenshot`。
- 标注验证图。

### 阶段三：分辨率自动获取

目标：

- 扩展 `GameViewLocator.cs`。
- 输出 `Screen.width/height`、`UnityStats.screenRes`。
- Python 端解析并写入配置。

交付：

- `gameResolution`。
- `scaleX/scaleY`。
- 分辨率变化检测。

### 阶段四：点击与截图接口

目标：

- 新增 `coordinate_mapper.py`。
- 新增 `screenshot_game_view.py`。
- 新增 `click_game_view.py`。

交付：

- 按设计坐标点击。
- 按归一化坐标点击。
- 自动截图真实游戏内容区。

### 阶段五：IDE 集成

目标：

- 在 IDE 中提供 Game 视图定位面板。
- 显示当前坐标、分辨率、缩放、来源、可信度。
- 支持重新定位、验证截图、手动校准。

交付：

- IDE 可视化状态。
- 错误诊断。
- 一键重新定位。

## 20. 风险与规避

### 20.1 Unity 版本反射兼容

风险：

- `viewInWindow` 在部分 Unity 版本中字段变化。

规避：

- 输出 `game_view_fields.txt`。
- 保留多字段匹配。
- 保留图像分析降级。

### 20.2 多 Unity 实例

风险：

- 找错 Unity 窗口。

规避：

- 根据项目路径匹配窗口标题。
- IDE 列出候选实例。
- 配置当前目标进程 ID。

### 20.3 游戏画面单色

风险：

- 图像边界修正失败。

规避：

- 优先使用比例计算。
- 保存上次成功结果。
- 提供手动校准。

### 20.4 GameView 缩放误差

风险：

- 显示缩放和分辨率计算有小数误差。

规避：

- 点击前保留浮点计算，最后一步四舍五入。
- 允许 1 到 2 像素容差。
- 用中心点点击，避免点在边缘。

## 21. 最终推荐结论

AutoSmoke 应将 Game 视图定位能力做成一个独立基础模块。

推荐最终落地路线：

```text
低侵入 Editor 脚本读取 GameView
+ 多显示器截图转换
+ 设计分辨率比例适配拉伸
+ 图像分析微调边界
+ 统一坐标映射
+ IDE 可视化验证
```

对于不能修改 Unity 工程的项目，提供无侵入降级：

```text
Windows API
+ 多显示器截图
+ 图像分析定位
+ 配置分辨率
+ 手动校准兜底
```

这样既能满足当前快速落地，也能支撑后续自动点击、截图识别、OCR、UI 树提取、页面关系图和测试报告闭环。
