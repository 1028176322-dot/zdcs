# AutoSmoke - 按用例步骤自动点击方案

## 1. 目标

本方案用于实现：

```text
IDE 导入 Excel 用例
-> 解析每条操作步骤
-> 定位目标元素或坐标
-> 自动点击/等待/断言
-> 记录点击前后证据
-> 输出步骤结果和测试报告
```

最终目标是让测试人员在 IDE 中选择用例文件后，AutoSmoke 能按用例步骤自动执行点击，并判断每一步是否通过。

## 2. 设计边界

后续实现必须遵守：

```text
不修改游戏业务运行过程代码
允许使用 Unity Editor 辅助脚本读取 GameView、分辨率等只读信息
所有功能最终封装到 IDE
坐标、截图、点击、报告均以 gameContentRect 为基准
gameResolution 必须动态读取，不写死 1170x2532
```

## 3. 总体流程

```text
1. IDE 导入 Excel 用例
2. 用例解析器解析步骤文本
3. 执行前刷新定位状态
4. 获取 gameContentRect 和 gameResolution
5. 构建 CoordinateMapper
6. 按步骤定位目标
7. 执行点击/等待/断言
8. 采集点击前后截图、日志、UI 树
9. 判断步骤结果
10. 汇总生成报告
```

## 4. 用例步骤格式建议

### 4.1 支持的动作

第一阶段建议支持：

```text
点击
等待
断言存在
断言不存在
截图
返回
```

第二阶段扩展：

```text
长按
滑动
输入
拖拽
循环点击
条件等待
```

### 4.2 推荐写法

```text
点击 text("使用")
点击 normalized(0.5,0.95)
点击 design(585,2400)
点击 template("use_button")
等待 2 秒
断言存在 text("联盟迁城")
断言不存在 text("加载中")
截图
```

### 4.3 不推荐写法

```text
点击屏幕右下角
点击第三个按钮
点击 Button_1
点击坐标 515,763
```

原因：

```text
屏幕坐标受分辨率、窗口位置、副屏影响
节点名可能不稳定
顺序型描述容易因 UI 变化失效
```

## 5. 步骤解析器

建议新增模块：

```text
E:/zdcs/AutoSmoke/case_step_parser.py
```

### 5.1 输入

来自 Excel 的步骤文本：

```text
点击 text("使用")
等待 2 秒
断言存在 text("联盟迁城")
```

### 5.2 输出结构

```json
{
  "action": "click",
  "target": {
    "type": "text",
    "value": "使用"
  },
  "raw": "点击 text(\"使用\")"
}
```

### 5.3 支持解析类型

```text
text("xxx")          OCR 文本定位
template("xxx")      模板匹配定位
normalized(x,y)      归一化坐标
design(x,y)          设计分辨率坐标
content(x,y)         GameContent 内坐标
testId("xxx")        后续 Unity 元数据定位
```

## 6. 点击目标定位策略

点击目标按优先级执行：

```text
1. testId 定位
2. text/OCR 定位
3. template 模板匹配
4. normalized 坐标
5. design 坐标
6. content 坐标
7. screen 坐标，仅调试允许
```

### 6.1 text 定位

流程：

```text
1. 截取 game_content_screenshot
2. OCR 识别文字
3. 找到目标文本矩形
4. 取中心点
5. game_content 坐标 -> screen 坐标
6. 点击
```

### 6.2 template 定位

流程：

```text
1. 截取 game_content_screenshot
2. 使用模板匹配
3. 找到最高分区域
4. 判断 score 是否超过阈值
5. 取中心点点击
```

### 6.3 normalized 定位

流程：

```text
normalized(x,y)
-> design 坐标
-> screen 坐标
-> 点击
```

适合长期用例，因为它比固定 design 坐标更抗分辨率变化。

### 6.4 design 定位

design 坐标必须带有基准分辨率：

```json
{
  "coordinateType": "design",
  "x": 585,
  "y": 2400,
  "baseResolution": [1170, 2532]
}
```

如果当前分辨率发生变化：

```text
允许自动缩放：先转 normalized，再映射当前分辨率
不允许自动缩放：阻断并标记 RESOLUTION_CHANGED_BLOCKED
```

## 7. 执行前检查

每条用例执行前必须检查：

```text
Unity/GameView 是否可用
gameContentRect 是否有效
gameResolution 是否已读取
CoordinateMapper 是否可构建
scaleX / scaleY 是否一致
截图能力是否可用
点击模块是否可用
```

如果失败：

```text
该用例标记 ERROR
不继续执行点击
报告中记录失败原因
```

