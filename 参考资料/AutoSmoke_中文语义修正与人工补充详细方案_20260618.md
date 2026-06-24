# AutoSmoke 中文语义修正与人工补充详细方案

> 日期：2026-06-18  
> 目标：支持用户用准确中文描述修正元素语义，并由 IDE 自动更新 `targetName / displayName / semanticId / testId / role / pageId / elementType` 等字段。  
> 适用场景：自动生成语义不准确、候选匹配错误、需要人工补充目标、需要把人工确认结果反哺规则库。

---

## 1. 核心目标

当前问题示例：

```text
UIShop/Root/TopRes/ResItem_1
自动生成 semanticId = UIShop.查看/选择道具
实际语义 = 背包界面的金币途径按钮
```

期望 IDE 支持：

```text
用户输入：背包界面的金币途径按钮
IDE 自动生成：
targetName = 背包金币途径按钮
displayName = 背包-金币途径按钮
semanticId = bag.gold.source_button
testId = bag.gold.source.button 或保持原 testId
pageId = bag
role = resource_source
elementType = Button
```

核心原则：

```text
用户负责说明“它是什么”
IDE 负责推导“字段怎么填、是否唯一、保存到哪里、是否需要重验”
```

---

## 2. 功能入口设计

### 2.1 元素详情页入口

在目标详情 / 元素详情中增加：

```text
中文语义描述：
[ 背包界面的金币途径按钮 ]

[解析并预填] [保存修正] [保存并验证] [保存并反哺规则]
```

### 2.2 映射缺口页入口

在缺口项后增加：

```text
[重新匹配] [运行态发现] [手动补充] [中文语义修正] [忽略]
```

适用场景：

```text
无候选
候选语义错误
多个候选无法区分
slot 元素被泛化
代码语义不足
需要人工明确中文语义
```

---

## 3. 用户操作流程

### 3.1 语义修正流程

```text
1. 用户在目标/元素详情中选择一个元素
2. 输入中文语义描述
3. 点击“解析并预填”
4. IDE 展示解析结果预览
5. 用户确认或手动微调字段
6. IDE 执行唯一性检查
7. 用户选择保存方式
8. IDE 更新对应文件
9. IDE 根据需要重新验证
10. 用户选择是否反哺规则库
```

### 3.2 手动补充流程

```text
1. 用户在缺口页点击“手动补充”
2. IDE 自动带出目标名、来源用例、source_ref
3. 用户输入中文语义描述
4. IDE 自动解析字段
5. 用户选择定位方式：testId / semanticId / poco / text / template / 坐标
6. IDE 自动生成或预填定位值
7. 保存为草稿
8. 执行高亮/点击/用例验证
9. 通过后加入正式映射
```

---

## 4. 表单字段设计

### 4.1 简单模式

默认只展示：

| 字段 | 必填 | 示例 |
|---|---:|---|
| 中文语义描述 | 是 | 背包界面的金币途径按钮 |
| 所属页面 | 自动/可选 | 背包 |
| 元素类型 | 自动/可选 | 按钮 |
| 定位方式 | 手动补充时必填 | testId |
| 定位值 | 手动补充时必填 | bag.gold.source.button |

### 4.2 解析预览

点击“解析并预填”后显示：

```text
解析结果：

targetName:  背包金币途径按钮
displayName: 背包-金币途径按钮
semanticId:  bag.gold.source_button
testId:      bag.gold.source.button
pageId:      bag
role:        resource_source
elementType: Button

来源：
- 页面词：背包 → bag
- 对象词：金币 → gold
- 角色词：途径 → resource_source
- 类型词：按钮 → Button

影响文件：
- mapping_task_queue.json
- element_mapping_draft.json
- element_mapping_formal.json（当前为 confirmed 时）
- mapping_evidence.json

[确认保存] [修改字段] [取消]
```

### 4.3 高级模式

高级模式默认折叠：

```text
targetName
displayName
semanticId
testId
pageId
role
elementType
priority
source_ref
modifyReason
是否同步重命名 testId
是否反哺规则库
```

---

## 5. 字段生成规则

### 5.1 中文解析总流程

