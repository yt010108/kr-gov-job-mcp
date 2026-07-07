# ALIO HTML 구조 조사

조사일: 2026-07-07 KST

## 목적

ALIO 항목별 보고서 raw HTML을 바로 파싱하기 전에, 수시 게시판과 정기 보고서의 실제 HTML
구조를 분리해 확인한다. 이 문서는 parser 구현 전에 바로 자동화할 수 있는 필드와 사람이
검토해야 하는 필드를 나눈다.

조사 기준 샘플은 `data/raw_samples/alio_disclosure/...` 아래 로컬 raw sample이다. Git에는
raw HTML을 커밋하지 않고, 구조 관찰 결과만 남긴다.

## 대상 항목

| 항목 | 내부 번호 | 유형 | 조사 결과 |
| --- | --- | --- | --- |
| 6-2 직원 채용정보 | `B1020` | 수시 게시판 | title, 공고기간, 채용분야 표, 첨부파일, 원문 URL 파싱 가능 |
| 40 주요사업 | `31501` | 정기 보고서 | 예산/결산 table과 첨부 링크 파싱 가능 |
| 47-1 국회지적사항 | `B1210` | 수시 게시판 | 제목, 시행기간, 지적사항/조치결과 text, 첨부 링크 파싱 가능 |
| 49-1 입찰공고 | `B1030` | 수시 게시판 | 제목, 등록일, 나라장터 링크, 첨부 링크 파싱 가능 |
| 49-2 수의계약 | `7030` | 정기 보고서 | 연도별 첨부 table 파싱 가능, 계약 행 데이터는 첨부 XLSX 안에 있음 |
| 50-1 자체 연구 보고서 | `B1040` | 수시 게시판 | 기관별 0건 가능, 빈 목록을 정상 상태로 처리 |
| 50-2 외부용역 연구 보고서 | `B1260` | 수시 게시판 | 제목, 발간일, 등록일, 계약방식, 연구기관, 첨부 링크 파싱 가능 |

47-2 감사원 지적사항과 47-3 주무부처 지적사항은 수집 범위에서 제외한다.

## 목록 JSON 구조

수시 게시판 항목은 `/item/itemReportListSusi.json`에서 목록을 받는다.

| 필드 | 의미 |
| --- | --- |
| `apbaId` | ALIO 기관 ID |
| `reportFormNo` | 내부 항목 번호 |
| `title` | 게시글 제목 |
| `idate` | 등록/공시일 |
| `submissionNo` | 제출 번호 |
| `disclosureNo` | 상세 조회 번호. `B1210`은 `0000000000000000`일 수 있음 |
| `idx` | 게시판 상세의 실제 row key |
| `idxName` | `IDX`, `BOARD_NO`, `SUBMISSION_NO` 등 |
| `tableName` | 상세 조회 대상 table |
| `reportGbn` | 게시판/보고서 구분 |

정기 보고서 항목은 `/item/itemOrganListJung.json`에서 목록을 받는다.

| 필드 | 의미 |
| --- | --- |
| `apbaId` | ALIO 기관 ID |
| `apbaNa` | 기관명 |
| `reportFormNo` | 실제 보고서 번호. `7030`은 `70301`처럼 세부 번호로 내려올 수 있음 |
| `reportParnFormNo` | 상위 보고서 번호 |
| `disclosureNo` | 정기 보고서 본문/첨부 조회 키 |
| `submissionNo` | 제출 번호 |
| `critYyyy` | 기준연도 |
| `critQuar`, `quartNa` | 기준 분기 |
| `files` | `fileNo@fileName` 문자열 목록 |

## 수시 게시판 HTML 구조

수시 게시판은 `/item/itemBoard{reportFormNo}.do` HTML이다. 전체 wrapper는 ALIO 공통 popup
HTML, Vue script, 닫기 버튼을 포함한다. 본문 parser는 전체 문서가 아니라 내용 영역 안의
label-value 블록, table, 링크만 대상으로 삼는 편이 안전하다.

### B1020 직원 채용정보

관찰 샘플: `2026070303204326-item-6-2-B1020-board-html.json`

