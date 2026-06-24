# AutoSmoke 目标驱动映射交接文档

日期：2026-06-18  
当前 IDE 版本：v1.5.20  
工作目录：E:/zdcs

## 1. 当前结论

目标驱动映射已经完成单目标严格闭环：

```text
运行态目标生成
→ 候选匹配
→ 候选选择
→ 高亮确认
→ Unity 真实点击
→ 生成业务 testId
→ 写入 draft/formal/evidence
```

当前已验证样例：

```text
targetId: runtime.647b3c9358
targetName: TopRes ResItem_1 item cell
confirmedTestId: ui_shop.top_res.item_1.cell
status: click_confirmed
```

严格方案要求的三层文件均已写入：

```text
任务层: E:/zdcs/AutoSmoke/metadata/mapping_task_queue.json
草稿层: E:/zdcs/AutoSmoke/元数据/element_mapping_draft.json
正式层: E:/zdcs/AutoSmoke/metadata/element_mapping_formal.json
证据层: E:/zdcs/AutoSmoke/metadata/mapping_evidence.json
```

兼容旧文件仍会同步写：

```text
C:/Users/Administrator/.autosmoke/metadata/element_mapping.json
```

## 2. 已实现功能

### 2.1 Target Workbench API

核心文件：

```text
E:/zdcs/AutoSmoke/IDE/debug_panel.py
```

主要接口：

```text
/api/target/list
/api/target/save
/api/target/import
/api/target/generate_from_cases
/api/target/generate_from_runtime_current
/api/target/match_candidates
/api/target/select_candidate
/api/target/runtime_match
/api/target/highlight
/api/target/visual_confirm
/api/target/test_click
```

主要状态流：

```text
pending_match
candidate_found
runtime_matched
highlight_generated
visual_confirmed
click_confirmed
blocked
ignored
```

### 2.2 运行态目标生成

入口：

```text
/api/target/generate_from_runtime_current
```

读取：

```text
E:/zdcs/AutoSmoke/metadata/runtime_ui_tree_current.json
```

写入：

```text
E:/zdcs/AutoSmoke/metadata/mapping_task_queue.json
```

对应模块：

```text
E:/zdcs/AutoSmoke/元数据/target_catalog.py
```

### 2.3 候选匹配

对应模块：

```text
E:/zdcs/AutoSmoke/元数据/target_candidate_matcher.py
```

已实现能力：

```text
runtimeHint 强匹配
runtimePath 精确/后缀匹配
name/page/role/type/code semantic 综合打分
top candidates 返回
risk 标记: runtime_path_mismatch / duplicate_name / screen_rect_missing
```

### 2.4 高亮确认

接口：

```text
/api/target/highlight
/api/target/visual_confirm
```

当前目标已生成高亮证据：

```text
E:/zdcs/AutoSmoke/screenshots/mapping_review/...
```

高亮记录写入：

```text
mapping_task_queue.json -> task.evidence.visual
```

### 2.5 Unity 真实点击链路

涉及文件：

```text
E:/s1/k3client/client/Assets/Editor/AutoSmokeRuntimeBridge.cs
E:/zdcs/AutoSmoke/tools/AutoSmokeRuntimeBridge.cs

E:/s1/k3client/client/Assets/Editor/AutoSmokeClickInjector.cs
E:/zdcs/AutoSmoke/tools/AutoSmokeClickInjector.cs
```

已修复问题：

```text
1. IDE 等错 Bridge 响应文件名。
2. Unity Bridge 处理旧请求积压。
3. Bridge 等待 ClickInjector 结果过短。
4. ClickInjector path 精确匹配过严，增加唯一后缀匹配。
5. RectTransform 世界坐标被误当屏幕坐标，改为 WorldToScreenPoint。
6. Raycast 命中 text 子节点但业务事件在父节点，改为 ExecuteHierarchy。
```

关键代码点：

```text
AutoSmokeRuntimeBridge.cs
- test_click_element 分支
- 处理后 File.Delete(reqFile)
- DateTime.Now.AddSeconds(45)
- matchedClickResult requestId 校验

AutoSmokeClickInjector.cs
- FindByPath: suffixMatches 唯一后缀匹配
- CalcSafePoint: RectTransformUtility.WorldToScreenPoint
- 点击派发: ExecuteEvents.ExecuteHierarchy
- ClickInfo.dispatchTarget
```

当前可确认：

```text
游戏内实际点击已经生效。
```

### 2.6 严格方案写入

核心函数：

```text
E:/zdcs/AutoSmoke/IDE/debug_panel.py

_target_business_test_id(...)
_target_unique_test_id(...)
_target_upsert_draft_mapping(...)
_target_write_formal_and_evidence(...)
_target_confirm_test_id(...)
api_target_test_click(...)
```

