# check_and_record_completed_mapping_page 用法说明

`check_and_record_completed_mapping_page.py` 用于检查某个界面是否已经完成“全部元素映射确认”，并在通过后自动写入：

- `E:\zdcs\杩涘害\宸插畬鎴愬叏閮ㄥ厓绱犳槧灏勭‘璁ょ晫闈㈣褰?md`

## 快速运行（推荐）

```powershell
cd E:\zdcs\AutoSmoke\tools
.\check_and_record_completed_mapping_page.ps1 character_info
```

## 参数说明

- `-Page`：必填，界面名或 pageId
- `-StrictDrafts`：开启后会严格检查该 page 下所有 draft（含 project_inventory 待审项）
- `-DryRun`：只校验不写入台账
- `-Note`：写入台账时追加说明
- `-Date`：自定义完成日期（默认脚本使用本机当日，格式 `yyyy-MM-dd`）
- `-Python`：自定义 Python 路径（默认使用 `C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe`）

## 常见示例

```powershell
# 仅校验，不写入
.\check_and_record_completed_mapping_page.ps1 character_info -DryRun

# 严格检查全部 page draft（含 project_inventory 待审项）
.\check_and_record_completed_mapping_page.ps1 character_info -StrictDrafts

# 指定环境信息与备注
.\check_and_record_completed_mapping_page.ps1 "character_info" -Note "确认完成并复核通过" -Date "2026-06-24"
```

## 你原始命令的等价形式

```powershell
& 'C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe' 'E:\zdcs\AutoSmoke\tools\check_and_record_completed_mapping_page.py' character_info
```
