# H05 · 琴落草间，歌后静默 · v1.3

本场10秒；全片起点：90 + D_H04。D_H04未定。

**状态：导演准备稿；实际前片和动态音画验收未完成。**

先复制本场TXT，再按图片、音频、视频编号投料。缺项MD不是媒体，不上传，不用其他文件顶替。

## Prompt

627字符，含换行。

```text
10秒，16:9真实古装电影。图1孙、图2潘是唯一脸部母版，保留真人脸型、眉眼鼻唇、年龄和发际线，不美型换脸。潘自然短圆脸，痣按图2正脸画面右侧嘴角下方皮肤、与唇线留间隔；与玉簪同侧，不镜像。其他图只取姿态/空间，不递归继承漂移的脸。图3同一夕照草坡，图4阮全形，图5孙持阮手位，图6开场1.8米站位，图7只供中段蹲身落琴动作，图8只供末态1.2米站位与地面琴位。视频1接H04真实最后4秒，仅从歌与琴尾已结束的最终状态续接；起点由最终音轨确定，不能剪断末字、琴尾或重唱。
0–1.5秒双人中景：歌与琴已自然结束，孙低头轻笑，潘看他，留第一次短静默。1.5–6.5秒保持连续镜头，孙左手稳琴颈、右手托琴盘，屈膝把阮轻放自己画左后方半步的软草地，避开两人靠近路线；琴面朝上、琴颈指画左后方，四弦金纹短红穗完整，琴触地稳定后松手，才直起，不能一闪落地。潘原位安静等待，不伸手拉他。6.5–8秒孙站稳，小半步回到约1.2米处。8–10秒双手自然垂下，抬眼互望；没有歌后情绪才渐渐显露，本段不吻。
孙在画左、潘在画右，摄影机不越轴；同一巨松、草坡坡度、山脊和夕阳方向。以图3统一逆光，不追随关键帧中漂移的太阳位置。自然草浪、远山薄雾、金橙浅粉晚霞，少量松针。无跳舞、转圈、甩头、搭肩、搂腰、搂颈、突抱、夸张摸脸、现代物件、字幕旁白；阮不变琵琶或吉他，不穿手，不增减红穗。不上传歌曲或音色；仅草叶、衣料、呼吸和自然风。保持H04尾音已结束的状态，不人为掐掉声音。
```

## 图片顺序

### 图1 · C01

![C01](../../../../../assets/characters/C01/C01_DISGUISE_FRONT_HALF_v01.png)

[原文件](../../../../../assets/characters/C01/C01_DISGUISE_FRONT_HALF_v01.png) · identity_master

### 图2 · C05

![C05](../../../../../assets/characters/C05/C05_FRONT_HALF_v04.png)

[原文件](../../../../../assets/characters/C05/C05_FRONT_HALF_v04.png) · identity_master

### 图3 · S15_NEW

![S15_NEW](../../../../../assets/scenes/S15_PINE_MEADOW_SUNSET_v01.png)

[原文件](../../../../../assets/scenes/S15_PINE_MEADOW_SUNSET_v01.png) · source_image

### 图4 · P_RUAN

![P_RUAN](../../../../../assets/props/CH04/P_RUAN_ORNATE_v01.png)

[原文件](../../../../../assets/props/CH04/P_RUAN_ORNATE_v01.png) · source_image

### 图5 · C01_RUAN_HOLD

![C01_RUAN_HOLD](../../../../../assets/characters/C01/C01_RUAN_HOLD_v01.png)

[原文件](../../../../../assets/characters/C01/C01_RUAN_HOLD_v01.png) · pose_and_composition_only

### 图6 · KF_H06_START

![KF_H06_START](../../../../../assets/keyframes/CH04/H06_START_MEADOW_v01.png)

[原文件](../../../../../assets/keyframes/CH04/H06_START_MEADOW_v01.png) · pose_and_composition_only

### 图7 · KF_SETDOWN

![KF_SETDOWN](../../../../../assets/keyframes/CH04/H06_SETDOWN_MEADOW_v01.png)

[原文件](../../../../../assets/keyframes/CH04/H06_SETDOWN_MEADOW_v01.png) · pose_and_composition_only

### 图8 · KF_H07_START

![KF_H07_START](../../../../../assets/keyframes/CH04/H07_START_MEADOW_v02.png)

[原文件](../../../../../assets/keyframes/CH04/H07_START_MEADOW_v02.png) · pose_and_composition_only

## 音频顺序

不上传独立歌曲或声线；仅自然环境、衣料与呼吸。

## 连续状态

视频1：H04的实际末4秒（目前文件不存在）。取 H04 最后4秒并确认歌句和琴尾完整结束，接约1.8米与双手持阮。音源未锁前不能填写全片起点。 实际首尾帧同样尚未生成；规划图不能当实际输出帧。

- 开场：完整歌句与自然尾音结束；两人约1.8米相望，孙仍双手持阮，无接触。
- 结束：琴已稳放画左后方、靠近路线外，面朝上颈朝左后方；孙左潘右，双手下垂，约1.2米互望。

多模态参考模式：图中初末态只是软构图约束，不与严格first_frame/last_frame API模式混投。
