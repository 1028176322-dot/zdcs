# AutoSmoke Agent Handoff README

更新时间：2026-06-17

本文用于让后续接手的 agent 快速理解当前 AutoSmoke IDE 的目标、代码位置、启动方式、近期修复内容和仍需注意的问题。

## 1. 项目目标

AutoSmoke 的最终目标是把 Unity SLG 游戏自动化测试能力封装到一个 IDE 中，覆盖：

- 环境配置、Unity 项目连接、Poco/Bridge/SDK 部署。
- Unity 实时 UI 树导入、工程态 UI 清单导入、元素映射草稿生成。
- 在 IDE 中连接 Unity 当前实时界面，人工审核元素映射。
- 自动点击、弹窗处理、页面关系图记录、异常检测。
- 崩溃、卡死、空页面、Missing Reference、阻塞弹窗、Loading、重连、引导等状态识别。
- 自动执行用例并输出测试报告。

重要原则：

- 自动点击必须以精准为前提。
- 正式执行优先使用 Unity 运行态路径、instanceId、EventSystem/Raycast 注入点击。
- 工程导出的映射草稿只是低优先级参考，最终正确性以 IDE 连接 Unity 后的实时界面确认结果为准。
- 不修改游戏业务逻辑代码；允许增加 Unity Editor-only 工具脚本和自动化辅助脚本。

## 2. 关键路径

AutoSmoke 根目录：

```text
E:\zdcs\AutoSmoke
```

Unity 工程目录：

```text
E:\s1\k3client\client
```

IDE 主入口：

```text
E:\zdcs\AutoSmoke\autosmoke_web_ide.py
```

IDE 主界面与接口：

```text
E:\zdcs\AutoSmoke\IDE\debug_panel.py
```

运行态 UI 树匹配器：

```text
E:\zdcs\AutoSmoke\元数据\runtime_matcher.py
```

Unity 运行态 UI 树导出脚本：

```text
E:\s1\k3client\client\Assets\Editor\AutoSmokeRuntimeUITreeDumper.cs
E:\zdcs\AutoSmoke\tools\AutoSmokeRuntimeUITreeDumper.cs
```

Unity 直出截图脚本：

```text
E:\s1\k3client\client\Assets\Editor\AutoSmokeGameContentCapture.cs
```

运行态 UI 树文件：

```text
E:\zdcs\AutoSmoke\metadata\runtime_ui_tree_current.json
```

元素映射文件：

```text
C:\Users\Administrator\.autosmoke\metadata\element_mapping.json
```

截图与高亮输出：

```text
E:\zdcs\AutoSmoke\screenshots
E:\zdcs\AutoSmoke\screenshots\mapping_review
```

方案文档目录：

```text
E:\zdcs\进度
```

## 3. IDE 启动方式

用户习惯使用：

```text
E:\zdcs\AutoSmoke\start_ide.bat
```

当前 `start_ide.bat` 已改成“干净重启”启动器：

- 先关闭旧的 `autosmoke_web_ide.py` Python 进程。
- 删除旧的 `runtime\web_ide.pid`。
- 优先使用：

```text
C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe
```

- 固定从 `E:\zdcs\AutoSmoke` 启动。
- 固定端口 `5000`。
- 固定参数：

```text
autosmoke_web_ide.py --port 5000 --no-debug
```

- 日志：

```text
E:\zdcs\AutoSmoke\logs\web_ide_5000.out.log
E:\zdcs\AutoSmoke\logs\web_ide_5000.err.log
```

访问地址：

```text
http://localhost:5000
```

检查 IDE 状态：

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/ide/status' -TimeoutSec 10
```

检查端口占用：

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 5000 }
```

## 4. 当前已经修复的关键问题

### 4.1 多个 IDE 进程和旧进程问题

曾出现同一机器多个 `autosmoke_web_ide.py` 进程，浏览器访问的是旧进程，导致代码修改不生效。

处理方式：

- `start_ide.bat` 启动前会杀掉旧 IDE 进程。
- `autosmoke_web_ide.py` 的 PID 锁逻辑已增强：PID 文件存在但 5000 端口未监听时，会视为失效锁，不再阻止启动。

