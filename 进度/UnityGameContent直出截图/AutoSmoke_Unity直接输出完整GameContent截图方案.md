# AutoSmoke Unity 直接输出完整 GameContent PNG 方案

## 1. 目标

当前 AutoSmoke 的 GameContent 截图主要依赖：

```text
Python 全屏截图
  -> 裁 Unity GameView
    -> 裁 GameContent
```

该方案会受到以下因素影响：

- Unity GameView 工具栏高度
- GameView 缩放 Scale
- GameView 黑边
- Windows DPI
- 多显示器坐标
- Unity Editor 窗口位置
- Python crop 超范围
- GameView 被拉伸后的比例重算

本方案目标是：

```text
由 Unity Editor / Unity Runtime 侧直接输出完整游戏画面 PNG，
AutoSmoke IDE 只读取 PNG 和 metadata，
不再依赖屏幕坐标裁剪 GameContent。
```

最终效果：

- 不再裁进 Unity 工具栏。
- 不再因为 GameView 高度不足少截底部。
- 不再因为 contentTop 错误裁掉顶部。
- 不再依赖 Windows 屏幕坐标。
- 可作为自动化测试截图、视觉识别、报告截图的主输入。

## 2. 核心结论

Unity 直接输出完整 GameContent PNG 有两条路线：

| 路线 | 说明 | 推荐级别 |
|---|---|---|
| 路线 A：GameView 截图导出 | 从 Unity Editor GameView 当前显示结果导出 PNG | 推荐作为第一阶段 |
| 路线 B：相机 / RenderTexture 合成导出 | Unity 内部按分辨率渲染完整画面到 Texture，再保存 PNG | 推荐作为长期稳定方案 |

如果目标是尽快解决当前 GameContent 裁剪不准问题，建议先做：

```text
路线 A：Unity Editor GameView 截图导出
```

如果目标是长期稳定、可脱离 Editor 窗口大小、可批量自动化，建议最终演进到：

```text
路线 B：RenderTexture / Camera 合成导出
```

## 3. 方案边界

### 3.1 允许做的事

- 新增 Unity Editor 工具脚本。
- 新增 AutoSmoke 菜单。
- 在 Editor Play 模式下导出当前游戏画面 PNG。
- 导出截图 metadata JSON。
- IDE 读取 Unity 输出的 PNG。
- 不修改游戏业务逻辑。

### 3.2 不允许做的事

- 不修改主城、大地图、战斗等业务代码。
- 不修改线上包运行逻辑。
- 不把测试代码打进正式包。
- 不依赖人工拖动 GameView 窗口大小。

### 3.3 代码放置建议

Unity 项目内：

```text
Assets/AutoSmoke/Editor/AutoSmokeGameContentCapture.cs
Assets/AutoSmoke/Editor/AutoSmokeCaptureConfig.asset
```

所有代码需要加：

```csharp
#if UNITY_EDITOR
...
#endif
```

确保只在 Editor 中生效。

## 4. 路线 A：Unity Editor GameView 截图导出

### 4.1 原理

Unity Editor 的 GameView 已经显示了最终游戏画面，包括：

- 场景相机画面
- UGUI
- Screen Space Overlay UI
- Screen Space Camera UI
- 世界空间 UI
- 后处理效果

如果能从 Unity Editor 侧直接获取 GameView 当前显示结果，就可以绕过 Python 屏幕裁剪。

流程：

```text
Unity Editor Play 模式
  -> 触发 GameView 截图
    -> 保存 PNG
      -> 保存 metadata JSON
        -> AutoSmoke IDE 读取
```

### 4.2 推荐输出路径

```text
E:\zdcs\AutoSmoke\runtime\unity_capture\latest_game_content.png
E:\zdcs\AutoSmoke\runtime\unity_capture\latest_game_content.json
```

每次截图也可以保存历史文件：

```text
E:\zdcs\AutoSmoke\screenshots\unity_20260615_171500\game_content.png
E:\zdcs\AutoSmoke\screenshots\unity_20260615_171500\metadata.json
```

### 4.3 metadata 格式

