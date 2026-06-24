# AutoSmoke 方案要求 vs 当前实现 — 全面差距分析

> 分析日期：2026-06-15
> 方案文档：AutoSmoke_UI树与元素资料完整提取执行方案.md
> 代码仓库：e:\zdcs\AutoSmoke\ 及 e:\s1\k3client\client\Assets\Editor\

---

## 维度 1：工程态扫描（方案第6章）

### 方案要求
- 新增 `Assets/AutoSmoke/Editor/AutoSmokeUIPrefabScanner.cs`（方案第6.4节）
- 菜单：AutoSmoke/UI/Scan All UI Prefabs / Scan All Scenes / Export Project UI Inventory
- 递归扫描 `Assets/**/*.prefab` / `.unity` / `.asset`
- 输出 `project_ui_inventory.json`，包含 prefab 列表、每个节点的 path/name/components/text/clickable/rectTransform
- 包含图标类元素的独立识别（spriteName/atlasName/possibleIconType/possibleClickAction）

### 当前实现
- ❌ **`AutoSmokeUIPrefabScanner.cs` 不存在** — 在 `e:\zdcs\AutoSmoke\tools\` 和 `e:\s1\k3client\client\Assets\Editor\` 下均未找到
- ❌ **没有任何 prefab 扫描逻辑** — 现有 `.cs` 脚本全部是运行态导出/点击注入/截图/布局诊断
- ❌ **没有 `project_ui_inventory.json` 输出** — 全盘搜索未发现

### 差距分析
| 差距项 | 严重度 | 说明 |
|--------|--------|------|
| 缺失完整 Unity Editor 脚本 | P0 | 需要一个 Editor 脚本遍历所有 .prefab 文件并提取 UI 元素 |
| 缺失工程态图标扫描 | P0 | 方案要求独立识别图标类型（道具/奖励/资源/建筑/活动） |
| 缺失 MenuItem 菜单 | P1 | 方案要求 3 个菜单项，当前无任何工程态菜单 |
| 缺失 guid/category 字段 | P1 | 输出格式要求 assetPath/guid/category 等字段 |
| 缺失 Missing Script/Reference 检测 | P1 | 方案第6.6节要求在工程态扫描中检测 |

---

## 维度 2：运行态导出（方案第7章）

### 方案要求
- 新增 `Assets/AutoSmoke/Editor/AutoSmokeUITreeExporter.cs`（方案第7.3节）
- 输出字段：path/name/activeInHierarchy/visible/interactable/clickable/components/text/screenRect/gameContentRect/normalizedRect/canvas/sortingOrder/siblingIndex/raycastTarget/buttonInteractable/canvasGroupAlpha/prefabSource/iconInfo/visualNode/clickTargetNode/roleGuess
- 输出格式：screenRect 为 `{x, y, width, height}` 对象，normalizedRect 为 `{x, y, width, height}` 对象
- 可见性判断：综合 activeInHierarchy + RectTransform size + CanvasGroup alpha + Image/Text alpha + 是否在 GameContent 范围内 + 是否被遮挡
- 可点击性判断：Button/Toggle/InputField/EventTrigger/IPointerClickHandler/自定义脚本/raycastTarget

### 当前实现
- ⚠️ **`AutoSmokeMetadataExporter.cs` 存在** — 位于 `tools/AutoSmokeMetadataExporter.cs`，已部署到 `k3client/Assets/Editor/`
- ⚠️ **部分字段实现**：
  - ✅ 已实现：path/name/components/text/activeInHierarchy/visible/interactable/clickable/type/screenRect/normalizedRect/depth/childCount
  - ❌ 缺失：gameContentRect/sortingOrder（仅verbose模式有）/siblingIndex/raycastTarget/buttonInteractable/canvasGroupAlpha/prefabSource/iconInfo/visualNode/clickTargetNode/roleGuess
- ❌ **输出格式不匹配**：screenRect 为数组 `[x1, y1, x2, y2]`，方案要求的是对象 `{x, y, width, height}`
- ⚠️ **可见性判断**：仅检查 activeInHierarchy + CanvasGroup alpha，缺少遮挡检测和 GameContent 范围检测
- ✅ **可点击性判断**：相对完整，包含 Button/Toggle/Slider/InputField/EventTrigger/IPointerClickHandler/自定义脚本/raycastTarget
- ❌ **菜单项名称不匹配**：当前使用中文（"导出元数据"），方案要求英文（"Export Current UI Tree"）
- ❌ **输出路径不匹配**：当前输出到 `%USERPROFILE%\.autosmoke\metadata\current_ui.json`，方案要求输出到 `runtime/ui_tree/pages/{pageId}.json`

### 差距分析
| 差距项 | 严重度 | 说明 |
|--------|--------|------|
| 缺失 gameContentRect | P1 | 方案要求同时输出 gameContentRect |
| 缺失 sortingOrder/siblingIndex | P1 | 影响 z-order 判断 |
| 缺失 raycastTarget 导出 | P1 | 用于判断是否接收点击事件 |
| 缺失 canvasGroupAlpha | P1 | 影响透明遮罩判断 |
| 缺失 prefabSource | P1 | 影响工程态-运行态合并 |
| 缺失 roleGuess | P1 | 方案要求每个节点有 roleGuess |
| screenRect 输出格式为数组而非对象 | P2 | 与下游工具兼容性问题 |
| 可见性判断缺少遮挡检测 | P1 | 可能导致不可点击元素被标记为 visible |
| 输出路径不符合方案规划 | P2 | 方案要求统一 `runtime/ui_tree/` 目录 |
| 菜单项名称为中文而非英文 | P3 | 仅影响使用习惯 |

---

## 维度 3：图标采集（方案第7.7-7.9章）

### 方案要求
- 采集 spriteName/atlasName/textureName/materialName/raycastTarget/parentClickable
- 推断 possibleIconType（item/reward/resource/building/activity/decoration）
- 推断 possibleClickAction（open_item_tips/open_detail/open_source）
- 区分 visualNode 和 clickTargetNode
- 输出 iconInfo 字段，包含图标完整上下文
- 图标可点击判断规则（P0~P4 优先级表）

### 当前实现
- ❌ **没有任何图标相关扫描逻辑** — `AutoSmokeMetadataExporter.cs` 中：
  - 没有读取 `Image.sprite` 或 `RawImage.texture` 信息
  - 没有 spriteName/atlasName 字段
  - 没有 possibleIconType 推断
  - 没有 visualNode/clickTargetNode 区分
  - 没有 iconInfo 输出字段
  - 没有图标单独分类级别
- ❌ **没有图标与配置表关联逻辑** — 没有 itemId→itemName→iconName 的反查

### 差距分析
| 差距项 | 严重度 | 说明 |
|--------|--------|------|
| 缺失 spriteName/atlasName 采集 | P0 | 图标基础信息缺失 |
| 缺失 iconType 推断 | P0 | 无法区分道具/奖励/资源/活动/装饰图标 |
| 缺失 visualNode/clickTargetNode | P0 | 自动点击可能点击错误节点（应点父节点而非 Icon） |
| 缺失 iconInfo 输出字段 | P0 | 方案第7.7节定义的完整图标输出格式 |
| 缺失图标可点击判断表 | P1 | 方案第7.9节 P0~P4 优先级规则未实现 |
| 缺失配置表关联 | P1 | 无法从 iconName 反推 itemId/itemName |

---

## 维度 4：工程态与运行态合并（方案第9章）

### 方案要求
- 合并成 `enhanced_ui_tree.json`
- 合并依据：P0 prefab instance id → P1 path suffix → P2 节点名+组件 → P3 文本+位置 → P4 人工绑定
- 输出包含 runtimePath + prefabPath + prefabNodePath + name + text + clickable + visible + screenRect + components + semanticGuess + confidence

### 当前实现
- ❌ **没有任何合并逻辑** — 全代码库搜索 "enhanced_ui_tree"、"merge_ui" 均无结果
- ❌ **没有 `enhanced_ui_tree.json` 输出**
- ❌ **没有 prefabPath ↔ runtimePath 匹配算法**

### 差距分析
| 差距项 | 严重度 | 说明 |
|--------|--------|------|
| 不存在任何合并脚本 | P0 | 工程态数据都不存在，自然无法合并 |
| 缺失匹配规则引擎 | P0 | P0~P4 多规则匹配未实现 |
| 缺失 semanticGuess 和 confidence | P0 | 方案要求每个节点有语义推断 |
| 缺失合并后的 unified 视图 | P1 | 无法在一个文件中看到工程态+运行态的完整信息 |

---

## 维度 5：映射草稿中文描述（方案第10章）

### 方案要求
- 自动生成 `element_mapping_draft.json`
- 每个草稿包含：displayName / chineseDescription / reviewHint / suggestedTestId / suggestedSemanticId / role / confidence / evidence / screenshotRef / highlightRect
- 中文描述生成规则：页面中文名 + 位置 + 外观/文本 + 元素类型 + 作用
- 页面中文名映射字典
- role 中文名映射字典
- 图标也应生成映射草稿（包含 visualNode/clickTargetNode/clickAction）

### 当前实现
- ❌ **`element_mapping.py` 存在但功能严重不足**：
  - 仅是一个 CRUD 管理器（增删改查）
  - ❌ **不自动生成草稿** — 没有语义推断逻辑
  - ❌ **不生成 `element_mapping_draft.json`**
  - ❌ **没有 displayName/chineseDescription/reviewHint 的自动生成**
  - ❌ **没有页面中文名字典**
  - ❌ **没有 role 中文名字典**
  - ❌ **没有 confidence 计算**
  - ❌ **没有 evidence 字段**
  - ❌ **没有图标映射草稿**
  - 实际上仅提供手动标注接口（通过 Web IDE 的 mapping 面板）

### 差距分析
| 差距项 | 严重度 | 说明 |
|--------|--------|------|
| 缺失草稿自动生成器 | P0 | 没有一个脚本根据运行态数据推断语义并生成草稿 |
| 缺失中文描述字段 | P0 | displayName/chineseDescription/reviewHint 全部缺失 |
| 缺失语义推断规则 | P0 | 方案第10.2节定义的 9 种信号+权重规则未实现 |
| 缺失页面中文名字典 | P1 | 方案第10.6节建议维护 |
| 缺失 role 中文名字典 | P1 | 方案第10.7节建议维护 |
| 缺失图标映射草稿 | P1 | 方案第10.8节的交互图标映射 |

---

## 维度 6：场景对象扫描（方案第13章）

### 方案要求
- 新增独立文件 `AutoSmokeSceneObjectExporter.cs`
- 采集：建筑/资源点/船/NPC/怪物/岛屿/引导目标
- 输出格式：objectId/name/path/worldPosition/screenRect/clickable
- worldPosition 为三维坐标，screenRect 为 `{x, y, width, height}` 对象
- 目标单位：建筑（Barracks）、资源点、Npc、Monster 等

### 当前实现
- ⚠️ **功能内嵌在 `AutoSmokeMetadataExporter.cs` 的 `ScanSceneObjects()` 方法中**（行 833-1164）
  - ✅ 扫描建筑和地图对象
  - ✅ 支持世界坐标 → 屏幕坐标映射
  - ✅ 可点击判断（Collider/IPointerClickHandler/EventTrigger）
  - ❌ **不是独立文件** — 方案要求独立 `AutoSmokeSceneObjectExporter.cs`
  - ❌ **输出格式不匹配**：缺少 objectId 字段，worldPosition 缺少原始三维坐标（仅 Round 后）
  - ❌ **缺少 NPC/怪物/岛屿/引导目标的专门分类**
  - ❌ **只扫描第一层子对象**（行 938：`i < parent.childCount && i < 5`），可能漏项
  - ❌ **缺少船/NPC的具体识别**

### 差距分析
| 差距项 | 严重度 | 说明 |
|--------|--------|------|
| 没有独立脚本文件 | P2 | 功能耦合在 MetadataExporter 中 |
| 缺少 objectId 字段 | P1 | 影响元素定位的唯一标识 |
| 缺失 NPC/怪物/岛屿/引导目标分类 | P1 | 当前只有 Building/MapObject/Resource/Monster/NPC 5 种 |
| 子对象只扫描 5 个 | P2 | 可能导致遗漏场景对象 |
| 输出格式为数组而非对象 | P2 | screenRect 输出格式不匹配方案要求 |

---

## 维度 7：页面关系图（方案第15章）

### 方案要求
- 每次自动探索记录：fromPage / action / element / toPage
- 最终输出：page_graph.json / page_graph.html
- 展示：页面入口/弹窗关系/返回路径/死路页面/危险操作入口

### 当前实现
- ❌ **没有任何页面关系图相关代码** — 全代码库搜索 "page_graph"、"fromPage"、"toPage" 无结果
- ❌ **没有自动探索逻辑** — 没有自动点击→检测页面变化→记录关系的流程
- ❌ **没有图标探索（方案第16章阶段七）** — 没有 icon→tips 关系记录
- ❌ **没有 `icon_interaction_map.json`**

### 差距分析
| 差距项 | 严重度 | 说明 |
|--------|--------|------|
| 不存在页面关系图 | P1 | 整个第15章功能缺失 |
| 不存在自动探索引擎 | P1 | 整个第16.6章自动探索阶段缺失 |
| 不存在图标探索 | P1 | 整个第16.7章图标Tips探索阶段缺失 |
| 不存在 icon_interaction_map | P1 | 图标点击后 Tips 关系无法记录 |

---

## 维度 8：验收标准（方案第17章）

### 方案要求（共 18 项验收）

#### UIE 工程态（4 项）
| 编号 | 场景 | 通过标准 | 当前状态 |
|------|------|---------|---------|
| UIE-001 | 扫描全部 prefab | 输出 project_ui_inventory.json | ❌ 未达标 |
| UIE-002 | 识别按钮 | Button 节点数量正确 | ❌ 未达标 |
| UIE-003 | 识别文本 | Text/TMP 文本可导出 | ❌ 未达标 |
| UIE-004 | Missing 检测 | Missing Script/Reference 可报告 | ❌ 未达标 |

#### UIR 运行态（4 项）
| 编号 | 场景 | 通过标准 | 当前状态 |
|------|------|---------|---------|
| UIR-001 | 主城 | 导出底部按钮、右侧活动、任务栏 | ⚠️ 部分达标（可导出 UI，但格式和字段不全） |
| UIR-002 | 背包 | 导出道具卡片、tab、使用按钮 | ⚠️ 部分达标 |
| UIR-003 | 奖励弹窗 | 导出确认按钮和奖励列表 | ⚠️ 部分达标 |
| UIR-004 | 建筑菜单 | 导出呼出按钮 | ⚠️ 部分达标 |

#### UIM 映射（4 项）
| 编号 | 场景 | 通过标准 | 当前状态 |
|------|------|---------|---------|
| UIM-001 | 背包使用按钮 | 生成 `Bag.UseButton` | ❌ 未达标（无自动草稿） |
| UIM-002 | 奖励确认 | 生成 `RewardPopup.ConfirmButton` | ❌ 未达标 |
| UIM-003 | 活动入口 | 生成对应 Activity testId | ❌ 未达标 |
| UIM-004 | 人工审核 | 状态可从 pending 改为 confirmed | ⚠️ 部分达标（Web IDE 可手动标注，但无 pending/confirmed 状态机） |

#### UII 图标（6 项）
| 编号 | 场景 | 通过标准 | 当前状态 |
|------|------|---------|---------|
| UII-001 | 背包道具图标 | 采集 itemId/itemName/spriteName/count | ❌ 未达标（无图标扫描） |
| UII-002 | 奖励弹窗图标 | 采集奖励 itemId/count，标记是否可点击 | ❌ 未达标 |
| UII-003 | 图标点击目标 | 正确区分 visualNode 和 clickTargetNode | ❌ 未达标 |
| UII-004 | 道具 Tips | 点击道具图标后记录 open_item_tips | ❌ 未达标 |
| UII-005 | 纯展示图标 | 不进入可点击元素映射 | ❌ 未达标 |
| UII-006 | 活动图标 | 生成活动入口 testId/semanticId | ❌ 未达标 |

---

## 综合优先级差距表

### P0 级（必须优先修复）

| # | 维度 | 差距项 | 缺失内容 | 建议修复方案 |
|---|------|--------|---------|------------|
| 1 | 工程态 | AutoSmokeUIPrefabScanner.cs 不存在 | Assets/**/*.prefab/.unity 全量扫描 | 新建 Editor 脚本，使用 AssetDatabase.FindAssets 遍历，提取 RectTransform/Button/Text/Image/Toggle/InputField 组件信息 |
| 2 | 工程态 | project_ui_inventory.json 不存在 | 整个工程态输出产物 | 在扫描脚本中序列化输出，包含方案第6.5节定义的所有字段 |
| 3 | 图标 | 图标扫描完全缺失 | spriteName/atlasName/iconType/visualNode/clickTargetNode | 在 MetadataExporter 中增加 ICON_SCAN 模式：读取 Image.sprite.name/SpriteAtlas，提取父节点点击属性 |
| 4 | 映射 | 映射草稿自动生成器不存在 | element_mapping_draft.json + 中文描述 | 新建 element_mapping_draft_generator.py，实现方案第10.2~10.5节的语义推断和中文描述生成 |
| 5 | 合并 | 工程态-运行态合并逻辑不存在 | enhanced_ui_tree.json + 匹配算法 | 新建 merge_ui_tree.py，实现 P0~P4 五级匹配规则 |
| 6 | 验收 | UIE-001~004 全部未达标 | 4 项工程态验收 | 完成 AutoSmokeUIPrefabScanner.cs 后自然达标 |
| 7 | 验收 | UII-001~006 全部未达标 | 6 项目标验收 | 完成图标扫描后自然达标 |

### P1 级（建议在 P0 完成后跟进）

| # | 维度 | 差距项 | 缺失内容 | 建议修复方案 |
|---|------|--------|---------|------------|
| 8 | 运行态 | gameContentRect 缺失 | 运行时需要 GameContent 相对坐标 | 在 CalcScreenRect 中同时计算相对 GameContent 的坐标 |
| 9 | 运行态 | sortingOrder/siblingIndex 缺失 | 影响 z-order 判断 | 在 ScanTransform 中增加 canvas.sortingOrder 和 transform.GetSiblingIndex() |
| 10 | 运行态 | raycastTarget 缺失 | 影响点击判断 | 读取 Graphic.raycastTarget/Image.raycastTarget |
| 11 | 运行态 | prefabSource 缺失 | 影响合并关联 | 使用 PrefabUtility.GetCorrespondingObjectFromSource 获取 |
| 12 | 运行态 | roleGuess 缺失 | 方案要求每个节点有角色猜测 | 在 InferType 后加 role 推断逻辑（primary_button/close_button/tab/etc） |
| 13 | 运行态 | 可见性判断缺少遮挡检测 | 可能导致 false positive | 在 IsVisible 中添加 RectTransformUtility.RectangleContainsScreenPoint 或 Renderer 遮挡检测 |
| 14 | 图标 | 图标可点击优先级表未实现 | 方案第7.9节 P0~P4 规则 | 实现 5 级图标可点击判断，输出 interactive_icon/display_icon/unknown_icon 分类 |
| 15 | 映射 | 页面中文名字典不存在 | 方案第10.6节 | 维护 page_chinese_names.json |
| 16 | 映射 | role 中文名字典不存在 | 方案第10.7节 | 维护 role_chinese_names.json |
| 17 | 映射 | evidence 字段缺失 | 自动推断依据 | 在草稿生成器中实现证据链记录 |
| 18 | 场景 | objectId 字段缺失 | 场景对象唯一标识 | 在 ScanSceneObjects 输出中增加 objectId |
| 19 | 场景 | NPC/怪物/引导目标识别不足 | 方案第13章要求 | 增加关键词列表和分类规则 |
| 20 | 验收 | UIM-001~003 未达标 | 映射草稿 | 完成草稿生成器后自然达标 |

### P2 级（后续优化）

| # | 维度 | 差距项 | 缺失内容 | 建议修复方案 |
|---|------|--------|---------|------------|
| 21 | 运行态 | 菜单项名称不匹配方案要求 | 中文 vs 英文 | 增加英文菜单项，保持与方案一致 |
| 22 | 运行态 | 输出路径不匹配方案规划 | %USERPROFILE% vs runtime/ui_tree/ | 增加配置项支持方案指定路径 |
| 23 | 运行态 | screenRect 格式数组 vs 对象 | 兼容性问题 | 增加可选的 `{x,y,w,h}` 对象格式输出 |
| 24 | 场景 | ScanSceneObjects 不是独立文件 | 不符合方案命名 | 拆分为 AutoSmokeSceneObjectExporter.cs |
| 25 | 场景 | 子对象只扫描 5 个 | 可能漏项 | 改为递归但跳过非建筑/非 MapObject 分支 |
| 26 | 验收 | UIM-004 审核状态机不完整 | pending/confirmed/modified/ignored/rejected | 在 element_mapping.py 和 Web IDE 中增加完整状态机 |
| 27 | 页面图 | 整个页面关系图缺失 | P1 功能 | 新建 page_graph_builder.py 和自动探索引擎 |
| 28 | 页面图 | icon_interaction_map 缺失 | 图标Tips探索 | 新建 auto_explorer.py 阶段七功能 |

---

## 总结结论

### 总体完成度：约 15%

| 维度 | 方案要求 | 当前实现 | 完成度 |
|------|---------|---------|--------|
| 1. 工程态扫描 | AutoSmokeUIPrefabScanner.cs + project_ui_inventory.json | 不存在 | **0%** |
| 2. 运行态导出 | AutoSmokeUITreeExporter.cs + 完整字段集 | AutoSmokeMetadataExporter.cs（字段缺 40%） | **60%** |
| 3. 图标采集 | spriteName/atlasName/visualNode/clickTargetNode | 不存在 | **0%** |
| 4. 工程态-运行态合并 | enhanced_ui_tree.json + 匹配算法 | 不存在 | **0%** |
| 5. 映射草稿中文描述 | element_mapping_draft.json + 中文字段 | element_mapping.py（仅 CRUD，无草稿） | **10%** |
| 6. 场景对象扫描 | AutoSmokeSceneObjectExporter.cs | ScanSceneObjects() 内嵌在 MetadataExporter | **40%** |
| 7. 页面关系图 | page_graph.json/html + 自动探索 | 不存在 | **0%** |
| 8. 验收标准 | 18 项 | ⚠️ UIR-001~004 约 50%，其余 14 项 0% | **~10%** |

### 核心结论

**当前实现了运行态 UI 导出（维度2）的约 60% 和场景对象扫描（维度6）的约 40%。** 其余 6 个维度基本缺失。

**最关键的差距（P0）：**
1. 工程态扫描完全不存在 → 无法获取 prefab 层面的 UI 信息
2. 图标采集完全不存在 → 无法处理 SLG 游戏最核心的图标交互
3. 映射草稿自动生成完全不存在 → 人工审核效率极低
4. 工程态-运行态合并不存在 → 无法获得完整的 UI 视图

**推荐 P0 修复顺序：**
1. 建立工程态扫描（按方案第6章）
2. 补齐运行态缺失字段（按方案第7章）
3. 实现图标采集（按方案第7.7-7.9章）
4. 实现合并逻辑（按方案第9章）
5. 实现映射草稿生成（按方案第10章）
