-- Built fresh from the raw tables on every run, so these never go stale.

-- 1. Mortgage rates: FRED is weekly, Redfin is monthly, so average each month's weeks
CREATE OR REPLACE VIEW monthly_rates AS
SELECT
    date_trunc('month', week_date)::DATE AS month,
    ROUND(AVG(rate_30yr), 2)             AS rate_30yr
FROM mortgage_rates
GROUP BY 1;

-- 2. Metro: Redfin gives single months, so roll it to 3 months to match the towns.
--    Flows (sales, listings) are summed over the window; levels are averaged.
CREATE OR REPLACE VIEW metro_rolling AS
SELECT
    region_id,
    region_name,
    date_trunc('month', period_end)::DATE AS month,
    SUM(homes_sold)        OVER w AS homes_sold,
    SUM(new_listings)      OVER w AS new_listings,
    AVG(median_sale_price) OVER w AS median_sale_price,   -- approximation: mean of 3 monthly medians
    AVG(inventory)         OVER w AS inventory,
    AVG(months_of_supply)  OVER w AS months_of_supply,
    AVG(median_dom)        OVER w AS median_dom,
    COUNT(*)               OVER w AS months_in_window
FROM redfin_market
WHERE frequency = 'Monthly'
WINDOW w AS (PARTITION BY region_id ORDER BY period_end ROWS BETWEEN 2 PRECEDING AND CURRENT ROW);

-- 3. Towns + rolled metro in one shape: one row per region per month
CREATE OR REPLACE VIEW market_3mo AS
SELECT
    region_id,
    region_name,
    'town' AS region_level,
    date_trunc('month', period_end)::DATE AS month,
    homes_sold, new_listings, median_sale_price, inventory, months_of_supply, median_dom
FROM redfin_market
WHERE frequency = 'Rolling 3 Months'
UNION ALL
SELECT
    region_id, region_name, 'metro', month,
    homes_sold, new_listings, median_sale_price, inventory, months_of_supply, median_dom
FROM metro_rolling
WHERE months_in_window = 3;   -- drop the first 2 months, which aren't full windows

-- 4. The dashboard table: changes, comparison to metro, rates, and a small-sample flag
CREATE OR REPLACE VIEW market_metrics AS
WITH with_changes AS (
    SELECT
        cur.*,
        cur.median_sale_price / prev_m.median_sale_price - 1 AS price_mom,
        cur.median_sale_price / prev_y.median_sale_price - 1 AS price_yoy,
        cur.inventory / prev_y.inventory - 1                 AS inventory_yoy
    FROM market_3mo cur
    -- Join on the actual month, not "the previous row", so a missing month can't
    -- silently shift the comparison onto the wrong period
    LEFT JOIN market_3mo prev_m
        ON prev_m.region_id = cur.region_id AND prev_m.month = cur.month - INTERVAL 1 MONTH
    LEFT JOIN market_3mo prev_y
        ON prev_y.region_id = cur.region_id AND prev_y.month = cur.month - INTERVAL 12 MONTH
)
SELECT
    t.*,
    t.median_sale_price / m.median_sale_price - 1 AS price_vs_metro,
    r.rate_30yr,
    t.homes_sold < 20 AS low_sample   -- medians on under 20 sales are noisy
FROM with_changes t
LEFT JOIN market_3mo m
    ON m.region_level = 'metro' AND m.month = t.month
LEFT JOIN monthly_rates r
    ON r.month = t.month;