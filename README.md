# Flowmart

> An agentic real-time e-commerce lakehouse built with PostgreSQL, Debezium, Kafka, Apache Flink, Apache Iceberg, MinIO, Trino, dbt, semantic modeling, AI analytics, autonomous anomaly detection, observability, and CI/CD.

Flowmart is an end-to-end modern data platform that simulates an e-commerce environment and continuously transforms operational transactions into analytical, governed, and AI-accessible data.

```text
PostgreSQL
    ↓
Debezium CDC
    ↓
Kafka
    ↓
Apache Flink
    ↓
Apache Iceberg + MinIO
    ↓
Bronze → Silver → Gold
    ↓
dbt
    ↓
Semantic Layer
    ↓
Trino
    ├── BI / SQL Analytics
    └── AI Analyst
          ├── Natural-language analytics
          └── Anomaly Detection
                 ↓
            Observability
                 ↓
              CI/CD
```

---

## Why Flowmart?

Flowmart demonstrates how the components of a modern data platform work together rather than presenting isolated technology demos.

The platform covers:

* Operational data generation
* Change Data Capture
* Event streaming
* Stream processing
* Open lakehouse storage
* Bronze/Silver/Gold modeling
* Analytics engineering
* Data quality
* Semantic modeling
* Natural-language analytics
* LLM-powered analysis
* Autonomous anomaly detection
* Pipeline observability
* Automated testing
* CI/CD

---

# Technology Stack

| Layer             | Technology                                  |
| ----------------- | ------------------------------------------- |
| OLTP              | PostgreSQL 17                               |
| CDC               | Debezium 3.3                                |
| Streaming         | Apache Kafka 4.1                            |
| Stream processing | Apache Flink 2.1                            |
| Lakehouse         | Apache Iceberg 1.11                         |
| Object storage    | MinIO                                       |
| Query engine      | Trino 483                                   |
| Transformation    | dbt                                         |
| AI                | Python + Groq/OpenAI-compatible LLM clients |
| Semantic modeling | Custom YAML semantic contract               |
| Data quality      | dbt + Python                                |
| Anomaly detection | Python statistical detection                |
| Observability     | Python metrics + health checks              |
| Infrastructure    | Docker Compose                              |
| CI/CD             | GitHub Actions                              |
| Languages         | Python, SQL, Java                           |

---

# Architecture

```text
                    ┌──────────────────────┐
                    │   E-Commerce App     │
                    │ Generator / Simulator│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     PostgreSQL       │
                    │       OLTP           │
                    └──────────┬───────────┘
                               │
                         Logical CDC
                               │
                               ▼
                    ┌──────────────────────┐
                    │       Debezium       │
                    │    Kafka Connect     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │        Kafka         │
                    │     Event Stream     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Apache Flink      │
                    │  Stream Processing   │
                    └──────────┬───────────┘
                               │
                               ▼
             ┌──────────────────────────────────┐
             │     Apache Iceberg + MinIO       │
             │          Lakehouse Storage        │
             └───────────────┬──────────────────┘
                             │
                 ┌───────────┼───────────┐
                 ▼           ▼           ▼
              Bronze      Silver       Gold
                 │           │           │
                 └───────────┼───────────┘
                             ▼
                            dbt
                             │
                             ▼
                     Semantic Contract
                             │
                             ▼
                           Trino
                       ┌─────┴─────┐
                       ▼           ▼
                    Analytics   AI Analyst
                                   │
                         ┌─────────┴─────────┐
                         ▼                   ▼
                    LLM Analysis       Anomaly Detection
                                             │
                                             ▼
                                        Observability
```

---

# Project Structure

