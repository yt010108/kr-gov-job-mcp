# Collector Setup and Data Observation Workflow

이 문서는 팀원이 같은 조건으로 수집기를 실행하고, raw sample과 필드 관찰 결과를
같은 기준으로 남기기 위한 운영 규칙이다.

## 1. 로컬 준비

Python 3.11 이상을 사용한다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Windows PowerShell에서는 다음처럼 활성화한다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

기본 확인:

```bash
python -m pytest -q
python -m ruff check .
python -m kr_gov_job_mcp.server
```

현재 공개 웹 수집은 별도 API 키를 요구하지 않는다. `.env`가 필요한 수집기가 추가되면
`.env.example`에 변수명만 추가하고 실제 값은 커밋하지 않는다.

## 2. 수집기 실행 원칙

수집기는 최종 분석 결과를 만들지 않는다. 수집 단계의 목표는 다음 세 가지다.

- 원본 응답과 요청 조건을 보존한다.
- 필드명이 실제로 어떻게 내려오는지 확인한다.
- ERD와 분석 스키마를 정하기 전에 결측과 예외를 발견한다.

공통 실행 형태:

```python
import asyncio

from kr_gov_job_mcp.collectors import RawSampleStore
from kr_gov_job_mcp.collectors.some_source import SomeSourceCollector


async def main():
    collector = SomeSourceCollector()
    result = await collector.collect_raw(
        query={"institution_name": "한국인터넷진흥원"},
        sample_store=RawSampleStore("data/raw_samples"),
    )
    print(result.model_dump())


asyncio.run(main())
```

`data/raw_samples`는 `.gitignore` 대상이다. raw sample은 로컬 재현과 필드 관찰에 쓰고,
PR에는 raw 파일 자체를 올리지 않는다.

## 3. Raw Sample 저장 규칙

`RawSampleStore`는 다음 경로를 사용한다.

```txt
data/raw_samples/
  <source>/
    <raw_type>/
      <YYYY-MM-DD>/
        <sample_id>.json
```

예시:

```txt
data/raw_samples/job_alio/list/2026-07-07/kisa-search.json
data/raw_samples/alio_disclosure/detail/2026-07-07/C0399-institution-detail.json
data/raw_samples/cleaneye/html/2026-07-07/seoul-facility-list.json
```

`sample_id`는 가능한 한 원천 시스템 식별자를 포함한다.

| 상황 | 권장 sample_id |
| --- | --- |
| 기관 단위 | `C0399-institution-detail`, `B552909-job-list` |
| 공고 단위 | `<notice_id>-detail` |
| 페이지 단위 | `<source-page>-page-1` |
| 검색 결과 | `<stable-key>-search` |
| 첨부파일 | `<disclosure_no>-files` |

한글 기관명만 sample id로 쓰면 안전 경로 변환 후 충돌할 수 있으므로, 기관 코드나 공고 ID를
함께 사용한다.

## 4. 필드 인벤토리 작성 규칙

필드 인벤토리 문서는 `docs/<source>-field-inventory.md`에 둔다.

필수 섹션:

| 섹션 | 기록 내용 |
| --- | --- |
| 조사일 | 날짜, 수집자, 기준 브랜치 |
| 접근 경로 | URL, HTTP method, 주요 파라미터, 응답 형식 |
| 샘플 기준 | 기관/공고 2~3개, 선택 이유 |
| 원본 필드 | raw field name, 타입, 의미, 예시 |
| 분석 후보 필드 | 분석에 바로 쓸 수 있는 필드와 정규화 이름 |
| 결측 패턴 | null, 빈 문자열, 항목 없음, 파일 없음, 페이지 없음 |
| 못 쓰는 필드 | 불안정하거나 파생이 어려운 필드와 이유 |
| 원본 링크 | 사람이 확인 가능한 원본 페이지와 수집 시각 |

필드 판단 기준:

