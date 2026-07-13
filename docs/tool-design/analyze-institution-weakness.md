# analyze_institution_weakness

## 구현 상태

MVP MCP tool 구현됨. 입력 evidence와 signal 후보가 없으면 `lookup_job_alio_codes`와 같은
기관명 resolver로 기관 코드를 먼저 확인한 뒤 ALIO 항목별 공시를 실시간 조회해 개선 과제 signal을
만든다. Cleaneye 자동 수집은 아직 별도 단계다.

이 도구는 `47-1 국회지적사항`을 근거로 “기관의 부족한 점” 질문에 연결할 수 있는 개선 과제를
구조화한다. 감사원/주무부처 지적사항은 현재 수집 범위에서 제외한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `institution_name` | 분석 대상 기관명. 필수 |
| `year` | 분석 기준 연도 |
| `alio_id` | ALIO/Job-ALIO 기관 코드. 기관명 resolver 결과를 우회하고 직접 지정할 때 사용 |
| `apba_id` | `alio_id` 별칭 |
| `fetch_live_alio` | evidence/signals가 없을 때 ALIO를 실시간 조회할지 여부. 기본값 `true` |
| `evidence` | ALIO, Cleaneye, 수동 입력에서 온 개선 과제 근거 후보 목록 |
| `signals` | 사전에 추출된 개선 과제 signal 후보 목록 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 분석 출처. 현재 값은 `institution_analysis` |
| `query` | 호출 입력 요약 |
| `institution_name` | 기관명 |
| `normalized_name` | 공백과 괄호만 정리한 기관명 |
| `year` | 분석 기준 연도 |
| `weakness_signals` | evidence 기반 개선 과제 signal 목록 |
| `weakness_signals[].category` | signal 분류. 예: `improvement_task`, `financial_or_operational`, `management_evaluation` |
| `weakness_signals[].summary` | 개선 과제 요약 |
| `weakness_signals[].careful_wording` | 단정적 비판을 피하기 위한 표현 기준 |
| `weakness_signals[].applicant_connection` | 지원자가 기여할 수 있는 포인트 |
| `weakness_signals[].evidence` | 원문 근거 목록 |
| `verification_notes` | 근거 부족 또는 확인 필요 사항 |
| `warnings` | 호출 경고 목록 |

## CLI 점검 예시

도구 등록 확인:

```bash
python -m kr_gov_job_mcp.server --list-tools
```

기관명만 넣어 ALIO를 실시간 조회하는 경우:

```bash
python -m kr_gov_job_mcp.server --call-tool analyze_institution_weakness --input '{"institution_name":"(재)한국보건의료정보원","year":2026}'
```

이 호출은 기관명 resolver로 `alio_id`를 찾고, `47-1 국회지적사항`을 조회해
`weakness_signals`를 반환해야 한다.

ALIO 조회를 끄고 evidence 부족 안내만 확인하는 경우:

```bash
python -m kr_gov_job_mcp.server --call-tool analyze_institution_weakness --input '{"institution_name":"한국인터넷진흥원","year":2026,"fetch_live_alio":false}'
```

이 호출은 `weakness_signals`를 비워 두고 `verification_notes`에 확인 필요 항목을 반환해야 한다.

evidence가 있는 경우:

```bash
python -m kr_gov_job_mcp.server --call-tool analyze_institution_weakness --input '{"institution_name":"한국인터넷진흥원","year":2026,"evidence":[{"title":"국회 지적사항","source_type":"alio_disclosure","url":"https://example.test/audit","excerpt":"정보보호 서비스 운영 체계의 개선 필요성이 지적되었다.","fields":{"source_type":"audit_point"}}]}'
```

이 호출은 `weakness_signals[].category`, `summary`, `careful_wording`, `applicant_connection`,
`evidence`를 반환해야 한다. `fields.source_type`은 `audit_point`, `management_evaluation`,
`financial`, `operational`처럼 후속 LLM이 면접 질문 유형을 나눌 때 참고할 수 있는 source 구분값으로
보존한다.

## 데이터 소스

- ALIO 국회 지적사항
- ALIO 감사/평가 후보 항목
- Cleaneye 경영평가, 부채, 외부기관 감사결과
- 입력으로 전달된 `evidence`와 `signals`가 있으면 이를 우선 사용하고, 없으면 기관명 resolver와 ALIO `47-1`을 실시간 조회한다.

## 처리 원칙

- 국회 지적사항, 감사결과, 경영평가성 자료는 원문 근거 링크와 함께만 사용한다.
- `year`를 지정한 live ALIO 조회는 같은 공시 연도의 자료만 사용한다. 일치 자료가 없으면 다른 연도 자료로 대체하지 않고 `warnings`로 반환한다.
- 자동 수집 evidence에는 근거 연도 `evidence_year`, timezone이 확인된 공시 시점 `disclosed_at`, 실제 수집 시각 `retrieved_at`을 보존한다. 정기공시는 `critYyyy`를 근거 연도로 사용한다. 날짜만 제공된 공시는 임의 timezone을 붙이지 않고 원문을 `fields.disclosed_date`와 기존 `collected_at`에 유지하며 `disclosed_at`은 비워 둔다.
- 개선 과제는 지원자가 자기소개서나 면접에서 활용 가능한 표현으로 바꾸되, 원문 의미를 과장하지 않는다.
- 현재 ALIO `47-2`, `47-3`은 수집 범위에서 제외되어 있으므로 근거로 쓰지 않는다.
- `applicant_connection`은 지원자 맞춤 답변이 아니라, 후속 면접 준비 단계가 재가공할 때 지켜야 할 연결 기준이다.
