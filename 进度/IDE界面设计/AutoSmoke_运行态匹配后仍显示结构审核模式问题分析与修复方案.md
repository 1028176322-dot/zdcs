# AutoSmoke 运行态匹配后仍显示结构审核模式问题分析与修复方案

## 1. 问题现象

当前 IDE 页面显示：

```text
匹配完成：3584/10759
已匹配：1385冲突
```

说明运行态匹配流程已经执行，并且后端确实产出了匹配统计。

但是在用户点击某个草稿元素后，中间和右侧仍显示：

```text
当前为结构审核模式
来自 enhanced_ui_tree.json
没有运行态截图和 screenRect
可以进行结构确认，关键元素后续需要点击确认
```

界面表现为：

```text
全局看起来已经匹配完成
单个元素详情仍然像未匹配
中间高亮区域没有显示截图高亮
右侧没有进入运行态/视觉审核模式
视觉确认按钮可能不可用或没有依据
```

这会导致用户无法判断：

```text
这个元素到底有没有实时匹配成功？
匹配到 Unity 当前界面里的哪个节点？
它在截图上在哪里？
能不能视觉确认？
能不能点击确认？
```

## 2. 核心结论

这个问题不是“运行态匹配完全失败”。

更准确地说是：

```text
运行态匹配结果已经有了，
但匹配结果没有完整写回单个元素，
或前端没有把 runtimeMatch 当成视觉审核依据使用，
或当前选中的元素并不是已匹配元素。
```

因此问题分三层：

```text
1. 列表层：全局匹配完成，但左侧仍混合显示未匹配元素。
2. 数据层：runtimeMatch 没有同步成详情页需要的 screenRect/screenshotRef/hasScreenshot。
3. 视图层：选中元素后没有自动调用 highlight 接口，中间区域仍显示静态结构审核文案。
```

## 3. 当前代码相关位置

### 3.1 前端详情渲染

文件：

```text
E:\zdcs\AutoSmoke\IDE\debug_panel.py
```

函数：

```text
shDraft(p)
```

当前判断是否有截图的逻辑类似：

```javascript
var hasImg = !!((data.screenshotRef && String(data.screenshotRef).trim()) || data.hasScreenshot);
```

问题：

```text
只看顶层 screenshotRef / hasScreenshot。
没有把 runtimeMatch.screenRect 算作可高亮依据。
没有把 current_runtime_state.screenshotPath 算作当前截图来源。
```

所以即使元素已经有：

```json
{
  "runtimeMatch": {
    "status": "matched",
    "screenRect": {...}
  }
}
```

只要顶层没有：

```text
screenshotRef
hasScreenshot
```

前端仍会显示：

```text
当前为结构审核模式
```

### 3.2 运行态匹配接口

文件：

```text
E:\zdcs\AutoSmoke\IDE\debug_panel.py
```

接口：

```text
POST /api/mapping/runtime_match
```

当前逻辑大致是：

```python
for r in result.get("results", []):
    if r.get("matched") and r.get("matchScore", 0) >= 0.85:
        path = r.get("draftPath", "")
        m = mgr.get(path)
        if m:
            m["reviewStatus"] = "runtime_matched"
            m["sourceLevel"] = "L2"
            m["runtimeMatch"] = {
                "status": "matched",
                "matchScore": r.get("matchScore", 0),
                "matchLevel": r.get("matchLevel", ""),
                "runtimePath": r.get("runtimePath", ""),
                "instanceId": r.get("instanceId", 0),
                "visible": r.get("visible", False),
                "interactable": r.get("interactable", False),
                "screenRect": r.get("screenRect", []),
                "matchedAt": ...
            }
            mgr.upsert(path, m)
```

问题：

```text
只写了 runtimeMatch。
没有同步写顶层 screenRect。
没有同步写顶层 runtimePath。
没有同步写 hasHighlightRect。
没有同步写 hasRuntimeMatch。
没有同步写 screenshotRef。
```

因此前端旧逻辑无法识别它已经具备视觉审核条件。

### 3.3 截图高亮接口

文件：

```text
E:\zdcs\AutoSmoke\IDE\debug_panel.py
```

接口：

```text
POST /api/mapping/highlight
```

当前已有能力：

```text
读取当前截图
根据 screenRect 画红框
输出 highlightImage
```

问题：

```text
前端选中草稿后没有自动调用该接口。
中间区域没有 img 容器更新 highlightImage。
```

所以即使接口存在，页面也不会自动从“结构审核模式”变成“截图高亮模式”。

## 4. 根因分析

