# AutoSmoke 映射文件拆分与相对路径改造详细方案

> 日期：2026-06-23  
> 目标：解决 `element_mapping_draft.json`、`element_mapping_formal.json`、`mapping_evidence.json` 后续元素过多导致的性能、维护和路径兼容问题。  
> 核心要求：小文件按所属界面命名并归类；所有代码和落盘数据禁止写死绝对路径；IDE 不能因为路径变化失效。

---

## 1. 背景与问题

当前 AutoSmoke 映射数据主要集中在 3 个文件：

```text
AutoSmoke/元数据/element_mapping_draft.json
AutoSmoke/metadata/element_mapping_formal.json
AutoSmoke/metadata/mapping_evidence.json
```

其中 `element_mapping_draft.json` 已经达到万级候选规模，后续随着项目 UI 元素继续增加，会出现：

```text
1. IDE 首屏加载慢
2. 搜索和筛选慢
3. 每次保存都重写大 JSON
4. evidence 越积越大
5. 人工确认时容易卡顿
6. Git / 文件对比 / 回滚困难
7. 路径一旦改动，IDE 和执行器容易找不到文件
```

因此需要把大文件改成：

```text
索引文件 + 按界面拆分的小文件 + 按 testId 拆分的证据文件 + 统一路径解析层
```

---

## 2. 总体设计原则

### 2.1 存储原则

```text
draft 按所属界面 pageId 拆分
formal 按所属界面 pageId + global 拆分
evidence 按 testId 单文件拆分
index 负责查找
旧 3 个 JSON 只作为兼容导出物
```

### 2.2 路径原则

```text
所有代码禁止写死绝对路径
所有 JSON 禁止长期保存绝对路径
所有路径通过 MappingStore / PathResolver 统一解析
文件内保存 relative path 或 logical ref
绝对路径只允许运行时临时生成，不允许落盘
```

禁止：

```python
"E:\\zdcs\\AutoSmoke\\metadata\\element_mapping_formal.json"
"E:\\zdcs\\AutoSmoke\\metadata\\mapping_evidence.json"
"E:\\zdcs\\AutoSmoke\\元数据\\element_mapping_draft.json"
```

推荐：

```python
store = MappingStore(project_root=get_project_root())
entry = store.get_formal_by_testid(test_id)
```

或：

```python
path = resolver.metadata_path("mapping_store/formal/by_page/bag.json")
```

### 2.3 IDE 兼容原则

```text
前端 API 尽量不改
后端 API 内部切换到 MappingStore
旧 draft_path 参数继续兼容
evidenceRef 保持稳定
testId 不因文件拆分而变化
文件名只是存储名，不是业务 ID
```

---

## 3. 新目录结构

新增主存储目录：

```text
AutoSmoke/metadata/mapping_store/
├── manifest.json
├── indexes/
│   ├── page.index.json
│   ├── draft.index.json
│   ├── formal.index.json
│   ├── evidence.index.json
│   ├── testid.index.json
│   └── semantic.index.json
├── pages/
│   └── page_name_dictionary.json
├── draft/
│   ├── by_page/
│   │   ├── bag.json
│   │   ├── artifact.json
│   │   ├── shop.json
│   │   ├── main_city.json
│   │   ├── unknown.json
│   │   └── debug.json
│   └── queues/
│       ├── pending.json
│       ├── needs_review.json
│       ├── ignored.json
│       └── rejected.json
├── formal/
│   ├── by_page/
│   │   ├── bag.json
│   │   ├── artifact.json
│   │   ├── shop.json
│   │   └── main_city.json
│   └── global/
│       ├── common_dialog.json
│       ├── top_bar.json
│       └── navigation.json
└── evidence/
    ├── by_page/
    │   ├── bag.json
    │   └── artifact.json
    ├── by_testid/
    │   ├── bag/
    │   │   ├── bag_use_button.json
    │   │   └── bag_resource_tab_button.json
    │   └── artifact/
    │       └── artifact_upgrade_enhance_button.json
    └── assets/
        ├── highlights/
        ├── screenshots/
        └── click_logs/
```

旧文件保留：

