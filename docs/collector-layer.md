# Collector Layer and Raw Sample Storage

## Purpose

Collectors gather source data before the project commits to a final ERD or analysis schema.
They should preserve raw source fields, save reproducible samples, and keep normalized collector
outputs separate from later analysis results.

For the team workflow, source-specific observation checklist, and PR checklist, see
`docs/collector-workflow.md`.

## Package Structure

```txt
src/kr_gov_job_mcp/
  clients/
    job_alio_web_client.py
  collectors/
    __init__.py
    base.py
    raw_store.py
  schemas/
    job.py
```

- `clients/`: source-specific HTTP adapters and response parsing.
- `collectors/`: orchestration contracts, run metadata, and raw sample storage.
- `schemas/`: normalized source response models only. Analysis schemas should wait until raw
  field inventories are stable.

## Collector Contract

Each collector should expose:

- `name`: stable source name such as `job_alio`, `alio_disclosure`, `cleaneye`,
  or `institution_page`.
- `http_policy`: timeout, retry, user-agent, and rate-limit defaults.
- `collect_raw(query, sample_store)`: collects raw source data, writes `RawSample` files through
  a `RawSampleWriter`, and returns a `CollectionResult`.

The collector result records run-level metadata. It should not contain final analysis output.

## HTTP Baseline

- Timeout: 10 seconds per request.
- Retry: 2 retries for transient request failures.
- Backoff: 0.5 seconds as a baseline before retrying.
- Rate limit: 1 request per second per source unless a source-specific rule is stricter.
- User-Agent: `kr-gov-job-mcp/0.1 (raw-data-observation)`.

Collectors may use stricter settings when a source is fragile or rate-limited.

## Raw Sample Layout

Raw samples are written under `data/raw_samples`, which is already excluded by `.gitignore`.

```txt
data/raw_samples/
  <source>/
    <raw_type>/
      <YYYY-MM-DD>/
        <sample_id>.json
```

Example:

```txt
data/raw_samples/job_alio/detail/2026-07-07/302423.json
```

Use `RawSampleStore` to write files so paths stay stable and safe.

## Raw Sample JSON

Each raw sample stores:

- `source`: source name.
- `raw_type`: `list`, `detail`, `attachment`, `html`, `pdf_text`, `api_response`,
  `metadata`, or `other`.
- `sample_id`: source identifier or a deterministic local identifier.
- `payload`: original source payload, with no analysis fields added.
- `request`: sanitized request metadata.
- `collected_at`: UTC timestamp.
- `content_type`: response content type when known.
- `metadata`: source-specific observation notes, such as pagination or parser version.

Do not store secrets, access tokens, personal notes, or applicant-private data in raw samples.

## Separation Rules

- Raw samples keep original source fields and source-specific names.
- Normalized source schemas may expose stable collector fields, but should retain the raw payload
  when it helps field inventory work.
- Analysis results should not be written into `data/raw_samples`.
- Field inventory documents should be derived from raw samples, not from guessed final schemas.
