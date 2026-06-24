# -*- coding: utf-8 -*-
"""구조요인 → 변호사 밀도(A1) 선형회귀 — 석사논문 방법론과의 다리.

[배경] 조민하(2021, 서울대 행정대학원) 석사논문은 '지역별 인구 만명당 변호인 수'를
종속변수로, 1인당 총생산(GRDP)·판사수를 독립변수로 패널 고정효과 회귀를 했다.
본 프로젝트(LLAI)는 지수·진단 중심이라 회귀가 없었다 — 이 모듈이 그 빈자리를 메운다.

[설계] 표본이 13권역(횡단면)이라 추론이 아니라 '방향·상대 크기' 탐색이다(정직히 명시).
  - 타깃   : A1 = 인구 10만명당 개업변호사 수  (논문 종속변수와 동일 개념)
  - 피처   : grdp_per_capita (논문 독립변수1: 소득)
             cases_per_capita = 법원 본안사건 / 인구  (수요 대리; 논문의 '판사수' 자리)
             log_population   (지역 규모 통제)
  - 표준화 : 단위가 다른 피처를 StandardScaler로 맞춰 계수를 비교 가능하게.

[해석 포인트] GRDP 계수의 부호·크기, 그리고 cases_per_capita 계수가 크면
'변호사가 사건(수요) 많은 곳으로 끌려간다'는 demand-pull 가설(보고서 4.7)과 정합.

산출물:
  outputs/tables/regression_structural.csv
  outputs/figures/fig_regression_coef.png

사용:
  python src/model/regression.py            # region13
  python src/model/regression.py region10   # region10
"""
from __future__ import annotations
import sys
from pathlib import Path

try:  # Windows 콘솔(cp949)에서도 한글·기호 출력 안전하게
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROCESSED, OUTPUTS  # noqa: E402

# 탐색적(demand-pull) 모형: 어떤 구조요인이 변호사 밀도와 함께 움직이나
FEATURES = ["grdp_per_capita", "cases_per_capita", "businesses_per_capita", "log_population"]
# 논문(조민하 2021) 재현 모형: 변호사밀도 ~ GRDP + 판사수
THESIS_FEATURES = ["grdp_per_capita", "judges"]
LABEL = {
    "grdp_per_capita": "1인당 GRDP",
    "cases_per_capita": "인구당 사건수(수요)",
    "businesses_per_capita": "인구당 사업체수(수요)",
    "judges": "판사수",
    "log_population": "log 인구(규모)",
}


def _latest_panel_col(unit: str, col: str) -> pd.Series | None:
    """패널에서 권역별 '가장 최근 결측 아닌' 값. (LLAI 단면연도엔 GRDP 등 결측일 수 있음)"""
    panel = pd.read_csv(PROCESSED / f"panel_{unit}.csv")
    if col not in panel.columns:
        return None
    g = panel.dropna(subset=[col]).sort_values("year")
    if g.empty:
        return None
    return g.groupby("region")[col].last()


def build_features(unit: str = "region13") -> pd.DataFrame:
    """LLAI 단면(타깃 A1·인구·사건) + 패널 최신 구조요인 → 회귀용 피처 프레임.

    사업체수·판사수는 패널에 있을 때만 자동 포함(없으면 해당 피처 생략).
    """
    cross = pd.read_csv(OUTPUTS / "tables" / f"llai_{unit}.csv")
    df = cross[["region", "population", "total_cases", "A1"]].copy()
    grdp = _latest_panel_col(unit, "grdp_per_capita")
    if grdp is not None:
        df = df.merge(grdp.rename("grdp_per_capita"), on="region", how="left")
    df["cases_per_capita"] = df["total_cases"] / df["population"]
    df["log_population"] = np.log(df["population"])

    biz = _latest_panel_col(unit, "business_count")
    if biz is not None:
        df = df.merge(biz.rename("business_count"), on="region", how="left")
        df["businesses_per_capita"] = df["business_count"] / df["population"]

    judges = _latest_panel_col(unit, "judges")
    if judges is not None:
        df = df.merge(judges.rename("judges"), on="region", how="left")
    return df


def fit_structural(df: pd.DataFrame, target: str = "A1", features: list | None = None) -> dict:
    """구조요인 → 타깃 표준화 선형회귀. 표준화 계수·R² 반환 + 보기 좋게 출력."""
    feats = [c for c in (features or FEATURES) if c in df.columns]
    data = df.dropna(subset=feats + [target])
    X = StandardScaler().fit_transform(data[feats])
    y = data[target].to_numpy()

    model = LinearRegression().fit(X, y)
    r2 = model.score(X, y)
    coefs = dict(zip(feats, np.round(model.coef_, 3)))

    print(f"[regression] {target} ~ {' + '.join(feats)}  (n={len(data)})")
    print(f"  R² = {r2:.3f}   (표본 작아 탐색적 — 통계적 유의성 아닌 방향·크기로 해석)")
    for f, c in sorted(coefs.items(), key=lambda kv: -abs(kv[1])):
        print(f"  표준화계수 {LABEL.get(f, f):16s} = {c:+.3f} {'↑' if c > 0 else '↓'}")
    return {"coef": coefs, "r2": r2, "n": len(data), "features": feats, "target": target}


def fig_coef(result: dict, save: bool = True):
    """표준화 회귀계수 막대 (양=파랑·음=빨강)."""
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    items = sorted(result["coef"].items(), key=lambda kv: kv[1])
    names = [LABEL.get(k, k) for k, _ in items]
    vals = [v for _, v in items]
    colors = ["#C44E52" if v < 0 else "#2c7fb8" for v in vals]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.barh(names, vals, color=colors)
    ax.axvline(0, color="gray", lw=0.8)
    ax.set_xlabel("표준화 회귀계수 (크기=상대 영향, 부호=방향)")
    ax.set_title(f"구조요인 → 변호사 밀도(A1)  (R²={result['r2']:.2f}, n={result['n']})")
    fig.tight_layout()
    if save:
        out = OUTPUTS / "figures" / "fig_regression_coef.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, bbox_inches="tight", dpi=120)
    return fig


def _save_table(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"feature": f, "std_coef": c} for f, c in result["coef"].items()]
        + [{"feature": "R2", "std_coef": round(result["r2"], 3)},
           {"feature": "n", "std_coef": result["n"]}]
    ).to_csv(path, index=False, encoding="utf-8-sig")


def main(unit: str = "region13") -> None:
    df = build_features(unit)

    print("── [탐색적] demand-pull 구조요인 회귀 ──")
    result = fit_structural(df, target="A1")
    fig_coef(result)
    _save_table(result, OUTPUTS / "tables" / "regression_structural.csv")
    print("저장: outputs/tables/regression_structural.csv, outputs/figures/fig_regression_coef.png")

    # 논문(조민하 2021) 재현: 변호사밀도 ~ GRDP + 판사수 (판사수 데이터 있을 때만)
    if "judges" in df.columns:
        print("\n── [논문 재현] 변호사밀도 ~ GRDP + 판사수 (조민하 2021 모형) ──")
        rep = fit_structural(df, target="A1", features=THESIS_FEATURES)
        _save_table(rep, OUTPUTS / "tables" / "regression_thesis_replication.csv")
        print("저장: outputs/tables/regression_thesis_replication.csv")
    else:
        print("\n[안내] 판사수(data/raw/court/judges_by_region.csv) 추가 시 "
              "논문 회귀(변호사밀도~GRDP+판사수) 재현이 자동 활성화됩니다.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "region13")
