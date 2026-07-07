# Raw Data Inventory

조사일: 2026-07-07 KST

## 목적

최종 ERD나 분석 스키마를 먼저 확정하지 않고, 실제 수집 데이터의 원본 필드와 결측 패턴을
관찰하기 위한 inventory다. 이 문서는 raw sample 저장 기준, 원본 유형, 소스별 안정 필드,
자주 비는 필드, 소스 전용 필드, 코드값/표시명 분리 기준을 정리한다.

구조화 예시는 `examples/raw-data-inventory.json`에 둔다. 이 예시는 최종 분석 스키마가 아니라
필드 관찰표다.

## Raw Sample 유형

| raw_type | 의미 | 예시 |
| --- | --- | --- |
| `list` | 검색/목록 응답 | Job-ALIO 공고 목록, Cleaneye 기관 검색 |
| `detail` | 단일 상세 JSON | Job-ALIO 공고 상세 |
| `attachment` | 첨부파일 메타데이터 또는 다운로드 후보 | 공고문, 직무기술서 |
| `html` | 원문 HTML | Cleaneye/ALIO 공시 본문 |
| `pdf_text` | PDF/HWP 등 문서에서 추출한 텍스트 | 직무기술서 텍스트 |
| `api_response` | API 원본 응답 | 공개 API 또는 Ajax JSON |
| `metadata` | 수집 과정에서 만든 관찰 메타데이터 | 최종 URL, 링크 후보, item metadata |
| `other` | 위 유형으로 분류하기 어려운 원본 | 임시 조사 산출물 |

## 소스별 필드 관찰표

| source key | 설명 |
| --- | --- |
| `job_alio` | 잡알리오 채용공고 |
| `alio_disclosure` | ALIO 경영공시 |
| `cleaneye` | Cleaneye 지방공공기관 공시 |

### Job-ALIO

| 구분 | 필드 |
| --- | --- |
| 안정 필드 | `recrutPblntSn`, `instNm`, `pblntInstCd`, `recrutPbancTtl`, `pbancBgngYmd`, `pbancEndYmd` |
| NCS 필드 | `ncsCdLst`, `ncsCdNmLst` |
| 자주 비는 필드 | `prefCn`, `srcUrl`, `files`, `steps` |
| 전용 필드 | `replmprYn`, `recrutSeNm`, `hireTypeNmLst`, `workRgnNmLst` |
| 임시 정규화 후보 | `id`, `institution_name`, `title`, `start_date`, `end_date`, `ncs_codes`, `attachments` |

코드와 표시명은 `ncsCdLst`/`ncsCdNmLst`, `pblntInstCd`/`instNm`처럼 분리해 보존한다.

### ALIO 경영공시

| 구분 | 필드 |
| --- | --- |
| 안정 필드 | `apbaId`, 기관명, 공시 item ID/name, source URL |
| 자주 비는 필드 | 항목별 `contents`, 첨부 URL, 표 row |
| 전용 필드 | 공시 항목 코드, 기준연도, 반기/분기 기준 |
| 임시 정규화 후보 | `institution_id`, `disclosure_item`, `body_html`, `body_text_preview` |

ALIO는 중앙 공공기관 중심이다. 기관 ID와 항목 ID를 각각 보존하고, HTML/표 구조는 분석 전에
별도 파서로 확인한다.

### Cleaneye

| 구분 | 필드 |
| --- | --- |
| 안정 필드 | `entId`, `insttCode`, `entName`, `insttNm`, `entKind`, `itemNo`, `itemId`, `itemNm` |
| 자주 비는 필드 | `portalActionUrl`, `useYn`, 항목별 HTML table row |
| 전용 필드 | 지방공기업/출자출연 구분, 기준연도 변수 |
| 임시 정규화 후보 | `institution_id`, `institution_kind`, `kind_code`, `disclosure_item`, `body_html` |

지방공기업은 `entId`, 지방출자출연은 `insttCode`를 쓴다. 두 ID를 같은 의미로 합치지 않는다.

## 코드값과 표시명 분리 원칙

| 소스 | 코드 | 표시명 |
| --- | --- | --- |
| Job-ALIO | `ncsCdLst` | `ncsCdNmLst` |
| Job-ALIO | `pblntInstCd` | `instNm` |
| ALIO | `apbaId` | 기관명 |
| ALIO | item ID | item name |
| Cleaneye | `entId` | `entName` |
| Cleaneye | `insttCode` | `insttNm` |
| Cleaneye | `itemNo` | `itemNm` |

코드와 표시명 길이가 맞지 않거나 누락되면 임의 보정하지 않고 inventory에 결측으로 남긴다.

## 결측 기록 기준

결측은 다음처럼 구분한다.

| 구분 | 의미 |
| --- | --- |
| 항상 있는 필드 | 목록/상세 대부분에서 관찰되는 식별자와 제목 |
| 자주 비는 필드 | 소스 구조상 선택적이거나 기관별로 달라지는 값 |
| 소스 전용 필드 | 해당 출처 안에서만 의미가 있는 코드나 상태값 |
| 파생 후보 | 분석을 위해 임시로 만든 정규화 필드 |

파생 후보는 최종 스키마가 아니다. raw sample과 field inventory를 더 쌓은 뒤 ERD와 분석
스키마로 승격한다.
