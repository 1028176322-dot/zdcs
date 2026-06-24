# IDE 编码与路径改造编写规范（防止文件损坏版）

目标：避免再次出现中文乱码、字符串断裂、IDE 相关文件运行异常。

适用范围：IDE 运行相关文件（含 `autosmoke_ide.py`、`autosmoke_web_ide.py`、`AutoSmoke/ide`、`AutoSmoke/视觉识别`、`AutoSmoke/定位`、`AutoSmoke/core_engine/ui_processor`、`AutoSmoke/core_engine/poco_connector`）。

1. 文件编码规范
1.1 全部源码统一为 UTF-8（无 BOM）。
1.2 读写文件必须显式指定编码，不允许使用平台默认编码。
1.3 禁止任何“猜测性”字符重编码操作。
1.4 允许的工具链必须支持 UTF-8；不能用会改写编码的命令/插件写回源码。
1.5 文件头统一保留：`# -*- coding: utf-8 -*-`。

1. 写文件建议模板
```python
from pathlib import Path

content = Path("xxx.py").read_text(encoding="utf-8")
# ...只改必要片段...
Path("xxx.py").write_text(content, encoding="utf-8")
```

2. 路径规范
2.1 禁止硬编码绝对盘符路径（`C:\`、`D:\`、`/home/...`、`/usr/...`）。
2.2 所有项目内路径按项目根统一计算。
```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
```
2.3 外部配置/系统相关路径只使用环境变量映射（如 `USERPROFILE`、`HOME`）。

2.4 模块导入采用项目内相对可移植形式，避免系统环境差异影响。
```python
from 元数据.metadata_reader import MetadataReader
```

3. 修改操作规范（防误伤）
3.1 路径替换只修改最小 token，不做跨文件全量文本替换。
3.2 禁止“模糊改写”中文文案、UI HTML/JS 字符串、注释等内容。
3.3 分段执行：改一个文件先自检，再继续下一文件。
3.4 一次操作不改超过 3-5 个高风险文件，避免失控。

4. 字符串与语法保护
4.1 修改前必须核对 `"""`/`'''` 成对存在。
4.2 避免把模板字符串与代码混改。
4.3 每次修改后执行语法检查：
```bash
python -m py_compile autosmoke_ide.py autosmoke_web_ide.py AutoSmoke/ide/debug_panel.py
```
4.4 若存在中文大段模板，优先先小范围人工确认再提交。

5. 变更禁忌（必须避免）
5.1 不允许一次性 `Set-Content` + 全量替换覆盖整目录源码文本。
5.2 不允许直接修改 `docstring/注释` 中乱码片段替代代码逻辑。
5.3 不允许使用未指定编码的 `read/write` 命令处理源码。
5.4 禁止把问题文件当作“清洗文本”再复写。

6. IDE 高风险文件清单（建议每次改后重点回归）
6.1 `autosmoke_ide.py`
6.2 `autosmoke_web_ide.py`
6.3 `AutoSmoke/ide/debug_panel.py`
6.4 `AutoSmoke/视觉识别/game_content_vision.py`
6.5 `AutoSmoke/视觉识别/visualize_clickable_elements.py`
6.6 `AutoSmoke/定位/locate_active_region.py`
6.7 `AutoSmoke/core_engine/ui_processor/*`
6.8 `AutoSmoke/core_engine/poco_connector/*`

7. 变更后检查清单（每次 PR 前）
7.1 扫描绝对路径（根目录 + IDE 相关范围）
```bash
rg -n "[A-Za-z]:[\\/]" autosmoke_ide.py autosmoke_web_ide.py AutoSmoke/ide AutoSmoke/视觉识别 AutoSmoke/定位 AutoSmoke/core_engine/ui_processor AutoSmoke/core_engine/poco_connector
```
7.2 检查文件是否能通过 `py_compile`（至少相关文件全部通过）。
7.3 若有中文目录名，重点看首行与文案区域是否保持 UTF-8 文本正常。
7.4 仅检查通过后再发布运行。

8. 预防性建议（可选）
8.1 建议新增一个 `scripts/ide_guard.py`，做以下统一校验：
- UTF-8 解码检查
- 绝对路径扫描
- `py_compile` 列表校验
- `"""`/`'''` 成对检测
8.2 在 IDE 启动前增加最小预检步骤，快速中断异常文件加载。

8.3 目录映射示例：
```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTOSMOKE_ROOT = PROJECT_ROOT / "AutoSmoke"
CONFIG_DIR = PROJECT_ROOT
```

10. 一句话执行约定
能改的最小项先改，先改逻辑再改文案；任何导致语法报错的变更，一律回滚重做，不做“补丁式救火”。
