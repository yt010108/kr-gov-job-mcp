"""Filesystem storage for raw collector samples."""

from __future__ import annotations

import json
import re
from pathlib import Path

from kr_gov_job_mcp.collectors.base import RawSample


class RawSampleStore:
    """Write raw samples to a stable, git-ignored directory layout."""

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
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
        cleaned = cleaned.strip(".-_")
        return cleaned or "unknown"
