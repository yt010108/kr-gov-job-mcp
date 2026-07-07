# Cleaneye 지방공공기관 필드 조사

현재 MVP 범위 밖의 미래 설계 문서입니다. Job-ALIO 검색, 상세 조회, 준비 리포트 흐름이 안정된 뒤 Cleaneye 기관 분석 단계에서 다시 사용합니다.

조사일: 2026-07-07 KST

## 접근 경로

| 목적 | 지방공기업 경로 | 지방출자출연 경로 | 방식 |
| --- | --- | --- | --- |
| 기관별공시 홈 | `/user/itemGongsi.do` | `/user/iptItemGongsi.do` | GET HTML |
| 기관 검색 | `/user/selectNewEntSearchList.do` | `/user/selectIptEntSearchList.do` | POST form |
| 기관/분류 트리 | `/user/selectNewItemEntList.do` | `/user/selectIptItemEntList.do` | POST form |
| 항목 메타데이터 | `/user/selectItemIdCheck.do` | `/user/selectIptItemIdCheck.do` | POST form |
| 일반현황 본문 | `/user/empCommStatus.do` | `/user/iptSuCommStatus.do` | POST form, HTML |

Cleaneye 기관별공시는 iframe 기반 화면이다. 상단 프레임에서 기관과 항목을 고르고, 왼쪽
프레임에서 기관 트리를 선택한 뒤, 오른쪽 프레임에 항목별 HTML 본문이 로드된다.

## 기관 검색 필드

### 지방공기업

요청:

| 파라미터 | 의미 |
| --- | --- |
| `entName` | 기관명 검색어 |
| `entKind` | 기관 유형 코드. 비워두면 전체 |

응답 예시 필드:

| 정규화 필드 | 원본 필드 | 예시 |
| --- | --- | --- |
| `id` | `entId` | `2017000008` |
| `name` | `entName` | `서울교통공사` |
| `kind_code` | `entKind` | `006001` |
| `kind` | 고정값 | `local_public_enterprise` |

### 지방출자출연

요청:

| 파라미터 | 의미 |
| --- | --- |
| `insttNm` | 기관명 검색어 |
| `iptEntKind` | 출자/출연 분류 |
| `entGubun` | 기관 유형 코드 |

응답 예시 필드:

| 정규화 필드 | 원본 필드 | 예시 |
| --- | --- | --- |
| `id` | `insttCode` | `B000261` |
| `name` | `insttNm` | `서울시립교향악단` |
| `kind_code` | `entKind` | `012002` |
| `kind` | 고정값 | `local_invested_contributed` |

## 확인한 항목 후보

### 지방공기업

| 분석 후보 | itemNo | itemId | action |
| --- | --- | --- | --- |
| 일반현황 | `1_1` | `commStatus` | `/user/empCommStatus.do` |
| 경영평가등급 | `10_1` | `mngEvaluGrade` | `/user/empMngEvaluGrade.do` |
| 부채규모 | `7_1` | `debtScale` | `/user/empDebtScale.do` |
| 사업보고서 | `12_3` | `workReport` | `/user/empWorkReport.do` |
| 신규투자사업 | `6_19_4` | `newInvestBusi` | `/user/empNewInvestBusi.do` |

### 지방출자출연

| 분석 후보 | itemNo | itemId | action |
| --- | --- | --- | --- |
| 일반현황 | `10` | `iptSuCommStatus` | `/user/iptSuCommStatus.do` |
| 경영성과 | `45` | `iptMngResult` | `/user/iptMngResult.do` |
| 재무현황 | `50_30` | `iptFinance` | `/user/iptFinance.do` |
| 재무·부채관리 계획 | `50_70` | `iptFincLbltMngGoal` | `/user/iptFincLbltMngGoal.do` |
| 외부기관 감사결과 | `60_20` | `iptSuExtInspectResult` | `/user/iptSuExtInspectResult.do` |

## 샘플 기관 관찰

