# 实验3设计文件与 GitHub/Gitee 提交说明

本目录保存“AI象棋对弈助手系统”的实验3设计源文件。报告正文引用这些文件，但不依赖在线编辑器才能阅读。

## 1. 建议的仓库目录

```text
AI-Xiangqi-Assistant/
├─ docs/
│  └─ experiments/
│     ├─ exp2-requirements-v1.md
│     └─ exp3-architecture-ui-v1.md
├─ design/
│  ├─ diagrams/
│  │  ├─ 01-system-context.mmd
│  │  ├─ 02-overall-architecture.mmd
│  │  ├─ 03-data-model.mmd
│  │  ├─ 04-core-flow.mmd
│  │  └─ 05-page-navigation.mmd
│  └─ prototypes/
│     ├─ 01-home.svg
│     ├─ 02-game.svg
│     └─ 03-review.svg
└─ README.md
```

本次交付目录中的中文文件名可以直接使用；若课程要求统一英文文件名，可按上面的英文目录复制或重命名，内容不变。

## 2. 第一次提交到 GitHub/Gitee

在存放项目文件的根目录打开 PowerShell：

```powershell
git init
git branch -M main
git add docs design README.md
git commit -m "docs: add experiment 3 architecture and UI design"
git remote add origin <你的GitHub或Gitee仓库地址>
git push -u origin main
```

如果仓库已经有远程地址，不要重复 `git remote add origin`，先检查：

```powershell
git remote -v
git status
```

## 3. 生成作业要求的 Commit 证据

提交成功后执行：

```powershell
git log -1 --oneline
git rev-parse HEAD
git ls-tree -r --name-only HEAD | Select-String "exp2|exp3|design"
```

把输出中的短 Commit（例如 `a1b2c3d`）、完整 Commit、仓库 URL 和文件路径填入实验3报告的“仓库版本证据”表。建议提交后不要再修改这批文件；如果修改，重新提交并更新表格中的 Commit。

## 4. 后续修改的提交方式

```powershell
git add docs design
git commit -m "docs: refine experiment 3 diagrams and prototypes"
git push
```

## 5. GitHub 与 Gitee 的区别

- GitHub：在仓库页面复制 HTTPS 或 SSH 地址，登录方式按学校/个人账号配置。
- Gitee：创建仓库后复制仓库地址；第一次推送若提示身份验证，按 Gitee 页面提示使用账号密码或私人令牌。
- 两个平台都需要在浏览器仓库页面确认文件已经出现，再把仓库 URL 和 Commit 写入报告。

## 6. 常见问题

**远程仓库不是空仓库：**先 `git pull --rebase origin main`，解决冲突后再 `git push`。  
**文件名含中文：**Git 可以正常保存；若命令行显示乱码，优先以 `git ls-tree` 或网页文件列表为准。  
**不想上传构建产物：**将 `*.pdf`、`work/` 和临时渲染图片写入 `.gitignore`；本实验报告 PDF 若老师要求仓库留存，则不要忽略最终 PDF。