| 구조 | 관찰 |
| --- | --- |
| 제목 | 본문 text와 목록 JSON `title` 모두 안정적 |
| 표 | table 2개, `caption`은 `전형단계별 채용정보` |
| 주요 label | 공고기간, 채용분야, 고용형태, 채용구분, 근무지, 채용인원, 우대조건 |
| 첨부 | `/download/download.json?fileNo=...` 링크, 공고문/입사지원서/직무기술서/기타 첨부파일 label |
| 원문 URL | 기관 접수 사이트 링크 |

바로 구현 가능한 필드:

- `title`
- `announcement_period`
- `recruitment_fields`
- `employment_type`
- `work_regions`
- `headcount`
- `attachments`
- `source_url`
- `selection_steps`

보류할 필드:

- 전형단계별 채용정보의 세부 row는 colspan과 반복 header가 많아 전용 parser가 필요하다.
- 선발인원/응시인원처럼 값이 비어 있는 row는 누락으로 보존한다.

### B1210 국회지적사항

관찰 샘플: `2025051210195031-item-47-1-B1210-board-html.json`

| 구조 | 관찰 |
| --- | --- |
| table | 없음 |
| 본문 | label-value text 중심 |
| 주요 label | 시행기간, 지적사항, 조치결과 |
| 첨부 | `javascript:void(0);` 링크에 파일명 text가 있음 |
| 상세 키 | 목록의 `disclosureNo`는 0값일 수 있어 `idx`/`submissionNo`가 더 안정적 |

바로 구현 가능한 필드:

- `title`
- `enforcement_period`
- `point_text`
- `action_result_text`
- `attachment_names`

보류할 필드:

- `javascript:void(0)` 첨부의 실제 download URL은 HTML만으로 확정하지 않는다.
- 같은 지적사항의 이력/수정본 관계는 `submissionNo` 기준으로 별도 확인이 필요하다.

### B1030 입찰공고

관찰 샘플: `2026070603205381-item-49-1-B1030-board-html.json`

| 구조 | 관찰 |
| --- | --- |
| table | 없음 |
| 주요 label | 제목, 입찰종료일, 등록일, 첨부파일 |
| 외부 링크 | 나라장터 상세 바로가기 |
| 첨부 | 나라장터 `UntyAtchFile/downloadFile.do` 링크 |

바로 구현 가능한 필드:

- `title`
- `registered_date`
- `bid_end_date`
- `g2b_source_url`
- `attachments`

보류할 필드:

- 입찰번호, 차수, 공고기관 같은 세부 필드는 URL query와 나라장터 상세를 추가 파싱해야 한다.

### B1040 자체 연구 보고서

KISA 샘플에서는 0건이었다. 빈 목록은 오류가 아니라 `total_count=0`, `reports=[]` 상태로
보존한다. parser는 행이 있을 때 B1260과 같은 수시 게시판 계열로 처리할 수 있는지 추가
샘플에서 확인한다.

### B1260 외부용역 연구 보고서

관찰 샘플: `2025071603027310-item-50-2-B1260-board-html.json`

| 구조 | 관찰 |
| --- | --- |
| table | 없음 |
| 주요 label | 발간일, 등록일, 계약방식, 연구기관 |
| 첨부 | `/download/download.json?fileNo=...` 링크 |
| 목록 JSON 보강 | `contractSum`, `contractWay`, `researchAgensy`, 공개 여부 필드가 목록에 있음 |

바로 구현 가능한 필드:

- `title`
- `published_date`
- `registered_date`
- `contract_method`
- `contract_amount`
- `research_agency`
- `attachments`

보류할 필드:

- 원문 공개/비공개 사유는 목록 JSON과 상세 text를 함께 봐야 한다.

## 정기 보고서 HTML 구조

정기 보고서는 `/item/itemReportRight.do?disclosureNo=...` HTML이다. 전체 문서가 ALIO report
HTML 조각에 가깝고, `<div id="doc-">`, `cover-title`, `SECTION-1`, `table.nb`, `table border=1`
패턴이 반복된다.

### 31501 주요사업

관찰 샘플: `2026041303151983-item-40-31501-html.json`

