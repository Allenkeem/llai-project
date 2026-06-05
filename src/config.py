"""프로젝트 공통 설정 및 지역 매핑 헬퍼.

모든 스크립트는 여기서 경로와 region_mapping.csv 기반 매핑을 가져온다.
분석 단위는 13개 권역(region13). 단일 기준표: 프로젝트 루트 region_mapping.csv
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

# ---- 경로 ----
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
OUTPUTS = ROOT / "outputs"
MAPPING_CSV = ROOT / "region_mapping.csv"

for _p in (INTERIM, PROCESSED, OUTPUTS):
    _p.mkdir(parents=True, exist_ok=True)

# ---- 변협 지방회 이름 → region13 ----
# 변협 표기(짧은 이름) 기준. 경기중앙/경기북부는 경기로 통합.
BAR_TO_REGION13 = {
    "서울": "서울",
    "경기중앙": "경기",
    "경기북부": "경기",
    "인천": "인천",
    "강원": "강원",
    "충북": "충북",
    "대전": "대전권",
    "대구": "대구권",
    "부산": "부산",
    "울산": "울산",
    "경남": "경남",
    "광주": "광주권",
    "전북": "전북",
    "제주": "제주",
}

# region13 표준 순서(보고서/그래프 정렬용)
REGION13_ORDER = [
    "서울", "경기", "인천", "강원", "충북", "대전권", "대구권",
    "부산", "울산", "경남", "광주권", "전북", "제주",
]

# ---- 10 도단위(region10) ----
# 공단 법률구조(A3)가 광역시를 인접 도에 통합 제공하므로, 모든 지표가 공통으로
# 해상 가능한 가장 거친 단위. 부산·울산→경남권, 인천→경기, 대구→경북권 등.
REGION10_ORDER = [
    "서울", "경기", "강원", "충북", "충남권", "경북권", "경남권", "전북", "전남권", "제주",
]

# 시도(정식명칭, 신·구 모두) → region10
SIDO_TO_REGION10 = {
    "서울특별시": "서울",
    "부산광역시": "경남권", "울산광역시": "경남권", "경상남도": "경남권",
    "대구광역시": "경북권", "경상북도": "경북권",
    "인천광역시": "경기", "경기도": "경기",
    "광주광역시": "전남권", "전라남도": "전남권",
    "대전광역시": "충남권", "세종특별자치시": "충남권", "충청남도": "충남권",
    "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북",
    "전북특별자치도": "전북", "전라북도": "전북",
    "제주특별자치도": "제주", "제주도": "제주",
}

# region13 → region10 (집계/근사배분용)
REGION13_TO_REGION10 = {
    "서울": "서울", "경기": "경기", "인천": "경기", "강원": "강원", "충북": "충북",
    "대전권": "충남권", "대구권": "경북권", "부산": "경남권", "울산": "경남권",
    "경남": "경남권", "광주권": "전남권", "전북": "전북", "제주": "제주",
}

# 법원(관내) 접두어 → region13. 모든 법원명이 도시 토큰으로 시작하므로 접두어로 판정.
# (서울중앙/동부/가정/회생 → 서울, 수원·의정부 → 경기 등). 특허법원은 전국관할이라 제외.
COURT_PREFIX_TO_REGION13 = {
    "서울": "서울", "의정부": "경기", "수원": "경기", "인천": "인천",
    "춘천": "강원", "청주": "충북", "대전": "대전권", "대구": "대구권",
    "부산": "부산", "울산": "울산", "창원": "경남", "광주": "광주권",
    "전주": "전북", "제주": "제주",
}

# 공단 xlsx 지역 컬럼명 → region10
KLAC_COL_TO_REGION10 = {
    "서울특별시": "서울", "경기도": "경기", "강원도": "강원", "충청북도": "충북",
    "충청남도": "충남권", "경상북도": "경북권", "경상남도": "경남권",
    "전라북도": "전북", "전라남도": "전남권", "제주특별자치도": "제주",
}


def load_mapping() -> pd.DataFrame:
    """region_mapping.csv 로드 (시도 17행 → region13)."""
    return pd.read_csv(MAPPING_CSV, dtype={"sido_code": str})


def sido_to_region13() -> dict[str, str]:
    """시도명 → region13_name 딕셔너리. KOSIS/법원/공단 데이터 집계에 사용.

    시도명은 부분일치도 잡히도록 짧은 키('서울','충남'...)와 풀네임 모두 등록.
    """
    m = load_mapping()
    d: dict[str, str] = {}
    for _, r in m.iterrows():
        full = r["sido_name"]
        d[full] = r["region13_name"]
        # 짧은 이름(앞 2글자, 단 '세종'은 그대로) 별칭 추가
        short = full[:2]
        d.setdefault(short, r["region13_name"])
    return d


def normalize_sido_name(name: str) -> str | None:
    """원본 데이터의 다양한 시도 표기를 region13으로 매핑. 못 찾으면 None."""
    if not isinstance(name, str):
        return None
    key = name.strip().replace(" ", "")
    table = sido_to_region13()
    if key in table:
        return table[key]
    for k, v in table.items():
        if key.startswith(k) or k.startswith(key):
            return v
    return None


def normalize_to_region10(name: str) -> str | None:
    """시도 표기를 region10(10 도단위)으로 매핑. 못 찾으면 None.

    '강원특별자치도','전북특별자치도' 등 신표기와 '강원도' 약칭 모두 처리.
    """
    if not isinstance(name, str):
        return None
    key = name.strip().replace(" ", "")
    if key in SIDO_TO_REGION10:
        return SIDO_TO_REGION10[key]
    for k, v in SIDO_TO_REGION10.items():
        if key.startswith(k):
            return v
    return None


# 시도명 표준화: 옛/신 명칭 변이를 region_mapping의 정식 17개 명칭으로 통일.
# (강원도↔강원특별자치도, 전라북도↔전북특별자치도 등 출처별 표기 차이 흡수)
# 3글자 접두(충청북/경상남 등)를 2글자보다 먼저 검사해 충/경/전 모호성 제거.
_CANON_ORDER = [
    ("서울", "서울특별시"), ("부산", "부산광역시"), ("대구", "대구광역시"),
    ("인천", "인천광역시"), ("광주", "광주광역시"), ("대전", "대전광역시"),
    ("울산", "울산광역시"), ("세종", "세종특별자치시"), ("경기", "경기도"),
    ("강원", "강원특별자치도"),
    ("충청북", "충청북도"), ("충청남", "충청남도"), ("충북", "충청북도"), ("충남", "충청남도"),
    ("전라북", "전북특별자치도"), ("전라남", "전라남도"), ("전북", "전북특별자치도"), ("전남", "전라남도"),
    ("경상북", "경상북도"), ("경상남", "경상남도"), ("경북", "경상북도"), ("경남", "경상남도"),
    ("제주", "제주특별자치도"),
]


def canonical_sido(name: str) -> str | None:
    """시도명 변이를 정식 17개 명칭으로 표준화. 못 찾으면 None."""
    if not isinstance(name, str):
        return None
    key = name.strip().replace(" ", "")
    for token, full in _CANON_ORDER:
        if key.startswith(token):
            return full
    return None


def normalize_court(name: str) -> str | None:
    """법원(관내)명을 region13으로. 접두 도시 토큰으로 판정. 못 찾으면 None."""
    if not isinstance(name, str):
        return None
    key = name.strip().replace(" ", "")
    for prefix, region in COURT_PREFIX_TO_REGION13.items():
        if key.startswith(prefix):
            return region
    return None