```json
{
  "schemaVersion": 1,
  "source": "unity_gameview_capture",
  "timestamp": "2026-06-15T17:15:00.000+08:00",
  "unity": {
    "version": "2022.3.62f3",
    "projectPath": "E:/project/client",
    "playMode": true
  },
  "gameResolution": {
    "width": 1170,
    "height": 2532
  },
  "image": {
    "path": "E:/zdcs/AutoSmoke/runtime/unity_capture/latest_game_content.png",
    "width": 1170,
    "height": 2532,
    "format": "png"
  },
  "capture": {
    "method": "game_view",
    "frame": 123456,
    "containsOverlayUI": true,
    "containsCameraUI": true,
    "containsWorldUI": true
  }
}
```

### 4.4 优点

- 最接近测试人员眼睛看到的 GameView。
- 通常能包含 Overlay UI。
- 不需要知道 GameView 屏幕坐标。
- 不需要 Python 裁剪。
- 适合快速解决当前 GameContent 截图不完整问题。

### 4.5 风险

| 风险 | 说明 | 处理 |
|---|---|---|
| GameView 截图 API 不稳定 | Unity 没有完全公开 GameView 截图 API | 使用 Editor 反射，失败时回退路线 B |
| 分辨率受 GameView 当前设置影响 | GameView 当前分辨率不对会影响输出 | 截图前强制设置 GameView 分辨率 |
| 异步保存 | 截图可能下一帧才完成 | 使用协程 / delayCall 等待文件生成 |
| Editor 焦点影响 | 部分截图接口可能需要 GameView 激活 | 截图前 Focus GameView |

## 5. 路线 B：RenderTexture / Camera 合成导出

### 5.1 原理

不依赖 Unity Editor GameView 显示区域，而是由 Unity 内部创建一个目标分辨率的 `RenderTexture`，将游戏画面渲染进去，再编码为 PNG。

流程：

```text
创建 RenderTexture(1170, 2532)
  -> 主相机渲染到 RenderTexture
    -> UI 相机 / Canvas 渲染
      -> ReadPixels / AsyncGPUReadback
        -> EncodeToPNG
          -> 保存 PNG + metadata
```

### 5.2 关键问题：是否能包含全部 UI

Unity UI 常见模式：

| UI 类型 | 是否容易捕获 | 说明 |
|---|---|---|
| Screen Space - Camera | 容易 | 绑定 UI Camera 后可渲染 |
| World Space Canvas | 容易 | 由相机正常渲染 |
| Screen Space - Overlay | 需要特殊处理 | Overlay 不属于普通 Camera.Render |

如果项目大量使用：

```text
Screen Space - Overlay
```

那么单纯 `Camera.Render()` 到 RenderTexture 可能截不到 Overlay UI。

需要以下处理之一：

1. 使用 Unity GameView / ScreenCapture 路线。
2. 临时将 Overlay Canvas 复制或切换到 Screen Space Camera。
3. 使用能捕获完整屏幕输出的接口。

考虑“不修改游戏过程代码”的要求，不建议运行时修改 Canvas 模式作为第一方案。

### 5.3 推荐用途

路线 B 更适合：

- 后续构建稳定的截图服务。
- 不依赖 Editor 窗口大小。
- 批量跑自动化测试。
- 固定分辨率截图。
- 需要更高质量截图。

但第一阶段建议先确认项目 UI 类型，再决定是否全面采用。

## 6. 推荐落地路线

### 6.1 第一阶段：Editor GameView 直出 PNG

目标：

```text
先解决当前 GameContent 裁剪不完整问题。
```

做法：

```text
Unity Editor 侧直接导出 GameView 当前完整画面 PNG。
AutoSmoke IDE 使用该 PNG 作为 game_content_image。
```

输出：

```text
latest_game_content.png
latest_game_content.json
```

IDE 侧不再执行：

```text
全屏截图 -> 裁 GameView -> 裁 GameContent
```

而是：

```text
请求 Unity 导出截图 -> 读取 PNG
```

### 6.2 第二阶段：确认 UI 渲染模式

检查项目中 Canvas 类型：

```text
Screen Space - Overlay
Screen Space - Camera
World Space
```

输出统计：

```json
{
  "canvasSummary": {
    "overlay": 12,
    "screenSpaceCamera": 3,
    "worldSpace": 5
  }
}
```

如果 Overlay UI 很多：

```text
继续优先使用 GameView / ScreenCapture。
```

如果 UI 都能由相机渲染：

```text
可以演进 RenderTexture 方案。
```

### 6.3 第三阶段：Unity Capture Server

Unity Editor 启动本地 HTTP 服务或文件轮询服务：

