# analyze_institution_strategy

## 구현 상태

MVP MCP tool 구현됨. 입력 evidence와 signal 후보가 없으면 `lookup_job_alio_codes`와 같은
기관명 resolver로 기관 코드를 먼저 확인한 뒤 ALIO 항목별 공시를 실시간 조회해 사업 방향과
연구보고서 signal을 만든다. 기관 홈페이지와 Cleaneye 자동 수집은 아직 별도 단계다.
상위 주무부처 정책브리핑과 보도자료 자동 수집도 현재 구현 범위에 포함되지 않는다.

이 도구는 ALIO 근거를 바탕으로 기업 분석용 signal을 만든다. `40 주요사업`은 규모와 성장성을
계산하고, `50-1/50-2 연구보고서`는 직무 관심과 마지막 할 말 소재로 재사용할 수 있게 반환한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `institution_name` | 분석 대상 기관명. 필수 |
| `year` | 분석 기준 연도 |
| `job_family` | 직무군. 보안 직무는 `정보보안`/`정보보호`가 아니라 Job-ALIO NCS 대분류명 `정보통신`으로 입력한다. |
| `alio_id` | ALIO/Job-ALIO 기관 코드. 기관명 resolver 결과를 우회하고 직접 지정할 때 사용 |
| `apba_id` | `alio_id` 별칭 |
| `fetch_live_alio` | evidence/signals가 없을 때 ALIO를 실시간 조회할지 여부. 기본값 `true` |
| `evidence` | ALIO, Cleaneye, 기관 홈페이지, 수동 입력에서 온 기관 근거 후보 목록 |
| `signals` | 사전에 추출된 기관 signal 후보 목록 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 분석 출처. 현재 값은 `institution_analysis` |
| `query` | 호출 입력 요약 |
| `institution_name` | 기관명 |
| `normalized_name` | 공백과 괄호만 정리한 기관명 |
| `year` | 분석 기준 연도 |
| `job_family` | 직무군 |
| `strategy_signals` | evidence 기반 기관 사업 방향 및 연구보고서 signal 목록 |
| `strategy_signals[].category` | signal 분류. 예: `business_direction`, `job_connection` |
| `strategy_signals[].summary` | 사업 방향 요약 |
| `strategy_signals[].job_connection` | 직무 연결 포인트 |
| `strategy_signals[].evidence` | 원문 근거 목록 |
| `verification_notes` | 근거 부족 또는 확인 필요 사항 |
| `warnings` | 호출 경고 목록 |

## CLI 점검 예시

도구 등록 확인:

```bash
python -m kr_gov_job_mcp.server --list-tools
```

기관명만 넣어 ALIO를 실시간 조회하는 경우:

```bash
python -m kr_gov_job_mcp.server --call-tool analyze_institution_strategy --input '{"institution_name":"(재)한국보건의료정보원","year":2026,"job_family":"보건의료정보"}'
```

이 호출은 기관명 resolver로 `alio_id`를 찾고, `40 주요사업`, `50-1 자체 연구 보고서`,
`50-2 외부용역 연구 보고서`를 조회해 `strategy_signals`를 반환해야 한다.

ALIO 조회를 끄고 evidence 부족 안내만 확인하는 경우:

```bash
python -m kr_gov_job_mcp.server --call-tool analyze_institution_strategy --input '{"institution_name":"한국인터넷진흥원","year":2026,"job_family":"정보통신","fetch_live_alio":false}'
```

이 호출은 `strategy_signals`를 비워 두고 `verification_notes`에 확인 필요 항목을 반환해야 한다.

evidence가 있는 경우:

```bash
python -m kr_gov_job_mcp.server --call-tool analyze_institution_strategy --input '{"institution_name":"한국인터넷진흥원","year":2026,"job_family":"정보통신","evidence":[{"title":"ALIO 주요사업","source_type":"alio_disclosure","url":"https://example.test/alio","excerpt":"디지털 신뢰 기반 조성과 정보보호 산업 지원을 주요사업으로 제시했다.","fields":{"source_type":"major_business"}}]}'
```

이 호출은 `strategy_signals[].category`, `summary`, `job_connection`, `evidence`를 반환해야 한다.
`fields.source_type`은 `major_business`, `policy_research`, `homepage_business`처럼 후속 LLM이
면접 질문 유형을 나눌 때 참고할 수 있는 source 구분값으로 보존한다.

## 데이터 소스

- ALIO 주요사업
- ALIO 자체 연구 보고서
- ALIO 외부용역 연구 보고서
- 기관 홈페이지
- 연구/정책 자료
- 필요 시 Cleaneye 사업보고서 또는 신규투자사업
- 입력으로 전달된 `evidence`와 `signals`가 있으면 이를 우선 사용하고, 없으면 기관명 resolver와 ALIO를 실시간 조회한다.

상위 주무부처 정책 자료를 연결하는 후속 계약은
[상위 주무부처 정책 source 확장 설계](parent-ministry-policy-source.md)에 정리한다. 이 설계는
정책 자료를 기관 공식 입장과 분리하고, 새 외부 source나 schema 변경 전에 별도 승인을 받는 것을
전제로 한다.

## 처리 원칙

- evidence가 없는 사업 방향은 최종 주장으로 쓰지 않는다.
- ALIO와 Cleaneye 기관 ID를 기관명만으로 강제 병합하지 않는다.
- 기관 홈페이지는 구조가 기관마다 다르므로 출처 URL과 excerpt를 함께 보존한다.
- ALIO 주요사업은 최신 예산 규모와 직전 결산 대비 성장성을 함께 반환한다.
- `year`를 지정한 live ALIO 조회는 같은 공시 연도의 자료만 사용한다. 일치 자료가 없으면 다른 연도 자료로 대체하지 않고 `warnings`로 반환한다.
- 자동 수집 evidence에는 근거 연도 `evidence_year`, timezone이 확인된 공시 시점 `disclosed_at`, 실제 수집 시각 `retrieved_at`을 보존한다. 정기공시는 `critYyyy`를 근거 연도로 사용한다. 날짜만 제공된 공시는 임의 timezone을 붙이지 않고 원문을 `fields.disclosed_date`와 기존 `collected_at`에 유지하며 `disclosed_at`은 비워 둔다.
- `job_connection`은 최종 답변 문장이 아니라, 직무/경험과 연결할 때 사용할 검토 축이다.
