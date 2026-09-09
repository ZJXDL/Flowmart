-- Business rule: orders must have a valid status.

SELECT
    order_id,
    status
FROM {{ ref('orders_current') }}
WHERE status NOT IN (
    'pending',
    'shipped',
    'completed',
    'cancelled',
    'refunded'
)
   OR status IS NULL