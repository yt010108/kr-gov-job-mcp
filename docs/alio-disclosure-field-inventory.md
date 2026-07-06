# ALIO 경영공시 필드 조사

조사일: 2026-07-07 KST

# 확인한 접근 경로

| 목적 | 경로 | 방식 | 확인한 주요 파라미터 |
| --- | --- | --- | --- |
| 기관 검색 | `/organ/findOrganApbaList.json` | POST JSON | `apbaNa`, `apba_id`, `pageNo` |
| 기관 상세 | `/organ/findOrganApbaDtl.json` | GET | `apbaId` |
| 국회 지적사항 | `/occasional/findPointList.json` | GET | `reportFormNo=B1210`, `type=apbaNa`, `word`, `pageNo`, `countPerPage` |
| 감사원/주무부처 지적사항 | `/occasional/findPointList.json` | GET | `reportFormNo=B1220`, `type=apbaNa`, `word`, `pageNo`, `countPerPage` |
| 일반현황 보고서 목록 | `/item/itemReportListSusi.json` | POST JSON | `apbaId`, `apbaType`, `reportFormRootNo=10105`, `pageNo` |
| 정기공시 보고서 목록 | `/organ/quarterlyReport.do` | GET HTML | `apbaId`, `nowQuarter=0` |
| 보고서 본문 | `/item/itemReportRight.do` | GET HTML | `disclosureNo` |
| 보고서 첨부파일 | `/item/itemReportFiles.json` | GET | `disclosureNo` |

정기공시 보고서 목록은 별도 JSON API가 아니라 `quarterlyReport.do` HTML 안의
`reportList: JSON.parse(...)`에 포함된다. 이 중 `reportFormNo=31501`이 주요사업이다.

# 분석에 바로 쓸 수 있는 필드

기관 검색/상세에서 안정적으로 확인한 필드:

| 정규화 필드 | ALIO 원본 필드 | 비고 |
| --- | --- | --- |
| `id` | `apbaId` | ALIO 기관 코드 |
| `name` | `apbaNa`, `dcsrApbaNa` | 기관명 |
| `type_name` | `typeNa`, `apbaTypeNa` | 기관 유형명 |
| `ministry_name` | `jidtNa`, `jidtDptmNa`, `cd` | 주무부처명 |
| `ceo` | `ceo` | 기관장 |
| `established_date` | `fdate` | `YYYYMMDD`를 ISO 날짜로 변환 가능 |
| `region` | `addrCd` | 광역 지역 |
| `address` | `addr1` | 주소 |
| `homepage_url` | `homepage` | 스킴이 없는 값이 많아 `https://` 보정 |
| `main_business` | `contents` | `&cr;` 구분자를 줄바꿈으로 변환 |
| `submission_no` | `submissionNo` | 보고서/이미지 경로 연결에 사용 |

국회/감사 지적사항에서 안정적으로 확인한 필드:

| 정규화 필드 | ALIO 원본 필드 | 비고 |
| --- | --- | --- |
| `id` | `submissionNo` | 상세 페이지 `seq`로 사용 |
| `report_form_no` | `reportFormNo` | `B1210`, `B1220` |
| `institution_id` | `apbaId` | 기관 코드 |
| `institution_name` | `apbaNa`, `pname` | 기관명 |
| `title` | `rtitle` | 일부 값에 줄바꿈/HTML 포함 가능 |
| `registered_date` | `idate` | 표시용 날짜 |
| `action_plan_date` | `pdate`, `actnPlanRegYmd` | 조치계획 등록일 |
| `action_result_date` | `rdate`, `actnResRegYmd` | 조치실행 등록일 |
| `enforcement_start_date` | `enfcBgngYmd` | 시행기간 시작 |
| `enforcement_end_date` | `enfcEndYmd` | 시행기간 종료 |
| `attachments` | `filedata1`~`filedata3` | `**` 구분 문자열로 파일명/저장경로 추출 가능 |

# 주의가 필요한 필드와 결측 패턴

| 영역 | 관찰 내용 |
| --- | --- |
| 기관 코드 검색 | `apbaId` 직접 상세 조회는 가능하다. 목록 검색은 화면에 따라 `apba_id`를 사용한다. |
| 기관 일반현황 | `findOrganApbaDtl.json`만으로 기본 필드는 충분하지만, 공시 원문 보고서 본문은 HTML 테이블이다. |
| 주요사업 | 기관 상세의 `contents`에서 요약 텍스트를 얻을 수 있고, 정기공시 `31501` 보고서에서 원문 HTML/PDF 첨부를 얻을 수 있다. |
| 보고서 구조화 | `itemReportRight.do`는 HTML 조각을 반환한다. 표 단위 정규화는 별도 파서가 필요하다. |
| 보고서 결측 | `quarterlyReport.do`의 `reportList` 안에 `disclosureNo=null`인 항목이 있다. 해당 항목은 원문 본문/첨부 조회가 불가능하다. |
| 첨부파일 크기 | `itemReportFiles.json`의 `fileSize`가 `0`으로 내려오는 사례가 있다. 존재 여부 판단에는 파일 목록 자체를 우선 사용해야 한다. |
| 숫자/금액 | 기관 상세의 `fmoney`는 `null`인 경우가 있다. 현재 분석 필드에서는 제외한다. |

# 샘플 기관 관찰

아래 값은 2026-07-07에 ALIO 라이브 엔드포인트로 확인한 1페이지 기준 관찰치다.

| 기관 | ALIO 코드 | 기관 유형 | 주무부처 | `contents` 길이 | 국회 지적사항 | 감사/평가 지적사항 |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 한국인터넷진흥원 | `C0399` | 준정부기관(위탁집행형) | 과학기술정보통신부 | 216 | 78 | 5 |
| 창업진흥원 | `C0451` | 기타공공기관 | 중소벤처기업부 | 600 | 5 | 9 |
| 한국전력공사 | `C0247` | 공기업(시장형) | 기후에너지환경부 | 191 | 48 | 22 |

# 구현 메모

`AlioDisclosureClient`는 확인된 공개 ALIO 경로만 감싼다.

`AlioDisclosureCollector`는 `institution_name` 또는 `institution_code` 기준으로 다음 raw sample을
`data/raw_samples/alio_disclosure/...` 아래에 저장한다. 이 디렉터리는 `.gitignore` 대상이다.

수집되는 raw sample:

| sample | 내용 |
| --- | --- |
| institution search | 기관 목록 검색 원본 JSON |
| institution detail | 기관 상세 원본 JSON |
| national assembly points | 국회 지적사항 원본 JSON |
| audit points | 감사원/주무부처 지적사항 원본 JSON |
| general status reports | 일반현황 보고서 목록 원본 JSON |
| general status files/html | 일반현황 첨부파일 목록과 본문 HTML |
| quarterly report list | 정기공시 HTML과 추출한 `reportList` |
| main business files/html | 주요사업 첨부파일 목록과 본문 HTML |
| source links | 기관 상세/일반현황/주요사업/지적사항 원본 링크 |
