# 대한민국 법률 서비스 접근성 불균형 분석

> 지역별 **종합 법률 접근성 지수(LLAI)** 를 개발해 변호사·법원·법률구조 자원의 지역 격차를 정량화한다.

서강대학교 26-1 빅데이터컴퓨팅(BDS3010) 프로젝트 · 20210717 김찬우

변호사 분포(A1)·법원 사건부담(A2)·취약계층 접근성(A3) **3개 차원**을 단일 지수(0~100)로 통합하고,
17개 시도를 출처 정합성에 맞춘 **13개 권역 / 10개 도단위**로 분석한다. 기준연도 **2024**.

---

## 핵심 발견

<p align="center">
  <img src="outputs/figures/fig7_map_region13.png" width="46%">
  <img src="outputs/figures/fig7_map_region13_exseoul.png" width="46%">
</p>
<p align="center"><em>왼쪽: 전체 LLAI(서울 91로 압도) · 오른쪽: 서울 제외 재정규화(지방 내부 구조)</em></p>

1. **서울 일극 집중** — 서울 LLAI 91, 인구 10만 명당 변호사 263명으로 다른 권역(12~37명)과 격차가 극단적. 클러스터링에서 서울이 단독 그룹으로 분리된다.
2. **변호사 수 ↔ 사건부담은 강한 음의 상관 (H2 지지)** — `corr(A1, A2) = −0.84 ~ −0.88` (p<0.01). 변호사가 부족한 비수도권일수록 1인당 업무 부담이 크다.
3. **'수도권 우위'는 사실상 서울 단독 현상** — 인구가 큰 **인천·경기는 전체 분석에서도 중하위권**(인천은 사건부담이 높아 5위 아래). 서울 제외 후 재정규화하면 **부산·울산·제주**가 상위로 부상한다. 비수도권 내부에서도 광역시 vs 인구분산형(강원·충북) 격차가 뚜렷.
4. **격차는 축소되지 않음 (H4)** — 변호사가 2009→2026년 **3.4배**(9,612→32,273명) 늘었음에도 서울 집중은 **71%→76%**로 심화(HHI 0.53→0.60). 법률구조 격차(변동계수)도 0.85→0.90으로 확대.

| | region13 LLAI 상위 | 하위 |
|---|---|---|
| 전체 | 서울(91) · 울산(24) · 제주(23) | 강원(2) · 충북(4) · 인천(5) |
| 서울 제외 | 부산(69) · 울산(66) · 제주(64) | 강원(4) · 충북(12) · 인천(24) |

---

## LLAI 지표 정의

| 지표 | 정의 | 방향 | 출처 |
|---|---|---|---|
| **A1** 변호사 접근성 | 인구 10만 명당 개업변호사 수 | ↑ 좋음 | 대한변호사협회 |
| **A2** 사건 부담 | 변호사 1인당 법원 본안사건 수 | ↓ 좋음 | 대법원 사법연감 |
| **A3** 취약계층 접근성 | 법률구조 건수 / 저소득층 인구 | ↑ 좋음 | 대한법률구조공단 |

`LLAI = w₁·A1n + w₂·(1−A2n) + w₃·A3n` (0~100). Min-Max 정규화 후 **가중치 3종(균등·엔트로피·PCA)** 을 병기해 강건성 확인.

### 분석 단위 — 두 가지 병행
출처별 지역 해상도가 달라(변협 14지방회, 공단 10도단위) 두 단위로 산출·비교한다.
- **region13** — 변협 기준 13권역. 부산·인천·울산 분리 유지. A3는 인구비 근사배분.
- **region10** — 공단 기준 10도단위. 모든 지표 공통 해상도(가장 정합적).

단일 기준 매핑표: [`region_mapping.csv`](region_mapping.csv) (시도 ↔ 권역 ↔ 변협회 ↔ 관할법원).

---

## 데이터 출처