```text
AutoSmoke/元数据/element_mapping_draft.json
AutoSmoke/metadata/element_mapping_formal.json
AutoSmoke/metadata/mapping_evidence.json
```

旧文件定位：

```text
兼容导出物
迁移前兜底
老模块临时读取
```

不允许新旧两套同时作为主数据源。

---

## 4. 页面命名与中文转英文规则

### 4.1 页面文件命名

小文件按照所属界面的英文 `pageId` 命名：

```text
背包界面      -> bag.json
神器界面      -> artifact.json
商城界面      -> shop.json
任务界面      -> task.json
主城界面      -> main_city.json
联盟科技界面  -> alliance_tech.json
未知界面      -> unknown.json
调试界面      -> debug.json
```

文件名规则：

```text
小写英文
单词用下划线
不能使用中文
不能使用 Unity runtime path
不能使用随机 hash 作为页面名
无法识别时进入 unknown.json
Debug / Framework / GraphicDebug 等进入 debug.json
```

### 4.2 页面字典

新增：

```text
AutoSmoke/metadata/mapping_store/pages/page_name_dictionary.json
```

格式：

```json
{
  "schema_version": "page_name_dictionary.v1",
  "updated_at": "2026-06-23T00:00:00+08:00",
  "pages": [
    {
      "pageId": "bag",
      "displayName": "背包界面",
      "aliases": [
        "背包",
        "道具背包",
        "物品界面"
      ],
      "files": {
        "draft": "mapping_store/draft/by_page/bag.json",
        "formal": "mapping_store/formal/by_page/bag.json"
      }
    },
    {
      "pageId": "artifact",
      "displayName": "神器界面",
      "aliases": [
        "神器",
        "神器功能",
        "神器养成"
      ],
      "files": {
        "draft": "mapping_store/draft/by_page/artifact.json",
        "formal": "mapping_store/formal/by_page/artifact.json"
      }
    }
  ]
}
```

### 4.3 IDE 保存时 pageId 推断顺序

当用户在 IDE 中输入或修改中文 `targetName`，例如：

```text
神器界面强化按钮
背包界面金币途径按钮
联盟科技界面捐献按钮
```

按以下优先级推断页面：

```text
1. 用户手动选择 pageId，优先使用
2. targetName / chineseDescription 命中 page_name_dictionary
3. draft/formal 原本已有 pageId，沿用
4. prefabRoot / runtimePath / code semantic 能推断 pageId
5. 无法识别，进入 unknown.json，并提示人工确认
```

如果是新界面，例如：

```text
联盟科技界面捐献按钮
```

IDE 应提示：

```text
检测到新界面：联盟科技界面
建议 pageId：alliance_tech
建议文件：mapping_store/formal/by_page/alliance_tech.json
是否创建？
```

确认后：

```text
1. 创建 draft/by_page/alliance_tech.json
2. 创建 formal/by_page/alliance_tech.json
3. 写入 page_name_dictionary.json
4. 更新 page.index.json
5. 当前元素保存到对应页面文件
```

---

## 5. draft 拆分设计

### 5.1 存储位置

```text
AutoSmoke/metadata/mapping_store/draft/by_page/{pageId}.json
```

示例：

```text
AutoSmoke/metadata/mapping_store/draft/by_page/bag.json
AutoSmoke/metadata/mapping_store/draft/by_page/artifact.json
AutoSmoke/metadata/mapping_store/draft/by_page/unknown.json
AutoSmoke/metadata/mapping_store/draft/by_page/debug.json
```

### 5.2 文件格式

```json
{
  "schema_version": "element_mapping_draft.page.v1",
  "pageId": "bag",
  "displayName": "背包界面",
  "updated_at": "2026-06-23T00:00:00+08:00",
  "count": 2,
  "drafts": {
    "DRAFT_bag_use_button": {
      "draftId": "DRAFT_bag_use_button",
      "path": "UIShop/Root/Shop/Content/Bag/Buttom_Other/UsedBtn",
      "nodeName": "UsedBtn",
      "targetName": "背包道具使用按钮",
      "suggestedTestId": "bag.use.button",
      "suggestedSemanticId": "bag.use.button",
      "pageId": "bag",
      "role": "use",
      "elementType": "Button",
      "reviewStatus": "pending",
      "source": "project_inventory"
    }
  },
  "groups": {
    "top_bar": [],
    "tabs": [],
    "content": [],
    "bottom_actions": [
      "DRAFT_bag_use_button"
    ],
    "navigation": []
  }
}
```

