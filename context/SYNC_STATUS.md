# 同步记录

**当前：v3_prepared_for_publish。5图与音画同步逻辑修订正在本轮提交；下面保留v2已成功发布的历史回执。**

资产提交：[2f749070e7f486cb1aadf9a391c17d25a64f5763](https://github.com/YuxiangLiu-lyx/DYS_history/commit/2f749070e7f486cb1aadf9a391c17d25a64f5763)。完整回执：`history/publication/EP01_v2_asset_receipt.json`；逐文件快照：`history/publication/EP01_v2_asset_snapshot.json`。随后同步回执文档的提交在此资产提交之上。

以下403是权限修复前的历史记录。发布成功回执已写在上方；保留旧故障原因供追溯。

目标：`https://github.com/YuxiangLiu-lyx/DYS_history`，默认分支main。

2026-09-22：只读查询成功，仓库为空（size=0，git ls-remote无refs）；仓库API返回用户级push权限，但当前安装集成写入不可用。尝试通过已连接GitHub的create_file创建README，GitHub返回：

```text
403 Resource not accessible by integration
```

写入没有成功，没有远端提交SHA，没有上传成功的图片。没有使用其他身份或路径绕过拒绝。此问题来自GitHub集成权限，不是用户未授权任务，也不是自动审批拒绝。

## 权限修复后的同步

本地归档包含全部内容和规则，可由拥有该仓库写权限的GitHub连接或用户自己的Git客户端提交。需要给当前GitHub App对本仓库的Contents写权限/适当仓库访问范围，或换用用户自己已授权的正常Git客户端；不是要求把密码或token贴给AI。

收到具备写权限的连接后，先读取远端现状。仓库如果仍为空，可在当前归档目录正常初始化/提交后push main；如果已有新文件，先合并远端，禁止强推或覆盖。上传成功后更新context/STATUS.json与history/CHANGELOG.md，记录实际commit并验证README、锁定剧本、manifest和至少一张PNG在远端可读。

本包已附`AGENTS.md`声明关键内容位置和每轮AI必须存档的内容。只要未来AI实际提交这些记录，即可从仓库恢复；不能承诺未提交聊天也会被自动记住。
