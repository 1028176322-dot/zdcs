# AutoSmoke UI_DebugGraphic 误匹配与高亮异常修复方案

## 1. 问题现象

当前在 IDE 中选择 `UI_DebugGraphic` 相关元素后，高亮预览出现异常。

截图表现为：

```text
中间高亮图不是完整游戏界面
而是显示了局部放大的背包界面内容
看不到明确红框
右侧元素显示为 runtime_matched
```

当前选中元素类似：

```text
UI_DebugGraphic-查看/选择道具-页签
pageId = UI_DebugGraphic
elementType = tab
reviewStatus = runtime_matched
```

但当前真实游戏界面是：

```text
背包界面
```

这说明系统把 Debug 面板候选错误匹配到了当前背包运行态节点。

## 2. 已确认的异常数据

抽样看到类似映射数据：

```json
{
  "pageId": "UI_DebugGraphic",
  "elementType": "tab",
  "reviewStatus": "runtime_matched",
  "runtimePath": "ResItem_1",
  "runtimeMatch": {
    "status": "matched",
    "matchScore": 1.0,
    "matchLevel": "P0",
    "runtimePath": "ResItem_1",
    "visible": true,
    "interactable": true,
    "screenRect": [-1, 5, 0, 4]
  }
}
```

异常点：

```text
1. pageId=UI_DebugGraphic，但当前真实页面不是 UI_DebugGraphic。
2. runtimePath=ResItem_1，看起来属于背包/资源项，不属于 DebugGraphic。
3. screenRect=[-1,5,0,4] 是无效坐标。
4. matchScore=1.0 不合理，pageId 不一致时不应满分。
5. 该元素被标记 runtime_matched，导致前端允许进入高亮/确认流程。
```

## 3. 根因分析

### 3.1 Debug UI 没有被排除

`UI_DebugGraphic` 路径：

```text
Assets/Framework/Debug/Resources/UI/GraphicDebug/UI_DebugGraphic.prefab
```

明显属于：

```text
Debug UI
工具面板
非玩家业务界面
```

它不应该默认进入业务元素审核主流程。

正确处理：

```text
elementType = debug_ui
priority = LOW
excludeReason = debug_ui
默认隐藏
不参与当前页业务匹配
不参与严格有效点击
```

### 3.2 runtime_match 缺少 pageId 强约束

当前运行态匹配可能用了宽泛规则，例如：

```text
nodeName
text
component
spriteName
```

但没有强制校验：

```text
候选 pageId 是否与当前 pageId 一致
候选是否允许跨页匹配
候选是否属于 Debug UI
```

导致：

```text
UI_DebugGraphic 草稿
错误匹配到 BagPanel 当前页节点 ResItem_1
```

### 3.3 screenRect 缺少有效性校验

异常坐标：

```text
[-1, 5, 0, 4]
```

如果按 `[x,y,width,height]` 理解：

```text
x=-1
y=5
width=0
height=4
```

无效。

如果按 `[x1,y1,x2,y2]` 理解：

```text
x1=-1
y1=5
x2=0
y2=4
```

也无效，因为：

```text
x2 <= x1
y2 <= y1
```

这种坐标必须判为：

```text
invalid_rect
```

不能进入：

```text
runtime_matched
visual_confirmed
click_confirmed
```

### 3.4 screenRect 格式混用

当前 `/api/mapping/highlight` 中 list 类型坐标被直接当成：

```text
[x1, y1, x2, y2]
```

代码类似：

```python
draw.rectangle(screen_rect[:4], outline="red", width=3)
```

但 Unity 侧很多地方更推荐导出：

```text
{x, y, width, height}
```

如果数组格式混用：

```text
[x, y, width, height]
```

就会画错框。

### 3.5 前端高亮预览显示方式不正确

后端 `/api/mapping/highlight` 当前逻辑是：

```text
打开整张截图
画框
保存整张高亮图
```

没有裁剪图片。

用户看到“局部放大”的原因很可能是前端容器显示图片时没有：

```css
object-fit: contain;
max-width: 100%;
max-height: 100%;
```

导致大图以原始尺寸塞进小容器，只显示了局部。

## 4. 修复目标

修复后应达到：

```text
UI_DebugGraphic 默认不参与业务映射审核
Debug UI 不会误匹配当前业务界面
pageId 不一致时不能高分匹配
无效 screenRect 不能进入视觉确认
高亮图显示完整游戏界面
坐标格式统一
错误原因可在 IDE 中明确显示
```

## 5. 修复方案一：Debug UI 排除

### 5.1 在 enhanced 生成阶段识别 Debug UI

识别规则：

```text
prefabPath/name/path 包含：
Debug
debug
UI_Debug
GraphicDebug
GM
Console
TestPanel
Dev
Editor
```

