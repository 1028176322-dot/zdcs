# AutoSmoke — UI自动化测试框架

SLG 游戏自动化测试项目，包含 IDE、Poco 集成、场景交互检测等功能。

---

## 🚀 快速开始（新电脑拉取项目）

### 1️⃣ 安装 Git

从官网下载安装：https://git-scm.com/downloads

安装时一路默认选项即可。

### 2️⃣ 克隆仓库

```bash
# 进入你放项目的目录（比如 D:\Projects）
cd D:\Projects

# 克隆到本地（需要先配好SSH，见下方说明）
git clone git@github.com:1028176322-dot/zdcs.git

# 进入项目目录
cd zdcs
```

### 3️⃣ 查看代码

```bash
# 查看当前状态
git status

# 查看提交历史
git log --oneline
```

---

## 📥 日常更新（拉取最新代码）

后续在其他电脑工作前，先拉取远程最新的改动：

```bash
# 进入项目目录
cd D:\Projects\zdcs

# 拉取最新代码
git pull
```

---

## 📤 日常提交（修改后上传）

```bash
# 1. 查看改了什么
git status

# 2. 添加所有改动
git add -A

# 3. 提交并写说明
git commit -m "做了什么修改"

# 4. 推送到远程
git push
```

---

## 🔑 新电脑第一次使用——配置 SSH

本仓库只支持 **SSH 方式**访问，配置好之后就永久免密码。

### 第一步：安装 Git

从 https://git-scm.com/downloads 下载安装，一路默认。

### 第二步：生成 SSH 密钥

打开 **Git Bash**，执行：

```bash
ssh-keygen -t ed25519 -C "1028176322@qq.com"
```

一路回车（不用设密码），执行完会生成一对密钥。

### 第三步：把公钥添加到 GitHub

```bash
# 查看并复制公钥内容
cat ~/.ssh/id_ed25519.pub
```

会输出一行以 `ssh-ed25519` 开头的文本，**全选复制它**。

然后打开 GitHub：
- 点右上角头像 → **Settings**
- 左侧 **SSH and GPG keys**
- 点 **New SSH key**
- Title 随便填（比如 `公司电脑`）
- Key 里粘贴刚才复制的内容
- 点 **Add SSH key**

### 第四步：克隆仓库

```bash
git clone git@github.com:1028176322-dot/zdcs.git
```

以后 `git push` / `git pull` 都不需要再输任何密码。

---

## 📁 项目结构说明

```
zdcs/
├── AutoSmoke/           # 自动化测试核心
│   ├── IDE/             # IDE 集成代码
│   ├── archive/         # 归档脚本
│   ├── runtime/         # 运行时桥接
│   ├── metadata/        # 界面元数据
│   └── 元数据/           # 项目界面数据
├── data_access/         # 数据访问层
├── Poco-SDK/            # Poco UI 自动化 SDK
├── 参考资料/             # 技术文档
├── 进度/                # 测试进度台账
└── .gitignore           # Git 忽略规则
```

---

## AutoSmoke IDE 实现进度与当前状态（2026-06-25）

### 整体定位

AutoSmoke IDE 当前已经从早期的“截图/点击调试面板”扩展为一个集成工作台，覆盖环境准备、Unity Bridge、截图定位、UI 树导入、元素映射审核、目标绑定、用例执行、异常检测、阻塞处理、报告导出、QA_Reader handoff 接入等流程。

当前主入口：

```text
http://127.0.0.1:5000
```

主要代码入口：

```text
AutoSmoke/IDE/debug_panel.py
```

### 已实现模块

#### 1. 环境与运行前检查

- 已实现基础状态检查：Python/Flask 服务、AutoSmoke 根目录、Unity 项目路径、Poco 路径、设计分辨率等。
- 已实现用例执行前置预检：截图通道、日志/服务可达性、用例文件、执行上下文。
- 已实现阻塞项展示、复制阻塞详情、下载预检结果。
- 已实现部分 quick fix：刷新用例上下文、刷新定位、截图通道检测、环境配置切换等。

当前状态：可用，但仍依赖本机 Unity/Bridge/截图环境是否正确启动。

#### 2. Unity Bridge 与运行态能力

- 已实现 Bridge 状态刷新。
- 已实现 runtime UI tree 请求/导出。
- 已实现 runtime path 点击、候选匹配、点击验证、页面状态刷新。
- 已实现 bridge 请求/响应文件通道。

当前状态：核心链路可用。Bridge 未响应时会出现超时、点击验证失败或 runtime UI tree 为空，需要先处理 Unity 侧连接。

#### 3. 截图、坐标与点击定位