## 8. 点击执行模式

AutoSmoke 需要支持多种点击模式，供 IDE 按项目情况选择。

```text
1. real_mouse
   使用系统鼠标真实点击 Unity GameView。

2. poco_click
   通过 Poco 节点执行点击。

3. unity_inject
   通过 Unity Editor 辅助脚本向 Unity EventSystem 注入点击。
```

默认建议：

```text
第一阶段使用 real_mouse 跑通完整链路。
第二阶段增加 unity_inject 作为高级点击模式。
Poco UI 树可信时再使用 poco_click。
```

### 8.1 real_mouse 模式

执行链路：

```text
目标定位
-> game_content 坐标
-> CoordinateMapper 转 screen 坐标
-> Windows API 移动鼠标并点击
```

优点：

```text
不修改游戏代码
最接近真实用户操作
能验证真实点击链路
```

限制：

```text
鼠标会被占用
Unity 窗口需要可见
窗口被遮挡可能失败
多屏/窗口移动后必须重新定位
```

### 8.2 poco_click 模式

执行链路：

```text
通过 Poco dump 找到节点
-> poco(node).click()
```

优点：

```text
不占用鼠标
能基于 UI 树执行
```

限制：

```text
依赖 Poco UI 树质量
clickable/type 不可信时容易失败
主城/大地图对象不一定在 UI 树中
```

### 8.3 unity_inject 模式

`unity_inject` 是通过 Unity Editor 辅助脚本完成点击注入，不移动系统鼠标。

设计边界：

```text
允许新增 Assets/Editor/AutoSmokeClickInjector.cs
只在 Unity Editor 中运行
不进入正式构建包
不修改游戏业务逻辑
不修改按钮/界面运行过程代码
```

执行链路：

```text
IDE/Python 写入 click_request.json
-> Unity Editor 辅助脚本监听请求
-> 转换 design/normalized/game_content 坐标到 Unity Screen 坐标
-> EventSystem.RaycastAll 命中 UI 对象
-> ExecuteEvents 派发 pointerDown/pointerUp/pointerClick
-> 写回 click_result.json
```

请求文件示例：

```json
{
  "action": "click",
  "coordinateType": "design",
  "x": 585,
  "y": 2400,
  "gameResolution": [1170, 2532],
  "requestId": "click_001",
  "timestamp": "2026-06-12T18:00:00"
}
```

结果文件示例：

```json
{
  "requestId": "click_001",
  "status": "OK",
  "hitObject": "Canvas/BagPanel/Button_Use",
  "screenPosition": [585, 132],
  "message": "pointerClick executed"
}
```

未命中示例：

```json
{
  "requestId": "click_001",
  "status": "NO_HIT",
  "message": "EventSystem.RaycastAll returned empty"
}
```

Unity 侧核心伪代码：

```csharp
var pointer = new PointerEventData(EventSystem.current)
{
    position = screenPosition,
    button = PointerEventData.InputButton.Left
};

var results = new List<RaycastResult>();
EventSystem.current.RaycastAll(pointer, results);

if (results.Count > 0)
{
    var target = results[0].gameObject;
    ExecuteEvents.Execute(target, pointer, ExecuteEvents.pointerDownHandler);
    ExecuteEvents.Execute(target, pointer, ExecuteEvents.pointerUpHandler);
    ExecuteEvents.Execute(target, pointer, ExecuteEvents.pointerClickHandler);
}
```

坐标注意事项：

```text
截图坐标通常左上角为 (0,0)
Unity Screen 坐标通常左下角为 (0,0)
需要校验 y 轴是否反转
screenY = Screen.height - yFromTop
```

优点：

```text
不占用真实鼠标
Unity 窗口不一定需要前台
不受 Windows 多屏鼠标坐标影响
能返回实际命中的 GameObject
诊断能力强
```

限制：

```text
主要适合 UGUI/EventSystem UI
3D 场景对象需要 PhysicsRaycaster 或自定义 Raycast
自研输入系统需要额外适配
需要 Unity Editor 辅助脚本，属于低侵入方案
```

## 9. 单步骤执行流程

以 `点击 text("使用")` 为例：

```text
1. 解析步骤
2. 刷新当前定位状态
3. 截取 before 图片
4. OCR 找到“使用”
5. 计算目标中心点
6. 转换为 screen 坐标
7. 点击前安全校验
8. 执行点击
9. 等待稳定时间
10. 截取 after 图片
11. 计算截图差异
12. 采集日志/UI 树
13. 生成 step_result
```

不同点击模式的第 8 步不同：

