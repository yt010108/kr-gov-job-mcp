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

## 3. Collector 구현 기준

현재 collector 관련 기준 문서는 이 파일에 모은다. Job-ALIO에서 실제 관찰한 필드는
`docs/inventory/job-alio-field-inventory.md`를 기준으로 본다.

패키지 구조:

```txt
src/kr_gov_job_mcp/
  clients/
    job_alio_web_client.py
  collectors/
    __init__.py
    base.py
    raw_store.py
  schemas/
    job.py
```

- `clients/`: 소스별 HTTP adapter와 응답 parsing을 둔다.
- `collectors/`: 수집 실행 계약, run metadata, raw sample 저장을 둔다.
- `schemas/`: 안정화된 소스 응답 model만 둔다. 분석 스키마는 field inventory가 충분히 쌓인 뒤 정한다.

각 collector는 다음 계약을 따른다.

- `name`: `job_alio`, `alio_disclosure`, `cleaneye` 같은 안정적인 source 이름.
- `http_policy`: timeout, retry, user-agent, rate-limit 기본값.
- `collect_raw(query, sample_store)`: 원본 데이터를 수집하고 `RawSampleStore`로 raw sample을 쓴 뒤 `CollectionResult`를 반환한다.

HTTP 기본값:

- Timeout: request당 10초.
- Retry: 일시적 실패에는 2회 재시도.
- Backoff: 재시도 전 0.5초.
- Rate limit: source별 초당 1회 요청. 더 취약한 source는 더 엄격하게 둔다.
- User-Agent: `kr-gov-job-mcp/0.1 (raw-data-observation)`.

분리 원칙:

- Raw sample은 원천 필드와 source별 이름을 그대로 보존한다.
- 안정화된 source schema는 raw payload를 유지해 field inventory 작업에 쓸 수 있게 한다.
- 분석 결과는 `data/raw_samples`에 쓰지 않는다.
- 필드 인벤토리는 추측한 최종 스키마가 아니라 raw sample에서 관찰한 내용으로 작성한다.

## 4. Raw Sample 저장 규칙

`RawSampleStore`는 다음 경로를 사용한다.

```txt
data/raw_samples/
  <source>/
    <raw_type>/
      <YYYY-MM-DD>/
        <sample_id_slug>-<sample_id_sha256>-<collected_at_token>.json
```

예시:

```txt
data/raw_samples/job_alio/list/2026-07-07/kisa-search-<sample_id_sha256>-2026-07-07T00-01-02Z-<collected_at_sha256>.json
data/raw_samples/alio_disclosure/detail/2026-07-07/C0399-institution-detail-<sample_id_sha256>-2026-07-07T00-01-02Z-<collected_at_sha256>.json
data/raw_samples/cleaneye/html/2026-07-07/seoul-facility-list-<sample_id_sha256>-2026-07-07T00-01-02Z-<collected_at_sha256>.json
```

파일명의 `sample_id_slug`와 `collected_at_token`은 Windows와 Linux에서 쓸 수 있는 ASCII로
정규화한다. `sample_id_slug`는 최대 48자이며, 한글처럼 ASCII slug가 없는 값은 `unknown`이
될 수 있다. 이 경우에도 원문 `sample_id` 전체의 SHA-256 digest를 파일명에 넣으므로 서로
다른 ID를 충돌 가능성이 매우 낮은 별도 경로로 구분한다. `collected_at_token`에도 원문 수집
시각의 SHA-256 digest를 넣어 정규화 결과가 같아져도 구분한다. Windows 예약명과 끝 공백·
마침표, 예약명에 붙은 확장자도 저장 경로에서 정리한다.

같은 `sample_id`를 다른 `collected_at`으로 재수집하면 별도 파일로 저장한다. 정확히 같은
최종 경로에 다시 쓰려 하면 기존 raw JSON을 덮어쓰지 않고 `FileExistsError`로 실패한다.
쓰기는 같은 디렉터리의 임시 파일을 완전히 기록한 뒤 no-clobber 방식으로 publish하므로,
실패한 쓰기가 target JSON 또는 임시 partial JSON을 남기지 않는다.

기존 `<sample_id>.json` 형태의 raw 파일은 자동 migration하지 않는다. 다만 `read_sample()`은
전달된 경로의 JSON을 그대로 읽으므로 기존 경로와 새 경로 모두 호환된다.

`sample_id`는 가능한 한 원천 시스템 식별자를 포함한다.

