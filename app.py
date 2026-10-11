from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

from film_search import DatasetError, SearchEngine, load_jsonl, load_jsonl_text
from film_search.media import find_media_tool
from film_search.optional_models import (
    LocalClipProvider,
    LocalSentenceTransformerProvider,
    OptionalModelError,
)
from film_search.subtitles import parse_srt, parse_vtt
from film_search.timecode import format_range


DEFAULT_DATASET = PROJECT_ROOT / "data" / "demo_segments.jsonl"
EXPERIMENT_CSV = PROJECT_ROOT / "data" / "experiment_results.csv"
MEDIA_TYPE_LABELS = {
    "全部类型": "",
    "动漫": "anime",
    "电视剧": "tv",
    "电影": "movie",
    "其他": "other",
}


def optional_providers():
    semantic = None
    visual = None
    messages: list[str] = []
    sentence_dir = os.environ.get("FILM_SEARCH_SENTENCE_MODEL_DIR", "").strip()
    clip_dir = os.environ.get("FILM_SEARCH_CLIP_MODEL_DIR", "").strip()
    if sentence_dir:
        try:
            semantic = LocalSentenceTransformerProvider(sentence_dir)
            messages.append("句向量：已从本地目录加载")
        except OptionalModelError as exc:
            messages.append(f"句向量：不可用（{exc}）")
    else:
        messages.append("句向量：未配置本地模型目录")
    if clip_dir:
        try:
            visual = LocalClipProvider(clip_dir, PROJECT_ROOT)
            messages.append("视觉模型：已从本地目录加载")
        except OptionalModelError as exc:
            messages.append(f"视觉模型：不可用（{exc}）")
    else:
        messages.append("视觉模型：未配置本地模型目录")
    return semantic, visual, messages


def resolve_asset(raw_path: str) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        return None
    return resolved if resolved.is_file() else None


def build_engine(segments):
    semantic, visual, messages = optional_providers()
    return SearchEngine(
        segments, semantic_provider=semantic, visual_provider=visual
    ), messages


def load_active_segments():
    uploaded = st.sidebar.file_uploader(
        "导入标准 JSONL（可选）", type=["jsonl"], help="文件只在当前会话中解析。"
    )
    if uploaded is None:
        return load_jsonl(DEFAULT_DATASET), "内置模拟数据"
    text = uploaded.getvalue().decode("utf-8-sig")
    return load_jsonl_text(text, source_name=uploaded.name), uploaded.name


def render_result(result) -> None:
    segment = result.segment
    with st.container(border=True):
        left, right = st.columns([2, 3])
        with left:
            keyframe = resolve_asset(segment.keyframe_path)
            if keyframe:
                st.image(str(keyframe), width="stretch")
            else:
                st.info("该片段没有可用关键帧。")
        with right:
            st.subheader(f"#{result.rank} · {segment.title}")
            if segment.dialogue:
                st.markdown(f"> {segment.dialogue}")
            metric_a, metric_b, metric_c = st.columns(3)
            metric_a.metric("总相似度", f"{result.similarity:.3f}")
            metric_b.metric("起止时间", format_range(segment.start_seconds, segment.end_seconds))
            metric_c.metric("所在分钟", f"第 {segment.minute_number} 分钟")
            score_text = " · ".join(
                f"{name}={value:.3f}" for name, value in result.component_scores.items()
            )
            st.caption(f"分项：{score_text}；匹配原因：{result.explanation}")
            if result.fallback_reason:
                st.warning(result.fallback_reason)
            st.caption(f"场景：{segment.scene_description or '未提供'}")
            st.caption(f"关键词：{'、'.join(segment.keywords) if segment.keywords else '未提供'}")
            status = "模拟演示数据" if segment.is_simulated else segment.rights_status
            st.caption(f"权限状态：{status}；依据：{segment.license_source}")
            media = resolve_asset(segment.effective_source_path)
            if media and media.suffix.casefold() in {".mp4", ".mov", ".m4v", ".webm"}:
                st.video(str(media), start_time=int(segment.start_seconds))


def subtitle_import_tab() -> None:
    st.subheader("导入字幕并生成标准 JSONL")
    st.write("字幕不会上传到外部服务。生成前必须确认你有权处理相应素材。")
    subtitle = st.file_uploader("选择 SRT 或 VTT", type=["srt", "vtt"])
    title = st.text_input("影片/素材名称", key="import_title")
    media_id = st.text_input("媒体 ID", value="local_media", key="import_media_id")
    media_type = st.selectbox("媒体类型", ["movie", "tv", "anime", "other"])
    rights = st.selectbox(
        "权限状态", ["authorized", "public_domain", "permissive_license"]
    )
    license_source = st.text_input("授权文件或许可证说明")
    confirmed = st.checkbox("我确认有权处理这份字幕及其对应媒体")
    if not subtitle:
        st.info("选择字幕后可预览并下载标准 JSONL。")
        return
    if not all([title.strip(), media_id.strip(), license_source.strip(), confirmed]):
        st.warning("请填写名称、媒体 ID、权限依据并确认权利。")
        return
    try:
        text = subtitle.getvalue().decode("utf-8-sig")
        cues = parse_vtt(text) if subtitle.name.casefold().endswith(".vtt") else parse_srt(text)
    except (UnicodeDecodeError, ValueError) as exc:
        st.error(f"字幕解析失败：{exc}")
        return
    records = []
    for index, cue in enumerate(cues, start=1):
        records.append(
            {
                "segment_id": f"{media_id.strip()}_{index:06d}",
                "media_id": media_id.strip(),
                "title": title.strip(),
                "media_type": media_type,
                "dialogue": cue.text,
                "scene_description": "由本地字幕导入；尚未提供场景描述。",
                "keywords": ["字幕导入"],
                "start_seconds": cue.start_seconds,
                "end_seconds": cue.end_seconds,
                "keyframe_path": "",
                "source_path": "",
                "media_path": "",
                "rights_status": rights,
                "license_source": license_source.strip(),
                "is_simulated": False,
            }
        )
    payload = "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n"
    st.success(f"已解析 {len(records)} 条字幕。")
    st.dataframe(records[:20], width="stretch")
    st.download_button(
        "下载标准 JSONL",
        payload.encode("utf-8"),
        file_name=f"{media_id.strip()}_segments.jsonl",
        mime="application/x-ndjson",
    )


