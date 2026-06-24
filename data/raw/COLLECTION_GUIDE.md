# 데이터 수집 가이드 — 확장 데이터 (선택)

기본 LLAI(A1·A2·A3)는 이미 수집·정제되어 있다. 이 문서는 **선행연구(조민하 2021)를 발전시키기
위해 새로 추가한 4종 데이터**의 수집 방법이다. 각 데이터는 **있으면 자동 사용, 없으면 건너뜀**
(파이프라인은 항상 동작). 파일을 채운 뒤 아래 명령을 실행하면 해당 분석이 활성화된다.

> 이 환경(과제 채점/오프라인)에서 네트워크가 막혀 있을 수 있다. 실제 수집은 개인 PC에서.

---

## 1. 사업체수 (demand-pull 수요 변수) — KOSIS
**무엇을 여는가** "변호사는 일(수요) 있는 곳으로 간다"는 demand-pull 가설을 *사업체 수*로 실측 검증.
회귀(`src/model/regression.py`)에 `인구당 사업체수` 피처가 자동 추가된다.

- **출처**: KOSIS(kosis.kr) → 전국사업체조사 → 시도별 사업체 수.
- **파일**: `data/raw/kosis/business_count_sido.csv` (KOSIS 가로형 그대로 저장)
  - 행=시도, 열=연도. 사업체수만이면 그대로; '사업체수+종사자수' 2항목이면
    `load_kosis.py`의 `items_per_year=1`을 `2`로.
- **활성화**:
  ```bash
  python src/prepare/load_kosis.py     # → data/interim/kosis_business.csv
  python src/prepare/build_panel.py    # 패널에 business_count 추가
  python src/model/regression.py       # 인구당 사업체수 피처 자동 포함
  ```

## 2. 판사수 (논문 회귀 재현) — 대법원규칙 별표
**무엇을 여는가** 조민하(2021)의 모형(**변호사밀도 ~ GRDP + 판사수**)을 *그대로 재현* →
논문과 1:1 비교(보고서가 한계로 남긴 것). `regression.py`에 '논문 재현' 회귀가 자동 추가된다.

- **출처**: 대법원규칙 「각급 법원 판사 정원」 별표 (국가법령정보센터/법원행정처).
  연 2회 개정되면 마지막 차수 기준(논문 방식).
- **파일**: `data/raw/court/judges_by_region.csv`
  - 템플릿 `judges_by_region.template.csv`를 복사해 `judges` 열을 채운다.
  - 스키마: `region13, year, judges`. 별표의 각급 법원 정원을 13권역으로 합산
    (법원 접두 도시 → 권역은 `config.COURT_PREFIX_TO_REGION13` 참조).
- **활성화**:
  ```bash
  python src/prepare/build_panel.py    # 패널에 judges 추가 (별도 로더 불필요)
  python src/model/regression.py       # '논문 재현' 회귀 자동 활성화
  ```

## 3. 유사법무직렬 (무변촌 재정의) — 각 협회 통계
**무엇을 여는가** 논문이 길게 논했으나 측정 못한 차원. "변호사 없는 지역(무변촌)이 정말
법률 사각인가 — 법무사·변리사·세무사가 메우나"를 검증(`src/model/quasi_legal.py`).

- **출처**: 대한법무사협회·대한변리사회·한국세무사회 회원현황(시도/지방회별).
- **파일**: `data/raw/quasi/quasi_legal.csv`
  - 템플릿 `quasi_legal.template.csv`를 복사해 채운다.
  - 스키마: `sido_name, year, beopmusa(법무사), byeollisa(변리사), semusa(세무사)`.
    (값이 없는 직렬은 비워도 됨 — 있는 것만 합산)
- **활성화**:
  ```bash
  python src/prepare/load_quasi.py     # → data/interim/quasi_legal.csv
  python src/prepare/build_panel.py    # 패널에 quasi_total 추가
  python src/model/quasi_legal.py      # 무변촌 재정의 분석(표·그림)
  ```

## 4. A2 다년 시계열 (LLAI 시계열) — 과거 사법연감
**무엇을 여는가** 단면(2024)뿐인 사건부담(A2)을 연도별로 → 진짜 추세분석의 기반.
(변호사 A1 시계열은 `src/model/lawyer_panel.py`가 Wayback으로 자동 복원.)

- **출처**: 대법원 사법연감(법원행정처, 매년). ⚠️ 1년 지연 발간(사법연감 2025 = 2024 데이터).
- **파일**: 연도별 폴더 `data/raw/court/(YYYY)년_사건개황/(YYYY)01.개황.01항.총설.xlsx`
  - 2024와 같은 규칙. **연도당 총설 1파일이면 충분**(시트 '6' = 지역별 인구·사건수).
    민사/형사(02·07항)는 있으면 분야별로 추가, 없으면 본안 총계만.
  - 추천: 2022·2023·2024 3년이면 A1·A2·A3 겹치는 3년 점수 패널.
- **활성화**:
  ```bash
  python src/prepare/load_court.py     # 모든 (YYYY)년_사건개황 폴더 자동 스캔
  python src/prepare/build_panel.py
  ```

---

## 확인
각 활성화 후 `build_panel.py` 출력의 단면표에 해당 컬럼(`business_count`·`judges`·`quasi_total`)이
보이면 반영된 것이다. 분석 스크립트는 데이터가 없으면 안내 메시지를 출력하고 건너뛴다.
