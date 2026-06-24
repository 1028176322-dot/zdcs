# AutoSmoke - Unity Game 视图定位技术文档

## 1. 项目背景

AutoSmoke 是一个 Unity 游戏自动化测试框架。在进行 UI 自动化时，需要精确定位 Unity Editor 中 Game 视图的像素坐标，以便后续对游戏画面进行点击、截图等操作。

### 问题定义

**核心问题**：如何自动获取 Unity Editor 中 Game 视图的准确像素坐标？

**挑战**：
1. Unity Editor 的 Game 视图是一个内部 GUI 窗口，不是独立的 Windows 窗口
2. 用户可能使用多显示器（Game 视图可能在副屏）
3. Game 视图的大小取决于 Unity 布局，而不是游戏分辨率
4. 需要通过代码自动获取，而非手动校准

---

## 2. 实现步骤

### 阶段 1：问题分析（❌ 失败）

#### 尝试 1.1：颜色突变检测
**原理**：Game 视图内部颜色丰富，外部（其他面板）颜色较单一，通过检测颜色突变找到 Game 视图边界。

**结果**：❌ 失败。整个 Unity 客户区颜色都丰富，阈值太高，无法准确分割。

#### 尝试 1.2：Windows API 枚举子窗口
**原理**：使用 `win32gui.EnumChildWindows` 枚举 Unity 窗口的所有子窗口，找到 Game 视图。

**结果**：❌ 部分成功。找到了一个子窗口，但坐标转换后有偏差（Game 视图是 Unity 内部窗口，Windows API 可能无法正确枚举）。

#### 尝试 1.3：直接使用副屏截图
**原理**：使用 `ImageGrab.grab(bbox=负坐标)` 截取副屏上的 Unity 窗口。

**结果**：❌ 失败。`ImageGrab` 在副屏负坐标上截图有问题，截取到全黑图像。

---

### 阶段 2：突破 - 多显示器截图（✅ 成功）

#### 关键发现
`ImageGrab.grab(all_screens=True)` 可以截取所有显示器的内容，返回一个拼接的大图像。

**原理**：
1. 使用 `user32.GetSystemMetrics` 获取虚拟屏幕边界（所有显示器的联合边界）
2. 使用 `ImageGrab.grab(all_screens=True)` 截取所有屏幕
3. 计算屏幕坐标到图像坐标的偏移量
4. 裁剪出 Unity 窗口客户区部分

**代码实现**：`locate_game_area_smart.py` 中的 `capture_all_screens()` 和 `screen_to_image_coords()` 函数。

**结果**：✅ 成功截取副屏上的 Unity 窗口。

---

### 阶段 3：C# Editor 脚本反射读取（✅ 成功）

#### 原理
Unity 提供了 C# Editor 脚本机制，可以通过反射读取内部窗口的坐标。

**实现步骤**：
1. 创建 C# Editor 脚本 `GameViewLocator.cs`
2. 将脚本放到 Unity 项目的 `Assets/Editor/` 目录
3. Unity 会自动编译并执行脚本
4. 脚本通过反射找到 `UnityEditor.GameView` 实例
5. 读取 `GameView.position` 属性（屏幕坐标）
6. 将坐标保存到 JSON 文件
7. Python 端读取 JSON，转换为截图坐标

#### 关键代码（C#）
```csharp
// 查找所有 GameView 实例
Type gameViewType = asm.GetType("UnityEditor.GameView");
var windows = Resources.FindObjectsOfTypeAll(gameViewType);

// 读取位置
var pos = target.position;  // Rect (屏幕坐标)
```

#### 问题 3.1：InitializeOnLoad 自动触发
**现象**：脚本已编译，但 `InitializeOnLoad` 特性未立即触发菜单项。

**解决方案**：使用 `[InitializeOnLoad]` + `EditorApplication.delayCall` 实现自动触发。

**原理**：
1. `[InitializeOnLoad]` 在 Unity 编译完成后自动调用静态构造函数
2. `EditorApplication.delayCall` 延迟执行，确保 Unity 界面已初始化
3. 两次延迟后调用 `LocateAndSave()` 自动执行定位

**代码**：
```csharp
[InitializeOnLoad]
public static class GameViewLocator
{
    static GameViewLocator()
    {
        EditorApplication.delayCall += OnFirstDelay;
    }
    
    private static void OnFirstDelay()
    {
        EditorApplication.delayCall += OnSecondDelay;
    }
    
    private static void OnSecondDelay()
    {
        LocateAndSave();  // 自动执行，无需手动点击菜单
    }
}
```

**验证结果**：✅ 已测试通过，Unity 编译完成后自动执行，无需手动操作。

**备用方案**：仍保留菜单项 `AutoSmoke > Locate Game View`，用于手动触发（调试用）。

#### 问题 3.2：坐标偏差（整个面板 vs 游戏渲染区域）
**现象**：`EditorWindow.position` 返回的是 **整个 GameView 面板**的坐标，包含标题栏、工具栏等，而不是游戏渲染区域的坐标。

