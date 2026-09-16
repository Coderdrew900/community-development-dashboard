# Data preparation script. This is included so the final CSV can be rebuilt from the original sources.
"""Download, clean, and combine the community-development indicators.

Sources
-------
* U.S. Census Bureau, American Community Survey (ACS) 1-year detailed tables
* U.S. Bureau of Labor Statistics, Local Area Unemployment Statistics (LAUS)

The script creates one CSV with 51 states/DC across three years (2022-2024).
It uses the public ACS bulk files, so a Census API key is not required.
"""

from __future__ import annotations

import argparse
import io
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests


YEARS = (2022, 2023, 2024)
ACS_BASE = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/"
    "{year}/table-based-SF/data/1YRData/acsdt1y{year}-{table}.dat"
)
BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

STATES = {
    "01": ("Alabama", "AL", "South"), "02": ("Alaska", "AK", "West"),
    "04": ("Arizona", "AZ", "West"), "05": ("Arkansas", "AR", "South"),
    "06": ("California", "CA", "West"), "08": ("Colorado", "CO", "West"),
    "09": ("Connecticut", "CT", "Northeast"), "10": ("Delaware", "DE", "South"),
    "11": ("District of Columbia", "DC", "South"), "12": ("Florida", "FL", "South"),
    "13": ("Georgia", "GA", "South"), "15": ("Hawaii", "HI", "West"),
    "16": ("Idaho", "ID", "West"), "17": ("Illinois", "IL", "Midwest"),
    "18": ("Indiana", "IN", "Midwest"), "19": ("Iowa", "IA", "Midwest"),
    "20": ("Kansas", "KS", "Midwest"), "21": ("Kentucky", "KY", "South"),
    "22": ("Louisiana", "LA", "South"), "23": ("Maine", "ME", "Northeast"),
    "24": ("Maryland", "MD", "South"), "25": ("Massachusetts", "MA", "Northeast"),
    "26": ("Michigan", "MI", "Midwest"), "27": ("Minnesota", "MN", "Midwest"),
    "28": ("Mississippi", "MS", "South"), "29": ("Missouri", "MO", "Midwest"),
    "30": ("Montana", "MT", "West"), "31": ("Nebraska", "NE", "Midwest"),
    "32": ("Nevada", "NV", "West"), "33": ("New Hampshire", "NH", "Northeast"),
    "34": ("New Jersey", "NJ", "Northeast"), "35": ("New Mexico", "NM", "West"),
    "36": ("New York", "NY", "Northeast"), "37": ("North Carolina", "NC", "South"),
    "38": ("North Dakota", "ND", "Midwest"), "39": ("Ohio", "OH", "Midwest"),
    "40": ("Oklahoma", "OK", "South"), "41": ("Oregon", "OR", "West"),
    "42": ("Pennsylvania", "PA", "Northeast"), "44": ("Rhode Island", "RI", "Northeast"),
    "45": ("South Carolina", "SC", "South"), "46": ("South Dakota", "SD", "Midwest"),
    "47": ("Tennessee", "TN", "South"), "48": ("Texas", "TX", "South"),
    "49": ("Utah", "UT", "West"), "50": ("Vermont", "VT", "Northeast"),
    "51": ("Virginia", "VA", "South"), "53": ("Washington", "WA", "West"),
    "54": ("West Virginia", "WV", "South"), "55": ("Wisconsin", "WI", "Midwest"),
    "56": ("Wyoming", "WY", "West"),
}


def _download_acs_table(year: int, table: str, columns: list[str]) -> pd.DataFrame:
    url = ACS_BASE.format(year=year, table=table.lower())
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    frame = pd.read_csv(io.StringIO(response.text), sep="|", usecols=["GEO_ID", *columns], dtype={"GEO_ID": "string"}, low_memory=False)
    frame["state_fips"] = frame["GEO_ID"].str.extract(r"^0400000US(\d{2})$")[0]
    frame = frame[frame["state_fips"].isin(STATES)].copy()
    if len(frame) != 51:
        raise ValueError(f"Expected 51 state/DC rows for {table} {year}; found {len(frame)}")
    return frame.drop(columns="GEO_ID")


def fetch_acs_year(year: int) -> pd.DataFrame:
    poverty = _download_acs_table(year, "b17001", ["B17001_E001","B17001_E002","B17001_E003","B17001_E017","B17001_E032","B17001_E046"])
    education = _download_acs_table(year, "b15003", ["B15003_E001","B15003_E022","B15003_E023","B15003_E024","B15003_E025"])
    internet = _download_acs_table(year, "b28002", ["B28002_E001","B28002_E013"])
    transit = _download_acs_table(year, "b08301", ["B08301_E001","B08301_E010"])

    merged = poverty.merge(education, on="state_fips", validate="one_to_one")
    merged = merged.merge(internet, on="state_fips", validate="one_to_one")
    merged = merged.merge(transit, on="state_fips", validate="one_to_one")
    numeric = [column for column in merged.columns if column != "state_fips"]
    merged[numeric] = merged[numeric].apply(pd.to_numeric, errors="coerce")

    merged["poverty_rate_total"] = 100 * merged["B17001_E002"] / merged["B17001_E001"]
    merged["poverty_rate_male"] = 100 * merged["B17001_E003"] / (merged["B17001_E003"] + merged["B17001_E032"])
    merged["poverty_rate_female"] = 100 * merged["B17001_E017"] / (merged["B17001_E017"] + merged["B17001_E046"])
    degree_count = merged[["B15003_E022","B15003_E023","B15003_E024","B15003_E025"]].sum(axis=1)
    merged["bachelors_plus_rate"] = 100 * degree_count / merged["B15003_E001"]
    merged["no_internet_rate"] = 100 * merged["B28002_E013"] / merged["B28002_E001"]
    merged["public_transit_rate"] = 100 * merged["B08301_E010"] / merged["B08301_E001"]
    merged["year"] = year
    return merged[["state_fips","year","poverty_rate_total","poverty_rate_male","poverty_rate_female","bachelors_plus_rate","no_internet_rate","public_transit_rate"]]


