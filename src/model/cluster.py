"""K-means 클러스터링으로 접근성 유사 권역 그룹화.

입력: outputs/tables/llai.csv (compute_llai.py 산출)
특징벡터: A1n, A2n_inv, A3n (방향보정·정규화 지표)
최적 K: Elbow(관성) + Silhouette 함께 보고.

사용:
  python src/model/cluster.py            # 최신 연도 기준 클러스터링
  python src/model/cluster.py --demo     # 데모 데이터로 동작 검증
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OUTPUTS  # noqa: E402
from index.compute_llai import compute_llai, _demo_panel, DIRECTED  # noqa: E402


def choose_k(X: np.ndarray, k_min: int = 2, k_max: int = 6) -> pd.DataFrame:
    rows = []
    k_max = min(k_max, len(X) - 1)
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        sil = silhouette_score(X, km.labels_) if k < len(X) else np.nan
        rows.append({"k": k, "inertia": km.inertia_, "silhouette": sil})
    return pd.DataFrame(rows)


def main() -> None:
    if "--demo" in sys.argv:
        df, _ = compute_llai(_demo_panel())
        _cluster_one(df, unit="demo", save=False)
        return
    for unit in ("region10", "region13"):
        path = OUTPUTS / "tables" / f"llai_{unit}.csv"
        if not path.exists():
            raise SystemExit(f"{path} 없음. 먼저 compute_llai.py 실행.")
        _cluster_one(pd.read_csv(path), unit=unit, save=True)


def _cluster_one(df: pd.DataFrame, unit: str, save: bool) -> None:
    cur = df[df["year"] == df["year"].max()].copy()
    X = cur[DIRECTED].to_numpy()

    diag = choose_k(X)
    best_k = int(diag.loc[diag["silhouette"].idxmax(), "k"])

    km = KMeans(n_clusters=best_k, n_init=10, random_state=42).fit(X)
    cur["cluster"] = km.labels_
    order = cur.groupby("cluster")["LLAI"].mean().sort_values(ascending=False)
    rank = {c: i for i, c in enumerate(order.index)}
    cur["cluster_rank"] = cur["cluster"].map(rank)

    print(f"\n############ {unit}  (K={best_k}) ############")
    print("최적 K 진단:")
    print(diag.round(3).to_string(index=False))
    out = cur.sort_values(["cluster_rank", "LLAI"], ascending=[True, False])
    print("\n클러스터(0=고접근성):")
    print(out[["region", "A1", "A2", "A3", "LLAI", "cluster_rank"]]
          .round(2).to_string(index=False))

    if save:
        out.to_csv(OUTPUTS / "tables" / f"clusters_{unit}.csv", index=False, encoding="utf-8-sig")
        diag.to_csv(OUTPUTS / "tables" / f"cluster_k_diag_{unit}.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()