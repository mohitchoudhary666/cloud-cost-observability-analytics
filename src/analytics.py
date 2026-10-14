"""Small, transparent analytics functions for the cloud-cost demo."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "cloud_daily_costs.csv"
REQUIRED_COLUMNS = {
    "date",
    "account",
    "region",
    "service",
    "environment",
    "cost_usd",
    "daily_budget_usd",
    "injected_spike",
}


def load_cost_data(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Load and validate the project's CSV dataset."""
    frame = pd.read_csv(path, parse_dates=["date"])
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError("The cost dataset contains no rows.")
    if frame[["cost_usd", "daily_budget_usd"]].isna().any().any():
        raise ValueError("Cost and budget values must not be empty.")
    if (frame[["cost_usd", "daily_budget_usd"]] < 0).any().any():
        raise ValueError("Cost and budget values must be non-negative.")
    return frame.sort_values(["service", "date"]).reset_index(drop=True)


def filter_cost_data(
    frame: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    environments: list[str],
    regions: list[str],
    services: list[str],
) -> pd.DataFrame:
    """Apply dashboard filters while retaining chronological order."""
    mask = (
        frame["date"].between(pd.Timestamp(start), pd.Timestamp(end))
        & frame["environment"].isin(environments)
        & frame["region"].isin(regions)
        & frame["service"].isin(services)
    )
    return frame.loc[mask].sort_values(["service", "date"]).reset_index(drop=True)


def add_anomaly_scores(frame: pd.DataFrame, window: int = 28) -> pd.DataFrame:
    """Add trailing robust scores using history available before each row."""
    result = frame.sort_values(["service", "date"]).copy()
    grouped = result.groupby("service", sort=False)["cost_usd"]
    result["baseline_median"] = grouped.transform(
        lambda values: values.rolling(window, min_periods=14).median().shift(1)
    )
    result["absolute_deviation"] = (result["cost_usd"] - result["baseline_median"]).abs()
    deviations = result.groupby("service", sort=False)["absolute_deviation"]
    result["baseline_mad"] = deviations.transform(
        lambda values: values.rolling(window, min_periods=14).median().shift(1)
    )
    scale = 1.4826 * result["baseline_mad"]
    result["robust_score"] = (result["cost_usd"] - result["baseline_median"]) / scale.where(scale > 0)
    result["is_anomaly"] = result["robust_score"].gt(3.5).fillna(False)
    return result


def summarize_month_to_date(frame: pd.DataFrame, as_of: pd.Timestamp | None = None) -> dict[str, float]:
    """Return spend, budget and a simple month-end run-rate estimate."""
    if frame.empty:
        return {"spend": 0.0, "budget": 0.0, "variance": 0.0, "run_rate": 0.0}
    as_of = pd.Timestamp(as_of or frame["date"].max()).normalize()
    month_start = as_of.replace(day=1)
    month_end = month_start + pd.offsets.MonthEnd(0)
    current = frame.loc[frame["date"].between(month_start, as_of)]
    elapsed_days = max(1, as_of.day)
    total_days = month_end.day
    spend = float(current["cost_usd"].sum())
    budget = float(current["daily_budget_usd"].sum())
    run_rate = spend / elapsed_days * total_days
    return {"spend": spend, "budget": budget, "variance": spend - budget, "run_rate": run_rate}
