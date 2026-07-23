# 기관 뉴스·이슈 분석 확장 설계

## 상태와 범위

이 문서는 기관 관련 뉴스에서 최근 이슈 후보를 정리하는 후속 기능의 계약을 제안한다.
현재 서버는 BigKinds API나 뉴스 검색을 호출하지 않으며 뉴스 분석 MCP tool도 제공하지 않는다.
이번 설계는 새 외부 source, dependency 또는 기존 tool schema를 추가하지 않는다.

1차 구현은 사용자가 제공한 기사 메타데이터와 짧은 excerpt만 처리한다. BigKinds는 기사 발견
경로일 수 있지만 원 기사의 발행처나 공식 확인 자료를 대신하는 근거로 취급하지 않는다.

## 설계 결정

- 뉴스는 ALIO나 기관 홈페이지와 성격이 달라 별도 `analyze_institution_news_issues` 경계를 둔다.
- 현재 기관 전략·약점·면접 구현에는 뉴스형 수동 evidence를 판별하는 guard가 없다. 전략
  evidence는 사업 방향, 약점 evidence는 개선과제 signal로 변환될 수 있고, 두 결과 모두 면접
  카드 선택에 사용될 수 있다. 승인된 뉴스 경계를 구현하기 전에는 호출자가 뉴스를 기존
  `evidence`나 `signals`에 전달하지 않는다.
- 기사에 실제로 포함된 기관명과 excerpt가 있을 때만 기관 관련성 후보를 만든다.
- 보도 내용, 기관 공식 입장, 직무 연결 해석을 서로 다른 필드로 보존한다.
- 사고·논란 보도는 공식 확인 전까지 사실로 단정하지 않고 `needs_verification=true`로 둔다.
- 기사 본문 전체를 저장하거나 반환하지 않는다.

## 1차 입력 계약 제안

```json
{
  "institution_name": "기관명",
  "job_name": "지원 직무명",
  "keywords": ["정책 키워드"],
  "period": {
    "start": "2026-01-01",
    "end": "2026-07-14"
  },
  "news_items": [
    {
      "title": "기사 제목",
      "publisher": "언론사명",
      "url": "https://기사-원문.example/news/1",
      "published_at": "2026-07-10T09:00:00+09:00",
      "retrieved_at": "2026-07-14T12:00:00+09:00",
      "excerpt": "기관명과 이슈 판단 근거가 포함된 짧은 원문",
      "source": "user_provided",
      "discovery_source": "bigkinds"
    }
  ],
  "official_evidence": []
}
```

| 필드 | 계약 |
| --- | --- |
| `institution_name` | 분석 대상 기관명. 필수 |
| `job_name` | 직무 관련성 검토에만 사용하며 없으면 직무 연결을 비운다. |
| `keywords` | 필터 보조값이며 기사에 없는 사실을 생성하는 근거가 아니다. |
| `period` | 기사 게시 시점의 포함 범위다. 시작일은 종료일보다 늦을 수 없다. |
| `news_items` | 사용자가 제공한 기사 제목, 발행처, URL, 시점, excerpt 목록이다. |
| `source` | `user_provided`, `bigkinds`, `web_search`, `unknown` 후보 값이다. |
| `discovery_source` | 기사를 발견한 경로이며 기사 발행처와 구분한다. |
| `official_evidence` | 기관 보도자료 등 기사 내용을 교차 확인하는 별도 공식 근거다. |

`news_items`, `official_evidence`와 source 값은 향후 구현 승인이 필요한 schema 후보다.
BigKinds에서 발견했더라도 `publisher`, 원 기사 URL과 excerpt가 없으면 분석하지 않는다.

## 출력 계약 제안

```json
{
  "news_issue_signals": [
    {
      "title": "최근 이슈 제목",
      "issue_type": "policy",
      "summary": "기사에서 확인되는 범위의 요약",
      "institution_relevance": {
        "status": "explicit",
        "matched_mentions": ["기관명"],
        "reason": "기사 excerpt에 기관명이 명시됨"
      },
      "job_relevance": {
        "status": "candidate",
        "reason": "지원 직무에서 확인할 업무 연결점"
      },
      "article_evidence": [
        {
          "publisher": "언론사명",
          "url": "https://기사-원문.example/news/1",
          "published_at": "2026-07-10T09:00:00+09:00",
          "excerpt": "기관명과 이슈 판단 근거가 포함된 짧은 원문",
          "source": "user_provided",
          "discovery_source": "bigkinds"
        }
      ],
      "official_evidence": [],
      "confidence": "medium",
      "needs_verification": true
    }
  ],
  "interview_question_candidates": [],
  "cover_letter_usage_candidates": [],
  "verification_notes": [],
  "warnings": []
}
```

