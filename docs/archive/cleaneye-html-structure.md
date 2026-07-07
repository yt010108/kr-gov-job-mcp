# Cleaneye HTML 구조 조사

현재 MVP 범위 밖의 미래 설계 문서입니다. Job-ALIO 검색, 상세 조회, 준비 리포트 흐름이 안정된 뒤 Cleaneye parser 단계에서 다시 사용합니다.

조사일: 2026-07-07 KST

## 목적

Cleaneye 공시 raw HTML을 필드 단위로 파싱하기 전에 지방공기업과 지방출자출연기관의 실제
본문 구조를 비교한다. 이 문서는 공통 table parser로 처리할 수 있는 영역과 Cleaneye 전용
전처리/항목별 parser가 필요한 영역을 나눈다.

조사 기준 샘플은 `data/raw_samples/cleaneye/...` 아래 로컬 raw sample이다. Git에는 raw HTML을
커밋하지 않고 구조 관찰 결과만 남긴다.

## 샘플 범위

| 기관 | 구분 | ID 필드 | ID | 수집 항목 |
| --- | --- | --- | --- | --- |
| 서울교통공사 | 지방공기업 | `entId` | `2017000008` | 일반현황, 경영평가등급, 부채규모, 사업보고서, 신규투자사업 |
| 서울시립교향악단 | 지방출자출연기관 | `insttCode` | `B000261` | 일반현황, 경영성과, 재무현황, 재무·부채관리 계획, 외부기관 감사결과 |

## 공통 HTML wrapper

Cleaneye 본문은 항목별 action URL에 POST form을 보내면 전체 HTML 문서로 내려온다. 실제 데이터는
`#contents`, `#ceBoxContents`, `#ceContents`, `typeATable` 아래에 있지만, 응답에는 head script,
frame 제어 코드, excel download JavaScript, 숨겨진 file form도 함께 포함된다.

공통으로 관찰한 패턴:

- 페이지 제목은 `<title>`과 `h3`, `h4`에 중복된다.
- 실제 데이터 표는 `div.defaultTable` 아래 `<table>`로 내려오며 `caption`이 있는 경우가 많다.
- 본문형 설명은 `div.ceTxBox`, `textarea`, 이미지 링크, 일반 anchor가 섞인다.
- `h6`에는 작성기준, 입력 대상기관, 공시 담당자 같은 안내/메타 텍스트가 들어간다.
- 다운로드 링크는 실제 URL이 아니라 `javascript:toExcel(...)`, `javascript:fn_FileDown(...)`,
  `javascript:fn_detail(...)` 형태가 많다.

parser 전처리 권장 범위:

1. head/script/form wrapper를 제거하고 `#ceContents` 내부만 대상으로 삼는다.
2. `h3`, `h4`, `h5`, `caption`을 provenance와 섹션 식별자로 보존한다.
3. `h6` 작성기준과 공시 담당자 표는 기본 분석 필드가 아니라 debug/provenance로 분리한다.
4. `javascript:` 링크는 원문 문자열을 보존하고, 함수별 인자 파싱은 Cleaneye 전용 단계에서 처리한다.

## 지방공기업 항목 구조

### 일반현황

샘플: `2017000008-general_status-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `1_1`, `commStatus`, `/user/empCommStatus.do` |
| table | 2개 |
| caption | 기관소개, 공시책임자 |
| section heading | 기관소개, 기관설립조례, 주요 기능 및 역할, 기관 연혁, 경영목표 및 전략, 기관장 소개, 조직 기구도, 소재지, 공시책임자 |
| link | 로고/전략/조직/소재지 이미지, 홈페이지 URL |

바로 구현 가능한 필드:

- `institution_name`
- `established_date`
- `address`
- `homepage_url`
- `chief_name`
- `contact`
- `institution_summary`
- `functions_and_roles`
- `history_text`
- `strategy_image_url`
- `organization_image_url`
- `location_image_url`

보류할 필드:

- 기관소개의 장문 `textarea`와 `ceTxBox`는 text block으로 먼저 보존하고, 요약/키워드 추출은 분석 단계로 넘긴다.
- 이미지 파일은 stable URL 후보이지만 파일 저장/다운로드 정책이 필요하다.

### 경영평가등급

샘플: `2017000008-management_evaluation-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `10_1`, `mngEvaluGrade`, `/user/empMngEvaluGrade.do` |
| table | 2개 |
| 주요 row | `평가(실적)연도`, `평가등급` |
| link | `javascript:toExcel()`, 입력 대상기관 확인 |
| caption | 없음 |