### 4.1 根因一：全局匹配统计与单元素状态混在一起

顶部显示：

```text
匹配完成：3584/10759
```

这只是全局统计。

它不代表当前左侧列表中每一条都是：

```text
runtime_matched
```

当前左侧仍可能混合显示：

```text
auto_draft
structure_confirmed
runtime_matched
rejected
ignored
```

所以用户点击的 `ctrl面板`、`ResetButton` 等元素，可能根本不是已匹配元素。

必须提供明确筛选：

```text
已匹配
未匹配
匹配冲突
当前页已匹配
```

### 4.2 根因二：runtimeMatch 没有提升为视觉审核字段

详情页判断视觉审核条件时，当前只看：

```text
screenshotRef
hasScreenshot
```

但是运行态匹配带来的关键字段在：

```text
runtimeMatch.screenRect
runtimeMatch.runtimePath
runtimeMatch.visible
runtimeMatch.interactable
```

因此要么后端同步字段，要么前端识别 runtimeMatch。

最好两边都做。

### 4.3 根因三：没有“运行态匹配模式”

当前详情面板只有两类显示：

```text
结构审核模式
有页面截图，可视觉确认
```

缺少中间态：

```text
运行态已匹配，但未生成高亮图
运行态已匹配，已有 screenRect，可生成高亮
运行态已匹配，但缺少 screenRect，只能点击确认/结构确认
```

### 4.4 根因四：中间高亮区域是静态区域

当前中间区域默认文案类似：

```text
当前为结构审核模式
选择草稿后显示详情
```

它没有根据选中元素动态切换为：

```text
运行态匹配信息
截图高亮
冲突候选列表
无截图原因
```

## 5. 正确的状态显示逻辑

单个元素详情页应该按以下状态判断。

### 5.1 未匹配

条件：

```text
runtimeMatch 不存在
或 runtimeMatch.status != matched
```

显示：

```text
结构审核模式
该元素来自 enhanced_ui_tree.json
尚未匹配到 Unity 当前实时界面
可进行结构确认，但不能视觉确认和点击确认
```

允许操作：

```text
结构确认
重新匹配
忽略
拒绝
```

### 5.2 已匹配但无坐标

条件：

```text
runtimeMatch.status == matched
但 runtimeMatch.screenRect 为空
```

显示：

```text
运行态已匹配
runtimePath: xxx
matchScore: xxx
visible: true/false
interactable: true/false
缺少 screenRect，暂不能截图高亮
```

允许操作：

```text
结构确认
测试点击
重新刷新 UI 树
```

不允许：

```text
视觉确认
```

### 5.3 已匹配且有坐标，但无截图

条件：

```text
runtimeMatch.status == matched
runtimeMatch.screenRect 有效
但没有当前截图
```

显示：

```text
运行态已匹配
已有 screenRect
当前缺少截图，请刷新截图或调用 Unity 直出截图
```

允许操作：

```text
刷新截图
测试点击
```

不允许：

```text
视觉确认
```

### 5.4 已匹配且有坐标和截图

条件：

```text
runtimeMatch.status == matched
runtimeMatch.screenRect 有效
当前截图存在
```

显示：

```text
运行态已匹配
截图高亮可查看
可进行视觉确认
可进行测试点击
```

允许操作：

```text
视觉确认
测试点击
点击确认
```

### 5.5 已点击确认

条件：

```text
clickVerification.status == passed
reviewStatus == click_confirmed
```

显示：

```text
点击已确认
命中对象：xxx
事件接收匹配：是
点击后页面/状态：xxx
```

允许操作：

```text
加入正式自动点击
重新验证
查看点击前后截图
```

## 6. 后端修复方案

### 6.1 runtime_match 写回字段补齐

位置：

```text
POST /api/mapping/runtime_match
```

当前写入：

```python
m["runtimeMatch"] = {...}
```

建议补充：

```python
screen_rect = r.get("screenRect", [])
runtime_path = r.get("runtimePath", "")

m["reviewStatus"] = "runtime_matched"
m["sourceLevel"] = "L2"
m["hasRuntimeMatch"] = True
m["runtimePath"] = runtime_path or m.get("runtimePath", "")
m["screenRect"] = screen_rect or m.get("screenRect", [])
m["hasHighlightRect"] = bool(screen_rect)
m["runtimeMatchedAt"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
m["runtimeMatch"] = {
    "status": "matched",
    "matchScore": r.get("matchScore", 0),
    "matchLevel": r.get("matchLevel", ""),
    "runtimePath": runtime_path,
    "instanceId": r.get("instanceId", 0),
    "visible": r.get("visible", False),
    "interactable": r.get("interactable", False),
    "screenRect": screen_rect,
    "matchedAt": m["runtimeMatchedAt"],
}
```

