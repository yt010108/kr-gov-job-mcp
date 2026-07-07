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
from kr_gov_job_mcp.collectors.career_page import CareerPageCollector
from kr_gov_job_mcp.collectors.cleaneye import CleaneyeCollector
from kr_gov_job_mcp.collectors.job_alio import JobAlioCollector
from kr_gov_job_mcp.collectors.raw_store import RawSampleStore

__all__ = [
    "AlioDisclosureCollector",
    "CareerPageCollector",
    "CleaneyeCollector",
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
