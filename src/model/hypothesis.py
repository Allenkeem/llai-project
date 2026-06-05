"""가설 검정 (H1~H3). 가용 데이터(기준연도 2024 + 최신 GRDP)로 검정 가능한 범위.

H1 수도권(서울·인천·경기)의 변호사 1인당 인구 < 비수도권   → 집단 비교(Mann-Whitney)
H2 변호사 적은 권역일수록 사건부담(A2)↑                    → corr(A1, A2) < 0
H3 소득(GRDP) 낮을수록 법률구조(A3) 수요↑·변호사(A1) 부족   → corr(GRDP, A3/A1)

표본이 작아(n=13/10) 비모수 검정·상관계수 위주로 보고한다.
H4(시계열 격차)는 변호사가 스냅샷이라 LLAI 시계열 불가 → A3 격차 추세로 별도 확인.

사용:
  python src/model/hypothesis.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (OUTPUTS, INTERIM, canonical_sido,  # noqa: E402
                    normalize_to_region10, normalize_sido_name)

CAPITAL = {"서울", "인천", "경기"}  # 수도권(region13). region10에선 인천이 경기에 포함.


def _latest_grdp(unit: str) -> pd.DataFrame:
    """권역별 최신 연도 1인당 GRDP (인구가중)."""
    grdp = pd.read_csv(INTERIM / "kosis_grdp.csv")
    pop = pd.read_csv(INTERIM / "kosis_population.csv")
    # 옛/신 명칭 차이를 흡수하기 위해 정식 시도명으로 표준화 후 병합
    grdp["sido_c"] = grdp["sido_name"].map(canonical_sido)
    pop["sido_c"] = pop["sido_name"].map(canonical_sido)
    fn = normalize_to_region10 if unit == "region10" else normalize_sido_name
    g = grdp.merge(pop[["sido_c", "year", "population"]], on=["sido_c", "year"], how="left")
    g["region"] = g["sido_c"].map(fn)
    g = g.dropna(subset=["region", "population"])
    g["w"] = g["grdp_per_capita"] * g["population"]
    gw = g.groupby(["region", "year"], as_index=False).agg(w=("w", "sum"), p=("population", "sum"))
    gw["grdp"] = gw["w"] / gw["p"]
    return gw.sort_values("year").groupby("region").tail(1)[["region", "grdp"]]


def run(unit: str = "region13") -> None:
    df = pd.read_csv(OUTPUTS / "tables" / f"llai_{unit}.csv")
    df = df.merge(_latest_grdp(unit), on="region", how="left")
    df["pop_per_lawyer"] = df["population"] / df["practicing"]  # 변호사 1인당 인구

    print(f"################ 가설 검정 ({unit}, n={len(df)}) ################\n")

    # H1
    cap = df[df["region"].isin(CAPITAL)]
    non = df[~df["region"].isin(CAPITAL)]
    u, p = stats.mannwhitneyu(cap["pop_per_lawyer"], non["pop_per_lawyer"], alternative="less")
    print("[H1] 수도권 변호사 1인당 인구 < 비수도권")
    print(f"  수도권({list(cap['region'])}) 중앙값 {cap['pop_per_lawyer'].median():,.0f}명/변호사")
    print(f"  비수도권 중앙값 {non['pop_per_lawyer'].median():,.0f}명/변호사")
    print(f"  Mann-Whitney U={u:.1f}, p={p:.4f} → {'지지' if p < 0.05 else '기각/불충분'}\n")

    # H2
    r, pr = stats.pearsonr(df["A1"], df["A2"])
    rs, ps = stats.spearmanr(df["A1"], df["A2"])
    print("[H2] 변호사 많을수록 사건부담↓  (corr(A1,A2) < 0)")
    print(f"  Pearson r={r:.3f} (p={pr:.4f}), Spearman ρ={rs:.3f} (p={ps:.4f})")
    print(f"  → {'음의 상관 지지' if r < 0 and pr < 0.1 else '불충분'}\n")

    # H3
    print("[H3] 소득(GRDP)과 접근성 지표 상관")
    for col, label in [("A3", "법률구조 접근성"), ("A1", "변호사 접근성"), ("LLAI", "종합 LLAI")]:
        r, pr = stats.pearsonr(df["grdp"], df[col])
        print(f"  corr(GRDP, {label:10s}) r={r:+.3f} (p={pr:.4f})")
    print()


def h4_trend() -> None:
    """H4 보조: 법률구조(A3 원자료) 권역 격차(변동계수) 추세."""
    klac = pd.read_csv(INTERIM / "klac_legalaid.csv")
    cv = klac.groupby("year")["aid_cases"].agg(lambda s: s.std() / s.mean())
    print("[H4 보조] 법률구조 건수 권역 격차(변동계수) 추세:")
    print(f"  {int(cv.index.min())}년 CV={cv.iloc[0]:.3f} → {int(cv.index.max())}년 CV={cv.iloc[-1]:.3f}")
    slope = stats.linregress(cv.index, cv.values).slope
    print(f"  추세 기울기={slope:+.4f}/년 → 격차 {'확대' if slope > 0 else '축소'}\n")


if __name__ == "__main__":
    for u in ("region13", "region10"):
        run(u)
    h4_trend()