- 已实现 GameView/GameContent 截图。
- 已实现 Unity 直出截图优先、本地截图降级。
- 已实现坐标映射、截图高亮、区域裁剪、截图差异对比。
- 已实现点击测试、单步执行、手动点击辅助。
- 已对固定 Debug 区域误触问题做过规避处理：优先使用 Bridge/runtimePath 点击，必要时才回退坐标点击。

当前状态：可用，但截图区域仍受 Unity 窗口位置、GameView 尺寸、工具栏高度、缩放比例影响。真实点击前应先看高亮和点击验证结果。

#### 4. UI 树、元数据与导入

- 已实现当前 UI tree 扫描。
- 已实现 Prefab/工程态 UI 数据扫描。
- 已实现 enhanced_ui_tree 生成、状态检查、导入。
- 已实现项目 UI inventory / current_ui_tree / runtime_ui_tree 多来源回退。
- 已实现 UI 导入报告查看。

当前状态：可用。大文件如 `project_ui_inventory.json` 不纳入 Git，需要在新电脑单独准备。

#### 5. 元素映射审核

- 已实现映射草稿列表、状态筛选、页面筛选、分组查看。
- 已实现草稿详情查看、字段编辑、截图高亮、运行态匹配、点击验证、确认/拒绝/忽略。
- 已实现正式 MappingStore 写入。
- 已实现目标名、displayName、semanticId、testId 等字段的校验与候选生成。
- 已实现目标重复、候选冲突、已确认候选占用等风险提示。

当前状态：核心流程可用。仍需持续注意同名目标、动态列表、跨页面候选污染、reviewStatus 状态回退等历史问题。

#### 6. 目标工作台

- 已实现目标队列列表、状态展示、目标搜索、快速添加。
- 已实现当前页目标生成、批量推荐、重校验、回放历史。
- 已实现候选匹配、选择候选、生成高亮、运行下一步、忽略/恢复。
- 已实现与元素映射草稿、正式 mapping、用例回放状态的联动。

当前状态：可用，但仍需要重点防止按钮操作异常改动目标列表。历史已知风险包括：

- 生成当前页目标后出现重复目标。
- 生成高亮后把其它界面的元素刷新进当前目标列表。
- 同描述目标需要结合 `targetId/runtimePath/pageId/index` 区分，不能只靠中文名。

#### 7. 用例导入与执行

- 已实现 Excel 用例导入、用例列表、用例校验。
- 已实现单用例执行、批量执行。
- 已实现执行前预检，不满足条件时阻塞执行。
- 已实现步骤解析：点击、等待、断言存在/不存在、截图、返回、长按、滑动、输入等。
- 已实现 BatchRunner 执行结果写入 `batch_report.json`。

当前状态：可用。真实执行强依赖正式 mapping、截图通道、Bridge 状态和当前游戏页面。

#### 8. 报告与归档

- 已实现历史报告列表。
- 已实现 batch_report JSON 导出。
- 已实现 HTML 报告导出。
- 已实现失败包导出。
- 已实现页面关系图报告、模块验收报告、迁移验收报告入口。
- 已实现截图与日志对比区域。

当前状态：基础可用。报告内容仍以执行结果为主，业务解释、失败根因归类还需要继续增强。

#### 9. 异常检测与阻塞处理

- 已实现 Unity 日志读取。
- 已实现崩溃/卡死/异常日志检测。
- 已实现阻塞检测与阻塞处理入口。
- 已实现 PostActionGuard，在步骤之间检查界面状态。

当前状态：可用但偏辅助性质。复杂弹窗、活动跳转、网络等待、登录态变化仍需要更多规则沉淀。

#### 10. 页面关系图

- 已实现页面关系配置入口。
- 已实现 page_graph 信息查看、HTML 查看、导出。
- 已和部分扫描/准备流程联动。

当前状态：基础能力存在。页面进入、返回、恢复策略还没有完全自动化。

#### 11. QA_Reader handoff 接入

- 已实现 handoff schema：`AutoSmoke/schemas/`。
- 已实现 handoff 校验、导入、转换：`AutoSmoke/tools/handoff_pipeline.py`。
- 已实现 `target_name_catalog` 转目标绑定任务。
- 已实现 `manual_test_cases` 转 AutoSmoke cases。
- 已实现 semanticId/testId 候选生成。
- 已实现业务状态采集与断言执行：`AutoSmoke/tools/business_runtime.py`。
- 已实现 `value_assets`、`optional_external_refs`、截图 diff、业务结果。
- 已实现 QA_Reader 回执生成：`AutoSmoke/tools/handoff_feedback.py`。
- 已实现候选生成：`AutoSmoke/tools/handoff_candidates.py`。
- 已实现 `candidate_feature_flow/feature_flow_review_result.flows` 自动生成候选用例：`AutoSmoke/tools/handoff_case_candidates.py`。
- 已实现 `test_data_profile` 前置状态检查：`AutoSmoke/tools/handoff_preconditions.py`。
- 已实现 handoff 预执行/真实执行入口：`AutoSmoke/tools/handoff_runner.py`。
- IDE 当前按钮包括：准入校验、导入目标队列、只转换、执行计划、业务断言、业务结果、生成回执、生成候选、候选用例、预执行、真实执行、联合匹配。

