from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import statistics
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from film_search import SearchEngine, load_jsonl
from film_search.evaluation import ndcg_at_k, recall_at_k, reciprocal_rank
from film_search.optional_models import (
    LocalClipProvider,
    LocalSentenceTransformerProvider,
    OptionalModelError,
)


def load_queries(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            relevance = record.get("relevance")
            if relevance is None and record.get("expected_segment_id"):
                relevance = {record["expected_segment_id"]: 3}
            if not isinstance(relevance, dict) or not relevance:
                raise ValueError(f"query line {line_number} requires a relevance mapping")
            rows.append({"query": str(record["query"]), "relevance": relevance})
    if not rows:
        raise ValueError("query file is empty")
    return rows


def evaluate_configuration(name: str, engine: SearchEngine, queries: list[dict], method: str) -> dict:
    latencies_ms: list[float] = []
    raw_rows: list[dict] = []
    recall1_values: list[float] = []
    recall5_values: list[float] = []
    mrr_values: list[float] = []
    ndcg_values: list[float] = []
    for item in queries:
        started = time.perf_counter()
        results = engine.search(item["query"], top_k=5, method=method)
        latencies_ms.append((time.perf_counter() - started) * 1000)
        ranked_ids = [result.segment.segment_id for result in results]
        relevance = {key: int(value) for key, value in item["relevance"].items()}
        metrics = {
            "recall_at_1": recall_at_k(ranked_ids, relevance, 1),
            "recall_at_5": recall_at_k(ranked_ids, relevance, 5),
            "mrr_at_5": reciprocal_rank(ranked_ids, relevance, 5),
            "ndcg_at_5": ndcg_at_k(ranked_ids, relevance, 5),
        }
        recall1_values.append(metrics["recall_at_1"])
        recall5_values.append(metrics["recall_at_5"])
        mrr_values.append(metrics["mrr_at_5"])
        ndcg_values.append(metrics["ndcg_at_5"])
        raw_rows.append(
            {
                "configuration": name,
                "query": item["query"],
                "relevance": relevance,
                "ranked_ids": ranked_ids,
                "scores": [round(result.similarity, 8) for result in results],
                "methods_used": [result.method_used for result in results],
                "latency_ms": latencies_ms[-1],
                **metrics,
            }
        )
    return {
        "configuration": name,
        "status": "completed",
        "scope": "simulated_demo_only",
        "queries": len(queries),
        "recall_at_1": statistics.fmean(recall1_values),
        "recall_at_5": statistics.fmean(recall5_values),
        "mrr_at_5": statistics.fmean(mrr_values),
        "ndcg_at_5": statistics.fmean(ndcg_values),
        "average_latency_ms": statistics.fmean(latencies_ms),
        "raw_rows": raw_rows,
    }


def unavailable_row(name: str, reason: str, *, index_time_ms: float | None = None) -> dict:
    return {
        "configuration": name,
        "status": "not_run",
        "scope": "simulated_demo_only",
        "queries": 0,
        "recall_at_1": None,
        "recall_at_5": None,
        "mrr_at_5": None,
        "ndcg_at_5": None,
        "average_latency_ms": None,
        "index_time_ms": index_time_ms,
        "reason": reason,
        "raw_rows": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the simulated functional dataset.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "data" / "demo_segments.jsonl")
    parser.add_argument("--queries", type=Path, default=PROJECT_ROOT / "data" / "demo_queries.jsonl")
    parser.add_argument("--json-output", type=Path, default=PROJECT_ROOT.parent / "experiment_raw_results.json")
    parser.add_argument("--csv-output", type=Path, default=PROJECT_ROOT.parent / "experiment_results.csv")
    parser.add_argument("--report-output", type=Path, default=PROJECT_ROOT.parent / "experiment_report.md")
    args = parser.parse_args()

    segments = load_jsonl(args.dataset)
    queries = load_queries(args.queries)
    summaries: list[dict] = []

    configurations = [
        ("tfidf_full_fields", {"dialogue": 3, "scene": 1, "keywords": 2, "title": 1}),
        ("tfidf_dialogue_only_ablation", {"dialogue": 1, "scene": 0, "keywords": 0, "title": 0}),
    ]
    for name, field_weights in configurations:
        started = time.perf_counter()
        engine = SearchEngine(segments, field_weights=field_weights)
        index_time_ms = (time.perf_counter() - started) * 1000
        summary = evaluate_configuration(name, engine, queries, "tfidf")
        summary["index_time_ms"] = index_time_ms
        summaries.append(summary)

    sentence_dir = os.environ.get("FILM_SEARCH_SENTENCE_MODEL_DIR", "").strip()
    clip_dir = os.environ.get("FILM_SEARCH_CLIP_MODEL_DIR", "").strip()
    semantic = None
    if not sentence_dir:
        summaries.append(unavailable_row("multilingual_sentence_embedding", "no local sentence model configured"))
    else:
        try:
            semantic = LocalSentenceTransformerProvider(sentence_dir)
            started = time.perf_counter()
            engine = SearchEngine(segments, semantic_provider=semantic)
            index_time_ms = (time.perf_counter() - started) * 1000
            summary = evaluate_configuration("multilingual_sentence_embedding", engine, queries, "semantic")
            summary["index_time_ms"] = index_time_ms
            summaries.append(summary)
        except OptionalModelError as exc:
            summaries.append(unavailable_row("multilingual_sentence_embedding", str(exc)))

    if not sentence_dir or not clip_dir:
        missing = []
        if not sentence_dir:
            missing.append("sentence model")
        if not clip_dir:
            missing.append("CLIP model")
        summaries.append(unavailable_row("text_visual_fusion", "no local " + " and ".join(missing) + " configured"))
    else:
        try:
            visual = LocalClipProvider(clip_dir, PROJECT_ROOT)
            semantic = semantic or LocalSentenceTransformerProvider(sentence_dir)
            started = time.perf_counter()
            engine = SearchEngine(segments, semantic_provider=semantic, visual_provider=visual)
            index_time_ms = (time.perf_counter() - started) * 1000
            summary = evaluate_configuration("text_visual_fusion", engine, queries, "fusion")
            summary["index_time_ms"] = index_time_ms
            summaries.append(summary)
        except OptionalModelError as exc:
            summaries.append(unavailable_row("text_visual_fusion", str(exc)))

    serializable = {
        "evaluation_scope": "simulated_demo_only",
        "random_seed": 20261011,
        "dataset_segments": len(segments),
        "queries": len(queries),
        "warning": "Synthetic functional evaluation only; not a real-media performance claim.",
        "configurations": summaries,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(serializable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fieldnames = [
        "configuration",
        "status",
        "scope",
        "queries",
        "recall_at_1",
        "recall_at_5",
        "mrr_at_5",
        "ndcg_at_5",
        "average_latency_ms",
        "index_time_ms",
        "reason",
    ]
    with args.csv_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for summary in summaries:
            row = dict(summary)
            for field in ("average_latency_ms", "index_time_ms"):
                if isinstance(row.get(field), float):
                    row[field] = round(row[field], 6)
            writer.writerow(row)

    report_lines = [
        "# 影视剪辑素材检索实验报告",
        "",
        "## 实验边界",
        "",
        "本次运行只使用项目自建模拟文本、模拟查询和 SVG 占位图。它验证评测链路，不能代表真实动漫、电视剧或电影中的检索性能。",
        "",
        f"- 模拟片段：{len(segments)} 条",
        f"- 模拟查询：{len(queries)} 条",
        "- 随机种子记录：20261011（算法本身为确定性，没有随机抽样）",
        "- 数据划分：模拟数据只作功能检查；未进行真实训练/验证/测试划分",
        "",
        "## 实际结果",
        "",
        "| 配置 | 状态 | Recall@1 | Recall@5 | MRR@5 | nDCG@5 | 平均延迟(ms) | 索引时间(ms) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    not_run_notes: list[str] = []
    for summary in summaries:
        def shown(name):
            value = summary.get(name)
            return "—" if value is None else f"{value:.6f}"
        report_lines.append(
            f"| {summary['configuration']} | {summary['status']} | {shown('recall_at_1')} | "
            f"{shown('recall_at_5')} | {shown('mrr_at_5')} | {shown('ndcg_at_5')} | "
            f"{shown('average_latency_ms')} | {shown('index_time_ms')} |"
        )
        if summary.get("reason"):
            not_run_notes.append(
                f"- `{summary['configuration']}` 未运行：{summary['reason']}。"
            )
    report_lines.extend(
        [
            "",
            "## 未运行配置",
            "",
            *(not_run_notes or ["无。"]),
            "",
            "## 消融解释",
            "",
            "`tfidf_dialogue_only_ablation` 移除了场景描述、关键词和标题字段，用于观察结构化辅助文本的影响。任何差异都只针对当前模拟查询，不外推到真实影视。",
            "",
            "## 真实性能所需后续数据",
            "",
            "需要用户提供合法媒体或可核验开放许可素材，按媒体分组划分，并人工标注查询到片段的相关等级；随后应重新运行同一脚本，不能沿用本报告数值。",
        ]
    )
    args.report_output.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps(serializable, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
