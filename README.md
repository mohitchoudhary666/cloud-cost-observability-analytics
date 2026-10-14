# Cloud Cost Observability Analytics

An interactive FinOps dashboard for exploring daily cloud spend, spotting unusual service-level charges, and estimating the current month's spend from historical usage.

> **Dataset:** All records in `data/cloud_daily_costs.csv` are deterministic synthetic examples. They are not AWS billing records and do not represent actual customer costs. The project runs locally and needs no AWS account, credentials, or network connection after dependencies are installed.

## What it does

- Filters by date range, environment, AWS-style region, and service.
- Tracks total spend, budget variance, and a simple month-end run-rate estimate.
- Compares daily spend by service and environment.
- Flags service/day spend spikes using a trailing 28-day rolling median and median absolute deviation (MAD), avoiding look-ahead by using only prior days.
- Includes a reproducible standard-library data generator so you can regenerate the synthetic dataset.

## Run locally

Use Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens in your browser at the local Streamlit address. No AWS keys or cloud resources are used.

## Regenerate the sample data

```bash
python scripts/generate_data.py
```

The generator uses a fixed random seed and writes one year of daily service-level rows to `data/cloud_daily_costs.csv`. It deliberately injects a few labeled cost spikes so the anomaly view has examples to show.

## Data fields

| Column | Meaning |
| --- | --- |
| `date` | Usage date (UTC, date only) |
| `account` | Synthetic account alias |
| `region` | Example region label |
| `service` | Synthetic service category |
| `environment` | `production`, `staging`, or `development` |
| `cost_usd` | Simulated daily service spend in USD |
| `daily_budget_usd` | Example service-level daily budget |
| `injected_spike` | Generator label for intentionally seeded sample spikes |

## Anomaly method and limitations

For each service, the dashboard compares a day's cost with the preceding 28 available daily observations. It calculates a robust score using the rolling median and MAD, then flags positive scores above 3.5. The first 14 observations for each service are shown without a score because there is not enough history. This is a transparent demonstration, not a production billing alert: seasonality, missing data, credits, shared costs, and real AWS Cost and Usage Report schemas need additional handling.

The month-end estimate is a simple month-to-date daily average multiplied by the number of days in the month. It is a run-rate illustration, not a forecast model.

## Project structure

```text
app.py                         Streamlit dashboard
src/analytics.py               Loading, filtering, aggregation, anomaly scoring
scripts/generate_data.py       Reproducible synthetic data generator
data/cloud_daily_costs.csv     One year of sample data
requirements.txt               Runtime dependencies
```

## Ideas to extend

- Add AWS Cost and Usage Report ingestion behind an explicit local file upload.
- Add team, owner, and cost-center tag completeness analysis.
- Compare forecast errors against a seasonal baseline.
- Add Athena/Glue deployment as an optional infrastructure layer.

## License

MIT. See [LICENSE](LICENSE).