바로 구현 가능한 필드:

- `evaluation_years`
- `performance_years`
- `evaluation_grades`

보류할 필드:

- 입력 대상기관 여부는 별도 팝업/목록 JavaScript를 추가 확인해야 한다.
- caption이 없는 표도 있으므로 첫 번째 row header를 fallback table name으로 써야 한다.

### 부채규모

샘플: `2017000008-debt_scale-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `7_1`, `debtScale`, `/user/empDebtScale.do` |
| table | 2개 |
| caption | 부채규모 |
| 주요 column | `구분`, 5개 연도 |
| 주요 row | 유동자산, 비유동자산, 자산합계, 유동부채, 비유동부채, 부채합계, 자본합계, 부채비율 |
| link | `javascript:toExcel()` |

바로 구현 가능한 필드:

- `yearly_assets`
- `yearly_liabilities`
- `yearly_equity`
- `debt_ratio`
- `debt_change_amount`
- `debt_change_rate`

보류할 필드:

- `rowspan`/`colspan`이 섞여 row cell 수가 6개 또는 7개로 달라진다. header carry-forward 처리가 필요하다.
- 금액 단위는 화면 text와 caption 밖 안내를 함께 확인해야 한다.

### 사업보고서

샘플: `2017000008-business_report-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `12_3`, `workReport`, `/user/empWorkReport.do` |
| table | 1개 |
| caption | 사업보고서 |
| 주요 column | 번호, 연도, 제목, 등록일자, 첨부, 조회수 |
| link | `javascript:fn_detail('...')` |

바로 구현 가능한 필드:

- `report_year`
- `title`
- `registered_date`
- `detail_key`
- `view_count`

보류할 필드:

- 목록의 제목이 `해당사항 없음`으로 반복될 수 있어 분석 신호로 바로 쓰기 어렵다.
- 상세 modal/page에서 실제 첨부나 본문이 따로 내려오는지 추가 확인이 필요하다.

### 신규투자사업

샘플: `2017000008-new_investment-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `6_19_4`, `newInvestBusi`, `/user/empNewInvestBusi.do` |
| table | 1개 |
| caption | 신규투자사업 |
| 주요 column | 번호, 사업실명제 등록번호, 사업명, 등록일자, 조회수 |
| row 상태 | 대상기관/해당사항 없음 계열의 단일 cell row 가능 |

바로 구현 가능한 필드:

- `project_registration_no`
- `project_name`
- `registered_date`
- `view_count`
- `not_applicable`

보류할 필드:

- 실제 사업 row가 있는 기관 샘플을 추가해야 상세 row 구조를 확정할 수 있다.

## 지방출자출연기관 항목 구조

### 일반현황

샘플: `B000261-general_status-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `10`, `iptSuCommStatus`, `/user/iptSuCommStatus.do` |
| table | 2개 |
| caption | 일반현황, 공시감독자 |
| 주요 row | 기관명/주소, 홈페이지, 기관소개, 설립근거, 연혁, 관계기관, 주요기능, 기관장명/사장명 |
| link | `javascript:fn_UrlLink('www.seoulphil.or.kr')` |

바로 구현 가능한 필드:

- `institution_name`
- `address`
- `homepage_url`
- `institution_summary`
- `legal_basis`
- `history_text`
- `related_agency`
- `main_functions`
- `chief_name`

