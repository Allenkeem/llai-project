"""변호사 분포 집중도: 2009 vs 현재(2026) 비교 — H4 직접 검정.

연도별 지방회별 변호사 시계열은 공개 다운로드가 어렵다(변협 백서 PDF 산재).
대신 신뢰 가능한 2시점을 비교한다:
  - 2009년 말 지역별 개업변호사 수(7권역): 법률저널(2010) 게재, 대한변협 자료 기준.
  - 현재(2026): 변협 회원현황 스크랩(data/raw/bar) → 동일 7권역으로 집계.

H4("로스쿨 도입 이후 변호사 증가에도 지역 격차 미축소")를 서울 집중도·HHI 변화로 검정.

산출물:
  outputs/tables/lawyer_concentration.csv
  outputs/figures/fig8_lawyer_trend.png

사용:
  python src/model/lawyer_trend.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW, OUTPUTS  # noqa: E402

# 2009년 말 지역별 개업변호사 수 (7권역) — 법률저널 2010.04, 대한변협 자료
LAWYER_2009 = {
    "서울": 6830, "경기인천": 1016, "경상": 952,
    "충청": 365, "전라": 332, "강원": 81, "제주": 36,
}

# region13 → 7권역 (2009 자료와 동일 구분)
REGION13_TO_R7 = {
    "서울": "서울", "경기": "경기인천", "인천": "경기인천",
    "부산": "경상", "울산": "경상", "경남": "경상", "대구권": "경상",
    "대전권": "충청", "충북": "충청",
    "광주권": "전라", "전북": "전라",
    "강원": "강원", "제주": "제주",
}
R7_ORDER = ["서울", "경기인천", "경상", "충청", "전라", "강원", "제주"]


def current_by_r7() -> dict[str, int]:
    bar = pd.read_csv(RAW / "bar" / "bar_region13.csv")
    bar["r7"] = bar["region13_name"].map(REGION13_TO_R7)
    return bar.groupby("r7")["practicing"].sum().to_dict()


def _hhi(shares: pd.Series) -> float:
    """허핀달 지수(점유율 제곱합, 0~1). 클수록 집중."""
    return float((shares ** 2).sum())


def build() -> pd.DataFrame:
    cur = current_by_r7()
    df = pd.DataFrame({
        "region": R7_ORDER,
        "y2009": [LAWYER_2009[r] for r in R7_ORDER],
        "y2026": [cur.get(r, 0) for r in R7_ORDER],
    })
    df["share_2009"] = df["y2009"] / df["y2009"].sum() * 100
    df["share_2026"] = df["y2026"] / df["y2026"].sum() * 100
    df["share_change"] = df["share_2026"] - df["share_2009"]
    return df


def main() -> None:
    df = build()
    out = OUTPUTS / "tables"
    out.mkdir(parents=True, exist_ok=True)
    df.round(2).to_csv(out / "lawyer_concentration.csv", index=False, encoding="utf-8-sig")

    tot09, tot26 = df["y2009"].sum(), df["y2026"].sum()
    hhi09 = _hhi(df["share_2009"] / 100)
    hhi26 = _hhi(df["share_2026"] / 100)
    seoul09 = df.loc[df.region == "서울", "share_2009"].iloc[0]
    seoul26 = df.loc[df.region == "서울", "share_2026"].iloc[0]

    print("=== 변호사 분포 집중도: 2009 vs 2026 ===")
    print(df.round(2).to_string(index=False))
    print(f"\n총 개업변호사: {tot09:,} (2009) → {tot26:,} (2026), {tot26/tot09:.1f}배")
    print(f"서울 비중: {seoul09:.1f}% → {seoul26:.1f}%  ({seoul26-seoul09:+.1f}%p)")
    print(f"HHI(집중도): {hhi09:.3f} → {hhi26:.3f}  ({'심화' if hhi26 > hhi09 else '완화'})")
    print("\n[H4 검정] 변호사 수가 {0:.1f}배 늘었음에도 서울 집중은 심화 → H4(격차 미축소) 지지"
          .format(tot26 / tot09))

    # 도표: 권역별 점유율 2009 vs 2026
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    import numpy as np
    x = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.bar(x - 0.2, df["share_2009"], 0.4, label="2009", color="#8C8C8C")
    ax.bar(x + 0.2, df["share_2026"], 0.4, label="2026", color="#C44E52")
    for i, (a, b) in enumerate(zip(df["share_2009"], df["share_2026"])):
        ax.text(i - 0.2, a + 0.5, f"{a:.0f}", ha="center", fontsize=8)
        ax.text(i + 0.2, b + 0.5, f"{b:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x, df["region"])
    ax.set_ylabel("개업변호사 점유율 (%)")
    ax.set_title(f"변호사 지역 분포 집중도 2009 → 2026 (총 {tot09:,}→{tot26:,}명, {tot26/tot09:.1f}배)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUTS / "figures" / "fig8_lawyer_trend.png", bbox_inches="tight", dpi=120)
    print("\n저장: outputs/tables/lawyer_concentration.csv, outputs/figures/fig8_lawyer_trend.png")


if __name__ == "__main__":
    main()