当前状态：P0 基本完成，P1 执行闭环已补齐，P2 基础业务链路已完成，P3 已完成候选目标、候选断言、候选用例和 QA_Reader 回执生成。当前 armrace 示例仍保留 `activity_main` 入口规则缺口，因为尚未确认“主城活动入口”正式映射，不能伪造自动入口。

### 重要产物路径

```text
AutoSmoke/runtime/                                  # 运行时上下文、pid、bridge 临时状态
AutoSmoke/runtime/bridge/                           # Unity Bridge 请求/响应/heartbeat
AutoSmoke/runtime/ui_tree/                          # 运行态 UI tree 相关文件
AutoSmoke/metadata/                                 # 当前主要元数据目录
AutoSmoke/metadata/mapping_store/                   # 正式元素映射
AutoSmoke/metadata/mapping_task_queue.json          # 目标工作台任务队列
AutoSmoke/metadata/runtime_ui_tree_current.json     # 当前 runtime UI tree
AutoSmoke/metadata/handoff/imports/<package_id>/    # handoff 转换产物
AutoSmoke/metadata/handoff/reports/                 # handoff 校验/导入报告
AutoSmoke/metadata/handoff/business_results/        # handoff 业务断言结果
AutoSmoke/metadata/handoff/feedback/                # QA_Reader 回执
AutoSmoke/metadata/handoff/candidates/              # handoff 候选清单
AutoSmoke/metadata/handoff/prepare_results/         # handoff 前置条件检查结果
AutoSmoke/metadata/handoff/runs/                    # handoff 预执行/真实执行报告
AutoSmoke/screenshots/                              # 截图、执行过程、batch_report
AutoSmoke/reports/                                  # HTML/导出报告
```

### 遗留问题

- `debug_panel.py` 体积很大，前后端和大量业务逻辑集中在一个文件里，后续需要拆分为 API、前端模板、工具服务三层。
- 目标工作台仍需继续防止按钮副作用：生成目标、生成高亮、批量推荐、重校验都不能异常改动目标列表。
- 同名目标和动态列表目标仍是高风险点，需要强制使用 `pageId + targetId + runtimePath + index/collection` 区分。
- 正式 mapping 的 `reviewStatus`、`targetName`、`displayName`、`semanticId` 状态需要持续校验，避免确认后又回退为 `manual/template/pending`。
- Debug 固定区域遮挡点击的问题已做规避，但坐标点击回退仍可能受窗口缩放和遮挡影响，真实点击前仍建议先走高亮和点击验证。
- handoff 真实执行已经接入入口；当前主要缺口是具体业务页面的入口/返回/恢复规则需要正式映射支撑，armrace 示例只剩 `activity_main` 入口缺正式映射。
- QA_Reader `candidate_feature_flow`/`feature_flow_review_result.flows` 已可生成候选用例，但生成结果仍需人工审核后再替换正式 `manual_test_cases`。
- 业务断言目前支持 UI runtime tree/manual/screenshot_diff，奖励到账、邮件、排行榜、配置生效等真实外部系统采集器还需要补。
- 报告已可导出，但失败根因分类、修复建议、责任归属还需要继续增强。
- 新电脑拉取仓库后，大型元数据文件不在 Git 中，需要单独同步，否则 UI 扫描/语义匹配能力会下降。

### 注意事项

- 修改 `AutoSmoke/IDE/debug_panel.py`、`AutoSmoke/tools/*.py` 后，需要重启 IDE 服务。
- 真实执行、真实点击前，先确认 Unity、Bridge、截图通道、当前页面、正式 mapping 都正常。
- `预执行` 不会实际点击，只用于检查 handoff 用例能否转换为执行步骤。
- `真实执行` 会调用 BatchRunner 和点击链路，可能改变游戏状态。
- `AutoSmoke/runtime/`、`AutoSmoke/screenshots/`、Bridge 请求/响应、heartbeat 多数是运行时生成物，通常不作为功能代码提交。
- 对元素映射三字段 `semanticId / targetName / displayName` 的写入和修改，必须遵守对象词典与中文反补流程，不能绕过统一命名规则。
- 有用户或运行时生成的脏工作区改动时，不要随意回滚；先确认来源和影响。

---

## ⚠️ 注意事项