```text
flowmart/
│
├── apps/
│   ├── ecommerce-generator/
│   │   ├── generator.py
│   │   └── simulator.py
│   │
│   └── ai-analyst/
│       ├── requirements.txt
│       └── src/
│           ├── analyst_answer_generator.py
│           ├── analyst_engine.py
│           ├── analyst_intent.py
│           ├── analytical_query_service.py
│           ├── groq_llm_client.py
│           ├── intent_interpreter.py
│           ├── llm_analyst_engine.py
│           ├── llm_client.py
│           ├── llm_intent_interpreter.py
│           ├── openai_llm_client.py
│           ├── openrouter_llm_client.py
│           ├── run_real_analyst.py
│           ├── semantic_bridge.py
│           ├── semantic_query_builder.py
│           └── tools/
│               └── trino_tool.py
│
├── infrastructure/
│   ├── postgres/
│   ├── kafka/
│   ├── flink/
│   ├── minio/
│   ├── iceberg/
│   └── trino/
│
├── ingestion/
│   ├── cdc/
│   └── events/
│
├── pipelines/
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
├── semantic/
│   ├── metrics/
│   ├── dimensions/
│   ├── relationships/
│   ├── registry.py
│   └── validator.py
│
├── quality/
│   └── anomaly/
│       ├── detectors/
│       ├── alerts/
│       ├── anomaly_service.py
│       └── anomaly_runner.py
│
├── observability/
│   ├── metrics/
│   ├── dashboards/
│   └── alerts/
│
├── dbt/
│   ├── models/
│   └── tests/
│
├── dashboards/
├── tests/
├── docs/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── docker-compose.yml
├── dbt_project.yml
├── .env.example
├── .gitignore
└── README.md
```

---

# 1. E-Commerce Data Generation

Flowmart includes a Python e-commerce generator that creates operational data in PostgreSQL.

The source schema contains:

* Categories
* Products
* Customers
* Orders
* Order items
* Payments
* Inventory

The generated dataset contains:

```text
Categories       6
Products        31
Customers    1,000
Orders       5,000+
Order Items  15,000+
Payments     5,000+
Inventory       31
```

A live simulator generates additional transactions.

Each transaction is performed atomically:

```text
Create order
    ↓
Create order items
    ↓
Update inventory
    ↓
Calculate total
    ↓
Create payment
    ↓
Commit
```

This provides a continuously changing operational source for the streaming architecture.

---

# 2. Change Data Capture

PostgreSQL is configured for logical replication.

Debezium captures database changes and publishes them to Kafka.

Example topics:

```text
atlas.public.categories
atlas.public.customers
atlas.public.inventory
atlas.public.order_items
atlas.public.orders
atlas.public.payments
```

CDC events preserve information such as:

* Operation type
* Event timestamp
* Before state
* After state

The ingestion flow is:

```text
PostgreSQL
    ↓
Logical Replication
    ↓
Debezium
    ↓
Kafka
```

This allows downstream systems to react to database changes without directly coupling themselves to the OLTP database.

---

# 3. Kafka

Kafka acts as the event backbone.

It decouples PostgreSQL from downstream stream-processing workloads and provides:

* Durable event storage
* Consumer offsets
* Replay capability
* Producer/consumer decoupling
* Multiple independent consumers

This makes Kafka the central transport layer between CDC and streaming analytics.

---

# 4. Apache Flink

Apache Flink consumes the CDC event stream and writes processed data into the lakehouse.

The streaming layer uses:

* Exactly-once checkpointing
* 10-second checkpoint intervals
* Kafka event consumption
* Iceberg sinks
* UTC processing timezone

The Bronze pipeline preserves CDC information while converting the incoming events into an analytical Iceberg representation.

---

# 5. Lakehouse

Flowmart uses Apache Iceberg for table management and MinIO for S3-compatible object storage.

The lakehouse follows a layered architecture:

```text
Bronze
  ↓
Silver
  ↓
Gold
```

## Bronze

Bronze remains close to the incoming CDC representation.

The order event model contains:

```text
order_id
customer_id
status
total_amount
created_at
updated_at
operation
event_ts
```

This layer provides traceability back toward the source events.

## Silver

Silver reconstructs useful analytical order state from the CDC stream.

It handles:

* Latest-record selection
* Delete handling
* CDC state reconstruction
* Normalization
* Analytical typing

## Gold

Gold contains business-oriented analytical models.

The current daily sales model calculates:

* Order count
* Revenue
* Average order value

Example verified result:

```text
Date          Orders    Revenue       Avg Order
2026-09-02    5015      4,967,781.58   990.58
```

---

# 6. Trino

Trino provides the SQL query layer over Iceberg.

The verified environment uses Trino 483.

The Iceberg catalog exposes the Flowmart schema:

```text
iceberg.atlas
```

Verified tables include:

```text
bronze_orders
silver_orders
silver_orders_current
orders
orders_current
daily_sales
```

This gives analytical workloads a standard SQL interface over the lakehouse.

---

# 7. dbt

dbt provides the analytics engineering layer.

Current models:

```text
dbt/models/
├── orders_current.sql
├── orders.sql
├── daily_sales.sql
└── schema.yml
```

