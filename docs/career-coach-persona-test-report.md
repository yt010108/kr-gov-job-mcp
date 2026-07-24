# 공공기관 취업 코치 페르소나 테스트

테스트 기준일은 2026-07-24이며, 대상은
`codex/public-job-career-coach` 브랜치의 `public_job_career_coach`다.

## 테스트 목적

대표 요청인 “공공기관 취업하려는데 도와줘”에서 시작해 다음 계약을 확인한다.

1. 사용자 유형 네 가지를 먼저 제시한다.
2. 선택한 유형에 필요한 정보만 추가로 요청한다.
3. 사용자가 제공한 답변을 다음 호출에 보존한다.
4. 필수 정보가 모이면 후속 도구를 자동 실행한다.
5. 공고 탐색, 지원 준비, 면접 준비 결과를 한 화면용 `dashboard`로 반환한다.
6. 정보 부족과 외부 조회 실패에서도 상태를 명확히 구분한다.

페르소나 원문과 구조화 인자는
[`examples/career-coach-personas.json`](../examples/career-coach-personas.json)에 고정했다.
재현 가능한 자동 검증은
[`tests/test_public_job_career_coach_execution.py`](../tests/test_public_job_career_coach_execution.py)의
persona 테스트가 담당한다.

## 테스트 층

| 층 | 검증 범위 | 외부 데이터 |
| --- | --- | --- |
| 결정적 자동 테스트 | 메뉴 → 추가 질문 → 답변 병합 → 하위 도구 → dashboard | 고정 fake |
| 실제 데이터 스모크 | Job-ALIO 공고·상세, ALIO 평균보수·기관 분석 | 사용 |
| 호스트 자연어 E2E | 자연어 발화를 호스트 모델이 `support_mode`와 인자로 변환 | 미실행 |

`public_job_career_coach`는 자연어 분류기 자체가 아니라 구조화된 MCP 인자를 받는 도구다.
따라서 CI는 구조화 인자 이후를 결정적으로 검증한다. 마지막 층은 배포된 MCP Player나
동일한 호스트 모델 환경에서 별도로 확인해야 한다.

## 페르소나

| ID | 사용자 | 유형 | 핵심 요구 |
| --- | --- | --- | --- |
| `beginner_minji` | 민지 | `beginner` | 관심 분야에서 직무와 공고를 찾는 첫 준비 |
| `job_search_junho` | 준호 | `job_search` | 정보보호 신입 공고 3개와 보수·적합도 비교 |
| `application_seoyeon` | 서연 | `application` | 선택 공고 분석과 경험 기반 STAR |
| `interview_hyeonu` | 현우 | `interview` | 기관 전략·개선과제·예상 질문·STAR |
| `missing_information_jisu` | 지수 | 예외 | 목표 직무가 없어 추가 질문 필요 |
| `partial_salary_taehun` | 태훈 | 예외 | 평균보수 실패 시 나머지 결과 보존 |

## 결정적 자동 테스트 결과

| 페르소나 | 기대 상태 | 검증 결과 |
| --- | --- | --- |
| 민지 | `completed` | `job_discovery`, 공고 카드·D-day·보수·적합도·보완 역량·오늘 할 일·링크 확인 |
| 준호 | `completed` | `profile_fit` 공고 순위와 한 화면 카드 확인 |
| 서연 | `completed` | `source_job_id` 재사용, 지원 패키지와 STAR 확인 |
| 현우 | `completed` | 공고·기관 일치, 전략·개선·질문·STAR·근거 링크 확인 |
| 지수 | `needs_more_information` | `target_role`만 다시 요청하고 하위 호출 0회 |
| 태훈 | `partial_success` | 공고·적합도·링크 유지, 보수만 `null`, 보수 trace만 실패 |

persona 테스트 7개를 포함해 전체 테스트는 `285 passed`였고 Ruff도 통과했다.

## 실제 공공데이터 스모크 결과

실데이터 값은 조회 시점에 바뀌므로 특정 기관명, 공고 ID, 보수액을 자동 assertion으로
고정하지 않았다. 구조, 최대 개수, 링크, 주의문과 상태만 검증 기준으로 사용했다.

