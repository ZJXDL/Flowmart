-- Gold Layer: Daily Sales
-- Aggregated from the deduplicated Silver table.

CREATE TABLE iceberg.atlas.gold_daily_sales AS
SELECT
    CAST(created_at AS DATE) AS sales_date,
    COUNT(*) AS order_count,
    SUM(total_amount) AS total_revenue,
    AVG(total_amount) AS average_order_value
FROM iceberg.atlas.silver_orders_current
WHERE order_id IS NOT NULL
GROUP BY CAST(created_at AS DATE);