### 4.2 Unity 截图出现两套 run 文件夹

曾出现一次操作生成两个截图目录：Unity cap 目录和 Python fallback 目录。

原因：

- IDE 旧进程还在跑。
- `/api/capture` 等待的目录和 Unity 实际输出目录不一致。

处理方向：

- 确保只保留一个 IDE 进程。
- `capture_reader.py` 已支持查找 Unity 新截图目录：

```text
E:\zdcs\AutoSmoke\screenshots\run_*\cap_*.png
```

### 4.3 运行态 UI 树坐标错误

曾出现 `screenRect` 类似 `[-1,5,0,4]` 的错误坐标。

原因：

- Unity 脚本直接把 `RectTransform.GetWorldCorners()` 的世界坐标当成屏幕坐标。

已修复：

- `AutoSmokeRuntimeUITreeDumper.cs` 使用 `RectTransformUtility.WorldToScreenPoint` 转屏幕坐标。
- 将 Unity 左下原点坐标转换为截图左上原点坐标。

### 4.4 当前在背包界面，但匹配到非背包元素

这是最近刚修复的重点问题。

现象：

- 用户在背包界面。
- 点击“刷新运行态 UI 树”后，匹配结果和高亮经常跑到主界面、聊天、底部区域或其它非背包节点。

根因：

- Unity 运行态节点的原始 `pageId` 不是业务页面名，而是就近容器名，例如：

```text
BtnClose
BG
Tab
View
ViewPort
ScrollView
TopRes
```

- 背包子节点实际路径在：

```text
Root/Shop/Content/Bag/...
```

但部分节点原始 `pageId` 是 `ScrollView / ViewPort / BG`。

已修复：

- 在 `runtime_matcher.py` 中新增运行态节点归属页推断：

```text
ownerPageId
currentBusinessPageId
rawPageId
```

- 当前业务页不再直接信任 Unity 顶层返回的 `pageId=BtnClose`。
- 背包页现在会识别为：

```text
pageId = UIShop(Clone)_UIShopPop [UIShopPop]
rawPageId = BtnClose
currentBusinessPageId = UIShop(Clone)_UIShopPop [UIShopPop]
```

- 匹配时优先使用 `ownerPageId`，再兼容原始 `pageId`。
- 对异常巨大矩形不再进行面积加分，避免 UIMain 特效节点抢走当前页。

