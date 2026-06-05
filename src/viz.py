"""LLAI 분석 시각화. outputs/figures/ 에 PNG 저장.

생성 도표:
  fig1_llai_ranking_{unit}.png    권역별 LLAI 순위 (가로 막대, 클러스터 색)
  fig2_scatter_a1_a2_{unit}.png   변호사 접근성 vs 사건부담 산점도 (H2)
  fig3_subindicators_{unit}.png   A1/A2/A3 정규화 히트맵
  fig4_weights_{unit}.png         가중치 3종별 LLAI 비교
  fig5_h1_box.png                 수도권 vs 비수도권 변호사 1인당 인구 (H1)
  fig6_h4_trend.png               법률구조 격차(변동계수) 추세 (H4)

사용:
  python src/viz.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUTS, INTERIM  # noqa: E402

FIG = OUTPUTS / "figures"
CAPITAL = {"서울", "인천", "경기"}


def setup_font() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110


def _load(unit: str) -> pd.DataFrame:
    llai = pd.read_csv(OUTPUTS / "tables" / f"llai_{unit}.csv")
    clu = pd.read_csv(OUTPUTS / "tables" / f"clusters_{unit}.csv")[["region", "cluster_rank"]]
    return llai.merge(clu, on="region", how="left")


def fig_llai_ranking(unit: str, save=True):
    df = _load(unit).sort_values("LLAI")
    colors = plt.cm.RdYlBu(np.linspace(0.15, 0.85, df["cluster_rank"].nunique()))
    c = [colors[int(r)] for r in df["cluster_rank"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(df["region"], df["LLAI"], color=c)
    for y, v in enumerate(df["LLAI"]):
        ax.text(v + 1, y, f"{v:.1f}", va="center", fontsize=9)
    ax.set_xlabel("LLAI (0~100)")
    ax.set_title(f"권역별 종합 법률 접근성 지수 LLAI ({unit}, 2024)")
    ax.margins(x=0.12)
    fig.tight_layout()
    if save:
        fig.savefig(FIG / f"fig1_llai_ranking_{unit}.png", bbox_inches="tight")
    return fig


def fig_scatter_a1_a2(unit: str, save=True):
    df = _load(unit)
    fig, ax = plt.subplots(figsize=(7, 5.5))
    sc = ax.scatter(df["A1"], df["A2"], s=df["LLAI"] * 4 + 30,
                    c=df["cluster_rank"], cmap="RdYlBu_r", edgecolor="k", alpha=0.85)
    for _, r in df.iterrows():
        ax.annotate(r["region"], (r["A1"], r["A2"]), fontsize=8,
                    xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("A1: 인구 10만명당 변호사 수 (↑ 좋음)")
    ax.set_ylabel("A2: 변호사 1인당 사건 수 (↓ 좋음)")
    ax.set_title(f"변호사 접근성 vs 사건 부담 ({unit})\n점 크기=LLAI, 색=클러스터")
    fig.tight_layout()
    if save:
        fig.savefig(FIG / f"fig2_scatter_a1_a2_{unit}.png", bbox_inches="tight")
    return fig


def fig_subindicators(unit: str, save=True):
    df = _load(unit).sort_values("LLAI", ascending=False)
    M = df.set_index("region")[["A1n", "A2n_inv", "A3n"]]
    M.columns = ["A1 변호사", "A2 사건부담(역)", "A3 취약계층"]
    fig, ax = plt.subplots(figsize=(6, 5.5))
    im = ax.imshow(M.values, cmap="YlGnBu", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(3), M.columns, fontsize=9)
    ax.set_yticks(range(len(M)), M.index, fontsize=9)
    for i in range(len(M)):
        for j in range(3):
            ax.text(j, i, f"{M.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title(f"정규화 세부지표 (0~1, {unit})")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    if save:
        fig.savefig(FIG / f"fig3_subindicators_{unit}.png", bbox_inches="tight")
    return fig


def fig_weights(unit: str, save=True):
    df = _load(unit).sort_values("LLAI_entropy", ascending=False)
    x = np.arange(len(df))
    w = 0.26
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - w, df["LLAI_equal"], w, label="균등")
    ax.bar(x, df["LLAI_entropy"], w, label="엔트로피")
    ax.bar(x + w, df["LLAI_pca"], w, label="PCA")
    ax.set_xticks(x, df["region"], rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("LLAI")
    ax.set_title(f"가중치 방식별 LLAI 비교 ({unit})")
    ax.legend()
    fig.tight_layout()
    if save:
        fig.savefig(FIG / f"fig4_weights_{unit}.png", bbox_inches="tight")
    return fig


def fig_h1_box(save=True):
    df = _load("region13")
    df["pop_per_lawyer"] = df["population"] / df["practicing"]
    df["grp"] = np.where(df["region"].isin(CAPITAL), "수도권", "비수도권")
    fig, ax = plt.subplots(figsize=(5.5, 5))
    groups = ["수도권", "비수도권"]
    data = [df[df.grp == g]["pop_per_lawyer"].values for g in groups]
    ax.boxplot(data, tick_labels=groups, widths=0.5)
    for i, g in enumerate(groups, 1):
        ys = df[df.grp == g]["pop_per_lawyer"].values
        ax.scatter(np.full(len(ys), i), ys, color="crimson", alpha=0.6, zorder=3)
    ax.set_ylabel("변호사 1인당 인구 (명)")
    ax.set_title("H1: 수도권 vs 비수도권 변호사 1인당 인구")
    fig.tight_layout()
    if save:
        fig.savefig(FIG / "fig5_h1_box.png", bbox_inches="tight")
    return fig


def fig_h4_trend(save=True):
    klac = pd.read_csv(INTERIM / "klac_legalaid.csv")
    cv = klac.groupby("year")["aid_cases"].agg(lambda s: s.std() / s.mean())
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(cv.index, cv.values, "o-", color="#C44E52")
    z = np.polyfit(cv.index, cv.values, 1)
    ax.plot(cv.index, np.poly1d(z)(cv.index), "--", color="gray",
            label=f"추세 {z[0]:+.4f}/년")
    ax.set_xlabel("연도")
    ax.set_ylabel("변동계수 (격차)")
    ax.set_title("H4: 법률구조 권역 격차 추세 (변동계수)")
    ax.legend()
    fig.tight_layout()
    if save:
        fig.savefig(FIG / "fig6_h4_trend.png", bbox_inches="tight")
    return fig


def main() -> None:
    setup_font()
    FIG.mkdir(parents=True, exist_ok=True)
    for unit in ("region13", "region10"):
        fig_llai_ranking(unit)
        fig_scatter_a1_a2(unit)
        fig_subindicators(unit)
        fig_weights(unit)
    fig_h1_box()
    fig_h4_trend()
    plt.close("all")
    saved = sorted(p.name for p in FIG.glob("*.png"))
    print(f"저장된 도표 {len(saved)}개 → outputs/figures/")
    for s in saved:
        print("  -", s)


if __name__ == "__main__":
    main()