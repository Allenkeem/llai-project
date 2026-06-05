# 대한민국 법률 서비스 접근성 불균형 분석

서강대 26-1 빅데이터컴퓨팅(BDS3010) 프로젝트 · 20210717 김찬우

지역별 종합 법률 접근성 지수(LLAI)를 개발하여 법률 서비스 접근성의 지역 격차를 분석한다.
분석 단위는 **13개 권역**(변협 지방회 기준, `region_mapping.csv`).

- 실행 계획: [PLAN.md](PLAN.md)
- 단일 기준 매핑표: [region_mapping.csv](region_mapping.csv)

## 데이터 출처

| 데이터 | URL | 형식 | 연도 |
|---|---|---|---|
| 인구·1인당 GRDP·고령화율 | https://kosis.kr | CSV | 2010~ |
| 법률구조 지역별 통계 | https://www.klac.or.kr/disclosure/countryStatistic.do · https://kosis.kr | 엑셀 | 2012~2025H1 |
| 법원 사건 통계(사법연감) | https://www.scourt.go.kr/portal/justicesta/JusticestaListAction.work?gubun=10 | 엑셀/PDF | 2010~ |
| 변호사 회원현황(지방회별) | https://www.koreanbar.or.kr/pages/introduce/stat.asp | HTML(스냅샷) | 현재 |
| 행정구역 경계 SHP | https://sgis.kostat.go.kr | SHP | 최신 |
| (보조) 공공데이터포털 | https://www.data.go.kr | API/파일 | - |

## 환경

- Python (pandas, numpy, geopandas, scikit-learn, statsmodels)
- 시각화: matplotlib, seaborn, plotly, folium
- PDF: pymupdf (환경에 설치됨)

## 폴더 구조

```
data/raw/{kosis,court,bar,klac,shp}  원본
data/interim / data/processed        중간·최종 패널
src/{collect,prepare,index,model}    수집·정제·지수·모델
notebooks  outputs/{figures,maps,tables}  reports
```

## 분석 단위 — 두 가지 병행

법률구조(A3)가 공단 기준 **10 도단위**로만 제공되어, 두 단위로 산출·비교한다.
- **region10**(10 도단위): 모든 지표 공통 해상도. 서울/경기(+인천)/강원/충북/충남권/경북권/경남권(+부산·울산)/전북/전남권/제주
- **region13**(13권역): 부산·인천·울산 분리 유지. A3는 소속 region10값을 인구비로 근사배분

## 실행 파이프라인

```bash
pip install -r requirements.txt

# 1) 수집 — 변협 회원현황 스크랩
python src/collect/scrape_bar.py          # → data/raw/bar/bar_region13.csv

# 2) 정제 — KOSIS·공단·법원 원본을 tidy long으로
python src/prepare/load_kosis.py          # → data/interim/kosis_{population,grdp,basic}.csv
python src/prepare/load_klac.py           # → data/interim/klac_legalaid.csv (region10)
python src/prepare/load_court.py          # → data/interim/court_cases.csv (사법연감 본안사건, A2)

# 3) 패널 조립 — region10·region13 동시
python src/prepare/build_panel.py         # → data/processed/panel_region10.csv, panel_region13.csv

# 4) LLAI 산출 — 가중치 3종(균등/엔트로피/PCA) 비교
python src/index/compute_llai.py          # → outputs/tables/llai.csv

# 5) 클러스터링 — K-means + Elbow/Silhouette
python src/model/cluster.py               # → outputs/tables/clusters.csv

# 데이터 없이 로직만 검증: --demo
python src/index/compute_llai.py --demo
```

## 데이터 현황 (2026-06-05)

| 차원 | 상태 | 비고 |
|---|---|---|
| A1 변호사 | ✅ 변협 스냅샷(현재) | 시계열 없음 → 횡단면 분석 |
| A2 법원 사건수 | ✅ 사법연감 2024 본안사건 | 법원관내→region, 비송 제외 |
| A3 법률구조 | ✅ 공단 민사 2012~2025 | 10 도단위, 반기→연 합산 |
| 인구·저소득층·GRDP | ✅ KOSIS | 기준연도 2024 단면 결측 0 |

**3차원 LLAI 완성** (기준연도 2024). 산출물: `outputs/tables/llai_{region10,region13}.csv`,
`clusters_{region10,region13}.csv`.

검증 메모: 법원관내 인구 합 = region10 KOSIS 인구와 정확히 일치(부산+울산+창원관내=경남권 759만).
본안사건 합 1,106,526 = 사법연감 전국 본안과 일치.