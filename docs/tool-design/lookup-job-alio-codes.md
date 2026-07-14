# lookup_job_alio_codes

## 구현 상태

MCP tool 구현됨. Job-ALIO 검색 필터에 사용할 NCS 코드 후보와 기관명 후보를 조회한다.
NCS는 JOB-ALIO 화면에 노출된 25개 표준직무 코드를 제공한다.
기관명은 공식 Job-ALIO 채용정보 화면의 `select#id-select-pblntInstCd`에서 수집한
405개 코드/표시명 쌍을 패키지의 `job_alio_institution_codes.csv`로 제공한다.
기존 `alio_institution_codes.csv`는 일치하는 코드의 약칭과 정규화 이름을 보강하는 데만 사용한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `code_type` | 조회할 코드 유형. 현재 `institution`, `ncs` 지원 |
| `query` | 기관명, 기관 약칭, NCS명, 직무 키워드 또는 코드 |
| `limit` | 반환할 최대 후보 수. 기본 20, 최대 50 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 현재 값은 `job_alio` |
| `code_type` | 조회한 코드 유형 |
| `query` | 정규화 전 입력 query |
| `result_count` | 반환된 후보 수 |
| `codes[].code` | Job-ALIO 검색 필터에 바로 넣을 코드 |
| `codes[].name` | 코드 표시명 |
| `codes[].aliases` | 자연어 alias 후보 |
| `codes[].score` | 간단한 매칭 점수 |
| `codes[].source` | 후보 출처 |
| `warnings` | 0건 또는 제한 사항 |

## 처리 원칙

- 이 도구는 코드 후보 조회만 담당한다.
- 자연어 직무를 하나의 NCS 코드로 확정하고 검색 호출 인자를 만들려면 `resolve_ncs_code`를 사용한다.
- `search_public_jobs` 내부에서 자동 resolver를 실행하지 않는다.
- 후보가 여러 개면 LLM이나 사용자가 확인한 뒤 `search_public_jobs`에 코드를 전달한다.
- 코드 테이블과 필터 표시명 목록에 없는 후보는 빈 결과와 warning으로 안전하게 반환한다.

## 데이터 갱신 원칙

- 갱신할 때는 공식 `https://opendata.alio.go.kr/new/odaApiMng/recrutInquiryList.do`의
  `select#id-select-pblntInstCd`만 `html.parser`로 읽어 `institution_code,institution_name` CSV를 생성한다.
- 생성 전후에 코드 형식(`C` + 4자리 숫자), 코드 중복, 정규화 표시명 중복, 총 405개를 검증한다.
- 해산 표기와 표시명 변경은 CSV에서 임의로 정리하지 않고 공식 화면 원문을 그대로 반영한다. 기존 ALIO
  CSV의 이름이 달라도 코드가 같으면 공식 표시명을 유지하고 별칭만 결합한다.
