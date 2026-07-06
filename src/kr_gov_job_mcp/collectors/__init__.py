"""Shared collector interfaces and raw sample storage helpers."""

from kr_gov_job_mcp.collectors.base import (
    CollectionResult,
    Collector,
    CollectorHttpPolicy,
    CollectorRequest,
    RawSample,
    RawSampleWriter,
    RawSampleType,
)
from kr_gov_job_mcp.collectors.job_alio import JobAlioCollector
from kr_gov_job_mcp.collectors.raw_store import RawSampleStore

__all__ = [
    "CollectionResult",
    "Collector",
    "CollectorHttpPolicy",
    "CollectorRequest",
    "JobAlioCollector",
    "RawSample",
    "RawSampleStore",
    "RawSampleWriter",
    "RawSampleType",
]