当前正式 testId 生成规则：

```text
page.area.node.suffix
```

例：

```text
UIShop + TopRes + ResItem_1 + item_cell
→ ui_shop.top_res.item_1.cell
```

正式映射样例：

```json
{
  "testId": "ui_shop.top_res.item_1.cell",
  "pageId": "UIShop",
  "role": "item",
  "elementType": "item_cell",
  "reviewStatus": "click_confirmed",
  "evidenceRef": "EVIDENCE_ui_shop.top_res.item_1.cell",
  "locator": {
    "type": "runtimePath",
    "value": "DeepUI/LayerUI/UIShop(Clone)_UIShopPop [UIShopPop]/Root/TopRes/ResItem_1"
  }
}
```

证据样例：

```json
{
  "testId": "ui_shop.top_res.item_1.cell",
  "targetName": "TopRes ResItem_1 item cell",
  "structure": {
    "path": "Assets/k1/K1D1/Res/UI/Panel/Shop/UIShop.prefab::UIShop/Root/TopRes/ResItem_1",
    "pageId": "UIShop",
    "elementType": "item_cell"
  },
  "runtime": {
    "matched": true,
    "runtimePath": "DeepUI/LayerUI/UIShop(Clone)_UIShopPop [UIShopPop]/Root/TopRes/ResItem_1"
  },
  "visual": {
    "confirmed": true
  },
  "click": {
    "confirmed": true,
    "result": "PASS",
    "method": "unity_event_system"
  }
}
```

## 3. 当前未实现功能与执行步骤

### 3.1 快速点击验证模式

问题：

当前点击验证仍慢，原因是 IDE 主要等待 Bridge response，Bridge 有时先写 CLICK_TIMEOUT，IDE 再从 `click_result.json` 兜底恢复。

目标：

让 IDE 同时监听：

```text
E:/zdcs/AutoSmoke/runtime/bridge/responses/click_xxx.json
C:/Users/Administrator/.autosmoke/click_result.json
```

谁先返回同 requestId 的有效结果，就立即结束。

执行步骤：

1. 修改 `debug_panel.py` 中 `/api/mapping/drafts/<draft_path>/test_click` 的 Bridge 等待循环。
2. 发出 Bridge request 后，循环中同时检查 Bridge done 和 `click_result.json`。
3. 如果 `click_result.json.requestId == request_id` 且 `status == OK`，直接设置：

```python
result_data = {
    "clickResult": "OK",
    "eventReceiverMatched": click["receiverMatchTarget"],
    "hitRuntimePath": click["eventReceiver"],
    "dispatchTarget": click["dispatchTarget"],
    "screenPoint": click["screenPoint"],
    "injectorResultRecovered": True,
}
click_method = "unity_event_system"
```

4. Bridge response 仅作为备用。
5. 超时时间可从 60 秒降到 8-12 秒。

核心代码位置：

```text
E:/zdcs/AutoSmoke/IDE/debug_panel.py
api_mapping_test_click(...)
当前 click_result 兜底逻辑在 Path.home() / ".autosmoke" / "click_result.json"
```

### 3.2 执行层优先读取 formal

问题：

方案要求执行层只信任：

```text
element_mapping_formal.json
```

但当前执行器/locator 仍可能优先读兼容旧文件：

```text
C:/Users/Administrator/.autosmoke/metadata/element_mapping.json
```

执行步骤：

1. 搜索执行层读取映射入口：

```powershell
rg -n "element_mapping|element_mapping_formal|metadata_reader|testId" E:/zdcs/AutoSmoke
```

2. 修改 `metadata_reader.py` 或 `target_locator.py` 的读取顺序：

```text
1. E:/zdcs/AutoSmoke/metadata/element_mapping_formal.json
2. C:/Users/Administrator/.autosmoke/metadata/element_mapping.json
3. E:/zdcs/AutoSmoke/元数据/element_mapping_draft.json 中 click_confirmed/manual_confirmed 项
```

3. 对 `testId("ui_shop.top_res.item_1.cell")` 做定位测试。
4. 确认正式映射命中 runtimePath，而不是旧兼容映射。

核心代码候选：

```text
E:/zdcs/AutoSmoke/元数据/metadata_reader.py
E:/zdcs/AutoSmoke/元数据/target_locator.py
E:/zdcs/AutoSmoke/用例层/case_step_executor.py
```

### 3.3 批量自动推进

问题：

目前主要是单目标点击“下一步”，还没有一键批量。

目标：

新增批量 API：

```text
/api/target/batch_advance
```

执行步骤：

1. 读取 `mapping_task_queue.json`。
2. 过滤状态：

```text
pending_match / candidate_found / visual_confirmed
```

3. 对每个目标按状态推进：

