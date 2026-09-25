# Seedance规格核验 · 2026-09-25

依据字节Seed官方与火山方舟API文档；实际制作界面未成功查看，因此不能保证产品UI与API入口参数完全相同。

|项目|本轮核验结果|本包做法|
|---|---|---|
|模型/时长|Seedance 2.5；API模型 doubao-seedance-2-5-260628；单段最多30秒|H01–H03已完成并冻结；H04/H05各30秒完整覆盖用户60秒音轨；H06–H09为12/18/14/24秒|
|参考数量|最多30图+10视频+10音频，合计50|每场按清单少量投料，50不是50张图片|
|音频|wav/mp3，单条2–30秒，合计≤30秒；单条≤15MB，请求音频合计≤64MB|H04/H05各只上传对应的一条连续30秒切片，不加声线；最终铺原完整60秒音轨|
|视频|参考合计≤30秒；支持引用/编辑/延长|已完成H03及后续实际前片取末4秒；H03不重做，不上传累计60/90秒|
|首尾帧|严格first_frame/last_frame与全能多模态参考不可同次混用|本包选多模态参考，规划首末态图只作软构图约束，不承诺严格首尾|
|分辨率|API 480p/720p/1080p，默认720p|计划16:9、1080p；不把其他产品宣传4K写成此API能力|
|音声/口型|支持音频参考与原生音画生成|不保证现成歌逐字唱者正确，须实片验证|
|Prompt|本项目用户输入限制小于2000字符|每个TXT按全部字符含换行校验；不是官方API2000硬限声明|

推荐当前组合：独立人物母版+同场景+完整阮+动作参考+上一段真实短尾片；唱段再加唯一真实歌曲。各类素材显式写编号，构图帧不替换人物身份。官方建议参考主体聚焦，不能为了达到上限塞图。

本包使用多模态 `reference_image/reference_audio/reference_video`。若改用严格首尾帧入口，须单独重建输入，不能把此包角色/音频参照与严格模式强混。API延长/编辑及严格首尾模式按官方采用 `ratio=adaptive` 并以16:9输入继承；普通参考生成用16:9。扩展时只接真正新增片段，保留连续音轨；本版不强制使用旧“两次30秒延长”结构。

本项目前次检查时，Runway连接已认证，但当时免费工作区未提供视频模型，暴露的generate_video包装也无音频参考字段。本轮未重新查询其能力，未发起付费视频生成，未生成Seedance成片。以上不影响素材/Prompt制作；不能把已认证当成精确对唱可执行证明。

来源：[Seedance 2.5](https://seed.bytedance.com/zh/seedance2_5) · [官方介绍](https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5) · [方舟视频API](https://docs.volcengine.com/docs/ark/create-video-generation-task-api?lang=zh&redirect=1) · [Prompt指南](https://docs.volcengine.com/docs/ark/seedance-2-5-prompt-guide?lang=zh)。
