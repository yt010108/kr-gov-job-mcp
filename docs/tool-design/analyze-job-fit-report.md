# analyze_job_fit_report

## 구현 상태

MVP MCP tool 구현됨. Job-ALIO 공고 상세를 조회해 준비 항목 리포트를 만들고, 추출된
직무기술서 텍스트가 입력되면 NCS/K/S/A 후보를 리포트에 연결한다. PDF/HWP 자동 다운로드와
텍스트 추출, 기관 signal 자동 연결은 아직 planned 단계다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `job_id` | Job-ALIO 공고 ID |
| `source_job_id` | `search_public_jobs`가 반환한 Job-ALIO 원본 공고 ID alias |
| `recruitment_notice_sn` | Job-ALIO 채용공고 일련번호 alias |
| `target_role` | 지원자가 목표로 하는 직무 또는 준비 초점 |
| `known_skills` | 지원자가 이미 보유한 기술, 자격, 경험 목록 |
| `preparation_notes` | 지원자 준비 상태에 대한 추가 메모 |
| `duty_description_text` | 직무기술서 PDF/HWP/HWPX 등에서 별도로 추출한 원문 텍스트 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 데이터 출처. 현재 값은 `job_alio` |
| `query` | 호출 입력 요약 |
| `job_id` | Job-ALIO 공고 ID |
| `institution_name` | 기관명 |
| `job_title` | 공고명 |
| `applicant_target_role` | 지원자가 입력한 목표 직무 |
| `preparation_items` | 지원자가 우선 준비해야 할 항목 목록 |
| `preparation_items[].priority` | 준비 우선순위. 예: `P0`, `P1`, `P2` |
| `preparation_items[].title` | 준비 항목 제목 |
| `preparation_items[].rationale` | 준비 항목이 필요한 이유 |
| `preparation_items[].recommended_actions` | 권장 행동 목록 |
| `preparation_items[].evidence` | 준비 항목 근거 목록 |
| `preparation_items[].verification_notes` | 항목별 확인 필요 사항 |
| `knowledge_gaps` | 보완해야 할 직무 지식 후보 목록 |
| `ncs_mapping` | 공고 상세와 직무기술서 텍스트에서 준비한 NCS/K/S/A 매핑 입력 |
| `ncs_mapping.ksa_candidates` | 필요지식, 필요기술, 직무수행태도 등 K/S/A 후보 |
| `ncs_mapping.verification_notes` | NCS/K/S/A 매핑 확인 필요 사항 |
| `institution_materials_to_check` | 추가 확인이 필요한 기관 자료 목록 |
| `evidence_links` | 리포트 전체 근거 링크 목록 |
| `verification_notes` | 근거 부족 또는 확인 필요 사항 |
| `warnings` | 호출 경고 목록 |

## 데이터 소스

- `fetch_job_detail` 출력
- `duty_description_text`로 전달된 직무기술서 추출 텍스트
- NCS/K/S/A mapping helper 출력
- `collect_institution_context` 또는 기관 분석 입력
- 지원자 준비 상태 입력

## 처리 원칙

- 공고, NCS, 기관 signal은 evidence가 연결된 항목만 강한 주장으로 사용한다.
- `duty_description_text`가 있으면 `필요지식:`, `필요기술:`, `직무수행태도:` 같은 명시적
  라벨에서 K/S/A 후보를 추출한다.
- `duty_description_text`가 없으면 K/S/A 후보를 단정하지 않고 verification note로 남긴다.
- 부족한 자료는 `verification_notes` 또는 `institution_materials_to_check`로 남긴다.
- 리포트는 지원자가 다음에 확인하거나 준비해야 할 항목을 우선순위로 정리한다.
