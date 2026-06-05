"""사법연감 2024 엑셀 → 법원별 사건 접수(A2) tidy long.

A2 정의: 변호사 1인당 연간 법원 사건 부담. 분자 = 제1심 '본안사건' 접수.
  - 본안사건(총설 01항 시트6 '지역별 인구 및 사건수') = 민사본안+형사공판+가사+행정 등 제1심.
    비송(등기·공탁)을 제외해 변호사 업무량을 대표. 이미 법원관내(=지역) 단위.
  - 보조: 민사 제1심 본안(02항 시트6), 형사 제1심 공판(07항 시트4)을 분야별로 추출.

법원관내명은 접두 도시 토큰으로 region13에 매핑(config.normalize_court).
법원관내 인구 합이 region10 KOSIS 인구와 정확히 일치함을 확인(검증 완료).

산출물(data/interim/):
    court_cases.csv   region13, year, total_cases, civil_main, criminal_trial

사용:
  python src/prepare/load_court.py
"""
from __future__ import annotations
import sys
import re
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW, INTERIM, REGION13_ORDER, normalize_court  # noqa: E402

COURT = RAW / "court" / "2024년_사건개황"
YEAR = 2024


def _cells(path: Path, sheet: str):
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)[sheet]
    return list(ws.iter_rows(values_only=True))


def _num(v) -> float | None:
    if v is None:
        return None
    s = re.sub(r"[^\d.\-]", "", str(v))
    return float(s) if s not in ("", "-", ".") else None


def parse_main_cases() -> pd.DataFrame:
    """총설 시트6: 법원관내별 본안사건 건수(col 5)."""
    rows = _cells(COURT / "(2024)01.개황.01항.총설.xlsx", "6")
    rec = []
    for r in rows:
        c0 = str(r[0]).strip() if r and r[0] else ""
        if c0.endswith("관내"):
            reg = normalize_court(c0)
            val = _num(r[5])  # 본안사건 건수
            if reg and val is not None:
                rec.append({"region13": reg, "total_cases": val})
    return pd.DataFrame(rec).groupby("region13", as_index=False)["total_cases"].sum()


def parse_civil() -> pd.DataFrame:
    """민사 시트6: 법원별 제1심 민사본안 접수(계, col 4)."""
    rows = _cells(COURT / "(2024)01.개황.02항.민사.xlsx", "6")
    rec = []
    for r in rows:
        c0 = str(r[0]).strip() if r and r[0] else ""
        reg = normalize_court(c0)
        if reg and "법원" in c0:
            val = _num(r[4])
            if val is not None:
                rec.append({"region13": reg, "civil_main": val})
    return pd.DataFrame(rec).groupby("region13", as_index=False)["civil_main"].sum()


def parse_criminal() -> pd.DataFrame:
    """형사 시트4: 법원별 제1심 형사공판 접수(계, col 1)."""
    rows = _cells(COURT / "(2024)01.개황.07항.형사.xlsx", "4")
    rec = []
    for r in rows:
        c0 = str(r[0]).strip() if r and r[0] else ""
        reg = normalize_court(c0)
        if reg:
            val = _num(r[1])
            if val is not None:
                rec.append({"region13": reg, "criminal_trial": val})
    return pd.DataFrame(rec).groupby("region13", as_index=False)["criminal_trial"].sum()


def main() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    main_df = parse_main_cases()
    civil = parse_civil()
    crim = parse_criminal()

    df = main_df.merge(civil, on="region13", how="left").merge(crim, on="region13", how="left")
    df["year"] = YEAR
    df = df.set_index("region13").reindex(REGION13_ORDER).reset_index()
    df = df[["region13", "year", "total_cases", "civil_main", "criminal_trial"]]
    df.to_csv(INTERIM / "court_cases.csv", index=False, encoding="utf-8-sig")

    print(f"법원 사건(A2): {len(df)}개 region13, 기준 {YEAR}년")
    print(df.to_string(index=False))
    print(f"\n검증: 본안사건 합계 = {df['total_cases'].sum():,.0f} (사법연감 전국 본안 1,106,526)")
    print(f"      민사본안 합계 = {df['civil_main'].sum():,.0f} / 형사공판 합계 = {df['criminal_trial'].sum():,.0f}")


if __name__ == "__main__":
    main()