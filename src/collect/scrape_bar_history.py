# -*- coding: utf-8 -*-
"""[패널화] 변협 회원현황 '과거' 시계열 — Wayback Machine 아카이브 복원.

변협 stat.asp는 '현재 스냅샷'만 제공하지만 web.archive.org에 연도별 스냅샷이 남아 있다.
CDX API로 연 1개씩 스냅샷을 찾아, 같은 파서(scrape_bar.parse_table)로 과거 개업변호사 수를
추출한다 → 변호사(A1) 시계열을 '자동' 복원(변호사백서 PDF 수작업 불필요).

이로써 H4(변호사 증가에도 격차 미축소)를 2시점(2009 vs 2026, lawyer_trend.py)이 아니라
'연도별 추세'로 확장한다(lawyer_panel.py).

[방어] 아카이브는 느리고 일부 연도는 누락 → 스냅샷별 try/except + 캐시.
산출: data/raw/bar/bar_history.csv  [bar_association, year, practicing]

사용:
  python src/collect/scrape_bar_history.py
"""
from __future__ import annotations
import sys
import json
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW  # noqa: E402
from collect.scrape_bar import parse_table  # noqa: E402

CDX = ("http://web.archive.org/cdx/search/cdx?url=koreanbar.or.kr/pages/introduce/"
       "stat.asp&output=json&from=2012&to=2025&collapse=timestamp:4")
HCACHE = RAW / "bar" / "bar_history.csv"
UA = {"User-Agent": "Mozilla/5.0 (legal-access panel)"}


def _snapshots(timeout: int = 40) -> list[str]:
    """CDX에서 연도별 스냅샷 타임스탬프 목록."""
    data = json.loads(urllib.request.urlopen(CDX, timeout=timeout).read().decode("utf-8"))
    return [row[1] for row in data[1:]]  # data[0]=헤더


def fetch_history(use_cache: bool = True, timeout: int = 60, retries: int = 1) -> pd.DataFrame:
    """과거 지방회별 개업변호사 수 [bar_association, year, practicing]. 실패 스냅샷은 건너뜀."""
    if use_cache and HCACHE.exists():
        print(f"[bar_history] 캐시 사용: {HCACHE.name}")
        return pd.read_csv(HCACHE)

    try:
        snaps = _snapshots()
    except Exception as e:
        print(f"[bar_history] 스냅샷 목록 조회 실패({type(e).__name__}) — 네트워크 확인 필요")
        return pd.DataFrame()

    recs = []
    for ts in snaps:
        url = (f"http://web.archive.org/web/{ts}id_/"
               f"https://www.koreanbar.or.kr/pages/introduce/stat.asp")
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, headers=UA)
                html = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
                df, asof = parse_table(html)
                year = int(asof[:4]) if asof else int(ts[:4])
                for _, r in df.iterrows():
                    recs.append({"bar_association": r["bar_association"],
                                 "year": year, "practicing": int(r["practicing"])})
                seoul = df[df["bar_association"] == "서울"]["practicing"]
                print(f"  {ts[:8]} -> {year}: {len(df)}지방회 (서울 "
                      f"{int(seoul.iloc[0]) if len(seoul) else '-'})")
                break
            except Exception as e:
                if attempt == retries:
                    print(f"  {ts[:8]} 실패: {type(e).__name__}")

    hist = pd.DataFrame(recs)
    if len(hist):
        hist = hist.drop_duplicates(["bar_association", "year"], keep="last")
        HCACHE.parent.mkdir(parents=True, exist_ok=True)
        hist.sort_values(["year", "bar_association"]).to_csv(
            HCACHE, index=False, encoding="utf-8-sig")
        print(f"[bar_history] 저장: {hist['year'].nunique()}개 연도 "
              f"({hist['year'].min()}~{hist['year'].max()}) -> {HCACHE}")
    else:
        print("[bar_history] 복원 실패(네트워크/아카이브 없음) — 캐시 미생성")
    return hist


if __name__ == "__main__":
    h = fetch_history(use_cache=False)
    if len(h):
        print(h.pivot(index="year", columns="bar_association", values="practicing")
              .get(["서울", "부산", "경기중앙"]))