```text
POST /autosmoke/capture
GET  /autosmoke/status
GET  /autosmoke/latest
```

AutoSmoke IDE 点击截图时：

```text
请求 Unity Capture Server
等待 PNG 生成
读取 metadata
展示截图
```

## 7. Unity 侧接口设计

### 7.1 菜单

```text
AutoSmoke/Capture GameContent Once
AutoSmoke/Start Capture Bridge
AutoSmoke/Stop Capture Bridge
AutoSmoke/Open Capture Folder
```

### 7.2 文件协议

请求文件：

```text
E:\zdcs\AutoSmoke\runtime\unity_capture\capture_request.json
```

内容：

```json
{
  "requestId": "cap_20260615_171500",
  "resolution": {
    "width": 1170,
    "height": 2532
  },
  "outputDir": "E:/zdcs/AutoSmoke/runtime/unity_capture",
  "includeMetadata": true
}
```

Unity 输出：

```text
E:\zdcs\AutoSmoke\runtime\unity_capture\cap_20260615_171500.png
E:\zdcs\AutoSmoke\runtime\unity_capture\cap_20260615_171500.json
```

完成标记：

```text
E:\zdcs\AutoSmoke\runtime\unity_capture\cap_20260615_171500.done
```

错误标记：

```text
E:\zdcs\AutoSmoke\runtime\unity_capture\cap_20260615_171500.error.json
```

### 7.3 状态文件

```json
{
  "running": true,
  "lastCapture": {
    "requestId": "cap_20260615_171500",
    "status": "success",
    "png": "E:/zdcs/AutoSmoke/runtime/unity_capture/cap_20260615_171500.png",
    "metadata": "E:/zdcs/AutoSmoke/runtime/unity_capture/cap_20260615_171500.json"
  }
}
```

## 8. AutoSmoke IDE 集成

### 8.1 配置

```json
{
  "unity_capture": {
    "enabled": true,
    "mode": "game_view",
    "request_file": "E:/zdcs/AutoSmoke/runtime/unity_capture/capture_request.json",
    "output_dir": "E:/zdcs/AutoSmoke/runtime/unity_capture",
    "timeout_ms": 5000,
    "fallback_to_screen_crop": true
  }
}
```

### 8.2 截图优先级

```text
P0 Unity 直出 PNG
P1 Unity Bridge gameContentRectOnScreen
P2 Python GameView 截图裁剪
P3 手动截图配置
```

### 8.3 IDE 截图流程

```text
1. 判断 unity_capture.enabled
2. 写入 capture_request.json
3. 等待 .done 或 .error.json
4. 读取 PNG
5. 读取 metadata
6. 将 PNG 作为 game_content_image
7. 保存到 run_xxx 目录
8. 进入 OCR / 模板匹配 / 报告流程
```

### 8.4 对后续模块的影响

使用 Unity 直出 PNG 后：

```text
OCR / 模板匹配 / 报告截图
```

可以直接使用这张 PNG。

坐标点击仍然需要映射：

```text
PNG 坐标 -> 游戏设计分辨率坐标 -> Poco / Unity 点击坐标
```

如果点击仍然是鼠标真实点击，则还需要：

```text
PNG 坐标 -> GameView 屏幕坐标
```

因此建议截图和点击分开：

| 能力 | 推荐来源 |
|---|---|
| 截图识别 | Unity 直出 PNG |
| UI 元素坐标 | Poco / 元数据 |
| 鼠标点击屏幕坐标 | Unity Bridge gameContentRectOnScreen |

## 9. 点击坐标关系

Unity 直出 PNG 解决的是：

```text
识别用截图完整准确
```

但如果执行真实鼠标点击，还需要屏幕坐标。

因此 metadata 应包含：

```json
{
  "image": {
    "width": 1170,
    "height": 2532
  },
  "screenMapping": {
    "available": true,
    "gameContentRectOnScreen": {
      "x": 490,
      "y": 116,
      "width": 341,
      "height": 739
    }
  }
}
```

映射公式：

```text
screenX = gameContentRectOnScreen.x + imageX / imageWidth  * gameContentRectOnScreen.width
screenY = gameContentRectOnScreen.y + imageY / imageHeight * gameContentRectOnScreen.height
```

如果使用 Unity 注入点击，则不需要屏幕坐标：