```text
中文描述
  → 分词/关键词识别
  → 页面识别
  → 对象识别
  → 角色识别
  → 类型识别
  → 生成 targetName/displayName
  → 生成 semanticId
  → 生成 testId 候选
  → 唯一性检查
  → 输出预览
```

### 5.2 词典规则

建议新增：

```text
E:/zdcs/AutoSmoke/metadata/semantic_dictionary.json
```

示例：

```json
{
  "schema_version": "semantic_dictionary.v1",
  "pages": {
    "背包": "bag",
    "商店": "shop",
    "登录好礼": "activity.login_gift",
    "七日签到": "activity.login_gift",
    "主城": "main_city",
    "奖励弹窗": "reward_popup"
  },
  "objects": {
    "金币": "gold",
    "粮食": "food",
    "钻石": "diamond",
    "入口": "entry",
    "红点": "red_dot",
    "奖励": "reward",
    "第1天": "day1",
    "第2天": "day2",
    "第7天": "day7"
  },
  "roles": {
    "途径": "resource_source",
    "来源": "resource_source",
    "领取": "claim",
    "关闭": "close",
    "确认": "confirm",
    "取消": "cancel",
    "返回": "back",
    "已领取": "claimed_state",
    "未解锁": "locked_state",
    "可领取": "claimable_state"
  },
  "types": {
    "按钮": "Button",
    "界面": "Panel",
    "面板": "Panel",
    "弹窗": "Popup",
    "文本": "Text",
    "图标": "Icon",
    "红点": "RedDot",
    "状态": "State",
    "格子": "Item"
  },
  "test_id_suffix": {
    "Button": "button",
    "Panel": "panel",
    "Popup": "popup",
    "Text": "text",
    "Icon": "icon",
    "RedDot": "red_dot",
    "State": "state",
    "Item": "item"
  }
}
```

### 5.3 targetName 规则

生成规则：

```text
targetName = 页面中文 + 对象中文 + 角色中文 + 类型中文
```

但要去掉冗余词：

```text
输入：背包界面的金币途径按钮
输出：背包金币途径按钮
```

### 5.4 displayName 规则

生成规则：

```text
displayName = 页面中文 + "-" + 对象/角色/类型中文
```

示例：

```text
背包-金币途径按钮
登录好礼-第1天奖励领取按钮
主城-登录好礼入口图标
```

### 5.5 semanticId 规则

推荐格式：

```text
{feature_or_page}.{object}.{role}
```

示例：

```text
bag.gold.source_button
bag.food.source_button
login_gift.entry_button
login_gift.day1.claim_button
login_gift.entry_red_dot
```

说明：

```text
semanticId 表达语义对象，可比 testId 更贴近业务。
semanticId 可以不直接用于执行，但应尽量唯一。
```

### 5.6 testId 规则

推荐格式：

```text
{domain}.{feature}.{object}.{role}
```

示例：

```text
bag.gold.source.button
bag.food.source.button
activity.login_gift.entry.button
activity.login_gift.day1.claim.button
```

默认策略：

```text
语义修正模式：不自动修改已有 testId
完整重命名模式：用户勾选后同步修改 testId
```

原因：

```text
修改 testId 会影响用例引用、evidenceRef、formal mapping key、历史报告。
```

---

## 6. 核心代码逻辑说明

以下为核心伪代码/实现规则，供后续开发使用。

### 6.1 中文语义解析

```python
def parse_chinese_semantic(desc: str, dictionary: dict) -> dict:
    desc = normalize_text(desc)

    page_cn, page_id = match_first(desc, dictionary["pages"])
    object_terms = match_all(desc, dictionary["objects"])
    role_cn, role = match_first(desc, dictionary["roles"])
    type_cn, element_type = match_first(desc, dictionary["types"])

    if not element_type:
        element_type = infer_type_by_role(role)

    object_id = build_object_id(object_terms)
    suffix = dictionary["test_id_suffix"].get(element_type, "element")

    target_name = build_target_name(page_cn, object_terms, role_cn, type_cn)
    display_name = build_display_name(page_cn, target_name)
    semantic_id = build_semantic_id(page_id, object_id, role, element_type)
    test_id = build_test_id(page_id, object_id, role, suffix)

    return {
        "targetName": target_name,
        "displayName": display_name,
        "semanticId": semantic_id,
        "testId": test_id,
        "pageId": page_id,
        "role": role,
        "elementType": element_type,
        "parseEvidence": {
            "page": page_cn,
            "objects": object_terms,
            "role": role_cn,
            "type": type_cn
        }
    }
```

