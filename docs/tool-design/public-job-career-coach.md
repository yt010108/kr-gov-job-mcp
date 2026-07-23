# public_job_career_coach

`public_job_career_coach`는 “공공기관 취업하려는데 도와줘”처럼 준비 단계를 특정하지 않은
요청을 받는 대표 원스톱 도구다. 첫 호출에서 사용자 유형을 선택하게 하고, 선택한 유형에 필요한
정보가 모이면 기존 MCP 도구를 안전한 순서로 실제 호출해 한 화면용 대시보드로 합친다.

기본값은 `auto_execute=true`다. 따라서 필수 정보가 모인 뒤 에이전트가 개별 도구를 다시
조합할 필요가 없다. 호출 계획만 확인하려면 `auto_execute=false`를 명시한다.

## 대표 프롬프트

> 공공기관 취업하려는데 도와줘

에이전트는 이 요청에 바로 세부 조건을 추측하지 않고 도구를 빈 입력으로 호출한다.

```json
{}
```

## 사용자 유형 선택

빈 입력 호출은 다음 네 가지 유형을 반환한다.

| `support_mode` | 사용자에게 보여줄 선택지 | 준비할 워크플로 |
| --- | --- | --- |
| `beginner` | 처음 준비하고 있어요 | 관심 직무와 준비 방향 탐색 |
| `job_search` | 지원할 공고를 찾고 있어요 | 조건에 맞는 채용공고 탐색 |
| `application` | 지원할 공고가 정해졌어요 | 공고 상세, 적합도, 지원 준비 |
| `interview` | 면접을 준비하고 있어요 | 기관 분석, 예상 질문, STAR 준비 |

에이전트는 네 선택지를 사용자에게 그대로 안내하고, 사용자가 고른 값을 다음 호출의
`support_mode`로 전달한다.

## 대화 상태

| `status` | 의미 | 에이전트의 다음 행동 |
| --- | --- | --- |
| `needs_user_selection` | 아직 사용자 유형을 선택하지 않음 | 네 가지 사용자 유형을 보여주고 하나를 선택하게 함 |
| `needs_more_information` | 유형은 선택했지만 해당 워크플로에 필요한 정보가 부족함 | `missing_fields`와 질문을 전달한 뒤 같은 도구를 다시 호출 |
| `completed` | 선택한 워크플로의 핵심 단계가 실행되고 대시보드가 완성됨 | `dashboard`를 사용자에게 보여줌 |
| `partial_success` | 일부 조회·분석이 실패하거나 제한됐지만 사용할 수 있는 결과가 있음 | 확보된 결과와 `warnings`를 함께 보여줌 |
| `no_results` | 공고 검색은 실행됐지만 조건에 맞는 현재 접수 공고가 없음 | 검색 진단과 조건 완화용 `today_actions`를 보여줌 |
| `failed` | 핵심 단계 실패로 요청한 패키지를 만들 수 없음 | `execution_trace`와 `warnings`를 바탕으로 입력·원문 접근 상태를 확인 |
| `workflow_ready` | `auto_execute=false`로 요청해 실행하지 않고 계획만 준비됨 | `workflow_steps`를 검토하거나 별도로 실행 |

MCP 도구는 호출 도중 사용자의 답을 기다리지 않는다. 각 상태를 반환하고 호출을 끝내며,
에이전트가 사용자의 답을 받은 뒤 같은 도구를 다시 호출한다.

## 입력

첫 호출에는 필수 입력이 없다.

| field | 설명 |
| --- | --- |
| `support_mode` | `beginner`, `job_search`, `application`, `interview` 중 하나 |
| `career_level` | `entry`, `experienced`, `any` 중 하나 |
| `interests` | 입문 사용자가 관심 있는 업무나 분야 |
| `target_role` | 관심 있거나 지원하려는 직무 |
| `known_skills` | 보유 자격, 기술, 프로젝트, 업무 경험 |
| `regions` | 희망 근무지역 목록 |
| `job_id` | Job-ALIO 공고 ID. 세 ID alias 중 하나만 있어도 됨 |
| `source_job_id` | `search_public_jobs`가 반환한 Job-ALIO 원본 공고 ID alias |
| `recruitment_notice_sn` | Job-ALIO 채용공고 일련번호 alias |
| `institution_name` | 지원 기관명 |
| `user_experiences` | 자기소개서나 면접 답변에 사용할 경험 목록 |
| `question` | STAR 답변을 준비할 자기소개서 문항 또는 면접 질문 |
| `preparation_notes` | 지원 준비 상태나 경험에 대한 추가 메모 |
| `year` | 기관 분석과 평균보수 조회 기준 연도. `2000`~`2100` |
| `as_of_date` | D-day 계산 기준일. 생략하면 한국 표준시 기준 호출일 |
| `max_results` | 한 화면에 표시할 공고 수. `1`~`3`, 기본값 `3` |
| `fetch_live_alio` | 기관 분석에서 ALIO 실시간 조회 허용 여부. 기본값 `true` |
| `auto_execute` | 필수 정보 수집 후 기존 도구 자동 실행 여부. 기본값 `true` |

