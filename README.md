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

## ⚠️ 注意事项

- 代码中 **不要提交公司敏感信息**（密钥、密码等）
- 推送前先 `git pull` 拉取最新代码，避免冲突
- `AutoSmoke/元数据/project_ui_inventory.json` 和 `AutoSmoke/metadata/ui_code_semantics_test.json` 文件过大（>100MB），已排除在 Git 追踪之外，需要单独拷贝