### 6.2 文本归一化

```python
def normalize_text(text: str) -> str:
    text = text.strip()
    text = text.replace("界面的", "")
    text = text.replace("界面中", "")
    text = text.replace("页面的", "")
    text = text.replace("的", "")
    return text
```

### 6.3 对象 ID 生成

```python
def build_object_id(object_terms: list) -> str:
    # 输入: [("第1天", "day1"), ("奖励", "reward")]
    # 输出: day1.reward
    return ".".join([item["id"] for item in object_terms])
```

### 6.4 semanticId 生成

```python
def build_semantic_id(page_id, object_id, role, element_type):
    # page_id = "bag"
    # object_id = "gold"
    # role = "resource_source"
    # element_type = "Button"
    if role == "resource_source":
        return f"{page_id}.{object_id}.source_button"
    if role.endswith("_state"):
        return f"{page_id}.{object_id}.{role}"
    if element_type == "Button":
        return f"{page_id}.{object_id}.{role}_button"
    return f"{page_id}.{object_id}.{role}"
```

### 6.5 testId 生成

```python
def build_test_id(page_id, object_id, role, suffix):
    # semanticId 用下划线，testId 用点号
    role_part = role.replace("_", ".")

    if role == "resource_source":
        return f"{page_id}.{object_id}.source.{suffix}"
    if role.endswith("_state"):
        state = role.replace("_state", "")
        return f"{page_id}.{object_id}.{state}.state"
    return f"{page_id}.{object_id}.{role_part}.{suffix}"
```

### 6.6 唯一性检查

```python
def check_mapping_uniqueness(candidate, formal_mapping, draft_mapping, runtime_tree):
    issues = []
    test_id = candidate["testId"]
    semantic_id = candidate["semanticId"]
    page_id = candidate["pageId"]

    if test_id in formal_mapping:
        issues.append({
            "code": "duplicate_test_id_formal",
            "message": f"testId 已存在: {test_id}",
            "existing": formal_mapping[test_id]
        })

    draft_hits = find_by_field(draft_mapping, "testId", test_id)
    if draft_hits:
        issues.append({
            "code": "duplicate_test_id_draft",
            "message": f"草稿中已有相同 testId: {test_id}",
            "items": draft_hits
        })

    semantic_hits = find_by_field(formal_mapping, "semanticId", semantic_id)
    if len(semantic_hits) > 1:
        issues.append({
            "code": "duplicate_semantic_id",
            "message": f"semanticId 对应多个正式映射: {semantic_id}",
            "items": semantic_hits
        })

    runtime_hits = find_visible_runtime_hits(runtime_tree, test_id, page_id)
    if len(runtime_hits) > 1:
        issues.append({
            "code": "multi_visible_runtime_hit",
            "message": "同一运行态页面存在多个可见命中",
            "items": runtime_hits
        })

    return {
        "ok": len(issues) == 0,
        "issues": issues
    }
```

### 6.7 保存策略

```python
def save_semantic_correction(element_key, parsed, options):
    current = load_current_mapping(element_key)
    old = snapshot(current)

    update = {
        "targetName": parsed["targetName"],
        "displayName": parsed["displayName"],
        "semanticId": parsed["semanticId"],
        "pageId": parsed["pageId"],
        "role": parsed["role"],
        "elementType": parsed["elementType"],
        "modifiedBy": "user",
        "modifiedAt": now(),
        "modifyReason": "semantic_correction",
        "oldValues": old
    }

    if options.get("rename_test_id"):
        update["testId"] = parsed["testId"]
        update["renameImpact"] = compute_rename_impact(old["testId"], parsed["testId"])

    if current["status"] in ("click_confirmed", "case_verified", "manual_confirmed"):
        update_formal_mapping(element_key, update)
        update_mapping_evidence(element_key, update)
    else:
        update_draft_mapping(element_key, update)
        update_mapping_task(element_key, update)

    if options.get("revalidate"):
        enqueue_validation_task(element_key)

    if options.get("feed_rule"):
        add_or_update_semantic_rule(element_key, parsed, current)
```