| 기관 | 구분 | Cleaneye ID | 검색 결과 |
| --- | --- | --- | --- |
| 서울교통공사 | 지방공기업 | `2017000008` | `selectNewEntSearchList.do`에서 1건 |
| 부산교통공사 | 지방공기업 | `2007100228` | `selectNewEntSearchList.do`에서 1건 |
| 서울시립교향악단 | 지방출자출연 | `B000261` | `selectIptEntSearchList.do`에서 1건 |

본문 HTML 확인:

- `서울교통공사` 일반현황은 `/user/empCommStatus.do` POST로 HTML 본문을 받을 수 있다.
- `서울시립교향악단` 일반현황은 `/user/iptSuCommStatus.do` POST로 HTML 본문을 받을 수 있다.
- 항목 본문은 HTML 테이블 기반이므로, 필드 단위 정규화는 별도 테이블 파서가 필요하다.

## ALIO와 Cleaneye 구분 기준

| 항목 | ALIO | Cleaneye |
| --- | --- | --- |
| 대상 | 중앙 공공기관 | 지방공기업, 지방출자·출연기관 |
| 기관 ID | `apbaId` 예: `C0399` | `entId` 숫자형 또는 `insttCode` B-prefix |
| 주요 화면 | `alio.go.kr` | `cleaneye.go.kr` |
| 일반현황 | ALIO 항목 `10105` | 지방공기업 `1_1`, 출자출연 `10` |
| 주요사업 후보 | ALIO 항목 `31501`, `contents` | 사업보고서/신규투자사업 HTML |
| 경영평가/감사 | ALIO 지적사항/평가 화면 | 경영평가등급, 외부기관 감사결과 항목 |

분석 흐름에서는 `source=alio`와 `source=cleaneye`를 분리하고, 기관 종류는
`kind=local_public_enterprise` 또는 `kind=local_invested_contributed`로 보존한다.
공통 분석 스키마는 이 구분을 유지한 뒤 기관명, 기관 유형, 주요사업 후보, 재무/평가 후보
필드를 합치는 방향이 안전하다.

## 결측과 주의점

| 영역 | 관찰 내용 |
| --- | --- |
| 검색 결과 | 기관명 완전 일치가 아니면 여러 기관이 나올 수 있어 ID 기반 sample id가 필요하다. |
| 항목 메타데이터 | 잘못된 itemNo는 `data`가 null에 가까운 형태로 내려올 수 있다. |
| 기준연도 | 상단 프레임에 현재 기준연도 변수가 하드코딩되어 있다. 2026-07-07 기준 지방공기업 `fixedYear=2025`, 출자출연 `fixedYear=2024`. |
| 본문 형식 | JSON이 아니라 HTML이다. 표 구조가 항목별로 달라 raw HTML 보존 후 별도 파싱이 필요하다. |
| 주요사업 | ALIO처럼 단일 `contents` 필드가 아니라 사업보고서/신규투자사업 등 후보 항목을 봐야 한다. |
| 파일/첨부 | 이번 조사 범위에서는 첨부파일 다운로드 URL을 안정 endpoint로 확정하지 않았다. |

## 구현 메모

`CleaneyeClient`는 확인된 공개 endpoint만 감싼다.

`CleaneyeCollector`는 다음 raw sample을 저장한다.

| sample | 내용 |
| --- | --- |
| institution search | 기관명 검색 원본 JSON |
| item tree | 기관/유형 트리 원본 JSON |
| item metadata | 주요 후보 항목별 item metadata JSON |
| item html | 주요 후보 항목별 본문 HTML |
| source links | 기관별공시 홈과 Cleaneye 기관 구분 메타데이터 |

raw sample은 `data/raw_samples/cleaneye/...` 아래에 저장되며 `.gitignore` 대상이다.
HTML table, caption, row 구조와 공통/전용 parser 판단 근거는
`docs/archive/cleaneye-html-structure.md`에 따로 정리한다.
