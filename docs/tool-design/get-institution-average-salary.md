# 11. get_institution_average_salary

## 목적

`get_institution_average_salary`는 ALIO 정기공시의 `직원 평균보수` 항목에서
`1인당 평균 보수액`을 조회한다. 채용 공고 추천이나 연봉 협상 기준을 추정하지 않으며, ALIO에
공시된 기관 단위의 보수 값과 공시 근거만 반환한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `institution_name` | 조회할 공공기관명. 필수 |
| `alio_id` | ALIO 기관 코드(apbaId). 기관명 중복을 피할 때 사용 |
| `apba_id` | `alio_id` 별칭 |
| `year` | 조회할 평균보수 연도. 생략하면 가장 최근 결산값 선택 |

## 데이터 기준

- ALIO 정기공시 `직원 평균보수` 항목(`reportFormRootNo=2060`)의 `1인당 평균 보수액` 행만 읽는다.
- 금액 단위는 ALIO 표의 천원 단위를 원화(`amount_krw`)와 천원(`amount_thousand_krw`)으로 함께 반환한다.
- 기본 선택값은 가장 최근 `결산` 열이다. 당해 `예산` 열은 결산값과 구분해 `basis: "예산"`으로 반환한다.
- 요청한 연도의 값이 없으면 다른 연도로 대체하지 않고 `average_salary: null`과 경고를 반환한다.

## 출력 주요 필드

| field | 설명 |
| --- | --- |
| `average_salary` | 선택된 평균보수. 연도, 원화 금액, 천원 금액, 결산/예산 구분 포함 |
| `salary_history` | 같은 정기공시 표에서 추출한 연도별 평균보수 목록. 고용형태 구분이 있으면 함께 반환 |
| `report` | ALIO 공시 항목 번호, 공시번호, 원문 URL |
| `warnings` | 기관 미확인, 공시 없음, 표 형식 불일치, 요청 연도 부재 등 검증 필요 사항 |

## CLI 예시

```bash
python -m kr_gov_job_mcp.server --call-tool get_institution_average_salary --input '{"institution_name":"국민건강보험공단","alio_id":"C0026"}'
```