- 하나의 샘플에서만 보인 필드는 “후보”로만 둔다.
- 최소 2~3개 샘플에서 반복 확인된 필드만 안정 필드로 분류한다.
- 화면 표시용 날짜와 API 내부 timestamp가 같이 있으면 둘 다 raw에 보존한다.
- 첨부파일은 파일명, 원본 링크, 파일 타입을 우선 보존하고 본문 파싱은 별도 단계로 둔다.
- HTML/PDF 본문 파싱이 필요한 필드는 “추가 파서 필요”로 표시한다.

## 5. 소스별 관찰 흐름

### Job-ALIO

목표:

- 공고 검색 목록을 저장한다.
- 공고 상세, 첨부파일, 전형 단계 필드를 확인한다.
- 공고 원문 링크와 수집 시각을 보존한다.

샘플 추천:

- 한국인터넷진흥원 또는 창업진흥원처럼 IT/사업관리 공고가 있는 기관
- 공고 첨부파일이 있는 채용공고
- 전형 단계 데이터가 있는 채용공고

관찰 체크:

- `recrutPblntSn`, `instNm`, `pblntInstCd`
- 공고 시작/마감일 형식
- NCS 코드와 NCS 명칭 목록
- 첨부파일 이름, 파일 번호, 다운로드 URL
- 전형 단계별 인원, 지원자 수, 경쟁률 결측 여부

### ALIO 경영공시

목표:

- 기관명 또는 ALIO 기관 코드로 기관을 찾는다.
- 일반현황과 주요사업 원본을 확인한다.
- 국회 지적사항과 감사원/주무부처 지적사항 접근 가능 여부를 확인한다.

샘플 추천:

- 한국인터넷진흥원
- 창업진흥원
- 한국전력공사

관찰 체크:

- `apbaId`, `apbaNa`, 기관 유형, 주무부처
- `contents` 주요사업 텍스트와 줄바꿈 패턴
- 일반현황 보고서 번호 `10105`
- 주요사업 보고서 번호 `31501`
- 국회 지적사항 `B1210`
- 감사원/주무부처 지적사항 `B1220`
- `disclosureNo`, `submissionNo`, 첨부파일 목록

### Cleaneye

목표:

- 지방공기업 기관 검색과 기관 상세 접근 가능 여부를 확인한다.
- 경영공시와 채용/인력 관련 필드가 공개 웹에서 재현 가능한지 확인한다.
- ALIO와 같은 정규화 필드로 합칠 수 있는지 판단한다.

샘플 추천:

- 도시철도/시설공단/환경공단 유형을 섞어 2~3개 기관
- 광역 지자체와 기초 지자체 산하 기관을 나누어 확인

관찰 체크:

- 기관명, 기관 유형, 설립 지자체
- 기관 코드 또는 상세 페이지 식별자
- 주요사업/설립목적/인력현황 필드
- 경영평가, 감사, 지적사항 접근 가능 여부
- 페이지네이션과 검색 조건 보존 방법

## 6. 데모 재현 흐름

기준 입력은 `examples/kisa-demo-input.json`을 사용한다.

재현 순서:

1. Job-ALIO에서 한국인터넷진흥원 관련 공고 목록과 상세 raw sample을 만든다.
2. ALIO 경영공시에서 한국인터넷진흥원 일반현황, 주요사업, 국회/감사 지적사항 raw sample을 만든다.
3. 각 source별 field inventory에서 “분석에 바로 쓸 수 있는 필드”만 추려 분석 스키마 후보로 옮긴다.
4. `examples/kisa-demo-output.md`의 리포트 형태와 비교해 부족한 근거 링크를 보강한다.

데모 전에 확인할 결과물:

- `data/raw_samples/<source>/...`에 당일 수집 파일이 있는지
- 각 raw sample에 `request`, `collected_at`, `content_type`, `metadata`가 있는지
- 필드 인벤토리에 샘플 2~3개 기준 결측 패턴이 적혀 있는지
- 원본 링크가 사람이 브라우저에서 열 수 있는지

## 7. PR 전 체크리스트

- `python -m pytest -q`
- `python -m ruff check .`
- `git diff --check`
- raw sample 파일이 stage되지 않았는지 확인
- 필드 인벤토리에 추측이 아니라 관찰한 필드만 안정 필드로 적었는지 확인
- 새 수집기가 외부 사이트에 과도한 요청을 보내지 않는지 확인