**正确坐标**：
```
GameView 面板 (488 x 711):
┌─────────────────────────┐
│  标题栏 ("Game")         │  ← 高度 ~21px
├─────────────────────────┤
│  工具栏 (分辨率下拉等)    │  ← 高度 ~0-20px
├─────────────────────────┤
│                         │
│  游戏渲染区域            │  ← 我们真正需要的区域 (488 x 690)
│  (实际游戏画面)         │
│                         │
└─────────────────────────┘
```

**解决方案**：通过反射读取 `GameView` 的 `viewInWindow` 属性，这个属性直接给出了游戏渲染区域在 GameView 窗口中的坐标。

**代码**：
```csharp
PropertyInfo property = type.GetProperty("viewInWindow", 
    BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance);
if (property != null && property.PropertyType == typeof(Rect))
{
    Rect rect = (Rect)property.GetValue(gameView, null);
    // rect = Rect(0, 21, 488, 690)
}
```

---

### 阶段 4：图像分析修正（✅ 成功）

#### 问题 4.1：`viewInWindow.height` 比实际高度小
**现象**：`viewInWindow.height = 690`，但图像分析得到的正确高度是 `710`（底部在 761）。

**可能原因**：`viewInWindow` 不包含 Game 视图底部的某些 UI（状态栏、工具栏等）。

**解决方案**：结合使用 C# 反射读取近似坐标 + 图像分析修正底部位置。

**实现步骤**：
1. 用 C# 脚本读取近似坐标 `(271, 51, 759, 741)`
2. 在返回的坐标附近（当前底部 -50 到 +200），用图像分析搜索正确的底部
3. 使用两种方法：
   - **方法 1**：检测水平分隔线（颜色突变）
   - **方法 2**：检测 Game 视图底部（从当前底部向下搜索，找到第一个"颜色丰富"的行）
4. 选择更可信的结果

**代码实现**：`locate_game_area_smart.py` 中的 `correct_game_view_bottom()` 函数。

**结果**：✅ 成功修正底部位置，从 `741` 修正为 `761`。

---

## 3. 技术方法

### 3.1 C# Editor 脚本反射
**用途**：直接读取 Unity Editor 内部窗口坐标。

**优点**：
- 最准确（直接从 Unity 内存读取）
- 不依赖图像分析
- 速度快

**缺点**：
- 需要 Unity 项目路径
- 需要等待 Unity 编译
- 可能因 Unity 版本不同而无法工作

**关键 API**：
- `Resources.FindObjectsOfTypeAll(Type)`：查找所有 EditorWindow 实例
- `EditorWindow.position`：获取窗口屏幕坐标
- `Type.GetProperty("viewInWindow")`：反射读取内部属性
- `MenuItem`：添加 Unity 菜单项

### 3.2 多显示器截图
**用途**：截取副屏上的 Unity 窗口。

**原理**：
1. 获取虚拟屏幕边界（`GetSystemMetrics(76-79)`）
2. 截取所有屏幕（`ImageGrab.grab(all_screens=True)`）
3. 计算偏移量（屏幕坐标 → 图像坐标）
4. 裁剪出 Unity 客户区

**关键代码**：
```python
# 获取虚拟屏幕边界
virtual_left = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
virtual_top = user32.GetSystemMetrics(77)    # SM_YVIRTUALSCREEN

# 截取所有屏幕
img = ImageGrab.grab(all_screens=True)

# 转换为图像坐标
image_x = screen_x - virtual_left
image_y = screen_y - virtual_top
```

### 3.3 坐标转换
**用途**：将屏幕坐标转换为截图坐标。

**原理**：
1. 读取 Unity 客户区左上角的屏幕坐标（`ClientToScreen(hwnd, (0,0))`）
2. 读取虚拟屏幕的起始坐标（`GetSystemMetrics(76-77)`）
3. 计算偏移量
4. 转换坐标

**公式**：
```
截图X = 屏幕X - 虚拟屏幕左边界
截图Y = 屏幕Y - 虚拟屏幕上边界
```

**注意**：当 Unity 窗口在副屏时，屏幕坐标可能是负值。

### 3.4 图像分析修正
**用途**：在 C# 反射读取的近似坐标基础上，用图像分析修正底部位置。

**方法 1**：检测水平分隔线
- 计算每一行的平均颜色
- 计算与上一行的差异（欧氏距离）
- 如果差异很大且持续多行，可能是分隔线

**方法 2**：检测 Game 视图底部
- 从当前底部向下搜索
- 找到第一个"颜色丰富"的行（标准差突然变大）
- 或者找到颜色标准差突然变化的行（底部边界）

---

## 4. 相关文件脚本

### 4.1 C# Editor 脚本

#### `E:\s1\k3client\client\Assets\Editor\GameViewLocator.cs`
**用途**：Unity Editor 脚本，通过反射读取 Game 视图坐标。

