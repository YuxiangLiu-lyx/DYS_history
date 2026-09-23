# 德云史记 · 慧后本纪

**当前续篇：第三至五回，共8段×30秒、240秒。第二回N04同步修订为边唱边舞。**

| 章节 | 分段与内容 | 制作入口 |
|---|---|---|
| 第三回《一梦悬双画，七字动满堂》 | P01/P02，60秒；两幅梦图、质疑、答联与“江—大—歌” | [导演稿](episodes/ep03/script/EP03_DIRECTOR_v1.md) · [生产包](episodes/ep03/production/VIDEO_PRODUCTION_PACK.md) · [操作步骤](episodes/ep03/production/QUICKSTART.md) |
| 第四回《灯下问苍生，帘后起相思》 | Q01/Q02/Q03，90秒；音音、民生、魏笑线索、侍女打趣 | [导演稿](episodes/ep04/script/EP04_DIRECTOR_v1.md) · [生产包](episodes/ep04/production/VIDEO_PRODUCTION_PACK.md) · [操作步骤](episodes/ep04/production/QUICKSTART.md) |
| 第五回《松下听卜卦，一曲定情深》 | R01/R02/R03，90秒；客栈议策、迎客松分唱与一吻 | [导演稿](episodes/ep05/script/EP05_DIRECTOR_v1.md) · [生产包](episodes/ep05/production/VIDEO_PRODUCTION_PACK.md) · [操作步骤](episodes/ep05/production/QUICKSTART.md) |

每条完整Prompt均不超过2000字符，每段默认只用4–6张必要图片，另加真实尾帧时最多7张；图片/原声/道具/首尾状态/反打/环境声和跨段衔接见对应生产包。两张梦图、三处空景已生成，均待审；真实视频和完整逐镜Storyboard尚未生成。两张梦图是架空画作，现代IG画面由2018官方资料重构并把TheShy移至中央，不冒称原始纪实照片。

**演唱口型尚待最终音频锁定。** 已搜到歌词资料与孙潘合唱条目，但没有取得用户实际使用的原声。R02/R03的秒表是预排；实际歌词/字音/笑场锚点为null。不要先生成随意哑口型再换任意配音。先提供最终两段30秒导唱时间线，再按同版音频驱动画面，移除生成声轨后铺原声。现有五人MP3仅为说话音色。研究依据与版本区别见[歌曲核对记录](history/research/EP03_05_song_research.md)。

[N04歌舞修订](episodes/ep02/production/prompts/N04_PROMPT.txt)保留18秒歌舞、7秒面部近景；其它四段与21句对白不变。新资料打包：`python tools/build_next_bundles.py --out /tmp/DYS_EP03_05`；校验：`python tools/validate_next_pack.py`。最新上传状态见[同步记录](context/SYNC_STATUS.md)，资产看[画册](REVIEW_GALLERY.html)，后续AI先读[AGENTS.md](AGENTS.md)。

本轮已[上传并核验370个文件](https://github.com/YuxiangLiu-lyx/DYS_history/commit/49c0ba12c02362e1550f96db73b0a334b24be52f)，旧版完整保留。

以下保留第二回及第一回制作入口。

**第二回《微服入江南，听松初逢卿》v1.1，5段×30秒，共150秒。** 29镜、21句对白；每段Prompt小于2000字符。新增两位微服定妆和4处场景，保留第一回原稿和全部素材。新图片及导演稿可审阅；尚未生成本章视频，首尾关键帧与完整Storyboard仍待补齐。

| 第二回需要什么 | 入口 |
|---|---|
| 导演稿与对白 | [EP02导演版](episodes/ep02/script/EP02_DIRECTOR_v1.md) |
| 每幕时间轴、动作、声音、Prompt | [EP02生产包](episodes/ep02/production/VIDEO_PRODUCTION_PACK.md) |
| 按步骤制作 | [EP02操作流程](episodes/ep02/production/QUICKSTART.md) |
| 单独复制Prompt | [N01密奏](episodes/ep02/production/prompts/N01_PROMPT.txt) · [N02议策](episodes/ep02/production/prompts/N02_PROMPT.txt) · [N03徽州](episodes/ep02/production/prompts/N03_PROMPT.txt) · [N04初见](episodes/ep02/production/prompts/N04_PROMPT.txt) · [N05诗会](episodes/ep02/production/prompts/N05_PROMPT.txt) |
| 图音上传顺序 | [EP02 refs](episodes/ep02/production/refs_upload.json) |
| 声音与后配卜卦 | [EP02后期手册](episodes/ep02/production/audio/AUDIO_POST_WORKFLOW.md) |
| 微服与新场景 | [系列图像画册](REVIEW_GALLERY.html) · [生成记录](history/generation/) |
| 重建5个按幕材料包 | `python tools/build_ep02_bundles.py --out /tmp/DYS_EP02_v1` |

EP02已[上传并核验295个文件](https://github.com/YuxiangLiu-lyx/DYS_history/commit/0e46f26c174178004237bf64fa18f9ef60d9ede2)，回执在history/publication/，后续元数据提交保留该证据。

本回西卡留京；初见发生在听松楼，取代旧“第三回迎客松下初见”的未来规划。N04边唱边舞，加入面部近景、口型与句间微笑，待补同版最终歌段作为口型导唱，交付不生成歌声，用户后配《卜卦》，N05开始前音乐退下，保证低语听清。潘慧痣位仍由C05_FRONT_HALF_v04锁定。

以下为第一回既有v4制作入口，保持有效。

**第一回v4：第一回《风起徽州》，Seedance 2.5，三幕各30秒。** 成片90秒、24个叙事镜头＋片尾字卡，基础生成从11次整合为3次。保留原剧情、原台词和全部角色图；仅做已记录的时间调整。每幕用9/9/11张图与1/3/1段角色原声，不凑满素材额度。

已[上传并核验全部256个文件](https://github.com/YuxiangLiu-lyx/DYS_history/commit/aa27eb60f996ec607735604db6e5cb6a4e254bb3)，包含5份用户原MP3；上传回执和当前状态另行随版本记录。

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