def main() -> None:
    st.set_page_config(page_title="影视剪辑素材语义搜索系统", page_icon="🎬", layout="wide")
    st.title("🎬 影视剪辑素材语义搜索系统")
    st.write("从有权处理的本地素材中检索台词与场景，返回时间位置、关键帧和可解释分数。")

    with st.sidebar:
        st.header("检索设置")
        method_label = st.selectbox(
            "模型配置",
            ["A · TF-IDF 基线", "B · 多语言句向量", "C · 文本—视觉融合"],
        )
        method = {"A": "tfidf", "B": "semantic", "C": "fusion"}[method_label[0]]
        top_k = st.slider("返回数量", 1, 20, 5)
        min_similarity = st.slider("最低相似度", 0.0, 1.0, 0.05, 0.01)
        media_type_label = st.selectbox("媒体类型", list(MEDIA_TYPE_LABELS))
        st.caption("系统不会联网下载影视内容或模型。")

    try:
        segments, dataset_label = load_active_segments()
        engine, model_messages = build_engine(segments)
    except (DatasetError, UnicodeDecodeError, ValueError) as exc:
        st.error(f"数据集无法加载：{exc}")
        st.stop()

    titles = sorted({segment.title for segment in segments})
    simulated_count = sum(segment.is_simulated for segment in segments)
    if simulated_count:
        st.warning(
            f"当前数据源“{dataset_label}”含 {simulated_count} 条模拟片段，只用于功能测试，"
            "不能代表真实影视检索性能。"
        )

    search_tab, import_tab, model_tab, experiment_tab, rights_tab = st.tabs(
        ["搜索", "素材导入与建库", "模型设置", "实验评测", "数据与版权"]
    )

    with search_tab:
        query = st.text_input(
            "台词、关键词或场景描述",
            placeholder="例如：雨夜站台告别 / an overheated spacecraft engine",
        )
        title_choice = st.selectbox("影片筛选", ["全部影片", *titles])
        if st.button("开始检索", type="primary"):
            if not query.strip():
                st.info("请输入检索内容。")
            else:
                with st.spinner("正在检索…"):
                    results = engine.search(
                        query,
                        top_k=top_k,
                        min_similarity=min_similarity,
                        title_filter=None if title_choice == "全部影片" else title_choice,
                        media_type_filter=MEDIA_TYPE_LABELS[media_type_label] or None,
                        method=method,
                    )
                st.subheader(f"检索结果 · {len(results)} 条")
                if not results:
                    st.info("没有超过阈值的结果。可降低阈值、取消过滤或更换描述。")
                for result in results:
                    render_result(result)

    with import_tab:
        subtitle_import_tab()
        with st.expander("无字幕视频与关键帧工具状态"):
            ffprobe = find_media_tool("ffprobe", "FILM_SEARCH_FFPROBE")
            ffmpeg = find_media_tool("ffmpeg", "FILM_SEARCH_FFMPEG")
            st.write(f"FFprobe：{'可用' if ffprobe else '未配置'}")
            st.write(f"FFmpeg：{'可用' if ffmpeg else '未配置'}")
            st.caption("未配置时仍可使用 JSONL/SRT/VTT；不会假装完成视频抽帧。")

    with model_tab:
        st.subheader("模型可用性与降级")
        for message in model_messages:
            st.write(f"- {message}")
        st.code(
            "FILM_SEARCH_SENTENCE_MODEL_DIR=<本地句向量模型目录>\n"
            "FILM_SEARCH_CLIP_MODEL_DIR=<本地CLIP模型目录>",
            language="text",
        )
        st.info("首次下载模型前应单独核对名称、大小和许可证；本应用不会自动下载。")

    with experiment_tab:
        st.subheader("实验评测")
        if EXPERIMENT_CSV.is_file():
            csv_text = EXPERIMENT_CSV.read_text(encoding="utf-8-sig")
            st.dataframe(list(csv.DictReader(io.StringIO(csv_text))), width="stretch")
        else:
            st.info("尚未生成实验汇总。请运行 tools/evaluate_demo.py。")
        st.caption("模拟指标只用于验证工程链路；真实媒体需独立标注和重新评测。")

    with rights_tab:
        st.subheader("数据与版权边界")
        st.markdown(
            "- 只导入自己提供、公共领域或许可证允许处理的媒体。\n"
            "- 项目不下载、不抓取、不分发影视文件。\n"
            "- 每条真实记录必须保存权限状态与依据。\n"
            "- 模拟数据和真实性能结论必须分开。"
        )


if __name__ == "__main__":
    main()