### 6.2 写入当前截图路径

如果存在：

```text
current_runtime_state.json
```

并且其中有：

```text
screenshotPath
```

则匹配成功时同步：

```python
current_state = read_current_runtime_state()
screenshot_path = current_state.get("screenshotPath", "")
if screenshot_path:
    m["screenshotRef"] = screenshot_path
    m["hasScreenshot"] = True
```

如果没有截图，不要假装有截图：

```python
m["hasScreenshot"] = False
```

### 6.3 保存匹配失败和冲突

当前只写入高分匹配。

建议同时写入失败原因：

```python
if not r.get("matched"):
    m["runtimeMatch"] = {
        "status": "not_matched",
        "reason": r.get("reason", ""),
        "matchedAt": ...
    }
```

冲突写入：

```python
m["runtimeMatch"] = {
    "status": "conflict",
    "candidates": r.get("candidates", []),
    "reason": "multiple_candidates"
}
```

这样前端可以显示：

```text
未匹配
冲突
```

而不是所有元素看起来都只是“结构审核”。

### 6.4 `/api/mapping/highlight` 支持 draftPath

当前 highlight 接口如果只接收 `screenRect`，前端调用会比较麻烦。

建议支持：

```json
{
  "draftPath": "...",
  "useRuntimeMatch": true
}
```

后端逻辑：

```text
根据 draftPath 读取映射
优先使用 runtimeMatch.screenRect
其次顶层 screenRect
读取 screenshotRef 或 current_runtime_state.screenshotPath
绘制高亮图
返回 highlightImage
```

返回：

```json
{
  "success": true,
  "highlightImage": "...",
  "screenRect": {},
  "sourceScreenshot": "...",
  "runtimePath": "..."
}
```

## 7. 前端修复方案

### 7.1 增加“已匹配”筛选按钮

左侧筛选增加：

```text
已匹配
未匹配
冲突
当前页已匹配
```

调用：

```text
/api/mapping/drafts?status=runtime_matched
```

或：

```text
/api/mapping/drafts?runtimeMatch=matched
```

建议后端同时支持 `runtimeMatch` 参数。

### 7.2 修正 hasImg / hasVisualEvidence 判断

不要只判断：

```javascript
data.screenshotRef || data.hasScreenshot
```

建议：

```javascript
function _hasRect(rect){
  if(!rect) return false;
  if(Array.isArray(rect)) return rect.length >= 4;
  if(typeof rect === 'object') return (rect.width > 0 && rect.height > 0) || (rect.x2 !== undefined);
  return false;
}

var rm = data.runtimeMatch || {};
var hasRuntimeMatch = rm.status === 'matched' || data.reviewStatus === 'runtime_matched';
var hasRuntimeRect = _hasRect(rm.screenRect) || _hasRect(data.screenRect);
var hasScreenshot = !!(
  (data.screenshotRef && String(data.screenshotRef).trim()) ||
  data.hasScreenshot ||
  data.highlightImage
);
var canHighlight = hasRuntimeMatch && hasRuntimeRect;
var canVisualConfirm = canHighlight && hasScreenshot;
```

显示模式：

```javascript
if(!hasRuntimeMatch){
  mode = 'structure';
}else if(hasRuntimeMatch && !hasRuntimeRect){
  mode = 'runtime_no_rect';
}else if(hasRuntimeMatch && hasRuntimeRect && !hasScreenshot){
  mode = 'runtime_need_screenshot';
}else{
  mode = 'visual';
}
```

### 7.3 选中元素后自动高亮

在 `shDraft(p)` 成功获取 data 后：

```javascript
if(canHighlight){
  fetch('/api/mapping/highlight', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      draftPath: p,
      useRuntimeMatch: true
    })
  })
  .then(r=>r.json())
  .then(h=>{
    if(h.success){
      renderHighlightImage(h.highlightImage);
    }else{
      renderHighlightError(h.error);
    }
  });
}
```

### 7.4 中间区域改成动态容器

当前中间区域不能只是静态文案。

建议 HTML：

```html
<div id="rPreview">
  <div id="rPreviewText">选择草稿</div>
  <img id="rPreviewImg" style="display:none;max-width:100%;max-height:100%;">
</div>
```

前端函数：