**功能**：
1. 用反射找到所有 `UnityEditor.GameView` 实例
2. 读取 `viewInWindow` 属性（游戏渲染区域坐标）
3. 转换为屏幕坐标
4. 写入 JSON 文件

**输出**：
- JSON 文件：`%USERPROFILE%\.autosmoke\game_view_pos.json`（屏幕坐标）
- 调试文件：`%USERPROFILE%\.autosmoke\game_view_fields.txt`（所有字段列表）

**注意**：路径中的 `%USERPROFILE%` 在 Windows 上会自动展开为 `C:\Users\Administrator`（当前用户），或其他用户的对应路径。

**触发方式**：
- **自动（推荐）**：Unity 编译完成后自动执行（通过 `[InitializeOnLoad]` + `EditorApplication.delayCall`）
- **手动（调试用）**：Unity 菜单 **AutoSmoke > Locate Game View**

**自动化原理**：
1. `[InitializeOnLoad]` 特性在 Unity 编译完成后自动调用静态构造函数
2. `EditorApplication.delayCall` 延迟执行，确保 Unity 界面已初始化
3. 两次延迟后调用 `LocateAndSave()` 自动执行定位
4. 无需手动点击菜单，无需任何用户操作

---

### 4.2 Python 主脚本

#### `E:\zdcs\AutoSmoke\locate_game_area_smart.py`
**用途**：主脚本，自动定位 Game 视图并标注。

**功能**：
1. 加载配置（游戏分辨率）
2. 查找 Unity 窗口
3. 截取 Unity 客户区（支持多显示器）
4. 获取 Game 视图坐标（优先用 C# 反射，降级用图像分析）
5. 修正底部位置（图像分析）
6. 保存标注截图

**用法**：
```bash
# 自动选择最佳方法（推荐）
python locate_game_area_smart.py

# 强制使用图像分析（调试用）
python locate_game_area_smart.py --force-image
```

**关键函数**：
- `try_get_unity_game_view_pos()`：通过 C# 反射读取坐标
- `correct_game_view_bottom()`：用图像分析修正底部位置
- `capture_window_client()`：截取 Unity 客户区
- `find_game_window_in_editor()`：图像分析定位 Game 视图（降级方案）
- `draw_game_area()`：标注 Game 视图区域

---

### 4.3 Python 辅助脚本

#### `E:\zdcs\AutoSmoke\game_view_locator.py`
**用途**：Python 端，负责与 C# 脚本交互。

**功能**：
1. 复制 C# 脚本到 Unity 项目
2. 读取 JSON 文件
3. 必要时触发 Unity 检测（通过菜单）
4. 坐标转换（屏幕坐标 → 截图坐标）

**关键函数**：
- `get_game_view_pos()`：获取 Game 视图坐标（会触发 Unity 编译+执行）
- `convert_to_screenshot_coords()`：将屏幕坐标转换为截图坐标

---

#### `E:\zdcs\AutoSmoke\config_manager.py`
**用途**：配置文件管理工具。

**功能**：
1. 读取/保存游戏分辨率
2. 读取/保存 Unity 项目路径
3. 读取/保存 Game 视图坐标

**新增函数**（本次实现）：
- `get_game_view_coords()`：读取 Game 视图坐标
- `set_game_view_coords()`：保存 Game 视图坐标

---

#### `E:\zdcs\AutoSmoke\detect_game_bottom.py`
**用途**：测试脚本，用于调试图像分析修正底部位置。

**功能**：
1. 读取最新截图
2. 在红框附近搜索 Game 视图的真实底部
3. 使用两种方法：检测水平分隔线、检测颜色丰富区域
4. 生成标注图

**用法**：
```bash
python detect_game_bottom.py
```

---

#### `E:\zdcs\AutoSmoke\test_game_view_coords.py`
**用途**：测试脚本，验证保存的 Game 视图坐标是否正确。

**功能**：
1. 从配置文件读取 Game 视图坐标
2. 读取最新截图
3. 验证坐标是否在截图范围内
4. 裁剪 Game 视图区域并保存

**用法**：
```bash
python test_game_view_coords.py
```

---

### 4.4 配置文件

#### `E:\zdcs\AutoSmoke\config.json`
**用途**：主配置文件。

**内容**：
```json
{
  "game_resolution": {
    "width": 1170,
    "height": 2532
  },
  "auto_detect_region": true,
  "black_threshold": 30,
  "unity_project_path": "E:/s1/k3client/client",
  "game_view_coords": {
    "left": 271,
    "top": 51,
    "right": 759,
    "bottom": 761,
    "width": 488,
    "height": 710,
    "timestamp": "2026-06-12T12:07:00"
  }
}
```

**关键字段**：
- `game_view_coords`：Game 视图的截图坐标（本次实现保存）

---