### 이슈 signal

- `issue_type`: `policy`, `business`, `incident`, `performance`, `controversy`,
  `recruitment_or_organization` 중 하나다. 복수 유형이면 후보를 나누거나 가장 직접적인 유형과
  보조 태그를 반환하며 임의로 평판 점수를 만들지 않는다.
- `summary`: 기사 제목과 excerpt에서 확인되는 내용만 요약하고 반드시 “보도에 따르면” 같은
  출처 맥락을 유지한다.
- `institution_relevance.status`: 기관명이 명시된 `explicit`, 공식 별칭이 명시된 `alias`,
  추가 확인이 필요한 `candidate` 중 하나다.
- `job_relevance`: 기사 사실이 아니라 지원 직무 관점의 검토 축이다. 입력 직무나 근거가 없으면
  `null`이다.
- `article_evidence`: 기사 발행처, 원 URL, excerpt, 게시·수집 시점을 담는다.
- `official_evidence`: 기관 또는 관계기관의 공식 확인 자료만 담는다. 기사와 한 배열에 섞지 않는다.
- `confidence`: 입력 완전성, 기관명 명시 여부와 공식 교차 확인 여부를 반영한
  `low`, `medium`, `high`다.
- `needs_verification`: 공식 확인 부족, 기관 관련성 후보, 시점 오류 또는 출처 불명확 중 하나라도
  있으면 `true`다.

`confidence=high`는 공식 자료가 기사의 핵심 주장을 직접 확인하고 기사·공식 자료의 기관과
시점이 일치할 때만 가능하다. 높은 confidence도 기사 해석을 기관의 공식 입장으로 바꾸지는 않는다.

| confidence | 기준 |
| --- | --- |
| `low` | source가 불명확하거나 기관 관련성이 후보 수준이다. |
| `medium` | 기사 필수 필드와 기관 명시 근거는 있지만 공식 교차 확인이 없다. |
| `high` | 필수 필드가 있고 기관 관련성이 명시됐으며 공식 자료가 핵심 주장을 직접 확인한다. |

### 면접·자기소개서 연결

뉴스 signal은 기존 기관 signal과 다른 model로 유지한다. 향후
`prepare_institution_interview`에 `news_issue_signals` 전용 입력을 추가하더라도 다음 조건을
모두 만족한 항목만 카드 후보로 사용한다.

1. 기관 관련성이 `explicit` 또는 검증된 `alias`다.
2. 기사 URL, 발행처, 게시 시점과 excerpt가 모두 있다.
3. 요청 기간 안의 기사다.
4. 사고·논란은 공식 교차 확인이 있거나 카드 전체가 확인 질문 형태로 작성된다.

허용 카드 유형은 `최근 현안 이해`, `직무 관심도`, `확인할 질문`이다. 뉴스만으로
`지원동기`, `입사후포부`, `개선과제`나 기관 평가 문장을 확정하지 않는다. 자기소개서 활용
후보도 기관의 공식 사업 근거가 별도로 있을 때 보조 맥락으로만 반환한다.

면접 질문 후보는 완성 답변이 아니라 다음 구조로 반환한다.

```json
{
  "question_type": "최근 현안 이해",
  "likely_question": "최근 보도된 이슈를 어떻게 보고 있나요?",
  "answer_direction": "보도 내용과 공식 확인 여부를 구분하고 지원 직무에서 확인할 점을 설명한다.",
  "signal_indexes": [0],
  "evidence": [],
  "caution": "미확인 보도를 기관의 확정 사실로 표현하지 않는다.",
  "needs_verification": true
}
```

`signal_indexes`는 사용한 `news_issue_signals`를 가리키며 원 기사 evidence를 함께 반환한다.
`cover_letter_usage_candidates`는 `status=blocked` 또는 `supporting_context`를 사용한다. 기관
공식 사업 근거가 없거나 뉴스 signal이 검증되지 않았으면 `blocked`와 이유만 반환하고 문장을
생성하지 않는다.

## 검증과 부분 실패

