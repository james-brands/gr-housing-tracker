import os

import duckdb

DB_PATH = "data/housing.duckdb"
EXPORT_DIR = "data/processed"


def main():
    con = duckdb.connect(DB_PATH)
    with open("sql/transform.sql") as f:
        con.execute(f.read())

    # Quick look at the latest month so you can eyeball the results
    print(con.sql("""
        SELECT region_name, month, median_sale_price::INT AS price,
               ROUND(price_yoy * 100, 1) AS yoy_pct,
               ROUND(price_vs_metro * 100, 1) AS vs_metro_pct,
               homes_sold::INT AS sold, low_sample, rate_30yr
        FROM market_metrics
        WHERE month = (SELECT MAX(month) FROM market_metrics)
        ORDER BY region_level DESC, price DESC
    """))

    # Export the dashboard tables as CSV. These small files are what get committed,
    # and git only sees a change when the numbers actually change.
    os.makedirs(EXPORT_DIR, exist_ok=True)
    con.execute(f"COPY (SELECT * FROM market_metrics ORDER BY region_id, month) TO '{EXPORT_DIR}/market_metrics.csv'")
    con.execute(f"COPY (SELECT * FROM monthly_rates ORDER BY month) TO '{EXPORT_DIR}/monthly_rates.csv'")
    print(f"Exported market_metrics.csv and monthly_rates.csv to {EXPORT_DIR}/")
    con.close()


if __name__ == "__main__":
    main()