#### `%USERPROFILE%\.autosmoke\game_view_pos.json`
**用途**：C# 脚本输出的 JSON 文件（屏幕坐标）。

**内容**：
```json
{
  "found": true,
  "x": -1649,
  "y": 94,
  "width": 488,
  "height": 690,
  "error": "",
  "timestamp": "2026-06-12T03:56:47.4880397Z",
  "unityVersion": "2022.3.62f3"
}
```

**说明**：这个文件是 C# 脚本生成的，Python 端会读取它并转换为截图坐标。

**路径说明**：`%USERPROFILE%` 在 Windows 上会自动展开为当前用户的主目录（如 `C:\Users\Administrator`）。

---

## 5. 使用说明

### 5.1 自动定位（推荐）
```bash
python locate_game_area_smart.py
```

**流程**：
1. 查找 Unity 窗口
2. 读取 Game 视图坐标（C# 反射，自动触发）
3. 修正底部位置（图像分析）
4. 保存标注截图

**输出**：
- `E:\zdcs\AutoSmoke\screenshots\editor_YYYYMMDD_HHMMSS.png`（Unity Editor 截图）
- `E:\zdcs\AutoSmoke\screenshots\game_YYYYMMDD_HHMMSS.png`（Game 视图截图）
- `E:\zdcs\AutoSmoke\screenshots\game_area_YYYYMMDD_HHMMSS.png`（标注后截图）

**注意**：首次运行时，Python 脚本会自动复制 C# 脚本到 Unity 项目，Unity 编译完成后会自动执行定位，无需手动操作。

---

### 5.2 手动触发（调试用）

**适用场景**：当自动触发失败时，用于调试。

#### 步骤 1：确保 C# 脚本已复制到 Unity
检查文件是否存在：
```
E:\s1\k3client\client\Assets\Editor\GameViewLocator.cs
```

如果不存在，运行：
```bash
python locate_game_area_smart.py
```
脚本会自动复制。

#### 步骤 2：等待 Unity 编译
- 看 Unity 底部状态栏是否有进度条在转
- 等待编译完成（通常几秒钟）
- 编译完成后，脚本会自动执行定位（无需手动点击菜单）

#### 步骤 3：查看输出（可选）
如果需要查看详细日志，打开 Unity **Console** 窗口，查看输出：
```
[AutoSmoke] 找到属性 viewInWindow: x=0, y=21, w=488, h=690
[AutoSmoke] GameView: x=-1649, y=94, w=488, h=690
[AutoSmoke] JSON: C:\Users\Administrator\.autosmoke\game_view_pos.json
```

#### 步骤 4：运行 Python 脚本
```bash
python locate_game_area_smart.py
```

---

### 5.3 强制图像分析（降级方案）
```bash
python locate_game_area_smart.py --force-image
```

**用途**：当 C# 反射读取失败时使用。

**原理**：在截图上分析颜色/结构特征定位 Game 视图。

**评分标准**：
1. 宽高比匹配（40分）
2. 内容颜色丰富度（30分）
3. 位置（20分）
4. 标签栏特征（10分）

---

## 6. 已知问题和限制

### 6.1 Unity 版本兼容性
- C# 脚本中的反射代码可能因 Unity 版本不同而无法工作
- 当前在 **Unity 2022.3.62f3** 测试通过
- 如果使用其他版本，可能需要调整反射读取的字段/属性名

### 6.2 多 Unity 实例
- 当前代码假设只有一个 Unity Editor 实例
- 如果有多个 Unity 窗口，可能找到错误的实例

### 6.3 Game 视图最小化/关闭
- 如果 Game 视图被最小化或关闭，`Resources.FindObjectsOfTypeAll` 可能找不到实例
- 需要确保 Game 视图在 Unity Editor 中是可见的

### 6.4 布局变化
- 如果 Unity 布局发生变化（拖拽 Game 视图到不同位置），需要重新运行定位
- 坐标缓存有效期为 60 秒，过期后会重新读取

### 6.5 图像分析准确性
- 图像分析修正底部位置的方法依赖于颜色特征
- 如果 Game 视图内容颜色单一（如全黑、全白），可能无法准确修正

---

## 7. 调试技巧

### 7.1 查看 C# 脚本输出了哪些字段
C# 脚本会生成一个调试文件：
```
%USERPROFILE%\.autosmoke\game_view_fields.txt
```

这个文件列出了 `GameView` 的所有字段和属性，可以用于查找其他有用的坐标信息。

**路径说明**：`%USERPROFILE%` 在 Windows 上会自动展开为当前用户的主目录。

### 7.2 查看 Python 端日志
运行 `locate_game_area_smart.py` 时，会输出详细日志：
```
[方法1] 尝试通过 Unity 反射读取 Game 视图坐标...
  ✅ Unity 返回屏幕坐标: x=-1649, y=94, w=488, h=690
  📐 初步截图坐标: (271, 51, 759, 741)

  🔍 用图像分析修正底部位置...
    搜索范围: y=691 到 y=941
    找到底部边界: y=761, 标准差差异=59.9
  ✅ 修正底部: 741 -> 761 (+20px)
```

