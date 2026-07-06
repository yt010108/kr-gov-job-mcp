"""Shared response schemas for kr-gov-job-mcp."""

from kr_gov_job_mcp.schemas.job import (
    JobAlioAttachment,
    JobAlioDetail,
    JobAlioSearchResult,
    JobAlioStep,
    JobAlioSummary,
)
from kr_gov_job_mcp.schemas.press_release import (
    PressReleaseDetail,
    PressReleaseEvidenceSource,
    PressReleaseLink,
    PressReleaseListItem,
)

__all__ = [
    "JobAlioAttachment",
    "JobAlioDetail",
    "JobAlioSearchResult",
    "JobAlioStep",
    "JobAlioSummary",
    "PressReleaseDetail",
    "PressReleaseEvidenceSource",
    "PressReleaseLink",
    "PressReleaseListItem",
]
