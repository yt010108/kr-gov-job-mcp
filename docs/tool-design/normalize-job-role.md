# normalize_job_role

`normalize_job_role`은 사용자가 입력한 직무명과 자연어 요청을 채용/NCS 맥락의 직무군으로 정규화한다.

이번 MVP에서는 정보보안/정보보호 계열 표현을 Job-ALIO/NCS의 `정보통신` 계열로 정규화하고, 원문 직무명은 별도 필드로 보존한다.

## 입력

```json
{
  "query": "KISA 정보보안 면접준비",
  "target_role": "정보보안",
  "job_family": "정보보호",
  "known_skills": ["웹 보안", "정보보안기사"],
  "preparation_notes": "개인정보보호 업무 경험을 면접 답변으로 정리하고 싶다."
}
```

모든 필드는 선택값이지만, 최소 하나 이상의 입력이 필요하다. 명시적인 `target_role` 또는
`job_family`가 있으면 그 값을 우선한다. 따라서 회계 직무 지원자가 정보보안 자격이나 교육 이력을
함께 입력해도 목표 직무를 `정보통신`으로 바꾸지 않는다.

## 출력

주요 필드는 다음과 같다.

- `original_target_role`: 정규화 전 사용자가 입력한 목표 직무
- `original_job_family`: 정규화 전 사용자가 입력한 직무군
- `normalized_target_role`: 다음 도구 호출에 사용할 정규화된 목표 직무
- `normalized_job_family`: 다음 도구 호출에 사용할 정규화된 직무군
- `is_security_role`: 보안 직무 표현 감지 여부
- `matched_aliases`: 감지된 보안 직무 별칭
- `matched_fields`: 별칭이 발견된 입력 필드
- `recommended_next_arguments`: 후속 도구 호출에 넘기기 쉬운 인자 묶음
- `safe_context`: 취업 준비용 허용 출력과 금지 출력 범위

예시:

```json
{
  "original_target_role": "정보보안",
  "original_job_family": "정보보호",
  "normalized_target_role": "정보통신",
  "normalized_job_family": "정보통신",
  "is_security_role": true,
  "matched_aliases": ["정보보안", "정보보호"],
  "recommended_next_arguments": {
    "target_role": "정보통신",
    "job_family": "정보통신",
    "original_target_role": "정보보안"
  }
}
```

## 라우팅 기준

다음 표현이 `query`, `target_role`, `job_family`, `known_skills`, `preparation_notes` 중 하나에 포함되면 `prepare_institution_interview` 또는 `analyze_job_fit_report` 호출 전에 이 도구를 먼저 호출한다.

- 정보보안
- 정보보호
- 보안
- 침해대응
- 침해사고 대응
- 취약점 분석
- 개인정보보호
- 정보통신 보안
- 웹 보안
- 네트워크 보안

## 안전 범위

이 도구는 보안 직무명을 취업 준비 맥락으로 정규화하기 위한 도구다. 공격 절차, 악용 가능한 페이로드, 무단 접근 방법, 악성코드나 우회 절차는 출력 범위에서 제외한다.

## CLI 예시

```bash
python -m kr_gov_job_mcp.server --call-tool normalize_job_role --input '{"query":"KISA 정보보안 면접준비","target_role":"정보보안","known_skills":["웹 보안"]}'
```