### 7.3 验证坐标是否正确
使用测试脚本：
```bash
python test_game_view_coords.py
```

这个脚本会：
1. 从配置文件读取 Game 视图坐标
2. 读取最新截图
3. 验证坐标是否在截图范围内
4. 裁剪 Game 视图区域并保存

---

## 8. 下一步计划

### 8.1 截图 Game 视图
实现 `screenshot_game_view.py`，根据保存的坐标自动截图 Game 视图。

### 8.2 点击 Game 视图中的坐标
实现 `click_game_view.py`，将游戏内坐标转换为截图坐标，然后模拟点击。

### 8.3 UI 自动化
基于 Game 视图坐标，实现图像模板匹配、OCR 文字识别等 UI 自动化功能。

---

## 9. 总结

### 9.1 实现方法
1. **C# Editor 脚本反射**（最准确）：通过反射读取 `GameView.viewInWindow` 属性，获取游戏渲染区域坐标
2. **自动化触发**（已验证）：使用 `[InitializeOnLoad]` + `EditorApplication.delayCall` 实现 Unity 编译完成后自动执行
3. **多显示器截图**（关键突破）：使用 `ImageGrab.grab(all_screens=True)` 解决副屏截图问题
4. **坐标转换**（必要步骤）：屏幕坐标 → 截图坐标
5. **图像分析修正**（提高准确性）：在 C# 反射读取的近似坐标基础上，用图像分析修正底部位置

### 9.2 最终坐标
**GameView 面板截图坐标**：`(271, 51, 759, 803)`  
**GameView 面板尺寸**：`488 x 752`

**GameContent（纯游戏画面）截图坐标**：`(85, 62, 403, 750)`  
**GameContent 尺寸**：`318 x 688`  
**缩放比例**：`scaleX=0.2718, scaleY=0.2717`

**验证结果**：✅ 三层标注已确认正确，绿框精确框住纯游戏画面，不含 Unity 工具栏、不含左右黑边、不含顶部灰色背景。

### 9.3 关键文件
- **C# 脚本源文件**：`E:\zdcs\AutoSmoke\tools\GameViewLocator.cs`（会自动复制到 Unity 项目）
- **C# 脚本（Unity 项目）**：`E:\s1\k3client\client\Assets\Editor\GameViewLocator.cs`
- **Python 主脚本**：`E:\zdcs\AutoSmoke\locate_game_area_smart.py`
- **Python 辅助脚本**：`E:\zdcs\AutoSmoke\game_view_locator.py`
- **GameContent 三层定位**：`E:\zdcs\AutoSmoke\core_engine\game_content_locator.py`
- **配置文件**：`E:\zdcs\AutoSmoke\config\config.json`
- **C# 输出文件**：`%USERPROFILE%\.autosmoke\game_view_pos.json`

### 9.4 自动化流程
1. Python 脚本复制 C# 脚本到 Unity 项目
2. Unity 自动编译 C# 脚本
3. `[InitializeOnLoad]` 触发自动执行定位
4. C# 脚本输出 JSON 文件
5. Python 脚本读取 JSON 并转换为截图坐标
6. 图像分析修正底部位置
7. 保存标注截图

**无需手动操作**，整个流程完全自动化。

---

## 10. 在其他电脑上运行

### 10.1 路径配置原则

本项目已改进为支持在其他电脑上运行，主要改进：

1. **配置文件位置**：从项目目录改为用户主目录（`~/.autosmoke/config.json`）
   - 跨项目共享配置
   - 不受项目路径影响

2. **Unity 项目路径**：支持多种配置方式
   - 环境变量：`AUTOSMOKE_UNITY_PROJECT_PATH`
   - 配置文件：`~/.autosmoke/config.json` 中的 `unity_project_path`
   - 自动检测：查找当前目录及父目录中的 `Assets` 文件夹

3. **C# 脚本源文件路径**：支持多种搜索位置
   - 当前脚本所在目录
   - `tools` 子目录
   - 用户主目录的 `.autosmoke` 目录
   - 环境变量：`AUTOSMOKE_CS_SOURCE_DIR`

4. **C# 脚本输出路径**：使用 `%USERPROFILE%\.autosmoke\`
   - 可通过环境变量 `AUTOSMOKE_CONFIG_DIR` 覆盖

### 10.2 环境变量配置（推荐）

在其他电脑上运行前，建议设置以下环境变量：

#### Windows（PowerShell）
```powershell
# Unity 项目路径
$env:AUTOSMOKE_UNITY_PROJECT_PATH = "E:\your_unity_project"

# C# 脚本源目录（可选，如果不放在默认位置）
$env:AUTOSMOKE_CS_SOURCE_DIR = "E:\your_cs_source_dir"

# C# 脚本输出目录（可选，如果不使用默认位置）
$env:AUTOSMOKE_CONFIG_DIR = "E:\your_config_dir"

# 永久设置（重启后保留）
[System.Environment]::SetEnvironmentVariable("AUTOSMOKE_UNITY_PROJECT_PATH", "E:\your_unity_project", "User")
```