### 5.3 分组规则

页面文件内部按区域归类：

```text
top_bar          顶部资源栏
tabs             页签区
content          主内容区
bottom_actions   底部操作区
navigation       返回/关闭/导航
dialogs          弹窗
list_templates   动态列表模板
unknown          未归类
```

### 5.4 draft 状态队列

同时维护队列索引：

```text
mapping_store/draft/queues/pending.json
mapping_store/draft/queues/needs_review.json
mapping_store/draft/queues/ignored.json
mapping_store/draft/queues/rejected.json
```

队列文件只保存轻量引用：

```json
{
  "schema_version": "draft_queue.v1",
  "status": "ignored",
  "items": [
    {
      "draftId": "DRAFT_debug_btn_tab_info",
      "pageId": "debug",
      "draftPath": "mapping_store/draft/by_page/debug.json",
      "reason": "debug_ui_not_in_scope"
    }
  ]
}
```

---

## 6. formal 拆分设计

### 6.1 存储位置

普通页面元素：

```text
AutoSmoke/metadata/mapping_store/formal/by_page/{pageId}.json
```

跨页面通用元素：

```text
AutoSmoke/metadata/mapping_store/formal/global/{scope}.json
```

示例：

```text
formal/by_page/bag.json
formal/by_page/artifact.json
formal/global/common_dialog.json
formal/global/top_bar.json
```

### 6.2 文件格式

```json
{
  "schema_version": "element_mapping_formal.page.v1",
  "pageId": "bag",
  "displayName": "背包界面",
  "updated_at": "2026-06-23T00:00:00+08:00",
  "mappings": {
    "bag.use.button": {
      "testId": "bag.use.button",
      "semanticId": "bag.use.button",
      "targetName": "背包道具使用按钮",
      "displayName": "背包-使用按钮",
      "pageId": "bag",
      "role": "use",
      "elementType": "Button",
      "locator": {
        "type": "runtimePath",
        "value": "DeepUI/LayerUI/UIShop(Clone)_UIShopPop/Root/Shop/Content/Bag/Buttom_Other/UsedBtn"
      },
      "fallbackLocators": [],
      "reviewStatus": "click_confirmed",
      "evidenceRef": "EVIDENCE_bag.use.button"
    }
  },
  "groups": {
    "tabs": [
      "bag.resource.tab.button",
      "bag.speedup.tab.button"
    ],
    "content": [
      "bag.prop_item.click_area"
    ],
    "bottom_actions": [
      "bag.use.button"
    ],
    "navigation": [
      "bag.back.button"
    ]
  }
}
```

### 6.3 formal 准入状态

只有以下状态允许进入 formal：

```text
visual_confirmed
click_confirmed
case_verified
manual_confirmed
collection_confirmed
template
```

以下状态不能进入 formal：

```text
pending
needs_review
ignored
rejected
blocked
auto_draft
runtime_matched
```

---

## 7. evidence 拆分设计

### 7.1 存储位置

每个 `testId` 一个 evidence 文件：

```text
AutoSmoke/metadata/mapping_store/evidence/by_testid/{pageId}/{safeTestId}.json
```

示例：

```text
mapping_store/evidence/by_testid/bag/bag_use_button.json
mapping_store/evidence/by_testid/artifact/artifact_upgrade_enhance_button.json
```

### 7.2 文件格式