| 페르소나 | 상태 | 시간 | 후보 흐름 | 결과 |
| --- | --- | ---: | --- | --- |
| 민지 | `partial_success` | 5.97초 | 검색 8 → 상세 4 → 표시 2 | 두 카드 모두 필수 6개 항목 충족 |
| 준호 | `completed` | 7.45초 | 검색 8 → 상세 6 → 표시 3 | 세 카드 모두 필수 6개 항목 충족 |
| 서연 | `completed` | 1.93초 | 준호의 1순위 `302694` 재사용 | 공고·보수·적합도·행동·링크·STAR 1개 |
| 현우 | `partial_success` | 19.59초 | 같은 공고와 상세 기관명 재사용 | 전략 3, 개선 1, 질문 4, STAR 1, 링크 12 |

여기서 필수 6개 항목은 D-day, 평균보수, 적합도, 보완·확인 역량, 오늘 할 일,
지원 링크다.

민지는 “디지털 서비스”의 NCS 코드가 모호해 keyword 검색으로 전환되었기 때문에
`partial_success`였다. 결과 카드는 모두 완성됐다. 현우는 요청 연도 2025에 맞는 ALIO
주요사업 공시가 없어 경고가 발생했지만, 확보한 다른 공시 근거와 평균보수로 면접 패키지를
완성했다.

## 확인된 문제와 위험

### P1: 정보 부족 응답의 자유서술 원문 재노출

`needs_more_information` 상태는 다음 호출을 위해 `preserved_arguments`와
`next_call.arguments`를 반환한다. 사용자가 공고 ID보다 경험·준비 메모를 먼저 입력하면
해당 원문도 응답에 포함된다.

합성 전화번호 sentinel로 확인한 결과:

```text
missing_information_echoes_free_text = true
```

무상태 재호출에 필요한 일반 필드는 유지하되 `user_experiences`,
`preparation_notes` 같은 민감 가능 필드는 호스트가 별도로 보관하거나 안전한 참조값으로
교체하는 설계가 필요하다.

### P1: 하위 예외 문자열의 비밀값 재노출

하위 도구 예외는 길이만 240자로 제한해 `warnings`와 `execution_trace.error`에 넣는다.
합성 API key sentinel로 확인한 결과:

```text
downstream_error_echoes_secret_text = true
```

오류 메시지를 반환하기 전에 토큰, API key, 이메일, 전화번호 형태를 제거하는 공통
sanitizer가 필요하다.

### P1: 면접 실데이터 응답 시간이 시간 예산에 근접

현우 페르소나는 19.59초가 걸렸다. 코치는 시작 후 20초가 지나면 새 하위 단계를 시작하지
않으므로 네트워크가 조금만 느려져도 평균보수나 STAR가 생략될 수 있다. 기관 전략과
개선과제가 같은 ALIO context를 중복 조회하지 않도록 공유하거나 병렬화하는 개선이 필요하다.

### P2: “이번 달” 의미가 완전히 구현되지 않음

준호의 발화는 “이번 달 지원할 만한 공고”지만 현재 구현은 `ongoing_only=true`, 즉
조회일 현재 접수 중인 공고로 해석한다. 이번 달 안에 마감하는 공고만 제한하지 않으므로
다음 달 마감 공고가 포함될 수 있다.

`application_window` 또는 `deadline_scope` 같은 명시적 입력을 추가해 다음 두 의미를
분리하는 편이 안전하다.

- `open_now`: 지금 접수 가능한 공고
- `deadline_this_month`: 기준 월 안에 마감하는 공고

### P2: 넓은 관심 분야는 부분 성공으로 내려갈 수 있음

“디지털 서비스”처럼 NCS 후보가 여러 개인 관심 분야는 코드로 확정하지 않고 keyword
검색으로 전환한다. 결과는 사용할 수 있지만 상태가 `partial_success`가 되므로 시연에서는
경고 이유를 사용자에게 함께 설명해야 한다.

## 결론

유형 선택 이후의 네 핵심 워크플로와 두 예외 워크플로는 재현 가능한 테스트를 통과했다.
실데이터에서도 네 핵심 페르소나 모두 최종 dashboard를 만들었고, 공고 탐색과 지원 준비는
대표 시연에 사용할 수 있는 수준이었다.

다음 우선순위는 자유서술·오류 문자열 redaction, 면접 흐름의 ALIO 조회 재사용과 응답시간
개선, “이번 달” 검색 범위의 명시적 구분이다. 배포된 MCP Player에서는 마지막으로 자연어
발화가 올바른 `support_mode`와 인자로 변환되는지 별도 E2E 확인이 필요하다.