def fetch_bls_unemployment(years: tuple[int, ...] = YEARS) -> pd.DataFrame:
    series_to_fips = {f"LASST{fips}0000000000003": fips for fips in STATES}
    records = []
    series_ids = list(series_to_fips)
    for start in range(0, len(series_ids), 20):
        batch = series_ids[start:start+20]
        payload = {"seriesid": batch, "startyear": str(min(years)), "endyear": str(max(years))}
        response = requests.post(BLS_API, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        if result.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS request failed: {result.get('message')}")
        for series in result.get("Results", {}).get("series", []):
            fips = series_to_fips[series["seriesID"]]
            for point in series["data"]:
                if point["period"].startswith("M") and point["period"] != "M13":
                    records.append({"state_fips": fips, "year": int(point["year"]), "month": point["period"], "unemployment_rate": float(point["value"])})
        time.sleep(0.2)
    monthly = pd.DataFrame(records)
    annual = monthly[monthly["year"].isin(years)].groupby(["state_fips","year"], as_index=False).agg(unemployment_rate=("unemployment_rate","mean"), months=("month","nunique"))
    incomplete = annual.loc[annual["months"] != 12]
    if not incomplete.empty:
        raise ValueError(f"Incomplete BLS monthly data:\n{incomplete}")
    return annual.drop(columns="months")


def add_priority_scores(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    for group in ("total","male","female"):
        poverty = f"poverty_rate_{group}"
        components = pd.DataFrame(index=result.index)
        components["poverty"] = result.groupby("year")[poverty].rank(pct=True)
        components["unemployment"] = result.groupby("year")["unemployment_rate"].rank(pct=True)
        components["internet"] = result.groupby("year")["no_internet_rate"].rank(pct=True)
        components["education_gap"] = result.groupby("year")["bachelors_plus_rate"].rank(pct=True, ascending=False)
        components["transit_gap"] = result.groupby("year")["public_transit_rate"].rank(pct=True, ascending=False)
        result[f"priority_score_{group}"] = 100 * (0.30*components["poverty"] + 0.25*components["unemployment"] + 0.20*components["internet"] + 0.15*components["education_gap"] + 0.10*components["transit_gap"])
    return result


def validate(data: pd.DataFrame) -> None:
    if len(data) != len(STATES) * len(YEARS):
        raise ValueError(f"Expected {len(STATES) * len(YEARS)} rows; found {len(data)}")
    if data.duplicated(["state_fips","year"]).any():
        raise ValueError("Duplicate state-year rows found")
    if data.isna().any().any():
        raise ValueError("Missing values found")
    rate_columns = [c for c in data.columns if c.endswith("_rate")]
    if not data[rate_columns].apply(lambda c: c.between(0,100).all()).all():
        raise ValueError("At least one percentage is outside 0-100")
    priority_columns = [c for c in data.columns if c.startswith("priority_score_")]
    if not data[priority_columns].apply(lambda c: c.between(0,100).all()).all():
        raise ValueError("At least one priority score is outside 0-100")


def build_dataset(output_path: str | Path) -> pd.DataFrame:
    acs = pd.concat([fetch_acs_year(year) for year in YEARS], ignore_index=True)
    unemployment = fetch_bls_unemployment()
    data = acs.merge(unemployment, on=["state_fips","year"], validate="one_to_one")
    state_metadata = pd.DataFrame([{"state_fips": fips, "state": name, "state_code": code, "region": region} for fips,(name,code,region) in STATES.items()])
    data = data.merge(state_metadata, on="state_fips", validate="many_to_one")
    data = add_priority_scores(data)
    ordered = ["state_fips","state","state_code","region","year","unemployment_rate","poverty_rate_total","poverty_rate_male","poverty_rate_female","no_internet_rate","bachelors_plus_rate","public_transit_rate","priority_score_total","priority_score_male","priority_score_female"]
    data = data[ordered].sort_values(["year","state"]).reset_index(drop=True)
    float_columns = data.select_dtypes(include=["float"]).columns
    data[float_columns] = data[float_columns].round(2)
    validate(data)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_path, index=False)
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data" / "community_indicators.csv")
    args = parser.parse_args()
    data = build_dataset(args.output)
    print(f"Saved {len(data)} validated rows to {args.output}")


if __name__ == "__main__":
    main()
