# prepare_institution_interview

`prepare_institution_interview`는 기관명과 목표 직무를 받아 면접 준비용 답변 카드를 만든다.

이번 MVP는 아래 공개 자료만 사용한다.

- ALIO 40 주요사업
- ALIO 47 국회 지적사항
- ALIO 50 연구보고서

감사/경영평가 자료, 채용공고, 직무기술서, NCS 정보는 아직 사용하지 않는다.

## 입력

```json
{
  "institution_name": "(재)한국보건의료정보원",
  "target_role": "보건의료정보",
  "year": 2026,
  "focus_areas": ["지원동기", "기관이해", "개선과제", "입사후포부"],
  "fetch_live_alio": true,
  "evidence": [],
  "signals": []
}
```

`target_role`은 필수다. `job_family`는 `target_role` 별칭으로 받을 수 있다.
보안 직무는 `정보보안`/`정보보호`가 아니라 Job-ALIO NCS 대분류명 `정보통신`으로 입력한다.

`evidence`와 `signals`가 비어 있고 `fetch_live_alio`가 `true`면, 도구는 먼저
`lookup_job_alio_codes` 기반 기관명 resolver로 ALIO 기관 코드를 찾고 40/47/50 항목을 조회한다.
`year`를 지정하면 같은 공시 연도의 자료만 면접 카드 근거로 사용한다. 일치 자료가 없으면 다른 연도 자료로 대체하지 않고 `warnings`로 반환한다.

자동 수집 evidence에는 근거 연도 `evidence_year`, 공시 시점 `disclosed_at`, 실제 수집 시각
`retrieved_at`을 보존한다. 기존 `collected_at`은 호환을 위해 실제 수집 시각과 같은 값으로 유지한다.

## 출력

주요 필드는 다음과 같다.

- `interview_cards`: 면접 질문 카드 목록
- `materials_to_check`: 이번 MVP에서 확인하는 자료
- `excluded_for_now`: 아직 사용하지 않는 자료
- `verification_notes`: 근거가 없거나 추가 확인이 필요한 항목
- `warnings`: ALIO 조회 중 발생한 비차단 경고

카드는 아래 구조를 따른다.

```json
{
  "question_type": "개선과제",
  "likely_question": "기관이 보완해야 할 점은 무엇이라고 보나요?",
  "answer_strategy": "국회 지적사항을 근거로 삼되, 기관 비판이 아니라 개선 방향과 지원 직무의 기여로 전환합니다.",
  "answer_points": [],
  "sample_answer_sentence": "",
  "evidence": [],
  "caution": "",
  "safe_framing": ""
}
```

근거가 없는 내용은 답변 본문으로 확정하지 않고 `verification_notes`에 남긴다.

## CLI 예시

live ALIO 조회:

```bash
python -m kr_gov_job_mcp.server --call-tool prepare_institution_interview --input '{"institution_name":"(재)한국보건의료정보원","target_role":"보건의료정보","year":2026,"focus_areas":["지원동기","기관이해","개선과제","입사후포부"]}'
```

수동 evidence 기반 호출:

```bash
python -m kr_gov_job_mcp.server --call-tool prepare_institution_interview --input '{"institution_name":"한국인터넷진흥원","target_role":"정보통신","year":2026,"fetch_live_alio":false,"focus_areas":["지원동기"],"evidence":[{"title":"ALIO 주요사업","source_type":"alio_disclosure","excerpt":"디지털 신뢰 기반 조성 사업을 주요사업으로 제시했습니다.","fields":{"source_type":"major_business","alio_item_no":"40"}}],"signals":[{"category":"business_direction","title":"주요사업","summary":"디지털 신뢰 기반 조성 사업을 주요사업으로 제시했습니다.","evidence":[{"title":"ALIO 주요사업","source_type":"alio_disclosure","excerpt":"디지털 신뢰 기반 조성 사업을 주요사업으로 제시했습니다.","fields":{"source_type":"major_business","alio_item_no":"40"}}]}]}'
```

## 면접 카드 연결 기준

- 주요사업: 지원동기, 기관 이해, 입사 후 포부
- 연구/정책 자료: 기관 현안 이해, 직무 관심도, 전문성 어필
- 국회 지적사항: 개선과제

국회 지적사항은 면접에서 위험하게 들릴 수 있으므로 `safe_framing`과 `caution`을 반드시 포함한다.