验证命令：

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/runtime_ui/refresh' -Method Post -TimeoutSec 20
```

期望返回中包含：

```text
pageId: UIShop(Clone)_UIShopPop [UIShopPop]
```

运行态树落盘验证：

```powershell
python - <<'PY'
import json, collections
p=r'E:\zdcs\AutoSmoke\metadata\runtime_ui_tree_current.json'
data=json.load(open(p,encoding='utf-8'))
print(data.get('pageId'))
print(data.get('rawPageId'))
print(data.get('currentBusinessPageId'))
print(collections.Counter(n.get('ownerPageId','') for n in data.get('nodes',[])).most_common(8))
PY
```

## 5. IDE 中当前推荐操作流程

用户在 Unity 中打开目标界面，例如背包界面后：

1. 启动 IDE：

```text
E:\zdcs\AutoSmoke\start_ide.bat
```

2. 浏览器打开或刷新：

```text
http://localhost:5000
```

3. 浏览器按 `Ctrl+F5` 强刷，避免前端缓存旧 JS。

4. 在 IDE 中点击：

```text
刷新运行态UI树
```

5. 确认 Unity 连接区域显示当前业务页，例如：

```text
UIShop(Clone)_UIShopPop [UIShopPop]
```

6. 点击：

```text
匹配当前页
```

7. 在元素列表中选择元素。

8. 如果元素已有运行态匹配和 `screenRect`，点击：

```text
刷新截图并生成高亮
```

9. 人工确认高亮是否框住正确目标。

10. 对正确元素执行：

```text
视觉确认
点击确认
保存
```

正式自动点击应优先使用 `click_confirmed` 元素。

## 6. 映射审核原则

元素状态建议含义：

```text
auto_draft            自动草稿，不能直接用于正式执行
structure_confirmed   结构确认，仍不能保证当前界面正确
runtime_matched       已匹配到 Unity 当前运行态节点
visual_confirmed      高亮截图人工确认正确
click_confirmed       Unity 注入点击验证通过，可用于正式自动点击
rejected              明确错误
ignored               不参与自动化
```

正式执行优先级：

```text
click_confirmed > visual_confirmed > runtime_matched
```

不建议正式执行使用：

```text
auto_draft
structure_confirmed
```

## 7. 自动点击定位原则

自动点击不能只靠截图像素位置。

优先级：

1. Unity 运行态节点 `instanceId`。
2. Unity 运行态 `runtimePath`。
3. `clickTargetNode`。
4. `screenRect` 中心点。
5. 截图模板或 OCR 只作为兜底。

复杂元素要区分：

```text
visualNode       用于截图高亮和人工识别
clickTargetNode  实际注入点击的目标节点
```

例如道具图标、奖励格子、建筑呼出按钮、空白关闭区域，视觉节点和点击节点可能不是同一个。

## 8. 当前仍需注意的问题

### 8.1 同页内重名元素仍可能需要人工确认

例如：

```text
Item
Button
BG
Icon
ClickContent
```

这些名字在多个页面、多个列表项中大量重复。即使当前页识别正确，也可能需要通过：

- 父路径。
- siblingIndex。
- spriteName。
- text。
- screenRect 区域。
- clickTargetNode。
- 可见性。
- 列表索引。

进一步区分。

### 8.2 某些大面积 BG 节点可能仍被当成可点击

需要继续优化有效点击规则：

- Button/Toggle/EventTrigger/IPointerClickHandler 权重最高。
- Image.raycastTarget + 可点击父节点可以作为图标可点击候选。
- BG、Mask、Panel、Content 默认不能直接算作有效点击，除非明确属于空白关闭区域或拖拽区域。

### 8.3 UIMain 是常驻界面，不能轻易当当前业务页

主城/大地图常驻 HUD 会一直存在，因此“当前业务页”判断必须优先识别弹窗、全屏面板、业务根节点。

已做降权：

```text
UiMain(Clone) [UIMainPopup]
```

但如果后续进入主城/大地图无弹窗场景，需要单独定义场景页：

```text
MainCity
WorldMap
```

并引入场景对象树。

## 9. 常用接口

IDE 状态：

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/ide/status' -TimeoutSec 10
```

刷新运行态 UI 树：

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/runtime_ui/refresh' -Method Post -TimeoutSec 20
```

运行当前页匹配：

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/mapping/runtime_match' -Method Post -ContentType 'application/json' -Body '{}' -TimeoutSec 120
```

Unity 截图：

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/capture' -TimeoutSec 15
```

手动生成高亮：

```powershell
$body = @{ draftPath = '元素draftPath' } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/mapping/highlight' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 20
```

## 10. 最近改过的文件

本目录当前不是 git 仓库，不能依赖 `git diff` 查看变更。

最近关键修改文件：

```text
E:\zdcs\AutoSmoke\start_ide.bat
E:\zdcs\AutoSmoke\autosmoke_web_ide.py
E:\zdcs\AutoSmoke\IDE\debug_panel.py
E:\zdcs\AutoSmoke\元数据\runtime_matcher.py
E:\s1\k3client\client\Assets\Editor\AutoSmokeRuntimeUITreeDumper.cs
E:\zdcs\AutoSmoke\tools\AutoSmokeRuntimeUITreeDumper.cs
```

## 11. 接手时优先检查

接手后先做这几步：

1. 双击或运行：

```text
E:\zdcs\AutoSmoke\start_ide.bat
```

2. 确认只有一个 5000 端口监听：

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 5000 }
```

3. 打开 IDE：

```text
http://localhost:5000
```

4. 在 Unity 中进入一个明确界面，例如背包。

5. IDE 点击“刷新运行态UI树”。

6. 检查返回页面是否为业务页，而不是 `BtnClose/BG/ViewPort/Tab`。

7. 再点击“匹配当前页”。

