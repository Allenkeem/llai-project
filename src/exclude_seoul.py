"""서울 제외 비교 분석.

서울은 변호사 접근성에서 극단적 이상치라, 정규화·가중치·색스케일·클러스터링을
모두 지배한다. 서울을 제외하고 재산출하면 비수도권/지방 권역 간 상대 구조가 드러난다.

처리: 기준연도 단면에서 서울을 제외 → compute_llai(재정규화·재가중) → 재클러스터링.
산출물(접미사 _exseoul):
  outputs/tables/llai_{unit}_exseoul.csv, clusters_{unit}_exseoul.csv
  outputs/figures/fig*_{unit}_exseoul.png, fig7_map_{unit}_exseoul.png
  outputs/maps/llai_map_{unit}_exseoul.html

사용:
  python src/exclude_seoul.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PROCESSED, OUTPUTS  # noqa: E402
from index.compute_llai import compute_llai, NEED, DIRECTED  # noqa: E402
from model.cluster import choose_k  # noqa: E402
import viz  # noqa: E402
import map_viz  # noqa: E402

TAG = "_exseoul"


def build(unit: str) -> pd.DataFrame:
    p = pd.read_csv(PROCESSED / f"panel_{unit}.csv")
    ref = int(p.dropna(subset=NEED)["year"].max())
    cross = p[p["year"] == ref].dropna(subset=NEED).copy()
    cross = cross[cross["region"] != "서울"]   # 서울 제외 후 재정규화

    df, w = compute_llai(cross)
    df = df.sort_values("LLAI", ascending=False)

    # 재클러스터링
    X = df[DIRECTED].to_numpy()
    diag = choose_k(X)
    best_k = int(diag.loc[diag["silhouette"].idxmax(), "k"])
    km = KMeans(n_clusters=best_k, n_init=10, random_state=42).fit(X)
    df["cluster"] = km.labels_
    order = df.groupby("cluster")["LLAI"].mean().sort_values(ascending=False)
    df["cluster_rank"] = df["cluster"].map({c: i for i, c in enumerate(order.index)})

    out = OUTPUTS / "tables"
    # llai 파일은 클러스터 컬럼 제외(viz._load가 clusters 파일과 병합하므로 중복 방지)
    df.drop(columns=["cluster", "cluster_rank"]).to_csv(
        out / f"llai_{unit}{TAG}.csv", index=False, encoding="utf-8-sig")
    df.to_csv(out / f"clusters_{unit}{TAG}.csv", index=False, encoding="utf-8-sig")
    w.to_csv(out / f"llai_weights_{unit}{TAG}.csv", encoding="utf-8-sig")

    print(f"\n############ {unit} · 서울 제외 (n={len(df)}, K={best_k}) ############")
    print("가중치:"); print(w.round(3).to_string())
    cols = ["region", "A1", "A2", "A3", "LLAI", "cluster_rank"]
    print(df[cols].round(2).to_string(index=False))
    return df


def main() -> None:
    viz.setup_font()
    for unit in ("region10", "region13"):
        build(unit)
        for f in (viz.fig_llai_ranking, viz.fig_scatter_a1_a2,
                  viz.fig_subindicators, viz.fig_weights):
            f(unit, tag=TAG)
        map_viz.make_static(unit, tag=TAG)
        map_viz.make_interactive(unit, tag=TAG)
    import matplotlib.pyplot as plt
    plt.close("all")
    print("\n서울 제외 도표·지도 저장 완료 (접미사 _exseoul)")


if __name__ == "__main__":
    main()
