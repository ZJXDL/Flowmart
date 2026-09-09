{{ config(materialized='table') }}

SELECT
    CAST(created_at AS DATE) AS sales_date,
    COUNT(*) AS order_count,
    SUM(total_amount) AS total_revenue,
    AVG(total_amount) AS average_order_value
FROM {{ ref('orders') }}
WHERE order_id IS NOT NULL
GROUP BY CAST(created_at AS DATE)