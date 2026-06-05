"""공단 법률구조 현황(지역별) xlsx → tidy long.

원본 구조: 행=시점(반기)×{인원수,건수}, 열=10 도단위 지역.
A3는 '이용 건수' 기준 → 건수(건) 행을 추출하고, 상+하반기를 합산해 연 단위로.
지역은 region10(10 도단위)으로 매핑.

산출물(data/interim/):
    klac_legalaid.csv     region10, year, aid_cases   (민사 등 법률구조, 연 합산)

주의:
  - 민사: 2012~2025 (풍부)  /  형사: 2012~2020 (불완전) → A3 기본은 민사 사용.
  - 광역시가 인접 도에 통합된 10 도단위가 원천 해상도의 한계.

사용:
  python src/prepare/load_klac.py
"""
from __future__ import annotations
import sys
import re
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW, INTERIM, KLAC_COL_TO_REGION10, REGION10_ORDER  # noqa: E402

KLAC = RAW / "klac"


def parse_legalaid(path: Path, sheet: str, metric: str = "건수") -> pd.DataFrame:
    """법률구조 xlsx 파싱 → (region10, year, aid_cases) 연 합산 long."""
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)

    # 헤더 행: '서울특별시'를 포함한 행
    hdr_idx = next(i for i in range(len(raw))
                   if raw.iloc[i].astype(str).str.contains("서울특별시").any())
    header = raw.iloc[hdr_idx].astype(str).tolist()
    col_to_region = {j: KLAC_COL_TO_REGION10[h.strip()]
                     for j, h in enumerate(header) if h.strip() in KLAC_COL_TO_REGION10}

    records = []
    cur_period = None
    for i in range(hdr_idx + 1, len(raw)):
        row = raw.iloc[i]
        c0 = str(row[0]).strip() if pd.notna(row[0]) else ""
        c1 = str(row[1]).strip() if pd.notna(row[1]) else ""
        if c0 and c0 not in ("nan", ""):
            cur_period = c0
        if "합계" in (cur_period or ""):
            continue
        m = re.match(r"(\d{4})\s*(상반기|하반기)", cur_period or "")
        if not m or metric not in c1:
            continue
        year = int(m.group(1))
        for j, region in col_to_region.items():
            val = row[j]
            if pd.isna(val):
                continue
            num = re.sub(r"[^\d]", "", str(val))
            if num:
                records.append({"region10": region, "year": year, "aid_cases": int(num)})

    df = pd.DataFrame(records)
    # 상+하반기 합산 → 연
    annual = df.groupby(["region10", "year"], as_index=False)["aid_cases"].sum()
    return annual


def main() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    civil = parse_legalaid(KLAC / "legalaid_civil_region.xlsx", sheet="Data")
    civil.to_csv(INTERIM / "klac_legalaid.csv", index=False, encoding="utf-8-sig")
    print(f"민사 법률구조: {len(civil)}행, {civil['year'].min()}~{civil['year'].max()}, "
          f"권역 {civil['region10'].nunique()}개")

    latest = civil["year"].max()
    snap = (civil[civil["year"] == latest]
            .set_index("region10")["aid_cases"]
            .reindex(REGION10_ORDER))
    print(f"\n[검증] {latest}년 권역별 민사 법률구조 건수(상+하반기):")
    print(snap.to_string())

    # 형사도 참고용 저장(2012~2020)
    try:
        crim = parse_legalaid(KLAC / "legalaid_criminal_region.xlsx", sheet="Sheet1")
        crim.to_csv(INTERIM / "klac_legalaid_criminal.csv", index=False, encoding="utf-8-sig")
        print(f"\n(참고) 형사 법률구조: {len(crim)}행, {crim['year'].min()}~{crim['year'].max()}")
    except Exception as e:
        print(f"\n(형사 파싱 건너뜀: {e})")


if __name__ == "__main__":
    main()