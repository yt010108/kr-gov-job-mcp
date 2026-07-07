# ALIO 경영공시 필드 조사

조사일: 2026-07-07 KST

기준 페이지:
`https://www.alio.go.kr/organ/organDisclosureDtl.do?apbaId=C0399&pageNo=1&apba_id=C0399`

## 확인한 수집 범위

기관 상세 페이지의 항목별 보고서 표에서 `openItemReport(reportNo, isFixed)` 값을 직접 확인했다.
현재 수집기는 공공기관 지원 준비에 바로 쓰는 항목만 대상으로 한다.

| 항목번호 | 항목명 | ALIO 내부 번호 | 유형 | 수집 여부 |
| --- | --- | --- | --- | --- |
| 6-2 | 직원 채용정보 | `B1020` | 수시 게시판 | 수집 |
| 40 | 주요사업 | `31501` | 정기 보고서 | 수집 |
| 47-1 | 국회지적사항 | `B1210` | 수시 게시판 | 수집 |
| 47-2 | 감사원 지적사항 | 제외 | 수시 게시판 | 제외 |
| 47-3 | 주무부처 지적사항 | 제외 | 수시 게시판 | 제외 |
| 49-1 | 입찰공고 | `B1030` | 수시 게시판 | 수집 |
| 49-2 | 수의계약 | `7030` | 정기 보고서 | 수집 |
| 50-1 | 자체 연구 보고서 | `B1040` | 수시 게시판 | 수집 |
| 50-2 | 외부용역 연구 보고서 | `B1260` | 수시 게시판 | 수집 |

47-2와 47-3은 사용자가 제외하기로 한 감사원/주무부처 지적사항이라 수집하지 않는다.

## 접근 경로

| 목적 | 경로 | 방식 | 주요 파라미터 |
| --- | --- | --- | --- |
| 기관 검색 | `/organ/findOrganApbaList.json` | POST JSON | `apbaNa`, `apba_id`, `pageNo` |
| 기관 상세 | `/organ/findOrganApbaDtl.json` | GET | `apbaId` |
| 항목별 보고서 화면 | `/item/itemOrganList.do` | GET HTML | `apbaId`, `reportFormRootNo` |
| 수시 항목 목록 | `/item/itemReportListSusi.json` | POST JSON | `pageNo`, `apbaId`, `apbaType`, `reportFormRootNo`, `search_flag` |
| 정기 항목 목록 | `/item/itemOrganListJung.json` | POST JSON | `apbaId`, `reportFormRootNo`, `quart` |
| 수시 게시판 상세 | `/item/itemBoard{reportFormNo}.do` | GET HTML | `disclosureNo`, `apbaId`, `reportFormNo`, `table_name`, `idx_name`, `idx` |
| 정기 보고서 본문 | `/item/itemReportRight.do` | GET HTML | `disclosureNo` |
| 정기 보고서 첨부파일 | `/item/itemReportFiles.json` | GET | `disclosureNo` |

ALIO 화면 기준으로 `isFixed=true`인 항목은 정기 보고서 경로를 쓰고,
`isFixed=false`인 항목은 수시 게시판 경로를 쓴다.

## 샘플 관찰

2026-07-07에 한국인터넷진흥원 `C0399` 기준으로 확인한 1페이지 응답이다.
3개 기관 확대 검증 결과는 `docs/alio-sample-validation.md`에 따로 기록한다.

| 항목 | 내부 번호 | 관찰 결과 |
| --- | --- | --- |
| 직원 채용정보 | `B1020` | `itemReportListSusi.json`에서 총 54건, 첫 항목은 2026년 기간제 근로자 채용 공고 |
| 주요사업 | `31501` | `itemOrganListJung.json`에서 1건, PDF 첨부파일 목록 포함 |
| 국회지적사항 | `B1210` | `itemReportListSusi.json`에서 총 78건 |
| 입찰공고 | `B1030` | `itemReportListSusi.json`에서 총 4718건 |
| 수의계약 | `7030` | `itemOrganListJung.json`에서 여러 `7030x` 보고서가 묶여 내려옴 |
| 자체 연구 보고서 | `B1040` | 한국인터넷진흥원 기준 0건 |
| 외부용역 연구 보고서 | `B1260` | `itemReportListSusi.json`에서 총 53건 |

## 원본 샘플 저장 방식

수집기는 최종 분석 결과를 바로 만들지 않고, 먼저 원본 응답을 `data/raw_samples/alio_disclosure/...`
아래에 저장한다. 이 디렉터리는 `.gitignore` 대상이다.

| raw type | 저장 내용 |
| --- | --- |
| `list` | 기관 검색 결과, 항목별 보고서 목록 JSON |
| `detail` | 기관 상세 JSON |
| `html` | 수시 게시판 상세 HTML 또는 정기 보고서 본문 HTML |
| `attachment` | 정기 보고서 첨부파일 메타데이터 |
| `metadata` | 원본 화면 링크와 항목번호 매핑 |

HTML raw 저장은 파서와 ERD를 추측으로 만들지 않기 위한 개발용 근거다.
수시 게시판 항목은 별도 첨부파일 API가 비어 있는 경우가 많아, 목록 JSON과 상세 HTML을 먼저 보존한다.
정기 보고서 항목은 `itemReportFiles.json`에서 첨부파일 목록을 함께 보존한다.

## 분석에 바로 쓸 수 있는 필드

| 정규화 필드 | ALIO 원본 필드 | 비고 |
| --- | --- | --- |
| `id` | `apbaId` | ALIO 기관 코드 |
| `name` | `apbaNa`, `dcsrApbaNa` | 기관명 |
| `type_name` | `typeNa`, `apbaTypeNa` | 기관 유형 |
| `ministry_name` | `jidtNa`, `jidtDptmNa`, `cd` | 주무부처명 |
| `homepage_url` | `homepage` | `https://` 없는 값 보정 |
| `main_business` | `contents` | 기관 상세의 주요사업 요약 |
| `disclosure_no` | `disclosureNo` | 보고서 상세 조회 키 |
| `report_form_no` | `reportFormNo` | 실제 내부 보고서 번호 |
| `title` | `title`, `rtitle` | 항목 제목 |
| `disclosed_date` | `idate` | 공시일 |
| `submission_no` | `submissionNo` | 제출 번호 |
| `source_url` | 조합 URL | 원문 상세 페이지 |

## 구현 메모

`AlioDisclosureClient.TARGET_ITEM_REPORTS`가 항목번호와 내부 번호를 관리한다.
기본 수집 대상은 `6-2`, `40`, `47-1`, `49-1`, `49-2`, `50-1`, `50-2`다.

쿼리에서 `item_numbers`를 넘기면 일부 항목만 수집할 수 있다.
`49`는 `49-1`, `49-2`로, `50`은 `50-1`, `50-2`로 확장된다.
`47`은 제외 결정을 반영해 `47-1`만 확장된다.