```json
{
  "schema_version": "mapping_evidence.item.v1",
  "evidenceRef": "EVIDENCE_bag.use.button",
  "testId": "bag.use.button",
  "semanticId": "bag.use.button",
  "targetName": "背包道具使用按钮",
  "pageId": "bag",
  "updated_at": "2026-06-23T00:00:00+08:00",
  "structure": {
    "path": "UIShop/Root/Shop/Content/Bag/Buttom_Other/UsedBtn",
    "pageId": "bag",
    "elementType": "Button"
  },
  "runtime": {
    "matched": true,
    "runtimePath": "Root/Shop/Content/Bag/Buttom_Other/UsedBtn",
    "screenRect": [
      380,
      2376,
      790,
      2527
    ],
    "matchScore": 0.95
  },
  "visual": {
    "confirmed": true,
    "highlightImage": "mapping_store/evidence/assets/highlights/bag_use_button.png"
  },
  "click": {
    "confirmed": true,
    "result": "PASS",
    "method": "unity_event_system",
    "detailRef": "mapping_store/evidence/assets/click_logs/bag_use_button_20260623.json"
  }
}
```

### 7.3 evidence 资产路径

图片、日志、点击详情必须保存相对路径：

推荐：

```json
{
  "highlightImage": "mapping_store/evidence/assets/highlights/bag_use_button.png",
  "detailRef": "mapping_store/evidence/assets/click_logs/bag_use_button_20260623.json"
}
```

禁止：

```json
{
  "highlightImage": "E:\\zdcs\\AutoSmoke\\screenshots\\mapping_review\\20260618_145622_highlight.png"
}
```

---

## 8. 索引文件设计

### 8.1 manifest.json

```json
{
  "schema_version": "mapping_store.v1",
  "store_version": 1,
  "layout": "page_sharded_mapping_store",
  "updated_at": "2026-06-23T00:00:00+08:00",
  "files": {
    "page_index": "mapping_store/indexes/page.index.json",
    "draft_index": "mapping_store/indexes/draft.index.json",
    "formal_index": "mapping_store/indexes/formal.index.json",
    "evidence_index": "mapping_store/indexes/evidence.index.json",
    "testid_index": "mapping_store/indexes/testid.index.json",
    "semantic_index": "mapping_store/indexes/semantic.index.json",
    "page_dictionary": "mapping_store/pages/page_name_dictionary.json"
  }
}
```

### 8.2 page.index.json

```json
{
  "schema_version": "mapping_index.page.v1",
  "pages": {
    "bag": {
      "displayName": "背包界面",
      "draftPath": "mapping_store/draft/by_page/bag.json",
      "formalPath": "mapping_store/formal/by_page/bag.json",
      "draftCount": 420,
      "mappingCount": 32,
      "confirmedCount": 18,
      "ignoredCount": 80
    }
  }
}
```

### 8.3 testid.index.json

```json
{
  "schema_version": "mapping_index.testid.v1",
  "items": {
    "bag.use.button": {
      "pageId": "bag",
      "formalPath": "mapping_store/formal/by_page/bag.json",
      "evidencePath": "mapping_store/evidence/by_testid/bag/bag_use_button.json",
      "reviewStatus": "click_confirmed"
    }
  }
}
```

### 8.4 semantic.index.json

```json
{
  "schema_version": "mapping_index.semantic.v1",
  "items": {
    "bag.use.button": [
      {
        "testId": "bag.use.button",
        "pageId": "bag",
        "formalPath": "mapping_store/formal/by_page/bag.json"
      }
    ]
  }
}
```

---

## 9. 统一 MappingStore 设计

### 9.1 必须新增统一存储层

新增：

```text
AutoSmoke/元数据/mapping_store.py
```

所有 IDE、用例执行器、target 定位器都必须通过它读写映射数据。

禁止业务代码直接读写：

```text
element_mapping_draft.json
element_mapping_formal.json
mapping_evidence.json
mapping_store/formal/by_page/*.json
mapping_store/evidence/by_testid/**/*.json
```

### 9.2 核心接口

```python
class MappingStore:
    def __init__(self, project_root=None):
        ...

    def list_pages(self) -> dict:
        ...

    def resolve_page_id(self, target_name: str, current_page_id: str = "") -> dict:
        ...

    def list_drafts(self, page_id="", status="", keyword="", limit=300, offset=0) -> dict:
        ...

    def get_draft(self, draft_id_or_path: str) -> dict:
        ...

    def save_draft(self, draft: dict) -> dict:
        ...

    def ignore_draft(self, draft_id_or_path: str, reason: str) -> dict:
        ...

    def reject_draft(self, draft_id_or_path: str, reason: str) -> dict:
        ...

    def get_formal_by_testid(self, test_id: str) -> dict:
        ...

    def upsert_formal(self, item: dict) -> dict:
        ...

    def list_formal_by_page(self, page_id: str) -> dict:
        ...

    def get_evidence(self, evidence_ref: str = "", test_id: str = "") -> dict:
        ...

    def upsert_evidence(self, evidence: dict) -> dict:
        ...

    def rebuild_indexes(self) -> dict:
        ...

    def export_legacy_files(self) -> dict:
        ...
```

