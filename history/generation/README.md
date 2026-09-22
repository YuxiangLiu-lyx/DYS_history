# 原始生成记录与恢复

本目录保存本轮完整Prompt、实际引用、输出原路径和复用关系。PATH_RELOCATION.json按文件SHA将历史临时路径映射至本包实际图片；图片原字节保留，不依赖原机器。

早期22图原索引在archive/costume_pack_v1/asset_index.json。其中少数旧Prompt只留下摘要或“Full prompt in conversation”，完整原文当前不可恢复，保持原记录不伪造补全。未来生成必须把完整Prompt实际写入此目录，不能只指向聊天。

新图为候选，generation prompt中个别“approved reference”是当时工具描述，不能据此认定用户已批准本轮新图；用户审阅状态以context/STATUS.json为准。首轮潘慧错边点、披帛纹理错误、A台阶与G21雨景初稿已被后续版本替代。

image_gen未返回内部模型确切版本、seed或计费账单；这些字段为未知，不能根据PNG数量捏造费用。当前未发生视频生成费用。