| 차원 | 출처 | 형식 | 기간 |
|---|---|---|---|
| A1 변호사 | [대한변호사협회 회원현황](https://www.koreanbar.or.kr/pages/introduce/stat.asp) | HTML 스크랩 | 현재(스냅샷) |
| A2 법원 사건 | [대법원 사법연감](https://www.scourt.go.kr) | 엑셀 | 2024 |
| A3 법률구조 | [대한법률구조공단](https://www.klac.or.kr/disclosure/countryStatistic.do) | 엑셀 | 2012~2025 |
| 인구·저소득층·GRDP | [통계청 KOSIS](https://kosis.kr) | CSV | 2008~2025 |
| 변호사 2009 분포(H4) | 법률저널(2010)·대한변협 자료 | 기사(7권역) | 2009 |
| 시도 경계 | southkorea-maps (통계청 2018) | GeoJSON | 2018 |

> **검증** — 법원관내 인구 합 = region10 KOSIS 인구와 정확히 일치(부산+울산+창원관내 = 경남권 759만).
> 본안사건 합 1,106,526 = 사법연감 전국 본안과 일치.

---

## 노트북 (분석 흐름)

| 노트북 | 내용 |
|---|---|
| [01_분석정리](notebooks/01_분석정리.ipynb) | 배경·데이터·패널·LLAI·클러스터링 전체 흐름 |
| [02_가설검정_시각화](notebooks/02_가설검정_시각화.ipynb) | H1~H4 검정 + 도표 |
| [03_지도시각화](notebooks/03_지도시각화.ipynb) | 코로플레스 지도(정적·인터랙티브) |
| [04_서울제외_비교](notebooks/04_서울제외_비교.ipynb) | 서울 제외 재정규화 — 지방 간 상대 구조 |

`src/`는 수집·정제·지수·모델 **엔진(.py)**, 노트북은 이를 불러와 결과를 재현·해석한다.

---

## 실행 파이프라인

```bash
pip install -r requirements.txt

# 1) 수집 — 변협 회원현황 스크랩
python src/collect/scrape_bar.py          # → data/raw/bar/bar_region13.csv

# 2) 정제 — KOSIS·공단·사법연감 원본을 tidy long으로
python src/prepare/load_kosis.py          # 인구·GRDP·저소득층
python src/prepare/load_klac.py           # 법률구조(A3, region10)
python src/prepare/load_court.py          # 사법연감 본안사건(A2)

# 3) 패널 조립 — region10·region13 동시
python src/prepare/build_panel.py         # → data/processed/panel_*.csv

# 4) LLAI 산출 — 가중치 3종 비교
python src/index/compute_llai.py          # → outputs/tables/llai_*.csv

# 5) 클러스터링 — K-means + Elbow/Silhouette
python src/model/cluster.py

# 6) 가설검정 · 시각화
python src/model/hypothesis.py            # H1~H4
python src/model/lawyer_trend.py          # H4 직접: 변호사 집중도 2009 vs 2026
python src/viz.py                         # 도표 10종 → outputs/figures/

# 7) 코로플레스 지도 (시도 경계 → 권역 dissolve)
python src/map_viz.py                     # → outputs/figures/, outputs/maps/*.html

# 8) 서울 제외 비교 (재정규화)
python src/exclude_seoul.py               # → *_exseoul 산출물

# 데이터 없이 로직만 검증
python src/index/compute_llai.py --demo
```

---

## 폴더 구조

```
data/
  raw/{bar,kosis,klac,court,geo}   원본
  interim/                         정제 tidy
  processed/                       region10·region13 패널
src/
  collect/scrape_bar.py            변협 스크랩
  prepare/{load_kosis,load_klac,load_court,build_panel}.py
  index/compute_llai.py            LLAI(정규화·가중치·합산)
  model/{cluster,hypothesis}.py    클러스터링·가설검정
  viz.py  map_viz.py  exclude_seoul.py
  config.py                        경로·지역 매핑 헬퍼
notebooks/   01~04
outputs/{tables,figures,maps}      결과물
region_mapping.csv  PLAN.md  requirements.txt
```

---

## 한계와 향후 과제

- **변호사 데이터가 현재 스냅샷** — LLAI 시계열·H4 직접 검정 불가. 변호사백서 PDF로 과거 시계열 보강 필요.
- **표본이 작음**(권역 10~13개) — 통계적 검정력 제한(H1은 방향만 일치, 비유의).
- **A3 해상도** — 공단 통계가 10도단위라 부산·인천·울산을 분리 못 해 region13에선 근사배분.

## 환경
Python 3.13 · pandas · numpy · scikit-learn · scipy · statsmodels · matplotlib · seaborn · geopandas · folium · openpyxl · pymupdf

## 문서
- 📄 **최종 보고서**: [reports/보고서.md](reports/보고서.md)
- 📊 **발표 슬라이드**: [reports/발표자료.pptx](reports/발표자료.pptx) (13장, 그림 임베드) · 구성안 [발표_개요.md](reports/발표_개요.md)
- 상세 계획: [PLAN.md](PLAN.md)