---

## 7. 保存策略详解

### 7.1 草稿状态

如果元素当前是：

```text
auto_draft
pending
runtime_matched
modified
manual_added
```

则更新：

```text
mapping_task_queue.json
element_mapping_draft.json
```

状态变为：

```text
modified
```

并要求重新验证。

### 7.2 正式状态

如果元素当前是：

```text
visual_confirmed
click_confirmed
case_verified
manual_confirmed
```

则更新：

```text
element_mapping_formal.json
mapping_evidence.json
```

并写入修改记录：

```json
{
  "modifiedBy": "user",
  "modifiedAt": "2026-06-18T00:00:00+08:00",
  "modifyReason": "semantic_correction",
  "oldSemanticId": "UIShop.查看/选择道具",
  "newSemanticId": "bag.gold.source_button",
  "oldTargetName": "TopRes ResItem_1 item cell",
  "newTargetName": "背包金币途径按钮"
}
```

### 7.3 testId 是否同步修改

默认不修改 `testId`。

默认语义修正只改：

```text
targetName
displayName
semanticId
role
pageId
elementType
```

只有用户勾选：

```text
同步重命名 testId
```

才修改：

```text
testId
formal mapping key
evidenceRef
case step 引用
task queue 引用
```

界面必须提示：

```text
修改 testId 会影响用例引用、证据引用和历史报告。是否迁移？
```

---

## 8. 反哺规则库

### 8.1 作用

人工修正不应只影响当前元素，还应沉淀为自动生成规则，避免下次再错。

保存位置：

```text
E:/zdcs/AutoSmoke/metadata/semantic_mapping_rules.json
```

### 8.2 规则生成逻辑

如果当前元素具备明显 slot 特征：

```text
path = UIShop/Root/TopRes/ResItem_1
中文语义 = 背包界面的金币途径按钮
```

可生成：

```json
{
  "rule_id": "RULE_UI_SHOP_TOP_RES",
  "rule_type": "fixed_slot",
  "description": "UIShop 顶部资源途径按钮槽位语义映射",
  "match": {
    "pageId": "UIShop",
    "path_contains": "Root/TopRes",
    "node_regex": "ResItem_(\\d+)"
  },
  "slot_mapping": {
    "1": {
      "targetName": "背包金币途径按钮",
      "semanticId": "bag.gold.source_button",
      "testId": "bag.gold.source.button",
      "role": "resource_source",
      "elementType": "Button"
    }
  },
  "source": "manual_correction",
  "created_at": "2026-06-18T00:00:00+08:00"
}
```

### 8.3 反哺规则按钮

保存后提示：

```text
是否将本次修正沉淀为规则？

[生成槽位规则] [生成文本规则] [仅保存本元素] [取消]
```

---

## 9. API 设计建议

### 9.1 解析接口

```text
POST /api/mapping/semantic/parse
```

请求：

```json
{
  "description": "背包界面的金币途径按钮",
  "context": {
    "path": "UIShop/Root/TopRes/ResItem_1",
    "pageId": "UIShop",
    "currentTestId": "ui_shop.top_res.item_1.cell"
  }
}
```

响应：

```json
{
  "success": true,
  "parsed": {
    "targetName": "背包金币途径按钮",
    "displayName": "背包-金币途径按钮",
    "semanticId": "bag.gold.source_button",
    "testId": "bag.gold.source.button",
    "pageId": "bag",
    "role": "resource_source",
    "elementType": "Button"
  },
  "parseEvidence": {
    "page": "背包",
    "object": "金币",
    "role": "途径",
    "type": "按钮"
  },
  "warnings": []
}
```

### 9.2 唯一性检查接口

```text
POST /api/mapping/semantic/check_unique
```

请求：

```json
{
  "testId": "bag.gold.source.button",
  "semanticId": "bag.gold.source_button",
  "pageId": "bag"
}
```

响应：

```json
{
  "ok": false,
  "issues": [
    {
      "code": "duplicate_test_id_formal",
      "message": "testId 已存在",
      "existingPath": "UIShop/Root/TopRes/ResItem_1"
    }
  ]
}
```

### 9.3 保存修正接口

```text
POST /api/mapping/semantic/save
```

