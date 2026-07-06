"""Shared response schemas for kr-gov-job-mcp."""

from kr_gov_job_mcp.schemas.job import (
    JobAlioAttachment,
    JobAlioDetail,
    JobAlioSearchResult,
    JobAlioStep,
    JobAlioSummary,
)
from kr_gov_job_mcp.schemas.ncs import (
    KsaCandidate,
    KsaCategory,
    NcsAttachmentCandidate,
    NcsCodeMapping,
    NcsEvidenceReference,
    NcsEvidenceType,
    NcsMappingInput,
    NcsVerificationNote,
)

__all__ = [
    "JobAlioAttachment",
    "JobAlioDetail",
    "JobAlioSearchResult",
    "JobAlioStep",
    "JobAlioSummary",
    "KsaCandidate",
    "KsaCategory",
    "NcsAttachmentCandidate",
    "NcsCodeMapping",
    "NcsEvidenceReference",
    "NcsEvidenceType",
    "NcsMappingInput",
    "NcsVerificationNote",
]
