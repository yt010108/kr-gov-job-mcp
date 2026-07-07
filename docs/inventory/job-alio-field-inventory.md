# Job-ALIO Field Inventory

## Observation Scope

This inventory records the first raw Job-ALIO recruitment fields to use before
the project finalizes an ERD or analysis schema.

- Source: Job-ALIO recruitment Ajax endpoints.
- List sample: 50 ongoing notices.
- Detail sample: first 10 notices from the list sample.
- Observation date: 2026-07-07 KST.
- Raw storage target: `data/raw_samples/job_alio/<list|detail>/<YYYY-MM-DD>/`.

Raw sample files are intentionally git-ignored. Commit derived field inventory
documents, not raw source dumps.

## Collector Flow

1. Search ongoing notices with `JobAlioWebClient.search_jobs`.
2. Save one `RawSample` with `raw_type="list"` containing page metadata and raw list rows.
3. Fetch selected details with `JobAlioWebClient.fetch_job_detail`.
4. Save one `RawSample` per selected notice with `raw_type="detail"`.
5. Derive field inventories from saved raw samples.

## Field Inventory

| Raw field | Normalized field | List presence | Detail presence | Notes |
| --- | --- | --- | --- | --- |
| `recrutPblntSn` | `id` | 50/50 | 10/10 | Stable notice identifier. Use as detail sample id. |
| `instNm` | `institution_name` | 50/50 | 10/10 | Institution display name. |
| `pblntInstCd` | `institution_code` | 50/50 | 10/10 | Job-ALIO posting institution code. |
| `pbadmsStdInstCd` | raw only | 50/50 | 10/10 | Public administration standard institution code candidate. |
| `recrutPbancTtl` | `title` | 50/50 | 10/10 | Recruitment notice title. |
| `pbancBgngYmd` | `start_date` | 50/50 | 10/10 | `YYYYMMDD`; normalize to ISO date. |
| `pbancEndYmd` | `end_date` | 50/50 | 10/10 | `YYYYMMDD`; normalize to ISO date. |
| `ongoingYn` | `is_ongoing` | 50/50 | 0/10 | Present in list rows, absent in sampled detail rows. |
| `ncsCdLst` | `ncs_codes` | 50/50 | 10/10 | Comma-separated NCS code list. |
| `ncsCdNmLst` | `ncs_categories` | 50/50 | 10/10 | Comma-separated NCS display names. |
| `hireTypeLst` | raw only | 50/50 | 10/10 | Employment type code list. |
| `hireTypeNmLst` | `employment_types` | 50/50 | 10/10 | Comma-separated employment type names. |
| `recrutSe` | raw only | 50/50 | 10/10 | Recruitment type code. |
| `recrutSeNm` | `recruitment_type` | 50/50 | 10/10 | Recruitment type display name. |
| `recrutNope` | `headcount` | 50/50 | 10/10 | Numeric text. |
| `workRgnLst` | raw only | 50/50 | 10/10 | Work region code list. |
| `workRgnNmLst` | `work_regions` | 50/50 | 10/10 | Comma-separated region names. |
| `srcUrl` | `source_url` | 50/50 | 10/10 | Institution source page. |
| `aplyQlfcCn` | `qualification` | 50/50 | 10/10 | Long free text; preserve raw line breaks. |
| `prefCondCn` | `preferred_conditions` | 49/50 | 10/10 | One sampled list row had an empty value. |
| `prefCn` | `preference` | 50/50 | 10/10 | Preferential treatment text. |
| `disqlfcRsn` | `disqualification_reason` | 50/50 | 10/10 | Long free text. |
| `scrnprcdrMthdExpln` | `screening_procedure` | 50/50 | 10/10 | Long free text. |
| `replmprYn` | `replacement_recruitment` | 50/50 | 10/10 | `Y`/`N`. |
| `acbgCondLst` | raw only | 50/50 | 10/10 | Academic condition code list. |
| `acbgCondNmLst` | raw only | 50/50 | 10/10 | Academic condition display names. |
| `decimalDay` | raw only | 50/50 | 10/10 | Remaining-day style display value. |
| `nonatchRsn` | raw only | 7/50 | 2/10 | Present when there are attachment notes or missing-attachment reasons. |
| `files` | `attachments` | 0/50 | 10/10 | Detail-only attachment metadata. Sampled details had 3 to 5 files. |
| `steps` | `steps` | 0/50 | 10/10 | Detail-only process step metadata. Sampled details had 2 to 48 steps. |

## Missingness Notes

- List rows are good enough for search result cards and first-pass field inventory.
- Detail rows are required for attachment metadata and recruitment step data.
- `ongoingYn` appeared list-only in the sampled responses.
- `files` and `steps` appeared detail-only in the sampled responses.
- Source-specific code fields should remain in raw payloads until the ERD decides whether to
  store both codes and display names.

## Raw Sample Criteria

For the next inventory pass, collect:

- 50 to 100 list rows from ongoing notices.
- At least 10 detail rows from the list sample.
- Details that include varied `ncsCdLst`, `hireTypeNmLst`, `workRgnNmLst`, `files`, and `steps`.
- The original raw row under `RawSample.payload`; do not replace source fields with analysis fields.