请求：

```json
{
  "elementKey": "ui_shop.top_res.item_1.cell",
  "description": "背包界面的金币途径按钮",
  "parsed": {
    "targetName": "背包金币途径按钮",
    "displayName": "背包-金币途径按钮",
    "semanticId": "bag.gold.source_button",
    "testId": "bag.gold.source.button",
    "pageId": "bag",
    "role": "resource_source",
    "elementType": "Button"
  },
  "options": {
    "rename_test_id": false,
    "revalidate": true,
    "feed_rule": true
  }
}
```

响应：

```json
{
  "success": true,
  "updatedFiles": [
    "element_mapping_formal.json",
    "mapping_evidence.json"
  ],
  "reviewStatus": "modified",
  "nextAction": "revalidate"
}
```

### 9.4 反哺规则接口

```text
POST /api/mapping/semantic/feed_rule
```

请求：

```json
{
  "elementPath": "UIShop/Root/TopRes/ResItem_1",
  "description": "背包界面的金币途径按钮",
  "ruleType": "fixed_slot",
  "parsed": {
    "semanticId": "bag.gold.source_button",
    "testId": "bag.gold.source.button",
    "targetName": "背包金币途径按钮"
  }
}
```

---

## 10. 具体示例

### 10.1 金币途径按钮

输入：

```text
背包界面的金币途径按钮
```

解析：

```json
{
  "targetName": "背包金币途径按钮",
  "displayName": "背包-金币途径按钮",
  "semanticId": "bag.gold.source_button",
  "testId": "bag.gold.source.button",
  "pageId": "bag",
  "role": "resource_source",
  "elementType": "Button"
}
```

默认保存：

```text
保留当前 testId：ui_shop.top_res.item_1.cell
更新 semanticId / targetName / displayName / role / pageId / elementType
```

如果用户选择同步重命名：

```text
ui_shop.top_res.item_1.cell → bag.gold.source.button
```

### 10.2 粮食途径按钮

输入：

```text
背包界面的粮食途径按钮
```

解析：

```json
{
  "targetName": "背包粮食途径按钮",
  "displayName": "背包-粮食途径按钮",
  "semanticId": "bag.food.source_button",
  "testId": "bag.food.source.button",
  "pageId": "bag",
  "role": "resource_source",
  "elementType": "Button"
}
```

---

## 11. 开发落地顺序

推荐按以下顺序实现：

```text
1. 新增 semantic_dictionary.json
2. 新增中文语义解析函数
3. 新增解析预览接口
4. 新增唯一性检查接口
5. 在目标/元素详情页加“中文语义描述”输入框
6. 支持保存修正到 draft/formal/evidence
7. 支持可选同步重命名 testId
8. 支持反哺 semantic_mapping_rules.json
9. 保存后自动进入重新验证流程
10. 在映射缺口页接入“中文语义修正”
```

---

## 12. 验收标准

### 12.1 基础验收

```text
输入“背包界面的金币途径按钮”
能自动生成正确 targetName/displayName/semanticId/pageId/role/elementType
```

### 12.2 保存验收

```text
草稿元素保存后进入 modified
formal 元素保存后同步更新 formal/evidence
保存前执行唯一性检查
```

### 12.3 重命名验收

```text
默认不修改 testId
勾选同步重命名后能提示影响范围
能迁移 formal key/evidenceRef/task queue/case 引用
```

### 12.4 规则反哺验收

```text
人工修正 ResItem_1 = 金币后
semantic_mapping_rules.json 中生成 fixed_slot 规则
下次自动生成不再使用泛化语义 UIShop.查看/选择道具
```

### 12.5 体验验收

```text
用户只输入一句中文描述即可完成大部分字段预填
高级字段可展开修改
保存后能一键高亮/验证
错误可回滚或重新编辑
```

---

## 13. 最终结论

中文语义修正能力是批量映射闭环中的人工兜底层。

它要做到：

```text
一句中文描述
  → 自动解析字段
  → 预览确认
  → 唯一性检查
  → 保存到正确文件
  → 重新验证
  → 可选反哺规则库
```

默认只修正语义字段，不自动改 `testId`。  
如果需要同步重命名 `testId`，必须显式确认并执行引用迁移。

