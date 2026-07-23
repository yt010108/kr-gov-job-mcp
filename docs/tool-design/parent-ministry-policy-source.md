# 상위 주무부처 정책 source 확장 설계

## 상태와 범위

이 문서는 `analyze_institution_strategy`에 상위 주무부처 정책 근거를 연결하기 위한 후속
계약을 정의한다. 현재 구현은 정책브리핑이나 부처 보도자료를 조회하지 않으며, 아래 이름과
schema는 모두 제안 단계다. 이 PR은 새 MCP tool, 외부 데이터 source, dependency 또는 실제
입출력 schema를 추가하지 않는다.

권장 방향은 별도 `analyze_parent_ministry_policy` tool보다 기존 기관 분석 결과에 정책 전용
경로를 추가하는 것이다. 정책을 기관 사실로 오인하지 않도록 기존 `evidence`와 `signals`에
섞어 넣지 않는다.

## 핵심 원칙

- 기관명만으로 주무부처를 추론하거나 자동 선택하지 않는다.
- 정책 원문, 기관 공식 근거, 양자의 관계 근거를 서로 다른 필드로 보존한다.
- 정책을 기관의 공식 입장, 확정 사업 또는 채용 계획으로 표현하지 않는다.
- URL이나 제목만 있는 자료는 signal로 만들지 않는다.
- 관계와 출처가 확인되지 않은 결과는 `needs_verification=true`를 유지한다.
- 유효한 자료와 잘못된 자료가 섞이면 유효한 자료는 살리고 항목별 경고를 반환한다.

## 1차 입력 계약 제안

