import sys

import duckdb
import yaml

DB_PATH = "data/housing.duckdb"


def main():
    with open("config/regions.yaml") as f:
        config = yaml.safe_load(f)
    expected = len(config["towns"]) + 1  # every town plus the metro

    con = duckdb.connect(DB_PATH, read_only=True)
    latest_month, regions = con.execute("""
        SELECT month, COUNT(DISTINCT region_id)
        FROM market_metrics
        WHERE month = (SELECT MAX(month) FROM market_metrics)
        GROUP BY month
    """).fetchone()
    rate_rows = con.execute("SELECT COUNT(*) FROM mortgage_rates").fetchone()[0]
    con.close()

    problems = []
    if regions != expected:
        problems.append(f"expected {expected} regions in {latest_month}, found {regions}")
    if rate_rows < 2000:
        problems.append(f"only {rate_rows} mortgage rate rows; FRED pull looks broken")

    if problems:
        # A non-zero exit fails the GitHub Action, so a bad run never gets committed
        print("DATA CHECK FAILED: " + "; ".join(problems))
        sys.exit(1)
    print(f"Data check passed: {regions} regions for {latest_month}, {rate_rows} rate rows")


if __name__ == "__main__":
    main()