#### Windows（命令提示符）
```cmd
set AUTOSMOKE_UNITY_PROJECT_PATH=E:\your_unity_project
```

#### 永久设置（Windows 系统属性）
1. 右键"此电脑" → "属性"
2. "高级系统设置" → "环境变量"
3. 在"用户变量"中新建：
   - 变量名：`AUTOSMOKE_UNITY_PROJECT_PATH`
   - 变量值：`E:\your_unity_project`

### 10.3 配置文件说明

配置文件位置：`%USERPROFILE%\.autosmoke\config.json`

**首次运行**时，如果配置文件不存在，会自动创建默认配置。

**手动创建配置文件**：
```json
{
  "game_resolution": {
    "width": 1170,
    "height": 2532
  },
  "auto_detect_region": true,
  "black_threshold": 30,
  "unity_project_path": "E:/your_unity_project"
}
```

**注意**：路径使用正斜杠 `/` 或双反斜杠 `\\`，避免转义问题。

### 10.4 自动检测功能

如果不想配置环境变量或配置文件，项目支持自动检测：

1. **Unity 项目路径自动检测**：
   - 查找当前目录及父目录中的 `Assets` 文件夹
   - 如果找到，自动使用该项目路径

2. **Game 视图坐标自动获取**：
   - 通过 C# Editor 脚本反射读取
   - 无需手动校准

### 10.5 在其他电脑上部署的步骤

#### 步骤 1：安装依赖
```bash
# 安装 Python 包
pip install pillow numpy pywin32
```

#### 步骤 2：复制项目文件
将以下文件复制到目标电脑：
```
AutoSmoke/
├── config_manager.py
├── game_view_locator.py
├── locate_game_area_smart.py
├── tools/
│   └── GameViewLocator.cs
└── screenshots/（空目录）
```

#### 步骤 3：配置 Unity 项目路径
选择以下任一方式：

**方式 1：设置环境变量**（推荐）
```powershell
$env:AUTOSMOKE_UNITY_PROJECT_PATH = "E:\your_unity_project"
```

**方式 2：创建配置文件**
创建 `%USERPROFILE%\.autosmoke\config.json`，内容如上。

**方式 3：自动检测**
确保当前目录或父目录中有 `Assets` 文件夹，项目会自动检测。

#### 步骤 4：运行测试
```bash
python locate_game_area_smart.py
```

如果一切正常，会看到：
- 找到 Unity 窗口
- 复制 C# 脚本到 Unity 项目
- Unity 自动编译并执行定位
- 生成标注截图

### 10.6 常见问题

#### Q1：在其他电脑上，C# 脚本源文件应该放在哪里？

**A**：可以放在以下任一位置：
1. `locate_game_area_smart.py` 同级目录
2. `tools` 子目录
3. `%USERPROFILE%\.autosmoke\`
4. 环境变量 `AUTOSMOKE_CS_SOURCE_DIR` 指定的目录

#### Q2：配置文件可以放在项目目录下吗？

**A**：可以，但需要修改 `config_manager.py` 中的 `CONFIG_FILE` 变量。建议使用默认位置（用户主目录），这样可以跨项目共享配置。

#### Q3：如果 Unity 项目路径改变了，需要修改代码吗？

**A**：不需要。可以通过以下任一方式更新：
1. 修改环境变量 `AUTOSMOKE_UNITY_PROJECT_PATH`
2. 修改配置文件 `%USERPROFILE%\.autosmoke\config.json`
3. 将项目文件放到 Unity 项目目录中（自动检测）

#### Q4：在多台电脑上共享配置

**A**：可以将配置文件 `%USERPROFILE%\.autosmoke\config.json` 复制到每台电脑的相同位置。注意根据实际情况修改 `unity_project_path`。

---

## 11. 参考资料

### 10.1 Unity 官方文档
- [EditorWindow.position](https://docs.unity3d.com/ScriptReference/EditorWindow-position.html)
- [Resources.FindObjectsOfTypeAll](https://docs.unity3d.com/ScriptReference/Resources.FindObjectsOfTypeAll.html)
- [MenuItem](https://docs.unity3d.com/ScriptReference/MenuItem.html)

### 10.2 Python 库文档
- [Pillow (PIL)](https://pillow.readthedocs.io/)
- [NumPy](https://numpy.org/doc/)
- [pywin32 (win32gui)](https://github.com/mhammond/pywin32)

---

**文档版本**：2.0  
**最后更新**：2026-06-12  
**作者**：AutoSmoke Team

---

## 12. 三层区域模型（GameContentLocator v2）

### 12.1 概述

在获取 GameView 面板坐标后，需要进一步定位**真实游戏画面区域**，以排除 Unity 工具栏、左右黑边等非游戏内容。为此实现了三层区域模型。

### 12.2 三层定义

```
Layer 1 - GameViewPanel（红框）
┌─────────────────────────────────┐
│  完整 GameView 截图             │  488 x 752
│  ┌───────────────────────────┐  │
│  │ Layer 2 - GameRenderArea  │  │  (黄框) 488 x 730 (top=22)
│  │ ┌─────────────────────┐   │  │
│  │ │ Layer 3 - GameContent│   │  │  (绿框) 318 x 688 (top=62, left=85)
│  │ │ 真实游戏画面         │   │  │
│  │ └─────────────────────┘   │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