| 상황 | 권장 sample_id |
| --- | --- |
| 기관 단위 | `C0399-institution-detail`, `B552909-job-list` |
| 공고 단위 | `<notice_id>-detail` |
| 페이지 단위 | `<source-page>-page-1` |
| 검색 결과 | `<stable-key>-search` |
| 첨부파일 | `<disclosure_no>-files` |

한글 기관명만 sample id로 써도 digest가 별도 경로를 만들지만, 사람이 raw 파일을 찾기 쉽게
기관 코드나 공고 ID를 함께 사용하는 것을 권장한다.

Raw sample JSON은 다음 필드를 포함한다.

| 필드 | 의미 |
| --- | --- |
| `source` | source 이름 |
| `raw_type` | `list`, `detail`, `attachment`, `html`, `pdf_text`, `api_response`, `metadata`, `other` 중 하나 |
| `sample_id` | source 식별자 또는 결정 가능한 local identifier |
| `payload` | 분석 필드를 더하지 않은 원본 payload |
| `request` | 민감값을 제거한 request metadata |
| `collected_at` | UTC 수집 시각 |
| `content_type` | 확인 가능한 경우 응답 content type |
| `metadata` | pagination, parser version 같은 source별 관찰 note |

비밀값, access token, 개인 메모, 지원자 개인 데이터는 raw sample에 저장하지 않는다.

## 5. 필드 인벤토리 작성 규칙

필드 인벤토리 문서는 `docs/inventory/<source>-field-inventory.md`에 둔다.

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

## 6. 소스별 관찰 흐름

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
- 기관 상세 페이지의 항목별 보고서 표에서 필요한 항목번호를 기준으로 원본을 확인한다.
- 채용정보, 주요사업, 국회지적사항, 계약정보, 연구보고서 원본을 저장한다.
- 감사원 지적사항과 주무부처 지적사항은 수집 범위에서 제외한다.

샘플 추천:

- 한국인터넷진흥원
- 창업진흥원
- 한국전력공사

관찰 체크:

- `apbaId`, `apbaNa`, 기관 유형, 주무부처
- `contents` 주요사업 텍스트와 줄바꿈 패턴
- 6-2 직원 채용정보 `B1020`
- 40 주요사업 `31501`
- 47-1 국회지적사항 `B1210`
- 49-1 입찰공고 `B1030`
- 49-2 수의계약 `7030`
- 50-1 자체 연구 보고서 `B1040`
- 50-2 외부용역 연구 보고서 `B1260`
- `disclosureNo`, `submissionNo`, `idx`, `tableName`, `idxName`, 첨부파일 목록
- 수시 게시판 항목은 목록 JSON과 상세 HTML이 같이 저장되는지 확인
- 정기 보고서 항목은 목록 JSON, 첨부파일 메타데이터, 본문 HTML이 같이 저장되는지 확인

3개 기관 확대 검증 결과는 `docs/archive/alio-sample-validation.md`에 기록한다.

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

## 7. 데모 재현 흐름

기준 입력은 `examples/kisa-demo-input.json`을 사용한다.

재현 순서:

1. Job-ALIO에서 한국인터넷진흥원 관련 공고 목록과 상세 raw sample을 만든다.
2. ALIO 경영공시에서 한국인터넷진흥원 일반현황, 주요사업, 국회/감사 지적사항 raw sample을 만든다.
3. 각 source별 field inventory에서 “분석에 바로 쓸 수 있는 필드”만 추려 분석 스키마 후보로 옮긴다.
4. `examples/kisa-demo-template.md`와 `examples/kisa-real-demo-output.md`를 비교해 부족한 근거 링크를 보강한다.

데모 전에 확인할 결과물:

- `data/raw_samples/<source>/...`에 당일 수집 파일이 있는지
- 각 raw sample에 `request`, `collected_at`, `content_type`, `metadata`가 있는지
- 필드 인벤토리에 샘플 2~3개 기준 결측 패턴이 적혀 있는지
- 원본 링크가 사람이 브라우저에서 열 수 있는지

## 8. PR 전 체크리스트

- `python -m pytest -q`
- `python -m ruff check .`
- `git diff --check`
- raw sample 파일이 stage되지 않았는지 확인
- 필드 인벤토리에 추측이 아니라 관찰한 필드만 안정 필드로 적었는지 확인
- 새 수집기가 외부 사이트에 과도한 요청을 보내지 않는지 확인
