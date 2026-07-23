# public_job_career_coach

`public_job_career_coach`는 “공공기관 취업하려는데 도와줘”처럼 준비 단계를 특정하지 않은
요청을 받는 대표 진입 도구다. 첫 호출에서 사용자 유형을 선택하게 하고, 선택한 유형에 필요한
정보가 모이면 기존 MCP 도구를 사용할 수 있는 워크플로를 안내한다.

이 도구의 현재 범위는 사용자 유형 분류와 다음 워크플로 준비까지다. 공고 검색, 기관 분석,
평균보수 조회, 적합도 분석, 면접 카드 작성, STAR 답변 생성을 한 호출에서 자동 실행하지 않는다.

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
| `needs_more_information` | 유형은 선택했지만 해당 워크플로에 필요한 정보가 부족함 | `missing_fields`와 질문을 사용자에게 전달한 뒤 같은 도구를 다시 호출 |
| `workflow_ready` | 다음 워크플로를 시작할 정보가 준비됨 | 반환된 워크플로와 추천 도구를 바탕으로 후속 도구 호출 |

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

## 출력

모든 응답은 `status`를 포함한다. 상태에 따라 다음 필드가 추가된다.

| 상태 | 주요 출력 필드 |
| --- | --- |
| `needs_user_selection` | `menu`, `choices`, `next_call` |
| `needs_more_information` | `support_mode`, `questions`, `missing_fields`, `preserved_arguments`, `next_call` |
| `workflow_ready` | `support_mode`, `preserved_arguments`, `workflow_steps`, `next_call` |

`preserved_arguments`는 사용자가 이미 제공한 유효 입력을 다음 호출이나 후속 도구 연결에
재사용하기 위한 값이다. `workflow_steps`의 각 항목은 `order`, `tool`, `purpose`를 담는다.
`workflow_ready`에서는 대표 도구 재호출이 필요하지 않으므로 `next_call`은 `null`이다.

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

### 3. 워크플로 준비

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
  ]
}
```

필요한 정보가 모이면 `workflow_ready`를 반환한다. 이 상태는 공고 검색 결과가 이미
생성됐다는 뜻이 아니라, 공고 검색 워크플로를 시작할 입력이 준비됐다는 뜻이다.

## 대표 대화 예시

```text
사용자: 공공기관 취업하려는데 도와줘.

에이전트:
현재 준비 상태를 선택해 주세요.
1. 공공기관 취업을 처음 준비하고 있어요.
2. 지원할 공고를 찾고 있어요.
3. 지원할 공고가 정해졌어요.
4. 면접을 준비하고 있어요.

사용자: 2번.

에이전트: 목표 직무와 신입·경력 여부를 알려주세요.

사용자:
정보보호 신입 공고를 찾고 있어. 정보보안기사와 웹 보안 프로젝트 경험이 있고,
서울이나 경기를 희망해.

에이전트:
공고 탐색 워크플로가 준비됐습니다. 직무·경력·보유 역량·지역 조건을 바탕으로
코드 조회, 공고 검색, 상세 조회, 평균보수 확인, 적합도 분석 순서로 진행하겠습니다.
```

## 유형별 후속 흐름

| `support_mode` | 후속 흐름 |
| --- | --- |
| `beginner` | 직무 코드 후보 해석 → 공고 검색 → 공고 상세 조회 |
| `job_search` | 직무 코드 해석 → 지역 코드 확인(지역 입력 시) → 공고 검색 → 상세 조회 → 평균보수 → 적합도 |
| `application` | 공고 상세 → 적합도 → STAR 답변 준비(경험 입력 시) |
| `interview` | 공고 상세(공고 ID 입력 시) → 기관 전략 → 개선과제 → 면접 카드 → STAR 답변 준비(경험 입력 시) |

후속 흐름은 추천 순서다. 실제로 호출한 도구의 근거와 경고를 보존하고, 평균보수를 신입 초봉이나
채용 제시 연봉으로 표현하지 않는다.
