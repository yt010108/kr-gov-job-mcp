"""Shared response schemas for kr-gov-job-mcp."""

from kr_gov_job_mcp.schemas.alio import (
    AlioInstitution,
    AlioInstitutionSearchResult,
    AlioPointAttachment,
    AlioPointItem,
    AlioPointKind,
    AlioPointSearchResult,
    AlioReportDisclosure,
    AlioReportFile,
    AlioReportSearchResult,
)
from kr_gov_job_mcp.schemas.job import (
    JobAlioAttachment,
    JobAlioDetail,
    JobAlioSearchResult,
    JobAlioStep,
    JobAlioSummary,
)

__all__ = [
    "AlioInstitution",
    "AlioInstitutionSearchResult",
    "AlioPointAttachment",
    "AlioPointItem",
    "AlioPointKind",
    "AlioPointSearchResult",
    "AlioReportDisclosure",
    "AlioReportFile",
    "AlioReportSearchResult",
    "JobAlioAttachment",
    "JobAlioDetail",
    "JobAlioSearchResult",
    "JobAlioStep",
    "JobAlioSummary",
]