The current-state model reconstructs the latest order record from CDC-derived data.

The analytical model then aggregates business metrics.

dbt also validates schema and business rules.

Verified test suite:

```text
17 / 17 passed
```

Example status distribution from the current dataset:

```text
completed    3245
pending       472
refunded      444
cancelled     441
shipped       413
```

---

# 8. Semantic Layer

Flowmart contains a project-level semantic contract implemented with YAML.

It defines:

```text
9 metrics
6 dimensions
3 relationships
```

The semantic layer provides a controlled vocabulary between business concepts and physical data structures.

For example:

```text
Business concept
      ↓
Semantic metric
      ↓
Query definition
      ↓
Trino SQL
```

The semantic layer is intentionally described as a **project-level semantic contract**, rather than being presented as the official dbt Semantic Layer / MetricFlow implementation.

---

# 9. AI Analyst

Flowmart contains an AI-powered analytical assistant.

A natural-language question passes through:

```text
User Question
      ↓
Intent Detection
      ↓
Semantic Interpretation
      ↓
Query Construction
      ↓
Security Validation
      ↓
Trino
      ↓
Query Result
      ↓
LLM
      ↓
Natural-Language Answer
```

Example questions include:

```text
What percentage of orders were refunded?

What was the revenue on the latest business date?

Which customers generated the most revenue?
```

The AI layer supports Groq and OpenAI-compatible model clients.

A real end-to-end LLM demonstration was successfully run against the Flowmart analytical data.

---

# 10. AI Query Security

The AI Analyst does not receive unrestricted database access.

The Trino tool is designed for controlled analytical reads.

The architecture intentionally separates:

```text
Natural-language reasoning
        ↓
Query construction
        ↓
Query validation
        ↓
Read-only analytical execution
```

This reduces the risk of an LLM directly executing arbitrary database modifications.

---

# 11. Autonomous Anomaly Detection

Flowmart contains a statistical anomaly detection subsystem.

Structure:

```text
quality/anomaly/
├── detectors/
├── alerts/
├── anomaly_service.py
└── anomaly_runner.py
```

The system separates:

```text
Detection
    ↓
Evaluation
    ↓
Alert construction
```

Verified validation:

```text
Statistical detector      10 / 10
Anomaly service           11 / 11
Alert builder              8 / 8
Anomaly runner             8 / 8
----------------------------------
Total                     37 / 37
```

The architecture is designed so additional detectors can be introduced without replacing the service layer.

---

# 12. Observability

Flowmart monitors the health of its data-processing components.

Structure:

```text
observability/
├── metrics/
├── dashboards/
└── alerts/
```

The observability subsystem includes:

* Pipeline metrics
* Health checks
* Alert generation
* Health dashboard logic

Verified validation:

```text
Pipeline metrics          13 / 13
Observability alerts      11 / 11
Health dashboard          11 / 11
-----------------------------------
Total                     35 / 35
```

Combined anomaly detection and observability validation:

```text
72 / 72 passed
```

---

# 13. CI/CD

GitHub Actions is configured to automatically validate the project.

The CI workflow covers:

* Dependency installation
* Semantic layer validation
* Semantic query builder
* Analyst intent
* LLM intent interpreter
* Trino query security
* Answer generation
* LLM analyst engine
* Anomaly detection
* Anomaly alerts
* Anomaly runner
* Pipeline metrics
* Observability alerts
* Health dashboard

Workflow:

```text
Push / Pull Request
        ↓
GitHub Actions
        ↓
Install Dependencies
        ↓
Run Validation
        ↓
Run Application Tests
        ↓
Run Anomaly Tests
        ↓
Run Observability Tests
```

The workflow is located at:

```text
.github/workflows/ci.yml
```

> The workflow is configured locally but has not yet been confirmed through a successful GitHub-hosted Actions run.

---

# Running Flowmart

## Prerequisites

Install:

* Docker Desktop
* Python 3.10+
* Git

For AI functionality, configure the required provider API key in the local environment.

Never commit secrets to the repository.

---

## Start Infrastructure

From the project root:

```cmd
docker compose up -d
```

Check containers:

```cmd
docker compose ps
```

---

# Service Ports

| Service       | Address          |
| ------------- | ---------------- |
| PostgreSQL    | `localhost:5433` |
| MinIO API     | `localhost:9010` |
| MinIO Console | `localhost:9011` |
| Kafka         | `localhost:9092` |
| Kafka UI      | `localhost:8080` |
| Flink         | `localhost:8081` |
| Kafka Connect | `localhost:8083` |
| Iceberg REST  | `localhost:8181` |
| Trino         | `localhost:8082` |

