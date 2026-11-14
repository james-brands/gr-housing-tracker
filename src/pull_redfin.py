import csv
import os

import requests
import yaml

BASE_URL = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_data_center/property_types/monthly"
SOURCES = {
    "cities": (f"{BASE_URL}/all_cities.csv", "data/raw/redfin_cities.csv"),
    "metro": (f"{BASE_URL}/all_metros.csv", "data/raw/redfin_metro.csv"),
}


def pull(url, out_path, region_ids, property_type, seasonally_adjusted):
    # stream=True downloads the file in pieces instead of holding 2 GB in memory
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        resp.encoding = "utf-8"  # S3 doesn't say, so tell requests how to decode the bytes
        lines = resp.iter_lines(decode_unicode=True)
        reader = csv.DictReader(lines)

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        kept = 0
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                # Filter as rows arrive, so only the matching rows are ever kept
                if (
                    row["REGION ID"] in region_ids
                    and row["PROPERTY TYPE"] == property_type
                    and row["IS SEASONALLY ADJUSTED"] == seasonally_adjusted
                ):
                    writer.writerow(row)
                    kept += 1
    return kept


def main():
    with open("config/regions.yaml") as f:
        config = yaml.safe_load(f)

    # Redfin's CSV stores everything as text, so compare IDs and flags as text too
    town_ids = {str(t["redfin_id"]) for t in config["towns"]}
    metro_ids = {str(config["metro"]["redfin_id"])}
    property_type = config["redfin_filters"]["property_type"]
    sa_flag = str(config["redfin_filters"]["seasonally_adjusted"]).lower()

    for name, ids in [("cities", town_ids), ("metro", metro_ids)]:
        url, out_path = SOURCES[name]
        kept = pull(url, out_path, ids, property_type, sa_flag)
        print(f"{name}: kept {kept} rows -> {out_path}")


if __name__ == "__main__":
    main()