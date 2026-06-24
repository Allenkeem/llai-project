"""KOSIS 가로형(wide) 원본 CSV를 세로형(tidy long)으로 변환한다.

KOSIS는 보통 [행=시도, 열=연도×항목] 다중헤더 가로형으로 내려준다.
각 파일별 구조가 달라 전용 파서를 둔다. 산출물은 모두 long 형식:
    columns = [sido_name, year, <값>]

산출물(data/interim/):
    kosis_population.csv     sido_name, year, population
    kosis_grdp.csv           sido_name, year, grdp_per_capita
    kosis_basic.csv          sido_name, year, low_income_pop

사용:
  python src/prepare/load_kosis.py
"""
from __future__ import annotations
import sys
import re
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW, INTERIM, canonical_sido  # noqa: E402


def _canon(df: pd.DataFrame) -> pd.DataFrame:
    """시도명을 정식 17개 명칭으로 통일(옛/새 표기 혼용 흡수).

    GRDP는 옛 이름(강원도·전라북도), 인구는 새 이름(강원특별자치도·전북특별자치도)을
    써서 패널 병합 때 두 권역이 매칭 실패 → 표준화로 해결.
    """
    df = df.copy()
    df["sido_name"] = df["sido_name"].map(canonical_sido)
    return df.dropna(subset=["sido_name"]).reset_index(drop=True)

KOSIS = RAW / "kosis"
SIDO17 = {
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시",
    "울산광역시", "세종특별자치시", "경기도", "강원특별자치도", "강원도", "충청북도",
    "충청남도", "전북특별자치도", "전라북도", "전라남도", "경상북도", "경상남도",
    "제주특별자치도",
}


def _read(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, header=None, dtype=str)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise RuntimeError(f"인코딩 판별 실패: {path}")


def _to_int(s: str) -> float | None:
    if s is None or str(s).strip() in ("", "-", "X", "..."):
        return None
    cleaned = re.sub(r"[^\d.\-]", "", str(s))
    if cleaned in ("", "-", ".", "-."):
        return None
    return float(cleaned)


def parse_wide_repeating(path: Path, item_keep: str, value_name: str,
                         items_per_year: int, item_index: int) -> pd.DataFrame:
    """연도가 items_per_year개씩 반복되는 2행 헤더 가로형 파서.

    item_index 위치 항목만 추출(예: 인구=총인구수가 3개 중 0번째).
    """
    df = _read(path)
    years = df.iloc[0].tolist()
    items = df.iloc[1].tolist()
    data = df.iloc[2:].reset_index(drop=True)

    records = []
    for _, row in data.iterrows():
        sido = str(row[0]).strip()
        if sido not in SIDO17:
            continue
        for col in range(1, len(row)):
            # 해당 항목 위치만
            if (col - 1) % items_per_year != item_index:
                continue
            y = re.sub(r"[^\d]", "", str(years[col]))
            if not y:
                continue
            records.append({
                "sido_name": sido,
                "year": int(y),
                value_name: _to_int(row[col]),
            })
    out = pd.DataFrame(records).dropna(subset=[value_name])
    return out.sort_values(["sido_name", "year"]).reset_index(drop=True)


def parse_basic_livelihood(path: Path) -> pd.DataFrame:
    """기초생활수급자: 일반 다중키 + 연도열. 성별=계·연령별=계 행만."""
    for enc in ("cp949", "utf-8-sig", "utf-8"):
        try:
            df = pd.read_csv(path, encoding=enc, dtype=str)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    cols = list(df.columns)
    region_col, sex_col, age_col = cols[0], cols[1], cols[2]
    year_cols = [c for c in cols if re.search(r"\d{4}", str(c))]

    sub = df[(df[sex_col].str.strip() == "계") & (df[age_col].str.strip() == "계")]
    records = []
    for _, row in sub.iterrows():
        sido = str(row[region_col]).strip()
        if sido not in SIDO17:
            continue
        for yc in year_cols:
            y = int(re.sub(r"[^\d]", "", str(yc)))
            records.append({"sido_name": sido, "year": y,
                            "low_income_pop": _to_int(row[yc])})
    out = pd.DataFrame(records).dropna(subset=["low_income_pop"])
    return out.sort_values(["sido_name", "year"]).reset_index(drop=True)


def main() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)

    pop = parse_wide_repeating(
        KOSIS / "population_sigungu.csv",
        item_keep="총인구수", value_name="population",
        items_per_year=3, item_index=0)
    pop = _canon(pop)
    pop.to_csv(INTERIM / "kosis_population.csv", index=False, encoding="utf-8-sig")
    print(f"인구: {len(pop)}행, {pop['year'].min()}~{pop['year'].max()}, "
          f"시도 {pop['sido_name'].nunique()}개")

    grdp = parse_wide_repeating(
        KOSIS / "grdp_income_sido.csv",
        item_keep="1인당 지역내총생산", value_name="grdp_per_capita",
        items_per_year=4, item_index=0)
    grdp = _canon(grdp)
    grdp.to_csv(INTERIM / "kosis_grdp.csv", index=False, encoding="utf-8-sig")
    print(f"GRDP: {len(grdp)}행, {grdp['year'].min()}~{grdp['year'].max()}, "
          f"시도 {grdp['sido_name'].nunique()}개")

    basic = parse_basic_livelihood(KOSIS / "basic_livelihood_recipients.csv")
    basic = _canon(basic)
    basic.to_csv(INTERIM / "kosis_basic.csv", index=False, encoding="utf-8-sig")
    print(f"수급자: {len(basic)}행, {basic['year'].min()}~{basic['year'].max()}, "
          f"시도 {basic['sido_name'].nunique()}개")

    # [추가] 사업체수(전국사업체조사) — demand-pull 수요 대리변수. 선택(파일 있을 때만).
    # 사업체수만 있으면 items_per_year=1, '사업체수+종사자수' 2항목이면 items_per_year=2.
    biz_path = KOSIS / "business_count_sido.csv"
    if biz_path.exists():
        biz = parse_wide_repeating(
            biz_path, item_keep="사업체수", value_name="business_count",
            items_per_year=1, item_index=0)
        biz = _canon(biz)
        biz.to_csv(INTERIM / "kosis_business.csv", index=False, encoding="utf-8-sig")
        print(f"사업체수: {len(biz)}행, {biz['year'].min()}~{biz['year'].max()}, "
              f"시도 {biz['sido_name'].nunique()}개")
    else:
        print("[건너뜀] kosis/business_count_sido.csv 없음 — 사업체수 미수집(선택)")

    # 미리보기: 최신 연도
    print("\n[검증] 2022년 시도별 값 (있으면):")
    for name, d, col in [("인구", pop, "population"), ("GRDP", grdp, "grdp_per_capita"),
                         ("수급자", basic, "low_income_pop")]:
        y = 2022 if 2022 in d["year"].values else d["year"].max()
        snap = d[d["year"] == y].set_index("sido_name")[col]
        print(f"  {name}({y}) 서울={snap.get('서울특별시')}, 경기도={snap.get('경기도')}")


if __name__ == "__main__":
    main()