보류할 필드:

- 홈페이지는 일반 `href`가 아니라 `fn_UrlLink` 인자라 Cleaneye 전용 JavaScript 인자 parser가 필요하다.
- 지방공기업 일반현황보다 한 표 안에 더 많은 row가 모여 있어 섹션 heading 기반 parser만으로는 부족하다.

### 경영성과

샘플: `B000261-management_result-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `45`, `iptMngResult`, `/user/iptMngResult.do` |
| table | 4개 |
| caption | 경영실적평가, 경영평가 실적보고서, 기관장 성과계약서 |
| link | `javascript:toExcel()`, `javascript:fn_FileDown(...)` |

바로 구현 가능한 필드:

- `evaluation_years`
- `evaluation_grades`
- `performance_report_attachments`
- `chief_performance_contract_attachments`

보류할 필드:

- `fn_FileDown` 인자에서 저장 파일명, 표시 파일명, attachment path, category를 안전하게 분리해야 한다.
- 동일 회계연도에 파일이 여러 개 있을 수 있어 attachment list는 복수 값을 허용해야 한다.

### 재무현황

샘플: `B000261-finance-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `50_30`, `iptFinance`, `/user/iptFinance.do` |
| table | 4개 |
| caption | 요약재무상태표, 요약포괄손익계산서, 재무결산 |
| 주요 column | `구분`, 5개 연도 |
| link | table별 `toExcel`, 재무결산 `fn_FileDown` |

바로 구현 가능한 필드:

- `yearly_assets`
- `yearly_liabilities`
- `yearly_equity`
- `debt_ratio`
- `operating_revenue`
- `operating_expense`
- `net_income`
- `financial_statement_attachments`

보류할 필드:

- 요약재무상태표와 요약포괄손익계산서가 같은 row/column 형식을 공유하지만 caption별 metric set이 다르다.
- 첨부는 연도별로 `fn_FileDown` 인자와 table cell을 매칭해야 한다.

### 재무·부채관리 계획

샘플: `B000261-finance_debt_plan-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `50_70`, `iptFincLbltMngGoal`, `/user/iptFincLbltMngGoal.do` |
| table | 2개 |
| caption | 재무관리 목표, 부채관리 목표 |
| row 상태 | `대상기관 아님` 단일 cell row |
| link | `toExcel`, 입력 대상기관 확인 |

바로 구현 가능한 필드:

- `not_applicable`
- `target_status_text`

보류할 필드:

- 대상기관인 샘플에서 자산/부채/자본/부채비율 목표 row 구조를 추가 확인해야 한다.

### 외부기관 감사결과

샘플: `B000261-external_audit-html.json`

| 관찰 항목 | 내용 |
| --- | --- |
| item | `60_20`, `iptSuExtInspectResult`, `/user/iptSuExtInspectResult.do` |
| table | 1개 |
| caption | 외부기관 감사결과 |
| 주요 column | 번호, 감사주체, 감사기간, 주요지적사항, 등록일자, 첨부파일, 조회수 |
| link | `javascript:fn_detail(...)`, `javascript:fn_FileDown(...)` |

바로 구현 가능한 필드:

- `audit_subject`
- `audit_period`
- `finding_summary`
- `registered_date`
- `attachment_metadata`
- `view_count`

보류할 필드:

- 조치결과는 caption에는 없고 상세 페이지에서 확인해야 할 수 있다.
- 감사 상세 본문은 `fn_detail` 대상 구조를 추가 수집하기 전까지 목록 row 수준으로 둔다.

## entId와 insttCode 차이

| 구분 | 지방공기업 | 지방출자출연기관 |
| --- | --- | --- |
| 기관 ID | `entId` | `insttCode` |
| 검색 endpoint | `/user/selectNewEntSearchList.do` | `/user/selectIptEntSearchList.do` |
| 항목 트리 endpoint | `/user/selectNewItemEntList.do` | `/user/selectIptItemEntList.do` |
| 항목 메타 endpoint | `/user/selectItemIdCheck.do` | `/user/selectIptItemIdCheck.do` |
| 본문 POST form | `entId`, `entName`, `entKind`, `itemId` | `entId` key에 `insttCode` 값을 넣어 POST, `entName`, `entKind`, `itemId` |
| 공시 기준연도 | 지방공기업 기본 context `fixedYear=2025` | 출자출연 기본 context `fixedYear=2024` |

collector 내부에서는 둘 다 `institution.id`로 보존하되, `kind`를 반드시 함께 저장해야 한다.
분석 스키마로 넘길 때도 `cleaneye_id`와 `cleaneye_kind`를 같이 보존한다.

## 공통 파서와 전용 파서 판단

공통 table parser로 처리 가능한 것:

- table/caption/thead/tbody/tr/th/td 추출
- `scope`, `headers`, `rowspan`, `colspan` attribute 보존
- 첫 row를 column header로 보는 단순 목록형 table
- `구분` + 연도 column으로 구성된 matrix table
- 단일 cell `대상기관 아님` row 감지

Cleaneye 전용 parser가 필요한 것:

- `#ceContents` 본문 추출과 작성기준/공시담당자 분리
- `javascript:fn_FileDown(...)` 인자 파싱
- `javascript:fn_detail(...)` 상세 key 파싱
- `javascript:fn_UrlLink(...)` URL 보정
- image endpoint와 `download` filename 매핑
- caption이 없는 table의 fallback 식별
- 입력 대상기관 확인 팝업/목록 판단