示例：

```text
Assets/Framework/Debug/Resources/UI/GraphicDebug/UI_DebugGraphic.prefab
```

应标记：

```json
{
  "elementType": "debug_ui",
  "priority": "LOW",
  "excludeReason": "debug_ui",
  "businessCandidate": false,
  "allowRuntimeMatch": false
}
```

### 5.2 IDE 默认隐藏 Debug UI

左侧列表默认不显示：

```text
elementType=debug_ui
excludeReason=debug_ui
priority=LOW
```

除非用户勾选：

```text
包含调试UI
```

### 5.3 Debug UI 不进入严格有效点击

有效点击分析中：

```text
if excludeReason == debug_ui:
    strictEffectiveClickable = false
    keyEffectiveClickable = false
```

## 6. 修复方案二：runtime_match 增加 pageId 强约束

### 6.1 当前页上下文

运行态匹配前必须先得到：

```text
currentPageId
currentSceneId
contextType
```

例如：

```json
{
  "currentPageId": "BagPanel",
  "contextType": "panel"
}
```

### 6.2 匹配前过滤候选

候选元素进入匹配前必须满足：

```text
draft.pageId == currentPageId
或 draft.pageId in allowedGlobalPages
或 draft.allowCrossPageMatch=true
```

Debug UI 默认：

```text
allowRuntimeMatch=false
```

所以：

```text
UI_DebugGraphic 不允许匹配 BagPanel 当前页。
```

### 6.3 pageId 不一致直接失败

建议规则：

```python
if draft.pageId and current_page_id and draft.pageId != current_page_id:
    if not draft.get("allowCrossPageMatch"):
        return not_matched("page_mismatch")
```

失败结果：

```json
{
  "matched": false,
  "reason": "page_mismatch",
  "draftPageId": "UI_DebugGraphic",
  "currentPageId": "BagPanel"
}
```

### 6.4 matchScore 扣分规则

如果不直接失败，也必须大幅扣分：

```text
pageId 一致：+0.20
pageId 不一致：-0.80
debug_ui：-1.00
invalid_rect：-0.50
```

因此 pageId 不一致不可能得到：

```text
matchScore=1.0
```

## 7. 修复方案三：screenRect 有效性校验

### 7.1 统一 Rect 格式

建议统一为对象：

```json
{
  "x": 120,
  "y": 300,
  "width": 80,
  "height": 60
}
```

不建议继续混用：

```text
[x1,y1,x2,y2]
[x,y,width,height]
```

如果必须兼容数组，必须加字段说明：

```json
{
  "screenRect": [120, 300, 80, 60],
  "screenRectFormat": "xywh"
}
```

### 7.2 Rect 校验函数

后端增加：

```python
def normalize_rect(rect, fmt=None):
    if isinstance(rect, dict):
        x = rect.get("x", 0)
        y = rect.get("y", 0)
        w = rect.get("width", 0)
        h = rect.get("height", 0)
        return {"x": x, "y": y, "width": w, "height": h}

    if isinstance(rect, list) and len(rect) >= 4:
        a, b, c, d = rect[:4]
        if fmt == "xywh":
            return {"x": a, "y": b, "width": c, "height": d}
        if fmt == "xyxy":
            return {"x": a, "y": b, "width": c - a, "height": d - b}

        # 自动判断：如果 c>a 且 d>b，更可能是 xyxy；否则按 xywh 尝试
        if c > a and d > b:
            return {"x": a, "y": b, "width": c - a, "height": d - b}
        return {"x": a, "y": b, "width": c, "height": d}

    return None
```

校验：

```python
def is_valid_rect(r, image_width, image_height):
    if not r:
        return False
    if r["width"] <= 4 or r["height"] <= 4:
        return False
    if r["x"] < 0 or r["y"] < 0:
        return False
    if r["x"] >= image_width or r["y"] >= image_height:
        return False
    if r["x"] + r["width"] <= 0 or r["y"] + r["height"] <= 0:
        return False
    return True
```

### 7.3 无效 Rect 的处理

如果无效：

```text
runtimeMatch.status = not_matched
runtimeMatch.reason = invalid_rect
reviewStatus 不得设为 runtime_matched
hasHighlightRect = false
visual_confirmed 禁用
click_confirmed 禁用
```

## 8. 修复方案四：高亮接口修正

当前接口：

```text
POST /api/mapping/highlight
```

需要修正：

```text
1. 支持 draftPath 自动读取 runtimeMatch.screenRect。
2. 使用 normalize_rect 统一坐标。
3. 校验 rect 有效性。
4. 按 x,y,width,height 画框。
5. 返回 rect 校验结果。
```

绘制逻辑：