```text
real_mouse：调用 Windows API 点击
poco_click：调用 Poco click
unity_inject：写入 click_request.json 并等待 click_result.json
```

## 10. 点击安全校验

执行点击前必须校验：

```text
目标点是否在 gameContentRect 内
目标点是否在虚拟屏幕范围内
gameResolution 是否与 mapper 一致
是否命中危险操作
是否处于 Loading/遮罩状态
当前截图是否为空页面
```

危险操作建议黑名单：

```text
充值
购买
删除
退出登录
消耗钻石
确认支付
解散
重置
```

命中危险操作时：

```text
不点击
标记 BLOCKED_DANGEROUS_ACTION
报告中保留目标截图
```

## 11. 步骤结果判定

每一步执行后输出：

```text
PASS
FAIL
BUG
ERROR
BLOCKED
SKIPPED
WARNING
```

### 11.1 点击类步骤判定

```text
点击成功发出 + 画面变化明显       -> PASS 或 CLICK_CHANGED
点击成功发出 + 画面无变化         -> WARNING 或 FAIL
目标找不到                       -> FAIL
坐标越界                         -> ERROR
危险操作被拦截                   -> BLOCKED
点击后出现异常日志/崩溃/空页面    -> BUG
```

### 11.2 断言类步骤判定

```text
断言存在且找到目标       -> PASS
断言存在但未找到目标     -> FAIL
断言不存在且未找到目标   -> PASS
断言不存在但找到目标     -> FAIL
```

## 12. step_result 数据结构

```json
{
  "caseId": "TC_001",
  "stepIndex": 1,
  "rawStep": "点击 text(\"使用\")",
  "action": "click",
  "target": {
    "type": "text",
    "value": "使用"
  },
  "location": {
    "coordinateType": "game_content",
    "x": 158,
    "y": 660
  },
  "mapped": {
    "coordinateType": "screen",
    "x": 515,
    "y": 763
  },
  "gameResolution": [1170, 2532],
  "gameContentRect": [86, 62, 317, 686],
  "result": "PASS",
  "clickMode": "real_mouse",
  "diffRatio": 0.034,
  "beforeScreenshot": "runs/run_x/screenshots/before_001.png",
  "afterScreenshot": "runs/run_x/screenshots/after_001.png",
  "logs": "runs/run_x/logs/step_001.log",
  "message": "点击后画面发生变化"
}
```

`unity_inject` 模式下可额外记录：

```json
{
  "clickMode": "unity_inject",
  "injectResult": {
    "status": "OK",
    "hitObject": "Canvas/BagPanel/Button_Use",
    "message": "pointerClick executed"
  }
}
```

## 13. 用例执行器

建议新增模块：

```text
E:/zdcs/AutoSmoke/case_step_executor.py
```

职责：

```text
加载用例
解析步骤
调用定位/截图/点击/OCR/模板模块
按顺序执行步骤
处理失败短路
生成 step_result
汇总 case_result
```

### 13.1 失败短路策略

建议默认：

```text
当前步骤 FAIL/BUG/ERROR 后，终止当前用例
继续执行下一条用例
```

可配置：

```text
fail_fast=true/false
continue_on_warning=true/false
```

## 14. IDE 封装方式

IDE 中需要提供：

```text
用例导入
步骤预览
步骤解析结果展示
单步执行
从当前步骤继续
整条用例执行
批量执行
暂停/继续/停止
执行日志
点击前后截图对比
失败原因查看
报告导出
点击模式选择：real_mouse / poco_click / unity_inject
```

### 14.1 用例步骤预览

展示：

```text
原始步骤文本
解析后的 action
定位方式
目标值
预计点击坐标
风险标记
点击模式
```

### 14.2 单步调试

支持：

```text
只定位不点击
显示目标框
执行点击
查看 before/after
查看 diff
查看 OCR/模板识别结果
查看 unity_inject 命中对象
```

## 15. 不修改游戏代码策略

该方案不需要修改游戏业务运行过程代码。

允许：

```text
使用 Unity Editor 辅助脚本读取 GameView/分辨率
使用 Poco dump
使用截图/OCR/模板匹配
使用外部鼠标点击
使用 Unity Editor 辅助脚本注入 EventSystem 点击
```

不允许：

```text
修改按钮逻辑
修改 UI 流程
修改业务状态
修改正式运行时代码
```

## 16. 验收标准

### 16.1 基础点击验收

```text
能执行 点击 normalized(x,y)
能执行 点击 design(x,y)
能执行 点击 text("使用")
每次点击都有 before/after 截图
```

### 16.2 用例步骤验收