| 상황 | 처리 |
| --- | --- |
| 제목, URL, 발행처 또는 excerpt 누락 | 해당 항목을 제외하고 `news_items[i]` note를 반환한다. |
| URL 형식 오류 | 해당 항목을 제외하고 원래 index를 `warnings`에 남긴다. |
| 게시 시점 없음 또는 형식 오류 | 기간 판정에서 제외하고 원문 값과 확인 방법을 남긴다. |
| 요청 기간 밖 기사 | 결과에서 제외하며 기간 안의 기사로 대체했다고 표현하지 않는다. |
| 기사에 기관명·확인된 별칭 없음 | 관련성을 `candidate`로 두고 우선 결과에서 제외한다. |
| 검색 키워드만 일치 | 기관 관련성 근거로 승격하지 않는다. |
| 사고·논란의 공식 근거 없음 | 요약은 보도 내용으로 한정하고 `needs_verification=true`를 유지한다. |
| 공식 자료가 기사를 반박함 | 양쪽 근거를 보존하고 `conflict` warning을 반환한다. |
| 같은 기사가 중복됨 | 정규화 URL을 우선하고 발행처·제목·게시 시점 조합으로 보조 판정한다. |
| 유효·무효 항목 혼재 | 유효한 결과와 무효 항목별 warning을 함께 반환한다. |
| 유효한 기사가 0건 | 빈 signal과 검색 범위·기관명·원 URL 확인 note를 반환한다. |

중복 기사에서 대표 원문 하나를 선택하되 `discovery_source`와 원래 입력 index는 보존한다.
객체형 `verification_notes`는 동일한 `field`, `reason`, `suggested_check` 조합으로 중복
제거한다. `warnings: list[str]`는 문자열 배열 계약을 유지하고 동일한 문자열만 최초 순서대로
중복 제거한다.

## 저작권과 개인정보

- 기사 전체 본문, 유료 기사 본문이나 대량 검색 결과를 저장하지 않는다.
- 제목, 메타데이터와 판단에 필요한 짧은 excerpt만 보존한다.
- 입력에 기자 연락처나 기사와 무관한 개인정보가 있으면 signal evidence에서 제외한다.
- 결과는 원문을 대체하는 기사 재게시물이 아니라 출처 링크가 있는 분석 후보여야 한다.

## 단계별 구현과 승인

### 1단계: 사용자 제공 뉴스

- 뉴스 전용 schema와 분석 helper 추가
- `analyze_institution_news_issues` MCP tool 등록
- 정상, 출처 부족, 기관 미일치, 사고·논란 미확인, 기간 밖, 부분 실패 테스트 추가
- 현재 기관 전략과 면접 tool에 자동 연결하지 않음

새 MCP tool과 schema를 추가하므로 구현 전에 별도 승인이 필요하다.

### 2단계: 면접 tool 연결

- `prepare_institution_interview`에 `news_issue_signals` 전용 입력 추가
- 카드 allowlist와 공식 근거 우선 규칙 구현
- 기존 ALIO signal과 뉴스 provenance가 섞이지 않는 회귀 테스트 추가

기존 tool 입력·출력 schema 변경이므로 별도 승인이 필요하다.

### 3단계: BigKinds 또는 검색 연동

- 접근 권한, API 약관, 원문 제공 범위와 호출 제한 확인
- 검색 client, pagination, 중복 제거와 수집 시점 정책 정의
- 실패 시 사용자 제공 입력으로 돌아가는 부분 결과 계약 구현

새 외부 데이터 source와 dependency 가능성이 있으므로 별도 승인이 필요하다.

## 구현 변경 지점

승인 후 1단계 구현은 다음 경계를 사용한다.

- `schemas/`: 기사 evidence, 이슈 signal과 report model
- `analysis/`: 입력 검증, 중복 제거, 관련성·유형 후보 생성
- `tools/`: 전용 tool schema와 orchestration handler
- `tools/builtin.py`: 승인된 tool 등록
- `tests/`: 정상·0건·충돌·부분 실패와 registry 회귀 테스트

특정 기관명, 기사 또는 좋은 데모 결과를 위한 seed는 추가하지 않는다.

## 완료 판단

- 각 signal에 기사 source, confidence와 `needs_verification`이 있다.
- 기사 evidence와 기관 공식 evidence가 분리된다.
- 기관 관련성과 직무 관련성의 근거가 별도 필드로 반환된다.
- 뉴스가 기존 기관 사업 방향이나 기관 공식 입장으로 자동 승격되지 않는다.
- 면접·자기소개서에서 허용되는 사용 범위와 차단 조건이 명시돼 있다.
- 기간 오류, 중복, 충돌, 무효 항목과 0건 결과가 안전하게 처리된다.
- BigKinds 직접 연동은 접근 조건 확인과 별도 승인 전까지 구현하지 않는다.
