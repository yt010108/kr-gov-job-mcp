# search_public_jobs

## 구현 상태

Job-ALIO 검색 기반 1차 구현 완료. Cleaneye 채용/인턴 공고 사이트 통합과 `new_grad_only`
같은 코드 테이블 기반 필터는 아직 보류한다.

## 입력

- `keyword`
- `page`
- `limit`
- `ongoing_only`
- `institution_code`
- `ncs_code`
- `region`
- `region_code`
- `academic_condition_code`
- `employment_type_code`
- `recruitment_type`
- `replacement_only`
- `announcement_start_date`
- `announcement_end_date`
- `institution_type`
- `institution_classification`

## 출력

- 공고명
- 기관명
- 기관 코드
- 공고 시작일
- 마감일
- 진행 여부
- 지역
- NCS 코드/표시명 매핑 후보
- 고용 유형
- 채용 구분
- 채용 인원
- 원문 링크

## 데이터 소스

- 잡알리오 채용정보 Ajax 목록 응답

## 처리 원칙

- `region_code`가 있으면 그대로 Job-ALIO 검색에 사용한다.
- `region`이 있으면 `lookup_region_codes`와 같은 resolver로 Job-ALIO 지역 코드로 바꾼다.
- `region`과 `region_code`가 서로 충돌하면 검색하지 않고 오류를 낸다.
- `limit`은 한 번의 Job-ALIO 요청 기준 최대 100으로 제한한다.
