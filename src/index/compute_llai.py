"""종합 법률 접근성 지수(LLAI) 산출.

세부지표:
  A1 변호사 접근성 = 인구 10만명당 개업변호사 수          (↑ 좋음)
  A2 사건 부담     = 변호사 1인당 연간 법원 사건 수        (↓ 좋음)
  A3 취약계층 접근성 = 법률구조 건수 / 저소득층 인구         (↑ 좋음)

절차:
  1) A1~A3 계산
  2) Min-Max 정규화 [0,1]  (A2는 방향 보정: 1 - A2n 사용)
  3) 가중치 3종 산출·비교: 균등 / 엔트로피 / PCA
  4) LLAI = Σ w_i · (방향보정 지표) × 100

가중치를 3종 병기하는 이유: 지표가 3개뿐이라 PCA 단일가중치는 표본에 민감하다.
강건성(robustness) 확인을 위해 함께 보고한다.

사용:
  python src/index/compute_llai.py                 # data/processed/panel.csv 사용
  python src/index/compute_llai.py --demo          # 내장 데모 패널로 동작 검증
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.decomposition import PCA

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROCESSED, OUTPUTS, REGION13_ORDER  # noqa: E402

SUB = ["A1", "A2", "A3"]
DIRECTED = ["A1n", "A2n_inv", "A3n"]  # 모두 '클수록 접근성 좋음' 방향


def compute_subindices(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    df["A1"] = df["practicing"] / df["population"] * 100_000
    df["A2"] = df["total_cases"] / df["practicing"]
    df["A3"] = df["aid_cases"] / df["low_income_pop"]
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    scaler = MinMaxScaler()
    df[["A1n", "A2n", "A3n"]] = scaler.fit_transform(df[SUB])
    df["A2n_inv"] = 1 - df["A2n"]  # 사건부담은 낮을수록 좋음
    return df


def weights_equal() -> np.ndarray:
    return np.array([1 / 3, 1 / 3, 1 / 3])


def weights_entropy(X: np.ndarray) -> np.ndarray:
    """엔트로피 가중법. X: (n, k) 방향보정·[0,1] 지표 행렬."""
    P = X + 1e-12
    P = P / P.sum(axis=0, keepdims=True)
    n = X.shape[0]
    k = -1.0 / np.log(n)
    E = k * (P * np.log(P)).sum(axis=0)   # 각 지표 엔트로피
    d = 1 - E                              # 다양성(정보량)
    return d / d.sum()


def weights_pca(X: np.ndarray) -> np.ndarray:
    """PCA 1주성분 적재량(절대값) 기반 가중치."""
    Z = StandardScaler().fit_transform(X)
    pca = PCA(n_components=1).fit(Z)
    load = np.abs(pca.components_[0])
    return load / load.sum()


def compute_llai(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = normalize(compute_subindices(panel))
    X = df[DIRECTED].to_numpy()

    wsets = {
        "equal": weights_equal(),
        "entropy": weights_entropy(X),
        "pca": weights_pca(X),
    }
    for name, w in wsets.items():
        df[f"LLAI_{name}"] = (X @ w) * 100

    # 기본 LLAI는 엔트로피(권장) — 보고서에서 3종 비교 후 확정
    df["LLAI"] = df["LLAI_entropy"]

    wtable = pd.DataFrame(wsets, index=["A1(변호사)", "A2(사건부담,역)", "A3(취약계층)"]).T
    return df, wtable


def _demo_panel() -> pd.DataFrame:
    """동작 검증용 데모 패널(실제 데이터 아님). 13권역 × 1개 연도."""
    rng = np.random.default_rng(20210717)
    n = len(REGION13_ORDER)
    return pd.DataFrame({
        "region": REGION13_ORDER,
        "year": 2024,
        "practicing": rng.integers(150, 25000, n),
        "population": rng.integers(600_000, 13_000_000, n),
        "total_cases": rng.integers(50_000, 2_000_000, n),
        "low_income_pop": rng.integers(50_000, 1_500_000, n),
        "aid_cases": rng.integers(2_000, 80_000, n),
    })


NEED = ["practicing", "population", "total_cases", "low_income_pop", "aid_cases"]


def run_unit(unit: str) -> None:
    path = PROCESSED / f"panel_{unit}.csv"
    if not path.exists():
        raise SystemExit(f"{path} 없음. 먼저 build_panel.py 실행.")
    panel = pd.read_csv(path)
    miss = set(NEED) - set(panel.columns)
    if miss:
        raise SystemExit(f"패널 컬럼 누락: {miss}")

    # 횡단면: LLAI 입력이 모두 존재하는 최신 연도(변호사 스냅샷 기준연도)
    ok = panel.dropna(subset=NEED)
    ref = int(ok["year"].max())
    cross = panel[panel["year"] == ref].dropna(subset=NEED).copy()

    df, wtable = compute_llai(cross)
    df = df.sort_values("LLAI", ascending=False)

    print(f"\n############ {unit}  (기준연도 {ref}, {len(df)}개 권역) ############")
    print("가중치(행=방식): ")
    print(wtable.round(3).to_string())
    cols = ["region", "A1", "A2", "A3", "LLAI_equal", "LLAI_entropy", "LLAI_pca", "LLAI"]
    print("\nLLAI 순위:")
    print(df[cols].round(2).to_string(index=False))

    out = OUTPUTS / "tables"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / f"llai_{unit}.csv", index=False, encoding="utf-8-sig")
    wtable.to_csv(out / f"llai_weights_{unit}.csv", encoding="utf-8-sig")


def main() -> None:
    if "--demo" in sys.argv:
        print("[DEMO] 내장 데모 패널 동작 검증\n")
        df, wtable = compute_llai(_demo_panel())
        print(wtable.round(3).to_string())
        print(df.sort_values("LLAI", ascending=False)[
            ["region", "A1", "A2", "A3", "LLAI"]].round(2).to_string(index=False))
        return
    for unit in ("region10", "region13"):
        run_unit(unit)
    print(f"\n저장: outputs/tables/llai_region10.csv, llai_region13.csv")


if __name__ == "__main__":
    main()