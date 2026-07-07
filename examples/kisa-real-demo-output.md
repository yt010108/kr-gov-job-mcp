# KISA 실제 MVP 데모 출력

실행일: 2026-07-07 KST

이 문서는 실제 Job-ALIO 조회 결과를 기준으로 현재 MVP 흐름이 어디까지 동작하는지 기록한다. 기준 공고는 한국인터넷진흥원 `302324` 공고다.

## 사용한 입력

```json
{
  "institution_name": "한국인터넷진흥원",
  "target_role": "정보보호",
  "known_skills": ["웹 보안", "네트워크", "정보보안기사"]
}
```

## 1. 공고 검색

실행 명령:

```bash
python -m kr_gov_job_mcp.server --call-tool search_public_jobs --input '{"keyword":"한국인터넷진흥원","limit":5,"ongoing_only":false}'
```

검색 결과 일부:

| 필드 | 값 |
| --- | --- |
| `source_job_id` | `302324` |
| `institution_name` | 한국인터넷진흥원 |
| `institution_code` | `C0399` |
| `title` | 2026년 한국인터넷진흥원 기간제 근로자 3차 채용 공고(전문연구직, 연구지원직) |
| `start_date` | `2026-07-06` |
| `end_date` | `2026-07-20` |
| `is_ongoing` | `true` |
| `employment_types` | 비정규직 |
| `recruitment_type` | 신입+경력 |
| `headcount` | 15 |
| `work_regions` | 부산, 대구, 세종, 경기, 전남 |
| `source_url` | `https://kisa.applyin.co.kr` |

NCS 매핑 후보:

| code | display_name | needs_verification |
| --- | --- | --- |
| `R600001` | 사업관리 | `false` |
| `R600002` | 경영.회계.사무 | `false` |
| `R600005` | 법률.경찰.소방.교도.국방 | `false` |
| `R600020` | 정보통신 | `false` |

## 2. 공고 상세 조회

실행 명령:

```bash
python -m kr_gov_job_mcp.server --call-tool fetch_job_detail --input '{"job_id":"302324"}'
```

상세 조회에서 확인된 핵심 필드:

| 필드 | 관찰 내용 |
| --- | --- |
| `qualification` | 공통 자격과 법제, 기술(R&D), 정책(R&D) 분야별 자격요건이 포함됨 |
| `preferred_conditions` | 취업지원대상자, 장애인, 저소득층, 관련 자격 등 |
| `preference` | CISSP, CISA, CCNP, ISMS-P, 정보보안기사 등 일부 자격 서류전형 가점 |
| `screening_procedure` | 서류전형 5배수, 최종면접전형 1배수 |
| `replacement_recruitment` | `true` |
| `attachments` | 공고문, 직무기술서, 붙임문서, 입사지원서 zip |
| `steps` | 법제, 기술, 정책, 경영 등 모집 분야별 전형 단계 metadata |

직무기술서 후보:

```json
{
  "name": "[직무기술서] 3차 기간제근로자 채용.pdf",
  "file_type": "C",
  "duty_description_candidate": true,
  "url": "https://opendata.alio.go.kr/recruit/downloadAtchFile?recrutAtchFileNo=3059662"
}
```

## 3. 준비 리포트 생성

실행 명령:

```bash
python -m kr_gov_job_mcp.server --call-tool analyze_job_fit_report --input '{"job_id":"302324","target_role":"정보보호","known_skills":["웹 보안","네트워크","정보보안기사"]}'
```

출력 요약:

| 필드 | 값 |
| --- | --- |
| `source` | `job_alio` |
| `job_id` | `302324` |
| `institution_name` | 한국인터넷진흥원 |
| `job_title` | 2026년 한국인터넷진흥원 기간제 근로자 3차 채용 공고(전문연구직, 연구지원직) |
| `applicant_target_role` | 정보보호 |

준비 항목:

| priority | title | rationale |
| --- | --- | --- |
| `P0` | 직무기술서에서 요구역량 확정 | K/S/A와 직무수행능력은 직무기술서 원문 근거가 있어야 합니다. |
| `P0` | NCS 분류와 공고 요구사항 연결 | 공고의 NCS 코드와 표시명은 준비 범위를 좁히는 1차 기준입니다. |
| `P1` | 지원자격과 우대사항 대응 사례 준비 | 공고 본문 필드는 지원 준비 판단의 직접 기준입니다. |
| `P2` | 기관 원문 공고 최종 대조 | Job-ALIO 요약과 기관 원문 공고가 다를 수 있습니다. |

지식 보완 후보:

| priority | title | 확인 방식 |
| --- | --- | --- |
| `P1` | 사업관리 관련 직무 지식 점검 | 직무기술서의 필요지식/필요기술과 겹치는 부분 우선 확인 |
| `P1` | 경영.회계.사무 관련 직무 지식 점검 | 공고 내 세부 분야와 실제 지원 직무를 대조 |
| `P1` | 법률.경찰.소방.교도.국방 관련 직무 지식 점검 | 법제 분야 지원 여부 확인 |
| `P1` | 정보통신 관련 직무 지식 점검 | 정보보호 목표 역할과 NCS 정보통신 범위 대조 |

근거 링크:

| source_type | title | url |
| --- | --- | --- |
| `job_posting` | 잡알리오 공고 상세 | `https://kisa.applyin.co.kr` |
| `duty_description` | [직무기술서] 3차 기간제근로자 채용.pdf | `https://opendata.alio.go.kr/recruit/downloadAtchFile?recrutAtchFileNo=3059662` |
| `ncs` | 잡알리오 NCS 분류 | `https://kisa.applyin.co.kr` |
| `job_posting` | 지원자격 | `https://kisa.applyin.co.kr` |
| `job_posting` | 우대조건 | `https://kisa.applyin.co.kr` |
| `job_posting` | 가점/우대사항 | `https://kisa.applyin.co.kr` |
| `job_posting` | 전형절차 | `https://kisa.applyin.co.kr` |

## 4. 미구현 또는 확인 필요

현재 MVP에서 명확히 미구현인 항목:

| 항목 | 현재 상태 | 다음 확인 |
| --- | --- | --- |
| NCS/KSA 세부 역량 추출 | 직무기술서 파일 후보만 찾음 | 직무기술서 PDF/HWP 텍스트 추출 후 `map_ncs_competencies` 구현 |
| 기관 사업 방향 분석 | 자동 연결 없음 | ALIO 주요사업, 기관 홈페이지 evidence 연결 |
| 기관 개선 과제 분석 | 자동 연결 없음 | ALIO 국회 지적사항, 경영평가, 감사 자료 연결 |
| 기관 signal 기반 리포트 | `verification_notes`에 남김 | 기관 분석 입력 구현 후 리포트에 evidence 연결 |

실제 `verification_notes`:

```json
[
  {
    "field": "institution_signals",
    "reason": "기관 사업 방향 또는 개선 과제 signal이 없습니다.",
    "suggested_check": "기관 분석 입력에서 ALIO, Cleaneye, 기관 홈페이지 evidence를 먼저 연결합니다."
  }
]
```

## 5. 다음 보강 데이터 소스

- ALIO 주요사업과 기관 일반현황
- ALIO 국회 지적사항, 경영평가, 감사 관련 자료
- 한국인터넷진흥원 기관 홈페이지 사업 소개
- 직무기술서 본문 텍스트 추출 결과
