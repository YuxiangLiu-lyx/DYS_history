# 同步记录

**当前：prepared_for_publish。2026-09-22用户已开启GitHub权限，正常create_blob写入测试成功。远端main已有test.txt，已要求保留；对象上传与分支发布分开核验，main尚未更新前不标记synced。**

以下403是权限修复前的历史记录。实际发布完成后应追加远端commit、验证范围与结果，不删除旧故障原因。

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
