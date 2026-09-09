-- Business rule: order totals must never be negative.

SELECT
    order_id,
    total_amount
FROM {{ ref('orders_current') }}
WHERE total_amount < 0