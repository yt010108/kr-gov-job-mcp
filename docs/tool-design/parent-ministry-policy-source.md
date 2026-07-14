# 상위 주무부처 정책 source 확장 설계

## 상태와 범위

이 문서는 `analyze_institution_strategy`에 상위 주무부처 정책 근거를 연결하기 위한 후속 설계다.
현재 구현은 정책브리핑이나 부처 보도자료를 자동 조회하지 않는다. 이 문서만으로 새 MCP tool,
외부 데이터 source, 입력·출력 schema를 추가하지 않는다.

권장 방향은 별도 `analyze_parent_ministry_policy` tool을 먼저 만들기보다 기존 기관 분석의
evidence 흐름을 확장하는 것이다. 기관 근거와 정책 근거를 한 결과에서 연결하되, 두 출처의
주장을 섞지 않고 provenance를 유지한다.

## 핵심 원칙

- 주무부처는 기관명만으로 단정하지 않는다.
- 부처 정책은 기관의 공식 입장이나 확정 사업으로 표현하지 않는다.
- URL만 있는 자료는 분석 근거로 사용하지 않고 제목, 원문 excerpt, 시점을 함께 보존한다.
- 기관 근거와 정책 근거가 모두 있을 때만 연결점을 확정한다.
- 한쪽 근거가 없으면 빈 연결 결과와 `verification_notes`를 반환한다.

## 설계 결정

- 신규 MCP tool보다 기존 `analyze_institution_strategy` evidence 확장을 우선한다.
- 기관-주무부처 관계를 제공하는 안정적인 공식 필드가 확인되기 전에는 자동 선택하지 않는다.
- 같은 문서가 여러 곳에 게시되면 부처 공식 원문을 우선하고 정책브리핑은 발견 경로로 기록한다.
- 사용자 제공 요약은 공식 원문 URL과 excerpt를 확인할 수 있을 때만 분석 근거로 승격한다.

## 1차 입력 계약 제안

1차 구현은 실시간 조회 없이 사용자가 제공한 정책 문서를 받는다. `ministry_name`은 명시
입력을 우선하며, 기관과의 관계가 확인되지 않았으면 검증 대상으로 남긴다.

```json
{
  "institution_name": "기관명",
  "job_family": "지원 직무군",
  "year": 2026,
  "ministry_name": "주무부처명",
  "policy_evidence": [
    {
      "title": "정책 자료 제목",
      "source_type": "government_policy",
      "url": "https://공식-원문.example",
      "evidence_year": 2026,
      "disclosed_at": "2026-03-10T00:00:00+09:00",
      "retrieved_at": "2026-07-14T00:00:00+09:00",
      "excerpt": "연결 판단에 사용하는 원문 일부",
      "fields": {
        "source_organization": "주무부처명",
        "document_type": "policy_briefing",
        "institution_relation": "user_provided"
      }
    }
  ]
}
```

`government_policy`, `ministry_name`, `policy_evidence`는 향후 승인이 필요한 schema 변경
후보다. 승인 전에는 현재 `evidence` 입력을 정책 자동 연동으로 설명하지 않는다.

## 근거 모델

정책 문서는 기존 `InstitutionEvidence`의 공통 시점 필드를 재사용한다.

| 필드 | 기준 |
| --- | --- |
| `source_type` | 향후 `government_policy` 추가 제안 |
| `url` | 정부 또는 부처 공식 원문 URL |
| `evidence_year` | 정책이 대상으로 삼는 연도 |
| `disclosed_at` | 원문 게시 시점. timezone을 확인할 수 없으면 비워 둔다. |
| `retrieved_at` | 실제 수집 시점 |
| `excerpt` | 요약과 연결 판단에 직접 사용한 원문 |
| `fields.source_organization` | 자료를 발표한 기관 |
| `fields.document_type` | `policy_briefing`, `press_release`, `work_plan` 등 |
| `fields.institution_relation` | `confirmed`, `user_provided`, `candidate` |

`institution_relation=confirmed`는 공식 관계 근거가 있을 때만 사용한다. 명시 입력은
`user_provided`, 자동 추론 후보는 `candidate`로 두고 `needs_verification`을 유지한다.

## 출력 계약 제안

정책 signal은 기존 `strategy_signals`와 구분해 정책을 기관 사실처럼 보이게 하지 않는다.

