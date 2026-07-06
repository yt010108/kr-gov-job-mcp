"""Shared collector interfaces and raw sample storage helpers."""

from kr_gov_job_mcp.collectors.alio_disclosure import AlioDisclosureCollector
from kr_gov_job_mcp.collectors.base import (
    CollectionResult,
    Collector,
    CollectorHttpPolicy,
    CollectorRequest,
    RawSample,
    RawSampleWriter,
    RawSampleType,
)
from kr_gov_job_mcp.collectors.raw_store import RawSampleStore

__all__ = [
    "AlioDisclosureCollector",
    "CollectionResult",
    "Collector",
    "CollectorHttpPolicy",
    "CollectorRequest",
    "RawSample",
    "RawSampleStore",
    "RawSampleWriter",
    "RawSampleType",
]
