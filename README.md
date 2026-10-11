# 影视剪辑素材语义搜索系统

一个可离线运行的本科机器学习课程项目。用户输入台词、关键词或场景描述，系统从**有权处理的本地素材索引**中检索片段，并返回影片名称、匹配台词、起止时间、所在分钟、相似度、分项得分、匹配原因和关键帧。

项目不含真实影视文件、下载器、抓取器或大型模型。除原有的 12 条自建模拟片段外，现已加入《Sintel》和《Tears of Steel》共 22 条 CC BY 3.0 真实英文字幕记录；真实库与模拟库可在侧栏切换。许可与时间来源见 `data/OPEN_MOVIES_NOTICE.md`。

公网演示：https://film-clip-search-zeyanx.streamlit.app/

源码仓库：https://github.com/zeyanx/film-clip-semantic-search

## 已实现

- A：离线字符/词 TF-IDF + 余弦相似度基线；
- B：可选本地多语言句向量接口，模型缺失时明确回退；
- C：可选本地 CLIP 关键帧接口与加权融合，缺失分支不伪装为已运行；
- 中文/英文查询、Top-K、阈值、标题和媒体类型过滤；
- 同一媒体中相邻或重叠结果去重；
- JSONL 严格数据与权限校验；
- SRT/VTT 导入、MP4/MKV/MOV 等视频识别、固定窗口和可选 FFmpeg 抽帧；
- JSON 索引保存、载入和按 `segment_id` 增量更新；
- Streamlit 五个标签页：搜索、素材导入与建库、模型设置、实验评测、数据与版权；
- Recall@1/5、MRR@5、nDCG@5、延迟、索引时间和字段消融评测；
- 自动测试与可解释的真实性能边界。
- 开放许可真实字幕库：两部 Blender Foundation 开放电影、22 条字幕、原片时间戳与署名追溯；不把它冒充已标注的真实检索实验。

## 快速运行

在本目录打开 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
.\.venv\Scripts\python.exe -m streamlit run app.py
```

或者在依赖已安装的环境中执行：

```powershell
.\run_app.ps1
```

网页默认使用 `data\demo_segments.jsonl`，并醒目标明模拟数据边界。普通结果页不会显示本地绝对路径。

## 命令行搜索

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m film_search.cli "雨夜站台告别" --top-k 3 --method tfidf
```

`--method` 支持 `tfidf`、`semantic`、`fusion`。后两者只有在本地模型配置成功时才真正运行，否则结果字段会记录回退原因。

## 本地可选模型

应用不会自动下载模型。首次下载前应单独核对模型名称、体积、许可证和硬件要求。配置本地目录：

```powershell
$env:FILM_SEARCH_SENTENCE_MODEL_DIR = 'D:\models\sentence-model'
$env:FILM_SEARCH_CLIP_MODEL_DIR = 'D:\models\clip-model'
```

句向量分支需要兼容 `sentence-transformers` 的本地模型和相应 Python 包；视觉分支需要本地 CLIP 模型以及 `transformers`、`torch`、`Pillow`。这些不是基础版依赖。

## 导入字幕

仅在你确实有权处理相应字幕和媒体时使用：

```powershell
python .\tools\import_srt.py `
  --srt "D:\authorized_media\example.srt" `
  --output "D:\authorized_media\example.jsonl" `
  --title "已授权素材名称" `
  --media-id "authorized_example" `
  --media-type movie `
  --rights-status authorized `
  --license-source "授权文件或许可证说明" `
  --media-path "D:\authorized_media\example.mp4" `
  --confirm-rights
```

SRT/VTT 不包含可靠场景描述。生成的记录会如实写明“未提供场景描述”，不会自动编造。

## 无字幕视频窗口

如果本地安装了 FFprobe，可按固定窗口创建记录；安装 FFmpeg 后还可抽取窗口中点关键帧：

```powershell
python .\tools\index_video_windows.py `
  --video "D:\authorized_media\example.mp4" `
  --output "D:\authorized_media\example_windows.jsonl" `
  --keyframe-dir "D:\authorized_media\keyframes" `
  --title "已授权素材名称" `
  --media-id "authorized_example" `
  --rights-status authorized `
  --license-source "授权说明" `
  --confirm-rights
```

没有 FFprobe 时工具会给出明确错误；没有 FFmpeg 时不会声称已抽帧。

## 索引保存与增量更新

```powershell
python .\tools\build_index.py --dataset .\data\demo_segments.jsonl --output .\data\demo.index.json
python .\tools\build_index.py --dataset D:\authorized\new.jsonl --existing-index .\data\demo.index.json --output D:\authorized\updated.index.json
```

## 测试与评测

```powershell
.\run_tests.ps1
python .\tools\evaluate_demo.py
```

加入开放电影字幕库后需重新执行测试；模拟集指标和未运行模型状态见 `data/experiment_results.csv` 与交付目录中的 `experiment_report.md`。模拟集的满分只证明测试样例可被基线找回，不代表真实影视泛化能力；开放电影字幕库没有相关性标注，因此暂不报告真实检索指标。

## 目录

```text
film_clip_semantic_search/
├─ app.py
├─ src/film_search/            检索、数据、字幕、媒体、索引、指标与可选模型
├─ data/                       模拟数据、开放电影真实字幕库和数据说明
├─ assets/keyframes/           自建模拟 SVG
├─ tools/                      字幕/视频导入、索引、评测
├─ tests/                      自动测试
└─ docs/                       数据规范、评测协议、测试记录和实现说明
```

## 当前边界

- 已接入两部开放电影的真实字幕，但没有提交影片本体，也没有真实相关性标注，因此没有真实媒体性能数据；
- 没有配置本地句向量或 CLIP 模型，因此 B/C 在本次实验中是 `not_run`；
- 预训练模型不是本项目训练成果；
- 获得合法媒体后必须重新标注并运行同一评测协议，不能沿用模拟指标。

