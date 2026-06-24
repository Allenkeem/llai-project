# -*- coding: utf-8 -*-
"""'무변촌' 재정의 — 변호사 부족 지역을 유사법무직렬이 메우는가.

선행연구(조민하 2021)는 변호사가 소송에 치중해 법무사·변리사·세무사가 그 공백을
메워 왔다고 논했다. 본 분석은 변호사 밀도(A1)가 낮은 권역에서 유사직렬 밀도(B1)가
높은지(보완) 아니면 함께 낮은지(진짜 사각)를 본다.

  A1 = 개업변호사 / 인구 ×10만
  B1 = 유사직렬(법무사+변리사+세무사) / 인구 ×10만
  통합 법률인력 밀도 = (변호사 + 유사직렬) / 인구 ×10만

데이터(quasi_total)가 패널에 없으면 graceful skip.
산출물: outputs/tables/quasi_legal_compare.csv · outputs/figures/fig_quasi_legal.png

사용:  python src/model/quasi_legal.py  [region13|region10]
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROCESSED, OUTPUTS  # noqa: E402


def _latest(panel: pd.DataFrame, col: str) -> pd.Series | None:
    if col not in panel.columns:
        return None
    g = panel.dropna(subset=[col]).sort_values("year")
    return None if g.empty else g.groupby("region")[col].last()


def build(unit: str = "region13") -> pd.DataFrame | None:
    panel = pd.read_csv(PROCESSED / f"panel_{unit}.csv")
    quasi = _latest(panel, "quasi_total")
    if quasi is None:
        return None
    pop = _latest(panel, "population")
    law = _latest(panel, "practicing")
    df = pd.concat([pop.rename("population"), law.rename("practicing"),
                    quasi.rename("quasi_total")], axis=1).dropna()
    df["A1_변호사"] = df["practicing"] / df["population"] * 100_000
    df["B1_유사직렬"] = df["quasi_total"] / df["population"] * 100_000
    df["통합_법률인력"] = (df["practicing"] + df["quasi_total"]) / df["population"] * 100_000
    df["변호사_순위"] = df["A1_변호사"].rank(ascending=False).astype(int)
    df["통합_순위"] = df["통합_법률인력"].rank(ascending=False).astype(int)
    df["순위변화"] = df["변호사_순위"] - df["통합_순위"]  # +면 유사직렬 포함 시 상승
    return df.sort_values("A1_변호사", ascending=False).reset_index().rename(columns={"index": "region"})


def fig(df: pd.DataFrame, save: bool = True):
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.scatter(df["A1_변호사"], df["B1_유사직렬"], s=60, color="#2c7fb8")
    for _, r in df.iterrows():
        ax.annotate(r["region"], (r["A1_변호사"], r["B1_유사직렬"]), fontsize=8,
                    xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("변호사 밀도 A1 (10만명당)")
    ax.set_ylabel("유사직렬 밀도 B1 (10만명당)")
    ax.set_title("변호사 부족 지역을 유사직렬이 메우나 — A1 vs B1")
    fig.tight_layout()
    if save:
        out = OUTPUTS / "figures" / "fig_quasi_legal.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, bbox_inches="tight", dpi=120)
    return fig


def main(unit: str = "region13") -> None:
    df = build(unit)
    if df is None:
        print("[quasi_legal] 유사직렬 데이터 없음 — 분석 생략.")
        print("  → data/raw/quasi/quasi_legal.csv 채운 뒤 load_quasi.py·build_panel.py 실행.")
        return
    out = OUTPUTS / "tables" / "quasi_legal_compare.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.round(2).to_csv(out, index=False, encoding="utf-8-sig")
    fig(df)

    corr = df["A1_변호사"].corr(df["B1_유사직렬"])
    print(df[["region", "A1_변호사", "B1_유사직렬", "통합_법률인력", "순위변화"]].round(1).to_string(index=False))
    print(f"\ncorr(A1 변호사, B1 유사직렬) = {corr:+.3f}")
    print("  음(−)이면 변호사 적은 곳에 유사직렬 많음(보완), 양(+)이면 함께 쏠림(보완 안 됨).")
    print("저장: outputs/tables/quasi_legal_compare.csv, outputs/figures/fig_quasi_legal.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "region13")
