# AutoSmoke Target-Driven Mapping Implementation Plan

Updated: 2026-06-17

## 1. Goal

Build a target-driven mapping validation workbench in AutoSmoke IDE.

The workbench must start from automation targets required by test cases, not
from the full raw UI tree. The review flow is:

```text
target -> candidates -> runtime match -> highlight evidence
       -> visual confirmation -> test click -> click confirmation
       -> formal mapping
```

The first implementation scope is a minimum closed loop for one target at a
time. Bulk verification, formal export gates, case replay upgrades, and version
revalidation are later phases.

## 2. Hard Rules

1. Bulk generation only creates candidates.
2. Candidates are not trusted mappings.
3. A formal clickable mapping must have click evidence.
4. Page, panel, status, red-dot, and text assertion mappings must at least have
   visual evidence.
5. Runtime match and code semantics are evidence for recommendation, not final
   confirmation.
6. The default workbench entry must be the target list, not the raw UI node
   list.
7. Do not modify game business process code.
8. Keep IDE responses small; large scans must write result files and return
   summaries.

## 3. Current IDE Capabilities

Already implemented:

```text
UI metadata import
draft mapping list and detail
runtime UI refresh
runtime match
runtime discover
highlight screenshot generation
visual confirmation
test click
click confirmation
case import and run APIs
code semantic index generation
```

Partially implemented:

```text
mapping draft status lifecycle
runtime evidence persistence
code semantic evidence
large response limiting
prepare summary
```

Not implemented yet:

```text
target_name_catalog.json
mapping_task_queue.json
target-driven task APIs
candidate recommendation by target
Target Workbench UI
target-level evidence persistence
formal mapping export from target workflow
mapping gate before execution
case replay status upgrade
version revalidation
```

Deferred:

```text
bulk highlight
bulk safe click verification
formal mapping export gate
case_verified automatic upgrade
mapping gap report generation
stale mapping report
UI version revalidation queue
```

## 4. File Layers

Target and draft layer:

```text
AutoSmoke/metadata/target_name_catalog.json
AutoSmoke/metadata/mapping_task_queue.json
AutoSmoke/元数据/element_mapping_draft.json
```

Formal mapping layer:

```text
AutoSmoke/metadata/element_mapping_formal.json
```

Evidence layer:

```text
AutoSmoke/metadata/mapping_evidence.json
AutoSmoke/metadata/runtime_match_result.json
AutoSmoke/screenshots/mapping_review/
```

Rule:

```text
draft/task is editable
formal is executable
evidence explains trust
```

## 5. Phase 1 Scope

Phase 1 delivers a single-target closed loop:

1. Target task data model.
2. Manual target JSON import or form-based target add.
3. Candidate recommendation from existing mapping drafts, enhanced UI tree,
   runtime match result, and code semantics.
4. Target list API.
5. Target save, ignore, select candidate APIs.
6. Target Workbench UI under Prepare -> UI tree and element mapping.
7. Runtime match for the selected target candidate.
8. Highlight for the selected target candidate.
9. Visual confirmation result persisted to the target task.
10. Test click result persisted to the target task.

Phase 1 does not need to export formal mappings or run bulk click operations.

## 6. Target Task Contract

```json
{
  "targetId": "activity.login_gift.entry",
  "targetName": "login gift entry icon",
  "sourceCases": ["DL_RK_003"],
  "pageHint": "UiMain",
  "role": "entry",
  "elementType": "interactive_icon",
  "priority": "P0",
  "expectedBehavior": "click opens login gift main panel",
  "status": "pending_match",
  "candidates": [],
  "selectedDraftPath": "",
  "evidence": {}
}
```

Statuses:

```text
pending_match
candidate_found
runtime_matched
highlight_generated
visual_confirmed
click_confirmed
case_verified
blocked
ignored
```

Failure reasons must be explicit, for example:

```text
no_candidate
draft_path_missing
runtime_node_missing
invalid_screen_rect
highlight_failed
click_failed
duplicate_confirmed_candidate
```

## 7. Candidate Recommendation

Inputs:

```text
targetName
pageHint
role
elementType
priority
element_mapping_draft
enhanced_ui_tree
ui_code_semantics
runtime_match_result
```

Minimum scoring:

```text
name or description match: 0.25
pageId match:              0.20
role/elementType match:    0.20
code semantic match:       0.20
runtime exists:            0.15
```

Candidate shape:

```json
{
  "draftPath": "UIRoot/Panel/Button",
  "displayName": "Claim",
  "score": 0.86,
  "reasons": ["page_match", "role_match", "runtime_matched"],
  "risks": ["duplicate_name"]
}
```

## 8. Phase 1 APIs

```text
GET  /api/target/list
POST /api/target/import
POST /api/target/save
POST /api/target/ignore
POST /api/target/match_candidates
POST /api/target/select_candidate
POST /api/target/runtime_match
POST /api/target/highlight
POST /api/target/visual_confirm
POST /api/target/test_click
```

Use JSON request bodies. Do not put raw UI paths in URL path parameters.

## 9. Workbench UI

Location:

```text
Prepare page -> UI tree and element mapping module -> Target Workbench
```

Default columns:

```text
target name
source case
recommended candidate
confidence
status
next step
```

Detail view:

```text
Left: target list
Middle: candidate list and selected candidate
Right: evidence, runtime result, highlight image, click result
```

Next-step behavior:

```text
pending_match       -> match candidates
candidate_found     -> runtime match
runtime_matched     -> generate highlight
highlight_generated -> visual confirm
visual_confirmed    -> test click
click_confirmed     -> ready for formal mapping later
```

## 10. Acceptance Criteria

1. IDE shows a Target Workbench.
2. User can add or import at least one target.
3. System recommends candidates with reasons.
4. User can select a candidate.
5. User can run runtime match for that target.
6. User can generate a highlight image and confirm it.
7. User can run a test click and persist the result.
8. `mapping_task_queue.json` survives page refresh and IDE restart.

## 11. Later Phases

Phase 2: bulk highlight.

Phase 3: bulk safe click verification.

Phase 4: formal mapping export and uniqueness gate.

Phase 5: case replay loop and mapping gap report.

Phase 6: UI version revalidation and stale mapping report.
