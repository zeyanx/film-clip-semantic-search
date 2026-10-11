from __future__ import annotations

from dataclasses import dataclass


ALLOWED_RIGHTS = {
    "authorized",
    "public_domain",
    "permissive_license",
    "simulated",
}

ALLOWED_MEDIA_TYPES = {"anime", "tv", "movie", "other"}


@dataclass(frozen=True, slots=True)
class Segment:
    segment_id: str
    title: str
    dialogue: str
    scene_description: str
    keywords: tuple[str, ...]
    start_seconds: float
    end_seconds: float
    keyframe_path: str
    media_path: str
    rights_status: str
    license_source: str
    is_simulated: bool
    media_id: str = ""
    media_type: str = "other"
    source_path: str = ""
    semantic_vector: tuple[float, ...] = ()
    visual_vector: tuple[float, ...] = ()

    @property
    def minute_number(self) -> int:
        """Return the human-friendly one-based minute containing the start time."""
        return int(self.start_seconds // 60) + 1

    @property
    def searchable_text(self) -> str:
        # Dialogue and human-supplied keywords receive transparent field weighting.
        keyword_text = " ".join(self.keywords)
        return " ".join(
            [
                self.dialogue,
                self.dialogue,
                self.dialogue,
                self.scene_description,
                keyword_text,
                keyword_text,
                self.title,
            ]
        )

    @property
    def effective_media_id(self) -> str:
        return self.media_id or self.title.casefold()

    @property
    def effective_source_path(self) -> str:
        """Return the canonical source path while preserving old data compatibility."""
        return self.source_path or self.media_path

