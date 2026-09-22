# 德云史记 · 慧后本纪

**当前v4：第一回《风起徽州》，Seedance 2.5，三幕各30秒。** 成片90秒、24个叙事镜头＋片尾字卡，基础生成从11次整合为3次。保留原剧情、原台词和全部角色图；仅做已记录的时间调整。每幕用9/9/11张图与1/3/1段角色原声，不凑满素材额度。

| 需要什么 | 当前入口 |
|---|---|
| 直接开始制作 | [新版操作流程](episodes/ep01/production/SEEDANCE_QUICKSTART.md) |
| 三幕完整镜头/动作/声音/Prompt | [生产包](episodes/ep01/production/VIDEO_PRODUCTION_PACK.md) |
| 复制Prompt | [M01](episodes/ep01/production/prompts/M01_PROMPT.txt) · [M02](episodes/ep01/production/prompts/M02_PROMPT.txt) · [M03](episodes/ep01/production/prompts/M03_PROMPT.txt) |
| 有序图片与音频清单 | [refs_upload.json](episodes/ep01/production/refs_upload.json) |
| 五位角色用户原声 | [文件与说明](assets/audio/voice_references/VOICE_REFERENCES.md) · [音频清单](assets/audio/voice_references/manifest.json) |
| 具体改了哪些秒数 | [TIMING_CHANGES_v4.md](episodes/ep01/production/TIMING_CHANGES_v4.md) |
| 当前执行时间轴 | [timeline.json](episodes/ep01/production/timeline.json) |
| 口型、声源与故障处理 | [音画手册](episodes/ep01/production/audio/AV_SYNC_WORKFLOW.md) · [逐句合同](episodes/ep01/production/audio/dialogue_contract.json) |
| 局部返修 | [任务清单](episodes/ep01/production/audio/dialogue_repair_plan.json) · [Prompt](episodes/ep01/production/prompts/repairs/) |
| 字幕/人物条/音乐/剪辑 | [后期说明](episodes/ep01/production/POSTPRODUCTION.md) |
| 重新导出每幕上传ZIP | `python tools/build_seedance25_bundles.py --out /tmp/DYS_EP01_v4`（含有序图片、MP3、Prompt） |
| 新AI先读及每轮保存要求 | [AGENTS.md](AGENTS.md) |
| 当前状态与上传回执 | [STATUS](context/STATUS.json) · [同步记录](context/SYNC_STATUS.md) |
| 原剧本、世界观 | [锁定原稿](episodes/ep01/script/EP01_LOCKED_v1.md) · [设定](canon/PROJECT_CANON.md) |
| 既有图像、版本、哈希 | [资产清单](assets/manifest.json) · [画册](REVIEW_GALLERY.html) |
| 旧5图版 | [v3历史归档](archive/production_pack_v3/) |

五段原声按用户文件名绑定身份；只借音色，不复制样本中的现代聊天或背景。西卡本集无对白，原声保存备用，不让他代说小腿台词。潘慧在M02、M03使用同一02_pan_hui.mp3。

潘慧身份权威为C05_FRONT_HALF_v04；美人痣固定在正脸画面右侧嘴角下方的皮肤上，与唇线留间隔、与玉簪同侧，禁止镜像。衣发和夜披帛沿用现有图，不重生成全部定妆。

“50个参考素材”是官方30图＋10视频＋10音频总数；当前只使用必要素材。时间表、Prompt及自动校验用于降低可预防错误，不保证每次生成零bug。未收到实际试片，未将生产包校验冒称成片验收。

AI生成／架空历史二创。官职、贪腐情节、关系事件和对白是艺术改编，不作为真人私人事件的事实裁决，不表示真人出演或背书。制作声明、中文名牌与片尾在后期准确叠加。