8. 选择几个背包元素生成高亮，确认红框位置是否和元素一致。

如果第 6 步失败，优先看：

```text
E:\zdcs\AutoSmoke\元数据\runtime_matcher.py
```

重点函数：

```text
enrich_runtime_nodes
infer_current_business_page_id
page_matches
page_matches_any
```

## 12. 用户偏好

用户希望：

- 方案文档按功能分类放在：

```text
E:\zdcs\进度\<功能名>\
```

- 后续记忆文件也分类放置。
- IDE 最终分为三大页签：

```text
准备
执行
结果
```

- 不要只给理论方案；需要能落地到 IDE 操作流程和代码实现。
- 自动点击准确性优先于截图完整性。
- 不修改游戏业务流程代码，只做自动化工具层和 Unity Editor 辅助层。

## 13. 2026-06-17 最新接手重点

### 13.1 IDE 功能精简方向

后续 IDE 不应继续堆散按钮，而是收敛为三大页签下的主流程：

```text
准备
执行
结果
```

准备页主流程：

```text
初始化环境
同步工程数据
同步当前界面
审核元素映射
```

其中“同步当前界面”应合并：

```text
刷新运行态 UI 树
Unity 直出截图
当前业务页识别
当前页元素匹配
运行态发现补充
当前页匹配摘要
```

最新方案文件：

```text
E:\zdcs\进度\IDE界面设计\AutoSmoke_IDE功能精简整合与代码语义索引增强方案.md
```

### 13.2 当前 Unity 界面反查工程代码并融合匹配

后续核心增强方向：

```text
当前 Unity 运行态界面
  -> 识别 currentBusinessPageId
  -> normalizedPageId
  -> 反查工程 Prefab
  -> 反查 Lua / C# / 配置代码
  -> 提取绑定函数和业务语义
  -> 与运行态 UI 树、工程 UI 清单融合匹配
```

目标是让 IDE 不只知道元素“在哪里”，还知道元素“是干什么的”。

元素详情后续应补充：

```text
boundHandler
actionType
businessAction
requiresState
expectedResult
sourceFiles
semanticConfidence
```

建议新增模块：

```text
E:\zdcs\AutoSmoke\元数据\code_semantic_indexer.py
E:\zdcs\AutoSmoke\元数据\current_page_code_resolver.py
E:\zdcs\AutoSmoke\元数据\semantic_fusion_matcher.py
E:\zdcs\AutoSmoke\metadata\ui_code_semantics.json
E:\zdcs\AutoSmoke\metadata\current_page_semantics.json
E:\zdcs\AutoSmoke\config\code_semantic_rules.json
```

建议新增接口：

```text
POST /api/prepare/sync_current_page
POST /api/code_semantics/rebuild
POST /api/code_semantics/query_current_page
POST /api/code_semantics/query_element
```

### 13.3 背包页当前验证结果

当前测试和调试主要基于背包界面 `UIShop`。

已验证：

```text
currentBusinessPageId = UIShop(Clone)_UIShopPop [UIShopPop]
normalizedPageId = UIShop
UiMain 匹配到背包页 = 0
使用按钮 = 1
道具格子 = 4
资源加号 = 4
页签 = 5
已匹配总数 = 19
```

运行态发现去重规则：

```text
道具格子只保留 ClickContent
资源加号只保留 add
页签只保留页签根节点
过滤 Quality / Icon / Text / On / Off / Item(Clone)
一个实际点击目标只保留一个审核项
```

涉及代码：

```text
E:\zdcs\AutoSmoke\元数据\runtime_matcher.py
E:\zdcs\AutoSmoke\IDE\debug_panel.py
```

### 13.4 后续优先事项

优先实现顺序：

```text
1. 做 /api/prepare/sync_current_page，把当前多个按钮合并成一键流程。
2. 做 code_semantic_indexer.py，先支持 UIShop 样例。
3. 在元素详情中展示代码语义。
4. 将代码语义加入匹配评分。
5. 把背包页规则推广到奖励弹窗、确认弹窗、建筑菜单、主城、大地图、Loading、重连、引导。
```
