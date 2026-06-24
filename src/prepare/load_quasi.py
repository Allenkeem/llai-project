# -*- coding: utf-8 -*-
"""유사법무직렬(법무사·변리사·세무사) 지역분포 로더.

선행연구(조민하 2021)는 변호사가 소송업무에 치중해 그 공백을 법무사·변리사·세무사 등
'유사법무직렬'이 메워 왔다고 길게 논했으나, 이들의 지역분포는 측정하지 않았다.
본 로더는 그 차원을 추가해 "무변촌(변호사 없는 지역)이 정말 법률 사각인가"를 재검토한다.

입력(선택): data/raw/quasi/quasi_legal.csv
  스키마: sido_name, year, beopmusa(법무사), byeollisa(변리사), semusa(세무사)
  (템플릿: quasi_legal.template.csv — 각 협회 공개통계로 채운 뒤 .csv로 저장)

산출물: data/interim/quasi_legal.csv  [sido_name, year, beopmusa, byeollisa, semusa, quasi_total]

사용:
  python src/prepare/load_quasi.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW, INTERIM, canonical_sido  # noqa: E402

SRC = RAW / "quasi" / "quasi_legal.csv"
PROFS = ["beopmusa", "byeollisa", "semusa"]


def load() -> pd.DataFrame | None:
    if not SRC.exists():
        print(f"[건너뜀] {SRC.relative_to(RAW.parent)} 없음 — 유사직렬 미수집(선택)")
        return None
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            df = pd.read_csv(SRC, encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    df["sido_name"] = df["sido_name"].map(canonical_sido)
    df = df.dropna(subset=["sido_name"])
    for c in PROFS:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["quasi_total"] = df[PROFS].sum(axis=1, min_count=1)
    out = df[["sido_name", "year", *PROFS, "quasi_total"]].sort_values(["sido_name", "year"])
    return out.reset_index(drop=True)


def main() -> None:
    df = load()
    if df is None:
        return
    INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_csv(INTERIM / "quasi_legal.csv", index=False, encoding="utf-8-sig")
    print(f"유사직렬: {len(df)}행, {df['year'].min()}~{df['year'].max()}, "
          f"시도 {df['sido_name'].nunique()}개")
    print(df[df["year"] == df["year"].max()].to_string(index=False))


if __name__ == "__main__":
    main()
