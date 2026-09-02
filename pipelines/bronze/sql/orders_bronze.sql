CREATE FUNCTION decode_debezium_decimal
AS 'com.atlas.bronze.DebeziumDecimalDecoder';

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
    'properties.group.id' = 'atlas-bronze-orders',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json'
);

SELECT
    payload.`after`.order_id AS order_id,
    payload.`after`.customer_id AS customer_id,
    payload.`after`.status AS status,
    decode_debezium_decimal(
        payload.`after`.total_amount,
        2
    ) AS total_amount,
    payload.`after`.created_at AS created_at,
    payload.`after`.updated_at AS updated_at,
    payload.`op` AS operation,
    payload.ts_ms AS event_ts
FROM orders_cdc
WHERE payload.`after`.order_id IS NOT NULL;
