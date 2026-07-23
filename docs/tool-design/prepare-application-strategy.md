# 11. prepare_application_strategy

## 구현 상태

MCP tool 구현 완료. 기존 resolver, Job-ALIO 검색, 공고별 적합도/NCS 분석, 기관 분석,
면접 카드 도구를 호출 순서와 실패 경계만 담당하는 orchestration 계층으로 조합한다.

## 입력

| field | 설명 |
| --- | --- |
| `institution_name` | 지원할 기관명 또는 약칭. 필수 |
| `target_role` | 자연어 목표 직무. 필수 |
| `region` | 선택적인 근무지역명 |
| `known_skills` | 보유 기술·자격·경험 |
| `preparation_notes` | 준비 상태에 대한 추가 메모 |
| `ongoing_only` | 현재 접수 중 공고만 검색할지 여부 |
| `limit` | 검색하고 분석할 공고 후보 수. 최대 5 |
| `include_*` | NCS, 기관 분석, 면접 카드 포함 여부 |
| `fetch_live_alio` | 기관 분석의 ALIO 실시간 조회 여부 |

## 출력

- 기관 코드와 NCS 코드 해석 결과
- `job_candidates`와 검토 대상 `recommended_job_ids`
- 공고별 `fit_report`와 NCS/KSA 결과
- 공통 기관 전략·개선 과제·면접 카드
- `evidence_links`, `verification_notes`, `warnings`
- 0건 검색의 원래 `diagnostics`

## 처리 원칙

- 기관 코드와 NCS 코드가 각각 하나로 확정된 경우에만 공고 검색을 실행한다.
- 여러 공고는 모두 후보로 유지하고 하나를 최종 선택했다고 표현하지 않는다.
- 하위 도구 하나가 실패해도 이미 수집한 공고와 분석 결과는 유지한다.
- 하위 결과의 원문 링크와 검증 필요 사항을 삭제하지 않는다.
