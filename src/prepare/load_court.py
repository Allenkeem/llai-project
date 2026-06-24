"""사법연감 엑셀 → 법원별 사건 접수(A2) tidy long. **다년 스캔 지원**.

A2 정의: 변호사 1인당 연간 법원 사건 부담. 분자 = 제1심 '본안사건' 접수.
  - 본안사건(총설 01항 시트6 '지역별 인구 및 사건수') = 민사본안+형사공판+가사+행정 등 제1심.
    비송(등기·공탁)을 제외해 변호사 업무량을 대표. 이미 법원관내(=지역) 단위.
  - 보조: 민사 제1심 본안(02항 시트6), 형사 제1심 공판(07항 시트4)을 분야별로 추출.

[다년] data/raw/court/ 아래 '(YYYY)년_사건개황' 폴더를 모두 스캔한다.
  - 각 폴더 필수: (YYYY)01.개황.01항.총설.xlsx  → total_cases (시계열 핵심)
  - 선택: 02항.민사 / 07항.형사 (있으면 civil_main·criminal_trial 추가; 과거연도는 보통 없음)
  → 단일 단면뿐이던 A2를 연도별로 만들어 LLAI 시계열의 기반을 마련(과거 사법연감 추가 시 자동).

법원관내명은 접두 도시 토큰으로 region13에 매핑(config.normalize_court).

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

COURT_DIR = RAW / "court"


def _cells(path: Path, sheet: str):
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)[sheet]
    return list(ws.iter_rows(values_only=True))


def _find(base: Path, keyword: str) -> Path | None:
    """폴더에서 파일명에 keyword가 든 첫 xlsx (표기 변형 흡수: '01항.총설'/'01항_총설' 등)."""
    for f in sorted(base.glob("*.xlsx")):
        if keyword in f.name:
            return f
    return None


def _num(v) -> float | None:
    if v is None:
        return None
    s = re.sub(r"[^\d.\-]", "", str(v))
    return float(s) if s not in ("", "-", ".") else None


def parse_main_cases(base: Path, year: int) -> pd.DataFrame:
    """총설 시트6: 법원관내별 본안사건 건수(col 5)."""
    f = _find(base, "총설")
    if f is None:
        raise FileNotFoundError(f"{base.name}: 총설 파일 없음")
    rows = _cells(f, "6")
    rec = []
    for r in rows:
        c0 = str(r[0]).strip() if r and r[0] else ""
        if c0.endswith("관내"):
            reg = normalize_court(c0)
            val = _num(r[5])  # 본안사건 건수
            if reg and val is not None:
                rec.append({"region13": reg, "total_cases": val})
    return pd.DataFrame(rec).groupby("region13", as_index=False)["total_cases"].sum()


def parse_civil(base: Path, year: int) -> pd.DataFrame | None:
    """민사 시트6: 법원별 제1심 민사본안 접수(계, col 4). 파일 없으면 None."""
    f = _find(base, "민사")
    if f is None:
        return None
    rec = []
    for r in _cells(f, "6"):
        c0 = str(r[0]).strip() if r and r[0] else ""
        reg = normalize_court(c0)
        if reg and "법원" in c0:
            val = _num(r[4])
            if val is not None:
                rec.append({"region13": reg, "civil_main": val})
    return pd.DataFrame(rec).groupby("region13", as_index=False)["civil_main"].sum()


def parse_criminal(base: Path, year: int) -> pd.DataFrame | None:
    """형사 시트4: 법원별 제1심 형사공판 접수(계, col 1). 파일 없으면 None."""
    f = _find(base, "형사")
    if f is None:
        return None
    rec = []
    for r in _cells(f, "4"):
        c0 = str(r[0]).strip() if r and r[0] else ""
        reg = normalize_court(c0)
        if reg:
            val = _num(r[1])
            if val is not None:
                rec.append({"region13": reg, "criminal_trial": val})
    return pd.DataFrame(rec).groupby("region13", as_index=False)["criminal_trial"].sum()


def parse_year(base: Path, year: int) -> pd.DataFrame:
    """한 연도 폴더 → region13 사건수(총설 필수, 민사/형사 선택)."""
    df = parse_main_cases(base, year)
    civil = parse_civil(base, year)
    crim = parse_criminal(base, year)
    if civil is not None:
        df = df.merge(civil, on="region13", how="left")
    if crim is not None:
        df = df.merge(crim, on="region13", how="left")
    df["year"] = year
    return df


def discover_year_dirs() -> list[tuple[Path, int]]:
    """data/raw/court 아래 '(YYYY)년_사건개황' 폴더 목록 → (경로, 연도)."""
    out = []
    if COURT_DIR.exists():
        for d in sorted(COURT_DIR.iterdir()):
            m = re.match(r"(\d{4})년[ _]?사건개황$", d.name) if d.is_dir() else None
            if m:
                out.append((d, int(m.group(1))))
    return out


def main() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    year_dirs = discover_year_dirs()
    if not year_dirs:
        raise SystemExit(f"사건개황 폴더 없음: {COURT_DIR}/(YYYY)년_사건개황")

    parts = []
    for base, year in year_dirs:
        try:
            parts.append(parse_year(base, year))
            print(f"  {year}년 파싱 완료")
        except Exception as e:
            print(f"  {year}년 실패: {type(e).__name__} — 건너뜀")

    df = pd.concat(parts, ignore_index=True)
    for c in ("civil_main", "criminal_trial"):
        if c not in df.columns:
            df[c] = pd.NA
    df = df[["region13", "year", "total_cases", "civil_main", "criminal_trial"]]
    # region13 순서로 정렬(연도→권역)
    cat = pd.Categorical(df["region13"], categories=REGION13_ORDER, ordered=True)
    df = df.assign(_o=cat).sort_values(["year", "_o"]).drop(columns="_o").reset_index(drop=True)
    df.to_csv(INTERIM / "court_cases.csv", index=False, encoding="utf-8-sig")

    years = sorted(df["year"].unique())
    print(f"\n법원 사건(A2): {df['region13'].nunique()}개 region13 × {len(years)}개 연도 {years}")
    latest = df[df["year"] == max(years)]
    print(latest.to_string(index=False))
    print(f"\n검증({max(years)}): 본안사건 합계 = {latest['total_cases'].sum():,.0f} "
          f"(사법연감 2024 전국 본안 1,106,526)")


if __name__ == "__main__":
    main()