유형별 최소 입력은 다음과 같다.

| `support_mode` | 최소 입력 |
| --- | --- |
| `beginner` | `career_level`, 한 개 이상의 `interests` |
| `job_search` | `target_role`, `career_level` |
| `application` | `job_id`, `source_job_id`, `recruitment_notice_sn` 중 하나 |
| `interview` | `institution_name`, `target_role` |

도구가 반환한 `missing_fields`와 질문을 기준으로 필요한 정보만 추가하고, 사용자가 제공하지
않은 자격이나 경험을 추측해 채우지 않는다. `application`에서 세 ID alias가 모두 없을 때
`missing_fields`에는 대표 필드인 `job_id`가 표시된다. ID alias를 둘 이상 함께 전달할 때는
값이 모두 같아야 하며, 스키마에 없는 입력 필드는 허용하지 않는다.

자유서술 입력과 배열에는 크기 제한이 있다. `user_experiences`는 최대 10개이며 각 항목은
2,000자, `preparation_notes`는 4,000자까지다. 실제 STAR 자동 생성은 호출량을 제한하기
위해 앞의 경험 3개만 사용하며 이 경우 `partial_success`와 경고를 반환한다.

## 출력

모든 응답은 `status`를 포함한다. 상태에 따라 다음 필드가 추가된다.

| 상태 | 주요 출력 필드 |
| --- | --- |
| `needs_user_selection` | `menu`, `choices`, `next_call` |
| `needs_more_information` | `support_mode`, `questions`, `missing_fields`, `preserved_arguments`, `next_call` |
| `completed`, `partial_success`, `no_results`, `failed` | `support_mode`, `as_of_date`, `summary`, `dashboard`, `workflow_steps`, `execution_trace`, `warnings`, `input_summary`, `next_call` |
| `workflow_ready` | `support_mode`, `preserved_arguments`, `workflow_steps`, `next_call` |

`preserved_arguments`는 사용자가 이미 제공한 유효 입력을 다음 호출이나 후속 도구 연결에
재사용해야 하는 대화·계획 상태에만 포함한다. 자동 실행을 마친 응답의 `input_summary`는
`user_experiences`와 `preparation_notes` 원문을 복제하지 않고 제공 여부와 항목 수만
반환한다. 실행 추적에도 하위 도구 전체 인자나 사용자 경험 원문을 넣지 않는다. 다만
`question`과 입문자의 관심 분야는 STAR·직무 해석 결과의 맥락으로 표시될 수 있다.
`workflow_steps`의 각 항목은 `order`, `tool`, `purpose`를 담는다.
자동 실행 결과의 `execution_trace`에는 실제 단계별 도구와 `success`, `failed`, `cached`,
`skipped` 상태가 남는다. 자동 실행 결과와 `workflow_ready` 모두 대표 도구 재호출이
필요하지 않으므로 `next_call`은 `null`이다.

## 상태별 호출 예시

### 1. 빈 입력으로 사용자 유형 요청

```json
{}
```

응답 상태는 `needs_user_selection`이며, 네 가지 `choices`를 반환한다.

### 2. 유형 선택 후 추가 정보 요청

사용자가 “2번, 지원할 공고를 찾고 있어요”라고 답하면 같은 도구를 다시 호출한다.

```json
{
  "support_mode": "job_search"
}
```

공고 탐색에 필요한 정보가 부족하면 `needs_more_information`과 `missing_fields`를 반환한다.
에이전트는 응답에 포함된 질문만 사용자에게 묻는다.

### 3. 기본 자동 실행

```json
{
  "support_mode": "job_search",
  "target_role": "정보보호",
  "career_level": "entry",
  "known_skills": [
    "정보보안기사",
    "웹 보안 프로젝트"
  ],
  "regions": [
    "서울",
    "경기"
  ],
  "max_results": 3
}
```

`auto_execute`를 생략했으므로 기존 도구를 실제 호출한다. 정상 완료하면 `completed`, 일부
조회가 실패해도 사용할 수 있는 결과가 있으면 `partial_success`를 반환한다. 공고 탐색 결과는
조회일 현재 접수 중인 공고를 최대 3개까지 한 화면에 정리한다. 검색 요약만으로 최종 3개를
고정하지 않고 최대 6개 후보의 상세 내용을 먼저 비교한 뒤 보유 역량을 반영해 최종 순위를
정한다.

### 4. 계획만 확인

```json
{
  "support_mode": "job_search",
  "target_role": "정보보호",
  "career_level": "entry",
  "auto_execute": false
}
```