```text
imageX/imageY -> normalizedX/normalizedY -> Unity EventSystem click
```

## 10. 验收标准

### 10.1 截图完整性

Unity 直出 PNG 必须包含：

- 顶部头像完整
- 顶部资源栏完整
- 主城 / 大地图画面完整
- 右侧活动按钮完整
- 左侧功能按钮完整
- 任务栏完整
- 聊天按钮完整
- 底部功能栏完整
- Debug 标签完整

不得包含：

- Unity GameView 工具栏
- `Display 1`
- `Scale`
- `Play Focused`
- Windows 桌面背景
- PIL 补黑

### 10.2 分辨率

输出 PNG 尺寸应为请求分辨率：

```text
1170x2532
```

或 metadata 明确实际输出尺寸：

```json
"image": {
  "width": 1170,
  "height": 2532
}
```

### 10.3 时效性

截图 metadata 必须包含：

```json
{
  "frame": 123456,
  "timestamp": "...",
  "captureDurationMs": 35
}
```

IDE 等待超时：

```text
默认 5000ms
```

超时后可回退旧方案。

### 10.4 与当前 GameView 一致

在主城 / 大地图场景验证：

```text
Unity 直出 PNG 与肉眼看到的 GameView 内容一致
```

允许差异：

- 分辨率更高。
- 不包含 Unity Editor 工具栏。

不允许差异：

- UI 缺失。
- 底部菜单缺失。
- 顶部资源栏缺失。
- 弹窗遮罩缺失。

## 11. 风险与处理

### 11.1 Overlay UI 截不到

风险：

如果使用 RenderTexture + Camera.Render，Overlay UI 可能缺失。

处理：

```text
第一阶段优先使用 GameView / ScreenCapture。
RenderTexture 作为后续增强，不作为第一阶段唯一方案。
```

### 11.2 截图延迟一帧

风险：

点击后立即截图，可能截到上一帧。

处理：

```text
点击后等待 1~2 帧再截图。
metadata 记录 frame。
```

### 11.3 截图时 GameView 未激活

风险：

GameView 未刷新，截图不是最新画面。

处理：

```text
截图前 Focus GameView。
请求 Repaint。
下一帧执行截图。
```

### 11.4 文件未写完 IDE 就读取

风险：

IDE 读到半个 PNG。

处理：

```text
先写临时文件 .tmp
写完后 rename 为 .png
最后写 .done
```

### 11.5 正式包污染

风险：

Editor 测试代码进入正式包。

处理：

```text
所有代码放入 Editor 目录。
所有类包裹 #if UNITY_EDITOR。
构建前检查 AutoSmoke Editor 脚本不在 Runtime Assembly。
```

## 12. 推荐实施步骤

### 步骤一：实现 Unity 手动截图菜单

目标：

```text
点击 AutoSmoke/Capture GameContent Once
能输出一张完整 PNG。
```

验收：

```text
PNG 不包含 Unity 工具栏
PNG 包含完整顶部和底部 UI
```

### 步骤二：输出 metadata

目标：

```text
PNG 旁边生成 JSON。
```

验收：

```text
metadata 包含 source、timestamp、resolution、image path。
```

### 步骤三：IDE 读取 Unity PNG

目标：

```text
IDE 截图按钮优先展示 Unity 输出 PNG。
```

验收：

```text
metadata.locator.source = unity_capture_png
```

### 步骤四：文件请求协议

目标：

```text
IDE 写 request，Unity 自动响应截图。
```

验收：

```text
IDE 点击截图后 5 秒内拿到 PNG。
```

### 步骤五：点击坐标映射

目标：

```text
识别坐标能映射到真实点击坐标。
```

验收：

```text
识别到的按钮中心点可以被真实点击或 Unity 注入点击命中。
```

## 13. 最终建议

当前 GameContent 截图问题已经证明：

```text
只靠屏幕裁剪和 GameView rect 推算，仍然容易缺顶部或缺底部。
```

因此推荐最终主方案改为：

```text
Unity 直接输出完整 GameContent PNG
```

同时保留：

```text
Unity Bridge gameContentRectOnScreen
```

用于真实鼠标点击坐标映射。

最终架构：

```text
截图识别：Unity 直出 PNG
元素坐标：Poco / 可测试性元数据
真实点击：Unity Bridge 屏幕坐标 或 Unity 注入点击
图像裁剪：仅作为兜底
```

