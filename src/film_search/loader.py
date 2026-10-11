from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
from typing import Any

from .models import ALLOWED_MEDIA_TYPES, ALLOWED_RIGHTS, Segment


class DatasetError(ValueError):
    pass


REQUIRED_FIELDS = {
    "segment_id",
    "title",
    "dialogue",
    "scene_description",
    "keywords",
    "start_seconds",
    "end_seconds",
    "keyframe_path",
    "media_path",
    "rights_status",
    "license_source",
    "is_simulated",
}


def _optional_vector(record: dict[str, Any], name: str, *, location: str) -> tuple[float, ...]:
    value = record.get(name, [])
    if value in (None, []):
        return ()
    if not isinstance(value, list) or not value:
        raise DatasetError(f"{location}{name} must be a non-empty numeric list when supplied")
    try:
        vector = tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise DatasetError(f"{location}{name} must contain only numbers") from exc
    if not all(math.isfinite(item) for item in vector):
        raise DatasetError(f"{location}{name} must contain only finite values")
    return vector


def _derived_media_id(title: str, source_path: str) -> str:
    seed = f"{title.casefold()}\n{source_path.casefold()}".encode("utf-8")
    return "media_" + hashlib.sha1(seed).hexdigest()[:12]


def parse_segment(record: dict[str, Any], *, line_number: int = 0) -> Segment:
    missing = sorted(REQUIRED_FIELDS - record.keys())
    location = f"line {line_number}: " if line_number else ""
    if missing:
        raise DatasetError(f"{location}missing fields: {', '.join(missing)}")

    rights_status = str(record["rights_status"]).strip()
    if rights_status not in ALLOWED_RIGHTS:
        raise DatasetError(f"{location}unsupported rights_status: {rights_status!r}")

    is_simulated = record["is_simulated"]
    if not isinstance(is_simulated, bool):
        raise DatasetError(f"{location}is_simulated must be true or false")
    if is_simulated != (rights_status == "simulated"):
        raise DatasetError(
            f"{location}is_simulated must be true exactly when rights_status is 'simulated'"
        )

    license_source = str(record["license_source"]).strip()
    if not license_source:
        raise DatasetError(f"{location}license_source must not be empty")

    keywords_value = record["keywords"]
    if not isinstance(keywords_value, list) or not all(
        isinstance(item, str) and item.strip() for item in keywords_value
    ):
        raise DatasetError(f"{location}keywords must be a list of non-empty strings")

    try:
        start_seconds = float(record["start_seconds"])
        end_seconds = float(record["end_seconds"])
    except (TypeError, ValueError) as exc:
        raise DatasetError(f"{location}start_seconds and end_seconds must be numeric") from exc
    if start_seconds < 0 or end_seconds <= start_seconds:
        raise DatasetError(f"{location}time range must satisfy 0 <= start < end")

    text_fields = {
        name: str(record[name]).strip()
        for name in ("segment_id", "title", "dialogue", "scene_description")
    }
    if not text_fields["segment_id"] or not text_fields["title"]:
        raise DatasetError(f"{location}segment_id and title must not be empty")
    if not text_fields["dialogue"] and not text_fields["scene_description"]:
        raise DatasetError(f"{location}dialogue and scene_description cannot both be empty")

    source_path = str(record.get("source_path", record.get("media_path", ""))).strip()
    media_id = str(record.get("media_id", "")).strip() or _derived_media_id(
        text_fields["title"], source_path
    )
    media_type = str(record.get("media_type", "other")).strip().casefold()
    if media_type not in ALLOWED_MEDIA_TYPES:
        raise DatasetError(
            f"{location}media_type must be one of: {', '.join(sorted(ALLOWED_MEDIA_TYPES))}"
        )

    return Segment(
        **text_fields,
        keywords=tuple(item.strip() for item in keywords_value),
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        keyframe_path=str(record["keyframe_path"]).strip(),
        media_path=str(record["media_path"]).strip(),
        rights_status=rights_status,
        license_source=license_source,
        is_simulated=is_simulated,
        media_id=media_id,
        media_type=media_type,
        source_path=source_path,
        semantic_vector=_optional_vector(record, "semantic_vector", location=location),
        visual_vector=_optional_vector(record, "visual_vector", location=location),
    )


def load_jsonl(path: str | Path) -> list[Segment]:
    dataset_path = Path(path)
    if not dataset_path.is_file():
        raise DatasetError(f"dataset does not exist: {dataset_path}")

    segments: list[Segment] = []
    seen_ids: set[str] = set()
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise DatasetError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise DatasetError(f"line {line_number}: each line must contain a JSON object")
            segment = parse_segment(record, line_number=line_number)
            if segment.segment_id in seen_ids:
                raise DatasetError(f"line {line_number}: duplicate segment_id {segment.segment_id!r}")
            seen_ids.add(segment.segment_id)
            segments.append(segment)

    if not segments:
        raise DatasetError(f"dataset is empty: {dataset_path}")
    return segments


def load_jsonl_text(text: str, *, source_name: str = "uploaded JSONL") -> list[Segment]:
    segments: list[Segment] = []
    seen_ids: set[str] = set()
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise DatasetError(
                f"{source_name}, line {line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(record, dict):
            raise DatasetError(f"{source_name}, line {line_number}: expected a JSON object")
        segment = parse_segment(record, line_number=line_number)
        if segment.segment_id in seen_ids:
            raise DatasetError(
                f"{source_name}, line {line_number}: duplicate segment_id {segment.segment_id!r}"
            )
        seen_ids.add(segment.segment_id)
        segments.append(segment)
    if not segments:
        raise DatasetError(f"{source_name} is empty")
    return segments

