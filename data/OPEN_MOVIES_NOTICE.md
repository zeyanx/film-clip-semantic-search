# 开放电影真实字幕库说明

本库包含 22 条真实英文字幕记录，来自 Blender Foundation 的两部开放电影片段。它不是模拟语料，但也不是经过人工相关性标注的检索评测集。

| 作品 | 纳入范围 | 记录数 | 许可与署名 | 原始来源 |
|---|---:|---:|---|---|
| Sintel | 原片 01:45–02:30 | 11 | CC BY 3.0；© copyright Blender Foundation \| durian.blender.org | https://durian.blender.org/sharing/ |
| Tears of Steel | 原片 00:20–01:05 | 11 | CC BY 3.0；(CC) Blender Foundation \| mango.blender.org | https://mango.blender.org/sharing/ |

字幕取自 `ActuallyAnson/moment` 仓库中已重新对齐到 45 秒片段的官方英文字幕：

- https://github.com/ActuallyAnson/moment/blob/main/clips/sintel/subs.srt
- https://github.com/ActuallyAnson/moment/blob/main/clips/tos/subs.srt
- 该仓库的素材来源与署名说明：https://github.com/ActuallyAnson/moment/blob/main/clips/NOTICE.md

`open_movies_segments.jsonl` 已把片段内时间加回原片起始偏移量：Sintel 加 105 秒，Tears of Steel 加 20 秒。因此网页显示的是原片分钟位置，不是截取文件内部时间。

只为字幕实际覆盖的代表时刻引用两张开放许可关键帧：Sintel 原片约 02:09.5，以及 Tears of Steel 原片约 00:29。其余记录不显示关键帧，且没有补写未经核验的场景描述。仓库不包含两部影片的视频或音频文件。

