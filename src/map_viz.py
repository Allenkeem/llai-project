"""LLAI 코로플레스 지도. 시도 경계를 권역(region10/region13)으로 dissolve 후 색칠.

원천: data/raw/geo/skorea_provinces.geojson (통계청 2018 시도 경계, 17개)
산출물:
  outputs/maps/llai_map_{unit}.html     folium 인터랙티브 지도
  outputs/figures/fig7_map_{unit}.png   geopandas 정적 지도

사용:
  python src/map_viz.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (OUTPUTS, RAW, canonical_sido,  # noqa: E402
                    normalize_sido_name, normalize_to_region10)

GEO = RAW / "geo" / "skorea_provinces.geojson"
MAPS = OUTPUTS / "maps"
FIG = OUTPUTS / "figures"


def load_regions(unit: str, tag: str = "") -> gpd.GeoDataFrame:
    """시도 경계를 권역으로 dissolve하고 LLAI를 병합. tag='_exseoul'이면 서울은 NaN."""
    gdf = gpd.read_file(GEO)
    fn = normalize_to_region10 if unit == "region10" else normalize_sido_name
    gdf["region"] = gdf["name"].map(lambda n: fn(canonical_sido(n)))
    diss = gdf.dissolve(by="region").reset_index()
    diss["geometry"] = diss.geometry.simplify(0.005, preserve_topology=True)

    import pandas as pd
    llai = pd.read_csv(OUTPUTS / "tables" / f"llai_{unit}{tag}.csv")
    keep = ["region", "A1", "A2", "A3", "LLAI"]
    diss = diss.merge(llai[keep].round(2), on="region", how="left")
    return diss


def make_static(unit: str, save: bool = True, tag: str = ""):
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    diss = load_regions(unit, tag)
    fig, ax = plt.subplots(figsize=(7, 8))
    diss.plot(column="LLAI", cmap="RdYlBu", linewidth=0.6, edgecolor="white",
              legend=True, ax=ax, legend_kwds={"label": "LLAI (0~100)", "shrink": 0.6},
              missing_kwds={"color": "lightgray", "label": "서울(제외)"})
    for _, r in diss.iterrows():
        if pd.isna(r["LLAI"]):
            continue
        c = r.geometry.representative_point()
        ax.annotate(f"{r['region']}\n{r['LLAI']:.0f}", (c.x, c.y),
                    ha="center", va="center", fontsize=8, fontweight="bold")
    sub = " · 서울 제외" if tag else ""
    ax.set_title(f"지역별 종합 법률 접근성 지수 LLAI ({unit}{sub}, 2024)")
    ax.axis("off")
    fig.tight_layout()
    if save:
        FIG.mkdir(parents=True, exist_ok=True)
        fig.savefig(FIG / f"fig7_map_{unit}{tag}.png", bbox_inches="tight", dpi=120)
    return fig


def make_interactive(unit: str, save: bool = True, tag: str = ""):
    import folium
    diss = load_regions(unit, tag)
    m = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles="cartodbpositron")
    folium.Choropleth(
        geo_data=diss.to_json(),
        data=diss, columns=["region", "LLAI"],
        key_on="feature.properties.region",
        fill_color="RdYlBu", fill_opacity=0.8, line_opacity=0.5,
        legend_name=f"LLAI ({unit}, 2024)", nan_fill_color="lightgray",
    ).add_to(m)
    folium.GeoJson(
        diss.to_json(),
        style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
        tooltip=folium.GeoJsonTooltip(
            fields=["region", "LLAI", "A1", "A2", "A3"],
            aliases=["권역", "LLAI", "변호사/10만", "사건/변호사", "법률구조"],
        ),
    ).add_to(m)
    if save:
        MAPS.mkdir(parents=True, exist_ok=True)
        m.save(str(MAPS / f"llai_map_{unit}{tag}.html"))
    return m


def main() -> None:
    for unit in ("region10", "region13"):
        make_static(unit)
        plt.close("all")
        make_interactive(unit)
        print(f"[{unit}] 정적 fig7_map_{unit}.png · 인터랙티브 llai_map_{unit}.html 저장")


if __name__ == "__main__":
    main()
