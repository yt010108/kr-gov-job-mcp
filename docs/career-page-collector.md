# 기관별 채용 페이지 collector 설계

조사일: 2026-07-07 KST

## 목적

잡알리오 상세의 `source_url`은 기관 홈페이지 채용 게시판, 전용 채용 플랫폼, 단순 채용
메인 화면을 모두 가리킨다. 잡알리오 본문이나 첨부만으로 부족한 정보를 보강하려면 먼저
원문 페이지를 안전하게 보존하고, 자동 파싱 가능한 범위를 좁혀야 한다.

## 확인한 source_url 유형

| 유형 | 예시 | 관찰 |
| --- | --- | --- |
| 기관 게시판 상세 | `kised.or.kr/board.es?...act=view...` | HTML 제목과 게시글 본문, 첨부 다운로드 후보 링크가 보인다. |
| 기관 채용 상세 | `knps.or.kr/.../recruitDtl.do?...` | 공고 상세 HTML과 첨부 다운로드 후보 링크가 보인다. |
| 일반 홈페이지 게시글 | `bohun.or.kr/.../selectNttInfo.do?...` | 본문은 읽히지만 메뉴/하단 링크가 많아 후보 링크 필터가 필요하다. |
| 전용 채용 플랫폼 상세 | `fairyhr.com/announcement/detail/...` | HTML은 받을 수 있지만 본문은 JavaScript 렌더링일 수 있다. |
| 전용 채용 플랫폼 메인 | `recruiter.co.kr/appsite/company/index` | 정적 HTML에는 링크가 거의 없고 브라우저 렌더링이나 별도 API 확인이 필요하다. |
| 단순 채용 메인 | `reb.or.kr/recruit` | 특정 공고 상세가 아니라 보강 근거로 쓰기 어렵다. |

## 수집 범위 결정

1. 범용 collector는 `source_url` GET 결과를 HTML raw sample로 저장한다.
2. 같은 응답에서 `final_url`, HTTP status, content type, title, 본문 preview, 링크 후보를
   metadata raw sample로 저장한다.
3. 첨부파일 후보와 접수 링크 후보는 URL과 링크 텍스트의 힌트로만 분류한다.
4. 파일 다운로드, 지원서 제출, 로그인/세션이 필요한 API 호출은 자동화하지 않는다.
5. 같은 기관/호스트에서 반복적으로 안정 패턴이 확인될 때만 기관별 adapter를 추가한다.

## 보강 후보 필드

| 후보 필드 | 수집 방식 | 신뢰도 |
| --- | --- | --- |
| `source_url` | 잡알리오 상세 원문 URL | 높음 |
| `final_url` | redirect 이후 최종 URL | 높음 |
| `page_title` | HTML `<title>` | 중간 |
| `body_text_preview` | script/style 제외 텍스트 preview | 중간 |
| `attachment_candidates` | `.pdf`, `.hwp`, `.hwpx`, `download`, `file` 링크 힌트 | 중간 |
| `apply_candidates` | `apply`, `입사지원`, `접수`, 전용 채용 플랫폼 힌트 | 낮음 |
| `page_type` | URL path, host, 링크 후보 기반 분류 | 중간 |

## 사이트별 예외 기준

| 예외 | 처리 |
| --- | --- |
| JavaScript 렌더링 페이지 | HTML과 최종 URL만 보존하고, 브라우저/API adapter 후보로 표시한다. |
| 채용 메인 화면 | 특정 공고 상세가 없으면 `career_landing_or_dynamic_page`로 분류한다. |
| `javascript:;` 링크 | 수집하지 않는다. |
| 메뉴/푸터의 파일 링크 | 후보로만 남기고 자동 다운로드하지 않는다. |
| 외부 접수 플랫폼 | 링크 후보만 남기고 지원 플로우는 따라가지 않는다. |
| 로그인, CAPTCHA, 개인정보 입력 | collector 범위 밖으로 둔다. |

## adapter 분리 기준

범용 collector는 모든 `source_url`에 적용한다. 기관별 adapter는 다음 조건을 모두 만족할 때
추가한다.

- 같은 host/path 패턴의 샘플이 3건 이상이다.
- 본문, 첨부, 접수 링크를 CSS selector나 안정 endpoint로 구분할 수 있다.
- 로그인이나 개인정보 입력 없이 공개 GET/POST로 확인 가능하다.
- 실패해도 잡알리오 기본 상세와 첨부 수집 흐름을 방해하지 않는다.

## 구현 메모

`CareerPageCollector`는 다음 raw sample을 저장한다.

| sample | 내용 |
| --- | --- |
| `html` | 기관 원문 페이지 HTML |
| `metadata` | 최종 URL, title, page type, 본문 preview, 링크 후보 |

이 collector는 Job-ALIO 상세 collector 뒤에서 선택적으로 실행하는 보강 단계가 적합하다.
분석 단계에서는 잡알리오의 구조화 필드를 우선 사용하고, 기관 페이지는 공고문/직무기술서
첨부와 접수 링크가 부족할 때 보조 근거로만 사용한다.
