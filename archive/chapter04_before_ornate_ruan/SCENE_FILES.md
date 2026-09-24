# 第四回 · 六个独立场景文件

每一行对应一个独立ZIP；每包都有自己的Prompt、编号图片、编号音频、上传说明与离线index.html。解压任意一包即可独立查看，不依赖其他包。

| 独立文件 | 内容 | 本场清单 |
|---|---|---|
| CH04_H01.zip | 三梦惊醒（30秒） | [H01](scenes/H01/README.md) |
| CH04_H02.zip | 梦醒未安，客栈议策（30秒） | [H02](scenes/H02/README.md) |
| CH04_H03.zip | 以曲相邀，松下将逢（30秒） | [H03](scenes/H03/README.md) |
| CH04_H04.zip | 男声起曲，她循声回首（30秒） | [H04](scenes/H04/README.md) |
| CH04_H05.zip | 女声接曲，放琴相携（30秒） | [H05](scenes/H05/README.md) |
| CH04_H06.zip | 伴奏渐歇，清唱定情（30秒） | [H06](scenes/H06/README.md) |

H01梦图顺序：图4密集弹幕→图5求婚→图6打码聊天。各场缺项保留原编号，尤其H04–H06歌曲音频1尚待补；已附人物音色不是歌曲。

重建：`python3 tools/build_ch04_scene_files.py --out <输出目录>`。保存记录见仓库 `history/generation/CH04_scene_files_delivery.json`。
