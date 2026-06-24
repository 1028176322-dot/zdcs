# AutoSmoke 项目笔记

## 开发规范
- **修改 IDE 文件前必须备份**：修改 `debug_panel.py` 前先执行 `cp ...py ...py.bak.YYYYMMDD`
- Python 3.13：大小写敏感导入，目录名必须与 import 语句完全匹配
- Unity C# 脚本部署：修改后同时更新 `tools/` 和 `Assets/Editor/` 两份
- MODIFYING `IDE/debug_panel.py` REQUIRES BACKUP FIRST
## 2026-06-16 ����������¼
- �Ѷ�ȡ��ȷ�ϼ����ļ��� IDE �����������ط������� `AutoSmoke/IDE/debug_panel.py`��
- ��ִ�б��ݣ�`E:/zdcs/AutoSmoke/IDE/debug_panel.py.bak.20260616102548`��
- �ƻ������㣺�޸�ǰ�˽ӿڵ�����·�ɲ�һ�£�����ҳ���ϵͼ�������������֡�׼��/ִ��/�����һ��ջ���

2026-06-16 10:35:46 ���£���ʼִ��P0-1ִ��һ���Է������� debug_panel.py ���У���������ִ�������ĳ־û��ļ����д/��һ������������ /api/case/context��/api/case/import|list|validate|run|run_batch ͳһ�������Ľ��� path/stepField/caseIdField/sheet����������ǰ/������д�����ģ�ǰ������ collectCaseCtx()��ִ��/����/У��ǰͬ�������ģ�run �� run_batch ����������� payload��

- 2026-06-16 10:48:00 �������������� P0-2 Ԥ����·��
  - ���� AutoSmoke/IDE/debug_panel.py �������Ԥ��ϸ���߼���_check_bridge_service �� _check_capture_channels������չ /api/precheck ���� ��ͼͨ������־/����ɴ��� blocker ��飻���� precheckState ������������ʾչʾ��ǰ�� preCheck()����
  - ���θĶ�ǰ�ٴα����ļ���E:/zdcs/AutoSmoke/IDE/debug_panel.py.bak.20260616_104257��


- 2026-06-16 10:49:00 继续开发：执行入口 P0-3。
  - 已为 `debug_panel.py` 增加“执行前自动预检联动”：新增 `ensurePrecheckAndRun` 与 `preCheck(cb)` 回调能力，`runCase` / `batchRun` 在执行前自动触发 `/api/precheck`（超过 60s 自动刷新），若阻塞项存在则中止执行。
  - 修改前已备份：`E:/zdcs/AutoSmoke/IDE/debug_panel.py.bak.20260616_104809`。
- 2026-06-16 10:51:51 继续按优先级执行（P0-4）：补齐预检交互能力。`n  - 在 debug_panel.py 中补充 /api/precheck 的阻塞项 quickFix 元数据（应用配置、用例执行前置、Unity脚本部署、坐标映射配置、截图通道、日志/服务可达性、用例文件）。`n  - 在前端 运行预检区新增：阻塞项提示清单 + 快速修复按钮（open_config、run_deploy、refSt、cap、chkAll 等），并新增“复制结果/导出JSON”按钮。`n  - swt("execute") 首次进入执行页签时自动触发一次预检。`n  - 编辑前备份: E:\zdcs\AutoSmoke\IDE\debug_panel.py.bak.20260616_105151 ; E:\zdcs\.workbuddy\memory\MEMORY.md.bak.20260616_105151

## 2026-06-17 AutoSmoke 上游输入与转换层决策

- 已明确：如果转换层放在 AutoSmoke，上游不需要直接提供可执行自动化步骤或最终 `testId`，但必须提供可稳定转换的业务原料。
- 推荐上游交付包：`autosmoke_upstream_handoff.v1/`。
- 必需文件：
  - `manifest.json`
  - `manual_test_cases.v1.xlsx` 或 `.json`
  - `case_seed_package.v0.json`（推荐作为 DocReader 业务事实输入）
  - `target_name_catalog.v1.json`
  - `source_trace.v1.json`
  - `review_items.v1.json`
- 增强文件：
  - `value_assets.v1.json`
  - `optional_external_refs.v1.json`
- 已生成详细规范文件：
  - `E:/zdcs/参考资料/AutoSmoke_上游交付包格式规范_转换层在AutoSmoke_20260617.md`
  - `E:/zdcs/参考资料/AutoSmoke_自动执行框架定义_20260617.md`
  - `E:/zdcs/参考资料/AutoSmoke_对上游DocReader自动化输入反馈_20260617.md`
  - `E:/zdcs/参考资料/AutoSmoke资产包方案_vs_DocReader对接文档_差异对比_20260617.md`
- 手工用例如果达到 A 级自然语言标准，很多资产可由 AutoSmoke 转换层生成草稿：
  - `target_name_catalog.draft.json`
  - `precondition_registry.draft.json`
  - `assertion_catalog.draft.json`
  - `source_trace.v1.json`
  - `review_items.draft.json`
  - `value_assets.draft.json`
  - `optional_external_refs.draft.json`
- A 级手工用例标准：
  - 一个前置条件 = 一个明确状态。
  - 一个操作步骤 = 一个动作 + 一个目标。
  - 一个预期结果 = 一个可观察结果 + 一个目标。
  - 避免“正常 / 正确 / 符合预期 / 这个 / 那里 / 按钮”等泛称。
  - 目标名应与 `target_name_catalog.v1.json` 的 `target_name` 或 `aliases` 一致。
- 如果上游能按 A 级样式提供手工用例，额外最少还需要：
  - `manifest.json`
  - `target_name_catalog.v1.json`
  - 若 AutoSmoke 不能自动从 Excel 行号生成来源，再提供 `source_trace.v1.json`
- 前置状态边界：
  - A 级手工用例可提供前置状态自然语言。
  - 如果 AutoSmoke/测试环境已有账号池和前置状态库，上游可不提供 `precondition_registry.v1.json`。
  - 如果没有账号池/前置状态库，还需要 `precondition_registry.v1.json` 和 `test_data_registry.v1.json`。
- 责任边界：
  - 上游负责：业务事实、手工用例、稳定目标名、来源、值资产、待确认项。
  - AutoSmoke 负责：动作推断、步骤生成、semanticId/testId 解析、前置状态映射、断言生成、阻断判断、执行与报告。