### 9.3 读取优先级

```text
1. 如果 mapping_store/manifest.json 存在，读取新分片
2. 如果新分片不存在，fallback 旧 3 个 JSON
3. 如果新旧都不存在，返回空结构
```

### 9.4 写入优先级

```text
1. 默认写 mapping_store
2. 更新 indexes
3. 可选调用 export_legacy_files()
4. 不直接写旧文件作为主存储
```

---

## 10. 相对路径与逻辑引用规范

### 10.1 logical ref

推荐在数据中保存逻辑引用：

```text
formal://bag/bag.use.button
evidence://bag/bag.use.button
asset://highlights/bag_use_button.png
draft://bag/DRAFT_bag_use_button
```

示例：

```json
{
  "formalRef": "formal://bag/bag.use.button",
  "evidenceRef": "EVIDENCE_bag.use.button",
  "assetRef": "asset://highlights/bag_use_button.png"
}
```

### 10.2 relative path

当必须保存路径时，只保存相对 `AutoSmoke/metadata` 的路径：

```text
mapping_store/formal/by_page/bag.json
mapping_store/evidence/by_testid/bag/bag_use_button.json
mapping_store/evidence/assets/highlights/bag_use_button.png
```

### 10.3 禁止落盘绝对路径

禁止：

```text
E:\zdcs\AutoSmoke\metadata\element_mapping_formal.json
E:\zdcs\AutoSmoke\metadata\mapping_evidence.json
E:\zdcs\AutoSmoke\screenshots\mapping_review\xxx.png
```

迁移时如果遇到旧绝对路径，必须转换：

```text
E:\zdcs\AutoSmoke\screenshots\mapping_review\20260618_145622_highlight.png
→ screenshots/mapping_review/20260618_145622_highlight.png
```

或者复制到新资产目录：

```text
mapping_store/evidence/assets/highlights/bag_use_button_20260618.png
```

---

## 11. 现有代码改造范围

### 11.1 `AutoSmoke/元数据/element_mapping.py`

当前职责：

```text
生成 draft
维护 self._mappings
导出 element_mapping_draft.json
```

改造：

```text
1. 引入 MappingStore
2. export_drafts() 写入 mapping_store/draft/by_page/*.json
3. self._mappings 只作为当前页缓存或兼容缓存
4. save/load 保持兼容旧文件
5. export_legacy_files() 时才生成旧 element_mapping_draft.json
```

### 11.2 `AutoSmoke/IDE/debug_panel.py`

涉及接口：

```text
GET  /api/mapping/drafts
GET  /api/mapping/drafts/<draft_path>
POST /api/mapping/drafts/<draft_path>/save
POST /api/mapping/drafts/<draft_path>/confirm
POST /api/mapping/drafts/<draft_path>/reject
POST /api/mapping/drafts/<draft_path>/ignore
POST /api/mapping/drafts/<draft_path>/test_click
POST /api/mapping/drafts/<draft_path>/visual_confirm
```

改造：

```text
1. GET /api/mapping/drafts 改为 store.list_drafts(...)
2. GET /api/mapping/drafts/<id> 改为 store.get_draft(...)
3. save 改为 store.save_draft(...)
4. confirm 改为 store.upsert_formal(...) + store.upsert_evidence(...)
5. reject / ignore 改为 store.reject_draft / store.ignore_draft
6. 保留 draft_path 参数兼容，内部映射为 draftId
```

### 11.3 `AutoSmoke/用例层/case_step_executor.py`

当前硬编码读取：

```text
metadata/element_mapping_formal.json
metadata/mapping_evidence.json
```

改造：