```text
pending_match -> match_candidates
candidate_found/runtime_matched -> highlight
highlight_generated -> visual_confirm
visual_confirmed -> test_click
```

4. 每个目标写入 evidence。
5. 输出批量报告：

```json
{
  "total": 20,
  "advanced": 12,
  "blocked": 5,
  "ignored": 3,
  "items": []
}
```

核心代码位置：

```text
E:/zdcs/AutoSmoke/IDE/debug_panel.py
api_target_match_candidates
api_target_highlight
api_target_visual_confirm
api_target_test_click
```

建议不要直接 HTTP 调自己的 API，可提取内部 helper，避免多层 Flask 调用。

### 3.4 唯一性检查 UI 与报告

当前状态：

`_target_unique_test_id(...)` 已有冲突兜底，冲突时追加 hash 后缀。

未实现：

没有 UI 报告，也没有保存前阻断策略。

执行步骤：

1. 新增 API：

```text
/api/target/testid_uniqueness_report
```

2. 扫描：

```text
element_mapping_formal.json
mapping_task_queue.json
element_mapping_draft.json
```

3. 检查：

```text
同一个 testId 是否对应多个 elementPath
同一 pageId + testId 是否对应多个可见元素
同一个 semanticId 是否映射多个 testId
```

4. UI 在 Target Workbench 顶部显示重复项。
5. 保存 formal 前如有同页冲突，默认阻断。

核心代码建议：

```python
def _target_collect_test_id_index():
    ...

def _target_check_test_id_uniqueness(test_id, page_id, element_path):
    ...
```

### 3.5 codeSemantics 证据补齐

当前 `mapping_evidence.json` 已有：

```text
structure
runtime
visual
click
```

缺少：

```text
codeSemantics
caseReplay
versionInfo
retryHistory
```

执行步骤：

1. 在 `_target_write_formal_and_evidence(...)` 中读取：

```text
E:/zdcs/AutoSmoke/metadata/ui_code_semantics.json
```

2. 按 `draftPath/runtimePath/pageId` 找绑定代码语义。
3. 写入：

```json
"codeSemantics": {
  "matched": true,
  "ownerClass": "...",
  "boundMethod": "...",
  "businessKeywords": []
}
```

4. 后续用例回放成功后补 `caseReplay`。

核心代码位置：

```text
E:/zdcs/AutoSmoke/IDE/debug_panel.py
_target_write_formal_and_evidence(...)
```

### 3.6 用例回放验证 case_verified

问题：

当前最高到 `click_confirmed`，未跑真实用例步骤。

执行步骤：

1. 从 formal 中读取 `testId`。
2. 生成或选择用例步骤：

```text
点击 testId("ui_shop.top_res.item_1.cell")
```

3. 调用现有 case executor。
4. 成功后更新：

```text
mapping_task_queue.status = case_verified
element_mapping_formal.mappings[testId].reviewStatus = case_verified
mapping_evidence.evidence[evidenceRef].caseReplay = {...}
```

核心代码候选：

```text
E:/zdcs/AutoSmoke/用例层/case_step_parser.py
E:/zdcs/AutoSmoke/用例层/case_step_executor.py
```

### 3.7 失败反馈补洞任务

当前：

失败只写 `blockedReason`。

目标：

失败后自动生成补洞任务。

执行步骤：

1. 在 `api_target_test_click`、用例执行失败处收集：

```text
targetName
failedTestId
failureType
runtimeHint
lastEvidence
```

2. 写回 `mapping_task_queue.json`，创建新 target：

```text
targetId: repair.<hash>
status: pending_match
sourceCases: ["FAILED_CLICK", caseId]
```

3. UI 显示“失败补洞”筛选。

核心代码建议：

```python
def _target_create_repair_task(failure):
    ...
```

## 4. 当前遗留问题

### 4.1 点击响应延迟高

现象：

一次 `/api/target/test_click` 可能耗时 50 秒左右。

原因：

```text
IDE -> Bridge -> click_request.json -> ClickInjector -> click_result.json -> Bridge -> IDE
```

Bridge 仍可能先写 `CLICK_TIMEOUT`，IDE 再用 `click_result.json` 兜底恢复。

临时解决：

IDE 已能恢复真实 `OK`，但耗时仍高。

建议优先做 3.1 快速点击验证模式。

### 4.2 Bridge 与 ClickInjector 文件通信脆弱

当前依赖文件轮询：

```text
E:/zdcs/AutoSmoke/runtime/bridge/requests
E:/zdcs/AutoSmoke/runtime/bridge/responses
C:/Users/Administrator/.autosmoke/click_request.json
C:/Users/Administrator/.autosmoke/click_result.json
```

风险：

```text
Unity 编译未加载新 Bridge
旧 click_result 被误读
response 与 result 同秒竞争
```