ALIO와 공유 가능한 범위는 낮은 수준의 HTML table extractor까지다. Cleaneye는 wrapper, JavaScript
download, 대상기관 아님 row, 작성기준 block 때문에 source-specific normalization layer가 필요하다.

## 기관 분석 입력 후보

| 후보 | 출처 | 분석 용도 |
| --- | --- | --- |
| 기관명, 설립일, 주소, 홈페이지 | 일반현황 | 기관 identity/provenance |
| 기관소개, 주요기능, 연혁, 경영목표 | 일반현황 | 기관 소개 및 사업 방향 후보 |
| 경영평가등급 | 경영평가등급, 경영성과 | 기관 평가 signal |
| 부채총계, 자본합계, 부채비율, 부채증감 | 부채규모, 재무현황 | 재무 안정성 signal |
| 영업수익, 영업비용, 당기순이익 | 재무현황 | 수익/비용 구조 signal |
| 사업보고서 목록 | 사업보고서 | 주요사업 근거 후보 |
| 신규투자사업 목록 | 신규투자사업 | 향후 투자/사업 방향 후보 |
| 외부기관 감사 주요지적사항 | 외부기관 감사결과 | 개선 과제 signal |

단순 표시/provenance로 우선 둘 것:

- 공시 담당자/감독자/확인자 연락처
- 작성기준 text
- 조회수
- excel download JavaScript
- 입력 대상기관 확인 링크

## Parser 구현 범위

1. Cleaneye HTML 전처리
   - `#ceContents` 내부 추출
   - `h3/h4/h5/caption` section metadata 보존
   - `h6` 작성기준 block 분리
2. 공통 table extractor
   - caption, header row, body row, row/col span attribute 추출
   - matrix table과 list table 구분
   - 단일 cell not-applicable row 감지
3. Cleaneye link parser
   - `fn_FileDown` 인자 분리
   - `fn_detail` key 분리
   - `fn_UrlLink` URL 보정
   - image endpoint와 download filename 보존
4. 항목별 mapper
   - 일반현황 key-value table mapper
   - 평가/재무 matrix mapper
   - 사업보고서/감사결과 list mapper

보류:

- 사업보고서와 감사결과의 상세 page/modal 구조
- 대상기관 확인 팝업 endpoint
- 첨부파일 다운로드 실행 및 파일 hash/provenance 정책