```javascript
function renderPreviewText(text){
  document.getElementById('rPreviewImg').style.display='none';
  document.getElementById('rPreviewText').style.display='block';
  document.getElementById('rPreviewText').innerHTML=text;
}

function renderHighlightImage(path){
  var img=document.getElementById('rPreviewImg');
  img.src='/api/screenshot/'+encodeURIComponent(path)+'?t='+Date.now();
  img.style.display='block';
  document.getElementById('rPreviewText').style.display='none';
}
```

### 7.5 视觉确认按钮启用条件

当前：

```javascript
视觉确认按钮依赖 hasImg
```

建议改为：

```text
canVisualConfirm = runtimeMatch.status=matched + screenRect有效 + 高亮图生成成功
```

如果没有高亮图：

```text
视觉确认按钮禁用
提示“请先生成截图高亮”
```

## 8. IDE 显示文案修正

### 8.1 未匹配

```text
当前为结构审核模式
该元素尚未匹配到 Unity 当前实时界面
请先刷新实时 UI 树并执行“匹配当前页”
```

### 8.2 已匹配无坐标

```text
运行态已匹配
但缺少 screenRect，无法截图高亮
可先测试点击，或重新导出运行态 UI 树
```

### 8.3 已匹配有坐标无截图

```text
运行态已匹配
已有 screenRect
请点击“刷新截图”或“生成高亮”
```

### 8.4 可视觉确认

```text
运行态已匹配
截图高亮已生成
请确认红框是否框中正确目标
```

### 8.5 点击已确认

```text
点击已确认
该元素可进入正式自动点击
```

## 9. 推荐修复顺序

### P0：必须先修

```text
1. 左侧增加“已匹配”筛选。
2. runtime_match 写回顶层 screenRect/runtimePath/hasHighlightRect/hasRuntimeMatch。
3. shDraft 判断 runtimeMatch.screenRect，不再只看 screenshotRef。
4. 中间区域根据状态显示运行态匹配信息。
```

### P1：紧接着修

```text
5. 选中 runtime_matched 元素时自动调用 /api/mapping/highlight。
6. 中间区域显示高亮图。
7. 视觉确认按钮只在高亮图成功后启用。
8. highlight 接口支持 draftPath。
```

### P2：体验优化

```text
9. 增加“当前页已匹配”筛选。
10. 增加冲突候选选择面板。
11. 增加未匹配原因展示。
12. 点击确认失败时保留失败原因和截图。
```

## 10. 验收标准

### 10.1 已匹配筛选验收

```text
点击“已匹配”后，左侧只显示 reviewStatus=runtime_matched 或 runtimeMatch.status=matched 的元素。
未匹配元素不会混在已匹配列表中。
```

### 10.2 单元素详情验收

选择已匹配元素后，右侧必须显示：

```text
运行态匹配
matchScore
matchLevel
runtimePath
visible
interactable
screenRect
```

不能继续只显示：

```text
当前为结构审核模式
```

### 10.3 高亮验收

选择已匹配且有 screenRect 的元素后：

```text
自动生成 highlightImage
中间区域显示高亮图
红框位置与游戏截图中元素位置一致
```

### 10.4 视觉确认验收

只有满足：

```text
runtimeMatch.status=matched
screenRect 有效
highlightImage 已生成
```

才允许点击：

```text
视觉确认
```

确认后：

```text
reviewStatus=visual_confirmed
visualReview.confirmed=true
visualReview.highlightImage=xxx
```

### 10.5 点击确认验收

视觉确认后点击测试：

```text
优先使用 runtimePath/instanceId
命中正确 GameObject
eventReceiverMatched=true
成功后 reviewStatus=click_confirmed
```

## 11. 最终效果

修复前：

```text
全局显示匹配完成
选中元素仍显示结构审核模式
没有高亮图
用户不知道是否能视觉确认
```

修复后：

```text
全局匹配结果可筛选
单个元素明确显示运行态匹配状态
已匹配元素能自动高亮
用户可以视觉确认
用户可以测试点击
成功后进入 click_confirmed
```

最终用户看到的流程应是：

```text
匹配当前页
 -> 点击“已匹配”
 -> 选择元素
 -> 中间显示高亮图
 -> 右侧显示 runtimePath / matchScore / screenRect
 -> 视觉确认
 -> 测试点击
 -> click_confirmed
```

## 12. 结论

当前问题的本质是：

```text
运行态匹配结果已经生成，
但审核 UI 仍按“静态草稿/结构审核”逻辑展示。
```

需要把 IDE 审核页从：

```text
草稿审核页面
```

升级为：

```text
运行态匹配审核页面
```

也就是让 `runtimeMatch` 成为详情页、高亮页、视觉确认、点击确认的核心依据。
