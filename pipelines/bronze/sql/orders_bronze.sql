-- ============================================================
-- ATLAS BRONZE ORDERS PIPELINE
-- ============================================================

SET 'table.local-time-zone' = 'UTC';

-- Iceberg streaming sink requires checkpoints for commits
SET 'execution.checkpointing.interval' = '10s';
SET 'execution.checkpointing.mode' = 'EXACTLY_ONCE';


-- ============================================================
-- 1. Register Iceberg REST Catalog
-- ============================================================

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

CREATE DATABASE IF NOT EXISTS atlas;

USE atlas;

CREATE TABLE IF NOT EXISTS bronze_orders (
    order_id STRING,
    customer_id STRING,
    status STRING,
    total_amount DECIMAL(38,2),
    created_at TIMESTAMP_LTZ(6),
    updated_at TIMESTAMP_LTZ(6),
    operation STRING,
    event_ts BIGINT
);


-- ============================================================
-- 2. Register Debezium decimal decoder
-- ============================================================

CREATE TEMPORARY SYSTEM FUNCTION decode_debezium_decimal
AS 'com.atlas.bronze.DebeziumDecimalDecoder';


-- ============================================================
-- 3. Switch back to Flink default catalog
-- ============================================================

USE CATALOG default_catalog;

USE default_database;


-- ============================================================
-- 4. Kafka CDC source
-- ============================================================

CREATE TABLE orders_cdc (
    payload ROW<
        `before` ROW<
            order_id STRING,
            customer_id STRING,
            status STRING,
            total_amount STRING,
            created_at STRING,
            updated_at STRING
        >,
        `after` ROW<
            order_id STRING,
            customer_id STRING,
            status STRING,
            total_amount STRING,
            created_at STRING,
            updated_at STRING
        >,
        `source` ROW<
            version STRING,
            connector STRING,
            name STRING,
            ts_ms BIGINT,
            snapshot STRING,
            db STRING,
            sequence STRING,
            ts_us BIGINT,
            ts_ns BIGINT,
            schema STRING,
            `table` STRING,
            txId BIGINT,
            lsn BIGINT,
            xmin BIGINT
        >,
        `transaction` ROW<
            id STRING,
            total_order BIGINT,
            data_collection_order BIGINT
        >,
        `op` STRING,
        ts_ms BIGINT,
        ts_us BIGINT,
        ts_ns BIGINT
    >
) WITH (
    'connector' = 'kafka',
    'topic' = 'atlas.public.orders',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'atlas-bronze-orders-v5',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json'
);


-- ============================================================
-- 5. Stream CDC events into Iceberg Bronze
-- ============================================================

INSERT INTO atlas_iceberg.atlas.bronze_orders

SELECT
    payload.`after`.order_id,
    payload.`after`.customer_id,
    payload.`after`.status,

    CAST(
        decode_debezium_decimal(
            payload.`after`.total_amount,
            2
        ) AS DECIMAL(38,2)
    ),

    CAST(
        REPLACE(
            REPLACE(payload.`after`.created_at, 'T', ' '),
            'Z',
            ''
        ) AS TIMESTAMP_LTZ(6)
    ),

    CAST(
        REPLACE(
            REPLACE(payload.`after`.updated_at, 'T', ' '),
            'Z',
            ''
        ) AS TIMESTAMP_LTZ(6)
    ),

    payload.`op`,
    payload.ts_ms

FROM default_catalog.default_database.orders_cdc

WHERE payload.`after`.order_id IS NOT NULL;