```python
store = MappingStore(project_root=Path(CONFIG_DIR))
entry = store.get_formal_by_testid(test_id)
evidence_item = store.get_evidence(evidence_ref, test_id)
```

formal gate 逻辑保持：

```text
reviewStatus 是否允许
evidenceRef 是否存在
locator 是否存在
revalidateStatus 是否 stale/failed
```

### 11.4 `AutoSmoke/元数据/target_locator.py`

当前：

```text
_load_formal_mapping(testid) 直接读取 element_mapping_formal.json
```

改造：

```text
_load_formal_mapping(testid) 改为 MappingStore.get_formal_by_testid(testid)
screenRect / locator 解析逻辑不变
```

### 11.5 `AutoSmoke/元数据/target_catalog.py`

当前 `mapping_task_queue.json` 中存在绝对路径字段：

```text
formalPath
evidencePath
recommendationPath
```

改造：

```text
1. 新 task 不再保存绝对 formalPath/evidencePath
2. 改为保存 logical ref
3. 旧字段保留兼容，但不作为主引用
4. 展示路径时通过 MappingStore.resolve_paths() 生成
```

推荐：

```json
{
  "formalRef": "formal://bag/bag.use.button",
  "evidenceRef": "EVIDENCE_bag.use.button",
  "recommendationRef": "recommendation://target.runtime.xxx"
}
```

---

## 12. IDE 读取策略

### 12.1 当前问题

当前 IDE 容易出现：

```text
启动时加载全量 draft
搜索时遍历全量 _mappings
保存时写回大文件
```

### 12.2 新策略

```text
1. IDE 启动只读取 manifest + indexes
2. 左侧展示 page / status / count 汇总
3. 用户点击某个页面后加载 draft/by_page/{pageId}.json
4. 用户点击某个正式映射后加载对应 evidence 文件
5. 保存时只写单个 page 文件或单个 evidence 文件
```

首屏加载文件：

```text
mapping_store/manifest.json
mapping_store/indexes/page.index.json
mapping_store/indexes/draft.index.json
mapping_store/indexes/formal.index.json
```

不再首屏加载：

```text
14155 条 draft
所有 formal
所有 evidence
所有 click detail
```

---

## 13. 保存流程

### 13.1 保存中文 targetName

```text
1. 用户输入：神器界面强化按钮
2. IDE 调用 semantic_correction
3. 解析 pageNameZh = 神器界面
4. MappingStore.resolve_page_id() 得到 pageId = artifact
5. 如果 artifact 文件不存在，创建页面文件
6. 保存 draft/formal 到 artifact.json
7. 更新 page_name_dictionary
8. 更新 indexes
```

### 13.2 draft 确认为 formal

```text
1. 读取 draft/by_page/{pageId}.json
2. 找到 draft
3. 生成 testId / semanticId
4. 写 formal/by_page/{pageId}.json
5. 写 evidence/by_testid/{pageId}/{safeTestId}.json
6. 更新 testid.index.json
7. 更新 semantic.index.json
8. 更新 page.index.json
9. draft 标记 confirmed 或 moved_to_formal
10. 可选导出旧 element_mapping_formal.json / mapping_evidence.json
```

### 13.3 忽略元素

```text
1. draft.reviewStatus = ignored
2. 写 ignoredReason / ignoredAt
3. 保留在原 page draft 文件
4. 同步更新 draft/queues/ignored.json
5. 不进入 formal
6. 不要求 evidence
```

---

## 14. 动态列表元素处理

背包格子、奖励列表、商城商品等动态列表，不要为每个实例无限生成 formal。

推荐 formal 保存模板：

```json
{
  "testId": "bag.prop_item.click_area",
  "semanticId": "bag.prop_item.click_area",
  "targetName": "背包道具点击区",
  "pageId": "bag",
  "role": "item_click",
  "elementType": "Button",
  "locator": {
    "type": "dynamicList",
    "value": "Root/Shop/Content/Bag/ScrollView/ViewPort/Content"
  },
  "collection": {
    "type": "dynamic_list",
    "collectionId": "collection.bag.prop_item.click_area",
    "containerPath": "Root/Shop/Content/Bag/ScrollView/ViewPort/Content",
    "itemPattern": "Item(Clone)/PropItem_{index}/ClickContent",
    "semanticPattern": "bag.prop_item_{index}.click_area",
    "targetNamePattern": "背包第{index}个道具点击区",
    "indexBase": 1
  },
  "reviewStatus": "template"
}
```

