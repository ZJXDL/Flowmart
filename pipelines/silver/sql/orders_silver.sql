SET 'table.local-time-zone' = 'UTC';

SET 'execution.checkpointing.interval' = '10s';
SET 'execution.checkpointing.mode' = 'EXACTLY_ONCE';

CREATE CATALOG atlas_iceberg WITH (
    'type' = 'iceberg',
    'catalog-type' = 'rest',
    'uri' = 'http://172.23.0.7:8181',
    'warehouse' = 's3://warehouse',
    's3.endpoint' = 'http://172.23.0.5:9000',
    's3.path-style-access' = 'true',
    's3.access-key-id' = 'atlas',
    's3.secret-access-key' = 'atlas_minio_password'
);

USE CATALOG atlas_iceberg;

CREATE DATABASE IF NOT EXISTS atlas;

USE atlas;

CREATE TABLE IF NOT EXISTS silver_orders (
    order_id STRING,
    customer_id STRING,
    status STRING,
    total_amount DECIMAL(38,2),
    created_at TIMESTAMP_LTZ(6),
    updated_at TIMESTAMP_LTZ(6),
    operation STRING,
    event_ts BIGINT
);

INSERT INTO silver_orders
SELECT
    order_id,
    customer_id,
    status,
    total_amount,
    created_at,
    updated_at,
    operation,
    event_ts
FROM bronze_orders
WHERE order_id IS NOT NULL;