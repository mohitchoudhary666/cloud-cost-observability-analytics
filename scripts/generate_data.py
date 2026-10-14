"""Generate a reproducible synthetic cloud-cost dataset using only Python's standard library."""

from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path


OUTPUT = Path(__file__).resolve().parents[1] / "data" / "cloud_daily_costs.csv"
SEED = 20261014
START = date(2025, 10, 15)
DAYS = 365

SERVICES = {
    "EC2": (16.50, 25.00),
    "RDS": (10.25, 16.00),
    "S3": (4.10, 7.00),
    "Lambda": (2.20, 4.00),
    "CloudWatch": (1.60, 3.00),
}
ENVIRONMENTS = {"production": 0.68, "staging": 0.22, "development": 0.10}
REGIONS = ("us-east-1", "us-west-2", "eu-west-1")
SPIKES = {
    ("EC2", 78): 2.7,
    ("RDS", 164): 3.2,
    ("S3", 251): 3.8,
    ("CloudWatch", 319): 4.0,
}


def main() -> None:
    rng = random.Random(SEED)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["date", "account", "region", "service", "environment", "cost_usd", "daily_budget_usd", "injected_spike"]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for day_index in range(DAYS):
            current = START + timedelta(days=day_index)
            seasonality = 1.0 + 0.08 * math.sin(day_index / 23.0)
            weekend = 0.91 if current.weekday() >= 5 else 1.0
            for service, (base, daily_budget) in SERVICES.items():
                environment = rng.choices(list(ENVIRONMENTS), weights=list(ENVIRONMENTS.values()), k=1)[0]
                env_factor = {"production": 1.0, "staging": 0.48, "development": 0.26}[environment]
                region = rng.choice(REGIONS)
                growth = 1.0 + 0.00035 * day_index
                noise = max(0.55, rng.gauss(1.0, 0.105))
                spike = SPIKES.get((service, day_index), 1.0)
                cost = base * env_factor * seasonality * weekend * growth * noise * spike
                writer.writerow({
                    "date": current.isoformat(),
                    "account": f"demo-{1 + (day_index % 2):03d}",
                    "region": region,
                    "service": service,
                    "environment": environment,
                    "cost_usd": f"{cost:.2f}",
                    "daily_budget_usd": f"{daily_budget * env_factor:.2f}",
                    "injected_spike": str(spike > 1.0).lower(),
                })
    print(f"Wrote {DAYS * len(SERVICES)} synthetic rows to {OUTPUT}")


if __name__ == "__main__":
    main()
