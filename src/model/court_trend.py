# -*- coding: utf-8 -*-
"""법원 본안사건(법률 수요) 시계열 추세 — 과거 사법연감 다년 적재(④)로 가능해진 분석.

기존 A2(사건부담)는 2024 단면뿐이었으나, load_court가 2019~2024 사법연감을 적재하면서
'사건수(법률 수요)'를 연도별로 볼 수 있게 됐다. 단, A2(=사건÷변호사)의 완전한 추세는
변호사(A1) 연도별 수가 필요한데 변협이 현재 스냅샷만 제공하므로(→ lawyer_panel은 Wayback 복원),
여기서는 변호사와 무관하게 직접 얻어지는 두 가지를 본다:
  ① 전국 본안사건 추세(절대)        ② 권역별 인구 1만명당 사건수 추세(수요 밀도)

※ '사건부담(A2=사건/변호사)' 완전 시계열은 A1 연도별(lawyer_panel) 확보 후 결합 가능(향후).

산출물:
  outputs/tables/court_caseload_trend.csv        region × year, 인구1만명당 사건수
  outputs/figures/fig_court_caseload_trend.png   전국 추세 + 권역별 인구당 추세

사용:  python src/model/court_trend.py  [region13|region10]
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROCESSED, OUTPUTS  # noqa: E402


def build(unit: str = "region13") -> pd.DataFrame | None:
    p = pd.read_csv(PROCESSED / f"panel_{unit}.csv")
    d = p.dropna(subset=["total_cases", "population"]).copy()
    if d["year"].nunique() < 2:
        return None
    d["cases_per_10k"] = d["total_cases"] / d["population"] * 10_000
    return d[["region", "year", "total_cases", "population", "cases_per_10k"]]


def fig(d: pd.DataFrame, save: bool = True):
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    nat = d.groupby("year", as_index=False)["total_cases"].sum()
    pivot = d.pivot(index="year", columns="region", values="cases_per_10k")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    # ① 전국 본안사건 추세
    ax1.plot(nat["year"], nat["total_cases"] / 10_000, "o-", color="#C44E52")
    ax1.set_title("전국 본안사건 추세")
    ax1.set_xlabel("연도"); ax1.set_ylabel("본안사건 (만 건)")
    for _, r in nat.iterrows():
        ax1.annotate(f"{r['total_cases']/10_000:.0f}", (r["year"], r["total_cases"]/10_000),
                     fontsize=8, xytext=(0, 5), textcoords="offset points", ha="center")

    # ② 권역별 인구 1만명당 사건수 추세 (서울 강조)
    for col in pivot.columns:
        is_seoul = col == "서울"
        ax2.plot(pivot.index, pivot[col], "-", lw=2.2 if is_seoul else 0.9,
                 color="#C44E52" if is_seoul else "#999999",
                 label="서울" if is_seoul else None, zorder=3 if is_seoul else 1)
    ax2.set_title("권역별 인구 1만명당 본안사건 추세")
    ax2.set_xlabel("연도"); ax2.set_ylabel("인구 1만명당 사건수")
    ax2.legend(loc="upper right")
    fig.tight_layout()
    if save:
        out = OUTPUTS / "figures" / "fig_court_caseload_trend.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, bbox_inches="tight", dpi=120)
    return fig


def main(unit: str = "region13") -> None:
    d = build(unit)
    if d is None:
        print("[court_trend] 사건수 시계열이 1개 연도뿐 — 분석 생략.")
        print("  → 과거 사법연감을 data/raw/court/(YYYY)년_사건개황/에 추가 후 load_court.py 실행.")
        return
    out = OUTPUTS / "tables" / "court_caseload_trend.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tbl = d.pivot(index="region", columns="year", values="cases_per_10k").round(1)
    tbl.to_csv(out, encoding="utf-8-sig")
    fig(d)

    years = sorted(d["year"].unique())
    nat = d.groupby("year")["total_cases"].sum()
    print(f"[court_trend] 본안사건 시계열 {years[0]}~{years[-1]} ({len(years)}개 연도, {unit})")
    print(f"  전국 본안사건: {int(nat.iloc[0]):,}({years[0]}) → {int(nat.iloc[-1]):,}({years[-1]}) "
          f"({(nat.iloc[-1]/nat.iloc[0]-1)*100:+.1f}%)")
    print("\n[인구 1만명당 사건수] (권역 × 연도)")
    print(tbl.to_string())
    print(f"\n저장: outputs/tables/court_caseload_trend.csv, outputs/figures/fig_court_caseload_trend.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "region13")
