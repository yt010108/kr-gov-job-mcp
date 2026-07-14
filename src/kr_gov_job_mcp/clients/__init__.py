"""External service clients."""

from kr_gov_job_mcp.clients.attachment_text_client import (
    AttachmentTextClient,
    AttachmentTextResult,
)

from kr_gov_job_mcp.clients.alio_disclosure_client import (
    AlioDisclosureClient,
    AlioDisclosureClientError,
)
from kr_gov_job_mcp.clients.cleaneye_client import CleaneyeClient, CleaneyeClientError
from kr_gov_job_mcp.clients.job_alio_web_client import JobAlioWebClient, JobAlioWebClientError

__all__ = [
    "AttachmentTextClient",
    "AttachmentTextResult",
    "AlioDisclosureClient",
    "AlioDisclosureClientError",
    "CleaneyeClient",
    "CleaneyeClientError",
    "JobAlioWebClient",
    "JobAlioWebClientError",
]
