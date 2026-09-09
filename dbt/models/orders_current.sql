{{ config(materialized='table') }}

SELECT
    order_id,
    customer_id,
    status,
    total_amount,
    created_at,
    updated_at,
    operation,
    event_ts
FROM (
    SELECT
        order_id,
        customer_id,
        status,
        total_amount,
        created_at,
        updated_at,
        operation,
        event_ts,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY event_ts DESC
        ) AS rn
    FROM iceberg.atlas.silver_orders
    WHERE order_id IS NOT NULL
)
WHERE rn = 1
  AND operation <> 'd'