import csv
import os

import requests
import yaml
from dotenv import load_dotenv

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
OUT_PATH = "data/raw/fred_mortgage30us.csv"


def main():
    # 1. Secrets come from .env (locally) or GitHub Secrets (in Actions), never from code
    load_dotenv()
    api_key = os.environ["FRED_API_KEY"]

    # 2. What to pull comes from config, so changing it never means editing code
    with open("config/regions.yaml") as f:
        config = yaml.safe_load(f)
    series_id = config["fred"]["series_id"]

    # 3. Call the API. params= builds the URL safely; timeout= stops it hanging forever
    resp = requests.get(
        FRED_URL,
        params={"series_id": series_id, "api_key": api_key, "file_type": "json"},
        timeout=30,
    )
    if resp.status_code != 200:
        # Don't print resp.url here, because it contains the API key
        raise RuntimeError(f"FRED returned {resp.status_code}: {resp.text[:200]}")

    # 4. Keep date + value, and skip FRED's "." placeholder for missing weeks
    rows = [
        (obs["date"], float(obs["value"]))
        for obs in resp.json()["observations"]
        if obs["value"] != "."
    ]

    # 5. Write the raw CSV
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "rate_30yr"])
        writer.writerows(rows)

    print(f"{series_id}: {len(rows)} rows, {rows[0][0]} to {rows[-1][0]}, latest {rows[-1][1]}%")


if __name__ == "__main__":
    main()