이 경우에만 기존 도구를 호출하지 않고 `workflow_ready`와 `workflow_steps`를 반환한다.

## 한 화면 대시보드

자동 실행 결과의 `dashboard.view`는 사용자 유형에 따라 달라진다.

| 사용자 유형 | `dashboard.view` | 핵심 내용 |
| --- | --- | --- |
| `beginner`, `job_search` | `job_discovery` | 목표 직무 해석, 최대 3개 공고 순위, 오늘 할 일 |
| `application` | `application_package` | 선택 공고 카드, 적합도·평균보수, STAR 프레임 |
| `interview` | `interview_package` | 기관 전략·개선과제, 면접 질문, STAR 프레임 |

`job_discovery.job_rankings`의 각 공고 카드는 다음 내용을 담는다.

- 순위, 기관명, 공고명, 공고 ID
- 마감일, 남은 일수, `D-Day` 또는 `D-n` 표시
- 채용 구분, 고용형태, 근무지역
- 직무·경력·보유 역량·지역을 근거로 한 지원 우선순위
- 적합 근거와 `missing_competencies`
- 최대 3개의 `today_actions`
- 지원 원문, 직무기술서, 평균보수 공시 링크
- ALIO 직원 평균보수와 기준 연도·결산/예산 구분

적합도 점수는 지원 우선순위를 정하기 위한 근거 점수이며 합격 가능성이나 합격 확률이 아니다.
`missing_competencies`도 확정된 결핍이 아니라 공고·NCS 근거에서 나온 보완·확인 후보다.
평균보수는 기관 전체 직원 기준이며 신입 초봉이나 채용 제시 연봉이 아니다.

`application_package`는 선택 공고 한 건의 동일한 공고 카드와 지원 준비 행동을 제공한다.
`user_experiences`가 있으면 경험별 STAR 프레임을 최대 3개까지 추가한다.
입력 기관명과 공고 상세 기관명이 다르면 공고 상세 기관을 기준으로 평균보수를 연결하고
불일치 경고를 남긴다. 평균보수 카드에도 조회 기관명을 함께 표시한다.

`interview_package`는 기관명·목표 직무, 선택 공고 요약, 평균보수, 전략 신호, 개선과제 신호,
예상 면접 질문, 오늘 할 일과 근거 링크를 합친다. 사용자 경험이 있으면 면접용 STAR 프레임을
최대 3개까지 추가한다.

## 대표 대화 예시

```text
사용자: 공공기관 취업하려는데 도와줘.

에이전트:
현재 준비 상태를 선택해 주세요.
1. 처음 준비하고 있어요.
2. 지원할 공고를 찾고 있어요.
3. 지원할 공고가 정해졌어요.
4. 면접을 준비하고 있어요.

사용자: 2번.

에이전트: 목표 직무와 신입·경력 여부를 알려주세요.

사용자:
정보보호 신입 공고를 찾고 있어. 정보보안기사와 웹 보안 프로젝트 경험이 있고,
서울이나 경기를 희망해.

에이전트:
조회일 현재 접수 중인 공고를 최대 3개까지 정리했습니다.
각 공고의 D-day, 기관 직원 평균보수, 적합 근거, 보완·확인 역량, 오늘 할 일과
지원 원문 링크를 한 화면에서 보여드리겠습니다.
```

## 유형별 자동 실행 흐름

| `support_mode` | 실제 호출 흐름 |
| --- | --- |
| `beginner` | `resolve_ncs_code` → `search_public_jobs` → 상위 공고별 상세·평균보수·적합도 |
| `job_search` | `resolve_ncs_code` → 지역 코드 확인(입력 시) → `search_public_jobs` → 상위 공고별 상세·평균보수·적합도 |
| `application` | 공고 상세 → 평균보수 → 적합도 → STAR 프레임(경험 입력 시) |
| `interview` | 공고 상세(공고 ID 입력 시) → NCS 해석 → 기관 전략·개선과제 → 면접 카드 → 평균보수 → STAR 프레임(경험 입력 시) |

같은 기관의 평균보수는 한 번 조회한 뒤 재사용한다. 일부 상세·평균보수·적합도·STAR 호출이
실패해도 확보한 공고나 기관 결과는 버리지 않고 `partial_success`로 반환한다. 동일한
NCS·지역 검색 조건은 중복 호출하지 않으며 검색 조합은 최대 3개, 전체 워크플로 외부 호출은
최대 21회로 제한한다. 워크플로 시작 후 20초가 지나면 새로운 후속 단계를 시작하지 않고
확보한 결과를 반환한다. 개별 외부 클라이언트의 요청 제한시간은 별도로 적용된다. 제한으로
일부 조건이 생략되면 경고와 `partial_success`로 표시한다.