```text
Excel 中连续 3 个步骤可顺序执行
步骤失败后能标记失败原因
下一条用例不受上一条失败影响
```

### 16.3 分辨率适配验收

```text
GameView 拉伸后重新定位仍可点击
gameResolution 变化后能重建 mapper
旧 OCR/模板坐标不会被复用
```

### 16.4 点击模式验收

```text
real_mouse 模式能真实点击“使用”按钮
unity_inject 模式能返回 hitObject
unity_inject 未命中时返回 NO_HIT
IDE 中可选择点击模式
不同点击模式结果均写入 step_result
```

### 16.5 报告验收

```text
每步有 result
每步有截图证据
失败步骤有原因
BUG 步骤有日志/截图/复现路径
```

## 17. 实施优先级

```text
1. case_step_parser.py
2. case_step_executor.py
3. 点击 normalized/design 步骤
4. 点击 text/template 步骤
5. click_mode 抽象：real_mouse / poco_click / unity_inject
6. unity_inject Editor 辅助脚本
7. 断言存在/不存在
8. IDE 单步调试面板
9. 批量用例执行
10. 报告中心接入
```

## 18. 结论

按用例步骤自动点击的核心不是“点一下鼠标”，而是：

```text
解析步骤
定位目标
安全校验
执行点击
结果判定
证据留存
报告输出
点击模式可切换
```

完成这条链路后，AutoSmoke 就可以从手动调试工具进入真正的自动化用例执行阶段，并最终封装进 IDE。

---

## 19. 实施完成总结（2026-06-12）

### 19.1 交付物（10 优先级全部完成 ✅）

| 优先级 | 模块 | 文件 | 状态 |
|:------:|------|------|:----:|
| 1 | 步骤解析器 | `case_step_parser.py` | ✅ |
| 2 | 步骤执行器 | `case_step_executor.py` | ✅ |
| 3-4 | 坐标/文本定位 | 复用已有 `coordinate_mapper` / `game_content_vision` | ✅ 已接入 |
| 5 | click_mode 抽象 | `click_mode.py` | ✅ 三种模式 |
| 6 | unity_inject 脚本 | `tools/AutoSmokeClickInjector.cs` | ✅ C# 脚本就绪 |
| 7 | 断言完善 | executor 增强 | ✅ 重试 + 超时 |
| 8 | IDE 调试面板 | `debug_panel.py` | ✅ Flask 网页 |
| 9 | 批量用例执行 | `batch_runner.py` | ✅ Excel + 字典 |
| 10 | 报告中心 | `report_center.py` | ✅ HTML 报告 |

### 19.2 完整模块依赖

| 层 | 模块 | 用途 | 状态 |
|:--:|------|------|:----:|
| 定位 | `game_content_locator.py` | Game 视图三层定位 | ✅ |
| — | `locate_game_area_smart.py` | GameView 坐标定位 | ✅ |
| 一 | `resolution_manager.py` | 动态分辨率读取 | ✅ |
| 二 | `coordinate_mapper.py` | 6 种坐标互转 + 副屏修正 | ✅ |
| 三 | `screenshot_game_content.py` | 纯 gameContent 截图 | ✅ |
| 四 | `click_game_content.py` | 4 种点击类型 + before/after | ✅ |
| 五 | `screenshot_diff.py` | 截图差异 + 高亮图 | ✅ |
| 六 | `game_content_vision.py` | OCR / 模板匹配 | ✅ |
| 用例 | `case_step_parser.py` | 步骤文本解析 | ✅ |
| — | `case_step_executor.py` | 步骤执行器 | ✅ |
| — | `click_mode.py` | 三种点击模式 | ✅ |
| — | `debug_panel.py` | Flask IDE 调试面板 | ✅ |
| — | `batch_runner.py` | 批量用例执行 | ✅ |
| — | `report_center.py` | HTML 报告输出 | ✅ |
| — | `tools/AutoSmokeClickInjector.cs` | Unity EventSystem 注入 | ✅ 待部署 |

### 19.3 执行链路验证

```text
输入步骤文本
  → CaseStepParser 解析为结构化动作
    → CaseStepExecutor 按顺序执行
      → coordinate_mapper 坐标转换
        → ClickMode 点击（real_mouse / poco_click / unity_inject）
          → click_game_content 执行点击
            → screenshot_diff 差异判定
              → batch_runner 批量汇总
                → report_center HTML 报告
```

实测验证：
```text
步骤: 等待 1 秒        → PASS
步骤: 截图            → PASS
步骤: 点击 OCR不存在   → FAIL (短路)
步骤: 后续步骤        → SKIPPED
```