```json
{
  "ministry_candidates": [
    {
      "name": "주무부처 후보",
      "relation_evidence": [],
      "confidence": "medium",
      "needs_verification": true
    }
  ],
  "policy_signals": [
    {
      "summary": "정책 방향 요약",
      "policy_keywords": [],
      "institution_connection": "기관 주요사업 근거와 확인된 연결점",
      "job_connection": "지원 직무에서 검토할 기여 방향",
      "evidence": [],
      "needs_verification": false
    }
  ],
  "verification_notes": [],
  "warnings": []
}
```

- `ministry_candidates`: 관계 근거가 있는 후보만 반환하며 자동으로 하나를 선택하지 않는다.
- `summary`: 정책 원문만 요약한다.
- `institution_connection`: 별도 기관 evidence가 있을 때만 채운다.
- `job_connection`: 직무 관점의 검토 축이며 기관의 채용 계획으로 단정하지 않는다.
- `needs_verification`: 주무부처 관계, 시점, 원문 중 하나라도 불명확하면 `true`다.

`prepare_institution_interview`는 검증된 `policy_signals`만 기관 현안 이해 카드의 후보로 받는다.
정책 signal 단독으로 지원동기나 입사 후 포부 문장을 확정하지 않는다.

## 출처 우선순위

1. 주무부처 공식 업무계획, 보도자료, 정책 원문
2. 정책브리핑에 게시된 부처 자료와 원문 연결 정보
3. 사용자가 제공한 제목, URL, excerpt

우선순위가 낮다는 이유만으로 자료를 버리지는 않는다. 동일 문서 중복을 제거할 때 더 직접적인
원문을 대표 evidence로 선택하고, 발견 경로는 `fields.discovery_source`에 남긴다.

## 처리 흐름

1. 기관명과 기관 코드를 기존 resolver로 확인한다.
2. 명시된 주무부처명과 관계 근거를 분리해 기록한다.
3. 정책 문서를 출처, 원문, 시점이 있는 evidence로 정규화한다.
4. ALIO 주요사업 등 기관 evidence와 정책 evidence를 각각 signal로 만든다.
5. 두 근거의 키워드와 대상 사업이 직접 맞닿을 때만 `institution_connection`을 만든다.
6. 연결 근거가 부족하면 후보를 확정하지 않고 확인 방법을 반환한다.

## 실패 처리

| 상황 | 반환 원칙 |
| --- | --- |
| `ministry_name` 없음 | 주무부처 후보를 단정하지 않고 관계 확인 필요 note 반환 |
| 정책 원문 없음 | `policy_signals=[]`과 원문 확보 방법 반환 |
| URL만 있음 | 분석하지 않고 excerpt 필요 note 반환 |
| 기관 evidence 없음 | 정책 요약은 유지하되 `institution_connection=null` |
| 연도 불일치 | 다른 연도로 대체하지 않고 warning 반환 |
| 관계가 후보 수준 | `needs_verification=true` 유지 |

## 단계별 구현과 승인

### 1단계: 사용자 제공 evidence

- 기존 `analyze_institution_strategy` 확장
- `government_policy` source type과 정책 입력·출력 schema 추가
- 정상, 관계 미확인, 원문 없음, 연도 불일치 테스트 추가

새 source type과 tool schema 변경이므로 구현 전에 승인이 필요하다.

### 2단계: 공식 정책 자료 자동 수집

- 정책브리핑 또는 부처 공식 자료 검색 경로 선정
- 원문 수집기와 pagination, 중복, 시점 정책 정의
- 기관-주무부처 관계 source 선정

새 외부 데이터 source 연동이므로 별도 승인이 필요하다. 특정 기관 seed나 수동 매핑을
일반 resolver처럼 사용하지 않는다.

## 완료 판단

- 주무부처 관계의 확인 수준이 결과에 표시된다.
- 정책 방향, 기관 연결, 직무 연결이 서로 다른 필드로 반환된다.
- 모든 연결 결과가 기관 evidence와 정책 evidence를 함께 가진다.
- 근거 URL, 원문 excerpt, 근거 연도, 게시·수집 시점이 보존된다.
- 근거 부족과 0건 결과가 단정 없이 반환된다.
- 기존 기관 전략·면접 도구에 전달 가능한 schema가 정의된다.