| 层级 | 名称 | 内容 | 说明 |
|------|------|------|------|
| L1 | gameViewPanelRect | 整个 GameView 截图 | 含所有 Unity UI |
| L2 | gameRenderAreaRect | 去掉顶部 Unity 工具栏 | 含左右黑边 |
| L3 | gameContentRect | 纯游戏画面 | 无工具栏、无黑边 |

### 12.3 算法流程

```
                    ┌───────────────────────┐
                    │  输入：GameView 截图    │
                    │  488 x 752             │
                    └──────────┬────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ L1: GameViewPanel   │
                    │ left=0, top=0       │
                    │ 整个截图即为面板区域 │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ L2: 检测工具栏高度   │
                    │ detect_toolbar_height │
                    │ → toolbarHeight=22   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │ 预计算 L3 内容宽度（比例法）  │
                    │ contentWidth = renderAreaH   │
                    │   × 1170/2532 = 337          │
                    │ leftBlack = (488-337)/2 = 75 │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │ 检测 L3 contentTop          │
                    │ detect_content_top()        │
                    │ scan_start = max(22+35, 50) │
                    │   = 57 (跳过工具栏区域)      │
                    │ → contentTop = 62           │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │ contentTop > toolbarHeight?  │
                    │ 是 → 重新计算：              │
                    │   actualH = 752-62 = 690    │
                    │   contentWidth = 690×0.462  │
                    │     = 318                   │
                    │   leftBlack = (488-318)/2   │
                    │     = 85                    │
                    │   contentHeight = 318×2532  │
                    │     /1170 = 688             │
                    │   contentBottom = 62+688    │
                    │     = 750 < 752 ✅          │
                    │ 否 → 使用预计算值            │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ 输出三层区域结果     │
                    │ status: OK          │
                    └─────────────────────┘
```

### 12.4 详细实现

#### 12.4.1 `detect_toolbar_height()`

**用途**：检测 Unity GameView 顶部工具栏高度。

**算法**：
1. 从 y=0 开始向下扫描前 50 行
2. 对每一行计算 RGB 三通道的均值
3. 判断是否为"灰色行"（三通道差异 < 30，均值在 100-200 之间）
4. 遇到第一个非灰色行停止
5. 如果未找到，返回默认值 22

**代码**：
```python
def detect_toolbar_height(img_rgb):
    for y in range(min(50, height)):
        row = img_rgb[y, :]
        channel_diff = np.max(row, axis=0) - np.min(row, axis=0)
        row_mean = np.mean(row, axis=0)
        is_gray = (np.mean(channel_diff) < 30) and \
                  (np.mean(row_mean) > 100) and \
                  (np.mean(row_mean) < 200)
        if is_gray:
            toolbar_bottom = y + 1
        else:
            break
    return toolbar_bottom or 22
```

**输出**：`toolbarHeight = 22`

---

#### 12.4.2 `detect_content_top()`

**用途**：检测游戏画面顶部边界，精确找到游戏画面开始的行。

**算法**：
1. `scan_start = max(render_top + 35, 50)` — 安全偏移，跳过 Unity 工具栏
2. 从 `scan_start` 向下扫描
3. 对每一行 y，检查 y 到 y+2 共 3 行
4. 每行在 `contentLeft~contentRight` 范围内计算有效像素比例
5. 有效像素定义：NOT（RGB 通道差异 < 20 且 亮度 < 60）
6. 3 行全部满足有效比例 >= 50%，则 y 为 contentTop

**伪代码**：
```python
def detect_content_top(img_rgb, render_rect, content_left, content_right):
    scan_start = max(render_rect.top + 35, 50)  # 跳过工具栏
    
    for y in range(scan_start, render_bottom - 2):
        ok = 0
        for yy in range(y, y + 3):
            row = img_rgb[yy, content_left:content_right]
            valid = calc_non_toolbar_pixel_ratio(row)
            if valid >= 0.5:
                ok += 1
        if ok == 3:
            return y
    return None
```

**输出**：`contentTop = 62`

---

#### 12.4.3 `calc_non_toolbar_pixel_ratio()`

**用途**：计算一行中游戏内容像素的比例。

