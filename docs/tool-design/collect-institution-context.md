# collect_institution_context

## 구현 상태

MVP MCP tool 구현됨. 기관명으로 ALIO 기관 정보를 조회하고, 기관 분석에 바로 넣을 수 있는
identity, evidence, signal 후보를 만든다. 현재는 ALIO 기관 정보와 ALIO에 등록된 홈페이지 URL
근거를 지원한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `institution_name` | 근거를 수집할 기관명 |
| `sources` | 수집 출처 목록. 현재 `alio`, `homepage` 지원 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 데이터 출처. 현재 값은 `institution_context` |
| `query` | 호출 입력 요약 |
| `institution_name` | 선택된 기관명 |
| `normalized_name` | 정규화된 기관명 |
| `alio_id` | ALIO 기관 코드 |
| `identity_candidates` | 기관 식별 후보 |
| `evidence` | 기관 분석에 연결할 원문 근거 후보 |
| `signals` | 근거가 연결된 기관 signal 후보 |
| `verification_notes` | 근거 부족 또는 확인 필요 사항 |
| `warnings` | 수집 중 발생한 경고 |

## 데이터 소스

- ALIO 기관 목록/상세 정보
- ALIO 기관 정보에 등록된 홈페이지 URL

## 처리 원칙

- ALIO 기관 검색 결과 첫 번째 후보를 선택한다.
- ALIO 상세의 주요사업 본문이 있으면 `alio_disclosure` evidence로 변환한다.
- 주요사업 evidence는 `business_direction` signal 후보로도 변환한다.
- ALIO 호출 실패나 결과 없음은 오류로 단정하지 않고 verification note와 warning으로 남긴다.
- 이 도구의 `evidence`와 `signals` 출력은 `analyze_institution_strategy`,
  `analyze_institution_weakness` 입력으로 그대로 넘길 수 있다.
