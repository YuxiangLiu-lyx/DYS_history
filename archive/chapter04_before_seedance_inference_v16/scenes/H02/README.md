# H02 · 梦醒未安，客栈议策 · v1.3

本场30秒；全片起点：30。D_H04未定。

**状态：导演准备稿；实际前片和动态音画验收未完成。**

先复制本场TXT，再按图片、音频、视频编号投料。缺项MD不是媒体，不上传，不用其他文件顶替。

## Prompt

455字符，含换行。

```text
续接上一段，只生成新的30秒。图1潘慧、图2侍女、图3卧房；图4深蓝便装孙亚龙、图5便装小腿、图6上午客栈：沿用图中天光方向与闭门布局，不能退回夜景。图1、4、5为独立身份母版，禁止美型换脸。视频1仅取H01末4秒的姿态、扶肩位置和音底，不重演惊醒。0.4–7.1秒潘慧沿用床内坐起姿态，怔怔说：“梦见些奇怪的景象……可那感觉，倒像真的经历过。”先喘息后稳住，短圆脸与嘴角下方小痣不漂移。7.5–10秒她说完后切窗格晨光，晨钟先行，自然转至上午客栈闭门议事。10.2–17.2秒孙按案上纸札：“魏笑这人，狡猾得很。贸然去查，只怕打草惊蛇。”后半句切小腿皱眉倾听，画外声仍属孙。17.5–20秒两人沉默思量。20.1–28.9秒小腿抬眼轻声：“潘姑娘才思过人，又知内情，或许有办法。只是交情尚浅，她未必肯尽言。”最后1秒保持对视和屋内风声。音频1潘慧、2孙、3小腿各自只借音色，不复读参考。每人只说自己的话，听者闭口；不加旁白字幕配乐。孙在画左，小腿画右，轴线固定。镜头为中景、说者近景、听者反应，不平均切镜。
```

## 图片顺序

### 图1 · C05

![C05](../../../../../assets/characters/C05/C05_FRONT_HALF_v04.png)

[原文件](../../../../../assets/characters/C05/C05_FRONT_HALF_v04.png) · identity_master

### 图2 · E06

![E06](../../../../../assets/characters/E06/E06_MAID_v01.png)

[原文件](../../../../../assets/characters/E06/E06_MAID_v01.png) · source_image

### 图3 · S06

![S06](../../../../../assets/scenes/S06_ROOM_NIGHT_v01.png)

[原文件](../../../../../assets/scenes/S06_ROOM_NIGHT_v01.png) · source_image

### 图4 · C01

![C01](../../../../../assets/characters/C01/C01_DISGUISE_FRONT_HALF_v01.png)

[原文件](../../../../../assets/characters/C01/C01_DISGUISE_FRONT_HALF_v01.png) · identity_master

### 图5 · C03

![C03](../../../../../assets/characters/C03/C03_DISGUISE_FRONT_HALF_v01.png)

[原文件](../../../../../assets/characters/C03/C03_DISGUISE_FRONT_HALF_v01.png) · identity_master

### 图6 · S14

![S14](../../../../../assets/scenes/S14_INN_ROOM_MORNING_v01.png)

[原文件](../../../../../assets/scenes/S14_INN_ROOM_MORNING_v01.png) · source_image

## 音频顺序

- 音频1：[VOICE_C05](../../../../../assets/audio/ch04/C05_TIMBRE_10S_v01.wav)，10秒，仅供原有对白声线。
- 音频2：[VOICE_C01](../../../../../assets/audio/ch04/C01_TIMBRE_10S_v01.wav)，10秒，仅供原有对白声线。
- 音频3：[VOICE_C03](../../../../../assets/audio/ch04/C03_TIMBRE_10S_v01.wav)，10秒，仅供原有对白声线。

## 连续状态

视频1：H01的实际末4秒（目前文件不存在）。用真实输出最后4秒或尾帧；仅对齐开头卧房，不把夜色带入客栈。 实际首尾帧同样尚未生成；规划图不能当实际输出帧。

- 开场：延续H01扶肩与床内坐起姿态，潘慧准备回答。
- 结束：客栈内小腿说完看向孙，孙正待回应。

多模态参考模式：图中初末态只是软构图约束，不与严格first_frame/last_frame API模式混投。