**条件**：像素满足以下条件之一即为"有效"（游戏内容）：
- RGB 三通道差异 >= 20（有颜色变化）
- 亮度 >= 60（不是极暗）

```python
channel_diff = np.max(row, axis=1) - np.min(row, axis=1)
brightness = np.mean(row, axis=1)
is_invalid = (channel_diff < 20) & (brightness < 60)
valid_ratio = 1 - (np.sum(is_invalid) / len(row))
```

---

#### 12.4.4 `find_game_content_rect()` 自适应重算逻辑

**核心问题**：预计算的 contentWidth 基于 `render_area_height`，但当 contentTop 偏移后，实际可用高度减少，原 contentWidth 会导致 bottom 溢出。

**解决**：检测到 contentTop > toolbar_height 后，用实际可用高度重算：

```python
if content_top > toolbar_height:
    actual_height = image_height - content_top
    content_width = int(actual_height * target_ratio)
    left_black = (panel_width - content_width) // 2
    content_height = int(content_width * design_height / design_width)
```

**效果**：contentWidth 从 337 调整为 318，contentHeight 从 729 调整为 688，bottom=750 < 752。

---

### 12.5 关键参数

| 参数 | 值 | 说明 |
|------|------|------|
| toolbar_safe_gap | 35 | contentTop 扫描偏移量 |
| min_content_top | 50 | contentTop 最小起始行 |
| valid_ratio_threshold | 0.5 | 有效像素比例阈值 |
| consecutive_rows | 3 | 连续满足条件的行数 |
| channel_diff_threshold | 20 | 像素通道差异阈值 |
| brightness_threshold | 60 | 像素亮度阈值 |
| horizontal_sample_rows | 30 | 水平边界检测采样行数 |
| brightness_min | 15 | 非黑像素亮度下限 |

### 12.6 文件说明

#### `E:\zdcs\AutoSmoke\core_engine\game_content_locator.py`

**用途**：GameContentLocator v2 实现，三层区域模型。

**核心函数**：

| 函数 | 用途 |
|------|------|
| `detect_toolbar_height()` | 检测 Unity 工具栏高度 |
| `detect_content_top()` | 检测游戏画面顶部边界 |
| `calc_non_toolbar_pixel_ratio()` | 计算有效像素比例 |
| `find_game_content_rect()` | 主入口，执行三层检测 |
| `test_locator()` | 测试入口，截图+分析+保存 |

**输出到 config.json**：
```json
{
  "game_content_result": {
    "status": "OK",
    "gameViewPanelRect": {"left": 0, "top": 0, "width": 488, "height": 752},
    "gameRenderAreaRect": {"left": 0, "top": 22, "width": 488, "height": 730},
    "gameContentRect": {"left": 85, "top": 62, "width": 318, "height": 688},
    "scale": {"x": 0.2718, "y": 0.2717},
    "debug_info": {
      "contentLeft": 85,
      "contentRight": 403,
      "contentWidth": 318,
      "detectedContentTop": 62,
      "contentTopScanStart": 57,
      "expectedContentHeight": 688,
      "expectedContentBottom": 750,
      "panelImageHeight": 752,
      "isCaptureTooShort": false,
      "toolbarHeight": 22,
      "renderAreaHeight": 730
    }
  }
}
```

### 12.7 最终坐标

| 区域 | 截图坐标 | 尺寸 |
|------|----------|------|
| GameViewPanel | (0, 0, 488, 752) | 488 × 752 |
| GameRenderArea | (0, 22, 488, 752) | 488 × 730 |
| **GameContent** | **(85, 62, 403, 750)** | **318 × 688** |

**点击坐标转换**：所有后续 UI 点击基于 gameContentRect 换算
```python
# 游戏内坐标 (gx, gy) → 截图坐标
screen_x = content_left + int(gx * scale_x)
screen_y = content_top + int(gy * scale_y)
```

### 12.8 迭代历史

| 轮次 | 问题 | 解决 |
|------|------|------|
| v1 | contentTop 从工具栏开始 | contentTop 图像检测 |
| v2α | contentTop=62 导致 bottom 超界 | 自适应回退到 toolbar_height |
| v2β | 回退后绿色框包含工具栏 | contentTop 偏移后重算 contentWidth |
| v2γ | 水平边界图像检测被工具栏干扰 | 恢复比例计算 + scan_start 偏移 |
| **v2 最终** | 全部通过 | **contentTop=62, bottom=750, scaleX≈scaleY** |

### 12.9 验收标准

- [x] 绿色框顶部从游戏画面顶部开始（y=62）
- [x] 绿色框底部包含完整按钮栏（y=750 < 752）
- [x] 绿色框左右边界不包含黑边（left=85, right=403）
- [x] 输出 game_content_realtime.png（纯游戏内容截图）
- [x] scaleX 与 scaleY 差异 < 1%（0.2718 vs 0.2717）
- [x] 截图不足时能明确输出 GAME_VIEW_CAPTURE_TOO_SHORT