| 구조 | 관찰 |
| --- | --- |
| table | 12개 |
| 주요 데이터 table | `border="1"` table, header는 사업구분/연도별 결산/예산/비고 |
| 장식 table | `class="nb"` table은 제목, 기관명, 공백, 단위 표시 등 |
| 첨부 | `javascript:report_attach_down('파일명')` 링크 |
| footer | 기준일/제출일, 기관 공시 담당자 table |

바로 구현 가능한 필드:

- `business_name`
- `yearly_actuals`
- `current_year_budget`
- `attachment_name`
- `basis_date`
- `submission_date`

보류할 필드:

- 사업명 변동과 종료사업 row는 연도별 비교 로직 없이 분석 판단으로 승격하지 않는다.
- 담당자 table은 분석용이 아니라 provenance/debug 정보로만 둔다.

### 7030 수의계약

관찰 샘플: `2026041303153038-item-49-2-7030-html.json`

| 구조 | 관찰 |
| --- | --- |
| table | 11개 |
| 주요 데이터 table | 연도/첨부파일 table |
| 첨부 | `javascript:report_attach_down('파일명')` 링크 |
| 실제 계약 row | HTML 본문이 아니라 첨부 XLSX 안에 있음 |

바로 구현 가능한 필드:

- `year`
- `attachment_name`
- `basis_quarter`
- `submission_date`

보류할 필드:

- 계약명, 계약금액, 계약상대자 등은 XLSX 다운로드/파싱 이후에만 만든다.

## 목록 JSON보다 HTML에서 더 안정적인 필드

| 항목 | HTML에서 안정적인 필드 |
| --- | --- |
| B1020 | 첨부 구분, 직무기술서 파일명, 원문 URL, 전형단계별 채용정보 caption |
| B1210 | 지적사항 본문, 조치결과 본문, 첨부 파일명 |
| B1030 | 나라장터 바로가기 URL, 첨부 다운로드 URL |
| 31501 | 사업별 예산/결산 row, report attachment display name |
| 7030 | 연도별 첨부 row |
| B1260 | 발간일, 연구기관, 첨부 다운로드 URL |

## Parser 구현 범위

1. 공통 전처리
   - script/style/vue boilerplate 제거
   - ALIO popup wrapper 제거
   - 상대 download URL 절대 URL 보정
2. 수시 게시판 parser
   - label-value text 추출
   - `/download/download.json?fileNo=...`와 외부 첨부 링크 추출
   - 목록 JSON의 `idx`, `idxName`, `tableName`, `submissionNo`를 provenance로 보존
3. B1020 전용 parser
   - 첨부 label과 파일명 매핑
   - 원문 URL 추출
   - 채용분야/근무지/인원 등 table row 후보 추출
4. 정기 보고서 table parser
   - `class="nb"` 장식 table 제외
   - `border="1"` table의 header/body 행 추출
   - `report_attach_down(...)` 파일명 추출

보류:

- B1030 나라장터 상세 파싱
- B1210 `javascript:void(0)` 첨부의 실제 다운로드 URL 확정
- 7030 XLSX 내부 계약 row 파싱
- B1040 자체 연구 보고서의 기관별 HTML 변형 확정

## ERD/기관분석 입력 승격 후보

| 후보 | 출처 | 승격 대상 |
| --- | --- | --- |
| 채용공고 title/openDate/idate/source_url | B1020 목록+HTML | `JobPosting`, `EvidenceSource` |
| 직무기술서 첨부 | B1020 HTML | `JobPostingAttachment` |
| 주요사업 예산/결산 row | 31501 HTML | `DisclosureReport`, `InstitutionSignalCandidate` |
| 국회 지적사항/조치결과 | B1210 HTML | `DisclosureReport`, `InstitutionSignalCandidate` |
| 입찰공고 제목/나라장터 URL | B1030 HTML | `ContractInfo`, `EvidenceSource` |
| 수의계약 연도별 첨부 | 7030 HTML/files | `DisclosureAttachment` |
| 연구보고서 제목/기관/첨부 | B1260 HTML | `ResearchReport`, `EvidenceSource` |
