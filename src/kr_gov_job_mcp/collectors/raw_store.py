"""Filesystem storage for raw collector samples."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from kr_gov_job_mcp.collectors.base import RawSample


class RawSampleStore:
    """Write raw samples to a stable, git-ignored directory layout."""

    _MAX_SEGMENT_LENGTH = 80

    def __init__(self, root: str | Path = "data/raw_samples") -> None:
        self.root = Path(root)

    def path_for(self, sample: RawSample) -> Path:
        collected_date = sample.collected_at.split("T", maxsplit=1)[0] or "unknown-date"
        return (
            self.root
            / self._safe_segment(sample.source)
            / self._safe_segment(sample.raw_type)
            / self._safe_segment(collected_date)
            / f"{self._safe_segment(sample.sample_id)}.json"
        )

    def write_sample(self, sample: RawSample) -> Path:
        path = self.path_for(sample)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sample.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return path

    def read_sample(self, path: str | Path) -> RawSample:
        return RawSample.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    @staticmethod
    def _safe_segment(value: str) -> str:
        original = value.strip()
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", original)
        cleaned = cleaned.strip(".-_")
        cleaned = cleaned or "unknown"

        needs_digest = cleaned != original or len(cleaned) > RawSampleStore._MAX_SEGMENT_LENGTH
        if not needs_digest:
            return cleaned

        digest = hashlib.sha1(original.encode("utf-8")).hexdigest()[:10]
        max_stem_length = RawSampleStore._MAX_SEGMENT_LENGTH - len(digest) - 1
        if len(cleaned) > max_stem_length:
            head_length = max_stem_length // 2
            tail_length = max_stem_length - head_length - 1
            head = cleaned[:head_length].rstrip(".-_")
            tail = cleaned[-tail_length:].lstrip(".-_")
            stem = f"{head}-{tail}".strip(".-_")
        else:
            stem = cleaned
        stem = stem or "unknown"
        return f"{stem}-{digest}"
