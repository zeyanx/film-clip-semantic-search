# 数据目录

仓库附带两类小型数据：

- `demo_segments.jsonl`：12 条自建模拟文本与 SVG 占位图；
- `open_movies_segments.jsonl`：22 条来自《Sintel》和《Tears of Steel》的真实开放许可英文字幕，不含视频或音频。许可、署名、时间偏移和来源见 `OPEN_MOVIES_NOTICE.md`。

真实数据应使用标准 JSONL 格式，并且每条记录都保存 `rights_status` 和
`license_source`。推荐把体积较大的媒体保存在仓库外，通过本地记录中的
`source_path` 引用；不要把受版权保护的视频提交到项目或交付压缩包。

