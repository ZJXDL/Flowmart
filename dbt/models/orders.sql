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
FROM {{ ref('orders_current') }}
WHERE order_id IS NOT NULL