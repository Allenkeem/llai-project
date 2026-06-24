# -*- coding: utf-8 -*-
"""[패널화] 변호사 집중도 '추세' — H4를 2시점에서 연도별 시계열로 확장.

lawyer_trend.py는 2009 vs 2026 두 시점만 비교한다. 이 모듈은 Wayback으로 복원한
연도별 변호사 수(scrape_bar_history)를 region13으로 집계해, 서울·수도권 점유율과
집중도(HHI)가 시간에 따라 어떻게 변하는지 '추세'로 보여준다.

산출물:
  outputs/tables/lawyer_concentration_trend.csv
  outputs/figures/fig_lawyer_concentration_trend.png

사용:
  python src/model/lawyer_panel.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW, OUTPUTS, BAR_TO_REGION13  # noqa: E402

CAPITAL_R13 = {"서울", "경기", "인천"}


def _history_to_region13() -> pd.DataFrame:
    """bar_history.csv(없으면 복원) + 현재 스냅샷 → [region13, year, practicing] 연도별."""
    from collect.scrape_bar_history import fetch_history
    hist = fetch_history()
    if hist is None or not len(hist):
        return pd.DataFrame()

    rows = [hist.assign(region13=hist["bar_association"].map(BAR_TO_REGION13))]

    # 현재(라이브) 스냅샷을 최신 연도로 보강
    cur_path = RAW / "bar" / "bar_region13.csv"
    if cur_path.exists():
        cur = pd.read_csv(cur_path)
        year = int(str(cur["asof"].iloc[0])[:4]) if "asof" in cur.columns else 2026
        rows.append(pd.DataFrame({
            "region13": cur["region13_name"], "year": year, "practicing": cur["practicing"]}))

    df = pd.concat(rows, ignore_index=True).dropna(subset=["region13"])
    return (df.groupby(["region13", "year"], as_index=False)["practicing"].sum()
              .drop_duplicates(["region13", "year"], keep="last"))


def concentration_trend(reg: pd.DataFrame) -> pd.DataFrame:
    """연도별 총변호사·서울/수도권 점유율·HHI."""
    out = []
    for y, g in reg.groupby("year"):
        tot = g["practicing"].sum()
        if not tot:
            continue
        seoul = g.loc[g["region13"] == "서울", "practicing"].sum()
        cap = g.loc[g["region13"].isin(CAPITAL_R13), "practicing"].sum()
        hhi = ((g["practicing"] / tot) ** 2).sum()
        out.append({"year": int(y), "총변호사": int(tot),
                    "서울점유율": round(seoul / tot * 100, 1),
                    "수도권점유율": round(cap / tot * 100, 1),
                    "HHI": round(float(hhi), 3)})
    return pd.DataFrame(out).sort_values("year")


def fig_trend(trend: pd.DataFrame, save: bool = True):
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.plot(trend["year"], trend["서울점유율"], "o-", color="#C44E52", label="서울 점유율")
    ax.plot(trend["year"], trend["수도권점유율"], "s-", color="#2c7fb8", label="수도권 점유율")
    ax.set_ylabel("변호사 점유율 (%)")
    ax.set_xlabel("연도")
    ax2 = ax.twinx()
    ax2.bar(trend["year"], trend["총변호사"], alpha=0.15, color="gray")
    ax2.set_ylabel("총 개업변호사 수")
    ax.set_title("변호사 서울·수도권 집중도 추세 (Wayback 복원, region13)")
    ax.legend(loc="center left")
    fig.tight_layout()
    if save:
        out = OUTPUTS / "figures" / "fig_lawyer_concentration_trend.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, bbox_inches="tight", dpi=120)
    return fig


def main() -> None:
    reg = _history_to_region13()
    if reg.empty:
        print("[lawyer_panel] 변호사 히스토리 없음(네트워크 필요) — 추세 생략.")
        print("  → 인터넷 연결 후 'python src/collect/scrape_bar_history.py' 로 캐시 생성 후 재실행.")
        return
    trend = concentration_trend(reg)
    out = OUTPUTS / "tables" / "lawyer_concentration_trend.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    trend.to_csv(out, index=False, encoding="utf-8-sig")
    fig_trend(trend)

    print("[lawyer_panel] 변호사 집중도 추세:")
    print(trend.to_string(index=False))
    if len(trend) >= 2:
        a, b = trend.iloc[0], trend.iloc[-1]
        print(f"\n[요약] {int(a['year'])}->{int(b['year'])}: 총 {a['총변호사']:,}->{b['총변호사']:,}명, "
              f"서울 {a['서울점유율']}%->{b['서울점유율']}% "
              f"({'심화' if b['서울점유율'] > a['서울점유율'] else '완화'})")
    print("\n저장: outputs/tables/lawyer_concentration_trend.csv, "
          "outputs/figures/fig_lawyer_concentration_trend.png")


if __name__ == "__main__":
    main()
