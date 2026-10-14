from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.analytics import add_anomaly_scores, filter_cost_data, load_cost_data, summarize_month_to_date


st.set_page_config(page_title="Cloud Cost Observatory", page_icon="☁️", layout="wide")
st.markdown(
    """
    <style>
      .stApp { background: #0b1220; color: #e6edf7; }
      [data-testid="stMetric"] { background: #111c2e; border: 1px solid #243650;
        padding: 16px; border-radius: 14px; }
      [data-testid="stSidebar"] { background: #0e1929; }
      h1, h2, h3 { letter-spacing: -0.03em; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("☁️ Cloud Cost Observatory")
st.caption("FinOps-style spend visibility • robust anomaly signals • synthetic demo data")
st.info(
    "Demo dataset only: these are generated example costs, not real AWS billing data. "
    "No AWS credentials or cloud connection are used.",
    icon="ℹ️",
)

try:
    data = load_cost_data()
except (OSError, ValueError) as exc:
    st.error(f"Could not load the sample dataset: {exc}")
    st.stop()

with st.sidebar:
    st.header("Explore costs")
    min_date, max_date = data["date"].min().date(), data["date"].max().date()
    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range
    environments = st.multiselect("Environment", sorted(data["environment"].unique()), default=sorted(data["environment"].unique()))
    regions = st.multiselect("Region", sorted(data["region"].unique()), default=sorted(data["region"].unique()))
    services = st.multiselect("Service", sorted(data["service"].unique()), default=sorted(data["service"].unique()))
    st.caption("The sample generator is deterministic. See scripts/generate_data.py.")

scope = filter_cost_data(data, data["date"].min(), data["date"].max(), environments, regions, services)
filtered = scope.loc[scope["date"].between(start_date, end_date)].reset_index(drop=True)
if filtered.empty:
    st.warning("No rows match these filters. Select at least one environment, region, and service.")
    st.stop()

scored = add_anomaly_scores(scope)
scored = scored.loc[scored["date"].between(start_date, end_date)]
summary = summarize_month_to_date(filtered)
anomalies = scored.loc[scored["is_anomaly"]].sort_values("robust_score", ascending=False)
budget_pct = (summary["variance"] / summary["budget"] * 100) if summary["budget"] else 0.0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Spend in selected range", f"${filtered['cost_usd'].sum():,.2f}")
k2.metric("Selected month-to-date", f"${summary['spend']:,.2f}", f"Budget variance ${summary['variance']:,.2f}")
k3.metric("Month-end run rate", f"${summary['run_rate']:,.2f}", "Simple MTD average")
k4.metric("Anomaly signals", f"{len(anomalies)}", f"Budget variance {budget_pct:+.1f}%")

left, right = st.columns([1.6, 1])
with left:
    st.subheader("Daily spend by service")
    daily = filtered.groupby(["date", "service"], as_index=False)["cost_usd"].sum()
    chart = px.line(daily, x="date", y="cost_usd", color="service", markers=False,
                    labels={"date": "Date", "cost_usd": "Daily cost (USD)", "service": "Service"})
    chart.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend_title_text="")
    st.plotly_chart(chart, use_container_width=True)
with right:
    st.subheader("Spend by service")
    by_service = filtered.groupby("service", as_index=False)["cost_usd"].sum().sort_values("cost_usd", ascending=False)
    donut = px.pie(by_service, names="service", values="cost_usd", hole=0.64,
                   labels={"cost_usd": "Cost (USD)"})
    donut.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend_title_text="")
    st.plotly_chart(donut, use_container_width=True)

st.subheader("Budget variance by environment")
budget_view = filtered.groupby("environment", as_index=False).agg(cost_usd=("cost_usd", "sum"), budget_usd=("daily_budget_usd", "sum"))
budget_view["variance_usd"] = budget_view["cost_usd"] - budget_view["budget_usd"]
bar = px.bar(budget_view, x="environment", y="variance_usd", color="variance_usd", color_continuous_scale=["#44d7b6", "#ffbe66", "#ff6b7a"],
             labels={"environment": "Environment", "variance_usd": "Spend minus budget (USD)"})
bar.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
st.plotly_chart(bar, use_container_width=True)

st.subheader("Unusual daily charges")
if anomalies.empty:
    st.success("No positive cost spikes crossed the robust-score threshold for this selection.")
else:
    display = anomalies[["date", "service", "environment", "region", "cost_usd", "baseline_median", "robust_score", "injected_spike"]].copy()
    display = display.rename(columns={"date": "Date", "service": "Service", "environment": "Environment", "region": "Region", "cost_usd": "Cost (USD)", "baseline_median": "Prior median (USD)", "robust_score": "Robust score", "injected_spike": "Seeded example"})
    st.dataframe(display.style.format({"Cost (USD)": "${:,.2f}", "Prior median (USD)": "${:,.2f}", "Robust score": "{:.2f}"}), use_container_width=True, hide_index=True)

with st.expander("How to read this dashboard"):
    st.markdown(
        "- **Budget variance** is selected spend minus the sum of the example daily budgets.\n"
        "- **Month-end run rate** scales the month-to-date daily average across the calendar month; it is not a predictive model.\n"
        "- **Anomaly score** uses each service's preceding 28 observations, rolling median, and MAD. Scores are calculated only from earlier dates.\n"
        "- The seeded spikes are artificial examples. Production use needs real billing ingestion, missing-data checks, seasonality, and alert thresholds tuned to the workload."
    )

st.divider()
st.caption("Built with Python, pandas, Plotly, and Streamlit • Synthetic data • Local-only demo")
