# 第四回 · 七个独立场景文件

每一行对应一个独立ZIP。每包包含可复制Prompt、按上传号排列的实际图片与现有音频、前段视频说明及离线index.html。H01/H02沿用此前原包，H03–H06更新，新增H07；共210秒。

| 独立文件 | 内容 | 本场清单 |
|---|---|---|
| CH04_H01.zip | 三梦惊醒（30秒） | [H01](scenes/H01/README.md) |
| CH04_H02.zip | 梦醒未安，客栈议策（30秒） | [H02](scenes/H02/README.md) |
| CH04_H03.zip | 以曲相邀，松下将逢（30秒） | [H03](scenes/H03/README.md) |
| CH04_H04.zip | 循声回首，暮色相望（30秒） | [H04](scenes/H04/README.md) |
| CH04_H05.zip | 一曲相答，草间渐近（30秒） | [H05](scenes/H05/README.md) |
| CH04_H06.zip | 歌声渐歇，松下凝眸（30秒） | [H06](scenes/H06/README.md) |
| CH04_H07.zip | 天地无声，松下相吻（30秒） | [H07](scenes/H07/README.md) |

H03–H07图片已齐。H04–H06音频1仍待实际《卜卦》曲参，男/女音色固定音频2/3；缺项说明不能上传或挤掉编号。H07无外部歌曲/声线输入，只生成自然环境声。前段MP4尚未制作，不能上传假文件。

H01图4/5/6固定密集弹幕、求婚、打码聊天；前三回不变。当前歌唱秒数为导演预排，不能代替实源口型实测。

重建全部七包：`python3 tools/build_ch04_scene_files.py --out <输出目录>`。只重建新版五包，加`--blocks H03 H04 H05 H06 H07`。保存记录见`history/generation/CH04_scene_files_delivery.json`。
