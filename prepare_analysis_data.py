"""Prepare the daily regression file from four validated local source extracts.

This script performs deterministic project-specific data preparation. It has
no network access, never changes the source files, and writes only
predetermined files inside this project folder.
"""

from pathlib import Path
import pandas as pd

PROJECT = Path(__file__).resolve().parent
SOURCE = PROJECT / "source_data"
DATA = PROJECT / "data"
RESULTS = PROJECT / "results"
DATA.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)

START = pd.Timestamp("2023-05-01")
END = pd.Timestamp("2025-12-31")
EXPECTED_DATES = pd.date_range(START, END, freq="D")


def read_daily(filename):
    """Read a daily source and stop on invalid or duplicate date keys."""
    frame = pd.read_csv(SOURCE / filename)
    if "date" not in frame.columns:
        raise ValueError(f"{filename} has no date column")
    frame["date"] = pd.to_datetime(frame["date"], format="%Y-%m-%d")
    if frame["date"].isna().any() or frame["date"].duplicated().any():
        raise ValueError(f"{filename} contains invalid or duplicate dates")
    if not frame["date"].sort_values().reset_index(drop=True).equals(
            pd.Series(EXPECTED_DATES, name="date")):
        raise ValueError(f"{filename} does not contain the exact 976-day sample")
    return frame


# Read and validate the three daily sources without altering them.
price = read_daily("CAISO_SP15_daily_outcome.csv")
battery = read_daily("EIA860M_CISO_daily_lagged_battery_capacity.csv")
gas = read_daily("CAISO_PRC_FUEL_FRSCE3_daily.csv")

# Read EIA hourly data. EIA labels hours by local hour-ending number, whereas
# the price outcome uses interval-start hours. Therefore, price hours 10-15
# correspond to EIA hour-ending numbers 11-16, and price hours 17-20 correspond
# to EIA hour-ending numbers 18-21. This prevents a one-hour alignment error.
hourly = pd.read_csv(SOURCE / "EIA930_CISO_hourly_adjusted_demand_solar.csv")
hourly["Data Date"] = pd.to_datetime(hourly["Data Date"], format="%Y-%m-%d")
key = ["Data Date", "Hour Number"]
if hourly[key].duplicated().any():
    raise ValueError("EIA-930 contains duplicate date/hour keys")
if set(hourly["Data Date"].unique()) != set(EXPECTED_DATES):
    raise ValueError("EIA-930 does not cover every sample date")

midday_hours = [11, 12, 13, 14, 15, 16]
evening_hours = [18, 19, 20, 21]


def window_mean(frame, hours, value, output_name):
    """Calculate a fixed-window mean only when every required value exists."""
    selected = frame.loc[frame["Hour Number"].isin(hours), ["Data Date", value]]
    grouped = selected.groupby("Data Date")[value]
    means = grouped.mean()
    valid = (grouped.size() == len(hours)) & (grouped.count() == len(hours))
    means.loc[~valid] = float("nan")
    return means.rename(output_name)


# Build daily demand and solar controls in GW. No interpolation, forward fill,
# backward fill, or mean replacement is used. A source-blank window remains
# missing so the analysis applies the pre-specified complete-window rule.
dm = "Demand (MW) (Adjusted)"
sm = "solar_adjusted_mw"
midday_demand = window_mean(hourly, midday_hours, dm, "midday_demand_mw")
evening_demand = window_mean(hourly, evening_hours, dm, "evening_demand_mw")
midday_solar = window_mean(hourly, midday_hours, sm, "midday_solar_mw")
evening_solar = window_mean(hourly, evening_hours, sm, "evening_solar_mw")
controls = pd.concat(
    [midday_demand, evening_demand, midday_solar, evening_solar], axis=1
).reset_index().rename(columns={"Data Date": "date"})
controls["demand_gap_gw"] = (
    controls["evening_demand_mw"] - controls["midday_demand_mw"]
) / 1000
controls["solar_drop_gw"] = (
    controls["midday_solar_mw"] - controls["evening_solar_mw"]
) / 1000

# Select and rename variables, preserving the original units in the names.
price = price.rename(columns={
    "evening_minus_midday_spread_usd_per_mwh": "spread_usd_mwh",
    "evening_mean_lmp_usd_per_mwh": "evening_lmp_usd_mwh",
    "midday_mean_lmp_usd_per_mwh": "midday_lmp_usd_mwh",
})
price["negative_price_hours_24eq"] = (
    price["negative_lmp_interval_count"] /
    price["total_lmp_interval_count"] * 24
)
battery["battery_gw"] = (
    battery["battery_power_capacity_mw_lag1month"] / 1000
)
battery["battery_gwh"] = (
    battery["battery_energy_capacity_mwh_lag1month"] / 1000
)