1차 구현은 실시간 조회 없이 사용자가 제공한 정책 문서와 관계 근거만 받는다.

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
      "excerpt": "정책 방향을 요약하는 데 사용한 원문 일부",
      "fields": {
        "source_organization": "주무부처명",
        "document_type": "policy_briefing",
        "official_source_verified": true,
        "discovery_source": "사용자 제공"
      }
    }
  ],
  "relation_evidence": [
    {
      "title": "기관-주무부처 관계를 밝힌 공식 자료",
      "source_type": "government_relation",
      "url": "https://공식-관계자료.example",
      "excerpt": "기관과 주무부처 관계를 확인할 수 있는 원문 일부",
      "fields": {
        "institution_name": "기관명",
        "ministry_name": "주무부처명"
      }
    }
  ]
}
```

`ministry_name`, `policy_evidence`, `relation_evidence`와 두 source type은 모두 향후 승인이
필요한 schema 변경 후보다. `ministry_name`은 후보 생성의 명시 입력일 뿐 관계 확인 근거가
아니다. 승인 전에는 현재 `evidence` 입력이 이 계약을 지원한다고 설명하지 않는다.

## 주무부처 후보 결정

후보는 명시한 `ministry_name`과 `policy_evidence[].fields.source_organization`에서만 만든다.
기관명, 키워드 또는 특정 기관 seed로 부처명을 추론하지 않는다. 이름을 정규화해 중복을
제거하되 원문 표기는 보존한다.

```json
{
  "ministry_candidates": [
    {
      "name": "주무부처 후보",
      "relation_status": "confirmed",
      "relation_evidence": [
        {
          "title": "기관-주무부처 관계를 밝힌 공식 자료",
          "url": "https://공식-관계자료.example",
          "excerpt": "기관과 주무부처 관계를 확인할 수 있는 원문 일부"
        }
      ],
      "confidence": "high",
      "needs_verification": false
    }
  ],
  "selected_ministry": "주무부처 후보"
}
```

- `relation_status`는 `confirmed`, `user_provided`, `candidate` 중 하나다.
- `confirmed`는 같은 기관명과 부처명을 명시한 공식 `relation_evidence`가 있을 때만 쓴다.
- 명시 입력만 있으면 `user_provided`, 정책 발표기관에서만 얻었으면 `candidate`다.
- `selected_ministry`는 확인된 후보가 정확히 하나일 때만 채운다. 0개 또는 2개 이상이면
  `null`이다.
- 후보 이름을 얻지 못하면 `ministry_candidates=[]`, `selected_ministry=null`과 함께
  `field=ministry_candidates`인 `verification_notes`에 이유와 확인 방법을 반환한다.

## 근거와 signal 계약

정책 문서는 기존 `InstitutionEvidence`의 시점 필드 형태를 재사용하되 정책 전용 model로
검증한다. 정책 signal은 기존 `InstitutionSignalCandidate`와 다른 model이다.

```json
{
  "policy_signals": [
    {
      "title": "정책 방향 제목",
      "ministry_name": "주무부처 후보",
      "ministry_relation_status": "confirmed",
      "summary": "정책 원문만으로 작성한 요약",
      "policy_keywords": [],
      "institution_connection": "두 근거로 확인된 연결점",
      "job_connection": "지원 직무에서 검토할 기여 방향",
      "policy_evidence": [{"title": "정책 자료 제목"}],
      "institution_evidence": [{"title": "ALIO 주요사업"}],
      "relation_evidence": [{"title": "기관-주무부처 관계를 밝힌 공식 자료"}],
      "needs_verification": false
    }
  ]
}
```

| 필드 | 계약 |
| --- | --- |
| `title` | 정책 원문의 주제를 짧게 표시한다. |
| `ministry_name` | 정책을 발표한 후보 부처의 정규화 이름이다. |
| `ministry_relation_status` | 기관과 부처 관계의 확인 수준을 보존한다. |
| `summary` | 정책 원문만 요약하며 기관의 입장을 섞지 않는다. |
| `policy_evidence` | 정책의 제목, URL, excerpt, 연도와 게시·수집 시점을 보존한다. |
| `institution_evidence` | ALIO 주요사업 등 기관 자체 활동을 보여 주는 공식 근거만 담는다. |
| `relation_evidence` | 해당 기관과 부처의 관계를 확인한 공식 근거만 담는다. |
| `institution_connection` | 세 근거 중 정책과 기관 근거가 있고 관계가 확인됐을 때만 채운다. |
| `job_connection` | 답변 문장이 아니라 지원 직무 관점의 검토 축이다. |
| `needs_verification` | 관계, 원문 출처, 연도 또는 시점 중 하나라도 불명확하면 `true`다. |

한 배열에 서로 다른 provenance를 넣지 않는다. `institution_connection` 문자열 자체도 근거로
취급하지 않는다. 연결된 signal은 최소 한 개의 `policy_evidence`와
`institution_evidence`, 확인된 후보의 `relation_evidence`를 모두 가져야 한다.

## 기존 분석과 면접 도구 연결

향후 `analyze_institution_strategy`는 기관 전략과 정책 맥락을 분리해 반환한다.
`government_policy`와 `government_relation` evidence는 기존
`institution_strategy._signal_from_evidence`의 일반 변환 대상에서 제외하고 정책 전용
adapter에서만 처리한다. 따라서 정책 자료가 기본 `business_direction`으로 승격되는 경로는
허용하지 않는다.

`prepare_institution_interview`에는 기존 `signals`와 별도로 `policy_signals`,
`ministry_candidates`, `selected_ministry` 입력을 추가한다. 세 필드는
`analyze_institution_strategy`의 정책 adapter가 반환한 결과를 함께 전달하며, 면접 adapter는
`selected_ministry`가 `relation_status=confirmed`인 단일 후보인지 다시 확인한다. 정책 signal을
현재 `InstitutionSignalCandidate` 모양으로 변환하거나 현재 tool이 이미 받을 수 있다고 간주하지
않는다. 면접 adapter는 다음 조건을 모두 만족한 signal만 사용한다.

1. `needs_verification=false`다.
2. `ministry_relation_status=confirmed`이고 signal의 부처가 분석 결과의 `selected_ministry`와 일치한다.
3. 정책, 기관, 관계 evidence가 각각 하나 이상 있다.
4. 요청 연도와 policy evidence 연도가 일치한다.

정책 signal 단독 사용이 가능한 카드는 `기관 현안 이해`, `직무 관심도`, `전문성 어필`이다.
`지원동기`, `입사후포부`, `개선과제`에는 정책 signal만으로 문장을 만들지 않는다. 지원동기나
입사 후 포부에서 보조 맥락으로 사용할 때도 기관 공식 evidence를 주 근거로 선택하고 정책
evidence를 별도로 표시한다. 검증 상태는 adapter를 통과하면서 제거하거나 낮추지 않는다.

## 검증과 부분 실패

| 상황 | 처리 |
| --- | --- |
| URL만 있거나 제목만 있음 | 해당 문서를 제외하고 `policy_evidence[i]` note를 반환한다. |
| 제목, URL 또는 excerpt 누락 | 해당 문서를 제외한다. 다른 유효 문서는 계속 처리한다. |
| URL 형식 오류 | 해당 문서를 제외하고 `warnings`에 원래 index를 남긴다. |
| 공식 원문 여부 미확인 | 요약 후보는 유지할 수 있으나 연결에는 쓰지 않고 `needs_verification=true`로 둔다. |
| 발표기관과 후보 부처 불일치 | 자동 교정하지 않고 후보를 모두 남기며 `selected_ministry=null`로 둔다. |
| 관계 evidence 없음 | 정책 요약은 유지하되 `institution_connection=null`, `needs_verification=true`다. |
| 기관 evidence 없음 | 정책 요약은 유지하되 `institution_connection=null`, `needs_verification=true`다. |
| 요청 연도와 근거 연도 불일치 | 해당 연도의 연결에서 제외하며 다른 연도 자료로 대체하지 않는다. |
| 게시·수집 시점 형식 오류 | 원문 값은 `fields.raw_*`에 보존하고 파싱 필드는 `null`, `needs_verification=true`로 둔다. |
| 같은 문서가 중복됨 | 정규화 URL, 발표기관, 게시 시점 조합으로 합치고 발견 경로와 별칭을 보존한다. |
| 유효·무효 문서가 혼재함 | 유효 문서 결과와 무효 문서의 index별 경고를 함께 반환한다. |
| 확인된 부처 후보가 여러 개 | 자동 선택하지 않고 모든 후보와 확인 note를 반환한다. |

정책 검증의 객체형 `verification_notes`는 동일한 `field`, `reason`, `suggested_check` 조합으로
중복 제거한다. 기존 ALIO 조회와 정책 검증의 `warnings: list[str]`는 문자열 배열 계약을 유지해
이어 붙이고, 동일한 문자열만 최초 순서대로 중복 제거한다. 두 필드를 서로 합치거나 형식을
바꾸지 않는다. 빈 결과도 정상 응답이며 `policy_signals=[]`과 확인 방법을 반환한다.

## 출처 우선순위와 중복

1. 주무부처 공식 업무계획, 보도자료, 정책 원문
2. 정책브리핑에 게시된 부처 자료와 공식 원문 연결 정보
3. 사용자가 제공한 제목, URL, excerpt

우선순위는 대표 evidence를 고르는 기준이며 낮은 순위 자료를 자동으로 공식 근거로 승격하는
규칙이 아니다. 특정 도메인을 코드에 고정하지 않고 source 검증 방법은 외부 source 연동 승인
시 별도로 정한다.

## 구현 변경 지점

승인 후 1차 구현은 다음 경계를 함께 변경해야 한다.

- `schemas/institution.py`: `government_policy`, `government_relation`, `MinistryCandidate`,
  `PolicySignal`, 정책 입력·출력 필드 추가
- `tools/institution_analysis.py`: 전략 tool의 정책 입력·출력과 면접 tool의 `policy_signals`,
  `ministry_candidates`, `selected_ministry` 입력을 JSON schema와 handler에 함께 추가
- `analysis/institution_strategy.py`: 일반 evidence 변환에서 정책 source 제외, 정책 전용 adapter 추가
- `analysis/institution_interview.py`: 검증된 정책 signal의 카드 allowlist와 주 근거 선택 규칙 추가
- `tests/`: 후보 0·1·복수, provenance 분리, 연도 불일치, 부분 실패, 면접 카드 차단 테스트 추가

입력만 추가하고 출력이나 면접 handler를 그대로 두는 부분 구현은 하지 않는다.

## 단계별 구현과 승인

### 1단계: 사용자 제공 evidence

- 기존 `analyze_institution_strategy`에 정책 전용 입력·출력 계약 추가
- 기존 `prepare_institution_interview`에 검증된 `policy_signals` 입력 추가
- 정상, 관계 미확인, 원문 없음, 연도 불일치, 복수 후보, 부분 실패 테스트 추가

새 source type과 기존 tool schema 변경이므로 구현 전에 승인이 필요하다.

### 2단계: 공식 정책 자료 자동 수집

- 정책브리핑 또는 부처 공식 자료 검색 경로 선정
- 원문 수집기, pagination, 중복 제거와 시점 정책 정의
- 기관-주무부처 관계 source 선정

새 외부 데이터 source 연동이므로 별도 승인이 필요하다. 특정 기관 seed나 수동 매핑을 일반
resolver처럼 사용하지 않는다.

## 완료 판단

- 주무부처 후보의 출처와 관계 확인 수준이 결과에 표시된다.
- 정책, 기관, 관계 evidence가 각각 보존된다.
- 정책 방향, 기관 연결, 직무 연결이 서로 다른 필드로 반환된다.
- 정책 evidence가 기존 기관 전략 signal로 자동 승격되지 않는다.
- 면접 도구의 정책 입력과 카드별 사용 범위가 명시돼 있다.
- 근거 부족, 잘못된 항목, 복수 후보와 0건 결과가 단정 없이 반환된다.
- 실제 구현에 필요한 schema, handler, adapter와 테스트 변경 지점이 모두 정의된다.
