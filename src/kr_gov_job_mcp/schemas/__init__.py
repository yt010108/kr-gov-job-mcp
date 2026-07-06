"""Shared response schemas for kr-gov-job-mcp."""

from kr_gov_job_mcp.schemas.job import (
    JobAlioAttachment,
    JobAlioDetail,
    JobAlioSearchResult,
    JobAlioStep,
    JobAlioSummary,
)
from kr_gov_job_mcp.schemas.job_fit import (
    ApplicantReadinessInput,
    InstitutionMaterialCheck,
    JobFitEvidenceSource,
    JobFitEvidenceType,
    JobFitInstitutionSignal,
    JobFitPreparationItem,
    JobFitPreparationReport,
    JobFitVerificationNote,
    PreparationPriority,
)

__all__ = [
    "ApplicantReadinessInput",
    "InstitutionMaterialCheck",
    "JobAlioAttachment",
    "JobAlioDetail",
    "JobAlioSearchResult",
    "JobAlioStep",
    "JobAlioSummary",
    "JobFitEvidenceSource",
    "JobFitEvidenceType",
    "JobFitInstitutionSignal",
    "JobFitPreparationItem",
    "JobFitPreparationReport",
    "JobFitVerificationNote",
    "PreparationPriority",
]