# Construct the pre-specified additional one-month timing lag. The baseline
# battery_gw series already assigns the prior month-end EIA inventory to every
# day of the following month. This robustness variable shifts those 32 monthly
# exposure levels by one further calendar month. May 2023 is intentionally
# missing because the archived daily exposure series begins in May; no value is
# invented, backfilled, or carried in from outside the validated source range.
battery["sample_month"] = battery["date"].dt.to_period("M")
monthly_battery = battery[["sample_month", "battery_gw"]].drop_duplicates(
    subset=["sample_month"]
).sort_values("sample_month")
monthly_battery["battery_lag1_gw"] = monthly_battery["battery_gw"].shift(1)
battery = battery.merge(
    monthly_battery[["sample_month", "battery_lag1_gw"]],
    on="sample_month", how="left", validate="many_to_one"
)
gas["gas_usd_mmbtu"] = gas["fuel_price_usd_per_mmbtu"]

# Merge by exact date with one-to-one validation. A failed key relationship
# stops execution instead of silently creating or deleting observations.
merged = price[[
    "date", "spread_usd_mwh", "evening_lmp_usd_mwh",
    "midday_lmp_usd_mwh", "negative_price_hours_24eq"
]].merge(
    battery[["date", "battery_gw", "battery_lag1_gw", "battery_gwh"]],
    on="date", how="left", validate="one_to_one"
).merge(
    controls[["date", "demand_gap_gw", "solar_drop_gw"]],
    on="date", how="left", validate="one_to_one"
).merge(
    gas[["date", "gas_usd_mmbtu"]],
    on="date", how="left", validate="one_to_one"
).sort_values("date").reset_index(drop=True)

# Construct transparent calendar and trend controls after the merge.
merged["time_days"] = (merged["date"] - START).dt.days
merged["month_id"] = (
    (merged["date"].dt.year - START.year) * 12 +
    merged["date"].dt.month - START.month + 1
)
merged["weekday"] = merged["date"].dt.day_name()
merged["month"] = merged["date"].dt.month_name()
merged["trend_years"] = merged["time_days"] / 365.25
merged["tariff_break"] = (merged["date"] >= "2025-02-15").astype(int)

ordered = [
    "date", "time_days", "month_id", "weekday", "month",
    "spread_usd_mwh", "evening_lmp_usd_mwh", "midday_lmp_usd_mwh",
    "battery_gw", "battery_lag1_gw", "battery_gwh", "demand_gap_gw", "solar_drop_gw",
    "gas_usd_mmbtu", "trend_years", "tariff_break",
    "negative_price_hours_24eq",
]
merged = merged[ordered]
merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")

# Validate the locked sample facts. Exactly one official-source day should be
# incomplete: 2 November 2024, leaving 975 regression observations.
required = [
    "spread_usd_mwh", "evening_lmp_usd_mwh", "midday_lmp_usd_mwh",
    "battery_gw", "demand_gap_gw", "solar_drop_gw", "gas_usd_mmbtu",
]
incomplete = merged.loc[merged[required].isna().any(axis=1), "date"].tolist()
lag_missing = merged.loc[merged["battery_lag1_gw"].isna(), "date"].tolist()
expected_lag_missing = pd.date_range(
    "2023-05-01", "2023-05-31", freq="D"
).strftime("%Y-%m-%d").tolist()
if merged.shape[0] != 976 or merged["date"].duplicated().any():
    raise ValueError("Merged file failed the 976-row/unique-date gate")
if incomplete != ["2024-11-02"]:
    raise ValueError(f"Unexpected incomplete dates: {incomplete}")
if lag_missing != expected_lag_missing:
    raise ValueError(f"Unexpected timing-lag missing dates: {lag_missing}")

# Write the analysis file and a compact preparation audit.
output = DATA / "CAISO_daily_analysis.csv"
merged.to_csv(output, index=False)
audit = pd.DataFrame({
    "check": [
        "sample dates", "unique dates", "incomplete regression dates",
        "usable complete cases", "timing robustness usable cases",
        "duplicate dates"
    ],
    "result": [976, merged["date"].nunique(), "; ".join(incomplete),
               976 - len(incomplete), 944,
               int(merged["date"].duplicated().sum())]
})
audit.to_csv(RESULTS / "00_preparation_audit.csv", index=False)
print(f"Created {output}")
print("976 dates; 975 baseline cases; 944 additional timing-lag cases.")