---

# Verification

## PostgreSQL

```cmd
docker exec -it atlas-postgres psql -U atlas -d atlas
```

## Kafka

```cmd
docker exec atlas-kafka kafka-topics.sh --bootstrap-server kafka:9092 --list
```

## Trino

```cmd
curl -4 http://127.0.0.1:8082/v1/info
```

Show catalogs:

```cmd
docker exec atlas-trino trino --execute "SHOW CATALOGS"
```

Show Iceberg schemas:

```cmd
docker exec atlas-trino trino --execute "SHOW SCHEMAS FROM iceberg"
```

Show Flowmart tables:

```cmd
docker exec atlas-trino trino --execute "SHOW TABLES FROM iceberg.atlas"
```

---

# Engineering Highlights

### Event-driven ingestion

Database changes are captured through logical replication and propagated through Kafka.

### Streaming architecture

Apache Flink processes events continuously rather than relying exclusively on scheduled batch extraction.

### Open lakehouse architecture

Iceberg provides the table format while MinIO provides S3-compatible storage.

### Layered data architecture

Bronze, Silver, and Gold layers separate raw ingestion, cleaned state, and business-oriented analytics.

### Analytics engineering

dbt provides repeatable transformation logic and automated tests.

### Semantic modeling

Business metrics and dimensions are defined separately from their physical query implementation.

### AI-powered analytics

Natural-language questions can be translated into controlled analytical queries and summarized by an LLM.

### AI security

The AI Analyst uses a controlled read-only Trino interface rather than unrestricted database access.

### Automated anomaly detection

Statistical detectors identify unusual analytical behavior and generate structured alerts.

### Observability

The platform monitors its own pipeline health in addition to processing business data.

### CI/CD

GitHub Actions provides automated validation for future changes.

---

# Validation Summary

| Component                |  Result |
| ------------------------ | ------: |
| PostgreSQL generator     |       ✅ |
| Live simulator           |       ✅ |
| Debezium CDC             |       ✅ |
| Kafka                    |       ✅ |
| Flink                    |       ✅ |
| Iceberg                  |       ✅ |
| MinIO                    |       ✅ |
| Bronze                   |       ✅ |
| Silver                   |       ✅ |
| Gold                     |       ✅ |
| Trino                    |       ✅ |
| dbt                      | 17 / 17 |
| Semantic layer           |       ✅ |
| AI Analyst               |       ✅ |
| Real LLM E2E             |       ✅ |
| Anomaly detection        | 37 / 37 |
| Observability            | 35 / 35 |
| Anomaly + observability  | 72 / 72 |
| CI/CD configuration      |       ✅ |
| GitHub Actions execution |       ⏳ |

---

# Known Data Limitation

The current dataset contains limited historical daily data.

Because statistical anomaly detection benefits from a longer historical baseline, the daily revenue detector cannot currently demonstrate a genuine long-term baseline using the existing dataset.

Flowmart intentionally does **not** fabricate historical observations to make the anomaly detection system appear more capable than it is.

A future extension can run the simulator over a longer period or generate controlled historical events to establish meaningful time-series baselines.

---

# Future Improvements

Potential extensions include:

* Longer historical data generation
* Customer lifetime value models
* Product-level analytical models
* Real-time dashboards
* Kafka Schema Registry
* Data lineage
* OpenTelemetry
* Additional anomaly detectors
* Automated remediation
* AI evaluation tracking
* AI conversation memory
* Role-based analytical access
* Cloud deployment
* Kubernetes
* Terraform
* Production secret management

---

# Portfolio Takeaway

Flowmart demonstrates the design and implementation of a complete modern data platform.

The project combines:

```text
Data Engineering
        +
Streaming
        +
Lakehouse Architecture
        +
Analytics Engineering
        +
Data Quality
        +
Semantic Modeling
        +
Generative AI
        +
Anomaly Detection
        +
Observability
        +
CI/CD
```

The result is an end-to-end platform that takes operational e-commerce transactions and transforms them into governed, queryable, observable, and AI-accessible analytical data.

---

## Author

Built as a portfolio data engineering project focused on modern lakehouse architecture, streaming systems, analytics engineering, and AI-powered data platforms.