```python
r = normalize_rect(screen_rect, fmt=screen_rect_format)
if not is_valid_rect(r, img.width, img.height):
    return jsonify({
        "success": False,
        "error": "invalid_rect",
        "rect": r,
        "imageSize": [img.width, img.height]
    })

draw.rectangle(
    [r["x"], r["y"], r["x"] + r["width"], r["y"] + r["height"]],
    outline="red",
    width=3
)
```

返回：

```json
{
  "success": true,
  "highlightImage": "...",
  "normalizedRect": {
    "x": 120,
    "y": 300,
    "width": 80,
    "height": 60
  },
  "imageSize": [1170, 2532],
  "rectSource": "runtimeMatch"
}
```

## 9. 修复方案五：前端高亮显示修正

中间预览区域图片必须完整显示。

### 9.1 HTML

```html
<div id="rPreview" class="mapping-preview">
  <div id="rPreviewText">选择草稿</div>
  <img id="rPreviewImg" style="display:none;">
</div>
```

### 9.2 CSS

```css
.mapping-preview {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #fafafa;
}

.mapping-preview img {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  display: block;
}
```

这样前端会显示整张高亮图，而不是只露出左上局部。

### 9.3 前端错误显示

如果高亮失败：

```text
invalid_rect
page_mismatch
debug_ui
screenshot_not_found
```

中间区域显示中文原因：

```text
无法生成高亮：坐标无效
screenRect=[-1,5,0,4]
该元素可能被误匹配，请重新匹配或忽略。
```

## 10. 修复方案六：当前页匹配结果显示

UI_DebugGraphic 这种元素在背包界面应显示为：

```text
状态：未匹配
原因：debug_ui / page_mismatch
当前页：BagPanel
元素页：UI_DebugGraphic
```

而不是：

```text
runtime_matched
```

左侧列表增加列或标签：

```text
排除原因
匹配原因
当前页
元素页
```

## 11. 推荐修复顺序

### P0：必须先修

```text
1. Debug UI 识别并默认排除。
2. runtime_match 增加 pageId 强约束。
3. invalid screenRect 不能标 runtime_matched。
4. screenRect 统一 normalize + validate。
```

### P1：紧接着修

```text
5. /api/mapping/highlight 使用 normalize_rect。
6. 高亮失败返回明确原因。
7. 前端高亮图 object-fit: contain。
8. 中间区域显示完整图片。
```

### P2：体验优化

```text
9. 左侧增加 Debug UI 筛选。
10. 左侧增加 page_mismatch / invalid_rect 排除筛选。
11. 详情区显示“当前页 vs 元素页”。
12. 支持手动把 Debug UI 标记为永久忽略。
```

## 12. 验收标准

### 12.1 Debug UI 排除验收

```text
UI_DebugGraphic 默认不显示在业务审核列表。
勾选“包含调试UI”后才显示。
UI_DebugGraphic 不参与严格有效点击。
```

### 12.2 pageId 匹配验收

在当前页面为 BagPanel 时：

```text
pageId=UI_DebugGraphic 的元素不能匹配到 BagPanel 节点。
匹配结果应为 page_mismatch。
matchScore 不得为 1.0。
```

### 12.3 Rect 校验验收

以下坐标必须判无效：

```text
[-1, 5, 0, 4]
[0, 4, -1, 5]
{x:-1,y:5,width:0,height:4}
```

无效时：

```text
不能 runtime_matched
不能 visual_confirmed
不能 click_confirmed
```

### 12.4 高亮图验收

选择正常业务元素，例如：

```text
背包-使用按钮
```

应显示：

```text
完整游戏截图
红框框中使用按钮
图片不被裁切成局部放大图
```

### 12.5 错误显示验收

选择 UI_DebugGraphic 误匹配元素时，应显示：

```text
无法高亮：page_mismatch / debug_ui / invalid_rect
```

而不是显示错误局部图。

## 13. 最终效果

修复前：

```text
UI_DebugGraphic 被误匹配到背包元素
screenRect 无效但仍 runtime_matched
高亮图显示异常局部
用户可能误以为该元素可确认
```

修复后：

```text
UI_DebugGraphic 默认排除
pageId 不一致直接匹配失败
无效坐标不能生成高亮
高亮图完整显示
用户只能确认真实当前页业务元素
```

## 14. 结论

这个问题的本质不是单纯高亮图片显示问题，而是：

```text
Debug UI 候选进入了业务审核流程
运行态匹配缺少当前页上下文约束
无效坐标没有被拦截
前端高亮图显示方式不完整
```

必须同时修：

```text
候选过滤
匹配评分
坐标校验
高亮绘制
前端预览
```

否则即使高亮图显示正常，也仍然可能把错误元素确认进正式映射。
