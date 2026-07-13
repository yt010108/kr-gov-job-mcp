"""Filesystem storage for raw collector samples."""

from __future__ import annotations

import json
import os
import re
import tempfile
from hashlib import sha256
from pathlib import Path

from kr_gov_job_mcp.collectors.base import RawSample


class RawSampleStore:
    """Write raw samples to a stable, git-ignored directory layout."""

    _MAX_SAMPLE_SLUG_LENGTH = 48
    _MAX_TIME_TOKEN_LENGTH = 48
    _MAX_SEGMENT_LENGTH = 80
    _WINDOWS_RESERVED_SEGMENTS = frozenset(
        {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{number}" for number in range(1, 10)),
            *(f"LPT{number}" for number in range(1, 10)),
        }
    )

    def __init__(self, root: str | Path = "data/raw_samples") -> None:
        self.root = Path(root)

    def path_for(self, sample: RawSample) -> Path:
        collected_date = sample.collected_at.split("T", maxsplit=1)[0] or "unknown-date"
        return (
            self.root
            / self._safe_segment(sample.source)
            / self._safe_segment(sample.raw_type)
            / self._safe_segment(collected_date)
            / self._filename_for(sample)
        )

    def write_sample(self, sample: RawSample) -> Path:
        path = self.path_for(sample)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.stem}-",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(sample.model_dump_json(indent=2) + "\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())

            try:
                os.link(temp_path, path)
            except FileExistsError as error:
                raise FileExistsError(f"Raw sample already exists: {path}") from error
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

        return path

    def read_sample(self, path: str | Path) -> RawSample:
        return RawSample.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def _filename_for(cls, sample: RawSample) -> str:
        sample_slug = cls._safe_segment(sample.sample_id, cls._MAX_SAMPLE_SLUG_LENGTH)
        sample_digest = sha256(sample.sample_id.encode("utf-8")).hexdigest()
        time_token = cls._time_token(sample.collected_at)
        return f"{sample_slug}-{sample_digest}-{time_token}.json"

    @classmethod
    def _time_token(cls, collected_at: str) -> str:
        safe_time = cls._safe_segment(collected_at, cls._MAX_TIME_TOKEN_LENGTH)
        time_digest = sha256(collected_at.encode("utf-8")).hexdigest()
        return f"{safe_time}-{time_digest}"

    @staticmethod
    def _safe_segment(value: str, max_length: int = _MAX_SEGMENT_LENGTH) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
        cleaned = cleaned.strip(" .-_")[:max_length].rstrip(". ")
        cleaned = cleaned or "unknown"
        if cleaned.upper() in RawSampleStore._WINDOWS_RESERVED_SEGMENTS:
            cleaned = f"_{cleaned}"
        return cleaned