规则：

```text
列表存模板
可见实例存 evidence
不为每个历史/不可见列表项生成 formal
```

---

## 15. 迁移步骤

### 阶段一：新增 MappingStore

```text
1. 新增 AutoSmoke/元数据/mapping_store.py
2. 支持读取旧 3 个 JSON
3. 支持写新 mapping_store 目录
4. 支持 export_legacy_files()
5. 不改 IDE 前端
```

验收：

```text
旧文件存在时，IDE 行为不变
新 store 存在时，MappingStore 能读取同样的 draft/formal/evidence
```

### 阶段二：迁移 draft

```text
1. element_mapping_draft.json 按 pageId 拆到 draft/by_page
2. 生成 draft.index.json / page.index.json
3. GET /api/mapping/drafts 改为按页加载
4. IDE 列表默认只加载当前 page 或 limit
```

验收：

```text
IDE 打开不再一次加载 14155 条
搜索/筛选仍可用
保存 draft 不重写 14MB 大文件
```

### 阶段三：迁移 evidence

```text
1. mapping_evidence.json 拆成 evidence/by_testid
2. click.detail 拆到 assets/click_logs
3. evidence.index.json 建立 evidenceRef -> file 映射
4. formal 中 evidenceRef 不变
```

验收：

```text
visual_confirm / click_confirm 仍能回写 evidence
case_step_executor 能找到 evidence
旧 mapping_evidence.json 可导出
```

### 阶段四：迁移 formal

```text
1. formal 按 pageId / global 拆分
2. 生成 testid.index / semantic.index
3. target_locator 和 case_step_executor 改为 MappingStore
```

验收：

```text
用例执行 testId 仍可定位
formal gate 仍可检查 reviewStatus/evidence/locator
```

### 阶段五：清理硬编码路径

```text
1. debug_panel.py 所有 mapping 文件读写改 MappingStore
2. case_step_executor.py 改 MappingStore
3. target_locator.py 改 MappingStore
4. target_catalog.py 不再写绝对 formalPath/evidencePath
5. 旧文件只在 export_legacy_files 时生成
```

---

## 16. 验收标准

### 16.1 路径验收

```text
1. 代码中没有写死 E:\zdcs 这类绝对路径
2. 新 JSON 中没有 E:\zdcs 这类绝对路径
3. evidence 图片和日志使用相对路径
4. mapping_task_queue 新记录不保存绝对 formalPath/evidencePath
5. 换目录运行时 MappingStore 可以重新解析路径
```

### 16.2 IDE 验收

```text
1. IDE 首屏可以正常打开
2. 页面列表按 pageId 展示
3. 点击页面后只加载该页面 draft
4. 修改中文 targetName 后能自动进入对应页面文件
5. 新界面能提示创建 pageId
6. 保存/确认/忽略/拒绝功能正常
7. 高亮确认和点击确认仍能写入 evidence
```

### 16.3 执行验收

```text
1. 用例执行通过 testId 能找到 formal
2. formal gate 能找到 evidence
3. locator 能正常解析
4. reviewStatus 准入逻辑不变
5. 旧文件导出后老模块仍可读取
```

---

## 17. 最终结论

最终推荐方案：

```text
真实数据源：AutoSmoke/metadata/mapping_store/
draft：按所属界面 pageId 拆分
formal：按所属界面 pageId + global 拆分
evidence：按 testId 单文件拆分
页面命名：由中文 targetName / pageName 通过 page_name_dictionary 解析
路径管理：代码和 JSON 禁止绝对路径，统一走 MappingStore / PathResolver
兼容策略：旧 3 个 JSON 保留为导出物
IDE 改造：前端 API 尽量不变，后端统一接 MappingStore
```

一句话：

```text
小文件按界面归类是正确方向，但必须先建立统一 MappingStore 和相对路径规范；否则文件一拆，IDE、用例执行、target_locator、mapping_task_queue 都会被旧路径硬编码拖住。
```
