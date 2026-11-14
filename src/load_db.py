import duckdb

DB_PATH = "data/housing.duckdb"

# Redfin column -> our column. We keep the levels (prices, counts) and skip
# Redfin's own MoM/YoY columns, because computing those is our job in SQL.
REDFIN_COLUMNS = {
    "REGION ID": "region_id",
    "REGION NAME": "region_name",
    "REGION TYPE": "region_type",
    "FREQUENCY": "frequency",
    "PERIOD BEGIN": "period_begin",
    "PERIOD END": "period_end",
    "PROPERTY TYPE": "property_type",
    "IS SEASONALLY ADJUSTED": "is_seasonally_adjusted",
    "HOMES SOLD": "homes_sold",
    "MEDIAN SALE PRICE NSA ($)": "median_sale_price",
    "MEDIAN SALE PRICE PER SQ.FT. ($)": "median_ppsf",
    "NEW LISTINGS": "new_listings",
    "ACTIVE LISTINGS": "active_listings",
    "INVENTORY": "inventory",
    "PENDING SALES": "pending_sales",
    "MONTHS OF SUPPLY": "months_of_supply",
    "MEDIAN DAYS ON MARKET (DAYS)": "median_dom",
    "AVERAGE SALE TO LIST RATIO (%)": "avg_sale_to_list",
    "SHARE SOLD ABOVE ORIGINAL LIST (%)": "share_sold_above_list",
    "LAST UPDATED": "source_updated",
}

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS mortgage_rates (
    week_date   DATE PRIMARY KEY,
    rate_30yr   DOUBLE
);

CREATE TABLE IF NOT EXISTS redfin_market (
    region_id              INTEGER,
    region_name            VARCHAR,
    region_type            VARCHAR,
    frequency              VARCHAR,
    period_begin           DATE,
    period_end             DATE,
    property_type          VARCHAR,
    is_seasonally_adjusted BOOLEAN,
    homes_sold             DOUBLE,
    median_sale_price      DOUBLE,
    median_ppsf            DOUBLE,
    new_listings           DOUBLE,
    active_listings        DOUBLE,
    inventory              DOUBLE,
    pending_sales          DOUBLE,
    months_of_supply       DOUBLE,
    median_dom             DOUBLE,
    avg_sale_to_list       DOUBLE,
    share_sold_above_list  DOUBLE,
    source_updated         DATE,
    -- One row per region, period and slice: this is what makes upserts possible
    PRIMARY KEY (region_id, period_begin, period_end, property_type, is_seasonally_adjusted)
);
"""


def load_fred(con):
    con.execute("""
        INSERT OR REPLACE INTO mortgage_rates
        SELECT date, rate_30yr
        FROM read_csv('data/raw/fred_mortgage30us.csv', header = true)
    """)


def load_redfin(con, csv_path):
    select_list = ", ".join(f'"{src}" AS {dst}' for src, dst in REDFIN_COLUMNS.items())
    # all_varchar + nullstr: read everything as text with "NA" as missing,
    # then the table's column types do the converting on insert
    con.execute(f"""
        INSERT OR REPLACE INTO redfin_market BY NAME
        SELECT {select_list}
        FROM read_csv('{csv_path}', header = true, all_varchar = true, nullstr = 'NA')
    """)


def main():
    con = duckdb.connect(DB_PATH)
    con.execute(CREATE_TABLES)

    load_fred(con)
    load_redfin(con, "data/raw/redfin_cities.csv")
    load_redfin(con, "data/raw/redfin_metro.csv")

    for table in ["mortgage_rates", "redfin_market"]:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")
    con.close()


if __name__ == "__main__":
    main()