已缓解：

```text
requestId 校验
旧请求清理
IDE 兜底读 click_result
```

仍建议后续改为事件/Socket/EditorApplication.delayCall 更可靠的直连模式。

### 4.3 ClickInjector 坐标仍可能异常

当前样例 screenPoint：

```text
[363, 2457]
```

在当前游戏分辨率下能正确点击，但仍需确认：

```text
不同 GameView 缩放
不同 Canvas renderMode
不同分辨率
多相机 UI
```

建议增加 `screenPoint` 合法性检查和 GameView 分辨率记录。

### 4.4 testId 命名仍依赖启发式

当前生成：

```text
ui_shop.top_res.item_1.cell
```

已经符合业务语义风格，但仍主要依赖：

```text
pageHint
runtime nodeName
role
elementType
```

还未深度使用：

```text
绑定方法
代码语义
业务词典
用例目标名别名
```

建议在 codeSemantics 补齐后，优先用业务词生成 testId。

### 4.5 兼容旧映射仍存在

仍写入：

```text
C:/Users/Administrator/.autosmoke/metadata/element_mapping.json
```

严格方案要求执行层优先 formal。旧文件保留是兼容策略，但后续必须明确：

```text
formal 是唯一可信源
element_mapping.json 仅为过渡兼容
```

## 5. 当前关键文件清单

### Python / IDE

```text
E:/zdcs/AutoSmoke/IDE/debug_panel.py
E:/zdcs/AutoSmoke/元数据/target_catalog.py
E:/zdcs/AutoSmoke/元数据/target_candidate_matcher.py
E:/zdcs/AutoSmoke/元数据/element_mapping.py
```

### Unity Editor

```text
E:/s1/k3client/client/Assets/Editor/AutoSmokeRuntimeBridge.cs
E:/s1/k3client/client/Assets/Editor/AutoSmokeClickInjector.cs
```

### AutoSmoke 工具副本

```text
E:/zdcs/AutoSmoke/tools/AutoSmokeRuntimeBridge.cs
E:/zdcs/AutoSmoke/tools/AutoSmokeClickInjector.cs
```

### 数据输出

```text
E:/zdcs/AutoSmoke/metadata/mapping_task_queue.json
E:/zdcs/AutoSmoke/元数据/element_mapping_draft.json
E:/zdcs/AutoSmoke/metadata/element_mapping_formal.json
E:/zdcs/AutoSmoke/metadata/mapping_evidence.json
C:/Users/Administrator/.autosmoke/metadata/element_mapping.json
```

## 6. 验证命令

### IDE 状态

```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:5000/api/ide/status' -TimeoutSec 10 |
  Select-Object -ExpandProperty Content
```

期望：

```json
{"version":"v1.5.20"}
```

### 当前目标点击确认

```powershell
Invoke-WebRequest `
  -Uri 'http://127.0.0.1:5000/api/target/test_click' `
  -Method POST `
  -ContentType 'application/json' `
  -Body '{"targetId":"runtime.647b3c9358"}' `
  -TimeoutSec 90 |
  Select-Object -ExpandProperty Content
```

期望：

```json
{
  "success": true,
  "status": "click_confirmed",
  "confirmedTestId": "ui_shop.top_res.item_1.cell"
}
```

### formal 检查

```powershell
Select-String `
  -LiteralPath 'E:/zdcs/AutoSmoke/metadata/element_mapping_formal.json' `
  -Pattern 'ui_shop.top_res.item_1.cell' `
  -Context 0,20
```

### evidence 检查

```powershell
Select-String `
  -LiteralPath 'E:/zdcs/AutoSmoke/metadata/mapping_evidence.json' `
  -Pattern 'EVIDENCE_ui_shop.top_res.item_1.cell' `
  -Context 0,30
```

## 7. 下一步推荐优先级

1. 快速点击验证模式，解决 50 秒级延迟。
2. 执行层优先读取 `element_mapping_formal.json`。
3. 唯一性检查 UI 和保存阻断。
4. 批量自动推进。
5. codeSemantics 与 caseReplay 证据补齐。
6. 失败补洞任务。

## 8. 注意事项

1. 修改 `E:/zdcs/AutoSmoke/IDE/debug_panel.py` 前先备份，并升级 `_APP_VERSION`。
2. Unity C# 修改必须同步两份：

```text
E:/s1/k3client/client/Assets/Editor/...
E:/zdcs/AutoSmoke/tools/...
```

3. Unity C# 修改后需要 Unity Editor 重新编译；必要时退出 Play Mode 再进入。
4. 当前点击是否真正生效，以游戏界面变化为准；`OK` 只代表注入器层成功。
5. 严格方案下正式执行应信任 formal，不应直接信任 draft。
