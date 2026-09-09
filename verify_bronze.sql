SET 'execution.runtime-mode' = 'batch';

CREATE CATALOG atlas_iceberg WITH (
    'type' = 'iceberg',
    'catalog-type' = 'rest',
    'uri' = 'http://atlas-iceberg-rest:8181',
    'warehouse' = 's3://warehouse',
    's3.endpoint' = 'http://atlas-minio:9000',
    's3.path-style-access' = 'true',
    's3.access-key-id' = 'atlas',
    's3.secret-access-key' = 'atlas_minio_password'
);

USE CATALOG atlas_iceberg;

USE atlas;

SELECT
    COUNT(*) AS row_count,
    COUNT(order_id) AS order_ids,
    COUNT(total_amount) AS amounts
FROM bronze_orders;