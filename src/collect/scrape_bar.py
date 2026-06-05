"""대한변호사협회 지방회별 회원현황 스크래퍼.

출처: https://www.koreanbar.or.kr/pages/introduce/stat.asp
이 페이지는 '현재 시점' 스냅샷만 HTML 표로 제공한다(다운로드·시계열 없음).
14개 지방회의 개업회원/준회원/소계를 추출해 13개 권역으로 집계한다.

산출물:
  data/raw/bar/bar_snapshot_raw.csv      지방회 14행 원본
  data/raw/bar/bar_region13.csv          권역 13행 집계(분석용)

사용:
  python src/collect/scrape_bar.py
"""
from __future__ import annotations
import sys
import re
from pathlib import Path

import urllib.request
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW, BAR_TO_REGION13, REGION13_ORDER  # noqa: E402

URL = "https://www.koreanbar.or.kr/pages/introduce/stat.asp"
OUT_DIR = RAW / "bar"


def fetch_html(url: str = URL) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def _clean(cell: str) -> str:
    return re.sub(r"<.*?>", "", cell).replace("\xa0", "").strip()


def parse_table(html: str) -> tuple[pd.DataFrame, str | None]:
    """회원현황 표를 파싱. (지방회 14행 DataFrame, 기준일) 반환."""
    tables = re.findall(r"<table.*?</table>", html, re.S)
    target = next((t for t in tables if "서울" in t and "개업" in t), None)
    if target is None:
        raise RuntimeError("회원현황 표를 찾지 못함 — 페이지 구조 변경 가능성")

    rows = re.findall(r"<tr.*?</tr>", target, re.S)
    records = []
    for r in rows:
        cells = [_clean(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
        if len(cells) < 4:
            continue
        name = cells[0]
        # 데이터 행만: 첫 칸이 지방회 이름이고 둘째 칸이 숫자
        if name in BAR_TO_REGION13 and re.fullmatch(r"[\d,]+", cells[1] or ""):
            records.append({
                "bar_association": name,
                "practicing": int(cells[1].replace(",", "")),   # 개업회원
                "associate": int(cells[2].replace(",", "")),    # 준회원(휴업+미개업)
                "total": int(cells[3].replace(",", "")),        # 소계
            })

    df = pd.DataFrame(records)
    if len(df) != 14:
        print(f"[경고] 지방회 행 수 {len(df)} (기대 14). 매핑 확인 필요.", file=sys.stderr)

    m = re.search(r"(\d{4}-\d{2}-\d{2})", html)
    return df, (m.group(1) if m else None)


def to_region13(df: pd.DataFrame, asof: str | None) -> pd.DataFrame:
    df = df.copy()
    df["region13_name"] = df["bar_association"].map(BAR_TO_REGION13)
    agg = (
        df.groupby("region13_name")[["practicing", "associate", "total"]]
        .sum()
        .reindex(REGION13_ORDER)
        .reset_index()
    )
    agg.insert(0, "asof", asof)
    return agg


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html = fetch_html()
    raw, asof = parse_table(html)
    raw.insert(0, "asof", asof)
    raw.to_csv(OUT_DIR / "bar_snapshot_raw.csv", index=False, encoding="utf-8-sig")

    region = to_region13(raw.drop(columns=["asof"]), asof)
    region.to_csv(OUT_DIR / "bar_region13.csv", index=False, encoding="utf-8-sig")

    print(f"기준일: {asof}")
    print(f"지방회 {len(raw)}행 → 권역 {len(region)}행 저장")
    print(region.to_string(index=False))
    print(f"\n총 개업회원 합계: {region['practicing'].sum():,}")


if __name__ == "__main__":
    main()
