# generate_star_answer_framework

`generate_star_answer_framework`는 사용자가 직접 제공한 경험 원문을 Situation, Task, Action,
Result로 나누고, 부족한 근거와 과장 위험을 먼저 확인하는 도구다. 외부 공고나 기관 정보를
자동 조회하지 않는다.

## 입력

```json
{
  "question": "문제를 해결한 경험을 설명해 주세요.",
  "user_experience": "Situation: ...\nTask: ...\nAction: ...\nResult: ...",
  "target_job": "전산직",
  "institution_name": "한국인터넷진흥원",
  "ncs_competencies": ["문제해결능력"],
  "mode": "both"
}
```

필수 입력은 `question`, `user_experience`, `target_job`이다. `institution_name`과
`ncs_competencies`는 선택 입력이며, `mode`는 `cover_letter`, `interview`, `both` 중 하나다.
PREP와 AUTO 프레임은 이 도구에서 지원하지 않는다.

## 출력 계약

- `star`: 각 STAR 항목의 `source_excerpts`, `status`, 작성 가이드
- `job_connections`: 지원 직무와 NCS 후보를 사용자 경험과 대조하기 위한 보수적 연결 문장
- `institution_connection`: 기관명이 있을 때만 반환하는 추가 확인 안내
- `missing_evidence`, `follow_up_questions`: 비어 있는 STAR 항목과 보완 질문
- `risk_flags`: 절대 표현, 단독 수행, 조직 전체 범위, 검증되지 않은 수치 표현
- `interview_answer`, `cover_letter_draft`: 요청한 mode에 맞춘 별도 형식의 답변 초안

네 STAR 항목이 모두 사용자 원문으로 뒷받침되고 과장 위험 표현이 없을 때만 답변 본문을
생성한다. 그렇지 않으면 `needs_evidence` 상태와 보완 질문을 반환하며, 누락된 성과·수치·역할을
임의로 채우지 않는다.

NCS 후보는 사용자가 이미 보유한 역량이라고 단정하지 않는다. 기관 연결도 기관의 공개 공고,
직무기술서, 사업 자료를 별도로 확인한 뒤 보완해야 한다.

## CLI 예시

```bash
python -m kr_gov_job_mcp.server --call-tool generate_star_answer_framework --input '{"question":"문제 해결 경험을 설명해 주세요.","user_experience":"Situation: 반복 오류가 있었다.\nTask: 원인 파악을 맡았다.\nAction: 로그를 분석했다.\nResult: 점검 절차를 만들었다.","target_job":"전산직","ncs_competencies":["문제해결능력"],"mode":"both"}'
```