- 代码中 **不要提交公司敏感信息**（密钥、密码等）
- 推送前先 `git pull` 拉取最新代码，避免冲突
- `AutoSmoke/元数据/project_ui_inventory.json` 和 `AutoSmoke/metadata/ui_code_semantics_test.json` 文件过大（>100MB），已排除在 Git 追踪之外，需要单独拷贝
---

## 文件备份实施规则

本仓库已经接入远程 Git，后续以 **Git 远程仓库 + 清晰提交记录** 作为主要备份、同步和回滚方案。原则上不再依赖手工复制文件、`.bak` 文件或时间戳备份文件。

### 总原则

- 源码、工具脚本、schema、文档、关键配置、可复用示例数据，应通过 Git 跟踪和提交。
- 运行时文件、截图、日志、heartbeat、Bridge 请求/响应、临时缓存、自动生成的大体积文件，不作为常规备份提交。
- 修改前先确认工作区状态，避免覆盖用户或运行时已经产生的改动。
- 每次提交只表达一个清晰目的，不把功能修改、运行时生成物、清理动作混在一起。

### 修改前必须执行

```bash
git status
git diff
```

执行目的：

- 确认当前有哪些文件已被修改。
- 区分“自己准备改的文件”和“用户/运行时已经改过的文件”。
- 如果发现不相关改动，不要回滚；只处理本次任务需要的文件。

### 修改中规则

- 不再新建 `.bak`、`.backup`、`.bak.时间戳` 作为常规备份。
- 修改已纳入 Git 的文件时，依靠 `git diff` 查看改动。
- 大改动或风险较高改动，应优先新建分支：

```bash
git checkout -b codex/功能说明
```

- 连续多步开发时，可以用 checkpoint commit 代替手工备份：

```bash
git add 相关文件
git commit -m "checkpoint: 当前阶段说明"
```

### 修改后必须执行

```bash
git diff
git status
```

确认无误后再提交：

```bash
git add 相关文件
git commit -m "简明说明本次修改"
git push
```

提交要求：

- 只提交和本次任务相关的文件。
- 不提交运行时噪声文件。
- 不提交本地路径、账号、密钥、密码、机器专属配置。
- 如果测试或验证生成了报告，只提交有复用价值的报告模板或说明；普通运行报告默认不提交。

### 应纳入 Git 的文件

```text
AutoSmoke/IDE/*.py
AutoSmoke/tools/*.py
AutoSmoke/schemas/*.json
AutoSmoke/examples/**/*
AutoSmoke/参考资料或项目文档
README.md
进度/*.md
关键规则文件、规范文件、流程文件
```

### 默认不纳入 Git 的文件

```text
AutoSmoke/runtime/**
AutoSmoke/runtime/bridge/**
AutoSmoke/screenshots/**
AutoSmoke/logs/**
AutoSmoke/reports/普通运行报告
AutoSmoke/**/__pycache__/**
*.pyc
*.bak
*.backup
*.tmp
heartbeat.json
capture_request.json
capture_response.json
```

### 大文件与本地专属文件

以下文件体积大或与本机环境强相关，不作为普通 Git 备份：

```text
AutoSmoke/元数据/project_ui_inventory.json
AutoSmoke/metadata/ui_code_semantics_test.json
```

处理方式：

- 新电脑使用时单独拷贝或重新生成。
- 如果必须纳入长期版本管理，需要先评估 Git LFS 或拆分压缩方案。
- 不要直接把超过 100MB 的数据文件普通提交到 Git。

### 清理历史备份文件规则

如果需要清理旧 `.bak`、运行时生成物、误提交缓存：

- 单独做一次清理提交。
- 不和功能修改混在一起。
- 清理前先确认这些文件没有被代码引用。
- 已经被 Git 跟踪的生成物，需要用索引清理方式移出跟踪，而不是只删除本地文件。

示例：

```bash
git rm --cached 路径
git commit -m "清理运行时生成物跟踪"
```

### 回滚规则

- 小范围回滚优先使用 `git diff` 找到具体文件和具体行后手动修正。
- 不使用 `git reset --hard` 回滚整个工作区，除非明确确认所有未提交改动都可以丢弃。
- 不使用 `git checkout -- .` 批量覆盖工作区，避免误删用户改动。
- 需要回退某次提交时，优先使用 `git revert <commit>`，保留可追溯记录。

### Codex/自动化助手执行规则

- 修改前必须检查 `git status`。
- 不创建手工 `.bak` 文件。
- 不回滚用户已有改动。
- 只编辑任务相关文件。
- 涉及代码功能变更时，尽量运行最小验证命令。
- 完成后说明改了哪些文件、是否验证、是否需要重启 IDE。
