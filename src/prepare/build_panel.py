"""tidy 중간파일을 10도단위(region10)·13권역(region13) 패널로 조립.

선행: load_kosis.py, load_klac.py, scrape_bar.py (→ data/interim, data/raw/bar)
법원 사건수(A2)는 data/raw/court/court_cases.csv 가 있으면 자동 포함, 없으면 결측.

집계 규칙:
  인구·수급자        합산(sum)
  1인당 GRDP         인구가중 평균
  변호사(개업)       합산
  법률구조(A3)       region10은 직접 / region13은 소속 region10값을 인구비로 근사배분
  법원사건(A2)       합산(있을 때)

산출물(data/processed/):
  panel_region10.csv,  panel_region13.csv

사용:
  python src/prepare/build_panel.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (RAW, INTERIM, PROCESSED, REGION10_ORDER, REGION13_ORDER,  # noqa: E402
                    REGION13_TO_REGION10, BAR_TO_REGION13,
                    normalize_to_region10, normalize_sido_name)


def _load(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        print(f"  [건너뜀] {path.name} 없음")
        return None
    return pd.read_csv(path)


def _sido_to_unit(df: pd.DataFrame, unit: str) -> pd.Series:
    fn = normalize_to_region10 if unit == "region10" else normalize_sido_name
    return df["sido_name"].map(fn)


def build(unit: str) -> pd.DataFrame:
    order = REGION10_ORDER if unit == "region10" else REGION13_ORDER
    frames = []

    pop = _load(INTERIM / "kosis_population.csv")
    basic = _load(INTERIM / "kosis_basic.csv")
    grdp = _load(INTERIM / "kosis_grdp.csv")
    biz = _load(INTERIM / "kosis_business.csv")      # 사업체수(선택, demand-pull)
    quasi = _load(INTERIM / "quasi_legal.csv")       # 유사법무직렬(선택)
    judges = _load(RAW / "court" / "judges_by_region.csv")  # 판사수(선택, region13 기준)
    klac = _load(INTERIM / "klac_legalaid.csv")     # region10 기준
    bar = _load(RAW / "bar" / "bar_region13.csv")    # region13 기준
    court = _load(INTERIM / "court_cases.csv")       # region13 기준

    # 인구(분모로도 쓰이므로 먼저)
    pop_u = None
    if pop is not None:
        pop["unit"] = _sido_to_unit(pop, unit)
        pop_u = pop.dropna(subset=["unit"]).groupby(["unit", "year"], as_index=False)["population"].sum()
        frames.append(pop_u)

    if basic is not None:
        basic["unit"] = _sido_to_unit(basic, unit)
        b = basic.dropna(subset=["unit"]).groupby(["unit", "year"], as_index=False)["low_income_pop"].sum()
        frames.append(b)

    if grdp is not None and pop is not None:
        g = grdp.merge(pop[["sido_name", "year", "population"]], on=["sido_name", "year"], how="left")
        g["unit"] = _sido_to_unit(g, unit)
        g = g.dropna(subset=["unit", "population"])
        g["w"] = g["grdp_per_capita"] * g["population"]
        gw = g.groupby(["unit", "year"], as_index=False).agg(w=("w", "sum"), p=("population", "sum"))
        gw["grdp_per_capita"] = gw["w"] / gw["p"]
        frames.append(gw[["unit", "year", "grdp_per_capita"]])

    # 사업체수(선택): 수요 대리변수. sido → unit 합산.
    if biz is not None:
        biz["unit"] = _sido_to_unit(biz, unit)
        bz = biz.dropna(subset=["unit"]).groupby(["unit", "year"], as_index=False)["business_count"].sum()
        frames.append(bz)

    # 유사법무직렬(선택): sido → unit 합산.
    if quasi is not None:
        quasi["unit"] = _sido_to_unit(quasi, unit)
        qcols = [c for c in ["beopmusa", "byeollisa", "semusa", "quasi_total"] if c in quasi.columns]
        q = quasi.dropna(subset=["unit"]).groupby(["unit", "year"], as_index=False)[qcols].sum()
        frames.append(q)

    # 판사수(선택): region13 템플릿 → unit 합산.
    if judges is not None and "region13" in judges.columns:
        j = judges.copy()
        j["unit"] = j["region13"] if unit == "region13" else j["region13"].map(REGION13_TO_REGION10)
        jj = j.dropna(subset=["unit"]).groupby(["unit", "year"], as_index=False)["judges"].sum()
        frames.append(jj)

    # 변호사: region13 → unit
    # 스냅샷이므로 LLAI 입력(인구·저소득층·법률구조)이 모두 존재하는 최신 공통연도에 귀속
    ref_year = min(x["year"].max() for x in (pop, basic, klac) if x is not None)
    if bar is not None:
        b = bar.copy()
        b["year"] = ref_year
        if unit == "region10":
            b["unit"] = b["region13_name"].map(REGION13_TO_REGION10)
        else:
            b["unit"] = b["region13_name"]
        bb = b.groupby(["unit", "year"], as_index=False)["practicing"].sum()
        frames.append(bb)

    # 법률구조(A3)
    if klac is not None:
        if unit == "region10":
            a3 = klac.rename(columns={"region10": "unit"})[["unit", "year", "aid_cases"]]
        else:
            # region10값을 소속 region13에 인구비로 근사배분
            if pop_u is None:
                a3 = None
            else:
                p13 = pop.copy()
                p13["region13"] = p13["sido_name"].map(normalize_sido_name)
                p13["region10"] = p13["region13"].map(REGION13_TO_REGION10)
                p13 = p13.dropna(subset=["region13", "region10"])
                p13 = p13.groupby(["region13", "region10", "year"], as_index=False)["population"].sum()
                tot = p13.groupby(["region10", "year"], as_index=False)["population"].sum().rename(
                    columns={"population": "pop10"})
                p13 = p13.merge(tot, on=["region10", "year"]).merge(
                    klac, on=["region10", "year"], how="left")
                p13["aid_cases"] = p13["aid_cases"] * p13["population"] / p13["pop10"]
                a3 = p13.rename(columns={"region13": "unit"})[["unit", "year", "aid_cases"]]
        if a3 is not None:
            frames.append(a3)

    # 법원사건(A2) — interim/court_cases.csv (region13 기준). 있을 때만.
    if court is not None:
        c = court.copy()
        c["unit"] = c["region13"] if unit == "region13" else c["region13"].map(REGION13_TO_REGION10)
        case_cols = [x for x in ["total_cases", "civil_main", "criminal_trial"] if x in c.columns]
        c = c.dropna(subset=["unit"]).groupby(["unit", "year"], as_index=False)[case_cols].sum()
        frames.append(c)

    if not frames:
        raise SystemExit("중간파일이 없습니다. load_kosis.py / load_klac.py 먼저 실행.")

    keys = pd.concat([f[["unit", "year"]] for f in frames]).drop_duplicates()
    panel = keys
    for f in frames:
        panel = panel.merge(f, on=["unit", "year"], how="left")

    panel = panel.rename(columns={"unit": "region"})
    cat = pd.Categorical(panel["region"], categories=order, ordered=True)
    panel = panel.assign(_o=cat).sort_values(["year", "_o"]).drop(columns="_o").reset_index(drop=True)
    return panel


def main() -> None:
    for unit in ("region10", "region13"):
        print(f"\n===== {unit} 패널 =====")
        panel = build(unit)
        out = PROCESSED / f"panel_{unit}.csv"
        panel.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"저장: {out.name}  ({len(panel)}행, {panel['year'].nunique()}개 연도, "
              f"{panel['region'].nunique()}개 권역)")
        # 변호사 스냅샷 기준연도 단면 미리보기 (변호사 데이터 없으면 건너뜀)
        if "practicing" not in panel.columns or panel["practicing"].notna().sum() == 0:
            continue
        bar_year = int(panel.loc[panel["practicing"].notna(), "year"].max())
        print(f"[기준연도 {bar_year} 단면]")
        snap = panel[panel["year"] == bar_year]
        if len(snap):
            cols = [c for c in ["region", "practicing", "population", "low_income_pop",
                                "grdp_per_capita", "aid_cases", "total_cases"] if c in snap.columns]
            print(snap[cols].to_string(index=False))


if __name__ == "__main__":
    main()